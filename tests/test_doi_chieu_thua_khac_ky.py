import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: hóa đơn "THỪA trong MISA" chỉ được báo khi NẰM TRONG kỳ
đang đối chiếu (khung ngày SÁT, không nới) — dòng MISA rơi vào phần NỚI THÊM
1 ngày mỗi đầu (chỉ dùng để KHỚP hóa đơn nguồn sát biên, không phải để BÁO
THỪA) không được liệt vào "thừa" — đúng phản hồi người dùng: "hãy chỉnh lại
những hoá đơn thừa này khác kỳ import — kỳ đang import là tháng 8/2026,
những hoá đơn này không nằm trong tháng 8/2026" (dò ra là do phần nới biên
±1 ngày kéo vào record của kỳ khác)."""
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
    # Nguồn CHỈ có đúng 1 hóa đơn, ngày 14/08/2026 -> khung SÁT = [14/08,14/08],
    # khung NỚI (dùng để lấy MISA) = [13/08,15/08].
    conn.execute("INSERT INTO invoices VALUES (1,'purchase','0317743519','0100000000','C1','9001',"
                 "'2026-08-14T08:00:00',1000000,80000,'1','{}',NULL)")
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
        if "FROM PUInvoice" in sql:
            rows = [
                # khớp đúng nguồn (14/08)
                ("0317743519", "9001", 1000000, 80000, datetime.datetime(2026, 8, 14)),
                # NGOÀI khung SÁT (13/08) nhưng còn trong khung NỚI -> KHÔNG được báo "thừa"
                ("0399999999", "8001", 500000, 40000, datetime.datetime(2026, 8, 13)),
                # trong khung SÁT (14/08), không khớp gì -> PHẢI báo "thừa"
                ("0399999999", "8002", 700000, 56000, datetime.datetime(2026, 8, 14)),
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

so_hd_thua = [x["so_hd"] for x in mh["thua"]]
assert "8001" not in so_hd_thua, (
    f"Hóa đơn 8001 (13/08, chỉ lọt qua nhờ khung NỚI biên, khác kỳ tháng 8 đang xét theo khung SÁT) "
    f"KHÔNG được báo 'thừa' — được thua={mh['thua']}")
assert "8002" in so_hd_thua, (
    f"Hóa đơn 8002 (14/08, đúng trong kỳ, thật sự không khớp gì) PHẢI báo 'thừa' đúng — được thua={mh['thua']}")
assert len(mh["thua"]) == 1, f"Chỉ được báo đúng 1 hóa đơn thừa (8002), được {mh['thua']}"
print("PASS: hóa đơn chỉ lọt vào nhờ phần NỚI biên (khác kỳ thật) KHÔNG bị báo 'thừa' nữa; hóa đơn "
      "thật sự thừa TRONG kỳ vẫn báo đúng bình thường.")

print("\nTẤT CẢ TEST PASS")
