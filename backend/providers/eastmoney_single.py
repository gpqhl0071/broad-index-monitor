"""东方财富单票接口：并行请求 stock/get，与批量 ulist 分流。"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from backend.config import QUOTE_ITEMS, QuoteItem
from backend.providers.base import QuoteProvider, build_base_row

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://quote.eastmoney.com/",
}

STOCK_FIELDS = "f43,f44,f45,f46,f47,f48,f57,f58,f60,f169,f170,f171"
HOSTS = (
    "https://push2.eastmoney.com",
    "https://push2delay.eastmoney.com",
    "https://88.push2.eastmoney.com",
)


def _scale_price(raw: Any, kind: str) -> float | None:
    if raw is None:
        return None
    v = float(raw)
    return round(v / 100, 2) if kind == "index" else round(v / 1000, 3)


def _scale_optional(raw: Any, kind: str) -> float | None:
    if raw is None:
        return None
    return _scale_price(raw, kind)


class EastMoneySingleProvider(QuoteProvider):
    name = "eastmoney_single"
    label = "东方财富·单票"

    async def _fetch_one(
        self, client: httpx.AsyncClient, item: QuoteItem, host: str
    ) -> dict[str, Any] | None:
        url = f"{host}/api/qt/stock/get"
        params = {"secid": item.secid, "fields": STOCK_FIELDS}
        resp = await client.get(url, params=params, headers=HEADERS, timeout=10.0)
        resp.raise_for_status()
        raw = (resp.json().get("data") or {})
        if not raw:
            return None

        row = build_base_row(item, full_name=raw.get("f58") or item.name)
        kind = item.kind
        row.update(
            {
                "price": _scale_price(raw.get("f43"), kind),
                "open": _scale_optional(raw.get("f46"), kind),
                "pre_close": _scale_optional(raw.get("f60"), kind),
                "high": _scale_optional(raw.get("f44"), kind),
                "low": _scale_optional(raw.get("f45"), kind),
                "amount": raw.get("f48"),
                "change_pct": float(raw["f170"]) / 100 if raw.get("f170") is not None else None,
                "change_amt": _scale_optional(raw.get("f169"), kind),
            }
        )
        return row

    async def fetch(self, client: httpx.AsyncClient) -> list[dict[str, Any]]:
        last_err: Exception | None = None
        for host in HOSTS:
            try:
                tasks = [self._fetch_one(client, item, host) for item in QUOTE_ITEMS]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                rows: list[dict[str, Any]] = []
                for r in results:
                    if isinstance(r, Exception):
                        raise r
                    if r:
                        rows.append(r)
                if len(rows) < len(QUOTE_ITEMS) * 0.8:
                    raise RuntimeError(f"仅 {len(rows)}/{len(QUOTE_ITEMS)} 条")
                return self.finalize(rows)
            except Exception as e:
                last_err = e
        raise last_err or RuntimeError("东方财富单票全部节点失败")
