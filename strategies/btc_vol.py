"""BTC Volume Surge Strategy - Daily swing, long-only"""

from strategy_base import Strategy


class BtcVol(Strategy):
    name = "BTC_VOL"
    display_name = "BTC Volume Surge"
    symbol = "BTC/USDC:USDC"
    timeframe = "1d"

    risk_per_trade = 0.03
    stop_loss_pct = 0.03
    take_profit_pct = 0.10
    time_stop_hours = None
    long_only = True

    strategy_type = "spot"
    filters_description = "Daily + LONG-ONLY"

    volume_mult = 2.0
    price_change_pct = 0.02

    def check_signal(self, df, h4_df=None, daily_df=None):
        if len(df) < 21:
            return 0

        current_volume = df['volume'].iloc[-1]
        volume_ma = df['volume'].rolling(20).mean().iloc[-1]
        price_change = (df['close'].iloc[-1] / df['close'].iloc[-2]) - 1

        if current_volume > (volume_ma * self.volume_mult) and price_change > self.price_change_pct:
            return 1

        return 0
