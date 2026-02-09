"""
One-time script: Remove 4 faulty trades caused by the restart bug (2026-02-09).
Run on server: python fix_faulty_trades.py
Then delete this file.
"""
import json

STATE_FILE = 'paper_trading_state.json'

# The 4 faulty trades to remove (matched by entry price + side + strategy)
FAULTY_TRADES = [
    {'strategy': 'SOL_CCI', 'side': 'SHORT', 'entry_price': 84.81, 'tolerance': 0.5},
    {'strategy': 'AVAX_CCI', 'side': 'SHORT', 'entry_price': 8.918, 'tolerance': 0.05},
    {'strategy': 'ETH_CCI', 'side': 'SHORT', 'entry_price': 2049.36, 'tolerance': 2.0},
    {'strategy': 'ADA_CCI', 'side': 'SHORT', 'entry_price': 0.2655, 'tolerance': 0.002},
]

with open(STATE_FILE, 'r') as f:
    state = json.load(f)

for faulty in FAULTY_TRADES:
    strat = faulty['strategy']
    if strat not in state:
        print(f"  {strat}: not found in state, skipping")
        continue

    trades = state[strat].get('closed_trades', [])
    original_count = len(trades)

    # Find and remove the matching trade
    to_remove = None
    for trade in trades:
        if (trade.get('side') == faulty['side'] and
            abs(trade.get('entry_price', 0) - faulty['entry_price']) < faulty['tolerance']):
            to_remove = trade
            break

    if to_remove:
        pnl = to_remove['pnl']
        trades.remove(to_remove)
        # Restore capital (undo the loss)
        state[strat]['capital'] -= pnl  # pnl is negative, so subtracting adds back
        print(f"  {strat}: removed faulty {to_remove['side']} trade (PnL: ${pnl:.2f}), capital restored to ${state[strat]['capital']:.2f}")
    else:
        print(f"  {strat}: no matching faulty trade found")

with open(STATE_FILE, 'w') as f:
    json.dump(state, f, indent=2, default=str)

print("\nDone. State file updated. You can delete this script now.")
