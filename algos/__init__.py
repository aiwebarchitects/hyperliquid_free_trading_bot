"""
Algorithms package for the crypto trading system
"""

from .base_algorithm import BaseAlgorithm, BacktestEngine
from .rsi_algorithm import RSIAlgorithm
from .rsi_1min_double_confirm_algorithm import RSI1MinDoubleConfirmAlgorithm

__all__ = ['BaseAlgorithm', 'BacktestEngine', 'RSIAlgorithm', 
           'RSI1MinDoubleConfirmAlgorithm', 'AlgorithmFactory']


class AlgorithmFactory:
    """Factory class for creating algorithm instances"""
    
    @staticmethod
    def create_algorithm(name: str, **params):
        """Create an algorithm instance by name"""
        algorithms = {
            'RSI': RSIAlgorithm,
            'RSI_1MIN_DOUBLE_CONFIRM': RSI1MinDoubleConfirmAlgorithm
        }
        
        if name not in algorithms:
            raise ValueError(f"Unknown algorithm: {name}. Available: {list(algorithms.keys())}")
        
        return algorithms[name](**params)
    
    @staticmethod
    def get_available_algorithms():
        """Get list of available algorithm names"""
        return ['RSI', 'RSI_1MIN_DOUBLE_CONFIRM']
