"""AVAX Whale Candle Follow - 15m with H4 filter, 5:1 RR"""

import pandas as pd
import numpy as np
from strategy_base import Strategy, calculate_atr, h4_filter


class AvaxWhale(Strategy):
    name = "AVAX_WHALE"
    display_name = "AVAX Whale Candle"
    symbol = "AVAX/USDT"
    timeframe = "15m"

    stop_loss_pct = 0.01
    take_profit_pct = 0.05
    time_stop_hours = 96
    long_only = False
    needs_h4_filter = True

    strategy_type = "leverage"
    filters_description = "H4 + Whale"

    atr_mult = 2.5
    vol_mult = 2.0
    body_ratio_min = 0.7
    lookback = 20

    def check_signal(self, df, h4_df=None, daily_df=None):
        if len(df) < self.lookback + 5:
            return 0

        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift(1)).abs()
        low_close = (df['low'] - df['close'].shift(1)).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(self.lookback).mean()
        vol_avg = df['volume'].rolling(self.lookback).mean()

        prev = df.iloc[-1]
        prev_atr = atr.iloc[-2]
        prev_vol_avg = vol_avg.iloc[-2]

        if pd.isna(prev_atr) or pd.isna(prev_vol_avg) or prev_vol_avg == 0:
            return 0

        body = abs(prev['close'] - prev['open'])
        rng = prev['high'] - prev['low']
        if rng == 0:
            return 0

        body_ratio = body / rng

        if (body > prev_atr * self.atr_mult and
            prev['volume'] > prev_vol_avg * self.vol_mult and
            body_ratio > self.body_ratio_min):

            is_bullish = prev['close'] > prev['open']

            if self.needs_h4_filter and h4_df is not None:
                h4_dir = h4_filter(h4_df)
                if is_bullish and h4_dir > 0:
                    return 1
                elif not is_bullish and h4_dir < 0:
                    return -1
                return 0
            else:
                return 1 if is_bullish else -1

        return 0
