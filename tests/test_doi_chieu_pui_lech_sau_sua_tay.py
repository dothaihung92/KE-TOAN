import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: đúng ca thật người dùng báo lại — hóa đơn Số HĐ 22619
(MST 0108705693-008) có dòng "Phí kéo lầu bồn" bị người dùng TỰ TAY cộng
dồn nhầm vào tiền hàng rồi quên xóa dòng phí (lỗi nhập liệu của người
dùng, không phải phần mềm — đã xác nhận qua so khớp với XML hóa đơn gốc)
khiến MISA ghi dư 120.000đ (5.648.148đ thay vì đúng 5.537.037đ).

Người dùng sau đó tự tay XÓA dòng "Phí kéo lầu bồn" thừa NGAY TRÊN MISA
UI (màn "Mua hàng hóa, dịch vụ" > Chi tiết) — "Tổng tiền hàng" trên màn
hình MISA đã hiện ĐÚNG 5.537.037đ (chỉ còn 1 dòng "Bồn Inox") — nhưng
"Đối chiếu tổng giá trị & VAT" của phần mềm VẪN báo LỆCH -120.000đ y hệt
như trước khi sửa.

Nguyên nhân: _misa_doi_chieu_import_toan_bo tính tổng MISA (mua hàng) từ
PUInvoice.TotalTurnoverAmount/TotalVATAmount — 2 cột LƯU SẴN (ghi 1 LẦN
lúc phần mềm này TẠO chứng từ, = tổng lúc ghi ban đầu 5.648.148/451.852),
KHÔNG được MISA tự tính lại nếu người dùng sau đó tự tay SỬA/XÓA dòng
"Chi tiết" (PUVoucherDetail) ngay trên MISA UI — nên dù Chi tiết đã đúng,
2 cột lưu sẵn này vẫn "đóng băng" ở số CŨ, khiến đối chiếu báo lệch oan.

Fix: tính thêm TỔNG THẬT theo PUVoucherDetail ĐANG liên kết (qua
PUInvoiceDetail.PUVoucherRefID) — nếu có VÀ khác số PUInvoice đang lưu
(>1đ), DÙNG số TỔNG THẬT này thay thế, phản ánh đúng "Chi tiết" người
dùng đang thấy trên MISA ngay lúc đối chiếu."""
import sys, sqlite3
sys.path.insert(0, _REPO_ROOT)
import server


def db_factory(mst, so_hd, tong_nguon, thue_nguon):
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
        "'2026-08-29T10:00:00',?,?,'1','{}',NULL)", (mst, so_hd, tong_nguon, thue_nguon))
    conn.commit()
    return conn


class FakeCursor:
    """PUInvoice vẫn lưu số CŨ (5.648.148/451.852, lúc ghi ban đầu — TRƯỚC
    khi người dùng tự xóa dòng phí thừa) — nhưng PUVoucherDetail ĐANG liên
    kết (qua PUInvoiceDetail) đã CHỈ CÒN 1 dòng ĐÚNG (5.537.037/442.963,
    sau khi người dùng tự sửa NGAY TRÊN MISA UI)."""
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
                return [("RefID", "uniqueidentifier"), ("AccountObjectTaxCode", "nvarchar"),
                        ("InvNo", "nvarchar"), ("TotalTurnoverAmount", "money"),
                        ("TotalVATAmount", "money"), ("RefDate", "datetime")]
            if table == "PUVoucherDetail":
                return [("Amount", "money"), ("VATAmount", "money")]
            return []
        if "FROM (SELECT DISTINCT RefID, PUVoucherRefID FROM PUInvoiceDetail)" in sql:
            # tổng THẬT theo Chi tiết (PUVoucherDetail) đang liên kết — ĐÃ
            # ĐÚNG sau khi người dùng tự xóa dòng phí thừa ngay trên MISA.
            return [("rid-22619", 5537037, 442963)]
        if "FROM PUInvoice WHERE" in sql:
            # PUInvoice vẫn giữ số CŨ (chưa được MISA tự cập nhật lại).
            return [("0108705693-008", "22619", 5648148, 451852, None, "rid-22619")]
        return []

    def fetchone(self):
        if "FROM OrganizationUnit" in self.last_sql:
            return (1,)
        if "OBJECT_ID" in self.last_sql:
            return None   # không cần View_PUVoucherService cho test này
        return None


class FakeConn:
    def __init__(self):
        self._cur = FakeCursor()

    def cursor(self):
        return self._cur

    def close(self):
        pass


def test_dung_tong_that_theo_chi_tiet_dang_lien_ket_khi_pui_da_cu():
    orig_db, orig_connect = server.db, server._misa_sql_connect
    server.db = lambda: db_factory("0108705693-008", "22619", 5537037, 442963)
    server._misa_sql_connect = lambda cid, database=None: FakeConn()
    try:
        kq = server._misa_doi_chieu_import_toan_bo(1, "TESTDB")
    finally:
        server.db = orig_db
        server._misa_sql_connect = orig_connect

    mh = kq["mua_hang"]
    print("Mua hàng:", mh)
    assert not mh["lech"], (
        f"Hóa đơn 22619 đã được người dùng tự sửa ĐÚNG trên MISA (Chi tiết PUVoucherDetail hiện "
        f"5.537.037đ) — KHÔNG được báo LỆCH nữa dù PUInvoice.TotalTurnoverAmount vẫn còn lưu số CŨ "
        f"5.648.148đ (đóng băng từ lúc ghi ban đầu, MISA không tự cập nhật lại) — phải TÍNH LẠI theo "
        f"PUVoucherDetail đang liên kết — được lech={mh.get('lech')}")
    assert not mh["thieu"], f"Hóa đơn 22619 không được báo thiếu — được thieu={mh.get('thieu')}"
    print("PASS: PUInvoice.TotalTurnoverAmount lưu số CŨ (đóng băng, không tự cập nhật khi người dùng "
          "tự sửa Chi tiết ngay trên MISA UI) không còn khiến đối chiếu báo LỆCH oan — dùng đúng tổng "
          "THẬT theo PUVoucherDetail đang liên kết.")


test_dung_tong_that_theo_chi_tiet_dang_lien_ket_khi_pui_da_cu()

print("\nTẤT CẢ TEST PASS")
