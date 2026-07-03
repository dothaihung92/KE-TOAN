"""
Chấm điểm tín hiệu kỹ thuật từ các chỉ báo đã tính (xem indicators.py).

Mỗi chỉ báo được chấm điểm trong khoảng [-1, 1]:
    -1  = tín hiệu bán mạnh
     0  = trung lập
    +1  = tín hiệu mua mạnh

Điểm tổng hợp là trung bình có trọng số. Đây là quy tắc rõ ràng, dễ giải
thích - không phải khuyến nghị đầu tư chuyên nghiệp.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import pandas as pd


@dataclass
class TechnicalSignal:
    score: float  # [-1, 1]
    reasons: List[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)


def _clip(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def score_trend(row: pd.Series) -> tuple[float, str | None]:
    close, sma20, sma50 = row.get("close"), row.get("sma20"), row.get("sma50")
    if pd.isna(sma20) or pd.isna(sma50):
        return 0.0, None
    if close > sma20 > sma50:
        return 1.0, "Giá > MA20 > MA50: xu hướng tăng rõ ràng"
    if close < sma20 < sma50:
        return -1.0, "Giá < MA20 < MA50: xu hướng giảm rõ ràng"
    if close > sma20:
        return 0.4, "Giá đang ở trên MA20"
    if close < sma20:
        return -0.4, "Giá đang ở dưới MA20"
    return 0.0, None


def score_rsi(row: pd.Series) -> tuple[float, str | None]:
    r = row.get("rsi14")
    if pd.isna(r):
        return 0.0, None
    if r < 30:
        return 0.8, f"RSI={r:.0f}: vùng quá bán, có thể hồi phục"
    if r > 70:
        return -0.8, f"RSI={r:.0f}: vùng quá mua, rủi ro điều chỉnh"
    # Tuyến tính hoá quanh vùng trung lập 30-70, tâm 50
    return _clip((50 - r) / 20 * 0.3), None


def score_macd(row: pd.Series) -> tuple[float, str | None]:
    macd_line, signal_line, hist = row.get("macd"), row.get("macd_signal"), row.get("macd_hist")
    if pd.isna(macd_line) or pd.isna(signal_line):
        return 0.0, None
    if macd_line > signal_line and hist > 0:
        return 0.7, "MACD cắt lên đường tín hiệu: động lượng tăng"
    if macd_line < signal_line and hist < 0:
        return -0.7, "MACD cắt xuống đường tín hiệu: động lượng giảm"
    return 0.0, None


def score_bollinger(row: pd.Series) -> tuple[float, str | None]:
    close, upper, lower = row.get("close"), row.get("bb_upper"), row.get("bb_lower")
    if pd.isna(upper) or pd.isna(lower):
        return 0.0, None
    if close <= lower:
        return 0.6, "Giá chạm dải Bollinger dưới: có thể đảo chiều tăng"
    if close >= upper:
        return -0.6, "Giá chạm dải Bollinger trên: có thể đảo chiều giảm"
    return 0.0, None


def score_volume(row: pd.Series, trend_score: float) -> tuple[float, str | None]:
    vol, vol_avg = row.get("volume"), row.get("vol_avg20")
    if pd.isna(vol_avg) or vol_avg == 0:
        return 0.0, None
    ratio = vol / vol_avg
    if ratio < 1.3:
        return 0.0, None
    # Khối lượng đột biến khuếch đại tín hiệu xu hướng hiện tại
    boost = _clip(0.3 * (ratio - 1))
    direction = 1 if trend_score >= 0 else -1
    return direction * boost, f"Khối lượng gấp {ratio:.1f}x trung bình 20 phiên, xác nhận tín hiệu"


WEIGHTS = {
    "trend": 0.3,
    "rsi": 0.2,
    "macd": 0.25,
    "bollinger": 0.15,
    "volume": 0.1,
}


def compute_signal(df_with_indicators: pd.DataFrame) -> TechnicalSignal:
    """Tính tín hiệu kỹ thuật cho phiên gần nhất trong DataFrame."""
    if df_with_indicators.empty:
        return TechnicalSignal(score=0.0, reasons=["Không có dữ liệu giá"])

    row = df_with_indicators.iloc[-1]

    trend_s, trend_r = score_trend(row)
    rsi_s, rsi_r = score_rsi(row)
    macd_s, macd_r = score_macd(row)
    bb_s, bb_r = score_bollinger(row)
    vol_s, vol_r = score_volume(row, trend_s)

    total = (
        trend_s * WEIGHTS["trend"]
        + rsi_s * WEIGHTS["rsi"]
        + macd_s * WEIGHTS["macd"]
        + bb_s * WEIGHTS["bollinger"]
        + vol_s * WEIGHTS["volume"]
    )
    total = _clip(total)

    reasons = [r for r in (trend_r, rsi_r, macd_r, bb_r, vol_r) if r]

    return TechnicalSignal(
        score=round(total, 3),
        reasons=reasons,
        details={
            "trend": round(trend_s, 3),
            "rsi": round(rsi_s, 3),
            "macd": round(macd_s, 3),
            "bollinger": round(bb_s, 3),
            "volume": round(vol_s, 3),
            "close": row.get("close"),
            "rsi14": row.get("rsi14"),
        },
    )
