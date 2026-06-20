"""
Quản lý danh sách công ty (khách hàng của dịch vụ kế toán).

Mỗi công ty gồm: tên, MST (tài khoản đăng nhập HĐĐT), mật khẩu.
Mật khẩu được **mã hoá** bằng Fernet trước khi lưu vào SQLite, không lưu
dạng văn bản thường.

Khoá mã hoá lấy từ biến môi trường HDDT_SECRET. Nếu không có, sẽ tự sinh
và lưu vào instance/secret.key (cần bảo vệ file này).
"""

from __future__ import annotations

import base64
import hashlib
import os
import sqlite3
from datetime import datetime
from typing import List, Optional

from cryptography.fernet import Fernet

# Thư mục lưu dữ liệu cục bộ
INSTANCE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "instance")
DB_PATH = os.path.join(INSTANCE_DIR, "ketoan.db")
KEY_PATH = os.path.join(INSTANCE_DIR, "secret.key")


def _ensure_instance() -> None:
    os.makedirs(INSTANCE_DIR, exist_ok=True)


def _load_or_create_key() -> bytes:
    """Lấy khoá mã hoá Fernet (32 byte, base64-url)."""
    _ensure_instance()
    secret = os.environ.get("HDDT_SECRET")
    if secret:
        # Suy ra khoá Fernet hợp lệ từ chuỗi bí mật tuỳ ý
        digest = hashlib.sha256(secret.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest)
    if os.path.exists(KEY_PATH):
        with open(KEY_PATH, "rb") as f:
            return f.read().strip()
    key = Fernet.generate_key()
    with open(KEY_PATH, "wb") as f:
        f.write(key)
    try:
        os.chmod(KEY_PATH, 0o600)
    except OSError:
        pass
    return key


def _cipher() -> Fernet:
    return Fernet(_load_or_create_key())


def get_conn() -> sqlite3.Connection:
    _ensure_instance()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ten TEXT NOT NULL,
                mst TEXT NOT NULL,
                password_enc TEXT NOT NULL,
                ghi_chu TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )


def encrypt_password(plain: str) -> str:
    return _cipher().encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_password(enc: str) -> str:
    return _cipher().decrypt(enc.encode("utf-8")).decode("utf-8")


def list_companies() -> List[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM companies ORDER BY ten COLLATE NOCASE"
        ).fetchall()


def get_company(company_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM companies WHERE id = ?", (company_id,)
        ).fetchone()


def get_company_password(company_id: int) -> Optional[str]:
    row = get_company(company_id)
    if not row:
        return None
    return decrypt_password(row["password_enc"])


def add_company(ten: str, mst: str, password: str, ghi_chu: str = "") -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO companies (ten, mst, password_enc, ghi_chu, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (ten, mst, encrypt_password(password), ghi_chu,
             datetime.now().isoformat(timespec="seconds")),
        )
        return cur.lastrowid


def update_company(company_id: int, ten: str, mst: str,
                   password: Optional[str], ghi_chu: str = "") -> None:
    """Cập nhật công ty. Nếu password None/rỗng thì giữ mật khẩu cũ."""
    with get_conn() as conn:
        if password:
            conn.execute(
                "UPDATE companies SET ten=?, mst=?, password_enc=?, ghi_chu=? WHERE id=?",
                (ten, mst, encrypt_password(password), ghi_chu, company_id),
            )
        else:
            conn.execute(
                "UPDATE companies SET ten=?, mst=?, ghi_chu=? WHERE id=?",
                (ten, mst, ghi_chu, company_id),
            )


def delete_company(company_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM companies WHERE id = ?", (company_id,))
