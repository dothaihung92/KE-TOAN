import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: khi 1 group (MST, Số hóa đơn) có NHIỀU ứng viên MISA mà
Ký hiệu HĐ không khớp Y HỆT (2 hệ thống — tra cứu Thuế vs MISA — có thể ghi
Ký hiệu CÙNG 1 hóa đơn thật KHÁC ĐỊNH DẠNG), phải ghép theo ỨNG VIÊN CÓ SỐ
TIỀN GẦN NGUỒN NHẤT — KHÔNG được loại thẳng ứng viên chỉ vì Ký hiệu không
khớp y hệt (dễ loại NHẦM ứng viên ĐÚNG, báo oan "THIẾU" dù hóa đơn có sẵn
trong MISA), và cũng KHÔNG được cứ lấy ứng viên ĐẦU TIÊN theo thứ tự SQL
Server trả về (thứ tự này không liên quan gì tới đúng/sai cặp ghép).

Xác nhận đúng qua phản hồi người dùng: sau khi sửa lỗi CCCD (gộp khách lẻ vào
đúng MST rỗng, PR trước — khiến nhiều hóa đơn khách lẻ cùng Số hóa đơn nay
dồn chung 1 group thay vì mỗi hóa đơn 1 khóa CCCD riêng), số hóa đơn Bán hàng
báo "THIẾU trong MISA" lại TĂNG (1403 -> 1448) thay vì giảm — đúng dấu hiệu
bước lọc theo Ký hiệu (_ky_hieu_chac_chan_khac) loại nhầm ứng viên đúng khi
nhiều hóa đơn cùng group."""
import sys
sys.path.insert(0, _REPO_ROOT)
import server


def db_factory():
    import sqlite3
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE invoices (
        company_id INTEGER, loai TEXT, nbmst TEXT, nmmst TEXT, khhdon TEXT, shdon TEXT,
        tdlap TEXT, tgtcthue REAL, tgtthue REAL, tthai TEXT, raw TEXT, detail_json TEXT)""")
    conn.execute("""CREATE TABLE companies (
        id INTEGER PRIMARY KEY, save_dir TEXT)""")
    conn.execute("INSERT INTO companies VALUES (1, '')")
    # 3 hóa đơn khách lẻ CÙNG Số HĐ "999" nhưng khác CCCD/số tiền/Ký hiệu —
    # sau sửa lỗi CCCD, cả 3 dồn chung group (mst rỗng, "999"); mỗi hóa đơn có
    # Ký hiệu RIÊNG (không rỗng) nên KHÔNG bị gộp lẫn nhau ở bước tổng hợp
    # phía nguồn (chỉ gộp khi Ký hiệu TRÙNG NHAU).
    conn.execute("INSERT INTO invoices VALUES (1,'sold','0100000000','079000000001','1','999',"
                 "'2026-08-14T08:00:00',100000,10000,'1','{}',NULL)")     # A: 100.000đ
    conn.execute("INSERT INTO invoices VALUES (1,'sold','0100000000','079000000002','2','999',"
                 "'2026-08-14T09:00:00',999999,99999,'1','{}',NULL)")     # B: 999.999đ
    conn.execute("INSERT INTO invoices VALUES (1,'sold','0100000000','079000000003','3','999',"
                 "'2026-08-14T10:00:00',5000000,500000,'1','{}',NULL)")   # C: 5.000.000đ (KHÔNG có trong MISA)
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
            return []
        if "FROM SAVoucher" in sql:
            import datetime
            # Ký hiệu HĐ (InvSeries) trên MISA KHÁC ĐỊNH DẠNG với nguồn ("1"
            # vs "B01"...) dù CÙNG 1 hóa đơn thật — không rỗng, không trùng
            # Ký hiệu nguồn -> exact-match thất bại nhưng KHÔNG được loại
            # thẳng, phải dùng số tiền. THỨ TỰ CỐ Ý NGƯỢC với thứ tự nguồn
            # A,B — mô phỏng đúng việc thứ tự SQL Server trả về không liên
            # quan gì tới đúng/sai cặp ghép.
            rows = [
                (None, "999", "B01", 1099998, 99999, datetime.datetime(2026, 8, 14)),  # <- khớp B (999.999)
                (None, "999", "A01", 110000, 10000, datetime.datetime(2026, 8, 14)),   # <- khớp A (100.000)
            ]
            lo, hi = self.last_params[0], self.last_params[1]
            return [r[:6] for r in rows if lo <= r[5] <= hi]
        return []

    def fetchone(self):
        rows = self.fetchall()
        return rows[0] if rows else None


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
print("Kết quả Bán hàng:", {k: v for k, v in bh.items()})

assert bh["khop"] == 2, f"Phải ghép ĐÚNG 2 cặp (A<->110.000đ, B<->1.099.999đ) theo số tiền gần nhất, được khop={bh['khop']}"
assert len(bh["thieu"]) == 1 and bh["thieu"][0]["doanh_so_nguon"] == 5000000, (
    f"Chỉ hóa đơn C (5.000.000đ, thật sự không có trong MISA) mới được báo thiếu — được thieu={bh['thieu']}")
assert not bh["lech"], f"Ghép đúng cặp theo số tiền thì A,B đều khớp tuyệt đối, không được có LỆCH — được {bh['lech']}"
print("PASS: ghép đúng cặp theo số tiền GẦN NGUỒN NHẤT dù Ký hiệu HĐ 2 bên khác định dạng và thứ tự "
      "MISA trả về ngược với thứ tự nguồn — chỉ hóa đơn C (thật sự không có trong MISA) mới bị báo "
      "thiếu, A/B không còn bị loại nhầm vì Ký hiệu không khớp y hệt.")

print("\nTẤT CẢ TEST PASS")
