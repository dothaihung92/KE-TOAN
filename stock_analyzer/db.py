"""
Lưu trữ cục bộ (SQLite) cho ứng dụng phân tích chứng khoán:

- watchlist: danh sách mã cổ phiếu đang theo dõi.
- recommendation_cache: kết quả phân tích/khuyến nghị mới nhất mỗi mã
  (được scheduler làm mới định kỳ, trang web đọc từ đây cho nhanh).
- market_news_cache: tin tức thị trường chung mới nhất.
- holdings: danh mục cổ phiếu đang nắm giữ, nhập THỦ CÔNG từ file sao kê
  VCBS (Excel/CSV) - KHÔNG lưu tài khoản/mật khẩu VCBS ở đây.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from typing import Iterable, List, Optional

from .data_sources.market import DEFAULT_WATCHLIST

INSTANCE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance")
DB_PATH = os.path.join(INSTANCE_DIR, "stock_analyzer.db")


def _ensure_instance() -> None:
    os.makedirs(INSTANCE_DIR, exist_ok=True)


def get_conn() -> sqlite3.Connection:
    _ensure_instance()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS watchlist (
                symbol TEXT PRIMARY KEY,
                added_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS recommendation_cache (
                symbol TEXT PRIMARY KEY,
                updated_at TEXT NOT NULL,
                quote_json TEXT,
                recommendation_json TEXT,
                error TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS market_news_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fetched_at TEXT NOT NULL,
                title TEXT NOT NULL,
                link TEXT,
                published TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS holdings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                quantity REAL NOT NULL,
                avg_cost REAL NOT NULL,
                imported_at TEXT NOT NULL,
                source_file TEXT
            )
            """
        )
        row = conn.execute("SELECT COUNT(*) AS c FROM watchlist").fetchone()
        if row["c"] == 0:
            now = datetime.now().isoformat(timespec="seconds")
            conn.executemany(
                "INSERT OR IGNORE INTO watchlist (symbol, added_at) VALUES (?, ?)",
                [(s, now) for s in DEFAULT_WATCHLIST],
            )


# ---------------------------------------------------------------- watchlist

def list_watchlist_symbols() -> List[str]:
    with get_conn() as conn:
        rows = conn.execute("SELECT symbol FROM watchlist ORDER BY symbol").fetchall()
    return [r["symbol"] for r in rows]


def add_watchlist_symbol(symbol: str) -> None:
    symbol = symbol.strip().upper()
    if not symbol:
        return
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO watchlist (symbol, added_at) VALUES (?, ?)",
            (symbol, datetime.now().isoformat(timespec="seconds")),
        )


def remove_watchlist_symbol(symbol: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol.strip().upper(),))
        conn.execute("DELETE FROM recommendation_cache WHERE symbol = ?", (symbol.strip().upper(),))


# ----------------------------------------------------------- recommendation

def save_recommendation_cache(
    symbol: str, quote: Optional[dict], recommendation: Optional[dict], error: Optional[str] = None
) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO recommendation_cache (symbol, updated_at, quote_json, recommendation_json, error)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                updated_at=excluded.updated_at,
                quote_json=excluded.quote_json,
                recommendation_json=excluded.recommendation_json,
                error=excluded.error
            """,
            (
                symbol.upper(),
                datetime.now().isoformat(timespec="seconds"),
                json.dumps(quote, ensure_ascii=False) if quote else None,
                json.dumps(recommendation, ensure_ascii=False) if recommendation else None,
                error,
            ),
        )


def _row_to_cache(row: sqlite3.Row) -> dict:
    return {
        "symbol": row["symbol"],
        "updated_at": row["updated_at"],
        "quote": json.loads(row["quote_json"]) if row["quote_json"] else None,
        "recommendation": json.loads(row["recommendation_json"]) if row["recommendation_json"] else None,
        "error": row["error"],
    }


def get_recommendation_cache(symbol: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM recommendation_cache WHERE symbol = ?", (symbol.upper(),)
        ).fetchone()
    return _row_to_cache(row) if row else None


def list_recommendation_cache() -> List[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM recommendation_cache ORDER BY symbol").fetchall()
    return [_row_to_cache(r) for r in rows]


# --------------------------------------------------------------- market news

def replace_market_news(items: Iterable[dict]) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        conn.execute("DELETE FROM market_news_cache")
        conn.executemany(
            "INSERT INTO market_news_cache (fetched_at, title, link, published) VALUES (?, ?, ?, ?)",
            [(now, i["title"], i.get("link", ""), i.get("published", "")) for i in items],
        )


def list_market_news(limit: int = 30) -> List[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM market_news_cache ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


# ------------------------------------------------------------------ holdings

def replace_holdings(holdings: Iterable[dict], source_file: str = "") -> None:
    """Thay toàn bộ danh mục bằng dữ liệu vừa nhập (mỗi lần nhập file = 1 bản chụp mới)."""
    now = datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        conn.execute("DELETE FROM holdings")
        conn.executemany(
            """
            INSERT INTO holdings (symbol, quantity, avg_cost, imported_at, source_file)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (h["symbol"].upper(), h["quantity"], h["avg_cost"], now, source_file)
                for h in holdings
            ],
        )


def list_holdings() -> List[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM holdings ORDER BY symbol").fetchall()
    return [dict(r) for r in rows]


def clear_holdings() -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM holdings")
