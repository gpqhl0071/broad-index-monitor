"""内存行情缓存：后台定时刷新，接口只读缓存。"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx

from backend.config import REFRESH_INTERVAL_SEC
from backend.fetcher import fetch_quotes, get_provider_stats

logger = logging.getLogger(__name__)


@dataclass
class QuoteCache:
    items: list[dict[str, Any]] = field(default_factory=list)
    updated_at: datetime | None = None
    last_error: str | None = None
    last_provider: str | None = None
    last_provider_label: str | None = None
    used_fallback: bool = False
    fetch_count: int = 0
    error_count: int = 0
    _provider_stats: dict[str, Any] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def refresh_once(self, client: httpx.AsyncClient) -> None:
        try:
            items, meta = await fetch_quotes(client)
            stats = get_provider_stats()
            async with self._lock:
                self.items = items
                self.updated_at = datetime.now(timezone.utc)
                self.last_error = None
                self.last_provider = meta.get("provider")
                self.last_provider_label = meta.get("provider_label")
                self.used_fallback = meta.get("used_fallback", False)
                self.fetch_count += 1
                self._provider_stats = stats
        except Exception as e:
            async with self._lock:
                self.last_error = str(e)
                self.error_count += 1
            logger.warning("行情刷新失败: %s", e)

    async def snapshot(self) -> dict[str, Any]:
        async with self._lock:
            out = {
                "items": list(self.items),
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
                "last_error": self.last_error,
                "last_provider": self.last_provider,
                "last_provider_label": self.last_provider_label,
                "used_fallback": self.used_fallback,
                "fetch_count": self.fetch_count,
                "error_count": self.error_count,
                "refresh_interval_sec": REFRESH_INTERVAL_SEC,
            }
            if self._provider_stats:
                out["provider_stats"] = self._provider_stats
            return out


async def run_refresh_loop(cache: QuoteCache, stop: asyncio.Event) -> None:
    timeout = httpx.Timeout(12.0, connect=8.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        while not stop.is_set():
            await cache.refresh_once(client)
            try:
                await asyncio.wait_for(stop.wait(), timeout=REFRESH_INTERVAL_SEC)
                break
            except asyncio.TimeoutError:
                pass
