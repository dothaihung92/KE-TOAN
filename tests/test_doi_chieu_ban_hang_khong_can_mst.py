import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: khóa ghép hóa đơn Bán hàng KHÔNG còn cần MST người mua
trùng khớp — chỉ cần (Ký hiệu, Số hóa đơn), vì Số hóa đơn đã duy nhất trong
phạm vi 1 Ký hiệu theo quy định hóa đơn điện tử.

Đúng ca thật người dùng gửi Bảng kê Bán hàng từ MISA: 1.403/2.461 hóa đơn là
khách lẻ "KL" — MST người mua ghi trên MISA (AccountObjectTaxCode của danh
mục Khách hàng) KHÔNG NHẤT QUÁN: có dòng để trống, có dòng lưu nguyên CCCD —
trong khi nguồn (tra cứu Thuế) LUÔN có MST/CCCD người mua trên từng hóa đơn,
và mã CCCD đã bị "làm trống" theo quy ước sẵn có (coi 12 số là không phải MST
thật). Nếu khóa ghép còn dựa vào MST, các trường hợp MISA KHÔNG để trống CCCD
(khác với giả định "KL luôn trống MST") sẽ bị coi khác nhóm, báo sai cả
"thiếu" (nguồn) lẫn "thừa" (MISA) cho CÙNG 1 hóa đơn thật.

Test mô phỏng đúng: 1 hóa đơn khách lẻ (CCCD 12 số trong nguồn, MST_K bị làm
trống) nhưng phía MISA dòng SAVoucher tương ứng lại lưu MST# một giá trị
KHÁC RỖNG (không phải CCCD y hệt, không phải rỗng) — khóa theo MST chắc chắn
lệch dù là CÙNG 1 hóa đơn (trùng Ký hiệu + Số hóa đơn)."""
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
    # Hóa đơn công ty bình thường -> khớp trực tiếp, không liên quan bug.
    conn.execute("INSERT INTO invoices VALUES (1,'sold','0100000000','0317743519','C26MHH','8489',"
                 "'2026-08-31T08:00:00',24049332,1923948,'1','{}',NULL)")
    # Hóa đơn khách lẻ: MST người mua trên hóa đơn ghi CCCD (12 số) -> mst_k
    # bị làm trống theo quy ước CCCD đã có sẵn.
    conn.execute("INSERT INTO invoices VALUES (1,'sold','0100000000','012345678912','C26MHH','8488',"
                 "'2026-08-31T08:00:00',4463191,357055,'1','{}',NULL)")
    # Hóa đơn PHỤ, cố ý không có trong MISA -> ép tong_khop=False, để nhánh
    # khớp từng hóa đơn (nơi có bộ lọc khóa đang test) thật sự chạy thay vì
    # tắt sớm qua đường tổng-đã-khớp.
    conn.execute("INSERT INTO invoices VALUES (1,'sold','0100000000','0399999999','C26MHH','9999',"
                 "'2026-08-31T08:00:00',999999,99999,'1','{}',NULL)")
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
            if self.last_params[0] == "SAVoucher":
                return [("AccountObjectTaxCode", "nvarchar"), ("InvNo", "nvarchar"),
                        ("InvSeries", "nvarchar"), ("TotalAmount", "money"),
                        ("TotalVATAmount", "money"), ("RefDate", "datetime")]
            return []
        if "FROM SAVoucher" in sql:
            rows = [
                ("0317743519", "8489", "C26MHH", 25973280, 1923948, datetime.datetime(2026, 8, 31)),
                # CÙNG hóa đơn khách lẻ 8488, nhưng MISA KHÔNG để trống MST —
                # lưu 1 giá trị khác rỗng, khác hẳn CCCD gốc trên hóa đơn.
                ("079099001234", "8488", "C26MHH", 4820246, 357055, datetime.datetime(2026, 8, 31)),
            ]
            lo, hi = self.last_params[0], self.last_params[1]
            return [r[:6] for r in rows if lo <= r[5] <= hi]
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

bh = kq["ban_hang"]
print("Kết quả Bán hàng:", bh)

assert bh["tong_khop"] is False, "Test phải ép tong_khop=False để nhánh khớp từng hóa đơn thật sự chạy"
so_hd_thieu = [x["so_hd"] for x in bh["thieu"]]
so_hd_thua = [x["so_hd"] for x in bh["thua"]]
assert "8489" not in so_hd_thieu and "8488" not in so_hd_thieu, (
    f"Hóa đơn 8488 (khách lẻ, MISA không để trống MST) PHẢI khớp qua (Ký hiệu, Số hóa đơn), "
    f"không được báo 'thiếu' — được thieu={bh['thieu']}")
assert "8489" not in so_hd_thua and "8488" not in so_hd_thua, (
    f"Hóa đơn 8488/8489 không được báo 'thừa' — được thua={bh['thua']}")
assert so_hd_thieu == ["9999"], f"Chỉ hóa đơn phụ 9999 (thật sự không có trong MISA) được báo 'thiếu' — được {bh['thieu']}"
print("PASS: hóa đơn khách lẻ khớp đúng theo (Ký hiệu, Số hóa đơn) dù MST ghi khác nhau giữa 2 hệ thống.")

print("\nTẤT CẢ TEST PASS")
