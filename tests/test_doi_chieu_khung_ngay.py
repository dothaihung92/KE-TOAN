import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: _misa_doi_chieu_import_toan_bo (server.py) phải LỌC phía
MISA theo khung ngày của CHÍNH dữ liệu nguồn trước khi so tổng/khớp từng hóa
đơn — theo đúng phản hồi người dùng: "đối chiếu bán ra thì phần mềm đang đối
chiếu dữ liệu misa toàn bộ thời gian còn phần mềm chỉ import tháng 8/2026
thôi". Trước khi sửa, hàm đọc TOÀN BỘ SAVoucher/PUInvoice/PUServiceDetail của
MISA (không lọc ngày) — công ty đã dùng MISA từ trước (dữ liệu cũ 2023) khiến
tổng MISA luôn cao vọt so với nguồn (chỉ có tháng 8/2026), dù phần MỚI import
đã ghi đủ và khớp 100%.

Test bằng cách gọi THẲNG hàm thật trong server.py: nguồn (sqlite invoices, 2
hóa đơn bán ra tháng 8/2026) khớp CHÍNH XÁC với 2 dòng SAVoucher "mới" phía
MISA (cùng MST/Số HĐ/số tiền) — NHƯNG cursor giả còn có sẵn 1 dòng SAVoucher
"cũ" (2023, MST/Số HĐ hoàn toàn khác, không có trong nguồn) mô phỏng dữ liệu
MISA có từ trước. Cursor giả tự áp dụng lọc ngày y hệt SQL Server thật sẽ làm
(chỉ trả về dòng khớp điều kiện WHERE ngày nếu code có truyền tham số lọc) —
nên nếu code KHÔNG truyền tham số lọc (bug cũ), dòng "cũ" vẫn lọt vào, làm
tổng MISA vượt xa tổng nguồn -> tong_khop=False dù thực ra khớp đủ."""
import sys, sqlite3, datetime, tempfile, os
sys.path.insert(0, _REPO_ROOT)
import server

DB_FILE = tempfile.mktemp(suffix=".sqlite3")


def setup_nguon():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""CREATE TABLE IF NOT EXISTS invoices (
        company_id INTEGER, loai TEXT, nbmst TEXT, nmmst TEXT, khhdon TEXT, shdon TEXT,
        tdlap TEXT, tgtcthue REAL, tgtthue REAL, tthai TEXT, raw TEXT, detail_json TEXT)""")
    conn.execute("""CREATE TABLE companies (
        id INTEGER PRIMARY KEY, save_dir TEXT)""")
    conn.execute("INSERT INTO companies VALUES (1, '')")
    conn.execute("DELETE FROM invoices")
    conn.execute("INSERT INTO invoices VALUES (1,'sold','0100000000','0200000001','01','100',"
                 "'2026-08-14T10:00:00',1000000,100000,'1','{}',NULL)")
    conn.execute("INSERT INTO invoices VALUES (1,'sold','0100000000','0200000002','01','101',"
                 "'2026-08-20T10:00:00',2000000,200000,'1','{}',NULL)")
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
        self.co_loc_ngay = {"SAVoucher": None, "PUInvoice": None, "PUServiceDetail": None}

    def execute(self, sql, params=()):
        self.last_sql = sql
        self.last_params = tuple(params) if isinstance(params, (tuple, list)) else (params,)
        return self

    def _sa_rows(self):
        # (mst, inv, kh, tot(gồm vat), vat, refdate)
        rows = [
            ("0200000001", "100", "01", 1100000, 100000, datetime.datetime(2026, 8, 14)),
            ("0200000002", "101", "01", 2200000, 200000, datetime.datetime(2026, 8, 20)),
            # Dữ liệu CŨ, không liên quan gì tới nguồn (2023) -> PHẢI bị loại nếu lọc ngày đúng.
            ("0300000099", "999", "01", 50000000, 5000000, datetime.datetime(2023, 1, 10)),
        ]
        if len(self.last_params) >= 2:
            self.co_loc_ngay["SAVoucher"] = True
            lo, hi = self.last_params[0], self.last_params[1]
            rows = [r for r in rows if lo <= r[5] <= hi]
        else:
            self.co_loc_ngay["SAVoucher"] = False
        return [r[:6] for r in rows]

    def fetchall(self):
        sql = self.last_sql
        if "FROM sys.columns" in sql:
            table = self.last_params[0]
            cols = {
                "SAVoucher": [("AccountObjectTaxCode", "nvarchar"), ("InvNo", "nvarchar"),
                              ("InvSeries", "nvarchar"), ("TotalAmount", "money"),
                              ("TotalVATAmount", "money"), ("RefDate", "datetime")],
                "PUInvoice": [], "PUServiceDetail": [],
            }
            return cols.get(table, [])
        if "FROM SAVoucher" in sql:
            return self._sa_rows()
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
fake_conn = FakeConn()
server._misa_sql_connect = lambda cid, database=None: fake_conn
try:
    kq = server._misa_doi_chieu_import_toan_bo(1, "TESTDB")
finally:
    server.db = orig_db
    server._misa_sql_connect = orig_connect
    os.remove(DB_FILE)

print("Kết quả Bán hàng:", {k: v for k, v in kq["ban_hang"].items() if k not in ("thieu", "lech")})

assert fake_conn.cursor().co_loc_ngay["SAVoucher"] is True, (
    "Truy vấn SAVoucher PHẢI truyền tham số lọc ngày (2 tham số RefDate>=?/<=?) — "
    "hiện KHÔNG lọc, đúng bug cũ (đọc toàn bộ lịch sử MISA).")
print("PASS: truy vấn SAVoucher có truyền tham số lọc theo khung ngày của nguồn.")

bh = kq["ban_hang"]
assert bh["tong_ds_misa"] == 3000000, f"Tổng doanh số MISA phải CHỈ gồm 2 dòng mới (1tr+2tr=3tr), KHÔNG cộng dòng cũ 50tr -> được {bh['tong_ds_misa']}"
assert bh["tong_thue_misa"] == 300000, f"Tổng thuế MISA phải CHỈ gồm 2 dòng mới (100k+200k=300k) -> được {bh['tong_thue_misa']}"
assert bh["tong_khop"] is True, (
    f"Tổng nguồn (3tr/300k) và tổng MISA (đã lọc, 3tr/300k) phải KHỚP — dữ liệu cũ 2023 không "
    f"được lẫn vào mới đúng, được tong_khop={bh['tong_khop']}, tong_ds_misa={bh['tong_ds_misa']}")
print("PASS: tổng doanh số/thuế MISA sau khi lọc CHỈ gồm dữ liệu trong khung ngày nguồn (3tr/300k), "
      "không còn bị dữ liệu cũ 2023 (50tr/5tr) làm phồng lên -> tong_khop=True đúng thực tế.")

print("\nTẤT CẢ TEST PASS")
