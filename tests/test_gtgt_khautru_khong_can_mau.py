import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: bước "6. Tờ khai GTGT + Khấu trừ" (_misa_tao_to_khai_khau_tru_gtgt)
KHÔNG được bắt buộc phải có sẵn 1 bút toán 'Khấu trừ thuế GTGT' thật trong MISA
mới chạy được — theo đúng yêu cầu người dùng ("bước 6 hãy lập luôn không cần
phải xem 1 bút toán"). Trước khi sửa, hàm này raise HTTPException 400 ngay khi
GLVoucher(RefType=4011)/GLVoucherDetail(Debit=33311,Credit=1331) không có sẵn
dòng nào, dù việc dựng glv_row/glvd_row hoàn toàn KHÔNG phụ thuộc nội dung 2
mẫu đó (chỉ mượn CreatedBy/ModifiedBy, đã có fallback "ADMIN" sẵn).

Test bằng cách GỌI THẲNG hàm thật trong server.py (không copy lại logic) với 1
cursor giả mô phỏng CSDL MISA: CÓ SẴN tờ khai 01/GTGT của quý đang xử lý
(tk_da_co=True, để đi vào nhánh "đọc lại số đã khai" thay vì tính từ đầu, né
bớt phần dựng chi tiết hóa đơn/phụ lục không liên quan tới lỗi đang sửa),
NHƯNG KHÔNG có bất kỳ bút toán GLVoucher RefType=4011 nào (glv_da_co=False,
mau_glv rỗng) — đúng kịch bản người dùng báo cáo trong ảnh chụp màn hình.
"""
import sys, time
sys.path.insert(0, _REPO_ROOT)
import server


class FakeCursor:
    def __init__(self):
        self.last_sql = ""
        self.last_params = ()

    def execute(self, sql, params=()):
        self.last_sql = sql
        self.last_params = params if isinstance(params, (tuple, list)) else (params,)
        return self

    def fetchall(self):
        sql = self.last_sql
        if "FROM sys.columns" in sql:
            table = self.last_params[0]
            cols_gia_pha = {
                "TADeclaration": [("RefID", "uniqueidentifier"), ("BranchID", "int"),
                                  ("RefType", "int"), ("DeclarationTerm", "nvarchar"),
                                  ("CareerCode", "nvarchar")],
                "TADeclarationDetail": [("RefDetailID", "uniqueidentifier"), ("RefID", "uniqueidentifier"),
                                        ("ItemCode", "nvarchar"), ("Value", "nvarchar")],
                "GLVoucher": [("RefID", "uniqueidentifier"), ("RefType", "int"),
                              ("RefNoFinance", "nvarchar"), ("JournalMemo", "nvarchar"),
                              ("CreatedBy", "nvarchar"), ("ModifiedBy", "nvarchar"),
                              ("BranchID", "int"), ("TotalAmount", "money")],
                "GLVoucherDetail": [("RefDetailID", "uniqueidentifier"), ("RefID", "uniqueidentifier"),
                                    ("DebitAccount", "nvarchar"), ("CreditAccount", "nvarchar"),
                                    ("Amount", "money")],
                "TADeclarationAppendix": [], "TA_011GTGT_Detail": [], "TA_012GTGT_Detail": [],
            }
            return cols_gia_pha.get(table, [])
        if "SELECT DeclarationTerm FROM TADeclaration" in sql:
            return [(TEST_KY,)]  # tờ khai quý đang test ĐÃ CÓ SẴN -> tk_da_co=True
        if "SELECT JournalMemo FROM GLVoucher" in sql:
            return []  # KHÔNG có bút toán 'Khấu trừ' nào -> glv_da_co=False
        if "SELECT RefNoFinance FROM GLVoucher" in sql:
            return []
        if "SELECT TOP 5" in sql and "FROM TADeclaration" in sql:
            # mau_tk: PHẢI có sẵn (để qua được check "chưa có tờ khai 01/GTGT")
            return [("id-1", 1, 5005, TEST_KY, "00")]
        if "SELECT TOP 5" in sql and "FROM GLVoucher" in sql:
            # mau_glv: CỐ Ý KHÔNG có dòng nào -> đúng kịch bản người dùng báo lỗi
            return []
        return []

    def fetchone(self):
        sql = self.last_sql
        if "OrganizationUnitID FROM OrganizationUnit" in sql:
            return (7,)
        if "ISNULL(MAX(RefOrder)" in sql:
            return (0,)
        if "ItemCode='Item43'" in sql:
            return None
        if "d.ItemCode=?" in sql:
            item_code = self.last_params[1]
            gia = {"Item35": "5000000", "Item22": "0", "Item25": "1000000"}
            return (gia.get(item_code, "0"),)
        rows = self.fetchall()
        return rows[0] if rows else None


class FakeConn:
    def __init__(self):
        self.autocommit = True
        self._cur = FakeCursor()
        self.rolled_back = False
        self.committed = False

    def cursor(self):
        return self._cur

    def rollback(self):
        self.rolled_back = True

    def commit(self):
        self.committed = True

    def close(self):
        pass


now = time.localtime()
TEST_QUY, TEST_NAM = 2, 2026
TEST_KY = f"Quý {TEST_QUY} năm {TEST_NAM}"

orig_connect = server._misa_sql_connect
server._misa_sql_connect = lambda cid, database=None: FakeConn()
try:
    kq = server._misa_tao_to_khai_khau_tru_gtgt(
        1, "TESTDB", preview=True, tu_quy=TEST_QUY, tu_nam=TEST_NAM, so_quy=1)
finally:
    server._misa_sql_connect = orig_connect

print("Kết quả:", kq)
assert kq["so_quy"] == 1, kq
dong = kq["danh_sach"][0]
assert dong["ky"] == TEST_KY, dong
assert "bút toán" in dong["trang_thai"] and "sẽ tạo" in dong["trang_thai"], (
    f"Phải BÁO SẼ TẠO bút toán khấu trừ dù chưa có mẫu thật để học cấu trúc — được: {dong}")
assert dong["so_tien_khau_tru"] == 1000000, (
    f"Số tiền khấu trừ phải = min(output_amount=5tr, deduction_amount=0+1tr=1tr) = 1tr — được {dong}")

print("PASS: _misa_tao_to_khai_khau_tru_gtgt KHÔNG còn raise HTTPException khi MISA "
      "chưa có sẵn bút toán 'Khấu trừ thuế GTGT' nào để học cấu trúc — tự lập bút toán "
      "ngay bằng cấu trúc chuẩn, đúng yêu cầu 'bước 6 hãy lập luôn không cần phải xem 1 bút toán'.")

# Test 2: đối chứng — vẫn phải raise đúng khi CHƯA CÓ tờ khai 01/GTGT nào (check
# này KHÔNG bị đụng tới, vẫn còn hiệu lực, chỉ riêng check glv/glvd bị bỏ).
class FakeCursorKhongCoTK(FakeCursor):
    def fetchall(self):
        sql = self.last_sql
        if "SELECT TOP 5" in sql and "FROM TADeclaration" in sql:
            return []  # KHÔNG có tờ khai 01/GTGT nào
        return super().fetchall()


class FakeConnKhongCoTK(FakeConn):
    def __init__(self):
        super().__init__()
        self._cur = FakeCursorKhongCoTK()


server._misa_sql_connect = lambda cid, database=None: FakeConnKhongCoTK()
try:
    try:
        server._misa_tao_to_khai_khau_tru_gtgt(1, "TESTDB", preview=True, tu_quy=TEST_QUY, tu_nam=TEST_NAM, so_quy=1)
        raise AssertionError("Phải raise HTTPException khi chưa có tờ khai 01/GTGT nào (check này KHÔNG đổi)")
    except server.HTTPException as e:
        assert "tờ khai 01/GTGT" in e.detail
        print("PASS: check 'chưa có tờ khai 01/GTGT' KHÔNG bị đụng tới, vẫn raise đúng như cũ.")
finally:
    server._misa_sql_connect = orig_connect

print("\nTẤT CẢ TEST PASS")
