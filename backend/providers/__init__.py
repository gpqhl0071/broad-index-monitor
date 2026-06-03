from backend.providers.eastmoney import eastmoney_batch
from backend.providers.eastmoney_single import EastMoneySingleProvider
from backend.providers.sina import SinaProvider
from backend.providers.tencent import TencentProvider
from backend.providers.tencent_ifzq import TencentIfzqProvider

PROVIDERS = [
    eastmoney_batch("eastmoney", "东方财富", "https://push2.eastmoney.com"),
    eastmoney_batch("eastmoney_delay", "东方财富·延时", "https://push2delay.eastmoney.com"),
    eastmoney_batch("eastmoney_his", "东方财富·His", "https://push2his.eastmoney.com"),
    EastMoneySingleProvider(),
    SinaProvider(),
    TencentProvider(),
    TencentIfzqProvider(),
]

PROVIDER_LABELS = {p.name: p.label for p in PROVIDERS}
