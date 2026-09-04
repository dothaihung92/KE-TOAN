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
         '_snum', '_to_num', '_misa_bank_account_du_phong', '_misa_reason_type_du_phong',
         '_misa_reason_type_hop_le', '_misa_dam_bao_hop_le_ngan_hang_ly_do', '_misa_ghi_thu_chi']

class FakeHTTPException(Exception):
    def __init__(self, code, msg):
        self.code = code; self.msg = msg
        super().__init__(f"{code}: {msg}")

ns = {'datetime': datetime, 'HTTPException': FakeHTTPException, '_PM_MARK': 'HDDT-AUTO'}
for n in names:
    exec(extract_fn(n), ns)

# --- Schemas mirroring the REAL diagnostic dump (subset of columns, enough to exercise the logic) ---
cols_badeposit = [("RefID","uniqueidentifier"),("BranchID","uniqueidentifier"),("RefDate","datetime"),
    ("PostedDate","datetime"),("RefNoFinance","nvarchar"),("RefNoManagement","nvarchar"),
    ("AccountObjectID","uniqueidentifier"),("AccountObjectName","nvarchar"),("JournalMemo","nvarchar"),
    ("RefOrder","int"),("TotalAmountOC","money"),("TotalAmount","money"),
    ("IsPostedFinance","bit"),("IsPostedManagement","bit"),("CreatedDate","datetime"),
    ("ModifiedDate","datetime"),("CustomField10","nvarchar")]
cols_badepositdetail = [("BADepositDetailID","uniqueidentifier"),("RefID","uniqueidentifier"),
    ("AccountObjectID","uniqueidentifier"),("Description","nvarchar"),("CreditAccount","nvarchar"),
    ("Amount","money"),("AmountOC","money")]
cols_generalledger = [("GeneralLedgerID","int"),("RefID","uniqueidentifier"),("RefDetailID","uniqueidentifier"),
    ("RefNo","nvarchar"),("RefNo1","nvarchar"),("RefNo2","nvarchar"),("RefDate","datetime"),("RefDate1","datetime"),
    ("PostedDate","datetime"),("AccountNumber","nvarchar"),("CorrespondingAccountNumber","nvarchar"),
    ("DebitAmountOC","money"),("DebitAmount","money"),("CreditAmountOC","money"),("CreditAmount","money"),
    ("JournalMemo","nvarchar"),("Description","nvarchar"),("AccountObjectID","uniqueidentifier"),
    ("AccountObjectName","nvarchar"),("AccountObjectNameDI","nvarchar"),("AccountObjectCode","nvarchar"),
    ("AccountObjectTaxCode","nvarchar"),("BranchID","uniqueidentifier"),("RefOrder","int"),("EntryType","int")]
cols_accountobjectledger = [("AccountObjectLedgerID","int"),("RefID","uniqueidentifier"),
    ("RefDetailID","uniqueidentifier"),("AccountNumber","nvarchar"),("DebitAmountOC","money"),
    ("DebitAmount","money"),("CreditAmountOC","money"),("CreditAmount","money"),("JournalMemo","nvarchar"),
    ("Description","nvarchar"),("AccountObjectID","uniqueidentifier"),("AccountObjectCode","nvarchar"),
    ("AccountObjectName","nvarchar"),("AccountObjectNameDI","nvarchar"),("AccountObjectTaxCode","nvarchar"),
    ("BranchID","uniqueidentifier"),("RefOrder","int"),("PayKeyID","nvarchar"),("DebtKeyID","nvarchar"),
    ("EntryType","int"),("RefNo","nvarchar"),("PostedDate","datetime"),("RefDate","datetime")]
cols_bdwl = [("RefID","uniqueidentifier"),("PostedDate","datetime"),("RefDate","datetime"),
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

def fake_cot_bang_that(cur, table):
    m = {"BADeposit": cols_badeposit, "BADepositDetail": cols_badepositdetail,
         "GeneralLedger": cols_generalledger, "AccountObjectLedger": cols_accountobjectledger,
         "BADepositWithdrawList": cols_bdwl, "CustomFieldLedger": cols_cfl}
    return {c.lower(): (c, t) for c, t in m.get(table, [])}

REAL_M_ID = "1D5EDD79-E8F3-4787-8D38-29DB26511379"
REAL_D_ID = "2949FC6B-6093-4C6B-A077-69F8564C3E3B"

def fake_mau_dong_that(cur, table, where, params=()):
    if table == "BADepositDetail":
        return {"BADepositDetailID": REAL_D_ID, "RefID": REAL_M_ID, "AccountObjectID": "old-aid",
                "Description": "old", "CreditAccount": "131", "Amount": 1155000, "AmountOC": 1155000}
    if table == "BADeposit":
        return {"RefID": REAL_M_ID, "BranchID": "branch-1", "RefDate": datetime.datetime(2025,9,12),
                "RefNoFinance": "NTTK00001", "AccountObjectID": "old-aid", "AccountObjectName": "OLD",
                "JournalMemo": "old memo", "RefOrder": 6, "TotalAmountOC": 1155000, "TotalAmount": 1155000,
                "IsPostedFinance": True, "IsPostedManagement": False, "CustomField10": None}
    return {}

class FakeCursor:
    def __init__(self):
        self.gl_store = {
            REAL_M_ID: [
                {"GeneralLedgerID": 1011, "RefID": REAL_M_ID, "RefDetailID": REAL_D_ID, "RefNo": "NTTK00001",
                 "RefNo1": "NTTK00001", "RefNo2": "NTTK00001", "RefDate": datetime.datetime(2025,9,12),
                 "RefDate1": datetime.datetime(2025,9,12), "PostedDate": datetime.datetime(2025,9,12),
                 "AccountNumber": "1121", "CorrespondingAccountNumber": "131",
                 "DebitAmountOC": 1155000, "DebitAmount": 1155000, "CreditAmountOC": 0, "CreditAmount": 0,
                 "JournalMemo": "m", "Description": "m", "AccountObjectID": "old-aid",
                 "AccountObjectName": "OLD", "AccountObjectNameDI": "OLD", "AccountObjectCode": "OLDCODE",
                 "AccountObjectTaxCode": "0318899822", "BranchID": "branch-1", "RefOrder": 6, "EntryType": 1},
                {"GeneralLedgerID": 1012, "RefID": REAL_M_ID, "RefDetailID": REAL_D_ID, "RefNo": "NTTK00001",
                 "RefNo1": "NTTK00001", "RefNo2": "NTTK00001", "RefDate": datetime.datetime(2025,9,12),
                 "RefDate1": datetime.datetime(2025,9,12), "PostedDate": datetime.datetime(2025,9,12),
                 "AccountNumber": "131", "CorrespondingAccountNumber": "1121",
                 "DebitAmountOC": 0, "DebitAmount": 0, "CreditAmountOC": 1155000, "CreditAmount": 1155000,
                 "JournalMemo": "m", "Description": "m", "AccountObjectID": "old-aid",
                 "AccountObjectName": "OLD", "AccountObjectNameDI": "OLD", "AccountObjectCode": "OLDCODE",
                 "AccountObjectTaxCode": "0318899822", "BranchID": "branch-1", "RefOrder": 6, "EntryType": 2},
            ]
        }
        self.aol_store = {
            REAL_M_ID: {"AccountObjectLedgerID": 433, "RefID": REAL_M_ID, "RefDetailID": REAL_D_ID,
                        "AccountNumber": "131", "DebitAmountOC": 0, "DebitAmount": 0,
                        "CreditAmountOC": 1155000, "CreditAmount": 1155000, "JournalMemo": "m",
                        "Description": "m", "AccountObjectID": "old-aid", "AccountObjectCode": "OLDCODE",
                        "AccountObjectName": "OLD", "AccountObjectNameDI": "OLD",
                        "AccountObjectTaxCode": "0318899822", "BranchID": "branch-1", "RefOrder": 6,
                        "PayKeyID": "old#pay", "DebtKeyID": "old#debt", "EntryType": 2,
                        "RefNo": "NTTK00001", "PostedDate": datetime.datetime(2025,9,12),
                        "RefDate": datetime.datetime(2025,9,12)}
        }
        self.bdwl_store = {
            REAL_M_ID: {"RefID": REAL_M_ID, "PostedDate": datetime.datetime(2025,9,12),
                        "RefDate": datetime.datetime(2025,9,12), "RefNoFinance": "NTTK00001",
                        "RefNoManagement": None, "IsPostedFinance": True, "IsPostedManagement": False,
                        "AccountObjectID": "old-aid", "AccountObjectName": "OLD", "BranchID": "branch-1",
                        "JournalMemo": "old memo", "BankAccountID": "bank-1", "BankName": "ACB",
                        "CurrencyID": "VND", "ExchangeRate": 1, "TotalAmountOC": 1155000,
                        "TotalAmount": 1155000, "RefOrder": 6, "CreatedDate": datetime.datetime(2025,9,12),
                        "CreatedBy": "ADMIN", "ModifiedDate": datetime.datetime(2025,9,12),
                        "ModifiedBy": "ADMIN", "CustomField10": None, "BAType": 0,
                        "ListTableName": "BADeposit", "RefTypeName": "Thu tiền gửi"}
        }
        self.cfl_store = {
            REAL_M_ID: {"CustomFieldLegerID": "old-cfl-id", "RefDetailID": REAL_D_ID, "RefID": REAL_M_ID,
                        "IsPostToManagementBook": False, "BranchID": "branch-1",
                        "PostedDate": datetime.datetime(2025,9,12), "IsUpdateRedundant": True}
        }
        self.inserted = {"BADeposit": [], "BADepositDetail": [], "GeneralLedger": [], "AccountObjectLedger": [],
                         "BADepositWithdrawList": [], "CustomFieldLedger": []}

    def execute(self, sql, *params):
        params = params[0] if len(params) == 1 and isinstance(params[0], (tuple, list)) else params
        self._last_sql = sql
        self._last_params = params
        if sql.startswith("INSERT INTO"):
            table = sql.split(" ")[2]
            self.inserted.setdefault(table, []).append(params)
        return self

    def fetchall(self):
        sql = self._last_sql
        if "FROM GeneralLedger WHERE RefID=?" in sql:
            refid = self._last_params[0]
            return [tuple(row.values()) for row in self.gl_store.get(refid, [])]
        if "AccountObject" in sql and "FROM AccountObject" in sql:
            return [("aid-abc", "0317009837", "KH001", "CONG TY ABC")]
        if "RefNoFinance FROM" in sql and "CustomField10" in sql:
            return []
        return []

    def fetchone(self):
        sql = self._last_sql
        if "JOIN" in sql and "CustomField10" in sql:
            return (REAL_M_ID,)
        if sql.startswith("SELECT [") and "FROM BADepositDetail WHERE RefID=?" in sql:
            d = fake_mau_dong_that(None, "BADepositDetail", "")
            cols = [c for c in cols_badepositdetail]
            names = [c[0] for c in cols]
            return tuple(d.get(n) for n in names)
        if sql.startswith("SELECT [") and "FROM BADeposit WHERE RefID=?" in sql:
            m = fake_mau_dong_that(None, "BADeposit", "")
            names = [c[0] for c in cols_badeposit]
            return tuple(m.get(n) for n in names)
        if "FROM AccountObjectLedger WHERE RefID=?" in sql:
            refid = self._last_params[0]
            row = self.aol_store.get(refid)
            return tuple(row.values()) if row else None
        if "FROM BADepositWithdrawList WHERE RefID=?" in sql:
            refid = self._last_params[0]
            row = self.bdwl_store.get(refid)
            return tuple(row.values()) if row else None
        if "FROM CustomFieldLedger WHERE RefID=?" in sql:
            refid = self._last_params[0]
            row = self.cfl_store.get(refid)
            return tuple(row.values()) if row else None
        if "MAX([" in sql or "MAX(RefOrder" in sql:
            return (6,)
        if "OrganizationUnit" in sql:
            return ("branch-1",)
        return None

class FakeConn:
    def __init__(self, cur):
        self._cur = cur; self.autocommit = True
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
exec(extract_fn('_misa_ghi_thu_chi'), ns)
_misa_ghi_thu_chi = ns['_misa_ghi_thu_chi']

giao_dich = [{"so_ct": "UNT-NEW-001", "ngay": "15/03/2026", "mst": "0317009837",
              "ten_doi_tuong": "CONG TY ABC", "dien_giai": "Test thu tien",
              "tk_doi_ung": "131", "so_tien": 5000000}]

r = _misa_ghi_thu_chi(1, "TESTDB", "unt", giao_dich, preview=False, ghi_de=False)
print("Result:", r)
assert r["so_them"] == 1, "should create 1"
assert r["co_ghi_so_cai"] is True, "should have found GL/AOL templates"

# Inspect what actually got inserted
gl_inserts = cur.inserted["GeneralLedger"]
aol_inserts = cur.inserted["AccountObjectLedger"]
print(f"\nGeneralLedger inserts: {len(gl_inserts)}")
print(f"AccountObjectLedger inserts: {len(aol_inserts)}")
assert len(gl_inserts) == 2, f"expected 2 GL rows, got {len(gl_inserts)}"
assert len(aol_inserts) == 1, f"expected 1 AOL row, got {len(aol_inserts)}"

# Reconstruct the inserted GL rows as dicts using the same column order as the last INSERT SQL
# (columns are in m_row.keys()/g.keys() order which came from mau_gl dict order = original store order)
gl_cols = list(cur.gl_store[REAL_M_ID][0].keys())  # both real rows have same key order
for i, params in enumerate(gl_inserts):
    d = dict(zip(gl_cols, params))
    print(f"\nGL row #{i+1}: AccountNumber={d.get('AccountNumber')} Debit={d.get('DebitAmountOC')} Credit={d.get('CreditAmountOC')} RefID={d.get('RefID')}")
    assert d["RefID"] == d.get("RefID"), "sanity"

# Verify: row with AccountNumber=1121 should have Debit=5000000, Credit=0; row with 131 should have Credit=5000000, Debit=0
by_acc = {dict(zip(gl_cols, p))["AccountNumber"]: dict(zip(gl_cols, p)) for p in gl_inserts}
assert by_acc["1121"]["DebitAmountOC"] == 5000000 and by_acc["1121"]["CreditAmountOC"] == 0
assert by_acc["131"]["CreditAmountOC"] == 5000000 and by_acc["131"]["DebitAmountOC"] == 0
print("\nPASS: double-entry amounts correctly assigned per account side")

aol_cols = list(cur.aol_store[REAL_M_ID].keys())
aol_d = dict(zip(aol_cols, aol_inserts[0]))
print(f"\nAOL row: AccountNumber={aol_d.get('AccountNumber')} Credit={aol_d.get('CreditAmountOC')} PayKeyID={aol_d.get('PayKeyID')}")
assert aol_d["CreditAmountOC"] == 5000000
assert aol_d["AccountObjectID"] == "aid-abc"
assert aol_d["PayKeyID"].startswith(aol_d["RefID"]) if "RefID" in aol_d else True
print("PASS: AccountObjectLedger amounts + PayKeyID correctly computed")

# --- BADepositWithdrawList / CustomFieldLedger (đợt 3 — bảng nguồn LƯỚI liệt kê) ---
bdwl_inserts = cur.inserted["BADepositWithdrawList"]
cfl_inserts = cur.inserted["CustomFieldLedger"]
assert len(bdwl_inserts) == 1, f"expected 1 BADepositWithdrawList row, got {len(bdwl_inserts)}"
assert len(cfl_inserts) == 1, f"expected 1 CustomFieldLedger row, got {len(cfl_inserts)}"
bdwl_cols = list(cur.bdwl_store[REAL_M_ID].keys())
bdwl_d = dict(zip(bdwl_cols, bdwl_inserts[0]))
print(f"\nBADepositWithdrawList row: RefNoFinance={bdwl_d.get('RefNoFinance')} TotalAmountOC={bdwl_d.get('TotalAmountOC')} IsPostedFinance={bdwl_d.get('IsPostedFinance')} ListTableName={bdwl_d.get('ListTableName')}")
assert bdwl_d["RefNoFinance"] == "UNT-NEW-001"
assert bdwl_d["TotalAmountOC"] == 5000000
assert bdwl_d["IsPostedFinance"] is True
assert bdwl_d["AccountObjectID"] == "aid-abc"
assert bdwl_d["ListTableName"] == "BADeposit", "phải giữ nguyên từ mẫu (không tự đoán)"
cfl_cols = list(cur.cfl_store[REAL_M_ID].keys())
cfl_d = dict(zip(cfl_cols, cfl_inserts[0]))
print(f"CustomFieldLedger row: RefID={cfl_d.get('RefID')} IsUpdateRedundant={cfl_d.get('IsUpdateRedundant')}")
assert cfl_d["IsUpdateRedundant"] is True
print("PASS: BADepositWithdrawList + CustomFieldLedger correctly written")

print("\nALL DONE")
