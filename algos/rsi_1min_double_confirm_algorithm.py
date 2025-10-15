"""
RSI 1MIN Double Confirm Algorithm Implementation
Requires TWO consecutive oversold signals on 1-minute candles before buying
Uses 1-minute candle data with double confirmation strategy
"""

import pandas as pd
import numpy as np
from typing import Dict
from .base_algorithm import BaseAlgorithm


class RSI1MinDoubleConfirmAlgorithm(BaseAlgorithm):
    """RSI trading algorithm with double confirmation on 1-minute candles"""
    
    def __init__(self, period: int = 14, oversold_threshold: int = 30, 
                 overbought_threshold: int = 70, **kwargs):
        super().__init__("RSI_1MIN_DOUBLE_CONFIRM", **kwargs)
        self.period = period
        self.oversold_threshold = oversold_threshold
        self.overbought_threshold = overbought_threshold
    
    def calculate_rsi(self, prices: pd.Series) -> pd.Series:
        """Calculate RSI (Relative Strength Index)"""
        # Calculate price changes
        delta = prices.diff()
        
        # Separate gains and losses
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # Calculate average gain and loss using exponential moving average
        avg_gain = gain.ewm(span=self.period, adjust=False).mean()
        avg_loss = loss.ewm(span=self.period, adjust=False).mean()
        
        # Calculate RS (Relative Strength)
        rs = avg_gain / avg_loss
        
        # Calculate RSI
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        Generate RSI trading signals with new logic
        
        Strategy:
        - SHORT when:
          1. RSI tops (reaches overbought or peaks)
          2. Then RSI dips below 50
          3. AND price breaks below recent support (local low)
        - Cover when RSI reaches oversold
        """
        rsi = self.calculate_rsi(data['price'])
        signals = pd.Series(0, index=data.index)
        prices = data['price']
        
        # Track RSI state
        rsi_topped = pd.Series(False, index=data.index)
        
        # Detect RSI tops (when RSI was above overbought or at local peak)
        for i in range(2, len(rsi)):
            # RSI topped if it was above overbought threshold in recent past (last 5-10 candles)
            recent_high = rsi.iloc[max(0, i-10):i].max()
            if recent_high >= self.overbought_threshold:
                rsi_topped.iloc[i] = True
            # Or if RSI made a local peak (higher than neighbors)
            elif i >= 2 and rsi.iloc[i-1] > rsi.iloc[i-2] and rsi.iloc[i-1] > rsi.iloc[i]:
                if rsi.iloc[i-1] > 60:  # Only consider significant peaks
                    rsi_topped.iloc[i] = True
        
        # Calculate support levels (recent local lows in last 10 candles)
        support_levels = pd.Series(index=data.index, dtype=float)
        for i in range(10, len(prices)):
            # Support is the lowest low in the last 10 candles
            support_levels.iloc[i] = prices.iloc[i-10:i].min()
        
        # Generate SHORT signals
        # Condition: RSI topped, then dipped below 50, AND price breaks below support
        for i in range(11, len(signals)):
            if (rsi_topped.iloc[i] and 
                rsi.iloc[i] < 50 and 
                rsi.iloc[i-1] >= 50 and  # Just crossed below 50
                prices.iloc[i] < support_levels.iloc[i]):  # Price broke support
                signals.iloc[i] = -1  # SHORT signal
        
        # Generate COVER signals (exit short when RSI reaches oversold)
        cover_condition = (
            (rsi <= self.oversold_threshold) & 
            (rsi.shift(1) > self.oversold_threshold)
        )
        signals[cover_condition] = 1  # Cover short (buy to close)
        
        return signals
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate RSI indicator and add to data"""
        result = data.copy()
        result['rsi'] = self.calculate_rsi(data['price'])
        return result
    
    def get_parameter_ranges(self) -> Dict:
        """
        Get parameter ranges for RSI Double Confirm optimization
        
        Similar to standard RSI but optimized for double confirmation strategy
        """
        return {
            'period': [10, 12, 14, 16, 18, 20],
            'oversold_threshold': [15, 20, 25, 30, 35],
            'overbought_threshold': [65, 70, 75, 80, 85]
        }
    
    def __str__(self):
        return f"RSI_1MIN_DOUBLE_CONFIRM(period={self.period}, oversold={self.oversold_threshold}, overbought={self.overbought_threshold})"
