"""BNB OBV Divergence Strategy - Daily swing, long-only"""

from strategy_base import Strategy, calculate_obv


class BnbObv(Strategy):
    name = "BNB_OBV"
    display_name = "BNB OBV Divergence"
    symbol = "BNB/USDT"
    timeframe = "1d"

    risk_per_trade = 1.0
    stop_loss_pct = 0.05
    take_profit_pct = 0.15
    time_stop_hours = None
    long_only = True

    strategy_type = "spot"
    filters_description = "Daily + LONG-ONLY"

    obv_lookback = 10

    def check_signal(self, df, h4_df=None, daily_df=None):
        if len(df) < self.obv_lookback + 2:
            return 0

        obv = calculate_obv(df)

        price_down = df['close'].iloc[-1] < df['close'].iloc[-self.obv_lookback - 1]
        obv_up = obv[-1] > obv[-self.obv_lookback - 1]

        if price_down and obv_up:
            return 1

        return 0
