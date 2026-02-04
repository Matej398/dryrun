# DRYRUN v2 - Paper Trading Bot

**Strategy:** H4 Permission + RSI Extreme  
**Pair:** BTC only  
**Win Rate (backtested):** 59.3%  

## Features

- ✅ BTC only trading
- ✅ RSI Extreme entry trigger (30/70)
- ✅ H4 bias permission filter
- ✅ Live WebSocket prices (real-time)
- ✅ Live unrealized P&L
- ✅ Clean dashboard

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

Visit: `http://YOUR_VPS_IP:5050`

## Git & auto-deploy

- Repo: **https://github.com/Matej398/dryrun**
- Push to `main` triggers the webhook: pull on VPS + restart `dryrun-bot` and `dryrun-dashboard`.
- No `.env` is used; state/log files are gitignored so they stay on the VPS. See **DEPLOYMENT.md** for first-time push and webhook setup.

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

1. Check H4 candle bias (bullish/bearish/neutral)
2. If neutral → no trade
3. If bullish → only look for longs
4. If bearish → only look for shorts
5. Entry: RSI crosses back from extreme (30 or 70)
6. Stop: 1% | Target: 2% (2:1 RR)
7. Risk: 2% per trade

