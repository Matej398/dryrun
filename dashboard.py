"""
DRYRUN v5.3 - Dynamic Multi-Strategy Dashboard
- Auto-discovers strategies from strategies/ folder
- Risk exposure in portfolio summary
- Filter column in trades table
- Memory optimization for background tabs
- Animated pixel bot header with typewriter messages
"""
from flask import Flask, render_template_string, jsonify
from datetime import datetime
import json
import os
import re
import subprocess
import time

# Import bot components
from dashboard_bot import BOT_CSS, BOT_HTML, BOT_JS

# Import strategy auto-discovery
from strategies import discover_strategies

app = Flask(__name__)

STATE_FILE = "paper_trading_state.json"


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


# Register as Jinja2 filter
app.jinja_env.filters['fmt_price'] = fmt_price
STARTING_BALANCE = 1000  # Per strategy

# Auto-discover strategies (cached per request in route handlers)
_discovered_strategies = None


def get_discovered_strategies():
    """Get discovered strategy instances (cached)."""
    global _discovered_strategies
    if _discovered_strategies is None:
        try:
            _discovered_strategies = discover_strategies()
        except Exception:
            _discovered_strategies = {}
    return _discovered_strategies


def get_strategy_names(state):
    """Get strategy names from discovered strategies only."""
    discovered = get_discovered_strategies()
    return list(discovered.keys())


def extract_symbol_from_strategy(strategy_name):
    """Extract trading symbol from strategy name (BTC_RSI -> BTCUSDT)"""
    match = re.match(r'^([A-Z]+)_', strategy_name)
    if match:
        base = match.group(1)
        return f"{base}USDT"
    return "UNKNOWN"


def get_strategy_type(strategy_name):
    """Determine if strategy is spot (swing) or leverage (scalp)"""
    if 'VOL' in strategy_name or 'OBV' in strategy_name:
        return 'spot'
    return 'leverage'


def get_strategy_display_name(strategy_name):
    """Generate display name from strategy name"""
    parts = strategy_name.split('_')
    if len(parts) >= 2:
        base = parts[0]
        indicator = parts[1]
        if indicator == 'RSI':
            return f"{base} RSI Extreme"
        elif indicator == 'CCI':
            return f"{base} CCI Extreme"
        elif indicator == '4H':
            return f"{base} CCI 4H"
        elif indicator == 'VOL':
            return f"{base} Volume Surge"
        elif indicator == 'OBV':
            return f"{base} OBV Divergence"
    return strategy_name


def get_strategy_filters(strategy_name):
    """Generate filter description from strategy name"""
    strat_type = get_strategy_type(strategy_name)
    if strat_type == 'spot':
        return 'Daily + LONG-ONLY'
    elif 'RSI' in strategy_name:
        return 'H4 + LONG-ONLY'
    elif '4H' in strategy_name:
        return '4H+Daily'
    else:
        return 'H4+Daily'


def calculate_hold_time(entry_time, exit_time):
    """Calculate hold time between entry and exit"""
    if not entry_time or not exit_time:
        return "-"
    try:
        entry = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
        exit = datetime.fromisoformat(exit_time.replace('Z', '+00:00'))
        total_minutes = int((exit - entry).total_seconds() / 60)
        
        if total_minutes >= 1440:  # 24 hours or more
            days = total_minutes // 1440
            remaining_hours = (total_minutes % 1440) // 60
            if remaining_hours > 0:
                return f"{days}d {remaining_hours}h"
            return f"{days}d"
        elif total_minutes >= 60:
            hours = total_minutes // 60
            mins = total_minutes % 60
            if mins > 0:
                return f"{hours}h {mins}min"
            return f"{hours}h"
        else:
            return f"{total_minutes}min"
    except:
        return "-"


def time_ago(iso_timestamp):
    """Convert ISO timestamp to 'X minutes/hours ago' format"""
    if not iso_timestamp:
        return "Unknown"
    try:
        dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
        now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
        diff = now - dt
        seconds = diff.total_seconds()
        
        if seconds < 60:
            return "just now"
        elif seconds < 3600:
            mins = int(seconds / 60)
            return f"{mins} min{'s' if mins > 1 else ''} ago"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        else:
            days = int(seconds / 86400)
            return f"{days} day{'s' if days > 1 else ''} ago"
    except:
        return "Unknown"


DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>DRYRUN v5.1 - Dynamic Dashboard</title>
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
            overflow: hidden;
            height: 100vh;
        }
        .container { max-width: 100%; margin: 0 auto; padding: 0 10px; }
        .main-content {
            display: flex;
            gap: 15px;
            align-items: flex-start;
            height: calc(100vh - 200px);
        }
        .left-panel {
            width: 400px;
            flex-shrink: 0;
            height: 100%;
            display: flex;
            flex-direction: column;
        }
        .right-panel {
            flex: 1;
            min-width: 0;
            height: 100%;
            display: flex;
            flex-direction: column;
        }
        .scroll-content {
            flex: 1;
            overflow-y: scroll;
            position: relative;
            padding-bottom: 20px;
        }
        .scroll-content::-webkit-scrollbar {
            width: 8px;
            background: transparent;
        }
        .scroll-content::-webkit-scrollbar-thumb {
            background: rgba(45, 55, 72, 0);
            border-radius: 4px;
            transition: background 0.3s ease;
        }
        .scroll-content:hover::-webkit-scrollbar-thumb {
            background: rgba(45, 55, 72, 0.8);
        }
        .scroll-content::-webkit-scrollbar-thumb:hover {
            background: rgba(65, 80, 100, 0.9);
        }
        /* Firefox */
        @supports (scrollbar-color: auto) {
            .scroll-content {
                scrollbar-width: thin;
                scrollbar-color: transparent transparent;
                transition: scrollbar-color 0.3s ease;
            }
            .scroll-content:hover {
                scrollbar-color: rgba(45, 55, 72, 0.8) transparent;
            }
        }
        h1 { color: #f0f6fc; margin-bottom: 3px; font-size: 25px; }
        .subtitle { color: #67778E; margin-bottom: 10px; font-size: 13px; display: flex; gap: 15px; align-items: center; }
        .last-updated { color: #3CE3AB; }
        h2 { color: #67778E; margin: 10px 0 6px; font-size: 13px; text-transform: uppercase; }
        .section-header {
            background: #0A0C0F;
            border: 1px solid #171E27;
            padding: 10px 12px;
            margin-bottom: 10px;
            color: #67778E;
            font-size: 13px;
            text-transform: uppercase;
            flex-shrink: 0;
        }
        .section-header span {
            color: #f0f6fc;
            margin-left: 6px;
        }
        
        .portfolio-summary {
            background: linear-gradient(135deg, #0E1218 0%, #0E1218 100%);
            border: 1px solid #171E27;
            padding: 12px 16px;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 20px;
        }
        .portfolio-balance { font-size: 29px; font-weight: normal; }
        .portfolio-pnl { font-size: 14px; }
        .portfolio-divider { width: 1px; height: 30px; background: #171E27; }
        .portfolio-risk { font-size: 13px; color: #67778E; }
        .risk-active { color: #f0f6fc; }
        .risk-lev { color: #F23674; }
        .risk-spot { color: #3CE3AB; }
        .positive { color: #3CE3AB; }
        .negative { color: #F23674; }
        .neutral { color: #f0f6fc; }
        
        .strategies-grid {
            display: flex;
            flex-direction: column;
            gap: 12px;
            padding-bottom: 20px;
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
        .strategy-pair { font-size: 13px; color: #67778E; margin-top: 1px; }
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
        .stat-label { font-size: 13px; color: #67778E; }
        .stat-value { font-size: 18px; font-weight: normal; margin-top: 1px; }
        
        .position-box {
            background: #171E27;
            padding: 8px;
            margin-top: 6px;
        }
        .position-label { font-size: 12px; color: #67778E; margin-bottom: 3px; }
        .position-status { font-size: 14px; }
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
            font-size: 12px;
            color: #67778E;
            text-transform: uppercase;
        }
        .position-detail-value {
            font-size: 14px;
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
        th { background: #171E27; color: #67778E; font-weight: 500; font-size: 13px; }
        th:last-child, td:last-child { text-align: right; }
        tr:hover { background: #171E27; }
        tr.hidden-row { display: none; }
        
        .badge {
            display: inline-block;
            padding: 2px 6px;
            font-size: 12px;
            font-weight: normal;
        }
        .badge-long { background: #1a5a3a; color: #3CE3AB; }
        .badge-short { background: #5a1a3a; color: #F23674; }
        .badge-win { background: #1a5a3a; color: #3CE3AB; }
        .badge-loss { background: #5a1a3a; color: #F23674; }
        .filter-cell { font-size: 13px; color: #67778E; }
        
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
        .restart-btn {
            background: none; border: 1px solid #2A3441; color: #67778E;
            padding: 2px 10px; font-size: 11px; cursor: pointer;
        }
        .restart-btn:hover { border-color: #3CE3AB; color: #3CE3AB; }
        
        .no-trades {
            text-align: center;
            padding: 40px;
            color: #67778E;
            background: #0E1218;
        }
        
        """ + BOT_CSS + """
    </style>
</head>
<body>
    <div class="container">
        """ + BOT_HTML + """
        
        <div class="portfolio-summary">
            <div class="portfolio-balance {{ 'positive' if total_pnl >= 0 else 'negative' }}">${{ "%.2f"|format(total_balance) }}</div>
            <div class="portfolio-pnl {{ 'positive' if total_pnl >= 0 else 'negative' }}">
                {{ "+" if total_pnl >= 0 else "" }}${{ "%.2f"|format(total_pnl) }} ({{ "%.1f"|format(total_pnl_pct) }}%)
            </div>
            <div class="portfolio-divider"></div>
            <div class="portfolio-risk">
                Active: <span class="risk-active">${{ "%.0f"|format(total_exposure) }}</span> |
                Lev: <span class="risk-lev">${{ "%.0f"|format(leverage_exposure) }}</span> |
                Spot: <span class="risk-spot">${{ "%.0f"|format(spot_exposure) }}</span>
            </div>
        </div>
        
        <div class="main-content">
            <div class="left-panel">
                <div class="section-header">Strategies<span>({{ strategies|length }})</span></div>
                <div class="scroll-content">
                <div class="strategies-grid">
                    {% for strat_name, data in strategies.items() %}
                    <div class="strategy-card" data-symbol="{{ data.ws_symbol }}" data-strat="{{ strat_name }}">
                        <div class="strategy-header">
                            <div>
                                <div class="strategy-name">{{ data.name }}</div>
                                <div class="strategy-pair">{{ data.ws_symbol }}</div>
                            </div>
                            <div class="strategy-filters">{{ data.filters }}</div>
                        </div>
                        
                        <div class="live-price neutral" id="price-{{ strat_name }}">Loading...</div>
                        <div style="font-size: 12px; color: #67778E; margin-bottom: 8px;">Starting: ${{ "{:,.0f}".format(starting_balance) }}</div>
                
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
                                {% if data.position.direction == 'long' %}↑{% else %}↓{% endif %} {{ data.position.direction.upper() }} @ {{ data.position.entry_price|fmt_price }}
                                <span class="unrealized" id="unrealized-{{ strat_name }}">-</span>
                            </div>
                            <div class="position-details">
                                <div class="position-detail">
                                    <div class="position-detail-label">Entry</div>
                                    <div class="position-detail-value entry">{{ data.position.entry_price|fmt_price }}</div>
                                </div>
                                <div class="position-detail">
                                    <div class="position-detail-label">Stop Loss</div>
                                    <div class="position-detail-value sl">{{ data.position.stop_price|fmt_price }}</div>
                                </div>
                                <div class="position-detail">
                                    <div class="position-detail-label">Target</div>
                                    <div class="position-detail-value tp">{{ data.position.target_price|fmt_price }}</div>
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
            </div>
            
            <div class="right-panel">
                <div class="section-header">Total Trades<span>({{ trades|length }})</span></div>
                <div class="scroll-content">
                {% if trades %}
                <table class="trades-table" id="trades-table">
                    <thead>
                        <tr>
                            <th>Pair</th>
                            <th>Strategy</th>
                            <th>Filter</th>
                            <th>Direction</th>
                            <th>Entry</th>
                            <th>Exit</th>
                            <th>P&L</th>
                            <th>Result</th>
                            <th>Time</th>
                            <th>Hold</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for trade in trades[-100:]|reverse %}
                        <tr class="trade-row{% if loop.index > 50 %} hidden-row{% endif %}" data-row="{{ loop.index }}">
                            <td>{{ trade.pair }}</td>
                            <td>{{ trade.strategy_name }}</td>
                            <td class="filter-cell">{{ trade.filter }}</td>
                            <td><span class="badge badge-{{ trade.direction }}">{{ trade.direction.upper() }}</span></td>
                            <td>{{ trade.entry_price|fmt_price }}</td>
                            <td>{{ trade.exit_price|fmt_price }}</td>
                            <td class="{{ 'positive' if trade.pnl >= 0 else 'negative' }}">{{ "+" if trade.pnl >= 0 else "" }}${{ "%.2f"|format(trade.pnl) }}</td>
                            <td><span class="badge badge-{{ 'win' if trade.pnl >= 0 else 'loss' }}">{{ 'WIN' if trade.pnl >= 0 else 'LOSS' }}</span></td>
                            <td>{% if trade.exit_time %}{{ trade.exit_time[8:10] }}.{{ trade.exit_time[5:7] }} {{ trade.exit_time[11:16] }}{% else %}-{% endif %}</td>
                            <td>{{ trade.hold_time }}</td>
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
        </div>
        
        <div class="status-bar">
            <div class="ws-status">
                <div id="ws-dot" class="ws-dot"></div>
                <span id="ws-status">Connecting...</span>
            </div>
            <div style="display:flex;align-items:center;gap:12px;">
                <span>Auto-refresh: 60s | {{ strategies|length }} strategies | ${{ "{:,.0f}".format(starting_balance) }}/strategy</span>
                <button class="restart-btn" onclick="restartServices()">Restart</button>
            </div>
        </div>
    </div>
    
    <script>
        function restartServices() {
            if (!confirm('Restart bot + dashboard? (git pull + restart)')) return;
            const btn = document.querySelector('.restart-btn');
            btn.textContent = 'Restarting...';
            btn.style.color = '#F0B93A';
            btn.disabled = true;
            fetch('/api/restart', {method: 'POST'})
                .then(r => r.json())
                .then(d => { btn.textContent = d.status === 'ok' ? 'Restarting...' : 'Error'; setTimeout(() => location.reload(), 3000); })
                .catch(() => { btn.textContent = 'Error'; btn.style.color = '#F23674'; });
        }

        const positions = {{ positions_json|safe }};
        const prices = {};
        let ws;
        
        // Smart decimal formatting based on price level
        function fmtPrice(price) {
            if (price >= 100) {
                return '$' + price.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
            } else if (price >= 10) {
                return '$' + price.toLocaleString('en-US', {minimumFractionDigits: 3, maximumFractionDigits: 3});
            } else if (price >= 1) {
                return '$' + price.toLocaleString('en-US', {minimumFractionDigits: 4, maximumFractionDigits: 4});
            } else {
                return '$' + price.toLocaleString('en-US', {minimumFractionDigits: 5, maximumFractionDigits: 5});
            }
        }
        
        function connectWebSocket() {
            const streams = {{ ws_streams|safe }};
            ws = new WebSocket('wss://stream.binance.com:9443/stream?streams=' + streams.join('/'));
            
            ws.onopen = function() {
                document.getElementById('ws-dot').classList.add('connected');
                document.getElementById('ws-status').textContent = 'Live - Binance WebSocket';
            };
            
            ws.onmessage = function(event) {
                // Skip updates when tab is hidden to save memory
                if (!isPageVisible) return;
                
                const msg = JSON.parse(event.data);
                const data = msg.data;
                const symbol = data.s;
                const price = parseFloat(data.c);
                const change = parseFloat(data.P);
                
                prices[symbol] = price;
                
                document.querySelectorAll('.strategy-card[data-symbol="' + symbol + '"]').forEach(function(card) {
                    const stratName = card.dataset.strat;
                    const priceEl = document.getElementById('price-' + stratName);
                    if (priceEl) {
                        const prev = parseFloat(priceEl.dataset.price) || price;
                        priceEl.textContent = fmtPrice(price);
                        priceEl.innerHTML += '<span class="price-change ' + (change >= 0 ? 'positive' : 'negative') + '">' + 
                            (change >= 0 ? '+' : '') + change.toFixed(2) + '%</span>';
                        
                        priceEl.className = 'live-price ' + (price > prev ? 'positive' : price < prev ? 'negative' : 'neutral');
                        priceEl.dataset.price = price;
                    }
                    
                    updateUnrealized(stratName, price);
                });
            };
            
            ws.onclose = function() {
                document.getElementById('ws-dot').classList.remove('connected');
                document.getElementById('ws-status').textContent = 'Disconnected - Reconnecting...';
                setTimeout(connectWebSocket, 3000);
            };
        }
        
        function updateUnrealized(stratName, currentPrice) {
            const pos = positions[stratName];
            if (!pos) return;
            
            const el = document.getElementById('unrealized-' + stratName);
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
        
        // Track page visibility to prevent memory buildup in background tabs
        let isPageVisible = true;
        document.addEventListener('visibilitychange', function() {
            isPageVisible = !document.hidden;
            if (isPageVisible && (!ws || ws.readyState !== WebSocket.OPEN)) {
                connectWebSocket();
            }
        });
        
        // Clean up WebSocket before page unload
        window.addEventListener('beforeunload', function() {
            if (ws) {
                ws.close();
                ws = null;
            }
        });
        
        connectWebSocket();
        
        // Reload page every 60s to clear memory
        setTimeout(function() { 
            if (ws) ws.close();
            location.reload(); 
        }, 60000);
        
        """ + BOT_JS + """
    </script>
</body>
</html>
"""


def load_state():
    """Load state from file"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {}


@app.route('/')
def dashboard():
    state = load_state()
    
    strategies = {}
    total_balance = 0
    total_trades = 0
    positions_json = {}
    all_trades = []
    ws_symbols = set()
    
    # Portfolio-level metrics
    total_exposure = 0
    leverage_exposure = 0
    spot_exposure = 0
    
    # Auto-discover strategies + any in state file
    discovered = get_discovered_strategies()
    strategy_names = get_strategy_names(state)

    for strategy_name in strategy_names:
        # Get state data or use defaults
        strat_state = state.get(strategy_name, {
            'capital': STARTING_BALANCE,
            'positions': [],
            'closed_trades': []
        })

        # Get metadata from strategy instance if available, else fallback
        if strategy_name in discovered:
            meta = discovered[strategy_name].get_dashboard_metadata()
            ws_symbol = meta['ws_symbol']
            strat_type = meta['strategy_type']
            display_name = meta['name']
            filters = meta['filters_description']
        else:
            ws_symbol = extract_symbol_from_strategy(strategy_name)
            strat_type = get_strategy_type(strategy_name)
            display_name = get_strategy_display_name(strategy_name)
            filters = get_strategy_filters(strategy_name)
        
        ws_symbols.add(ws_symbol.lower() + '@ticker')
        
        balance = strat_state.get('capital', STARTING_BALANCE)
        closed_trades = strat_state.get('closed_trades', [])
        positions = strat_state.get('positions', [])
        
        # Calculate wins/losses
        wins = len([t for t in closed_trades if t.get('pnl', 0) > 0])
        losses = len([t for t in closed_trades if t.get('pnl', 0) <= 0])
        
        # Get current position
        position = None
        position_size = 0
        if positions and len(positions) > 0:
            pos = positions[0]
            position_size = pos.get('size', 0) * pos.get('entry_price', 1)
            position = {
                'direction': pos.get('side', 'long').lower(),
                'entry_price': pos.get('entry_price', 0),
                'stop_price': pos.get('stop_loss', 0),
                'target_price': pos.get('take_profit', 0),
                'size': position_size,
                'entry_time': pos.get('entry_time', '')
            }
            
            # Track exposure
            total_exposure += position_size
            if strat_type == 'leverage':
                leverage_exposure += position_size
            else:
                spot_exposure += position_size
        
        pnl = balance - STARTING_BALANCE
        pnl_pct = pnl / STARTING_BALANCE * 100
        win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
        
        total_balance += balance
        total_trades += wins + losses
        
        strategies[strategy_name] = {
            'name': display_name,
            'filters': filters,
            'ws_symbol': ws_symbol,
            'strat_type': strat_type,
            'balance': balance,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'position': position,
        }
        
        if position:
            positions_json[strategy_name] = position
        
        # Collect trades for display with hold time
        pair = ws_symbol.replace('USDT', '/USDT')
        for trade in closed_trades:
            all_trades.append({
                'symbol': ws_symbol,
                'pair': pair,
                'strategy_name': display_name,
                'filter': filters,
                'direction': trade.get('side', 'long').lower(),
                'entry_price': trade.get('entry_price', 0),
                'exit_price': trade.get('exit_price', 0),
                'pnl': trade.get('pnl', 0),
                'entry_time': trade.get('entry_time', ''),
                'exit_time': trade.get('exit_time', ''),
                'hold_time': calculate_hold_time(trade.get('entry_time'), trade.get('exit_time'))
            })
    
    # Sort trades by exit time
    all_trades.sort(key=lambda x: x.get('exit_time', ''), reverse=True)
    
    # Calculate portfolio-level metrics
    total_starting = STARTING_BALANCE * len(strategies)
    total_pnl = total_balance - total_starting
    total_pnl_pct = (total_pnl / total_starting * 100) if total_starting > 0 else 0
    
    # Last updated
    last_updated = time_ago(state.get('_last_updated'))
    
    return render_template_string(
        DASHBOARD_HTML,
        strategies=strategies,
        total_balance=total_balance,
        total_pnl=total_pnl,
        total_pnl_pct=total_pnl_pct,
        total_trades=total_trades,
        total_starting=total_starting,
        total_exposure=total_exposure,
        leverage_exposure=leverage_exposure,
        spot_exposure=spot_exposure,
        last_updated=last_updated,
        trades=all_trades,
        positions_json=json.dumps(positions_json),
        ws_streams=json.dumps(list(ws_symbols)),
        starting_balance=STARTING_BALANCE,
    )


@app.route('/api/status')
def api_status():
    state = load_state()
    all_trades = []
    for strategy_name in get_strategy_names(state):
        strat_state = state.get(strategy_name, {})
        if isinstance(strat_state, dict):
            all_trades.extend(strat_state.get('closed_trades', []))
    all_trades.sort(key=lambda x: x.get('exit_time', ''), reverse=True)
    return jsonify({'state': state, 'trades': all_trades[:20]})


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(PROJECT_DIR, 'venv', 'bin', 'python')


@app.route('/api/restart', methods=['POST'])
def api_restart():
    """Git pull + restart paper_trader and dashboard."""
    try:
        # Git pull
        subprocess.run(['git', 'pull'], cwd=PROJECT_DIR, timeout=30)

        # Kill ALL existing paper_trader instances and wait
        subprocess.run(['pkill', '-f', 'python paper_trader.py'])
        time.sleep(2)  # Wait for processes to die

        # Start paper_trader (PID lockfile prevents duplicates)
        subprocess.Popen(
            [VENV_PYTHON, 'paper_trader.py'],
            cwd=PROJECT_DIR,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        # Restart dashboard (delayed so response can be sent first)
        subprocess.Popen(
            ['bash', '-c', f'sleep 1 && pkill -f "python dashboard.py" && sleep 2 && {VENV_PYTHON} dashboard.py'],
            cwd=PROJECT_DIR,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5051, debug=False)
