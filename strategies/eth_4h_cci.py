"""ETH CCI 4H Strategy - 4H swing with Daily filter"""

from strategy_base import Strategy, calculate_cci, daily_filter


class Eth4hCci(Strategy):
    name = "ETH_4H"
    display_name = "ETH CCI 4H"
    symbol = "ETH/USDT"
    timeframe = "4h"

    stop_loss_pct = 0.04
    take_profit_pct = 0.08
    time_stop_hours = None  # No time stop for 4H
    long_only = False
    needs_daily_filter = True

    strategy_type = "leverage"
    filters_description = "4H+Daily"

    cci_oversold = -100
    cci_overbought = 100

    def check_signal(self, df, h4_df=None, daily_df=None):
        if len(df) < 25:
            return 0

        cci = calculate_cci(df)
        if len(cci) < 2:
            return 0

        current_cci = cci.iloc[-1]
        prev_cci = cci.iloc[-2]

        daily_dir = daily_filter(daily_df) if self.needs_daily_filter else 0

        # Long: CCI crosses above -100
        if current_cci > self.cci_oversold and prev_cci <= self.cci_oversold:
            if daily_dir >= 0:
                return 1

        # Short: CCI crosses below +100
        if not self.long_only:
            if current_cci < self.cci_overbought and prev_cci >= self.cci_overbought:
                if daily_dir <= 0:
                    return -1

        return 0
