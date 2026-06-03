"""新浪财经 hq.sinajs.cn 行情。"""

from __future__ import annotations

import re
from typing import Any

import httpx

from backend.config import QUOTE_ITEMS, QuoteItem
from backend.providers.base import QuoteProvider, build_base_row, market_prefix

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://finance.sina.com.cn",
}

_LINE_RE = re.compile(r'var hq_str_(\w+)="([^"]*)"', re.UNICODE)


class SinaProvider(QuoteProvider):
    name = "sina"
    label = "新浪财经"

    def _symbol_map(self) -> dict[str, QuoteItem]:
        return {f"{market_prefix(q)}{q.code}": q for q in QUOTE_ITEMS}

    async def fetch(self, client: httpx.AsyncClient) -> list[dict[str, Any]]:
        symbols = ",".join(f"{market_prefix(q)}{q.code}" for q in QUOTE_ITEMS)
        url = f"https://hq.sinajs.cn/list={symbols}"

        resp = await client.get(url, headers=HEADERS, timeout=12.0)
        resp.raise_for_status()
        text = resp.content.decode("gbk", errors="replace")

        sym_map = self._symbol_map()
        rows: list[dict[str, Any]] = []

        for match in _LINE_RE.finditer(text):
            sym, payload = match.group(1), match.group(2)
            item = sym_map.get(sym)
            if not item or not payload:
                continue
            parts = payload.split(",")
            if len(parts) < 10:
                continue

            try:
                open_p = float(parts[1])
                pre_close = float(parts[2])
                price = float(parts[3])
                high = float(parts[4])
                low = float(parts[5])
                amount = float(parts[9])
            except ValueError:
                continue

            row = build_base_row(item, full_name=parts[0] or item.name)
            row.update(
                {
                    "price": price,
                    "open": open_p,
                    "pre_close": pre_close,
                    "high": high,
                    "low": low,
                    "amount": amount,
                }
            )
            rows.append(row)

        if len(rows) < len(QUOTE_ITEMS) * 0.8:
            raise RuntimeError(f"Sina 返回条数不足: {len(rows)}/{len(QUOTE_ITEMS)}")
        return self.finalize(rows)
