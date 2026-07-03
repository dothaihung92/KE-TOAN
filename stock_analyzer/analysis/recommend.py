"""
Kết hợp điểm kỹ thuật (signals.py) và điểm cảm xúc tin tức (sentiment.py)
thành một khuyến nghị cuối cùng, kèm giải thích.

CẢNH BÁO: Đây là công cụ hỗ trợ tham khảo dựa trên quy tắc đơn giản,
KHÔNG PHẢI khuyến nghị đầu tư chuyên nghiệp. Người dùng tự chịu trách
nhiệm với quyết định đầu tư của mình.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .sentiment import aggregate_sentiment
from .signals import TechnicalSignal

TECHNICAL_WEIGHT = 0.7
NEWS_WEIGHT = 0.3

LABELS = [
    (0.5, "MUA MẠNH"),
    (0.15, "MUA"),
    (-0.15, "GIỮ / THEO DÕI"),
    (-0.5, "BÁN"),
    (float("-inf"), "BÁN MẠNH"),
]


def label_for_score(score: float) -> str:
    for threshold, label in LABELS:
        if score >= threshold:
            return label
    return "GIỮ / THEO DÕI"


@dataclass
class Recommendation:
    symbol: str
    label: str
    combined_score: float
    technical_score: float
    news_score: float
    reasons: List[str] = field(default_factory=list)
    news_count: int = 0
    technical_details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "label": self.label,
            "combined_score": self.combined_score,
            "technical_score": self.technical_score,
            "news_score": self.news_score,
            "reasons": self.reasons,
            "news_count": self.news_count,
            "technical_details": self.technical_details,
        }


def build_recommendation(
    symbol: str,
    technical: TechnicalSignal,
    news_headlines: List[str],
) -> Recommendation:
    news_score = aggregate_sentiment(news_headlines)
    combined = round(
        technical.score * TECHNICAL_WEIGHT + news_score * NEWS_WEIGHT, 3
    )
    label = label_for_score(combined)

    reasons = list(technical.reasons)
    if news_headlines:
        if news_score > 0.15:
            reasons.append(f"Tin tức gần đây thiên hướng tích cực ({len(news_headlines)} tin)")
        elif news_score < -0.15:
            reasons.append(f"Tin tức gần đây thiên hướng tiêu cực ({len(news_headlines)} tin)")

    if not reasons:
        reasons.append("Không có tín hiệu nổi bật, thị trường trung lập")

    return Recommendation(
        symbol=symbol,
        label=label,
        combined_score=combined,
        technical_score=technical.score,
        news_score=news_score,
        reasons=reasons,
        news_count=len(news_headlines),
        technical_details=technical.details,
    )
