"""
Lớp bọc (wrapper) quanh thư viện vnstock để lấy giá lịch sử và thông tin mã CP.

vnstock lấy dữ liệu công khai từ các công ty chứng khoán (VCI/SSI/TCBS...),
không cần tài khoản. Mọi lệnh gọi mạng đều được bọc try/except - nếu mạng
lỗi hoặc nguồn dữ liệu thay đổi, hàm trả về None/DataFrame rỗng kèm thông
điệp lỗi rõ ràng, thay vì làm sập ứng dụng.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

DEFAULT_SOURCE = "VCI"

# Danh mục mặc định: các mã vốn hoá lớn, thanh khoản cao (tham khảo rổ VN30).
# Dùng để khởi tạo watchlist khi người dùng chưa tự thêm/bớt mã.
DEFAULT_WATCHLIST = [
    "VCB", "BID", "CTG", "TCB", "VPB", "MBB", "ACB", "STB",
    "VIC", "VHM", "VRE", "GVR",
    "HPG", "GAS", "PLX", "POW",
    "FPT", "MWG", "MSN", "VNM", "SAB",
    "SSI", "VND", "VCI",
]


class MarketDataError(Exception):
    """Lỗi khi lấy dữ liệu thị trường (mạng, nguồn dữ liệu, mã không hợp lệ...)."""


def _stock(symbol: str, source: str = DEFAULT_SOURCE):
    from vnstock import Vnstock

    return Vnstock().stock(symbol=symbol.upper(), source=source)


def get_price_history(
    symbol: str,
    days: int = 250,
    source: str = DEFAULT_SOURCE,
) -> pd.DataFrame:
    """Lấy dữ liệu giá OHLCV `days` ngày gần nhất, cột: time, open, high, low, close, volume."""
    try:
        stock = _stock(symbol, source)
        end = datetime.now().date()
        start = end - timedelta(days=int(days * 1.6) + 10)  # dư ra để bù ngày nghỉ
        df = stock.quote.history(
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            interval="1D",
        )
        if df is None or df.empty:
            raise MarketDataError(f"Không có dữ liệu giá cho mã {symbol}")
        df = df.sort_values("time").reset_index(drop=True)
        return df.tail(days).reset_index(drop=True)
    except MarketDataError:
        raise
    except Exception as exc:  # noqa: BLE001 - nguồn ngoài có thể lỗi đủ kiểu
        logger.warning("Lỗi lấy giá %s: %s", symbol, exc)
        raise MarketDataError(f"Không lấy được dữ liệu giá cho {symbol}: {exc}") from exc


def get_latest_quote(symbol: str, source: str = DEFAULT_SOURCE) -> dict:
    """Giá đóng cửa gần nhất, % thay đổi so với phiên trước, khối lượng."""
    df = get_price_history(symbol, days=5, source=source)
    if len(df) < 1:
        raise MarketDataError(f"Không đủ dữ liệu cho {symbol}")
    last = df.iloc[-1]
    prev_close = df.iloc[-2]["close"] if len(df) >= 2 else last["close"]
    change = float(last["close"]) - float(prev_close)
    change_pct = (change / prev_close * 100) if prev_close else 0.0
    return {
        "symbol": symbol.upper(),
        "time": str(last["time"]),
        "close": float(last["close"]),
        "change": round(change, 2),
        "change_pct": round(change_pct, 2),
        "volume": int(last["volume"]),
    }


def search_symbols(keyword: str, source: str = DEFAULT_SOURCE) -> Optional[pd.DataFrame]:
    """Tìm mã CP theo từ khoá (tên công ty hoặc mã). Trả None nếu lỗi mạng."""
    try:
        from vnstock import Vnstock

        listing = Vnstock().stock(symbol="ACB", source=source).listing
        df = listing.symbols_by_exchange()
        if df is None or df.empty:
            return None
        keyword_lower = keyword.strip().lower()
        mask = df.apply(
            lambda r: keyword_lower in str(r.get("symbol", "")).lower()
            or keyword_lower in str(r.get("organ_name", "")).lower(),
            axis=1,
        )
        return df[mask].head(20)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Lỗi tìm mã '%s': %s", keyword, exc)
        return None
