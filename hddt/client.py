"""
Client giao tiếp với API của cổng hoá đơn điện tử Tổng cục Thuế.

Luồng hoạt động:
    1. Lấy captcha (GET /captcha) -> trả về key + ảnh SVG.
    2. Đăng nhập (POST /security-taxpayer/authenticate) với
       username (MST/tài khoản), password, captcha key + lời giải -> token.
    3. Dùng token (header Authorization: Bearer <token>) để tra cứu hoá đơn.

Các endpoint tra cứu:
    - /query/invoices/purchase   : hoá đơn mua vào (có mã)
    - /query/invoices/sold       : hoá đơn bán ra (có mã)
    - /sco-query/invoices/purchase : hoá đơn mua vào (máy tính tiền - SCO)
    - /sco-query/invoices/sold     : hoá đơn bán ra (máy tính tiền - SCO)
    - /query/invoices/detail     : chi tiết một hoá đơn
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional

import requests


BASE_URL = "https://hoadondientu.gdt.gov.vn"
# Các endpoint xác thực và tra cứu. Mặc định dùng cổng HTTPS chuẩn (443).
# Có thể ghi đè bằng biến môi trường HDDT_API_URL nếu Tổng cục Thuế đổi địa chỉ.
API_URL = os.environ.get("HDDT_API_URL", "https://hoadondientu.gdt.gov.vn")

DEFAULT_TIMEOUT = 60

# Ánh xạ "loại hoá đơn" -> đường dẫn API
INVOICE_ENDPOINTS = {
    "purchase": "/query/invoices/purchase",        # mua vào
    "sold": "/query/invoices/sold",                # bán ra
    "sco-purchase": "/sco-query/invoices/purchase",  # mua vào - máy tính tiền
    "sco-sold": "/sco-query/invoices/sold",          # bán ra - máy tính tiền
}


class HddtError(Exception):
    """Lỗi khi giao tiếp với cổng hoá đơn điện tử."""


class HoaDonDienTuClient:
    """Client tra cứu hoá đơn điện tử của cổng Tổng cục Thuế."""

    def __init__(self, timeout: int = DEFAULT_TIMEOUT, token: Optional[str] = None):
        self.timeout = timeout
        self.token = token
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0 Safari/537.36"
                ),
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "vi,en;q=0.9",
            }
        )

    # ------------------------------------------------------------------ #
    # Xác thực
    # ------------------------------------------------------------------ #
    def get_captcha(self) -> Dict[str, str]:
        """Lấy captcha. Trả về dict {'key': ..., 'content': '<svg...>'}"""
        url = f"{API_URL}/captcha"
        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            raise HddtError(f"Không lấy được captcha: {exc}") from exc
        if "key" not in data or "content" not in data:
            raise HddtError(f"Captcha không hợp lệ: {data}")
        return data

    def authenticate(
        self,
        username: str,
        password: str,
        captcha_key: str,
        captcha_value: str,
    ) -> str:
        """Đăng nhập, trả về token (JWT). Lưu token vào self.token."""
        url = f"{API_URL}/security-taxpayer/authenticate"
        payload = {
            "ckey": captcha_key,
            "cvalue": captcha_value,
            "username": username,
            "password": password,
        }
        try:
            resp = self.session.post(url, json=payload, timeout=self.timeout)
        except requests.RequestException as exc:
            raise HddtError(f"Lỗi kết nối khi đăng nhập: {exc}") from exc

        if resp.status_code != 200:
            # Thử đọc thông báo lỗi từ server
            try:
                err = resp.json()
                msg = err.get("message") or err.get("error") or resp.text
            except ValueError:
                msg = resp.text
            raise HddtError(f"Đăng nhập thất bại ({resp.status_code}): {msg}")

        data = resp.json()
        token = data.get("token")
        if not token:
            raise HddtError(f"Không nhận được token. Phản hồi: {data}")
        self.token = token
        return token

    def _auth_headers(self) -> Dict[str, str]:
        if not self.token:
            raise HddtError("Chưa đăng nhập (thiếu token).")
        return {"Authorization": f"Bearer {self.token}"}

    # ------------------------------------------------------------------ #
    # Tra cứu hoá đơn
    # ------------------------------------------------------------------ #
    @staticmethod
    def _format_date(value: str | datetime) -> str:
        """Chuẩn hoá ngày về dạng dd/mm/yyyy mà API yêu cầu."""
        if isinstance(value, datetime):
            return value.strftime("%d/%m/%Y")
        # Cho phép nhập 'yyyy-mm-dd' hoặc 'dd/mm/yyyy'
        value = value.strip()
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt).strftime("%d/%m/%Y")
            except ValueError:
                continue
        raise HddtError(f"Định dạng ngày không hợp lệ: {value!r}")

    def _build_search(
        self,
        from_date: str | datetime,
        to_date: str | datetime,
        ttxly: Optional[int],
    ) -> str:
        """Tạo chuỗi search theo cú pháp của API (RSQL-like)."""
        fd = self._format_date(from_date)
        td = self._format_date(to_date)
        parts = [
            f"tdlap=ge={fd}T00:00:00",
            f"tdlap=le={td}T23:59:59",
        ]
        if ttxly is not None:
            parts.append(f"ttxly=={ttxly}")
        return ";".join(parts)

    def query_invoices_page(
        self,
        invoice_type: str,
        from_date: str | datetime,
        to_date: str | datetime,
        ttxly: Optional[int] = None,
        size: int = 50,
        state: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Tra cứu một trang hoá đơn. Trả về JSON gốc từ server."""
        if invoice_type not in INVOICE_ENDPOINTS:
            raise HddtError(
                f"Loại hoá đơn không hợp lệ: {invoice_type!r}. "
                f"Hợp lệ: {list(INVOICE_ENDPOINTS)}"
            )
        url = f"{API_URL}{INVOICE_ENDPOINTS[invoice_type]}"
        params = {
            "sort": "tdlap:asc,khmshdon:asc,shdon:asc",
            "size": size,
            "search": self._build_search(from_date, to_date, ttxly),
        }
        if state:
            params["state"] = state
        try:
            resp = self.session.get(
                url, params=params, headers=self._auth_headers(), timeout=self.timeout
            )
        except requests.RequestException as exc:
            raise HddtError(f"Lỗi kết nối khi tra cứu: {exc}") from exc

        if resp.status_code == 401:
            raise HddtError("Token hết hạn hoặc không hợp lệ. Cần đăng nhập lại.")
        if resp.status_code != 200:
            raise HddtError(
                f"Tra cứu thất bại ({resp.status_code}): {resp.text[:500]}"
            )
        return resp.json()

    def query_invoices(
        self,
        invoice_type: str,
        from_date: str | datetime,
        to_date: str | datetime,
        ttxly: Optional[int] = None,
        size: int = 50,
        max_pages: int = 1000,
        sleep_between: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """Tra cứu toàn bộ hoá đơn (tự động phân trang). Trả về danh sách hoá đơn."""
        all_rows: List[Dict[str, Any]] = []
        state: Optional[str] = None
        for _ in range(max_pages):
            data = self.query_invoices_page(
                invoice_type, from_date, to_date, ttxly=ttxly, size=size, state=state
            )
            rows = data.get("datas") or []
            all_rows.extend(rows)
            state = data.get("state")
            # Hết dữ liệu khi không còn state hoặc trang trả về ít hơn size
            if not state or len(rows) < size or not rows:
                break
            if sleep_between:
                time.sleep(sleep_between)
        return all_rows

    def iter_invoices_all_types(
        self,
        from_date: str | datetime,
        to_date: str | datetime,
        types: Optional[List[str]] = None,
        ttxly: Optional[int] = None,
        size: int = 50,
    ) -> Iterator[tuple[str, List[Dict[str, Any]]]]:
        """Lặp qua nhiều loại hoá đơn, yield (loại, danh sách hoá đơn)."""
        types = types or list(INVOICE_ENDPOINTS)
        for t in types:
            yield t, self.query_invoices(
                t, from_date, to_date, ttxly=ttxly, size=size
            )

    def get_invoice_detail(
        self,
        nbmst: str,
        khhdon: str,
        khmshdon: str | int,
        shdon: str | int,
        sco: bool = False,
    ) -> Dict[str, Any]:
        """Lấy chi tiết một hoá đơn (gồm danh sách hàng hoá/dịch vụ)."""
        path = "/sco-query/invoices/detail" if sco else "/query/invoices/detail"
        url = f"{API_URL}{path}"
        params = {
            "nbmst": nbmst,
            "khhdon": khhdon,
            "khmshdon": khmshdon,
            "shdon": shdon,
        }
        try:
            resp = self.session.get(
                url, params=params, headers=self._auth_headers(), timeout=self.timeout
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise HddtError(f"Không lấy được chi tiết hoá đơn: {exc}") from exc
        return resp.json()

    # ------------------------------------------------------------------ #
    # Tiện ích token
    # ------------------------------------------------------------------ #
    def save_token(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"token": self.token, "saved_at": time.time()}, f)

    @classmethod
    def load_token(cls, path: str, max_age_seconds: int = 3600) -> "HoaDonDienTuClient":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if time.time() - data.get("saved_at", 0) > max_age_seconds:
            raise HddtError("Token đã lưu quá cũ, cần đăng nhập lại.")
        return cls(token=data["token"])
