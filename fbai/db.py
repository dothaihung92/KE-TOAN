"""
Lưu trữ: Fanpage đã kết nối, sản phẩm, bài đăng lên lịch, chiến dịch quảng cáo.

Dùng chung cơ chế mã hoá Fernet với webapp/db.py (Page Access Token là dữ
liệu nhạy cảm, không lưu văn bản thường).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import List, Optional

from webapp.db import get_conn, encrypt_password as _encrypt, decrypt_password as _decrypt


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS fb_pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ten TEXT NOT NULL,
                page_id TEXT NOT NULL,
                access_token_enc TEXT NOT NULL,
                ad_account_id TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS fb_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page_ref_id INTEGER NOT NULL,
                ten TEXT NOT NULL,
                mo_ta TEXT DEFAULT '',
                gia TEXT DEFAULT '',
                link TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (page_ref_id) REFERENCES fb_pages(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS fb_scheduled_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page_ref_id INTEGER NOT NULL,
                noi_dung TEXT NOT NULL,
                link TEXT DEFAULT '',
                image_url TEXT DEFAULT '',
                scheduled_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                fb_post_id TEXT DEFAULT '',
                error TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (page_ref_id) REFERENCES fb_pages(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS fb_campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page_ref_id INTEGER NOT NULL,
                ten TEXT NOT NULL,
                fb_campaign_id TEXT DEFAULT '',
                daily_budget_cents INTEGER DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'draft',
                created_at TEXT NOT NULL,
                FOREIGN KEY (page_ref_id) REFERENCES fb_pages(id)
            )
            """
        )


# ---------------------------------------------------------------------- #
# Fanpage
# ---------------------------------------------------------------------- #
def list_pages() -> List[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM fb_pages ORDER BY ten COLLATE NOCASE").fetchall()


def get_page(ref_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM fb_pages WHERE id = ?", (ref_id,)).fetchone()


def get_page_token(ref_id: int) -> Optional[str]:
    row = get_page(ref_id)
    if not row:
        return None
    return _decrypt(row["access_token_enc"])


def add_page(ten: str, page_id: str, access_token: str, ad_account_id: str = "") -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO fb_pages (ten, page_id, access_token_enc, ad_account_id, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (ten, page_id, _encrypt(access_token), ad_account_id,
             datetime.now().isoformat(timespec="seconds")),
        )
        return cur.lastrowid


def update_page(ref_id: int, ten: str, page_id: str,
                access_token: Optional[str], ad_account_id: str = "") -> None:
    with get_conn() as conn:
        if access_token:
            conn.execute(
                "UPDATE fb_pages SET ten=?, page_id=?, access_token_enc=?, ad_account_id=? WHERE id=?",
                (ten, page_id, _encrypt(access_token), ad_account_id, ref_id),
            )
        else:
            conn.execute(
                "UPDATE fb_pages SET ten=?, page_id=?, ad_account_id=? WHERE id=?",
                (ten, page_id, ad_account_id, ref_id),
            )


def delete_page(ref_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM fb_pages WHERE id = ?", (ref_id,))
        conn.execute("DELETE FROM fb_products WHERE page_ref_id = ?", (ref_id,))
        conn.execute("DELETE FROM fb_scheduled_posts WHERE page_ref_id = ?", (ref_id,))
        conn.execute("DELETE FROM fb_campaigns WHERE page_ref_id = ?", (ref_id,))


# ---------------------------------------------------------------------- #
# Sản phẩm
# ---------------------------------------------------------------------- #
def list_products(page_ref_id: int) -> List[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM fb_products WHERE page_ref_id = ? ORDER BY created_at DESC",
            (page_ref_id,),
        ).fetchall()


def get_product(product_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM fb_products WHERE id = ?", (product_id,)).fetchone()


def add_product(page_ref_id: int, ten: str, mo_ta: str, gia: str, link: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO fb_products (page_ref_id, ten, mo_ta, gia, link, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (page_ref_id, ten, mo_ta, gia, link,
             datetime.now().isoformat(timespec="seconds")),
        )
        return cur.lastrowid


def delete_product(product_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM fb_products WHERE id = ?", (product_id,))


# ---------------------------------------------------------------------- #
# Bài đăng lên lịch
# ---------------------------------------------------------------------- #
def list_scheduled_posts(page_ref_id: int) -> List[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM fb_scheduled_posts WHERE page_ref_id = ? ORDER BY scheduled_at DESC",
            (page_ref_id,),
        ).fetchall()


def list_due_posts(now_iso: str) -> List[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM fb_scheduled_posts WHERE status = 'pending' AND scheduled_at <= ?",
            (now_iso,),
        ).fetchall()


def add_scheduled_post(page_ref_id: int, noi_dung: str, scheduled_at: str,
                       link: str = "", image_url: str = "") -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO fb_scheduled_posts "
            "(page_ref_id, noi_dung, link, image_url, scheduled_at, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, 'pending', ?)",
            (page_ref_id, noi_dung, link, image_url, scheduled_at,
             datetime.now().isoformat(timespec="seconds")),
        )
        return cur.lastrowid


def mark_post_published(post_id: int, fb_post_id: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE fb_scheduled_posts SET status='published', fb_post_id=? WHERE id=?",
            (fb_post_id, post_id),
        )


def mark_post_failed(post_id: int, error: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE fb_scheduled_posts SET status='failed', error=? WHERE id=?",
            (error, post_id),
        )


def delete_scheduled_post(post_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM fb_scheduled_posts WHERE id = ?", (post_id,))


# ---------------------------------------------------------------------- #
# Chiến dịch quảng cáo
# ---------------------------------------------------------------------- #
def list_campaigns(page_ref_id: int) -> List[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM fb_campaigns WHERE page_ref_id = ? ORDER BY created_at DESC",
            (page_ref_id,),
        ).fetchall()


def add_campaign(page_ref_id: int, ten: str, fb_campaign_id: str,
                 daily_budget_cents: int, status: str = "draft") -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO fb_campaigns "
            "(page_ref_id, ten, fb_campaign_id, daily_budget_cents, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (page_ref_id, ten, fb_campaign_id, daily_budget_cents, status,
             datetime.now().isoformat(timespec="seconds")),
        )
        return cur.lastrowid


def update_campaign_status(campaign_id: int, status: str) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE fb_campaigns SET status=? WHERE id=?", (status, campaign_id))
