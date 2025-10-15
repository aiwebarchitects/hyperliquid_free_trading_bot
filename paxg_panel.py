#!/usr/bin/env python3
"""
PAXG Trading Bot Panel - Simple monitoring interface for PAXG RSI 1MIN Double Confirm bot
Free Hyperliquid Python Trading Bot 4 PAXG + Panel
"""

import curses
import time
import sys
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List

# Import bot modules
from executer import example_utils
from hyperliquid.utils import constants
import settings

# Import for RSI calculation
import pandas as pd
import requests

# Import backtest helper
from helpers.backtest_helper import PanelBacktester


class PAXGPanel:
    def __init__(self, stdscr, use_testnet: bool = None):
        self.stdscr = stdscr
        
        # Load configuration from settings.py
        self.use_testnet = use_testnet if use_testnet is not None else settings.BOT_USE_TESTNET
        self.api_url = constants.TESTNET_API_URL if self.use_testnet else constants.MAINNET_API_URL
        
        # Trading configuration
        self.coin = "PAXG"
        
        # Load RSI parameters from settings
        self.rsi_period = settings.BOT_RSI_PERIOD
        self.oversold_threshold = settings.BOT_RSI_OVERSOLD
        self.overbought_threshold = settings.BOT_RSI_OVERBOUGHT
        
        # Load risk management from settings
        self.take_profit_pct = settings.BOT_TAKE_PROFIT
        self.stop_loss_pct = settings.BOT_STOP_LOSS
        
        # Double confirm tracking
        self.last_rsi_values: List[float] = []
        self.rsi_topped = False
        self.support_level = None
        
        # Initialize colors
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(6, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(7, curses.COLOR_BLACK, curses.COLOR_RED)
        
        # Data storage
        self.account_data = {
            'balance': 0.0,
            'equity': 0.0,
            'total_pnl': 0.0,
            'margin_used': 0.0
        }
        
        self.position_data = {
            'size': 0.0,
            'entry_price': 0.0,
            'current_price': 0.0,
            'unrealized_pnl': 0.0,
            'position_value': 0.0
        }
        
        self.rsi_value = None
        self.last_update = None
        
        # Current view/tab
        self.current_tab = 0  # 0=Main, 1=Bot, 2=History, 3=Backtest
        self.tab_names = ["MAIN", "BOT", "HISTORY", "BACKTEST"]
        
        # Trade history
        self.trade_history = []
        
        # Bot control
        self.bot_running = False
        self.bot_logs = []
        self.max_logs = 100
        self.last_buy_time = None
        self.position_value_usd = settings.BOT_POSITION_VALUE_USD
        self.max_total_position_usd = settings.BOT_MAX_TOTAL_POSITION_USD
        self.buy_cooldown_minutes = settings.BOT_BUY_COOLDOWN_MINUTES
        
        # Initialize exchange connection
        self.address = None
        self.info = None
        self.exchange = None
        self._setup_exchange()
        
        # Initialize backtester
        self.backtester = PanelBacktester()
        self.backtest_results = None
        self.backtest_running = False
    
    def _setup_exchange(self):
        """Setup exchange connection"""
        try:
            self.address, self.info, self.exchange = example_utils.setup(
                self.api_url, skip_ws=True
            )
        except Exception as e:
            raise Exception(f"Failed to setup exchange: {e}")
    
    def safe_addstr(self, y, x, text, attr=0):
        """Safely add string with boundary checking"""
        h, w = self.stdscr.getmaxyx()
        if y >= h - 1 or x >= w - 1:
            return False
        try:
            if attr:
                self.stdscr.addstr(y, x, text[:w-x-1], attr)
            else:
                self.stdscr.addstr(y, x, text[:w-x-1])
            return True
        except curses.error:
            return False
    
    def calculate_rsi(self, prices: pd.Series) -> Optional[float]:
        """Calculate RSI"""
        if len(prices) < self.rsi_period + 1:
            return None
        
        delta = prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.ewm(span=self.rsi_period, adjust=False).mean()
        avg_loss = loss.ewm(span=self.rsi_period, adjust=False).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.iloc[-1]
    
    def get_recent_candles(self, limit: int = 100) -> Optional[pd.DataFrame]:
        """Get recent candle data for PAXG from Binance"""
        try:
            url = "https://api.binance.com/api/v3/klines"
            params = {
                "symbol": "PAXGUSDT",
                "interval": "1m",
                "limit": limit
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code != 200:
                return None
            
            data = response.json()
            if not data or len(data) == 0:
                return None
            
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            df['price'] = df['close'].astype(float)
            df['low'] = df['low'].astype(float)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            return df
            
        except Exception as e:
            return None
    
    def update_rsi_state(self, current_rsi: float, df: pd.DataFrame):
        """Update RSI state for double confirm logic"""
        # Keep track of last 10 RSI values
        self.last_rsi_values.append(current_rsi)
        if len(self.last_rsi_values) > 10:
            self.last_rsi_values.pop(0)
        
        # Check if RSI topped (reached overbought or made a peak)
        if len(self.last_rsi_values) >= 3:
            recent_high = max(self.last_rsi_values[-10:])
            if recent_high >= self.overbought_threshold:
                self.rsi_topped = True
            # Or if RSI made a local peak above 60
            elif (len(self.last_rsi_values) >= 3 and 
                  self.last_rsi_values[-2] > self.last_rsi_values[-3] and 
                  self.last_rsi_values[-2] > self.last_rsi_values[-1] and
                  self.last_rsi_values[-2] > 60):
                self.rsi_topped = True
        
        # Calculate support level (lowest low in last 10 candles)
        if len(df) >= 10:
            self.support_level = df['low'].iloc[-10:].min()
    
    def check_short_signal(self, current_rsi: float, current_price: float) -> bool:
        """Check if SHORT signal conditions are met"""
        if not self.rsi_topped or self.support_level is None:
            return False
        
        # Check if RSI just crossed below 50
        if len(self.last_rsi_values) >= 2:
            rsi_crossed_below_50 = (self.last_rsi_values[-1] < 50 and 
                                   self.last_rsi_values[-2] >= 50)
        else:
            rsi_crossed_below_50 = current_rsi < 50
        
        # Check if price broke below support
        price_broke_support = current_price < self.support_level
        
        return rsi_crossed_below_50 and price_broke_support
    
    def check_cover_signal(self, current_rsi: float) -> bool:
        """Check if COVER signal conditions are met"""
        if len(self.last_rsi_values) >= 2:
            # Just crossed into oversold
            return (current_rsi <= self.oversold_threshold and 
                   self.last_rsi_values[-2] > self.oversold_threshold)
        return current_rsi <= self.oversold_threshold
    
    def get_position_pnl_pct(self) -> float:
        """Get current position PnL as percentage"""
        position_value = self.position_data['position_value']
        if position_value == 0:
            return 0.0
        
        pnl = self.position_data['unrealized_pnl']
        return pnl / position_value
    
    def update_data(self):
        """Update all data from exchange"""
        try:
            # Get account info
            user_state = self.info.user_state(self.address)
            margin_summary = user_state.get("marginSummary", {})
            
            self.account_data['balance'] = float(margin_summary.get("accountValue", "0"))
            self.account_data['equity'] = float(margin_summary.get("accountValue", "0"))
            self.account_data['total_pnl'] = float(margin_summary.get("totalPnl", "0"))
            self.account_data['margin_used'] = float(margin_summary.get("totalMarginUsed", "0"))
            
            # Get PAXG position
            position = None
            for pos in user_state.get("assetPositions", []):
                if pos.get("position", {}).get("coin") == self.coin:
                    position = pos.get("position", {})
                    break
            
            if position:
                self.position_data['size'] = float(position.get("szi", "0"))
                self.position_data['entry_price'] = float(position.get("entryPx", "0"))
                self.position_data['unrealized_pnl'] = float(position.get("unrealizedPnl", "0"))
                
                # Get current price
                all_mids = self.info.all_mids()
                if self.coin in all_mids:
                    self.position_data['current_price'] = float(all_mids[self.coin])
                    self.position_data['position_value'] = abs(self.position_data['size']) * self.position_data['current_price']
            else:
                self.position_data = {
                    'size': 0.0,
                    'entry_price': 0.0,
                    'current_price': 0.0,
                    'unrealized_pnl': 0.0,
                    'position_value': 0.0
                }
            
            # Get RSI and update state
            df = self.get_recent_candles(limit=self.rsi_period + 50)
            if df is not None and len(df) >= self.rsi_period + 1:
                self.rsi_value = self.calculate_rsi(df['price'])
                if self.rsi_value is not None:
                    current_price = df['price'].iloc[-1]
                    self.update_rsi_state(self.rsi_value, df)
            
            self.last_update = datetime.now()
            
        except Exception as e:
            pass
    
    def draw_header(self):
        """Draw header"""
        h, w = self.stdscr.getmaxyx()
        
        # Title bar
        self.stdscr.attron(curses.color_pair(5) | curses.A_BOLD)
        self.safe_addstr(0, 0, " " * w)
        title = " PAXG RSI 1MIN DOUBLE CONFIRM BOT "
        self.safe_addstr(0, 2, title)
        
        # Connection status
        connection = "TESTNET" if self.use_testnet else "MAINNET"
        status_text = f" {connection} "
        if self.use_testnet:
            self.stdscr.attroff(curses.color_pair(5))
            self.stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
        else:
            self.stdscr.attroff(curses.color_pair(5))
            self.stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
        self.safe_addstr(0, w - len(status_text) - 1, status_text)
        
        self.stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
        self.stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
        self.stdscr.attroff(curses.color_pair(5) | curses.A_BOLD)
        
        # Tab menu
        if h > 2:
            tab_y = 2
            x_pos = 2
            for i, tab_name in enumerate(self.tab_names):
                if i == self.current_tab:
                    self.stdscr.attron(curses.A_BOLD | curses.color_pair(3))
                    self.safe_addstr(tab_y, x_pos, f"[{tab_name}]")
                    self.stdscr.attroff(curses.A_BOLD | curses.color_pair(3))
                else:
                    self.safe_addstr(tab_y, x_pos, f" {tab_name} ")
                x_pos += len(tab_name) + 4
    
    
    def load_trade_history(self):
        """Load PAXG trade history from Hyperliquid"""
        try:
            import requests
            
            # Prepare request to get user fills
            url = f"{self.api_url}/info"
            payload = {
                "type": "userFills",
                "user": self.address
            }
            
            response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
            
            if response.status_code != 200:
                self.trade_history = []
                return
            
            fills_data = response.json()
            
            # Filter for PAXG trades
            paxg_trades = []
            for fill in fills_data:
                if fill.get("coin") == "PAXG":
                    paxg_trades.append({
                        'time': fill.get('time', 0),
                        'side': fill.get('side', 'N/A'),
                        'price': float(fill.get('px', 0)),
                        'size': float(fill.get('sz', 0)),
                        'fee': float(fill.get('fee', 0)),
                        'closed_pnl': float(fill.get('closedPnl', 0))
                    })
            
            # Sort by time (most recent first) and take last 20
            paxg_trades.sort(key=lambda x: x['time'], reverse=True)
            self.trade_history = paxg_trades[:20]
            
        except Exception as e:
            self.trade_history = []
    
    def draw_history_tab(self, start_y):
        """Draw history tab with trade history"""
        h, w = self.stdscr.getmaxyx()
        y = start_y
        
        if y >= h - 2:
            return y
        
        # Section title
        self.stdscr.attron(curses.A_BOLD | curses.color_pair(3))
        self.safe_addstr(y, 2, "PAXG TRADE HISTORY (Last 20 Trades)")
        self.stdscr.attroff(curses.A_BOLD | curses.color_pair(3))
        y += 2
        
        if self.trade_history:
            # Header
            self.stdscr.attron(curses.A_BOLD)
            self.safe_addstr(y, 2, "Time                 Side    Price         Size          Fee      PnL")
            self.stdscr.attroff(curses.A_BOLD)
            y += 1
            
            # Trades
            for trade in self.trade_history:
                if y >= h - 4:
                    break
                
                # Format time
                time_val = trade['time']
                if isinstance(time_val, int):
                    time_str = datetime.fromtimestamp(time_val / 1000).strftime("%Y-%m-%d %H:%M:%S")
                else:
                    time_str = str(time_val)[:19]
                
                side = trade['side']
                price = trade['price']
                size = trade['size']
                fee = trade['fee']
                pnl = trade['closed_pnl']
                
                # Color code by side
                side_color = curses.color_pair(1) if side == 'B' else curses.color_pair(2)
                side_text = "BUY " if side == 'B' else "SELL"
                
                self.safe_addstr(y, 2, f"{time_str}  ")
                self.stdscr.attron(side_color)
                self.safe_addstr(y, 23, side_text)
                self.stdscr.attroff(side_color)
                self.safe_addstr(y, 28, f"  ${price:>10.2f}  {size:>10.6f}  ${fee:>7.4f}  ${pnl:>7.2f}")
                y += 1
        else:
            self.stdscr.attron(curses.color_pair(4))
            self.safe_addstr(y, 2, "No trade history available. Press R to load.")
            self.stdscr.attroff(curses.color_pair(4))
            y += 2
        
        return y
    
    def draw_backtest_tab(self, start_y):
        """Draw backtest tab"""
        h, w = self.stdscr.getmaxyx()
        y = start_y
        
        if y >= h - 2:
            return y
        
        # Section title
        self.stdscr.attron(curses.A_BOLD | curses.color_pair(3))
        self.safe_addstr(y, 2, "STRATEGY BACKTESTING - RSI 1MIN DOUBLE CONFIRM")
        self.stdscr.attroff(curses.A_BOLD | curses.color_pair(3))
        y += 2
        
        # Controls
        if y < h - 1:
            self.stdscr.attron(curses.color_pair(4))
            if not self.backtest_running:
                self.safe_addstr(y, 4, "Press B to run backtest with current settings | Press C to run with custom parameters")
            else:
                self.safe_addstr(y, 4, "Backtest running... Please wait")
            self.stdscr.attroff(curses.color_pair(4))
        y += 2
        
        # Current settings
        self.stdscr.attron(curses.A_BOLD | curses.color_pair(3))
        self.safe_addstr(y, 2, "CURRENT SETTINGS")
        self.stdscr.attroff(curses.A_BOLD | curses.color_pair(3))
        y += 1
        
        if y < h - 1:
            self.safe_addstr(y, 4, f"RSI Period:       {self.rsi_period}")
        y += 1
        
        if y < h - 1:
            self.safe_addstr(y, 4, f"Oversold:         {self.oversold_threshold}")
        y += 1
        
        if y < h - 1:
            self.safe_addstr(y, 4, f"Overbought:       {self.overbought_threshold}")
        y += 1
        
        if y < h - 1:
            self.safe_addstr(y, 4, f"Take Profit:      {self.take_profit_pct*100:.1f}%")
        y += 1
        
        if y < h - 1:
            self.safe_addstr(y, 4, f"Stop Loss:        {abs(self.stop_loss_pct)*100:.1f}%")
        y += 2
        
        # Backtest status
        if y < h - 1:
            self.safe_addstr(y, 4, f"Status: {self.backtester.status}")
        y += 1
        
        if self.backtester.progress > 0 and y < h - 1:
            progress_bar_width = 40
            filled = int(progress_bar_width * self.backtester.progress / 100)
            bar = "█" * filled + "░" * (progress_bar_width - filled)
            self.safe_addstr(y, 4, f"Progress: [{bar}] {self.backtester.progress}%")
        y += 2
        
        # Results
        if self.backtest_results and self.backtest_results.get('success'):
            metrics = self.backtest_results['metrics']
            
            self.stdscr.attron(curses.A_BOLD | curses.color_pair(3))
            self.safe_addstr(y, 2, "BACKTEST RESULTS")
            self.stdscr.attroff(curses.A_BOLD | curses.color_pair(3))
            y += 1
            
            if y < h - 1:
                self.safe_addstr(y, 4, f"Date Range:       {self.backtest_results['date_range']}")
            y += 1
            
            if y < h - 1:
                self.safe_addstr(y, 4, f"Data Points:      {self.backtest_results['data_points']:,}")
            y += 1
            
            if y < h - 1:
                self.safe_addstr(y, 4, f"Total Trades:     {metrics['total_trades']}")
            y += 1
            
            if y < h - 1:
                win_rate = metrics['win_rate']
                win_color = curses.color_pair(1) if win_rate >= 50 else curses.color_pair(2)
                self.safe_addstr(y, 4, "Win Rate:         ")
                self.stdscr.attron(curses.A_BOLD | win_color)
                self.safe_addstr(y, 22, f"{win_rate:.2f}%")
                self.stdscr.attroff(curses.A_BOLD | win_color)
            y += 1
            
            if y < h - 1:
                total_profit = metrics['total_profit']
                profit_color = curses.color_pair(1) if total_profit >= 0 else curses.color_pair(2)
                self.safe_addstr(y, 4, "Total Profit:     ")
                self.stdscr.attron(curses.A_BOLD | profit_color)
                self.safe_addstr(y, 22, f"{total_profit:.2f}%")
                self.stdscr.attroff(curses.A_BOLD | profit_color)
            y += 1
            
            if y < h - 1:
                self.safe_addstr(y, 4, f"Profit Factor:    {metrics['profit_factor']:.2f}")
            y += 1
            
            if y < h - 1:
                self.safe_addstr(y, 4, f"Max Drawdown:     {metrics['max_drawdown']:.2f}%")
            y += 1
            
            if y < h - 1:
                avg_profit = metrics['avg_profit']
                avg_color = curses.color_pair(1) if avg_profit >= 0 else curses.color_pair(2)
                self.safe_addstr(y, 4, "Avg Profit/Trade: ")
                self.stdscr.attron(avg_color)
                self.safe_addstr(y, 22, f"{avg_profit:.2f}%")
                self.stdscr.attroff(avg_color)
            y += 2
            
            # Recent trades
            trades = self.backtester.get_trade_summary(max_trades=5)
            if trades and y < h - 5:
                self.stdscr.attron(curses.A_BOLD | curses.color_pair(3))
                self.safe_addstr(y, 2, "RECENT TRADES (Last 5)")
                self.stdscr.attroff(curses.A_BOLD | curses.color_pair(3))
                y += 1
                
                # Header
                self.stdscr.attron(curses.A_BOLD)
                self.safe_addstr(y, 4, "Entry Time       Exit Time        Side   Entry     Exit      Profit   Reason")
                self.stdscr.attroff(curses.A_BOLD)
                y += 1
                
                for trade in trades:
                    if y >= h - 4:
                        break
                    
                    side_color = curses.color_pair(2)  # SHORT is red
                    profit_color = curses.color_pair(1) if trade['profit_pct'] >= 0 else curses.color_pair(2)
                    
                    self.safe_addstr(y, 4, f"{trade['entry_time']}  {trade['exit_time']}  ")
                    self.stdscr.attron(side_color)
                    self.safe_addstr(y, 43, f"{trade['side']:5s}")
                    self.stdscr.attroff(side_color)
                    self.safe_addstr(y, 49, f"  ${trade['entry_price']:7.2f}  ${trade['exit_price']:7.2f}  ")
                    self.stdscr.attron(profit_color)
                    self.safe_addstr(y, 73, f"{trade['profit_pct']:6.2f}%")
                    self.stdscr.attroff(profit_color)
                    self.safe_addstr(y, 81, f"  {trade['exit_reason'][:10]}")
                    y += 1
        
        elif self.backtest_results and not self.backtest_results.get('success'):
            if y < h - 1:
                self.stdscr.attron(curses.color_pair(2))
                self.safe_addstr(y, 4, f"Error: {self.backtest_results.get('error', 'Unknown error')}")
                self.stdscr.attroff(curses.color_pair(2))
        
        return y
    
    def add_log(self, message: str):
        """Add log message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.bot_logs.append(f"[{timestamp}] {message}")
        if len(self.bot_logs) > self.max_logs:
            self.bot_logs.pop(0)
    
    def execute_trading_cycle(self):
        """Execute one trading cycle with RSI 1MIN Double Confirm algorithm"""
        try:
            # Get current RSI and price
            if self.rsi_value is None:
                return
            
            df = self.get_recent_candles(limit=self.rsi_period + 50)
            if df is None:
                return
            
            current_price = df['price'].iloc[-1]
            
            # Get current position info
            position_value = self.position_data['position_value']
            position_pnl = self.position_data['unrealized_pnl']
            position_pnl_pct = self.get_position_pnl_pct()
            has_position = abs(self.position_data['size']) > 0
            
            if has_position:
                # PRIORITY 1: Check risk management (take profit / stop loss)
                if position_pnl_pct >= self.take_profit_pct:
                    self.add_log(f"🎯 TAKE PROFIT (PnL: {position_pnl_pct*100:.2f}%)")
                    result = self.close_position()
                    if result.get('status') == 'ok':
                        self.add_log(f"✅ Position closed at {position_pnl_pct*100:.2f}% profit")
                    else:
                        self.add_log(f"❌ Close failed: {result.get('error')}")
                
                elif position_pnl_pct <= self.stop_loss_pct:
                    self.add_log(f"🛑 STOP LOSS (PnL: {position_pnl_pct*100:.2f}%)")
                    result = self.close_position()
                    if result.get('status') == 'ok':
                        self.add_log(f"✅ Position closed at {position_pnl_pct*100:.2f}% loss")
                    else:
                        self.add_log(f"❌ Close failed: {result.get('error')}")
                
                # PRIORITY 2: Check for COVER signal (RSI oversold)
                elif self.check_cover_signal(self.rsi_value):
                    self.add_log(f"🟢 COVER SIGNAL (RSI: {self.rsi_value:.1f})")
                    result = self.close_position()
                    if result.get('status') == 'ok':
                        self.add_log(f"✅ Short covered at RSI {self.rsi_value:.1f}")
                    else:
                        self.add_log(f"❌ Cover failed: {result.get('error')}")
            
            else:
                # No position - check for SHORT signal
                if self.check_short_signal(self.rsi_value, current_price):
                    if self.is_in_cooldown():
                        self.add_log(f"⏳ Short signal but in cooldown (RSI: {self.rsi_value:.1f})")
                    elif self.can_open_new_position():
                        self.add_log(f"🔴 SHORT SIGNAL (RSI: {self.rsi_value:.1f}, Price: ${current_price:.2f})")
                        result = self.create_short_market_order()
                        if result.get('status') == 'ok':
                            self.add_log(f"✅ Short order created successfully")
                        else:
                            self.add_log(f"❌ Order failed: {result.get('error')}")
                    else:
                        self.add_log(f"⚠️ Position limit reached")
                    
        except Exception as e:
            self.add_log(f"❌ Error in trading cycle: {e}")
    
    def is_in_cooldown(self) -> bool:
        """Check if in cooldown"""
        if self.last_buy_time is None:
            return False
        time_since = datetime.now() - self.last_buy_time
        cooldown = timedelta(minutes=self.buy_cooldown_minutes) - time_since
        return cooldown.total_seconds() > 0
    
    def can_open_new_position(self) -> bool:
        """Check if can open new position"""
        current_value = self.position_data['position_value']
        return current_value + self.position_value_usd <= self.max_total_position_usd
    
    def create_short_market_order(self) -> Dict:
        """Create short market order"""
        try:
            all_mids = self.info.all_mids()
            if self.coin not in all_mids:
                return {"status": "error", "error": "No market price"}
            
            meta = self.info.meta()
            sz_decimals = {}
            for asset_info in meta["universe"]:
                sz_decimals[asset_info["name"]] = asset_info["szDecimals"]
            
            if self.coin not in sz_decimals:
                return {"status": "error", "error": "No szDecimals"}
            
            current_price = float(all_mids[self.coin])
            raw_size = self.position_value_usd / current_price
            size = round(raw_size, sz_decimals[self.coin])
            
            # SHORT = sell (is_buy = False)
            order_result = self.exchange.market_open(self.coin, False, size, None, 0.01)
            
            if order_result.get("status") == "ok":
                self.last_buy_time = datetime.now()
                return {"status": "ok", "result": order_result}
            else:
                return {"status": "error", "error": str(order_result)}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def close_position(self) -> Dict:
        """Close position"""
        try:
            position = None
            user_state = self.info.user_state(self.address)
            for pos in user_state.get("assetPositions", []):
                if pos.get("position", {}).get("coin") == self.coin:
                    position = pos.get("position", {})
                    break
            
            if not position:
                return {"status": "error", "error": "No position"}
            
            size = float(position.get("szi", "0"))
            if abs(size) == 0:
                return {"status": "error", "error": "Zero size"}
            
            meta = self.info.meta()
            sz_decimals = {}
            for asset_info in meta["universe"]:
                sz_decimals[asset_info["name"]] = asset_info["szDecimals"]
            
            close_size = round(abs(size), sz_decimals[self.coin])
            order_result = self.exchange.market_close(self.coin, close_size, None, 0.01)
            
            if order_result.get("status") == "ok":
                # Reset RSI state after closing
                self.rsi_topped = False
                return {"status": "ok", "result": order_result}
            else:
                return {"status": "error", "error": str(order_result)}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def draw_bot_tab(self, start_y):
        """Draw bot tab with trading status"""
        h, w = self.stdscr.getmaxyx()
        y = start_y
        
        if y >= h - 2:
            return y
        
        # Bot Status Section
        self.stdscr.attron(curses.A_BOLD | curses.color_pair(3))
        bot_status = "RUNNING" if self.bot_running else "STOPPED"
        status_color = curses.color_pair(1) if self.bot_running else curses.color_pair(2)
        self.safe_addstr(y, 2, "BOT STATUS: ")
        self.stdscr.attron(status_color)
        self.safe_addstr(y, 14, bot_status)
        self.stdscr.attroff(status_color)
        self.stdscr.attroff(curses.A_BOLD | curses.color_pair(3))
        y += 1
        
        # Controls
        if y < h - 1:
            self.stdscr.attron(curses.color_pair(4))
            self.safe_addstr(y, 4, "Press S to START bot | Press X to STOP bot")
            self.stdscr.attroff(curses.color_pair(4))
        y += 2
        
        # Bot configuration
        if y < h - 1:
            self.safe_addstr(y, 4, f"Strategy:    RSI 1MIN Double Confirm (SHORT-based)")
        y += 1
        
        if y < h - 1:
            self.safe_addstr(y, 4, f"Coin:        {self.coin}")
        y += 1
        
        if y < h - 1:
            self.safe_addstr(y, 4, f"RSI Period:  {self.rsi_period}")
        y += 1
        
        if y < h - 1:
            self.safe_addstr(y, 4, f"SHORT Signal: RSI tops, dips <50, price breaks support")
        y += 1
        
        if y < h - 1:
            self.safe_addstr(y, 4, f"COVER Signal: RSI < {self.oversold_threshold}")
        y += 1
        
        if y < h - 1:
            self.safe_addstr(y, 4, f"Take Profit: {self.take_profit_pct*100:.1f}%  |  Stop Loss: {abs(self.stop_loss_pct)*100:.1f}%")
        y += 2
        
        # Bot Logs Section
        self.stdscr.attron(curses.A_BOLD | curses.color_pair(3))
        self.safe_addstr(y, 2, "BOT ACTIVITY LOG")
        self.stdscr.attroff(curses.A_BOLD | curses.color_pair(3))
        y += 1
        
        if self.bot_logs:
            max_lines = h - y - 10
            start_idx = max(0, len(self.bot_logs) - max_lines)
            for log in self.bot_logs[start_idx:]:
                if y >= h - 10:
                    break
                self.safe_addstr(y, 4, log)
                y += 1
        else:
            if y < h - 1:
                self.stdscr.attron(curses.color_pair(4))
                self.safe_addstr(y, 4, "No activity yet. Start the bot to begin trading.")
                self.stdscr.attroff(curses.color_pair(4))
        y += 2
        
        # Current Signal Section
        self.stdscr.attron(curses.A_BOLD | curses.color_pair(3))
        self.safe_addstr(y, 2, "CURRENT SIGNAL")
        self.stdscr.attroff(curses.A_BOLD | curses.color_pair(3))
        y += 1
        
        if self.rsi_value is not None:
            df = self.get_recent_candles(limit=self.rsi_period + 50)
            if df is not None:
                current_price = df['price'].iloc[-1]
                
                # Determine current signal
                if self.check_short_signal(self.rsi_value, current_price):
                    signal = "SHORT SIGNAL"
                    signal_color = curses.color_pair(2)
                    action = "SHORT condition met (RSI topped, <50, support broken)"
                elif self.check_cover_signal(self.rsi_value):
                    signal = "COVER SIGNAL"
                    signal_color = curses.color_pair(1)
                    action = "COVER condition met (RSI oversold)"
                else:
                    signal = "NO SIGNAL"
                    signal_color = curses.color_pair(4)
                    topped_status = "topped" if self.rsi_topped else "not topped"
                    action = f"No trading signal (RSI {topped_status})"
                
                if y < h - 1:
                    self.safe_addstr(y, 4, f"RSI Value:   ")
                    self.stdscr.attron(curses.A_BOLD | signal_color)
                    self.safe_addstr(y, 17, f"{self.rsi_value:.2f}")
                    self.stdscr.attroff(curses.A_BOLD | signal_color)
                y += 1
                
                if y < h - 1:
                    self.safe_addstr(y, 4, "Signal:      ")
                    self.stdscr.attron(curses.A_BOLD | signal_color)
                    self.safe_addstr(y, 17, signal)
                    self.stdscr.attroff(curses.A_BOLD | signal_color)
                y += 1
                
                if y < h - 1:
                    self.safe_addstr(y, 4, f"Action:      {action}")
                y += 1
                
                if y < h - 1 and self.support_level:
                    self.safe_addstr(y, 4, f"Support:     ${self.support_level:.2f}")
                y += 2
        else:
            if y < h - 1:
                self.stdscr.attron(curses.color_pair(4))
                self.safe_addstr(y, 4, "Waiting for RSI data...")
                self.stdscr.attroff(curses.color_pair(4))
            y += 2
        
        # Settings from settings.py
        self.stdscr.attron(curses.A_BOLD | curses.color_pair(3))
        self.safe_addstr(y, 2, "BOT SETTINGS")
        self.stdscr.attroff(curses.A_BOLD | curses.color_pair(3))
        y += 1
        
        if y < h - 1:
            self.safe_addstr(y, 4, f"Position Size:     ${settings.BOT_POSITION_VALUE_USD:,.2f}")
        y += 1
        
        if y < h - 1:
            self.safe_addstr(y, 4, f"Max Position:      ${settings.BOT_MAX_TOTAL_POSITION_USD:,.2f}")
        y += 1
        
        if y < h - 1:
            self.safe_addstr(y, 4, f"Buy Cooldown:      {settings.BOT_BUY_COOLDOWN_MINUTES} minutes")
        y += 2
        
        return y
    
    def draw_account_section(self, start_y):
        """Draw account information section"""
        h, w = self.stdscr.getmaxyx()
        y = start_y
        
        if y >= h - 2:
            return y
        
        # Section title
        self.stdscr.attron(curses.A_BOLD | curses.color_pair(3))
        self.safe_addstr(y, 2, "ACCOUNT")
        self.stdscr.attroff(curses.A_BOLD | curses.color_pair(3))
        y += 1
        
        # Balance
        if y < h - 1:
            self.safe_addstr(y, 4, f"Balance:     ${self.account_data['balance']:>12,.2f}")
        y += 1
        
        # Equity
        if y < h - 1:
            self.safe_addstr(y, 4, f"Equity:      ${self.account_data['equity']:>12,.2f}")
        y += 1
        
        # Total PnL
        if y < h - 1:
            pnl = self.account_data['total_pnl']
            pnl_color = curses.color_pair(1) if pnl >= 0 else curses.color_pair(2)
            self.safe_addstr(y, 4, "Total P&L:   ")
            self.stdscr.attron(curses.A_BOLD | pnl_color)
            self.safe_addstr(y, 17, f"${pnl:>12,.2f}")
            self.stdscr.attroff(curses.A_BOLD | pnl_color)
        y += 1
        
        # Margin
        if y < h - 1:
            self.safe_addstr(y, 4, f"Margin Used: ${self.account_data['margin_used']:>12,.2f}")
        y += 2
        
        return y
    
    def draw_position_section(self, start_y):
        """Draw position information section"""
        h, w = self.stdscr.getmaxyx()
        y = start_y
        
        if y >= h - 2:
            return y
        
        # Section title
        self.stdscr.attron(curses.A_BOLD | curses.color_pair(3))
        self.safe_addstr(y, 2, "PAXG POSITION")
        self.stdscr.attroff(curses.A_BOLD | curses.color_pair(3))
        y += 1
        
        if abs(self.position_data['size']) > 0:
            # Side and Size
            if y < h - 1:
                size = self.position_data['size']
                side = "LONG" if size > 0 else "SHORT"
                side_color = curses.color_pair(1) if size > 0 else curses.color_pair(2)
                
                self.safe_addstr(y, 4, "Side:        ")
                self.stdscr.attron(curses.A_BOLD | side_color)
                self.safe_addstr(y, 17, f"{side:>6}")
                self.stdscr.attroff(curses.A_BOLD | side_color)
                self.safe_addstr(y, 25, f"   Size: {abs(size):.6f}")
            y += 1
            
            # Entry Price
            if y < h - 1:
                self.safe_addstr(y, 4, f"Entry Price: ${self.position_data['entry_price']:>12.2f}")
            y += 1
            
            # Current Price
            if y < h - 1:
                self.safe_addstr(y, 4, f"Current:     ${self.position_data['current_price']:>12.2f}")
            y += 1
            
            # Unrealized PnL
            if y < h - 1:
                pnl = self.position_data['unrealized_pnl']
                pnl_pct = self.get_position_pnl_pct()
                pnl_color = curses.color_pair(1) if pnl >= 0 else curses.color_pair(2)
                
                self.safe_addstr(y, 4, "P&L:         ")
                self.stdscr.attron(curses.A_BOLD | pnl_color)
                self.safe_addstr(y, 17, f"${pnl:>12,.2f} ({pnl_pct*100:>6.2f}%)")
                self.stdscr.attroff(curses.A_BOLD | pnl_color)
            y += 1
            
            # Position Value
            if y < h - 1:
                self.safe_addstr(y, 4, f"Value:       ${self.position_data['position_value']:>12,.2f}")
            y += 2
        else:
            # No position
            if y < h - 1:
                self.stdscr.attron(curses.color_pair(4))
                self.safe_addstr(y, 4, "No active position")
                self.stdscr.attroff(curses.color_pair(4))
            y += 3
        
        return y
    
    def draw_rsi_section(self, start_y):
        """Draw RSI information section"""
        h, w = self.stdscr.getmaxyx()
        y = start_y
        
        if y >= h - 2:
            return y
        
        # Section title
        self.stdscr.attron(curses.A_BOLD | curses.color_pair(3))
        self.safe_addstr(y, 2, "RSI INDICATOR (1MIN DOUBLE CONFIRM)")
        self.stdscr.attroff(curses.A_BOLD | curses.color_pair(3))
        y += 1
        
        if self.rsi_value is not None:
            # Current RSI with large display
            if y < h - 1:
                rsi_str = f"{self.rsi_value:.1f}"
                
                # Determine signal and color
                if self.rsi_value < self.oversold_threshold:
                    rsi_color = curses.color_pair(6)  # Green background
                    signal = "OVERSOLD - COVER SIGNAL"
                    signal_color = curses.color_pair(1)
                elif self.rsi_value > self.overbought_threshold:
                    rsi_color = curses.color_pair(7)  # Red background
                    signal = "OVERBOUGHT - POTENTIAL SHORT SETUP"
                    signal_color = curses.color_pair(2)
                else:
                    rsi_color = curses.color_pair(4)
                    signal = "NEUTRAL"
                    signal_color = curses.color_pair(4)
                
                self.safe_addstr(y, 4, "Current RSI: ")
                self.stdscr.attron(curses.A_BOLD | rsi_color)
                self.safe_addstr(y, 17, f" {rsi_str:>6} ")
                self.stdscr.attroff(curses.A_BOLD | rsi_color)
            y += 1
            
            # Signal
            if y < h - 1:
                self.safe_addstr(y, 4, "Signal:      ")
                self.stdscr.attron(curses.A_BOLD | signal_color)
                self.safe_addstr(y, 17, signal)
                self.stdscr.attroff(curses.A_BOLD | signal_color)
            y += 1
            
            # RSI State
            if y < h - 1:
                topped_status = "TOPPED" if self.rsi_topped else "NOT TOPPED"
                topped_color = curses.color_pair(2) if self.rsi_topped else curses.color_pair(4)
                self.safe_addstr(y, 4, "RSI State:   ")
                self.stdscr.attron(topped_color)
                self.safe_addstr(y, 17, topped_status)
                self.stdscr.attroff(topped_color)
            y += 1
            
            # Support Level
            if y < h - 1 and self.support_level:
                self.safe_addstr(y, 4, f"Support:     ${self.support_level:.2f}")
            y += 1
            
            # Thresholds
            if y < h - 1:
                self.safe_addstr(y, 4, f"Thresholds:  Cover < {self.oversold_threshold}  /  Overbought > {self.overbought_threshold}")
            y += 2
        else:
            if y < h - 1:
                self.stdscr.attron(curses.color_pair(4))
                self.safe_addstr(y, 4, "RSI data not available")
                self.stdscr.attroff(curses.color_pair(4))
            y += 3
        
        return y
    
    def draw_footer(self):
        """Draw footer"""
        h, w = self.stdscr.getmaxyx()
        
        # Separator line
        if h > 3:
            self.safe_addstr(h - 3, 0, "=" * (w - 1))
        
        # Last update time
        if self.last_update and h > 2:
            timestamp = self.last_update.strftime("%Y-%m-%d %H:%M:%S")
            self.stdscr.attron(curses.color_pair(4))
            self.safe_addstr(h - 2, 2, f"Last Update: {timestamp}")
            self.stdscr.attroff(curses.color_pair(4))
        
        # Controls
        if h > 1:
            self.stdscr.attron(curses.A_BOLD)
            if self.current_tab == 1:  # Bot tab
                self.safe_addstr(h - 1, 2, "S: Start Bot  |  X: Stop Bot  |  TAB/←→: Switch  |  Q: Quit")
            else:
                self.safe_addstr(h - 1, 2, "TAB/←→: Switch View  |  R: Refresh  |  Q: Quit")
            self.stdscr.attroff(curses.A_BOLD)
    
    def run(self):
        """Run the panel"""
        self.stdscr.clear()
        curses.curs_set(0)
        self.stdscr.nodelay(1)
        self.stdscr.timeout(100)
        
        # Initial data load
        self.update_data()
        
        last_auto_update = time.time()
        auto_update_interval = 5  # Update every 5 seconds
        
        while True:
            h, w = self.stdscr.getmaxyx()
            
            # Check minimum terminal size
            if h < 20 or w < 60:
                self.stdscr.clear()
                msg = "Terminal too small!"
                msg2 = f"Need at least 60x20, current: {w}x{h}"
                if h > 2 and w > len(msg):
                    self.safe_addstr(h//2, (w - len(msg))//2, msg)
                if h > 3 and w > len(msg2):
                    self.safe_addstr(h//2 + 1, (w - len(msg2))//2, msg2)
                self.stdscr.refresh()
                time.sleep(0.5)
                
                key = self.stdscr.getch()
                if key == ord('q') or key == ord('Q'):
                    break
                continue
            
            # Auto-update data every 5 seconds
            current_time = time.time()
            if current_time - last_auto_update >= auto_update_interval:
                self.update_data()
                # Execute trading cycle if bot is running
                if self.bot_running:
                    self.execute_trading_cycle()
                last_auto_update = current_time
            
            self.stdscr.clear()
            
            # Draw header (always visible)
            self.draw_header()
            
            # Draw content based on current tab
            if self.current_tab == 0:  # Main panel
                y = self.draw_account_section(4)
                y = self.draw_position_section(y)
                y = self.draw_rsi_section(y)
            elif self.current_tab == 1:  # Bot tab
                y = self.draw_bot_tab(4)
            elif self.current_tab == 2:  # History tab
                y = self.draw_history_tab(4)
            elif self.current_tab == 3:  # Backtest tab
                y = self.draw_backtest_tab(4)
            
            # Draw footer (always visible)
            self.draw_footer()
            
            self.stdscr.refresh()
            
            # Handle input
            key = self.stdscr.getch()
            
            if key == ord('q') or key == ord('Q'):
                break
            elif key == ord('r') or key == ord('R'):
                # Manual refresh
                self.update_data()
                if self.current_tab == 2:  # Reload history if on history tab
                    self.load_trade_history()
                last_auto_update = current_time
            elif key == ord('\t') or key == 9:  # Tab key
                self.current_tab = (self.current_tab + 1) % len(self.tab_names)
            elif key == curses.KEY_RIGHT:  # Right arrow - next tab
                self.current_tab = (self.current_tab + 1) % len(self.tab_names)
                if self.current_tab == 2:  # Load history when switching to history tab
                    self.load_trade_history()
            elif key == curses.KEY_LEFT:  # Left arrow - previous tab
                self.current_tab = (self.current_tab - 1) % len(self.tab_names)
                if self.current_tab == 2:  # Load history when switching to history tab
                    self.load_trade_history()
            elif key == ord('s') or key == ord('S'):  # Start bot
                if not self.bot_running:
                    self.bot_running = True
                    self.add_log("🤖 Bot STARTED - Auto-trading enabled")
            elif key == ord('x') or key == ord('X'):  # Stop bot
                if self.bot_running:
                    self.bot_running = False
                    self.add_log("🛑 Bot STOPPED - Auto-trading disabled")
            elif key == ord('b') or key == ord('B'):  # Run backtest
                if self.current_tab == 3 and not self.backtest_running:
                    self.backtest_running = True
                    # Run backtest in background (simplified - runs synchronously)
                    self.backtest_results = self.backtester.run_backtest(
                        period=self.rsi_period,
                        oversold=self.oversold_threshold,
                        overbought=self.overbought_threshold,
                        take_profit=self.take_profit_pct,
                        stop_loss=self.stop_loss_pct,
                        days=1  # Test with 1 day of data (max 1000 candles from Binance)
                    )
                    self.backtest_running = False


def main(stdscr):
    """Main function"""
    try:
        panel = PAXGPanel(stdscr)
        panel.run()
    except Exception as e:
        stdscr.clear()
        stdscr.addstr(0, 0, f"Error: {str(e)}")
        stdscr.addstr(1, 0, "Press any key to exit...")
        stdscr.refresh()
        stdscr.nodelay(0)
        stdscr.getch()


if __name__ == "__main__":
    curses.wrapper(main)
