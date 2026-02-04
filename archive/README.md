# Archive - Old Versions

This folder contains old versions of the bot and dashboard that are no longer in use.

## Files:

- `dashboard.py` - v2 dashboard (BTC only, reads from `paper_state.json`)
- `paper_trader_v3.py` - v3 bot (BTC RSI + BNB Stoch + ETH CCI)
- `paper_trader_v3_1.py` - v3.1 minor update
- `paper_trader_v3_backup.py` - backup of v3

## Current Active Files (in root):

- `paper_trader.py` - **v4 bot** (BTC RSI long-only + ETH CCI, writes to `paper_trading_state.json`)
- `dashboard.py` - **v4 dashboard** (reads from `paper_trading_state.json`)

## Why archived:

- v3 included BNB strategy which failed backtesting (-100% return over 3 years)
- v2 was single-strategy BTC only
- v4 is the validated version based on 3-year backtest data
