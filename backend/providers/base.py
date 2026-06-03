"""行情数据源抽象与行数据规范化。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx

from backend.config import QUOTE_ITEMS, QuoteItem


def market_prefix(item: QuoteItem) -> str:
    return "sh" if item.market == 1 else "sz"


def sort_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    order = {q.code: i for i, q in enumerate(QUOTE_ITEMS)}
    rows.sort(key=lambda r: order.get(r["code"], 999))
    return rows


def build_base_row(item: QuoteItem, *, full_name: str | None = None) -> dict[str, Any]:
    return {
        "code": item.code,
        "exchange": market_prefix(item),
        "group": item.group,
        "kind": item.kind,
        "name": item.name,
        "index_name": item.index_name,
        "full_name": full_name or item.name,
        "price": None,
        "change_pct": None,
        "change_amt": None,
        "open": None,
        "pre_close": None,
        "amount": None,
        "amplitude": None,
    }


def enrich_row(row: dict[str, Any]) -> dict[str, Any]:
    """缺失涨跌幅时根据现价与昨收计算。"""
    price = _to_float(row.get("price"))
    pre = _to_float(row.get("pre_close"))
    high = _to_float(row.get("high"))
    low = _to_float(row.get("low"))

    if row.get("change_pct") is None and price is not None and pre not in (None, 0):
        row["change_pct"] = round((price - pre) / pre * 100, 2)
    if row.get("change_amt") is None and price is not None and pre is not None:
        digits = 2 if row.get("kind") == "index" else 3
        row["change_amt"] = round(price - pre, digits)
    if row.get("amplitude") is None and high is not None and low is not None and pre not in (None, 0):
        row["amplitude"] = round((high - low) / pre * 100, 2)
    return row


def _to_float(v: Any) -> float | None:
    if v is None or v == "" or v == "-":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


class QuoteProvider(ABC):
    name: str
    label: str

    @abstractmethod
    async def fetch(self, client: httpx.AsyncClient) -> list[dict[str, Any]]:
        pass

    def finalize(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        for row in rows:
            enrich_row(row)
            row["source"] = self.name
        return sort_rows(rows)
