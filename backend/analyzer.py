"""行情分析与信号生成：把专业数据翻译成普通人语言。"""

from __future__ import annotations

import time
from typing import Any

from backend.history import _CACHE as HISTORY_CACHE


def _get_cached_bars(code: str, days: int = 7) -> list[dict[str, Any]] | None:
    """读取历史K线缓存（如已有）。"""
    key = f"{code}:{days}"
    cached = HISTORY_CACHE.get(key)
    if not cached:
        key = f"{code}:30"
        cached = HISTORY_CACHE.get(key)
    if not cached:
        return None
    ts, payload = cached
    # 缓存 5 分钟有效
    if time.monotonic() - ts > 300:
        return None
    return payload.get("items", [])


def _calc_ma(bars: list[dict[str, Any]], n: int) -> float | None:
    """计算N日均线。bars[0]为最新。"""
    if len(bars) < n:
        return None
    closes = [b["close"] for b in bars[:n]]
    return sum(closes) / len(closes)


def quick_analyze(row: dict[str, Any]) -> dict[str, Any]:
    """
    基于当日快照的快分析（不需要历史数据）。
    用于表格内"信号"列的快速展示。
    """
    change_pct = row.get("change_pct")
    amplitude = row.get("amplitude")

    if change_pct is None:
        return {
            "signal": "unknown",
            "signal_text": "数据不足",
            "trend_text": "—",
            "summary": "暂无分析数据",
            "risk": "unknown",
            "icon": "⚪",
            "details": [],
        }

    cp = float(change_pct)
    amp = float(amplitude) if amplitude else 0

    # 基础判断
    if cp > 3:
        trend_text = "强势上涨"
        signal = "caution"
        signal_text = "不宜追高"
        summary = "今日大涨超 3%，短期情绪偏热，不建议此时追涨"
        risk = "high"
        icon = "🟠"
    elif cp > 1.5:
        trend_text = "温和上涨"
        signal = "hold"
        signal_text = "继续持有"
        summary = "今日温和上涨，趋势向好，可安心持有"
        risk = "low"
        icon = "🟢"
    elif cp > -1.5:
        trend_text = "震荡整理"
        signal = "hold"
        signal_text = "观望为主"
        summary = "今日窄幅震荡，方向不明，建议多看少动"
        risk = "medium"
        icon = "🟡"
    elif cp > -3:
        trend_text = "短期回调"
        signal = "watch"
        signal_text = "逢低关注"
        summary = "今日回调较深，若连续调整可考虑分批布局"
        risk = "medium"
        icon = "🟡"
    else:
        trend_text = "大幅下跌"
        signal = "caution"
        signal_text = "注意风险"
        summary = "今日大跌超 3%，市场情绪较差，注意控制仓位"
        risk = "high"
        icon = "🔴"

    # 振幅修正描述
    if amp > 4:
        if cp > 0:
            summary += "，日内波动剧烈，小心获利盘回吐"
        else:
            summary += "，日内波动剧烈，恐慌情绪可能已释放"
    elif amp > 2.5:
        summary += "，日内分歧较大"

    return {
        "signal": signal,
        "signal_text": signal_text,
        "trend_text": trend_text,
        "summary": summary,
        "risk": risk,
        "icon": icon,
        "details": [],
    }


def deep_analyze(code: str, row: dict[str, Any]) -> dict[str, Any]:
    """
    基于历史K线的深度分析（用于悬停详情）。
    """
    result = quick_analyze(row)
    details: list[str] = []
    cp = float(row.get("change_pct") or 0)
    current_price = row.get("price")

    bars = _get_cached_bars(code, days=7)
    if not bars or len(bars) < 3:
        result["details"] = ["历史数据不足，以上仅基于当日行情判断"]
        return result

    # 均线分析
    ma5 = _calc_ma(bars, 5)
    ma10 = _calc_ma(bars, 10) if len(bars) >= 10 else None

    if ma5 and current_price:
        if current_price > ma5 * 1.01:
            details.append("价格站在5日均线上方，短期走势偏强")
        elif current_price < ma5 * 0.99:
            details.append("价格跌破5日均线，短期走势偏弱")

    if ma5 and ma10:
        if ma5 > ma10 * 1.005:
            details.append("5日均线向上穿过10日均线，中期趋势向好")
        elif ma5 < ma10 * 0.995:
            details.append("5日均线向下穿过10日均线，中期趋势偏弱")

    # 近N日涨跌统计
    check_days = min(5, len(bars))
    up_days = 0
    down_days = 0
    for i in range(check_days):
        pct = bars[i].get("change_pct")
        if pct is None:
            continue
        if pct > 0:
            up_days += 1
        elif pct < 0:
            down_days += 1

    if up_days >= 4:
        details.append(f"近{check_days}日有{up_days}天上涨，短期势头不错")
    elif down_days >= 4:
        details.append(f"近{check_days}日有{down_days}天下跌，短期承压明显")
    else:
        details.append(f"近{check_days}日涨跌互现，处于震荡整理阶段")

    # 成交量分析（近5日 vs 再前5日）
    if len(bars) >= 6:
        recent_vol = sum(b.get("volume", 0) for b in bars[:5]) / 5
        older_vol = sum(b.get("volume", 0) for b in bars[5:10]) / max(1, len(bars[5:10]))
        if older_vol > 0:
            ratio = recent_vol / older_vol
            if ratio > 1.5:
                details.append("近期成交量明显放大，资金关注度提升")
            elif ratio < 0.7:
                details.append("近期成交量萎缩，市场关注度下降")

    # 基于连续走势修正信号
    if down_days >= 3 and cp < -1.5:
        result["signal"] = "buy"
        result["signal_text"] = "逢低关注"
        result["icon"] = "🟢"
        result[
            "summary"
        ] = "连续多日调整后今日再跌，短期或已进入可布局区间，建议分批关注"
        result["risk"] = "medium"
    elif up_days >= 3 and cp > 2:
        result["signal"] = "caution"
        result["signal_text"] = "不追高"
        result["icon"] = "🟠"
        result[
            "summary"
        ] = "连续多日上涨后今日加速，短期或有回调压力，切勿追涨"
        result["risk"] = "high"
    elif down_days >= 3 and cp > -0.5:
        result["signal"] = "watch"
        result["signal_text"] = "可能企稳"
        result["icon"] = "🟡"
        result["summary"] = "连续调整后今日跌幅收窄，可能逐步企稳，可保持关注"
        result["risk"] = "low"

    result["details"] = details
    return result
