import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys, datetime
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test cho tính năng MỚI "ghi thẳng Xuất kho vào MISA" (bảng RIÊNG
# INOutward/INOutwardDetail — MÀN MISA "Kho > Nhập, xuất kho > Xuất kho"),
# theo đúng yêu cầu người dùng: "hãy thêm nút import thẳng xuất kho vào misa.
# import giống như hình" kèm ảnh chụp màn hình MISA (Ngày hạch toán/chứng
# từ, Số chứng từ "XK T12/2024", Tổng tiền 568.750.526, TK Nợ 632/Có 1561).
#
# Cấu trúc bảng INOutward/INOutwardDetail dùng trong test này lấy ĐÚNG từ
# file cấu trúc CSDL MISA THẬT người dùng gửi ("📄 Xuất cấu trúc TẤT CẢ
# bảng") — xác nhận khớp 1:1 với chính chứng từ thật "XK T12/2024" (RefType=
# 2020, TotalAmountFinance=568750526.0000, DebitAccount=632/CreditAccount=
# 1561 trên INOutwardDetail) đang có trong CSDL đó.

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
        self.code = code; self.msg = msg
        super().__init__(f"{code}: {msg}")

ns = {'datetime': datetime, 'HTTPException': FakeHTTPException, '_PM_MARK': 'HDDT-AUTO'}

names = ['_misa_cot_bang_that', '_misa_gia_tri_mac_dinh', '_misa_chon_cot', '_misa_gan',
         '_misa_branch_id', '_to_num', '_xk_ton_an_toan', '_xk_dau_ky_an_toan',
         '_xk_kiem_tra_vuot_ton', '_xk_key_ngay', '_xk_cuoi_thang', '_misa_doc_ngay',
         '_misa_ghi_xuat_kho']
for n in names:
    exec(extract_fn(n), ns)

def C(*names):
    return [(n, "nvarchar") for n in names]

cols_inoutward = C("RefID", "DisplayOnBook", "RefType", "RefDate", "PostedDate",
    "RefNoFinance", "RefNoManagement", "InvTemplateNo", "InvSeries", "InvNo",
    "IsPostedFinance", "IsPostedManagement", "AccountObjectID", "AccountObjectName",
    "TotalAmountFinance", "TotalAmountManagement", "BranchID",
    "IsPostedInventoryBookFinance", "IsPostedInventoryBookManagement",
    "InventoryPostedDate", "RefOrder", "CreatedDate", "CreatedBy", "ModifiedDate",
    "ModifiedBy", "CustomField10", "AssemblyRefID", "INRefOrder", "isBranchIssued",
    "IsSaleWithOutward", "IsInvoiceReplace", "RefIDMshop", "RefNoMshop",
    "IsGetForInvoice", "OrganizationUnitID", "InvoiceSystem", "InvoiceCode",
    "IsProcessInvoiceError", "InvReplaceType")
cols_inoutwarddetail = C("RefDetailID", "RefID", "InventoryItemID", "Description",
    "StockID", "DebitAccount", "CreditAccount", "UnitID", "Quantity",
    "UnitPriceFinance", "UnitPriceManagement", "AmountFinance", "AmountManagement",
    "IsUnUpdateOutwardPrice", "UnResonableCost", "MainUnitID", "MainUnitPriceFinance",
    "MainUnitPriceManagement", "MainConvertRate", "MainQuantity",
    "ExchangeRateOperator", "SortOrder", "IsPromotion")
cols_inventoryitem = C("InventoryItemID", "InventoryItemCode", "UnitID", "InventoryItemName")
cols_stock = C("StockID", "StockCode", "StockName")
cols_ininoutlist = C("RefID", "RefDate", "PostedDate", "RefType", "RefNoFinance", "RefNoManagement",
    "IsPostedFinance", "IsPostedManagement", "DisplayOnBook", "BranchID", "RefOrder", "CreatedDate",
    "CreatedBy", "ModifiedDate", "ModifiedBy", "CustomField10", "ListTableName", "INType", "RefTypeName",
    "TotalAmountFinance", "TotalAmountManagement", "TotalAmount", "TotalAmountOC")

TABLES = {"INOutward": cols_inoutward, "INOutwardDetail": cols_inoutwarddetail,
          "InventoryItem": cols_inventoryitem, "Stock": cols_stock,
          "INInwardOutwardList": cols_ininoutlist}
ns['_misa_cot_bang_that'] = lambda cur, table: {c.lower(): (c, t) for c, t in TABLES.get(table, [])}


class FakeCursor:
    """Mô phỏng CSDL MISA có sẵn 2 mã hàng (MH01/MH02) ở kho "Kho Hàng Hóa"
    (mã StockCode="HH"), KHÔNG có sẵn chứng từ 'Số chứng từ' nào trùng."""
    def __init__(self, so_ct_da_co=None, mark_da_co=None):
        self.inserted = {t: [] for t in TABLES}
        self.deleted = []
        self.so_ct_da_co = so_ct_da_co
        self.mark_da_co = mark_da_co

    def execute(self, sql, *params):
        params = params[0] if len(params) == 1 and isinstance(params[0], (tuple, list)) else params
        self._last_sql = sql
        self._last_params = params
        if sql.startswith("INSERT INTO"):
            table = sql.split(" ")[2]
            cols_str = sql[sql.index("(")+1:sql.index(")")]
            cols = [c.strip("[]") for c in cols_str.split(",")]
            self.inserted[table].append(dict(zip(cols, params)))
        elif sql.startswith("DELETE FROM"):
            self.deleted.append((sql.split(" ")[2], params[0] if params else None))
        return self

    def fetchall(self):
        sql = self._last_sql
        if 'sys.columns' in sql and 'sys.types' in sql:
            table = self._last_params[0] if isinstance(self._last_params, (list, tuple)) else self._last_params
            return [(c, t) for c, t in TABLES.get(table, [])]
        if sql.startswith("SELECT InventoryItemID, InventoryItemCode, UnitID, InventoryItemName"):
            return [("iid-mh01", "MH01", "uid-cai", "Hàng mẫu 01"),
                    ("iid-mh02", "MH02", "uid-cai", "Hàng mẫu 02")]
        if sql.startswith("SELECT StockID, StockCode, StockName FROM Stock"):
            return [("sid-hh", "HH", "Kho Hàng Hóa")]
        if sql.startswith("SELECT RefType, RefTypeName FROM SYSRefType WHERE MasterTableName='INOutward'"):
            return [(2020, "Xuất kho bán hàng"), (2021, "Xuất kho khác")]
        if sql.startswith("SELECT RefID, ISNULL(") and "FROM INOutward WHERE RefNoFinance=?" in sql:
            if self.so_ct_da_co:
                return [("refid-cu", self.mark_da_co or "")]
            return []
        return []

    def fetchone(self):
        sql = self._last_sql
        if sql.startswith("SELECT MAX(RefOrder) FROM INOutward"):
            return (1200,)
        return None


class FakeConn:
    def __init__(self, cur): self._cur = cur; self.autocommit = True
    def cursor(self): return self._cur
    def commit(self): self.committed = True
    def rollback(self): self.rolled_back = True
    def close(self): pass


ns['_misa_branch_id'] = lambda cur: "branch-1"
exec(extract_fn('_misa_ghi_xuat_kho'), ns)
_misa_ghi_xuat_kho = ns['_misa_ghi_xuat_kho']

GIATHANH_CO_BAN = [
    {"ma": "MH01", "ten_xk": "Hàng mẫu 01", "dvt_xk": "Cái", "sl_kho": 10, "sl": 10,
     "gia_xk": 100000, "ngay": "20/12/2024"},
    {"ma": "MH02", "ten_xk": "Hàng mẫu 02", "dvt_xk": "Cái", "sl_kho": 5, "sl": 5,
     "gia_xk": 50000, "ngay": "31/12/2024"},
]
TON_CO_BAN = [
    {"ma": "MH01", "ton": 100, "kho": "Kho Hàng Hóa"},
    {"ma": "MH02", "ton": 100, "kho": "Kho Hàng Hóa"},
]


def _chay(cur, giathanh, ton, preview=False, ghi_de=False):
    ns['_doc_du_lieu_cty'] = lambda cid: {"xk_giathanh": giathanh, "xk_ton": ton}
    ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur)
    exec(extract_fn('_misa_ghi_xuat_kho'), ns)
    fn = ns['_misa_ghi_xuat_kho']
    return fn(1, "TESTDB", preview=preview, ghi_de=ghi_de)


# ----- Test 1: ghi cơ bản đúng — Số chứng từ/Ngày hạch toán/TK Nợ-Có/tổng
# tiền khớp ĐÚNG quy ước đã xác nhận qua chứng từ THẬT "XK T12/2024". -----
cur1 = FakeCursor()
r1 = _chay(cur1, GIATHANH_CO_BAN, TON_CO_BAN)
assert r1["so_ct"] == "XK T12/2024", f"Số chứng từ phải 'XK T12/2024' (cuối tháng của ngày mới nhất 31/12/2024) — got {r1['so_ct']}"
assert r1["so_dong"] == 2 and r1["so_bo_qua_mahang"] == 0 and r1["so_bo_qua_kho"] == 0
assert r1["tong_tien"] == 10 * 100000 + 5 * 50000 == 1250000, f"got {r1['tong_tien']}"
h = cur1.inserted["INOutward"][0]
assert h["RefNoFinance"] == "XK T12/2024" and h["RefType"] == 2020
assert h["IsPostedFinance"] is False and h["IsPostedManagement"] is False, (
    "PHẢI để CHƯA GHI SỔ (an toàn) — người dùng tự bấm Ghi sổ trong MISA sau khi kiểm tra")
assert h["IsPostedInventoryBookFinance"] is False, (
    "KHÔNG được tự nhận đã ghi Sổ Kho — đúng chứng từ THẬT 'XK T12/2024' cũng "
    "IsPostedInventoryBookFinance=False dù IsPostedFinance=True")
assert h["TotalAmountFinance"] == 1250000
assert h["CustomField10"] == "HDDT-AUTO"
det = sorted(cur1.inserted["INOutwardDetail"], key=lambda d: d["SortOrder"])
assert len(det) == 2
assert det[0]["InventoryItemID"] == "iid-mh01" and det[0]["StockID"] == "sid-hh"
assert det[0]["DebitAccount"] == "632" and det[0]["CreditAccount"] == "1561"
assert det[0]["Quantity"] == 10 and det[0]["UnitPriceFinance"] == 100000 and det[0]["AmountFinance"] == 1000000
assert det[1]["InventoryItemID"] == "iid-mh02" and det[1]["AmountFinance"] == 250000
print("PASS 1: ghi đúng INOutward/INOutwardDetail — Số CT/TK Nợ 632-Có 1561/tổng tiền khớp ảnh chụp MISA thật, CHƯA ghi sổ.")

# ----- Test 1b (đúng lỗi thật người dùng vừa báo "chưa thấy phiếu xk"): PHẢI
# ghi kèm 1 dòng INInwardOutwardList — bảng RIÊNG nguồn cho lưới MISA "Kho >
# Nhập, xuất kho" hiển thị (khác InventoryLedger/Sổ Kho tính giá vốn, KHÔNG
# ghi) — CÙNG RefID với INOutward, ListTableName='INOutward', INType=1. -----
iol = cur1.inserted["INInwardOutwardList"]
assert len(iol) == 1, f"PHẢI ghi đúng 1 dòng INInwardOutwardList (thiếu bảng này khiến chứng từ ghi đúng vào INOutward nhưng KHÔNG hiện trên lưới MISA) — got {len(iol)}"
assert iol[0]["RefID"] == h["RefID"], "INInwardOutwardList.RefID phải TRÙNG với INOutward.RefID vừa ghi"
assert iol[0]["ListTableName"] == "INOutward" and iol[0]["INType"] == 1
assert iol[0]["RefNoFinance"] == "XK T12/2024" and iol[0]["TotalAmountFinance"] == 1250000
assert iol[0]["IsPostedFinance"] is False, "phải sao chép ĐÚNG trạng thái CHƯA GHI SỔ từ header INOutward"
print("PASS 1b: ghi kèm đúng 1 dòng INInwardOutwardList (cùng RefID, ListTableName='INOutward', INType=1) — đúng lỗi thật 'chưa thấy phiếu xk' đã báo.")

# ----- Test 2: mã hàng KHÔNG có trong Danh mục Vật tư MISA -> BỎ QUA dòng
# đó (không chặn hẳn cả chứng từ), báo lại đúng số lượng bị bỏ qua. -----
cur2 = FakeCursor()
giathanh2 = GIATHANH_CO_BAN + [
    {"ma": "MH-LA", "ten_xk": "Hàng lạ chưa có trong MISA", "dvt_xk": "Cái",
     "sl_kho": 3, "sl": 3, "gia_xk": 10000, "ngay": "15/12/2024"}]
ton2 = TON_CO_BAN + [{"ma": "MH-LA", "ton": 100, "kho": "Kho Hàng Hóa"}]
r2 = _chay(cur2, giathanh2, ton2)
assert r2["so_dong"] == 2 and r2["so_bo_qua_mahang"] == 1 and r2["ma_bo_qua"] == ["MH-LA"], f"got {r2}"
print("PASS 2: mã 'MH-LA' chưa có trong Danh mục Vật tư MISA bị bỏ qua đúng, 2 mã còn lại vẫn ghi bình thường.")

# ----- Test 3: kho KHÔNG xác định được (không khớp Stock nào trong MISA) ->
# BỎ QUA dòng đó — KHÔNG tự tạo kho ảo (khác Mua hàng nhập kho). -----
cur3 = FakeCursor()
giathanh3 = GIATHANH_CO_BAN + [
    {"ma": "MH03", "ten_xk": "Hàng mẫu 03", "dvt_xk": "Cái", "sl_kho": 2, "sl": 2,
     "gia_xk": 20000, "ngay": "10/12/2024"}]
ton3 = TON_CO_BAN + [{"ma": "MH03", "ton": 100, "kho": "Kho Không Tồn Tại Trong MISA"}]
ns['_misa_cot_bang_that'] = lambda cur, table: {c.lower(): (c, t) for c, t in TABLES.get(table, [])} \
    if table != "InventoryItem" else {c.lower(): (c, t) for c, t in cols_inventoryitem}
cur3fetch = cur3.fetchall
def _fetchall3():
    sql = cur3._last_sql
    if sql.startswith("SELECT InventoryItemID, InventoryItemCode, UnitID, InventoryItemName"):
        return [("iid-mh01", "MH01", "uid-cai", "Hàng mẫu 01"),
                ("iid-mh02", "MH02", "uid-cai", "Hàng mẫu 02"),
                ("iid-mh03", "MH03", "uid-cai", "Hàng mẫu 03")]
    return cur3fetch()
cur3.fetchall = _fetchall3
r3 = _chay(cur3, giathanh3, ton3)
assert r3["so_dong"] == 2 and r3["so_bo_qua_kho"] == 1 and r3["kho_bo_qua_ma"] == ["MH03"], f"got {r3}"
print("PASS 3: mã 'MH03' thuộc kho không xác định được trong MISA bị bỏ qua đúng, KHÔNG tự tạo kho ảo.")

# ----- Test 4: gán VƯỢT tồn kho thật -> CHẶN hẳn (không ghi gì), giống hệt
# quy tắc đang áp dụng cho '🗂 Xuất file Xuất Kho' (_xk_kiem_tra_vuot_ton). -----
cur4 = FakeCursor()
ton4 = [{"ma": "MH01", "ton": 5, "kho": "Kho Hàng Hóa"}, {"ma": "MH02", "ton": 100, "kho": "Kho Hàng Hóa"}]
try:
    _chay(cur4, GIATHANH_CO_BAN, ton4)   # MH01 cần 10 nhưng tồn chỉ 5
    assert False, "phải raise HTTPException vì MH01 vượt tồn (cần 10, tồn 5)"
except FakeHTTPException as e:
    assert "VƯỢT tồn kho" in e.msg and "MH01" in e.msg, f"got {e.msg}"
assert len(cur4.inserted["INOutward"]) == 0, "KHÔNG được ghi gì khi có mã vượt tồn"
print("PASS 4: mã 'MH01' vượt tồn kho (cần 10, tồn 5) bị CHẶN hẳn, không ghi chứng từ nào.")

# ----- Test 5: Số chứng từ trùng với chứng từ THẬT của khách (không phải do
# phần mềm tạo) -> CHẶN hẳn, KHÔNG được ghi đè (tránh mất dữ liệu thật). -----
cur5 = FakeCursor(so_ct_da_co=True, mark_da_co="")   # CustomField10 rỗng -> không phải phần mềm tạo
try:
    _chay(cur5, GIATHANH_CO_BAN, TON_CO_BAN, ghi_de=True)
    assert False, "phải raise HTTPException vì Số chứng từ trùng với chứng từ THẬT của khách"
except FakeHTTPException as e:
    assert "đã tồn tại trong MISA" in e.msg and "không phải do phần mềm" in e.msg, f"got {e.msg}"
assert len(cur5.inserted["INOutward"]) == 0
print("PASS 5: Số chứng từ 'XK T12/2024' trùng với chứng từ THẬT của khách (không do phần mềm tạo) bị CHẶN, không ghi đè.")

# ----- Test 6: Số chứng từ trùng với chứng từ DO CHÍNH phần mềm tạo trước
# đó (CustomField10=_PM_MARK) -> preview/ghi_de=False chỉ báo "đã tồn tại",
# ghi_de=True mới xoá + ghi lại. -----
cur6 = FakeCursor(so_ct_da_co=True, mark_da_co="HDDT-AUTO")
r6a = _chay(cur6, GIATHANH_CO_BAN, TON_CO_BAN, ghi_de=False)
assert r6a.get("da_ton_tai") is True and len(cur6.inserted["INOutward"]) == 0, f"got {r6a}"
r6b = _chay(cur6, GIATHANH_CO_BAN, TON_CO_BAN, ghi_de=True)
assert r6b.get("da_ghi_de") is True and len(cur6.inserted["INOutward"]) == 1
assert len(cur6.inserted["INInwardOutwardList"]) == 1, "ghi_de vẫn phải ghi lại đúng 1 dòng INInwardOutwardList mới"
assert ("INOutward", "refid-cu") in cur6.deleted and ("INOutwardDetail", "refid-cu") in cur6.deleted
assert ("INInwardOutwardList", "refid-cu") in cur6.deleted, (
    "ghi_de PHẢI xoá luôn dòng INInwardOutwardList CŨ (RefID cũ) — nếu không sẽ để lại dòng RÁC trỏ tới "
    "1 RefID đã bị xoá, có thể khiến lưới MISA hiện lỗi/dòng hỏng")
print("PASS 6: Số chứng từ trùng do CHÍNH phần mềm tạo trước đó — ghi_de=False chỉ báo đã tồn tại (không ghi), ghi_de=True xoá + ghi lại đúng CẢ INInwardOutwardList.")

print("\nTẤT CẢ TEST PASS")
