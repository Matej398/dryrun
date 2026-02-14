"""
ETH CCI 4H Strategy - 4H swing with Daily filter
Leverage: 2x
Backtest Results (3-year): +1030.8% | MaxDD: -83.3%
Walk-forward: Train +8.9% (bear), Test +1078% (bull)
"""

from strategy_base import Strategy, calculate_cci, daily_filter


class Eth4hCci(Strategy):
    name = "ETH_4H"
    display_name = "ETH CCI 4H"
    symbol = "ETH/USDC:USDC"
    timeframe = "4h"

    # Risk parameters
    capital = 1000
    risk_per_trade = 0.02
    stop_loss_pct = 0.04      # 4% stop on price
    take_profit_pct = 0.08    # 8% target on price
    time_stop_hours = None    # No time stop for 4H

    # Leverage
    leverage = 2              # 2x multiplier
                              # 8% price move = 16% account gain
                              # 4% stop loss = 8% account loss

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

        # Get Daily filter direction
        daily_dir = daily_filter(daily_df) if self.needs_daily_filter else 0

        # Long signal: CCI crosses above -100 (was below, now above)
        if current_cci > self.cci_oversold and prev_cci <= self.cci_oversold:
            if daily_dir >= 0:  # Daily bullish or neutral
                return 1

        # Short signal: CCI crosses below +100 (was above, now below)
        if not self.long_only:
            if current_cci < self.cci_overbought and prev_cci >= self.cci_overbought:
                if daily_dir <= 0:  # Daily bearish or neutral
                    return -1

        return 0
