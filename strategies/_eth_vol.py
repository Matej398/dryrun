"""ETH Volume Surge Strategy - same logic as BTC Volume Surge"""

from strategies.btc_vol import BtcVol


class EthVol(BtcVol):
    name = "ETH_VOL"
    display_name = "ETH Volume Surge"
    symbol = "ETH/USDT"
