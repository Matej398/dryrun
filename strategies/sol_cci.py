"""SOL CCI Extreme Strategy - same logic as ETH CCI"""

from strategies._eth_cci import EthCci


class SolCci(EthCci):
    name = "SOL_CCI"
    display_name = "SOL CCI Extreme"
    symbol = "SOL/USDC:USDC"
