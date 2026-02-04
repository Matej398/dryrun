#!/usr/bin/env python3
"""
DRYRUN v3.1 - Multi-Strategy Paper Trading Bot
Updated: Jan 23, 2026

Strategies:
  1. BTC RSI Extreme + H4 filter (LONG-ONLY - shorts lose money!)
  2. BNB Stochastic (no filter) - both directions
  3. ETH CCI Extreme + H4 + Daily filter - both directions
"""
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import json
import os

# =============================================================================
# STRATEGY CONFIGURATIONS
# =============================================================================

STRATEGIES = {
    'BTCUSDT': {
        'name': 'BTC RSI Extreme',
        'trigger': 'rsi',
        'use_h4_filter': True,
        'use_daily_filter': False,
        'long_only': True,  # NEW: Skip shorts (regime filter finding)
        'rsi_oversold': 30,
        'rsi_overbought': 70,
    },
    'BNBUSDT': {
        'name': 'BNB Stochastic',
        'trigger': 'stochastic',
        'use_h4_filter': False,
        'use_daily_filter': False,
        'long_only': False,  # Both directions OK
        'stoch_oversold': 20,
        'stoch_overbought': 80,
    },
    'ETHUSDT': {
        'name': 'ETH CCI Extreme',
        'trigger': 'cci',
        'use_h4_filter': True,
        'use_daily_filter': True,  # CRITICAL: Daily filter required!
        'long_only': False,  # Both directions OK
        'cci_oversold': -100,
        'cci_overbought': 100,
    },
}

CONFIG = {
    'starting_balance': 1000,  # Per strategy
    'risk_per_trade': 0.02,
    'stop_loss_pct': 0.01,
    'take_profit_pct': 0.02,
    'max_positions_per_strategy': 1,
    'check_interval': 60,
}

STATE_FILE = "paper_state_v3.json"
TRADES_FILE = "paper_trades_v3.json"
LOG_FILE = "paper_log_v3.txt"

# =============================================================================
# LOGGING
# =============================================================================

def log(message):
    """Log to file and console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    with open(LOG_FILE, 'a') as f:
        f.write(log_line + "\n")

# =============================================================================
# DATA FETCHING
# =============================================================================

def get_klines(symbol, interval, limit=100):
    """Fetch recent klines from Binance"""
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        
        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    except Exception as e:
        log(f"Error fetching {symbol} {interval}: {e}")
        return None

def get_current_price(symbol):
    """Get current price"""
    url = "https://api.binance.com/api/v3/ticker/price"
    params = {"symbol": symbol}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        return float(response.json()['price'])
    except:
        return None

# =============================================================================
# INDICATORS
# =============================================================================

def add_rsi(df, period=14):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    return df

def add_stochastic(df, k_period=14, d_period=3):
    low_min = df['low'].rolling(window=k_period).min()
    high_max = df['high'].rolling(window=k_period).max()
    df['stoch_k'] = 100 * (df['close'] - low_min) / (high_max - low_min)
    df['stoch_d'] = df['stoch_k'].rolling(window=d_period).mean()
    return df

def add_cci(df, period=20):
    tp = (df['high'] + df['low'] + df['close']) / 3
    sma = tp.rolling(window=period).mean()
    mad = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())
    df['cci'] = (tp - sma) / (0.015 * mad)
    return df

# =============================================================================
# BIAS FILTERS
# =============================================================================

def get_h4_bias(h4_df):
    """Get H4 bias from last closed candle"""
    if h4_df is None or len(h4_df) < 2:
        return 'neutral'
    
    candle = h4_df.iloc[-2]  # Last CLOSED candle
    body = abs(candle['close'] - candle['open'])
    total_range = candle['high'] - candle['low']
    
    if total_range == 0 or body / total_range < 0.3:
        return 'neutral'
    
    return 'bullish' if candle['close'] > candle['open'] else 'bearish'


def get_daily_bias(daily_df):
    """Get Daily bias - checks for EXPANDING candle"""
    if daily_df is None or len(daily_df) < 3:
        return 'neutral'
    
    candle = daily_df.iloc[-2]  # Last CLOSED candle
    prev_candle = daily_df.iloc[-3]
    
    body = abs(candle['close'] - candle['open'])
    prev_body = abs(prev_candle['close'] - prev_candle['open'])
    total_range = candle['high'] - candle['low']
    
    if total_range == 0:
        return 'neutral'
    
    body_ratio = body / total_range
    body_pct = body / candle['open']
    
    # EXPANDING criteria
    if body_ratio < 0.5 or body_pct < 0.005:
        return 'neutral'
    
    if body < prev_body * 0.8:
        return 'neutral'
    
    return 'bullish' if candle['close'] > candle['open'] else 'bearish'

# =============================================================================
# STATE MANAGEMENT
# =============================================================================

def load_state():
    """Load or initialize state"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    
    # Initialize fresh state
    state = {'strategies': {}}
    for symbol in STRATEGIES:
        state['strategies'][symbol] = {
            'balance': CONFIG['starting_balance'],
            'position': None,
            'total_trades': 0,
            'wins': 0,
            'losses': 0
        }
    save_state(state)
    return state

def save_state(state):
    """Save state to file"""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2, default=str)

def save_trade(trade):
    """Append trade to trades file"""
    trades = []
    if os.path.exists(TRADES_FILE):
        with open(TRADES_FILE, 'r') as f:
            trades = json.load(f)
    trades.append(trade)
    with open(TRADES_FILE, 'w') as f:
        json.dump(trades, f, indent=2, default=str)

# =============================================================================
# SIGNAL GENERATION
# =============================================================================

def check_signal(symbol, config, m15_df, h4_df, daily_df):
    """Check for entry signal"""
    
    # Add indicators
    if config['trigger'] == 'rsi':
        m15_df = add_rsi(m15_df)
        prev_val = m15_df['rsi'].iloc[-2]
        curr_val = m15_df['rsi'].iloc[-1]
        if pd.isna(prev_val) or pd.isna(curr_val):
            return None
        long_signal = prev_val < config['rsi_oversold'] and curr_val > config['rsi_oversold']
        short_signal = prev_val > config['rsi_overbought'] and curr_val < config['rsi_overbought']
        
    elif config['trigger'] == 'stochastic':
        m15_df = add_stochastic(m15_df)
        prev_val = m15_df['stoch_k'].iloc[-2]
        curr_val = m15_df['stoch_k'].iloc[-1]
        if pd.isna(prev_val) or pd.isna(curr_val):
            return None
        long_signal = prev_val < config['stoch_oversold'] and curr_val > config['stoch_oversold']
        short_signal = prev_val > config['stoch_overbought'] and curr_val < config['stoch_overbought']
        
    elif config['trigger'] == 'cci':
        m15_df = add_cci(m15_df)
        prev_val = m15_df['cci'].iloc[-2]
        curr_val = m15_df['cci'].iloc[-1]
        if pd.isna(prev_val) or pd.isna(curr_val):
            return None
        long_signal = prev_val < config['cci_oversold'] and curr_val > config['cci_oversold']
        short_signal = prev_val > config['cci_overbought'] and curr_val < config['cci_overbought']
    else:
        return None
    
    # Get biases
    h4_bias = get_h4_bias(h4_df) if config['use_h4_filter'] else 'any'
    daily_bias = get_daily_bias(daily_df) if config['use_daily_filter'] else 'any'
    
    # Skip if neutral when filter is active
    if config['use_h4_filter'] and h4_bias == 'neutral':
        return None
    if config['use_daily_filter'] and daily_bias == 'neutral':
        return None
    
    # Check alignment if both filters active
    if config['use_h4_filter'] and config['use_daily_filter']:
        if h4_bias != daily_bias:
            return None
    
    # Determine allowed direction
    if config['use_daily_filter']:
        allowed_direction = daily_bias
    elif config['use_h4_filter']:
        allowed_direction = h4_bias
    else:
        allowed_direction = 'any'
    
    # Check for LONG signal
    if long_signal and (allowed_direction in ['bullish', 'any']):
        return {
            'direction': 'long',
            'h4_bias': h4_bias,
            'daily_bias': daily_bias
        }
    
    # Check for SHORT signal (skip if long_only mode)
    if short_signal and (allowed_direction in ['bearish', 'any']):
        if config.get('long_only', False):
            log(f"  {symbol}: Short signal SKIPPED (long-only mode)")
            return None
        return {
            'direction': 'short',
            'h4_bias': h4_bias,
            'daily_bias': daily_bias
        }
    
    return None

# =============================================================================
# POSITION MANAGEMENT
# =============================================================================

def check_positions(state):
    """Check all open positions for exit"""
    
    for symbol, config in STRATEGIES.items():
        strategy_state = state['strategies'][symbol]
        position = strategy_state['position']
        
        if position is None:
            continue
        
        current_price = get_current_price(symbol)
        if current_price is None:
            continue
        
        direction = position['direction']
        exit_reason = None
        exit_price = None
        
        # Check stop loss
        if direction == 'long' and current_price <= position['stop_price']:
            exit_reason = 'stop_loss'
            exit_price = position['stop_price']
        elif direction == 'short' and current_price >= position['stop_price']:
            exit_reason = 'stop_loss'
            exit_price = position['stop_price']
        
        # Check take profit
        if direction == 'long' and current_price >= position['target_price']:
            exit_reason = 'take_profit'
            exit_price = position['target_price']
        elif direction == 'short' and current_price <= position['target_price']:
            exit_reason = 'take_profit'
            exit_price = position['target_price']
        
        # Execute exit
        if exit_reason:
            # Calculate PnL
            if direction == 'long':
                pnl = (exit_price - position['entry_price']) / position['entry_price'] * position['size']
            else:
                pnl = (position['entry_price'] - exit_price) / position['entry_price'] * position['size']
            
            # Update state
            strategy_state['balance'] += pnl
            strategy_state['total_trades'] += 1
            if exit_reason == 'take_profit':
                strategy_state['wins'] += 1
            else:
                strategy_state['losses'] += 1
            
            # Log and save trade
            log(f"  {symbol}: {direction.upper()} closed @ {exit_price:.2f} | {exit_reason} | PnL: ${pnl:.2f}")
            
            trade = {
                'symbol': symbol,
                'direction': direction,
                'entry_price': position['entry_price'],
                'entry_time': position['entry_time'],
                'exit_price': exit_price,
                'exit_time': datetime.now().isoformat(),
                'exit_reason': exit_reason,
                'pnl': pnl,
                'balance_after': strategy_state['balance']
            }
            save_trade(trade)
            
            # Clear position
            strategy_state['position'] = None
    
    save_state(state)
    return state

def check_entries(state):
    """Check for new entry signals"""
    
    for symbol, config in STRATEGIES.items():
        strategy_state = state['strategies'][symbol]
        
        # Skip if already in position
        if strategy_state['position'] is not None:
            continue
        
        # Fetch data
        m15_df = get_klines(symbol, '15m', 100)
        h4_df = get_klines(symbol, '4h', 50) if config['use_h4_filter'] else None
        daily_df = get_klines(symbol, '1d', 20) if config['use_daily_filter'] else None
        
        if m15_df is None:
            continue
        
        # Check for signal
        signal = check_signal(symbol, config, m15_df, h4_df, daily_df)
        
        if signal is None:
            continue
        
        # Get entry price
        entry_price = get_current_price(symbol)
        if entry_price is None:
            continue
        
        # Calculate position
        balance = strategy_state['balance']
        stop_pct = CONFIG['stop_loss_pct']
        target_pct = CONFIG['take_profit_pct']
        risk_per_trade = CONFIG['risk_per_trade']
        
        if signal['direction'] == 'long':
            stop_price = entry_price * (1 - stop_pct)
            target_price = entry_price * (1 + target_pct)
        else:
            stop_price = entry_price * (1 + stop_pct)
            target_price = entry_price * (1 - target_pct)
        
        position_size = balance * risk_per_trade / stop_pct
        
        # Enter position
        strategy_state['position'] = {
            'direction': signal['direction'],
            'entry_price': entry_price,
            'entry_time': datetime.now().isoformat(),
            'stop_price': stop_price,
            'target_price': target_price,
            'size': position_size,
            'filters': {
                'h4_bias': signal['h4_bias'],
                'daily_bias': signal['daily_bias']
            }
        }
        
        filters = []
        if config['use_h4_filter']:
            filters.append(f"H4={signal['h4_bias']}")
        if config['use_daily_filter']:
            filters.append(f"Daily={signal['daily_bias']}")
        filter_str = ", ".join(filters) if filters else "None"
        
        log(f"  {symbol}: {signal['direction'].upper()} @ {entry_price:.2f} | SL: {stop_price:.2f} | TP: {target_price:.2f} | Filters: {filter_str}")
    
    save_state(state)
    return state

# =============================================================================
# STATUS DISPLAY
# =============================================================================

def print_status(state):
    """Print current status"""
    print("\n" + "="*70)
    print(f"DRYRUN v3.1 Status - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    total_balance = 0
    total_starting = 0
    
    for symbol, config in STRATEGIES.items():
        strategy_state = state['strategies'][symbol]
        balance = strategy_state['balance']
        position = strategy_state['position']
        total_trades = strategy_state['total_trades']
        wins = strategy_state['wins']
        
        total_balance += balance
        total_starting += CONFIG['starting_balance']
        
        pnl_pct = (balance - CONFIG['starting_balance']) / CONFIG['starting_balance'] * 100
        wr = (wins / total_trades * 100) if total_trades > 0 else 0
        
        # Position status
        if position:
            current_price = get_current_price(symbol)
            if current_price:
                if position['direction'] == 'long':
                    unrealized = (current_price - position['entry_price']) / position['entry_price'] * 100
                else:
                    unrealized = (position['entry_price'] - current_price) / position['entry_price'] * 100
                pos_status = f"{position['direction'].upper()} @ {position['entry_price']:.2f} ({unrealized:+.2f}%)"
            else:
                pos_status = f"{position['direction'].upper()} @ {position['entry_price']:.2f}"
        else:
            pos_status = "FLAT"
        
        # Build filter string
        filters = []
        if config['use_h4_filter']:
            filters.append("H4")
        if config['use_daily_filter']:
            filters.append("Daily")
        if config.get('long_only', False):
            filters.append("LONG-ONLY")
        filter_str = "+".join(filters) if filters else "None"
        
        print(f"\n{symbol} ({config['name']}) [Filters: {filter_str}]")
        print(f"  Balance: ${balance:.2f} ({pnl_pct:+.1f}%) | Trades: {total_trades} | WR: {wr:.0f}%")
        print(f"  Position: {pos_status}")
    
    total_pnl = total_balance - total_starting
    total_pnl_pct = total_pnl / total_starting * 100
    
    print("\n" + "-"*70)
    print(f"TOTAL: ${total_balance:.2f} ({total_pnl_pct:+.1f}%)")
    print("="*70 + "\n")


def run_bot():
    """Main bot loop"""
    log("="*70)
    log("DRYRUN v3.1 - Multi-Strategy Bot Started")
    log("UPDATE: BTC RSI now LONG-ONLY (shorts were losing money)")
    for symbol, config in STRATEGIES.items():
        filters = []
        if config['use_h4_filter']:
            filters.append("H4")
        if config['use_daily_filter']:
            filters.append("Daily")
        if config.get('long_only', False):
            filters.append("LONG-ONLY")
        log(f"  {symbol}: {config['name']} | Filters: {'+'.join(filters) if filters else 'None'}")
    log("="*70)
    
    state = load_state()
    
    while True:
        try:
            state = check_positions(state)
            state = check_entries(state)
            print_status(state)
            log(f"Sleeping {CONFIG['check_interval']}s...")
            time.sleep(CONFIG['check_interval'])
        except KeyboardInterrupt:
            log("Bot stopped by user")
            break
        except Exception as e:
            log(f"Error: {e}")
            time.sleep(30)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'status':
            state = load_state()
            print_status(state)
        elif sys.argv[1] == 'reset':
            for f in [STATE_FILE, TRADES_FILE]:
                if os.path.exists(f):
                    os.remove(f)
            print("State reset")
        elif sys.argv[1] == 'reset-one' and len(sys.argv) > 2:
            symbol = sys.argv[2].upper()
            if symbol in STRATEGIES:
                state = load_state()
                state['strategies'][symbol] = {
                    'balance': CONFIG['starting_balance'],
                    'position': None,
                    'total_trades': 0,
                    'wins': 0,
                    'losses': 0
                }
                save_state(state)
                print(f"Reset {symbol} strategy")
            else:
                print(f"Unknown strategy: {symbol}")
        else:
            print("Usage: python paper_trader_v3.py [status|reset|reset-one <BTCUSDT|BNBUSDT|ETHUSDT>]")
    else:
        run_bot()
