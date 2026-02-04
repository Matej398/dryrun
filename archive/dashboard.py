"""
DRYRUN v2 - Live Dashboard with Real-Time Prices
Uses Binance WebSocket for instant price updates
"""
from flask import Flask, render_template_string, jsonify
import json
import os

app = Flask(__name__)

STATE_FILE = "paper_state.json"
TRADES_FILE = "paper_trades.json"
CONFIG_TRIGGER = "rsi_extreme"
STARTING_BALANCE = 1000

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>DRYRUN v2 - Live Trading Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0d1117; 
            color: #c9d1d9; 
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: #58a6ff; margin-bottom: 10px; }
        .subtitle { color: #8b949e; margin-bottom: 20px; font-size: 14px; }
        h2 { color: #8b949e; margin: 20px 0 10px; font-size: 14px; text-transform: uppercase; }
        
        .live-price-bar {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 15px 20px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 20px;
        }
        .price-label { color: #8b949e; font-size: 12px; }
        .live-price { 
            font-size: 32px; 
            font-weight: bold; 
            font-family: 'SF Mono', Monaco, monospace;
        }
        .price-up { color: #3fb950; }
        .price-down { color: #f85149; }
        .price-neutral { color: #58a6ff; }
        .live-dot {
            width: 8px;
            height: 8px;
            background: #3fb950;
            border-radius: 50%;
            animation: pulse 1s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 20px;
        }
        .stat-label { color: #8b949e; font-size: 12px; margin-bottom: 5px; }
        .stat-value { font-size: 28px; font-weight: bold; }
        .stat-value.positive { color: #3fb950; }
        .stat-value.negative { color: #f85149; }
        .stat-value.neutral { color: #58a6ff; }
        
        .positions-table, .trades-table {
            width: 100%;
            border-collapse: collapse;
            background: #161b22;
            border-radius: 8px;
            overflow: hidden;
            margin-bottom: 30px;
        }
        th, td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #30363d;
        }
        th { background: #21262d; color: #8b949e; font-weight: 500; font-size: 12px; text-transform: uppercase; }
        tr:hover { background: #21262d; }
        
        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
        }
        .badge-long { background: #238636; color: white; }
        .badge-short { background: #da3633; color: white; }
        .badge-win { background: #238636; }
        .badge-loss { background: #da3633; }
        
        .pnl-positive { color: #3fb950; }
        .pnl-negative { color: #f85149; }
        
        .unrealized {
            font-family: 'SF Mono', Monaco, monospace;
            font-weight: bold;
        }
        
        .empty-state {
            text-align: center;
            padding: 40px;
            color: #8b949e;
        }
        
        .status-bar {
            display: flex;
            align-items: center;
            gap: 10px;
            color: #8b949e;
            font-size: 12px;
            margin-top: 20px;
        }
        .ws-status {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        .ws-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #f85149;
        }
        .ws-dot.connected { background: #3fb950; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏃 DRYRUN v2 Dashboard</h1>
        <div class="subtitle">H4 Permission + RSI Extreme Strategy | Paper Trading</div>
        
        <div class="live-price-bar">
            <div class="live-dot"></div>
            <div>
                <div class="price-label">BTC/USDT Live Price</div>
                <div id="live-price" class="live-price price-neutral">Loading...</div>
            </div>
            <div style="margin-left: auto; text-align: right;">
                <div class="price-label">24h Change</div>
                <div id="price-change" class="live-price" style="font-size: 18px;">-</div>
            </div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Balance</div>
                <div id="balance" class="stat-value neutral">${{ "%.2f"|format(balance) }}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">P&L (Realized)</div>
                <div id="realized-pnl" class="stat-value {{ 'positive' if pnl >= 0 else 'negative' }}">{{ "+" if pnl >= 0 else "" }}${{ "%.2f"|format(pnl) }}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Unrealized P&L</div>
                <div id="unrealized-pnl" class="stat-value neutral">$0.00</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Win Rate</div>
                <div class="stat-value neutral">{{ "%.1f"|format(win_rate) }}%</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Trades</div>
                <div class="stat-value neutral">{{ total_trades }}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Wins / Losses</div>
                <div class="stat-value"><span class="pnl-positive">{{ wins }}</span> / <span class="pnl-negative">{{ losses }}</span></div>
            </div>
        </div>
        
        <h2>📍 Open Positions</h2>
        {% if positions %}
        <table class="positions-table">
            <thead>
                <tr>
                    <th>Symbol</th>
                    <th>Direction</th>
                    <th>Entry</th>
                    <th>Current</th>
                    <th>Stop</th>
                    <th>Target</th>
                    <th>Unrealized</th>
                    <th>H4 Bias</th>
                </tr>
            </thead>
            <tbody>
                {% for symbol, pos in positions.items() %}
                <tr data-symbol="{{ symbol }}" data-direction="{{ pos.direction }}" data-entry="{{ pos.entry_price }}" data-size="{{ pos.size }}">
                    <td><strong>{{ symbol }}</strong></td>
                    <td><span class="badge badge-{{ pos.direction }}">{{ pos.direction.upper() }}</span></td>
                    <td>${{ "%.2f"|format(pos.entry_price) }}</td>
                    <td class="current-price">-</td>
                    <td>${{ "%.2f"|format(pos.stop_price) }}</td>
                    <td>${{ "%.2f"|format(pos.target_price) }}</td>
                    <td class="unrealized-cell unrealized">-</td>
                    <td>{{ pos.h4_bias }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <div class="empty-state">No open positions - waiting for RSI extreme signal with H4 permission</div>
        {% endif %}
        
        <h2>📜 Recent Trades</h2>
        {% if trades %}
        <table class="trades-table">
            <thead>
                <tr>
                    <th>Symbol</th>
                    <th>Direction</th>
                    <th>Entry</th>
                    <th>Exit</th>
                    <th>P&L</th>
                    <th>Result</th>
                    <th>Exit Time</th>
                </tr>
            </thead>
            <tbody>
                {% for trade in trades[-10:]|reverse %}
                <tr>
                    <td><strong>{{ trade.symbol }}</strong></td>
                    <td><span class="badge badge-{{ trade.direction }}">{{ trade.direction.upper() }}</span></td>
                    <td>${{ "%.2f"|format(trade.entry_price) }}</td>
                    <td>${{ "%.2f"|format(trade.exit_price) }}</td>
                    <td class="{{ 'pnl-positive' if trade.pnl >= 0 else 'pnl-negative' }}">{{ "+" if trade.pnl >= 0 else "" }}${{ "%.2f"|format(trade.pnl) }}</td>
                    <td><span class="badge badge-{{ 'win' if trade.result == 'take_profit' else 'loss' }}">{{ 'WIN' if trade.result == 'take_profit' else 'LOSS' }}</span></td>
                    <td>{{ trade.exit_time[:16] if trade.exit_time else '-' }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <div class="empty-state">No trades yet</div>
        {% endif %}
        
        <div class="status-bar">
            <div class="ws-status">
                <div id="ws-dot" class="ws-dot"></div>
                <span id="ws-status">Connecting to Binance...</span>
            </div>
            <span style="margin-left: auto;">Strategy: RSI Extreme + H4 Permission | Pair: BTC only</span>
        </div>
    </div>
    
    <script>
        // Binance WebSocket for live BTC price
        let ws;
        let lastPrice = 0;
        let reconnectAttempts = 0;
        
        function connectWebSocket() {
            ws = new WebSocket('wss://stream.binance.com:9443/ws/btcusdt@ticker');
            
            ws.onopen = function() {
                document.getElementById('ws-dot').classList.add('connected');
                document.getElementById('ws-status').textContent = 'Live - Binance WebSocket';
                reconnectAttempts = 0;
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                const price = parseFloat(data.c);
                const change = parseFloat(data.P);
                
                // Update price display
                const priceEl = document.getElementById('live-price');
                priceEl.textContent = '$' + price.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                
                // Color based on price movement
                if (lastPrice > 0) {
                    if (price > lastPrice) {
                        priceEl.className = 'live-price price-up';
                    } else if (price < lastPrice) {
                        priceEl.className = 'live-price price-down';
                    }
                }
                lastPrice = price;
                
                // Update 24h change
                const changeEl = document.getElementById('price-change');
                changeEl.textContent = (change >= 0 ? '+' : '') + change.toFixed(2) + '%';
                changeEl.className = change >= 0 ? 'pnl-positive' : 'pnl-negative';
                
                // Update unrealized P&L for positions
                updateUnrealizedPnL(price);
            };
            
            ws.onclose = function() {
                document.getElementById('ws-dot').classList.remove('connected');
                document.getElementById('ws-status').textContent = 'Disconnected - Reconnecting...';
                
                // Reconnect with backoff
                reconnectAttempts++;
                setTimeout(connectWebSocket, Math.min(1000 * reconnectAttempts, 5000));
            };
            
            ws.onerror = function(error) {
                console.error('WebSocket error:', error);
            };
        }
        
        function updateUnrealizedPnL(currentPrice) {
            let totalUnrealized = 0;
            
            document.querySelectorAll('.positions-table tbody tr').forEach(row => {
                const symbol = row.dataset.symbol;
                if (symbol !== 'BTCUSDT') return;
                
                const direction = row.dataset.direction;
                const entryPrice = parseFloat(row.dataset.entry);
                const size = parseFloat(row.dataset.size);
                
                let unrealized;
                if (direction === 'long') {
                    unrealized = (currentPrice - entryPrice) / entryPrice * size;
                } else {
                    unrealized = (entryPrice - currentPrice) / entryPrice * size;
                }
                
                totalUnrealized += unrealized;
                
                // Update current price cell
                row.querySelector('.current-price').textContent = '$' + currentPrice.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                
                // Update unrealized cell
                const unrealizedCell = row.querySelector('.unrealized-cell');
                unrealizedCell.textContent = (unrealized >= 0 ? '+' : '') + '$' + unrealized.toFixed(2);
                unrealizedCell.className = 'unrealized-cell unrealized ' + (unrealized >= 0 ? 'pnl-positive' : 'pnl-negative');
            });
            
            // Update total unrealized
            const unrealizedEl = document.getElementById('unrealized-pnl');
            unrealizedEl.textContent = (totalUnrealized >= 0 ? '+' : '') + '$' + totalUnrealized.toFixed(2);
            unrealizedEl.className = 'stat-value ' + (totalUnrealized >= 0 ? 'positive' : 'negative');
        }
        
        // Start WebSocket connection
        connectWebSocket();
        
        // Refresh page every 60 seconds to get latest state from server
        setTimeout(function() {
            location.reload();
        }, 60000);
    </script>
</body>
</html>
"""


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {
        'balance': STARTING_BALANCE,
        'positions': {},
        'total_trades': 0,
        'wins': 0,
        'losses': 0,
    }


def load_trades():
    if os.path.exists(TRADES_FILE):
        with open(TRADES_FILE, 'r') as f:
            return json.load(f)
    return []


@app.route('/')
def dashboard():
    state = load_state()
    trades = load_trades()
    
    balance = state.get('balance', STARTING_BALANCE)
    pnl = balance - STARTING_BALANCE
    total_trades = state.get('total_trades', 0)
    wins = state.get('wins', 0)
    losses = state.get('losses', 0)
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    
    return render_template_string(
        DASHBOARD_HTML,
        balance=balance,
        pnl=pnl,
        total_trades=total_trades,
        wins=wins,
        losses=losses,
        win_rate=win_rate,
        positions=state.get('positions', {}),
        trades=trades,
    )


@app.route('/api/status')
def api_status():
    state = load_state()
    trades = load_trades()
    return jsonify({
        'state': state,
        'trades': trades[-20:],
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=False)
