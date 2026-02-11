"""
Strategy Base Class + Shared Helpers

All strategies inherit from Strategy and implement check_signal().
Shared infrastructure: filters, indicators.
"""

from abc import ABC, abstractmethod
import re
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import CCIIndicator


class Strategy(ABC):
    """
    Base class for all trading strategies.

    Subclasses MUST set:
        name, display_name, symbol, timeframe

    Subclasses MUST implement:
        check_signal(df, h4_df, daily_df) -> 1 (LONG), -1 (SHORT), 0 (none)
    """

    # --- Required (subclass MUST override) ---
    name: str = NotImplemented
    display_name: str = NotImplemented
    symbol: str = NotImplemented
    timeframe: str = NotImplemented

    # --- Optional with defaults ---
    enabled: bool = True
    capital: int = 1000
    risk_per_trade: float = 0.02
    stop_loss_pct: float = 0.01
    take_profit_pct: float = 0.02
    time_stop_hours = 48  # int or None
    leverage: int = 1
    long_only: bool = False
    needs_h4_filter: bool = False
    needs_daily_filter: bool = False
    strategy_type: str = "leverage"
    filters_description: str = ""

    # --- Dynamic exit support ---
    dynamic_exit: bool = False  # If True, TP is recalculated every cycle

    @abstractmethod
    def check_signal(self, df, h4_df=None, daily_df=None):
        """Return 1 (LONG), -1 (SHORT), or 0 (no signal)."""
        ...

    def update_take_profit(self, df, position):
        """Override in subclass to return dynamic TP price.
        Called every exit check cycle when dynamic_exit=True.
        Return None to keep existing TP unchanged."""
        return None

    def get_config_dict(self) -> dict:
        """Return config dict compatible with open_position/close_position."""
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'enabled': self.enabled,
            'capital': self.capital,
            'risk_per_trade': self.risk_per_trade,
            'stop_loss_pct': self.stop_loss_pct,
            'take_profit_pct': self.take_profit_pct,
            'time_stop_hours': self.time_stop_hours,
            'use_h4_filter': self.needs_h4_filter,
            'use_daily_filter': self.needs_daily_filter,
            'long_only': self.long_only,
            'leverage': self.leverage,
        }

    def get_dashboard_metadata(self) -> dict:
        """Return metadata for dashboard display."""
        match = re.match(r'^([A-Z]+)_', self.name)
        ws_symbol = f"{match.group(1)}USDT" if match else "UNKNOWN"
        return {
            'name': self.display_name,
            'ws_symbol': ws_symbol,
            'strategy_type': self.strategy_type,
            'filters_description': self.filters_description,
            'leverage': round((self.risk_per_trade / self.stop_loss_pct) * self.leverage),
        }


# =============================================================================
# SHARED FILTERS
# =============================================================================

def h4_filter(h4_df):
    """H4 candle direction: 1 (bullish), -1 (bearish), 0 (neutral)."""
    if h4_df is None or len(h4_df) == 0:
        return 0
    latest = h4_df.iloc[-1]
    if latest['close'] > latest['open']:
        return 1
    elif latest['close'] < latest['open']:
        return -1
    return 0


def daily_filter(daily_df):
    """Daily candle direction: 1 (bullish), -1 (bearish), 0 (neutral)."""
    if daily_df is None or len(daily_df) == 0:
        return 0
    latest = daily_df.iloc[-1]
    if latest['close'] > latest['open']:
        return 1
    elif latest['close'] < latest['open']:
        return -1
    return 0


# =============================================================================
# SHARED INDICATOR HELPERS
# =============================================================================

def calculate_rsi(df, window=14):
    """Calculate RSI indicator."""
    return RSIIndicator(df['close'], window=window).rsi()


def calculate_cci(df, window=20):
    """Calculate CCI indicator."""
    return CCIIndicator(df['high'], df['low'], df['close'], window=window).cci()


def calculate_obv(df):
    """Calculate On-Balance Volume."""
    obv = [0]
    for i in range(1, len(df)):
        if df['close'].iloc[i] > df['close'].iloc[i - 1]:
            obv.append(obv[-1] + df['volume'].iloc[i])
        elif df['close'].iloc[i] < df['close'].iloc[i - 1]:
            obv.append(obv[-1] - df['volume'].iloc[i])
        else:
            obv.append(obv[-1])
    return obv


def calculate_bollinger_bands(df, period=20, std_dev=2):
    """Calculate Bollinger Bands. Returns (sma, upper, lower) as Series."""
    sma = df['close'].rolling(period).mean()
    std = df['close'].rolling(period).std()
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    return sma, upper, lower


def calculate_atr(df, period=14):
    """Calculate Average True Range."""
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift(1)).abs()
    low_close = (df['low'] - df['close'].shift(1)).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(period).mean()
