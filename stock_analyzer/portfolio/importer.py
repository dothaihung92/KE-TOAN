"""
Đọc file sao kê danh mục xuất từ VCBS Trade (hoặc các công ty chứng khoán
khác có định dạng tương tự) - Excel (.xlsx) hoặc CSV.

Đây là cách LIÊN KẾT AN TOÀN với tài khoản môi giới: người dùng tự đăng
nhập VCBS, tự xuất file sao kê danh mục, rồi tải lên đây. Phần mềm KHÔNG
bao giờ lưu hay yêu cầu tài khoản/mật khẩu VCBS.

Vì các công ty chứng khoán không thống nhất tên cột, việc nhận diện cột
dựa trên danh sách bí danh (alias) tiếng Việt có dấu/không dấu.
"""

from __future__ import annotations

import csv
import io
import unicodedata
from dataclasses import dataclass
from typing import List, Optional

import pandas as pd


class PortfolioImportError(Exception):
    pass


@dataclass
class HoldingRow:
    symbol: str
    quantity: float
    avg_cost: float


def _strip_diacritics(text: str) -> str:
    norm = unicodedata.normalize("NFD", text)
    stripped = "".join(c for c in norm if unicodedata.category(c) != "Mn")
    return unicodedata.normalize("NFC", stripped).replace("đ", "d").replace("Đ", "D")


def _norm_header(text: str) -> str:
    return _strip_diacritics(str(text)).strip().lower()


SYMBOL_ALIASES = ["ma ck", "ma cp", "ma chung khoan", "symbol", "ticker", "ma"]
QUANTITY_ALIASES = [
    "so luong", "khoi luong", "quantity", "sl", "so luong hien tai", "so du",
]
AVG_COST_ALIASES = [
    "gia von", "gia von tb", "gia mua tb", "avg cost", "gia trung binh",
    "gia von binh quan", "gia von bq", "gia mua binh quan",
]

_MAX_HEADER_SCAN_ROWS = 15


def _match_alias(header: str, aliases: List[str]) -> bool:
    return any(alias in header for alias in aliases)


def _find_header_row(raw: pd.DataFrame) -> Optional[int]:
    for idx in range(min(_MAX_HEADER_SCAN_ROWS, len(raw))):
        cells = [_norm_header(v) for v in raw.iloc[idx].tolist()]
        has_symbol = any(_match_alias(c, SYMBOL_ALIASES) for c in cells)
        has_qty = any(_match_alias(c, QUANTITY_ALIASES) for c in cells)
        if has_symbol and has_qty:
            return idx
    return None


def _find_column(columns: List[str], aliases: List[str]) -> Optional[str]:
    normalized = {col: _norm_header(col) for col in columns}
    for col, norm in normalized.items():
        if _match_alias(norm, aliases):
            return col
    return None


def _read_raw(file_bytes: bytes, filename: str) -> pd.DataFrame:
    if not file_bytes or not file_bytes.strip():
        raise PortfolioImportError("File rỗng hoặc không đọc được dữ liệu")

    lower = filename.lower()
    if lower.endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(file_bytes), header=None)
    # CSV: thử utf-8 rồi tới bảng mã tiếng Việt cũ (cp1258) nếu lỗi
    for encoding in ("utf-8-sig", "utf-8", "cp1258", "latin1"):
        try:
            return pd.read_csv(io.BytesIO(file_bytes), header=None, encoding=encoding, sep=None, engine="python")
        except (UnicodeDecodeError, pd.errors.ParserError, csv.Error):
            continue
    raise PortfolioImportError("Không đọc được file CSV (thử lại với mã hoá UTF-8)")


def _to_float(value) -> Optional[float]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_portfolio_file(file_bytes: bytes, filename: str) -> List[HoldingRow]:
    """Phân tích file sao kê, trả về danh sách mã/số lượng/giá vốn.

    Ném PortfolioImportError kèm thông báo tiếng Việt nếu không nhận diện
    được cấu trúc file.
    """
    raw = _read_raw(file_bytes, filename)
    if raw.empty:
        raise PortfolioImportError("File rỗng hoặc không đọc được dữ liệu")

    header_idx = _find_header_row(raw)
    if header_idx is None:
        raise PortfolioImportError(
            "Không tìm thấy dòng tiêu đề có cột 'Mã CK' và 'Số lượng'. "
            "Vui lòng kiểm tra lại file xuất từ VCBS Trade."
        )

    header = [str(v).strip() for v in raw.iloc[header_idx].tolist()]
    data = raw.iloc[header_idx + 1:].copy()
    data.columns = header

    symbol_col = _find_column(header, SYMBOL_ALIASES)
    qty_col = _find_column(header, QUANTITY_ALIASES)
    cost_col = _find_column(header, AVG_COST_ALIASES)

    if not symbol_col or not qty_col:
        raise PortfolioImportError("Không xác định được cột Mã CK / Số lượng trong file")

    results: List[HoldingRow] = []
    for _, row in data.iterrows():
        symbol_raw = row.get(symbol_col)
        if symbol_raw is None or (isinstance(symbol_raw, float) and pd.isna(symbol_raw)):
            continue
        symbol = str(symbol_raw).strip().upper()
        if not symbol or not symbol.isalnum() or len(symbol) > 10:
            continue

        qty = _to_float(row.get(qty_col))
        if qty is None or qty == 0:
            continue

        avg_cost = _to_float(row.get(cost_col)) if cost_col else None

        results.append(HoldingRow(symbol=symbol, quantity=qty, avg_cost=avg_cost or 0.0))

    if not results:
        raise PortfolioImportError("Không tìm thấy dòng dữ liệu hợp lệ nào trong file")

    return results
