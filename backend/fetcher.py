"""多数据源轮询拉取：主源按轮询切换，失败时自动尝试其他源。"""

from __future__ import annotations

import logging
from itertools import cycle
from typing import Any

import httpx

from backend.config import QUOTE_ITEMS
from backend.providers import PROVIDERS, PROVIDER_LABELS
from backend.providers.base import QuoteProvider

logger = logging.getLogger(__name__)

_provider_cycle = cycle(PROVIDERS)
_stats: dict[str, int] = {"success": 0, "fallback": 0, "fail": 0}


def _provider_stats_snapshot() -> dict[str, Any]:
    return {
        "providers": [p.name for p in PROVIDERS],
        "provider_labels": PROVIDER_LABELS,
        "last_provider": _stats.get("last_provider"),
        "last_provider_label": PROVIDER_LABELS.get(_stats.get("last_provider", ""), ""),
        "success_count": _stats.get("success", 0),
        "fallback_count": _stats.get("fallback", 0),
        "fail_count": _stats.get("fail", 0),
    }


async def _try_provider(provider: QuoteProvider, client: httpx.AsyncClient) -> list[dict[str, Any]]:
    last_err: Exception | None = None
    for attempt in range(2):
        try:
            rows = await provider.fetch(client)
            if len(rows) < max(1, int(len(QUOTE_ITEMS) * 0.8)):
                raise RuntimeError(f"{provider.label} 数据不完整")
            return rows
        except Exception as e:
            last_err = e
            if attempt == 0:
                logger.debug("%s 第 1 次失败，重试: %s", provider.label, e)
    assert last_err is not None
    raise last_err


async def fetch_quotes(client: httpx.AsyncClient) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    每次刷新优先使用轮询到的数据源；失败则依次尝试其余源。
    返回 (行情列表, 拉取元信息)。
    """
    primary: QuoteProvider = next(_provider_cycle)
    order = [primary] + [p for p in PROVIDERS if p is not primary]
    errors: list[str] = []

    for i, provider in enumerate(order):
        try:
            rows = await _try_provider(provider, client)
            meta = {
                "provider": provider.name,
                "provider_label": provider.label,
                "used_fallback": i > 0,
            }
            _stats["last_provider"] = provider.name
            if i == 0:
                _stats["success"] = _stats.get("success", 0) + 1
            else:
                _stats["fallback"] = _stats.get("fallback", 0) + 1
                logger.info("主源 %s 失败，已切换至 %s", primary.label, provider.label)
            return rows, meta
        except Exception as e:
            errors.append(f"{provider.label}: {e}")
            logger.warning("数据源 %s 失败: %s", provider.label, e)

    _stats["fail"] = _stats.get("fail", 0) + 1
    raise RuntimeError("; ".join(errors))


def get_provider_stats() -> dict[str, Any]:
    return _provider_stats_snapshot()
