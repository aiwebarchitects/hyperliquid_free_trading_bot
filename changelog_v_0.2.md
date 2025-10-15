# Changelog - Version 0.2

## Release Date: October 15, 2025

## 🎉 Major Features

### Integrated Backtesting System
- **New BACKTEST Tab**: Added a dedicated tab in the panel for strategy backtesting
- **Real-time Data**: Fetches live 1-minute PAXG data from Binance API
- **Comprehensive Metrics**: Displays win rate, total profit, profit factor, max drawdown, and more
- **Trade Details**: Shows last 5 trades with entry/exit prices and reasons
- **Easy to Use**: Simply press 'B' on the BACKTEST tab to run a backtest

### Code Organization
- **Helper Folder**: Created `helpers/` directory for better code organization
- **Backtest Helper**: New `helpers/backtest_helper.py` module for panel backtesting
- **Moved Files**: Relocated `start_backtesting.py` to `helpers/` folder

### Cleaner Codebase
- **Removed Unused Algorithms**: Deleted MACD, SMA, Support Volume, and Vol24 algorithms
- **Focused Strategy**: Kept only RSI and RSI 1MIN Double Confirm algorithms
- **Updated Imports**: Cleaned up `algos/__init__.py` to reflect only used algorithms

## 📊 Interface Updates

### 4-Tab Interface
1. **MAIN**: Account overview, position, and RSI indicator (unchanged)
2. **BOT**: Bot control and activity logs (unchanged)
3. **HISTORY**: Trade history (unchanged)
4. **BACKTEST**: New tab for strategy backtesting

### New Keyboard Controls
- **B**: Run backtest (when on BACKTEST tab)
- All previous controls remain the same (TAB, S, X, R, Q)

## 🔧 Technical Improvements

### Backtest Features
- Tests up to 1000 candles (approximately 16 hours of 1-minute data)
- Uses same parameters as live trading for accurate results
- Progress bar shows backtest status
- Error handling for network issues
- Automatic data fetching from Binance

### Performance Metrics
- **Win Rate**: Percentage of profitable trades
- **Total Profit**: Cumulative profit/loss percentage
- **Profit Factor**: Ratio of gross profit to gross loss
- **Max Drawdown**: Largest peak-to-trough decline
- **Average Profit**: Mean profit per trade
- **Trade Count**: Total number of trades executed
- **Exit Reasons**: Breakdown by take profit, stop loss, or market close

## 🐛 Bug Fixes

### Fixed Issues
- **'side' Error**: Fixed KeyError when displaying backtest trades
  - Changed from accessing 'side' column to 'type' column
  - Properly converts 'long'/'short' to 'LONG'/'SHORT' for display

## 📁 File Structure Changes

### New Files
- `helpers/backtest_helper.py` - Panel backtesting module
- `changelog_v_0.2.md` - This file

### Moved Files
- `start_backtesting.py` → `helpers/start_backtesting.py`

### Deleted Files
- `algos/macd_algorithm.py`
- `algos/sma_algorithm.py`
- `algos/support_volume_algorithm.py`
- `algos/vol24_algorithm.py`

### Modified Files
- `paxg_panel.py` - Added BACKTEST tab and backtest functionality
- `algos/__init__.py` - Updated to only include RSI algorithms
- `README.md` - Updated for v0.2 with new features
- `system_files.txt` - Updated file structure documentation

## 🎯 Strategy Unchanged

The core RSI 1MIN Double Confirm strategy remains the same:
- SHORT when RSI tops, dips below 50, and price breaks support
- COVER when RSI reaches oversold (< 20)
- Take Profit: 1.5%
- Stop Loss: -0.7%

## 📝 Documentation Updates

### README.md
- Updated version number to 0.2
- Added backtesting section with usage instructions
- Updated file structure diagram
- Added troubleshooting for backtest errors
- Updated changelog section

### system_files.txt
- Updated to reflect new file structure
- Added helpers/ folder documentation
- Removed references to deleted algorithm files

## 🔄 Migration from v0.1

### For Existing Users
1. Pull latest changes from repository
2. No configuration changes needed
3. All existing settings in `settings.py` remain valid
4. API credentials in `executer/config.json` unchanged
5. Simply restart the panel to access new features

### Breaking Changes
- None - fully backward compatible with v0.1 configurations

## 🚀 Future Enhancements (Planned)

Potential features for future versions:
- Custom parameter input for backtesting
- Multiple timeframe support
- Additional trading strategies
- Export backtest results to CSV
- Performance charts and visualizations
- Multi-coin support

## 📊 Testing

### Tested On
- Python 3.8, 3.9, 3.10, 3.11
- Linux (Ubuntu 20.04, 22.04)
- macOS (Monterey, Ventura)

### Known Limitations
- Backtest limited to 1000 candles due to Binance API restrictions
- Requires internet connection for backtesting
- Terminal UI requires minimum 60x20 character display

## 🙏 Acknowledgments

Thanks to all users who provided feedback on v0.1 and requested backtesting functionality!

---

**Version**: 0.2  
**Release Date**: October 15, 2025  
**Status**: Stable  
**License**: Open Source
