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
        self.code = code; self.detail = msg
        super().__init__(f"{code}: {msg}")


# Cột thật (rút gọn nhưng đủ mọi cột _misa_gan cần) cho từng bảng liên quan —
# SONG SONG với COLUMNS của test_phan_bo_ccdc_ngay_gt.py, chỉ đổi tiền tố SU->FA.
COLUMNS = {
    "FixedAsset": [("FixedAssetID", "uniqueidentifier"), ("FixedAssetCode", "nvarchar"),
                   ("FixedAssetName", "nvarchar"), ("OrgPrice", "money"),
                   ("LifeTimeInMonth", "int"), ("MonthlyDepreciationAmount", "money"),
                   ("StartDepreciationDate", "datetime"), ("LifeTimeRemainingInMonth", "int"),
                   ("AccumDepreciationAmount", "money"), ("RemainingAmount", "money")],
    "FADepreciation": [("RefID", "uniqueidentifier"), ("RefType", "int"), ("RefDate", "datetime"),
                        ("PostedDate", "datetime"), ("RefNo", "nvarchar"), ("JournalMemo", "nvarchar"),
                        ("Month", "int"), ("Year", "int"), ("TotalAmount", "money"),
                        ("BranchID", "uniqueidentifier"), ("IsPostedManagement", "bit"),
                        ("DisplayOnBook", "bit"), ("RefOrder", "int"), ("CreatedDate", "datetime"),
                        ("CreatedBy", "nvarchar"), ("ModifiedDate", "datetime"), ("ModifiedBy", "nvarchar"),
                        ("IsPostedFinance", "bit")],
    "FADepreciationDetail": [("RefDetailID", "uniqueidentifier"), ("RefID", "uniqueidentifier"),
                              ("FixedAssetID", "uniqueidentifier"), ("OrganizationUnitID", "uniqueidentifier"),
                              ("MonthlyDepreciationAmount", "money"), ("AmountResonableCost", "money"),
                              ("AmountUnResonableCost", "money"), ("SortOrder", "int")],
    "FADepreciationDetailAllocation": [("RefDetailID", "uniqueidentifier"), ("RefID", "uniqueidentifier"),
                                        ("FixedAssetID", "uniqueidentifier"), ("OrganizationUnitID", "uniqueidentifier"),
                                        ("MonthlyDepreciationAmount", "money"), ("AllocationObjectID", "uniqueidentifier"),
                                        ("CostAccount", "nvarchar"), ("AllocationRate", "float"),
                                        ("AllocationAmount", "money"), ("SortOrder", "int")],
    "FADepreciationDetailPost": [("RefDetailID", "uniqueidentifier"), ("RefID", "uniqueidentifier"),
                                  ("Description", "nvarchar"), ("DebitAccount", "nvarchar"),
                                  ("CreditAccount", "nvarchar"), ("Amount", "money"),
                                  ("OrganizationUnitID", "uniqueidentifier"), ("UnResonableCost", "bit"),
                                  ("SortOrder", "int")],
    "FixedAssetLedger": [("RefID", "uniqueidentifier"), ("RefDetailID", "uniqueidentifier"),
                          ("FixedAssetID", "uniqueidentifier"), ("RefType", "int"), ("RefNo", "nvarchar"),
                          ("RefDate", "datetime"), ("PostedDate", "datetime"), ("OrganizationUnitID", "uniqueidentifier"),
                          ("LifeTimeInMonth", "int"), ("LifeTimeRemainingInMonth", "int"),
                          ("MonthlyDepreciationAmount", "money"), ("OriginDepreciationAmount", "money"),
                          ("AccumDepreciationAmount", "money"), ("TotalDepreciationAmount", "money"),
                          ("RemainingAmount", "money"), ("DepreciationAccount", "nvarchar"),
                          ("JournalMemo", "nvarchar"), ("BranchID", "uniqueidentifier"), ("RefOrder", "int"),
                          ("RefOrderInSubSystem", "int"), ("FixedAssetCode", "nvarchar"), ("FixedAssetName", "nvarchar")],
}


class FakeCursor:
    """Mô phỏng công ty ĐÃ ghi tăng 2 TSCĐ (qua _misa_ghi_tang_tscd, nên
    FixedAssetLedger đã có sẵn 2 dòng RefType=250 'Ghi tăng') nhưng CHƯA từng
    bấm 'Tính khấu hao' tay lần nào — đúng kịch bản thực tế: RefType=250 sẽ
    là ĐA SỐ (và DUY NHẤT) trong FixedAssetLedger, nên nếu dùng
    _misa_hoc_reftype kiểu 'đa số' thẳng trên FixedAssetLedger sẽ NHẦM trả về
    250 cho cả dòng khấu hao — bài test này xác nhận hàm phải tự tránh được
    bẫy đó và dò đúng qua SYSRefType (master_table='FixedAssetLedger')."""
    def __init__(self):
        self.updates = []       # (sql, params) - UPDATE FixedAsset thật đã chạy
        self.led_inserts = []   # params của các câu INSERT INTO FixedAssetLedger thật đã chạy

    def execute(self, sql, params=()):
        p = params if isinstance(params, (tuple, list)) else (params,) if params != () else ()
        if sql.startswith("UPDATE FixedAsset SET"):
            self.updates.append((sql, p))
            self._result = []
            return self
        if sql.startswith("INSERT INTO FixedAssetLedger"):
            cols_order = sql.split("([")[1].split("]) VALUES")[0].split("],[")
            self.led_inserts.append(dict(zip(cols_order, p)))
            self._result = []
            return self
        if "DISTINCT RefType FROM FixedAssetLedger WHERE RefType<>0 AND RefType<>?" in sql:
            self._result = []   # chưa từng có dòng khấu hao THẬT nào khác 250 (Ghi tăng)
            return self
        if "SELECT RefType FROM FixedAssetLedger WHERE RefType<>0" in sql:
            # Công ty ĐÃ ghi tăng 2 TSCĐ -> FixedAssetLedger có sẵn 2 dòng RefType=250.
            self._result = [(250,), (250,)]
            return self
        if "MAX(RefOrderInSubSystem) FROM FixedAssetLedger" in sql:
            self._result = [(2,)]   # đã có 2 dòng Ghi tăng chiếm slot 1,2
            return self
        if "sys.columns c" in sql and "sys.types ty" in sql:
            table = p[0]
            self._result = COLUMNS.get(table, [])
        elif "SELECT name FROM sys.columns WHERE object_id" in sql:
            table = p[0]
            self._result = [(n,) for n, _t in COLUMNS.get(table, [])]
        elif sql.startswith("SELECT TOP 5 ["):
            self._result = []   # công ty CHƯA có chứng từ KH thật nào để học mẫu
        elif "SYSRefType WHERE MasterTableName" in sql:
            master_table = p[0]
            if master_table == "FADepreciation":
                self._result = [(9101, "Khấu hao tài sản cố định")]
            elif master_table == "FixedAssetLedger":
                self._result = [(253, "Khấu hao tài sản cố định")]
            else:
                self._result = []
        elif "FROM FADepreciation WHERE RefType<>0" in sql:
            self._result = []   # chưa có dòng FADepreciation thật nào (RefType<>0)
        elif "SELECT RefNo FROM FADepreciation WHERE RefNo LIKE" in sql:
            self._result = []
        elif "FROM FixedAsset WHERE ISNULL" in sql:
            self._result = [
                ("fa-001", "TSCD00001", "May tinh 1", 100000, 4, 25000,
                 datetime.datetime(2026, 5, 26)),
                ("fa-002", "TSCD00002", "May tinh 2", 150000, 3, 50000,
                 datetime.datetime(2026, 6, 30)),
            ]
        elif "FADepreciationDetail WHERE FixedAssetID" in sql:
            self._result = [(0, 0)]   # chưa khấu hao kỳ nào
        elif "FixedAssetDetailAllocation WHERE FixedAssetID" in sql:
            self._result = []
        elif "FADepreciationDetailAllocation WHERE FixedAssetID" in sql:
            self._result = []
        elif "OrganizationUnit" in sql:
            self._result = [("branch-1",)]
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
        self.autocommit = True
    def cursor(self):
        return self._cur
    def commit(self):
        pass
    def rollback(self):
        pass
    def close(self):
        pass


ns = {'datetime': datetime, 'HTTPException': FakeHTTPException, 'calendar': __import__('calendar')}
def snum(v):
    try:
        return float(v)
    except Exception:
        return 0
ns['_snum'] = snum
ns['_CCDC_CO_MAC_DINH'] = "242"
ns['_TSCD_CO_MAC_DINH'] = "214"
ns['_PHAN_BO_NO_MAC_DINH'] = "642"
ns['_FA_LEDGER_REFTYPE'] = 250

for fn in ("_misa_pu_reftype", "_misa_hoc_reftype", "_misa_cot_bang_that",
           "_misa_gia_tri_mac_dinh", "_misa_chon_cot", "_misa_gan",
           "_misa_mau_dong_that", "_misa_branch_id", "_misa_khau_hao_tscd"):
    exec(extract_fn(fn), ns)

_misa_khau_hao_tscd = ns['_misa_khau_hao_tscd']

cur = FakeCursor()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur)

r = _misa_khau_hao_tscd(1, "TESTDB", preview=True, tu_thang="2026-01", so_thang=12)
assert r["danh_sach"], "Vẫn phải tính được dù công ty CHƯA có chứng từ KH mẫu nào (build .044)."
print("PASS: vẫn chạy được dù công ty MỚI chưa có chứng từ KH mẫu nào.")

thang_co_tscd001 = sorted(set(x["thang"] for x in r["danh_sach"] if x["ma"] == "TSCD00001"))
thang_co_tscd002 = sorted(set(x["thang"] for x in r["danh_sach"] if x["ma"] == "TSCD00002"))
assert thang_co_tscd001 and thang_co_tscd001[0] == "05/2026", thang_co_tscd001
assert thang_co_tscd002 and thang_co_tscd002[0] == "06/2026", thang_co_tscd002
print("PASS: TSCD00001 (ghi tăng 26/05/2026) chỉ khấu hao TỪ tháng 05/2026, "
      "TSCD00002 (ghi tăng 30/06/2026) chỉ khấu hao TỪ tháng 06/2026 (không lùi về trước).")

# ── Ghi THẬT (preview=False) — FixedAssetLedger (nguồn SỐNG nuôi "Sổ theo dõi
# TSCĐ", SONG SONG với SupplyLedger đã xác nhận đúng bên CCDC) phải được ghi
# thêm 1 dòng snapshot mỗi kỳ khấu hao, RefType KHÔNG được lẫn với 250 (Ghi tăng).
cur2 = FakeCursor()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur2)
r2 = _misa_khau_hao_tscd(1, "TESTDB", preview=False, tu_thang="2026-01", so_thang=12)

assert len(cur2.updates) == 2, f"Phải UPDATE lại FixedAsset cho đúng 2 TSCĐ — got {len(cur2.updates)}"

assert len(cur2.led_inserts) == 7, (
    f"Phải có 7 dòng FixedAssetLedger (4 kỳ TSCD00001 + 3 kỳ TSCD00002) — got {len(cur2.led_inserts)}")
led_by_fa = {}
for row in cur2.led_inserts:
    assert row["RefType"] == 253, f"RefType dòng khấu hao PHẢI dò được qua SYSRefType (253), " \
        f"KHÔNG được lẫn với RefType Ghi tăng (250) — got {row['RefType']}"
    led_by_fa.setdefault(row["FixedAssetID"], []).append(row)

assert len(led_by_fa["fa-001"]) == 4, led_by_fa["fa-001"]
assert len(led_by_fa["fa-002"]) == 3, led_by_fa["fa-002"]
print("PASS: FixedAssetLedger được ghi đúng 7 dòng, RefType=253 (dò qua SYSRefType, KHÔNG lẫn "
      "với RefType=250 của Ghi tăng dù 250 là RefType chiếm ĐA SỐ trong bảng).")

# Dòng CUỐI CÙNG của mỗi tài sản (kỳ khấu hao cuối) phải có LifeTimeRemainingInMonth=0,
# AccumDepreciationAmount = đúng tổng nguyên giá, RemainingAmount=0 — snapshot ĐÚNG tiến độ
# sau khi khấu hao hết, giống hệt ý nghĩa các cột đó trên dòng Ghi tăng (_misa_ghi_tang_tscd).
rows_001 = sorted(led_by_fa["fa-001"], key=lambda r: r["RefOrderInSubSystem"])
last_001 = rows_001[-1]
assert last_001["LifeTimeRemainingInMonth"] == 0, last_001
assert last_001["AccumDepreciationAmount"] == 100000, last_001
assert last_001["RemainingAmount"] == 0, last_001
assert last_001["TotalDepreciationAmount"] == 100000, last_001

rows_002 = sorted(led_by_fa["fa-002"], key=lambda r: r["RefOrderInSubSystem"])
last_002 = rows_002[-1]
assert last_002["LifeTimeRemainingInMonth"] == 0, last_002
assert last_002["AccumDepreciationAmount"] == 150000, last_002
assert last_002["RemainingAmount"] == 0, last_002

print("PASS: dòng FixedAssetLedger cuối cùng của mỗi TSCĐ đúng snapshot sau khi khấu hao hết "
      "(LifeTimeRemainingInMonth=0, AccumDepreciationAmount=đủ nguyên giá, RemainingAmount=0).")

print("\nALL DONE")

# ── Test 3: đúng lỗi thật người dùng báo bên Phân bổ CCDC (song song với
# test_phan_bo_ccdc_ngay_gt.py Test 3) — bấm "Import tự động toàn bộ" LẦN 2
# với "Từ tháng/năm" vẫn còn giữ giá trị lần chạy TRƯỚC -> tu_thang="2026-05"
# GIỐNG HỆT lần đầu. TSCĐ "fa-003" CHƯA khấu hao xong hẳn (2/6 kỳ) nên
# KHÔNG bị chặn bởi lớp an toàn CŨ "hết kỳ" — không được tạo trùng 2 tháng
# đã có (05,06/2026).
class FakeCursor3(FakeCursor):
    def execute(self, sql, params=()):
        p = params if isinstance(params, (tuple, list)) else (params,) if params != () else ()
        if "FROM FixedAsset WHERE ISNULL" in sql:
            self._result = [
                ("fa-003", "TSCD00003", "May chu", 300000, 6, 50000,
                 datetime.datetime(2026, 5, 1)),
            ]
            return self
        if "FADepreciationDetail WHERE FixedAssetID" in sql:
            self._result = [(2, 100000)]   # CHỈ mới 2/6 kỳ (05,06/2026)
            return self
        if "JOIN FADepreciation a ON" in sql:
            self._result = [("fa-003", 2026, 5), ("fa-003", 2026, 6)]
            return self
        return super().execute(sql, params)


cur3 = FakeCursor3()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur3)
r3 = _misa_khau_hao_tscd(1, "TESTDB", preview=True, tu_thang="2026-05", so_thang=12)
entries_003 = [x for x in r3["danh_sach"] if x.get("ma") == "TSCD00003"]
thang_bo_qua = sorted(x["thang"] for x in entries_003 if "bỏ qua" in x.get("trang_thai", ""))
thang_tao_moi = sorted(x["thang"] for x in entries_003 if x.get("so_chung_tu"))
assert thang_bo_qua == ["05/2026", "06/2026"], (
    f"Phải BÁO 'bỏ qua' ĐÚNG cho tháng 05/2026 và 06/2026 (TSCD00003 ĐÃ CÓ chứng từ thật cho 2 "
    f"tháng này rồi) — got {thang_bo_qua}")
assert "05/2026" not in thang_tao_moi and "06/2026" not in thang_tao_moi, (
    f"KHÔNG được TẠO MỚI chứng từ Khấu hao cho tháng 05/2026 và 06/2026 (đã có sẵn) — got {thang_tao_moi}")
assert thang_tao_moi == ["07/2026", "08/2026", "09/2026", "10/2026"], (
    f"Phải tự động BỎ QUA 05,06/2026 (đã có) và TẠO MỚI đúng 4 kỳ còn lại (07-10/2026) — got {thang_tao_moi}")
print("PASS: Test 3 — TSCĐ CHƯA khấu hao xong hẳn (còn 4/6 kỳ), bấm lại với 'Từ tháng/năm' TRÙNG lần "
      "chạy trước (2026-05, song song đúng lỗi thật bên Phân bổ CCDC) KHÔNG còn tạo trùng 2 tháng đã "
      "có (05,06) nữa — tự động báo bỏ qua rồi tạo mới đúng 4 kỳ còn lại (07-10/2026).")

print("\nALL DONE (test 3)")
