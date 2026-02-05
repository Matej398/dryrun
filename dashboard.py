"""
DRYRUN v5.0 - Dynamic Multi-Strategy Dashboard
- Reads strategies dynamically from state file
- Advanced metrics: Profit Factor, R:R, Exit Breakdown, Streaks, Hold Time
- Portfolio Risk Monitor with exposure tracking
- Circuit Breaker Warnings for drawdowns
- Last Updated timestamp
"""
from flask import Flask, render_template_string, jsonify
from datetime import datetime
import json
import os
import re

app = Flask(__name__)

STATE_FILE = "paper_trading_state.json"
STARTING_BALANCE = 1000  # Per strategy


def extract_symbol_from_strategy(strategy_name):
    """Extract trading symbol from strategy name (BTC_RSI -> BTCUSDT)"""
    # Extract first part before underscore
    match = re.match(r'^([A-Z]+)_', strategy_name)
    if match:
        base = match.group(1)
        return f"{base}USDT"
    return "UNKNOWN"


def get_strategy_type(strategy_name):
    """Determine if strategy is spot (swing) or leverage (scalp)"""
    # Spot/swing strategies contain VOL or OBV
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
    else:
        return 'H4+Daily'


def calculate_metrics(closed_trades):
    """Calculate advanced metrics from closed trades"""
    if not closed_trades:
        return {
            'profit_factor': 0,
            'realized_rr': 0,
            'exit_target': 0,
            'exit_stop': 0,
            'exit_time': 0,
            'win_streak': 0,
            'loss_streak': 0,
            'avg_hold_time': 0,
            'avg_hold_unit': 'h'
        }
    
    # Profit Factor: total wins / total losses
    total_wins = sum(t['pnl'] for t in closed_trades if t.get('pnl', 0) > 0)
    total_losses = abs(sum(t['pnl'] for t in closed_trades if t.get('pnl', 0) < 0))
    profit_factor = total_wins / total_losses if total_losses > 0 else total_wins if total_wins > 0 else 0
    
    # Realized R:R: average win / average loss
    wins = [t['pnl'] for t in closed_trades if t.get('pnl', 0) > 0]
    losses = [abs(t['pnl']) for t in closed_trades if t.get('pnl', 0) < 0]
    avg_win = sum(wins) / len(wins) if wins else 0
    avg_loss = sum(losses) / len(losses) if losses else 0
    realized_rr = avg_win / avg_loss if avg_loss > 0 else avg_win if avg_win > 0 else 0
    
    # Exit Breakdown
    total = len(closed_trades)
    exit_target = sum(1 for t in closed_trades if t.get('exit_reason') in ['take_profit', 'TARGET', 'TP']) / total * 100 if total > 0 else 0
    exit_stop = sum(1 for t in closed_trades if t.get('exit_reason') in ['stop_loss', 'STOP', 'SL']) / total * 100 if total > 0 else 0
    exit_time = sum(1 for t in closed_trades if t.get('exit_reason') in ['time_stop', 'TIME', 'TIMEOUT']) / total * 100 if total > 0 else 0
    
    # Streaks
    win_streak = 0
    loss_streak = 0
    current_win = 0
    current_loss = 0
    for t in closed_trades:
        if t.get('pnl', 0) > 0:
            current_win += 1
            current_loss = 0
            win_streak = max(win_streak, current_win)
        else:
            current_loss += 1
            current_win = 0
            loss_streak = max(loss_streak, current_loss)
    
    # Average Hold Time
    hold_times = []
    for t in closed_trades:
        if t.get('entry_time') and t.get('exit_time'):
            try:
                entry = datetime.fromisoformat(t['entry_time'].replace('Z', '+00:00'))
                exit = datetime.fromisoformat(t['exit_time'].replace('Z', '+00:00'))
                hold_times.append((exit - entry).total_seconds() / 3600)  # hours
            except:
                pass
    
    avg_hold = sum(hold_times) / len(hold_times) if hold_times else 0
    if avg_hold >= 24:
        avg_hold_time = avg_hold / 24
        avg_hold_unit = 'd'
    else:
        avg_hold_time = avg_hold
        avg_hold_unit = 'h'
    
    return {
        'profit_factor': profit_factor,
        'realized_rr': realized_rr,
        'exit_target': exit_target,
        'exit_stop': exit_stop,
        'exit_time': exit_time,
        'win_streak': win_streak,
        'loss_streak': loss_streak,
        'avg_hold_time': avg_hold_time,
        'avg_hold_unit': avg_hold_unit
    }


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
    <title>DRYRUN v5.0 - Dynamic Dashboard</title>
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
            height: calc(100vh - 220px);
        }
        .left-panel {
            width: 420px;
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
        h1 { color: #f0f6fc; margin-bottom: 3px; font-size: 25px; }
        .subtitle { color: #67778E; margin-bottom: 10px; font-size: 13px; display: flex; gap: 15px; align-items: center; }
        .last-updated { color: #3CE3AB; }
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
            padding: 12px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .portfolio-balance { font-size: 29px; font-weight: normal; }
        .portfolio-pnl { font-size: 15px; margin-top: 3px; }
        .positive { color: #3CE3AB; }
        .negative { color: #F23674; }
        .neutral { color: #f0f6fc; }
        .warning-color { color: #F2A93B; }
        
        .risk-monitor {
            background: #0E1218;
            border: 1px solid #171E27;
            padding: 10px 12px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            font-size: 12px;
        }
        .risk-item { text-align: center; }
        .risk-label { color: #67778E; font-size: 10px; text-transform: uppercase; }
        .risk-value { font-size: 14px; margin-top: 2px; }
        
        .circuit-warning {
            padding: 10px 12px;
            margin-bottom: 10px;
            font-size: 13px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .warning-yellow {
            background: rgba(242, 169, 59, 0.15);
            border: 1px solid #F2A93B;
            color: #F2A93B;
        }
        .warning-red {
            background: rgba(242, 54, 116, 0.15);
            border: 1px solid #F23674;
            color: #F23674;
        }
        
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
        .strategy-pair { font-size: 12px; color: #67778E; margin-top: 1px; }
        .strategy-type {
            font-size: 10px;
            padding: 2px 6px;
            margin-left: 6px;
        }
        .type-leverage { background: #5a1a3a; color: #F23674; }
        .type-spot { background: #1a5a3a; color: #3CE3AB; }
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
            grid-template-columns: repeat(3, 1fr);
            gap: 6px;
            margin-bottom: 8px;
        }
        .stat-item {
            background: #171E27;
            padding: 6px;
        }
        .stat-label { font-size: 10px; color: #67778E; }
        .stat-value { font-size: 14px; font-weight: normal; margin-top: 1px; }
        
        .metrics-row {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 6px;
            margin-bottom: 8px;
        }
        .metric-item {
            background: #171E27;
            padding: 5px;
            text-align: center;
        }
        .metric-label { font-size: 9px; color: #67778E; text-transform: uppercase; }
        .metric-value { font-size: 12px; margin-top: 1px; }
        .metric-good { color: #3CE3AB; }
        .metric-ok { color: #f0f6fc; }
        .metric-bad { color: #F23674; }
        
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
            border-top: 1px solid #0E1218;
        }
        .position-detail { text-align: center; }
        .position-detail-label { font-size: 10px; color: #67778E; text-transform: uppercase; }
        .position-detail-value { font-size: 13px; font-weight: normal; margin-top: 1px; }
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
        <h1><span class="live-dot"></span>DRYRUN v5.0 Dashboard</h1>
        <div class="subtitle">
            <span>{{ strategies|length }} Strategies | ${{ "{:,.0f}".format(total_starting) }} Capital</span>
            <span class="last-updated">Updated: {{ last_updated }}</span>
        </div>
        
        {% if drawdown_pct <= -25 %}
        <div class="circuit-warning warning-red">
            🚨 CRITICAL: Portfolio drawdown at {{ "%.1f"|format(drawdown_pct) }}% - Consider pausing trading
        </div>
        {% elif drawdown_pct <= -15 %}
        <div class="circuit-warning warning-yellow">
            ⚠️ WARNING: Portfolio drawdown at {{ "%.1f"|format(drawdown_pct) }}% - Review performance
        </div>
        {% endif %}
        
        <div class="portfolio-summary">
            <div>
                <div class="portfolio-balance {{ 'positive' if total_pnl >= 0 else 'negative' }}">${{ "%.2f"|format(total_balance) }}</div>
                <div class="portfolio-pnl {{ 'positive' if total_pnl >= 0 else 'negative' }}">
                    {{ "+" if total_pnl >= 0 else "" }}${{ "%.2f"|format(total_pnl) }} ({{ "%.1f"|format(total_pnl_pct) }}%)
                </div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 24px; color: #8b949e;">{{ total_trades }}</div>
                <div style="font-size: 12px; color: #8b949e;">Total Trades</div>
            </div>
        </div>
        
        <div class="risk-monitor">
            <div class="risk-item">
                <div class="risk-label">Active Risk</div>
                <div class="risk-value {{ 'positive' if total_exposure > 0 else 'neutral' }}">${{ "%.0f"|format(total_exposure) }}</div>
            </div>
            <div class="risk-item">
                <div class="risk-label">Leverage</div>
                <div class="risk-value {{ 'negative' if leverage_exposure > 0 else 'neutral' }}">${{ "%.0f"|format(leverage_exposure) }}</div>
            </div>
            <div class="risk-item">
                <div class="risk-label">Spot</div>
                <div class="risk-value {{ 'positive' if spot_exposure > 0 else 'neutral' }}">${{ "%.0f"|format(spot_exposure) }}</div>
            </div>
            <div class="risk-item">
                <div class="risk-label">Portfolio PF</div>
                <div class="risk-value {{ 'metric-good' if portfolio_pf > 1.5 else 'metric-ok' if portfolio_pf >= 1.0 else 'metric-bad' }}">{{ "%.2f"|format(portfolio_pf) }}</div>
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
                                <div class="strategy-name">
                                    {{ data.name }}
                                    <span class="strategy-type type-{{ data.strat_type }}">{{ data.strat_type.upper() }}</span>
                                </div>
                                <div class="strategy-pair">{{ data.ws_symbol }}</div>
                            </div>
                            <div class="strategy-filters">{{ data.filters }}</div>
                        </div>
                        
                        <div class="live-price neutral" id="price-{{ strat_name }}">Loading...</div>
                        
                        <div class="strategy-stats">
                            <div class="stat-item">
                                <div class="stat-label">Balance</div>
                                <div class="stat-value {{ 'positive' if data.pnl >= 0 else 'negative' }}">${{ "%.0f"|format(data.balance) }}</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-label">P&L</div>
                                <div class="stat-value {{ 'positive' if data.pnl >= 0 else 'negative' }}">{{ "+" if data.pnl >= 0 else "" }}{{ "%.1f"|format(data.pnl_pct) }}%</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-label">Win Rate</div>
                                <div class="stat-value">{{ "%.0f"|format(data.win_rate) }}%</div>
                            </div>
                        </div>
                        
                        <div class="metrics-row">
                            <div class="metric-item">
                                <div class="metric-label">PF</div>
                                <div class="metric-value {{ 'metric-good' if data.metrics.profit_factor > 1.5 else 'metric-ok' if data.metrics.profit_factor >= 1.0 else 'metric-bad' }}">{{ "%.2f"|format(data.metrics.profit_factor) }}</div>
                            </div>
                            <div class="metric-item">
                                <div class="metric-label">R:R</div>
                                <div class="metric-value {{ 'metric-good' if data.metrics.realized_rr > 1.8 else 'metric-ok' if data.metrics.realized_rr >= 1.5 else 'metric-bad' }}">{{ "%.2f"|format(data.metrics.realized_rr) }}</div>
                            </div>
                            <div class="metric-item">
                                <div class="metric-label">Streaks</div>
                                <div class="metric-value"><span class="metric-good">{{ data.metrics.win_streak }}W</span>/<span class="metric-bad">{{ data.metrics.loss_streak }}L</span></div>
                            </div>
                            <div class="metric-item">
                                <div class="metric-label">Avg Hold</div>
                                <div class="metric-value">{{ "%.1f"|format(data.metrics.avg_hold_time) }}{{ data.metrics.avg_hold_unit }}</div>
                            </div>
                        </div>
                        
                        <div class="metrics-row">
                            <div class="metric-item">
                                <div class="metric-label">Target</div>
                                <div class="metric-value metric-good">{{ "%.0f"|format(data.metrics.exit_target) }}%</div>
                            </div>
                            <div class="metric-item">
                                <div class="metric-label">Stop</div>
                                <div class="metric-value metric-bad">{{ "%.0f"|format(data.metrics.exit_stop) }}%</div>
                            </div>
                            <div class="metric-item">
                                <div class="metric-label">Time</div>
                                <div class="metric-value warning-color">{{ "%.0f"|format(data.metrics.exit_time) }}%</div>
                            </div>
                            <div class="metric-item">
                                <div class="metric-label">Trades</div>
                                <div class="metric-value">{{ data.wins }}/{{ data.losses }}</div>
                            </div>
                        </div>
                        
                        <div class="position-box">
                            <div class="position-label">Position</div>
                            {% if data.position %}
                            <div class="position-status position-{{ data.position.direction }}">
                                {% if data.position.direction == 'long' %}↑{% else %}↓{% endif %} {{ data.position.direction.upper() }} @ ${{ "%.2f"|format(data.position.entry_price) }}
                                <span class="unrealized" id="unrealized-{{ strat_name }}">-</span>
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
            </div>
            
            <div class="right-panel">
                <div class="section-header">Recent Trades<span>({{ trades|length }})</span></div>
                <div class="scroll-content">
                {% if trades %}
                <table class="trades-table" id="trades-table">
                    <thead>
                        <tr>
                            <th>Pair</th>
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
                            <td>{{ trade.pair }}</td>
                            <td>{{ trade.strategy_name }}</td>
                            <td><span class="badge badge-{{ trade.direction }}">{{ trade.direction.upper() }}</span></td>
                            <td>${{ "%.2f"|format(trade.entry_price) }}</td>
                            <td>${{ "%.2f"|format(trade.exit_price) }}</td>
                            <td class="{{ 'positive' if trade.pnl >= 0 else 'negative' }}">{{ "+" if trade.pnl >= 0 else "" }}${{ "%.2f"|format(trade.pnl) }}</td>
                            <td><span class="badge badge-{{ 'win' if trade.pnl >= 0 else 'loss' }}">{{ 'WIN' if trade.pnl >= 0 else 'LOSS' }}</span></td>
                            <td>{% if trade.exit_time %}{{ trade.exit_time[8:10] }}.{{ trade.exit_time[5:7] }} {{ trade.exit_time[11:16] }}{% else %}-{% endif %}</td>
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
            <div>Auto-refresh: 60s | {{ strategies|length }} strategies | ${{ "{:,.0f}".format(starting_balance) }}/strategy</div>
        </div>
    </div>
    
    <script>
        const positions = {{ positions_json|safe }};
        const prices = {};
        let ws;
        
        function connectWebSocket() {
            const streams = {{ ws_streams|safe }};
            ws = new WebSocket('wss://stream.binance.com:9443/stream?streams=' + streams.join('/'));
            
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
                
                document.querySelectorAll('.strategy-card[data-symbol="' + symbol + '"]').forEach(function(card) {
                    const stratName = card.dataset.strat;
                    const priceEl = document.getElementById('price-' + stratName);
                    if (priceEl) {
                        const prev = parseFloat(priceEl.dataset.price) || price;
                        priceEl.textContent = '$' + price.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
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
        
        connectWebSocket();
        
        setTimeout(function() { location.reload(); }, 60000);
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
    all_closed_trades = []
    
    # Dynamically read strategies from state (skip keys starting with _)
    for strategy_name, strat_state in state.items():
        if strategy_name.startswith('_'):
            continue
        if not isinstance(strat_state, dict):
            continue
        if 'capital' not in strat_state:
            continue
        
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
        
        # Calculate metrics
        metrics = calculate_metrics(closed_trades)
        
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
        all_closed_trades.extend(closed_trades)
        
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
            'metrics': metrics,
        }
        
        if position:
            positions_json[strategy_name] = position
        
        # Collect trades for display
        pair = ws_symbol.replace('USDT', '/USDT')
        for trade in closed_trades:
            all_trades.append({
                'symbol': ws_symbol,
                'pair': pair,
                'strategy_name': display_name,
                'direction': trade.get('side', 'long').lower(),
                'entry_price': trade.get('entry_price', 0),
                'exit_price': trade.get('exit_price', 0),
                'pnl': trade.get('pnl', 0),
                'exit_time': trade.get('exit_time', '')
            })
    
    # Sort trades by exit time
    all_trades.sort(key=lambda x: x.get('exit_time', ''), reverse=True)
    
    # Calculate portfolio-level metrics
    total_starting = STARTING_BALANCE * len(strategies)
    total_pnl = total_balance - total_starting
    total_pnl_pct = (total_pnl / total_starting * 100) if total_starting > 0 else 0
    drawdown_pct = total_pnl_pct if total_pnl < 0 else 0
    
    # Portfolio Profit Factor
    portfolio_metrics = calculate_metrics(all_closed_trades)
    portfolio_pf = portfolio_metrics['profit_factor']
    
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
        drawdown_pct=drawdown_pct,
        portfolio_pf=portfolio_pf,
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
    for strategy_name, strat_state in state.items():
        if strategy_name.startswith('_'):
            continue
        if isinstance(strat_state, dict):
            all_trades.extend(strat_state.get('closed_trades', []))
    all_trades.sort(key=lambda x: x.get('exit_time', ''), reverse=True)
    return jsonify({'state': state, 'trades': all_trades[:20]})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5051, debug=False)
