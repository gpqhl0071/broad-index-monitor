"""最近 N 个交易日 K 线（腾讯 fqkline）。"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from backend.config import QUOTE_ITEMS, QuoteItem
from backend.providers.base import market_prefix

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://gu.qq.com/"}
API = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"

_CODE_MAP: dict[str, QuoteItem] = {q.code: q for q in QUOTE_ITEMS}
_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_CACHE_TTL_SEC = 300


def _parse_bars(raw: list[list[Any]]) -> list[dict[str, Any]]:
    """腾讯日 K：[日期, 开盘, 收盘, 最高, 最低, 成交量]。"""
    bars: list[dict[str, Any]] = []
    for row in raw:
        if len(row) < 6:
            continue
        try:
            bars.append(
                {
                    "date": str(row[0]),
                    "open": float(row[1]),
                    "close": float(row[2]),
                    "high": float(row[3]),
                    "low": float(row[4]),
                    "volume": float(row[5]),
                }
            )
        except (TypeError, ValueError):
            continue
    return bars


def _with_change_pct(bars: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, bar in enumerate(bars):
        row = dict(bar)
        if i > 0:
            prev_close = bars[i - 1]["close"]
            if prev_close:
                row["change_pct"] = round((bar["close"] - prev_close) / prev_close * 100, 2)
        out.append(row)
    return out


async def fetch_history(
    client: httpx.AsyncClient,
    code: str,
    *,
    days: int = 7,
) -> dict[str, Any]:
    item = _CODE_MAP.get(code)
    if not item:
        raise ValueError(f"未知代码: {code}")

    cache_key = f"{code}:{days}"
    now = time.monotonic()
    cached = _CACHE.get(cache_key)
    if cached and now - cached[0] < _CACHE_TTL_SEC:
        return cached[1]

    sym = f"{market_prefix(item)}{item.code}"
    need = days + 1
    params = {"param": f"{sym},day,,,{need},qfq", "app": "web"}
    resp = await client.get(API, params=params, headers=HEADERS, timeout=10.0)
    resp.raise_for_status()
    block = (resp.json().get("data") or {}).get(sym) or {}
    raw = block.get("qfqday") or block.get("day") or []
    parsed = _parse_bars(raw)
    if len(parsed) < 2:
        raise RuntimeError("历史行情条数不足")

    recent = _with_change_pct(parsed[-need:])[-days:]
    recent.reverse()

    payload = {
        "code": item.code,
        "name": item.name,
        "index_name": item.index_name,
        "kind": item.kind,
        "days": days,
        "items": recent,
    }
    _CACHE[cache_key] = (now, payload)
    return payload
