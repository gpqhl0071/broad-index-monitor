"""腾讯 ifzq 单票接口：并行 fqkline，与 qt.gtimg 分流。"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from backend.config import QUOTE_ITEMS, QuoteItem
from backend.providers.base import QuoteProvider, build_base_row, market_prefix

HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://gu.qq.com/"}
API = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"


def _row_from_qt(item: QuoteItem, qt: list[Any]) -> dict[str, Any] | None:
    if len(qt) < 6:
        return None
    try:
        price = float(qt[3])
        pre_close = float(qt[4])
        open_p = float(qt[5])
    except (TypeError, ValueError):
        return None

    row = build_base_row(item, full_name=str(qt[1]) if len(qt) > 1 else item.name)
    row.update(
        {
            "price": price,
            "pre_close": pre_close,
            "open": open_p,
            "amount": float(qt[9]) if len(qt) > 9 and qt[9] not in ("", None) else None,
        }
    )
    return row


class TencentIfzqProvider(QuoteProvider):
    name = "tencent_ifzq"
    label = "腾讯财经·IFZQ"

    async def _fetch_one(self, client: httpx.AsyncClient, item: QuoteItem) -> dict[str, Any] | None:
        sym = f"{market_prefix(item)}{item.code}"
        params = {"param": f"{sym},day,,,1,qfq", "app": "web"}
        resp = await client.get(API, params=params, headers=HEADERS, timeout=10.0)
        resp.raise_for_status()
        body = resp.json()
        block = (body.get("data") or {}).get(sym)
        if not block:
            return None
        qt = (block.get("qt") or {}).get(sym)
        if not qt:
            return None
        return _row_from_qt(item, qt)

    async def fetch(self, client: httpx.AsyncClient) -> list[dict[str, Any]]:
        tasks = [self._fetch_one(client, item) for item in QUOTE_ITEMS]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        rows: list[dict[str, Any]] = []
        for r in results:
            if isinstance(r, Exception):
                raise r
            if r:
                rows.append(r)
        if len(rows) < len(QUOTE_ITEMS) * 0.8:
            raise RuntimeError(f"IFZQ 返回条数不足: {len(rows)}/{len(QUOTE_ITEMS)}")
        return self.finalize(rows)
