# DRYRUN v4 - Multi-Strategy Paper Trading Bot

## Scalp Strategies (15m timeframe)
- BTC RSI Extreme + H4 filter (LONG-ONLY)
- ETH CCI Extreme + H4 + Daily filter  
- SOL CCI Extreme + H4 + Daily filter (105% robustness)
- ADA CCI Extreme + H4 + Daily filter (115% robustness)
- AVAX CCI Extreme + H4 + Daily filter (122% robustness - CHAMPION!)

## Swing Strategies (Daily timeframe)
- BTC Volume Surge (LONG-ONLY) - Entry: Vol > 2x avg + 2% price up
- ETH Volume Surge (LONG-ONLY) - Entry: Vol > 2x avg + 2% price up
- BNB OBV Divergence (LONG-ONLY) - Entry: Price down + OBV up (accumulation)

**Based on 3-year backtest validation (2023-2026)**  
**Total Capital: $8,000 ($1,000 per strategy)**

## Features

- ✅ 8 validated strategies: 5 Scalp (15m) + 3 Swing (Daily)
- ✅ RSI, CCI, Volume Surge, OBV Divergence indicators
- ✅ Live WebSocket prices (real-time)
- ✅ Live unrealized P&L tracking
- ✅ Telegram alerts for all trades
- ✅ Clean dashboard with trade history
- ✅ Auto-deploy via GitHub webhook

## Quick Setup

```bash
# 1. Go to folder
cd /var/www/html/codelabhaven/projects/dryrun

# 2. Create venv
python3 -m venv venv
source venv/bin/activate

# 3. Install requirements
pip install -r requirements.txt

# 4. Copy service files
cp dryrun-bot.service /etc/systemd/system/
cp dryrun-dashboard.service /etc/systemd/system/

# 5. Start services
systemctl daemon-reload
systemctl enable dryrun-bot dryrun-dashboard
systemctl start dryrun-bot dryrun-dashboard

# 6. Check status
systemctl status dryrun-bot
systemctl status dryrun-dashboard
```

## Dashboard

Visit: `http://YOUR_VPS_IP:5051`

## Commands

```bash
# View bot logs
journalctl -u dryrun-bot -f

# Restart bot
systemctl restart dryrun-bot

# Stop everything
systemctl stop dryrun-bot dryrun-dashboard

# Reset state (clear all trades)
rm /var/www/html/codelabhaven/projects/dryrun/*.json
systemctl restart dryrun-bot
```

## Strategy Logic

### BTC RSI (Long-Only)
1. H4 filter: Only trade longs when H4 is bullish or neutral
2. Entry: RSI crosses above 30 (oversold bounce)
3. Stop: -1% | Target: +2% (2:1 RR)
4. Risk: 2% per trade
5. Starting capital: $1,000

### ETH CCI (Both Directions)
1. H4 + Daily filters: Both must align with direction
2. Entry Long: CCI crosses above -100 (oversold)
3. Entry Short: CCI crosses below +100 (overbought)
4. Stop: -1% | Target: +2% (2:1 RR)
5. Risk: 2% per trade
6. Starting capital: $1,000

### SOL CCI (Both Directions) - 105% Robustness
1. H4 + Daily filters: Both must align with direction
2. Entry Long: CCI crosses above -100 (oversold)
3. Entry Short: CCI crosses below +100 (overbought)
4. Stop: -1% | Target: +2% (2:1 RR)
5. Risk: 2% per trade
6. Starting capital: $1,000

### ADA CCI (Both Directions) - 115% Robustness
1. H4 + Daily filters: Both must align with direction
2. Entry Long: CCI crosses above -100 (oversold)
3. Entry Short: CCI crosses below +100 (overbought)
4. Stop: -1% | Target: +2% (2:1 RR)
5. Risk: 2% per trade
6. Starting capital: $1,000
7. Backtest: +31% / 3 years, 73.7% win rate

### AVAX CCI (Both Directions) - 122% Robustness (CHAMPION!)
1. H4 + Daily filters: Both must align with direction
2. Entry Long: CCI crosses above -100 (oversold)
3. Entry Short: CCI crosses below +100 (overbought)
4. Stop: -1% | Target: +2% (2:1 RR)
5. Risk: 2% per trade
6. Starting capital: $1,000
7. Backtest: +33% / 3 years, 73.2% win rate

---

## Daily Swing Strategies

### BTC Volume Surge (Long-Only)
1. Timeframe: Daily (1d)
2. Entry: Volume > 2x 20-day average AND price up 2%+
3. Stop: -3% | Target: +10%
4. Risk: 100% capital per trade (swing position)
5. Starting capital: $1,000

### ETH Volume Surge (Long-Only)
1. Timeframe: Daily (1d)
2. Entry: Volume > 2x 20-day average AND price up 2%+
3. Stop: -3% | Target: +10%
4. Risk: 100% capital per trade (swing position)
5. Starting capital: $1,000

### BNB OBV Divergence (Long-Only)
1. Timeframe: Daily (1d)
2. Entry: Price down over 10 days BUT OBV up (accumulation signal)
3. Stop: -5% | Target: +15%
4. Risk: 100% capital per trade (swing position)
5. Starting capital: $1,000

## Project Structure

```
dryrun/
├── paper_trader.py          # Main bot (v4)
├── dashboard.py              # Web dashboard (v4)
├── dryrun-bot.service        # Systemd service for bot
├── dryrun-dashboard.service  # Systemd service for dashboard
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── DEPLOYMENT.md             # Git & webhook setup guide
├── archive/                  # Old versions (v2, v3)
└── .env                      # Telegram credentials (not in git)
```
