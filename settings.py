"""
Settings configuration for the PAXG trading bot
"""

# =============================================================================
# LIVE TRADING BOT SETTINGS
# =============================================================================

# Network configuration
BOT_USE_TESTNET = False  # True for testnet, False for mainnet (REAL MONEY!)

# Trading configuration
BOT_POSITION_VALUE_USD = 100.0  # USD value per position
BOT_MAX_TOTAL_POSITION_USD = 500.0  # Maximum total position value in USD
BOT_CYCLE_INTERVAL = 60  # Seconds between trading cycles

# Cooldown configuration
BOT_BUY_COOLDOWN_MINUTES = 5  # Minutes to wait after each buy before buying again

# RSI trading parameters (optimized for RSI 1MIN Double Confirm strategy)
BOT_RSI_PERIOD = 10  # RSI calculation period
BOT_RSI_OVERSOLD = 20  # Cover when RSI drops below this value
BOT_RSI_OVERBOUGHT = 65  # Short setup when RSI rises above this value

# Risk management
BOT_TAKE_PROFIT = 0.015  # Take profit at 1.5%
BOT_STOP_LOSS = -0.007  # Stop loss at -0.7%

# Sell conditions
BOT_SELL_ENTIRE_POSITION = True  # True = sell entire position, False = sell one position at a time
