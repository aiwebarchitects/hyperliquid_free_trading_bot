"""
Main backtesting script for the multi-algorithm crypto backtesting system
"""

import os
import sys
import json
import time
import pandas as pd
import numpy as np
from datetime import datetime
from itertools import product
from typing import Dict, List, Tuple, Optional

# Import settings and algorithms
import settings
from algos import AlgorithmFactory, BacktestEngine
from historical_data_fetcher import CryptoCompareHistoricalFetcher


class ParameterOptimizer:
    """Optimizer for finding best algorithm parameters"""
    
    def __init__(self, algorithm_name: str, data: pd.DataFrame, coin: str):
        self.algorithm_name = algorithm_name
        self.data = data
        self.coin = coin
        self.results = []
    
    def get_parameter_combinations(self) -> List[Dict]:
        """Get all parameter combinations for optimization"""
        if self.algorithm_name == "RSI":
            param_ranges = settings.RSI_PARAMS
        elif self.algorithm_name == "MACD":
            param_ranges = settings.MACD_PARAMS
        elif self.algorithm_name == "SUPPORT_VOLUME":
            param_ranges = settings.SUPPORT_VOLUME_PARAMS
        elif self.algorithm_name == "VOL24":
            param_ranges = settings.VOL24_PARAMS
        elif self.algorithm_name == "SMA":
            param_ranges = settings.SMA_PARAMS
        else:
            raise ValueError(f"Unknown algorithm: {self.algorithm_name}")
        
        # Get algorithm-specific parameters
        algorithm = AlgorithmFactory.create_algorithm(self.algorithm_name)
        algo_ranges = algorithm.get_parameter_ranges()
        
        # Combine with take_profit and stop_loss
        all_ranges = {**algo_ranges, 
                     'take_profit': param_ranges['take_profit'],
                     'stop_loss': param_ranges['stop_loss']}
        
        # Generate all combinations
        keys = list(all_ranges.keys())
        values = list(all_ranges.values())
        combinations = []
        
        for combo in product(*values):
            param_dict = dict(zip(keys, combo))
            
            # Filter invalid combinations
            if self.algorithm_name == "MACD":
                if param_dict['fast_period'] >= param_dict['slow_period']:
                    continue
            elif self.algorithm_name == "SMA":
                if param_dict['short_period'] >= param_dict['long_period']:
                    continue
            
            combinations.append(param_dict)
        
        return combinations
    
    def optimize(self) -> Dict:
        """Run parameter optimization"""
        combinations = self.get_parameter_combinations()
        total_combinations = len(combinations)
        
        print(f"Testing {total_combinations} parameter combinations for {self.algorithm_name}...")
        
        best_result = {
            'total_profit': float('-inf'),
            'parameters': None,
            'metrics': None,
            'trades_df': None
        }
        
        for i, params in enumerate(combinations):
            if settings.VERBOSE and i % 50 == 0:
                print(f"Progress: {i+1}/{total_combinations} ({((i+1)/total_combinations)*100:.1f}%)")
            
            try:
                # Extract algorithm parameters and trading parameters
                algo_params = {k: v for k, v in params.items() 
                              if k not in ['take_profit', 'stop_loss']}
                
                # Create algorithm instance
                algorithm = AlgorithmFactory.create_algorithm(self.algorithm_name, **algo_params)
                
                # Create backtest engine
                engine = BacktestEngine(
                    algorithm=algorithm,
                    take_profit=params['take_profit'],
                    stop_loss=params['stop_loss'],
                    commission=settings.COMMISSION_RATE
                )
                
                # Run backtest
                trades_df, metrics = engine.backtest(self.data)
                
                # Store result
                result = {
                    **params,
                    'win_rate': metrics['win_rate'],
                    'total_trades': metrics['total_trades'],
                    'total_profit': metrics['total_profit'],
                    'profit_factor': metrics['profit_factor'],
                    'max_drawdown': metrics['max_drawdown'],
                    'avg_profit': metrics['avg_profit']
                }
                
                self.results.append(result)
                
                # Check if this is the best total profit so far
                if (metrics['total_profit'] > best_result['total_profit'] and 
                    metrics['total_trades'] >= settings.MIN_TRADES_THRESHOLD):
                    best_result = {
                        'total_profit': metrics['total_profit'],
                        'parameters': params,
                        'metrics': metrics,
                        'trades_df': trades_df
                    }
                    
            except Exception as e:
                if settings.VERBOSE:
                    print(f"Error with parameters {params}: {e}")
                continue
        
        print(f"Optimization complete! Best total profit: {best_result['total_profit']:.2f}%")
        return best_result


class BacktestingSystem:
    """Main backtesting system orchestrator"""
    
    def __init__(self):
        self.results = []
        self.data_fetcher = CryptoCompareHistoricalFetcher()
        
        # Ensure directories exist
        os.makedirs(settings.DATA_DIR, exist_ok=True)
        os.makedirs(settings.RESULTS_DIR, exist_ok=True)
    
    def download_historical_data(self) -> bool:
        """Download historical data for all coins"""
        print("="*60)
        print("DOWNLOADING HISTORICAL DATA")
        print("="*60)
        
        try:
            success = self.data_fetcher.bootstrap_historical_data(
                base_data_dir=settings.DATA_DIR,
                coins=settings.COINS,
                use_coingecko=True
            )
            
            if success:
                print("✅ Historical data download completed successfully!")
                return True
            else:
                print("❌ Failed to download historical data")
                return False
                
        except Exception as e:
            print(f"❌ Error downloading data: {e}")
            return False
    
    def load_data(self, coin: str) -> Optional[pd.DataFrame]:
        """Load historical data for a specific coin"""
        try:
            # Try to load minute data first
            data_file = os.path.join(settings.DATA_DIR, coin, f"{settings.TIMEFRAME}.json")
            
            if not os.path.exists(data_file):
                print(f"Data file not found: {data_file}")
                return None
            
            with open(data_file, 'r') as f:
                file_data = json.load(f)
            
            data_list = file_data.get('data', [])
            if not data_list:
                print(f"No data found in {data_file}")
                return None
            
            # Convert to DataFrame
            df_data = []
            for item in data_list:
                df_data.append({
                    'timestamp': pd.to_datetime(item['timestamp']),
                    'price': float(item['price']),
                    'volume': float(item['volume'])
                })
            
            df = pd.DataFrame(df_data)
            df.set_index('timestamp', inplace=True)
            df = df.sort_index()
            
            print(f"Loaded {len(df)} data points for {coin}")
            print(f"Data range: {df.index[0]} to {df.index[-1]}")
            
            return df
            
        except Exception as e:
            print(f"Error loading data for {coin}: {e}")
            return None
    
    def run_algorithm_backtest(self, algorithm_name: str, coin: str, data: pd.DataFrame) -> Dict:
        """Run backtest for a specific algorithm and coin"""
        print(f"\n--- Running {algorithm_name} backtest for {coin} ---")
        
        # Initialize optimizer
        optimizer = ParameterOptimizer(algorithm_name, data, coin)
        
        # Run optimization
        start_time = time.time()
        best_result = optimizer.optimize()
        end_time = time.time()
        
        print(f"Optimization completed in {end_time - start_time:.2f} seconds")
        
        if best_result['parameters'] is None:
            print(f"❌ No valid results found for {algorithm_name} on {coin}")
            return None
        
        # Display results
        print(f"\n✅ Best {algorithm_name} strategy for {coin}:")
        print(f"Win Rate: {best_result['metrics']['win_rate']:.2f}%")
        print(f"Total Trades: {best_result['metrics']['total_trades']}")
        print(f"Total Profit: {best_result['metrics']['total_profit']:.2f}%")
        print(f"Profit Factor: {best_result['metrics']['profit_factor']:.2f}")
        print(f"Parameters: {best_result['parameters']}")
        
        return best_result
    
    def save_results(self, algorithm_name: str, coin: str, result: Dict):
        """Save backtest results to JSON file"""
        if result is None:
            return
        
        filename = "best_results.json"
        filepath = os.path.join(settings.RESULTS_DIR, filename)
        
        # Load existing results or create new structure
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                all_results = json.load(f)
        else:
            all_results = {"strategies": []}
        
        # Convert numpy types to native Python types
        def convert_types(obj):
            if hasattr(obj, 'item'):
                return obj.item()
            elif isinstance(obj, (np.integer, np.int64)):
                return int(obj)
            elif isinstance(obj, (np.floating, np.float64)):
                return float(obj)
            elif isinstance(obj, dict):
                return {k: convert_types(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_types(v) for v in obj]
            return obj
        
        # Prepare new result
        new_result = {
            'strategy_name': algorithm_name,
            'coin': coin,
            'timeframe': settings.TIMEFRAME,
            'optimization_date': datetime.now().isoformat(),
            'data_points': len(self.current_data) if hasattr(self, 'current_data') else 0,
            'parameters': convert_types(result['parameters']),
            'win_rate': float(result['metrics']['win_rate']),
            'metrics': convert_types(result['metrics'])
        }
        
        # Remove existing result for this algorithm and coin
        all_results["strategies"] = [
            r for r in all_results["strategies"] 
            if not (r.get('strategy_name') == algorithm_name and r.get('coin') == coin)
        ]
        
        # Add new result
        all_results["strategies"].append(new_result)
        
        # Sort by total profit
        all_results["strategies"].sort(key=lambda x: x['metrics']['total_profit'], reverse=True)
        
        # Save to file
        with open(filepath, 'w') as f:
            json.dump(all_results, f, indent=2)
        
        print(f"Results saved to {filepath}")
    
    def display_final_summary(self):
        """Display final summary of all results"""
        filepath = os.path.join(settings.RESULTS_DIR, "best_results.json")
        
        if not os.path.exists(filepath):
            print("No results file found")
            return
        
        with open(filepath, 'r') as f:
            all_results = json.load(f)
        
        strategies = all_results.get("strategies", [])
        
        if not strategies:
            print("No strategies found in results")
            return
        
        print("\n" + "="*80)
        print("FINAL BACKTESTING SUMMARY - BEST STRATEGIES")
        print("="*80)
        
        # Find best strategy overall
        best_strategy = strategies[0]  # Already sorted by total profit
        
        print(f"\n🏆 BEST OVERALL STRATEGY:")
        print(f"Algorithm: {best_strategy['strategy_name']}")
        print(f"Coin: {best_strategy['coin']}")
        print(f"Win Rate: {best_strategy['win_rate']:.2f}%")
        print(f"Total Trades: {best_strategy['metrics']['total_trades']}")
        print(f"Total Profit: {best_strategy['metrics']['total_profit']:.2f}%")
        print(f"Profit Factor: {best_strategy['metrics']['profit_factor']:.2f}")
        print(f"Parameters: {best_strategy['parameters']}")
        
        print(f"\n📊 ALL STRATEGIES RANKED BY TOTAL PROFIT:")
        print("-" * 80)
        
        for i, strategy in enumerate(strategies[:10], 1):  # Show top 10
            print(f"{i:2d}. {strategy['strategy_name']:4s} | {strategy['coin']:3s} | "
                  f"Win Rate: {strategy['win_rate']:6.2f}% | "
                  f"Trades: {strategy['metrics']['total_trades']:3d} | "
                  f"Profit: {strategy['metrics']['total_profit']:7.2f}%")
    
    def run(self):
        """Run the complete backtesting system"""
        print("="*80)
        print("MULTI-ALGORITHM CRYPTO BACKTESTING SYSTEM")
        print("="*80)
        print(f"Coins: {', '.join(settings.COINS)}")
        print(f"Algorithms: {', '.join(settings.ALGORITHMS)}")
        print(f"Timeframe: {settings.TIMEFRAME}")
        
        # Step 1: Download historical data
        if not self.download_historical_data():
            print("❌ Failed to download data. Exiting.")
            return
        
        # Step 2: Run backtests for each coin and algorithm
        for coin in settings.COINS:
            print(f"\n{'='*60}")
            print(f"PROCESSING {coin}")
            print(f"{'='*60}")
            
            # Load data for this coin
            data = self.load_data(coin)
            if data is None:
                print(f"❌ Skipping {coin} - no data available")
                continue
            
            self.current_data = data  # Store for saving results
            
            # Run each algorithm
            for algorithm_name in settings.ALGORITHMS:
                try:
                    result = self.run_algorithm_backtest(algorithm_name, coin, data)
                    if result:
                        self.save_results(algorithm_name, coin, result)
                        self.results.append({
                            'algorithm': algorithm_name,
                            'coin': coin,
                            'result': result
                        })
                except Exception as e:
                    print(f"❌ Error running {algorithm_name} on {coin}: {e}")
                    continue
        
        # Step 3: Display final summary
        self.display_final_summary()
        
        print(f"\n✅ Backtesting completed! Check {settings.RESULTS_DIR}/ for detailed results.")


def main():
    """Main entry point"""
    try:
        system = BacktestingSystem()
        system.run()
    except KeyboardInterrupt:
        print("\n❌ Backtesting interrupted by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
