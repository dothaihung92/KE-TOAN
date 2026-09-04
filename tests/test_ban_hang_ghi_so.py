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

names = ['_misa_cot_bang_that', '_misa_gia_tri_mac_dinh', '_misa_chon_cot', '_misa_gan',
         '_misa_khncc_chuan_mst', '_misa_branch_id', '_misa_tk_fallback', '_misa_pu_reftype',
         '_to_num', '_chuan_mst', '_dinh_dang_mst', '_bh_cols', '_ky_hieu_chac_chan_khac',
         '_misa_ghi_ban_hang']
for n in names:
    exec(extract_fn(n), ns)
ns['_chuan_thue_suat'] = lambda v: (round(v) if v else 0)

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

for varname in ('_SA_VOUCHER_DEFAULT', '_SA_VOUCHER_DET_DEFAULT', '_SA_INVOICE_DEFAULT'):
    code = _extract_dict_literal(varname)
    exec(code, ns)

def C(*names):
    return [(n, "nvarchar") for n in names]

cols_savoucher = C("RefID", "BranchID", "DisplayOnBook", "RefType", "RefDate", "PostedDate",
    "RefNoFinance", "RefNoManagement", "IsPostedFinance", "IsPostedManagement", "IncludeInvoice",
    "IsInvoiceExported", "AccountObjectID", "AccountObjectName", "AccountObjectTaxCode",
    "JournalMemo", "TotalSaleAmountOC", "TotalSaleAmount", "TotalAmountOC", "TotalAmount",
    "TotalVATAmountOC", "TotalVATAmount", "InvNo", "InvDate", "InvSeries", "CreatedDate",
    "CreatedBy", "ModifiedDate", "ModifiedBy", "RefOrder", "CustomField10",
    "AccountObjectAddress", "Payer", "ShippingAddress", "CurrencyID", "ExchangeRate")
cols_savoucherdetail = C("RefDetailID", "RefID", "InventoryItemID", "Description", "DebitAccount",
    "CreditAccount", "UnitID", "Quantity", "UnitPrice", "AmountOC", "Amount", "MainQuantity",
    "MainUnitPrice", "DiscountAccount", "VATRate", "VATAmountOC", "VATAmount", "VATAccount",
    "VATDescription", "AccountObjectID", "AccountObjectName", "QuantityBilled",
    "MainQuantityBilled", "AmountAfterTax", "SortOrder", "GuarantyPeriod",
    "AccountObjectAddress", "SAInvoiceRefID", "StockID")
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
cols_sll = C("SaleLedgerID", "BranchID", "RefID", "RefDetailID", "RefType", "RefNo", "RefDate",
    "PostedDate", "CurrencyID", "ExchangeRate", "InvDate", "InvSeries", "InvNo", "JournalMemo",
    "InventoryItemID", "Description", "StockID", "DebitAccount", "CreditAccount", "UnitID",
    "UnitPrice", "SaleQuantity", "SaleAmountOC", "SaleAmount", "DiscountRate",
    "DiscountAmountOC", "DiscountAmount", "DiscountAccount", "VATRate", "VATAmountOC",
    "VATAmount", "VATAccount", "ReturnQuantity", "ReturnAmountOC", "ReturnAmount",
    "ReduceAmountOC", "ReduceAmount", "IsPromotion", "MainUnitID", "MainUnitPrice",
    "MainConvertRate", "MainQuantity", "ExchangeRateOperator", "IsPostToManagementBook",
    "AccountObjectID", "AccountObjectName", "SortOrder", "RefOrder", "InventoryItemCode",
    "InventoryItemName", "AccountObjectCode", "IsUpdateRedundant", "AccountObjectNameDI",
    "RefTypeName", "ReturnMainQuantity", "ReceiptAmountOC", "ReceiptAmount", "UnitPriceOC",
    "MainUnitPriceOC")
cols_inventoryitem = C("InventoryItemID", "InventoryItemCode", "InventoryItemName",
    "InventoryItemType", "UnitID", "InventoryAccount", "COGSAccount", "SaleAccount", "TaxRate",
    "MinimumStock", "PurchaseDiscountRate", "UnitPrice", "SalePrice1", "SalePrice2",
    "SalePrice3", "FixedSalePrice", "FixedUnitPrice", "IsUnitPriceAfterTax", "IsSystem",
    "Inactive", "IsPromotion", "VAT43Type", "CreatedDate")
cols_accountobject = C("AccountObjectID", "AccountObjectCode", "AccountObjectName", "IsVendor",
    "IsCustomer", "AccountObjectType", "Inactive", "BranchID", "CreatedDate")

TABLES = {
    "SAVoucher": cols_savoucher, "SAVoucherDetail": cols_savoucherdetail,
    "GeneralLedger": cols_gl, "AccountObjectLedger": cols_aol, "CustomFieldLedger": cols_cfl,
    "SaleLedger": cols_sll, "InventoryItem": cols_inventoryitem, "AccountObject": cols_accountobject,
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
            return [("aid-kh1", "0100109106", "0100109106", "CÔNG TY TNHH KHÁCH HÀNG A")]
        if sql.startswith("SELECT InventoryItemID, InventoryItemCode, UnitID, InventoryItemName"):
            return [("bh-id", "BH", None, "Bán Hàng")]
        if sql.startswith("SELECT AccountNumber FROM Account"):
            return [("131",), ("5111",), ("33311",), ("5211",)]
        if sql.startswith("SELECT RefType, RefTypeName FROM SYSRefType WHERE MasterTableName='SAInvoice'"):
            return []
        if sql.startswith("SELECT RefType, RefTypeName FROM SYSRefType WHERE MasterTableName='SAVoucher'"):
            return [(3531, "Bán hàng hóa, dịch vụ trong nước - Tiền mặt"),
                    (3532, "Bán hàng hóa, dịch vụ trong nước - Chưa thu tiền")]
        if sql.startswith("SELECT RefType, RefTypeName FROM SYSRefType WHERE MasterTableName=?"):
            mt = self._last_params[0] if self._last_params else None
            if mt == "SAVoucher":
                return [(3531, "Bán hàng hóa, dịch vụ trong nước - Tiền mặt"),
                        (3532, "Bán hàng hóa, dịch vụ trong nước - Chưa thu tiền")]
            return []
        if sql.startswith("SELECT sv.RefType, rt.RefTypeName"):
            return []
        if "RefNoManagement FROM SAVoucher WHERE RefNoManagement LIKE 'BH%'" in sql:
            return []
        if sql.startswith("SELECT AccountNumber, AccountName FROM Account"):
            return [("131", "Phải thu của khách hàng"), ("5111", "Doanh thu bán hàng hóa"),
                    ("33311", "Thuế GTGT đầu ra")]
        return []

    def fetchone(self):
        sql = self._last_sql
        if sql.startswith("SELECT COUNT(*) FROM SAVoucher"):
            return (len(self.inserted["SAVoucher"]),)
        if "SVD.StockID" in sql or "svd.StockID" in sql:
            return None
        if sql.startswith("SELECT TOP 1 StockID FROM Stock"):
            return None
        if "RefID, RefNoManagement, ISNULL(AccountObjectTaxCode" in sql:
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
ns['_misa_tu_kiem_tra_muahang'] = lambda cur, ref_ids, branch_id, bang_chinh, ket: None

header = ["Ngày lập", "Số hóa đơn", "MST người mua", "Tên người mua", "Mặt hàng",
          "Doanh số bán chưa thuế", "Thuế GTGT", "Ký hiệu HĐ", "Ký hiệu mẫu"]
rows = [
    ["31/03/2026", "2968", "0100109106", "CÔNG TY TNHH KHÁCH HÀNG A", "Bán Hàng",
     846700, 0, "", ""],
]
ns['nhap_lieu_get'] = lambda cid, loai: {"header": header, "rows": rows}
exec(extract_fn('_misa_ghi_ban_hang'), ns)
_misa_ghi_ban_hang = ns['_misa_ghi_ban_hang']

r = _misa_ghi_ban_hang(1, "TESTDB", preview=False, ghi_de=False)
print("Result:", r["danh_sach"])
assert r["danh_sach"][0]["da_ghi_so_tai_chinh"] is True
assert "đã ghi Sổ Tài chính" in r["danh_sach"][0]["trang_thai"]

sv = cur.inserted["SAVoucher"]
assert len(sv) == 1 and sv[0]["IsPostedFinance"] is True
assert sv[0]["IsPostedManagement"] in (0, False, None)
print("PASS: SAVoucher IsPostedFinance=True, IsPostedManagement vẫn False")

svd = cur.inserted["SAVoucherDetail"]
assert len(svd) == 1 and svd[0]["DebitAccount"] == "131"
print("PASS: 1 dòng SAVoucherDetail, TK Nợ=131 (công nợ)")

gl = cur.inserted["GeneralLedger"]
# VAT=0 trong test này -> chỉ ghi cặp doanh thu (2 dòng), KHÔNG ghi cặp thuế (thue=0 -> if thue: False)
assert len(gl) == 2, f"expected 2 GL (chỉ cặp doanh thu vì thue=0), got {len(gl)}"
tong_no = sum(g["DebitAmountOC"] for g in gl)
tong_co = sum(g["CreditAmountOC"] for g in gl)
assert tong_no == 846700 and tong_co == 846700
by_acc = {g["AccountNumber"]: g for g in gl}
assert by_acc["131"]["DebitAmountOC"] == 846700 and by_acc["131"]["DetailPostOrder"] == 1
assert by_acc["5111"]["CreditAmountOC"] == 846700
print("PASS: 2 dòng GeneralLedger đúng cặp Nợ 131/Có 5111 = 846.700, DetailPostOrder=1")

aol = cur.inserted["AccountObjectLedger"]
assert len(aol) == 1, f"expected 1 AOL (chỉ cặp doanh thu, thue=0 nên không có dòng thuế), got {len(aol)}"
assert aol[0]["AccountNumber"] == "131" and aol[0]["DebitAmountOC"] == 846700
print("PASS: 1 dòng AccountObjectLedger cho TK 131 (công nợ phải thu), đúng vế Nợ")

cfl = cur.inserted["CustomFieldLedger"]
assert len(cfl) == 1
sll = cur.inserted["SaleLedger"]
assert len(sll) == 1 and sll[0]["SaleAmountOC"] == 846700
print("PASS: CustomFieldLedger + SaleLedger đúng 1 dòng")

print("\nALL DONE")

# --- Test 2: có thuế GTGT > 0 -> phải ghi thêm cặp thuế (GL +2, AOL +1) ---
cur2 = FakeCursor()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur2)
rows2 = [
    ["31/03/2026", "2969", "0100109106", "CÔNG TY TNHH KHÁCH HÀNG A", "Bán Hàng",
     1000000, 80000, "", ""],
]
ns['nhap_lieu_get'] = lambda cid, loai: {"header": header, "rows": rows2}
exec(extract_fn('_misa_ghi_ban_hang'), ns)
_misa_ghi_ban_hang = ns['_misa_ghi_ban_hang']
r2 = _misa_ghi_ban_hang(1, "TESTDB", preview=False, ghi_de=False)
gl2 = cur2.inserted["GeneralLedger"]
assert len(gl2) == 4, f"expected 4 GL (2 cap: doanh thu + thue), got {len(gl2)}"
vat_rows = [g for g in gl2 if g["AccountNumber"] == "33311" or g["CorrespondingAccountNumber"] == "33311"]
assert len(vat_rows) == 2
assert all(g["DetailPostOrder"] == 3 for g in vat_rows), "cap thue Ban hang DetailPostOrder phai =3"
assert sum(g["DebitAmountOC"] for g in vat_rows if g["AccountNumber"] == "131") == 0  # thue ghi Có/No the nao? kiem tra tong
aol2 = cur2.inserted["AccountObjectLedger"]
assert len(aol2) == 2, f"expected 2 AOL (doanh thu + thue), got {len(aol2)}"
tong_no_aol = sum(a["DebitAmountOC"] for a in aol2)
assert tong_no_aol == 1080000, f"tong AOL debit phai = 1000000+80000=1080000, got {tong_no_aol}"
print("PASS: Test 2 — có thuế GTGT: 4 dòng GL (2 cặp), 2 dòng AOL, DetailPostOrder=3 cho cặp thuế")

print("\nALL DONE (test 2)")

# --- Test 3: đúng lỗi thật người dùng báo (bảng đối chiếu tổng giá trị & VAT)
# — KH "MAC MARKETING" MST 0314263169 có 2 hóa đơn KHÁC NHAU hoàn toàn
# nhưng CÙNG Số HĐ=29 vì khác Ký hiệu (Số hóa đơn chỉ duy nhất TRONG PHẠM
# VI 1 Ký hiệu). MISA đã có sẵn HĐ 29/Ký hiệu "1C26TKK" (khách tự nhập tay,
# không phải phần mềm tạo) — hóa đơn MỚI đang ghi là 29/"1C25TKK" (Ký hiệu
# KHÁC hẳn) PHẢI được ghi bình thường, KHÔNG được coi là trùng.
class FakeCursor3(FakeCursor):
    def fetchall(self):
        sql = self._last_sql
        if sql.startswith("SELECT AccountObjectID, CompanyTaxCode, AccountObjectCode, AccountObjectName"):
            return [("aid-mac", "0314263169", "0314263169", "CÔNG TY CỔ PHẦN MAC MARKETING")]
        if "ISNULL(AccountObjectTaxCode,''), ISNULL(InvNo,''), ISNULL(InvSeries,'')" in sql and \
                "FROM SAVoucher WHERE ISNULL(InvNo,'')<>''" in sql:
            # 1 hóa đơn 29/"1C26TKK" đã có sẵn (khách tự nhập tay) — KHÔNG
            # trùng Ký hiệu với hóa đơn MỚI (29/"1C25TKK") đang ghi.
            return [("0314263169", "29", "1C26TKK", datetime.datetime(2025, 11, 1))]
        return super().fetchall()


cur3 = FakeCursor3()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur3)
rows3 = [
    ["19/11/2025", "29", "0314263169", "CÔNG TY CỔ PHẦN MAC MARKETING", "Bán Hàng",
     12000000, 960000, "1C25TKK", ""],
]
ns['nhap_lieu_get'] = lambda cid, loai: {"header": header, "rows": rows3}
exec(extract_fn('_misa_ghi_ban_hang'), ns)
_misa_ghi_ban_hang = ns['_misa_ghi_ban_hang']
r3 = _misa_ghi_ban_hang(1, "TESTDB", preview=False, ghi_de=False)
print("Result 3:", r3["danh_sach"])
assert r3["danh_sach"][0]["trang_thai"] == "đã thêm (đã ghi Sổ Tài chính)", (
    f"HĐ 29/'1C25TKK' PHẢI được ghi bình thường (Ký hiệu KHÁC hẳn HĐ 29/'1C26TKK' đã có sẵn trong "
    f"MISA) — KHÔNG được coi là trùng và bỏ qua — đúng lỗi thực tế người dùng báo (khóa cũ chỉ "
    f"(MST, Số HĐ) khiến hóa đơn này bị bỏ qua nhầm) — got {r3['danh_sach'][0]}")
sv3 = cur3.inserted["SAVoucher"]
assert len(sv3) == 1 and sv3[0]["InvNo"] == "29" and sv3[0]["InvSeries"] == "1C25TKK"
print("PASS: Test 3 — HĐ 29/Ký hiệu '1C25TKK' (KH MAC MARKETING) ghi ĐÚNG vào MISA dù đã có sẵn HĐ "
      "29/Ký hiệu '1C26TKK' KHÁC của CÙNG khách hàng — khóa trùng lặp giờ có Ký hiệu HĐ nên không còn "
      "coi 2 hóa đơn khác Ký hiệu là trùng nhau nữa (đúng nguyên nhân gốc hóa đơn số 29 ngày "
      "19/11/2025 bị sót khi ghi vào MISA).")

print("\nALL DONE (test 3)")

# --- Test 4: đúng lỗi MỚI người dùng vừa báo — bắt CỨNG khóa phải luôn có
# Ký hiệu HĐ (như Test 3) khiến hóa đơn ĐÃ GHI đúng trước đó (Ký hiệu THẬT
# "1C25TKK" trong MISA) bị ghi THÊM 1 bản trùng vì Bảng kê Đầu ra HIỆN TẠI
# không đọc được cột "Ký hiệu HĐ" (vd header khác, kyhieu="" ) — 1 bên rỗng/
# không rõ PHẢI coi là CÓ THỂ trùng (an toàn), không phải "chắc chắn khác".
class FakeCursor4(FakeCursor):
    def fetchall(self):
        sql = self._last_sql
        if sql.startswith("SELECT AccountObjectID, CompanyTaxCode, AccountObjectCode, AccountObjectName"):
            return [("aid-hd12", "0800000012", "0800000012", "KHÁCH HÀNG SỐ 12")]
        if "ISNULL(AccountObjectTaxCode,''), ISNULL(InvNo,''), ISNULL(InvSeries,'')" in sql and \
                "FROM SAVoucher WHERE ISNULL(InvNo,'')<>''" in sql:
            # HĐ 12 ĐÃ CÓ trong MISA với Ký hiệu THẬT "1C25TKK".
            return [("0800000012", "12", "1C25TKK", datetime.datetime(2025, 10, 10))]
        return super().fetchall()


cur4 = FakeCursor4()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur4)
header4 = ["Ngày lập", "Số hóa đơn", "MST người mua", "Tên người mua", "Mặt hàng",
           "Doanh số bán chưa thuế", "Thuế GTGT"]   # KHÔNG có cột "Ký hiệu HĐ"
rows4 = [
    ["14/10/2025", "12", "0800000012", "KHÁCH HÀNG SỐ 12", "Bán Hàng", 1150000, 57500],
]
ns['nhap_lieu_get'] = lambda cid, loai: {"header": header4, "rows": rows4}
exec(extract_fn('_misa_ghi_ban_hang'), ns)
_misa_ghi_ban_hang = ns['_misa_ghi_ban_hang']
r4 = _misa_ghi_ban_hang(1, "TESTDB", preview=False, ghi_de=False)
print("Result 4:", r4["danh_sach"])
assert "bỏ qua" in r4["danh_sach"][0]["trang_thai"] and "đã có sẵn" in r4["danh_sach"][0]["trang_thai"], (
    f"HĐ 12 ĐÃ CÓ trong MISA (Ký hiệu '1C25TKK') phải được BỎ QUA dù Bảng kê Đầu ra hiện tại KHÔNG "
    f"đọc được cột Ký hiệu HĐ (kyhieu rỗng) — 1 bên rỗng/không rõ PHẢI coi là CÓ THỂ trùng (an toàn), "
    f"KHÔNG được ghi thêm bản trùng — đúng lỗi MỚI người dùng vừa báo (204 chứng từ bị ghi lại) — "
    f"got {r4['danh_sach'][0]}")
assert len(cur4.inserted["SAVoucher"]) == 0, "KHÔNG được ghi thêm SAVoucher nào (đã có sẵn, phải bỏ qua)"
print("PASS: Test 4 — HĐ 12 ĐÃ CÓ trong MISA (Ký hiệu THẬT '1C25TKK') vẫn được nhận đúng là TRÙNG dù "
      "Bảng kê Đầu ra hiện tại không đọc được cột Ký hiệu HĐ (kyhieu rỗng) — chỉ coi là 'chắc chắn "
      "khác' khi CẢ 2 bên đều có Ký hiệu thật và khác nhau, không phải hễ khác chuỗi là khác hóa đơn "
      "— sửa đúng lỗi MỚI (ghi trùng hàng loạt) mà KHÔNG làm mất fix gốc ở Test 3.")

print("\nALL DONE (test 4)")

# --- Test 5: đúng lỗi THẬT người dùng vừa báo (ảnh chụp banHangImportMisa()
# preview) — HẦU HẾT/TẤT CẢ hóa đơn bị báo sai "bỏ qua — Khách hàng (MST...)
# chưa có trong MISA" dù khách hàng ĐÃ CÓ thật trong Danh mục Đối tượng
# MISA. Nguyên nhân: vòng lặp dựng _pm_invoices (bản ghi do CHÍNH phần mềm
# tạo trước đó, SAVoucher.CustomField10=_PM_MARK) dùng biến "kh" cho GIÁ
# TRỊ KÝ HIỆU HĐ của từng dòng — TRÙNG TÊN với dict tra cứu Khách hàng "kh"
# dựng ở đầu hàm — nên khi SAVoucher CÓ ÍT NHẤT 1 dòng phần mềm đã tạo
# trước đó (chắc chắn có sau vài lần chạy thật), vòng lặp GHI ĐÈ "kh"
# thành 1 CHUỖI, làm mọi tra cứu "mst_k not in kh" sau đó thành so sánh
# CHUỖI CON thay vì tra cứu dict -> gần như MỌI khách hàng bị báo sai
# "chưa có trong MISA", 0 chứng từ được ghi dù dữ liệu hoàn toàn hợp lệ.
# 3 test trước KHÔNG bắt được bug này vì FakeCursor.fetchall() mặc định
# trả về [] (rỗng) cho câu SELECT dựng _pm_invoices -> vòng lặp đó KHÔNG
# BAO GIỜ chạy trong test cũ, "kh" không bao giờ bị ghi đè.
class FakeCursor5(FakeCursor):
    def fetchall(self):
        sql = self._last_sql
        if sql.startswith("SELECT AccountObjectID, CompanyTaxCode, AccountObjectCode, AccountObjectName"):
            return [("aid-kh100", "0100109106", "0100109106", "CÔNG TY TNHH KHÁCH HÀNG A")]
        if "RefID, RefNoManagement, ISNULL(AccountObjectTaxCode" in sql and \
                "FROM SAVoucher WHERE ISNULL(CustomField10,'')=?" in sql:
            # Mô phỏng ÍT NHẤT 1 hóa đơn phần mềm đã tạo TRƯỚC ĐÓ (khác hóa
            # đơn ĐANG ghi ở dưới) -> BẮT BUỘC vòng lặp _pm_invoices chạy
            # ít nhất 1 lần để tái hiện đúng bug ghi đè biến "kh".
            return [(1, "BH001/T01/2026", "0100109106", "99", "1C25TKK", 1, 0)]
        return super().fetchall()


cur5 = FakeCursor5()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur5)
rows5 = [
    ["15/01/2026", "100", "0100109106", "CÔNG TY TNHH KHÁCH HÀNG A", "Bán Hàng",
     2000000, 200000, "1C25TKK", ""],
]
ns['nhap_lieu_get'] = lambda cid, loai: {"header": header, "rows": rows5}
exec(extract_fn('_misa_ghi_ban_hang'), ns)
_misa_ghi_ban_hang = ns['_misa_ghi_ban_hang']
r5 = _misa_ghi_ban_hang(1, "TESTDB", preview=False, ghi_de=False)
print("Result 5:", r5["danh_sach"])
assert r5["danh_sach"][0]["trang_thai"] == "đã thêm (đã ghi Sổ Tài chính)", (
    f"HĐ 100 (KH 0100109106 ĐÃ CÓ THẬT trong Danh mục Đối tượng MISA) PHẢI được ghi bình thường — "
    f"KHÔNG được báo sai 'bỏ qua — Khách hàng chưa có trong MISA' chỉ vì SAVoucher đã có 1 hóa đơn "
    f"khác (99) do phần mềm tạo trước đó (kích hoạt vòng lặp _pm_invoices) — đúng bug người dùng vừa "
    f"báo (204/204 hóa đơn báo sai thiếu khách hàng) — got {r5['danh_sach'][0]}")
sv5 = cur5.inserted["SAVoucher"]
assert len(sv5) == 1 and sv5[0]["InvNo"] == "100"
print("PASS: Test 5 — sửa đúng bug biến 'kh' bị vòng lặp _pm_invoices ghi đè thành chuỗi Ký hiệu HĐ "
      "(trùng tên với dict tra cứu Khách hàng) khi SAVoucher đã có sẵn hóa đơn khác do phần mềm tạo "
      "trước đó — không còn báo sai HÀNG LOẠT 'Khách hàng chưa có trong MISA' nữa.")

print("\nALL DONE (test 5)")

# --- Test 6: đúng lỗi THẬT người dùng vừa báo (Đối chiếu tổng giá trị &
# VAT xác nhận 2 hóa đơn Số HĐ 1/2, Khách lẻ, tháng 1/2026 CHẮC CHẮN chưa
# có trong MISA, nhưng "Import tự động toàn bộ" lại báo "bỏ qua — đã có
# sẵn trong MISA", 0 chứng từ được ghi). Nguyên nhân: MST rỗng (Khách lẻ)
# dồn CHUNG 1 nhóm "kl" theo Số HĐ trong _da_co_hoa_don — hóa đơn Khách lẻ
# Số HĐ nhỏ (1) của kỳ ĐANG import trùng số với 1 hóa đơn Khách lẻ HOÀN
# TOÀN KHÁC đã có sẵn trong MISA từ RẤT LÂU trước đó (2023, trước khi dùng
# phần mềm này) — Ký hiệu cả 2 bên đều rỗng (không chắc chắn khác) nên bị
# coi là trùng dù cách nhau tới gần 3 năm.
class FakeCursor6(FakeCursor):
    def fetchall(self):
        sql = self._last_sql
        if sql.startswith("SELECT AccountObjectID, CompanyTaxCode, AccountObjectCode, AccountObjectName"):
            return []   # Khách lẻ -> không cần khớp Danh mục Đối tượng theo MST
        if ("ISNULL(AccountObjectTaxCode,''), ISNULL(InvNo,''), ISNULL(InvSeries,'')" in sql and
                "FROM SAVoucher WHERE ISNULL(InvNo,'')<>''" in sql):
            # Hóa đơn Khách lẻ Số HĐ "1" ĐÃ CÓ trong MISA — NHƯNG từ năm
            # 2023 (RefDate), Ký hiệu rỗng, HOÀN TOÀN không liên quan tới
            # hóa đơn Khách lẻ Số HĐ "1" của kỳ đang import (tháng 1/2026).
            return [("", "1", "", datetime.datetime(2023, 5, 10))]
        return super().fetchall()


cur6 = FakeCursor6()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur6)
rows6 = [
    ["09/01/2026", "1", "", "Khách lẻ", "Bán Hàng", 581338473, 0, "", ""],
]
ns['nhap_lieu_get'] = lambda cid, loai: {"header": header, "rows": rows6}
exec(extract_fn('_misa_ghi_ban_hang'), ns)
_misa_ghi_ban_hang = ns['_misa_ghi_ban_hang']
r6 = _misa_ghi_ban_hang(1, "TESTDB", preview=False, ghi_de=False)
print("Result 6:", r6["danh_sach"])
assert r6["danh_sach"][0]["trang_thai"] == "đã thêm (đã ghi Sổ Tài chính)", (
    f"HĐ Khách lẻ Số HĐ '1' ngày 09/01/2026 PHẢI được ghi bình thường — hóa đơn Khách lẻ Số HĐ '1' "
    f"ĐÃ CÓ trong MISA là từ NĂM 2023 (cách gần 3 năm), Ký hiệu 2 bên đều rỗng nên không chắc chắn "
    f"khác nhau nhưng ngày CÁCH XA quá 400 ngày -> KHÔNG được coi là cùng 1 hóa đơn — đúng lỗi thật đã "
    f"báo cáo (Đối chiếu tổng giá trị & VAT xác nhận hóa đơn này chưa có trong MISA nhưng Import tự "
    f"động toàn bộ vẫn báo 'đã có sẵn', 0 chứng từ được ghi) — got {r6['danh_sach'][0]}")
sv6 = cur6.inserted["SAVoucher"]
assert len(sv6) == 1 and sv6[0]["InvNo"] == "1"
print("PASS: Test 6 — hóa đơn Khách lẻ Số HĐ '1' KHÔNG còn bị khớp nhầm với hóa đơn Khách lẻ khác "
      "Số HĐ '1' từ gần 3 năm trước trong MISA (MST rỗng dồn chung nhóm 'kl', Ký hiệu 2 bên đều rỗng) "
      "— đã ghi đúng, không còn bỏ qua nhầm.")

print("\nALL DONE (test 6)")
