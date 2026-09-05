import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: đúng ca thật người dùng báo cáo (5/9/2026) — người dùng
tự kiểm tra TỔNG trên chính màn hình "Mua hàng hóa, dịch vụ" của MISA (kỳ 6
tháng cuối năm, xuất Excel kèm theo) ra ĐÚNG 429.697.670đ/7.302.848đ thuế
(khớp với "nguồn"), nhưng bảng đối chiếu của phần mềm vẫn báo "⚠ Mua hàng —
TỔNG LỆCH" với tổng MISA 439.697.670đ/8.102.848đ — CAO HƠN đúng 10.000.000đ
+ 800.000đ (= VAT 8% của 10.000.000đ) — dù khớp từng hóa đơn báo "0/115 hóa
đơn thiếu/lệch". Vẫn còn LỆCH y hệt sau lần fix ĐẦU (chỉ lọc PUInvoice) —
xác nhận rác nằm ở CẢ 2 phía có thể xảy ra (nk/kqk qua PUInvoice VÀ dv qua
PUServiceDetail), nên phải lọc CẢ HAI, dùng CHUNG 1 view.

Nguyên nhân: câu SELECT dựng tổng MISA (misa["purchase"]) từ PUInvoice
(nk/kqk) VÀ PUServiceDetail (dv) trong _misa_doi_chieu_import_toan_bo lấy
TẤT CẢ các dòng khớp khung ngày, KHÔNG kiểm tra chứng từ Mua hàng liên kết
có THẬT SỰ "hiện rõ trên MISA" hay không — đúng bộ lọc màn hình MISA dùng
(PostedDate + BranchID + DisplayOnBook, qua View_PUVoucherService — CHÍNH
view MISA dùng cho màn hình "Mua hàng hóa, dịch vụ", bắt được từ câu lệnh
MISA thực thi, xem _misa_tu_kiem_tra_muahang/_hd_da_co_hien_ro). Một bản ghi
CŨ bị ẩn/lỗi (tồn đọng từ lần ghi trước bị lỗi giữa chừng, KHÔNG hiện trên
màn hình Mua hàng MISA nên người dùng không thấy) vẫn bị CỘNG DỒN vào tổng
MISA ở đây (trùng khóa MST+Số HĐ với 1 hóa đơn ĐÃ khớp đúng khác) — khiến
báo TỔNG LỆCH oan dù MISA thật (theo màn hình) đã khớp đúng nguồn.

Fix: thêm điều kiện EXISTS (...JOIN View_PUVoucherService..., PostedDate IS
NOT NULL + đúng BranchID + DisplayOnBook IN (0,2)) vào CẢ 2 câu SELECT
PUInvoice VÀ PUServiceDetail — CHỈ tính các dòng thật sự hiện rõ trên MISA."""
import sys, sqlite3
sys.path.insert(0, _REPO_ROOT)
import server


def db_factory(mst, so_hd, tong, thue):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE invoices (
        company_id INTEGER, loai TEXT, nbmst TEXT, nmmst TEXT, khhdon TEXT, shdon TEXT,
        tdlap TEXT, tgtcthue REAL, tgtthue REAL, tthai TEXT, raw TEXT, detail_json TEXT)""")
    conn.execute("""CREATE TABLE companies (
        id INTEGER PRIMARY KEY, save_dir TEXT)""")
    conn.execute("INSERT INTO companies VALUES (1, '')")
    conn.execute(
        "INSERT INTO invoices VALUES (1,'purchase',?,'0100000000','1',?,"
        "'2026-07-15T10:00:00',?,?,'1','{}',NULL)", (mst, so_hd, tong, thue))
    conn.commit()
    return conn


def chay_test(ten, bang_lech, mst, so_hd, dong_that, dong_rac_an):
    """bang_lech: 'PUInvoice' (nk/kqk) hoặc 'PUServiceDetail' (dv) — bảng nào
    có dòng RÁC ẩn/lỗi cần bị lọc bỏ khỏi tổng MISA."""

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
                if table == bang_lech == "PUInvoice":
                    return [("AccountObjectTaxCode", "nvarchar"), ("InvNo", "nvarchar"),
                            ("TotalTurnoverAmount", "money"), ("TotalVATAmount", "money")]
                if table == bang_lech == "PUServiceDetail":
                    return [("TaxAccountObjectTaxCode", "nvarchar"), ("InvNo", "nvarchar"),
                            ("Amount", "money"), ("VATAmount", "money")]
                return []
            if ("FROM %s WHERE" % bang_lech) in sql:
                if "EXISTS" in sql:
                    assert self.last_params == (1,), (
                        f"Lọc EXISTS phải truyền đúng branch_id -> tham số phải là (1,), "
                        f"được {self.last_params}")
                    return [dong_that]
                return [dong_that, dong_rac_an]
            return []

        def fetchone(self):
            if "FROM OrganizationUnit" in self.last_sql:
                return (1,)
            if "OBJECT_ID" in self.last_sql:
                return (12345,)   # giả lập View_PUVoucherService TỒN TẠI trong CSDL MISA
            return None

    class FakeConn:
        def __init__(self):
            self._cur = FakeCursor()

        def cursor(self):
            return self._cur

        def close(self):
            pass

    orig_db, orig_connect = server.db, server._misa_sql_connect
    server.db = lambda: db_factory(mst, so_hd, dong_that[2], dong_that[3])
    server._misa_sql_connect = lambda cid, database=None: FakeConn()
    try:
        kq = server._misa_doi_chieu_import_toan_bo(1, "TESTDB")
    finally:
        server.db = orig_db
        server._misa_sql_connect = orig_connect

    mh = kq["mua_hang"]
    print(f"[{ten}] Mua hàng:", mh)
    assert not mh["thieu"], f"[{ten}] Hóa đơn {so_hd} KHÔNG được báo thiếu — được thieu={mh.get('thieu')}"
    assert not mh["lech"], (
        f"[{ten}] Hóa đơn {so_hd} KHÔNG được báo LỆCH — dòng {bang_lech} RÁC (chứng từ liên kết bị ẩn/"
        f"lỗi, KHÔNG hiện trên màn hình Mua hàng MISA) phải bị LOẠI khỏi tổng MISA, chỉ tính dòng THẬT "
        f"hiện rõ — được lech={mh.get('lech')}")
    print(f"PASS [{ten}]: dòng {bang_lech} ẩn/lỗi (không hiện trên MISA) không còn bị cộng dồn vào tổng "
          f"MISA -> TỔNG LỆCH oan đã hết, khớp đúng nguồn.")


# ===== Test 1: rác nằm ở PUInvoice (Mua hàng Nhập kho/Không qua kho) =====
chay_test("nk/kqk (PUInvoice)", "PUInvoice", "0317009837", "1824",
          dong_that=("0317009837", "1824", 5000000, 400000),
          dong_rac_an=("0317009837", "1824", 10000000, 800000))

# ===== Test 2: rác nằm ở PUServiceDetail (Mua hàng Dịch vụ) — CHƯA từng có
# hien_ro nào ở nhánh này trước fix, đúng nghi vấn còn lệch sau lần fix đầu
# (chỉ lọc PUInvoice) không đủ giải quyết ca thật của người dùng. =====
chay_test("dv (PUServiceDetail)", "PUServiceDetail", "0317009837", "1824",
          dong_that=("0317009837", "1824", 5000000, 400000),
          dong_rac_an=("0317009837", "1824", 10000000, 800000))

print("\nTẤT CẢ TEST PASS")
