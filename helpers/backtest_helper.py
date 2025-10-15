"""
Backtest helper module for the PAXG panel
Simplified backtesting functionality for RSI 1MIN Double Confirm strategy
"""

import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import sys
import os

# Add parent directory to path to import algos
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from algos import RSI1MinDoubleConfirmAlgorithm, BacktestEngine


class PanelBacktester:
    """Simplified backtester for the panel interface"""
    
    def __init__(self):
        self.results = None
        self.trades_df = None
        self.status = "Ready"
        self.progress = 0
        
    def fetch_binance_data(self, symbol: str = "PAXGUSDT", days: int = 7) -> Optional[pd.DataFrame]:
        """Fetch historical data from Binance"""
        try:
            self.status = "Fetching data..."
            self.progress = 10
            
            url = "https://api.binance.com/api/v3/klines"
            
            # Calculate how many 1-minute candles we need
            limit = min(days * 24 * 60, 1000)  # Binance limit is 1000
            
            params = {
                "symbol": symbol,
                "interval": "1m",
                "limit": limit
            }
            
            response = requests.get(url, params=params, timeout=30)
            if response.status_code != 200:
                self.status = f"Error: HTTP {response.status_code}"
                return None
            
            data = response.json()
            if not data:
                self.status = "Error: No data received"
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['price'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float)
            df['low'] = df['low'].astype(float)
            df['high'] = df['high'].astype(float)
            
            df = df[['timestamp', 'price', 'volume', 'low', 'high']]
            df.set_index('timestamp', inplace=True)
            
            self.status = f"Loaded {len(df)} candles"
            self.progress = 30
            
            return df
            
        except Exception as e:
            self.status = f"Error: {str(e)}"
            return None
    
    def run_backtest(self, 
                     period: int = 10,
                     oversold: int = 20,
                     overbought: int = 65,
                     take_profit: float = 0.015,
                     stop_loss: float = -0.007,
                     days: int = 7) -> Dict:
        """
        Run backtest with specified parameters
        
        Args:
            period: RSI period
            oversold: Oversold threshold
            overbought: Overbought threshold
            take_profit: Take profit percentage (e.g., 0.015 = 1.5%)
            stop_loss: Stop loss percentage (e.g., -0.007 = -0.7%)
            days: Number of days of historical data to test
        
        Returns:
            Dictionary with backtest results
        """
        try:
            self.status = "Starting backtest..."
            self.progress = 0
            
            # Fetch data
            df = self.fetch_binance_data(days=days)
            if df is None:
                return {
                    'success': False,
                    'error': self.status
                }
            
            self.status = "Running backtest..."
            self.progress = 40
            
            # Create algorithm instance
            algorithm = RSI1MinDoubleConfirmAlgorithm(
                period=period,
                oversold_threshold=oversold,
                overbought_threshold=overbought
            )
            
            # Create backtest engine
            engine = BacktestEngine(
                algorithm=algorithm,
                take_profit=take_profit,
                stop_loss=stop_loss,
                commission=0.0005  # 0.05% commission
            )
            
            self.progress = 60
            
            # Run backtest
            trades_df, metrics = engine.backtest(df)
            
            self.progress = 90
            
            # Store results
            self.results = metrics
            self.trades_df = trades_df
            
            self.status = "Backtest complete!"
            self.progress = 100
            
            return {
                'success': True,
                'metrics': metrics,
                'trades': trades_df,
                'data_points': len(df),
                'date_range': f"{df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}"
            }
            
        except Exception as e:
            self.status = f"Error: {str(e)}"
            self.progress = 0
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_trade_summary(self, max_trades: int = 10) -> list:
        """Get summary of recent trades"""
        if self.trades_df is None or len(self.trades_df) == 0:
            return []
        
        trades = []
        for idx, trade in self.trades_df.tail(max_trades).iterrows():
            trades.append({
                'entry_time': trade['entry_time'].strftime('%Y-%m-%d %H:%M'),
                'exit_time': trade['exit_time'].strftime('%Y-%m-%d %H:%M'),
                'side': trade['type'].upper(),  # 'long' or 'short' -> 'LONG' or 'SHORT'
                'entry_price': trade['entry_price'],
                'exit_price': trade['exit_price'],
                'profit_pct': trade['profit_pct'],
                'exit_reason': trade['exit_reason']
            })
        
        return trades
