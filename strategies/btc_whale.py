"""BTC Whale Candle Follow - 15m with H4 filter, 5:1 RR"""

import pandas as pd
import numpy as np
from strategy_base import Strategy, calculate_atr, h4_filter


class BtcWhale(Strategy):
    name = "BTC_WHALE"
    display_name = "BTC Whale Candle"
    symbol = "BTC/USDT"
    timeframe = "15m"

    stop_loss_pct = 0.01       # 1% SL
    take_profit_pct = 0.05     # 5% TP (5:1 RR)
    time_stop_hours = 96       # 4 days (bigger target needs more time)
    long_only = False
    needs_h4_filter = True

    strategy_type = "leverage"
    filters_description = "H4 + Whale"

    # Whale candle detection params
    atr_mult = 2.5        # Body must be > 2.5x ATR
    vol_mult = 2.0        # Volume must be > 2x average
    body_ratio_min = 0.7  # Body/range ratio (conviction)
    lookback = 20         # Period for ATR and volume average

    def check_signal(self, df, h4_df=None, daily_df=None):
        if len(df) < self.lookback + 5:
            return 0

        # Calculate ATR and volume average
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift(1)).abs()
        low_close = (df['low'] - df['close'].shift(1)).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(self.lookback).mean()

        vol_avg = df['volume'].rolling(self.lookback).mean()

        # Check the PREVIOUS closed candle (iloc[-1] is latest closed after strip)
        prev = df.iloc[-1]
        prev_atr = atr.iloc[-2]  # ATR before the candle (avoid lookahead)
        prev_vol_avg = vol_avg.iloc[-2]

        if pd.isna(prev_atr) or pd.isna(prev_vol_avg) or prev_vol_avg == 0:
            return 0

        body = abs(prev['close'] - prev['open'])
        rng = prev['high'] - prev['low']

        if rng == 0:
            return 0

        body_ratio = body / rng

        # Whale candle conditions: large body + high volume + strong conviction
        if (body > prev_atr * self.atr_mult and
            prev['volume'] > prev_vol_avg * self.vol_mult and
            body_ratio > self.body_ratio_min):

            # Determine direction
            is_bullish = prev['close'] > prev['open']

            # Apply H4 filter
            if self.needs_h4_filter and h4_df is not None:
                h4_dir = h4_filter(h4_df)
                if is_bullish and h4_dir > 0:
                    return 1
                elif not is_bullish and h4_dir < 0:
                    return -1
                return 0  # Filtered out
            else:
                return 1 if is_bullish else -1

        return 0
