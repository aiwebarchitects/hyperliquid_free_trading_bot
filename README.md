# Free Hyperliquid Python Trading Bot 4 PAXG + Panel v0.2

A real-time monitoring and trading panel for PAXG (Paxos Gold) using the RSI 1MIN Double Confirm strategy on Hyperliquid, now with integrated backtesting!

![Free Hyperliquid Trading Bot](free_hyperliquid_trading_bot.png)

## 🎁 Get Started with Bonus

**Sign up using our referral link to get a 4% fee discount bonus:**
👉 [Join Hyperliquid with BONUS500](https://app.hyperliquid.xyz/join/BONUS500)

After signing up, get your API keys from: [Hyperliquid API Settings](https://app.hyperliquid.xyz/API)

## Screenshots

The bot features a clean, four-tab interface for monitoring, controlling, and backtesting your trading operations:

### Main Dashboard
![Main Dashboard](screenshots/Main.png)
*Real-time account overview with balance, current position, and RSI indicator*

### Bot Control Panel
![Bot Control](screenshots/Bot.png)
*Start/stop the bot, view activity logs, and monitor current trading signals*

### Trade History
![Trade History](screenshots/History.png)
*Track your last 20 PAXG trades with detailed information*

### Backtest Analysis
![Backtest](screenshots/Backtest.png)
*Test your strategy with historical data and view comprehensive performance metrics*

## Version 0.2 - Backtest Integration Release

**What's New in v0.2:**
- ✨ **Integrated Backtesting**: Test your strategy directly from the panel
- 📊 **4-Tab Interface**: Added dedicated BACKTEST tab
- 🧹 **Cleaner Codebase**: Removed unused algorithms (MACD, SMA, Support Volume, Vol24)
- 📁 **Better Organization**: Backtesting files moved to `helpers/` folder
- 🎯 **Focused Strategy**: Optimized for RSI 1MIN Double Confirm only

## Overview

This bot implements a SHORT-based trading strategy using RSI (Relative Strength Index) with a double confirmation mechanism:
- **SHORT Signal**: RSI tops above 65, then dips below 50 while price breaks support
- **COVER Signal**: RSI reaches oversold levels (< 20)
- **Risk Management**: Automatic take profit (1.5%) and stop loss (-0.7%)

## Features

- 🎯 **Real-time Monitoring**: Live account balance, positions, and RSI tracking
- 🤖 **Automated Trading**: Set-and-forget bot with configurable parameters
- 📊 **4-Tab Interface**: Main dashboard, bot control, trade history, and backtesting
- 🔬 **Integrated Backtesting**: Test strategy performance with historical data
- 🔒 **Risk Management**: Built-in take profit and stop loss protection
- 🌐 **Testnet Support**: Test strategies safely before going live

## Installation

### Prerequisites

- Python 3.8 or higher
- Linux/Mac (for curses terminal UI)
- Hyperliquid account with API access

### Setup

1. Clone the repository:
```bash
git clone https://github.com/aiwebarchitects/hyperliquid_free_trading_bot.git
cd hyperliquid_free_trading_bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure API credentials:
Open `executer/config.json` and replace the placeholder values with your Hyperliquid API credentials:
```json
{
  "account_address": "your_wallet_address",
  "secret_key": "your_private_key"
}
```

**For Mainnet:**
Get your API credentials from [Hyperliquid API Settings](https://app.hyperliquid.xyz/API)

**For Testnet:**
- First, claim 1000 USDC test funds: [Testnet Faucet](https://app.hyperliquid-testnet.xyz/drip)
- Then create your testnet API key: [Testnet API Settings](https://app.hyperliquid-testnet.xyz/API)
- Remember to set `BOT_USE_TESTNET = True` in `settings.py`

4. Configure bot settings:
Edit `settings.py` to customize:
- `BOT_USE_TESTNET`: Set to `True` for testnet, `False` for mainnet
- `BOT_POSITION_VALUE_USD`: Position size per trade
- `BOT_MAX_TOTAL_POSITION_USD`: Maximum total position value
- `BOT_BUY_COOLDOWN_MINUTES`: Cooldown between trades

## Usage

### Start the Panel

```bash
python3 paxg_panel.py
```

### Keyboard Controls

- **TAB** or **←/→**: Switch between tabs (Main, Bot, History, Backtest)
- **S**: Start the automated trading bot
- **X**: Stop the automated trading bot
- **B**: Run backtest (when on BACKTEST tab)
- **R**: Refresh data manually
- **Q**: Quit the application

### Tabs

1. **MAIN**: Account overview, current position, and RSI indicator
2. **BOT**: Bot control, activity logs, and current signals
3. **HISTORY**: Last 20 PAXG trades
4. **BACKTEST**: Strategy backtesting with performance metrics

## Backtesting

### How to Use

1. Navigate to the **BACKTEST** tab
2. Review current settings (RSI period, thresholds, take profit, stop loss)
3. Press **B** to run backtest
4. View results including:
   - Win rate and total profit
   - Profit factor and max drawdown
   - Average profit per trade
   - Recent trades with entry/exit details

### Backtest Features

- Fetches real 1-minute PAXG data from Binance
- Tests up to 1000 candles (approximately 16 hours of data)
- Shows detailed trade-by-trade results
- Displays comprehensive performance metrics
- Uses same parameters as live trading

## Trading Strategy

### RSI 1MIN Double Confirm (SHORT-based)

The bot uses a sophisticated double confirmation mechanism:

1. **Setup Phase**: RSI must first "top" by either:
   - Reaching overbought (> 65), OR
   - Making a local peak above 60

2. **SHORT Signal** (all conditions must be met):
   - RSI has topped (from step 1)
   - RSI crosses below 50
   - Price breaks below support level (lowest low in last 10 candles)

3. **COVER Signal**:
   - RSI crosses into oversold territory (< 20)

4. **Risk Management** (checked every cycle):
   - Take Profit: Close at +1.5% profit
   - Stop Loss: Close at -0.7% loss

### Optimized Parameters

The bot uses the following optimized parameters:
- RSI Period: 10
- Oversold Threshold: 20
- Overbought Threshold: 65
- Take Profit: 1.5%
- Stop Loss: -0.7%

## Configuration

### settings.py

```python
# Network Configuration
BOT_USE_TESTNET = False  # Set to True for testnet

# Trading Configuration
BOT_POSITION_VALUE_USD = 100.0  # Position size per trade
BOT_MAX_TOTAL_POSITION_USD = 500.0  # Maximum total position
BOT_BUY_COOLDOWN_MINUTES = 5  # Cooldown between trades

# RSI Parameters
BOT_RSI_PERIOD = 10
BOT_RSI_OVERSOLD = 20
BOT_RSI_OVERBOUGHT = 65

# Risk Management
BOT_TAKE_PROFIT = 0.015  # 1.5%
BOT_STOP_LOSS = -0.007   # -0.7%
```

## Safety Features

- ✅ Testnet mode for safe testing
- ✅ Position size limits
- ✅ Trade cooldown periods
- ✅ Automatic stop loss
- ✅ Manual bot control (start/stop anytime)
- ✅ Backtesting before live trading

## File Structure

```
hyperliquid_free_trading_bot_0.2/
├── paxg_panel.py                    # Main application
├── settings.py                      # Bot configuration
├── README.md                        # This file
├── requirements.txt                 # Python dependencies
├── system_files.txt                 # System documentation
├── changelog_v_0.2.md              # Version changelog
├── free_hyperliquid_trading_bot.png # Bot screenshot
├── algos/                           # Trading algorithms
│   ├── __init__.py
│   ├── base_algorithm.py
│   ├── rsi_algorithm.py
│   └── rsi_1min_double_confirm_algorithm.py
├── helpers/                         # Helper modules
│   ├── backtest_helper.py          # Panel backtester
│   └── start_backtesting.py        # Standalone backtester
├── executer/                        # Exchange utilities
│   ├── example_utils.py
│   └── config.json                 # API credentials
└── screenshots/                     # UI screenshots
    ├── Main.png
    ├── Bot.png
    └── History.png
```

## Troubleshooting

### Terminal Size Error
If you see "Terminal too small!", resize your terminal to at least 60x20 characters.

### Connection Issues
- Verify your API credentials in `executer/config.json`
- Check if you're using the correct network (testnet vs mainnet)
- Ensure you have internet connectivity

### No RSI Data
- The bot fetches data from Binance API for RSI calculation
- Check your internet connection
- Wait a few seconds for initial data load

### Backtest Errors
- Ensure you have internet connectivity (fetches data from Binance)
- Check that pandas and requests are properly installed
- Try running backtest again if it times out

## Changelog

### Version 0.2 (Current)
- Added integrated backtesting system
- New BACKTEST tab in panel interface
- Moved backtesting files to `helpers/` folder
- Removed unused algorithms (MACD, SMA, Support Volume, Vol24)
- Cleaner, more focused codebase
- Updated documentation

### Version 0.1
- Initial release
- 3-tab interface (Main, Bot, History)
- RSI 1MIN Double Confirm strategy
- Manual bot start/stop
- Basic monitoring features

## Disclaimer

⚠️ **IMPORTANT**: This bot is for educational purposes only. Trading cryptocurrencies involves substantial risk of loss. Always:
- Test thoroughly on testnet first
- Use backtesting to validate strategy
- Start with small position sizes
- Never invest more than you can afford to lose
- Monitor the bot regularly
- Understand the strategy before using it

## License

This project is provided as-is without any warranty. Use at your own risk.

## Support

For issues or questions, please check the system_files.txt for technical details or review the code documentation.

## Contributing

This is an open-source project. Feel free to fork, modify, and improve!
