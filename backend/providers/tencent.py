"""腾讯财经 qt.gtimg.cn 行情。"""

from __future__ import annotations

import re
from typing import Any

import httpx

from backend.config import QUOTE_ITEMS, QuoteItem
from backend.providers.base import QuoteProvider, build_base_row, market_prefix

HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://gu.qq.com/"}

_LINE_RE = re.compile(r'v_(\w+)="([^"]*)"', re.UNICODE)


class TencentProvider(QuoteProvider):
    name = "tencent"
    label = "腾讯财经"

    def _symbol_map(self) -> dict[str, QuoteItem]:
        return {f"{market_prefix(q)}{q.code}": q for q in QUOTE_ITEMS}

    async def fetch(self, client: httpx.AsyncClient) -> list[dict[str, Any]]:
        symbols = ",".join(f"{market_prefix(q)}{q.code}" for q in QUOTE_ITEMS)
        url = f"https://qt.gtimg.cn/q={symbols}"

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

            main, _, tail = payload.partition("~~")
            parts = main.split("~")
            if len(parts) < 6:
                continue

            try:
                price = float(parts[3])
                pre_close = float(parts[4])
                open_p = float(parts[5])
            except ValueError:
                continue

            change_amt = change_pct = high = low = amount = None
            if tail:
                t = tail.split("~")
                if len(t) >= 5:
                    try:
                        change_amt = float(t[1])
                        change_pct = float(t[2])
                        high = float(t[3])
                        low = float(t[4])
                    except ValueError:
                        pass
                if len(t) >= 6 and "/" in t[5]:
                    try:
                        amount = float(t[5].split("/")[-1])
                    except ValueError:
                        pass

            row = build_base_row(item, full_name=parts[1] or item.name)
            row.update(
                {
                    "price": price,
                    "pre_close": pre_close,
                    "open": open_p,
                    "change_amt": change_amt,
                    "change_pct": change_pct,
                    "high": high,
                    "low": low,
                    "amount": amount,
                }
            )
            rows.append(row)

        if len(rows) < len(QUOTE_ITEMS) * 0.8:
            raise RuntimeError(f"Tencent 返回条数不足: {len(rows)}/{len(QUOTE_ITEMS)}")
        return self.finalize(rows)
