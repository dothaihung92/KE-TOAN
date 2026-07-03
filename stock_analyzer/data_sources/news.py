"""
Lấy tin tức chứng khoán:

1. Tin theo từng mã cổ phiếu - qua vnstock (nguồn VCI).
2. Tin thị trường chung - qua RSS công khai của CafeF (không cần đăng nhập).

Tất cả lỗi mạng được bắt lại, trả về danh sách rỗng kèm log cảnh báo thay
vì làm sập ứng dụng - vì đây là dữ liệu "cập nhật liên tục", có lúc lấy
được lúc không là bình thường.
"""

from __future__ import annotations

import logging
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import List, Optional

import requests

logger = logging.getLogger(__name__)

MARKET_NEWS_RSS_URL = os.environ.get(
    "STOCK_NEWS_RSS_URL", "https://cafef.vn/thi-truong-chung-khoan.rss"
)
REQUEST_TIMEOUT = 10


@dataclass
class NewsItem:
    title: str
    link: str = ""
    published: str = ""
    symbol: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "link": self.link,
            "published": self.published,
            "symbol": self.symbol,
        }


_TITLE_COLUMNS = ["news_title", "title", "headline", "news_short_content"]
_DATE_COLUMNS = ["public_date", "news_source_link", "created_at", "date"]
_LINK_COLUMNS = ["news_source_link", "link", "url"]


def get_company_news(symbol: str, limit: int = 10, source: str = "VCI") -> List[NewsItem]:
    try:
        from vnstock import Vnstock

        company = Vnstock().stock(symbol=symbol.upper(), source=source).company
        df = company.news()
        if df is None or df.empty:
            return []

        title_col = next((c for c in _TITLE_COLUMNS if c in df.columns), None)
        if not title_col:
            return []
        link_col = next((c for c in _LINK_COLUMNS if c in df.columns), None)
        date_col = next((c for c in _DATE_COLUMNS if c in df.columns), None)

        items = []
        for _, row in df.head(limit).iterrows():
            items.append(
                NewsItem(
                    title=str(row.get(title_col, "")).strip(),
                    link=str(row.get(link_col, "") or "") if link_col else "",
                    published=str(row.get(date_col, "") or "") if date_col else "",
                    symbol=symbol.upper(),
                )
            )
        return [i for i in items if i.title]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Lỗi lấy tin tức mã %s: %s", symbol, exc)
        return []


def get_market_news(limit: int = 20, rss_url: str = MARKET_NEWS_RSS_URL) -> List[NewsItem]:
    """Tin thị trường chung, qua RSS công khai. Trả [] nếu không lấy được."""
    try:
        resp = requests.get(rss_url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        items: List[NewsItem] = []
        for item in root.findall(".//item")[:limit]:
            title = (item.findtext("title") or "").strip()
            if not title:
                continue
            link = (item.findtext("link") or "").strip()
            pub_date = (item.findtext("pubDate") or "").strip()
            items.append(NewsItem(title=title, link=link, published=pub_date))
        return items
    except Exception as exc:  # noqa: BLE001
        logger.warning("Lỗi lấy tin thị trường từ %s: %s", rss_url, exc)
        return []
