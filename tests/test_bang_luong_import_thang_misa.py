import os
import re
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import asyncio
import server
from fastapi import HTTPException

# Yêu cầu: "làm thêm nút import thẳng vào misa" — ghi THẲNG chứng từ Nghiệp vụ khác của bảng lương vào CSDL MISA (GLVoucher/GLVoucherDetail)
# thay cho bước import Excel. Không có MISA thật trong môi trường test -> dùng CSDL GIẢ có trạng thái (mô phỏng đúng các câu SQL hàm dùng).

TS = server._luong_chuan_tham_so(None, 2025)
base = {"luong_cb": 5_310_000, "tien_com": 700_000, "muc_xang": 500_000, "pc_chuc_vu": 500_000, "muc_dt": 500_000, "trang_phuc": 400_000}


def rows_thang(thang, n=3):
    return [server._luong_tinh_dong(dict(base, ma=str(i), ten=f"NV{i}", ghi_chu="CK" if i % 2 == 0 else ""), TS, thang) for i in range(n)]


GLV_COLS = [("RefID", "uniqueidentifier"), ("RefType", "int"), ("DisplayOnBook", "bit"), ("RefDate", "datetime"), ("PostedDate", "datetime"),
            ("RefNoFinance", "nvarchar"), ("IsPostedFinance", "bit"), ("IsPostedManagement", "bit"), ("JournalMemo", "nvarchar"),
            ("TotalAmountOC", "money"), ("TotalAmount", "money"), ("BranchID", "uniqueidentifier"), ("CurrencyID", "nvarchar"),
            ("ExchangeRate", "decimal"), ("RefOrder", "int"), ("CreatedDate", "datetime"), ("CreatedBy", "nvarchar"), ("CustomField10", "nvarchar")]
GLVD_COLS = [("RefDetailID", "uniqueidentifier"), ("RefID", "uniqueidentifier"), ("Description", "nvarchar"), ("DebitAccount", "nvarchar"),
             ("CreditAccount", "nvarchar"), ("AmountOC", "money"), ("Amount", "money"), ("UnResonableCost", "bit"), ("SortOrder", "int"),
             ("BusinessType", "int"), ("BankAccountID", "uniqueidentifier"), ("BankName", "nvarchar"), ("ListItemID", "uniqueidentifier")]


class Db:
    def __init__(self, tk=None):
        self.glv, self.glvd, self.log, self.committed, self.rolled = [], [], [], 0, 0
        self.tk = tk if tk is not None else {"6422", "6421", "3341", "3383", "3384", "3386", "3335", "1111", "1121"}
        self.tk_nh = {"0123456789": ("bank-1", "Vietcombank")}


class Cur:
    def __init__(self, db):
        self.db, self.rowcount, self._r = db, 0, []

    def execute(self, sql, *params):
        db = self.db
        if len(params) == 1 and isinstance(params[0], (tuple, list)):
            params = tuple(params[0])
        sql1 = " ".join(sql.split())
        db.log.append(sql1)
        self._r = []
        if "FROM sys.columns" in sql1:
            self._r = [(n, t) for n, t in (GLV_COLS if params[0] == "GLVoucher" else GLVD_COLS if params[0] == "GLVoucherDetail"
                                                   else [("BankAccountID", "uniqueidentifier"), ("AccountNumber", "nvarchar"), ("BankName", "nvarchar")] if params[0] == "BankAccount" else [])]
        elif sql1.startswith("DELETE FROM GLVoucherDetail"):
            cf, yy, mm = params
            ids = {g["RefID"] for g in db.glv if g["CustomField10"] == cf and not g["IsPostedFinance"] and g["RefDate"].year == yy and g["RefDate"].month == mm}
            db.glvd = [d for d in db.glvd if d["RefID"] not in ids]
        elif sql1.startswith("DELETE FROM GLVoucher"):
            cf, yy, mm = params
            keep = [g for g in db.glv if not (g["CustomField10"] == cf and not g["IsPostedFinance"] and g["RefDate"].year == yy and g["RefDate"].month == mm)]
            self.rowcount = len(db.glv) - len(keep)
            db.glv = keep
        elif "WHERE gd.Description=?" in sql1:
            for d in db.glvd:
                if d["Description"] == params[0]:
                    g = next(x for x in db.glv if x["RefID"] == d["RefID"])
                    self._r = [(g["RefNoFinance"],)]
                    break
        elif "RefNoFinance LIKE 'NVK%'" in sql1 and sql1.startswith("SELECT RefNoFinance"):
            self._r = [(g["RefNoFinance"],) for g in db.glv if str(g["RefNoFinance"]).startswith("NVK")]
        elif sql1.startswith("SELECT TOP 1 RefID FROM GLVoucher WHERE RefNoFinance=?"):
            self._r = [(g["RefID"],) for g in db.glv if g["RefNoFinance"] == params[0]][:1]
        elif "FROM Account" in sql1:
            self._r = [(t,) for t in db.tk]
        elif "FROM SYSRefType" in sql1:
            self._r = [(4010,)]
        elif "MAX(RefOrder)" in sql1:
            self._r = [(max([g["RefOrder"] for g in db.glv] or [0]),)]
        elif "FROM OrganizationUnit" in sql1:
            self._r = [("branch-1",)]
        elif "FROM ListItem" in sql1:
            self._r = []
        elif "FROM BankAccount" in sql1:
            self._r = [("bank-1", "0123456789", "Vietcombank")]
        elif sql1.startswith("INSERT INTO GLVoucherDetail"):
            cols = re.findall(r"\[(\w+)\]", sql1.split("VALUES")[0])
            db.glvd.append(dict(zip(cols, params)))
        elif sql1.startswith("INSERT INTO GLVoucher"):
            cols = re.findall(r"\[(\w+)\]", sql1.split("VALUES")[0])
            db.glv.append(dict(zip(cols, params)))
        return self

    def fetchall(self):
        return self._r

    def fetchone(self):
        return self._r[0] if self._r else None


class Conn:
    def __init__(self, db):
        self.db, self.autocommit = db, True
        self._snap = ([dict(x) for x in db.glv], [dict(x) for x in db.glvd])

    def cursor(self):
        return Cur(self.db)

    def commit(self):
        self.db.committed += 1
        self._snap = ([dict(x) for x in self.db.glv], [dict(x) for x in self.db.glvd])

    def rollback(self):
        self.db.rolled += 1
        self.db.glv, self.db.glvd = [dict(x) for x in self._snap[0]], [dict(x) for x in self._snap[1]]

    def close(self):
        pass


def dung(db):
    server._misa_sql_connect = lambda cid, database=None, **kw: Conn(db)


def goi(**kw):
    d = {"nam": 2025, "thang": {"05": rows_thang("05"), "06": rows_thang("06")}, "database": "MISA_TEST"}
    d.update(kw)
    return d


class Req:
    def __init__(self, b): self._b = b
    async def json(self): return self._b


def goi_api(b):
    return asyncio.run(server.bang_luong_import_misa(1, Req(b)))


# ===== 1: xem trước không ghi gì (rollback), nhưng trả đúng danh sách chứng từ giống bản Excel =====
db = Db()
dung(db)
kq = goi_api(goi())
assert kq["preview"] is True and db.glv == [] and db.glvd == [] and db.committed == 0 and db.rolled == 1
assert kq["so_chung_tu"] == 4 and kq["so_dong"] == 2 * (7 + 1)   # lương mẫu không có thuế TNCN -> dòng 0đ bỏ; mỗi tháng: BH(7 dòng) + TT lương(1 dòng)
mong_doi = server._luong_misa_chung_tu(2025, {"05": rows_thang("05"), "06": rows_thang("06")}, {}, 1)
assert [c["so_ct"] for c in kq["chung_tu"]] == [c["so_ct"] for c in mong_doi] == ["NVK1/5/2025", "NVK2/5/2025", "NVK3/6/2025", "NVK4/6/2025"]
assert kq["da_ghi_so"] is False
print("PASS 1: xem trước không ghi gì, danh sách chứng từ trùng bản Excel.")

# ===== 2: ghi thật — đúng bảng, cờ chưa ghi sổ, marker, tài khoản, số tiền, cân Nợ = Có =====
db = Db()
dung(db)
kq = goi_api(goi(preview=False))
assert db.committed == 1 and len(db.glv) == 4 and len(db.glvd) == kq["so_dong"]
for g in db.glv:
    assert g["IsPostedFinance"] is False and g["CustomField10"] == server._LUONG_MISA_MARK and g["RefType"] == 4010 and g["CurrencyID"] == "VND"
    ds = [d for d in db.glvd if d["RefID"] == g["RefID"]]
    assert ds and abs(sum(d["Amount"] for d in ds) - g["TotalAmount"]) < 1 and all(d["AmountOC"] == d["Amount"] > 0 for d in ds)
    assert [d["SortOrder"] for d in ds] == list(range(len(ds)))
assert len({g["RefOrder"] for g in db.glv}) == 4
c1 = next(g for g in db.glv if g["RefNoFinance"] == "NVK1/5/2025")
assert c1["RefDate"].strftime("%d/%m/%Y") == "31/05/2025"
d1 = [d for d in db.glvd if d["RefID"] == c1["RefID"]]
assert [(d["Description"], d["DebitAccount"], d["CreditAccount"]) for d in d1][:2] == [
    ("Hạch toán chi phí lương T5/2025", "6422", "3341"), ("Trích BHXH T5/2025", "6421", "3383")]
# TK 334: tổng Có (chi phí) = tổng Nợ (BH NLĐ + thuế + TT lương)
co334 = sum(d["Amount"] for d in db.glvd if d["CreditAccount"] == "3341")
no334 = sum(d["Amount"] for d in db.glvd if d["DebitAccount"] == "3341")
assert co334 == no334
print("PASS 2: ghi thật GLVoucher/GLVoucherDetail: chưa ghi sổ, có marker, TK 334 cân.")

# ===== 3: chạy lại -> thấy chứng từ chưa ghi sổ do mình tạo thì GỠ rồi ghi lại (không nhân đôi, không trùng số) =====
kq2 = goi_api(goi(preview=False))
assert len(db.glv) == 4 and kq2["so_go_cu"] == 4 and not kq2["bo_qua"]
assert sorted(g["RefNoFinance"] for g in db.glv) == sorted(c["so_ct"] for c in kq2["chung_tu"])
assert len({g["RefNoFinance"] for g in db.glv}) == 4
print("PASS 3: ghi lại thay thế bản cũ chưa ghi sổ, không nhân đôi.")

# ===== 4: chứng từ đã GHI SỔ (hoặc do người dùng tự nhập) thì KHÔNG đụng: tháng đó bị bỏ qua, không ghi trùng =====
for g in db.glv:
    if g["RefDate"].month == 5:
        g["IsPostedFinance"] = True
kq3 = goi_api(goi(preview=False))
assert len(kq3["bo_qua"]) == 1 and kq3["bo_qua"][0]["thang"] == "05" and "đã có chứng từ hạch toán lương" in kq3["bo_qua"][0]["ly_do"]
assert sum(1 for g in db.glv if g["RefDate"].month == 5) == 2 and all(g["IsPostedFinance"] for g in db.glv if g["RefDate"].month == 5)
assert sum(1 for g in db.glv if g["RefDate"].month == 6) == 2
assert len({g["RefNoFinance"] for g in db.glv}) == len(db.glv)
try:
    goi_api(goi(thang={"05": rows_thang("05")}, preview=False))
    raise SystemExit("phải báo lỗi: mọi tháng đều đã có chứng từ")
except HTTPException as e:
    assert e.status_code == 400 and "đã có chứng từ hạch toán lương" in e.detail
print("PASS 4: chứng từ đã ghi sổ không bị đụng; tháng đã có thì bỏ qua, không ghi trùng.")

# ===== 5: số chứng từ nối tiếp NVK lớn nhất đang có; hoặc theo số người dùng nhập; số đã tồn tại thì chặn =====
db = Db()
db.glv.append({"RefID": "x", "RefNoFinance": "NVK40/1/2025", "CustomField10": None, "IsPostedFinance": True, "RefDate": __import__("datetime").datetime(2025, 1, 31), "RefOrder": 9})
dung(db)
kq = goi_api(goi(thang={"05": rows_thang("05")}))
assert kq["so_bat_dau"] == 41 and kq["chung_tu"][0]["so_ct"] == "NVK41/5/2025"
kq = goi_api(goi(thang={"05": rows_thang("05")}, so_bat_dau="100"))
assert kq["chung_tu"][0]["so_ct"] == "NVK100/5/2025"
db.glv.append({"RefID": "y", "RefNoFinance": "NVK40/5/2025", "CustomField10": None, "IsPostedFinance": True, "RefDate": __import__("datetime").datetime(2025, 5, 31), "RefOrder": 10})
try:
    goi_api(goi(thang={"05": rows_thang("05")}, so_bat_dau="40"))
    raise SystemExit("phải chặn trùng số")
except HTTPException as e:
    assert e.status_code == 400 and "NVK40/5/2025" in e.detail
print("PASS 5: số NVK nối tiếp / tự nhập; số đã tồn tại bị chặn.")

# ===== 6: tài khoản chưa có trong MISA -> báo rõ (không để lỗi khóa ngoại), rollback =====
db = Db(tk={"6422", "6421", "3341", "3383", "3384", "3386", "1111"})     # thiếu 3335
dung(db)
try:
    goi_api(goi(thang={"05": [server._luong_tinh_dong(dict(base, luong_cb=40_000_000, ma="1", ten="GD"), TS, "05")]}, preview=False))   # lương cao -> có thuế TNCN (TK 3335)
    raise SystemExit("phải báo thiếu TK")
except HTTPException as e:
    assert e.status_code == 400 and "3335" in e.detail
assert db.glv == [] and db.committed == 0
print("PASS 6: thiếu tài khoản trong danh mục MISA -> báo rõ, không ghi gì.")

# ===== 7: lỗi SQL giữa chừng -> hoàn tác toàn bộ =====
db = Db()
dung(db)
_ins = Cur.execute
def loi(self, sql, *p):
    if " ".join(sql.split()).startswith("INSERT INTO GLVoucherDetail") and len(self.db.glvd) >= 2:
        raise RuntimeError("giả lập lỗi SQL")
    return _ins(self, sql, *p)
Cur.execute = loi
try:
    goi_api(goi(preview=False))
    raise SystemExit("phải báo lỗi")
except HTTPException as e:
    assert e.status_code == 400 and "đã hoàn tác" in e.detail
finally:
    Cur.execute = _ins
assert db.glv == [] and db.glvd == [] and db.committed == 0
print("PASS 7: lỗi giữa chừng -> hoàn tác toàn bộ.")

# ===== 8: TK ngân hàng cho dòng TT lương chuyển khoản; thiếu thì chỉ cảnh báo =====
db = Db()
dung(db)
kq = goi_api(goi(thang={"05": rows_thang("05")}, tach_ck=True, tk_nh_ma="0123456789", preview=False))
dong_nh = [d for d in db.glvd if d["CreditAccount"] == "1121"]
assert len(dong_nh) == 1 and dong_nh[0]["BankAccountID"] == "bank-1" and dong_nh[0]["BankName"] == "Vietcombank" and not kq["canh_bao"]
db = Db()
dung(db)
kq = goi_api(goi(thang={"05": rows_thang("05")}, tach_ck=True, preview=False))
assert any("TK ngân hàng" in c for c in kq["canh_bao"]) and len(db.glv) == 2
print("PASS 8: TK ngân hàng ghi vào dòng chuyển khoản; thiếu thì cảnh báo, không chặn.")

# ===== 9: chưa cấu hình CSDL MISA -> báo rõ; không có dữ liệu -> 404 =====
server._misa_sql_cfg = lambda cid: {}
try:
    goi_api(goi(database=""))
    raise SystemExit("phải báo chưa cấu hình")
except HTTPException as e:
    assert e.status_code == 400 and "Chưa cấu hình" in e.detail
try:
    goi_api({"nam": 2025, "thang": {}, "database": "X"})
    raise SystemExit("phải 404")
except HTTPException as e:
    assert e.status_code == 404
print("PASS 9: thiếu cấu hình / thiếu dữ liệu báo lỗi rõ.")

print("\nALL DONE")
