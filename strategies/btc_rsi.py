"""BTC RSI Extreme Strategy - Long-only 15m scalp"""

from strategy_base import Strategy, calculate_rsi, h4_filter


class BtcRsi(Strategy):
    name = "BTC_RSI"
    display_name = "BTC RSI Extreme"
    symbol = "BTC/USDT"
    timeframe = "15m"

    stop_loss_pct = 0.01
    take_profit_pct = 0.02
    time_stop_hours = 48
    long_only = True
    needs_h4_filter = True

    strategy_type = "leverage"
    filters_description = "H4 + LONG-ONLY"

    rsi_oversold = 30

    def check_signal(self, df, h4_df=None, daily_df=None):
        if len(df) < 20:
            return 0

        rsi = calculate_rsi(df)
        current_rsi = rsi.iloc[-1]
        prev_rsi = rsi.iloc[-2]

        # H4 filter: block longs when bearish
        if self.needs_h4_filter:
            h4_dir = h4_filter(h4_df)
            if h4_dir < 0:
                return 0

        # Long signal: RSI crosses above oversold
        if current_rsi > self.rsi_oversold and prev_rsi <= self.rsi_oversold:
            return 1

        return 0
