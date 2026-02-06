"""ETH CCI Extreme Strategy - 15m scalp with H4+Daily filter"""

from strategy_base import Strategy, calculate_cci, h4_filter, daily_filter


class EthCci(Strategy):
    name = "ETH_CCI"
    display_name = "ETH CCI Extreme"
    symbol = "ETH/USDT"
    timeframe = "15m"

    stop_loss_pct = 0.01
    take_profit_pct = 0.02
    time_stop_hours = 48
    long_only = False
    needs_h4_filter = True
    needs_daily_filter = True

    strategy_type = "leverage"
    filters_description = "H4+Daily"

    cci_oversold = -100
    cci_overbought = 100

    def check_signal(self, df, h4_df=None, daily_df=None):
        if len(df) < 25:
            return 0

        cci = calculate_cci(df)
        current_cci = cci.iloc[-1]
        prev_cci = cci.iloc[-2]

        h4_dir = h4_filter(h4_df) if self.needs_h4_filter else 0
        daily_dir = daily_filter(daily_df) if self.needs_daily_filter else 0

        # Long: CCI crosses above -100
        if current_cci > self.cci_oversold and prev_cci <= self.cci_oversold:
            if (not self.needs_h4_filter or h4_dir >= 0) and \
               (not self.needs_daily_filter or daily_dir >= 0):
                return 1

        # Short: CCI crosses below +100
        if not self.long_only:
            if current_cci < self.cci_overbought and prev_cci >= self.cci_overbought:
                if (not self.needs_h4_filter or h4_dir <= 0) and \
                   (not self.needs_daily_filter or daily_dir <= 0):
                    return -1

        return 0
