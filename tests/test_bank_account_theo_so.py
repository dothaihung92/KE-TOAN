import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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


class FakeCursor:
    def __init__(self, bank_accounts):
        # bank_accounts: list of (BankAccountID, AccountNumber, BankName)
        self.bank_accounts = bank_accounts

    def execute(self, sql, params=()):
        if "sys.columns" in sql:
            # _misa_cot_bang_that queries sys.columns JOIN sys.types -> (name, type) rows
            self._result = [("BankAccountID", "uniqueidentifier"), ("AccountNumber", "nvarchar"), ("BankName", "nvarchar")]
        elif "FROM BankAccount" in sql:
            self._result = self.bank_accounts
        else:
            self._result = []
        return self

    def fetchone(self):
        return self._result[0] if self._result else None

    def fetchall(self):
        return self._result


ns = {}
# Need _misa_cot_bang_that and _misa_chon_cot — extract real implementations
exec(extract_fn('_misa_cot_bang_that'), ns)
exec(extract_fn('_misa_chon_cot'), ns)
exec(extract_fn('_misa_bank_account_theo_so'), ns)
_misa_bank_account_theo_so = ns['_misa_bank_account_theo_so']

cur = FakeCursor([
    ("id-vcb", "0011002233", "Vietcombank"),
    ("id-acb", "28071268", "Ngân hàng TMCP Á Châu"),
    ("id-mb", "999-888-77", "MBBank"),
])

# Test 1: exact match
bid, bname = _misa_bank_account_theo_so(cur, "28071268")
assert bid == "id-acb" and bname == "Ngân hàng TMCP Á Châu", (bid, bname)
print("PASS Test 1: khop dung so tai khoan chinh xac")

# Test 2: match with dashes/spaces in input
bid, bname = _misa_bank_account_theo_so(cur, "999 888 77")
assert bid == "id-mb", bid
print("PASS Test 2: khop dung khi input co khoang trang (chuan hoa dung)")

bid, bname = _misa_bank_account_theo_so(cur, "999-888-77")
assert bid == "id-mb", bid
print("PASS Test 2b: khop dung khi input co gach ngang")

# Test 3: no match
bid, bname = _misa_bank_account_theo_so(cur, "0000000000")
assert bid is None and bname is None, (bid, bname)
print("PASS Test 3: khong khop -> None, None")

# Test 4: empty input
bid, bname = _misa_bank_account_theo_so(cur, "")
assert bid is None and bname is None
bid, bname = _misa_bank_account_theo_so(cur, None)
assert bid is None and bname is None
print("PASS Test 4: input rong -> None, None (khong loi)")

print("\nALL DONE")
