"""ADA CCI Extreme Strategy - same logic as ETH CCI"""

from strategies._eth_cci import EthCci


class AdaCci(EthCci):
    name = "ADA_CCI"
    display_name = "ADA CCI Extreme"
    symbol = "ADA/USDC:USDC"
