import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: khi bảng "invoices" (nguồn) KHÔNG CÓ hóa đơn nào cho 1
loại (Bán hàng hoặc Mua hàng) — chưa từng tra cứu/chưa lưu Bảng kê cho loại
đó — _misa_doi_chieu_import_toan_bo KHÔNG được báo "TỔNG LỆCH" kèm hàng loạt
hóa đơn "THỪA trong MISA" (chính là TOÀN BỘ lịch sử MISA không lọc được
theo khung ngày vì nguồn không có mốc ngày nào cả) — phải coi là "không có
gì để đối chiếu" (tong_khop=True), không phải "lệch".

Đúng ca thật người dùng báo cáo: "dữ liệu import quý 2/2026 đã khớp hết
nhưng phần mềm đối chiếu vẫn báo lệch" — ảnh chụp cho thấy Mua hàng "Tổng
doanh số: nguồn 0đ / MISA 5.188.002.742đ" báo "TỔNG LỆCH (0/0 hóa đơn
thiếu/lệch + 934 hóa đơn thừa trong MISA)" với ngày trải dài 2023-2025,
hoàn toàn không liên quan gì tới đợt đang làm việc — chỉ vì MISA có sẵn
dữ liệu mua hàng cũ từ trước, không phải lỗi thật."""
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
    # CHỈ có hóa đơn "sold" (Bán hàng) — hoàn toàn KHÔNG có hóa đơn "purchase"
    # nào trong bảng invoices (chưa từng tra cứu Mua vào cho công ty này).
    conn.execute("INSERT INTO invoices VALUES (1,'sold','0100000000','0200000001','C1','501',"
                 "'2026-04-14T08:00:00',500000,40000,'1','{}',NULL)")
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
            if self.last_params[0] == "PUInvoice":
                return [("AccountObjectTaxCode", "nvarchar"), ("InvNo", "nvarchar"),
                        ("TotalTurnoverAmount", "money"), ("TotalVATAmount", "money"),
                        ("RefDate", "datetime")]
            return []
        if "FROM SAVoucher" in sql:
            # Bán hàng: nguồn CÓ 1 hóa đơn (501), khớp đúng với MISA -> không
            # phải case đang test (chỉ để đối chứng không đổi hành vi bình thường).
            rows = [("0200000001", "501", "C1", 540000, 40000, datetime.datetime(2026, 4, 14))]
            # KHÔNG lọc theo tham số vì nguồn "sold" CÓ mốc ngày thật (khung
            # ngày hoạt động bình thường) — mô phỏng giống thật.
            return [r[:6] for r in rows]
        if "FROM PUInvoice" in sql:
            # Mua hàng: MISA có RẤT NHIỀU dữ liệu mua hàng CŨ (2023-2025),
            # không liên quan gì — nguồn "purchase" HOÀN TOÀN RỖNG nên
            # _khung_ngay("purchase") trả (None,None), KHÔNG lọc được theo
            # ngày -> câu SQL thật sẽ KHÔNG có điều kiện AND ngày (tham số
            # rỗng) -> trả về TOÀN BỘ, đúng mô phỏng lỗi thật.
            rows = [
                ("0102721191001", "1966", 836850, 66940, datetime.datetime(2024, 1, 1)),
                ("3603192392", "5", 9920000, 992000, datetime.datetime(2023, 4, 1)),
                ("3702645727", "5", 16400000, 1640000, datetime.datetime(2023, 4, 1)),
            ]
            return [r[:5] for r in rows]
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

# Bán hàng: nguồn CÓ dữ liệu, khớp đúng -> hành vi bình thường không đổi.
assert bh["tong_khop"] is True and not bh["thieu"] and not bh["lech"] and not bh["thua"]
print("PASS (đối chứng): Bán hàng có nguồn thật, khớp đúng — không đổi hành vi bình thường.")

# Mua hàng: nguồn RỖNG (0 hóa đơn) dù MISA có sẵn 934-kiểu dữ liệu cũ ->
# PHẢI coi là "không có gì để đối chiếu" (tong_khop=True), KHÔNG được báo
# "TỔNG LỆCH" kèm cả loạt "THỪA trong MISA" là dữ liệu cũ không liên quan.
assert mh["tong_hd_nguon"] == 0, f"Nguồn Mua hàng phải rỗng (0 hóa đơn) — được {mh['tong_hd_nguon']}"
assert mh["tong_khop"] is True, (
    f"Nguồn RỖNG (chưa tra cứu Mua vào) phải coi là 'không có gì để đối chiếu' (tong_khop=True), "
    f"KHÔNG được báo TỔNG LỆCH — được {mh}")
assert not mh["thieu"] and not mh["lech"] and not mh["thua"], (
    f"KHÔNG được báo bất kỳ hóa đơn THỪA nào (đó là TOÀN BỘ dữ liệu MISA cũ, không liên quan gì tới "
    f"đợt đang làm việc vì nguồn không có mốc ngày nào để lọc) — được thua={mh['thua']}")
print("PASS: nguồn Mua hàng RỖNG (chưa tra cứu) không còn báo 'TỔNG LỆCH' giả kèm hàng loạt hóa đơn "
      "'THỪA trong MISA' là dữ liệu cũ không liên quan (đúng lỗi thật người dùng báo cáo).")

print("\nTẤT CẢ TEST PASS")
