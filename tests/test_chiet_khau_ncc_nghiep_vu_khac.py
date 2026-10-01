import os, sys, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Người dùng chọn hạch toán chiết khấu NCC đúng như đã gõ: Nợ 331 / Có 6427 / Có 1331, SỐ DƯƠNG (Chứng từ nghiệp vụ khác), không ghi âm.
# Cấu trúc bảng sổ MISA khác nhau -> CLONE chứng từ mẫu thật (Nợ 331/Có 6427 123.457 + Nợ 331/Có 1331 9.877), thay id/số CT/ngày/HĐ/NCC/số tiền.
T = {  # tên bảng -> ([(cột, kiểu)], pk)
    "GLVoucher": ([("RefID", "uniqueidentifier"), ("RefType", "int"), ("RefDate", "datetime"), ("PostedDate", "datetime"), ("RefNoFinance", "nvarchar"),
                   ("JournalMemo", "nvarchar"), ("TotalAmount", "decimal"), ("TotalAmountOC", "decimal"), ("IsPostedFinance", "bit"),
                   ("RefOrder", "int"), ("CreatedDate", "datetime"), ("CustomField10", "nvarchar")], ["RefID"]),
    "GLVoucherDetail": ([("RefDetailID", "uniqueidentifier"), ("RefID", "uniqueidentifier"), ("Description", "nvarchar"), ("DebitAccount", "nvarchar"),
                         ("CreditAccount", "nvarchar"), ("Amount", "decimal"), ("AmountOC", "decimal"), ("DebitAccountObjectID", "uniqueidentifier"),
                         ("SortOrder", "int")], ["RefDetailID"]),
    "GeneralLedger": ([("GeneralLedgerID", "uniqueidentifier"), ("RefID", "uniqueidentifier"), ("RefDetailID", "uniqueidentifier"), ("AccountNumber", "nvarchar"),
                       ("CorrespondingAccountNumber", "nvarchar"), ("DebitAmount", "decimal"), ("CreditAmount", "decimal"), ("Description", "nvarchar"),
                       ("AccountObjectID", "uniqueidentifier"), ("RefNo", "nvarchar"), ("RefDate", "datetime"), ("InvNo", "nvarchar"), ("InvDate", "datetime"),
                       ("RefOrder", "int")], ["GeneralLedgerID"]),
    "AccountObjectLedger": ([("AccountObjectLedgerID", "uniqueidentifier"), ("RefID", "uniqueidentifier"), ("RefDetailID", "uniqueidentifier"),
                             ("AccountNumber", "nvarchar"), ("DebitAmount", "decimal"), ("AccountObjectID", "uniqueidentifier"), ("RefNo", "nvarchar")],
                            ["AccountObjectLedgerID"]),
    "PUService": ([("RefID", "uniqueidentifier"), ("CustomField10", "nvarchar")], ["RefID"]),
    "PUServiceDetail": ([("RefDetailID", "uniqueidentifier"), ("RefID", "uniqueidentifier"), ("InvNo", "nvarchar"), ("Amount", "decimal")], ["RefDetailID"]),
    "PurchaseLedger": ([("PurchaseLedgerID", "uniqueidentifier"), ("RefID", "uniqueidentifier")], ["PurchaseLedgerID"]),
}
MAU = "REF-MAU"
D1, D2, AO_MAU = "DET-1", "DET-2", "AO-MAU"
NGAY_M = datetime.datetime(2026, 1, 5)
SAMPLE = {
    "GLVoucher": [{"RefID": MAU, "RefType": 4000, "RefDate": NGAY_M, "PostedDate": NGAY_M, "RefNoFinance": "NVK00012", "JournalMemo": "Mẫu CK",
                   "TotalAmount": 133334, "TotalAmountOC": 133334, "IsPostedFinance": True, "RefOrder": 7, "CreatedDate": NGAY_M, "CustomField10": None}],
    "GLVoucherDetail": [{"RefDetailID": D1, "RefID": MAU, "Description": "Mẫu net", "DebitAccount": "331", "CreditAccount": "6427", "Amount": 123457,
                         "AmountOC": 123457, "DebitAccountObjectID": AO_MAU, "SortOrder": 0},
                        {"RefDetailID": D2, "RefID": MAU, "Description": "Mẫu vat", "DebitAccount": "331", "CreditAccount": "1331", "Amount": 9877,
                         "AmountOC": 9877, "DebitAccountObjectID": AO_MAU, "SortOrder": 1}],
    "GeneralLedger": [
        {"GeneralLedgerID": "GL-1", "RefID": MAU, "RefDetailID": D1, "AccountNumber": "331", "CorrespondingAccountNumber": "6427", "DebitAmount": 123457,
         "CreditAmount": 0, "Description": "Mẫu net", "AccountObjectID": AO_MAU, "RefNo": "NVK00012", "RefDate": NGAY_M, "InvNo": "MAU1", "InvDate": NGAY_M, "RefOrder": 8},
        {"GeneralLedgerID": "GL-2", "RefID": MAU, "RefDetailID": D1, "AccountNumber": "6427", "CorrespondingAccountNumber": "331", "DebitAmount": 0,
         "CreditAmount": 123457, "Description": "Mẫu net", "AccountObjectID": None, "RefNo": "NVK00012", "RefDate": NGAY_M, "InvNo": "MAU1", "InvDate": NGAY_M, "RefOrder": 9},
        {"GeneralLedgerID": "GL-3", "RefID": MAU, "RefDetailID": D2, "AccountNumber": "331", "CorrespondingAccountNumber": "1331", "DebitAmount": 9877,
         "CreditAmount": 0, "Description": "Mẫu vat", "AccountObjectID": AO_MAU, "RefNo": "NVK00012", "RefDate": NGAY_M, "InvNo": "MAU1", "InvDate": NGAY_M, "RefOrder": 10},
        {"GeneralLedgerID": "GL-4", "RefID": MAU, "RefDetailID": D2, "AccountNumber": "1331", "CorrespondingAccountNumber": "331", "DebitAmount": 0,
         "CreditAmount": 9877, "Description": "Mẫu vat", "AccountObjectID": None, "RefNo": "NVK00012", "RefDate": NGAY_M, "InvNo": "MAU1", "InvDate": NGAY_M, "RefOrder": 11}],
    "AccountObjectLedger": [{"AccountObjectLedgerID": "AOL-1", "RefID": MAU, "RefDetailID": D1, "AccountNumber": "331", "DebitAmount": 133334,
                             "AccountObjectID": AO_MAU, "RefNo": "NVK00012"}],
}

class Cur:
    def __init__(self, existing=None, legacy=None, docs=("NVK00012",), co_mau=True):
        self.ins, self.dele = [], []
        self.existing, self.legacy, self.docs, self.co_mau = existing or [], legacy or [], docs, co_mau
        self._r = []
    def execute(self, sql, *p):
        p = p[0] if len(p) == 1 and isinstance(p[0], (tuple, list)) else p
        self.sql, self.p = sql, p
        if sql.startswith("INSERT INTO"):
            t = sql.split("[")[1].split("]")[0]
            cols = [c.strip("[]") for c in sql[sql.index("(") + 1:sql.index(")")].split(",")]
            self.ins.append((t, dict(zip(cols, p))))
        elif sql.startswith("DELETE FROM"):
            self.dele.append((sql.split("[")[1].split("]")[0], p[0]))
        return self
    def fetchall(self):
        s, p = self.sql, self.p
        if "FROM sys.columns c JOIN sys.tables" in s:
            return [(t,) for t in T]
        if "sys.columns c" in s and "sys.types" in s:
            return [(c, ty) for c, ty in T.get(p[0], ([], []))[0]]
        if "sys.index_columns" in s:
            return [(c,) for c in T[p[0]][1]]
        if s.startswith("SELECT [") and "WHERE RefID=?" in s:
            t = s.split(" FROM [")[1].split("]")[0]
            return [tuple(r.get(c) for c in [x[0] for x in T[t][0]]) for r in SAMPLE.get(t, [])] if p[0] == MAU else []
        if s.startswith("SELECT RefNoFinance FROM GLVoucher"):
            return [(d,) for d in self.docs]
        if s.startswith("SELECT AccountObjectID, CompanyTaxCode"):
            return [("AO-SATORI", "0319340593", "NCC-SATORI", "CÔNG TY TNHH DỊCH VỤ THƯƠNG MẠI SATORI")]
        if s.startswith("SELECT RefID, ISNULL(TotalAmount"):
            return self.existing
        if s.startswith("SELECT DISTINCT ps.RefID"):
            return self.legacy
        return []
    def fetchone(self):
        s = self.sql
        if "SELECT TOP 1 gv.RefID" in s:
            return (MAU,) if self.co_mau else None
        if s.startswith("SELECT ISNULL(MAX(RefOrder)"):
            return (11,)
        if s.startswith("SELECT AccountObjectCode, AccountObjectName"):
            return ("NCC-MAU", "NCC MẪU", "0300000000")
        return None

class Conn:
    def __init__(self, c): self.c = c; self.autocommit = True; self.rb = self.cm = False
    def cursor(self): return self.c
    def commit(self): self.cm = True
    def rollback(self): self.rb = True
    def close(self): pass

hd = ["Ký hiệu", "Số HĐ", "Ngày", "Người bán", "MST bán", "STT", "Mã vt", "Tên hàng hóa/dịch vụ", "ĐVT", "Số lượng", "Đơn giá", "Thành tiền",
      "Thuế suất", "Tiền thuế GTGT", "Trị giá tính thuế NK", "Thuế suất NK", "Tiền thuế NK", "Nợ", "Có"]
rows = [["C26TSA", "5451", "17/09/2026", "SATORI", "0319340593", "1", "MHDV", "Hỗ trợ thị trường", None, 0, 0, 10980720, "8%", 878458, None, None, None, 331, 6427],
        ["C26TSA", "6036", "23/09/2026", "SATORI", "0319340593", "1", "MHDV", "Hỗ trợ phát triển", None, 0, 0, -13340460, "8%", -1067237, None, None, None, "331", ""]]
server.nhap_lieu_get = lambda cid, loai="in": {"header": hd, "rows": rows}

def chay(c, preview=False):
    cn = Conn(c)
    server._misa_sql_connect = lambda cid, database=None: cn
    return cn, server._misa_ghi_chiet_khau_ncc(1, "DB", preview=preview)

# 1) ghi mới 2 hóa đơn (5451 có thuế dương; 6036 số âm -> lấy trị tuyệt đối)
c = Cur(legacy=[("OLD-PU",)])
cn, r = chay(c)
assert r["so_chungtu"] == 2 and cn.cm, r
glv = [d for t, d in c.ins if t == "GLVoucher"]
assert [g["RefNoFinance"] for g in glv] == ["NVK00013", "NVK00014"], glv
assert glv[0]["TotalAmount"] == 11859178 and glv[0]["CustomField10"] == server._PM_MARK and glv[0]["RefDate"] == datetime.datetime(2026, 9, 17)
assert glv[1]["TotalAmount"] == 14407697, glv[1]
det = [d for t, d in c.ins if t == "GLVoucherDetail" and d["RefID"] == glv[0]["RefID"]]
assert sorted((d["DebitAccount"], d["CreditAccount"], d["Amount"]) for d in det) == [("331", "1331", 878458), ("331", "6427", 10980720)], det
assert all(d["DebitAccountObjectID"] == "AO-SATORI" for d in det), det
assert det[0]["Description"].startswith("Chiết khấu mua hàng HĐ 5451 (MST 0319340593)") and det[1]["Description"].startswith("Thuế GTGT - Chiết khấu mua hàng HĐ 5451")
gl = [d for t, d in c.ins if t == "GeneralLedger" and d["RefID"] == glv[0]["RefID"]]
assert len(gl) == 4 and {x["GeneralLedgerID"] for x in gl}.isdisjoint({"GL-1", "GL-2", "GL-3", "GL-4"}) and len({x["GeneralLedgerID"] for x in gl}) == 4
assert sorted((x["AccountNumber"], x["DebitAmount"], x["CreditAmount"]) for x in gl) == sorted([("331", 10980720, 0), ("6427", 0, 10980720), ("331", 878458, 0), ("1331", 0, 878458)])
assert all(x["InvNo"] == "5451" and x["RefNo"] == "NVK00013" and x["RefDetailID"] in {d["RefDetailID"] for d in det} for x in gl)
assert {x["AccountObjectID"] for x in gl} == {"AO-SATORI", None}
aol = [d for t, d in c.ins if t == "AccountObjectLedger" and d["RefID"] == glv[0]["RefID"]][0]
assert aol["DebitAmount"] == 11859178 and aol["AccountObjectID"] == "AO-SATORI"
assert ("PUServiceDetail", "OLD-PU") in c.dele and ("PUService", "OLD-PU") in c.dele, c.dele
assert [x[0] for x in c.ins][:3] == ["GLVoucher", "GLVoucherDetail", "GLVoucherDetail"], "header trước chi tiết trước sổ cái"
print("PASS 1: ghi mới Nợ 331/Có 6427 + Nợ 331/Có 1331 SỐ DƯƠNG (clone mẫu: id mới, số NVK nối tiếp, ngày/HĐ/NCC/số tiền đúng, sổ cái 4 dòng), gỡ chứng từ ghi âm cũ.")

# 2) chạy lại: đã đúng số -> bỏ qua; số khác -> gỡ + ghi lại GIỮ SỐ CHỨNG TỪ
c2 = Cur(existing=[("EX-1", 11859178, "NVK00013")])
cn2, r2 = chay(c2)
assert r2["so_trung"] == 1 and r2["so_chungtu"] == 1 and [d["RefNoFinance"] for t, d in c2.ins if t == "GLVoucher"] == ["NVK00013"], (r2, c2.ins[:1])
c3 = Cur(existing=[("EX-1", 999, "NVK00020")])
cn3, r3 = chay(c3)
assert ("GLVoucher", "EX-1") in c3.dele and ("GeneralLedger", "EX-1") in c3.dele and r3["so_ghi_de"] >= 1
assert "NVK00020" in [d["RefNoFinance"] for t, d in c3.ins if t == "GLVoucher"]
print("PASS 2: chạy lại — đúng số thì bỏ qua; đổi số thì gỡ cũ (cả sổ cái) và ghi lại giữ số chứng từ.")

# 3) xem trước không ghi; thiếu mẫu báo hướng dẫn; mẫu số tiền không đủ khác biệt báo lỗi
c4 = Cur(); cn4, r4 = chay(c4, preview=True)
assert not c4.ins and not c4.dele and cn4.rb and r4["so_chungtu"] == 2 and r4["danh_sach"][0]["trang_thai"].startswith("sẽ ghi")
try:
    chay(Cur(co_mau=False)); assert False
except server.HTTPException as ex:
    assert "chứng từ MẪU" in str(ex.detail)
print("PASS 3: xem trước không ghi gì (rollback); thiếu chứng từ mẫu thì hướng dẫn tạo mẫu.")

# 4) không còn đi qua chứng từ mua dịch vụ ghi âm; đối chiếu nhận diện nhóm
assert server._gen_mua_hang_dv(1, hd, rows) == []
dd = server._dong_chiet_khau_ncc(hd, rows)
assert [(x["so_hd"], x["net"], x["vat"]) for x in dd] == [("5451", 10980720, 878458), ("6036", 13340460, 1067237)] and dd[1]["tk_cp"] == "6427"
print("PASS 4: Nợ 331 không còn vào mua dịch vụ ghi âm; gom đúng theo hóa đơn (trị tuyệt đối).")
import re
mm = re.match(r"^%s (\S+) \(MST ([^)]*)\)" % re.escape(server._CK_NCC_MEMO), det[0]["Description"])
assert mm and mm.groups() == ("5451", "0319340593"), "memo ghi ra phải khớp mẫu mà Đối chiếu dùng để trừ vào đúng hóa đơn"
assert "_re_dc.match(r\"^%s (\\S+) \\(MST ([^)]*)\\)\"" in open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py"), encoding="utf-8").read()
print("PASS 5: memo chứng từ khớp biểu thức Đối chiếu dùng để trừ doanh số/thuế đúng hóa đơn.")
print("\nALL DONE")
