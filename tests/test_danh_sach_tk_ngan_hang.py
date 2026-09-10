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
    "BADeposit": C("RefID", "BankAccountID"),
    "BADepositDetail": C("RefDetailID", "RefID", "DebitAccount"),
    "BAWithDraw": C("RefID", "BankAccountID"),
    "BAWithDrawDetail": C("RefDetailID", "RefID", "CreditAccount"),
}


class FakeCursor:
    def __init__(self, bank_accounts, banks, account_numbers=(), ma_hach_toan_theo_id=None):
        self.bank_accounts = bank_accounts   # [(BankAccountID, BankAccountNumber, BankID, BankName, Inactive, AccountHolder)]
        self.banks = banks                   # [(BankID, BankName)]
        self.account_numbers = account_numbers   # Hệ thống tài khoản MISA (TK 1121x/1122x thật)
        # {BankAccountID: [mã đã dùng, lặp lại theo tần suất]} — mô phỏng lịch sử chứng từ Thu/Chi
        # tiền gửi THẬT (gộp CẢ BADeposit lẫn BAWithDraw, không cần phân biệt trong test này).
        self.ma_hach_toan_theo_id = ma_hach_toan_theo_id or {}

    def execute(self, sql, *params):
        self._last_sql = sql
        self._last_params = params[0] if len(params) == 1 else params
        return self

    def fetchall(self):
        sql = self._last_sql
        if 'sys.columns' in sql and 'sys.types' in sql:
            return []
        if sql.startswith("SELECT AccountNumber FROM Account WHERE AccountNumber LIKE '1121%'"):
            return [(an,) for an in self.account_numbers]
        if sql.startswith("SELECT [BankAccountID], [BankAccountNumber], [BankName], [AccountHolder], [BankID], [Inactive] FROM BankAccount"):
            return [(_id, bid_num, bname, holder, bank_id, inactive)
                     for (_id, bid_num, bank_id, bname, inactive, holder) in self.bank_accounts]
        if sql.startswith("SELECT [BankID],[BankName] FROM Bank"):
            return self.banks
        if "FROM BADeposit h JOIN BADepositDetail d" in sql or "FROM BAWithDraw h JOIN BAWithDrawDetail d" in sql:
            bank_account_id = self._last_params[0] if isinstance(self._last_params, tuple) else self._last_params
            ds = self.ma_hach_toan_theo_id.get(bank_account_id, [])
            dem = {}
            for ma in ds:
                dem[ma] = dem.get(ma, 0) + 1
            return list(dem.items())
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


for n in ('_misa_chon_cot', '_misa_hoc_ma_hach_toan_theo_bankaccount', '_misa_ma_hach_toan_theo_danh_muc',
          '_misa_danh_sach_tai_khoan_ngan_hang'):
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

# ----- Test 2 (ĐẢO NGƯỢC ưu tiên, đúng lỗi thật vừa báo "Tên ngân hàng
# đang hiển thị sai" kèm ảnh MISA thật): dù BankAccount.BankName CÓ SẴN
# giá trị, JOIN Bank qua BankID vẫn PHẢI ưu tiên hơn — vì cột SQL tên
# "BankName" ở 1 số CSDL MISA thật KHÔNG thật sự chứa tên ngân hàng (có
# thể bị dùng để lưu dữ liệu khác kiểu "Chi nhánh", vd "VND"/"USD" — xác
# nhận đúng qua ảnh chụp MISA thật: TK "28686828" Tên ngân hàng THẬT="Ngân
# hàng TMCP Á Châu" nhưng cột BankName lại có giá trị "VND"). Bank.BankName
# (qua BankID) mới là nguồn ĐÚNG mà chính màn hình MISA dùng hiển thị. -----
cur2 = FakeCursor(
    bank_accounts=[("id2", "11600294", "bankid-vcb", "VND", False, "CÔNG TY ABC")],
    banks=[("bankid-vcb", "Ngân hàng TMCP Ngoại thương Việt Nam")])
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur2)
r2 = _misa_danh_sach_tai_khoan_ngan_hang(1, "TESTDB")
assert r2["danh_sach"][0]["ten_ngan_hang"] == "Ngân hàng TMCP Ngoại thương Việt Nam", (
    f"PHẢI ưu tiên Bank.BankName qua JOIN BankID (đúng tên ngân hàng thật MISA hiển thị), KHÔNG được dùng "
    f"thẳng BankAccount.BankName='VND' (dữ liệu kiểu Chi nhánh, không phải tên ngân hàng) — got {r2['danh_sach'][0]}")
assert r2["danh_sach"][0]["chu_tai_khoan"] == "CÔNG TY ABC"
print("PASS 2: BankAccount.BankName='VND' (dữ liệu Chi nhánh, không phải tên NH thật) bị bỏ qua đúng, ưu tiên Bank.BankName qua JOIN BankID ra đúng tên ngân hàng thật.")

# ----- Test 2b: BankID KHÔNG resolve được qua bảng Bank (JOIN thất bại) ->
# fallback về BankAccount.BankName trực tiếp như phương án dự phòng cuối. -----
cur2b = FakeCursor(
    bank_accounts=[("id2b", "22222222", "bankid-khong-ton-tai", "Ngân hàng ABC", False, None)],
    banks=[("bankid-vcb", "Ngân hàng TMCP Ngoại thương Việt Nam")])
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur2b)
r2b = _misa_danh_sach_tai_khoan_ngan_hang(1, "TESTDB")
assert r2b["danh_sach"][0]["ten_ngan_hang"] == "Ngân hàng ABC", (
    f"BankID không JOIN được (không có trong bảng Bank) -> PHẢI fallback về BankAccount.BankName trực tiếp "
    f"— got {r2b['danh_sach'][0]}")
print("PASS 2b: BankID không JOIN được thì fallback đúng về BankAccount.BankName trực tiếp.")

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

# ----- Test 4 (đúng lỗi thật vừa báo): công ty CHỈ có ĐÚNG 1 TK con "1121"
# (không tách theo từng ngân hàng) -> ma_tk_vnd PHẢI đúng "1121", KHÔNG
# được để frontend tự đoán ra "1121-NG"/"1121-TK" (mã không hề tồn tại
# trong Hệ thống tài khoản thật, khiến Đối chiếu số dư TK không khớp được
# gì). -----
cur4 = FakeCursor(
    bank_accounts=[("id1", "934594948", "bankid-acb", None, False, None)],
    banks=[("bankid-acb", "Ngân hàng TMCP Á Châu")],
    account_numbers=["1121"])
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur4)
r4 = _misa_danh_sach_tai_khoan_ngan_hang(1, "TESTDB")
assert r4["ma_tk_vnd"] == "1121", f"Công ty chỉ có đúng 1 TK con '1121' thì PHẢI trả về đúng '1121' — got {r4['ma_tk_vnd']}"
assert r4["ma_tk_usd"] is None
print("PASS 4: công ty chỉ có đúng 1 TK con '1121' (không tách theo ngân hàng) -> trả về đúng '1121', không đoán sai thành '1121-NG'/'1121-TK'.")

# ----- Test 5: công ty có NHIỀU TK con 112x thật (tách theo từng ngân
# hàng) -> KHÔNG đoán, để None (an toàn hơn đoán sai khi có nhiều lựa
# chọn). -----
cur5 = FakeCursor(
    bank_accounts=[("id1", "934594948", "bankid-acb", None, False, None)],
    banks=[("bankid-acb", "Ngân hàng TMCP Á Châu")],
    account_numbers=["1121ACB", "1121VCB", "1122"])
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur5)
r5 = _misa_danh_sach_tai_khoan_ngan_hang(1, "TESTDB")
assert r5["ma_tk_vnd"] is None, f"Có NHIỀU TK con 1121x thật -> không đoán, phải None — got {r5['ma_tk_vnd']}"
assert r5["ma_tk_usd"] == "1122", f"Chỉ 1 TK con '1122' (USD) -> vẫn phải trả đúng — got {r5['ma_tk_usd']}"
print("PASS 5: có nhiều TK con 1121x thật (tách theo ngân hàng) -> ma_tk_vnd=None (không đoán bừa); TK USD riêng vẫn trả đúng vì chỉ có 1.")

# ----- Test 6: không có TK con 112x nào (Hệ thống tài khoản trống/lỗi
# truy vấn) -> không crash, cả 2 đều None. -----
cur6 = FakeCursor(
    bank_accounts=[("id1", "934594948", "bankid-acb", None, False, None)],
    banks=[("bankid-acb", "Ngân hàng TMCP Á Châu")],
    account_numbers=[])
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur6)
r6 = _misa_danh_sach_tai_khoan_ngan_hang(1, "TESTDB")
assert r6["ma_tk_vnd"] is None and r6["ma_tk_usd"] is None
assert len(r6["danh_sach"]) == 1, "vẫn phải trả đúng danh sách Tài khoản ngân hàng dù không dò được TK con 112x"
print("PASS 6: không có TK con 112x nào vẫn không crash, danh sách Tài khoản ngân hàng vẫn trả đúng.")

# ----- Test 7 (đúng lỗi thật vừa báo, kèm ảnh Hệ thống tài khoản MISA có 2
# mã con "11221"/"11222" cùng dưới "1122"): công ty có NHIỀU TK ngoại tệ
# dùng NHIỀU mã con 1122x KHÁC NHAU -> ma_tk_usd ở mức CÔNG TY = None (mơ
# hồ), NHƯNG mỗi TK ngân hàng CỤ THỂ (dò qua lịch sử Thu/Chi tiền gửi THẬT
# của ĐÚNG BankAccountID) PHẢI trả đúng "ma_hach_toan" RIÊNG của nó, KHÔNG
# lẫn lộn giữa 2 TK — "hãy lấy số tài khoản trong misa để gắn chứ phần mềm
# không tự gắn tài khoản đúng 11221". -----
cur7 = FakeCursor(
    bank_accounts=[
        ("id-usd1", "24449247", "bankid-acb", None, False, None),
        ("id-usd2", "362698698", "bankid-acb", None, False, None),
    ],
    banks=[("bankid-acb", "Ngân hàng TMCP Á Châu")],
    account_numbers=["1121", "11221", "11222"],   # 2 mã con 1122x -> mơ hồ ở mức công ty
    ma_hach_toan_theo_id={
        "id-usd1": ["11221", "11221", "11221"],   # TK 24449247 LUÔN dùng đúng 11221
        "id-usd2": ["11222", "11222"],            # TK 362698698 LUÔN dùng đúng 11222
    })
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur7)
r7 = _misa_danh_sach_tai_khoan_ngan_hang(1, "TESTDB")
assert r7["ma_tk_usd"] is None, f"Có nhiều TK con 1122x thật (11221/11222) -> ở mức CÔNG TY phải None (mơ hồ) — got {r7['ma_tk_usd']}"
by_so7 = {x["so_tk"]: x for x in r7["danh_sach"]}
assert by_so7["24449247"]["ma_hach_toan"] == "11221", (
    f"TK '24449247' PHẢI học đúng riêng mã '11221' từ lịch sử Thu/Chi tiền gửi THẬT của ĐÚNG "
    f"BankAccountID đó, KHÔNG được lẫn sang '11222' của TK khác — got {by_so7['24449247']}")
assert by_so7["362698698"]["ma_hach_toan"] == "11222", (
    f"TK '362698698' PHẢI học đúng riêng mã '11222' — got {by_so7['362698698']}")
print("PASS 7: công ty có nhiều TK ngoại tệ dùng nhiều mã con 1122x khác nhau (11221/11222) — mỗi TK "
      "học ĐÚNG mã riêng của mình qua lịch sử Thu/Chi tiền gửi thật, không còn lẫn lộn/gắn sai.")

# ----- Test 8: TK MỚI, chưa từng phát sinh chứng từ Thu/Chi nào (không có
# lịch sử) -> KHÔNG có field "ma_hach_toan" (an toàn hơn đoán khi thiếu dữ
# liệu, để frontend rơi về ma_tk_vnd/ma_tk_usd/suggestMisaAcct như cũ). -----
cur8 = FakeCursor(
    bank_accounts=[("id-moi", "111222333", "bankid-acb", None, False, None)],
    banks=[("bankid-acb", "Ngân hàng TMCP Á Châu")],
    account_numbers=["1121"],
    ma_hach_toan_theo_id={})
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur8)
r8 = _misa_danh_sach_tai_khoan_ngan_hang(1, "TESTDB")
assert "ma_hach_toan" not in r8["danh_sach"][0], (
    f"TK chưa có lịch sử chứng từ nào thì KHÔNG được có field 'ma_hach_toan' (tránh gán bừa) — got {r8['danh_sach'][0]}")
print("PASS 8: TK mới chưa có lịch sử chứng từ nào -> không có 'ma_hach_toan', an toàn hơn đoán khi thiếu dữ liệu.")

print("\nTẤT CẢ TEST PASS")
