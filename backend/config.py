"""行情标的配置：按上证 / 深证 / 科创 / 海外分组。"""

from dataclasses import dataclass
from typing import Literal

Kind = Literal["index", "fund"]
Group = Literal["sh", "sz", "kc", "us", "hk"]

GROUP_ORDER: list[Group] = ["sh", "sz", "kc", "us", "hk"]
GROUP_LABELS: dict[Group, str] = {
    "sh": "上证",
    "sz": "深证",
    "kc": "科创",
    "us": "美股",
    "hk": "港股",
}


@dataclass(frozen=True)
class QuoteItem:
    code: str
    market: int  # 1=上交所, 0=深交所
    name: str
    index_name: str
    kind: Kind = "fund"
    group: Group = "sh"

    @property
    def secid(self) -> str:
        return f"{self.market}.{self.code}"


# ---------- 上证：大盘指数 + 上交所宽基 ETF ----------
SH_ITEMS: list[QuoteItem] = [
    QuoteItem("000001", 1, "上证指数", "上证综合", "index", "sh"),
    QuoteItem("510300", 1, "沪深300ETF", "沪深300", "fund", "sh"),
    QuoteItem("510500", 1, "中证500ETF", "中证500", "fund", "sh"),
    QuoteItem("510050", 1, "上证50ETF", "上证50", "fund", "sh"),
    QuoteItem("560010", 1, "中证1000ETF", "中证1000", "fund", "sh"),
    QuoteItem("563300", 1, "中证2000ETF", "中证2000", "fund", "sh"),
    QuoteItem("510880", 1, "红利ETF", "上证红利", "fund", "sh"),
    QuoteItem("515180", 1, "红利低波ETF", "红利低波", "fund", "sh"),
    QuoteItem("512100", 1, "中证1000ETF(广)", "中证1000", "fund", "sh"),
    QuoteItem("562060", 1, "中证A50ETF", "中证A50", "fund", "sh"),
]

# ---------- 深证：大盘指数 + 创业板等深交所 ETF ----------
SZ_ITEMS: list[QuoteItem] = [
    QuoteItem("399001", 0, "深证成指", "深证综合", "index", "sz"),
    QuoteItem("159915", 0, "创业板ETF", "创业板指", "fund", "sz"),
    QuoteItem("159949", 0, "创业板50ETF", "创业板50", "fund", "sz"),
]

# ---------- 科创：科创板 ETF ----------
KC_ITEMS: list[QuoteItem] = [
    QuoteItem("588000", 1, "科创50ETF", "科创50", "fund", "kc"),
]

# ---------- 美股：QDII 场内 ETF（上交所） ----------
US_ITEMS: list[QuoteItem] = [
    QuoteItem("513100", 1, "纳指ETF", "纳斯达克100", "fund", "us"),
    QuoteItem("513500", 1, "标普500ETF", "标普500", "fund", "us"),
]

# ---------- 港股：QDII 场内 ETF（上交所） ----------
HK_ITEMS: list[QuoteItem] = [
    QuoteItem("513130", 1, "恒生科技ETF", "恒生科技", "fund", "hk"),
    QuoteItem("513060", 1, "恒生医疗ETF", "恒生医疗", "fund", "hk"),
]

QUOTE_ITEMS: list[QuoteItem] = SH_ITEMS + SZ_ITEMS + KC_ITEMS + US_ITEMS + HK_ITEMS

REFRESH_INTERVAL_SEC = 10
