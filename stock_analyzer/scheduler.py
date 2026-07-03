"""
Tác vụ nền: định kỳ lấy giá + tin tức mới nhất, tính tín hiệu/khuyến nghị,
rồi lưu vào cache SQLite để trang web đọc ra ngay (không phải chờ gọi API
ngoài mỗi lần tải trang) - đáp ứng yêu cầu "cập nhật tin tức liên tục".
"""

from __future__ import annotations

import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler

from . import db
from .analysis.indicators import compute_indicators
from .analysis.recommend import build_recommendation
from .analysis.signals import compute_signal
from .data_sources import market, news

logger = logging.getLogger(__name__)

PRICE_REFRESH_MINUTES = int(os.environ.get("STOCK_PRICE_REFRESH_MINUTES", "15"))
NEWS_REFRESH_MINUTES = int(os.environ.get("STOCK_NEWS_REFRESH_MINUTES", "10"))


def refresh_symbol(symbol: str) -> None:
    try:
        history = market.get_price_history(symbol)
        indicators_df = compute_indicators(history)
        signal = compute_signal(indicators_df)
        quote = market.get_latest_quote(symbol)
        headlines = [n.title for n in news.get_company_news(symbol, limit=10)]
        rec = build_recommendation(symbol, signal, headlines)
        db.save_recommendation_cache(symbol, quote, rec.to_dict())
        logger.info("Đã cập nhật %s: %s (%.2f)", symbol, rec.label, rec.combined_score)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Lỗi cập nhật %s: %s", symbol, exc)
        db.save_recommendation_cache(symbol, None, None, error=str(exc))


def refresh_all_watchlist() -> None:
    for symbol in db.list_watchlist_symbols():
        refresh_symbol(symbol)


def refresh_market_news() -> None:
    try:
        items = news.get_market_news(limit=30)
        db.replace_market_news([i.to_dict() for i in items])
        logger.info("Đã cập nhật %d tin thị trường", len(items))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Lỗi cập nhật tin thị trường: %s", exc)


_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        refresh_all_watchlist, "interval", minutes=PRICE_REFRESH_MINUTES,
        id="refresh_watchlist",
    )
    scheduler.add_job(
        refresh_market_news, "interval", minutes=NEWS_REFRESH_MINUTES,
        id="refresh_news",
    )
    scheduler.start()

    # Chạy ngay một lần lúc khởi động, không chờ hết chu kỳ đầu tiên
    scheduler.add_job(refresh_all_watchlist, id="refresh_watchlist_now")
    scheduler.add_job(refresh_market_news, id="refresh_news_now")

    _scheduler = scheduler
    return scheduler
