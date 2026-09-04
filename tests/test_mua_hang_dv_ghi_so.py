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

class FakeHTTPException(Exception):
    def __init__(self, code, msg):
        self.code = code; self.msg = msg
        super().__init__(f"{code}: {msg}")

ns = {'datetime': datetime, 'HTTPException': FakeHTTPException, '_PM_MARK': 'HDDT-AUTO'}
ns['_MISA_GIO_GHI_NHAP'] = 10
ns['_MUA_TEN'] = {"nk": "Mua hàng nhập kho", "kqk": "Mua hàng không qua kho", "dv": "Mua hàng dịch vụ"}
ns['_MUA_COT'] = {
    "dv": dict(doc=6, ngayct=5, sohd=33, mst=7, ten_ncc=8, ma=14, ten=15,
               dvt=19, sl=20, dgia=21, tt=22, no=16, co=17, ts=27, tthue=28,
               tk_thue=30, tkdu_thue=None, nhtg=None, nts=None, nthue=None,
               ntk=None, la_nk_col=None, kho=None),
}

names = ['_misa_cot_bang_that', '_misa_gia_tri_mac_dinh', '_misa_chon_cot', '_misa_gan',
         '_misa_khncc_chuan_mst', '_misa_branch_id', '_misa_tk_fallback', '_misa_unit_hong',
         '_misa_pu_reftype', '_num0', '_chuan_shd', '_misa_gio_nhap_co_dinh', '_misa_ghi_mua_hang_dv']
for n in names:
    exec(extract_fn(n), ns)

def _extract_dict_literal(varname):
    idx = src.index(varname + " = {")
    depth = 0
    i = idx + len(varname) + 3
    while True:
        if src[i] == '{':
            depth += 1
        elif src[i] == '}':
            depth -= 1
            if depth == 0:
                break
        i += 1
    return src[idx:i+1]

for varname in ('_PU_SERVICE_DEFAULT', '_PU_SERVICE_DET_DEFAULT'):
    code = _extract_dict_literal(varname)
    exec(code, ns)

def C(*names):
    return [(n, "nvarchar") for n in names]

cols_puservice = C("RefID", "BranchID", "RefDate", "PostedDate", "RefType", "RefNoFinance",
    "RefNoManagement", "IsPostedFinance", "IsPostedManagement", "IsFreightService",
    "AccountObjectID", "AccountObjectName", "JournalMemo", "TotalAmountOC", "TotalAmount",
    "TotalVATAmountOC", "TotalVATAmount", "DisplayOnBook", "CreatedDate", "CreatedBy",
    "ModifiedDate", "ModifiedBy", "CustomField10", "IncludeInvoice", "PUInvoiceRefID",
    "CurrencyID", "ExchangeRate", "RefOrder")
cols_puservicedetail = C("RefDetailID", "RefID", "InventoryItemID", "Description", "DebitAccount",
    "CreditAccount", "UnitID", "Quantity", "UnitPrice", "AmountOC", "Amount", "VATRate",
    "VATAmountOC", "VATAmount", "VATAccount", "InvNo", "InvDate", "TaxAccountObjectID",
    "TaxAccountObjectName", "TaxAccountObjectTaxCode", "AccountObjectID", "PurchasePurposeID",
    "VATDescription", "EInvoiceItemName", "SortOrder")
cols_gl = C("GeneralLedgerID", "RefID", "RefDetailID", "RefType", "RefNo", "RefNo1", "RefNo2",
    "RefDate", "RefDate1", "PostedDate", "InvNo", "InvDate", "CurrencyID", "ExchangeRate",
    "AccountNumber", "CorrespondingAccountNumber", "AccountName", "DebitAmountOC", "DebitAmount",
    "CreditAmountOC", "CreditAmount", "JournalMemo", "Description", "AccountObjectID",
    "AccountObjectName", "AccountObjectNameDI", "AccountObjectCode", "AccountObjectTaxCode",
    "BranchID", "UnResonableCost", "IsPostToManagementBook", "SortOrder", "RefOrder",
    "InventoryItemID", "InventoryItemCode", "InventoryItemName", "IsUpdateRedundant",
    "RefTypeName", "UnitID", "Quantity", "UnitPriceOC", "UnitPrice", "MainConvertRate",
    "ExchangeRateOperator", "EntryType", "DetailPostOrder", "IsPostedForCashOutDiff")
cols_aol = C("AccountObjectLedgerID", "BranchID", "RefID", "RefDetailID", "EntryType", "RefType",
    "RefNo", "RefDate", "PostedDate", "InvNo", "InvDate", "AccountNumber", "AccountName",
    "CorrespondingAccountNumber", "ExchangeRate", "CurrencyID", "UnitID", "UnitPriceOC",
    "UnitPrice", "Quantity", "DebitAmountOC", "DebitAmount", "CreditAmountOC", "CreditAmount",
    "JournalMemo", "Description", "AccountObjectID", "AccountObjectCode", "AccountObjectName",
    "AccountObjectNameDI", "AccountObjectTaxCode", "InventoryItemID", "InventoryItemCode",
    "InventoryItemName", "RefTypeName", "IsPostToManagementBook", "RefOrder", "SortOrder",
    "IsUpdateRedundant", "MainConvertRate", "ExchangeRateOperator", "DetailPostOrder",
    "PayKeyID", "DebtKeyID")
cols_cfl = C("CustomFieldLegerID", "RefDetailID", "RefID", "IsPostToManagementBook", "BranchID",
    "PostedDate", "IsUpdateRedundant")
cols_purl = C("PurchaseLedgerID", "RefDetailID", "RefID", "BranchID", "PostedDate", "RefDate",
    "RefType", "RefNo", "JournalMemo", "InventoryItemID", "Description", "DebitAccount",
    "CreditAccount", "UnitID", "UnitPrice", "PurchaseQuantity", "PurchaseAmountOC",
    "PurchaseAmount", "DiscountRate", "DiscountAmountOC", "DiscountAmount", "VATRate",
    "VATAmount", "VATAmountOC", "VATAccount", "ReturnQuantity", "ReturnAmountOC", "ReturnAmount",
    "ReduceAmountOC", "ReduceAmount", "InvDate", "InvNo", "CurrencyID", "ExchangeRate",
    "MainUnitID", "MainUnitPrice", "MainConvertRate", "MainQuantity", "ExchangeRateOperator",
    "IsPostToManagementBook", "AccountObjectID", "AccountObjectName", "AccountObjectTaxCode",
    "SortOrder", "RefOrder", "InventoryItemCode", "InventoryItemName", "AccountObjectCode",
    "IsUpdateRedundant", "AccountObjectNameDI", "RefTypeName", "ReturnMainQuantity",
    "UnitPriceOC", "MainUnitPriceOC", "IncludeInvoice")
cols_taxl = C("TaxLedgerID", "RefID", "RefDetailID", "VATAccount", "TaxType", "Description",
    "VATAmountOC", "VATAmount", "VATRate", "TurnOverAmountOC", "TurnOverAmount", "InvDate",
    "InvNo", "AccountObjectID", "AccountObjectName", "AccountObjectNameDI", "CompanyTaxCode",
    "BranchID", "PurchasePurposeID", "SortOrder", "RefOrder", "RefType", "RefDate", "PostedDate",
    "RefNo", "AccountObjectCode", "IsUpdateRedundant", "IsPostToManagementBook",
    "NotInVATDeclaration", "OriginInvoicePostedDate", "OriginInvoiceRefType",
    "OriginInvoiceRefID", "OriginInvoiceRefNo", "OriginInvoiceRefDate",
    "OriginInvoiceJournalMemo", "JournalMemo", "OriginRefType", "OriginRefID")
cols_inventoryitem = C("InventoryItemID", "InventoryItemCode", "InventoryItemName",
    "InventoryItemType", "UnitID", "InventoryAccount", "COGSAccount", "SaleAccount", "TaxRate",
    "MinimumStock", "PurchaseDiscountRate", "UnitPrice", "SalePrice1", "SalePrice2",
    "SalePrice3", "FixedSalePrice", "FixedUnitPrice", "IsUnitPriceAfterTax", "IsSystem",
    "Inactive", "IsPromotion", "VAT43Type", "CreatedDate")

TABLES = {
    "PUService": cols_puservice, "PUServiceDetail": cols_puservicedetail,
    "GeneralLedger": cols_gl, "AccountObjectLedger": cols_aol, "CustomFieldLedger": cols_cfl,
    "PurchaseLedger": cols_purl, "TaxLedger": cols_taxl, "InventoryItem": cols_inventoryitem,
}

class FakeCursor:
    def __init__(self):
        self.inserted = {t: [] for t in TABLES}

    def execute(self, sql, *params):
        params = params[0] if len(params) == 1 and isinstance(params[0], (tuple, list)) else params
        self._last_sql = sql
        self._last_params = params
        if sql.startswith("INSERT INTO"):
            table = sql.split(" ")[2]
            cols_str = sql[sql.index("(")+1:sql.index(")")]
            cols = [c.strip("[]") for c in cols_str.split(",")]
            self.inserted[table].append(dict(zip(cols, params)))
        return self

    def fetchall(self):
        sql = self._last_sql
        if 'sys.columns' in sql and 'sys.types' in sql:
            table = self._last_params[0] if isinstance(self._last_params, (list, tuple)) else self._last_params
            return [(c, t) for c, t in TABLES.get(table, [])]
        if sql.startswith("SELECT AccountObjectID, CompanyTaxCode, AccountObjectCode, AccountObjectName"):
            return [("aid-baove", "0314201839", "0314201839", "CÔNG TY TNHH DỊCH VỤ BẢO VỆ MẮT VÀNG")]
        if sql.startswith("SELECT InventoryItemID, InventoryItemCode, UnitID, InventoryItemName"):
            return [("mhdv-id", "MHDV", None, "Mua Hàng Dịch Vụ")]
        if sql.startswith("SELECT AccountNumber FROM Account"):
            return [("331",), ("6427",), ("1331",)]
        if sql.startswith("SELECT UnitID, UnitName FROM Unit"):
            return []
        if sql.startswith("SELECT RefType, RefTypeName FROM SYSRefType WHERE MasterTableName='PUService'"):
            return [(330, "Chứng từ mua dịch vụ chưa thanh toán")]
        if sql.startswith("SELECT RefType, RefTypeName FROM SYSRefType WHERE MasterTableName=?"):
            mt = self._last_params[0] if self._last_params else None
            if mt == "PUService":
                return [(330, "Chứng từ mua dịch vụ chưa thanh toán")]
            return []
        if sql.startswith("SELECT ps.RefType, rt.RefTypeName"):
            return []
        if sql.startswith("SELECT AccountNumber, AccountName FROM Account"):
            return [("331", "Phải trả cho người bán"), ("6427", "Chi phí dịch vụ mua ngoài"),
                    ("1331", "Thuế GTGT được khấu trừ của hàng hóa, dịch vụ")]
        return []

    def fetchone(self):
        sql = self._last_sql
        if sql.startswith("SELECT COUNT(*) FROM PUService"):
            return (len(self.inserted["PUService"]),)
        if sql.startswith("SELECT TOP 1 d.PurchasePurposeID"):
            return None
        if "PurchasePurpose" in sql:
            return None
        return None

ns['_misa_cot_bang_that'] = lambda cur, table: {c.lower(): (c, t) for c, t in TABLES.get(table, [])}
cur = FakeCursor()
class FakeConn:
    def __init__(self, cur): self._cur = cur; self.autocommit = True
    def cursor(self): return self._cur
    def commit(self): self.committed = True
    def rollback(self): self.rolled_back = True
    def close(self): pass
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur)
ns['_misa_branch_id'] = lambda cur: "branch-1"
ns['_misa_tu_dong_sua_dvt_sau_ghi'] = lambda *a, **k: (0, 0)
ns['_misa_tu_kiem_tra_muahang'] = lambda cur, ref_ids, branch_id, bang_chinh, ket: None

def mk_row(doc, ngayct, mst, ten_ncc, ma, ten, dvt, sl, dgia, tt, no, co, ts, tthue, tk_thue, sohd):
    row = [None] * 40
    row[6] = doc; row[5] = ngayct; row[7] = mst; row[8] = ten_ncc
    row[14] = ma; row[15] = ten; row[19] = dvt; row[20] = sl; row[21] = dgia; row[22] = tt
    row[16] = no; row[17] = co; row[27] = ts; row[28] = tthue; row[30] = tk_thue; row[33] = sohd
    return row

flat = [
    mk_row("DV-001", "31/03/2026", "0314201839", "CÔNG TY TNHH DỊCH VỤ BẢO VỆ MẮT VÀNG",
           "MHDV", "Chi phí dịch vụ bảo vệ từ ngày 01/03/2026 đến 31/03/2026", "", 1, 10000000,
           10000000, "6427", "331", 8, 800000, "1331", "216"),
]
ns['_gen_mua_hang_dv'] = lambda cid, header, rows: flat
ns['nhap_lieu_get'] = lambda cid, loai: {"header": [], "rows": [1]}
exec(extract_fn('_misa_ghi_mua_hang_dv'), ns)
_misa_ghi_mua_hang_dv = ns['_misa_ghi_mua_hang_dv']

r = _misa_ghi_mua_hang_dv(1, "TESTDB", preview=False, ghi_de=False)
print("Result:", r["danh_sach"])
assert r["danh_sach"][0]["da_ghi_so_tai_chinh"] is True
assert "đã ghi Sổ Tài chính" in r["danh_sach"][0]["trang_thai"]

ps = cur.inserted["PUService"]
assert len(ps) == 1 and ps[0]["IsPostedFinance"] is True
assert ps[0]["IsPostedManagement"] in (0, False, None)
print("PASS: PUService IsPostedFinance=True, IsPostedManagement vẫn False")

psd = cur.inserted["PUServiceDetail"]
assert len(psd) == 1
print("PASS: 1 dòng PUServiceDetail")

gl = cur.inserted["GeneralLedger"]
assert len(gl) == 4, f"1 dong x 2 cap (gia tri + thue) = 4 GL, got {len(gl)}"
goods = [g for g in gl if g["AccountNumber"] == "6427" or g["CorrespondingAccountNumber"] == "6427"]
vat = [g for g in gl if g["AccountNumber"] == "1331" or g["CorrespondingAccountNumber"] == "1331"]
assert len(goods) == 2 and len(vat) == 2
assert sum(g["DebitAmountOC"] for g in goods) == 10000000
assert sum(g["DebitAmountOC"] for g in vat) == 800000
assert all(g["DetailPostOrder"] == 1 for g in goods), "cap gia tri DetailPostOrder phai =1"
assert all(g["DetailPostOrder"] == 2 for g in vat), "cap thue DV DetailPostOrder phai =2 (KHAC PUVoucher=5)"
print("PASS: 4 dòng GeneralLedger đúng số tiền, DetailPostOrder=1(giá trị)/2(thuế) đúng kiểu Dịch vụ")

aol = cur.inserted["AccountObjectLedger"]
assert len(aol) == 2, f"expected 2 AOL (1 giá trị + 1 thuế), got {len(aol)}"
for a in aol:
    assert a["AccountNumber"] == "331"
    assert "#216#" in a["PayKeyID"], f"PayKeyID Dich vu phai co InvNo, got {a['PayKeyID']}"
    assert a["DebtKeyID"].split("#")[2] == "331", f"DebtKeyID phai co AccountNumber sau RefID#AccountObjectID#, got {a['DebtKeyID']}"
print("PASS: 2 dòng AccountObjectLedger, PayKeyID/DebtKeyID đúng định dạng riêng của Dịch vụ (có InvNo/InvDate)")

cfl = cur.inserted["CustomFieldLedger"]
assert len(cfl) == 1
purl = cur.inserted["PurchaseLedger"]
assert len(purl) == 1
taxl = cur.inserted["TaxLedger"]
assert len(taxl) == 1
assert taxl[0]["VATAmountOC"] == 800000 and taxl[0]["TurnOverAmountOC"] == 10000000
print("PASS: CustomFieldLedger/PurchaseLedger/TaxLedger đều ghi đúng 1 dòng, TaxLedger đúng số tiền")

# Lỗi thật đã gặp trên CSDL thật: "Cannot insert the value NULL into column 'MainConvertRate'"
# — dòng Dịch vụ có UnitID=None (không có ĐVT) khiến biểu thức "m['uid'] and 1" trả về None
# (không phải 0) do Python short-circuit "and" trả về TOÁN HẠNG rỗng, không phải giá trị mặc
# định — FakeCursor không có ràng buộc NOT NULL nên bài test cũ không bắt được lỗi này, phải
# kiểm tra tường minh không có cột NOT NULL nào bị gán None.
NOT_NULL_COLS = {"MainConvertRate"}
for bang, rows_ins in cur.inserted.items():
    for row in rows_ins:
        for k, v in row.items():
            if k in NOT_NULL_COLS:
                assert v is not None, f"{bang}.{k} bị NULL (vi phạm NOT NULL) trong dòng {row}"
print("PASS: không có cột NOT NULL (MainConvertRate) nào bị gán None — đúng bug đã gặp trên CSDL thật")

print("\nALL DONE")

# --- Test 2: đúng lỗi THẬT người dùng vừa báo (Đối chiếu tổng giá trị &
# VAT xác nhận nhiều hóa đơn Mua hàng Dịch vụ ĐÃ CÓ ĐỦ trong Bảng kê Đầu
# vào nhưng "Import tự động toàn bộ" báo NHẦM "đã có sẵn trong MISA", 0
# chứng từ được ghi). NCC "0314201839" đã có 1 hóa đơn KHÁC hẳn Số HĐ
# "216" từ NĂM 2021 trong PUServiceDetail — hóa đơn MỚI đang ghi CÙNG NCC,
# CÙNG Số HĐ "216" nhưng tháng 3/2026 (cách nhau gần 5 năm) PHẢI được ghi
# bình thường, KHÔNG được coi là trùng (PUServiceDetail chưa ghi InvSeries
# để phân biệt Ký hiệu, nên trước đây chỉ khớp thô (MST,Số HĐ) không xét
# ngày).
class FakeCursor2(FakeCursor):
    def fetchall(self):
        sql = self._last_sql
        if "SELECT TaxAccountObjectTaxCode, InvNo" in sql and "FROM PUServiceDetail" in sql:
            if "[InvDate]" in sql:
                return [("0314201839", "216", datetime.datetime(2021, 6, 1))]
            return [("0314201839", "216")]
        return super().fetchall()


cur2 = FakeCursor2()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur2)
flat2 = [
    mk_row("DV-999", "15/03/2026", "0314201839", "CÔNG TY TNHH DỊCH VỤ BẢO VỆ MẮT VÀNG",
           "MHDV", "Chi phí dịch vụ bảo vệ từ ngày 01/03/2026 đến 15/03/2026", "", 1, 5000000,
           5000000, "6427", "331", 8, 400000, "1331", "216"),
]
ns['_gen_mua_hang_dv'] = lambda cid, header, rows: flat2
exec(extract_fn('_misa_ghi_mua_hang_dv'), ns)
_misa_ghi_mua_hang_dv = ns['_misa_ghi_mua_hang_dv']
r2 = _misa_ghi_mua_hang_dv(1, "TESTDB", preview=False, ghi_de=False)
print("Result2:", r2["danh_sach"])
assert r2["danh_sach"][0]["trang_thai"] == "đã thêm (đã ghi Sổ Tài chính)", (
    f"Hóa đơn Số HĐ '216' (NCC 0314201839) tháng 3/2026 PHẢI được ghi bình thường — hóa đơn Số HĐ "
    f"'216' ĐÃ CÓ trong PUServiceDetail là từ NĂM 2021 (cách gần 5 năm), KHÔNG được coi là cùng 1 hóa "
    f"đơn chỉ vì trùng (MST,Số HĐ) — đúng lỗi thật đã báo cáo (Đối chiếu tổng giá trị & VAT xác nhận "
    f"nhiều hóa đơn Mua hàng chưa có trong MISA nhưng Import tự động toàn bộ vẫn báo 'đã có sẵn', 0 "
    f"chứng từ được ghi) — got {r2['danh_sach'][0]}")
assert len(cur2.inserted["PUService"]) == 1
print("PASS: Test 2 — hóa đơn Số HĐ '216' (NCC 0314201839) KHÔNG còn bị khớp nhầm với hóa đơn CÙNG Số "
      "HĐ của CÙNG NCC nhưng từ gần 5 năm trước trong PUServiceDetail — đã ghi đúng, không còn bỏ qua "
      "nhầm.")

print("\nALL DONE (test 2)")

# --- Test 3: đúng lỗi THẬT khác vừa gặp (3/9/2026, sau khi hạ ngưỡng 400
# ngày còn CHƯA đủ) — Đối chiếu tổng giá trị & VAT báo "THIẾU" hóa đơn Số
# HĐ "41" (NCC 3603122733, ngày 08/01/2026) dù Bảng kê Đầu vào đã có đủ,
# TK Nợ hợp lệ (6427), đúng nhóm — dùng công cụ "🔍 Vì sao đã có?" lộ ra
# NCC này CÓ 4 dòng PUServiceDetail CŨ trong MISA cùng Số HĐ "41" nhưng
# ngày 2025-01-10 (CÁCH ĐÚNG 363 NGÀY, dưới ngưỡng 400 ngày cũ) — 2 hóa
# đơn HOÀN TOÀN KHÁC NHAU của CÙNG 1 NCC (NCC đánh số hóa đơn lại theo
# NĂM, "41" xuất hiện lại sau đúng 1 năm) bị khớp NHẦM, hóa đơn 2026 thật
# không bao giờ ghi được. Ngưỡng hạ xuống 90 ngày để LOẠI được ca này.
class FakeCursor3(FakeCursor):
    def fetchall(self):
        sql = self._last_sql
        if "SELECT TaxAccountObjectTaxCode, InvNo" in sql and "FROM PUServiceDetail" in sql:
            if "[InvDate]" in sql:
                return [("3603122733", "41", datetime.datetime(2025, 1, 10))] * 4
            return [("3603122733", "41")] * 4
        if sql.startswith("SELECT AccountObjectID, CompanyTaxCode, AccountObjectCode, AccountObjectName"):
            return [("aid-giayphu", "3603122733", "3603122733",
                     "CÔNG TY TNHH MỘT THÀNH VIÊN SẢN XUẤT THƯƠNG MẠI GIẤY PHÚ VINH PHÚC")]
        return super().fetchall()


cur3 = FakeCursor3()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur3)
flat3 = [
    mk_row("DV-998", "08/01/2026", "3603122733",
           "CÔNG TY TNHH MỘT THÀNH VIÊN SẢN XUẤT THƯƠNG MẠI GIẤY PHÚ VINH PHÚC",
           "MHDV", "Thùng carton(415*415*420)", "Cái", 30, 23332, 699960, "6427", "331",
           8, 55997, "1331", "41"),
]
ns['_gen_mua_hang_dv'] = lambda cid, header, rows: flat3
exec(extract_fn('_misa_ghi_mua_hang_dv'), ns)
_misa_ghi_mua_hang_dv = ns['_misa_ghi_mua_hang_dv']
r3 = _misa_ghi_mua_hang_dv(1, "TESTDB", preview=False, ghi_de=False)
print("Result3:", r3["danh_sach"])
assert r3["danh_sach"][0]["trang_thai"] == "đã thêm (đã ghi Sổ Tài chính)", (
    f"Hóa đơn Số HĐ '41' (NCC 3603122733) ngày 08/01/2026 PHẢI được ghi bình thường — hóa đơn Số HĐ "
    f"'41' ĐÃ CÓ trong PUServiceDetail là từ 2025-01-10 (cách ĐÚNG 363 ngày, dưới ngưỡng CŨ 400 ngày "
    f"nhưng NGOÀI ngưỡng MỚI 90 ngày), 2 hóa đơn HOÀN TOÀN KHÁC NHAU của CÙNG NCC (đánh số lại theo "
    f"năm) — đúng lỗi thật đã báo cáo (Đối chiếu tổng giá trị & VAT xác nhận hóa đơn này chưa có trong "
    f"MISA, công cụ 'Vì sao đã có?' lộ ra 4 ứng viên PUServiceDetail cùng Số HĐ nhưng khác năm) — "
    f"got {r3['danh_sach'][0]}")
assert len(cur3.inserted["PUService"]) == 1
print("PASS: Test 3 — hóa đơn Số HĐ '41' (NCC 3603122733) ngày 08/01/2026 KHÔNG còn bị khớp nhầm với "
      "hóa đơn CÙNG Số HĐ của CÙNG NCC nhưng cách đúng 363 ngày (dưới ngưỡng cũ 400, ngoài ngưỡng mới "
      "90) trong PUServiceDetail — đã ghi đúng, không còn bỏ qua nhầm.")

print("\nALL DONE (test 3)")
