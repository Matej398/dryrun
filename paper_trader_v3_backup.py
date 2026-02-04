"""
DRYRUN v2 - Live Paper Trading Bot
H4 Permission + RSI Extreme Entry Strategy
"""
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import json
import os
import ta

# =============================================================================
# CONFIGURATION
# =============================================================================

CONFIG = {
    'pairs': ['BTCUSDT'],
    'starting_balance': 1000,
    'risk_per_trade': 0.02,
    'stop_loss_pct': 0.01,
    'take_profit_pct': 0.02,
    'max_positions': 1,
    'entry_trigger': 'rsi_extreme',
    'check_interval': 60,
}

STATE_FILE = "paper_state.json"
TRADES_FILE = "paper_trades.json"
LOG_FILE = "paper_log.txt"


# =============================================================================
# DATA FETCHING
# =============================================================================

def get_klines(symbol, interval, limit=100):
    """Fetch recent klines from Binance"""
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }
    
    response = requests.get(url, params=params)
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


def add_indicators(df):
    """Add technical indicators"""
    df = df.copy()
    
    df['ema_21'] = ta.trend.ema_indicator(df['close'], window=21)
    df['ema_50'] = ta.trend.ema_indicator(df['close'], window=50)
    df['rsi'] = ta.momentum.rsi(df['close'], window=14)
    df['atr'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
    
    return df


# =============================================================================
# H4 BIAS LOGIC
# =============================================================================

def get_h4_bias(symbol):
    """Get current H4 bias for a symbol"""
    df = get_klines(symbol, "4h", 10)
    
    # Use the last CLOSED candle (second to last)
    candle = df.iloc[-2]
    
    body = abs(candle['close'] - candle['open'])
    total_range = candle['high'] - candle['low']
    
    if total_range == 0:
        return 'neutral', candle
    
    body_ratio = body / total_range
    
    # Indecision check
    if body_ratio < 0.3:
        return 'neutral', candle
    
    if candle['close'] > candle['open']:
        return 'bullish', candle
    else:
        return 'bearish', candle


# =============================================================================
# ENTRY TRIGGER - RSI EXTREME
# =============================================================================

def check_rsi_extreme(df):
    """
    RSI Extreme trigger
    Long: RSI was below 30, now crossing above
    Short: RSI was above 70, now crossing below
    """
    if len(df) < 2:
        return False, False
    
    row = df.iloc[-1]
    prev_rsi = df['rsi'].iloc[-2]
    
    long_signal = prev_rsi < 30 and row['rsi'] > 30
    short_signal = prev_rsi > 70 and row['rsi'] < 70
    
    return long_signal, short_signal


# =============================================================================
# STATE MANAGEMENT
# =============================================================================

def load_state():
    """Load paper trading state"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    
    return {
        'balance': CONFIG['starting_balance'],
        'positions': {},
        'start_time': datetime.now().isoformat(),
        'total_trades': 0,
        'wins': 0,
        'losses': 0,
    }


def save_state(state):
    """Save paper trading state"""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2, default=str)


def load_trades():
    """Load trade history"""
    if os.path.exists(TRADES_FILE):
        with open(TRADES_FILE, 'r') as f:
            return json.load(f)
    return []


def save_trades(trades):
    """Save trade history"""
    with open(TRADES_FILE, 'w') as f:
        json.dump(trades, f, indent=2, default=str)


def log(message):
    """Log message to file and console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    
    with open(LOG_FILE, 'a') as f:
        f.write(log_line + "\n")


# =============================================================================
# PAPER TRADING LOGIC
# =============================================================================

def check_positions(state):
    """Check and manage open positions"""
    trades = load_trades()
    
    for symbol, pos in list(state['positions'].items()):
        # Get current price
        df = get_klines(symbol, "15m", 5)
        current_price = df.iloc[-1]['close']
        current_high = df.iloc[-1]['high']
        current_low = df.iloc[-1]['low']
        
        closed = False
        result = None
        exit_price = None
        
        if pos['direction'] == 'long':
            # Check stop loss
            if current_low <= pos['stop_price']:
                exit_price = pos['stop_price']
                pnl = (exit_price - pos['entry_price']) / pos['entry_price'] * pos['size']
                result = 'stop_loss'
                closed = True
                
            # Check take profit
            elif current_high >= pos['target_price']:
                exit_price = pos['target_price']
                pnl = (exit_price - pos['entry_price']) / pos['entry_price'] * pos['size']
                result = 'take_profit'
                closed = True
                
        else:  # short
            # Check stop loss
            if current_high >= pos['stop_price']:
                exit_price = pos['stop_price']
                pnl = (pos['entry_price'] - exit_price) / pos['entry_price'] * pos['size']
                result = 'stop_loss'
                closed = True
                
            # Check take profit
            elif current_low <= pos['target_price']:
                exit_price = pos['target_price']
                pnl = (pos['entry_price'] - exit_price) / pos['entry_price'] * pos['size']
                result = 'take_profit'
                closed = True
        
        if closed:
            state['balance'] += pnl
            state['total_trades'] += 1
            
            if result == 'take_profit':
                state['wins'] += 1
                log(f"✅ WIN: {symbol} {pos['direction']} closed at {exit_price:.2f} | PnL: ${pnl:.2f}")
            else:
                state['losses'] += 1
                log(f"❌ LOSS: {symbol} {pos['direction']} stopped at {exit_price:.2f} | PnL: ${pnl:.2f}")
            
            # Record trade
            trade = {
                'symbol': symbol,
                'direction': pos['direction'],
                'entry_time': pos['entry_time'],
                'exit_time': datetime.now().isoformat(),
                'entry_price': pos['entry_price'],
                'exit_price': exit_price,
                'stop_price': pos['stop_price'],
                'target_price': pos['target_price'],
                'size': pos['size'],
                'pnl': pnl,
                'result': result,
                'h4_bias': pos['h4_bias'],
                'trigger': CONFIG['entry_trigger'],
            }
            trades.append(trade)
            
            del state['positions'][symbol]
    
    save_state(state)
    save_trades(trades)
    return state


def check_entries(state):
    """Check for new entry signals"""
    if len(state['positions']) >= CONFIG['max_positions']:
        return state
    
    for symbol in CONFIG['pairs']:
        if symbol in state['positions']:
            continue  # Already in position
        
        # Get H4 bias
        h4_bias, h4_candle = get_h4_bias(symbol)
        
        if h4_bias == 'neutral':
            log(f"⏸️  {symbol}: H4 neutral - no permission to trade")
            continue
        
        # Get 15m data and check trigger
        df = get_klines(symbol, "15m", 100)
        df = add_indicators(df)
        
        long_signal, short_signal = check_rsi_extreme(df)
        current_price = df.iloc[-1]['close']
        
        # Only take trades in H4 direction
        entry_signal = False
        direction = None
        
        if h4_bias == 'bullish' and long_signal:
            entry_signal = True
            direction = 'long'
        elif h4_bias == 'bearish' and short_signal:
            entry_signal = True
            direction = 'short'
        
        if entry_signal:
            # Calculate position
            risk_amount = state['balance'] * CONFIG['risk_per_trade']
            position_size = risk_amount / CONFIG['stop_loss_pct']
            
            if direction == 'long':
                stop_price = current_price * (1 - CONFIG['stop_loss_pct'])
                target_price = current_price * (1 + CONFIG['take_profit_pct'])
            else:
                stop_price = current_price * (1 + CONFIG['stop_loss_pct'])
                target_price = current_price * (1 - CONFIG['take_profit_pct'])
            
            # Enter position
            state['positions'][symbol] = {
                'direction': direction,
                'entry_price': current_price,
                'entry_time': datetime.now().isoformat(),
                'stop_price': stop_price,
                'target_price': target_price,
                'size': position_size,
                'h4_bias': h4_bias,
                'trigger': CONFIG['entry_trigger'],
            }
            
            log(f"🚀 ENTRY: {symbol} {direction.upper()} @ {current_price:.2f}")
            log(f"   H4 Bias: {h4_bias} | Stop: {stop_price:.2f} | Target: {target_price:.2f}")
            log(f"   Size: ${position_size:.2f} | Risk: ${risk_amount:.2f}")
    
    save_state(state)
    return state


def print_status(state):
    """Print current status"""
    win_rate = (state['wins'] / state['total_trades'] * 100) if state['total_trades'] > 0 else 0
    pnl = state['balance'] - CONFIG['starting_balance']
    pnl_pct = pnl / CONFIG['starting_balance'] * 100
    
    print("\n" + "="*50)
    print("📊 DRYRUN STATUS")
    print("="*50)
    print(f"Balance: ${state['balance']:.2f} ({pnl_pct:+.1f}%)")
    print(f"Trades: {state['total_trades']} | Wins: {state['wins']} | Losses: {state['losses']}")
    print(f"Win Rate: {win_rate:.1f}%")
    print(f"Trigger: {CONFIG['entry_trigger']}")
    
    if state['positions']:
        print("\n📍 Open Positions:")
        for symbol, pos in state['positions'].items():
            df = get_klines(symbol, "15m", 1)
            current = df.iloc[-1]['close']
            if pos['direction'] == 'long':
                unrealized = (current - pos['entry_price']) / pos['entry_price'] * pos['size']
            else:
                unrealized = (pos['entry_price'] - current) / pos['entry_price'] * pos['size']
            print(f"  {symbol} {pos['direction'].upper()}: Entry {pos['entry_price']:.2f} | Current {current:.2f} | Unrealized: ${unrealized:.2f}")
    else:
        print("\n📍 No open positions")
    print("="*50 + "\n")


# =============================================================================
# MAIN LOOP
# =============================================================================

def run_bot():
    """Main bot loop"""
    log("="*50)
    log("🤖 DRYRUN v2 Paper Trading Bot Started")
    log(f"   Pairs: {CONFIG['pairs']}")
    log(f"   Trigger: {CONFIG['entry_trigger']}")
    log(f"   Starting Balance: ${CONFIG['starting_balance']}")
    log("="*50)
    
    state = load_state()
    
    while True:
        try:
            # Check existing positions
            state = check_positions(state)
            
            # Check for new entries
            state = check_entries(state)
            
            # Print status
            print_status(state)
            
            # Wait
            log(f"💤 Sleeping {CONFIG['check_interval']}s...")
            time.sleep(CONFIG['check_interval'])
            
        except KeyboardInterrupt:
            log("🛑 Bot stopped by user")
            break
        except Exception as e:
            log(f"⚠️ Error: {e}")
            time.sleep(30)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'status':
            state = load_state()
            print_status(state)
        elif sys.argv[1] == 'reset':
            if os.path.exists(STATE_FILE):
                os.remove(STATE_FILE)
            if os.path.exists(TRADES_FILE):
                os.remove(TRADES_FILE)
            print("✅ State reset")
        else:
            print("Usage: python paper_trader.py [status|reset]")
    else:
        run_bot()
