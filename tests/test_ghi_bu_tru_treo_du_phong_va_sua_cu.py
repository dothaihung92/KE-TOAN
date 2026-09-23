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


# Regression test cho _misa_ghi_bu_tru_treo() (server.py) — người dùng báo (kèm 2 ảnh chụp màn
# hình): báo cáo "Chi tiết công nợ phải thu" của MISA cho 1 khách hàng KHÔNG hề thấy dòng "Có" nào
# (tổng "Có" = 0, dù đã có 1 chứng từ "Điều chỉnh công nợ treo" mở ra xem vẫn đủ TK Nợ 1111/TK Có
# 131/Số tiền đúng) — "hạch toán điều chỉnh rồi nhưng sao MISA không thấy ghi nhận".
#
# Nguyên nhân xác nhận qua trao đổi với người dùng: công ty này CHƯA TỪNG tự tay tạo 1 chứng từ
# "Nghiệp vụ khác" đơn giản (1 dòng) nào trong MISA để phần mềm học cấu trúc GeneralLedger theo
# (mau_gl rỗng -> co_mau_so_cai=False) — trước đây trong tình huống này phần mềm CHỈ ghi
# GLVoucher/GLVoucherDetail (nên chứng từ mở ra xem vẫn đủ số liệu), THIẾU HẲN GeneralLedger (ghi
# kép Nợ/Có) + AccountObjectLedger (sổ chi tiết công nợ theo đối tượng) — 2 bảng mà "Chi tiết công
# nợ phải thu" của MISA thực sự đọc từ đó, nên KHÔNG hề thấy đối chiếu nào dù chứng từ "ghi sổ" đã
# xong (IsPostedFinance=1).
#
# Fix 1 (dự phòng mau_gl): GeneralLedger là bảng SỔ CÁI DÙNG CHUNG cho MỌI loại chứng từ (Bán
# hàng/Mua hàng/Ngân hàng/Nghiệp vụ khác...), nên khi KHÔNG tìm được mẫu từ 1 chứng từ "Nghiệp vụ
# khác" thật, mượn tạm 1 cặp Nợ/Có bất kỳ đã có CHẠM TK 131/331 (công ty chắc chắn ĐÃ CÓ — chính là
# dữ liệu công nợ đang cần điều chỉnh, VD từ hóa đơn Bán hàng) làm khung, rồi GHI ĐÈ tường minh
# RefType/RefTypeName/CurrencyID/ExchangeRate cho ĐÚNG loại "Nghiệp vụ khác" (không giữ nguyên của
# mẫu mượn, tránh lộ sai loại chứng từ trên MISA).
#
# Fix 2 (sửa chứng từ CŨ đã lỡ ghi thiếu): tự phát hiện + backfill 2 dòng GeneralLedger + 1 dòng
# AccountObjectLedger còn thiếu cho các chứng từ "Điều chỉnh công nợ treo" CHÍNH phần mềm này đã
# tạo trước đó (CustomField10 đánh dấu, IsPostedFinance=1) mà bị lỡ ghi thiếu sổ cái — dùng LẠI
# đúng RefID/RefDetailID/số chứng từ/ngày/đối tượng/số tiền đã có, KHÔNG tạo chứng từ mới/KHÔNG đụng
# gì tới GLVoucher/GLVoucherDetail đã có (an toàn tuyệt đối, chỉ THÊM phần còn thiếu).

AOID_KH = "kh-travel-buddy"

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
                        ("DebitObjectID", "uniqueidentifier"), ("BusinessType", "int")],
    "GeneralLedger": [("RefID", "uniqueidentifier"), ("RefDetailID", "uniqueidentifier"), ("RefType", "int"),
                      ("RefDate", "datetime"), ("RefDate1", "datetime"), ("PostedDate", "datetime"),
                      ("RefNo", "nvarchar"), ("RefNo1", "nvarchar"), ("RefNo2", "nvarchar"),
                      ("RefNoFinance", "nvarchar"), ("JournalMemo", "nvarchar"), ("Description", "nvarchar"),
                      ("AccountNumber", "nvarchar"), ("CorrespondingAccountNumber", "nvarchar"),
                      ("DebitAmountOC", "money"), ("DebitAmount", "money"),
                      ("CreditAmountOC", "money"), ("CreditAmount", "money"),
                      ("AccountObjectID", "uniqueidentifier"), ("AccountObjectName", "nvarchar"),
                      ("AccountObjectNameDI", "nvarchar"), ("AccountObjectCode", "nvarchar"),
                      ("BranchID", "uniqueidentifier"), ("RefOrder", "int"),
                      ("CurrencyID", "nvarchar"), ("ExchangeRate", "float"), ("RefTypeName", "nvarchar")],
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
                            ("PayKeyID", "nvarchar"), ("DebtKeyID", "nvarchar"),
                            ("CurrencyID", "nvarchar"), ("ExchangeRate", "float"), ("RefTypeName", "nvarchar")],
}

# Mẫu GeneralLedger THẬT mượn tạm từ 1 hóa đơn BÁN HÀNG (RefType=302 — KHÁC HẲN RefType của
# "Nghiệp vụ khác") — công ty này CHƯA TỪNG tự tạo tay 1 chứng từ Nghiệp vụ khác nào (mau_gl chính
# KHÔNG có), nhưng CÓ hóa đơn Bán hàng ghi nợ TK 131 (đúng dữ liệu công nợ đang cần điều chỉnh).
GL_BAN_HANG_NO = {
    "RefID": "sa-voucher-1", "RefDetailID": "sad1", "RefType": 302,
    "RefDate": datetime.datetime(2025, 6, 24), "RefDate1": datetime.datetime(2025, 6, 24),
    "PostedDate": datetime.datetime(2025, 6, 24), "RefNo": "BH00390", "RefNo1": "BH00390",
    "RefNo2": "BH00390", "RefNoFinance": "BH00390", "JournalMemo": "Bán hàng", "Description": "Bán hàng",
    "AccountNumber": "131", "CorrespondingAccountNumber": "5111",
    "DebitAmountOC": 19356975, "DebitAmount": 19356975, "CreditAmountOC": 0, "CreditAmount": 0,
    "AccountObjectID": "kh-khac-khong-lien-quan", "AccountObjectName": None, "AccountObjectNameDI": None,
    "AccountObjectCode": None, "BranchID": "branch-1", "RefOrder": 50,
    "CurrencyID": "VND", "ExchangeRate": 1, "RefTypeName": "Bán hàng trong nước",
}
GL_BAN_HANG_CO = {**GL_BAN_HANG_NO, "AccountNumber": "5111", "CorrespondingAccountNumber": "131",
                  "DebitAmountOC": 0, "DebitAmount": 0, "CreditAmountOC": 19356975, "CreditAmount": 19356975}
AOL_MAU = {
    "RefID": "sa-voucher-1", "RefDetailID": "sad1", "RefDate": datetime.datetime(2025, 6, 24),
    "PostedDate": datetime.datetime(2025, 6, 24), "RefNo": "BH00390", "RefNoFinance": "BH00390",
    "JournalMemo": "Bán hàng", "Description": "Bán hàng", "AccountNumber": "131",
    "CorrespondingAccountNumber": "5111", "DebitAmountOC": 19356975, "DebitAmount": 19356975,
    "CreditAmountOC": 0, "CreditAmount": 0, "AccountObjectID": "kh-khac-khong-lien-quan",
    "AccountObjectCode": "SENTUAN", "AccountObjectName": "HKD Sen Tuấn", "AccountObjectNameDI": "HKD Sen Tuan",
    "BranchID": "branch-1", "RefOrder": 50, "PayKeyID": "cu", "DebtKeyID": "cu",
    "CurrencyID": "VND", "ExchangeRate": 1, "RefTypeName": "Bán hàng trong nước",
}


class FakeCursor:
    """Công ty CHƯA TỪNG tự tạo tay 1 chứng từ 'Nghiệp vụ khác' nào (cả mẫu JournalMemo 'Điều
    chỉnh công nợ treo...' lẫn mẫu GLVoucher 1-dòng bất kỳ đều RỖNG) — nhưng CÓ hóa đơn Bán hàng
    thật ghi nợ TK 131 (GL_BAN_HANG_NO/CO) — đúng ca thật người dùng xác nhận: 'công ty chưa từng
    có chứng từ Nghiệp vụ khác nào chạm TK 131/331 để phần mềm học theo cấu trúc'."""
    def __init__(self):
        self.written = []
        self.deletes = []

    def execute(self, sql, params=()):
        p = params if isinstance(params, (tuple, list)) else (params,) if params != () else ()
        if sql.startswith("DELETE"):
            self.deletes.append((sql, p)); self._result = []; return self
        if sql.startswith("INSERT INTO"):
            table = sql.split("INSERT INTO ")[1].split(" (")[0].strip()
            cols_order = sql.split("([")[1].split("]) VALUES")[0].split("],[")
            self.written.append((table, dict(zip(cols_order, p))))
            self._result = []; return self
        if "sys.columns c" in sql and "sys.types ty" in sql:
            table = p[0]; self._result = COLUMNS.get(table, [])
        elif "SELECT TOP 500 [" in sql and "CreditAccount LIKE" in sql:
            self._result = [(AOID_KH, None)]   # đối tượng ở CreditObjectID (TK 131, bên Có, loai=kh)
        elif "SELECT TOP 500 [" in sql and "DebitAccount LIKE" in sql:
            self._result = []
        elif sql.startswith("SELECT name FROM sys.columns WHERE object_id"):
            table = p[0]; self._result = [(n,) for n, _t in COLUMNS.get(table, [])]
        elif sql.startswith("SELECT TOP 5 ["):
            self._result = []   # CHƯA TỪNG có chứng từ 'Điều chỉnh công nợ treo' nào
        elif "SELECT RefType, RefTypeName FROM SYSRefType WHERE MasterTableName=?" in sql:
            self._result = [(4501, "Chứng từ nghiệp vụ khác")]
        elif sql == "SELECT RefTypeName FROM SYSRefType WHERE MasterTableName='GLVoucher' AND RefType=?":
            self._result = [("Chứng từ nghiệp vụ khác",)]
        elif "ISNULL(MAX(RefOrder),0)" in sql:
            self._result = [(9,)]
        elif "RefNoFinance FROM GLVoucher WHERE RefNoFinance LIKE" in sql:
            self._result = []
        elif "SELECT TOP 1 gv.RefID FROM GLVoucher gv WHERE" in sql:
            self._result = []   # KHÔNG có chứng từ Nghiệp vụ khác 1-dòng nào để học (đúng ca thật)
        elif sql.startswith("SELECT TOP 1 RefID FROM GeneralLedger WHERE AccountNumber LIKE ? "
                            "GROUP BY RefID HAVING COUNT(*)=2"):
            self._result = [(GL_BAN_HANG_NO["RefID"],)]   # dự phòng — mượn cặp GL thật từ Bán hàng
        elif "FROM GeneralLedger WHERE RefID=? ORDER BY EntryType" in sql:
            cols = [c for c, _t in COLUMNS["GeneralLedger"]]
            self._result = [tuple(GL_BAN_HANG_NO[c] for c in cols), tuple(GL_BAN_HANG_CO[c] for c in cols)]
        elif "FROM AccountObjectLedger WHERE AccountNumber LIKE" in sql:
            cols = [c for c, _t in COLUMNS["AccountObjectLedger"]]
            self._result = [tuple(AOL_MAU[c] for c in cols)]
        elif "OrganizationUnit" in sql:
            self._result = [("branch-1",)]
        elif sql.startswith("SELECT gv.RefID, gv.RefNoFinance, gv.RefDate, gv.JournalMemo, gd.RefDetailID"):
            self._result = []   # mặc định: KHÔNG có chứng từ CŨ nào lỡ ghi thiếu (ghi đè ở lớp con)
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
           "_misa_mau_dong_that", "_misa_branch_id", "_misa_pu_reftype", "_snum", "_misa_doc_ngay",
           "_misa_ghi_bu_tru_treo"):
    exec(extract_fn(fn), ns)
ns['_to_num'] = lambda v: float(v) if v not in (None, '') else 0
ns['_PM_MARK'] = "HDDT-AUTO"
_misa_ghi_bu_tru_treo = ns['_misa_ghi_bu_tru_treo']

danh_sach_kh = [
    {"account_object_id": AOID_KH, "mst": "0318712827", "ten": "HỘ KINH DOANH TẠP HÓA SEN TUẤN",
     "inv_no": "351", "inv_date": "2025-06-24", "so_tien": 18988851},
]

# ===== Test 1 (QUAN TRỌNG — đúng bug thật): công ty CHƯA TỪNG tự tạo tay chứng từ 'Nghiệp vụ
# khác' nào (mau_glv=None, ref_id_mau_gl chính=None) nhưng CÓ hóa đơn Bán hàng thật ghi nợ TK 131
# -> PHẢI tự mượn tạm cặp GeneralLedger đó làm khung (co_mau_so_cai=True), KHÔNG còn rơi vào
# hoc_duoc_so_cai=False như trước (đúng nguyên nhân khiến "Chi tiết công nợ phải thu" của MISA
# không hề thấy đối chiếu nào dù chứng từ đã "ghi sổ"). =====
cur1 = FakeCursor()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur1)
r1 = _misa_ghi_bu_tru_treo(1, "TESTDB", "kh", danh_sach_kh, preview=False)
assert r1["hoc_duoc_so_cai"] is True, (
    "Công ty CHƯA từng tạo chứng từ Nghiệp vụ khác nào nhưng CÓ hóa đơn Bán hàng thật ghi TK 131 -> "
    "PHẢI tự mượn cặp GeneralLedger đó làm khung (dự phòng), không còn hoc_duoc_so_cai=False — đúng "
    "nguyên nhân báo cáo MISA không thấy đối chiếu nào dù chứng từ đã 'ghi sổ'.")
gl_rows1 = [row for tbl, row in cur1.written if tbl == "GeneralLedger"]
assert len(gl_rows1) == 2, f"Phải ghi đủ 2 dòng GeneralLedger — got {len(gl_rows1)}"
aol_rows1 = [row for tbl, row in cur1.written if tbl == "AccountObjectLedger"]
assert len(aol_rows1) == 1, f"Phải ghi đúng 1 dòng AccountObjectLedger — got {len(aol_rows1)}"
print("PASS 1: công ty chưa từng tạo chứng từ Nghiệp vụ khác nào -> tự mượn cặp GeneralLedger thật "
      "từ Bán hàng làm khung, co_mau_so_cai=True, ghi đủ GeneralLedger/AccountObjectLedger.")

# ===== Test 2 (QUAN TRỌNG — không hồi quy): mẫu mượn tạm từ Bán hàng có RefType=302/RefTypeName=
# 'Bán hàng trong nước' — PHẢI bị GHI ĐÈ đúng RefType/RefTypeName của 'Nghiệp vụ khác' (4501/
# 'Chứng từ nghiệp vụ khác'), KHÔNG được giữ nguyên RefType=302 của mẫu mượn (nếu không, MISA sẽ
# hiểu nhầm loại chứng từ dù số liệu/TK vẫn đúng). =====
for g in gl_rows1:
    assert g["RefType"] == 4501, f"GeneralLedger phải ghi đè RefType=4501 ('Nghiệp vụ khác'), không giữ RefType=302 của mẫu mượn (Bán hàng) — got {g['RefType']}"
    assert g.get("RefTypeName") == "Chứng từ nghiệp vụ khác", f"RefTypeName phải ghi đè đúng — got {g.get('RefTypeName')}"
    assert g["CurrencyID"] == "VND" and g["ExchangeRate"] == 1, g
assert aol_rows1[0].get("RefTypeName") == "Chứng từ nghiệp vụ khác", (
    f"AccountObjectLedger cũng phải ghi đè đúng RefTypeName ('Chứng từ nghiệp vụ khác'), không giữ "
    f"RefTypeName của mẫu mượn ('Bán hàng trong nước') — got {aol_rows1[0].get('RefTypeName')}")
assert aol_rows1[0]["AccountObjectID"] == AOID_KH, (
    "Phải ghi đè đúng đối tượng MỚI (AOID_KH), không giữ đối tượng không liên quan của mẫu mượn (kh-khac-khong-lien-quan)")
print("PASS 2: mẫu mượn tạm từ Bán hàng (RefType/RefTypeName khác hẳn) bị ghi đè đúng thành "
      "'Nghiệp vụ khác' trên cả GeneralLedger lẫn AccountObjectLedger, không lộ sai loại chứng từ.")


# ===== Test 3 (QUAN TRỌNG — đúng bug thật, backfill chứng từ CŨ): công ty CÓ 1 chứng từ 'Điều
# chỉnh công nợ treo' CŨ do CHÍNH phần mềm ghi ở lần chạy TRƯỚC (trước khi có fix, IsPostedFinance=1
# nhưng THIẾU GeneralLedger/AccountObjectLedger — đúng hiện tượng 2 ảnh chụp người dùng gửi) — lần
# ghi MỚI này (đã có mẫu, co_mau_so_cai=True) PHẢI tự phát hiện + backfill đủ Sổ Cái/Sổ chi tiết
# công nợ cho chứng từ CŨ đó, dùng LẠI đúng RefID/RefDetailID/số chứng từ đã có (không tạo chứng từ
# GLVoucher mới), KHÔNG đụng gì tới GLVoucher/GLVoucherDetail đã có sẵn. =====
class FakeCursorCoChungTuCu(FakeCursor):
    def execute(self, sql, params=()):
        if sql.startswith("SELECT gv.RefID, gv.RefNoFinance, gv.RefDate, gv.JournalMemo, gd.RefDetailID"):
            self._result = [(
                "broken-glv-1", "DCTH407/T12/2025", datetime.datetime(2025, 12, 31),
                "Điều chỉnh công nợ treo HĐ 390-24/06/2025 - HỘ KINH DOANH TẠP HÓA SEN TUẤN",
                "broken-glvd-1", 18988851, "obj-cty-cu-da-ghi-truoc",
            )]
            return self
        return super().execute(sql, params)


cur3 = FakeCursorCoChungTuCu()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur3)
r3 = _misa_ghi_bu_tru_treo(1, "TESTDB", "kh", danh_sach_kh, preview=False)
assert r3["so_sua"] == 1, f"Phải tự phát hiện + backfill ĐÚNG 1 chứng từ CŨ lỡ ghi thiếu sổ cái — got so_sua={r3.get('so_sua')}"
glv_written3 = [row for tbl, row in cur3.written if tbl == "GLVoucher"]
assert len(glv_written3) == 1, (
    f"KHÔNG được tạo GLVoucher MỚI cho chứng từ CŨ (chỉ backfill sổ cái còn thiếu) — chỉ chứng từ THẬT "
    f"SỰ mới (danh_sach_kh) mới được tạo GLVoucher mới — got {len(glv_written3)} dòng GLVoucher")
gl_cu = [row for tbl, row in cur3.written if tbl == "GeneralLedger" and row.get("RefID") == "broken-glv-1"]
assert len(gl_cu) == 2, f"Phải backfill đủ 2 dòng GeneralLedger cho ĐÚNG RefID cũ (broken-glv-1), không tạo RefID mới — got {len(gl_cu)}"
for g in gl_cu:
    assert g["RefDetailID"] == "broken-glvd-1", "Phải dùng LẠI đúng RefDetailID đã có của chứng từ cũ, không sinh mới"
    assert g["RefNoFinance"] == "DCTH407/T12/2025", "Phải dùng lại đúng số chứng từ cũ"
    assert g["AccountObjectID"] == "obj-cty-cu-da-ghi-truoc", "Phải dùng lại đúng đối tượng đã gắn từ trước"
tong_tien_gl_cu = sum(g["DebitAmount"] or 0 for g in gl_cu) if any(g["AccountNumber"] == "1111" for g in gl_cu) else None
aol_cu = [row for tbl, row in cur3.written if tbl == "AccountObjectLedger" and row.get("RefID") == "broken-glv-1"]
assert len(aol_cu) == 1, f"Phải backfill đúng 1 dòng AccountObjectLedger cho chứng từ cũ — got {len(aol_cu)}"
assert aol_cu[0]["CreditAmount"] == 18988851, f"Số tiền backfill phải khớp ĐÚNG số tiền đã ghi của chứng từ cũ (18.988.851) — got {aol_cu[0]['CreditAmount']}"
print("PASS 3: chứng từ 'Điều chỉnh công nợ treo' CŨ đã lỡ ghi thiếu Sổ Cái (đúng 2 ảnh chụp người "
      "dùng gửi) được tự động backfill đủ GeneralLedger/AccountObjectLedger, dùng lại đúng RefID/số "
      "chứng từ/đối tượng/số tiền đã có, KHÔNG tạo chứng từ mới, KHÔNG đụng GLVoucher/GLVoucherDetail cũ.")

# ===== Test 4 (không hồi quy — QUAN TRỌNG): công ty KHÔNG có chứng từ cũ nào lỡ ghi thiếu (trường
# hợp bình thường, đa số công ty) -> so_sua phải = 0, không tự ý ghi thêm gì ngoài ý muốn. =====
cur4 = FakeCursor()   # base — sql_hong trả rỗng mặc định
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur4)
r4 = _misa_ghi_bu_tru_treo(1, "TESTDB", "kh", danh_sach_kh, preview=False)
assert r4["so_sua"] == 0, f"Không có chứng từ cũ nào lỡ ghi thiếu -> so_sua phải = 0 — got {r4.get('so_sua')}"
print("PASS 4: không có chứng từ cũ nào lỡ ghi thiếu sổ cái -> so_sua=0, không ghi thêm gì ngoài ý muốn.")

# ===== Test 5 (không hồi quy — QUAN TRỌNG): preview=True KHÔNG được chạy backfill (chỉ xem trước,
# không ghi gì thật) dù có chứng từ cũ lỡ ghi thiếu. =====
cur5 = FakeCursorCoChungTuCu()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur5)
r5 = _misa_ghi_bu_tru_treo(1, "TESTDB", "kh", danh_sach_kh, preview=True)
assert r5["so_sua"] == 0, "preview=True KHÔNG được chạy backfill chứng từ cũ (chỉ xem trước)"
assert not cur5.written, "preview=True KHÔNG được ghi gì vào MISA (kể cả backfill)"
print("PASS 5: preview=True không chạy backfill chứng từ cũ, không ghi gì thật.")

# ===== Test 6 (frontend): static/index.html phải hiện rõ số chứng từ CŨ đã tự sửa bổ sung
# (d.so_sua) trong thông báo kết quả ghi — người dùng cần biết chứng từ cũ đã lỡ thiếu sổ cái nay
# đã được tự động vá, không chỉ thấy số chứng từ MỚI (d.so_ghi). =====
html = open(os.path.join(_REPO_ROOT, 'static', 'index.html'), encoding='utf-8').read()
assert 'd.so_sua' in html and 'đã tự sửa bổ sung Sổ Cái' in html, (
    "Modal kết quả ghi 'Điều chỉnh công nợ treo' (static/index.html) phải hiện rõ khi có chứng từ CŨ "
    "được tự động vá bổ sung Sổ Cái/Sổ chi tiết công nợ (d.so_sua), không chỉ im lặng sửa ngầm.")
print("PASS 6: static/index.html hiện rõ số chứng từ cũ đã được tự động vá bổ sung sổ cái.")

print("\nALL DONE")
