"""
============================================================
  PHẦN MỀM QUẢN LÝ HÓA ĐƠN ĐIỆN TỬ - ĐA CÔNG TY
  Kết nối hoadondientu.gdt.gov.vn (Tổng cục Thuế)
  Backend: FastAPI + SQLite
============================================================
"""
import os
import io
import json
import time
import base64
import sqlite3
import zipfile
import datetime
from typing import Optional, List

import requests
from fastapi import FastAPI, HTTPException, Body, Request
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# ============================================================
#  CẤU HÌNH ĐƯỜNG DẪN
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
DB_PATH = os.path.join(DATA_DIR, "hddt.db")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ============================================================
#  CẤU HÌNH TỐC ĐỘ TẢI (chống bị khóa tạm 429)
#  Mức "balanced" là cân bằng giữa tốc độ và an toàn.
# ============================================================
SPEED_PROFILES = {
    "fast":     {"page": 0.5, "status": 0.5, "month": 0.5, "file": 0.15, "retry_base": 4, "retry_max": 8, "between_loai": 2.5},
    "balanced": {"page": 1.0, "status": 1.0, "month": 1.2, "file": 0.6,  "retry_base": 5, "retry_max": 8, "between_loai": 3},
    "safe":     {"page": 2.0, "status": 2.0, "month": 2.5, "file": 1.2,  "retry_base": 10, "retry_max": 10, "between_loai": 5},
}
CURRENT_SPEED = "fast"  # mặc định nhanh

def SP():
    return SPEED_PROFILES.get(CURRENT_SPEED, SPEED_PROFILES["balanced"])


def _get_desktop_dir():
    """Trả về đường dẫn Desktop của người dùng (Windows/Mac/Linux).
    Hỗ trợ cả Desktop tiếng Việt (OneDrive). Nếu không thấy -> thư mục home."""
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, "Desktop"),
        os.path.join(home, "OneDrive", "Desktop"),
        os.path.join(home, "OneDrive", "Máy tính"),
        os.path.join(home, "Máy tính"),
    ]
    # đọc từ registry trên Windows (chính xác nhất)
    try:
        import sys
        if sys.platform.startswith("win"):
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
            val, _ = winreg.QueryValueEx(key, "Desktop")
            winreg.CloseKey(key)
            if val and os.path.isdir(os.path.expandvars(val)):
                return os.path.expandvars(val)
    except Exception:
        pass
    for c in candidates:
        if os.path.isdir(c):
            return c
    return home


def _open_file_local(path):
    """Mở file bằng ứng dụng mặc định của HĐH (Excel/trình xem XML).
    Chỉ chạy khi server chạy local trên máy người dùng."""
    try:
        import sys, subprocess
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass


def _to_num(v):
    """Chuyển '10.000000' hoặc '807544.000000' thành số; nếu không được giữ nguyên."""
    try:
        f = float(v)
        return int(f) if f == int(f) else f
    except Exception:
        return v if v not in (None,) else ""


def _save_invoice_files(folder, base, zip_bytes):
    """
    Lưu file invoice.zip do TCT trả về, đồng thời giải nén lấy
    invoice.html và file xml ra để dễ đọc.
    folder: thư mục lưu, base: tên file gốc (vd C26TYY_1360_0317483204)
    """
    import io as _io
    import zipfile as _zip
    os.makedirs(folder, exist_ok=True)
    # 1) Lưu nguyên file zip gốc
    zip_path = os.path.join(folder, base + ".zip")
    with open(zip_path, "wb") as f:
        f.write(zip_bytes)
    # 2) Thử giải nén lấy invoice.html và *.xml
    try:
        zf = _zip.ZipFile(_io.BytesIO(zip_bytes))
        for name in zf.namelist():
            low = name.lower()
            data = zf.read(name)
            if low.endswith(".html") or low.endswith(".htm"):
                with open(os.path.join(folder, base + "_invoice.html"), "wb") as f:
                    f.write(data)
            elif low.endswith(".xml"):
                with open(os.path.join(folder, base + ".xml"), "wb") as f:
                    f.write(data)
    except Exception:
        # không phải zip (có thể là xml thuần) -> lưu thẳng .xml
        if zip_bytes[:5] == b"<?xml" or zip_bytes[:5] == b"<HDon":
            with open(os.path.join(folder, base + ".xml"), "wb") as f:
                f.write(zip_bytes)


# ============================================================
#  GDT API CLIENT  (module gọi API Tổng cục Thuế)
#  --> Nếu TCT đổi endpoint, chỉ cần sửa các URL trong class này
# ============================================================
class GDTClient:
    # Endpoint thật xác nhận từ DevTools: có tiền tố /api
    BASE = "https://hoadondientu.gdt.gov.vn/api"
    BASE_QUERY = "https://hoadondientu.gdt.gov.vn/api/query"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self.token: Optional[str] = None
        self._last_total = 0
        self.last_query_total = 0
        self.last_query_got = 0

    # --- Lấy ảnh captcha ---
    def get_captcha(self):
        url = f"{self.BASE}/captcha"
        r = self.session.get(url, timeout=30)
        r.raise_for_status()
        # Trang trả JSON: {"key": "...", "content": "data:image/svg+xml;base64,..."}
        # (content có thể là chuỗi SVG thô hoặc data-URI base64)
        try:
            data = r.json()
        except Exception:
            # phòng trường hợp trả thẳng SVG/ảnh
            data = {"key": "", "content": r.text}
        return data  # trả nguyên về frontend để hiển thị

    # --- Đăng nhập lấy token ---
    def login(self, username, password, cvalue, ckey):
        url = f"{self.BASE}/security-taxpayer/authenticate"
        payload = {
            "username": username,
            "password": password,
            "cvalue": cvalue,   # mã captcha người dùng nhập
            "ckey": ckey,       # key captcha tương ứng
        }
        r = self.session.post(url, json=payload, timeout=30)
        if r.status_code != 200:
            raise Exception(f"Đăng nhập thất bại ({r.status_code}): {r.text[:200]}")
        data = r.json()
        token = data.get("token")
        if not token:
            raise Exception(f"Không nhận được token: {json.dumps(data)[:200]}")
        self.token = token
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        return token

    def set_token(self, token):
        self.token = token
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    # --- Tra cứu hóa đơn (tự chia nhỏ theo tháng) ---
    # loai: "purchase" (mua vào) hoặc "sold" (bán ra)
    # he_thong: "query" (HĐ điện tử thường) hoặc "sco-query" (HĐ máy tính tiền)
    def query_invoices(self, tu_ngay, den_ngay, loai="purchase", page_size=50,
                       he_thong="query", progress=None):
        """
        Tra cứu hóa đơn trong khoảng ngày bất kỳ (kể cả nhiều tháng/cả năm).
        Trang Thuế giới hạn mỗi lần gọi tối đa ~31 ngày, nên hàm này tự
        CHIA NHỎ khoảng ngày thành từng tháng rồi gộp kết quả lại.
        tu_ngay, den_ngay định dạng dd/mm/yyyy
        he_thong: "query" (hóa đơn điện tử) / "sco-query" (hóa đơn máy tính tiền)
        progress: hàm callback(msg) để báo tiến độ (tùy chọn)
        """
        d_from = datetime.datetime.strptime(tu_ngay, "%d/%m/%Y").date()
        d_to = datetime.datetime.strptime(den_ngay, "%d/%m/%Y").date()
        if d_from > d_to:
            d_from, d_to = d_to, d_from

        all_results = []
        seen = set()  # khử trùng lặp hóa đơn ở ranh giới tháng
        total_expected = 0
        cur = d_from
        while cur <= d_to:
            # cuối tháng hiện tại
            if cur.month == 12:
                month_end = datetime.date(cur.year, 12, 31)
            else:
                month_end = datetime.date(cur.year, cur.month + 1, 1) - datetime.timedelta(days=1)
            chunk_end = min(month_end, d_to)

            s_from = cur.strftime("%d/%m/%Y")
            s_to = chunk_end.strftime("%d/%m/%Y")
            if progress:
                progress(f"đang tải {s_from} → {s_to}...")

            self._last_total = 0
            chunk = self._query_one_range(s_from, s_to, loai, page_size, he_thong)
            total_expected += getattr(self, "_last_total", 0) or 0
            for inv in chunk:
                key = (inv.get("khmshdon"), inv.get("khhdon"),
                       inv.get("shdon"), inv.get("nbmst"))
                if key not in seen:
                    seen.add(key)
                    all_results.append(inv)
            # báo số tờ đã lấy lũy kế
            if progress:
                progress(f"đã lấy {len(all_results)} tờ (đến {s_to})")

            cur = chunk_end + datetime.timedelta(days=1)
            time.sleep(SP()["month"])  # nghỉ giữa các tháng
        # lưu tổng kỳ vọng để báo "đủ chưa"
        self.last_query_total = total_expected
        self.last_query_got = len(all_results)
        return all_results

    def _query_one_range(self, tu_ngay, den_ngay, loai="purchase",
                         page_size=50, he_thong="query"):
        """
        Tra cứu 1 khoảng ngày (<= 31 ngày).
        Khớp đúng cURL thật từ hoadondientu.gdt.gov.vn:
          HĐ điện tử : /api/query/invoices/{purchase,sold}
          HĐ máy tính tiền: /api/sco-query/invoices/{purchase,sold}
        Mua vào được phân theo trạng thái xử lý (ttxly): 5, 6, 8 -> gọi từng cái và gộp.
        """
        base = f"https://hoadondientu.gdt.gov.vn/api/{he_thong}"
        is_mtt = (he_thong == "sco-query")
        date_filter = (f"tdlap=ge={tu_ngay}T00:00:00;"
                       f"tdlap=le={den_ngay}T23:59:59")

        if loai == "purchase":
            url = f"{base}/invoices/purchase"
            action = "Tìm kiếm (hóa đơn %smua vào)" % ("máy tính tiền " if is_mtt else "")
            # Các trạng thái xử lý hóa đơn mua vào (mỗi cái là 1 lần gọi riêng):
            #   5 = tổng hợp/đã cấp mã, 6 = đã nhận không mã, 8 = HĐ có rủi ro...
            results = []
            seen = set()
            total_all = 0
            for ttxly in (5, 6, 8):
                search = f"{date_filter};ttxly=={ttxly}"
                try:
                    part, ptotal = self._fetch_paginated(url, search, action,
                                                         page_size, want_total=True)
                    if ptotal:
                        total_all += ptotal
                except Exception as e:
                    # 1 trạng thái lỗi/không có -> bỏ qua, vẫn lấy các trạng thái khác
                    if "TOKEN_EXPIRED" in str(e):
                        raise
                    part = []
                for inv in part:
                    key = (inv.get("khmshdon"), inv.get("khhdon"),
                           inv.get("shdon"), inv.get("nbmst"))
                    if key not in seen:
                        seen.add(key)
                        results.append(inv)
                time.sleep(SP()["status"])  # nghỉ giữa các trạng thái
            self._last_total = total_all
            return results
        else:
            url = f"{base}/invoices/sold"
            action = "Tìm kiếm (hóa đơn %sbán ra)" % ("máy tính tiền " if is_mtt else "")
            results, total = self._fetch_paginated(url, date_filter, action,
                                                   page_size, want_total=True)
            self._last_total = total  # lưu để báo lên
            return results

    def _fetch_paginated(self, url, search, action, page_size=50, want_total=False):
        """Gọi 1 endpoint với tham số search, tự phân trang và xử lý 429.
        want_total=True -> trả (results, total_kỳ_vọng) để kiểm tra đủ chưa."""
        from urllib.parse import quote
        extra_headers = {
            "accept-language": "vi",
            "action": quote(action),  # tiếng Việt -> URL-encode (header chỉ nhận latin-1)
            "end-point": "/tra-cuu/tra-cuu-hoa-don",
            "referer": "https://hoadondientu.gdt.gov.vn/tra-cuu/tra-cuu-hoa-don",
        }
        results = []
        state = None
        total_expected = None
        for _ in range(500):  # tối đa 500 trang an toàn
            qs = (f"sort=tdlap:desc&size={page_size}"
                  f"&search={quote(search, safe='=;,:/')}")
            if state:
                qs += f"&state={quote(str(state), safe='')}"
            full_url = f"{url}?{qs}"

            # Gọi có tự động thử lại khi bị 429 (Too Many Requests)
            r = None
            sp = SP()
            for attempt in range(sp["retry_max"]):
                r = self.session.get(full_url, headers=extra_headers, timeout=60)
                if r.status_code == 429:
                    ra = r.headers.get("Retry-After")
                    try:
                        wait = int(ra) if ra else sp["retry_base"] * (attempt + 1)
                    except Exception:
                        wait = sp["retry_base"] * (attempt + 1)
                    wait = min(wait, 90)
                    time.sleep(wait)
                    continue
                break

            if r.status_code == 401:
                raise Exception("TOKEN_EXPIRED")
            if r.status_code == 429:
                raise Exception(
                    "Trang Thuế tạm chặn do gọi quá nhiều (429). "
                    "Hãy đợi vài phút rồi thử lại, hoặc chuyển sang chế độ 'Chậm & an toàn'.")
            if r.status_code == 400:
                raise Exception(
                    f"Trang Thuế từ chối (400). Thử thu hẹp khoảng ngày "
                    f"(mỗi lần tối đa 1 tháng). Chi tiết: {r.text[:150]}")
            r.raise_for_status()
            data = r.json()
            datas = data.get("datas", []) or []
            results.extend(datas)
            # tổng số hóa đơn kỳ vọng (trang Thuế trả 'total')
            if total_expected is None:
                total_expected = data.get("total")
            state = data.get("state")
            if not state or len(datas) == 0:
                break
            time.sleep(sp["page"])  # nghỉ giữa các trang

        # KIỂM TRA ĐỦ CHƯA: nếu trang Thuế báo total nhiều hơn số lấy được,
        # thử phân trang lại 1 lần nữa (phòng trang bị lỗi giữa chừng)
        if (total_expected and len(results) < total_expected):
            try:
                retry_results = []
                state2 = None
                for _ in range(500):
                    qs = (f"sort=tdlap:desc&size={page_size}"
                          f"&search={quote(search, safe='=;,:/')}")
                    if state2:
                        qs += f"&state={quote(str(state2), safe='')}"
                    r2 = self.session.get(f"{url}?{qs}", headers=extra_headers, timeout=60)
                    if r2.status_code == 429:
                        time.sleep(min(SP()["retry_base"] * 2, 90)); continue
                    if r2.status_code != 200:
                        break
                    d2 = r2.json()
                    retry_results.extend(d2.get("datas", []) or [])
                    state2 = d2.get("state")
                    if not state2:
                        break
                    time.sleep(SP()["page"])
                # gộp, khử trùng
                seen = {(x.get("khmshdon"), x.get("khhdon"), x.get("shdon"), x.get("nbmst"))
                        for x in results}
                for inv in retry_results:
                    k = (inv.get("khmshdon"), inv.get("khhdon"), inv.get("shdon"), inv.get("nbmst"))
                    if k not in seen:
                        seen.add(k); results.append(inv)
            except Exception:
                pass

        if want_total:
            return results, total_expected
        return results

    # --- Tải file XML của 1 hóa đơn ---
    def download_xml(self, nbmst, khhdon, khmshdon, shdon, loai="purchase",
                     he_thong="query"):
        """Tải file invoice.zip (chứa XML + invoice.html) của 1 hóa đơn từ TCT.
        Endpoint thật: /api/{he_thong}/invoices/export-xml?nbmst=&khhdon=&shdon=&khmshdon=
        (không có tham số type)."""
        base = f"https://hoadondientu.gdt.gov.vn/api/{he_thong}"
        url = f"{base}/invoices/export-xml"
        params = {
            "nbmst": nbmst, "khhdon": khhdon,
            "shdon": shdon, "khmshdon": khmshdon,
        }
        extra_headers = {
            "accept-language": "vi",
            "action": "Xuat xml",
            "end-point": "/tra-cuu/tra-cuu-hoa-don",
            "referer": "https://hoadondientu.gdt.gov.vn/tra-cuu/tra-cuu-hoa-don",
        }
        try:
            r = self.session.get(url, params=params, headers=extra_headers, timeout=90)
        except Exception:
            return None
        if r.status_code == 200 and r.content[:5] not in (b'{"mes', b'{"err'):
            return r.content  # bytes của file zip
        return None

    def get_detail(self, nbmst, khhdon, khmshdon, shdon, he_thong="query"):
        """Lấy JSON chi tiết đầy đủ 1 hóa đơn. Có thử lại khi gặp 429/timeout
        để không bị sót hóa đơn (xử lý triệt để)."""
        base = f"https://hoadondientu.gdt.gov.vn/api/{he_thong}"
        url = f"{base}/invoices/detail"
        params = {
            "nbmst": nbmst, "khhdon": khhdon,
            "shdon": shdon, "khmshdon": khmshdon,
        }
        extra_headers = {
            "accept-language": "vi",
            "action": "Xem hoa don",
            "end-point": "/tra-cuu/tra-cuu-hoa-don",
            "referer": "https://hoadondientu.gdt.gov.vn/tra-cuu/tra-cuu-hoa-don",
        }
        sp = SP()
        for attempt in range(sp["retry_max"]):
            try:
                r = self.session.get(url, params=params,
                                     headers=extra_headers, timeout=60)
                if r.status_code == 200:
                    return r.json()
                if r.status_code == 401:
                    return None  # token hết hạn, không retry vô ích
                if r.status_code == 429:
                    ra = r.headers.get("Retry-After")
                    try:
                        wait = int(ra) if ra else sp["retry_base"] * (attempt + 1)
                    except Exception:
                        wait = sp["retry_base"] * (attempt + 1)
                    time.sleep(min(wait, 60))
                    continue
                # các lỗi khác (5xx...) -> chờ ngắn rồi thử lại
                time.sleep(sp["retry_base"])
            except Exception:
                time.sleep(sp["retry_base"])
        return None



# Mỗi công ty giữ 1 client riêng trong RAM (theo phiên token)
CLIENTS = {}  # {company_id: GDTClient}
FETCH_JOBS = {}  # {company_id: {messages, last, running, ...}} - tiến độ tra cứu nền

def get_client(company_id) -> GDTClient:
    if company_id not in CLIENTS:
        CLIENTS[company_id] = GDTClient()
    return CLIENTS[company_id]


# ============================================================
#  DATABASE
# ============================================================
def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ten TEXT NOT NULL,
        mst TEXT NOT NULL,
        username TEXT,
        password TEXT,
        ghichu TEXT,
        save_dir TEXT,
        created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER,
        loai TEXT,           -- purchase / sold
        he_thong TEXT,       -- query (HĐ điện tử) / sco-query (HĐ máy tính tiền)
        nbmst TEXT,          -- MST người bán
        nbten TEXT,          -- tên người bán
        nmmst TEXT,          -- MST người mua
        khmshdon TEXT,
        khhdon TEXT,
        shdon TEXT,
        tdlap TEXT,          -- ngày lập
        tgtcthue REAL,       -- tiền chưa thuế
        tgtthue REAL,        -- tiền thuế
        tgtttbso REAL,       -- tổng thanh toán
        tthai TEXT,          -- trạng thái
        raw TEXT,            -- json gốc
        UNIQUE(company_id, khmshdon, khhdon, shdon, loai, he_thong)
    );
    CREATE TABLE IF NOT EXISTS vat_balance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER,
        ky TEXT,                 -- kỳ MM/YYYY
        du_dau_ky REAL,          -- thuế GTGT còn được khấu trừ kỳ trước chuyển sang
        vat_mua REAL,            -- VAT đầu vào trong kỳ
        vat_ban REAL,            -- VAT đầu ra trong kỳ
        phai_nop REAL,           -- số phải nộp (nếu >0)
        du_cuoi_ky REAL,         -- còn được khấu trừ chuyển kỳ sau
        updated_at TEXT,
        UNIQUE(company_id, ky)
    );
    CREATE TABLE IF NOT EXISTS imported_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER,
        ky TEXT,                 -- kỳ MM/YYYY (rỗng = áp dụng chung)
        mua_ds REAL, mua_thue REAL,
        ban_ds_0 REAL,
        ban_ds_5 REAL, ban_thue_5 REAL,
        ban_ds_8 REAL, ban_thue_8 REAL,
        ban_ds_10 REAL, ban_thue_10 REAL,
        updated_at TEXT,
        UNIQUE(company_id, ky)
    );
    CREATE TABLE IF NOT EXISTS tokhai_nhap (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER,
        so_tk TEXT,              -- số tờ khai
        ngay_dk TEXT,            -- ngày đăng ký (yyyy-mm-dd)
        nguoi_xk TEXT,           -- tên người xuất khẩu
        items_json TEXT,         -- danh sách dòng hàng (JSON)
        updated_at TEXT,
        UNIQUE(company_id, so_tk)
    );
    """)
    # Migration: thêm cột he_thong nếu DB cũ chưa có
    cols = [r[1] for r in conn.execute("PRAGMA table_info(invoices)").fetchall()]
    if "he_thong" not in cols:
        conn.execute("ALTER TABLE invoices ADD COLUMN he_thong TEXT DEFAULT 'query'")
    if "detail_json" not in cols:
        conn.execute("ALTER TABLE invoices ADD COLUMN detail_json TEXT")
    ccols = [r[1] for r in conn.execute("PRAGMA table_info(companies)").fetchall()]
    if "save_dir" not in ccols:
        conn.execute("ALTER TABLE companies ADD COLUMN save_dir TEXT")
    if "nguoi_ky" not in ccols:
        conn.execute("ALTER TABLE companies ADD COLUMN nguoi_ky TEXT")
    conn.commit()
    conn.close()

init_db()


# ============================================================
#  FASTAPI APP
# ============================================================
app = FastAPI(title="HDDT Manager")


@app.get("/", response_class=HTMLResponse)
def home():
    with open(os.path.join(BASE_DIR, "static", "index.html"), encoding="utf-8") as f:
        return f.read()


# ---------- TỐC ĐỘ TẢI ----------
@app.get("/api/speed")
def get_speed():
    return {"speed": CURRENT_SPEED}

@app.post("/api/speed")
def set_speed(data: dict = Body(...)):
    global CURRENT_SPEED
    s = data.get("speed", "balanced")
    if s in SPEED_PROFILES:
        CURRENT_SPEED = s
    return {"speed": CURRENT_SPEED}


# ---------- QUẢN LÝ CÔNG TY ----------
@app.get("/api/companies")
def list_companies():
    conn = db()
    rows = conn.execute("SELECT * FROM companies ORDER BY ten").fetchall()
    conn.close()
    out = []
    for r in rows:
        d = dict(r)
        # Đã đăng nhập = có client với token còn hiệu lực
        cl = CLIENTS.get(r["id"])
        d["_online"] = bool(cl and getattr(cl, "token", None))
        d.pop("password", None)  # không gửi mật khẩu ra frontend
        out.append(d)
    return out

@app.get("/api/company/{cid}")
def get_company_detail(cid: int):
    """Lấy chi tiết 1 công ty KÈM mật khẩu (để điền sẵn vào form Sửa).
    App chạy cục bộ trên máy người dùng nên an toàn."""
    conn = db()
    r = conn.execute("SELECT * FROM companies WHERE id=?", (cid,)).fetchone()
    conn.close()
    if not r:
        raise HTTPException(404, "Không tìm thấy công ty")
    return dict(r)


@app.get("/api/login-status")
def login_status():
    """Trả danh sách company_id đang đăng nhập (token còn hiệu lực)."""
    return {"online": [cid for cid, cl in CLIENTS.items()
                       if getattr(cl, "token", None)]}

@app.post("/api/companies")
def add_company(data: dict = Body(...)):
    conn = db()
    mst = (data.get("mst") or "").strip()
    dup = conn.execute("SELECT ten FROM companies WHERE mst=?", (mst,)).fetchone()
    if dup:
        conn.close()
        raise HTTPException(400, f"MST {mst} đã dùng cho công ty '{dup['ten']}'. "
                                 f"Mỗi công ty phải có MST riêng.")
    conn.execute(
        "INSERT INTO companies (ten, mst, username, password, ghichu, save_dir, created_at) VALUES (?,?,?,?,?,?,?)",
        (data.get("ten"), mst, data.get("username"),
         data.get("password"), data.get("ghichu", ""), data.get("save_dir", ""),
         datetime.datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    return {"ok": True}

@app.put("/api/companies/{cid}")
def update_company(cid: int, data: dict = Body(...)):
    conn = db()
    mst = (data.get("mst") or "").strip()
    # Chặn trùng MST với công ty khác (gây lẫn dữ liệu)
    dup = conn.execute("SELECT id, ten FROM companies WHERE mst=? AND id<>?",
                       (mst, cid)).fetchone()
    if dup:
        conn.close()
        raise HTTPException(400, f"MST {mst} đã dùng cho công ty '{dup['ten']}'. "
                                 f"Mỗi công ty phải có MST riêng.")
    # Nếu password để trống -> GIỮ password cũ (không xóa)
    cur = conn.execute("SELECT password FROM companies WHERE id=?", (cid,)).fetchone()
    pw = data.get("password")
    if not pw:
        pw = cur["password"] if cur else ""
    conn.execute(
        "UPDATE companies SET ten=?, mst=?, username=?, password=?, ghichu=?, save_dir=? WHERE id=?",
        (data.get("ten"), mst, data.get("username"),
         pw, data.get("ghichu", ""), data.get("save_dir", ""), cid)
    )
    conn.commit()
    conn.close()
    # Luôn reset phiên đăng nhập cũ sau khi sửa (phòng đổi MST/mật khẩu)
    if cid in CLIENTS:
        del CLIENTS[cid]
    return {"ok": True}

@app.delete("/api/companies/{cid}")
def delete_company(cid: int):
    conn = db()
    conn.execute("DELETE FROM companies WHERE id=?", (cid,))
    conn.execute("DELETE FROM invoices WHERE company_id=?", (cid,))
    conn.commit()
    conn.close()
    return {"ok": True}


# ---------- ĐĂNG NHẬP THUẾ ----------
@app.get("/api/captcha/{cid}")
def get_captcha(cid: int):
    client = get_client(cid)
    try:
        data = client.get_captcha()
        return data
    except Exception as e:
        raise HTTPException(500, f"Lỗi lấy captcha: {e}")

@app.post("/api/login/{cid}")
def login(cid: int, body: dict = Body(...)):
    conn = db()
    comp = conn.execute("SELECT * FROM companies WHERE id=?", (cid,)).fetchone()
    conn.close()
    if not comp:
        raise HTTPException(404, "Không tìm thấy công ty")
    client = get_client(cid)
    try:
        token = client.login(
            username=comp["username"] or comp["mst"],
            password=comp["password"],
            cvalue=body.get("cvalue"),
            ckey=body.get("ckey"),
        )
        return {"ok": True, "token": token[:20] + "..."}
    except Exception as e:
        raise HTTPException(401, f"{e}")


# ---------- TỰ ĐỘNG GIẢI CAPTCHA + LOGIN (retry 3 lần) ----------
_DDDDOCR_INSTANCE = None
_DDDDOCR_ERR = ""

def _get_ddddocr():
    global _DDDDOCR_INSTANCE, _DDDDOCR_ERR
    if _DDDDOCR_INSTANCE is None:
        try:
            import ddddocr
            _DDDDOCR_INSTANCE = ddddocr.DdddOcr(show_ad=False)
            _DDDDOCR_ERR = ""
        except Exception as e:
            _DDDDOCR_INSTANCE = False
            _DDDDOCR_ERR = f"{type(e).__name__}: {e}"
    return _DDDDOCR_INSTANCE or None

def _svg_to_png(svg_text: str) -> bytes:
    """Rasterize SVG → PNG bytes (pure-Python qua svglib + reportlab). '' nếu thất bại."""
    try:
        from svglib.svglib import svg2rlg
        from reportlab.graphics import renderPM
        import io as _io
        drawing = svg2rlg(_io.StringIO(svg_text))
        if drawing is None:
            return b""
        # phóng to để OCR rõ hơn (mặc định captcha nhỏ ~120x40)
        scale = 4.0
        drawing.width = int((drawing.width or 120) * scale)
        drawing.height = int((drawing.height or 40) * scale)
        drawing.scale(scale, scale)
        buf = _io.BytesIO()
        renderPM.drawToFile(drawing, buf, fmt="PNG", bg=0xFFFFFF)
        return buf.getvalue()
    except Exception:
        return b""

def _preprocess_png(png_bytes: bytes) -> bytes:
    """Làm sạch PNG để ddddocr đoán chuẩn hơn: grayscale + threshold + phóng to."""
    try:
        from PIL import Image, ImageOps, ImageFilter
        import io as _io
        im = Image.open(_io.BytesIO(png_bytes)).convert("L")
        # phóng to nếu nhỏ
        if im.width < 200:
            im = im.resize((im.width * 3, im.height * 3), Image.LANCZOS)
        # tăng tương phản + làm sạch nét nhiễu
        im = ImageOps.autocontrast(im, cutoff=5)
        im = im.filter(ImageFilter.MedianFilter(size=3))
        # nhị phân hóa
        thr = 140
        im = im.point(lambda p: 255 if p > thr else 0)
        buf = _io.BytesIO()
        im.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return png_bytes

def _solve_captcha(content: str) -> str:
    """Trả về mã đoán được từ content (data URI / SVG / PNG base64). '' nếu không giải nổi."""
    import re as _re_cap
    if not content:
        return ""
    svg_text = ""
    png_bytes = None
    s = content.strip()
    if s.startswith("data:"):
        try:
            head, b64 = s.split(",", 1)
            raw = base64.b64decode(b64)
            if "svg" in head.lower():
                svg_text = raw.decode("utf-8", errors="replace")
            else:
                png_bytes = raw
        except Exception:
            pass
    elif "<svg" in s:
        svg_text = s
    else:
        try:
            png_bytes = base64.b64decode(s)
        except Exception:
            pass

    # 1) Trích <text> trực tiếp từ SVG (chỉ áp dụng khi SVG dùng <text>)
    if svg_text and "<text" in svg_text.lower():
        # bỏ comment + whitespace để regex bắt dễ hơn
        clean = _re_cap.sub(r'<!--.*?-->', '', svg_text, flags=_re_cap.DOTALL)
        # gom mọi nội dung trong <text>...</text> (kể cả <tspan>)
        groups = _re_cap.findall(r'<text\b[^>]*>(.*?)</text>',
                                 clean, flags=_re_cap.DOTALL | _re_cap.IGNORECASE)
        cand = ""
        for g in groups:
            inner = _re_cap.sub(r'<[^>]+>', '', g)  # bỏ tag con
            inner = _re_cap.sub(r'\s+', '', inner)
            cand += inner
        if 4 <= len(cand) <= 10 and cand.isalnum():
            return cand

    # 2) Nếu là SVG: rasterize → PNG để OCR
    if svg_text and not png_bytes:
        # tìm <image href="data:image/...,base64,..."> embed sẵn (đôi khi captcha dạng này)
        m_emb = _re_cap.search(
            r'<image\b[^>]*(?:xlink:)?href\s*=\s*["\']data:image/[^;]+;base64,([^"\']+)["\']',
            svg_text, _re_cap.IGNORECASE)
        if m_emb:
            try:
                png_bytes = base64.b64decode(m_emb.group(1))
            except Exception:
                png_bytes = None
        if not png_bytes:
            png_bytes = _svg_to_png(svg_text)

    # 3) OCR với ddddocr (preprocess + thử nhiều cách)
    if png_bytes:
        ocr = _get_ddddocr()
        if ocr:
            tries = [png_bytes, _preprocess_png(png_bytes)]
            for buf in tries:
                try:
                    ans = (ocr.classification(buf) or "").strip()
                    # giữ alnum, captcha TCT 6 ký tự
                    ans = _re_cap.sub(r'[^A-Za-z0-9]', '', ans)
                    if 4 <= len(ans) <= 10:
                        return ans
                except Exception:
                    pass
    return ""

@app.post("/api/auto-login/{cid}")
def auto_login(cid: int):
    """Tự lấy captcha → giải → đăng nhập, retry tối đa 5 lần."""
    conn = db()
    comp = conn.execute("SELECT * FROM companies WHERE id=?", (cid,)).fetchone()
    conn.close()
    if not comp:
        raise HTTPException(404, "Không tìm thấy công ty")
    client = get_client(cid)
    last_err = ""
    tried = []
    for lan in range(1, 6):
        try:
            cap = client.get_captcha()
        except Exception as e:
            raise HTTPException(500, f"Lỗi lấy captcha: {e}")
        ckey = cap.get("key") or ""
        cval = _solve_captcha(cap.get("content") or "")
        tried.append(cval or "(không giải được)")
        if not cval:
            last_err = "Không giải được captcha"
            continue
        try:
            token = client.login(
                username=comp["username"] or comp["mst"],
                password=comp["password"],
                cvalue=cval,
                ckey=ckey,
            )
            return {"ok": True, "token": token[:20] + "...",
                    "so_lan_thu": lan, "ma_da_thu": tried}
        except Exception as e:
            last_err = str(e)
            continue
    raise HTTPException(401, f"Tự đăng nhập thất bại sau 5 lần. Mã đã thử: {tried}. Lỗi cuối: {last_err}")


@app.get("/api/captcha-debug/{cid}")
def captcha_debug(cid: int):
    """Chẩn đoán vì sao không tự giải được captcha.
    Mở trong trình duyệt: http://127.0.0.1:8686/api/captcha-debug/<id-công-ty>
    """
    import re as _re_dbg
    info = {}

    # 1) Trạng thái thư viện
    info["ddddocr_loaded"] = _get_ddddocr() is not None
    info["ddddocr_error"] = _DDDDOCR_ERR
    try:
        import svglib  # noqa
        info["svglib_loaded"] = True
    except Exception as e:
        info["svglib_loaded"] = False
        info["svglib_error"] = f"{type(e).__name__}: {e}"
    try:
        import reportlab  # noqa
        info["reportlab_loaded"] = True
    except Exception as e:
        info["reportlab_loaded"] = False
        info["reportlab_error"] = f"{type(e).__name__}: {e}"
    try:
        import PIL  # noqa
        info["pillow_loaded"] = True
    except Exception as e:
        info["pillow_loaded"] = False
        info["pillow_error"] = f"{type(e).__name__}: {e}"

    # 2) Lấy 1 captcha thật và phân tích
    try:
        client = get_client(cid)
        cap = client.get_captcha()
    except Exception as e:
        info["captcha_fetch_error"] = f"{type(e).__name__}: {e}"
        return info

    content = cap.get("content") or ""
    info["has_key"] = bool(cap.get("key"))
    info["content_len"] = len(content)
    info["content_head_120"] = content[:120]
    s = content.strip()
    if s.startswith("data:"):
        info["content_type"] = "data-uri: " + s[:40]
    elif "<svg" in s.lower():
        info["content_type"] = "raw-svg"
    else:
        info["content_type"] = "khác (có thể base64 trần)"

    # 3) Có <text> trong SVG không?
    svg_for_check = ""
    if s.startswith("data:") and "svg" in s[:40].lower():
        try:
            svg_for_check = base64.b64decode(s.split(",", 1)[1]).decode("utf-8", "replace")
        except Exception:
            svg_for_check = ""
    elif "<svg" in s.lower():
        svg_for_check = s
    info["co_the_text"] = ("<text" in svg_for_check.lower()) if svg_for_check else None
    info["co_the_path"] = ("<path" in svg_for_check.lower()) if svg_for_check else None
    info["co_the_image"] = ("<image" in svg_for_check.lower()) if svg_for_check else None

    # 4) Thử giải thật
    info["ket_qua_giai"] = _solve_captcha(content) or "(rỗng)"
    return info


# ---------- TRA CỨU & TẢI HÓA ĐƠN (streaming tiến độ) ----------
def _run_fetch_job(cid: int, body: dict):
    """Lõi tra cứu + tải hóa đơn cho MỘT công ty (chạy đồng bộ trong thread).

    Giả định: FETCH_JOBS[cid] đã được khởi tạo bởi nơi gọi, và token còn hiệu lực.
    Dùng chung cho tra cứu 1 công ty (/api/fetch) và tra cứu hàng loạt
    (/api/fetch-batch).

    body: {
      tu_ngay, den_ngay,
      loai_list: ["purchase","sold"],
      he_thong_list: ["query","sco-query"],
      dl_buy:  ["xml","pdf"]  # định dạng tải cho mua vào (rỗng = không tải)
      dl_sell: ["xml","pdf"]  # định dạng tải cho bán ra
    }
    """
    client = get_client(cid)

    tu = body.get("tu_ngay")
    den = body.get("den_ngay")
    loai_list = body.get("loai_list", ["purchase", "sold"])
    he_thong_list = body.get("he_thong_list", ["query", "sco-query"])
    lay_ngan_hang = body.get("lay_ngan_hang", False)  # mặc định KHÔNG lấy HĐ ngân hàng
    dl_map = {
        "purchase": body.get("dl_buy", []),
        "sold": body.get("dl_sell", []),
    }

    def la_hoa_don_ngan_hang(inv):
        """Nhận diện hóa đơn ngân hàng/phí dịch vụ NH qua tên người bán."""
        ten = (inv.get("nbten") or "").upper()
        tu_khoa = ["NGAN HANG", "NGÂN HÀNG", "BANK", "TMCP", "THƯƠNG MẠI CỔ PHẦN",
                   "VIETCOMBANK", "VIETINBANK", "AGRIBANK", "BIDV", "TECHCOMBANK",
                   "SACOMBANK", "ACB", "MBBANK", "VPBANK", "TPBANK", "SHB"]
        return any(k in ten for k in tu_khoa)

    conn0 = db()
    comp = conn0.execute("SELECT * FROM companies WHERE id=?", (cid,)).fetchone()
    save_dir = (comp["save_dir"] or "").strip() if comp else ""
    conn0.close()

    def msg(**kw):
        # Ghi tiến độ vào job thay vì yield (để chạy nền, không phụ thuộc trình duyệt)
        job = FETCH_JOBS.get(cid)
        if job is not None:
            job["messages"].append(kw)
            job["last"] = kw
        return None

    def run():
        conn = db()
        try:
            # Xóa sạch toàn bộ hóa đơn cũ của công ty trước khi tra cứu mới
            conn.execute("DELETE FROM invoices WHERE company_id=?", (cid,))
            conn.commit()
            msg(stage="start", text="Đã xóa dữ liệu cũ. Bắt đầu tra cứu...")

            total_saved = 0
            file_saved = 0
            # đếm theo loại để tổng kết: {loai: {"exp": tổng trang Thuế báo, "got": số lấy được}}
            thongke = {"purchase": {"exp": 0, "got": 0}, "sold": {"exp": 0, "got": 0}}
            target_dir = None
            if save_dir:
                try:
                    os.makedirs(save_dir, exist_ok=True)
                    target_dir = save_dir
                except Exception as e:
                    msg(stage="warn", text=f"Không tạo được thư mục lưu: {e}")

            for li, loai in enumerate(loai_list):
                loai_txt = "mua vào" if loai == "purchase" else "bán ra"
                # nghỉ trước khi chuyển từ mua sang bán (mua đã gọi nhiều request)
                if li > 0:
                    time.sleep(SP().get("between_loai", 2))
                for he_thong in he_thong_list:
                    # dừng nếu người dùng chuyển công ty khác
                    _job = FETCH_JOBS.get(cid)
                    if _job and _job.get("cancel"):
                        msg(stage="warn", text="Đã dừng tra cứu (chuyển sang công ty khác)")
                        return
                    ht_txt = " (máy tính tiền)" if he_thong == "sco-query" else ""
                    msg(stage="query",
                        text=f"Đang tra cứu hóa đơn {loai_txt}{ht_txt}...")
                    try:
                        invs = client.query_invoices(
                            tu, den, loai=loai, he_thong=he_thong,
                            progress=lambda t: msg(stage="query", text=f"{loai_txt}{ht_txt}: {t}"))
                    except Exception as e:
                        es = str(e)
                        if "TOKEN_EXPIRED" in es:
                            msg(stage="error", text="Token hết hạn, cần đăng nhập lại")
                            return
                        if he_thong == "sco-query" and "404" in es:
                            msg(stage="warn",
                                text=f"{loai_txt}{ht_txt}: không có (404) — bỏ qua")
                            continue
                        # 429 = trang Thuế chặn tạm -> báo RÕ và thử lại nguyên loại này
                        if "429" in es or "quá nhiều" in es:
                            msg(stage="warn",
                                text=f"⚠ {loai_txt}{ht_txt}: Trang Thuế chặn tạm (429). Đang chờ 30s rồi thử lại...")
                            time.sleep(30)
                            try:
                                invs = client.query_invoices(
                                    tu, den, loai=loai, he_thong=he_thong,
                                    progress=lambda t: msg(stage="query", text=f"{loai_txt}{ht_txt}: {t}"))
                            except Exception as e2:
                                msg(stage="error",
                                    text=f"✗ {loai_txt}{ht_txt}: vẫn lỗi sau khi thử lại — {str(e2)[:120]}. "
                                         f"NÊN TRA CỨU LẠI riêng công ty này (hoặc chuyển chế độ Chậm & an toàn).")
                                continue
                        else:
                            msg(stage="error",
                                text=f"✗ Lỗi {loai_txt}{ht_txt}: {es[:140]} — NÊN TRA CỨU LẠI.")
                            continue

                    if not invs:
                        msg(stage="found",
                            text=f"{loai_txt}{ht_txt}: 0 hóa đơn (không có dữ liệu trong kỳ)",
                            total_saved=total_saved)
                        continue

                    if not lay_ngan_hang:
                        truoc = len(invs)
                        invs = [iv for iv in invs if not la_hoa_don_ngan_hang(iv)]
                        bo = truoc - len(invs)
                        if bo > 0:
                            msg(stage="info",
                                text=f"Đã loại {bo} hóa đơn ngân hàng khỏi {loai_txt}{ht_txt}")

                    for inv in invs:
                        try:
                            conn.execute("""
                                INSERT OR IGNORE INTO invoices
                                (company_id, loai, he_thong, nbmst, nbten, nmmst,
                                 khmshdon, khhdon, shdon,
                                 tdlap, tgtcthue, tgtthue, tgtttbso, tthai, raw)
                                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                            """, (
                                cid, loai, he_thong,
                                inv.get("nbmst"), inv.get("nbten"), inv.get("nmmst"),
                                str(inv.get("khmshdon", "")), inv.get("khhdon"), str(inv.get("shdon", "")),
                                inv.get("tdlap"),
                                inv.get("tgtcthue"), inv.get("tgtthue"), inv.get("tgtttbso"),
                                str(inv.get("tthai", "")),
                                json.dumps(inv, ensure_ascii=False),
                            ))
                        except Exception:
                            pass
                    conn.commit()
                    total_saved += len(invs)
                    # so sánh với tổng kỳ vọng từ trang Thuế (trước khi lọc ngân hàng)
                    exp = getattr(client, "last_query_total", 0) or 0
                    got_raw = getattr(client, "last_query_got", len(invs)) or len(invs)
                    thongke[loai]["exp"] += exp
                    thongke[loai]["got"] += got_raw
                    if exp and got_raw < exp:
                        msg(stage="warn",
                            text=f"⚠ {loai_txt}{ht_txt}: Trang Thuế báo có {exp} HĐ "
                                 f"nhưng chỉ lấy được {got_raw}. Có thể bị thiếu — "
                                 f"nên tra cứu LẠI kỳ này (hoặc chuyển chế độ Chậm & an toàn).")
                    elif exp:
                        msg(stage="info",
                            text=f"✓ {loai_txt}{ht_txt}: Đã lấy đủ {got_raw}/{exp} hóa đơn theo trang Thuế")
                    msg(stage="found",
                        text=f"Tìm thấy {len(invs)} hóa đơn {loai_txt}{ht_txt}",
                        total_saved=total_saved)

                    fmts = dl_map.get(loai, [])
                    if fmts and target_dir and invs:
                      try:
                        sub = os.path.join(target_dir, f"{loai_txt}".replace(" ", "_"))
                        os.makedirs(sub, exist_ok=True)
                        n = len(invs)
                        for i, inv in enumerate(invs, 1):
                            nbmst = inv.get("nbmst", "")
                            khhdon = inv.get("khhdon", "")
                            khmshdon = inv.get("khmshdon", "")
                            shdon = inv.get("shdon", "")
                            base = f"{khhdon}_{shdon}_{nbmst}"
                            msg(stage="download",
                                text=f"Đang tải file {loai_txt}: {i}/{n} (còn {n-i})",
                                cur=i, total=n)
                            if "xml" in fmts:
                                try:
                                    zdata = client.download_xml(nbmst, khhdon, khmshdon,
                                                                shdon, loai, he_thong)
                                except Exception:
                                    zdata = None
                                if zdata:
                                    try:
                                        _save_invoice_files(sub, base, zdata)
                                        file_saved += 1
                                    except Exception:
                                        pass
                            time.sleep(SP()["file"])
                      except Exception as e:
                        msg(stage="warn",
                            text=f"Lỗi tải file {loai_txt} (dữ liệu bảng vẫn lưu): {str(e)[:100]}")

            # ===== TỔNG KẾT số hóa đơn theo trang Thuế (để biết lấy đủ chưa) =====
            tk_mua = thongke["purchase"]
            tk_ban = thongke["sold"]
            dong_tk = []
            if "purchase" in loai_list:
                if tk_mua["exp"]:
                    dau = "✓" if tk_mua["got"] >= tk_mua["exp"] else "⚠"
                    dong_tk.append(f"{dau} Đầu vào (mua): lấy {tk_mua['got']}/{tk_mua['exp']} HĐ trang Thuế báo")
                else:
                    dong_tk.append(f"• Đầu vào (mua): lấy {tk_mua['got']} HĐ")
            if "sold" in loai_list:
                if tk_ban["exp"]:
                    dau = "✓" if tk_ban["got"] >= tk_ban["exp"] else "⚠"
                    dong_tk.append(f"{dau} Đầu ra (bán): lấy {tk_ban['got']}/{tk_ban['exp']} HĐ trang Thuế báo")
                else:
                    dong_tk.append(f"• Đầu ra (bán): lấy {tk_ban['got']} HĐ")
            for d in dong_tk:
                msg(stage="info", text=d)

            # cảnh báo nếu thiếu
            thieu = ((tk_mua["exp"] and tk_mua["got"] < tk_mua["exp"]) or
                     (tk_ban["exp"] and tk_ban["got"] < tk_ban["exp"]))
            done_text = f"Hoàn tất! Đã lưu {total_saved} hóa đơn"
            if "purchase" in loai_list or "sold" in loai_list:
                done_text += f" (đầu vào: {tk_mua['got']}, đầu ra: {tk_ban['got']})"
            if file_saved:
                done_text += f", tải {file_saved} file vào: {target_dir}"
            if thieu:
                done_text += " — ⚠ CÓ THỂ THIẾU, nên tra cứu lại (chế độ Chậm & an toàn)"
            msg(stage="done", text=done_text,
                total_saved=total_saved, file_saved=file_saved,
                tk_mua_got=tk_mua["got"], tk_mua_exp=tk_mua["exp"],
                tk_ban_got=tk_ban["got"], tk_ban_exp=tk_ban["exp"])
        except Exception as e:
            msg(stage="error", text=f"Lỗi: {str(e)[:160]}")
        finally:
            conn.close()
            job = FETCH_JOBS.get(cid)
            if job is not None:
                job["running"] = False

    # FETCH_JOBS[cid] đã được khởi tạo bởi nơi gọi (endpoint /api/fetch hoặc batch).
    # Chạy đồng bộ trong thread của nơi gọi.
    run()


def _new_fetch_job():
    return {"messages": [], "last": None, "running": True,
            "cursor": 0, "started": time.time(), "cancel": False}


@app.post("/api/fetch/{cid}")
def fetch_invoices(cid: int, body: dict = Body(...)):
    """Tra cứu + tải hóa đơn cho 1 công ty (chạy nền). Trình duyệt poll
    /api/fetch-status/{cid} để lấy tiến độ."""
    client = get_client(cid)
    if not client.token:
        raise HTTPException(401, "Chưa đăng nhập tài khoản thuế cho công ty này")
    FETCH_JOBS[cid] = _new_fetch_job()
    import threading
    threading.Thread(target=lambda: _run_fetch_job(cid, body), daemon=True).start()
    return {"ok": True, "started": True}


# ---------- TRA CỨU HÀNG LOẠT (nhiều công ty cùng lúc) ----------
# Mỗi batch lấy lần lượt từng công ty (tuần tự) để tránh bị Tổng cục Thuế
# chặn tạm (429). Tiến độ từng công ty vẫn ghi vào FETCH_JOBS[cid] như cũ,
# đồng thời BATCH_JOBS[batch_id] tổng hợp trạng thái toàn batch.
BATCH_JOBS = {}      # {batch_id: {...}}
_BATCH_SEQ = {"n": 0}


def _run_batch(batch_id: int, cids: list, body: dict):
    batch = BATCH_JOBS[batch_id]
    try:
        for cid in cids:
            if batch.get("cancel"):
                break
            item = batch["items"].get(cid)
            client = get_client(cid)
            if not client.token:
                item["status"] = "skipped"
                item["note"] = "Chưa đăng nhập — bỏ qua"
                batch["done"] += 1
                continue
            item["status"] = "running"
            batch["current"] = cid
            # khởi tạo job cho công ty này (UI từng công ty dùng lại được)
            FETCH_JOBS[cid] = _new_fetch_job()
            try:
                _run_fetch_job(cid, body)   # chạy đồng bộ trong thread batch
                last = (FETCH_JOBS.get(cid) or {}).get("last") or {}
                item["total_saved"] = last.get("total_saved", 0)
                if last.get("stage") == "error":
                    item["status"] = "error"
                    item["note"] = last.get("text", "Lỗi")
                else:
                    item["status"] = "done"
                    item["note"] = last.get("text", "Hoàn tất")
            except Exception as e:
                item["status"] = "error"
                item["note"] = str(e)[:160]
            batch["done"] += 1
    finally:
        batch["running"] = False
        batch["current"] = None


@app.post("/api/fetch-batch")
def fetch_batch(body: dict = Body(...)):
    """Tra cứu nhiều công ty một lần.
    body: { cids: [1,2,3], tu_ngay, den_ngay, loai_list, he_thong_list,
            dl_buy, dl_sell, lay_ngan_hang }
    Trả về { batch_id }. Poll /api/fetch-batch-status/{batch_id} để theo dõi."""
    cids = body.get("cids") or []
    cids = [int(c) for c in cids]
    if not cids:
        raise HTTPException(400, "Chưa chọn công ty nào")

    conn = db()
    rows = conn.execute(
        "SELECT id, ten, mst FROM companies WHERE id IN (%s)"
        % ",".join("?" * len(cids)), cids).fetchall()
    conn.close()
    ten_map = {r["id"]: (r["ten"] or r["mst"]) for r in rows}
    # giữ đúng thứ tự người dùng chọn, chỉ lấy công ty có thật
    cids = [c for c in cids if c in ten_map]
    if not cids:
        raise HTTPException(404, "Không tìm thấy công ty đã chọn")

    _BATCH_SEQ["n"] += 1
    batch_id = _BATCH_SEQ["n"]
    BATCH_JOBS[batch_id] = {
        "running": True,
        "cancel": False,
        "total": len(cids),
        "done": 0,
        "current": None,
        "started": time.time(),
        "order": cids,
        "items": {c: {"cid": c, "ten": ten_map[c], "status": "pending",
                      "total_saved": 0, "note": ""} for c in cids},
    }
    import threading
    threading.Thread(target=lambda: _run_batch(batch_id, cids, body),
                     daemon=True).start()
    return {"ok": True, "batch_id": batch_id}


@app.get("/api/fetch-batch-status/{batch_id}")
def fetch_batch_status(batch_id: int):
    batch = BATCH_JOBS.get(batch_id)
    if not batch:
        return {"running": False, "no_job": True}
    return {
        "running": batch["running"],
        "total": batch["total"],
        "done": batch["done"],
        "current": batch["current"],
        "items": [batch["items"][c] for c in batch["order"]],
    }


@app.post("/api/fetch-batch-cancel/{batch_id}")
def fetch_batch_cancel(batch_id: int):
    batch = BATCH_JOBS.get(batch_id)
    if batch:
        batch["cancel"] = True
        # dừng luôn công ty đang chạy
        cur = batch.get("current")
        if cur and FETCH_JOBS.get(cur):
            FETCH_JOBS[cur]["cancel"] = True
    return {"ok": True}


@app.post("/api/fetch-cancel/{cid}")
def fetch_cancel(cid: int):
    """Dừng tra cứu của công ty (khi người dùng chuyển sang công ty khác)."""
    job = FETCH_JOBS.get(cid)
    if job:
        job["cancel"] = True
    return {"ok": True}


@app.get("/api/fetch-status/{cid}")
def fetch_status(cid: int, cursor: int = 0):
    """Trả về các thông báo tiến độ MỚI kể từ cursor. Trình duyệt poll endpoint này.
    Chạy nền nên thu nhỏ cửa sổ vẫn không mất dữ liệu."""
    job = FETCH_JOBS.get(cid)
    if not job:
        return {"running": False, "messages": [], "cursor": 0, "no_job": True}
    msgs = job["messages"][cursor:]
    return {
        "running": job["running"],
        "messages": msgs,
        "cursor": cursor + len(msgs),
    }


@app.get("/api/invoices/{cid}")
def get_invoices(cid: int, loai: Optional[str] = None):
    conn = db()
    if loai:
        rows = conn.execute(
            "SELECT * FROM invoices WHERE company_id=? AND loai=? ORDER BY tdlap DESC",
            (cid, loai)).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM invoices WHERE company_id=? ORDER BY tdlap DESC",
            (cid,)).fetchall()
    conn.close()
    out = []
    for r in rows:
        d = dict(r)
        try:
            raw = json.loads(r["raw"]) if r["raw"] else {}
        except Exception:
            raw = {}
        # mô tả trạng thái (Hóa đơn mới / đã bị thay thế / hủy...)
        tthai_ma = str(raw.get("tthai", r["tthai"]) or "").strip()
        d["tthai_mota"] = _mo_ta_trang_thai(tthai_ma)
        d["tthai_ma"] = tthai_ma
        # tên người mua (raw từ trang Thuế có 'nmten'); người bán đã có ở nbten
        d["nmten"] = raw.get("nmten", "") or raw.get("nmtnmua", "") or ""
        # mặt hàng dòng đầu tiên (nếu có detail_json)
        mat_hang = ""
        try:
            dj = r["detail_json"]
            if dj:
                det = json.loads(dj)
                items = _parse_detail_json(det)
                if items:
                    mat_hang = items[0].get("ten_hang", "")
        except Exception:
            pass
        d["mat_hang_dau"] = mat_hang
        out.append(d)
    return out


# ---------- TẢI FILE XML / PDF (đóng gói ZIP) ----------
@app.post("/api/download/{cid}")
def download_files(cid: int, body: dict = Body(...)):
    """
    body: { loai, formats: ["xml","pdf"] }
    Trả về file ZIP chứa toàn bộ XML/PDF của các hóa đơn đã lưu.
    """
    client = get_client(cid)
    if not client.token:
        raise HTTPException(401, "Chưa đăng nhập tài khoản thuế")

    loai = body.get("loai", "purchase")
    formats = body.get("formats", ["xml", "pdf"])

    conn = db()
    rows = conn.execute(
        "SELECT * FROM invoices WHERE company_id=? AND loai=?",
        (cid, loai)).fetchall()
    comp = conn.execute("SELECT * FROM companies WHERE id=?", (cid,)).fetchone()
    conn.close()

    mem = io.BytesIO()
    ok_xml = 0
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as zf:
        for r in rows:
            base = f"{r['khhdon']}_{r['shdon']}_{r['nbmst']}"
            he_thong = r["he_thong"] or "query"
            if "xml" in formats:
                zdata = client.download_xml(
                    r["nbmst"], r["khhdon"], r["khmshdon"], r["shdon"],
                    loai, he_thong)
                if zdata:
                    # zdata là file invoice.zip của TCT -> giải nén lấy html+xml
                    try:
                        inner = zipfile.ZipFile(io.BytesIO(zdata))
                        for nm in inner.namelist():
                            zf.writestr(f"{base}/{os.path.basename(nm)}", inner.read(nm))
                    except Exception:
                        # không phải zip -> lưu thẳng
                        zf.writestr(f"{base}/{base}.xml", zdata)
                    ok_xml += 1
                time.sleep(SP()["file"])
            if "pdf" in formats:
                pass  # cần endpoint/cURL thật của nút tải PDF để bổ sung
    mem.seek(0)

    if ok_xml == 0 and "xml" in formats:
        raise HTTPException(
            502,
            "Không tải được file nào. Token có thể đã hết hạn — đăng nhập lại rồi thử.")

    fname = f"HoaDon_{comp['mst']}_{loai}.zip"
    return StreamingResponse(
        mem, media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={fname}"})


# ---------- XUẤT EXCEL ----------
# Map mã trạng thái xử lý (ttxly) -> mô tả tiếng Việt
TTXLY_DESC = {
    "4": "Hóa đơn không đủ điều kiện cấp mã",
    "5": "Đã cấp mã hóa đơn",
    "6": "Tổng cục thuế đã nhận không mã",
    "8": "TCT đã nhận HĐ có mã khởi tạo từ máy tính tiền",
}
# Map mã trạng thái hóa đơn (tthai)
TTHAI_DESC = {
    "1": "Hóa đơn mới",
    "2": "Hóa đơn thay thế",
    "3": "Hóa đơn điều chỉnh",
    "4": "Hóa đơn đã bị thay thế",
    "5": "Hóa đơn đã bị điều chỉnh",
    "6": "Hóa đơn hủy",
}

def _mo_ta_trang_thai(tthai):
    s = str(tthai or "").strip()
    return TTHAI_DESC.get(s, s or "")

def _mo_ta_ket_qua(ttxly):
    s = str(ttxly or "").strip()
    return TTXLY_DESC.get(s, s or "")


@app.post("/api/import-companies")
async def import_companies(request: Request):
    """
    Import nhiều công ty từ file Excel. Cột nhận diện theo tiêu đề (dòng 1):
    Tên công ty | MST | Tên đăng nhập | Mật khẩu | Thư mục lưu | Người ký
    (chỉ Tên và MST là bắt buộc). Bỏ qua dòng trùng MST.
    """
    import openpyxl, io as _io
    form = await request.form()
    up = form.get("file")
    if up is None:
        raise HTTPException(400, "Chưa chọn file Excel")
    content = await up.read()
    try:
        wb = openpyxl.load_workbook(_io.BytesIO(content), data_only=True)
    except Exception as e:
        raise HTTPException(400, f"Không đọc được file Excel: {e}")
    ws = wb.active

    def find_col(*names):
        for c in range(1, ws.max_column + 1):
            v = str(ws.cell(1, c).value or "").strip().lower()
            for n in names:
                if n in v:
                    return c
        return None

    c_ten = find_col("tên công ty", "ten cong ty", "tên")
    c_mst = find_col("mst", "mã số thuế", "ma so thue")
    c_user = find_col("đăng nhập", "dang nhap", "username", "user")
    c_pass = find_col("mật khẩu", "mat khau", "password", "pass")
    c_dir = find_col("thư mục", "thu muc", "save_dir", "lưu")
    c_nk = find_col("người ký", "nguoi ky")
    if not c_ten or not c_mst:
        raise HTTPException(400, "File phải có cột 'Tên công ty' và 'MST'")

    conn = db()
    added = skipped = 0
    errors = []
    for r in range(2, ws.max_row + 1):
        ten = str(ws.cell(r, c_ten).value or "").strip()
        mst = str(ws.cell(r, c_mst).value or "").strip()
        if not ten or not mst:
            continue
        # MST có thể bị Excel đọc thành số -> bỏ .0
        if mst.endswith(".0"):
            mst = mst[:-2]
        dup = conn.execute("SELECT id FROM companies WHERE mst=?", (mst,)).fetchone()
        if dup:
            skipped += 1
            continue
        user = str(ws.cell(r, c_user).value or "").strip() if c_user else ""
        pw = str(ws.cell(r, c_pass).value or "").strip() if c_pass else ""
        sdir = str(ws.cell(r, c_dir).value or "").strip() if c_dir else ""
        nk = str(ws.cell(r, c_nk).value or "").strip() if c_nk else ""
        try:
            conn.execute(
                "INSERT INTO companies (ten, mst, username, password, ghichu, save_dir, nguoi_ky, created_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (ten, mst, user, pw, "", sdir, nk, datetime.datetime.now().isoformat()))
            added += 1
        except Exception as e:
            errors.append(f"{ten}: {e}")
    conn.commit()
    conn.close()
    return {"ok": True, "added": added, "skipped": skipped, "errors": errors[:5]}


@app.get("/api/export-companies")
def export_companies():
    """Xuất danh sách công ty hiện có ra file Excel (kèm thông tin đăng nhập)."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill
    conn = db()
    rows = conn.execute("SELECT * FROM companies ORDER BY ten").fetchall()
    conn.close()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Danh sách công ty"
    headers = ["Tên công ty", "MST", "Tên đăng nhập", "Mật khẩu",
               "Thư mục lưu", "Người ký"]
    ws.append(headers)
    for c in range(1, len(headers) + 1):
        ws.cell(1, c).font = Font(bold=True, color="FFFFFF")
        ws.cell(1, c).fill = PatternFill("solid", fgColor="1F6B4A")
    for r in rows:
        d = dict(r)
        ws.append([d.get("ten", ""), d.get("mst", ""), d.get("username", ""),
                   d.get("password", ""), d.get("save_dir", ""), d.get("nguoi_ky", "")])
    for col, w in zip("ABCDEF", [32, 16, 16, 16, 24, 18]):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A2"
    fname = "DanhSach_CongTy.xlsx"
    path = os.path.join(DOWNLOAD_DIR, fname)
    wb.save(path)
    # lưu ra Desktop cho dễ tìm
    desktop = _get_desktop_dir()
    open_path = path
    if desktop and os.path.isdir(desktop):
        try:
            import shutil
            shutil.copy(path, os.path.join(desktop, fname))
            open_path = os.path.join(desktop, fname)
        except Exception:
            pass
    _open_file_local(open_path)
    return FileResponse(path, filename=fname)


@app.get("/api/companies-template")
def companies_template():
    """Tải file Excel mẫu để nhập danh sách công ty."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Danh sách công ty"
    headers = ["Tên công ty", "MST", "Tên đăng nhập", "Mật khẩu",
               "Thư mục lưu", "Người ký"]
    ws.append(headers)
    for c in range(1, len(headers) + 1):
        ws.cell(1, c).font = Font(bold=True, color="FFFFFF")
        ws.cell(1, c).fill = PatternFill("solid", fgColor="1F6B4A")
    ws.append(["CÔNG TY TNHH ABC", "0301234567", "0301234567", "matkhau123",
               "D:\\HoaDon\\ABC", "Nguyễn Văn A"])
    ws.append(["CÔNG TY TNHH XYZ", "0307654321", "", "", "", ""])
    for col, w in zip("ABCDEF", [32, 16, 16, 16, 22, 18]):
        ws.column_dimensions[col].width = w
    path = os.path.join(DOWNLOAD_DIR, "Mau_DanhSach_CongTy.xlsx")
    wb.save(path)
    return FileResponse(path, filename="Mau_DanhSach_CongTy.xlsx")


def _parse_tokhai_nhap(wb):
    """Đọc 1 file tờ khai hải quan nhập khẩu (.xlsx), trả về dict:
    {so_tk, ngay_dk, nguoi_xk, items:[{ten, sluong, dvt, tri_gia_gtgt, ts_gtgt,
     tien_thue_gtgt, tri_gia_nk, ts_nk, tien_thue_nk}, ...]}
    Cấu trúc: sheet TKN, mỗi trang bắt đầu '<IMP>', mỗi dòng hàng '<NN>'.
    Giá trị lấy theo NHÃN ở cột nhỏ + giá trị ở cột bên phải."""
    if "TKN" in wb.sheetnames:
        ws = wb["TKN"]
    else:
        ws = wb[wb.sheetnames[0]]

    def cell(r, c):
        v = ws.cell(r, c).value
        return str(v).strip() if v is not None else ""

    def to_num(s):
        # "18.320.976,2154" -> 18320976.2154 ; "8%" -> 8
        s = str(s).replace("%", "").strip()
        if not s:
            return 0
        s = s.replace(".", "").replace(",", ".")
        try:
            return float(s)
        except Exception:
            return 0

    def row_label(r):
        # nhãn của dòng = ô text đầu tiên ở cột C(3) hoặc D(4)
        return cell(r, 3) or cell(r, 4)

    # tìm số tờ khai, ngày đăng ký, người xuất khẩu (trang đầu)
    so_tk = ngay_dk = nguoi_xk = ""
    maxr = ws.max_row
    for r in range(1, min(maxr, 60) + 1):
        lab = cell(r, 3)
        if lab == "Số tờ khai" and not so_tk:
            so_tk = cell(r, 5) or cell(r, 6) or cell(r, 7)
        if lab == "Ngày đăng ký" and not ngay_dk:
            ngay_dk = cell(r, 7) or cell(r, 6) or cell(r, 8)
        if lab == "Người xuất khẩu" and not nguoi_xk:
            # tên thường ở dòng "Tên" 1-2 dòng sau, cột H
            for rr in range(r, min(r + 6, maxr)):
                if cell(rr, 4) == "Tên":
                    nguoi_xk = cell(rr, 8)
                    break

    # chuẩn hóa ngày: "16/01/2026 10:55:16" -> 2026-01-16
    nd = ""
    if ngay_dk:
        d0 = ngay_dk.split()[0]
        if "/" in d0:
            p = d0.split("/")
            if len(p) == 3:
                nd = f"{p[2]}-{int(p[1]):02d}-{int(p[0]):02d}"

    # duyệt các dòng hàng: mỗi khối bắt đầu ô C = '<01>'..'<NN>'
    import re as _re
    items = []
    r = 1
    while r <= maxr:
        cval = cell(r, 3)
        if _re.fullmatch(r"<\d+>", cval):
            blk_start = r
            # tìm hết khối (tới '<NN>' tiếp theo hoặc '<IMP>' hoặc hết)
            r2 = r + 1
            while r2 <= maxr:
                c2 = cell(r2, 3)
                if _re.fullmatch(r"<\d+>", c2) or c2 == "<IMP>":
                    break
                r2 += 1
            blk_end = r2
            it = _parse_hang_block(ws, blk_start, blk_end, cell, to_num)
            if it and (it.get("ten") or it.get("tri_gia_gtgt")):
                items.append(it)
            r = blk_end
        else:
            r += 1

    return {"so_tk": so_tk, "ngay_dk": nd, "nguoi_xk": nguoi_xk, "items": items}


def _parse_hang_block(ws, r0, r1, cell, to_num):
    """Trích 1 dòng hàng từ khối [r0, r1)."""
    it = {"ten": "", "sluong": 0, "dvt": "", "tri_gia_gtgt": 0, "ts_gtgt": "",
          "tien_thue_gtgt": 0, "tri_gia_nk": 0, "ts_nk": "", "tien_thue_nk": 0}
    in_thue_khac = False
    gtgt_found = False
    for r in range(r0, r1):
        lab_c = cell(r, 3)
        lab_d = cell(r, 4)
        # Mô tả hàng hóa -> cột G(7)
        if lab_c == "Mô tả hàng hóa":
            it["ten"] = cell(r, 7) or cell(r, 8)
        # Số lượng (1): nhãn ở cột S(19) -> giá trị V(22), đơn vị AE(31)
        if cell(r, 19) == "Số lượng (1)":
            it["sluong"] = to_num(cell(r, 22))
            it["dvt"] = cell(r, 31)  # AE = đơn vị tính (BAG/PCE...)
        # Thuế nhập khẩu
        if lab_c == "Thuế nhập khẩu":
            in_thue_khac = False
        # Trị giá tính thuế(S) (thuế NK) -> I(9)
        if lab_d == "Trị giá tính thuế(S)":
            it["tri_gia_nk"] = to_num(cell(r, 9))
        # Thuế suất NK -> I(9), chỉ lấy khi CHƯA vào phần thuế khác
        if lab_d == "Thuế suất" and not in_thue_khac and not it["ts_nk"]:
            it["ts_nk"] = cell(r, 9)
        # Số tiền thuế NK -> I(9)
        if lab_d == "Số tiền thuế" and not in_thue_khac and not it["tien_thue_nk"]:
            it["tien_thue_nk"] = to_num(cell(r, 9))
        # Phần "Thuế và thu khác" (chứa GTGT)
        if lab_c == "Thuế và thu khác":
            in_thue_khac = True
        # mục GTGT: Tên = "Thuế GTGT" (cột H=8)
        if in_thue_khac and cell(r, 8) == "Thuế GTGT":
            gtgt_found = True
        if gtgt_found and not it["tri_gia_gtgt"] and lab_d == "Trị giá tính thuế":
            it["tri_gia_gtgt"] = to_num(cell(r, 9))
        if gtgt_found and not it["ts_gtgt"] and lab_d == "Thuế suất":
            it["ts_gtgt"] = cell(r, 9)
        if gtgt_found and not it["tien_thue_gtgt"] and lab_d == "Số tiền thuế":
            it["tien_thue_gtgt"] = to_num(cell(r, 9))
    return it


@app.post("/api/import-tokhai-nhap/{cid}")
async def import_tokhai_nhap(cid: int, request: Request):
    """Import 1 hoặc nhiều file tờ khai hải quan nhập khẩu (.xlsx).
    Mỗi dòng hàng -> 1 dòng trong Chi tiết MUA VÀO."""
    import openpyxl, io as _io
    form = await request.form()
    files = form.getlist("files") or ([form.get("file")] if form.get("file") else [])
    if not files:
        raise HTTPException(400, "Chưa chọn file tờ khai")
    conn = db()
    added = 0
    tong_tk = 0
    loi = []
    for up in files:
        if up is None:
            continue
        try:
            content = await up.read()
            wb = openpyxl.load_workbook(_io.BytesIO(content), data_only=True)
            tk = _parse_tokhai_nhap(wb)
        except Exception as e:
            loi.append(f"{getattr(up,'filename','file')}: {e}")
            continue
        if not tk["so_tk"] or not tk["items"]:
            loi.append(f"{getattr(up,'filename','file')}: không đọc được số tờ khai hoặc dòng hàng")
            continue
        conn.execute("""
            INSERT INTO tokhai_nhap (company_id, so_tk, ngay_dk, nguoi_xk, items_json, updated_at)
            VALUES (?,?,?,?,?,?)
            ON CONFLICT(company_id, so_tk) DO UPDATE SET
                ngay_dk=excluded.ngay_dk, nguoi_xk=excluded.nguoi_xk,
                items_json=excluded.items_json, updated_at=excluded.updated_at
        """, (cid, tk["so_tk"], tk["ngay_dk"], tk["nguoi_xk"],
              json.dumps(tk["items"], ensure_ascii=False),
              datetime.datetime.now().isoformat()))
        added += len(tk["items"])
        tong_tk += 1
    conn.commit()
    conn.close()
    return {"ok": True, "so_to_khai": tong_tk, "so_dong_hang": added, "loi": loi[:5]}


@app.get("/api/tokhai-nhap/{cid}")
def list_tokhai_nhap(cid: int):
    conn = db()
    rows = conn.execute(
        "SELECT so_tk, ngay_dk, nguoi_xk, items_json FROM tokhai_nhap WHERE company_id=? ORDER BY ngay_dk",
        (cid,)).fetchall()
    conn.close()
    out = []
    for r in rows:
        try:
            items = json.loads(r["items_json"]) if r["items_json"] else []
        except Exception:
            items = []
        out.append({"so_tk": r["so_tk"], "ngay_dk": r["ngay_dk"],
                    "nguoi_xk": r["nguoi_xk"], "so_dong": len(items)})
    return out


@app.delete("/api/tokhai-nhap/{cid}")
def del_tokhai_nhap(cid: int, so_tk: str = ""):
    conn = db()
    if so_tk:
        conn.execute("DELETE FROM tokhai_nhap WHERE company_id=? AND so_tk=?", (cid, so_tk))
    else:
        conn.execute("DELETE FROM tokhai_nhap WHERE company_id=?", (cid,))
    conn.commit()
    conn.close()
    return {"ok": True}


@app.post("/api/clear-downloads")
def clear_downloads(scope: str = "temp"):
    """Xóa file đã tải để nhẹ máy.
    scope='temp'    -> chỉ xóa file tạm trong thư mục app (downloads/) - AN TOÀN
    scope='all'     -> xóa thêm file XML/PDF trong tất cả thư mục lưu của các công ty
    Trả về số file đã xóa và dung lượng giải phóng (MB)."""
    import shutil
    xoa = 0
    dung_luong = 0

    def _xoa_file(path):
        nonlocal xoa, dung_luong
        try:
            sz = os.path.getsize(path)
            os.remove(path)
            xoa += 1
            dung_luong += sz
        except Exception:
            pass

    # 1) xóa file tạm trong downloads/ (xlsx, xml, pdf, zip)
    if os.path.isdir(DOWNLOAD_DIR):
        for f in os.listdir(DOWNLOAD_DIR):
            fp = os.path.join(DOWNLOAD_DIR, f)
            if os.path.isfile(fp) and f.lower().endswith((".xml", ".pdf", ".zip", ".xlsx", ".html")):
                _xoa_file(fp)
            elif os.path.isdir(fp):
                # thư mục con (mua_vào, bán_ra...) -> xóa file bên trong
                for root, _dirs, files in os.walk(fp):
                    for ff in files:
                        if ff.lower().endswith((".xml", ".pdf", ".zip", ".html")):
                            _xoa_file(os.path.join(root, ff))

    # 2) nếu scope='all' -> xóa file XML/PDF trong thư mục lưu của các công ty
    if scope == "all":
        conn = db()
        dirs = conn.execute("SELECT DISTINCT save_dir FROM companies WHERE save_dir IS NOT NULL AND save_dir<>''").fetchall()
        conn.close()
        for d in dirs:
            sd = (d["save_dir"] or "").strip()
            if sd and os.path.isdir(sd):
                for root, _dirs, files in os.walk(sd):
                    for ff in files:
                        if ff.lower().endswith((".xml", ".pdf", ".zip", ".html", ".xlsx")):
                            _xoa_file(os.path.join(root, ff))

    return {"ok": True, "so_file": xoa, "dung_luong_mb": round(dung_luong / 1024 / 1024, 2)}


@app.get("/api/downloads-size")
def downloads_size():
    """Trả về số file và dung lượng đang chiếm (để hiển thị trước khi xóa)."""
    tong = 0
    sl = 0
    if os.path.isdir(DOWNLOAD_DIR):
        for root, _dirs, files in os.walk(DOWNLOAD_DIR):
            for ff in files:
                if ff.lower().endswith((".xml", ".pdf", ".zip", ".xlsx", ".html")):
                    try:
                        tong += os.path.getsize(os.path.join(root, ff))
                        sl += 1
                    except Exception:
                        pass
    return {"so_file": sl, "dung_luong_mb": round(tong / 1024 / 1024, 2)}


def _doc_sheet_nhap_lieu(wb, sheet_ten, header_marker):
    """Đọc 1 sheet, trả về (header, rows) đã bỏ tiêu đề/tổng/nhóm. None nếu không có sheet."""
    import re as _re2
    ws = None
    for sn in wb.sheetnames:
        if sn.strip().lower() == sheet_ten.lower():
            ws = wb[sn]; break
    if ws is None:
        return None
    hrow = None
    for r in range(1, min(ws.max_row, 15) + 1):
        if str(ws.cell(r, 1).value or "").strip() == header_marker:
            hrow = r; break
    if hrow is None:
        return None
    ncol = ws.max_column
    header = [str(ws.cell(hrow, c).value or "").strip() for c in range(1, ncol + 1)]
    rows = []
    for r in range(hrow + 1, ws.max_row + 1):
        vals = [ws.cell(r, c).value for c in range(1, ncol + 1)]
        if all(v is None or str(v).strip() == "" for v in vals):
            continue
        joined = " ".join(str(v) for v in vals if v is not None).lower().strip()
        if "tổng cộng" in joined or "tổng nhóm" in joined:
            continue
        if _re2.match(r"^\d+\.\s", joined):
            continue
        rows.append([("" if v is None else v) for v in vals])
    return header, rows


@app.post("/api/nhap-lieu/import/{cid}")
async def nhap_lieu_import(cid: int, request: Request, loai: str = "in"):
    """Import nhiều file Excel cho Nhập Liệu, GỘP (nối đuôi) thành 1 bảng.
    loai='in'  -> đọc sheet 'Chi tiết MUA VÀO'
    loai='out' -> đọc sheet 'BK Bán ra'
    Trả về header + tất cả các dòng dữ liệu đã gộp (bỏ tiêu đề và dòng tổng)."""
    import openpyxl, io as _io
    form = await request.form()
    files = form.getlist("files") or ([form.get("file")] if form.get("file") else [])
    if not files:
        raise HTTPException(400, "Chưa chọn file")

    header_in, rows_in = [], []
    header_out, rows_out = [], []
    so_file_ok = 0
    loi = []

    for up in files:
        if up is None:
            continue
        fn = getattr(up, "filename", "file")
        try:
            content = await up.read()
            wb = openpyxl.load_workbook(_io.BytesIO(content), data_only=True)
        except Exception as e:
            loi.append(f"{fn}: không đọc được ({e})")
            continue

        co_du_lieu = False
        kq_in = _doc_sheet_nhap_lieu(wb, "Chi tiết MUA VÀO", "Ký hiệu")
        if kq_in:
            h, rs = kq_in
            if not header_in:
                header_in = h
            rows_in.extend(rs)
            co_du_lieu = True
        kq_out = _doc_sheet_nhap_lieu(wb, "BK Bán ra", "STT")
        if kq_out:
            h, rs = kq_out
            if not header_out:
                header_out = h
            rows_out.extend(rs)
            co_du_lieu = True
        if co_du_lieu:
            so_file_ok += 1
        else:
            loi.append(f"{fn}: không có sheet 'Chi tiết MUA VÀO' hoặc 'BK Bán ra'")

    conn = db()
    conn.execute("""CREATE TABLE IF NOT EXISTS nhap_lieu (
        id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, loai TEXT,
        header_json TEXT, rows_json TEXT, updated_at TEXT,
        UNIQUE(company_id, loai))""")
    conn.commit()
    conn.close()

    return {"ok": True, "so_file": so_file_ok,
            "in": {"header": header_in, "rows": rows_in, "so_dong": len(rows_in)},
            "out": {"header": header_out, "rows": rows_out, "so_dong": len(rows_out)},
            "loi": loi[:5]}


@app.post("/api/nhap-lieu/save/{cid}")
async def nhap_lieu_save(cid: int, request: Request, loai: str = "in"):
    """Lưu bộ dữ liệu Nhập Liệu của công ty (mỗi công ty 1 bộ/loại, import đè lên)."""
    body = await request.json()
    header = body.get("header", [])
    rows = body.get("rows", [])
    conn = db()
    conn.execute("""CREATE TABLE IF NOT EXISTS nhap_lieu (
        id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, loai TEXT,
        header_json TEXT, rows_json TEXT, updated_at TEXT,
        UNIQUE(company_id, loai))""")
    conn.execute("""INSERT INTO nhap_lieu (company_id, loai, header_json, rows_json, updated_at)
        VALUES (?,?,?,?,?)
        ON CONFLICT(company_id, loai) DO UPDATE SET
            header_json=excluded.header_json, rows_json=excluded.rows_json,
            updated_at=excluded.updated_at""",
        (cid, loai, json.dumps(header, ensure_ascii=False),
         json.dumps(rows, ensure_ascii=False), datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return {"ok": True, "so_dong": len(rows)}


@app.get("/api/nhap-lieu/{cid}")
def nhap_lieu_get(cid: int, loai: str = "in"):
    """Lấy dữ liệu Nhập Liệu đã lưu của công ty."""
    conn = db()
    try:
        r = conn.execute("SELECT header_json, rows_json, updated_at FROM nhap_lieu WHERE company_id=? AND loai=?",
                         (cid, loai)).fetchone()
    except Exception:
        r = None
    conn.close()
    if not r:
        return {"header": [], "rows": [], "updated_at": ""}
    try:
        return {"header": json.loads(r["header_json"]), "rows": json.loads(r["rows_json"]),
                "updated_at": r["updated_at"] or ""}
    except Exception:
        return {"header": [], "rows": [], "updated_at": ""}


@app.delete("/api/nhap-lieu/{cid}")
def nhap_lieu_del(cid: int, loai: str = "in"):
    conn = db()
    try:
        conn.execute("DELETE FROM nhap_lieu WHERE company_id=? AND loai=?", (cid, loai))
        conn.commit()
    except Exception:
        pass
    conn.close()
    return {"ok": True}


@app.post("/api/nhap-lieu/export/{cid}")
async def nhap_lieu_export(cid: int, request: Request, loai: str = "in"):
    """Xuất bảng nhập liệu ra Excel (có dòng tổng cộng)."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    body = await request.json()
    header = body.get("header", [])
    rows = body.get("rows", [])
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Đầu ra" if loai == "out" else "Đầu vào"
    ws.append(header)
    for c in range(1, len(header) + 1):
        ws.cell(1, c).font = Font(bold=True, color="FFFFFF")
        ws.cell(1, c).fill = PatternFill("solid", fgColor="2E5C8A")
    # cột tiền để tính tổng + format
    def la_tien(h):
        t = str(h or "").lower()
        return any(k in t for k in ["doanh số", "thành tiền", "thuế gtgt", "chưa thuế",
                                    "chưa vat", "tiền thuế", "thuế nk", "trị giá", "tổng"])
    tien_idx = [i for i, h in enumerate(header) if la_tien(h)]
    for row in rows:
        vals = []
        for i, v in enumerate(row):
            if i in tien_idx and v not in ("", None):
                vals.append(_to_num(v) or 0)
            else:
                vals.append(v)
        ws.append(vals)
    # dòng tổng cộng
    tong_row = ["" for _ in header]
    if header:
        tong_row[0] = "TỔNG CỘNG"
    for i in tien_idx:
        s = sum(_to_num(r[i]) or 0 for r in rows if i < len(r))
        tong_row[i] = s
    ws.append(tong_row)
    last = ws.max_row
    for c in range(1, len(header) + 1):
        ws.cell(last, c).font = Font(bold=True, color="C00000")
    # format số + độ rộng
    from openpyxl.utils import get_column_letter
    for i in tien_idx:
        for r in range(2, ws.max_row + 1):
            ws.cell(r, i + 1).number_format = "#,##0"
    for c in range(1, len(header) + 1):
        ws.column_dimensions[get_column_letter(c)].width = 16
    ws.freeze_panes = "A2"
    if ws.max_row > 1:
        ws.auto_filter.ref = f"A1:{get_column_letter(len(header))}{ws.max_row}"

    fname = f"NhapLieu_{'DauRa' if loai=='out' else 'DauVao'}.xlsx"
    path = os.path.join(DOWNLOAD_DIR, fname)
    wb.save(path)
    desktop = _get_desktop_dir()
    if desktop and os.path.isdir(desktop):
        try:
            import shutil
            shutil.copy(path, os.path.join(desktop, fname))
        except Exception:
            pass
    return FileResponse(path, filename=fname)


@app.get("/api/danh-muc-ncc/{cid}")
def danh_muc_ncc(cid: int):
    """Tạo file Danh mục KH/NCC từ dữ liệu hóa đơn mua vào + bán ra.
    Lấy MST + tên từ Chi tiết MUA VÀO (nbmst/nbten) và BK Bán ra (nmmst/nmten).
    Lọc trùng MST, loại MST công ty mình. Trả về file Excel theo form mẫu MISA."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    conn = db()
    rows = conn.execute(
        "SELECT loai, nbmst, nbten, nmmst, raw FROM invoices WHERE company_id=?", (cid,)).fetchall()
    comp = conn.execute("SELECT mst FROM companies WHERE id=?", (cid,)).fetchone()
    conn.close()
    mst_cty = str(comp["mst"] or "").strip() if comp else ""

    def chuan_hoa_mst(s):
        """Chuẩn hóa MST: bỏ khoảng trắng, dấu gạch, chỉ giữ chữ số và chữ cái."""
        s = str(s or "").strip().replace("-", "").replace(" ", "").replace(".", "")
        return s

    # thu thập MST + tên (unique, lọc trùng)
    ds = {}  # {mst_chuan: ten}
    for r in rows:
        if r["loai"] == "purchase":
            mst = chuan_hoa_mst(r["nbmst"])
            ten = str(r["nbten"] or "").strip()
        else:
            try:
                raw = json.loads(r["raw"]) if r["raw"] else {}
            except Exception:
                raw = {}
            mst = chuan_hoa_mst(r["nmmst"] or raw.get("nmmst", ""))
            ten = str(raw.get("nmten", "") or "").strip()
        # bỏ qua: trống, MST công ty mình
        if not mst or mst == chuan_hoa_mst(mst_cty):
            continue
        # chỉ lấy lần đầu (tên dài hơn ưu tiên)
        if mst not in ds or (len(ten) > len(ds[mst])):
            ds[mst] = ten

    # ===== ĐỌC THÊM TỪ NHẬP LIỆU (bảng kê đã import vào nhap_lieu) =====
    try:
        conn2 = db()
        nl_rows = conn2.execute(
            "SELECT loai, header_json, rows_json FROM nhap_lieu WHERE company_id=?", (cid,)).fetchall()
        conn2.close()
        for nl in nl_rows:
            try:
                hdr = json.loads(nl["header_json"]) if nl["header_json"] else []
                data = json.loads(nl["rows_json"]) if nl["rows_json"] else []
            except Exception:
                continue
            hdr_low = [str(h or "").strip().lower() for h in hdr]
            # tìm cột MST và tên
            ci_mst = ci_ten = -1
            for i, h in enumerate(hdr_low):
                if ci_mst < 0 and ("mst" in h and ("bán" in h or "mua" in h or "ncc" in h or "cung" in h)):
                    ci_mst = i
                if ci_ten < 0 and ("người" in h and ("bán" in h or "mua" in h)):
                    ci_ten = i
            # fallback: cột có "mst" hoặc "mã số thuế"
            if ci_mst < 0:
                for i, h in enumerate(hdr_low):
                    if "mst" in h or "mã số thuế" in h:
                        ci_mst = i; break
            if ci_ten < 0:
                for i, h in enumerate(hdr_low):
                    if "tên" in h and ("bán" in h or "mua" in h or "ncc" in h or "khách" in h):
                        ci_ten = i; break
            if ci_mst < 0:
                continue
            for row in data:
                if ci_mst >= len(row):
                    continue
                mst = chuan_hoa_mst(row[ci_mst])
                ten = str(row[ci_ten] if ci_ten >= 0 and ci_ten < len(row) else "").strip()
                if not mst or mst == chuan_hoa_mst(mst_cty):
                    continue
                if mst not in ds or (ten and len(ten) > len(ds.get(mst, ""))):
                    ds[mst] = ten
    except Exception:
        pass

    # sắp xếp theo MST
    items = sorted(ds.items(), key=lambda x: x[0])

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Danh mục NCC"
    # header
    headers = ["Là tổ chức/cá nhân", "Là khách hàng", "Mã nhà cung cấp (*)",
               "Tên nhà cung cấp (*)", "Địa chỉ", "Mã số thuế",
               "Điện thoại", "Fax", "Email", "Website", "Nhóm KH/NCC"]
    ws.append(headers)
    for c in range(1, len(headers) + 1):
        cell = ws.cell(1, c)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="2E5C8A")

    for i, (mst, ten) in enumerate(items, 2):
        ws.cell(i, 1).value = 0                    # A: Là tổ chức/cá nhân = 0
        ws.cell(i, 2).value = 1                    # B: Là khách hàng = 1
        ws.cell(i, 3).value = mst                  # C: Mã NCC = MST
        ws.cell(i, 4).value = ten                  # D: Tên NCC
        # F: Mã số thuế = công thức Excel
        ws.cell(i, 6).value = f'=IF(AND(ISNUMBER(VALUE(LEFT(C{i},1))),LEN(C{i})<>12),C{i},"")'

    # format
    from openpyxl.utils import get_column_letter
    ws.column_dimensions["A"].width = 18
    ws.column_dimensions["B"].width = 14
    ws.column_dimensions["C"].width = 20
    ws.column_dimensions["D"].width = 40
    ws.column_dimensions["E"].width = 30
    ws.column_dimensions["F"].width = 20
    ws.freeze_panes = "A2"
    if ws.max_row > 1:
        ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{ws.max_row}"

    fname = f"DanhMuc_KHNCC_{mst_cty}.xlsx"
    path = os.path.join(DOWNLOAD_DIR, fname)
    wb.save(path)
    desktop = _get_desktop_dir()
    if desktop and os.path.isdir(desktop):
        try:
            import shutil
            shutil.copy(path, os.path.join(desktop, fname))
        except Exception:
            pass
    return FileResponse(path, filename=fname)


@app.post("/api/import-excel/{cid}")
async def import_excel(cid: int, request: Request, ky: str = ""):
    """
    Import file Excel đã kiểm tra/điều chỉnh. Đọc sheet 'Chi tiết MUA VÀO' và
    'Chi tiết BÁN RA', tính tổng doanh số + thuế (bán ra tách theo thuế suất),
    lưu vào imported_data. Sau khi import, xuất XML và tạm tính VAT dùng số này.
    """
    import openpyxl, io as _io
    form = await request.form()
    up = form.get("file")
    if up is None:
        raise HTTPException(400, "Chưa chọn file Excel")
    content = await up.read()
    try:
        wb = openpyxl.load_workbook(_io.BytesIO(content), data_only=True)
    except Exception as e:
        raise HTTPException(400, f"Không đọc được file Excel: {e}")

    def col_idx(ws, ten):
        for c in range(1, ws.max_column + 1):
            if str(ws.cell(1, c).value or "").strip().lower() == ten.lower():
                return c
        return None

    mua_ds = mua_thue = 0
    ban = {"0": {"ds": 0, "thue": 0}, "5": {"ds": 0, "thue": 0},
           "8": {"ds": 0, "thue": 0}, "10": {"ds": 0, "thue": 0}}

    def num(v):
        try:
            return float(v)
        except Exception:
            return 0

    def norm_ts(v):
        s = str(v or "").replace("%", "").strip()
        if s in ("0", "5", "8", "10"):
            return s
        return None

    # ===== MUA VÀO: đọc từ sheet 'BK Mua vào' =====
    if "BK Mua vào" in wb.sheetnames:
        ws = wb["BK Mua vào"]
        c_ds = col_idx(ws, "Doanh số mua chưa thuế")
        c_thue = col_idx(ws, "Thuế GTGT")
        for r in range(2, ws.max_row + 1):
            full = " ".join(str(ws.cell(r, c).value or "") for c in range(1, ws.max_column + 1)).lower()
            if "tổng" in full:   # bỏ dòng TỔNG CỘNG (ở bất kỳ cột nào)
                continue
            if c_ds:
                mua_ds += num(ws.cell(r, c_ds).value)
            if c_thue:
                mua_thue += num(ws.cell(r, c_thue).value)

    # ===== BÁN RA: đọc từ sheet 'BK Bán ra' (tách nhóm theo dòng tiêu đề) =====
    if "BK Bán ra" in wb.sheetnames:
        ws = wb["BK Bán ra"]
        c_ds = col_idx(ws, "Doanh số bán chưa thuế")
        c_thue = col_idx(ws, "Thuế GTGT")
        # nếu không tìm thấy header (do có tiêu đề phía trên), dò theo cột cố định
        if not c_ds:
            # tìm dòng header chứa "Doanh số bán chưa thuế"
            for r in range(1, min(ws.max_row, 30) + 1):
                for c in range(1, ws.max_column + 1):
                    v = str(ws.cell(r, c).value or "")
                    if "Doanh số bán chưa thuế" in v:
                        c_ds = c
                    if v.strip() == "Thuế GTGT":
                        c_thue = c
                if c_ds:
                    break
        cur_nhom = None
        for r in range(1, ws.max_row + 1):
            # gộp text cả dòng để phát hiện tiêu đề nhóm / dòng tổng
            full = " ".join(str(ws.cell(r, c).value or "") for c in range(1, ws.max_column + 1))
            low = full.lower()
            head3 = " ".join(str(ws.cell(r, c).value or "") for c in range(1, 4))
            # dòng tiêu đề nhóm thuế suất
            if "thuế suất" in head3.lower() or "%" in head3 or "không chịu thuế" in head3.lower():
                if "0%" in head3: cur_nhom = "0"
                elif "5%" in head3: cur_nhom = "5"
                elif "8%" in head3: cur_nhom = "8"
                elif "10%" in head3: cur_nhom = "10"
                elif "không chịu" in head3.lower(): cur_nhom = None
                continue
            # BỎ mọi dòng tổng (Tổng nhóm / TỔNG CỘNG - ở bất kỳ cột nào)
            if "tổng" in low:
                continue
            ds = num(ws.cell(r, c_ds).value) if c_ds else 0
            th = num(ws.cell(r, c_thue).value) if c_thue else 0
            if (ds or th) and cur_nhom in ban:
                ban[cur_nhom]["ds"] += ds
                ban[cur_nhom]["thue"] += th

    conn = db()
    conn.execute("""
        INSERT INTO imported_data (company_id, ky, mua_ds, mua_thue,
            ban_ds_0, ban_ds_5, ban_thue_5, ban_ds_8, ban_thue_8,
            ban_ds_10, ban_thue_10, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(company_id, ky) DO UPDATE SET
            mua_ds=excluded.mua_ds, mua_thue=excluded.mua_thue,
            ban_ds_0=excluded.ban_ds_0, ban_ds_5=excluded.ban_ds_5,
            ban_thue_5=excluded.ban_thue_5, ban_ds_8=excluded.ban_ds_8,
            ban_thue_8=excluded.ban_thue_8, ban_ds_10=excluded.ban_ds_10,
            ban_thue_10=excluded.ban_thue_10, updated_at=excluded.updated_at
    """, (cid, ky, round(mua_ds), round(mua_thue), round(ban["0"]["ds"]),
          round(ban["5"]["ds"]), round(ban["5"]["thue"]),
          round(ban["8"]["ds"]), round(ban["8"]["thue"]),
          round(ban["10"]["ds"]), round(ban["10"]["thue"]),
          datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return {
        "ok": True, "mua_ds": round(mua_ds), "mua_thue": round(mua_thue),
        "ban_thue": round(sum(b["thue"] for b in ban.values())),
        "ban_8_ds": round(ban["8"]["ds"]),
    }


def _get_imported(cid, ky=""):
    """Lấy dữ liệu đã import ĐÚNG KỲ. Nếu kỳ này chưa import -> None (dùng tra cứu).
    Chỉ khi không truyền kỳ (ky='') mới lấy bản import mới nhất."""
    conn = db()
    row = None
    if ky:
        # chỉ lấy import KHỚP ĐÚNG kỳ đang xem
        row = conn.execute("SELECT * FROM imported_data WHERE company_id=? AND ky=?",
                           (cid, ky)).fetchone()
    else:
        # không có kỳ -> lấy bản mới nhất (vd gọi không kèm kỳ)
        row = conn.execute(
            "SELECT * FROM imported_data WHERE company_id=? ORDER BY updated_at DESC LIMIT 1",
            (cid,)).fetchone()
    conn.close()
    return row


@app.get("/api/imported/{cid}")
def get_imported_api(cid: int, ky: str = ""):
    """Trả dữ liệu đã import để màn hình hiển thị (nếu có)."""
    row = _get_imported(cid, ky)
    if not row:
        return {"has_import": False}
    d = dict(row)
    mua_ds = _to_num(d["mua_ds"]) or 0
    mua_thue = _to_num(d["mua_thue"]) or 0
    ban_ds = sum((_to_num(d[k]) or 0) for k in
                 ["ban_ds_0", "ban_ds_5", "ban_ds_8", "ban_ds_10"])
    ban_thue = sum((_to_num(d[k]) or 0) for k in
                   ["ban_thue_5", "ban_thue_8", "ban_thue_10"])
    return {
        "has_import": True, "ky": d["ky"],
        "mua_ds": round(mua_ds), "mua_thue": round(mua_thue),
        "ban_ds": round(ban_ds), "ban_thue": round(ban_thue),
        "updated_at": d["updated_at"],
    }


@app.delete("/api/imported/{cid}")
def del_imported_api(cid: int):
    """Xóa dữ liệu import -> quay lại dùng dữ liệu tra cứu."""
    conn = db()
    conn.execute("DELETE FROM imported_data WHERE company_id=?", (cid,))
    conn.commit()
    conn.close()
    return {"ok": True}


@app.get("/api/vat-tmtinh/{cid}")
def vat_tam_tinh(cid: int, ky: str = "", du_dau_ky: float = None):
    """
    Tạm tính thuế VAT trong kỳ:
      - vat_mua: tổng VAT đầu vào (từ hóa đơn mua, loại HĐ thay thế/hủy)
      - vat_ban: tổng VAT đầu ra (từ hóa đơn bán)
      - du_dau_ky: số thuế còn được khấu trừ kỳ trước chuyển sang (người dùng nhập
        hoặc tự lấy 'du_cuoi_ky' của kỳ trước nếu đã lưu)
    Công thức: chenh = vat_ban - vat_mua - du_dau_ky
      chenh > 0 -> phải nộp = chenh ; du_cuoi_ky = 0
      chenh <= 0 -> phải nộp = 0 ; du_cuoi_ky = -chenh (chuyển kỳ sau)
    """
    conn = db()
    comp = conn.execute("SELECT * FROM companies WHERE id=?", (cid,)).fetchone()
    rows = conn.execute("SELECT * FROM invoices WHERE company_id=?", (cid,)).fetchall()
    if not comp:
        conn.close()
        raise HTTPException(404, "Không tìm thấy công ty")

    def loai_bo(r):
        try:
            raw = json.loads(r["raw"]) if r["raw"] else {}
        except Exception:
            raw = {}
        tt = str(raw.get("tthai", r["tthai"]) or "").strip()
        if tt in ("4", "6"):
            return True
        # loại HĐ không đủ điều kiện cấp mã
        kq = str(raw.get("ttxly", "") or "").strip().lower()
        kq_mota = _mo_ta_ket_qua(raw.get("ttxly", "")).lower()
        if kq == "4" or "không đủ điều kiện" in kq or "không đủ điều kiện" in kq_mota:
            return True
        return False

    # ƯU TIÊN dữ liệu đã import từ Excel (nếu có); nếu không, dùng dữ liệu tra cứu
    imp = _get_imported(cid, ky)
    if imp:
        vat_mua = _to_num(imp["mua_thue"]) or 0
        vat_ban = (_to_num(imp["ban_thue_5"]) or 0) + (_to_num(imp["ban_thue_8"]) or 0) \
                  + (_to_num(imp["ban_thue_10"]) or 0)
        nguon = "import"
    else:
        vat_mua = vat_ban = 0
        for r in rows:
            if loai_bo(r):
                continue
            if r["loai"] == "purchase":
                vat_mua += _to_num(r["tgtthue"]) or 0
            elif r["loai"] == "sold":
                vat_ban += _to_num(r["tgtthue"]) or 0
        nguon = "tra cứu"

    # số dư đầu kỳ: ưu tiên giá trị truyền vào; nếu None thì lấy du_cuoi_ky kỳ trước
    if du_dau_ky is None:
        prev = None
        if ky and "/" in ky:
            mm, yyyy = ky.split("/")
            m = int(mm); y = int(yyyy)
            pm = 12 if m == 1 else m - 1
            py = y - 1 if m == 1 else y
            prev_ky = f"{pm:02d}/{py}"
            prev = conn.execute(
                "SELECT du_cuoi_ky FROM vat_balance WHERE company_id=? AND ky=?",
                (cid, prev_ky)).fetchone()
        du_dau_ky = (prev["du_cuoi_ky"] if prev and prev["du_cuoi_ky"] else 0) or 0
        # nếu kỳ này đã lưu rồi, lấy lại số dư đầu kỳ đã lưu
        cur = conn.execute(
            "SELECT du_dau_ky FROM vat_balance WHERE company_id=? AND ky=?",
            (cid, ky)).fetchone()
        if cur and cur["du_dau_ky"] is not None:
            du_dau_ky = cur["du_dau_ky"]

    chenh = vat_ban - vat_mua - (du_dau_ky or 0)
    phai_nop = chenh if chenh > 0 else 0
    du_cuoi_ky = -chenh if chenh <= 0 else 0
    conn.close()
    return {
        "ky": ky, "vat_mua": round(vat_mua), "vat_ban": round(vat_ban),
        "du_dau_ky": round(du_dau_ky or 0),
        "phai_nop": round(phai_nop), "du_cuoi_ky": round(du_cuoi_ky),
        "nguon": nguon,
    }


@app.post("/api/vat-tmtinh/{cid}")
def vat_luu(cid: int, data: dict = Body(...)):
    """Lưu số dư VAT của kỳ (gọi khi bấm Save)."""
    ky = data.get("ky", "")
    if not ky:
        raise HTTPException(400, "Thiếu kỳ kê khai")
    conn = db()
    conn.execute("""
        INSERT INTO vat_balance (company_id, ky, du_dau_ky, vat_mua, vat_ban,
                                 phai_nop, du_cuoi_ky, updated_at)
        VALUES (?,?,?,?,?,?,?,?)
        ON CONFLICT(company_id, ky) DO UPDATE SET
            du_dau_ky=excluded.du_dau_ky, vat_mua=excluded.vat_mua,
            vat_ban=excluded.vat_ban, phai_nop=excluded.phai_nop,
            du_cuoi_ky=excluded.du_cuoi_ky, updated_at=excluded.updated_at
    """, (cid, ky, data.get("du_dau_ky", 0), data.get("vat_mua", 0),
          data.get("vat_ban", 0), data.get("phai_nop", 0),
          data.get("du_cuoi_ky", 0), datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return {"ok": True}


@app.get("/api/export-htkk/{cid}")
def export_htkk(cid: int, ky: str = "", nguoi_ky: str = "", tu: str = "", den: str = ""):
    """
    Tạo file XML tờ khai 01/GTGT (TT80/2021) để nhập vào HTKK.
    Hàng bán ra 8% -> đưa vào nhóm 10% (ct32/ct33) + Phụ lục NQ142/2024.
    ky: 'MM/YYYY' (vd '05/2026'); nếu trống lấy từ hóa đơn.
    """
    import html as _html
    conn = db()
    comp = conn.execute("SELECT * FROM companies WHERE id=?", (cid,)).fetchone()
    rows = conn.execute("SELECT * FROM invoices WHERE company_id=?", (cid,)).fetchall()
    if not comp:
        conn.close()
        raise HTTPException(404, "Không tìm thấy công ty")

    # Việc 1: lưu tên người ký vào công ty; nếu không truyền thì dùng cái đã lưu
    try:
        saved_nk = comp["nguoi_ky"] if "nguoi_ky" in comp.keys() else ""
    except Exception:
        saved_nk = ""
    if nguoi_ky:
        conn.execute("UPDATE companies SET nguoi_ky=? WHERE id=?", (nguoi_ky, cid))
        conn.commit()
    else:
        nguoi_ky = saved_nk or ""
    conn.close()

    def status_loai_bo(r):
        try:
            raw = json.loads(r["raw"]) if r["raw"] else {}
        except Exception:
            raw = {}
        tt = str(raw.get("tthai", r["tthai"]) or "").strip()
        if tt in ("4", "6"):  # đã bị thay thế / hủy
            return True
        kq = str(raw.get("ttxly", "") or "").strip().lower()
        kq_mota = _mo_ta_ket_qua(raw.get("ttxly", "")).lower()
        if kq == "4" or "không đủ điều kiện" in kq or "không đủ điều kiện" in kq_mota:
            return True
        return False

    # ----- Tổng MUA VÀO -----
    mua_ds = mua_thue = 0
    for r in rows:
        if r["loai"] != "purchase" or status_loai_bo(r):
            continue
        mua_ds += _to_num(r["tgtcthue"]) or 0
        mua_thue += _to_num(r["tgtthue"]) or 0

    # ----- BÁN RA: tách theo nhóm thuế suất từ chi tiết -----
    # Cần đọc chi tiết để biết hàng nào 8% (NQ142). Dùng detail_json/file nếu có.
    ban_theo_ts = {"0": {"ds": 0, "thue": 0}, "5": {"ds": 0, "thue": 0},
                   "8": {"ds": 0, "thue": 0}, "10": {"ds": 0, "thue": 0},
                   "KCT": {"ds": 0, "thue": 0}}
    save_dir = (comp["save_dir"] or "").strip() if comp else ""
    client = CLIENTS.get(cid)

    # Xây index file 1 lần (tránh os.walk lặp lại gây chậm)
    _fidx = {}
    if save_dir and os.path.isdir(save_dir):
        for rootdir, _d, files in os.walk(save_dir):
            for fn in files:
                low = fn.lower()
                if not (low.endswith(".zip") or low.endswith(".xml")):
                    continue
                nm = fn.rsplit(".", 1)[0]; parts = nm.split("_")
                if len(parts) >= 2:
                    _fidx.setdefault((parts[0], parts[1].lstrip("0") or "0"),
                                     os.path.join(rootdir, fn))

    def get_summary(r):
        """CHỈ dùng dữ liệu đã có (không gọi mạng để tránh treo)."""
        try:
            dj = r["detail_json"] if "detail_json" in r.keys() else None
        except Exception:
            dj = None
        if dj:
            try:
                return _summary_from_detail_json(json.loads(dj))
            except Exception:
                pass
        fp = _fidx.get((str(r["khhdon"] or ""), str(r["shdon"] or "").lstrip("0") or "0"))
        if fp:
            try:
                with open(fp, "rb") as f:
                    return _parse_invoice_summary(f.read())
            except Exception:
                pass
        return None

    def suy_nhom_thue(ds, thue):
        """Khi không có chi tiết, suy nhóm thuế suất từ tỷ lệ thuế/doanh số."""
        if not ds:
            return "10"
        ty_le = (thue or 0) / ds * 100
        if ty_le < 1:
            return "0"
        for muc in ("5", "8", "10"):
            if abs(ty_le - float(muc)) < 1.5:
                return muc
        return "10"

    ky_auto = ""
    for r in rows:
        if r["loai"] != "sold" or status_loai_bo(r):
            continue
        if not ky_auto:
            nd = (r["tdlap"] or "").split("T")[0]
            if "-" in nd:
                y, m, _d = nd.split("-"); ky_auto = f"{int(m):02d}/{y}"
        info = get_summary(r)
        if info and info.get("theo_ts"):
            for k, v in info["theo_ts"].items():
                tgt = k if k in ban_theo_ts else "10"
                ban_theo_ts[tgt]["ds"] += v["ds"]
                ban_theo_ts[tgt]["thue"] += v["thue"]
        else:
            ds = _to_num(r["tgtcthue"]) or 0
            thue = _to_num(r["tgtthue"]) or 0
            nhom = suy_nhom_thue(ds, thue)
            ban_theo_ts[nhom]["ds"] += ds
            ban_theo_ts[nhom]["thue"] += thue

    if not ky:
        ky = ky_auto or "01/2026"

    # ƯU TIÊN dữ liệu đã import từ Excel (nếu có) -> ghi đè số liệu tra cứu
    imp = _get_imported(cid, ky)
    if imp:
        mua_ds = _to_num(imp["mua_ds"]) or 0
        mua_thue = _to_num(imp["mua_thue"]) or 0
        ban_theo_ts = {
            "0": {"ds": _to_num(imp["ban_ds_0"]) or 0, "thue": 0},
            "5": {"ds": _to_num(imp["ban_ds_5"]) or 0, "thue": _to_num(imp["ban_thue_5"]) or 0},
            "8": {"ds": _to_num(imp["ban_ds_8"]) or 0, "thue": _to_num(imp["ban_thue_8"]) or 0},
            "10": {"ds": _to_num(imp["ban_ds_10"]) or 0, "thue": _to_num(imp["ban_thue_10"]) or 0},
            "KCT": {"ds": 0, "thue": 0},
        }

    mm, yyyy = ky.split("/")
    import calendar
    last_day = calendar.monthrange(int(yyyy), int(mm))[1]

    # ===== NHẬN BIẾT KỲ QUÝ: nếu khoảng ngày tra cứu trải đúng 1 quý =====
    la_quy = False
    quy_so = 0
    tu_ngay_kkhai = f"01/{mm}/{yyyy}"
    den_ngay_kkhai = f"{last_day}/{mm}/{yyyy}"
    if tu and den:
        try:
            d1 = datetime.datetime.strptime(tu, "%d/%m/%Y").date()
            d2 = datetime.datetime.strptime(den, "%d/%m/%Y").date()
            songay = (d2 - d1).days
            # quý: bắt đầu tháng 1/4/7/10, kéo dài ~3 tháng
            if d1.month in (1, 4, 7, 10) and d1.day == 1 and 85 <= songay <= 95:
                la_quy = True
                quy_so = (d1.month - 1) // 3 + 1
                yyyy = str(d1.year)
                tu_ngay_kkhai = d1.strftime("%d/%m/%Y")
                den_ngay_kkhai = d2.strftime("%d/%m/%Y")
        except Exception:
            pass

    # ===== SỐ DƯ ĐẦU KỲ [22]: lấy từ tạm tính VAT đã lưu (vat_balance) =====
    ct22_val = 0
    try:
        conn2 = db()
        ky_tim = (f"Q{quy_so}/{yyyy}" if la_quy else ky)
        vb = conn2.execute(
            "SELECT du_dau_ky FROM vat_balance WHERE company_id=? AND ky=?",
            (cid, ky_tim)).fetchone()
        if not vb:
            vb = conn2.execute(
                "SELECT du_dau_ky FROM vat_balance WHERE company_id=? AND ky=?",
                (cid, ky)).fetchone()
        conn2.close()
        if vb and vb["du_dau_ky"]:
            ct22_val = round(_to_num(vb["du_dau_ky"]) or 0)
    except Exception:
        pass

    # ----- Tính các chỉ tiêu tờ khai -----
    # ===== TỜ KHAI NHẬP KHẨU: tổng trị giá tính thuế GTGT + thuế GTGT hàng NK =====
    tk_ds_nk = tk_thue_nk = 0
    try:
        conn_tk = db()
        tk_rows = conn_tk.execute(
            "SELECT items_json FROM tokhai_nhap WHERE company_id=?", (cid,)).fetchall()
        conn_tk.close()
        for tkr in tk_rows:
            try:
                its = json.loads(tkr["items_json"]) if tkr["items_json"] else []
            except Exception:
                its = []
            for it in its:
                tk_ds_nk += round(it.get("tri_gia_gtgt", 0) or 0)
                tk_thue_nk += round(it.get("tien_thue_gtgt", 0) or 0)
    except Exception:
        pass

    # Hàng 8% bản chất là 10% được giảm -> gộp vào nhóm 10% (ct32/ct33)
    ds_8 = ban_theo_ts["8"]["ds"]
    thue_8 = ban_theo_ts["8"]["thue"]
    # nhóm 10% trên tờ khai = hàng 10% thật + hàng 8% (tính theo thuế GỐC 10%)
    ds_10 = ban_theo_ts["10"]["ds"] + ds_8
    thue_10 = ban_theo_ts["10"]["thue"] + thue_8
    ds_5 = ban_theo_ts["5"]["ds"]; thue_5 = ban_theo_ts["5"]["thue"]
    ds_0 = ban_theo_ts["0"]["ds"]

    ct23 = round(mua_ds); ct24 = round(mua_thue); ct25 = ct24
    ct30 = round(ds_5); ct31 = round(thue_5)
    ct32 = round(ds_10); ct33 = round(thue_10)
    ct27 = ct30 + ct32; ct28 = ct31 + ct33
    ct29 = round(ds_0)
    ct34 = ct27 + ct29; ct35 = ct28
    # NQ142: thuế được giảm = doanh số 8% × 2%
    thue_duoc_giam = round(ds_8 * 0.02)

    # ===== DÙNG TEMPLATE XML THẬT, chỉ thay giá trị các thẻ (giữ nguyên cấu trúc) =====
    import re as _re
    tpl_path = os.path.join(BASE_DIR, "templates", "htkk_01gtgt_template.xml")
    with open(tpl_path, encoding="utf-8-sig") as f:
        xml = f.read()

    def set_tag(xml, tag, value):
        """Thay nội dung <tag>...</tag> bằng value (chỉ thẻ đầu tiên khớp)."""
        pat = _re.compile(r"(<" + tag + r">)(.*?)(</" + tag + r">)", _re.DOTALL)
        return pat.sub(lambda m: m.group(1) + str(value) + m.group(3), xml, count=1)

    def esc(s):
        return _html.escape(str(s or ""))

    # Thông tin chung - kỳ kê khai (quý hoặc tháng)
    if la_quy:
        xml = set_tag(xml, "kieuKy", "Q")   # Q = kê khai theo QUÝ -> HTKK tự hiển thị "Quý"
        xml = set_tag(xml, "kyKKhai", f"{quy_so}/{yyyy}")  # chỉ số quý, KHÔNG kèm 'Q' (tránh 'Quý Q2')
    else:
        xml = set_tag(xml, "kieuKy", "M")   # M = theo tháng
        xml = set_tag(xml, "kyKKhai", esc(ky))
    xml = set_tag(xml, "kyKKhaiTuNgay", tu_ngay_kkhai)
    xml = set_tag(xml, "kyKKhaiDenNgay", den_ngay_kkhai)
    xml = set_tag(xml, "ngayLapTKhai", datetime.date.today().isoformat())
    xml = set_tag(xml, "mst", esc(comp["mst"]))
    xml = set_tag(xml, "tenNNT", esc(comp["ten"]))
    if nguoi_ky:
        xml = set_tag(xml, "nguoiKy", esc(nguoi_ky))
        xml = set_tag(xml, "ngayKy", datetime.date.today().isoformat())

    # Các chỉ tiêu (giữ nguyên những thẻ khác như ct22, ct36... = giá trị template
    # hoặc tính lại). Ở đây ta điền số liệu kỳ này:
    # ct23/24 = mua vào (gồm cả hàng nhập khẩu); ct23a/24a = TRONG ĐÓ hàng nhập khẩu
    ct23a = tk_ds_nk          # giá trị HHDV nhập khẩu (chưa thuế GTGT)
    ct24a = tk_thue_nk        # thuế GTGT hàng nhập khẩu
    ct23 = round(mua_ds) + tk_ds_nk      # tổng mua vào gồm cả nhập khẩu
    ct24 = round(mua_thue) + tk_thue_nk
    ct25 = ct24
    ct30 = round(ds_5); ct31 = round(thue_5)
    ds_10_tk = ban_theo_ts["10"]["ds"] + ds_8
    thue_10_tk = ban_theo_ts["10"]["thue"] + thue_8
    ct32 = round(ds_10_tk); ct33 = round(thue_10_tk)
    ct27 = ct30 + ct32; ct28 = ct31 + ct33
    ct29 = round(ds_0)
    ct34 = ct27 + ct29; ct35 = ct28
    ct36 = ct35 - ct25          # thuế GTGT phát sinh trong kỳ
    # ct22 = thuế còn được khấu trừ kỳ trước chuyển sang (số dư đầu kỳ)
    ct22 = ct22_val
    # Theo mẫu 01/GTGT (TT80):
    # [40a] = ([36]-[22]+[37]-[38]-[39a]) nếu ≥0 -> thuế phải nộp của hoạt động SXKD trong kỳ
    # [40]  = [40a] - [40b]  (ở đây 40b=0 -> [40]=[40a])
    # [41]  = phần âm (thuế chưa khấu trừ hết, chuyển kỳ sau) -> [43]=[41]-[42]
    ct37 = 0; ct38 = 0; ct39a = 0; ct40b = 0; ct42 = 0
    con_lai = ct36 - ct22 + ct37 - ct38 - ct39a
    ct40a = max(con_lai, 0)      # thuế phải nộp của SXKD trong kỳ
    ct40 = max(ct40a - ct40b, 0) # thuế còn phải nộp trong kỳ
    ct41 = max(-con_lai, 0)      # thuế chưa khấu trừ hết kỳ này
    ct43 = max(ct41 - ct42, 0)   # còn được khấu trừ chuyển kỳ sau

    for tag, val in [
        ("ct21", 0), ("ct22", ct22),
        ("ct23", ct23), ("ct24", ct24),
        ("ct23a", ct23a), ("ct24a", ct24a),
        ("ct25", ct25), ("ct26", 0),
        ("ct27", ct27), ("ct28", ct28), ("ct29", ct29),
        ("ct30", ct30), ("ct31", ct31),
        ("ct32", ct32), ("ct33", ct33), ("ct32a", 0),
        ("ct34", ct34), ("ct35", ct35),
        ("ct36", ct36), ("ct37", ct37), ("ct38", ct38),
        ("ct39a", ct39a), ("ct40a", ct40a), ("ct40b", ct40b), ("ct40", ct40),
        ("ct41", ct41), ("ct42", ct42), ("ct43", ct43),
    ]:
        xml = set_tag(xml, tag, val)

    # Phụ lục NQ142: điền số liệu hàng 8%
    xml = set_tag(xml, "giaTriHHDV", round(ds_8))
    xml = set_tag(xml, "thueGTGTDuocGiam", thue_duoc_giam)
    xml = set_tag(xml, "tongCongGiaTriHHDV", round(ds_8))
    xml = set_tag(xml, "tongCongThueGTGTDuocGiam", thue_duoc_giam)
    xml = set_tag(xml, "ct9", thue_duoc_giam)
    # tên hàng hóa bán ra trong phụ lục (thẻ tenHHDV - chỉ thẻ trong HH_DV_BanRaTrongKy)
    xml = _re.sub(r"(<tenHHDV>)(.*?)(</tenHHDV>)",
                  r"\g<1>Hàng hóa, dịch vụ thuế suất 8%\g<3>", xml, count=1)

    # phần kỳ trong tên file: quý -> Q{n}{yyyy}, tháng -> M{mm}{yyyy}
    if la_quy:
        ky_fname = f"Q{quy_so}{yyyy}"
    else:
        ky_fname = f"M{mm}{yyyy}"
    # MST trong tên file HTKK dùng dạng 13 số (MST 10 số + '000' cho trụ sở chính)
    mst_file = str(comp["mst"] or "").strip()
    if len(mst_file) == 10:
        mst_file = mst_file + "000"
    fname = f"{mst_file}-01_GTGT_TT80-{ky_fname}-L00.xml"
    path = os.path.join(DOWNLOAD_DIR, fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\ufeff" + xml)
    # Mặc định lưu ra DESKTOP cho dễ tìm; lưu thêm vào thư mục công ty (nếu có)
    open_path = path
    desktop = _get_desktop_dir()
    if desktop and os.path.isdir(desktop):
        try:
            dest = os.path.join(desktop, fname)
            with open(dest, "w", encoding="utf-8") as f:
                f.write("\ufeff" + xml)
            open_path = dest
        except Exception:
            pass
    save_dir2 = (comp["save_dir"] or "").strip() if comp else ""
    if save_dir2 and os.path.isdir(save_dir2):
        try:
            dest2 = os.path.join(save_dir2, fname)
            with open(dest2, "w", encoding="utf-8") as f:
                f.write("\ufeff" + xml)
        except Exception:
            pass
    _open_file_local(open_path)
    return {"ok": True, "fname": fname, "path": open_path}


def _parse_thue_suat(ts_raw):
    """Trả về tỷ lệ thuế (0.08 cho 8%) từ chuỗi thuế suất.
    Hỗ trợ: '8%', '8', 'KHAC:5.26%', 'KHAC:5.26', '5.26%'.
    Trả None nếu không xác định được (KCT, KHÔNG, rỗng, hoặc không có số)."""
    s = str(ts_raw or "").strip().upper()
    if not s or s in ("KCT", "KHÔNG", "KO", "0%", "0"):
        return 0.0 if s in ("0%", "0") else None
    # lấy phần sau dấu ':' nếu có (KHAC:5.26%)
    if ":" in s:
        s = s.split(":", 1)[1]
    s = s.replace("%", "").replace(",", ".").strip()
    try:
        v = float(s)
        return v / 100
    except Exception:
        return None


def _thue_theo_cong_thue(it, items, r):
    """Khi không parse được thuế suất của 1 dòng hàng, lấy tiền thuế theo số
    tổng của cổng thuế (tgtthue) chia theo tỷ lệ thành tiền của dòng đó."""
    tong_thue_hd = _to_num(r["tgtthue"]) or 0
    if not tong_thue_hd:
        return 0
    tong_tt = sum((_to_num(x.get("thtien")) or 0) for x in items) or 1
    ds = _to_num(it.get("thtien")) or 0
    return round(tong_thue_hd * (ds / tong_tt))


@app.get("/api/export-excel/{cid}")
def export_excel(cid: int):
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter

    conn = db()
    comp = conn.execute("SELECT * FROM companies WHERE id=?", (cid,)).fetchone()
    rows = conn.execute(
        "SELECT * FROM invoices WHERE company_id=? ORDER BY loai, tdlap DESC",
        (cid,)).fetchall()

    # ===== NẠP TRƯỚC CHI TIẾT SONG SONG (tăng tốc xuất Excel) =====
    # Chỉ nạp hóa đơn CHƯA có detail_json VÀ chưa có file đã tải.
    client0 = CLIENTS.get(cid)
    save_dir0 = (comp["save_dir"] or "").strip() if comp else ""
    if client0 and client0.token:
        # index file đã tải (để bỏ qua hóa đơn đã có file)
        have_file = set()
        if save_dir0 and os.path.isdir(save_dir0):
            for rootdir, _d, files in os.walk(save_dir0):
                for fn in files:
                    low = fn.lower()
                    if low.endswith(".zip") or low.endswith(".xml"):
                        parts = fn.rsplit(".", 1)[0].split("_")
                        if len(parts) >= 2:
                            have_file.add((parts[0], parts[1].lstrip("0") or "0"))

        can_nap = []
        for r in rows:
            if r["detail_json"]:
                continue
            khh = str(r["khhdon"] or ""); sho = str(r["shdon"] or "").lstrip("0") or "0"
            if (khh, sho) in have_file:
                continue
            can_nap.append(dict(r))

        if can_nap:
            import concurrent.futures as _cf
            lock = __import__("threading").Lock()
            results_map = {}

            def _tai_1(rr):
                ht0 = rr["he_thong"] or "query"
                for ht in [ht0, ("sco-query" if ht0 == "query" else "query")]:
                    try:
                        d = client0.get_detail(rr["nbmst"], rr["khhdon"],
                                               rr["khmshdon"], rr["shdon"], ht)
                        if d and (d.get("hdhhdvu") or d.get("nbmst")):
                            return rr["id"], json.dumps(d, ensure_ascii=False)
                    except Exception:
                        pass
                return rr["id"], None

            # số luồng song song theo tốc độ (nhanh=8, cân bằng=5, an toàn=3)
            workers = {"fast": 8, "balanced": 5, "safe": 3}.get(CURRENT_SPEED, 5)
            with _cf.ThreadPoolExecutor(max_workers=workers) as ex:
                for inv_id, dj in ex.map(_tai_1, can_nap):
                    if dj:
                        results_map[inv_id] = dj
            # lưu hết vào DB 1 lần
            for inv_id, dj in results_map.items():
                conn.execute("UPDATE invoices SET detail_json=? WHERE id=?", (dj, inv_id))
            conn.commit()
            # đọc lại rows để có detail_json mới
            rows = conn.execute(
                "SELECT * FROM invoices WHERE company_id=? ORDER BY loai, tdlap DESC",
                (cid,)).fetchall()
    conn.close()

    wb = openpyxl.Workbook()
    hdr_font = Font(bold=True, color="FFFFFF", name="Arial")
    hdr_fill = PatternFill("solid", fgColor="2E5C8A")

    def style_header(ws, ncol):
        for c in range(1, ncol + 1):
            cell = ws.cell(1, c)
            cell.font = hdr_font
            cell.fill = hdr_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")

    def autofit(ws):
        for col in ws.columns:
            w = max((len(str(c.value)) for c in col if c.value is not None), default=10)
            ws.column_dimensions[col[0].column_letter].width = min(w + 2, 50)

    # Định dạng SỐ cho các cột tiền (có dấu phân cách hàng nghìn)
    NUM_FMT = "#,##0"
    TIEN_COLS = {"thành tiền", "tiền thuế gtgt", "thuế gtgt", "tổng thanh toán",
                 "doanh số mua chưa thuế", "doanh số bán chưa thuế", "đơn giá",
                 "số lượng", "thành tiền chưa vat", "tổng tiền", "tổng cộng",
                 "chưa vat (chi tiết)", "chưa vat (bảng kê)", "lệch chưa vat",
                 "vat (chi tiết)", "vat (bảng kê)", "lệch vat", "thuế", "thành tiền chưa thuế",
                 "trị giá tính thuế nk", "tiền thuế nk"}

    def format_so(ws, header_row=None):
        """Áp định dạng số cho các cột tiền. Tự tìm (các) dòng header nếu cần."""
        # tìm tất cả dòng có chứa tên cột tiền (BK Bán ra có nhiều cụm header)
        header_rows = []
        if header_row:
            header_rows = [header_row]
        else:
            for r in range(1, min(ws.max_row, 200) + 1):
                for c in range(1, ws.max_column + 1):
                    if str(ws.cell(r, c).value or "").strip().lower() in TIEN_COLS:
                        header_rows.append(r); break
        if not header_rows:
            return
        num_cols = set()
        for hr in header_rows:
            for c in range(1, ws.max_column + 1):
                if str(ws.cell(hr, c).value or "").strip().lower() in TIEN_COLS:
                    num_cols.add(c)
        for r in range(1, ws.max_row + 1):
            if r in header_rows:
                continue
            for c in num_cols:
                cell = ws.cell(r, c)
                v = cell.value
                if isinstance(v, (int, float)):
                    cell.number_format = NUM_FMT
                elif isinstance(v, str) and v.strip() and v.replace(".", "").replace("-", "").isdigit():
                    try:
                        cell.value = float(v) if "." in v else int(v)
                        cell.number_format = NUM_FMT
                    except Exception:
                        pass

    # ===== Chuẩn bị: hàm tìm/đọc chi tiết hóa đơn =====
    save_dir = (comp["save_dir"] or "").strip() if comp else ""
    client = CLIENTS.get(cid)  # client đang đăng nhập (nếu có) để tải lại khi thiếu file

    # XÂY INDEX FILE 1 LẦN (nhanh hơn nhiều so với quét lại mỗi hóa đơn).
    # Khóa = (KHHDON, số HĐ bỏ 0 đầu) -> đường dẫn file
    _file_index = {}
    if save_dir and os.path.isdir(save_dir):
        for rootdir, _d, files in os.walk(save_dir):
            for fn in files:
                low = fn.lower()
                if not (low.endswith(".zip") or low.endswith(".xml")):
                    continue
                name = fn.rsplit(".", 1)[0]
                parts = name.split("_")
                if len(parts) >= 2:
                    f_khh = parts[0]
                    f_sho = parts[1].lstrip("0") or "0"
                    _file_index.setdefault((f_khh, f_sho), os.path.join(rootdir, fn))

    def find_invoice_file(r):
        khh = str(r["khhdon"] or "").strip()
        sho = str(r["shdon"] or "").strip().lstrip("0") or "0"
        return _file_index.get((khh, sho))

    _items_cache = {}
    def get_invoice_items(r):
        """Lấy danh sách mặt hàng của 1 hóa đơn:
        1) từ chi tiết đã lưu trong DB -> 2) từ file XML đã tải ->
        3) gọi endpoint detail (thử cả query và sco-query).
        Lấy được thì LƯU VÀO DB để lần sau khỏi gọi lại.
        Trả về (items, summary)."""
        key = (r["khhdon"], r["shdon"], r["nbmst"], r["loai"])
        if key in _items_cache:
            return _items_cache[key]
        items = []
        summary = None

        # (0) chi tiết đã lưu trong DB (cột detail_json)
        try:
            dj = r["detail_json"] if "detail_json" in r.keys() else None
        except Exception:
            dj = None
        if dj:
            try:
                detail = json.loads(dj)
                items = _parse_detail_json(detail)
                summary = _summary_from_detail_json(detail)
            except Exception:
                items = []; summary = None

        # (1) file đã tải
        if not items:
            fpath = find_invoice_file(r)
            if fpath:
                try:
                    with open(fpath, "rb") as f:
                        data = f.read()
                    items = _parse_xml_invoice(data)
                    summary = _parse_invoice_summary(data)
                except Exception:
                    items = []; summary = None

        # (2) gọi detail JSON — thử cả hệ thống đã lưu và hệ thống còn lại
        if not items and client and client.token:
            ht0 = r["he_thong"] or "query"
            for ht in [ht0, ("sco-query" if ht0 == "query" else "query")]:
                try:
                    detail = client.get_detail(
                        r["nbmst"], r["khhdon"], r["khmshdon"], r["shdon"], ht)
                    if detail and (detail.get("hdhhdvu") or detail.get("nbmst")):
                        items = _parse_detail_json(detail)
                        summary = _summary_from_detail_json(detail)
                        # LƯU vào DB để lần sau khỏi gọi lại
                        try:
                            cn = db()
                            cn.execute("UPDATE invoices SET detail_json=? WHERE id=?",
                                       (json.dumps(detail, ensure_ascii=False), r["id"]))
                            cn.commit(); cn.close()
                        except Exception:
                            pass
                        break
                    time.sleep(SP()["file"])
                except Exception:
                    pass
        _items_cache[key] = (items, summary)
        return items, summary

    detail_headers = ["Ký hiệu", "Số HĐ", "Ngày", "Người bán", "MST bán",
                      "Người mua", "MST mua", "STT", "Mã vt",
                      "Tên hàng hóa/dịch vụ",
                      "ĐVT", "Số lượng", "Đơn giá", "Thành tiền",
                      "Thuế suất", "Tiền thuế GTGT",
                      "Trạng thái", "Kết quả"]

    # Lưu tổng theo từng hóa đơn (để đối chiếu việc 4)
    ct_totals = {"purchase": {}, "sold": {}}

    def phan_bo_chiet_khau(items):
        """Xử lý hóa đơn MUA VÀO:
        - TChat=4 (ghi chú) KHÔNG có thành tiền: BỎ QUA.
        - TChat=4 (ghi chú) CÓ thành tiền âm (vd NQ204 ghi giảm): xử lý như CK.
        - TChat=3 (chiết khấu) hoặc tên chứa 'chiết khấu'/'NQ204': ghi ÂM tt + thuế.
        - Dòng hàng: giữ nguyên đúng số trên hóa đơn."""

        def la_dong_giam(it):
            """Nhận dạng dòng giảm giá / chiết khấu / NQ204 có giá trị âm."""
            tchat = str(it.get("tchat", "") or "")
            ten = str(it.get("ten_hang", "") or "").lower()
            tt = _to_num(it.get("thtien")) or 0
            # tchat=3 → CK rõ ràng
            if tchat == "3":
                return True
            # tchat=4 có thành tiền âm → dòng giảm (NQ204, giảm giá dạng ghi chú)
            if tchat == "4" and isinstance(tt, (int, float)) and tt < 0:
                return True
            # tên chứa từ khóa giảm + thành tiền âm
            keywords = ["chiết khấu", "chiet khau", "giảm giá", "nq204", "nq 204",
                        "204/2025", "nghị quyết 204", "nghi quyet 204"]
            if any(kw in ten for kw in keywords) and isinstance(tt, (int, float)) and tt < 0:
                return True
            return False

        import re as _re_hkd

        # --- Pass 1: Phát hiện dòng ghi chú HKD NQ204 (tchat=4, thtien=0) ---
        # Dạng: "Đã giảm X đồng theo 20% tỷ lệ % để tính thuế GTGT NQ204/2025"
        so_giam_hkd = 0
        for it in items:
            tchat = str(it.get("tchat", "") or "")
            tt = _to_num(it.get("thtien")) or 0
            if tchat == "4" and (not tt or tt == 0):
                ten_gc = str(it.get("ten_hang", "") or "")
                ten_l = ten_gc.lower()
                la_giam_hkd = (
                    ("giảm" in ten_l or "giam" in ten_l)
                    and "20" in ten_l
                    and ("tỷ lệ" in ten_l or "ty le" in ten_l
                         or "204" in ten_l or "gtgt" in ten_l)
                )
                if la_giam_hkd:
                    m_s = _re_hkd.search(r'(\d[\d.,]*)\s*đồng', ten_gc, _re_hkd.IGNORECASE)
                    if not m_s:
                        m_s = _re_hkd.search(r'(\d[\d.,]+)', ten_gc)
                    if m_s:
                        try:
                            so_giam_hkd = round(float(
                                m_s.group(1).replace('.', '').replace(',', '')))
                        except Exception:
                            pass
                    break  # chỉ có 1 dòng ghi chú NQ204

        # --- Pass 2: Xây dựng output ---
        # Lấy danh sách dòng hàng thực (bỏ tchat=4 không có thtien — kể cả ghi chú NQ204)
        hang_thuong = []
        for it in items:
            tchat = str(it.get("tchat", "") or "")
            tt = _to_num(it.get("thtien")) or 0
            if tchat == "4" and (not tt or tt == 0):
                continue
            hang_thuong.append(it)

        if so_giam_hkd > 0:
            # Phân bổ so_giam_hkd vào THÀNH TIỀN từng dòng hàng (không đụng vào tiền thuế)
            hang_chinh = [it for it in hang_thuong if not la_dong_giam(it)]
            tong_tt = sum(abs(_to_num(it.get("thtien")) or 0) for it in hang_chinh)
            out = []
            allocated = 0
            for idx, it in enumerate(hang_chinh):
                h = dict(it)
                tt_item = abs(_to_num(h.get("thtien")) or 0)
                if idx == len(hang_chinh) - 1:
                    giam_item = so_giam_hkd - allocated
                else:
                    giam_item = round(tt_item / tong_tt * so_giam_hkd) if tong_tt else 0
                    allocated += giam_item
                h["thtien"] = tt_item - giam_item
                out.append(h)
            # Các dòng chiết khấu/giảm giá khác (nếu có)
            for it in hang_thuong:
                if la_dong_giam(it):
                    h = dict(it)
                    tt2 = _to_num(h.get("thtien")) or 0
                    h["thtien"] = -abs(tt2)
                    dg = _to_num(h.get("dgia")) or 0
                    if isinstance(dg, (int, float)):
                        h["dgia"] = -abs(dg)
                    thue_goc = _to_num(h.get("tien_thue"))
                    ts_raw = str(h.get("tsuat", "") or "").strip()
                    rate = _parse_thue_suat(ts_raw)
                    if thue_goc is not None and str(thue_goc).strip() != "" and _to_num(thue_goc) != 0:
                        h["tien_thue"] = -abs(_to_num(thue_goc))
                    elif rate is not None and rate > 0:
                        h["tien_thue"] = -round(abs(tt2) * rate)
                    else:
                        h["tien_thue"] = 0
                    h["_la_ck"] = True
                    out.append(h)
            return out

        # Không có NQ204 HKD → xử lý bình thường
        out = []
        for it in hang_thuong:
            h = dict(it)
            if la_dong_giam(it):
                tt2 = _to_num(h.get("thtien")) or 0
                h["thtien"] = -abs(tt2)
                dg = _to_num(h.get("dgia")) or 0
                if isinstance(dg, (int, float)):
                    h["dgia"] = -abs(dg)
                thue_goc = _to_num(h.get("tien_thue"))
                ts_raw = str(h.get("tsuat", "") or "").strip()
                rate = _parse_thue_suat(ts_raw)
                if thue_goc is not None and str(thue_goc).strip() != "" and _to_num(thue_goc) != 0:
                    h["tien_thue"] = -abs(_to_num(thue_goc))
                elif rate is not None and rate > 0:
                    h["tien_thue"] = -round(abs(tt2) * rate)
                else:
                    h["tien_thue"] = 0
                ten = str(h.get("ten_hang", "") or "")
                if "204" in ten or "nq" in ten.lower():
                    h["_la_nq204"] = True
                else:
                    h["_la_ck"] = True
            out.append(h)
        return out

    def _fmt_ngay(s):
        """yyyy-mm-dd hoặc yyyy-mm-ddThh -> dd/mm/yyyy."""
        s = (s or "").split("T")[0]
        if "-" in s:
            p = s.split("-")
            if len(p) == 3:
                return f"{p[2]}/{p[1]}/{p[0]}"
        if "/" in s:  # đã đúng định dạng
            return s
        return s

    def _sort_key_ngay(r):
        nd = (r["tdlap"] or "").split("T")[0]
        return nd  # yyyy-mm-dd so sánh chuỗi = đúng thứ tự thời gian

    def build_detail_sheet(sheet_name, loai):
        ws = wb.create_sheet(sheet_name)
        # Việc 9: Chi tiết MUA VÀO bỏ Người mua/MST mua; BÁN RA bỏ Người bán/MST bán
        if loai == "purchase":
            headers = ["Ký hiệu", "Số HĐ", "Ngày", "Người bán", "MST bán",
                       "STT", "Mã vt", "Tên hàng hóa/dịch vụ", "ĐVT",
                       "Số lượng", "Đơn giá", "Thành tiền",
                       "Thuế suất", "Tiền thuế GTGT", "Trạng thái", "Kết quả",
                       "Trị giá tính thuế NK", "Thuế suất NK", "Tiền thuế NK"]
        else:
            headers = ["Ký hiệu", "Số HĐ", "Ngày", "Người mua", "MST mua",
                       "STT", "Mã vt", "Tên hàng hóa/dịch vụ", "ĐVT",
                       "Số lượng", "Đơn giá", "Thành tiền",
                       "Thuế suất", "Tiền thuế GTGT", "Trạng thái", "Kết quả"]
        ws.append(headers)
        style_header(ws, len(headers))

        # lọc + SORT theo ngày TĂNG DẦN (thấp -> cao)
        loai_rows = [r for r in rows if r["loai"] == loai]

        # AN TOÀN: với hóa đơn MUA VÀO, loại bỏ hóa đơn mà MST người mua (nmmst)
        # KHÁC MST công ty đang xem (đó là hóa đơn lẫn của công ty khác, vd hóa đơn
        # xuất khẩu của bên bán bị cổng thuế trả nhầm). Giữ lại nếu nmmst trống/khớp.
        if loai == "purchase":
            mst_cty = str(comp["mst"] or "").strip()
            def _hop_le_mua(r):
                nm = str(r["nmmst"] or "").strip()
                # nmmst trống -> giữ (một số HĐ không ghi MST mua)
                if not nm:
                    return True
                return nm == mst_cty
            loai_rows = [r for r in loai_rows if _hop_le_mua(r)]
        else:
            # hóa đơn BÁN RA: người bán phải là công ty mình -> loại HĐ nbmst khác
            mst_cty = str(comp["mst"] or "").strip()
            def _hop_le_ban(r):
                nb = str(r["nbmst"] or "").strip()
                if not nb:
                    return True
                return nb == mst_cty
            loai_rows = [r for r in loai_rows if _hop_le_ban(r)]

        loai_rows.sort(key=_sort_key_ngay)

        ngay_col = 3  # cột Ngày để format dd/mm/yyyy
        for r in loai_rows:
            try:
                raw = json.loads(r["raw"]) if r["raw"] else {}
            except Exception:
                raw = {}
            tthai_ma = str(raw.get("tthai", r["tthai"]) or "").strip()
            tt = _mo_ta_trang_thai(raw.get("tthai", r["tthai"]))
            kq = _mo_ta_ket_qua(raw.get("ttxly", ""))
            ttxly_raw = str(raw.get("ttxly", "") or "").strip()

            # Loại hóa đơn 'đã bị thay thế' (mã 4), hủy/xóa bỏ (6),
            # và 'không đủ điều kiện cấp mã' (kết quả kiểm tra ttxly=4)
            if (tthai_ma in ("4", "6")
                    or tt in ("Hóa đơn đã bị thay thế", "Hóa đơn hủy",
                              "Hóa đơn đã bị xóa bỏ", "Hóa đơn xóa bỏ")):
                continue
            if ttxly_raw == "4" or "không đủ điều kiện" in kq.lower():
                continue

            items, _summary = get_invoice_items(r)
            ikey = (str(r["khhdon"]), str(r["shdon"]).lstrip("0") or "0")
            ngay_fmt = _fmt_ngay(r["tdlap"])

            if not items:
                ly_do = "(không lấy được chi tiết — đăng nhập rồi xuất lại)"
                nmten_raw = raw.get("nmten", "") or raw.get("nmtnmua", "") or ""
                if loai == "purchase":
                    ws.append([r["khhdon"], r["shdon"], ngay_fmt,
                               r["nbten"], r["nbmst"], "", "", ly_do, "",
                               "", "", "", "", r["tgtttbso"],
                               tt, kq])
                else:
                    ws.append([r["khhdon"], r["shdon"], ngay_fmt,
                               nmten_raw, r["nmmst"], "", "", ly_do, "",
                               "", "", "", "", r["tgtttbso"],
                               tt, kq])
                cur = ct_totals[loai].setdefault(ikey, {"ds": 0, "thue": 0})
                cur["ds"] += _to_num(r["tgtcthue"]) or 0
                cur["thue"] += _to_num(r["tgtthue"]) or 0
                continue

            if loai == "purchase":
                items = phan_bo_chiet_khau(items)

            for it in items:
                ds = _to_num(it.get("thtien")) or 0
                ts_raw = str(it.get("tsuat", "") or "").strip()
                thue_goc_raw = it.get("tien_thue")
                ts_upper = ts_raw.upper()
                # 1. KCT → luôn 0
                if ts_upper in ("KCT", "KO", "KHÔNG"):
                    tien_thue = 0
                # 2. Có tiền thuế GỐC trên hóa đơn → dùng (kể cả = 0)
                elif thue_goc_raw is not None and str(thue_goc_raw).strip() != "":
                    tien_thue = round(_to_num(thue_goc_raw))
                # 3. Biết thuế suất → tính
                else:
                    rate = _parse_thue_suat(ts_raw)
                    if rate is not None and rate > 0:
                        tien_thue = round(ds * rate) if isinstance(ds, (int, float)) else 0
                    else:
                        tien_thue = 0
                ten = it.get("ten_hang", "")
                if it.get("_la_nq204"):
                    ten += " (Giảm NQ204 - ghi âm)"
                elif it.get("_la_ck"):
                    ten += " (Chiết khấu TM - ghi âm)"
                # cột người: purchase -> người bán; sold -> người mua
                if loai == "purchase":
                    nguoi = it.get("ten_nban", "") or r["nbten"]
                    mst = it.get("mst_nban", "") or r["nbmst"]
                else:
                    nguoi = it.get("ten_nmua", "") or raw.get("nmten", "") or ""
                    mst = it.get("mst_nmua", "") or r["nmmst"]
                ws.append([
                    r["khhdon"], r["shdon"],
                    ngay_fmt, nguoi, mst,
                    it.get("stt", ""), it.get("ma_vt", ""),
                    ten, it.get("dvt", ""),
                    _to_num(it.get("sluong")), _to_num(it.get("dgia")),
                    ds, it.get("tsuat", ""), tien_thue,
                    tt, kq,
                ])
                cur = ct_totals[loai].setdefault(ikey, {"ds": 0, "thue": 0})
                cur["ds"] += ds if isinstance(ds, (int, float)) else 0
                cur["thue"] += tien_thue if isinstance(tien_thue, (int, float)) else 0

        # ===== TỜ KHAI NHẬP KHẨU (chỉ cho MUA VÀO) =====
        if loai == "purchase":
            conn_tk = db()
            tk_rows = conn_tk.execute(
                "SELECT * FROM tokhai_nhap WHERE company_id=? ORDER BY ngay_dk", (cid,)).fetchall()
            conn_tk.close()
            for tkr in tk_rows:
                try:
                    tk_items = json.loads(tkr["items_json"]) if tkr["items_json"] else []
                except Exception:
                    tk_items = []
                ngay_tk = tkr["ngay_dk"] or ""
                if ngay_tk and "-" in ngay_tk:
                    p = ngay_tk.split("-"); ngay_tk = f"{p[2]}/{p[1]}/{p[0]}"
                for idx, it in enumerate(tk_items, 1):
                    ds_tk = it.get("tri_gia_gtgt", 0) or 0
                    thue_tk = it.get("tien_thue_gtgt", 0) or 0
                    sl_tk = it.get("sluong", 0) or 0
                    # đơn giá = thành tiền / số lượng
                    dgia_tk = round(ds_tk / sl_tk) if sl_tk else 0
                    # A..P: như hóa đơn thường; Q,R,S = thuế NK
                    ws.append([
                        "TKNK", tkr["so_tk"], ngay_tk,
                        tkr["nguoi_xk"], tkr["nguoi_xk"],          # Người bán & MST bán = tên người XK
                        idx, "", it.get("ten", ""), it.get("dvt", ""),
                        sl_tk, dgia_tk,                            # số lượng, đơn giá
                        round(ds_tk), it.get("ts_gtgt", ""), round(thue_tk),
                        "Tờ khai nhập khẩu", "",
                        round(it.get("tri_gia_nk", 0) or 0),       # Q: trị giá tính thuế NK
                        it.get("ts_nk", ""),                       # R: thuế suất NK
                        round(it.get("tien_thue_nk", 0) or 0),     # S: tiền thuế NK
                    ])
                    # cộng vào tổng đối chiếu (theo số tờ khai)
                    ikey = (str("TKNK"), str(tkr["so_tk"]))
                    cur = ct_totals["purchase"].setdefault(ikey, {"ds": 0, "thue": 0})
                    cur["ds"] += round(ds_tk)
                    cur["thue"] += round(thue_tk)

        autofit(ws)
        format_so(ws)
        ws.freeze_panes = "C2"
        # Việc 9: thêm Filter kéo từ đầu đến cuối
        if ws.max_row > 1:
            ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{ws.max_row}"

    build_detail_sheet("Chi tiết MUA VÀO", "purchase")
    build_detail_sheet("Chi tiết BÁN RA", "sold")

    # ===== SHEET BẢNG KÊ CHUẨN (theo mẫu Thông tư) =====
    from openpyxl.styles import Border, Side, Alignment as _Al
    thin = Side(style="thin")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    def la_hd_loai_bo(raw, r):
        """Loại bỏ hóa đơn:
        - 'Hóa đơn đã bị thay thế' (mã 4) và 'Hóa đơn hủy' (mã 6)
        - Kết quả kiểm tra = 'Hóa đơn không đủ điều kiện cấp mã'
        GIỮ 'Hóa đơn thay thế' (mã 2), 'điều chỉnh' (mã 3), 'mới' (mã 1)..."""
        tt = str(raw.get("tthai", r["tthai"]) or "").strip()
        mota = _mo_ta_trang_thai(raw.get("tthai", r["tthai"]))
        if tt in ("4", "6"):
            return True
        if mota in ("Hóa đơn đã bị thay thế", "Hóa đơn hủy",
                     "Hóa đơn đã bị xóa bỏ", "Hóa đơn xóa bỏ"):
            return True
        # loại HĐ không đủ điều kiện cấp mã (kết quả kiểm tra)
        kq = str(raw.get("ttxly", "") or "").strip().lower()
        kq_mota = _mo_ta_ket_qua(raw.get("ttxly", "")).lower()
        if kq == "4" or "không đủ điều kiện" in kq or "không đủ điều kiện" in kq_mota:
            return True
        return False

    # Lưu tổng BK theo hóa đơn để đối chiếu (việc 4)
    bk_totals = {"purchase": {}, "sold": {}}

    mst_cty_bk = str(comp["mst"] or "").strip()
    def _hd_dung_cty(r, loai):
        """Loại hóa đơn lẫn của công ty khác: mua vào -> nmmst phải = MST công ty;
        bán ra -> nbmst phải = MST công ty (cho phép trống)."""
        if loai == "purchase":
            nm = str(r["nmmst"] or "").strip()
            return (not nm) or nm == mst_cty_bk
        else:
            nb = str(r["nbmst"] or "").strip()
            return (not nb) or nb == mst_cty_bk

    # ----- BẢNG KÊ MUA VÀO (mỗi hóa đơn 1 dòng + cột Mặt hàng) -----
    ws = wb.create_sheet("BK Mua vào")
    hdr1 = ["STT", "Ký hiệu", "Số Hoá Đơn", "Ngày lập",
            "Tên người bán", "MST người bán", "Mặt hàng", "Thuế suất GTGT",
            "Doanh số mua chưa thuế", "Thuế GTGT", "Tổng thanh toán",
            "Trạng thái"]
    ws.append(hdr1)
    style_header(ws, len(hdr1))
    stt = 0
    tong_ds_mua = tong_thue_mua = 0
    for r in rows:
        if r["loai"] != "purchase":
            continue
        if not _hd_dung_cty(r, "purchase"):   # loại HĐ lẫn của công ty khác
            continue
        try:
            raw = json.loads(r["raw"]) if r["raw"] else {}
        except Exception:
            raw = {}
        if la_hd_loai_bo(raw, r):   # việc 3: chỉ loại HĐ thay thế / xóa bỏ
            continue
        stt += 1
        ngay = (r["tdlap"] or "").split("T")[0]
        if ngay and "-" in ngay:
            y, m, d = ngay.split("-"); ngay = f"{d}/{m}/{y}"
        ds = _to_num(r["tgtcthue"]) or 0
        thue = _to_num(r["tgtthue"]) or 0
        # HKD: nếu tgtcthue=0 nhưng tgtttbso>0 -> lấy thành tiền (tổng thanh toán)
        if not ds:
            ds = _to_num(r["tgtttbso"]) or 0
        # mặt hàng đầu tiên + thuế suất
        _items, _sm = get_invoice_items(r)
        la_ck_hd = False
        if _items:
            def _is_ck(it):
                tc = str(it.get("tchat", "") or "")
                if tc == "4": return False   # ghi chú -> không phải CK
                if tc == "3": return True
                ten = str(it.get("ten_hang", "") or "").lower()
                return "chiết khấu" in ten or "chiet khau" in ten
            items_ko_gc = [it for it in _items if str(it.get("tchat","") or "")!="4"]
            if items_ko_gc and all(_is_ck(it) for it in items_ko_gc):
                la_ck_hd = True
        if la_ck_hd:
            ds = -abs(ds) if isinstance(ds, (int, float)) else ds
            thue = -abs(thue) if isinstance(thue, (int, float)) else thue
        mat_hang = ""
        thue_suat = ""
        if _items:
            mat_hang = _items[0].get("ten_hang", "")
            # thuế suất từ summary (nếu có nhiều mức thì gộp); lấy mức đầu tiên có
            ts_set = []
            for it in _items:
                tsv = str(it.get("tsuat", "") or "").strip()
                if tsv and tsv not in ts_set:
                    ts_set.append(tsv)
            thue_suat = ", ".join(ts_set) if ts_set else ""
            if la_ck_hd:
                mat_hang += " (Chiết khấu TM - ghi âm)"
            elif len(_items) > 1:
                mat_hang += " ..."
        ws.append([stt, r["khhdon"], r["shdon"], ngay, r["nbten"], r["nbmst"],
                   mat_hang, thue_suat, ds, thue, _to_num(r["tgtttbso"]),
                   _mo_ta_trang_thai(raw.get("tthai", r["tthai"]))])
        tong_ds_mua += ds if isinstance(ds, (int, float)) else 0
        tong_thue_mua += thue if isinstance(thue, (int, float)) else 0
        ikey = (str(r["khhdon"]), str(r["shdon"]).lstrip("0") or "0")
        bk_totals["purchase"][ikey] = {"ds": ds, "thue": thue}

    # ===== TỜ KHAI NHẬP KHẨU: mỗi tờ khai gộp thành 1 dòng trong BK Mua vào =====
    conn_tk2 = db()
    tk_rows2 = conn_tk2.execute(
        "SELECT * FROM tokhai_nhap WHERE company_id=? ORDER BY ngay_dk", (cid,)).fetchall()
    conn_tk2.close()
    for tkr in tk_rows2:
        try:
            tk_items = json.loads(tkr["items_json"]) if tkr["items_json"] else []
        except Exception:
            tk_items = []
        if not tk_items:
            continue
        ds_tk_tong = sum(round(it.get("tri_gia_gtgt", 0) or 0) for it in tk_items)
        thue_tk_tong = sum(round(it.get("tien_thue_gtgt", 0) or 0) for it in tk_items)
        ngay_tk = tkr["ngay_dk"] or ""
        if ngay_tk and "-" in ngay_tk:
            p = ngay_tk.split("-"); ngay_tk = f"{p[2]}/{p[1]}/{p[0]}"
        stt += 1
        # gộp tên hàng: lấy tên dòng đầu + "(N dòng hàng)"
        ten_gop = (tk_items[0].get("ten", "") or "")[:40]
        if len(tk_items) > 1:
            ten_gop += f" ... ({len(tk_items)} dòng hàng)"
        ts_set = []
        for it in tk_items:
            tsv = str(it.get("ts_gtgt", "") or "").strip()
            if tsv and tsv not in ts_set:
                ts_set.append(tsv)
        ws.append([stt, "TKNK", tkr["so_tk"], ngay_tk, tkr["nguoi_xk"], tkr["nguoi_xk"],
                   ten_gop, ", ".join(ts_set), ds_tk_tong, thue_tk_tong,
                   _to_num(ds_tk_tong + thue_tk_tong), "Tờ khai nhập khẩu"])
        tong_ds_mua += ds_tk_tong
        tong_thue_mua += thue_tk_tong
        # key đối chiếu khớp với Chi tiết (TKNK + số tờ khai)
        bk_totals["purchase"][("TKNK", str(tkr["so_tk"]))] = {"ds": ds_tk_tong, "thue": thue_tk_tong}

    # dòng tổng (Doanh số giờ ở cột I=9, Thuế cột J=10)
    ws.append(["", "", "", "", "", "", "", "TỔNG CỘNG",
               _to_num(tong_ds_mua), _to_num(tong_thue_mua), "", ""])
    for c in range(1, 13):
        ws.cell(ws.max_row, c).font = Font(bold=True, color="C00000")
    autofit(ws)
    format_so(ws)
    ws.freeze_panes = "C2"
    if ws.max_row > 1:
        ws.auto_filter.ref = f"A1:{get_column_letter(len(hdr1))}{ws.max_row}"

    # ----- BẢNG KÊ BÁN RA (form BKDAURA chuẩn 01-1/GTGT, tách theo thuế suất) -----
    from openpyxl.styles import Border, Side, Alignment as _Al
    thin = Side(style="thin")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    bold = Font(bold=True, name="Times New Roman")
    center = _Al(horizontal="center", vertical="center", wrap_text=True)

    ws = wb.create_sheet("BK Bán ra")
    sold_rows = [r for r in rows if r["loai"] == "sold" and _hd_dung_cty(r, "sold")]

    # Bỏ phần tiêu đề dài (gây lệch cột) — header bắt đầu ngay dòng 1
    hdr2 = ["STT", "Ký hiệu mẫu", "Ký hiệu HĐ", "Số hóa đơn", "Ngày lập",
            "Tên người mua", "MST người mua", "Mặt hàng",
            "Doanh số bán chưa thuế", "Thuế GTGT", "Trạng thái", "Kết quả"]
    ws.append(hdr2)
    hrow = ws.max_row
    for c in range(1, len(hdr2) + 1):
        cell = ws.cell(hrow, c)
        cell.font = Font(bold=True, color="FFFFFF", name="Times New Roman")
        cell.fill = PatternFill("solid", fgColor="2E5C8A")
        cell.alignment = center
        cell.border = border

    # Gom hóa đơn bán ra theo nhóm thuế suất (loại HĐ bị thay thế - việc 3)
    groups = {"KCT": [], "0": [], "5": [], "8": [], "10": [], "KHAC": []}
    for r in sold_rows:
        try:
            raw = json.loads(r["raw"]) if r["raw"] else {}
        except Exception:
            raw = {}
        if la_hd_loai_bo(raw, r):   # việc 3: chỉ bỏ HĐ thay thế / xóa bỏ
            continue
        tt = _mo_ta_trang_thai(raw.get("tthai", r["tthai"]))
        kq = _mo_ta_ket_qua(raw.get("ttxly", ""))
        items, info = get_invoice_items(r)
        ikey = (str(r["khhdon"]), str(r["shdon"]).lstrip("0") or "0")
        if not info or not info.get("theo_ts"):
            groups["KHAC"].append((r, raw, tt, kq, None, None))
            bk_totals["sold"][ikey] = {"ds": _to_num(r["tgtcthue"]) or 0,
                                       "thue": _to_num(r["tgtthue"]) or 0}
            continue
        bt = bk_totals["sold"].setdefault(ikey, {"ds": 0, "thue": 0})
        for key, val in info["theo_ts"].items():
            g = key if key in groups else "KHAC"
            groups[g].append((r, raw, tt, kq, info, (key, val)))
            bt["ds"] += val["ds"]; bt["thue"] += val["thue"]

    nhom_label = {
        "KCT": "1. Hàng hóa, dịch vụ không chịu thuế GTGT (KCT)",
        "0": "2. Hàng hóa, dịch vụ chịu thuế suất 0%",
        "5": "3. Hàng hóa, dịch vụ chịu thuế suất 5%",
        "8": "4. Hàng hóa, dịch vụ chịu thuế suất 8%",
        "10": "5. Hàng hóa, dịch vụ chịu thuế suất 10%",
        "KHAC": "6. Khác / chưa lấy được file XML",
    }

    stt = 0
    grand_ds = grand_thue = 0
    for key in ["KCT", "0", "5", "8", "10", "KHAC"]:
        glist = groups[key]
        if not glist:
            continue
        ws.append([nhom_label[key]])
        ws.cell(ws.max_row, 1).font = bold
        sub_ds = sub_thue = 0
        for (r, raw, tt, kq, info, tsdata) in glist:
            stt += 1
            ngay = (r["tdlap"] or "").split("T")[0]
            if "-" in ngay:
                y, m, d = ngay.split("-"); ngay = f"{d}/{m}/{y}"
            if info and tsdata:
                _k, val = tsdata
                ds = val["ds"]; thue = val["thue"]
                ws.append([stt, info["khmshdon"], info["khhdon"], info["shdon"],
                           ngay, info["ten_nmua"] or "Khách lẻ", info["mst_nmua"],
                           info["mat_hang"], _to_num(ds), _to_num(thue), tt, kq])
            else:
                ds = _to_num(r["tgtcthue"]) or 0
                thue = _to_num(r["tgtthue"]) or 0
                ws.append([stt, "1", r["khhdon"], r["shdon"], ngay,
                           "", r["nmmst"], "(chưa lấy được file XML)",
                           ds, thue, tt, kq])
            sub_ds += ds if isinstance(ds, (int, float)) else 0
            sub_thue += thue if isinstance(thue, (int, float)) else 0
        ws.append(["", "", "", "", "", "", "", "Tổng nhóm",
                   _to_num(sub_ds), _to_num(sub_thue), "", ""])
        for c in range(1, 13):
            ws.cell(ws.max_row, c).font = bold
        grand_ds += sub_ds; grand_thue += sub_thue

    ws.append([])
    ws.append(["", "", "", "", "", "", "", "TỔNG CỘNG",
               _to_num(grand_ds), _to_num(grand_thue), "", ""])
    for c in range(1, 13):
        ws.cell(ws.max_row, c).font = Font(bold=True, color="C00000", name="Times New Roman")
    autofit(ws)
    format_so(ws)
    # thu nhỏ cột A (STT) và B (Ký hiệu mẫu) - giá trị ngắn
    ws.column_dimensions["A"].width = 6
    ws.column_dimensions["B"].width = 11
    # cố định phần header (dòng 1) để cuộn vẫn thấy cột
    ws.freeze_panes = f"A{hrow + 1}"
    # Việc 9: thêm Filter từ dòng header tới cuối
    if ws.max_row > hrow:
        ws.auto_filter.ref = f"A{hrow}:{get_column_letter(ws.max_column)}{ws.max_row}"

    # ===== SHEET ĐỐI CHIẾU (việc 4): so Chi tiết vs Bảng kê =====
    ws = wb.create_sheet("Đối chiếu")
    bold = Font(bold=True)
    ws.append(["BẢNG ĐỐI CHIẾU TỔNG HỢP (tự cập nhật khi sửa số liệu các sheet)"])
    ws.cell(ws.max_row, 1).font = Font(bold=True, color="2E5C8A", size=13)
    ws.append([])
    # Thông tin công ty
    ws.append(["Thông tin công ty"])
    ws.cell(ws.max_row, 1).font = Font(bold=True, size=11)
    ws.append([comp["ten"] or ""])
    ws.append([comp["mst"] or ""])
    # lấy địa chỉ từ hóa đơn bán ra (nbdchi = địa chỉ người bán = địa chỉ công ty)
    diachi = ""
    try:
        for r_dc in rows:
            if r_dc["loai"] == "sold" and r_dc["raw"]:
                raw_dc = json.loads(r_dc["raw"])
                dc = raw_dc.get("nbdchi", "") or raw_dc.get("dchi", "") or ""
                if dc and len(dc) > 5:
                    diachi = dc; break
    except Exception:
        pass
    if diachi:
        ws.append([diachi])
    ws.append([])

    # Cấu trúc cột:
    #  Chi tiết MUA VÀO/BÁN RA: Thành tiền = N(14), Tiền thuế = P(16)
    #  BK Mua vào: Doanh số = H(8), Thuế = I(9)
    #  BK Bán ra:  Doanh số = I(9), Thuế = J(10)
    CT_MUA, CT_BAN = "'Chi tiết MUA VÀO'", "'Chi tiết BÁN RA'"
    BK_MUA, BK_BAN = "'BK Mua vào'", "'BK Bán ra'"

    def add_row(nhom, chi_tieu, formula, ktra_label=None, ktra_formula=None):
        ws.append([nhom, chi_tieu, None, None, ktra_label, None])
        rr = ws.max_row
        ws.cell(rr, 3).value = formula
        if ktra_formula:
            ws.cell(rr, 6).value = ktra_formula
        return rr

    # ===== KHỐI MUA VÀO (đặt trên) =====
    ws.append(["KHỐI MUA VÀO"]); ws.cell(ws.max_row, 1).font = Font(bold=True, size=12, color="8a6d1f")
    # BK Mua vào: chỉ SUM dòng có STT (cột A) -> loại dòng TỔNG CỘNG
    r_bk_mua_ds = add_row("BK Mua vào", "Doanh số mua chưa có thuế",
                          f'=SUMIF({BK_MUA}!A:A,">0",{BK_MUA}!I:I)')
    r_bk_mua_thue = add_row("", "Thuế GTGT", f'=SUMIF({BK_MUA}!A:A,">0",{BK_MUA}!J:J)')
    r_ct_mua_ds = add_row("Chi tiết MUA VÀO", "Doanh số mua chưa có thuế",
                          f"=SUM({CT_MUA}!L:L)")
    r_ct_mua_thue = add_row("", "Thuế GTGT", f"=SUM({CT_MUA}!N:N)")
    ws.cell(r_bk_mua_ds, 5).value = "Kiểm tra Hàng hoá"
    ws.cell(r_bk_mua_ds, 6).value = f"=C{r_bk_mua_ds}-C{r_ct_mua_ds}"
    ws.cell(r_bk_mua_thue, 5).value = "Kiểm tra VAT"
    ws.cell(r_bk_mua_thue, 6).value = f"=C{r_bk_mua_thue}-C{r_ct_mua_thue}"
    ws.append([])

    # ===== KHỐI BÁN RA (đặt dưới) =====
    ws.append(["KHỐI BÁN RA"]); ws.cell(ws.max_row, 1).font = Font(bold=True, size=12, color="1F6B4A")
    # BK Bán ra: chỉ SUM dòng có STT (cột A là số) -> loại dòng "Tổng nhóm"/"TỔNG CỘNG"
    r_bk_ban_ds = add_row("BK Bán ra", "Tổng doanh thu hàng hoá, dịch vụ bán ra:",
                          f'=SUMIF({BK_BAN}!A:A,">0",{BK_BAN}!I:I)')
    r_bk_ban_thue = add_row("", "Tổng thuế GTGT của hàng hóa, dịch vụ bán ra:",
                            f'=SUMIF({BK_BAN}!A:A,">0",{BK_BAN}!J:J)')
    # Chi tiết BÁN RA: SUM theo dòng có STT (cột H)
    r_ct_ban_ds = add_row("Chi tiết BÁN RA", "Tổng tiền chưa thuế",
                          f"=SUM({CT_BAN}!L:L)")
    r_ct_ban_thue = add_row("", "Tổng tiền thuế", f"=SUM({CT_BAN}!N:N)")
    # dòng kiểm tra
    ws.cell(r_bk_ban_ds, 5).value = "Kiểm tra Hàng hoá"
    ws.cell(r_bk_ban_ds, 6).value = f"=C{r_bk_ban_ds}-C{r_ct_ban_ds}"
    ws.cell(r_bk_ban_thue, 5).value = "Kiểm tra VAT"
    ws.cell(r_bk_ban_thue, 6).value = f"=C{r_bk_ban_thue}-C{r_ct_ban_thue}"
    ws.append([])

    # ===== KẾT LUẬN =====
    ws.append(["KẾT LUẬN ĐỐI CHIẾU"]); ws.cell(ws.max_row, 1).font = Font(bold=True, size=12, color="2E5C8A")
    kr = ws.max_row
    ws.append(["", "Bán ra:", None])
    rr = ws.max_row
    ws.cell(rr, 3).value = (f'=IF(AND(ABS(C{r_bk_ban_ds}-C{r_ct_ban_ds})<100,ABS(C{r_bk_ban_thue}-C{r_ct_ban_thue})<100),'
                            f'"✓ KHỚP (BK Bán ra = Chi tiết Bán ra)",'
                            f'"⚠ LỆCH: hàng hoá "&TEXT(C{r_bk_ban_ds}-C{r_ct_ban_ds},"#,##0")&", VAT "&TEXT(C{r_bk_ban_thue}-C{r_ct_ban_thue},"#,##0"))')
    ws.cell(rr, 3).font = bold
    ws.append(["", "Mua vào:", None])
    rr = ws.max_row
    ws.cell(rr, 3).value = (f'=IF(AND(ABS(C{r_bk_mua_ds}-C{r_ct_mua_ds})<100,ABS(C{r_bk_mua_thue}-C{r_ct_mua_thue})<100),'
                            f'"✓ KHỚP (BK Mua vào = Chi tiết Mua vào)",'
                            f'"⚠ LỆCH: hàng hoá "&TEXT(C{r_bk_mua_ds}-C{r_ct_mua_ds},"#,##0")&", VAT "&TEXT(C{r_bk_mua_thue}-C{r_ct_mua_thue},"#,##0"))')
    ws.cell(rr, 3).font = bold

    # ===== DANH SÁCH HÓA ĐƠN LỆCH (để kiểm tra từng hóa đơn) =====
    # cấu hình cột để SUMIFS (ký hiệu + số HĐ → doanh số, thuế) theo từng sheet
    lech_cfg = {
        "sold": {"ct_sheet": "'Chi tiết BÁN RA'", "ct_kh": "A", "ct_key": "B", "ct_ds": "L", "ct_thue": "N",
                 "bk_sheet": "'BK Bán ra'", "bk_kh": "B", "bk_key": "D", "bk_ds": "I", "bk_thue": "J"},
        "purchase": {"ct_sheet": "'Chi tiết MUA VÀO'", "ct_kh": "A", "ct_key": "B", "ct_ds": "L", "ct_thue": "N",
                     "bk_sheet": "'BK Mua vào'", "bk_kh": "B", "bk_key": "C", "bk_ds": "I", "bk_thue": "J"},
    }

    def them_ds_lech(tieu_de, loai):
        cfg = lech_cfg[loai]
        ct = ct_totals[loai]; bk = bk_totals[loai]
        all_keys = sorted(set(ct.keys()) | set(bk.keys()),
                          key=lambda x: (x[0], int(x[1]) if x[1].isdigit() else 0))
        lech = []
        for k in all_keys:
            cc = ct.get(k, {"ds": 0, "thue": 0})
            bb = bk.get(k, {"ds": 0, "thue": 0})
            ld = round((cc["ds"] or 0) - (bb["ds"] or 0))
            lt = round((cc["thue"] or 0) - (bb["thue"] or 0))
            if abs(ld) >= 100 or abs(lt) >= 100:
                lech.append(k)
        ws.append([])
        ws.append([tieu_de])
        ws.cell(ws.max_row, 1).font = Font(bold=True, size=11, color="C00000")
        if not lech:
            ws.append(["", "✓ Không có hóa đơn nào lệch (>= 100đ)"])
            ws.cell(ws.max_row, 2).font = Font(color="1F6B4A")
            return
        ws.append(["Ký hiệu", "Số HĐ", "Chưa VAT (Chi tiết)", "Chưa VAT (Bảng kê)",
                   "Lệch chưa VAT", "VAT (Chi tiết)", "VAT (Bảng kê)", "Lệch VAT", "Ghi chú"])
        hr = ws.max_row
        for c in range(1, 10):
            ws.cell(hr, c).font = Font(bold=True, color="FFFFFF")
            ws.cell(hr, c).fill = PatternFill("solid", fgColor="C0392B")
        for k in lech:
            ghi = ""
            if k in ct and k not in bk:
                ghi = "Chỉ có ở Chi tiết (HĐ bị thay thế/không vào BK)"
            elif k in bk and k not in ct:
                ghi = "Chỉ có ở Bảng kê"
            ws.append([k[0], k[1], None, None, None, None, None, None, ghi])
            rr = ws.max_row
            # CÔNG THỨC SUMIFS: dùng cả Ký hiệu + Số HĐ để không bị trùng
            ws.cell(rr, 3).value = (f"=SUMIFS({cfg['ct_sheet']}!{cfg['ct_ds']}:{cfg['ct_ds']},"
                                    f"{cfg['ct_sheet']}!{cfg['ct_kh']}:{cfg['ct_kh']},$A{rr},"
                                    f"{cfg['ct_sheet']}!{cfg['ct_key']}:{cfg['ct_key']},$B{rr})")
            ws.cell(rr, 4).value = (f"=SUMIFS({cfg['bk_sheet']}!{cfg['bk_ds']}:{cfg['bk_ds']},"
                                    f"{cfg['bk_sheet']}!{cfg['bk_kh']}:{cfg['bk_kh']},$A{rr},"
                                    f"{cfg['bk_sheet']}!{cfg['bk_key']}:{cfg['bk_key']},$B{rr})")
            ws.cell(rr, 5).value = f"=C{rr}-D{rr}"
            ws.cell(rr, 6).value = (f"=SUMIFS({cfg['ct_sheet']}!{cfg['ct_thue']}:{cfg['ct_thue']},"
                                    f"{cfg['ct_sheet']}!{cfg['ct_kh']}:{cfg['ct_kh']},$A{rr},"
                                    f"{cfg['ct_sheet']}!{cfg['ct_key']}:{cfg['ct_key']},$B{rr})")
            ws.cell(rr, 7).value = (f"=SUMIFS({cfg['bk_sheet']}!{cfg['bk_thue']}:{cfg['bk_thue']},"
                                    f"{cfg['bk_sheet']}!{cfg['bk_kh']}:{cfg['bk_kh']},$A{rr},"
                                    f"{cfg['bk_sheet']}!{cfg['bk_key']}:{cfg['bk_key']},$B{rr})")
            ws.cell(rr, 8).value = f"=F{rr}-G{rr}"
            for c in range(1, 9):
                ws.cell(rr, c).font = Font(color="C00000")
                if c >= 3:
                    ws.cell(rr, c).number_format = "#,##0"
            ws.cell(rr, 9).font = Font(color="C00000")

    them_ds_lech("CHI TIẾT HÓA ĐƠN LỆCH - BÁN RA (kiểm tra & điều chỉnh):", "sold")
    them_ds_lech("CHI TIẾT HÓA ĐƠN LỆCH - MUA VÀO (kiểm tra & điều chỉnh):", "purchase")

    # định dạng số cột C và F (kể cả ô công thức SUMIF/SUM ra số lẻ)
    for r in range(1, ws.max_row + 1):
        for cc in (3, 6):
            v = ws.cell(r, cc).value
            if v is None:
                continue
            # ô kết luận dạng chữ (IF...TEXT) thì bỏ qua
            if isinstance(v, str) and v.startswith("=") and "TEXT" in v:
                continue
            if isinstance(v, (int, float)) or (isinstance(v, str) and v.startswith("=")):
                ws.cell(r, cc).number_format = "#,##0"
    ws.column_dimensions["A"].width = 18
    ws.column_dimensions["B"].width = 42
    ws.column_dimensions["C"].width = 20
    ws.column_dimensions["E"].width = 18
    ws.column_dimensions["F"].width = 18
    ws.freeze_panes = "C1"  # cố định cột tới cột 2 (A,B) để dễ xem

    wb.remove(wb["Sheet"])
    # tên file kèm kỳ (nếu có) để các kỳ không ghi đè nhau trên Desktop
    ky_fname = ""
    try:
        for r in rows:
            nd = (r["tdlap"] or "").split("T")[0]
            if "-" in nd:
                y, m, _d = nd.split("-"); ky_fname = f"_T{int(m):02d}{y}"; break
    except Exception:
        pass
    fname_x = f"BangKe_HoaDon_{comp['mst']}{ky_fname}.xlsx"
    path = os.path.join(DOWNLOAD_DIR, f"TongHop_{comp['mst']}.xlsx")
    wb.save(path)
    import shutil
    open_path = path
    # Mặc định lưu ra DESKTOP cho dễ tìm
    desktop = _get_desktop_dir()
    if desktop and os.path.isdir(desktop):
        try:
            dest = os.path.join(desktop, fname_x)
            shutil.copy(path, dest)
            open_path = dest
        except Exception:
            pass
    # lưu thêm vào thư mục công ty (nếu có cấu hình)
    save_dir3 = (comp["save_dir"] or "").strip() if comp else ""
    if save_dir3 and os.path.isdir(save_dir3):
        try:
            shutil.copy(path, os.path.join(save_dir3, fname_x))
        except Exception:
            pass
    _open_file_local(open_path)
    return FileResponse(path, filename=fname_x)


# ---------- ĐỌC FILE XML -> XUẤT EXCEL CHI TIẾT ----------
def _extract_invoice_xml(data_bytes):
    """
    Nhận bytes của file người dùng upload. File có thể là:
      - file invoice.zip của TCT (chứa invoice.xml bên trong) — kể cả khi đặt đuôi .xml
      - file XML thuần
    Trả về bytes của nội dung XML hóa đơn.
    """
    import io as _io
    import zipfile as _zip
    # File zip bắt đầu bằng 'PK'
    if data_bytes[:2] == b"PK":
        try:
            zf = _zip.ZipFile(_io.BytesIO(data_bytes))
            # ưu tiên invoice.xml, nếu không có lấy file .xml đầu tiên
            names = zf.namelist()
            target = None
            for n in names:
                if n.lower().endswith("invoice.xml"):
                    target = n
                    break
            if not target:
                for n in names:
                    if n.lower().endswith(".xml"):
                        target = n
                        break
            if target:
                return zf.read(target)
        except Exception:
            pass
    return data_bytes


def _parse_detail_json(detail):
    """
    Parse JSON chi tiết hóa đơn (từ endpoint detail của TCT) thành list mặt hàng.
    Cùng định dạng output với _parse_xml_invoice để dùng chung.
    """
    rows = []
    if not detail or not isinstance(detail, dict):
        return rows
    khmshdon = str(detail.get("khmshdon", "") or "")
    khhdon = detail.get("khhdon", "") or ""
    shdon = str(detail.get("shdon", "") or "")
    ngay = detail.get("tdlap", "") or ""
    ten_nban = detail.get("nbten", "") or ""
    mst_nban = detail.get("nbmst", "") or ""
    dchi_nban = detail.get("nbdchi", "") or ""
    ten_nmua = detail.get("nmten", "") or detail.get("nmtnmua", "") or ""
    mst_nmua = detail.get("nmmst", "") or ""
    items = detail.get("hdhhdvu") or []
    for it in items:
        rows.append({
            "khmshdon": khmshdon, "khhdon": khhdon, "shdon": shdon,
            "ngay": ngay, "ten_nban": ten_nban, "mst_nban": mst_nban,
            "dchi_nban": dchi_nban, "ten_nmua": ten_nmua, "mst_nmua": mst_nmua,
            "stt": str(it.get("stt", "") or ""),
            "tchat": str(it.get("tchat", "") or ""),
            "ma_vt": it.get("mhhdvu", "") or "",
            "ten_hang": it.get("ten", "") or it.get("thhdvu", "") or "",
            "dvt": it.get("dvtinh", "") or "",
            "sluong": it.get("sluong", ""),
            "dgia": it.get("dgia", ""),
            "thtien": it.get("thtien", ""),
            "stckhau": it.get("stckhau", ""),
            "tsuat": str(it.get("ltsuat", "") or it.get("tsuat", "") or ""),
            "tien_thue": it.get("tthue", "") or it.get("tongtien_thue", ""),
            "tgtcthue": detail.get("tgtcthue", ""),
            "tgtthue": detail.get("tgtthue", ""),
            "tgtttbso": detail.get("tgtttbso", ""),
        })
    return rows


def _summary_from_detail_json(detail):
    """Parse JSON detail -> thông tin gộp theo thuế suất (cho BK bán ra)."""
    if not detail or not isinstance(detail, dict):
        return None
    info = {
        "khmshdon": str(detail.get("khmshdon", "") or ""),
        "khhdon": detail.get("khhdon", "") or "",
        "shdon": str(detail.get("shdon", "") or ""),
        "ngay": detail.get("tdlap", "") or "",
        "ten_nban": detail.get("nbten", "") or "",
        "mst_nban": detail.get("nbmst", "") or "",
        "ten_nmua": detail.get("nmten", "") or detail.get("nmtnmua", "") or "",
        "mst_nmua": detail.get("nmmst", "") or "",
    }
    items = detail.get("hdhhdvu") or []
    ten_hangs = [it.get("ten") or it.get("thhdvu") for it in items if (it.get("ten") or it.get("thhdvu"))]
    info["mat_hang"] = (ten_hangs[0] + (" ..." if len(ten_hangs) > 1 else "")) if ten_hangs else ""

    def norm_ts(ts):
        s = str(ts or "").strip().upper()
        if s in ("", "KCT", "KHAC", "KO", "KHÔNG") or "KKK" in s or "KCT" in s:
            return "KCT"
        s2 = s.replace("%", "").strip()
        if s2 in ("0", "5", "8", "10"):
            return s2
        return s or "KHAC"

    theo_ts = {}
    # ưu tiên phần tổng hợp thuế suất nếu có
    ltsuat = detail.get("thttltsuat") or detail.get("hdhhdvu_ltsuat") or []
    if ltsuat and isinstance(ltsuat, list):
        for l in ltsuat:
            key = norm_ts(l.get("tsuat"))
            ds = _to_num(l.get("thtien")) or 0
            thue = _to_num(l.get("tthue")) or 0
            cur = theo_ts.setdefault(key, {"ds": 0, "thue": 0})
            cur["ds"] += ds if isinstance(ds, (int, float)) else 0
            cur["thue"] += thue if isinstance(thue, (int, float)) else 0
    else:
        for it in items:
            key = norm_ts(it.get("ltsuat") or it.get("tsuat"))
            ds = _to_num(it.get("thtien")) or 0
            try:
                rate = float(str(it.get("ltsuat") or it.get("tsuat") or "0").replace("%", "")) / 100
            except Exception:
                rate = 0
            thue = round(ds * rate) if isinstance(ds, (int, float)) else 0
            cur = theo_ts.setdefault(key, {"ds": 0, "thue": 0})
            cur["ds"] += ds if isinstance(ds, (int, float)) else 0
            cur["thue"] += thue
    info["theo_ts"] = theo_ts
    return info


def _parse_xml_invoice(xml_bytes):
    """
    Đọc 1 hóa đơn (XML thuần hoặc file invoice.zip), trả về list các dòng mặt hàng.
    Cấu trúc thật: HDon>DLHDon>NDHDon>{NBan,NMua,DSHHDVu>HHDVu,TToan}
    """
    import xml.etree.ElementTree as ET
    rows = []
    xml_bytes = _extract_invoice_xml(xml_bytes)
    try:
        root = ET.fromstring(xml_bytes)
    except Exception:
        return rows

    def find_text(node, *tags):
        for t in tags:
            el = node.find(f".//{t}")
            if el is not None and el.text:
                return el.text.strip()
        return ""

    khmshdon = find_text(root, "KHMSHDon")
    khhdon = find_text(root, "KHHDon")
    shdon = find_text(root, "SHDon")
    ngay = find_text(root, "NLap")
    # Người bán
    nban = root.find(".//NBan")
    ten_nban = mst_nban = dchi_nban = ""
    if nban is not None:
        ten_nban = find_text(nban, "Ten")
        mst_nban = find_text(nban, "MST")
        dchi_nban = find_text(nban, "DChi")
    # Người mua
    nmua = root.find(".//NMua")
    ten_nmua = mst_nmua = ""
    if nmua is not None:
        ten_nmua = find_text(nmua, "Ten")
        mst_nmua = find_text(nmua, "MST")
    # Tổng tiền
    tgtcthue = find_text(root, "TgTCThue")
    tgtthue = find_text(root, "TgTThue")
    tgtttbso = find_text(root, "TgTTTBSo")

    # Danh sách hàng hóa dịch vụ (chỉ lấy HHDVu trong DSHHDVu)
    dshh = root.find(".//DSHHDVu")
    hh_list = dshh.findall("HHDVu") if dshh is not None else root.findall(".//HHDVu")

    def lay_ttkhac(hh, ten_truong):
        """Lấy giá trị DLieu trong TTKhac>TTin có TTruong = ten_truong."""
        for ttin in hh.findall(".//TTKhac/TTin"):
            tt = ttin.find("TTruong")
            if tt is not None and tt.text and tt.text.strip() == ten_truong:
                dl = ttin.find("DLieu")
                if dl is not None and dl.text:
                    return dl.text.strip()
        return ""

    for hh in hh_list:
        rows.append({
            "khmshdon": khmshdon, "khhdon": khhdon, "shdon": shdon,
            "ngay": ngay, "ten_nban": ten_nban, "mst_nban": mst_nban,
            "dchi_nban": dchi_nban, "ten_nmua": ten_nmua, "mst_nmua": mst_nmua,
            "stt": find_text(hh, "STT"),
            "tchat": find_text(hh, "TChat"),     # 1=hàng, 2=KM, 3=chiết khấu
            "ma_vt": find_text(hh, "MHHDVu"),
            "ten_hang": find_text(hh, "THHDVu"),
            "dvt": find_text(hh, "DVTinh"),
            "sluong": find_text(hh, "SLuong"),
            "dgia": find_text(hh, "DGia"),
            "thtien": find_text(hh, "ThTien"),
            "stckhau": find_text(hh, "STCKhau"),  # số tiền chiết khấu dòng này
            "tsuat": find_text(hh, "TSuat"),
            # tiền thuế GTGT lấy ĐÚNG từ XML (TTKhac > TongTien_Thue)
            "tien_thue": lay_ttkhac(hh, "TongTien_Thue"),
            "tgtcthue": tgtcthue, "tgtthue": tgtthue, "tgtttbso": tgtttbso,
        })
    return rows


def _parse_invoice_summary(xml_bytes):
    """
    Đọc 1 hóa đơn, trả về thông tin GỘP theo hóa đơn (cho bảng kê bán ra):
      {khmshdon, khhdon, shdon, ngay, ten_nban, mst_nban, ten_nmua, mst_nmua,
       mat_hang, theo_ts: {'8': {'ds','thue'}, 'KCT': {...}, ...}}
    Mỗi hóa đơn có thể nhiều thuế suất (lấy từ THTTLTSuat).
    """
    import xml.etree.ElementTree as ET
    xml_bytes = _extract_invoice_xml(xml_bytes)
    try:
        root = ET.fromstring(xml_bytes)
    except Exception:
        return None

    def ft(node, *tags):
        if node is None:
            return ""
        for t in tags:
            el = node.find(f".//{t}")
            if el is not None and el.text:
                return el.text.strip()
        return ""

    info = {
        "khmshdon": ft(root, "KHMSHDon"),
        "khhdon": ft(root, "KHHDon"),
        "shdon": ft(root, "SHDon"),
        "ngay": ft(root, "NLap"),
    }
    nban = root.find(".//NBan")
    info["ten_nban"] = ft(nban, "Ten")
    info["mst_nban"] = ft(nban, "MST")
    nmua = root.find(".//NMua")
    info["ten_nmua"] = ft(nmua, "Ten") or ft(nmua, "HVTNMHang")
    info["mst_nmua"] = ft(nmua, "MST")

    dshh = root.find(".//DSHHDVu")
    ten_hangs = []
    if dshh is not None:
        for hh in dshh.findall("HHDVu"):
            t = ft(hh, "THHDVu")
            if t:
                ten_hangs.append(t)
    info["mat_hang"] = (ten_hangs[0] + (" ..." if len(ten_hangs) > 1 else "")) if ten_hangs else ""

    def norm_ts(ts):
        s = str(ts or "").strip().upper()
        if s in ("", "KCT", "KHAC", "KO", "KHÔNG") or "KKK" in s or "KCT" in s:
            return "KCT"
        s2 = s.replace("%", "").strip()
        if s2 in ("0", "5", "8", "10"):
            return s2
        return s or "KHAC"

    theo_ts = {}
    lts = root.findall(".//THTTLTSuat/LTSuat")
    if lts:
        for l in lts:
            key = norm_ts(ft(l, "TSuat"))
            ds = _to_num(ft(l, "ThTien")) or 0
            thue = _to_num(ft(l, "TThue")) or 0
            cur = theo_ts.setdefault(key, {"ds": 0, "thue": 0})
            cur["ds"] += ds if isinstance(ds, (int, float)) else 0
            cur["thue"] += thue if isinstance(thue, (int, float)) else 0
    elif dshh is not None:
        for hh in dshh.findall("HHDVu"):
            key = norm_ts(ft(hh, "TSuat"))
            ds = _to_num(ft(hh, "ThTien")) or 0
            try:
                rate = float(str(ft(hh, "TSuat")).replace("%", "")) / 100
            except Exception:
                rate = 0
            thue = round(ds * rate) if isinstance(ds, (int, float)) else 0
            cur = theo_ts.setdefault(key, {"ds": 0, "thue": 0})
            cur["ds"] += ds if isinstance(ds, (int, float)) else 0
            cur["thue"] += thue
    info["theo_ts"] = theo_ts
    return info


@app.post("/api/parse-xml")
async def parse_xml_to_excel(request: Request):
    """
    Nhận nhiều file XML (multipart), đọc và kết xuất ra 1 file Excel chi tiết
    theo đúng định dạng từng mặt hàng.
    """
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    form = await request.form()
    files = form.getlist("files")
    if not files:
        raise HTTPException(400, "Chưa chọn file XML nào")

    all_rows = []
    for f in files:
        content = await f.read()
        all_rows.extend(_parse_xml_invoice(content))

    if not all_rows:
        raise HTTPException(400, "Không đọc được dữ liệu từ các file XML (sai định dạng?)")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Chi tiết hóa đơn"
    headers = ["Ký hiệu mẫu", "Số seri", "Số", "Ngày",
               "Tên người bán", "MST người bán", "Người mua", "MST người mua",
               "STT", "Tên hàng hóa/dịch vụ", "ĐVT", "Số lượng", "Đơn giá",
               "Thành tiền", "Thuế suất",
               "Tổng chưa thuế (HĐ)", "Tổng thuế (HĐ)", "Tổng thanh toán (HĐ)"]
    ws.append(headers)
    for c in range(1, len(headers) + 1):
        cell = ws.cell(1, c)
        cell.font = Font(bold=True, color="FFFFFF", name="Arial")
        cell.fill = PatternFill("solid", fgColor="2E5C8A")
        cell.alignment = Alignment(horizontal="center")

    def num(v):
        try:
            return float(v)
        except Exception:
            return v

    for r in all_rows:
        ws.append([
            r["khmshdon"], r["khhdon"], r["shdon"], r["ngay"],
            r["ten_nban"], r["mst_nban"], r.get("ten_nmua", ""), r.get("mst_nmua", ""),
            r.get("stt", ""), r["ten_hang"], r["dvt"],
            num(r["sluong"]), num(r["dgia"]), num(r["thtien"]), r["tsuat"],
            num(r.get("tgtcthue", "")), num(r.get("tgtthue", "")), num(r.get("tgtttbso", "")),
        ])
    for col in ws.columns:
        w = max((len(str(c.value)) for c in col if c.value is not None), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(w + 2, 50)

    path = os.path.join(DOWNLOAD_DIR, "ChiTiet_TuXML.xlsx")
    wb.save(path)
    return FileResponse(path, filename="ChiTiet_HoaDon_TuXML.xlsx")


# ---------- MỤC 5: XEM HÓA ĐƠN DẠNG HTML (chuyển từ XML/JSON) ----------
def _render_invoice_html(inv):
    """Dựng HTML hiển thị 1 hóa đơn từ dict JSON đã lưu (field raw)."""
    def g(k, d=""):
        v = inv.get(k)
        return v if v not in (None, "") else d

    def vnd(x):
        try:
            return f"{float(x):,.0f}".replace(",", ".")
        except Exception:
            return x or ""

    items = inv.get("hdhhdvu") or []
    rows_html = ""
    for i, it in enumerate(items, 1):
        rows_html += f"""<tr>
            <td style="text-align:center">{i}</td>
            <td>{it.get('ten','') or it.get('thhdvu','')}</td>
            <td style="text-align:center">{it.get('dvtinh','')}</td>
            <td style="text-align:right">{vnd(it.get('sluong'))}</td>
            <td style="text-align:right">{vnd(it.get('dgia'))}</td>
            <td style="text-align:right">{vnd(it.get('thtien'))}</td>
        </tr>"""

    return f"""<!DOCTYPE html><html lang="vi"><head><meta charset="UTF-8">
<title>Hóa đơn {g('khhdon')}-{g('shdon')}</title>
<style>
  body{{font-family:'Times New Roman',serif;max-width:800px;margin:24px auto;color:#1a1a1a;padding:0 20px}}
  h2{{text-align:center;color:#c00;margin-bottom:4px}}
  .meta{{display:flex;justify-content:space-between;font-size:14px;margin:12px 0;flex-wrap:wrap}}
  .box{{border:1px solid #999;padding:12px 16px;border-radius:6px;margin:10px 0;font-size:14px;line-height:1.7}}
  table{{width:100%;border-collapse:collapse;margin-top:12px;font-size:13px}}
  th,td{{border:1px solid #aaa;padding:6px 8px}}
  th{{background:#f0e6d2}}
  .tongtien{{text-align:right;font-size:15px;margin-top:12px;line-height:1.8}}
  .label{{color:#666}}
</style></head><body>
<h2>HÓA ĐƠN GIÁ TRỊ GIA TĂNG</h2>
<div class="meta">
  <span>Ký hiệu: <b>{g('khmshdon')}{g('khhdon')}</b></span>
  <span>Số: <b>{g('shdon')}</b></span>
  <span>Ngày lập: <b>{(g('tdlap') or '').split('T')[0]}</b></span>
</div>
<div class="box">
  <div><span class="label">Người bán:</span> <b>{g('nbten')}</b></div>
  <div><span class="label">Mã số thuế:</span> {g('nbmst')}</div>
  <div><span class="label">Địa chỉ:</span> {g('nbdchi')}</div>
</div>
<div class="box">
  <div><span class="label">Người mua:</span> <b>{g('nmten')}</b></div>
  <div><span class="label">Mã số thuế:</span> {g('nmmst')}</div>
  <div><span class="label">Địa chỉ:</span> {g('nmdchi')}</div>
</div>
<table>
  <thead><tr><th>STT</th><th>Tên hàng hóa, dịch vụ</th><th>ĐVT</th>
  <th>Số lượng</th><th>Đơn giá</th><th>Thành tiền</th></tr></thead>
  <tbody>{rows_html or '<tr><td colspan=6 style="text-align:center">Không có chi tiết hàng hóa</td></tr>'}</tbody>
</table>
<div class="tongtien">
  <div>Cộng tiền hàng: <b>{vnd(g('tgtcthue'))}</b> đ</div>
  <div>Tiền thuế GTGT: <b>{vnd(g('tgtthue'))}</b> đ</div>
  <div>Tổng thanh toán: <b style="color:#c00;font-size:17px">{vnd(g('tgtttbso'))}</b> đ</div>
</div>
</body></html>"""


@app.get("/api/invoice-html/{invoice_id}")
def invoice_html(invoice_id: int):
    """
    Mở hóa đơn dạng HTML. Ưu tiên lấy ĐÚNG file invoice.html của Tổng cục Thuế
    (nguyên bản, không chỉnh sửa) từ file invoice.zip tải về.
    Thứ tự: (1) file zip đã lưu trong thư mục công ty -> (2) tải mới từ TCT
    -> (3) nếu không có, mới tự dựng HTML từ dữ liệu.
    """
    conn = db()
    row = conn.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
    comp = conn.execute("SELECT * FROM companies WHERE id=?",
                        (row["company_id"],)).fetchone() if row else None
    conn.close()
    if not row:
        raise HTTPException(404, "Không tìm thấy hóa đơn")

    he_thong = row["he_thong"] or "query"
    base = f"{row['khhdon']}_{row['shdon']}_{row['nbmst']}"

    def html_from_zip(zip_bytes):
        try:
            zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
            for nm in zf.namelist():
                if nm.lower().endswith("invoice.html"):
                    return zf.read(nm).decode("utf-8", "replace")
        except Exception:
            pass
        return None

    raw_html = None

    # (1) Tìm file zip đã lưu trong thư mục cấu hình
    save_dir = (comp["save_dir"] or "").strip() if comp else ""
    if save_dir and os.path.isdir(save_dir):
        for rootdir, _dirs, files in os.walk(save_dir):
            for fn in files:
                if fn.startswith(base) and fn.lower().endswith(".zip"):
                    try:
                        with open(os.path.join(rootdir, fn), "rb") as f:
                            raw_html = html_from_zip(f.read())
                    except Exception:
                        pass
                    if raw_html:
                        break
            if raw_html:
                break

    # (2) Chưa có -> tải mới từ TCT (nếu đang đăng nhập)
    if not raw_html:
        client = CLIENTS.get(row["company_id"])
        if client and client.token:
            zdata = client.download_xml(row["nbmst"], row["khhdon"],
                                        row["khmshdon"], row["shdon"],
                                        row["loai"], he_thong)
            if zdata:
                raw_html = html_from_zip(zdata)

    fname = f"HoaDon_{row['khhdon']}_{row['shdon']}.html"

    # (3) Có HTML gốc của TCT -> trả nguyên bản
    if raw_html:
        return HTMLResponse(raw_html)

    # Không lấy được -> tự dựng từ dữ liệu (dự phòng)
    try:
        inv = json.loads(row["raw"]) if row["raw"] else {}
    except Exception:
        inv = {}
    client = CLIENTS.get(row["company_id"])
    if client and client.token:
        detail = client.get_detail(row["nbmst"], row["khhdon"],
                                   row["khmshdon"], row["shdon"], he_thong)
        if detail:
            inv = detail
    return HTMLResponse(_render_invoice_html(inv))


@app.get("/api/invoices-html-zip/{cid}")
def invoices_html_zip(cid: int, loai: Optional[str] = None):
    """Tải file invoice.zip chứa 1 file invoice.html gộp toàn bộ hóa đơn để đọc."""
    conn = db()
    comp = conn.execute("SELECT * FROM companies WHERE id=?", (cid,)).fetchone()
    if loai:
        rows = conn.execute(
            "SELECT * FROM invoices WHERE company_id=? AND loai=? ORDER BY tdlap DESC",
            (cid, loai)).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM invoices WHERE company_id=? ORDER BY loai, tdlap DESC",
            (cid,)).fetchall()
    conn.close()

    if not rows:
        raise HTTPException(404, "Chưa có hóa đơn nào để xuất")

    # Gộp tất cả hóa đơn vào 1 file invoice.html (mỗi hóa đơn 1 trang, ngăn cách)
    parts = []
    for r in rows:
        try:
            inv = json.loads(r["raw"]) if r["raw"] else {}
        except Exception:
            inv = {}
        loai_txt = "MUA VÀO" if r["loai"] == "purchase" else "BÁN RA"
        # lấy phần body của từng hóa đơn
        html1 = _render_invoice_html(inv)
        body = html1.split("<body>", 1)[-1].split("</body>", 1)[0]
        parts.append(
            f'<div style="border-bottom:3px dashed #999;margin:30px 0;padding-bottom:20px">'
            f'<div style="background:#2E5C8A;color:#fff;padding:6px 12px;border-radius:6px;'
            f'display:inline-block;font-weight:bold;margin-bottom:10px">{loai_txt}</div>'
            f'{body}</div>')

    full_html = f"""<!DOCTYPE html><html lang="vi"><head><meta charset="UTF-8">
<title>Danh sách hóa đơn - {comp['ten']}</title>
<style>body{{font-family:'Times New Roman',serif;max-width:850px;margin:20px auto;padding:0 20px}}
table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{border:1px solid #aaa;padding:6px 8px}}
th{{background:#f0e6d2}}h2{{text-align:center;color:#c00}}</style></head><body>
<h1 style="text-align:center">DANH SÁCH HÓA ĐƠN - {comp['ten']}</h1>
<p style="text-align:center;color:#666">MST: {comp['mst']} | Tổng: {len(rows)} hóa đơn</p>
{''.join(parts)}
</body></html>"""

    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("invoice.html", full_html)
    mem.seek(0)
    return StreamingResponse(
        mem, media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=invoice.zip"})


if __name__ == "__main__":
    import webbrowser, threading, socket

    # Tự tìm cổng trống nếu 8686 đang bị chiếm
    def find_free_port(preferred=8686):
        for port in [preferred, 8687, 8688, 8689, 8690, 8787, 8888, 9000]:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.bind(("127.0.0.1", port))
                s.close()
                return port
            except OSError:
                s.close()
                continue
        return preferred

    PORT = find_free_port(8686)
    URL = f"http://127.0.0.1:{PORT}"

    def open_browser():
        time.sleep(1.5)
        webbrowser.open(URL)
    threading.Thread(target=open_browser, daemon=True).start()

    print("=" * 55)
    print("  PHẦN MỀM QUẢN LÝ HÓA ĐƠN ĐIỆN TỬ ĐA CÔNG TY")
    print(f"  Đang chạy tại: {URL}")
    if PORT != 8686:
        print(f"  (Cổng 8686 bận nên tự chuyển sang {PORT})")
    print("  (Đóng cửa sổ này để tắt phần mềm)")
    print("=" * 55)
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
