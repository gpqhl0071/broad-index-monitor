"""天气：Open-Meteo 代理（免 Key），支持坐标或客户端 IP 粗定位。"""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
REVERSE_GEO_URL = "https://api.bigdatacloud.net/data/reverse-geocode-client"

# WMO 天气代码 → 中文简述
WMO_LABELS: dict[int, str] = {
    0: "晴",
    1: "晴",
    2: "多云",
    3: "阴",
    45: "雾",
    48: "雾",
    51: "小雨",
    53: "小雨",
    55: "小雨",
    56: "冻雨",
    57: "冻雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    66: "冻雨",
    67: "冻雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "雪",
    80: "阵雨",
    81: "阵雨",
    82: "暴雨",
    85: "阵雪",
    86: "阵雪",
    95: "雷雨",
    96: "雷雨",
    99: "雷雨",
}

DEFAULT_LAT = 39.9042
DEFAULT_LON = 116.4074
DEFAULT_CITY = "北京"


def wmo_label(code: Optional[int]) -> str:
    if code is None:
        return "—"
    return WMO_LABELS.get(int(code), "未知")


def _weekday_zh(iso_date: str) -> str:
    from datetime import datetime

    d = datetime.strptime(iso_date, "%Y-%m-%d")
    names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    return names[d.weekday()]


async def _reverse_geocode(client: httpx.AsyncClient, lat: float, lon: float) -> str:
    try:
        r = await client.get(
            REVERSE_GEO_URL,
            params={"latitude": lat, "longitude": lon, "localityLanguage": "zh"},
        )
        r.raise_for_status()
        data = r.json()
        for key in ("city", "locality", "principalSubdivision"):
            name = data.get(key)
            if name:
                return str(name)
    except Exception as e:
        logger.warning("reverse geocode failed: %s", e)
    return DEFAULT_CITY


async def resolve_coords_from_ip(client: httpx.AsyncClient, client_ip: str) -> tuple[float, float, str]:
    """根据客户端 IP 粗定位；失败则回退默认坐标。"""
    if not client_ip or client_ip in ("127.0.0.1", "::1"):
        return DEFAULT_LAT, DEFAULT_LON, DEFAULT_CITY
    try:
        r = await client.get(
            f"http://ip-api.com/json/{client_ip}",
            params={"fields": "status,lat,lon,city", "lang": "zh-CN"},
        )
        r.raise_for_status()
        data = r.json()
        if data.get("status") == "success":
            return float(data["lat"]), float(data["lon"]), data.get("city") or DEFAULT_CITY
    except Exception as e:
        logger.warning("ip geolocation failed: %s", e)
    return DEFAULT_LAT, DEFAULT_LON, DEFAULT_CITY


async def fetch_weather(
    lat: float,
    lon: float,
    city_hint: Optional[str] = None,
) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=12.0) as client:
        geo_task = _reverse_geocode(client, lat, lon)
        forecast_r = await client.get(
            FORECAST_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,weather_code",
                "daily": "weather_code,temperature_2m_max,temperature_2m_min",
                "timezone": "auto",
                "forecast_days": 8,
            },
        )
        forecast_r.raise_for_status()
        payload = forecast_r.json()
        city = city_hint or await geo_task

    current = payload.get("current") or {}
    daily = payload.get("daily") or {}
    dates = daily.get("time") or []
    codes = daily.get("weather_code") or []
    tmax = daily.get("temperature_2m_max") or []
    tmin = daily.get("temperature_2m_min") or []

    days: list[dict[str, Any]] = []
    for i, d in enumerate(dates[:8]):
        days.append(
            {
                "date": d,
                "weekday": _weekday_zh(d),
                "label": wmo_label(codes[i] if i < len(codes) else None),
                "code": codes[i] if i < len(codes) else None,
                "temp_max": round(tmax[i], 0) if i < len(tmax) and tmax[i] is not None else None,
                "temp_min": round(tmin[i], 0) if i < len(tmin) and tmin[i] is not None else None,
                "is_today": i == 0,
            }
        )

    cur_temp = current.get("temperature_2m")
    cur_code = current.get("weather_code")

    return {
        "city": city,
        "latitude": lat,
        "longitude": lon,
        "current": {
            "temperature": round(cur_temp, 0) if cur_temp is not None else None,
            "label": wmo_label(cur_code),
            "code": cur_code,
        },
        "days": days,
    }
