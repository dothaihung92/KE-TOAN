import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: _misa_doi_chieu_import_toan_bo phải LOẠI HẲN các hóa đơn
nguồn cộng dồn ra ĐÚNG 0đ (cả doanh số lẫn thuế) khỏi việc đối chiếu — không
được báo "THIẾU trong MISA" cho hóa đơn không có giá trị thật (thường là
hóa đơn điều chỉnh/khuyến mãi 0đ, không cần hạch toán trong MISA).

Đúng ca thật người dùng báo cáo: sau khi sửa lỗi "Số chứng từ" trùng nhầm
(PR trước), Mua hàng giảm từ 47/94 xuống còn 4/94 hóa đơn thiếu/lệch — nhưng
4 hóa đơn còn lại đều hiện Doanh số/Thuế GTGT = 0đ ở CẢ nguồn lẫn MISA, không
có gì để thiếu cả."""
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
    # Hóa đơn mua vào THẬT (có giá trị, KHÔNG có trong MISA -> phải báo thiếu đúng)
    conn.execute("INSERT INTO invoices VALUES (1,'purchase','0317743519','0100000000','C1','9001',"
                 "'2026-08-14T08:00:00',1000000,80000,'1','{}',NULL)")
    # Hóa đơn mua vào 0 ĐỒNG (điều chỉnh/khuyến mãi, KHÔNG có trong MISA -> KHÔNG được báo thiếu)
    conn.execute("INSERT INTO invoices VALUES (1,'purchase','0302056457','0100000000','C1','20530',"
                 "'2026-08-15T08:00:00',0,0,'1','{}',NULL)")
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
            table = self.last_params[0]
            if table == "PUInvoice":
                return [("AccountObjectTaxCode", "nvarchar"), ("InvNo", "nvarchar"),
                        ("TotalTurnoverAmount", "money"), ("TotalVATAmount", "money"),
                        ("RefDate", "datetime")]
            return []
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

assert mh["tong_hd_nguon"] == 1, f"Hóa đơn 0đ (20530) phải bị loại khỏi tổng số hóa đơn nguồn, được tong_hd_nguon={mh['tong_hd_nguon']}"
assert any(x["so_hd"] == "9001" for x in mh["thieu"]), f"Hóa đơn thật (9001) phải vẫn báo thiếu đúng, được {mh['thieu']}"
assert not any(x["so_hd"] == "20530" for x in mh["thieu"]), (
    f"Hóa đơn 0đ (20530) KHÔNG được báo 'THIẾU trong MISA' — không có gì để thiếu, được {mh['thieu']}")
assert len(mh["thieu"]) == 1, f"Chỉ được báo thiếu đúng 1 hóa đơn (9001), được {mh['thieu']}"
print("PASS: hóa đơn 0đ (20530) bị loại hẳn khỏi đối chiếu (không tính vào tổng, không báo thiếu), "
      "hóa đơn thật (9001) vẫn báo thiếu đúng bình thường.")

print("\nTẤT CẢ TEST PASS")
