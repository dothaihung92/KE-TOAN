import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys, datetime
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

names = ['_misa_cot_bang_that', '_misa_gia_tri_mac_dinh', '_misa_chon_cot', '_misa_gan',
         '_misa_mau_dong_that', '_misa_khncc_chuan_mst', '_misa_branch_id', '_misa_doc_ngay',
         '_snum', '_to_num', '_misa_bank_account_du_phong', '_ten_tk_ke_toan_du_phong',
         '_misa_reason_type_du_phong', '_misa_reason_type_hop_le',
         '_misa_dam_bao_hop_le_ngan_hang_ly_do', '_misa_khung_ghi_so_du_phong', '_misa_ghi_thu_chi']

class FakeHTTPException(Exception):
    def __init__(self, code, msg):
        self.code = code; self.msg = msg
        super().__init__(f"{code}: {msg}")

ns = {'datetime': datetime, 'HTTPException': FakeHTTPException, '_PM_MARK': 'HDDT-AUTO',
      '_TEN_TK_KE_TOAN_CHUAN': {"1121": "Tiền Việt Nam", "131": "Phải thu của khách hàng",
                                "331": "Phải trả cho người bán"}}
for n in names:
    exec(extract_fn(n), ns)

# Cấu trúc cột ĐẦY ĐỦ (khớp thật, mirror diagnostic dump) — nhưng KHÔNG có mẫu THẬT nào (giả lập
# tình huống người dùng đã xoá sạch mọi chứng từ Ủy nhiệm thu trong MISA).
cols_badeposit = [("RefID","uniqueidentifier"),("BranchID","uniqueidentifier"),("RefType","int"),
    ("RefDate","datetime"),("PostedDate","datetime"),("RefNoFinance","nvarchar"),
    ("RefNoManagement","nvarchar"),("AccountObjectID","uniqueidentifier"),("AccountObjectName","nvarchar"),
    ("JournalMemo","nvarchar"),("RefOrder","int"),("TotalAmountOC","money"),("TotalAmount","money"),
    ("IsPostedFinance","bit"),("IsPostedManagement","bit"),("CreatedDate","datetime"),
    ("ModifiedDate","datetime"),("CustomField10","nvarchar"),("CurrencyID","nvarchar"),
    ("ExchangeRate","float"),("DisplayOnBook","int"),("ReasonTypeID","int"),
    ("BankAccountID","uniqueidentifier"),("BankName","nvarchar"),("CreatedBy","nvarchar"),
    ("ModifiedBy","nvarchar")]
cols_badepositdetail = [("BADepositDetailID","uniqueidentifier"),("RefID","uniqueidentifier"),
    ("AccountObjectID","uniqueidentifier"),("Description","nvarchar"),("DebitAccount","nvarchar"),
    ("CreditAccount","nvarchar"),("Amount","money"),("AmountOC","money")]
cols_generalledger = [("GeneralLedgerID","int"),("RefID","uniqueidentifier"),("RefType","int"),
    ("RefDetailID","uniqueidentifier"),
    ("RefNo","nvarchar"),("RefNo1","nvarchar"),("RefNo2","nvarchar"),("RefDate","datetime"),("RefDate1","datetime"),
    ("PostedDate","datetime"),("AccountNumber","nvarchar"),("CorrespondingAccountNumber","nvarchar"),
    ("AccountName","nvarchar"),("BankAccountID","uniqueidentifier"),("BankAccountNumber","nvarchar"),
    ("CurrencyID","nvarchar"),("ExchangeRate","float"),("MainConvertRate","float"),
    ("ExchangeRateOperator","nvarchar"),("RefTypeName","nvarchar"),
    ("DebitAmountOC","money"),("DebitAmount","money"),("CreditAmountOC","money"),("CreditAmount","money"),
    ("JournalMemo","nvarchar"),("Description","nvarchar"),("AccountObjectID","uniqueidentifier"),
    ("AccountObjectName","nvarchar"),("AccountObjectNameDI","nvarchar"),("AccountObjectCode","nvarchar"),
    ("AccountObjectTaxCode","nvarchar"),("BranchID","uniqueidentifier"),("RefOrder","int"),("EntryType","int")]
cols_accountobjectledger = [("AccountObjectLedgerID","int"),("RefID","uniqueidentifier"),("RefType","int"),
    ("RefDetailID","uniqueidentifier"),("AccountNumber","nvarchar"),("CorrespondingAccountNumber","nvarchar"),
    ("AccountName","nvarchar"),("CurrencyID","nvarchar"),("ExchangeRate","float"),
    ("MainConvertRate","float"),("ExchangeRateOperator","nvarchar"),("RefTypeName","nvarchar"),
    ("DebitAmountOC","money"),("DebitAmount","money"),("CreditAmountOC","money"),("CreditAmount","money"),
    ("JournalMemo","nvarchar"),("Description","nvarchar"),("AccountObjectID","uniqueidentifier"),
    ("AccountObjectCode","nvarchar"),("AccountObjectName","nvarchar"),("AccountObjectNameDI","nvarchar"),
    ("AccountObjectTaxCode","nvarchar"),("BranchID","uniqueidentifier"),("RefOrder","int"),
    ("PayKeyID","nvarchar"),("DebtKeyID","nvarchar"),("EntryType","int")]
cols_bdwl = [("RefID","uniqueidentifier"),("RefType","int"),("PostedDate","datetime"),("RefDate","datetime"),
    ("RefNoFinance","nvarchar"),("RefNoManagement","nvarchar"),("IsPostedFinance","bit"),
    ("IsPostedManagement","bit"),("AccountObjectID","uniqueidentifier"),("AccountObjectName","nvarchar"),
    ("BranchID","uniqueidentifier"),("JournalMemo","nvarchar"),("BankAccountID","uniqueidentifier"),
    ("BankName","nvarchar"),("CurrencyID","nvarchar"),("ExchangeRate","float"),("TotalAmountOC","money"),
    ("TotalAmount","money"),("RefOrder","int"),("CreatedDate","datetime"),("CreatedBy","nvarchar"),
    ("ModifiedDate","datetime"),("ModifiedBy","nvarchar"),("CustomField10","nvarchar"),("BAType","int"),
    ("ListTableName","nvarchar"),("RefTypeName","nvarchar")]
cols_cfl = [("CustomFieldLegerID","uniqueidentifier"),("RefDetailID","uniqueidentifier"),
    ("RefID","uniqueidentifier"),("IsPostToManagementBook","bit"),("BranchID","uniqueidentifier"),
    ("PostedDate","datetime"),("IsUpdateRedundant","bit")]
cols_bankaccount = [("BankAccountID","uniqueidentifier"),("BankName","nvarchar"),
    ("AccountNumber","nvarchar")]

def fake_cot_bang_that(cur, table):
    m = {"BADeposit": cols_badeposit, "BADepositDetail": cols_badepositdetail,
         "GeneralLedger": cols_generalledger, "AccountObjectLedger": cols_accountobjectledger,
         "BADepositWithdrawList": cols_bdwl, "CustomFieldLedger": cols_cfl,
         "BankAccount": cols_bankaccount}
    return {c.lower(): (c, t) for c, t in m.get(table, [])}

def fake_mau_dong_that(cur, table, where, params=()):
    return {}  # KHÔNG có chứng từ THẬT nào — mọi fallback đều trả rỗng

import re as _re

class FakeCursor:
    def __init__(self):
        self.inserted = {"BADeposit": [], "BADepositDetail": [], "GeneralLedger": [],
                         "AccountObjectLedger": [], "BADepositWithdrawList": [], "CustomFieldLedger": []}
        self.inserted_cols = {}

    def execute(self, sql, *params):
        params = params[0] if len(params) == 1 and isinstance(params[0], (tuple, list)) else params
        self._last_sql = sql
        self._last_params = params
        if sql.startswith("INSERT INTO"):
            table = sql.split(" ")[2]
            m = _re.match(r"INSERT INTO \S+ \(\[(.*?)\]\) VALUES", sql)
            cols = m.group(1).split("],[") if m else []
            self.inserted.setdefault(table, []).append(dict(zip(cols, params)))
            self.inserted_cols.setdefault(table, cols)
        return self

    def fetchall(self):
        sql = self._last_sql
        if "FROM AccountObject" in sql:
            return [("aid-abc", "0317009837", "KH001", "CONG TY ABC")]
        return []

    def fetchone(self):
        sql = self._last_sql
        # KHÔNG có chứng từ thật nào -> JOIN tìm ref_id_mau trả None
        if "JOIN" in sql and "CustomField10" in sql:
            return None
        if "FROM BADeposit WHERE RefID=?" in sql or "FROM BADepositDetail WHERE RefID=?" in sql:
            return None
        if "FROM GeneralLedger WHERE RefID=?" in sql or "FROM AccountObjectLedger WHERE RefID=?" in sql:
            return None
        if "FROM BADepositWithdrawList WHERE RefID=?" in sql or "FROM CustomFieldLedger WHERE RefID=?" in sql:
            return None
        if "OrganizationUnit" in sql:
            return ("branch-that",)
        if "FROM BankAccount" in sql:
            return ("bank-that", "Ngan hang ACB", "28071268")
        if "MAX([" in sql or "MAX(RefOrder" in sql:
            return (0,)
        return None

class FakeConn:
    def __init__(self, cur): self._cur = cur; self.autocommit = True
    def cursor(self): return self._cur
    def commit(self): self.committed = True
    def rollback(self): self.rolled_back = True
    def close(self): pass

cur = FakeCursor()
def fake_sql_connect(cid, database=None):
    return FakeConn(cur)

ns['_misa_cot_bang_that'] = fake_cot_bang_that
ns['_misa_mau_dong_that'] = fake_mau_dong_that
ns['_misa_sql_connect'] = fake_sql_connect
exec(extract_fn('_misa_bank_account_du_phong'), ns)
exec(extract_fn('_misa_khung_ghi_so_du_phong'), ns)
exec(extract_fn('_misa_ghi_thu_chi'), ns)
_misa_ghi_thu_chi = ns['_misa_ghi_thu_chi']

giao_dich = [{"so_ct": "UNT-DP-001", "ngay": "20/03/2026", "mst": "0317009837",
              "ten_doi_tuong": "CONG TY ABC", "dien_giai": "Test khong co mau that",
              "tk_doi_ung": "131", "so_tien": 3000000}]

r = _misa_ghi_thu_chi(1, "TESTDB", "unt", giao_dich, preview=False, ghi_de=False)
print("Result:", r)
assert r["so_them"] == 1, f"expected 1 created even with no real template, got {r['so_them']}"
assert r["co_ghi_so_cai"] is True, "khung du phong phai tu du dung du GL/AOL/BDWL"
print("PASS: import thanh cong du khong co chung tu that nao de nhan ban")

m_ins = cur.inserted["BADeposit"][0]
assert m_ins["RefType"] == 1500, f"RefType phai la 1500 cho UNT, got {m_ins['RefType']}"
assert m_ins["BranchID"] == "branch-that"
assert m_ins["BankAccountID"] == "bank-that"
assert m_ins["BankName"] == "Ngan hang ACB"
assert m_ins["CurrencyID"] == "VND"
assert m_ins["ExchangeRate"] == 1
assert m_ins["IsPostedFinance"] is True
assert m_ins["TotalAmountOC"] == 3000000
assert m_ins["ReasonTypeID"] is None, "ReasonTypeID phai de trong (khong doan mo)"
print("PASS: dong BADeposit du phong dung cau truc chuan")

d_ins = cur.inserted["BADepositDetail"][0]
assert d_ins["DebitAccount"] == "1121"
assert d_ins["CreditAccount"] == "131"
assert d_ins["Amount"] == 3000000
print("PASS: dong BADepositDetail du phong dung TK No/Co")

gl_ins = cur.inserted["GeneralLedger"]
assert len(gl_ins) == 2
by_acc = {g["AccountNumber"]: g for g in gl_ins}
assert by_acc["1121"]["DebitAmountOC"] == 3000000 and by_acc["1121"]["CreditAmountOC"] == 0
assert by_acc["131"]["CreditAmountOC"] == 3000000 and by_acc["131"]["DebitAmountOC"] == 0
for g in gl_ins:
    assert g["ExchangeRateOperator"] == "*", "cot NOT NULL phai co gia tri (loi that da gap)"
    assert g["CurrencyID"] == "VND"
    assert g["ExchangeRate"] == 1 and g["MainConvertRate"] == 1
    assert g["RefTypeName"] == "Thu tiền gửi"
    assert g["RefType"] == 1500, f"RefType phai la 1500 (loi that da gap: RefType=0 khien XEM/XOA loi)"
    assert g["BankAccountID"] == "bank-that"
    assert g["BankAccountNumber"] == "28071268"
assert by_acc["1121"]["AccountName"] == "Tiền Việt Nam"
assert by_acc["131"]["AccountName"] == "Phải thu của khách hàng"
print("PASS: 2 dong GeneralLedger du phong dung ghi kep, day du cot NOT NULL")

aol_ins = cur.inserted["AccountObjectLedger"][0]
assert aol_ins["AccountNumber"] == "131"
assert aol_ins["CreditAmountOC"] == 3000000 and aol_ins["DebitAmountOC"] == 0
assert aol_ins["ExchangeRateOperator"] == "*"
assert aol_ins["RefTypeName"] == "Thu tiền gửi"
assert aol_ins["RefType"] == 1500
print("PASS: dong AccountObjectLedger du phong dung, day du cot NOT NULL")

bdwl_ins = cur.inserted["BADepositWithdrawList"][0]
assert bdwl_ins["ListTableName"] == "BADeposit"
assert bdwl_ins["RefTypeName"] == "Thu tiền gửi"
assert bdwl_ins["RefType"] == 1500
assert bdwl_ins["BAType"] == 0
assert bdwl_ins["TotalAmountOC"] == 3000000
print("PASS: dong BADepositWithdrawList du phong dung — day la bang nguon LUOI liet ke")

print("\nALL DONE")

# --- Regression test riêng cho lỗi thật đã gặp: BankName để trống trên BADeposit/BAWithDraw dù
# BankAccountID vẫn đúng (màn XEM chi tiết của MISA báo lỗi ép kiểu DBNull->String). Mô phỏng:
# bảng BankAccount không dò được đúng tên cột lưu tên ngân hàng (trả None), NHƯNG có sẵn 1 dòng
# BADeposit thật (không do phần mềm ghi) đã có đủ BankAccountID + BankName -> phải MƯỢN được từ
# đó thay vì trả về None.
_misa_bank_account_du_phong = ns['_misa_bank_account_du_phong']

class FakeCursor2:
    def execute(self, sql, *params):
        self._last_sql = sql
        return self
    def fetchone(self):
        sql = self._last_sql
        if "FROM BADeposit WHERE BankAccountID IS NOT NULL AND BankName IS NOT NULL" in sql:
            return ("real-bank-id", "Ngân hàng TMCP Á Châu")
        # Lookup so TK (nice-to-have, bọc try/except ở source) -> khong co du lieu la binh thuong
        return None

r = _misa_bank_account_du_phong(FakeCursor2())
assert r[0] == "real-bank-id" and r[1] == "Ngân hàng TMCP Á Châu", \
    f"phai muon duoc BankAccountID/BankName tu BADeposit that, got {r}"
print("PASS: _misa_bank_account_du_phong muon dung BankAccountID/BankName tu 1 dong BADeposit that co san")

# --- Regression test riêng cho lỗi thật đợt 6: ReasonTypeID để NULL trên Master (dù đã sửa xong
# BankName ở cả 2 bảng) khiến bấm XEM/XOÁ vẫn báo lỗi DBNull->String y hệt — rất có thể do JOIN
# sang bảng "Lý do thu/chi" để lấy tên hiển thị, NULL không JOIN được. Xác nhận
# _misa_reason_type_du_phong mượn đúng giá trị có sẵn thay vì để trống.
_misa_reason_type_du_phong = ns['_misa_reason_type_du_phong']

class FakeCursor3:
    def execute(self, sql, *params):
        self._last_sql = sql
        return self
    def fetchone(self):
        if "SELECT TOP 1 ReasonTypeID FROM BADeposit WHERE ReasonTypeID IS NOT NULL AND ReasonTypeID<>0" in self._last_sql:
            return (34,)
        return None

r = _misa_reason_type_du_phong(FakeCursor3(), "BADeposit")
assert r == 34, f"phai muon duoc ReasonTypeID that su dang dung (34), got {r}"
print("PASS: _misa_reason_type_du_phong muon dung gia tri co san thay vi de trong")

