"""东方财富 push2 批量行情（多节点）。"""

from __future__ import annotations

from typing import Any

import httpx

from backend.config import QUOTE_ITEMS, QuoteItem
from backend.providers.base import QuoteProvider, build_base_row

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://quote.eastmoney.com/",
}

FIELDS = "f2,f3,f4,f6,f7,f12,f14,f17,f18,f15,f16"


class EastMoneyBatchProvider(QuoteProvider):
    """push2 ulist.np 批量接口，可配置不同 CDN 节点。"""

    def __init__(self, name: str, label: str, host: str) -> None:
        self.name = name
        self.label = label
        self.host = host.rstrip("/")

    async def fetch(self, client: httpx.AsyncClient) -> list[dict[str, Any]]:
        meta = {q.code: q for q in QUOTE_ITEMS}
        secids = ",".join(q.secid for q in QUOTE_ITEMS)
        url = f"{self.host}/api/qt/ulist.np/get"
        params = {"fltt": "2", "fields": FIELDS, "secids": secids}

        resp = await client.get(url, params=params, headers=HEADERS, timeout=12.0)
        resp.raise_for_status()
        body = resp.json()
        if body.get("rc") != 0:
            raise RuntimeError(f"{self.label} rc={body.get('rc')}")

        rows: list[dict[str, Any]] = []
        for raw in (body.get("data") or {}).get("diff") or []:
            code = raw.get("f12")
            if not code or code not in meta:
                continue
            item = meta[code]
            price = raw.get("f2")
            if price == "-":
                price = None
            row = build_base_row(item, full_name=raw.get("f14") or item.name)
            row.update(
                {
                    "price": price,
                    "change_pct": raw.get("f3"),
                    "change_amt": raw.get("f4"),
                    "open": raw.get("f17"),
                    "pre_close": raw.get("f18"),
                    "amount": raw.get("f6"),
                    "amplitude": raw.get("f7"),
                    "high": raw.get("f15"),
                    "low": raw.get("f16"),
                }
            )
            rows.append(row)

        if len(rows) < len(QUOTE_ITEMS) * 0.8:
            raise RuntimeError(f"{self.label} 返回条数不足: {len(rows)}/{len(QUOTE_ITEMS)}")
        return self.finalize(rows)


def eastmoney_batch(name: str, label: str, host: str) -> EastMoneyBatchProvider:
    return EastMoneyBatchProvider(name, label, host)
