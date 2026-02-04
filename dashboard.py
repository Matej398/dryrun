"""
DRYRUN v4.0 - Multi-Strategy Dashboard
Shows BTC RSI + ETH CCI with live WebSocket prices
Updated for paper_trader_v4.py compatibility
"""
from flask import Flask, render_template_string, jsonify
import json
import os

app = Flask(__name__)

STATE_FILE = "paper_trading_state.json"
STARTING_BALANCE = 1500  # Per strategy (v4)

# Map internal strategy names to display info and WebSocket symbols
STRATEGIES_INFO = {
    'BTC_RSI': {'name': 'BTC RSI Extreme', 'filters': 'H4 + LONG-ONLY', 'ws': 'btcusdt', 'symbol': 'BTCUSDT'},
    'ETH_CCI': {'name': 'ETH CCI Extreme', 'filters': 'H4+Daily', 'ws': 'ethusdt', 'symbol': 'ETHUSDT'},
    'SOL_CCI': {'name': 'SOL CCI Extreme', 'filters': 'H4+Daily', 'ws': 'solusdt', 'symbol': 'SOLUSDT'},
}

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>DRYRUN v4.0 - Multi-Strategy Dashboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { 
            margin: 0; 
            padding: 0; 
            box-sizing: border-box;
            font-family: 'IBM Plex Mono', monospace;
        }
        body { 
            font-family: 'IBM Plex Mono', monospace;
            background: #0A0C0F; 
            color: #c9d1d9; 
            padding: 10px;
            padding-bottom: 50px;
        }
        .container { max-width: 100%; margin: 0 auto; padding: 0 10px; }
        .main-content {
            display: flex;
            gap: 15px;
            align-items: flex-start;
        }
        .left-panel {
            width: 400px;
            flex-shrink: 0;
        }
        .right-panel {
            flex: 1;
            min-width: 0;
        }
        h1 { color: #f0f6fc; margin-bottom: 3px; font-size: 25px; }
        .subtitle { color: #67778E; margin-bottom: 10px; font-size: 13px; }
        h2 { color: #67778E; margin: 10px 0 6px; font-size: 13px; text-transform: uppercase; }
        
        .portfolio-summary {
            background: linear-gradient(135deg, #0E1218 0%, #0E1218 100%);
            border: 1px solid #171E27;
            padding: 12px;
            margin-bottom: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .portfolio-balance { font-size: 29px; font-weight: normal; }
        .portfolio-pnl { font-size: 15px; margin-top: 3px; }
        .positive { color: #3CE3AB; }
        .negative { color: #F23674; }
        .neutral { color: #f0f6fc; }
        
        .strategies-grid {
            display: flex;
            flex-direction: column;
            gap: 12px;
            margin-bottom: 15px;
        }
        
        .strategy-card {
            background: #0E1218;
            border: 1px solid #171E27;
            padding: 12px;
            position: relative;
        }
        .strategy-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 8px;
        }
        .strategy-name { font-size: 15px; font-weight: normal; color: #f0f6fc; }
        .strategy-pair { font-size: 12px; color: #67778E; margin-top: 1px; }
        .strategy-filters {
            background: #171E27;
            padding: 4px 8px;
            font-size: 12px;
            color: #67778E;
        }
        
        .live-price {
            font-size: 23px;
            font-weight: normal;
            font-family: 'IBM Plex Mono', monospace;
            margin-bottom: 8px;
        }
        .price-change {
            font-size: 13px;
            margin-left: 6px;
        }
        
        .strategy-stats {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 6px;
            margin-bottom: 8px;
        }
        .stat-item {
            background: #171E27;
            padding: 6px;
        }
        .stat-label { font-size: 11px; color: #67778E; }
        .stat-value { font-size: 16px; font-weight: normal; margin-top: 1px; }
        
        .position-box {
            background: #171E27;
            padding: 8px;
            margin-top: 6px;
        }
        .position-label { font-size: 11px; color: #67778E; margin-bottom: 3px; }
        .position-status { font-size: 13px; }
        .position-long { color: #3CE3AB; }
        .position-short { color: #F23674; }
        .position-flat { color: #67778E; }
        
        .position-details {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid #171E27;
        }
        .position-detail {
            text-align: center;
        }
        .position-detail-label {
            font-size: 10px;
            color: #67778E;
            text-transform: uppercase;
        }
        .position-detail-value {
            font-size: 13px;
            font-weight: normal;
            margin-top: 1px;
        }
        .position-detail-value.entry { color: #f0f6fc; }
        .position-detail-value.sl { color: #F23674; }
        .position-detail-value.tp { color: #3CE3AB; }
        
        .unrealized {
            font-family: 'IBM Plex Mono', monospace;
            font-weight: normal;
            margin-left: 10px;
        }
        
        .trades-table {
            width: 100%;
            border-collapse: collapse;
            background: #0E1218;
            overflow: hidden;
        }
        th, td {
            padding: 6px 10px;
            text-align: left;
            border-bottom: 1px solid #171E27;
            font-size: 13px;
        }
        th { background: #171E27; color: #67778E; font-weight: 500; font-size: 12px; }
        th:last-child, td:last-child { text-align: right; }
        tr:hover { background: #171E27; }
        tr.hidden-row { display: none; }
        
        .badge {
            display: inline-block;
            padding: 2px 6px;
            font-size: 11px;
            font-weight: normal;
        }
        .badge-long { background: #1a5a3a; color: #3CE3AB; }
        .badge-short { background: #5a1a3a; color: #F23674; }
        .badge-win { background: #1a5a3a; color: #3CE3AB; }
        .badge-loss { background: #5a1a3a; color: #F23674; }
        
        .show-more-btn {
            width: 100%;
            padding: 10px;
            background: #171E27;
            border: 1px solid #171E27;
            color: #67778E;
            font-family: 'IBM Plex Mono', monospace;
            font-size: 12px;
            cursor: pointer;
            margin-top: 5px;
        }
        .show-more-btn:hover {
            background: #1a2330;
            color: #f0f6fc;
        }
        
        .live-dot {
            width: 6px;
            height: 6px;
            background: #3CE3AB;
            display: inline-block;
            margin-right: 6px;
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }
        
        .status-bar {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 20px;
            background: #0E1218;
            border-top: 1px solid #171E27;
            font-size: 12px;
            color: #67778E;
            z-index: 100;
        }
        .ws-status { display: flex; align-items: center; gap: 5px; }
        .ws-dot { width: 6px; height: 6px; background: #F23674; }
        .ws-dot.connected { background: #3CE3AB; }
        
        .no-trades {
            text-align: center;
            padding: 40px;
            color: #67778E;
            background: #0E1218;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1><span class="live-dot"></span>DRYRUN v4.0 Dashboard</h1>
        <div class="subtitle">Multi-Strategy Paper Trading | BTC RSI (Long-Only) + ETH CCI (H4+Daily) + SOL CCI (H4+Daily)</div>
        
        <div class="portfolio-summary">
            <div>
                <div class="portfolio-balance" id="total-balance">${{ "%.2f"|format(total_balance) }}</div>
                <div class="portfolio-pnl {{ 'positive' if total_pnl >= 0 else 'negative' }}">
                    {{ "+" if total_pnl >= 0 else "" }}${{ "%.2f"|format(total_pnl) }} ({{ "%.1f"|format(total_pnl_pct) }}%)
                </div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 24px; color: #8b949e;">{{ total_trades }}</div>
                <div style="font-size: 12px; color: #8b949e;">Total Trades</div>
            </div>
        </div>
        
        <div class="main-content">
            <div class="left-panel">
                <h2>Strategies</h2>
                <div class="strategies-grid">
                    {% for symbol, data in strategies.items() %}
                    <div class="strategy-card" data-symbol="{{ symbol }}">
                        <div class="strategy-header">
                            <div>
                                <div class="strategy-name">{{ data.name }}</div>
                                <div class="strategy-pair">{{ symbol }}</div>
                            </div>
                            <div class="strategy-filters">{{ data.filters }}</div>
                        </div>
                        
                        <div class="live-price neutral" id="price-{{ symbol }}">Loading...</div>
                
                <div class="strategy-stats">
                    <div class="stat-item">
                        <div class="stat-label">Balance</div>
                        <div class="stat-value {{ 'positive' if data.pnl >= 0 else 'negative' }}">${{ "%.2f"|format(data.balance) }}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">P&L</div>
                        <div class="stat-value {{ 'positive' if data.pnl >= 0 else 'negative' }}">{{ "+" if data.pnl >= 0 else "" }}{{ "%.1f"|format(data.pnl_pct) }}%</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Win Rate</div>
                        <div class="stat-value">{{ "%.0f"|format(data.win_rate) }}%</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Trades</div>
                        <div class="stat-value">{{ data.wins }}/{{ data.losses }}</div>
                    </div>
                </div>
                
                <div class="position-box">
                    <div class="position-label">Position</div>
                    {% if data.position %}
                    <div class="position-status position-{{ data.position.direction }}">
                        {% if data.position.direction == 'long' %}↑{% else %}↓{% endif %} {{ data.position.direction.upper() }} @ ${{ "%.2f"|format(data.position.entry_price) }}
                        <span class="unrealized" id="unrealized-{{ symbol }}">-</span>
                    </div>
                    <div class="position-details">
                        <div class="position-detail">
                            <div class="position-detail-label">Entry</div>
                            <div class="position-detail-value entry">${{ "%.2f"|format(data.position.entry_price) }}</div>
                        </div>
                        <div class="position-detail">
                            <div class="position-detail-label">Stop Loss</div>
                            <div class="position-detail-value sl">${{ "%.2f"|format(data.position.stop_price) }}</div>
                        </div>
                        <div class="position-detail">
                            <div class="position-detail-label">Target</div>
                            <div class="position-detail-value tp">${{ "%.2f"|format(data.position.target_price) }}</div>
                        </div>
                    </div>
                    {% else %}
                    <div class="position-status position-flat">No position</div>
                    {% endif %}
                </div>
            </div>
            {% endfor %}
            </div>
        </div>
        
        <div class="right-panel">
                <h2>Recent Trades (All Strategies) - {{ trades|length }} total</h2>
                {% if trades %}
                <table class="trades-table" id="trades-table">
                    <thead>
                        <tr>
                            <th>Strategy</th>
                            <th>Direction</th>
                            <th>Entry</th>
                            <th>Exit</th>
                            <th>P&L</th>
                            <th>Result</th>
                            <th>Time</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for trade in trades[-100:]|reverse %}
                        <tr class="trade-row{% if loop.index > 50 %} hidden-row{% endif %}" data-row="{{ loop.index }}">
                            <td>{{ trade.strategy_name }}</td>
                            <td><span class="badge badge-{{ trade.direction }}">{{ trade.direction.upper() }}</span></td>
                            <td>${{ "%.2f"|format(trade.entry_price) }}</td>
                            <td>${{ "%.2f"|format(trade.exit_price) }}</td>
                            <td class="{{ 'positive' if trade.pnl >= 0 else 'negative' }}">{{ "+" if trade.pnl >= 0 else "" }}${{ "%.2f"|format(trade.pnl) }}</td>
                            <td><span class="badge badge-{{ 'win' if trade.pnl >= 0 else 'loss' }}">{{ 'WIN' if trade.pnl >= 0 else 'LOSS' }}</span></td>
                            <td>{% if trade.exit_time %}{{ trade.exit_time[8:10] }}.{{ trade.exit_time[5:7] }}.{{ trade.exit_time[:4] }} @ {{ trade.exit_time[11:16] }}{% else %}-{% endif %}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% if trades|length > 50 %}
                <button class="show-more-btn" id="show-more-btn" onclick="showMoreTrades()">Show More ({{ [trades|length - 50, 0]|max }} remaining)</button>
                {% endif %}
                {% else %}
                <div class="no-trades">
                    No trades yet - waiting for signals
                </div>
                {% endif %}
            </div>
        </div>
        
        <div class="status-bar">
            <div class="ws-status">
                <div id="ws-dot" class="ws-dot"></div>
                <span id="ws-status">Connecting...</span>
            </div>
            <div>Auto-refresh: 60s | BTC=H4+LongOnly, ETH=H4+Daily, SOL=H4+Daily | $1500/strategy</div>
        </div>
    </div>
    
    <script>
        const positions = {{ positions_json|safe }};
        const prices = {};
        let ws;
        
        function connectWebSocket() {
            ws = new WebSocket('wss://stream.binance.com:9443/stream?streams=btcusdt@ticker/ethusdt@ticker/solusdt@ticker');
            
            ws.onopen = function() {
                document.getElementById('ws-dot').classList.add('connected');
                document.getElementById('ws-status').textContent = 'Live - Binance WebSocket';
            };
            
            ws.onmessage = function(event) {
                const msg = JSON.parse(event.data);
                const data = msg.data;
                const symbol = data.s;
                const price = parseFloat(data.c);
                const change = parseFloat(data.P);
                
                prices[symbol] = price;
                
                const priceEl = document.getElementById('price-' + symbol);
                if (priceEl) {
                    const prev = parseFloat(priceEl.dataset.price) || price;
                    priceEl.textContent = '$' + price.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                    priceEl.innerHTML += '<span class="price-change ' + (change >= 0 ? 'positive' : 'negative') + '">' + 
                        (change >= 0 ? '+' : '') + change.toFixed(2) + '%</span>';
                    
                    priceEl.className = 'live-price ' + (price > prev ? 'positive' : price < prev ? 'negative' : 'neutral');
                    priceEl.dataset.price = price;
                }
                
                updateUnrealized(symbol, price);
            };
            
            ws.onclose = function() {
                document.getElementById('ws-dot').classList.remove('connected');
                document.getElementById('ws-status').textContent = 'Disconnected - Reconnecting...';
                setTimeout(connectWebSocket, 3000);
            };
        }
        
        function updateUnrealized(symbol, currentPrice) {
            const pos = positions[symbol];
            if (!pos) return;
            
            const el = document.getElementById('unrealized-' + symbol);
            if (!el) return;
            
            let unrealized;
            if (pos.direction === 'long') {
                unrealized = (currentPrice - pos.entry_price) / pos.entry_price * pos.size;
            } else {
                unrealized = (pos.entry_price - currentPrice) / pos.entry_price * pos.size;
            }
            
            el.textContent = (unrealized >= 0 ? '+' : '') + '$' + unrealized.toFixed(2);
            el.className = 'unrealized ' + (unrealized >= 0 ? 'positive' : 'negative');
        }
        
        let visibleRows = 50;
        function showMoreTrades() {
            const rows = document.querySelectorAll('.trade-row');
            const totalRows = rows.length;
            const nextVisible = Math.min(visibleRows + 15, totalRows);
            
            for (let i = visibleRows; i < nextVisible; i++) {
                rows[i].classList.remove('hidden-row');
            }
            visibleRows = nextVisible;
            
            const remaining = totalRows - visibleRows;
            const btn = document.getElementById('show-more-btn');
            if (remaining <= 0) {
                btn.style.display = 'none';
            } else {
                btn.textContent = 'Show More (' + remaining + ' remaining)';
            }
        }
        
        connectWebSocket();
        
        setTimeout(function() { location.reload(); }, 60000);
    </script>
</body>
</html>
"""


def load_state():
    """Load state from paper_trader_v4 format"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    # Default state matching v4 format
    return {
        'BTC_RSI': {'capital': STARTING_BALANCE, 'positions': [], 'closed_trades': []},
        'ETH_CCI': {'capital': STARTING_BALANCE, 'positions': [], 'closed_trades': []}
    }


@app.route('/')
def dashboard():
    state = load_state()
    
    strategies = {}
    total_balance = 0
    total_trades = 0
    positions_json = {}
    all_trades = []
    
    for strategy_name, info in STRATEGIES_INFO.items():
        # Get strategy state from v4 format (flat structure, not nested under 'strategies')
        strat_state = state.get(strategy_name, {
            'capital': STARTING_BALANCE,
            'positions': [],
            'closed_trades': []
        })
        
        balance = strat_state.get('capital', STARTING_BALANCE)
        closed_trades = strat_state.get('closed_trades', [])
        positions = strat_state.get('positions', [])
        
        # Calculate wins/losses from closed_trades
        wins = len([t for t in closed_trades if t.get('pnl', 0) > 0])
        losses = len([t for t in closed_trades if t.get('pnl', 0) <= 0])
        
        # Get current position (v4 uses positions array, take first if exists)
        position = None
        if positions and len(positions) > 0:
            pos = positions[0]
            # Convert v4 position format to dashboard format
            position = {
                'direction': pos.get('side', 'long').lower(),
                'entry_price': pos.get('entry_price', 0),
                'stop_price': pos.get('stop_loss', 0),
                'target_price': pos.get('take_profit', 0),
                'size': pos.get('size', 0) * pos.get('entry_price', 1),  # Convert to $ value
                'entry_time': pos.get('entry_time', '')
            }
        
        pnl = balance - STARTING_BALANCE
        pnl_pct = pnl / STARTING_BALANCE * 100
        win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
        
        total_balance += balance
        total_trades += wins + losses
        
        # Use WebSocket symbol for display
        ws_symbol = info['symbol']
        strategies[ws_symbol] = {
            'name': info['name'],
            'filters': info['filters'],
            'balance': balance,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'position': position,
        }
        
        if position:
            positions_json[ws_symbol] = position
        
        # Collect trades for display
        for trade in closed_trades:
            all_trades.append({
                'symbol': ws_symbol,
                'strategy_name': info['name'],  # Full strategy name
                'direction': trade.get('side', 'long').lower(),
                'entry_price': trade.get('entry_price', 0),
                'exit_price': trade.get('exit_price', 0),
                'pnl': trade.get('pnl', 0),
                'exit_time': trade.get('exit_time', '')
            })
    
    # Sort trades by exit time (newest first)
    all_trades.sort(key=lambda x: x.get('exit_time', ''), reverse=True)
    
    total_starting = STARTING_BALANCE * len(STRATEGIES_INFO)
    total_pnl = total_balance - total_starting
    total_pnl_pct = total_pnl / total_starting * 100
    
    return render_template_string(
        DASHBOARD_HTML,
        strategies=strategies,
        total_balance=total_balance,
        total_pnl=total_pnl,
        total_pnl_pct=total_pnl_pct,
        total_trades=total_trades,
        trades=all_trades,
        positions_json=json.dumps(positions_json),
    )


@app.route('/api/status')
def api_status():
    state = load_state()
    # Collect all trades from state
    all_trades = []
    for strategy_name in STRATEGIES_INFO.keys():
        strat_state = state.get(strategy_name, {})
        all_trades.extend(strat_state.get('closed_trades', []))
    all_trades.sort(key=lambda x: x.get('exit_time', ''), reverse=True)
    return jsonify({'state': state, 'trades': all_trades[:20]})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5051, debug=False)
