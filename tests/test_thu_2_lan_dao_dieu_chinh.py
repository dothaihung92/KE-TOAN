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


# ── Phần 1: PHÁT HIỆN thu 2 lần (_misa_doi_chieu_3_tang) ────────────────────
class FakeCursor1:
    """Mô phỏng ĐÚNG kịch bản người dùng nêu: KH-1 có HĐ 2025 (5.000.000đ)
    ĐÃ được điều chỉnh coi như thu tiền mặt (bút toán DCTH001/T12/2025, TK
    Nợ 1111/Có 131, RefID='dc-ref-1'), nhưng khách lại CHUYỂN KHOẢN THẬT trả
    đúng khoản đó vào 2026 (BADeposit, RefID='bank-ref-1')."""
    def execute(self, sql, params=()):
        p = params if isinstance(params, (tuple, list)) else (params,) if params != () else ()
        if "ISNULL(CorrespondingAccountNumber,'') LIKE '111%'" in sql:
            # _misa_doi_tuong_dieu_chinh_tien_mat (kh: CreditAmount trên 131)
            self._result = [("kh-1", datetime.datetime(2025, 12, 20), 5000000, "dc-ref-1")]
        elif "FROM AccountObjectLedger WHERE AccountNumber LIKE ?" in sql:
            # _misa_doi_tuong_hoa_don (kh: DebitAmount trên 131)
            self._result = [
                ("kh-1", "KH01", "", "KHÁCH HÀNG 1", "inv-1", "HD500",
                 datetime.datetime(2025, 6, 10), datetime.datetime(2025, 6, 10), 5000000, ""),
            ]
        elif "FROM BADeposit" in sql or "BADepositDetail" in sql:
            # _misa_doi_tuong_thanh_toan (kh) — khoản chuyển khoản THẬT 2026
            self._result = [("kh-1", datetime.datetime(2026, 2, 15), 5000000, "bank-ref-1",
                             "KHACH HANG 1 CHUYEN KHOAN", "", "UNT002")]
        else:
            self._result = []
        return self

    def fetchone(self):
        return self._result[0] if self._result else None

    def fetchall(self):
        return self._result


class FakeConn1:
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

cur1 = FakeCursor1()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn1(cur1)

r = _misa_doi_chieu_3_tang(1, "TESTDB", loai="kh", cua_so_thang=24)

assert len(r["thu_2_lan"]) == 1, f"Phải phát hiện đúng 1 trường hợp thu 2 lần — got {r['thu_2_lan']}"
conflict = r["thu_2_lan"][0]
assert conflict["inv_no"] == "HD500"
assert conflict["so_tien"] == 5000000
assert conflict["dieu_chinh_ref_id"] == "dc-ref-1"
assert conflict["thanh_toan_that_ref_id"] == "bank-ref-1"
assert conflict["dieu_chinh_ngay"] == "2025-12-20"
assert conflict["thanh_toan_that_ngay"] == "2026-02-15"
print("PASS: phát hiện ĐÚNG trường hợp 'thu 2 lần' — HĐ HD500 đã bị bút toán điều chỉnh (DCTH, "
      "20/12/2025) 'dùng mất', nhưng khách lại chuyển khoản THẬT trả đúng khoản đó (15/02/2026) — "
      "khoản chuyển khoản này bị 'mồ côi' (không khớp hóa đơn nào) nên được cờ đúng làm ứng viên đảo.")

# ── Phần 2: ĐẢO bút toán (_misa_dao_dieu_chinh_cong_no) ─────────────────────
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
    """Mô phỏng bút toán GỐC (DCTH001/T12/2025, Nợ 1111/Có 131, đối tượng
    gắn ở cột CreditObjectID='kh-1' — CHỈ cột này có giá trị, DebitObjectID
    để trống, đúng thật tế: TK 1111 không phải TK theo dõi đối tượng)."""
    def __init__(self):
        self.written = []   # (table, row_dict)

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
        elif "SELECT name FROM sys.columns WHERE object_id" in sql:
            table = p[0]
            self._result = [(n,) for n, _t in COLUMNS.get(table, [])]
        elif sql.startswith("SELECT TOP 5 [") and "GLVoucher " in sql and "GLVoucherDetail" not in sql:
            # mẫu dòng GỐC GLVoucher (RefID='dc-ref-1')
            self._result = [(
                "dc-ref-1", 4501, 0, datetime.datetime(2025, 12, 20), datetime.datetime(2025, 12, 20),
                "DCTH001/T12/2025", "Điều chỉnh công nợ treo HĐ HD500 - KHÁCH HÀNG 1", 5000000, 5000000,
                "branch-1", "VND", 1, 5, True, False, datetime.datetime(2025, 12, 20), "ADMIN",
                datetime.datetime(2025, 12, 20), "ADMIN",
            )]
        elif sql.startswith("SELECT TOP 5 [") and "GLVoucherDetail" in sql:
            # mẫu dòng chi tiết GỐC — Nợ 1111/Có 131, đối tượng ở CreditObjectID
            self._result = [(
                "detail-1", "dc-ref-1", "Điều chỉnh công nợ treo HĐ HD500 - KHÁCH HÀNG 1",
                "1111", "131", 5000000, 5000000, False, 0, "kh-1", None,
            )]
        elif "MAX(RefOrder) FROM GLVoucher" in sql:
            self._result = [(5,)]
        elif "RefNoFinance FROM GLVoucher WHERE RefNoFinance LIKE" in sql:
            self._result = []   # chưa có chứng từ ĐẢO nào trước đó
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
        self.autocommit = True
    def cursor(self):
        return self._cur
    def commit(self):
        pass
    def rollback(self):
        pass
    def close(self):
        pass


for fn in ("_misa_cot_bang_that", "_misa_gia_tri_mac_dinh", "_misa_chon_cot", "_misa_gan",
           "_misa_mau_dong_that", "_misa_branch_id", "_misa_dao_dieu_chinh_cong_no"):
    exec(extract_fn(fn), ns)
ns['_to_num'] = lambda v: float(v) if v not in (None, '') else 0
_misa_dao_dieu_chinh_cong_no = ns['_misa_dao_dieu_chinh_cong_no']

cur2 = FakeCursor2()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn2(cur2)

r2 = _misa_dao_dieu_chinh_cong_no(1, "TESTDB", "kh", r["thu_2_lan"], preview=False)

assert r2["so_dong"] == 1
item = r2["danh_sach"][0]
assert item["trang_thai"] == "đã tạo", item
assert item["doi_tuong_hoc_duoc"] is True, "Phải tự học được đúng cột 'Đối tượng' (CreditObjectID) qua so khớp giá trị"
print(f"PASS: tự học đúng cột 'Đối tượng' (CreditObjectID) trên bút toán gốc qua so khớp GIÁ TRỊ "
      f"với account_object_id đã biết (kh-1) — không đoán tên cột cố định.")

glv_written = [row for tbl, row in cur2.written if tbl == "GLVoucher"]
glvd_written = [row for tbl, row in cur2.written if tbl == "GLVoucherDetail"]
assert len(glv_written) == 1 and len(glvd_written) == 1

glv = glv_written[0]
assert glv["RefType"] == 4501, f"Phải học ĐÚNG RefType từ bút toán gốc (4501) — got {glv['RefType']}"
assert glv["RefNoFinance"] == "DCTHD001/T2/2026", f"Số chứng từ ĐẢO phải mang tiền tố riêng DCTHD, đúng " \
    f"tháng/năm của ngày thanh toán THẬT (02/2026) — got {glv['RefNoFinance']}"
assert glv["TotalAmount"] == 5000000

glvd = glvd_written[0]
assert glvd["DebitAccount"] == "131", f"ĐẢO: TK Có gốc (131) -> TK Nợ mới — got {glvd['DebitAccount']}"
assert glvd["CreditAccount"] == "1111", f"ĐẢO: TK Nợ gốc (1111) -> TK Có mới — got {glvd['CreditAccount']}"
assert glvd["Amount"] == 5000000
assert glvd["CreditObjectID"] == "kh-1", "Đối tượng phải được gắn lại ĐÚNG cột đã học được (CreditObjectID)"

print("PASS: bút toán ĐẢO được ghi đúng — TK Nợ/Có đảo ngược hoàn toàn so với bút toán gốc "
      "(Nợ 1111/Có 131 -> Nợ 131/Có 1111), đúng số tiền, đúng đối tượng, RefType học lại từ bút "
      "toán gốc (không đoán) — công nợ HĐ HD500 sẽ trở lại đúng số dư để khoản chuyển khoản thật "
      "(15/02/2026) tự khớp bình thường ở lần đối chiếu sau.")

print("\nALL DONE")
