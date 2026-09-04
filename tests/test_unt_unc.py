import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys, re, datetime
sys.path.insert(0, _REPO_ROOT)

# Extract just the functions we need, avoiding importing the whole server.py
# (which has heavy side effects: FastAPI app, license checks, etc.)
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

def extract_fn(name):
    idx = src.index('def ' + name + '(')
    i = src.index(':', idx)
    # find end: next top-level "def " or "@app" at column 0 after this point
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

ns = {
    'datetime': datetime,
    'HTTPException': FakeHTTPException,
    '_PM_MARK': 'HDDT-AUTO',
    '_TEN_TK_KE_TOAN_CHUAN': {"1121": "Tiền Việt Nam", "131": "Phải thu của khách hàng",
                              "331": "Phải trả cho người bán"},
}
for n in names:
    code = extract_fn(n)
    exec(code, ns)

_misa_ghi_thu_chi = ns['_misa_ghi_thu_chi']

# ---- Fake pyodbc-like cursor/connection ----
class FakeCursor:
    def __init__(self, tables, account_objects, existing_customfield10):
        self.tables = tables  # {table_name_lower: [(col, sqltype), ...]}
        self.account_objects = account_objects  # list of (aid, taxcode, code, name)
        self.existing = existing_customfield10  # list of RefNoFinance already marked by us
        self.inserted = {'BADeposit': [], 'BADepositDetail': [], 'BAWithDraw': [], 'BAWithDrawDetail': []}

    def execute(self, sql, *params):
        params = params[0] if len(params) == 1 and isinstance(params[0], (tuple, list)) else params
        self._last_sql = sql
        self._last_params = params
        return self

    def fetchall(self):
        sql = self._last_sql
        if 'sys.columns' in sql:
            # _misa_cot_bang_that: table name is passed as param
            table = self._last_params[0] if isinstance(self._last_params, (list, tuple)) else self._last_params
            cols = self.tables.get(table.lower(), [])
            return [(c, t) for c, t in cols]
        if 'FROM AccountObject' in sql:
            return self.account_objects
        if 'RefNoFinance FROM' in sql and 'CustomField10' in sql:
            return [(rn,) for rn in self.existing]
        return []

    def fetchone(self):
        sql = self._last_sql
        if 'MAX([' in sql or 'MAX(RefOrder' in sql:
            return (10,)
        if 'OrganizationUnit' in sql:
            return ('branch-1',)
        return None

class FakeConn:
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

# Monkeypatch _misa_sql_connect + _misa_mau_dong_that behavior via injecting into module-level ns
# _misa_mau_dong_that uses cur.execute(sql, tham_so) with sys.columns + a WHERE-filtered SELECT TOP 5.
# We need it to return a plausible "real row" dict for BADeposit/BADepositDetail/BAWithDraw/BAWithDrawDetail.

# Simpler: monkeypatch _misa_mau_dong_that and _misa_cot_bang_that directly with controlled fakes,
# since faithfully faking the "TOP 5 [...]" dynamic SQL is complex.
cols_badeposit = [
    ("RefID", "uniqueidentifier"), ("BranchID", "uniqueidentifier"), ("RefDate", "datetime"),
    ("PostedDate", "datetime"), ("RefNoFinance", "nvarchar"), ("RefNoManagement", "nvarchar"),
    ("AccountObjectID", "uniqueidentifier"), ("AccountObjectName", "nvarchar"),
    ("JournalMemo", "nvarchar"), ("RefOrder", "int"), ("TotalAmountOC", "money"),
    ("TotalAmount", "money"), ("IsPostedFinance", "bit"), ("IsPostedManagement", "bit"),
    ("CreatedDate", "datetime"), ("ModifiedDate", "datetime"), ("CustomField10", "nvarchar"),
    ("CurrencyID", "nvarchar"), ("ExchangeRate", "float"),
]
cols_badepositdetail = [
    ("BADepositDetailID", "uniqueidentifier"), ("RefID", "uniqueidentifier"),
    ("AccountObjectID", "uniqueidentifier"), ("Description", "nvarchar"),
    ("CreditAccount", "nvarchar"), ("Amount", "money"), ("AmountOC", "money"),
]
cols_bawithdraw = [
    ("RefID", "uniqueidentifier"), ("BranchID", "uniqueidentifier"), ("RefDate", "datetime"),
    ("PostedDate", "datetime"), ("RefNoFinance", "nvarchar"), ("RefNoManagement", "nvarchar"),
    ("AccountObjectID", "uniqueidentifier"), ("AccountObjectName", "nvarchar"),
    ("JournalMemo", "nvarchar"), ("RefOrder", "int"), ("TotalAmountOC", "money"),
    ("TotalAmount", "money"), ("IsPostedFinance", "bit"), ("IsPostedManagement", "bit"),
    ("CreatedDate", "datetime"), ("ModifiedDate", "datetime"), ("CustomField10", "nvarchar"),
    ("CurrencyID", "nvarchar"), ("ExchangeRate", "float"),
]
cols_bawithdrawdetail = [
    ("BAWithDrawDetailID", "uniqueidentifier"), ("RefID", "uniqueidentifier"),
    ("AccountObjectID", "uniqueidentifier"), ("Description", "nvarchar"),
    ("DebitAccount", "nvarchar"), ("Amount", "money"), ("AmountOC", "money"),
]

def fake_cot_bang_that(cur, table):
    m = {
        "BADeposit": cols_badeposit, "BADepositDetail": cols_badepositdetail,
        "BAWithDraw": cols_bawithdraw, "BAWithDrawDetail": cols_bawithdrawdetail,
    }
    return {c.lower(): (c, t) for c, t in m.get(table, [])}

def fake_mau_dong_that(cur, table, where, params=()):
    templates = {
        "BADeposit": {"RefID": "old-id", "BranchID": "branch-1", "RefDate": datetime.datetime(2025,1,1),
                      "RefNoFinance": "UNT_OLD", "AccountObjectID": "old-aid", "AccountObjectName": "OLD",
                      "JournalMemo": "old memo", "RefOrder": 5, "TotalAmountOC": 100, "TotalAmount": 100,
                      "IsPostedFinance": True, "IsPostedManagement": True, "CustomField10": None,
                      "CurrencyID": "VND", "ExchangeRate": 1},
        "BADepositDetail": {"BADepositDetailID": "old-d", "RefID": "old-id", "AccountObjectID": "old-aid",
                             "Description": "old", "CreditAccount": "131", "Amount": 100, "AmountOC": 100},
        "BAWithDraw": {"RefID": "old-id2", "BranchID": "branch-1", "RefDate": datetime.datetime(2025,1,1),
                       "RefNoFinance": "UNC_OLD", "AccountObjectID": "old-aid2", "AccountObjectName": "OLD2",
                       "JournalMemo": "old memo2", "RefOrder": 3, "TotalAmountOC": 50, "TotalAmount": 50,
                       "IsPostedFinance": True, "IsPostedManagement": True, "CustomField10": None,
                       "CurrencyID": "VND", "ExchangeRate": 1},
        "BAWithDrawDetail": {"BAWithDrawDetailID": "old-d2", "RefID": "old-id2", "AccountObjectID": "old-aid2",
                              "Description": "old", "DebitAccount": "331", "Amount": 50, "AmountOC": 50},
    }
    return dict(templates.get(table, {}))

ns['_misa_cot_bang_that'] = fake_cot_bang_that
ns['_misa_mau_dong_that'] = fake_mau_dong_that
exec(extract_fn('_misa_ghi_thu_chi'), ns)  # re-exec with patched deps in scope
_misa_ghi_thu_chi = ns['_misa_ghi_thu_chi']

import types
def fake_sql_connect(cid, database=None):
    account_objects = [
        ("aid-abc", "0317009837", "KH001", "CONG TY ABC"),
        ("aid-xyz", "0301111222", "KH002", "CONG TY XYZ"),
    ]
    cur = FakeCursor({}, account_objects, existing_customfield10=["UNT-005"])
    return FakeConn(cur)

ns['_misa_sql_connect'] = fake_sql_connect
exec(extract_fn('_misa_ghi_thu_chi'), ns)
_misa_ghi_thu_chi = ns['_misa_ghi_thu_chi']

# --- Test 1: normal UNT import, 1 known customer + 1 unknown MST + 1 duplicate ---
giao_dich = [
    {"so_ct": "UNT-001", "ngay": "12/09/2025", "mst": "0317009837", "ten_doi_tuong": "CONG TY ABC",
     "dien_giai": "Thu tien hang", "tk_doi_ung": "131", "so_tien": 1000000},
    {"so_ct": "UNT-002", "ngay": "13/09/2025", "mst": "9999999999", "ten_doi_tuong": "KHONG CO TRONG DM",
     "dien_giai": "Thu tien la", "tk_doi_ung": "131", "so_tien": 500000},
    {"so_ct": "UNT-005", "ngay": "14/09/2025", "mst": "0301111222", "ten_doi_tuong": "CONG TY XYZ",
     "dien_giai": "Da ghi truoc do", "tk_doi_ung": "131", "so_tien": 2000000},
]
r = _misa_ghi_thu_chi(1, "TESTDB", "unt", giao_dich, preview=True, ghi_de=False)
print("Test1 result:", r)
assert r["so_them"] == 1, f"expected 1 created, got {r['so_them']}"
assert r["so_bo_qua_kh"] == 1, f"expected 1 skipped (unknown MST), got {r['so_bo_qua_kh']}"
assert r["so_trung"] == 1, f"expected 1 skipped (duplicate), got {r['so_trung']}"
print("PASS: Test1 (skip unknown MST + skip duplicate + create 1 new)")

# --- Test 2: UNC path uses correct table/account ---
giao_dich2 = [
    {"so_ct": "UNC-100", "ngay": "01/10/2025", "mst": "0317009837", "ten_doi_tuong": "CONG TY ABC",
     "dien_giai": "Chi tien NCC", "tk_doi_ung": "331", "so_tien": 750000},
]
r2 = _misa_ghi_thu_chi(1, "TESTDB", "unc", giao_dich2, preview=True, ghi_de=False)
print("Test2 result:", r2)
assert r2["so_them"] == 1
assert r2["loai"] == "unc"
print("PASS: Test2 (UNC create)")

# --- Test 3: invalid loai raises ---
try:
    _misa_ghi_thu_chi(1, "TESTDB", "wrong", [], preview=True)
    print("FAIL: should have raised for invalid loai")
except FakeHTTPException as e:
    print("PASS: Test3 (invalid loai rejected):", e.msg)

print("\nALL DONE")
