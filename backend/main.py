"""国内宽指基金行情服务。"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.cache import QuoteCache, run_refresh_loop
from backend.history import fetch_history
from backend.weather import fetch_weather, resolve_coords_from_ip

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
cache = QuoteCache()


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop = asyncio.Event()
    task = asyncio.create_task(run_refresh_loop(cache, stop))
    yield
    stop.set()
    await task


app = FastAPI(title="国内宽指基金行情", lifespan=lifespan)


@app.get("/api/quotes")
async def get_quotes():
    return await cache.snapshot()


@app.post("/api/quotes/refresh")
async def refresh_quotes():
    timeout = httpx.Timeout(12.0, connect=8.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        await cache.refresh_once(client)
    return await cache.snapshot()


@app.get("/api/history")
async def history(code: str = Query(..., min_length=6, max_length=6), days: int = Query(7, ge=1, le=30)):
    try:
        timeout = httpx.Timeout(10.0, connect=6.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            return await fetch_history(client, code, days=days)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@app.get("/api/health")
async def health():
    snap = await cache.snapshot()
    ok = snap["updated_at"] is not None and len(snap["items"]) > 0
    return {"status": "ok" if ok else "degraded", **snap}


@app.get("/api/weather")
async def weather(
    request: Request,
    lat: Optional[float] = Query(None, ge=-90, le=90),
    lon: Optional[float] = Query(None, ge=-180, le=180),
):
    city_hint = None
    if lat is None or lon is None:
        client_ip = request.client.host if request.client else ""
        async with httpx.AsyncClient(timeout=8.0) as client:
            lat, lon, city_hint = await resolve_coords_from_ip(client, client_ip)
    return await fetch_weather(lat, lon, city_hint=city_hint)


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
