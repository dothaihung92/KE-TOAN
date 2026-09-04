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
        self.code = code; self.msg = msg; self.detail = msg
        super().__init__(f"{code}: {msg}")

class FakeCursor:
    def __init__(self):
        self.gl_balance = 0
        self.gl_opening_balance = 0
        self.gl_detail = []   # list of (RefNo, DebitAmount, CreditAmount)
        self.last_sql = None

    def execute(self, sql, params=()):
        self.last_sql = sql
        if "SUM(DebitAmount)" in sql:
            if "RefDate<?" in sql:   # số dư ĐẦU kỳ (< tu_ngay, khong co dau =)
                self._result = [(self.gl_opening_balance,)]
            else:                     # số dư CUỐI kỳ (<= den_ngay)
                self._result = [(self.gl_balance,)]
        elif "SELECT RefNo, DebitAmount, CreditAmount FROM GeneralLedger" in sql:
            self._result = list(self.gl_detail)
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


ns = {'datetime': datetime, 'HTTPException': FakeHTTPException}
def snum(v):
    try:
        return float(v)
    except Exception:
        return 0
ns['_snum'] = snum
exec(extract_fn('_misa_doi_chieu_so_du_nh'), ns)
_misa_doi_chieu_so_du_nh = ns['_misa_doi_chieu_so_du_nh']

cur = FakeCursor()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur)

# Test 1: khop (balance matches expected within 1 dong)
cur.gl_balance = 131230650
r1 = _misa_doi_chieu_so_du_nh(1, "TESTDB", "1121", datetime.datetime(2025, 9, 30), 131230650)
assert r1["khop"] is True, r1
assert r1["lech"] == 0
print("PASS Test 1: khop dung khi so du MISA == ky vong")

# Test 2: lech, khong co giao_dich_pm -> chi tra ve lech, khong doi chieu chi tiet
r2 = _misa_doi_chieu_so_du_nh(1, "TESTDB", "1121", datetime.datetime(2025, 9, 30), 100000000)
assert r2["khop"] is False
assert r2["lech"] == 31230650
assert "chi_o_pm" not in r2
print("PASS Test 2: lech dung, khong doi chieu khi thieu giao_dich_pm")

# Test 3: lech + co giao_dich_pm -> doi chieu chi tiet dung 3 nhom (nay doc tu GeneralLedger,
# KHONG con doc BADeposit/BAWithDraw - bug cu: CreditAccount/DebitAccount tren 2 bang detail do
# thuc ra la TK DOI UNG 131/331, khong phai TK ngan hang, nen truoc day luon bao "MISA khong thay"
# oan cho toan bo chung tu du da co that trong MISA).
cur.gl_detail = [("UNT001", 1000000, 0), ("UNT002", 2000000, 0), ("UNC001", 0, 500000)]
giao_dich_pm = [
    {"so_ct": "UNT001", "so_tien": 1000000},   # khop ca so_ct lan so_tien
    {"so_ct": "UNT002", "so_tien": 2500000},   # khop so_ct nhung LECH so_tien
    {"so_ct": "UNT003", "so_tien": 700000},    # co o pm, KHONG co o MISA
    # UNC001 co o MISA nhung KHONG co trong danh sach pm gui len
]
r3 = _misa_doi_chieu_so_du_nh(1, "TESTDB", "1121", datetime.datetime(2025, 9, 30), 100000000,
                              tu_ngay=datetime.datetime(2025, 9, 1), giao_dich_pm=giao_dich_pm)
assert r3["khop"] is False
assert r3["chi_o_pm"] == [{"so_ct": "UNT003", "so_tien": 700000}], r3["chi_o_pm"]
assert r3["chi_o_misa"] == [{"so_ct": "UNC001", "so_tien": 500000}], r3["chi_o_misa"]
assert r3["lech_so_tien"] == [{"so_ct": "UNT002", "so_tien_pm": 2500000, "so_tien_misa": 2000000}], r3["lech_so_tien"]
print("PASS Test 3: doi chieu chi tiet dung 3 nhom (chi_o_pm/chi_o_misa/lech_so_tien)")

# Test 4: mo phong dung ca that cua nguoi dung — trong ky khop hoan toan (khong chenh lech chung tu
# nao) nhung TONG so du van lech, vi so du DAU ky trong MISA (truoc tu_ngay) da mang san 1 khoan lon
# tu cac ky truoc. phat_sinh_ky_pm (theo phan mem, co huong unt/unc) phai KHOP voi phat_sinh_ky_misa,
# va so_du_dau_ky_misa + phat_sinh_ky_misa phai = so_du_misa (cong thuc chuan).
cur.gl_balance = 131230650       # 131.230.650 - dung so MISA that trong ca cua nguoi dung
cur.gl_opening_balance = 125054195  # so du truoc ky sao ke (tu cac ky truoc)
cur.gl_detail = [("UNT001", 252431455, 0), ("UNC001", 0, 246255000)]  # phat sinh dung trong ky
giao_dich_pm4 = [
    {"so_ct": "UNT001", "so_tien": 252431455, "loai": "unt"},
    {"so_ct": "UNC001", "so_tien": 246255000, "loai": "unc"},
]
r4 = _misa_doi_chieu_so_du_nh(1, "TESTDB", "1121", datetime.datetime(2025, 9, 30), 6176455,
                              tu_ngay=datetime.datetime(2025, 9, 1), giao_dich_pm=giao_dich_pm4)
assert r4["khop"] is False
assert not r4["chi_o_pm"] and not r4["chi_o_misa"] and not r4["lech_so_tien"], r4
assert r4["so_du_dau_ky_misa"] == 125054195, r4
assert r4["phat_sinh_ky_misa"] == 6176455, r4          # = so_du_misa - so_du_dau_ky_misa
assert r4["phat_sinh_ky_pm"] == 6176455, r4            # unt - unc = 252431455 - 246255000
assert r4["phat_sinh_ky_pm"] == r4["phat_sinh_ky_misa"]  # phat sinh TRONG KY khop hoan toan 2 ben
print("PASS Test 4: khong chung tu nao lech nhung tong van lech -> chi ro do so du DAU ky (125.054.195), "
      "phat sinh trong ky khop tuyet doi giua phan mem va MISA")

print("\nALL DONE")
