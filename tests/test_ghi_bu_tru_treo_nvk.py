import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import datetime
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

def extract_fn(name):
    idx = src.index('def ' + name + '(')
    i = src.index(':', idx)
    lines = src[i+1:].split('\n')
    body = []
    started = False
    for ln in lines:
        if ln.strip() == '' and not started:
            body.append(ln); continue
        if ln and not ln[0].isspace() and started:
            break
        if ln.strip():
            started = True
        body.append(ln)
    return src[idx:i+1] + '\n'.join(body)


class FakeHTTPException(Exception):
    def __init__(self, code, msg):
        self.code = code; self.detail = msg
        super().__init__(f"{code}: {msg}")


# Người dùng báo lỗi thực tế (ảnh chụp SQL Server): ghi thẳng phiếu Thu/Chi
# tiền mặt (CAReceipt/CAPayment) qua SQL "thành công" nhưng KHÔNG hiện trên
# lưới MISA 'Quỹ > Thu, chi tiền' (tầng cache riêng CAReceiptPaymentList
# không tự cập nhật khi ghi thẳng SQL) -> yêu cầu đổi sang ghi thẳng vào
# chứng từ NGHIỆP VỤ KHÁC (GLVoucher/GLVoucherDetail) của MISA thay vào,
# đúng bảng đã xác nhận ghi thẳng ổn định (dùng chung kỹ thuật với
# _misa_dao_dieu_chinh_cong_no/_misa_chuyen_cong_no_sai_doi_tuong).
AOID_KH = "kh-travel-buddy"
AOID_NCC = "ncc-binh-an-phat"

COLUMNS = {
    "GLVoucher": [("RefID", "uniqueidentifier"), ("RefType", "int"), ("DisplayOnBook", "bit"),
                  ("RefDate", "datetime"), ("PostedDate", "datetime"), ("RefNoFinance", "nvarchar"),
                  ("JournalMemo", "nvarchar"), ("TotalAmountOC", "money"), ("TotalAmount", "money"),
                  ("BranchID", "uniqueidentifier"), ("CurrencyID", "nvarchar"), ("ExchangeRate", "float"),
                  ("RefOrder", "int"), ("IsPostedFinance", "bit"), ("IsPostedManagement", "bit"),
                  ("CreatedDate", "datetime"), ("CreatedBy", "nvarchar"), ("ModifiedDate", "datetime"),
                  ("ModifiedBy", "nvarchar"), ("CustomField10", "nvarchar")],
    "GLVoucherDetail": [("RefDetailID", "uniqueidentifier"), ("RefID", "uniqueidentifier"),
                        ("Description", "nvarchar"), ("DebitAccount", "nvarchar"), ("CreditAccount", "nvarchar"),
                        ("AmountOC", "money"), ("Amount", "money"), ("UnResonableCost", "bit"),
                        ("SortOrder", "int"), ("CreditObjectID", "uniqueidentifier"),
                        ("DebitObjectID", "uniqueidentifier")],
    "GeneralLedger": [("RefID", "uniqueidentifier"), ("RefDetailID", "uniqueidentifier"), ("RefType", "int"),
                      ("RefDate", "datetime"), ("RefDate1", "datetime"), ("PostedDate", "datetime"),
                      ("RefNo", "nvarchar"), ("RefNo1", "nvarchar"), ("RefNo2", "nvarchar"),
                      ("RefNoFinance", "nvarchar"), ("JournalMemo", "nvarchar"), ("Description", "nvarchar"),
                      ("AccountNumber", "nvarchar"), ("CorrespondingAccountNumber", "nvarchar"),
                      ("DebitAmountOC", "money"), ("DebitAmount", "money"),
                      ("CreditAmountOC", "money"), ("CreditAmount", "money"),
                      ("AccountObjectID", "uniqueidentifier"), ("AccountObjectName", "nvarchar"),
                      ("AccountObjectNameDI", "nvarchar"), ("AccountObjectCode", "nvarchar"),
                      ("BranchID", "uniqueidentifier"), ("RefOrder", "int")],
    "AccountObjectLedger": [("RefID", "uniqueidentifier"), ("RefDetailID", "uniqueidentifier"),
                            ("RefDate", "datetime"), ("PostedDate", "datetime"),
                            ("RefNo", "nvarchar"), ("RefNoFinance", "nvarchar"),
                            ("JournalMemo", "nvarchar"), ("Description", "nvarchar"),
                            ("AccountNumber", "nvarchar"), ("CorrespondingAccountNumber", "nvarchar"),
                            ("DebitAmountOC", "money"), ("DebitAmount", "money"),
                            ("CreditAmountOC", "money"), ("CreditAmount", "money"),
                            ("AccountObjectID", "uniqueidentifier"), ("AccountObjectCode", "nvarchar"),
                            ("AccountObjectName", "nvarchar"), ("AccountObjectNameDI", "nvarchar"),
                            ("BranchID", "uniqueidentifier"), ("RefOrder", "int"),
                            ("PayKeyID", "nvarchar"), ("DebtKeyID", "nvarchar")],
}

# Mẫu chứng từ THẬT (không do phần mềm tạo) trong CSDL công ty — đúng tình
# huống thật người dùng báo: công ty này có chứng từ điều chỉnh công nợ
# treo THẬT nhưng đánh số theo tiền tố "DCCN..." (do PHIÊN BẢN CŨ HƠN của
# _xuat_excel_dieu_chinh_cong_no sinh ra), KHÔNG PHẢI "DCTR/DCTH" như bản
# hiện tại — dò theo tiền tố số chứng từ bị BỎ SÓT, phải dò theo NỘI DUNG
# DIỄN GIẢI (JournalMemo, ổn định qua mọi phiên bản) thay vào. Cũng có 1
# chứng từ "Chiết khấu thương mại" KHÔNG LIÊN QUAN nhưng số TÌNH CỜ cũng
# bắt đầu bằng "DC" (DCTM) — diễn giải KHÔNG khớp "Điều chỉnh công nợ
# treo..." nên phải bị loại, đúng lỗi thật đã gặp (MISA hiện nhầm "Nghiệp
# vụ" = "Chiết khấu thương mại (bán hàng)").
GLV_MAU_DIEU_CHINH = {
    "RefID": "real-glv-dieuchinh", "RefType": 4501, "DisplayOnBook": 0,
    "RefDate": datetime.datetime(2025, 12, 20), "PostedDate": datetime.datetime(2025, 12, 20),
    "RefNoFinance": "DCCN001/T12/2025",
    "JournalMemo": "Điều chỉnh công nợ treo HĐ 4 - CÔNG TY TNHH TRAVEL BUDDY",
    "TotalAmountOC": 100, "TotalAmount": 100, "BranchID": "branch-1", "CurrencyID": "VND", "ExchangeRate": 1,
    "RefOrder": 1, "IsPostedFinance": True, "IsPostedManagement": False,
    "CreatedDate": datetime.datetime(2025, 12, 20), "CreatedBy": "ADMIN",
    "ModifiedDate": datetime.datetime(2025, 12, 20), "ModifiedBy": "ADMIN",
    "CustomField10": None,
}
GLV_MAU_CHIET_KHAU = {**GLV_MAU_DIEU_CHINH, "RefID": "real-glv-chietkhau", "RefType": 9001,
                      "RefNoFinance": "DCTM001/T12/2025", "JournalMemo": "Chiết khấu thương mại tháng 12"}

# Mẫu GeneralLedger THẬT của 1 chứng từ Nghiệp vụ khác BẤT KỲ — cố tình
# dùng TK 642/331 (KHÔNG liên quan gì tới TK 1111/131 của bút toán bù trừ
# treo) để xác nhận code phải TỰ GHI ĐÈ đúng AccountNumber/
# CorrespondingAccountNumber theo giao dịch MỚI, không nhân bản mù TK cũ.
GL_MAU_NO = {
    "RefID": "real-glv-sample", "RefDetailID": "d1", "RefType": 7000,
    "RefDate": datetime.datetime(2025, 8, 1), "RefDate1": datetime.datetime(2025, 8, 1),
    "PostedDate": datetime.datetime(2025, 8, 1), "RefNo": "X001", "RefNo1": "X001", "RefNo2": "X001",
    "RefNoFinance": "X001", "JournalMemo": "mau", "Description": "mau",
    "AccountNumber": "642", "CorrespondingAccountNumber": "331",
    "DebitAmountOC": 500, "DebitAmount": 500, "CreditAmountOC": 0, "CreditAmount": 0,
    "AccountObjectID": None, "AccountObjectName": None, "AccountObjectNameDI": None,
    "AccountObjectCode": None, "BranchID": "branch-1", "RefOrder": 5,
}
GL_MAU_CO = {**GL_MAU_NO, "AccountNumber": "331", "CorrespondingAccountNumber": "642",
            "DebitAmountOC": 0, "DebitAmount": 0, "CreditAmountOC": 500, "CreditAmount": 500}
AOL_MAU = {
    "RefID": "real-glv-sample", "RefDetailID": "d1", "RefDate": datetime.datetime(2025, 8, 1),
    "PostedDate": datetime.datetime(2025, 8, 1), "RefNo": "X001", "RefNoFinance": "X001",
    "JournalMemo": "mau", "Description": "mau", "AccountNumber": "331",
    "CorrespondingAccountNumber": "642", "DebitAmountOC": 0, "DebitAmount": 0,
    "CreditAmountOC": 500, "CreditAmount": 500, "AccountObjectID": "obj-khac-khong-lien-quan",
    "AccountObjectCode": "XX", "AccountObjectName": "Công ty khác", "AccountObjectNameDI": "Cong ty khac",
    "BranchID": "branch-1", "RefOrder": 5, "PayKeyID": "cu", "DebtKeyID": "cu",
}


class FakeCursor:
    """Mô phỏng công ty ĐÃ có sẵn 2 mẫu chứng từ Nghiệp vụ khác thật: 1 cái
    có đối tượng ở bên NỢ (TK 331, DebitObjectID), 1 cái có đối tượng ở bên
    CÓ (TK 131, CreditObjectID) — đủ để tự học được cột 'Đối tượng' đúng
    theo từng chiều kh/ncc."""
    def __init__(self):
        self.written = []
        self.deletes = []

    def execute(self, sql, params=()):
        p = params if isinstance(params, (tuple, list)) else (params,) if params != () else ()
        if sql.startswith("DELETE"):
            self.deletes.append((sql, p))
            self._result = []
            return self
        if sql.startswith("INSERT INTO"):
            table = sql.split("INSERT INTO ")[1].split(" (")[0].strip()
            cols_order = sql.split("([")[1].split("]) VALUES")[0].split("],[")
            self.written.append((table, dict(zip(cols_order, p))))
            self._result = []
            return self
        if "sys.columns c" in sql and "sys.types ty" in sql:
            table = p[0]
            self._result = COLUMNS.get(table, [])
        elif "SELECT TOP 500 [" in sql and "CreditAccount LIKE" in sql:
            # obj_cols=[CreditObjectID,DebitObjectID] (thứ tự COLUMNS bên
            # dưới) -> dòng có đối tượng ở bên CÓ (TK 131) đặt ở vị trí 1.
            self._result = [(AOID_KH, None)]
        elif "SELECT TOP 500 [" in sql and "DebitAccount LIKE" in sql:
            # dòng có đối tượng ở bên NỢ (TK 331) đặt ở vị trí 2 (DebitObjectID).
            self._result = [(None, AOID_NCC)]
        elif sql.startswith("SELECT name FROM sys.columns WHERE object_id"):
            table = p[0]
            self._result = [(n,) for n, _t in COLUMNS.get(table, [])]
        elif sql.startswith("SELECT TOP 5 ["):
            # mẫu chứng từ để học RefType — công ty có CẢ 2: 1 chứng từ
            # "Điều chỉnh công nợ" hợp lệ (số DCCN..., diễn giải "Điều
            # chỉnh công nợ treo...") VÀ 1 chứng từ "Chiết khấu thương mại"
            # không liên quan (số DCTM..., cũng bắt đầu bằng "DC" nhưng
            # diễn giải khác hẳn). Query dò theo JournalMemo phải bỏ qua
            # được DCTM dù KHÔNG dò theo tiền tố số chứng từ nữa.
            cols = [c for c, _t in COLUMNS["GLVoucher"]]
            sample = GLV_MAU_DIEU_CHINH if "Điều chỉnh công nợ treo" in sql else GLV_MAU_CHIET_KHAU
            self._result = [tuple(sample[c] for c in cols)]
        elif "ISNULL(MAX(RefOrder),0)" in sql:
            self._result = [(9,)]
        elif "RefNoFinance FROM GLVoucher WHERE RefNoFinance LIKE" in sql:
            self._result = []   # chưa có chứng từ DCTH/DCTR nào -> đánh số từ 1
        elif "SELECT TOP 1 gv.RefID FROM GLVoucher gv WHERE" in sql:
            self._result = [(GL_MAU_NO["RefID"],)]
        elif "FROM GeneralLedger WHERE RefID=? ORDER BY EntryType" in sql:
            cols = [c for c, _t in COLUMNS["GeneralLedger"]]
            self._result = [tuple(GL_MAU_NO[c] for c in cols), tuple(GL_MAU_CO[c] for c in cols)]
        elif "FROM AccountObjectLedger WHERE AccountNumber LIKE" in sql:
            cols = [c for c, _t in COLUMNS["AccountObjectLedger"]]
            self._result = [tuple(AOL_MAU[c] for c in cols)]
        elif "OrganizationUnit" in sql:
            self._result = [("branch-1",)]
        else:
            self._result = []
        return self

    def fetchone(self):
        return self._result[0] if self._result else None

    def fetchall(self):
        return self._result


class FakeConn:
    def __init__(self, cur):
        self._cur = cur
    def cursor(self):
        return self._cur
    def commit(self):
        pass
    def rollback(self):
        pass
    def close(self):
        pass


ns = {'datetime': datetime, 'HTTPException': FakeHTTPException}
for fn in ("_misa_cot_bang_that", "_misa_gia_tri_mac_dinh", "_misa_chon_cot", "_misa_gan",
           "_misa_mau_dong_that", "_misa_branch_id", "_misa_pu_reftype", "_snum",
           "_misa_ghi_bu_tru_treo"):
    exec(extract_fn(fn), ns)
ns['_to_num'] = lambda v: float(v) if v not in (None, '') else 0
ns['_PM_MARK'] = "HDDT-AUTO"
_misa_ghi_bu_tru_treo = ns['_misa_ghi_bu_tru_treo']

# ── Test 1: loai='kh' — Nợ 1111 / Có 131, đối tượng học đúng CreditObjectID ──
cur = FakeCursor()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur)
danh_sach_kh = [
    {"account_object_id": AOID_KH, "mst": "0402196345", "ten": "CÔNG TY TNHH TRAVEL BUDDY",
     "inv_no": "4", "inv_date": "2025-09-16", "so_tien": 2656500},
]
r = _misa_ghi_bu_tru_treo(1, "TESTDB", "kh", danh_sach_kh, preview=False)
assert r["so_ghi"] == 1, r
assert r["hoc_duoc_cot_doi_tuong"] is True
assert r["danh_sach"][0]["so_ct"].startswith("DCTH"), r["danh_sach"]

glv = [row for tbl, row in cur.written if tbl == "GLVoucher"][0]
glvd = [row for tbl, row in cur.written if tbl == "GLVoucherDetail"][0]
assert glvd["DebitAccount"] == "1111" and glvd["CreditAccount"] == "131", glvd
assert glvd["CreditObjectID"] == AOID_KH, "Đối tượng KH phải gắn ở BÊN CÓ (TK 131, tài khoản công nợ)"
assert glvd["Amount"] == 2656500
assert glv["RefType"] == 4501, "RefType phải HỌC từ mẫu chứng từ DC% có sẵn, không đoán"
assert glv["IsPostedFinance"] is True, "Phải GHI SỔ NGAY (không để CHƯA GHI SỔ) theo đúng yêu cầu"
assert glv["CustomField10"] == "HDDT-AUTO", "Vẫn đánh dấu để truy vết dù đã ghi sổ ngay"
print("PASS: KH — ghi ĐÚNG vào GLVoucher/GLVoucherDetail (Nợ 1111/Có 131, DCTH...), KHÔNG còn đụng "
      "tới CAReceipt (bảng có tầng cache riêng gây lỗi 'ghi thành công nhưng không hiện trên lưới "
      "Quỹ' người dùng đã báo) — GHI SỔ NGAY, đối tượng học đúng cột CreditObjectID.")

# ── Test 2: loai='ncc' — Nợ 331 / Có 1111, đối tượng học đúng DebitObjectID ──
cur2 = FakeCursor()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur2)
danh_sach_ncc = [
    {"account_object_id": AOID_NCC, "mst": "KQK-001", "ten": "CÔNG TY TNHH ĐIỆN LẠNH BÌNH AN PHÁT",
     "inv_no": "1", "inv_date": "2025-09-11", "so_tien": 2688000},
]
r2 = _misa_ghi_bu_tru_treo(1, "TESTDB", "ncc", danh_sach_ncc, preview=False)
assert r2["danh_sach"][0]["so_ct"].startswith("DCTR"), r2["danh_sach"]
glvd2 = [row for tbl, row in cur2.written if tbl == "GLVoucherDetail"][0]
assert glvd2["DebitAccount"] == "331" and glvd2["CreditAccount"] == "1111", glvd2
assert glvd2["DebitObjectID"] == AOID_NCC, "Đối tượng NCC phải gắn ở BÊN NỢ (TK 331, tài khoản công nợ)"
print("PASS: NCC — ghi ĐÚNG chiều ngược lại (Nợ 331/Có 1111, DCTR...), đối tượng học đúng cột "
      "DebitObjectID — không lẫn lộn 2 chiều kh/ncc.")

# ── Test 3: preview=True KHÔNG ghi gì (chỉ tính toán) ────────────────────────
cur3 = FakeCursor()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur3)
r3 = _misa_ghi_bu_tru_treo(1, "TESTDB", "kh", danh_sach_kh, preview=True)
assert r3["so_ghi"] == 1
assert not cur3.written, "preview=True KHÔNG được ghi gì vào MISA (chỉ xem trước)"
print("PASS: preview=True không ghi gì thật (chỉ tính toán số chứng từ/số dòng để xem trước).")


# ── Test 4: công ty CHƯA TỪNG gắn đối tượng ở TK 131/331 trên Nghiệp vụ khác
# (đúng lỗi thực tế người dùng báo: 4 chứng từ ghi xong đều KHÔNG có đối
# tượng Nợ/Có) — so khớp GIÁ TRỊ không tìm ra mẫu nào, phải dự phòng bằng
# quy ước đặt tên Debit*/Credit* đã xác nhận có thật trên CHÍNH bảng này.
class FakeCursorKhongCoMau(FakeCursor):
    def execute(self, sql, params=()):
        if "SELECT TOP 500 [" in sql and ("CreditAccount LIKE" in sql or "DebitAccount LIKE" in sql):
            self._result = []   # không có dòng nào để học qua GIÁ TRỊ
            return self
        return super().execute(sql, params)


cur4 = FakeCursorKhongCoMau()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur4)
r4 = _misa_ghi_bu_tru_treo(1, "TESTDB", "kh", danh_sach_kh, preview=False)
assert r4["hoc_duoc_cot_doi_tuong"] is True, (
    "Phải dự phòng học qua TÊN CỘT (DebitAccount/CreditAccount đã xác nhận có thật trên CHÍNH bảng "
    "GLVoucherDetail) khi công ty chưa có dòng mẫu nào để so khớp GIÁ TRỊ — đúng lỗi thực tế người "
    "dùng báo: ghi xong 4 chứng từ nhưng KHÔNG có đối tượng Nợ/Có")
glvd4 = [row for tbl, row in cur4.written if tbl == "GLVoucherDetail"][0]
assert glvd4["CreditObjectID"] == AOID_KH, (
    f"Dự phòng theo tên cột phải chọn ĐÚNG CreditObjectID (chứa 'credit', khớp phía TK Có/131 của "
    f"kh) — got {glvd4}")
assert glvd4.get("DebitObjectID") in (None, ""), "Không được gán nhầm sang cột phía kia"
print("PASS: công ty CHƯA có sẵn mẫu nào gắn đối tượng ở TK 131/331 (so khớp GIÁ TRỊ ra rỗng) — tự "
      "dự phòng ĐÚNG qua quy ước đặt tên Debit*/Credit* (đã xác nhận có thật trên CHÍNH bảng "
      "GLVoucherDetail qua DebitAccount/CreditAccount), không còn bỏ trống đối tượng như lỗi thực tế "
      "người dùng đã báo.")

# ── Test 5: BÀI HỌC CHÍNH của lần sửa này — ghi đủ GeneralLedger (2 dòng) +
# AccountObjectLedger (1 dòng), KHÔNG chỉ GLVoucher/GLVoucherDetail. Đúng
# lỗi thực tế người dùng báo: chứng từ NVK "ghi sổ" xong nhưng hóa đơn vẫn
# hiện treo lại ở Tầng 3 (vì _misa_doi_tuong_dieu_chinh_tien_mat đọc TRỰC
# TIẾP từ AccountObjectLedger, không phải GLVoucherDetail). Đồng thời xác
# nhận RefType học ĐÚNG mẫu "Điều chỉnh công nợ" (DCTH, 4501), KHÔNG dính
# nhầm mẫu "Chiết khấu thương mại" (DCTM, 9001) dù cả 2 đều bắt đầu "DC".
cur5 = FakeCursor()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur5)
r5 = _misa_ghi_bu_tru_treo(1, "TESTDB", "kh", danh_sach_kh, preview=False)
assert r5["hoc_duoc_so_cai"] is True, "Phải học được mẫu Sổ Cái/Sổ chi tiết công nợ khi có mẫu thật"

glv5 = [row for tbl, row in cur5.written if tbl == "GLVoucher"][0]
assert glv5["RefType"] == 4501, (
    f"RefType phải học đúng mẫu 'Điều chỉnh công nợ' (4501), KHÔNG dính mẫu 'Chiết khấu thương mại' "
    f"(9001) dù cả 2 cùng bắt đầu bằng 'DC' — đúng ảnh chụp lỗi thật người dùng báo — got "
    f"{glv5['RefType']}")

gl_rows5 = [row for tbl, row in cur5.written if tbl == "GeneralLedger"]
assert len(gl_rows5) == 2, f"Phải ghi ĐỦ 2 dòng GeneralLedger (ghi kép Nợ/Có) — got {len(gl_rows5)}"
tk_theo_dong = {r["AccountNumber"]: r for r in gl_rows5}
assert set(tk_theo_dong.keys()) == {"1111", "131"}, (
    f"Phải TỰ GHI ĐÈ đúng TK của giao dịch MỚI (1111/131), KHÔNG nhân bản mù TK của mẫu cũ "
    f"(642/331) — got {set(tk_theo_dong.keys())}")
assert tk_theo_dong["1111"]["DebitAmount"] == 2656500 and tk_theo_dong["1111"]["CreditAmount"] == 0
assert tk_theo_dong["131"]["CreditAmount"] == 2656500 and tk_theo_dong["131"]["DebitAmount"] == 0
assert tk_theo_dong["1111"]["CorrespondingAccountNumber"] == "131"
assert tk_theo_dong["131"]["CorrespondingAccountNumber"] == "1111"
assert tk_theo_dong["1111"]["AccountObjectID"] == AOID_KH and tk_theo_dong["131"]["AccountObjectID"] == AOID_KH, (
    "Cả 2 dòng GeneralLedger đều phải gắn ĐÚNG đối tượng mới (không giữ lại đối tượng của mẫu cũ)")

aol_rows5 = [row for tbl, row in cur5.written if tbl == "AccountObjectLedger"]
assert len(aol_rows5) == 1, f"Phải ghi ĐÚNG 1 dòng AccountObjectLedger (vế công nợ 131) — got {len(aol_rows5)}"
aol5 = aol_rows5[0]
assert aol5["AccountNumber"] == "131" and aol5["CorrespondingAccountNumber"] == "1111", aol5
assert aol5["AccountObjectID"] == AOID_KH, (
    f"Phải TỰ GHI ĐÈ đúng đối tượng MỚI (AOID_KH), KHÔNG giữ lại đối tượng KHÔNG liên quan của mẫu "
    f"cũ (obj-khac-khong-lien-quan) — got {aol5['AccountObjectID']}")
assert aol5["CreditAmount"] == 2656500 and aol5["DebitAmount"] == 0, (
    "KH giảm công nợ phải thu -> ghi CreditAmount trên TK 131, đúng quy ước "
    "_misa_doi_tuong_dieu_chinh_tien_mat đã dùng để dò lại")
print("PASS: BÀI HỌC CHÍNH — đã ghi ĐỦ 2 dòng GeneralLedger + 1 dòng AccountObjectLedger (không chỉ "
      "GLVoucher/GLVoucherDetail), tự ghi đè ĐÚNG TK/đối tượng của giao dịch MỚI thay vì nhân bản mù "
      "TK/đối tượng KHÔNG liên quan của mẫu cũ — đúng lỗi thực tế: chứng từ NVK 'ghi sổ' xong nhưng "
      "hóa đơn vẫn hiện treo lại ở Tầng 3 vì thiếu 2 bảng này. RefType cũng học ĐÚNG mẫu 'Điều chỉnh "
      "công nợ', không dính nhầm mẫu 'Chiết khấu thương mại' trùng tiền tố 'DC'.")

# ── Test 6: công ty CHƯA TỪNG có chứng từ 'Điều chỉnh công nợ treo' nào
# (lần đầu dùng tính năng, mau_glv=None) — phải rơi đúng vào dự phòng
# _misa_pu_reftype dò qua SYSRefType, và PHẢI dò được (đúng lỗi thật vừa
# gặp: gọi với từ khóa "khac" KHÔNG dấu trong khi RefTypeName lưu tiếng
# Việt CÓ dấu "khác" -> so khớp luôn thất bại, rơi vào lỗi "thiếu dữ liệu
# SYSRefType" dù dữ liệu thật vẫn có).
class FakeCursorLanDau(FakeCursor):
    def execute(self, sql, params=()):
        p = params if isinstance(params, (tuple, list)) else (params,) if params != () else ()
        if sql.startswith("SELECT TOP 5 ["):
            self._result = []   # chưa từng có chứng từ điều chỉnh công nợ nào
            return self
        if "SELECT RefType, RefTypeName FROM SYSRefType WHERE MasterTableName=?" in sql:
            self._result = [(4501, "Chứng từ nghiệp vụ khác")]
            return self
        return super().execute(sql, params)


cur6 = FakeCursorLanDau()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur6)
r6 = _misa_ghi_bu_tru_treo(1, "TESTDB", "kh", danh_sach_kh, preview=False)
glv6 = [row for tbl, row in cur6.written if tbl == "GLVoucher"][0]
assert glv6["RefType"] == 4501, (
    f"Lần đầu dùng tính năng (chưa có mẫu JournalMemo nào) phải dự phòng dò ĐÚNG qua SYSRefType "
    f"với từ khóa CÓ DẤU 'khác' (khớp 'Chứng từ nghiệp vụ khác') — got {glv6.get('RefType')}")
print("PASS: công ty lần đầu dùng tính năng (chưa từng có chứng từ 'Điều chỉnh công nợ treo' nào) — "
      "dự phòng dò qua SYSRefType với từ khóa 'khác' CÓ DẤU dò ĐÚNG (trước đây gọi 'khac' KHÔNG dấu, "
      "không bao giờ khớp được RefTypeName tiếng Việt có dấu, rơi thẳng vào lỗi 'thiếu dữ liệu "
      "SYSRefType' dù dữ liệu thật vẫn có — đúng lỗi thực tế người dùng vừa báo).")

print("\nALL DONE")
