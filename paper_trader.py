"""
DRYRUN Paper Trading Bot v5.0 - Plugin Architecture

Strategies are auto-discovered from the strategies/ folder.
Add new strategy = drop a .py file, restart the bot.
"""

import ccxt
import pandas as pd
import time
from datetime import datetime
import json
import os
import sys
import signal
import atexit

from strategies import discover_strategies

# Load .env file if running locally (not via systemd)
from pathlib import Path
env_file = Path(__file__).parent / '.env'
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip())

# =============================================================================
# CONFIGURATION
# =============================================================================

INITIAL_CAPITAL_PER_STRATEGY = 1000

# State file for persistence
STATE_FILE = 'paper_trading_state.json'

# Telegram alerts (loaded from environment variables)
TELEGRAM_ENABLED = os.environ.get('TELEGRAM_ENABLED', 'true').lower() == 'true'
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')


# =============================================================================
# SMART PRICE FORMATTING
# =============================================================================

def fmt_price(price):
    """Smart decimal formatting based on price level.
    BTC/ETH = 2 decimals, mid-range = 3, small coins = 4-5 decimals.
    """
    if price >= 100:       # BTC, ETH, BNB, SOL
        return f"${price:,.2f}"
    elif price >= 10:      # AVAX, LINK, etc.
        return f"${price:,.3f}"
    elif price >= 1:       # ADA, XRP, etc.
        return f"${price:,.4f}"
    else:                  # DOGE, SHIB, etc.
        return f"${price:,.5f}"


def fmt_size(size, price):
    """Smart size formatting - more decimals for expensive coins."""
    if price >= 10000:     # BTC
        return f"{size:.6f}"
    elif price >= 100:     # ETH, BNB, SOL
        return f"{size:.4f}"
    elif price >= 1:       # ADA, AVAX
        return f"{size:.2f}"
    else:
        return f"{size:.1f}"


# =============================================================================
# STATE MANAGEMENT
# =============================================================================

def load_state():
    """Load trading state from file"""
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


# Old per-strategy capital before we switched to $1000 (one-time migration)
_OLD_CAPITAL_PER_STRATEGY = 1500


def _migrate_state_to_1000(state, strategy_names):
    """
    One-time migration: convert state from $1500/strategy to $1000/strategy.
    Preserves PnL: new_capital = 1000 + (old_capital - 1500).
    Returns (state, True) if migration was done, (state, False) otherwise.
    """
    if state.get('_schema') == 'v4_1000':
        return state, False
    migrated = False
    for strategy_name in strategy_names:
        if strategy_name not in state:
            continue
        cap = state[strategy_name].get('capital', INITIAL_CAPITAL_PER_STRATEGY)
        # Only migrate if clearly old 1500-base (e.g. 1500 or 1470 after loss)
        if 1400 <= cap <= 1600:
            new_cap = 1000 + (cap - _OLD_CAPITAL_PER_STRATEGY)
            state[strategy_name]['capital'] = round(new_cap, 2)
            migrated = True
    if migrated:
        state['_schema'] = 'v4_1000'
    return state, migrated


def save_state(state):
    """Save trading state to file"""
    state['_last_updated'] = datetime.now().isoformat()
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2, default=str)


# =============================================================================
# EXCHANGE CONNECTION
# =============================================================================

def init_exchange():
    """Initialize exchange connection - public data only, no keys needed"""
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {
            'defaultType': 'future',
        }
    })

    return exchange


# =============================================================================
# MARKET DATA
# =============================================================================

def fetch_candles(exchange, symbol, timeframe, limit=500):
    """Fetch OHLCV candles"""
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        print(f"Error fetching candles: {e}")
        return None


def build_higher_timeframe(df, timeframe):
    """Build higher timeframe (4H or Daily) from lower timeframe data"""
    tmp = df.copy()
    tmp.set_index('timestamp', inplace=True)

    resampled = tmp.resample(timeframe).agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()

    return resampled.reset_index()


# =============================================================================
# POSITION MANAGEMENT
# =============================================================================

def calculate_position_size(capital, risk_pct, stop_loss_pct, current_price):
    """Calculate position size based on risk"""
    risk_amount = capital * risk_pct
    position_value = risk_amount / stop_loss_pct
    position_size = position_value / current_price
    return position_size


def open_position(state, strategy_name, signal, current_price, config):
    """Open new position"""
    strategy_state = state[strategy_name]

    # Check if already in position
    if len(strategy_state['positions']) > 0:
        return  # Already have a position

    # Calculate position size (with leverage multiplier)
    position_size = calculate_position_size(
        strategy_state['capital'],
        config['risk_per_trade'],
        config['stop_loss_pct'],
        current_price
    ) * config.get('leverage', 1)

    # Calculate stops
    if signal == 1:  # LONG
        entry_price = current_price
        stop_loss = entry_price * (1 - config['stop_loss_pct'])
        take_profit = entry_price * (1 + config['take_profit_pct'])
        side = 'LONG'
    else:  # SHORT
        entry_price = current_price
        stop_loss = entry_price * (1 + config['stop_loss_pct'])
        take_profit = entry_price * (1 - config['take_profit_pct'])
        side = 'SHORT'

    # Create position
    position = {
        'entry_time': datetime.now().isoformat(),
        'entry_price': entry_price,
        'size': position_size,
        'side': side,
        'stop_loss': stop_loss,
        'take_profit': take_profit,
        'status': 'open'
    }

    strategy_state['positions'].append(position)

    p = fmt_price(entry_price)
    sl = fmt_price(stop_loss)
    tp = fmt_price(take_profit)
    sz = fmt_size(position_size, entry_price)
    log_message(f"🟢 {strategy_name} | {side} {sz} @ {p} | SL: {sl} | TP: {tp}")

    # Send Telegram alert
    alert_msg = f"🟢 <b>POSITION OPENED</b>\n\n"
    alert_msg += f"<b>Strategy:</b> {strategy_name}\n"
    alert_msg += f"<b>Direction:</b> {side}\n"
    alert_msg += f"<b>Entry:</b> {p}\n"
    alert_msg += f"<b>Size:</b> {sz}\n"
    alert_msg += f"<b>Stop Loss:</b> {sl}\n"
    alert_msg += f"<b>Take Profit:</b> {tp}"
    send_telegram_alert(alert_msg)

    return position


def check_exit_conditions(position, current_price, current_time, time_stop_hours=48):
    """Check if position should be closed - exits at ACTUAL market price"""
    entry_time = datetime.fromisoformat(position['entry_time'])
    hours_in_trade = (current_time - entry_time).total_seconds() / 3600

    if position['side'] == 'LONG':
        # Check stop loss
        if current_price <= position['stop_loss']:
            return 'stop_loss', current_price

        # Check take profit
        if current_price >= position['take_profit']:
            return 'take_profit', current_price

    else:  # SHORT
        # Check stop loss
        if current_price >= position['stop_loss']:
            return 'stop_loss', current_price

        # Check take profit
        if current_price <= position['take_profit']:
            return 'take_profit', current_price

    # Check time stop (None = disabled)
    if time_stop_hours is not None and hours_in_trade >= time_stop_hours:
        return 'time_stop', current_price

    return None, None


def close_position(state, strategy_name, position, exit_price, exit_reason):
    """Close position and update capital"""
    strategy_state = state[strategy_name]

    # Calculate PnL
    if position['side'] == 'LONG':
        pnl = (exit_price - position['entry_price']) * position['size']
    else:  # SHORT
        pnl = (position['entry_price'] - exit_price) * position['size']

    pnl_pct = (pnl / strategy_state['capital']) * 100

    # Update capital
    strategy_state['capital'] += pnl

    # Record trade
    trade = {
        'entry_time': position['entry_time'],
        'exit_time': datetime.now().isoformat(),
        'side': position['side'],
        'entry_price': position['entry_price'],
        'exit_price': exit_price,
        'size': position['size'],
        'pnl': pnl,
        'pnl_pct': pnl_pct,
        'exit_reason': exit_reason
    }

    strategy_state['closed_trades'].append(trade)
    strategy_state['positions'].remove(position)

    emoji = "✅" if pnl > 0 else "❌"
    ep = fmt_price(position['entry_price'])
    xp = fmt_price(exit_price)
    log_message(f"{emoji} {strategy_name} | CLOSED {position['side']} | {ep} → {xp} | PnL: ${pnl:.2f} ({pnl_pct:+.2f}%) | Reason: {exit_reason} | Capital: ${strategy_state['capital']:.2f}")

    # Send Telegram alert
    result_emoji = "✅" if pnl > 0 else "❌"
    alert_msg = f"{result_emoji} <b>POSITION CLOSED</b>\n\n"
    alert_msg += f"<b>Strategy:</b> {strategy_name}\n"
    alert_msg += f"<b>Direction:</b> {position['side']}\n"
    alert_msg += f"<b>Entry:</b> {ep}\n"
    alert_msg += f"<b>Exit:</b> {xp}\n"
    alert_msg += f"<b>PnL:</b> ${pnl:+,.2f} ({pnl_pct:+.2f}%)\n"
    alert_msg += f"<b>Reason:</b> {exit_reason}\n"
    alert_msg += f"<b>New Capital:</b> ${strategy_state['capital']:,.2f}"
    send_telegram_alert(alert_msg)

    return trade


# =============================================================================
# LOGGING & ALERTS
# =============================================================================

def log_message(message):
    """Print log with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def send_telegram_alert(message):
    """Send Telegram alert (if enabled)"""
    if not TELEGRAM_ENABLED:
        return

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log_message("WARNING: Telegram enabled but token/chat_id not set")
        return

    try:
        import requests
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, data=data, timeout=10)
        if response.status_code != 200:
            log_message(f"Telegram error: {response.status_code} - {response.text}")
    except Exception as e:
        log_message(f"Telegram send failed: {e}")


# =============================================================================
# MAIN TRADING LOOP
# =============================================================================

def run_trading_bot():
    """Main trading loop - auto-discovers strategies from strategies/ folder"""

    # Auto-discover strategies
    all_strategies = discover_strategies()
    enabled_strategies = {k: v for k, v in all_strategies.items() if v.enabled}

    strategy_names = list(enabled_strategies.keys())
    num_strategies = len(enabled_strategies)
    total_capital = num_strategies * INITIAL_CAPITAL_PER_STRATEGY

    log_message("=" * 70)
    log_message(f"DRYRUN Paper Trading Bot v5.0 - STARTED")
    log_message(f"Auto-discovered {num_strategies} strategies: {', '.join(strategy_names)}")
    log_message(f"Capital: ${INITIAL_CAPITAL_PER_STRATEGY}/strategy (${total_capital} total)")
    log_message(f"Telegram: {'ENABLED' if TELEGRAM_ENABLED else 'DISABLED'}")
    log_message("=" * 70)

    # Send startup notification
    if TELEGRAM_ENABLED:
        strat_list = ', '.join(strategy_names)
        send_telegram_alert(
            f"🤖 <b>DRYRUN Bot v5.0 Started</b>\n\n"
            f"✅ Plugin architecture\n"
            f"✅ {num_strategies} strategies loaded\n\n"
            f"Strategies: {strat_list}\n"
            f"Capital: ${INITIAL_CAPITAL_PER_STRATEGY}/strategy (${total_capital} total)"
        )

    # Initialize
    exchange = init_exchange()
    state = load_state()

    # Ensure state entries exist for all discovered strategies
    for name, strategy in enabled_strategies.items():
        if name not in state:
            state[name] = {
                'capital': strategy.capital,
                'positions': [],
                'closed_trades': []
            }

    # One-time migration (backward compatible)
    state, migrated = _migrate_state_to_1000(state, strategy_names)
    if migrated:
        save_state(state)
        log_message("Migrated state from $1500 to $1000 per strategy (PnL preserved)")

    # === STARTUP CHECK: Close any positions that are past SL/TP ===
    log_message("Checking for stale positions past SL/TP...")
    current_time = datetime.now()
    for strategy_name, strategy in enabled_strategies.items():
        if strategy_name not in state:
            continue
        strategy_state = state[strategy_name]
        if len(strategy_state['positions']) > 0:
            try:
                df = fetch_candles(exchange, strategy.symbol, strategy.timeframe, limit=5)
                if df is not None:
                    current_price = df['close'].iloc[-1]
                    for position in strategy_state['positions'][:]:
                        exit_reason, exit_price = check_exit_conditions(
                            position, current_price, current_time,
                            time_stop_hours=strategy.time_stop_hours
                        )
                        if exit_reason:
                            log_message(f"⚠️ STARTUP: Closing stale {strategy_name} position ({exit_reason})")
                            close_position(state, strategy_name, position, exit_price, exit_reason)
                            save_state(state)
            except Exception as e:
                log_message(f"Startup check error for {strategy_name}: {e}")

    # Main loop
    while True:
        try:
            current_time = datetime.now()

            for strategy_name, strategy in enabled_strategies.items():
                strategy_state = state[strategy_name]
                config = strategy.get_config_dict()

                # Fetch primary timeframe data
                df = fetch_candles(exchange, strategy.symbol, strategy.timeframe)
                if df is None:
                    continue

                # Build higher timeframes as needed
                h4_df = None
                daily_df = None

                if strategy.timeframe == '15m':
                    if strategy.needs_h4_filter:
                        h4_df = build_higher_timeframe(df, '4h')
                    if strategy.needs_daily_filter:
                        daily_df = build_higher_timeframe(df, '1D')
                elif strategy.timeframe == '4h':
                    if strategy.needs_daily_filter:
                        daily_df = build_higher_timeframe(df, '1D')
                # For '1d' strategies: no higher TF needed

                current_price = df['close'].iloc[-1]

                # Check exits on open positions
                for position in strategy_state['positions'][:]:
                    exit_reason, exit_price = check_exit_conditions(
                        position, current_price, current_time,
                        time_stop_hours=strategy.time_stop_hours
                    )
                    if exit_reason:
                        close_position(state, strategy_name, position, exit_price, exit_reason)
                        save_state(state)

                # Check for new entry signals (only if no open position)
                if len(strategy_state['positions']) == 0:
                    signal = strategy.check_signal(df, h4_df, daily_df)

                    # Safety: enforce long_only at engine level
                    if strategy.long_only and signal == -1:
                        signal = 0

                    if signal != 0:
                        open_position(state, strategy_name, signal, current_price, config)
                        save_state(state)

            # Print status every 15 minutes
            if current_time.minute % 15 == 0:
                total = sum(state[s]['capital'] for s in enabled_strategies if s in state)
                log_message(f"Status | {num_strategies} strategies | Total: ${total:.0f}")

            time.sleep(60)

        except KeyboardInterrupt:
            log_message("Bot stopped by user")
            break
        except Exception as e:
            log_message(f"Error: {e}")
            time.sleep(60)


# =============================================================================
# PERFORMANCE REPORT
# =============================================================================

def generate_performance_report():
    """Generate performance report from state file"""
    all_strategies = discover_strategies()
    state = load_state()
    state, _ = _migrate_state_to_1000(state, list(all_strategies.keys()))

    print("\n" + "=" * 70)
    print("PERFORMANCE REPORT")
    print("=" * 70)

    total_initial = 0
    total_current = 0

    for strategy_name, strategy in all_strategies.items():
        if strategy_name not in state:
            continue

        strategy_state = state[strategy_name]
        initial = INITIAL_CAPITAL_PER_STRATEGY
        current = strategy_state['capital']
        trades = strategy_state['closed_trades']

        total_initial += initial
        total_current += current

        if len(trades) > 0:
            winning_trades = [t for t in trades if t['pnl'] > 0]
            win_rate = (len(winning_trades) / len(trades)) * 100
            total_pnl = sum(t['pnl'] for t in trades)
            return_pct = ((current - initial) / initial) * 100
        else:
            win_rate = 0
            total_pnl = 0
            return_pct = 0

        print(f"\n{strategy_name}:")
        print(f"  Initial Capital: ${initial:.2f}")
        print(f"  Current Capital: ${current:.2f}")
        print(f"  Return: {return_pct:+.2f}%")
        print(f"  Total Trades: {len(trades)}")
        print(f"  Win Rate: {win_rate:.1f}%")
        print(f"  Total PnL: ${total_pnl:+.2f}")

    if total_initial > 0:
        total_return = ((total_current - total_initial) / total_initial) * 100
    else:
        total_return = 0

    print(f"\nPORTFOLIO:")
    print(f"  Initial: ${total_initial:.2f}")
    print(f"  Current: ${total_current:.2f}")
    print(f"  Return: {total_return:+.2f}%")
    print("=" * 70 + "\n")


PIDFILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'paper_trader.pid')


def acquire_lock():
    """Ensure only one instance runs. Kill stale process if needed."""
    if os.path.exists(PIDFILE):
        try:
            old_pid = int(open(PIDFILE).read().strip())
            os.kill(old_pid, 0)  # Check if alive
            # Old process is alive — kill it
            log_message(f"Killing old instance (PID {old_pid})")
            os.kill(old_pid, signal.SIGTERM)
            time.sleep(2)
        except (ProcessLookupError, ValueError):
            pass  # Stale PID file, safe to overwrite

    with open(PIDFILE, 'w') as f:
        f.write(str(os.getpid()))

    atexit.register(release_lock)


def release_lock():
    """Remove PID file on exit."""
    try:
        if os.path.exists(PIDFILE) and int(open(PIDFILE).read().strip()) == os.getpid():
            os.remove(PIDFILE)
    except Exception:
        pass


if __name__ == "__main__":
    acquire_lock()
    run_trading_bot()

    # Or generate report
    generate_performance_report()
