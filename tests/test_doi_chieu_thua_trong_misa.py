import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: _misa_doi_chieu_import_toan_bo phải phát hiện được cả
chiều "MISA CÓ nhưng nguồn KHÔNG CÓ" (thừa) — trước đây vòng lặp khớp CHỈ
duyệt theo nguồn, kiểm tra từng hóa đơn nguồn có mặt trong MISA hay không,
nên KHÔNG BAO GIỜ phát hiện được trường hợp NGƯỢC LẠI: MISA có 1 hóa đơn mà
nguồn không hề có — khiến TỔNG vẫn lệch dù danh sách "thiếu"/"lệch" đã hoàn
toàn trống, không rõ nguyên nhân — đúng phản hồi người dùng: sau khi Mua
hàng hết báo thiếu/lệch, tổng vẫn lệch ~1 tỷ mà không biết vì sao.

Test cho cả Bán hàng (misa["sold"], cấu trúc list theo Ký hiệu) và Mua hàng
(misa["purchase"], cấu trúc phẳng)."""
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
    # Mua hàng: 1 hóa đơn nguồn duy nhất (khớp đúng với MISA) — MISA còn có
    # THÊM 1 hóa đơn khác (NCC khác) hoàn toàn không có trong nguồn.
    conn.execute("INSERT INTO invoices VALUES (1,'purchase','0317743519','0100000000','C1','9001',"
                 "'2026-08-14T08:00:00',1000000,80000,'1','{}',NULL)")
    # Bán hàng: 1 hóa đơn nguồn duy nhất (khớp đúng) — MISA còn THỪA 1 hóa
    # đơn khác (khách khác) không có trong nguồn.
    conn.execute("INSERT INTO invoices VALUES (1,'sold','0100000000','0200000001','K1','501',"
                 "'2026-08-14T08:00:00',500000,40000,'1','{}',NULL)")
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
            if table == "SAVoucher":
                return [("AccountObjectTaxCode", "nvarchar"), ("InvNo", "nvarchar"),
                        ("InvSeries", "nvarchar"), ("TotalAmount", "money"),
                        ("TotalVATAmount", "money"), ("RefDate", "datetime")]
            if table == "PUInvoice":
                return [("AccountObjectTaxCode", "nvarchar"), ("InvNo", "nvarchar"),
                        ("TotalTurnoverAmount", "money"), ("TotalVATAmount", "money"),
                        ("RefDate", "datetime")]
            return []
        import datetime
        if "FROM SAVoucher" in sql:
            # (mst, inv, kh, tot(gồm vat), vat, refdate)
            rows = [
                # tot = ds+thue (SAVoucher.TotalAmount gồm VAT) -> ds=500000,thue=40000 khớp đúng nguồn
                ("0200000001", "501", "K1", 540000, 40000, datetime.datetime(2026, 8, 14)),      # khớp đúng
                ("0300000099", "999", "K9", 5940000, 440000, datetime.datetime(2026, 8, 14)),    # THỪA, không có trong nguồn
            ]
            lo, hi = self.last_params[0], self.last_params[1]
            return [r[:6] for r in rows if lo <= r[5] <= hi]
        if "FROM PUInvoice" in sql:
            # TotalTurnoverAmount KHÔNG gồm VAT -> ds=1000000,thue=80000 khớp đúng nguồn
            rows = [
                ("0317743519", "9001", 1000000, 80000, datetime.datetime(2026, 8, 14)),   # khớp đúng
                ("0399999999", "8888", 2000000, 160000, datetime.datetime(2026, 8, 14)),  # THỪA, không có trong nguồn
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

bh, mh = kq["ban_hang"], kq["mua_hang"]
print("Bán hàng:", bh)
print("Mua hàng:", mh)

assert not bh["thieu"] and not bh["lech"], f"Hóa đơn 501 phải khớp đúng, không thiếu/lệch — được {bh}"
assert len(bh["thua"]) == 1 and bh["thua"][0]["so_hd"] == "999", (
    f"Phải phát hiện đúng 1 hóa đơn THỪA trong MISA (999, NCC khác) — được thua={bh.get('thua')}")
print("PASS (Bán hàng): phát hiện đúng hóa đơn THỪA trong MISA (999) dù không có trong nguồn — "
      "trước đây hoàn toàn không phát hiện được chiều này.")

assert not mh["thieu"] and not mh["lech"], f"Hóa đơn 9001 phải khớp đúng, không thiếu/lệch — được {mh}"
assert len(mh["thua"]) == 1 and mh["thua"][0]["so_hd"] == "8888", (
    f"Phải phát hiện đúng 1 hóa đơn THỪA trong MISA (8888) — được thua={mh.get('thua')}")
print("PASS (Mua hàng): phát hiện đúng hóa đơn THỪA trong MISA (8888) dù không có trong nguồn.")

print("\nTẤT CẢ TEST PASS")
