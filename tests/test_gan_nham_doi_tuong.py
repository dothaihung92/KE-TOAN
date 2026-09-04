import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import datetime, itertools
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


# ── Phần 1: PHÁT HIỆN (đúng dữ liệu thật CHI_TIET_CONG_NO_PHAI_THU.xlsx) ────
# KH "DANH GIÁ": có 1 khoản 17/09 (1.877.040đ, nội dung "YN82A4SEP DUA KHAC
# HCM..." — KHÔNG nhắc gì tới "DANH GIA") chưa từng khớp hóa đơn nào của
# chính KH này. KH "OXYGEN" (đối tượng KHÁC) lại có 1 hóa đơn CÒN TREO đúng
# 1.877.040đ — rất có thể khoản CK trên thực ra thuộc về OXYGEN.
AOID_DANHGIA = "kh-danhgia"
AOID_OXYGEN = "kh-oxygen"


class FakeCursor:
    def execute(self, sql, params=()):
        p = params if isinstance(params, (tuple, list)) else (params,) if params != () else ()
        if "ISNULL(CorrespondingAccountNumber,'') LIKE '111%'" in sql:
            self._result = []   # _misa_doi_tuong_dieu_chinh_tien_mat — chưa có điều chỉnh nào
        elif "FROM AccountObjectLedger WHERE AccountNumber LIKE ?" in sql:
            # _misa_doi_tuong_hoa_don (kh) — DANH GIÁ có 1 hóa đơn ĐÃ trả đủ
            # (không liên quan), OXYGEN có 1 hóa đơn CÒN TREO 1.877.040đ.
            self._result = [
                (AOID_DANHGIA, "DG01", "0304692137", "CÔNG TY TNHH THỜI TRANG DANH GIÁ", "inv-dg",
                 "BH010", datetime.datetime(2025, 11, 19), datetime.datetime(2025, 11, 19), 1848000, ""),
                (AOID_OXYGEN, "OX01", "", "CÔNG TY TNHH OXYGEN RETAIL", "inv-ox",
                 "BH020", datetime.datetime(2025, 9, 1), datetime.datetime(2025, 9, 1), 1877040, ""),
            ]
        elif "FROM BADeposit" in sql or "BADepositDetail" in sql:
            # _misa_doi_tuong_thanh_toan (kh):
            #  - Khoản 17/09 gắn vào DANH GIÁ nhưng nội dung KHÔNG nhắc tới DANH GIÁ.
            #  - Khoản 24/11 gắn ĐÚNG vào DANH GIÁ, trả đủ hóa đơn BH010 (1.848.000đ).
            self._result = [
                (AOID_DANHGIA, datetime.datetime(2025, 9, 17), 1877040, "unt-1709",
                 "YN82A4SEP DUA KHAC HCM GD 819031-091625 18:23:42", "", "UNT718561709253"),
                (AOID_DANHGIA, datetime.datetime(2025, 11, 24), 1848000, "unt-2411",
                 "DANH GIA TT CP TRAI DUA SU KIEN LACOSTE SPORT DAY 28", "", "UNT7185624112547"),
            ]
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
    def close(self):
        pass


ns = {'datetime': datetime, 'itertools': itertools, 'HTTPException': FakeHTTPException}
for fn in ("_misa_ngay_str", "_misa_la_dong_thue", "_misa_doc_ngay", "_misa_bo_dau",
           "_misa_ten_khop_mo_ta", "_misa_doi_tuong_hoa_don",
           "_misa_doi_tuong_thanh_toan", "_misa_doi_tuong_dieu_chinh_tien_mat", "_misa_khop_1_2",
           "_misa_doi_chieu_3_tang"):
    exec(extract_fn(fn), ns)
ns['_MISA_TU_DEM_TEN_CTY'] = {
    "CONG", "TY", "TNHH", "CO", "PHAN", "MTV", "MOT", "THANH", "VIEN", "TRACH",
    "NHIEM", "HUU", "HAN", "DOANH", "NGHIEP", "TU", "NHAN", "XNK", "XUAT", "NHAP",
    "KHAU", "SAN", "THUONG", "MAI", "DAU", "TAP", "DOAN", "GROUP",
}
_misa_doi_chieu_3_tang = ns['_misa_doi_chieu_3_tang']

cur = FakeCursor()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur)

r = _misa_doi_chieu_3_tang(1, "TESTDB", loai="kh", cua_so_thang=24)

# (a) cảnh báo nội dung không khớp tên
assert len(r["nghi_sai_doi_tuong"]) == 1, f"got {r['nghi_sai_doi_tuong']}"
canh_bao = r["nghi_sai_doi_tuong"][0]
assert canh_bao["ma"] == "DG01"
assert canh_bao["so_tien"] == 1877040
assert "YN82A4SEP" in canh_bao["mo_ta"]
assert canh_bao["so_ct"] == "UNT718561709253", "Phải kèm Số chứng từ THẬT để người dùng tự tìm/mở trong MISA"
assert "hoa_don_gan" not in canh_bao and "tong_tien_hd" not in canh_bao and "chenh_lech" not in canh_bao, \
    "Mục CẢNH BÁO (nghi_sai_doi_tuong) giữ nguyên hình dạng gốc — thông tin hóa đơn đích/chênh " \
    "lệch thuộc về mục GỢI Ý (goi_y_chuyen), không phải mục này"
print("PASS: cảnh báo ĐÚNG khoản 17/09 (1.877.040đ) của DANH GIÁ — nội dung chuyển khoản "
      "'YN82A4SEP DUA KHAC...' không hề nhắc tới tên khách hàng đang gắn (DANH GIÁ). Giữ nguyên "
      "hình dạng gốc (không có thông tin hóa đơn đích).")

# khoản 24/11 (đã khớp đúng BH010, nội dung CÓ nhắc "DANH GIA") KHÔNG bị cảnh báo
assert not any(x["so_tien"] == 1848000 for x in r["nghi_sai_doi_tuong"]), \
    "Khoản đã khớp đúng hóa đơn, nội dung khớp tên -> KHÔNG được cảnh báo"
print("PASS: khoản 24/11 (đã khớp đúng hóa đơn BH010, nội dung khớp tên) KHÔNG bị cảnh báo — "
      "không báo nhầm khoản hợp lệ.")

# (b) gợi ý chuyển sang đúng đối tượng OXYGEN (trùng CHÍNH XÁC số tiền, còn treo)
assert len(r["goi_y_chuyen"]) == 1, f"got {r['goi_y_chuyen']}"
goi_y = r["goi_y_chuyen"][0]
assert goi_y["tu_ma"] == "DG01" and goi_y["den_ma"] == "OX01"
assert goi_y["so_tien"] == 1877040
assert goi_y["inv_no"] == "BH020"
assert goi_y["inv_date"] == "2025-09-01", "Phải kèm ngày hóa đơn đích để so sánh"
assert goi_y["hd_so_tien"] == 1877040, "Phải kèm số tiền hóa đơn đích để so sánh với số tiền TT"
assert goi_y["chenh_lech"] == 0, "Khớp CHÍNH XÁC số tiền -> chênh lệch phải bằng 0"
assert goi_y["tt_so_ct"] == "UNT718561709253", "Phải kèm Số chứng từ THẬT của khoản thanh toán để tra cứu"
print("PASS: gợi ý ĐÚNG — khoản 1.877.040đ đang gắn nhầm ở DANH GIÁ (DG01) trùng CHÍNH XÁC số "
      "tiền với hóa đơn BH020 CÒN TREO của OXYGEN (OX01) — đối tượng KHÁC duy nhất khớp số tiền, "
      "đủ tin cậy để đề xuất tự động chuyển. Kèm đủ thông tin ngày HĐ/số tiền HĐ/chênh lệch để "
      "người dùng tự so sánh trước khi đồng ý chuyển.")

# ── Phần 2: TỰ ĐỘNG CHUYỂN công nợ (_misa_chuyen_cong_no_sai_doi_tuong) ─────
COLUMNS = {
    "GLVoucher": [("RefID", "uniqueidentifier"), ("RefType", "int"), ("DisplayOnBook", "bit"),
                  ("RefDate", "datetime"), ("PostedDate", "datetime"), ("RefNoFinance", "nvarchar"),
                  ("JournalMemo", "nvarchar"), ("TotalAmountOC", "money"), ("TotalAmount", "money"),
                  ("BranchID", "uniqueidentifier"), ("CurrencyID", "nvarchar"), ("ExchangeRate", "float"),
                  ("RefOrder", "int"), ("IsPostedFinance", "bit"), ("IsPostedManagement", "bit"),
                  ("CreatedDate", "datetime"), ("CreatedBy", "nvarchar"), ("ModifiedDate", "datetime"),
                  ("ModifiedBy", "nvarchar")],
    "GLVoucherDetail": [("RefDetailID", "uniqueidentifier"), ("RefID", "uniqueidentifier"),
                        ("Description", "nvarchar"), ("DebitAccount", "nvarchar"), ("CreditAccount", "nvarchar"),
                        ("AmountOC", "money"), ("Amount", "money"), ("UnResonableCost", "bit"),
                        ("SortOrder", "int"), ("CreditObjectID", "uniqueidentifier"),
                        ("DebitObjectID", "uniqueidentifier")],
}


class FakeCursor2:
    """Mô phỏng công ty ĐÃ có sẵn 2 mẫu chứng từ Nghiệp vụ khác thật: 1 cái
    có đối tượng ở bên NỢ (TK 331, DebitObjectID), 1 cái có đối tượng ở bên
    CÓ (TK 131, CreditObjectID) — đủ để tự học được CẢ 2 cột khác nhau."""
    def __init__(self):
        self.written = []

    def execute(self, sql, params=()):
        p = params if isinstance(params, (tuple, list)) else (params,) if params != () else ()
        if sql.startswith("INSERT INTO"):
            table = sql.split("INSERT INTO ")[1].split(" (")[0].strip()
            cols_order = sql.split("([")[1].split("]) VALUES")[0].split("],[")
            self.written.append((table, dict(zip(cols_order, p))))
            self._result = []
            return self
        if "sys.columns c" in sql and "sys.types ty" in sql:
            table = p[0]
            self._result = COLUMNS.get(table, [])
        elif "SELECT TOP 500 [" in sql and "DebitAccount LIKE" in sql:
            # dòng có đối tượng ở bên NỢ (TK 331) -> DebitObjectID
            self._result = [(None, AOID_OXYGEN)]
        elif "SELECT TOP 500 [" in sql and "CreditAccount LIKE" in sql:
            # dòng có đối tượng ở bên CÓ (TK 131) -> CreditObjectID
            self._result = [(AOID_DANHGIA, None)]
        elif sql.startswith("SELECT name FROM sys.columns WHERE object_id"):
            table = p[0]
            self._result = [(n,) for n, _t in COLUMNS.get(table, [])]
        elif sql.startswith("SELECT TOP 5 ["):
            # mẫu chứng từ DC% có sẵn (học RefType)
            self._result = [(
                "any-ref", 4501, 0, datetime.datetime(2025, 12, 20), datetime.datetime(2025, 12, 20),
                "DCTH001/T12/2025", "x", 100, 100, "branch-1", "VND", 1, 1, True, False,
                datetime.datetime(2025, 12, 20), "ADMIN", datetime.datetime(2025, 12, 20), "ADMIN",
            )]
        elif "MAX(RefOrder) FROM GLVoucher" in sql:
            self._result = [(9,)]
        elif "RefNoFinance FROM GLVoucher WHERE RefNoFinance LIKE" in sql:
            self._result = []
        elif "OrganizationUnit" in sql:
            self._result = [("branch-1",)]
        else:
            self._result = []
        return self

    def fetchone(self):
        return self._result[0] if self._result else None

    def fetchall(self):
        return self._result


class FakeConn2:
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


for fn in ("_misa_cot_bang_that", "_misa_gia_tri_mac_dinh", "_misa_chon_cot", "_misa_gan",
           "_misa_mau_dong_that", "_misa_branch_id", "_misa_pu_reftype",
           "_misa_chuyen_cong_no_sai_doi_tuong"):
    exec(extract_fn(fn), ns)
ns['_to_num'] = lambda v: float(v) if v not in (None, '') else 0
_misa_chuyen_cong_no_sai_doi_tuong = ns['_misa_chuyen_cong_no_sai_doi_tuong']

cur2 = FakeCursor2()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn2(cur2)

r2 = _misa_chuyen_cong_no_sai_doi_tuong(1, "TESTDB", "kh", r["goi_y_chuyen"], preview=False)
assert r2["hoc_duoc_cot_doi_tuong"] is True
item = r2["danh_sach"][0]
assert item["trang_thai"] == "đã tạo", item

glvd = [row for tbl, row in cur2.written if tbl == "GLVoucherDetail"][0]
assert glvd["DebitAccount"] == "131" and glvd["CreditAccount"] == "131"
assert glvd["DebitObjectID"] == AOID_OXYGEN, "Nợ phải là đối tượng ĐÚNG (OXYGEN, đích)"
assert glvd["CreditObjectID"] == AOID_DANHGIA, "Có phải là đối tượng SAI (DANH GIÁ, nguồn)"
assert glvd["Amount"] == 1877040
print("PASS: bút toán CHUYỂN CÔNG NỢ ghi đúng — Nợ 131 (OXYGEN, đối tượng ĐÚNG) / Có 131 (DANH "
      "GIÁ, đối tượng SAI ban đầu), đúng số tiền 1.877.040đ, cột 'Đối tượng Nợ/Có' tự học đúng "
      "(khác nhau, không đoán) — công nợ sẽ tự chuyển đúng đối tượng.")


# ── Phần 3: đúng dữ liệu thật khác (CHI_TIET_CONG_NO_PHAI_THU.xlsx của KH
# "CODE LEAP") — khoản CK 07/11 (693.000đ, nội dung "YN32A28OCT - DUA KHAC
# HCM GD 333386-110625 18:25:11" — KHÔNG hề nhắc "CODE LEAP") lại TRÙNG
# CHÍNH XÁC số tiền với 1 hóa đơn PHÁT SINH SAU đó 6 ngày (13/11, trong
# phạm vi cho phép "thanh toán TRƯỚC ngày HĐ tối đa 7 ngày") của ĐÚNG
# CODE LEAP đang gắn -> Tầng 1 coi là ĐÃ KHỚP. ĐÃ TỪNG thử mở rộng
# nghi_sai_doi_tuong sang cả khoản ĐÃ khớp (khớp đúng số tiền không có
# nghĩa là khớp đúng đối tượng) — nhưng người dùng phản hồi lại: quá
# nhiều khoản ĐÃ khớp bị báo nhầm (nội dung CK thường chỉ ghi mã giao
# dịch/Số CT chứ không phải tên đối tượng), NÊN quay lại CHỈ xét khoản
# CÒN CHƯA khớp như ban đầu — khoản 07/11 (dù nội dung đáng ngờ) không
# còn bị đưa vào nghi_sai_doi_tuong nữa vì ĐÃ khớp Tầng 1. Thêm 1 hóa
# đơn KHÁC (HĐ 30, 500.000đ) CHƯA có thanh toán nào để xác nhận số dư
# cuối kỳ CODE LEAP vẫn đúng, không liên quan gì tới việc khoản 07/11
# có bị cảnh báo hay không (chỉ khoản CHƯA khớp mới được xét).
AOID_CODELEAP = "kh-codeleap"


class FakeCursor3(FakeCursor):
    def execute(self, sql, params=()):
        if "ISNULL(CorrespondingAccountNumber,'') LIKE '111%'" in sql:
            return super().execute(sql, params)
        if "FROM AccountObjectLedger WHERE AccountNumber LIKE ?" in sql:
            self._result = [
                (AOID_CODELEAP, "CL01", "", "CÔNG TY TNHH CODE LEAP", "inv-cl26",
                 "26", datetime.datetime(2025, 11, 13), datetime.datetime(2025, 11, 13), 693000, ""),
                (AOID_CODELEAP, "CL01", "", "CÔNG TY TNHH CODE LEAP", "inv-cl30",
                 "30", datetime.datetime(2025, 11, 20), datetime.datetime(2025, 11, 20), 500000, ""),
            ]
            return self
        if "FROM BADeposit" in sql or "BADepositDetail" in sql:
            self._result = [
                (AOID_CODELEAP, datetime.datetime(2025, 11, 7), 693000, "unt-0711",
                 "YN32A28OCT - DUA KHAC HCM GD 333386-110625 18:25:11", "", "UNT7185607112531"),
            ]
            return self
        return super().execute(sql, params)


cur3 = FakeCursor3()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur3)
r3 = _misa_doi_chieu_3_tang(1, "TESTDB", loai="kh", cua_so_thang=24, truoc_ngay=7)

assert len(r3["tang1"]) == 1 and r3["tang1"][0]["inv_no"] == "26", (
    f"Khoản CK 07/11 phải khớp Tầng 1 với hóa đơn 26 (13/11) — trong phạm vi cho phép thanh toán "
    f"TRƯỚC ngày HĐ tối đa 7 ngày — got {r3['tang1']}")
print("PASS: Phần 3 — khoản CK 07/11 (693.000đ) khớp Tầng 1 ĐÚNG với hóa đơn 26 (13/11, phát sinh "
      "SAU 6 ngày, trong phạm vi 'thanh toán trước ngày HĐ tối đa 7 ngày'); HĐ 30 (500.000đ) chưa có "
      "thanh toán nào -> CODE LEAP CÒN số dư cuối kỳ 500.000đ, chưa về 0.")

assert r3["nghi_sai_doi_tuong"] == [], (
    f"Khoản CK 07/11 ĐÃ khớp Tầng 1 (với HĐ 26) -> KHÔNG còn được đưa vào 'nghi_sai_doi_tuong' nữa, "
    f"dù nội dung 'YN32A28OCT - DUA KHAC HCM...' không khớp tên 'CODE LEAP' — theo đúng phản hồi mới "
    f"nhất của người dùng ('nếu tình trạng đã khớp rồi thì không cần hiện vào đây') — chỉ khoản CÒN "
    f"CHƯA khớp mới được soát nội dung CK — got {r3['nghi_sai_doi_tuong']}")
print("PASS: Phần 3 — khoản CK 07/11 ĐÃ khớp Tầng 1 (với HĐ 26) KHÔNG còn bị đưa vào "
      "'nghi_sai_doi_tuong' nữa dù nội dung CK không khớp tên đối tượng — quay lại đúng hành vi CHỈ "
      "xét khoản CÒN CHƯA khớp, theo phản hồi mới nhất của người dùng.")

# ── Phần 4 (MỚI, theo đúng yêu cầu người dùng): đối tượng ĐÃ "về không"
# hết (số dư cuối kỳ = 0, hóa đơn duy nhất đã được thanh toán đủ) THÌ
# KHÔNG cần soát nội dung CK nữa, dù nội dung đó KHÔNG khớp tên — về
# TỔNG THỂ đối tượng này không còn gì cần người dùng xử lý.
AOID_PAIDOFF = "kh-paidoff"


class FakeCursor4(FakeCursor):
    def execute(self, sql, params=()):
        if "ISNULL(CorrespondingAccountNumber,'') LIKE '111%'" in sql:
            return super().execute(sql, params)
        if "FROM AccountObjectLedger WHERE AccountNumber LIKE ?" in sql:
            self._result = [
                (AOID_PAIDOFF, "PO01", "", "CÔNG TY TNHH ĐÃ TRẢ ĐỦ", "inv-po1",
                 "50", datetime.datetime(2025, 11, 13), datetime.datetime(2025, 11, 13), 800000, ""),
            ]
            return self
        if "FROM BADeposit" in sql or "BADepositDetail" in sql:
            self._result = [
                (AOID_PAIDOFF, datetime.datetime(2025, 11, 10), 800000, "unt-po1",
                 "NOI DUNG CHUYEN KHOAN LA CHUOI HOAN TOAN KHAC, KHONG NHAC GI TOI TEN DOI TUONG",
                 "", "UNT-PO1"),
            ]
            return self
        return super().execute(sql, params)


cur4 = FakeCursor4()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur4)
r4 = _misa_doi_chieu_3_tang(1, "TESTDB", loai="kh", cua_so_thang=24, truoc_ngay=7)

assert len(r4["tang1"]) == 1 and r4["tang1"][0]["inv_no"] == "50", (
    f"Khoản CK 10/11 phải khớp Tầng 1 với hóa đơn 50 (13/11, số dư về 0) — got {r4['tang1']}")
assert r4["nghi_sai_doi_tuong"] == [], (
    f"'CÔNG TY TNHH ĐÃ TRẢ ĐỦ' đã về số dư 0 (HĐ 50/800.000đ đã khớp đủ khoản CK 800.000đ) -> KHÔNG "
    f"cần soát nội dung CK nữa dù nội dung hoàn toàn không khớp tên — đúng yêu cầu người dùng 'chỉ "
    f"kiểm tra nếu số dư cuối kỳ chưa khớp, nếu đã về không hết rồi thì không cần kiểm tra chi tiết "
    f"nữa' — got {r4['nghi_sai_doi_tuong']}")
print("PASS: Phần 4 — đối tượng ĐÃ về số dư cuối kỳ = 0 (hóa đơn duy nhất đã khớp đủ) thì KHÔNG còn "
      "bị soát nội dung CK/cảnh báo 'nghi ngờ gắn nhầm đối tượng' nữa, dù nội dung CK không hề khớp "
      "tên — đúng yêu cầu người dùng vừa nêu.")

print("\nALL DONE")
