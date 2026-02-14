"""
BNB Volume Breakout 6/3 Strategy - 4H with H4+Daily filters
Leverage: 2x
Backtest Results (9-year): +833.6% | Trades: 493
20-period breakout + 1.5x volume surge
"""

from strategy_base import Strategy, h4_filter, daily_filter


class BnbVol63(Strategy):
    name = "BNB_VOL_6_3"
    display_name = "BNB VOL 6/3"
    symbol = "BNB/USDC:USDC"
    timeframe = "4h"

    # Risk parameters
    capital = 1000
    risk_per_trade = 0.02
    stop_loss_pct = 0.03      # 3% stop
    take_profit_pct = 0.06    # 6% target (2:1 RR)
    time_stop_hours = None

    # Strategy settings
    long_only = False
    needs_h4_filter = True
    needs_daily_filter = True
    strategy_type = "leverage"
    filters_description = "H4+Daily+Volume"

    # Volume breakout parameters
    lookback = 20
    volume_multiplier = 1.5

    def check_signal(self, df, h4_df=None, daily_df=None):
        """
        Volume breakout strategy:
        - Price breaks 20-period high/low
        - Volume > 1.5x average
        - H4 and Daily filters aligned
        
        Returns:
            1 = LONG signal
            -1 = SHORT signal
            0 = No signal
        """
        if len(df) < self.lookback + 5:
            return 0

        # Calculate 20-period high/low and volume average
        high_20 = df['high'].rolling(window=self.lookback).max().iloc[-2]
        low_20 = df['low'].rolling(window=self.lookback).min().iloc[-2]
        avg_volume = df['volume'].rolling(window=self.lookback).mean().iloc[-2]

        current = df.iloc[-1]
        current_close = current['close']
        current_volume = current['volume']

        # Get filter directions
        h4_dir = h4_filter(h4_df) if self.needs_h4_filter else 0
        daily_dir = daily_filter(daily_df) if self.needs_daily_filter else 0

        # Check volume surge
        volume_surge = current_volume > (avg_volume * self.volume_multiplier)

        if not volume_surge:
            return 0

        # Long signal: breakout above high with volume
        if current_close > high_20:
            if h4_dir > 0 and daily_dir > 0:  # Both bullish
                return 1

        # Short signal: breakout below low with volume
        if not self.long_only:
            if current_close < low_20:
                if h4_dir < 0 and daily_dir < 0:  # Both bearish
                    return -1

        return 0
