"""
Chấm điểm cảm xúc (tích cực/tiêu cực) cho tiêu đề tin tức tài chính tiếng Việt.

Cách tiếp cận: từ điển từ khoá (lexicon-based). Đơn giản, không cần mô hình
học máy hay gọi API ngoài, dễ kiểm chứng và mở rộng thêm từ khoá.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable, List


POSITIVE_KEYWORDS = [
    "tăng trưởng", "tăng mạnh", "tăng vọt", "bứt phá", "lãi lớn", "lãi kỷ lục",
    "vượt kế hoạch", "lợi nhuận tăng", "doanh thu tăng", "khả quan", "tích cực",
    "trúng thầu", "hưởng lợi", "kỳ vọng", "mua ròng", "cổ tức cao", "chia cổ tức",
    "niêm yết mới", "phá đỉnh", "đột phá", "vượt đỉnh", "thặng dư", "mở rộng",
    "ký kết hợp đồng", "xuất khẩu tăng", "nâng hạng", "nâng dự báo", "khởi sắc",
    "phục hồi", "kỷ lục", "top đầu ngành", "dẫn đầu",
]

NEGATIVE_KEYWORDS = [
    "giảm mạnh", "giảm sàn", "lao dốc", "thua lỗ", "lỗ nặng", "nợ xấu",
    "bán tháo", "bán ròng", "cảnh báo", "huỷ niêm yết", "hủy niêm yết",
    "đình chỉ", "thanh tra", "điều tra", "phạt", "sai phạm", "thao túng",
    "rút vốn", "phá sản", "vỡ nợ", "áp lực", "suy giảm", "tiêu cực",
    "rủi ro", "hạ dự báo", "hạ bậc tín nhiệm", "kiểm soát đặc biệt",
    "cắt margin", "call margin", "giải chấp", "dừng giao dịch", "khó khăn",
    "sụt giảm", "downgrade",
]


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"\s+", " ", text)
    return text


@dataclass
class HeadlineSentiment:
    text: str
    score: float  # [-1, 1]
    matched_positive: List[str]
    matched_negative: List[str]


def score_headline(text: str) -> HeadlineSentiment:
    norm = _normalize(text or "")
    pos = [kw for kw in POSITIVE_KEYWORDS if kw in norm]
    neg = [kw for kw in NEGATIVE_KEYWORDS if kw in norm]
    raw = len(pos) - len(neg)
    if raw == 0:
        score = 0.0
    else:
        denom = max(len(pos) + len(neg), 1)
        score = max(-1.0, min(1.0, raw / denom))
    return HeadlineSentiment(text=text, score=score, matched_positive=pos, matched_negative=neg)


def score_headlines(texts: Iterable[str]) -> List[HeadlineSentiment]:
    return [score_headline(t) for t in texts]


def aggregate_sentiment(texts: Iterable[str]) -> float:
    """Điểm cảm xúc trung bình của một danh sách tiêu đề, trong [-1, 1]."""
    scored = score_headlines(texts)
    if not scored:
        return 0.0
    return round(sum(s.score for s in scored) / len(scored), 3)
