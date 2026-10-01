import os, sys, datetime
_HERE = os.path.dirname(os.path.abspath(__file__))
_t = open(os.path.join(_HERE, "test_ban_hang_ghi_so.py"), encoding="utf-8").read()
exec(_t[:_t.index('header = ["Ngày lập"')], globals())   # dùng lại harness MISA giả (ns, FakeCursor, FakeConn, TABLES...)

# Yêu cầu người dùng: sửa Bảng kê (HĐ 10216/10400 có dòng chiết khấu bị cộng dương), up Bảng kê mới rồi "Import tự động toàn
# bộ" nhưng bước 2 báo "0 chứng từ, bỏ qua (đã có) 2321" -> MISA vẫn giữ số SAI. Chứng từ DO PHẦN MỀM TẠO (kể cả đã ghi sổ)
# mà tổng tiền/VAT khác Bảng kê hiện tại phải được TỰ gỡ (cả sổ cái) và ghi lại đúng; khớp rồi thì vẫn bỏ qua.

class CurCN(FakeCursor):
    def __init__(self, pm_rows):
        super().__init__()
        self.pm_rows = pm_rows
        self.deleted = []
    def execute(self, sql, *params):
        if sql.startswith("DELETE FROM"):
            p = params[0] if len(params) == 1 and isinstance(params[0], (tuple, list)) else params
            self.deleted.append((sql.split(" ")[2], p[0] if p else None))
        return super().execute(sql, *params)
    def fetchall(self):
        sql = self._last_sql
        if sql.startswith("SELECT RefID, RefNoManagement, ISNULL(AccountObjectTaxCode") and "CustomField10" in sql:
            return self.pm_rows
        return super().fetchall()

header = ["Ngày lập", "Số hóa đơn", "MST người mua", "Tên người mua", "Mặt hàng",
          "Doanh số bán chưa thuế", "Thuế GTGT", "Ký hiệu HĐ", "Ký hiệu mẫu"]
def chay(pm_rows, rows, ghi_de=False, preview=False):
    cur_ = CurCN(pm_rows)
    ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur_)
    ns['nhap_lieu_get'] = lambda cid, loai: {"header": header, "rows": rows}
    exec(extract_fn('_misa_ghi_ban_hang'), ns)
    return cur_, ns['_misa_ghi_ban_hang'](1, "TESTDB", preview=preview, ghi_de=ghi_de)

MST = "0100109106"
# chứng từ cũ (đã ghi sổ, do phần mềm tạo) ghi SAI: 1.169.259 + 93.540 = 1.262.799
cu = [("old-ref", "BH521/T9/2026", MST, "10216", "C26MHH", 1, 0, 1262799, 93540)]
moi = [["24/09/2026", "10216", MST, "CÔNG TY TNHH KHÁCH HÀNG A", "Bột ngọt", 990741, 79260, "C26MHH", "1"]]

c1, r1 = chay(cu, moi)
assert r1["so_chungtu"] == 1, r1
assert "đã cập nhật" in r1["danh_sach"][0]["trang_thai"], r1["danh_sach"]
bang = [t for t, _ in c1.deleted]
for t in ("GeneralLedger", "AccountObjectLedger", "CustomFieldLedger", "SaleLedger", "SAVoucherDetail", "SAVoucher"):
    assert (t, "old-ref") in c1.deleted, (t, c1.deleted)
sv = c1.inserted["SAVoucher"]
assert len(sv) == 1 and sv[0]["RefNoManagement"] == "BH521/T9/2026" and sv[0]["TotalAmount"] == 1070001 and sv[0]["TotalVATAmount"] == 79260, sv
print("PASS 1: chứng từ đã ghi sổ do phần mềm tạo, số liệu đổi -> gỡ (cả sổ cái) và ghi lại đúng 1.070.001/79.260, giữ số chứng từ cũ.")

# số liệu KHỚP -> vẫn bỏ qua, không gỡ gì
cu_ok = [("old-ref", "BH521/T9/2026", MST, "10216", "C26MHH", 1, 0, 1070001, 79260)]
c2, r2 = chay(cu_ok, moi)
assert r2["so_chungtu"] == 0 and not c2.deleted and not c2.inserted["SAVoucher"], (r2, c2.deleted)
assert "đã ghi sổ" in r2["danh_sach"][0]["trang_thai"]
print("PASS 2: số liệu khớp -> bỏ qua như cũ, không xóa/ghi gì.")

# xem trước: báo 'sẽ cập nhật', không động DB
c3, r3 = chay(cu, moi, preview=True)
assert "sẽ cập nhật" in r3["danh_sach"][0]["trang_thai"] and not c3.deleted
print("PASS 3: xem trước báo 'sẽ cập nhật', chưa xóa gì.")

# hóa đơn 2 dòng trùng số (1 dòng 0đ như HĐ 10157): so TỔNG, không cập nhật nhầm
cu_2 = [("r1", "BH755/T9/2026", MST, "10157", "C26MHH", 1, 0, 809814, 59986),
        ("r2", "BH2321/T9/2026", MST, "10157", "C26MHH", 1, 0, 0, 0)]
moi_2 = [["21/09/2026", "10157", MST, "CÔNG TY TNHH KHÁCH HÀNG A", "Nước", 749828, 59986, "C26MHH", "1"],
         ["21/09/2026", "10157", MST, "CÔNG TY TNHH KHÁCH HÀNG A", "Nước", 0, 0, "C26MHH", "1"]]
c4, r4 = chay(cu_2, moi_2)
assert r4["so_chungtu"] == 0 and not c4.deleted, (r4, c4.deleted)
print("PASS 4: HĐ có dòng 0đ trùng số: so theo TỔNG, khớp -> không gỡ/ghi lại.")

# chứng từ cũ KHÔNG do phần mềm tạo (không có trong truy vấn CustomField10) -> không đụng
c5, r5 = chay([], moi)
assert not c5.deleted
print("PASS 5: chứng từ không do phần mềm tạo không bị đụng.")
assert "1 × đã ghi sổ trong MISA" in r2["ly_do_bo_qua"], r2["ly_do_bo_qua"]
print("PASS 6: kết quả nêu lý do bỏ qua (tính trên toàn bộ danh sách).")
# ===== Bảng kê đầu ra CŨ (còn số SAI do cộng chiết khấu) -> đối soát với dữ liệu hóa đơn GỐC và dùng số gốc =====
# Ca thật: xóa chứng từ 10216/10400 trong MISA rồi import lại vẫn ghi 1.169.259 vì Bảng kê đã lưu là bản cũ.
moi_cu = [["24/09/2026", "10216", MST, "CÔNG TY TNHH KHÁCH HÀNG A", "Bột ngọt", 1169259, 93540, "C26MHH", "1"]]
ns['_ban_ra_goc_theo_hoa_don'] = lambda cid: {"10216": [("c26mhh", 990741, 79260)]}
c7, r7 = chay([], moi_cu)
assert r7["so_sua_theo_goc"] == 1 and r7["so_chungtu"] == 1, r7
sv7 = c7.inserted["SAVoucher"]
assert len(sv7) == 1 and sv7[0]["TotalAmount"] == 1070001 and sv7[0]["TotalVATAmount"] == 79260, sv7
print("PASS 7: Bảng kê đầu ra cũ (1.169.259/93.540) -> ghi theo dữ liệu gốc 990.741/79.260.")

# Hóa đơn nhiều dòng trong Bảng kê (nhiều thuế suất) KHÔNG tự sửa; số khớp gốc thì không đụng; ngoại tệ/gốc = 0 không dùng
moi_2d = [["24/09/2026", "10216", MST, "CÔNG TY TNHH KHÁCH HÀNG A", "A", 500000, 40000, "C26MHH", "1"],
          ["24/09/2026", "10216", MST, "CÔNG TY TNHH KHÁCH HÀNG A", "B", 669259, 53540, "C26MHH", "1"]]
c8, r8 = chay([], moi_2d)
assert r8["so_sua_theo_goc"] == 0 and sorted(v["TotalAmount"] for v in c8.inserted["SAVoucher"]) == [540000, 722799]
c9, r9 = chay([], moi)           # đã đúng gốc
assert r9["so_sua_theo_goc"] == 0
ns['_ban_ra_goc_theo_hoa_don'] = lambda cid: {"10216": [("c26mhh", 0, 0)]}
c10, r10 = chay([], moi_cu)
assert r10["so_sua_theo_goc"] == 0
print("PASS 8: không tự sửa hóa đơn nhiều dòng / đã khớp gốc / gốc = 0.")

print("\nALL DONE")

# _ban_ra_goc_theo_hoa_don: đọc bảng invoices thật (chỉ HĐ bán, hợp lệ, VNĐ)
import sqlite3, tempfile, json as _json
sys.path.insert(0, os.path.dirname(_HERE))
import server as _srv
_dbf = tempfile.mktemp(suffix=".db")
def _db():
    c = sqlite3.connect(_dbf); c.row_factory = sqlite3.Row; return c
_srv.db = _db
_c = _db()
_c.execute("CREATE TABLE invoices (id INTEGER PRIMARY KEY, company_id INT, loai TEXT, khhdon TEXT, shdon TEXT, tgtcthue REAL, tgtthue REAL, tthai TEXT, raw TEXT)")
for row in ((1, 1, "sold", "C26MHH", "0010216", 990741, 79260, "1", "{}"), (2, 1, "sold", "C26MHH", "5", 100, 8, "4", "{}"),
            (3, 1, "sold", "C26MHH", "6", 100, 8, "1", _json.dumps({"dvtte": "USD"})), (4, 1, "purchase", "C26TSA", "7", 100, 8, "1", "{}"),
            (5, 2, "sold", "C26MHH", "8", 100, 8, "1", "{}")):
    _c.execute("INSERT INTO invoices VALUES (?,?,?,?,?,?,?,?,?)", row)
_c.commit(); _c.close()
g = _srv._ban_ra_goc_theo_hoa_don(1)
assert g == {"10216": [("c26mhh", 990741, 79260)]}, g
print("PASS 9: dữ liệu gốc chỉ lấy HĐ bán hợp lệ, VNĐ, đúng công ty (số HĐ chuẩn hóa bỏ số 0 đầu).")
print("\nALL DONE")
