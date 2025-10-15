"""
Base algorithm interface for the backtesting system
"""

from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
from typing import Dict, Tuple, List, Optional


class BaseAlgorithm(ABC):
    """Base class for all trading algorithms"""
    
    def __init__(self, name: str, **params):
        self.name = name
        self.params = params
    
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        Generate trading signals from price data
        
        Args:
            data: DataFrame with 'price' and 'volume' columns
            
        Returns:
            Series with trading signals: 1 for buy, -1 for sell, 0 for hold
        """
        pass
    
    @abstractmethod
    def get_parameter_ranges(self) -> Dict:
        """
        Get parameter ranges for optimization
        
        Returns:
            Dictionary with parameter names as keys and lists of values as ranges
        """
        pass
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate technical indicators (to be overridden by specific algorithms)
        
        Args:
            data: DataFrame with price data
            
        Returns:
            DataFrame with additional indicator columns
        """
        return data.copy()


class BacktestEngine:
    """Engine for running backtests with any algorithm"""
    
    def __init__(self, algorithm: BaseAlgorithm, take_profit: float = 0.01, 
                 stop_loss: float = -0.005, commission: float = 0.001):
        self.algorithm = algorithm
        self.take_profit = take_profit
        self.stop_loss = stop_loss
        self.commission = commission
    
    def calculate_exit_price(self, entry_price: float, is_long: bool) -> Tuple[float, float]:
        """Calculate take profit and stop loss prices"""
        if is_long:
            tp_price = entry_price * (1 + self.take_profit)
            sl_price = entry_price * (1 + self.stop_loss)
        else:
            tp_price = entry_price * (1 - self.take_profit)
            sl_price = entry_price * (1 - self.stop_loss)
        return tp_price, sl_price
    
    def simulate_trade(self, prices: pd.Series, entry_idx: int, is_long: bool) -> Tuple[int, float, str]:
        """Simulate a trade and return (exit_index, profit_pct, exit_reason)"""
        entry_price = prices.iloc[entry_idx]
        tp_price, sl_price = self.calculate_exit_price(entry_price, is_long)
        
        for i in range(entry_idx + 1, len(prices)):
            current_price = prices.iloc[i]
            
            if is_long:
                if current_price >= tp_price:
                    profit = self.take_profit - self.commission * 2  # Entry + exit commission
                    return i, profit, "take_profit"
                elif current_price <= sl_price:
                    profit = self.stop_loss - self.commission * 2
                    return i, profit, "stop_loss"
            else:
                if current_price <= tp_price:
                    profit = self.take_profit - self.commission * 2
                    return i, profit, "take_profit"
                elif current_price >= sl_price:
                    profit = -self.stop_loss - self.commission * 2
                    return i, profit, "stop_loss"
        
        # If no exit triggered, close at last price
        final_profit = (prices.iloc[-1] - entry_price) / entry_price
        if not is_long:
            final_profit = -final_profit
        final_profit -= self.commission * 2  # Account for commissions
        return len(prices) - 1, final_profit, "market_close"
    
    def backtest(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """Run backtest and return trades DataFrame and performance metrics"""
        signals = self.algorithm.generate_signals(data)
        trades_list = []
        current_trade = None
        i = 1
        
        while i < len(data):
            price = data['price'].iloc[i]
            signal = signals.iloc[i]
            
            # If we're not in a trade and we get a signal
            if current_trade is None:
                if signal == 1:  # Long signal
                    current_trade = {
                        'entry_time': data.index[i],
                        'entry_price': price,
                        'type': 'long',
                        'entry_idx': i
                    }
                elif signal == -1:  # Short signal
                    current_trade = {
                        'entry_time': data.index[i],
                        'entry_price': price,
                        'type': 'short',
                        'entry_idx': i
                    }
                i += 1
            else:
                # We're in a trade, check for exit
                is_long = current_trade['type'] == 'long'
                exit_idx, profit, exit_reason = self.simulate_trade(
                    data['price'],
                    current_trade['entry_idx'],
                    is_long
                )
                
                # Complete the trade
                exit_price = data['price'].iloc[exit_idx]
                current_trade.update({
                    'exit_time': data.index[exit_idx],
                    'exit_price': exit_price,
                    'profit_pct': profit * 100,
                    'exit_reason': exit_reason
                })
                trades_list.append(current_trade)
                current_trade = None
                
                # Move to the next candle after the exit
                i = exit_idx + 1
        
        # Handle any open trade at the end
        if current_trade is not None:
            final_price = data['price'].iloc[-1]
            entry_price = current_trade['entry_price']
            is_long = current_trade['type'] == 'long'
            
            if is_long:
                final_profit = (final_price - entry_price) / entry_price
            else:
                final_profit = (entry_price - final_price) / entry_price
            
            final_profit -= self.commission * 2  # Account for commissions
            
            current_trade.update({
                'exit_time': data.index[-1],
                'exit_price': final_price,
                'profit_pct': final_profit * 100,
                'exit_reason': 'market_close'
            })
            trades_list.append(current_trade)
        
        # Create trades DataFrame
        trades_df = pd.DataFrame(trades_list)
        
        # Calculate performance metrics
        metrics = self.calculate_performance_metrics(trades_df)
        
        return trades_df, metrics
    
    def calculate_performance_metrics(self, trades_df: pd.DataFrame) -> Dict:
        """Calculate performance metrics from trades"""
        if len(trades_df) == 0:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'avg_profit': 0,
                'total_profit': 0,
                'max_drawdown': 0,
                'profit_factor': 0,
                'long_trades': 0,
                'short_trades': 0,
                'avg_trade_duration': 0,
                'take_profit_exits': 0,
                'stop_loss_exits': 0,
                'market_close_exits': 0
            }
        
        winning_trades = trades_df[trades_df['profit_pct'] > 0]
        losing_trades = trades_df[trades_df['profit_pct'] <= 0]
        
        total_profit = trades_df['profit_pct'].sum()
        cumulative_profits = trades_df['profit_pct'].cumsum()
        max_drawdown = (cumulative_profits.cummax() - cumulative_profits).max()
        
        profit_factor = (
            abs(winning_trades['profit_pct'].sum()) /
            abs(losing_trades['profit_pct'].sum())
            if len(losing_trades) > 0 and losing_trades['profit_pct'].sum() != 0
            else float('inf')
        )
        
        metrics = {
            'total_trades': len(trades_df),
            'win_rate': len(winning_trades) / len(trades_df) * 100,
            'avg_profit': trades_df['profit_pct'].mean(),
            'total_profit': total_profit,
            'max_drawdown': max_drawdown,
            'profit_factor': profit_factor,
            'long_trades': len(trades_df[trades_df['type'] == 'long']),
            'short_trades': len(trades_df[trades_df['type'] == 'short']),
            'avg_trade_duration': (
                trades_df['exit_time'] - trades_df['entry_time']
            ).mean().total_seconds() / 60 if len(trades_df) > 0 else 0  # in minutes
        }
        
        # Add exit reason statistics
        exit_reasons = trades_df['exit_reason'].value_counts()
        for reason in ['take_profit', 'stop_loss', 'market_close']:
            metrics[f'{reason}_exits'] = exit_reasons.get(reason, 0)
            
        return metrics
