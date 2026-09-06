import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: đúng ca thật người dùng báo lại NGAY SAU bản .192 —
HÀNG LOẠT hóa đơn Mua hàng (bất kỳ hóa đơn nào có TỪ 2 DÒNG HÀNG trở lên,
KHÔNG hề bị sửa tay gì cả) báo "LỆCH" với "Doanh số MISA"/"Thuế GTGT MISA"
ĐÚNG GẤP ĐÔI (x2) số liệu nguồn — vd hóa đơn Số HĐ 82: nguồn 16.111.860đ
nhưng MISA báo 32.223.720đ = ĐÚNG GẤP 2 LẦN; hàng chục hóa đơn khác cùng
đúng tỷ lệ x2 y hệt.

Nguyên nhân: build .192 vừa thêm bước tính "tổng thật theo PUVoucherDetail
đang liên kết" (sửa lỗi PUInvoice.TotalTurnoverAmount bị "đóng băng" số cũ
sau khi người dùng tự sửa Chi tiết trên MISA — xem
test_doi_chieu_pui_lech_sau_sua_tay.py) bằng câu SQL:
  SELECT pid.RefID, SUM(pvd.Amount), SUM(pvd.VATAmount)
  FROM PUInvoiceDetail pid JOIN PUVoucherDetail pvd
  ON pvd.RefID=pid.PUVoucherRefID GROUP BY pid.RefID
PUInvoiceDetail có NHIỀU DÒNG cho CÙNG 1 hóa đơn (1 dòng/mặt hàng), TẤT CẢ
cùng trỏ PUVoucherRefID về ĐÚNG 1 PUVoucher — JOIN THẲNG (không qua
DISTINCT) sẽ NHÂN CHÉO: hóa đơn N dòng có N dòng PUInvoiceDetail × N dòng
PUVoucherDetail của CÙNG voucher = N×N cặp, GROUP BY pid.RefID cộng dồn
SUM(Amount) qua N×N cặp thay vì đúng N dòng thật — hóa đơn 2 dòng ra ĐÚNG
GẤP 2 LẦN số thật, hóa đơn 3 dòng sẽ ra gấp 3 lần, v.v. Số "tổng thật" bị
thổi phồng này sau đó bị dùng để GHI ĐÈ lên PUInvoice.TotalTurnoverAmount
(vốn đang lưu ĐÚNG số thật) vì khác nhau >1đ — biến hóa đơn ĐANG KHỚP ĐÚNG
thành báo "LỆCH" oan gấp đôi.

Fix: DISTINCT (RefID, PUVoucherRefID) TRƯỚC khi join — mỗi cặp hóa đơn-
chứng từ chỉ tính ĐÚNG 1 LẦN dù PUInvoiceDetail có bao nhiêu dòng."""
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
        "'2025-01-13T10:00:00',?,?,'1','{}',NULL)", (mst, so_hd, tong_nguon, thue_nguon))
    conn.commit()
    return conn


class FakeCursor:
    """Hóa đơn Số HĐ 82 CÓ 2 DÒNG HÀNG (2 dòng PUInvoiceDetail, CÙNG trỏ về
    ĐÚNG 1 PUVoucher 'voucher-82') — PUVoucherDetail của voucher đó CŨNG có
    ĐÚNG 2 dòng, tổng CHÍNH XÁC 16.111.860đ (KHỚP ĐÚNG PUInvoice đang lưu,
    KHÔNG hề bị sửa tay/lệch gì cả)."""
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
            # ĐÚNG (sau fix): 1 cặp (hóa đơn, voucher) duy nhất -> join đúng 1
            # lần với 2 dòng PUVoucherDetail thật -> tổng ĐÚNG 16.111.860.
            return [("rid-82", 16111860, 1611186)]
        if "FROM PUInvoiceDetail pid JOIN PUVoucherDetail pvd" in sql:
            # (Không nên còn được gọi tới sau fix — nếu code cũ còn tồn tại sẽ
            # rơi vào đây và trả về kết quả NHÂN ĐÔI, tái hiện đúng lỗi thật.)
            return [("rid-82", 32223720, 3222372)]
        if "FROM PUInvoice WHERE" in sql:
            # PUInvoice đang lưu ĐÚNG số thật (chưa từng bị sửa tay/lệch gì).
            return [("3703241188", "82", 16111860, 1611186, None, "rid-82")]
        return []

    def fetchone(self):
        if "FROM OrganizationUnit" in self.last_sql:
            return (1,)
        if "OBJECT_ID" in self.last_sql:
            return None
        return None


class FakeConn:
    def __init__(self):
        self._cur = FakeCursor()

    def cursor(self):
        return self._cur

    def close(self):
        pass


def test_hoa_don_nhieu_dong_khop_dung_khong_bi_nhan_doi():
    orig_db, orig_connect = server.db, server._misa_sql_connect
    server.db = lambda: db_factory("3703241188", "82", 16111860, 1611186)
    server._misa_sql_connect = lambda cid, database=None: FakeConn()
    try:
        kq = server._misa_doi_chieu_import_toan_bo(1, "TESTDB")
    finally:
        server.db = orig_db
        server._misa_sql_connect = orig_connect

    mh = kq["mua_hang"]
    print("Mua hàng:", mh)
    assert not mh["lech"], (
        f"Hóa đơn 82 (2 dòng hàng, KHỚP ĐÚNG với nguồn, không hề bị sửa tay) KHÔNG được báo LỆCH — "
        f"nếu câu SQL tính 'tổng thật theo PUVoucherDetail' bị nhân đôi (JOIN không qua DISTINCT) sẽ báo "
        f"sai MISA=32.223.720đ (gấp 2 lần 16.111.860đ thật) — được lech={mh.get('lech')}")
    assert mh["tong_ds_misa"] == 16111860, (
        f"Tổng doanh số MISA phải đúng 16.111.860đ (KHÔNG gấp đôi) — được {mh['tong_ds_misa']}")
    print("PASS: hóa đơn nhiều dòng hàng khớp đúng không còn bị nhân đôi giá trị khi tính 'tổng thật theo "
          "PUVoucherDetail' — đúng ca thật vừa báo lại (hàng loạt hóa đơn báo LỆCH x2 ngay sau bản .192).")


test_hoa_don_nhieu_dong_khop_dung_khong_bi_nhan_doi()

print("\nTẤT CẢ TEST PASS")
