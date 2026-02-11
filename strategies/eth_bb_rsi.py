"""ETH Bollinger Band + RSI Mean Reversion - 15m scalp with dynamic BB exit"""

from strategy_base import Strategy, calculate_rsi, calculate_bollinger_bands, h4_filter
import pandas as pd


class EthBbRsi(Strategy):
    name = "ETH_BB_RSI"
    display_name = "ETH BB+RSI MeanRev"
    symbol = "ETH/USDT"
    timeframe = "15m"

    stop_loss_pct = 0.01
    take_profit_pct = 0.02
    time_stop_hours = 48
    long_only = False
    needs_h4_filter = True

    strategy_type = "leverage"
    filters_description = "H4 + BB MeanRev"
    dynamic_exit = True

    rsi_period = 6
    rsi_oversold = 30
    rsi_overbought = 70
    bb_period = 20
    bb_std = 2

    def check_signal(self, df, h4_df=None, daily_df=None):
        if len(df) < 30:
            return 0

        rsi = calculate_rsi(df, window=self.rsi_period)
        sma, upper_bb, lower_bb = calculate_bollinger_bands(df, self.bb_period, self.bb_std)

        current_rsi = rsi.iloc[-1]
        current_close = df['close'].iloc[-1]
        current_lower = lower_bb.iloc[-1]
        current_upper = upper_bb.iloc[-1]

        if self.needs_h4_filter and h4_df is not None:
            h4_dir = h4_filter(h4_df)
        else:
            h4_dir = 0

        if current_close < current_lower and current_rsi < self.rsi_oversold:
            if h4_dir >= 0:
                return 1

        if current_close > current_upper and current_rsi > self.rsi_overbought:
            if h4_dir <= 0:
                return -1

        return 0

    def update_take_profit(self, df, position):
        if len(df) < self.bb_period:
            return None
        sma, _, _ = calculate_bollinger_bands(df, self.bb_period, self.bb_std)
        current_sma = sma.iloc[-1]
        if current_sma is None or pd.isna(current_sma):
            return None
        return float(current_sma)
