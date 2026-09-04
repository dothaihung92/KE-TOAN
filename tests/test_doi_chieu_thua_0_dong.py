import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: hóa đơn "THỪA trong MISA" cộng dồn ra ĐÚNG 0đ (cả doanh
số lẫn thuế) phải bị loại khỏi báo cáo — đối xứng với việc đã loại hóa đơn
NGUỒN 0đ khỏi báo "THIẾU" (PR trước) — đúng ca thật người dùng báo cáo: hóa
đơn MST 0302056457/Số HĐ 19987 báo "THỪA trong MISA" nhưng Doanh số/Thuế
GTGT đều = 0đ, không có gì để thừa cả."""
import sys, sqlite3, datetime
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
    conn.execute("INSERT INTO invoices VALUES (1,'purchase','0317743519','0100000000','C1','9001',"
                 "'2026-08-14T08:00:00',1000000,80000,'1','{}',NULL)")
    # Hóa đơn PHỤ, cố ý không có trong MISA -> ép tong_khop=False, để nhánh
    # khớp từng hóa đơn (nơi có bộ lọc 0đ đang test) thật sự chạy thay vì
    # tắt sớm qua đường tổng-đã-khớp.
    conn.execute("INSERT INTO invoices VALUES (1,'purchase','0399999999','0100000000','C1','7777',"
                 "'2026-08-14T08:00:00',999999,99999,'1','{}',NULL)")
    conn.commit()
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
            if self.last_params[0] == "PUInvoice":
                return [("AccountObjectTaxCode", "nvarchar"), ("InvNo", "nvarchar"),
                        ("TotalTurnoverAmount", "money"), ("TotalVATAmount", "money"),
                        ("RefDate", "datetime")]
            return []
        if "FROM PUInvoice" in sql:
            rows = [
                ("0317743519", "9001", 1000000, 80000, datetime.datetime(2026, 8, 14)),  # khớp đúng
                ("0302056457", "19987", 0, 0, datetime.datetime(2026, 8, 14)),            # THỪA nhưng 0đ
            ]
            lo, hi = self.last_params[0], self.last_params[1]
            return [r[:5] for r in rows if lo <= r[4] <= hi]
        return []

    def fetchone(self):
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
print("Kết quả Mua hàng:", mh)

assert mh["tong_khop"] is False, "Test phải ép tong_khop=False để nhánh khớp từng hóa đơn thật sự chạy"
assert not any(x["so_hd"] == "19987" for x in mh["thua"]), (
    f"Hóa đơn MISA 0đ (19987) không được báo 'thừa' — không có gì để thừa, được {mh['thua']}")
print("PASS: hóa đơn MISA cộng dồn ra 0đ không còn bị báo 'THỪA trong MISA'.")

print("\nTẤT CẢ TEST PASS")
