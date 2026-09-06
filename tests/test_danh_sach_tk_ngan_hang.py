import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test cho tính năng MỚI "🔄 Đồng bộ TK NH với MISA" ở
doi_chieu_ngan_hang.html (Kế Toán AI), theo yêu cầu người dùng: "hãy thêm
nút đồng bộ TK NH với misa khi nhấn vào phần mềm sẽ tự lấy thông tin tài
khoản để nhập vào phần mềm luôn".

_misa_danh_sach_tai_khoan_ngan_hang lấy danh sách Tài khoản ngân hàng THẬT
từ bảng BankAccount của MISA — xác nhận đúng qua dữ liệu thật người dùng
gửi (ảnh chụp màn hình "Tài khoản ngân hàng" MISA: STK 934594948, Ngân
hàng TMCP Á Châu) VÀ file cấu trúc CSDL: BankAccount.BankName THƯỜNG ĐỂ
NULL, tên ngân hàng thật lấy qua JOIN bảng Bank RIÊNG (BankAccount.BankID
-> Bank.BankID -> Bank.BankName, vd BankID=6C2AC906... -> BankName="Ngân
hàng TMCP Việt Á") — nếu chỉ đọc thẳng BankAccount.BankName sẽ luôn ra
rỗng, đúng lỗi tiềm ẩn nếu không JOIN bảng Bank."""
import sys
sys.path.insert(0, _REPO_ROOT)
import server


def C(*names):
    return [(n, "nvarchar") for n in names]


TABLES = {
    "BankAccount": C("BankAccountID", "BankAccountNumber", "BankID", "BankName", "Address",
                      "Description", "Inactive", "AccountHolder"),
    "Bank": C("BankID", "BankCode", "BankName"),
}


class FakeCursor:
    def __init__(self, bank_accounts, banks):
        self.bank_accounts = bank_accounts   # [(BankAccountID, BankAccountNumber, BankID, BankName, Inactive, AccountHolder)]
        self.banks = banks                   # [(BankID, BankName)]

    def execute(self, sql, *params):
        self._last_sql = sql
        return self

    def fetchall(self):
        sql = self._last_sql
        if 'sys.columns' in sql and 'sys.types' in sql:
            return []
        if sql.startswith("SELECT [BankAccountNumber], [BankName], [AccountHolder], [BankID], [Inactive] FROM BankAccount"):
            return [(bid_num, bname, holder, bank_id, inactive)
                     for (_id, bid_num, bank_id, bname, inactive, holder) in self.bank_accounts]
        if sql.startswith("SELECT [BankID],[BankName] FROM Bank"):
            return self.banks
        return []


ns = {'_misa_cot_bang_that': lambda cur, table: {c.lower(): (c, t) for c, t in TABLES.get(table, [])},
      '_misa_chon_cot': None, '_misa_sql_connect': None}


def extract_fn(name):
    src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()
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


for n in ('_misa_chon_cot', '_misa_danh_sach_tai_khoan_ngan_hang'):
    exec(extract_fn(n), ns)
_misa_danh_sach_tai_khoan_ngan_hang = ns['_misa_danh_sach_tai_khoan_ngan_hang']


class FakeConn:
    def __init__(self, cur): self._cur = cur
    def cursor(self): return self._cur
    def close(self): pass


# ----- Test 1: đúng ca thật — BankAccount.BankName=NULL, phải JOIN bảng
# Bank riêng để ra đúng "Ngân hàng TMCP Á Châu" (không phải rỗng). -----
cur1 = FakeCursor(
    bank_accounts=[("id1", "934594948", "bankid-acb", None, False, None)],
    banks=[("bankid-acb", "Ngân hàng TMCP Á Châu")])
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur1)
r1 = _misa_danh_sach_tai_khoan_ngan_hang(1, "TESTDB")
assert len(r1["danh_sach"]) == 1
assert r1["danh_sach"][0]["so_tk"] == "934594948"
assert r1["danh_sach"][0]["ten_ngan_hang"] == "Ngân hàng TMCP Á Châu", (
    f"PHẢI lấy tên ngân hàng qua JOIN bảng Bank (BankAccount.BankName để NULL đúng như dữ liệu thật) "
    f"— got {r1['danh_sach'][0]}")
assert r1["danh_sach"][0]["inactive"] is False
print("PASS 1: BankAccount.BankName=NULL vẫn ra đúng tên ngân hàng thật qua JOIN bảng Bank riêng.")

# ----- Test 2: BankAccount.BankName CÓ SẴN (một số CSDL khác có thể set
# trực tiếp) -> dùng luôn, không cần JOIN. -----
cur2 = FakeCursor(
    bank_accounts=[("id2", "11600294", "bankid-vcb", "Vietcombank", False, "CÔNG TY ABC")],
    banks=[("bankid-vcb", "Ngân hàng TMCP Ngoại thương Việt Nam")])
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur2)
r2 = _misa_danh_sach_tai_khoan_ngan_hang(1, "TESTDB")
assert r2["danh_sach"][0]["ten_ngan_hang"] == "Vietcombank", (
    f"Có sẵn BankAccount.BankName thì dùng luôn (ưu tiên hơn JOIN) — got {r2['danh_sach'][0]}")
assert r2["danh_sach"][0]["chu_tai_khoan"] == "CÔNG TY ABC"
print("PASS 2: BankAccount.BankName có sẵn được dùng trực tiếp, đúng Chủ tài khoản.")

# ----- Test 3: nhiều tài khoản, có tài khoản Inactive (ngừng theo dõi) —
# vẫn trả về đầy đủ (để phần mềm tự lọc/hiển thị), không tự ý bỏ qua. -----
cur3 = FakeCursor(
    bank_accounts=[
        ("id1", "934594948", "bankid-acb", None, False, None),
        ("id3", "999888777", "bankid-acb", None, True, None),
    ],
    banks=[("bankid-acb", "Ngân hàng TMCP Á Châu")])
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur3)
r3 = _misa_danh_sach_tai_khoan_ngan_hang(1, "TESTDB")
assert len(r3["danh_sach"]) == 2
by_so = {x["so_tk"]: x for x in r3["danh_sach"]}
assert by_so["999888777"]["inactive"] is True
assert by_so["934594948"]["inactive"] is False
print("PASS 3: trả về đủ cả tài khoản Inactive, đúng cờ inactive cho từng tài khoản.")

print("\nTẤT CẢ TEST PASS")
