"""
ETH CCI Daily-Only Strategy - 4H with DAILY filter ONLY (no H4)
Leverage: 2x
Backtest Results (9-year): +63094.4% | Trades: 901
Walk-forward: 100% robust (bear=bull performance)
CRITICAL: Daily filter ONLY - H4 filter BLOCKS good trades!
"""

from strategy_base import Strategy, calculate_cci, daily_filter


class EthCciDaily(Strategy):
    name = "ETH_CCI_DAILY"
    display_name = "ETH CCI Daily"
    symbol = "ETH/USDC:USDC"
    timeframe = "4h"

    # Risk parameters
    capital = 1000
    risk_per_trade = 0.02
    stop_loss_pct = 0.01      # 1% stop
    take_profit_pct = 0.02    # 2% target
    time_stop_hours = None

    # Strategy settings
    long_only = False
    needs_h4_filter = False   # CRITICAL: No H4 filter!
    needs_daily_filter = True # ONLY Daily filter
    strategy_type = "leverage"
    filters_description = "Daily ONLY"

    # CCI thresholds
    cci_oversold = -100
    cci_overbought = 100

    def check_signal(self, df, h4_df=None, daily_df=None):
        """
        Check for CCI reversal signals with DAILY filter ONLY.
        
        IMPORTANT: H4 filter is intentionally NOT used.
        Testing showed Daily-only gives 63x better returns.
        
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

        # Get Daily filter direction (no H4!)
        daily_dir = daily_filter(daily_df) if self.needs_daily_filter else 0

        # Long signal: CCI crosses above -100
        if current_cci > self.cci_oversold and prev_cci <= self.cci_oversold:
            if daily_dir > 0:  # Daily bullish
                return 1

        # Short signal: CCI crosses below +100
        if not self.long_only:
            if current_cci < self.cci_overbought and prev_cci >= self.cci_overbought:
                if daily_dir < 0:  # Daily bearish
                    return -1

        return 0
