import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test cho _misa_ghi_khncc() (server.py) — ghi Danh mục KH/NCC thẳng
# vào bảng AccountObject của MISA (Danh mục > Đối tượng). Người dùng gửi ảnh
# chụp màn hình báo lỗi thật khi bấm "Ghi 530 đối tượng vào MISA":
#   Lỗi ghi: Lỗi khi ghi vào MISA (đã hoàn tác, không ghi gì): ('23000',
#   "...Cannot insert duplicate key row in object 'dbo.AccountObject' with
#   unique index 'IX_AccountObject'. The duplicate key value is (CHKimLong)...")
#
# NGUYÊN NHÂN THẬT (dò trong code): "CHKimLong" là mã tự đặt tay (không phải
# MST thật) cho 1 khách/NCC không có MST — xuất hiện trên NHIỀU hóa đơn/dòng
# Bảng kê KHÁC NHAU với CÁCH VIẾT HOA/THƯỜNG KHÁC NHAU (vd "CHKimLong" ở hóa
# đơn này, "chkimlong" hay "CHKIMLONG" ở hóa đơn khác — dữ liệu gõ tay không
# nhất quán). _misa_thu_thap_khncc() dedup theo "mst" đã qua
# _misa_khncc_chuan_mst() (chỉ bỏ dấu gạch/khoảng trắng/chấm, KHÔNG hạ chữ
# thường) -> 2 cách viết hoa/thường khác nhau bị coi là 2 "mst" KHÁC NHAU, ra
# 2 dòng "items" RIÊNG BIỆT cho CÙNG 1 đối tượng thật. _misa_ghi_khncc() ghi
# CẢ 2 dòng: dòng ĐẦU insert thành công (Mã ĐT="CHKimLong"), dòng THỨ 2 (Mã
# ĐT="chkimlong"/"CHKIMLONG") KHÔNG được nhận diện là trùng (dict 'existing'
# chỉ build 1 LẦN từ DB TRƯỚC KHI ghi, không cập nhật khi ghi thêm dòng mới
# trong CÙNG lô) -> SQL Server (collation mặc định KHÔNG phân biệt hoa/thường)
# chặn ở ràng buộc UNIQUE ngay khi insert dòng thứ 2 -> lỗi ('23000'...) làm
# ROLLBACK SẠCH CẢ LÔ 530 đối tượng, không ghi được dòng nào (kể cả 529 dòng
# khác hoàn toàn không liên quan tới lỗi này).
#
# SỬA: đánh dấu NGAY vào 'existing' sau MỖI lần ghi thành công (không đợi
# query lại DB) — dòng thứ 2 (dù khác hoa/thường) sẽ được nhận diện ĐÚNG là
# đã có ngay trong CÙNG lô, xếp vào "đã có (bỏ qua)" thay vì cố INSERT gây
# lỗi. Đồng thời chuẩn hoá Mã ĐT ('code') CÙNG CÁCH với MST khi build dict
# 'existing' TỪ DB (qua _misa_khncc_chuan_mst, bỏ dấu gạch/khoảng trắng/
# chấm) — phòng thêm trường hợp Mã ĐT đã có sẵn trong MISA viết CÓ dấu gạch
# ngang (vd "CH-Kim-Long") mà dòng mới lại chuẩn hoá bỏ dấu.


def extract_fn(name):
    """Trích xuất hàm TOP-LEVEL (không nested) — cách làm sẵn có, dùng chung
    nhiều test khác trong repo (vd tests/test_chiet_khau_tchat_2_bi_sai.py)."""
    idx = src.index('def ' + name + '(')
    i = src.index(':', idx)
    lines = src[i + 1:].split('\n')
    body = []
    started = False
    for ln in lines:
        if ln.strip() == '' and not started:
            body.append(ln)
            continue
        if ln and not ln[0].isspace() and started:
            break
        if ln.strip():
            started = True
        body.append(ln)
    return src[idx:i + 1] + '\n'.join(body)


class _LoiTrungKhoa(Exception):
    """Giả lập lỗi SQL Server thật khi vi phạm UNIQUE INDEX (IX_AccountObject)
    — đúng dạng lỗi pyodbc.Error thật người dùng đã gặp và chụp màn hình gửi."""
    pass


class _FakeCursor:
    """Giả lập cursor pyodbc — CÓ kiểm tra ràng buộc UNIQUE trên
    AccountObjectCode giống SQL Server thật: collation MẶC ĐỊNH của SQL
    Server (vd Vietnamese_CI_AS/SQL_Latin1_General_CP1_CI_AS) KHÔNG PHÂN
    BIỆT HOA/THƯỜNG (Case-Insensitive) nhưng CÓ phân biệt dấu gạch ngang/
    khoảng trắng (không tự bỏ) — mô phỏng ĐÚNG 2 đặc điểm này để test XÁC
    NHẬN ĐƯỢC việc sửa lỗi thật sự tránh được lỗi DB, không phải chỉ giả
    định suông."""
    def __init__(self, existing_rows):
        self._existing_rows = list(existing_rows)   # [(code, taxcode, name), ...]
        self._da_ghi_codes = set(str(c).strip().lower() for c, _, _ in existing_rows if c)
        self.inserted = []

    def execute(self, sql, *params):
        sql_norm = " ".join(sql.split())
        if sql_norm.startswith("SELECT AccountObjectCode, CompanyTaxCode, AccountObjectName"):
            self._last_select = list(self._existing_rows)
            return self
        if sql_norm.startswith("SELECT TOP 1 OrganizationUnitID"):
            self._last_select = [("branch-gia-lap",)]
            return self
        if sql_norm.startswith("INSERT INTO AccountObject"):
            # params thứ tự: AccountObjectID, AccountObjectCode, AccountObjectName,
            # CompanyTaxCode, IsVendor, IsCustomer, AccountObjectType, Inactive,
            # BranchID, CreatedDate (đúng thứ tự cột trong câu INSERT thật)
            code = params[1]
            k = str(code).strip().lower()   # collation CI (không phân biệt hoa/thường)
            if k in self._da_ghi_codes:
                raise _LoiTrungKhoa(
                    "('23000', \"[23000] [Microsoft][ODBC Driver 17 for SQL Server][SQL Server]"
                    "Cannot insert duplicate key row in object 'dbo.AccountObject' with unique "
                    f"index 'IX_AccountObject'. The duplicate key value is ({code}). (2601) "
                    "(SQLExecDirectW);[23000] [Microsoft][ODBC Driver 17 for SQL Server][SQL Server]"
                    "The statement has been terminated. (3621)\")")
            self._da_ghi_codes.add(k)
            self.inserted.append(params)
            return self
        raise AssertionError(f"Câu SQL không mong đợi trong test: {sql_norm[:80]}")

    def fetchall(self):
        return self._last_select

    def fetchone(self):
        return self._last_select[0] if self._last_select else None


class _FakeConn:
    def __init__(self, cur):
        self._cur = cur
        self.autocommit = True
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        return self._cur

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        pass


class _FakeHTTPException(Exception):
    def __init__(self, status_code, detail):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


ns = {'datetime': __import__('datetime'), 'json': __import__('json'),
      'HTTPException': _FakeHTTPException}
exec(extract_fn('_misa_khncc_chuan_mst'), ns)
exec(extract_fn('_misa_khncc_dinh_dang_mst'), ns)
exec(extract_fn('_misa_branch_id'), ns)
exec(extract_fn('_misa_ghi_khncc'), ns)
_misa_ghi_khncc = ns['_misa_ghi_khncc']


def _tao_boi_canh(existing_rows, items):
    fake_cur = _FakeCursor(existing_rows)
    fake_conn = _FakeConn(fake_cur)
    ns['_misa_sql_connect'] = lambda cid, database=None: fake_conn
    ns['_misa_thu_thap_khncc'] = lambda cid: items
    return fake_cur, fake_conn


# ===== Test 1 (QUAN TRỌNG — đúng bug thật, ca "CHKimLong" người dùng báo):
# CÙNG 1 lô có 2 dòng "items" cho CÙNG 1 đối tượng thật nhưng viết hoa/thường
# khác nhau ("CHKimLong" và "chkimlong" — do dữ liệu gõ tay không nhất quán
# ở các hóa đơn/dòng Bảng kê khác nhau), CHƯA có gì trong MISA trước đó.
# Dòng ĐẦU phải ghi thành công; dòng THỨ 2 (trùng khi SQL Server so sánh
# KHÔNG phân biệt hoa/thường) PHẢI được nhận diện là "đã có" NGAY trong CÙNG
# lô, KHÔNG được cố INSERT (mới tránh được lỗi trùng khoá SQL Server thật). =====
items_1 = [
    {"mst": "CHKimLong", "mst_hien": "CHKimLong", "ten": "Cửa hàng Kim Long", "thieu_ten": False},
    {"mst": "chkimlong", "mst_hien": "chkimlong", "ten": "Cửa hàng Kim Long", "thieu_ten": False},
]
fake_cur1, fake_conn1 = _tao_boi_canh([], items_1)
ket1 = _misa_ghi_khncc(cid=1, database="TESTDB", preview=False)
assert ket1["so_them"] == 1 and ket1["so_trung"] == 1, (
    f"Dòng đầu ('CHKimLong') phải được THÊM, dòng thứ 2 ('chkimlong' — trùng khi không phân biệt hoa/"
    f"thường, đúng collation mặc định SQL Server) phải được nhận diện ĐÃ CÓ ngay trong cùng lô — got "
    f"so_them={ket1['so_them']}, so_trung={ket1['so_trung']}")
assert len(fake_cur1.inserted) == 1, (
    f"CHỈ được gọi INSERT đúng 1 lần (cho dòng đầu) — dòng thứ 2 KHÔNG được cố INSERT (sẽ bị SQL Server "
    f"chặn ở ràng buộc UNIQUE, đúng lỗi 'duplicate key (CHKimLong)' thật đã gặp) — got "
    f"{len(fake_cur1.inserted)} lượt INSERT.")
assert fake_conn1.committed and not fake_conn1.rolled_back, (
    "Giao dịch phải COMMIT thành công (không bị lỗi trùng khoá làm rollback sạch cả lô 530 đối tượng "
    "như bug thật đã gặp, dù chỉ 1 trong 530 dòng có vấn đề).")
print("PASS 1: 2 dòng CÙNG 1 đối tượng thật (khác hoa/thường, 'CHKimLong' vs 'chkimlong') trong CÙNG 1 "
      "lô — dòng đầu ghi thành công, dòng sau được nhận diện ĐÃ CÓ ngay trong lô (không đợi query lại "
      "DB), không còn cố INSERT gây lỗi 'duplicate key' SQL Server thật, giao dịch commit thành công "
      "thay vì rollback sạch cả 530 đối tượng.")

# ===== Test 2 (QUAN TRỌNG — đúng bug thật, biến thể khác: Mã ĐT đã có sẵn
# trong MISA viết CÓ dấu gạch ngang, vd "CH-Kim-Long"): dòng mới cần thêm đã
# qua _misa_khncc_chuan_mst() (bỏ hết dấu gạch/khoảng trắng/chấm) thành
# "CHKimLong" — PHẢI vẫn được nhận diện đúng là đã có (không phân biệt dấu
# gạch ngang khi so khớp), không cố INSERT (SQL Server sẽ KHÔNG coi 2 chuỗi
# khác dấu gạch ngang là trùng nên sẽ không tự chặn được — phải tự nhận diện
# đúng ở tầng ứng dụng TRƯỚC khi gửi SQL). =====
items_2 = [{"mst": "chkimlong", "mst_hien": "CHKimLong", "ten": "Cửa hàng Kim Long", "thieu_ten": False}]
existing_rows_2 = [("CH-Kim-Long", None, "Cửa hàng Kim Long")]
fake_cur2, fake_conn2 = _tao_boi_canh(existing_rows_2, items_2)
ket2 = _misa_ghi_khncc(cid=1, database="TESTDB", preview=False)
assert ket2["so_them"] == 0 and ket2["so_trung"] == 1, (
    f"Mã ĐT mới 'CHKimLong' phải được nhận diện trùng với Mã ĐT đã có 'CH-Kim-Long' (chỉ khác cách viết "
    f"dấu gạch ngang) — got so_them={ket2['so_them']}, so_trung={ket2['so_trung']}")
assert len(fake_cur2.inserted) == 0, (
    f"KHÔNG được cố INSERT khi Mã ĐT (sau khi bỏ dấu gạch ngang để so khớp) đã trùng với đối tượng có "
    f"sẵn — got {len(fake_cur2.inserted)} lượt INSERT.")
print("PASS 2: Mã ĐT có sẵn trong MISA viết CÓ dấu gạch ngang ('CH-Kim-Long') vẫn được nhận diện đúng "
      "là trùng với Mã ĐT mới đã chuẩn hoá bỏ dấu ('CHKimLong').")

# ===== Test 3 (không hồi quy — QUAN TRỌNG): đối tượng THẬT SỰ MỚI (MST chưa
# có trong MISA dưới bất kỳ dạng nào, không trùng hoa/thường lẫn dấu gạch
# ngang với bất kỳ ai) vẫn PHẢI được thêm bình thường — không bị 2 lần sửa
# lỗi ở Test 1/2 làm ảnh hưởng. =====
items_3 = [{"mst": "0318712827", "mst_hien": "0318712827", "ten": "Công ty TNHH ABC", "thieu_ten": False}]
existing_rows_3 = [("CH-Kim-Long", None, "Cửa hàng Kim Long")]
fake_cur3, fake_conn3 = _tao_boi_canh(existing_rows_3, items_3)
ket3 = _misa_ghi_khncc(cid=1, database="TESTDB", preview=False)
assert ket3["so_them"] == 1 and ket3["so_trung"] == 0, (
    f"Đối tượng THẬT SỰ MỚI (MST hoàn toàn chưa có trong MISA) phải được THÊM bình thường, không bị "
    f"coi nhầm là đã có — got {ket3}")
assert len(fake_cur3.inserted) == 1 and fake_cur3.inserted[0][1] == "0318712827", (
    f"Phải gọi đúng 1 lượt INSERT với đúng Mã ĐT = MST mới — got {fake_cur3.inserted}")
print("PASS 3: đối tượng thật sự mới (MST chưa có trong MISA dưới bất kỳ dạng nào) vẫn được thêm bình "
      "thường, không bị ảnh hưởng bởi 2 lần sửa lỗi ở Test 1/2 — không hồi quy.")

print("\nALL DONE")
