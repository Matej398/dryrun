"""
DRYRUN Paper Trading Bot - UPDATED v4.0
Based on 3-year backtest validation (Feb 2026)

CHANGES FROM v3:
- REMOVED: BNB Stochastic (failed 3-year backtest, -100% return)
- KEPT: BTC RSI + H4 (long-only), ETH CCI + H4 + Daily
- Capital allocation: $1500 per strategy (was $1000)
- NO time filters (made performance worse in backtest)

VALIDATED STRATEGIES:
1. BTC RSI + H4 (long-only): +40.6% / 3 years, 52.5% WR
2. ETH CCI + H4 + Daily: +498.4% / 3 years, 70% WR
"""

import ccxt
import pandas as pd
import time
from datetime import datetime
import json
from ta.momentum import RSIIndicator
from ta.trend import CCIIndicator

# =============================================================================
# CONFIGURATION
# =============================================================================

# Exchange setup (paper trading on Binance testnet)
EXCHANGE = 'binance'
API_KEY = 'your_testnet_api_key'
API_SECRET = 'your_testnet_api_secret'

# Capital allocation (per strategy)
INITIAL_CAPITAL_PER_STRATEGY = 1500  # $1500 each

# Strategy configurations
STRATEGIES = {
    'BTC_RSI': {
        'symbol': 'BTC/USDT',
        'timeframe': '15m',
        'enabled': True,
        'capital': INITIAL_CAPITAL_PER_STRATEGY,
        'risk_per_trade': 0.02,
        'stop_loss_pct': 0.01,
        'take_profit_pct': 0.02,
        'time_stop_hours': 48,
        'use_h4_filter': True,
        'long_only': True,
        'indicator': 'rsi',
        'rsi_oversold': 30,
        'rsi_overbought': 70
    },
    'ETH_CCI': {
        'symbol': 'ETH/USDT',
        'timeframe': '15m',
        'enabled': True,
        'capital': INITIAL_CAPITAL_PER_STRATEGY,
        'risk_per_trade': 0.02,
        'stop_loss_pct': 0.01,
        'take_profit_pct': 0.02,
        'time_stop_hours': 48,
        'use_h4_filter': True,
        'use_daily_filter': True,
        'indicator': 'cci',
        'cci_oversold': -100,
        'cci_overbought': 100
    },
    'SOL_CCI': {
        'symbol': 'SOL/USDT',
        'timeframe': '15m',
        'enabled': True,
        'capital': INITIAL_CAPITAL_PER_STRATEGY,
        'risk_per_trade': 0.02,
        'stop_loss_pct': 0.01,
        'take_profit_pct': 0.02,
        'time_stop_hours': 48,
        'use_h4_filter': True,
        'use_daily_filter': True,
        'indicator': 'cci',
        'cci_oversold': -100,
        'cci_overbought': 100
    }
}

# State file for persistence
STATE_FILE = 'paper_trading_state.json'

# Telegram alerts (optional)
TELEGRAM_ENABLED = False
TELEGRAM_BOT_TOKEN = 'your_bot_token'
TELEGRAM_CHAT_ID = 'your_chat_id'


# =============================================================================
# STATE MANAGEMENT
# =============================================================================

def load_state():
    """Load trading state from file"""
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            'BTC_RSI': {
                'capital': INITIAL_CAPITAL_PER_STRATEGY,
                'positions': [],
                'closed_trades': []
            },
            'ETH_CCI': {
                'capital': INITIAL_CAPITAL_PER_STRATEGY,
                'positions': [],
                'closed_trades': []
            },
            'SOL_CCI': {
                'capital': INITIAL_CAPITAL_PER_STRATEGY,
                'positions': [],
                'closed_trades': []
            }
        }


def save_state(state):
    """Save trading state to file"""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2, default=str)


# =============================================================================
# EXCHANGE CONNECTION
# =============================================================================

def init_exchange():
    """Initialize exchange connection"""
    exchange = ccxt.binance({
        'apiKey': API_KEY,
        'secret': API_SECRET,
        'enableRateLimit': True,
        'options': {
            'defaultType': 'future',  # or 'spot'
        }
    })
    
    # For testnet
    exchange.set_sandbox_mode(True)
    
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


def build_higher_timeframe(df_15m, timeframe):
    """Build 4H or Daily from 15m data"""
    df = df_15m.copy()
    df.set_index('timestamp', inplace=True)
    
    resampled = df.resample(timeframe).agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    return resampled.reset_index()


# =============================================================================
# FILTERS
# =============================================================================

def get_h4_filter(h4_df):
    """H4 permission filter"""
    if len(h4_df) == 0:
        return 0
    
    latest = h4_df.iloc[-1]
    
    if latest['close'] > latest['open']:
        return 1  # Bullish - longs allowed
    elif latest['close'] < latest['open']:
        return -1  # Bearish - shorts allowed
    return 0  # Doji - neutral


def get_daily_filter(daily_df):
    """Daily permission filter"""
    if len(daily_df) == 0:
        return 0
    
    latest = daily_df.iloc[-1]
    
    if latest['close'] > latest['open']:
        return 1  # Bullish - longs allowed
    elif latest['close'] < latest['open']:
        return -1  # Bearish - shorts allowed
    return 0  # Doji - neutral


# =============================================================================
# STRATEGY LOGIC
# =============================================================================

def check_btc_rsi_signal(df_15m, h4_df, config):
    """
    BTC RSI Extreme Strategy (LONG-ONLY)
    
    Entry:
    - RSI crosses above 30 (oversold bounce)
    - H4 filter: Only if H4 is bullish (or neutral)
    
    Exit:
    - Stop loss: -1%
    - Take profit: +2%
    - Time stop: 48 hours
    """
    if len(df_15m) < 20:
        return 0
    
    # Calculate RSI
    rsi = RSIIndicator(df_15m['close'], window=14).rsi()
    current_rsi = rsi.iloc[-1]
    prev_rsi = rsi.iloc[-2]
    
    # Check H4 filter
    if config['use_h4_filter']:
        h4_direction = get_h4_filter(h4_df)
        if h4_direction < 0:  # Bearish H4
            return 0  # Block longs when H4 bearish
    
    # Long signal: RSI crosses above 30
    if current_rsi > config['rsi_oversold'] and prev_rsi <= config['rsi_oversold']:
        return 1  # LONG signal
    
    # No short signals (long-only mode)
    return 0


def check_eth_cci_signal(df_15m, h4_df, daily_df, config):
    """
    ETH CCI Extreme Strategy
    
    Entry:
    - CCI crosses above -100 (oversold) → LONG
    - CCI crosses below +100 (overbought) → SHORT
    - H4 + Daily filters: Both must align with direction
    
    Exit:
    - Stop loss: -1%
    - Take profit: +2%
    - Time stop: 48 hours
    """
    if len(df_15m) < 25:
        return 0
    
    # Calculate CCI
    cci = CCIIndicator(df_15m['high'], df_15m['low'], df_15m['close'], window=20).cci()
    current_cci = cci.iloc[-1]
    prev_cci = cci.iloc[-2]
    
    # Check H4 filter
    if config['use_h4_filter']:
        h4_direction = get_h4_filter(h4_df)
    else:
        h4_direction = 0
    
    # Check Daily filter
    if config['use_daily_filter']:
        daily_direction = get_daily_filter(daily_df)
    else:
        daily_direction = 0
    
    # Long signal: CCI crosses above -100
    if current_cci > config['cci_oversold'] and prev_cci <= config['cci_oversold']:
        # Check filters allow longs
        if (not config['use_h4_filter'] or h4_direction >= 0) and \
           (not config['use_daily_filter'] or daily_direction >= 0):
            return 1  # LONG signal
    
    # Short signal: CCI crosses below +100
    if current_cci < config['cci_overbought'] and prev_cci >= config['cci_overbought']:
        # Check filters allow shorts
        if (not config['use_h4_filter'] or h4_direction <= 0) and \
           (not config['use_daily_filter'] or daily_direction <= 0):
            return -1  # SHORT signal
    
    return 0


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
    
    # Calculate position size
    position_size = calculate_position_size(
        strategy_state['capital'],
        config['risk_per_trade'],
        config['stop_loss_pct'],
        current_price
    )
    
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
    
    log_message(f"🟢 {strategy_name} | {side} {position_size:.4f} @ ${entry_price:.2f} | SL: ${stop_loss:.2f} | TP: ${take_profit:.2f}")
    
    return position


def check_exit_conditions(position, current_price, current_time):
    """Check if position should be closed"""
    entry_time = datetime.fromisoformat(position['entry_time'])
    hours_in_trade = (current_time - entry_time).total_seconds() / 3600
    
    if position['side'] == 'LONG':
        # Check stop loss
        if current_price <= position['stop_loss']:
            return 'stop_loss', position['stop_loss']
        
        # Check take profit
        if current_price >= position['take_profit']:
            return 'take_profit', position['take_profit']
    
    else:  # SHORT
        # Check stop loss
        if current_price >= position['stop_loss']:
            return 'stop_loss', position['stop_loss']
        
        # Check take profit
        if current_price <= position['take_profit']:
            return 'take_profit', position['take_profit']
    
    # Check time stop
    if hours_in_trade >= 48:
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
    log_message(f"{emoji} {strategy_name} | CLOSED {position['side']} | PnL: ${pnl:.2f} ({pnl_pct:+.2f}%) | Reason: {exit_reason} | Capital: ${strategy_state['capital']:.2f}")
    
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
    
    # TODO: Implement Telegram bot integration
    pass


# =============================================================================
# MAIN TRADING LOOP
# =============================================================================

def run_trading_bot():
    """Main trading loop"""
    log_message("="*70)
    log_message("DRYRUN Paper Trading Bot v4.0 - STARTED")
    log_message("Strategies: BTC RSI (long-only), ETH CCI (H4+Daily), SOL CCI (H4+Daily)")
    log_message("Capital: $1500 per strategy")
    log_message("="*70)
    
    # Initialize
    exchange = init_exchange()
    state = load_state()
    
    # Main loop
    while True:
        try:
            current_time = datetime.now()
            
            # Process each strategy
            for strategy_name, config in STRATEGIES.items():
                if not config['enabled']:
                    continue
                
                # Fetch market data
                df_15m = fetch_candles(exchange, config['symbol'], config['timeframe'])
                if df_15m is None:
                    continue
                
                df_4h = build_higher_timeframe(df_15m, '4h')
                df_daily = build_higher_timeframe(df_15m, '1D')
                
                current_price = df_15m['close'].iloc[-1]
                
                # Check open positions
                strategy_state = state[strategy_name]
                for position in strategy_state['positions'][:]:  # Copy list to allow removal
                    exit_reason, exit_price = check_exit_conditions(position, current_price, current_time)
                    if exit_reason:
                        close_position(state, strategy_name, position, exit_price, exit_reason)
                        save_state(state)
                
                # Check for new signals (only if no open position)
                if len(strategy_state['positions']) == 0:
                    if strategy_name == 'BTC_RSI':
                        signal = check_btc_rsi_signal(df_15m, df_4h, config)
                    elif strategy_name in ['ETH_CCI', 'SOL_CCI']:
                        signal = check_eth_cci_signal(df_15m, df_4h, df_daily, config)
                    else:
                        signal = 0
                    
                    if signal != 0:
                        open_position(state, strategy_name, signal, current_price, config)
                        save_state(state)
            
            # Print status
            if current_time.minute % 15 == 0:  # Every 15 minutes
                total = state['BTC_RSI']['capital'] + state['ETH_CCI']['capital'] + state['SOL_CCI']['capital']
                log_message(f"Status | BTC: ${state['BTC_RSI']['capital']:.2f} | ETH: ${state['ETH_CCI']['capital']:.2f} | SOL: ${state['SOL_CCI']['capital']:.2f} | Total: ${total:.2f}")
            
            # Sleep until next check (check every 1 minute)
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
    state = load_state()
    
    print("\n" + "="*70)
    print("PERFORMANCE REPORT")
    print("="*70)
    
    total_initial = 0
    total_current = 0
    
    for strategy_name in ['BTC_RSI', 'ETH_CCI', 'SOL_CCI']:
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
    
    total_return = ((total_current - total_initial) / total_initial) * 100
    
    print(f"\nPORTFOLIO:")
    print(f"  Initial: ${total_initial:.2f}")
    print(f"  Current: ${total_current:.2f}")
    print(f"  Return: {total_return:+.2f}%")
    print("="*70 + "\n")


if __name__ == "__main__":
    # Uncomment to run bot
    run_trading_bot()
    
    # Or generate report
    generate_performance_report()
