"""AVAX CCI Extreme Strategy - same logic as ETH CCI"""

from strategies.eth_cci import EthCci


class AvaxCci(EthCci):
    name = "AVAX_CCI"
    display_name = "AVAX CCI Extreme"
    symbol = "AVAX/USDT"
