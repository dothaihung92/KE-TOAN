import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: đúng ca thật người dùng báo cáo (5/9/2026), VẪN Y HỆT
sau 2 lần fix trước (lọc "hiện rõ trên MISA" cho PUInvoice/PUServiceDetail,
build .171/.172) — "⚠ Mua hàng — TỔNG LỆCH" (MISA 439.697.670đ/8.102.848đ
so với nguồn 429.697.670đ/7.302.848đ, chênh ĐÚNG 10.000.000đ + 800.000đ =
VAT 8%) NHƯNG bảng khoanh vùng "0/115 hóa đơn thiếu/lệch" bên dưới TRỐNG
TRƠN — không có dòng "thiếu", "lệch" hay "thừa" nào cả, người dùng không
biết hóa đơn nào gây lệch.

Nguyên nhân THẬT (khác 2 lần fix trước — những lần đó lọc chứng từ ẨN/LỖI,
không giải thích được vì sao bảng khoanh vùng trống trơn): khung ngày lấy
dữ liệu MISA từ SQL (tu_ngay_purchase/den_ngay_purchase, xem _khung_ngay)
được NỚI THÊM ±1 NGÀY so với khung ngày THẬT của nguồn (pham_vi_ngay, dùng
trong _dung_ky_that để lọc dòng "THỪA trong MISA" — cố tình làm khung SÁT
hơn, không nới, để KHÔNG báo "thừa" oan cho hóa đơn thật ra khác kỳ đang
đối chiếu, xem docstring _dung_ky_that). Hậu quả: 1 hóa đơn MISA nằm ĐÚNG
trong phần nới biên (khác kỳ đang đối chiếu, không khớp bất kỳ hóa đơn
nguồn nào) vẫn bị CỘNG VÀO TỔNG (tong_ds_misa_p, tính từ TOÀN BỘ dữ liệu
SQL lấy về, không lọc theo _dung_ky_that) — gây "TỔNG LỆCH" — nhưng lại bị
_dung_ky_that LOẠI KHỎI danh sách "THỪA" hiển thị (đúng theo thiết kế —
tránh báo thừa oan) — khiến TỔNG báo lệch mà bảng khoanh vùng không hiện
gì để người dùng dò, y hệt triệu chứng thật.

Fix: TỔNG (tong_ds_misa/tong_ds_misa_p ở CẢ Bán hàng lẫn Mua hàng) giờ chỉ
cộng những dòng MISA "đúng kỳ" (dùng CHUNG _dung_ky_that với danh sách
"thừa") — nhất quán: hóa đơn nào đã bị loại khỏi "thừa" (khác kỳ) thì cũng
không được tính vào TỔNG."""
import sys, sqlite3
sys.path.insert(0, _REPO_ROOT)
import server


def db_factory():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE invoices (
        company_id INTEGER, loai TEXT, nbmst TEXT, nmmst TEXT, khhdon TEXT, shdon TEXT,
        tdlap TEXT, tgtcthue REAL, tgtthue REAL, tthai TEXT, raw TEXT, detail_json TEXT)""")
    conn.execute("""CREATE TABLE companies (
        id INTEGER PRIMARY KEY, save_dir TEXT)""")
    conn.execute("INSERT INTO companies VALUES (1, '')")
    # DUY NHẤT 1 hóa đơn nguồn, ngày 15/07/2026 -> pham_vi_ngay["purchase"]
    # = [15/07/2026, 15/07/2026] (khung SÁT, không nới).
    conn.execute(
        "INSERT INTO invoices VALUES (1,'purchase','0317009837','0100000000','1','1824',"
        "'2026-07-15T10:00:00',5000000,400000,'1','{}',NULL)")
    conn.commit()
    return conn


class FakeCursor:
    """Giả lập CSDL MISA: PUInvoice có 2 dòng — (1) hóa đơn 1824 khớp đúng
    nguồn (5tr/400k, ngày 15/07 — TRONG kỳ), (2) hóa đơn 999 HOÀN TOÀN
    KHÔNG liên quan tới nguồn (10tr/800k, ngày 16/07 — nằm ĐÚNG trong phần
    nới biên +1 ngày của khung SQL, nhưng NGOÀI khung SÁT của nguồn) — mô
    phỏng đúng SQL Server: WHERE ngày BETWEEN 14/07 và 16/07 (đã nới ±1
    ngày) nên CẢ 2 dòng đều được trả về."""

    def __init__(self):
        self.last_sql = ""
        self.last_params = ()

    def execute(self, sql, params=()):
        self.last_sql = sql
        self.last_params = tuple(params) if isinstance(params, (tuple, list)) else (params,)
        return self

    def fetchall(self):
        sql = self.last_sql
        if "FROM sys.columns" in sql:
            table = self.last_params[0]
            if table == "PUInvoice":
                return [("AccountObjectTaxCode", "nvarchar"), ("InvNo", "nvarchar"),
                        ("TotalTurnoverAmount", "money"), ("TotalVATAmount", "money"),
                        ("RefDate", "datetime")]
            return []
        if "FROM PUInvoice WHERE" in sql:
            import datetime
            return [
                ("0317009837", "1824", 5000000, 400000, datetime.datetime(2026, 7, 15)),
                ("0399999999", "999", 10000000, 800000, datetime.datetime(2026, 7, 16)),
            ]
        return []

    def fetchone(self):
        if "FROM OrganizationUnit" in self.last_sql:
            return None   # không dò được BranchID -> KHÔNG lọc "hiện rõ" (không liên quan bug này)
        return None


class FakeConn:
    def __init__(self):
        self._cur = FakeCursor()

    def cursor(self):
        return self._cur

    def close(self):
        pass


orig_db, orig_connect = server.db, server._misa_sql_connect
server.db = db_factory
server._misa_sql_connect = lambda cid, database=None: FakeConn()
try:
    kq = server._misa_doi_chieu_import_toan_bo(1, "TESTDB")
finally:
    server.db = orig_db
    server._misa_sql_connect = orig_connect

mh = kq["mua_hang"]
print("Mua hàng:", mh)

assert mh["tong_khop"], (
    f"Hóa đơn 999 (10tr/800k, ngày 16/07 nằm NGOÀI kỳ đối chiếu 15/07 — chỉ lọt qua vì SQL nới biên "
    f"±1 ngày) KHÔNG được tính vào TỔNG MISA (đã bị loại khỏi 'thừa' vì khác kỳ, phải nhất quán loại "
    f"khỏi TỔNG luôn) — TỔNG phải khớp đúng nguồn (5tr/400k) — được tong_khop={mh.get('tong_khop')}, "
    f"tong_ds_misa={mh.get('tong_ds_misa')}, tong_thue_misa={mh.get('tong_thue_misa')}")
assert not mh["thieu"] and not mh["lech"] and not mh["thua"], (
    f"TỔNG đã khớp -> KHÔNG cần khoanh vùng gì thêm — được {mh}")
print("PASS: hóa đơn khác kỳ (chỉ lọt qua vì SQL nới biên ±1 ngày) không còn bị cộng vào TỔNG MISA -> "
      "hết báo 'TỔNG LỆCH' oan kèm bảng khoanh vùng trống trơn.")

print("\nTẤT CẢ TEST PASS")
