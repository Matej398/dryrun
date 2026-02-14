"""
BTC CCI Strategy - 4H with H4+Daily filters
Leverage: 2x
Backtest Results (9-year): +6655.2% | Trades: 784
Walk-forward validated
"""

from strategy_base import Strategy, calculate_cci, h4_filter, daily_filter


class BtcCci(Strategy):
    name = "BTC_CCI"
    display_name = "BTC CCI"
    symbol = "BTC/USDC:USDC"
    timeframe = "4h"

    # Risk parameters
    capital = 1000
    risk_per_trade = 0.02
    stop_loss_pct = 0.01      # 1% stop
    take_profit_pct = 0.02    # 2% target
    time_stop_hours = None

    # Strategy settings
    long_only = False
    needs_h4_filter = True
    needs_daily_filter = True
    strategy_type = "leverage"
    filters_description = "H4+Daily"

    # CCI thresholds
    cci_oversold = -100
    cci_overbought = 100

    def check_signal(self, df, h4_df=None, daily_df=None):
        """
        Check for CCI reversal signals with H4 and Daily filters.
        
        Returns:
            1 = LONG signal
            -1 = SHORT signal
            0 = No signal
        """
        if len(df) < 25:
            return 0

        # Calculate CCI
        cci = calculate_cci(df)
        if len(cci) < 2:
            return 0

        current_cci = cci.iloc[-1]
        prev_cci = cci.iloc[-2]

        # Get filter directions
        h4_dir = h4_filter(h4_df) if self.needs_h4_filter else 0
        daily_dir = daily_filter(daily_df) if self.needs_daily_filter else 0

        # Long signal: CCI crosses above -100
        if current_cci > self.cci_oversold and prev_cci <= self.cci_oversold:
            if h4_dir > 0 and daily_dir > 0:  # Both bullish
                return 1

        # Short signal: CCI crosses below +100
        if not self.long_only:
            if current_cci < self.cci_overbought and prev_cci >= self.cci_overbought:
                if h4_dir < 0 and daily_dir < 0:  # Both bearish
                    return -1

        return 0
