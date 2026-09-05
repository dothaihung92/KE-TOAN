import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys, datetime, uuid as _uuid_mod
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

# Constants copied verbatim from server.py (small, avoid brittle regex extraction of dict literals)
ns['_MISA_GIO_GHI_NHAP'] = 10
ns['_MUA_TEN'] = {"nk": "Mua hàng nhập kho", "kqk": "Mua hàng không qua kho", "dv": "Mua hàng dịch vụ"}
ns['_MUA_COT'] = {
    "nk": dict(doc=6, ngayct=5, sohd=10, mst=12, ten_ncc=13, ma=19, ten=20,
               dvt=25, sl=26, dgia=27, tt=28, no=23, co=24, ts=34, tthue=35,
               tk_thue=38, tkdu_thue=37, nhtg=41, nts=42, nthue=43, ntk=44,
               la_nk_col=1, kho=21),
    "kqk": dict(doc=6, ngayct=5, sohd=9, mst=11, ten_ncc=12, ma=17, ten=18,
                dvt=21, sl=22, dgia=23, tt=24, no=19, co=20, ts=30, tthue=31,
                tk_thue=34, tkdu_thue=33, nhtg=36, nts=37, nthue=38, ntk=39,
                la_nk_col=1, kho=None),
}

ns['_MISA_INV_ACC'] = {
    "hh":   ("1561", "632", "5111", "156%"),
    "nvl":  ("152",  "632", "5111", "152%"),
    "tscd": ("211",  "632", "5111", "211%"),
    "ccdc": ("153",  "632", "5111", "153%"),
}

names = ['_misa_cot_bang_that', '_misa_gia_tri_mac_dinh', '_misa_chon_cot', '_misa_gan',
         '_misa_khncc_chuan_mst', '_misa_branch_id', '_misa_tk_fallback', '_misa_unit_hong',
         '_misa_pu_reftype', '_num0', '_chuan_shd', '_misa_gio_nhap_co_dinh',
         '_misa_loai_dm_theo_tk', '_dm_ky_tu', '_misa_ghi_hang_hoa', '_misa_ghi_mua_hang']
for n in names:
    exec(extract_fn(n), ns)

# Mẫu ĐẦY ĐỦ mọi cột của PUVoucher/PUVoucherDetail (copy verbatim từ server.py, chỉ dùng để test).
def _extract_dict_literal(varname):
    idx = src.index(varname + " = {")
    depth = 0
    i = idx + len(varname) + 3
    start = i
    while True:
        if src[i] == '{':
            depth += 1
        elif src[i] == '}':
            depth -= 1
            if depth == 0:
                break
        i += 1
    return src[idx:i+1]

for varname in ('_PU_HEADER_DEFAULT', '_PU_DETAIL_DEFAULT', '_PU_INV_DEFAULT', '_PU_INV_DET_DEFAULT'):
    code = _extract_dict_literal(varname)
    exec(code, ns)

_misa_ghi_mua_hang = ns['_misa_ghi_mua_hang']

# ---- Cấu trúc cột GIẢ LẬP (rút gọn nhưng đủ mọi cột mà code thật sẽ _misa_gan vào) ----
def C(*names):
    return [(n, "nvarchar") for n in names]

cols_puvoucher = C("RefID", "BranchID", "RefDate", "PostedDate", "CABARefDate", "CABAPostedDate",
    "RefType", "RefNoFinance", "RefNoManagement", "IsPostedFinance", "IsPostedManagement",
    "IncludeInvoice", "PUInvoiceRefID", "AccountObjectID", "AccountObjectName", "JournalMemo",
    "CABAJournalMemo", "TotalAmountOC", "TotalAmount", "TotalImportTaxAmountOC",
    "TotalImportTaxAmount", "TotalVATAmountOC", "TotalVATAmount", "TotalInwardAmount",
    "DisplayOnBook", "CreatedDate", "INRefOrder", "CreatedBy", "ModifiedBy", "ModifiedDate",
    "RefOrder", "IsConvertVAT", "CustomField10", "CurrencyID", "ExchangeRate")
cols_puvoucherdetail = C("RefDetailID", "RefID", "InventoryItemID", "Description", "DebitAccount",
    "CreditAccount", "UnitID", "Quantity", "UnitPrice", "AmountOC", "Amount", "MainQuantity",
    "MainUnitPrice", "MainUnitID", "StockID", "AccountObjectID", "InwardAmount", "FOBAmountOC",
    "FOBAmount", "TaxAccountObjectID", "PurchasePurposeID", "VATDescription", "PUInvoiceRefID",
    "VATRate", "VATAmountOC", "VATAmount", "VATAccount", "DeductionDebitAccount",
    "ImportTaxRatePrice", "ImportTaxRate", "ImportTaxAmountOC", "ImportTaxAmount",
    "ImportTaxAccount", "SortOrder", "InvNo", "InvDate", "InvSeries", "InvTemplateNo")
cols_gl = C("GeneralLedgerID", "RefID", "RefDetailID", "RefType", "RefNo", "RefNo1", "RefNo2",
    "RefDate", "RefDate1", "PostedDate", "InvNo", "InvDate", "InvSeries", "CurrencyID",
    "ExchangeRate", "AccountNumber", "CorrespondingAccountNumber", "AccountName",
    "DebitAmountOC", "DebitAmount", "CreditAmountOC", "CreditAmount", "JournalMemo",
    "Description", "ContactName", "AccountObjectID", "AccountObjectName", "AccountObjectNameDI",
    "AccountObjectCode", "AccountObjectTaxCode", "BranchID", "UnResonableCost",
    "IsPostToManagementBook", "SortOrder", "RefOrder", "InventoryItemID", "InventoryItemCode",
    "InventoryItemName", "IsUpdateRedundant", "RefTypeName", "UnitID", "Quantity",
    "UnitPriceOC", "UnitPrice", "InvRefID", "MainUnitID", "MainUnitPrice", "MainQuantity",
    "MainConvertRate", "ExchangeRateOperator", "MainUnitPriceOC", "EntryType",
    "DetailPostOrder", "IsPostedForCashOutDiff")
cols_aol = C("AccountObjectLedgerID", "BranchID", "RefID", "RefDetailID", "EntryType", "RefType",
    "RefNo", "RefDate", "PostedDate", "InvRefID", "InvNo", "InvDate", "AccountNumber",
    "AccountName", "CorrespondingAccountNumber", "ExchangeRate", "CurrencyID", "UnitID",
    "UnitPriceOC", "UnitPrice", "Quantity", "DebitAmountOC", "DebitAmount", "CreditAmountOC",
    "CreditAmount", "JournalMemo", "Description", "AccountObjectID", "AccountObjectCode",
    "AccountObjectName", "AccountObjectNameDI", "AccountObjectTaxCode", "InventoryItemID",
    "InventoryItemCode", "InventoryItemName", "RefTypeName", "IsPostToManagementBook",
    "RefOrder", "SortOrder", "IsUpdateRedundant", "MainUnitID", "MainUnitPrice", "MainQuantity",
    "MainConvertRate", "ExchangeRateOperator", "DetailPostOrder", "MainUnitPriceOC",
    "PayKeyID", "DebtKeyID")
cols_cfl = C("CustomFieldLegerID", "RefDetailID", "RefID", "IsPostToManagementBook", "BranchID",
    "PostedDate", "IsUpdateRedundant")
cols_invl = C("InventoryLedgerID", "RefID", "RefDetailID", "RefType", "RefNo", "RefDate",
    "PostedDate", "AccountNumber", "CorrespondingAccountNumber", "StockID", "InventoryItemID",
    "UnitID", "UnitPrice", "InwardQuantity", "OutwardQuantity", "InwardAmount", "OutwardAmount",
    "InwardQuantityBalance", "InwardAmountBalance", "JournalMemo", "Description", "BranchID",
    "MainUnitID", "MainUnitPrice", "MainInwardQuantity", "MainOutwardQuantity",
    "MainConvertRate", "ExchangeRateOperator", "IsPromotion", "IsPostToManagementBook",
    "SortOrder", "RefOrder", "IsUnUpdateOutwardPrice", "StockCode", "StockName",
    "InventoryItemCode", "InventoryItemName", "AccountName", "AccountObjectID",
    "AccountObjectCode", "AccountObjectName", "AccountObjectNameDI", "IsUpdateRedundant",
    "RefTypeName", "UnUpdateOutwardPriceType", "InOutWardType", "INRefOrder", "CurrencyID",
    "ExchangeRate", "IsInward", "InventoryResaleTypeID", "RefNoFinance")
cols_purl = C("PurchaseLedgerID", "RefDetailID", "RefID", "BranchID", "PostedDate", "RefDate",
    "RefType", "RefNo", "JournalMemo", "InventoryItemID", "Description", "StockID",
    "DebitAccount", "CreditAccount", "UnitID", "UnitPrice", "PurchaseQuantity",
    "PurchaseAmountOC", "PurchaseAmount", "DiscountRate", "DiscountAmountOC", "DiscountAmount",
    "VATRate", "VATAmount", "VATAmountOC", "VATAccount", "ReturnQuantity", "ReturnAmountOC",
    "ReturnAmount", "ReduceAmountOC", "ReduceAmount", "InvDate", "InvSeries", "InvNo",
    "CurrencyID", "ExchangeRate", "MainUnitID", "MainUnitPrice", "MainConvertRate",
    "MainQuantity", "ExchangeRateOperator", "IsPostToManagementBook", "AccountObjectID",
    "AccountObjectName", "AccountObjectTaxCode", "SortOrder", "RefOrder", "InventoryItemCode",
    "InventoryItemName", "StockCode", "StockName", "AccountObjectCode", "IsUpdateRedundant",
    "AccountObjectNameDI", "RefTypeName", "ReturnMainQuantity", "InvRefID", "UnitPriceOC",
    "MainUnitPriceOC", "IncludeInvoice", "ImportChargeAmount", "FreightAmount")
cols_inout = C("RefID", "RefDate", "PostedDate", "RefType", "RefNoFinance", "IsPostedFinance",
    "IsPostedManagement", "IncludeInvoice", "PUInvoiceRefID", "AccountObjectID",
    "AccountObjectName", "BranchID", "JournalMemo", "TotalAmountOC", "TotalAmount",
    "CreatedDate", "CreatedBy", "ModifiedDate", "ModifiedBy", "CustomField10", "ListTableName",
    "INType", "TotalAmountFinance", "TotalAmountManagement", "RefTypeName", "ContactName",
    "AccountObjectContactName", "CurrencyID", "ExchangeRate", "RefOrder")

cols_puinvoice = C("RefID", "AccountObjectTaxCode", "InvNo", "RefDate", "InvDate")
# Cột InventoryItem/Unit — cần cho _misa_ghi_hang_hoa (TỰ ĐỘNG tạo mã hàng mới
# vào Danh mục MISA khi thiếu mã hàng lúc ghi Nhập kho, xem _misa_ghi_mua_hang).
cols_inventoryitem = C("InventoryItemID", "InventoryItemCode", "InventoryItemName", "InventoryItemType",
    "UnitID", "InventoryAccount", "COGSAccount", "SaleAccount", "TaxRate",
    "MinimumStock", "PurchaseDiscountRate", "UnitPrice", "SalePrice1", "SalePrice2",
    "SalePrice3", "FixedSalePrice", "FixedUnitPrice", "IsUnitPriceAfterTax",
    "IsSystem", "Inactive", "IsPromotion", "VAT43Type", "CreatedDate")
cols_unit = C("UnitID", "UnitName", "Description", "Inactive")

TABLES = {
    "PUVoucher": cols_puvoucher, "PUVoucherDetail": cols_puvoucherdetail,
    "GeneralLedger": cols_gl, "AccountObjectLedger": cols_aol, "CustomFieldLedger": cols_cfl,
    "InventoryLedger": cols_invl, "PurchaseLedger": cols_purl, "INInwardOutwardList": cols_inout,
    "PUInvoice": cols_puinvoice, "InventoryItem": cols_inventoryitem, "Unit": cols_unit,
}

class FakeCursor:
    def __init__(self):
        self.inserted = {t: [] for t in TABLES}
        self.inventory_ledger_existing = []  # [(iid, sid, refdate, inward_qty, outward_qty, inward_amt, outward_amt), ...]

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
            cols = TABLES.get(table, [])
            return [(c, t) for c, t in cols]
        if sql.startswith("SELECT AccountObjectID, CompanyTaxCode, AccountObjectCode, AccountObjectName"):
            return [("aid-doggyman", "0313093362", "0313093362", "CÔNG TY TNHH DOGGYMAN VIỆT NAM"),
                    ("aid-binhanphat", "0317171484", "0317171484", "CÔNG TY TNHH ĐIỆN LẠNH BÌNH AN PHÁT")]
        if sql.startswith("SELECT InventoryItemID, InventoryItemCode, UnitID, InventoryItemName"):
            return [
                ("iid-1", "MH216-0", "uid-cai", "Que gặm hương bò 120g"),
                ("iid-2", "MH217-0", "uid-cai", "Que gặm hương phô mai 120g"),
                ("iid-3", "CCDC072", "uid-cai", "Máy lạnh NAGAKAWA NIS-C09R2U51"),
            ]
        if sql.startswith("SELECT AccountNumber FROM Account"):
            return [("331",), ("1561",), ("1331",), ("242",)]
        if sql.startswith("SELECT UnitID, UnitName FROM Unit"):
            return [("uid-cai", "Cái")]
        if sql.startswith("SELECT StockID, StockCode, StockName FROM Stock"):
            return [("sid-1", "KHOCHINH", "Kho Chính")]
        if sql.startswith("SELECT RefType, RefTypeName FROM SYSRefType WHERE MasterTableName=?"):
            mt = self._last_params[0] if self._last_params else None
            if mt == "PUVoucher":
                return [(302, "Mua hàng trong nước nhập kho chưa thanh toán"),
                        (312, "Mua hàng trong nước không qua kho chưa thanh toán")]
            return []
        if sql.startswith("SELECT RefType, RefTypeName FROM SYSRefType") and "PUInvoice" in sql:
            return []
        if sql.startswith("SELECT pv.RefType, rt.RefTypeName"):
            return []
        if sql.startswith("SELECT AccountNumber, AccountName FROM Account"):
            return [("331", "Phải trả cho người bán"), ("1561", "Giá mua hàng hóa"),
                    ("1331", "Thuế GTGT được khấu trừ của hàng hóa, dịch vụ"),
                    ("242", "Chi phí trả trước")]
        return []

    def fetchone(self):
        sql = self._last_sql
        if sql.startswith("SELECT COUNT(*) FROM PUVoucher"):
            return (len(self.inserted["PUVoucher"]),)
        if sql.startswith("SELECT RefType, RefTypeName FROM SYSRefType WHERE MasterTableName=?"):
            return None
        if "ISNULL(SUM(InwardQuantity-OutwardQuantity),0)" in sql:
            iid, sid, truoc_ngay = self._last_params
            sl = tien = 0
            for (r_iid, r_sid, r_date, iq, oq, ia, oa) in self.inventory_ledger_existing:
                if r_iid == iid and r_sid == sid and r_date < truoc_ngay:
                    sl += (iq - oq); tien += (ia - oa)
            return (sl, tien)
        if "SELECT RefID, RefNoManagement, RefType, ISNULL(IsPostedFinance,0)" in sql:
            return None
        if "OrganizationUnit" in sql:
            return None
        if "SELECT TOP 1 d.PurchasePurposeID" in sql:
            return None
        if "PurchasePurpose" in sql:
            return None
        return None

ns['_misa_cot_bang_that'] = lambda cur, table: {c.lower(): (c, t) for c, t in TABLES.get(table, [])}
exec(extract_fn('_misa_ghi_mua_hang'), ns)
_misa_ghi_mua_hang = ns['_misa_ghi_mua_hang']

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
ns['_misa_tu_dong_sua_dvt_sau_ghi'] = lambda *a, **k: (0, 0)

# flat data đúng cột _MUA_COT["nk"] — 2 dòng hàng cho 1 chứng từ NK-001, ngày 05/01/2026.
def mk_row(doc, ngayct, sohd, mst, ten_ncc, ma, ten, dvt, sl, dgia, tt, no, co, ts, tthue,
           tk_thue, tkdu_thue, kho):
    row = [None] * 46
    row[6] = doc; row[5] = ngayct; row[10] = sohd; row[12] = mst; row[13] = ten_ncc
    row[19] = ma; row[20] = ten; row[25] = dvt; row[26] = sl; row[27] = dgia; row[28] = tt
    row[23] = no; row[24] = co; row[34] = ts; row[35] = tthue; row[38] = tk_thue
    row[37] = tkdu_thue; row[21] = kho
    return row

flat = [
    mk_row("NK-001", "05/01/2026", "326", "0313093362", "CÔNG TY TNHH DOGGYMAN VIỆT NAM",
           "MH216-0", "Que gặm hương bò 120g", "Cái", 45, 36750, 1653750, "1561", "331",
           0, 0, "1331", None, "KHOCHINH"),
    mk_row("NK-001", "05/01/2026", "326", "0313093362", "CÔNG TY TNHH DOGGYMAN VIỆT NAM",
           "MH217-0", "Que gặm hương phô mai 120g", "Cái", 45, 36750, 1653750, "1561", "331",
           0, 0, "1331", None, "KHOCHINH"),
]
ns['_gen_mua_hang_nk'] = lambda cid, header, rows: flat
ns['nhap_lieu_get'] = lambda cid, loai: {"header": [], "rows": [1]}  # chỉ cần non-empty

exec(extract_fn('_misa_ghi_mua_hang'), ns)
_misa_ghi_mua_hang = ns['_misa_ghi_mua_hang']

r = _misa_ghi_mua_hang(1, "TESTDB", "nk", preview=False, ghi_de=False)
print("Result:", r)

assert r["so_chungtu" if "so_chungtu" in r else "danh_sach"] or r.get("danh_sach"), r
ct = r["danh_sach"][0]
print("Chứng từ:", ct)
assert ct["da_ghi_so_tai_chinh"] is True, f"expected da_ghi_so_tai_chinh=True, got {ct}"
assert "đã ghi Sổ Tài chính" in ct["trang_thai"], ct["trang_thai"]

pv = cur.inserted["PUVoucher"]
assert len(pv) == 1, f"expected 1 PUVoucher insert, got {len(pv)}"
assert pv[0]["IsPostedFinance"] is True, "PUVoucher.IsPostedFinance phải =True"
assert pv[0]["IsPostedManagement"] in (0, False, None), \
    f"PUVoucher.IsPostedManagement phải vẫn False/0 (KHÔNG ghi Sổ quản trị), got {pv[0]['IsPostedManagement']}"
print("PASS: PUVoucher IsPostedFinance=True, IsPostedManagement vẫn False")

pvd = cur.inserted["PUVoucherDetail"]
assert len(pvd) == 2, f"expected 2 PUVoucherDetail, got {len(pvd)}"
print("PASS: 2 dòng PUVoucherDetail")

gl = cur.inserted["GeneralLedger"]
# mỗi dòng chi tiết có VATAccount (1331) -> 4 dòng GL (2 cặp); 2 dòng chi tiết -> 8 dòng GL
assert len(gl) == 8, f"expected 8 GeneralLedger rows (2 dòng x 4), got {len(gl)}"
by_refdetail = {}
for g in gl:
    by_refdetail.setdefault(g["RefDetailID"], []).append(g)
for rdid, rows8 in by_refdetail.items():
    assert len(rows8) == 4, f"expected 4 GL rows per detail line, got {len(rows8)} for {rdid}"
    # cặp thuế (1331<->331), amounts = 0 (VAT=0 trong test)
    vat_rows = [g for g in rows8 if g["AccountNumber"] == "1331" or g["CorrespondingAccountNumber"] == "1331"]
    assert len(vat_rows) == 2, vat_rows
    for g in vat_rows:
        assert g["DebitAmountOC"] == 0 and g["CreditAmountOC"] == 0, g
    # cặp giá trị hàng (1561<->331), amounts = 1653750
    goods_rows = [g for g in rows8 if g["AccountNumber"] in ("1561", "331") and g not in vat_rows]
    tong_no = sum(g["DebitAmountOC"] for g in goods_rows)
    tong_co = sum(g["CreditAmountOC"] for g in goods_rows)
    assert tong_no == 1653750 and tong_co == 1653750, (tong_no, tong_co)
print("PASS: 8 dòng GeneralLedger (2 dòng x 2 cặp Nợ/Có), đúng số tiền cặp giá trị hàng = 1,653,750")

aol = cur.inserted["AccountObjectLedger"]
assert len(aol) == 4, f"expected 4 AccountObjectLedger (2 dòng x 2), got {len(aol)}"
for a in aol:
    assert a["AccountNumber"] == "331", a
    assert a["DebitAmountOC"] == 0, "công nợ 331 luôn ở vế Có trong Mua hàng"
paykeys = {a["PayKeyID"] for a in aol}
assert len(paykeys) == 1, f"cùng 1 chứng từ + 1 NCC + 1 TK 331 -> PayKeyID phải GIỐNG NHAU, got {paykeys}"
print("PASS: 4 dòng AccountObjectLedger, đúng vế Có 331, PayKeyID nhất quán trong cùng chứng từ")

cfl = cur.inserted["CustomFieldLedger"]
assert len(cfl) == 2, f"expected 2 CustomFieldLedger, got {len(cfl)}"
print("PASS: 2 dòng CustomFieldLedger")

invl = cur.inserted["InventoryLedger"]
assert len(invl) == 2, f"expected 2 InventoryLedger, got {len(invl)}"
for il in invl:
    assert il["InwardQuantity"] == 45 and il["InwardAmount"] == 1653750
    assert il["InwardQuantityBalance"] == 45, "lần nhập ĐẦU TIÊN của mặt hàng -> số dư luỹ kế = đúng SL dòng này"
    assert il["InwardAmountBalance"] == 1653750
print("PASS: 2 dòng InventoryLedger, số dư luỹ kế ĐÚNG cho lần nhập đầu tiên (không có tồn trước đó)")

purl = cur.inserted["PurchaseLedger"]
assert len(purl) == 2, f"expected 2 PurchaseLedger, got {len(purl)}"
print("PASS: 2 dòng PurchaseLedger")

inout = cur.inserted["INInwardOutwardList"]
assert len(inout) == 1, f"expected 1 INInwardOutwardList (1/chứng từ), got {len(inout)}"
assert inout[0]["ListTableName"] == "PUVoucher"
assert inout[0]["TotalAmountFinance"] == 3307500  # 1653750*2
assert inout[0]["IsPostedFinance"] is True
print("PASS: 1 dòng INInwardOutwardList, TotalAmountFinance đúng tổng, IsPostedFinance=True (copy từ header)")

print("\nALL DONE")

# --- Test 2: 2 chứng từ khác ngày, CÙNG 1 mặt hàng (MH216-0) -> InwardQuantityBalance/
# InwardAmountBalance phải CỘNG DỒN đúng theo thứ tự ngày (bài học rủi ro nhất của tính năng này).
cur2 = FakeCursor()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur2)
flat2 = [
    mk_row("NK-101", "01/01/2026", "900", "0313093362", "CÔNG TY TNHH DOGGYMAN VIỆT NAM",
           "MH216-0", "Que gặm hương bò 120g", "Cái", 10, 36750, 367500, "1561", "331",
           0, 0, "1331", None, "KHOCHINH"),
    mk_row("NK-102", "02/01/2026", "901", "0313093362", "CÔNG TY TNHH DOGGYMAN VIỆT NAM",
           "MH216-0", "Que gặm hương bò 120g", "Cái", 20, 36750, 735000, "1561", "331",
           0, 0, "1331", None, "KHOCHINH"),
]
ns['_gen_mua_hang_nk'] = lambda cid, header, rows: flat2
exec(extract_fn('_misa_ghi_mua_hang'), ns)
_misa_ghi_mua_hang = ns['_misa_ghi_mua_hang']
r2 = _misa_ghi_mua_hang(1, "TESTDB", "nk", preview=False, ghi_de=False)
print("Result2:", r2["danh_sach"])
invl2 = cur2.inserted["InventoryLedger"]
assert len(invl2) == 2, f"expected 2 InventoryLedger (2 chứng từ x 1 dòng), got {len(invl2)}"
il_by_qty = sorted(invl2, key=lambda x: x["InwardQuantity"])
assert il_by_qty[0]["InwardQuantity"] == 10 and il_by_qty[0]["InwardQuantityBalance"] == 10, il_by_qty[0]
assert il_by_qty[1]["InwardQuantity"] == 20 and il_by_qty[1]["InwardQuantityBalance"] == 30, \
    f"chứng từ sau (ngày 02/01) phải cộng dồn 10+20=30, got {il_by_qty[1]}"
assert il_by_qty[1]["InwardAmountBalance"] == 367500 + 735000
print("PASS: Test 2 — InwardQuantityBalance/InwardAmountBalance cộng dồn ĐÚNG qua 2 chứng từ khác ngày cùng mặt hàng (10 -> 30)")

print("\nALL DONE (test 2)")

# --- Test 3: loai='kqk' (Không qua kho) -> phải ghi Sổ Tài chính (GL/AOL/CFL/PurchaseLedger)
# NHƯNG KHÔNG được ghi InventoryLedger/INInwardOutwardList (không có Kho thật) ---
cur3 = FakeCursor()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur3)
def mk_row_kqk(doc, ngayct, sohd, mst, ten_ncc, ma, ten, dvt, sl, dgia, tt, no, co, ts, tthue, tk_thue):
    row = [None] * 40
    row[6] = doc; row[5] = ngayct; row[9] = sohd; row[11] = mst; row[12] = ten_ncc
    row[17] = ma; row[18] = ten; row[21] = dvt; row[22] = sl; row[23] = dgia; row[24] = tt
    row[19] = no; row[20] = co; row[30] = ts; row[31] = tthue; row[34] = tk_thue
    return row
flat3 = [
    mk_row_kqk("KQK-001", "07/01/2026", "11", "0317171484", "CÔNG TY TNHH ĐIỆN LẠNH BÌNH AN PHÁT",
               "CCDC072", "Máy lạnh NAGAKAWA NIS-C09R2U51", "Cái", 1, 4120370, 4120370, "242", "331",
               8, 329630, "1331"),
]
ns['_gen_mua_hang_kqk'] = lambda cid, header, rows: flat3
exec(extract_fn('_misa_ghi_mua_hang'), ns)
_misa_ghi_mua_hang = ns['_misa_ghi_mua_hang']
r3 = _misa_ghi_mua_hang(1, "TESTDB", "kqk", preview=False, ghi_de=False)
print("Result3:", r3["danh_sach"])
assert r3["danh_sach"][0]["da_ghi_so_tai_chinh"] is True
assert len(cur3.inserted["PUVoucher"]) == 1 and cur3.inserted["PUVoucher"][0]["IsPostedFinance"] is True
assert len(cur3.inserted["GeneralLedger"]) == 4, f"1 dong x 2 cap = 4 GL, got {len(cur3.inserted['GeneralLedger'])}"
assert len(cur3.inserted["AccountObjectLedger"]) == 2
assert len(cur3.inserted["CustomFieldLedger"]) == 1
assert len(cur3.inserted["PurchaseLedger"]) == 1
assert len(cur3.inserted["InventoryLedger"]) == 0, "KQK KHÔNG được ghi InventoryLedger (không có Kho)"
assert len(cur3.inserted["INInwardOutwardList"]) == 0, "KQK KHÔNG được ghi INInwardOutwardList (không có Kho)"
print("PASS: Test 3 — KQK ghi đúng GL/AOL/CFL/PurchaseLedger, KHÔNG ghi InventoryLedger/INInwardOutwardList")

print("\nALL DONE (test 3)")

# --- Test 4: đúng lỗi THẬT người dùng vừa báo (Đối chiếu tổng giá trị &
# VAT xác nhận 27 hóa đơn Mua hàng ĐÃ CÓ ĐỦ trong Bảng kê Đầu vào nhưng
# "Import tự động toàn bộ" báo NHẦM "đã có sẵn trong MISA", 0 chứng từ
# được ghi). NCC "0313093362" đã có 1 hóa đơn KHÁC hẳn Số HĐ "326" từ NĂM
# 2022 trong PUInvoice — hóa đơn MỚI đang ghi CÙNG NCC, CÙNG Số HĐ "326"
# nhưng tháng 1/2026 (cách nhau gần 4 năm) PHẢI được ghi bình thường,
# KHÔNG được coi là trùng (PUInvoice chưa ghi InvSeries để phân biệt Ký
# hiệu, nên trước đây chỉ khớp thô (MST,Số HĐ) không xét ngày).
class FakeCursor4(FakeCursor):
    def fetchall(self):
        sql = self._last_sql
        if "SELECT RefID, AccountObjectTaxCode, InvNo" in sql and "FROM PUInvoice" in sql:
            # Trả ĐÚNG số cột theo SQL thật sự yêu cầu — bản CŨ (trước fix)
            # không hề SELECT cột ngày nên chỉ nhận 3 cột (không có ngày để
            # xét, đúng hiện trạng lỗi thật); bản MỚI SELECT thêm [RefDate].
            if "[RefDate]" in sql:
                return [("old-refid-2022", "0313093362", "326", datetime.datetime(2022, 3, 1))]
            return [("old-refid-2022", "0313093362", "326")]
        return super().fetchall()


cur4 = FakeCursor4()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur4)
flat4 = [
    mk_row("NK-999", "10/01/2026", "326", "0313093362", "CÔNG TY TNHH DOGGYMAN VIỆT NAM",
           "MH216-0", "Que gặm hương bò 120g", "Cái", 10, 36750, 367500, "1561", "331",
           0, 0, "1331", None, "KHOCHINH"),
]
ns['_gen_mua_hang_nk'] = lambda cid, header, rows: flat4
exec(extract_fn('_misa_ghi_mua_hang'), ns)
_misa_ghi_mua_hang = ns['_misa_ghi_mua_hang']
r4 = _misa_ghi_mua_hang(1, "TESTDB", "nk", preview=False, ghi_de=False)
print("Result4:", r4["danh_sach"])
assert r4["danh_sach"][0]["trang_thai"] == "đã thêm (đã ghi Sổ Tài chính)", (
    f"Hóa đơn Số HĐ '326' (NCC 0313093362) tháng 1/2026 PHẢI được ghi bình thường — hóa đơn Số HĐ "
    f"'326' ĐÃ CÓ trong PUInvoice là từ NĂM 2022 (cách gần 4 năm), KHÔNG được coi là cùng 1 hóa đơn chỉ "
    f"vì trùng (MST,Số HĐ) — đúng lỗi thật đã báo cáo (Đối chiếu tổng giá trị & VAT xác nhận 27 hóa đơn "
    f"Mua hàng chưa có trong MISA nhưng Import tự động toàn bộ vẫn báo 'đã có sẵn', 0 chứng từ được "
    f"ghi) — got {r4['danh_sach'][0]}")
assert len(cur4.inserted["PUVoucher"]) == 1
print("PASS: Test 4 — hóa đơn Số HĐ '326' (NCC 0313093362) KHÔNG còn bị khớp nhầm với hóa đơn CÙNG Số "
      "HĐ của CÙNG NCC nhưng từ gần 4 năm trước trong PUInvoice — đã ghi đúng, không còn bỏ qua nhầm.")

print("\nALL DONE (test 4)")

# --- Test 5: đúng lỗi THẬT người dùng báo cáo — "4a. Nhập kho vào MISA" bị
# "Lỗi — Lỗi khi ghi vào MISA (đã hoàn tác, không ghi gì): unsupported
# operand type(s) for +: 'decimal.Decimal' and 'float'". Nguyên nhân: mặt
# hàng ĐÃ CÓ giao dịch Sổ Kho (InventoryLedger) TỪ TRƯỚC ngày chứng từ mới
# -> so_du_kho_truoc() phải chạy SUM(...) THẬT qua SQL Server, kết quả trả
# về qua pyodbc là decimal.Decimal (không phải int/float như FakeCursor cơ
# bản ở Test 1-4 lỡ mô phỏng, luôn = 0 nên chưa từng lộ lỗi này) — cộng
# Decimal + float (m["sl"]/m["tt"], luôn là float) ném TypeError, khiến
# GHI VÀO MISA THẤT BẠI HOÀN TOÀN (đã hoàn tác) mỗi khi mặt hàng ĐÃ có tồn
# kho trước đó — đúng trường hợp PHỔ BIẾN NHẤT trong thực tế (hiếm khi 1
# mặt hàng nhập kho lần ĐẦU TIÊN).
import decimal


class FakeCursor5(FakeCursor):
    def fetchone(self):
        row = super().fetchone()
        if row is not None and self._last_sql and \
                "ISNULL(SUM(InwardQuantity-OutwardQuantity),0)" in self._last_sql:
            # Mô phỏng ĐÚNG kiểu dữ liệu pyodbc trả về cho SUM trên cột DECIMAL
            # của SQL Server thật — decimal.Decimal, không phải int/float.
            return tuple(decimal.Decimal(str(v)) for v in row)
        return row


cur5 = FakeCursor5()
# Mặt hàng MH216-0 (iid-1) tại kho KHOCHINH (sid-1) ĐÃ CÓ tồn TRƯỚC đó (SL 10,
# tiền 367.500) từ chứng từ khác/ghi trực tiếp trong MISA trước ngày chứng từ mới.
cur5.inventory_ledger_existing = [
    ("iid-1", "sid-1", datetime.datetime(2026, 1, 1), 10, 0, 367500, 0),
]
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur5)
flat5 = [
    # sl/tt CỐ Ý là số lẻ (float thật, khác Test 1-4 dùng số nguyên tình cờ
    # không lộ lỗi Decimal+int vẫn cộng được bình thường) — khớp đúng dữ
    # liệu Excel/Bảng kê thật đi qua _to_num() (trả float khi không phải số
    # nguyên tròn, xem server.py:_to_num) trước khi tới đây.
    mk_row("NK-777", "05/01/2026", "500", "0313093362", "CÔNG TY TNHH DOGGYMAN VIỆT NAM",
           "MH216-0", "Que gặm hương bò 120g", "Cái", 45.92, 36750, 1687560.5, "1561", "331",
           0, 0, "1331", None, "KHOCHINH"),
]
ns['_gen_mua_hang_nk'] = lambda cid, header, rows: flat5
exec(extract_fn('_misa_ghi_mua_hang'), ns)
_misa_ghi_mua_hang = ns['_misa_ghi_mua_hang']
r5 = _misa_ghi_mua_hang(1, "TESTDB", "nk", preview=False, ghi_de=False)
print("Result5:", r5["danh_sach"])
assert r5["danh_sach"][0]["trang_thai"] == "đã thêm (đã ghi Sổ Tài chính)", (
    f"Mặt hàng ĐÃ CÓ tồn trước đó (buộc so_du_kho_truoc() chạy SUM SQL thật, trả về decimal.Decimal) "
    f"PHẢI ghi vào MISA THÀNH CÔNG bình thường, KHÔNG được lỗi 'unsupported operand type(s) for +: "
    f"decimal.Decimal and float' (đã hoàn tác, không ghi gì) — đúng lỗi thật đã báo cáo ở bước "
    f"'4a. Nhập kho vào MISA' — got {r5['danh_sach'][0]}")
invl5 = cur5.inserted["InventoryLedger"]
assert len(invl5) == 1
assert invl5[0]["InwardQuantityBalance"] == 10 + 45.92, (
    f"Số dư luỹ kế PHẢI cộng đúng tồn TRƯỚC (10, kiểu Decimal) + SL nhập mới (45.92, kiểu float) = 55.92 — "
    f"got {invl5[0]['InwardQuantityBalance']}")
assert invl5[0]["InwardAmountBalance"] == 367500 + 1687560.5
print("PASS: Test 5 — mặt hàng ĐÃ CÓ tồn trước (SUM SQL trả decimal.Decimal) ghi vào MISA THÀNH CÔNG, "
      "không còn lỗi 'unsupported operand type(s) for +: decimal.Decimal and float', số dư luỹ kế cộng "
      "dồn đúng 10+45.92=55.92.")

print("\nALL DONE (test 5)")

# --- Test 6: đúng lỗi THẬT người dùng báo cáo — bấm "⬆ Nhập kho vào MISA"
# ra "Sẽ thêm: 0 chứng từ ... (hiện có 696 chứng từ Mua hàng trong bảng)"
# khiến người dùng tưởng 696 chứng từ trong Bảng kê Đầu vào của MÌNH mà
# không hiểu sao không thêm được cái nào — "696" thật ra là tong_trong_bang
# = COUNT(*) FROM PUVoucher, tức TOÀN BỘ số chứng từ Mua hàng ĐANG CÓ SẴN
# trong CSDL MISA (kể cả dữ liệu MISA có TỪ TRƯỚC khi dùng phần mềm này,
# không liên quan gì Bảng kê đang xử lý) — hoàn toàn không phải "696 chứng
# từ trong Bảng kê" như tên field/nhãn cũ khiến người ta hiểu lầm. Thêm
# field tong_dang_xu_ly = ĐÚNG số chứng từ (nhóm theo Số chứng từ) có trong
# Bảng kê Đầu vào ĐANG được xử lý ở LƯỢT NÀY — phải KHÁC tong_trong_bang
# khi MISA đã có sẵn dữ liệu lịch sử không liên quan.
#
# ĐỒNG THỜI test luôn tính năng người dùng yêu cầu tiếp theo: "chỉnh lại
# sao cho vừa chỉnh tay vừa import phải xử lý được các vấn đề này... phải
# xử lý được bằng import tự động vào misa để không bị lỗi thiếu nữa" — mã
# hàng CHƯA CÓ trong Danh mục MISA (nguyên nhân hóa đơn bị "THIẾU"/"LỆCH"
# khi đối chiếu Giá trị/VAT) giờ được _misa_ghi_mua_hang TỰ ĐỘNG tạo luôn
# vào Danh mục MISA (dùng lại _misa_ghi_hang_hoa, đúng TK kho suy theo TK
# Nợ của dòng qua _misa_loai_dm_theo_tk) rồi GHI TIẾP chứng từ đó bình
# thường trong CÙNG 1 lượt bấm "⬆ Nhập kho vào MISA" — KHÔNG còn phải tự
# tay chạy riêng "🏷 DM Hàng Hóa" trước rồi mới quay lại ghi Nhập kho.
class FakeCursor6(FakeCursor):
    """FakeCursor cơ bản trả DANH SÁCH InventoryItem CỐ ĐỊNH (bỏ qua
    self.inserted) cho đúng SELECT mà _misa_ghi_mua_hang dùng để nạp 'hang'
    — ĐÚNG cho Test 1-5 (không mã nào được tạo mới giữa chừng) nhưng SAI cho
    Test 6: sau khi _misa_ghi_hang_hoa TỰ TẠO mã mới (INSERT INTO
    InventoryItem, COMMIT qua kết nối riêng), _misa_ghi_mua_hang phải NẠP
    LẠI đúng danh sách MỚI NHẤT (kể cả mã vừa tự tạo) mới dùng được ngay
    trong CÙNG lượt ghi — ghép thêm self.inserted['InventoryItem'] vào danh
    sách cố định để mô phỏng đúng hành vi SQL Server thật (đọc lại thấy
    ngay dữ liệu vừa COMMIT từ kết nối khác)."""
    def fetchall(self):
        sql = self._last_sql
        if sql.startswith("SELECT InventoryItemID, InventoryItemCode, UnitID, InventoryItemName"):
            co_san = [("iid-1", "MH216-0", "uid-cai", "Que gặm hương bò 120g"),
                      ("iid-2", "MH217-0", "uid-cai", "Que gặm hương phô mai 120g"),
                      ("iid-3", "CCDC072", "uid-cai", "Máy lạnh NAGAKAWA NIS-C09R2U51")]
            moi = [(r["InventoryItemID"], r["InventoryItemCode"], r["UnitID"], r["InventoryItemName"])
                   for r in self.inserted.get("InventoryItem", [])]
            return co_san + moi
        return super().fetchall()


cur6 = FakeCursor6()
# Mô phỏng MISA đã có sẵn 5 chứng từ Mua hàng LỊCH SỬ không liên quan gì
# tới Bảng kê đang xử lý (vd nhập tay/hệ thống khác từ TRƯỚC khi dùng phần
# mềm này) -> tong_trong_bang (COUNT(*) FROM PUVoucher) phải tính CẢ 5 dòng
# này, không liên quan gì số chứng từ trong Bảng kê đang xử lý.
cur6.inserted["PUVoucher"] = [{"RefID": f"lich-su-{i}"} for i in range(5)]
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur6)
flat6 = [
    # Chứng từ 1: mã hàng CÓ trong danh mục -> "sẽ thêm" bình thường.
    mk_row("NK-201", "01/02/2026", "600", "0313093362", "CÔNG TY TNHH DOGGYMAN VIỆT NAM",
           "MH216-0", "Que gặm hương bò 120g", "Cái", 5, 36750, 183750, "1561", "331",
           0, 0, "1331", None, "KHOCHINH"),
    # Chứng từ 2: mã hàng KHÔNG có trong Danh mục MISA -> PHẢI được TỰ ĐỘNG
    # tạo vào Danh mục (TK kho 1561, đúng TK Nợ của dòng) rồi ghi TIẾP chứng
    # từ này bình thường trong CÙNG lượt, KHÔNG còn bị "bỏ qua — thiếu mã
    # hàng" như trước.
    mk_row("NK-202", "02/02/2026", "601", "0313093362", "CÔNG TY TNHH DOGGYMAN VIỆT NAM",
           "MAMOI-999", "Sản phẩm mới chưa có mã", "Cái", 3, 10000, 30000, "1561", "331",
           0, 0, "1331", None, "KHOCHINH"),
]
ns['_gen_mua_hang_nk'] = lambda cid, header, rows: flat6
exec(extract_fn('_misa_ghi_mua_hang'), ns)
_misa_ghi_mua_hang = ns['_misa_ghi_mua_hang']
r6 = _misa_ghi_mua_hang(1, "TESTDB", "nk", preview=False, ghi_de=False)
print("Result6:", {k: r6[k] for k in ("so_chungtu", "so_bo_qua_mahang", "so_tu_tao_mahang",
                                       "tong_trong_bang", "tong_dang_xu_ly")})
assert r6["so_chungtu"] == 2, (
    f"Cả 2 chứng từ (kể cả NK-202 với mã hàng lúc đầu chưa có) PHẢI được ghi — mã hàng thiếu phải được TỰ "
    f"ĐỘNG tạo vào Danh mục MISA trước rồi ghi tiếp, KHÔNG được để 'bỏ qua' như trước — got {r6}")
assert r6["so_bo_qua_mahang"] == 0, f"Không còn dòng nào bị bỏ qua vì thiếu mã hàng — got {r6}"
assert r6["so_tu_tao_mahang"] == 1, f"Phải tự tạo đúng 1 mã hàng mới (MAMOI-999) vào Danh mục MISA — got {r6}"
assert r6["tong_dang_xu_ly"] == 2, (
    f"tong_dang_xu_ly PHẢI đúng bằng số chứng từ (2: NK-201 + NK-202) đang có trong Bảng kê Đầu vào ĐANG "
    f"xử lý ở lượt này — got {r6['tong_dang_xu_ly']}")
assert r6["tong_trong_bang"] == 7, (
    f"tong_trong_bang (COUNT(*) FROM PUVoucher) PHẢI đúng bằng TOÀN BỘ chứng từ Mua hàng ĐANG CÓ trong "
    f"MISA (5 chứng từ lịch sử có sẵn + 2 chứng từ vừa ghi mới NK-201/NK-202) — got {r6['tong_trong_bang']}")
assert r6["tong_dang_xu_ly"] != r6["tong_trong_bang"], (
    "2 con số PHẢI khác nhau trong ca này để chứng minh chúng đo 2 thứ HOÀN TOÀN KHÁC NHAU — đúng lỗi thật "
    "đã báo cáo: nhãn cũ '(hiện có N chứng từ Mua hàng trong bảng)' dùng NHẦM tong_trong_bang (696, tổng "
    "toàn bộ lịch sử MISA) khiến người dùng tưởng đó là số chứng từ trong CHÍNH Bảng kê của mình.")
moi_dm = next(r for r in cur6.inserted["InventoryItem"] if r["InventoryItemCode"] == "MAMOI-999")
assert moi_dm["InventoryAccount"] == "1561", (
    f"Mã hàng tự tạo PHẢI đúng TK kho suy theo TK Nợ của dòng (1561 -> Hàng hóa) — got {moi_dm}")
print("PASS: Test 6 — tong_dang_xu_ly/tong_trong_bang tách riêng đúng (2 vs 7, không còn nhầm lẫn); mã hàng "
      "thiếu (MAMOI-999) được TỰ ĐỘNG tạo vào Danh mục MISA đúng TK kho rồi ghi tiếp chứng từ NK-202 bình "
      "thường trong CÙNG 1 lượt bấm 'Nhập kho vào MISA', không cần tự tay chạy riêng DM Hàng Hóa trước.")

print("\nALL DONE (test 6)")

# --- Test 7: đúng ca thật người dùng báo cáo (5/9/2026, công ty TNHH THƯƠNG
# MẠI PHẨM LỢI) — "phần mềm phải lấy đúng mã đã có từ trước nếu tên hàng
# giống chứ không cần tạo thêm mã". Dòng Bảng kê ghi mã 'MH1084' (đã bị xóa
# khỏi MISA, không còn trong Danh mục) cho hàng "Nekko cá ngừ thanh cua kèm
# nước sốt 70g (gói)" — nhưng MISA VẪN CÒN mã KHÁC 'MH1084-0' (Vật tư hàng
# hóa) cho CHÍNH XÁC cùng tên đó. Trước fix, _misa_ghi_mua_hang tự tạo THÊM
# mã 'MH1084' mới (trùng lặp, dù tính chất đúng Vật tư hàng hóa) — SAI, phải
# DÙNG LẠI 'MH1084-0' có sẵn, không tạo gì cả.
class FakeCursor7(FakeCursor):
    def fetchall(self):
        sql = self._last_sql
        if sql.startswith("SELECT InventoryItemID, InventoryItemCode, UnitID, InventoryItemName"):
            return [("iid-1", "MH216-0", "uid-cai", "Que gặm hương bò 120g"),
                    ("iid-2", "MH217-0", "uid-cai", "Que gặm hương phô mai 120g"),
                    ("iid-3", "CCDC072", "uid-cai", "Máy lạnh NAGAKAWA NIS-C09R2U51"),
                    ("iid-1084-0", "MH1084-0", "uid-cai",
                     "Nekko cá ngừ  thanh cua kèm nước sốt 70g (gói)")]
        if sql.startswith("SELECT InventoryItemCode, InventoryItemName, InventoryItemType, UnitID"):
            return [("MH216-0", "Que gặm hương bò 120g", 1, "uid-cai"),
                    ("MH217-0", "Que gặm hương phô mai 120g", 1, "uid-cai"),
                    ("CCDC072", "Máy lạnh NAGAKAWA NIS-C09R2U51", 1, "uid-cai"),
                    ("MH1084-0", "Nekko cá ngừ  thanh cua kèm nước sốt 70g (gói)", 1, "uid-cai")]
        return super().fetchall()


cur7 = FakeCursor7()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur7)
flat7 = [
    mk_row("NK-301", "03/02/2026", "700", "0313093362", "CÔNG TY TNHH DOGGYMAN VIỆT NAM",
           "MH1084", "Nekko cá ngừ  thanh cua kèm nước sốt 70g (gói)", "Cái", 9, 639360, 5754240,
           "1561", "331", 0, 0, "1331", None, "KHOCHINH"),
]
ns['_gen_mua_hang_nk'] = lambda cid, header, rows: flat7
exec(extract_fn('_misa_ghi_mua_hang'), ns)
_misa_ghi_mua_hang = ns['_misa_ghi_mua_hang']
r7 = _misa_ghi_mua_hang(1, "TESTDB", "nk", preview=False, ghi_de=False)
print("Result7:", {k: r7[k] for k in ("so_chungtu", "so_bo_qua_mahang", "so_tu_tao_mahang",
                                       "so_dung_ma_trung_ten")})
assert r7["so_chungtu"] == 1, f"Chứng từ NK-301 phải được ghi bình thường — got {r7}"
assert r7["so_tu_tao_mahang"] == 0, (
    f"KHÔNG được tự tạo mã mới nào — 'MH1084-0' đã có sẵn CÙNG tên, phải dùng lại, không tạo 'MH1084' "
    f"trùng lặp — got {r7}")
assert r7["so_dung_ma_trung_ten"] == 1, (
    f"Phải báo đúng 1 lần dùng lại mã có sẵn (trùng tên) thay vì tạo mới — got {r7}")
assert cur7.inserted["InventoryItem"] == [], (
    f"KHÔNG được tạo InventoryItem mới nào (mã 'MH1084' phải được coi là trùng tên với 'MH1084-0' đã có "
    f"sẵn, không tạo thêm) — got {cur7.inserted['InventoryItem']}")
pvd7 = cur7.inserted["PUVoucherDetail"]
assert len(pvd7) == 1 and pvd7[0]["InventoryItemID"] == "iid-1084-0", (
    f"Dòng chứng từ phải ghi ĐÚNG InventoryItemID của mã có sẵn 'MH1084-0' (iid-1084-0), KHÔNG được tạo/"
    f"dùng 1 InventoryItemID khác cho 'MH1084' — got {pvd7}")
print("PASS: Test 7 — mã hàng thiếu ('MH1084') nhưng TÊN đã trùng với mã KHÁC có sẵn ('MH1084-0') -> dùng "
      "lại đúng mã có sẵn đó, KHÔNG tạo mã mới trùng lặp; dòng chứng từ ghi đúng InventoryItemID của mã có "
      "sẵn.")

print("\nALL DONE (test 7)")

# --- Test 8: đúng yêu cầu người dùng SAU khi phát hiện mã 'HH4610-0' bị tồn
# ở CẢ 2 kho khác nhau trong MISA ("Kho HH" + "Kho Chó Mèo KO VAT") khiến
# Xuất Kho không xác định được kho đúng — "nếu mã hàng này đã có từ trước
# thì xem mã hàng này được gắn vào kho nào thì lấy đúng mã kho đó. còn mã
# nào chưa có thì cứ gắn mã kho là HH". Mã 'MH216-0' (iid-1) ĐÃ CÓ lịch sử
# Nhập kho TRƯỚC ĐÓ vào kho 'KHOCHINH' (sid-1) — dòng Bảng kê Đầu vào MỚI
# ghi cột "Kho" = "KHOKHAC" (kho KHÁC) -> PHẢI vẫn ghi vào ĐÚNG kho cũ
# 'KHOCHINH' (sid-1), KHÔNG được tạo/dùng kho 'KHOKHAC' mới, để 1 mã hàng
# không bị tách tồn ra nhiều kho qua các lần nhập khác nhau.
class FakeCursor8(FakeCursor):
    def fetchall(self):
        sql = self._last_sql
        if sql.startswith("SELECT il.InventoryItemID, il.StockID FROM InventoryLedger il"):
            # mã 'MH216-0' (iid-1) đã từng Nhập kho vào 'KHOCHINH' (sid-1) trước đó.
            return [("iid-1", "sid-1")]
        return super().fetchall()


cur8 = FakeCursor8()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur8)
flat8 = [
    mk_row("NK-401", "04/02/2026", "800", "0313093362", "CÔNG TY TNHH DOGGYMAN VIỆT NAM",
           "MH216-0", "Que gặm hương bò 120g", "Cái", 10, 36750, 367500, "1561", "331",
           0, 0, "1331", None, "KHOKHAC"),
]
ns['_gen_mua_hang_nk'] = lambda cid, header, rows: flat8
exec(extract_fn('_misa_ghi_mua_hang'), ns)
_misa_ghi_mua_hang = ns['_misa_ghi_mua_hang']
r8 = _misa_ghi_mua_hang(1, "TESTDB", "nk", preview=False, ghi_de=False)
print("Result8:", {k: r8[k] for k in ("so_chungtu",)})
assert r8["so_chungtu"] == 1, f"Chứng từ NK-401 phải được ghi bình thường — got {r8}"
pvd8 = cur8.inserted["PUVoucherDetail"]
assert len(pvd8) == 1 and pvd8[0]["StockID"] == "sid-1", (
    f"Mã 'MH216-0' ĐÃ CÓ lịch sử Nhập kho vào 'KHOCHINH' (sid-1) TRƯỚC ĐÓ -> dòng MỚI PHẢI vẫn ghi vào "
    f"ĐÚNG kho cũ đó, KHÔNG được đổi sang kho 'KHOKHAC' dù cột Kho của Bảng kê Đầu vào ghi khác — được "
    f"{pvd8}")
print("PASS: Test 8 — mã hàng ĐÃ CÓ lịch sử Nhập kho trước đó luôn dùng lại ĐÚNG kho gần nhất, không bị "
      "tách tồn ra kho khác dù dòng Bảng kê Đầu vào mới ghi cột Kho khác đi — đúng yêu cầu người dùng, "
      "tránh lặp lại ca thật 'HH4610-0' tồn ở 2 kho khác nhau.")

print("\nALL DONE (test 8)")

# --- Test 9: đúng lỗi THẬT người dùng vừa báo lại (build .181 đã lên nhưng
# mã 'HH4610-0' VẪN nhập nhầm vào kho 'HH' dù đã có kho 'Kho Chó Mèo KO VAT'
# từ trước) — nguyên nhân round 1 của fix (Test 8) không lộ ra: câu truy
# vấn "kho gần nhất" TRƯỚC ĐÂY dùng TOÀN BỘ "hang" (cả Danh mục MISA, công
# ty thật có 1468+ mã) làm danh sách IN (...) — SQL Server giới hạn CỨNG
# 2100 tham số/câu lệnh, danh mục lớn thừa sức vượt ngưỡng này khiến CẢ CÂU
# LỆNH LỖI (bị except nuốt mất), hoc_kho_gan_nhat rỗng cho MỌI mã — fix coi
# như vô tác dụng với bất kỳ công ty nào có Danh mục đủ lớn (đúng thực tế
# hầu hết công ty dùng phần mềm này). Test 8 (chỉ 3 mã trong "hang") không
# đủ lớn để lộ ra bug này.
class FakeCursor9(FakeCursor):
    def fetchall(self):
        sql = self._last_sql
        if sql.startswith("SELECT InventoryItemID, InventoryItemCode, UnitID, InventoryItemName"):
            # Danh mục LỚN — mô phỏng đúng quy mô công ty thật (1468+ mã hàng),
            # MH216-0 nằm lẫn trong đó.
            extra = [(f"iid-extra-{i}", f"EXTRA{i}", "uid-cai", f"Hàng thêm {i}") for i in range(1500)]
            return [("iid-1", "MH216-0", "uid-cai", "Que gặm hương bò 120g"),
                    ("iid-2", "MH217-0", "uid-cai", "Que gặm hương phô mai 120g"),
                    ("iid-3", "CCDC072", "uid-cai", "Máy lạnh NAGAKAWA NIS-C09R2U51")] + extra
        if sql.startswith("SELECT il.InventoryItemID, il.StockID FROM InventoryLedger il"):
            # Mô phỏng ĐÚNG giới hạn thật của SQL Server (2100 tham số/lệnh) —
            # nếu câu truy vấn lỡ nhét CẢ Danh mục (1503 mã, x2 nếu còn IN
            # trùng lặp = 3006 tham số) sẽ VỠ ở đây, đúng lỗi thật đã gặp.
            if len(self._last_params) > 2100:
                raise Exception("Đã tạo quá nhiều tham số, tối đa cho phép là 2100.")
            return [("iid-1", "sid-1")]
        return super().fetchall()


cur9 = FakeCursor9()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur9)
flat9 = [
    mk_row("NK-501", "05/02/2026", "900", "0313093362", "CÔNG TY TNHH DOGGYMAN VIỆT NAM",
           "MH216-0", "Que gặm hương bò 120g", "Cái", 5, 36750, 183750, "1561", "331",
           0, 0, "1331", None, "KHOKHAC"),
]
ns['_gen_mua_hang_nk'] = lambda cid, header, rows: flat9
exec(extract_fn('_misa_ghi_mua_hang'), ns)
_misa_ghi_mua_hang = ns['_misa_ghi_mua_hang']
r9 = _misa_ghi_mua_hang(1, "TESTDB", "nk", preview=False, ghi_de=False)
print("Result9:", {k: r9[k] for k in ("so_chungtu",)})
assert r9["so_chungtu"] == 1, f"Chứng từ NK-501 phải được ghi bình thường — got {r9}"
pvd9 = cur9.inserted["PUVoucherDetail"]
assert len(pvd9) == 1 and pvd9[0]["StockID"] == "sid-1", (
    f"Câu truy vấn 'kho gần nhất' PHẢI chỉ tra đúng mã hàng có trong Bảng kê đang xử lý (1 mã), KHÔNG "
    f"được nhét CẢ Danh mục MISA (1503 mã) vào IN (...) — nếu không sẽ VỠ giới hạn tham số SQL Server, "
    f"khiến toàn bộ tính năng vô tác dụng dù Danh mục công ty đủ lớn (đúng ca thật đã báo lại sau round 1 "
    f"của fix) — được {pvd9}")
print("PASS: Test 9 — câu truy vấn 'kho gần nhất' chỉ tra đúng mã hàng trong Bảng kê đang xử lý (không "
      "nhét cả Danh mục MISA lớn vào IN), không còn vỡ giới hạn tham số SQL Server với công ty có Danh "
      "mục lớn (1468+ mã) như ca thật vừa báo lại.")

print("\nALL DONE (test 9)")
