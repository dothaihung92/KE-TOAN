import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: hóa đơn Bán hàng cho khách lẻ mà dữ liệu tra cứu Thuế ghi
CCCD (12 số) vào "MST người mua" (thay vì để trống) KHÔNG được báo "THIẾU
trong MISA" nếu hóa đơn đó thật ra ĐÃ CÓ trong MISA dưới mã "KL" (Khách lẻ,
MST rỗng) — đúng ca thật người dùng báo cáo qua ảnh chụp màn hình MISA: hóa
đơn Số HĐ 6942, Ký hiệu C26MHH, 26.747đ, ngày 14/08/2026, Khách hàng "KL" —
ĐÃ CÓ trong MISA nhưng phần mềm báo "THIẾU trong MISA".

Root cause: _misa_ghi_khncc (ghi Danh mục KH/NCC) và bước xuất Excel Danh mục
NCC đã có sẵn quy ước "MST đúng 12 số toàn chữ số = CCCD, KHÔNG PHẢI MST thật"
(coi như trống) — nên _misa_ghi_ban_hang gộp các hóa đơn khách lẻ dạng này
vào chung mã "KL" (CompanyTaxCode=NULL). Nhưng _misa_doi_chieu_import_toan_bo
lại tính khóa so khớp TRỰC TIẾP từ invoices.nmmst (CHƯA áp quy ước này) —
nguồn tính khóa theo CCCD trong khi MISA lưu khóa rỗng -> lệch khóa -> báo
nhầm "THIẾU" dù hóa đơn đã có."""
import sys, sqlite3, datetime, tempfile, os
sys.path.insert(0, _REPO_ROOT)
import server

DB_FILE = tempfile.mktemp(suffix=".sqlite3")
CCCD_NGUOI_MUA = "079099001234"   # 12 số toàn chữ số -> CCCD, không phải MST


def setup_nguon():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""CREATE TABLE IF NOT EXISTS invoices (
        company_id INTEGER, loai TEXT, nbmst TEXT, nmmst TEXT, khhdon TEXT, shdon TEXT,
        tdlap TEXT, tgtcthue REAL, tgtthue REAL, tthai TEXT, raw TEXT, detail_json TEXT)""")
    conn.execute("""CREATE TABLE companies (
        id INTEGER PRIMARY KEY, save_dir TEXT)""")
    conn.execute("INSERT INTO companies VALUES (1, '')")
    conn.execute("DELETE FROM invoices")
    # Đúng hệt ca thật: HĐ 6942, ký hiệu C26MHH, 26.747đ (chưa gồm/đã gồm thuế
    # tùy quy ước — test này chỉ tập trung vào khóa MST/Số HĐ, số tiền đặt
    # trùng khớp cả 2 bên để không lẫn với nhánh "lệch" số tiền).
    conn.execute("INSERT INTO invoices VALUES (1,'sold','0100000000',?,'C26MHH','6942',"
                 "'2026-08-14T10:00:00',24297,2450,'1','{}',NULL)", (CCCD_NGUOI_MUA,))
    # Hóa đơn PHỤ, số tiền CỐ Ý không khớp gì với MISA -> ép tong_khop=False,
    # để nhánh khớp TỪNG hóa đơn (nơi có lỗi CCCD) thật sự chạy thay vì tắt
    # sớm qua đường tổng-đã-khớp (nếu chỉ có 1 hóa đơn khớp tuyệt đối như
    # trên, tong_khop=True làm nhánh lỗi không bao giờ được thực thi).
    conn.execute("INSERT INTO invoices VALUES (1,'sold','0100000000','0200000099','01','7001',"
                 "'2026-08-15T10:00:00',999999,99999,'1','{}',NULL)")
    conn.commit()
    conn.close()


def db_factory():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


class FakeCursor:
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
            if table == "SAVoucher":
                return [("AccountObjectTaxCode", "nvarchar"), ("InvNo", "nvarchar"),
                        ("InvSeries", "nvarchar"), ("TotalAmount", "money"),
                        ("TotalVATAmount", "money"), ("RefDate", "datetime")]
            return []
        if "FROM SAVoucher" in sql:
            # Đúng như MISA THẬT lưu: khách lẻ -> AccountObjectTaxCode = NULL
            # (mã "KL"), Ký hiệu HĐ = "C26MHH", Số HĐ = "6942" y hệt nguồn.
            rows = [(None, "6942", "C26MHH", 26747, 2450, datetime.datetime(2026, 8, 14))]
            if len(self.last_params) >= 2:
                lo, hi = self.last_params[0], self.last_params[1]
                rows = [r for r in rows if lo <= r[5] <= hi]
            return [r[:6] for r in rows]
        return []

    def fetchone(self):
        rows = self.fetchall()
        return rows[0] if rows else None


class FakeConn:
    def __init__(self):
        self._cur = FakeCursor()

    def cursor(self):
        return self._cur

    def close(self):
        pass


setup_nguon()
orig_db, orig_connect = server.db, server._misa_sql_connect
server.db = db_factory
server._misa_sql_connect = lambda cid, database=None: FakeConn()
try:
    kq = server._misa_doi_chieu_import_toan_bo(1, "TESTDB")
finally:
    server.db = orig_db
    server._misa_sql_connect = orig_connect
    os.remove(DB_FILE)

print("Kết quả Bán hàng:", kq["ban_hang"])

assert kq["ban_hang"]["tong_khop"] is False, (
    "Test phải ép tong_khop=False (nhờ hóa đơn phụ 7001 không khớp gì) để nhánh "
    "khớp từng hóa đơn thật sự chạy — nếu không nhánh có lỗi CCCD không được thực thi.")
thieu = kq["ban_hang"]["thieu"]
assert any(x["so_hd"] == "7001" for x in thieu), (
    f"Hóa đơn phụ 7001 (cố ý không có trong MISA) phải bị báo THIẾU đúng — "
    f"nếu không test tự nó có vấn đề. thieu={thieu}")
assert not any(x["so_hd"] == "6942" for x in thieu), (
    f"Hóa đơn 6942 (khách lẻ, nguồn ghi CCCD vào MST) ĐÃ CÓ trong MISA (mã KL) "
    f"nhưng vẫn bị báo THIẾU -> lỗi CHƯA được sửa. thieu={thieu}")
print("PASS: hóa đơn khách lẻ có CCCD trong MST nguồn KHÔNG còn bị báo nhầm "
      "'THIẾU trong MISA' khi đã có sẵn dưới mã 'KL' (MST rỗng) trên MISA.")

print("\nTẤT CẢ TEST PASS")
