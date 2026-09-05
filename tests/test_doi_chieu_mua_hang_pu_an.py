import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: đúng ca thật người dùng báo cáo (5/9/2026) — người dùng
tự kiểm tra TỔNG trên chính màn hình "Mua hàng hóa, dịch vụ" của MISA (kỳ 6
tháng cuối năm) ra ĐÚNG 429.697.670đ (khớp với "nguồn"), nhưng bảng đối
chiếu của phần mềm vẫn báo "⚠ Mua hàng — TỔNG LỆCH" với tổng MISA
439.697.670đ/8.102.848đ thuế — CAO HƠN đúng 10.000.000đ + 800.000đ (= VAT
8% của 10.000.000đ) — dù khớp từng hóa đơn báo "0/115 hóa đơn thiếu/lệch".

Nguyên nhân: câu SELECT dựng tổng MISA (misa["purchase"]) từ bảng PUInvoice
trong _misa_doi_chieu_import_toan_bo lấy TẤT CẢ các dòng PUInvoice khớp
khung ngày, KHÔNG kiểm tra chứng từ Mua hàng (PUVoucher) liên kết có THẬT
SỰ "hiện rõ trên MISA" hay không (PostedDate/BranchID/DisplayOnBook — xem
_hd_da_co_hien_ro, dùng khi ghi/ghi đè). Một bản ghi PUInvoice CŨ bị ẩn/lỗi
(tồn đọng từ lần ghi trước bị lỗi giữa chừng, KHÔNG hiện trên màn hình Mua
hàng MISA nên người dùng không thấy) vẫn bị CỘNG DỒN vào tổng MISA ở đây
(trùng khóa MST+Số HĐ với 1 hóa đơn ĐÃ khớp đúng khác) — khiến báo TỔNG
LỆCH oan dù MISA thật (theo màn hình) đã khớp đúng nguồn.

Fix: thêm điều kiện EXISTS (PUInvoiceDetail JOIN PUVoucher, PostedDate IS
NOT NULL + đúng BranchID + DisplayOnBook IN (0,2)) vào câu SELECT PUInvoice
— CHỈ tính các dòng thật sự hiện rõ trên MISA, y hệt _hd_da_co_hien_ro."""
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
    # 1 hóa đơn nguồn duy nhất, NCC 0317009837, Số HĐ 1824 — ĐÚNG khớp với
    # dòng PUInvoice "hiện rõ" ở MISA (5.000.000/400.000).
    conn.execute(
        "INSERT INTO invoices VALUES (1,'purchase','0317009837','0100000000','1','1824',"
        "'2026-07-15T10:00:00',5000000,400000,'1','{}',NULL)")
    conn.commit()
    return conn


class FakeCursor:
    """Giả lập CSDL MISA: bảng PUInvoice có 2 dòng CÙNG khóa (MST+Số HĐ) —
    1 dòng THẬT hiện rõ trên MISA (5tr/400k, khớp đúng nguồn) + 1 dòng RÁC
    tồn đọng do PUVoucher liên kết bị ẩn/lỗi (10tr/800k, đúng số tiền lệch
    người dùng báo cáo). Câu SELECT PUInvoice PHẢI lọc theo EXISTS(...) để
    chỉ lấy dòng hiện rõ — nếu không lọc (code lỗi cũ) sẽ cộng dồn CẢ 2."""

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
                        ("TotalTurnoverAmount", "money"), ("TotalVATAmount", "money")]
            return []
        if "FROM PUInvoice WHERE" in sql:
            dong_that = ("0317009837", "1824", 5000000, 400000)
            dong_rac_an = ("0317009837", "1824", 10000000, 800000)
            if "EXISTS" in sql:
                assert self.last_params == (1,), (
                    f"Lọc EXISTS phải truyền đúng branch_id -> tham số phải là (1,), được {self.last_params}")
                return [dong_that]
            return [dong_that, dong_rac_an]
        return []

    def fetchone(self):
        if "FROM OrganizationUnit" in self.last_sql:
            return (1,)
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

assert not mh["thieu"], f"Hóa đơn 1824 KHÔNG được báo thiếu — được thieu={mh.get('thieu')}"
assert not mh["lech"], (
    "Hóa đơn 1824 KHÔNG được báo LỆCH — dòng PUInvoice RÁC (10tr/800k, PUVoucher liên kết bị ẩn/lỗi, "
    "KHÔNG hiện trên màn hình Mua hàng MISA) phải bị LOẠI khỏi tổng MISA, chỉ tính dòng THẬT hiện rõ "
    f"(5tr/400k, khớp đúng nguồn) — được lech={mh.get('lech')}")
print("PASS: dòng PUInvoice ẩn/lỗi (không hiện trên MISA) không còn bị cộng dồn vào tổng MISA -> "
      "TỔNG LỆCH oan đã hết, khớp đúng nguồn.")

print("\nTẤT CẢ TEST PASS")
