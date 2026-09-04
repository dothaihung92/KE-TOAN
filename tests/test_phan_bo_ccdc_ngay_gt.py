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


# Cột thật (rút gọn nhưng đủ mọi cột _misa_gan cần) cho từng bảng liên quan.
COLUMNS = {
    "SUIncrement": [("SupplyID", "uniqueidentifier"), ("SupplyCode", "nvarchar"),
                     ("SupplyName", "nvarchar"), ("Amount", "money"),
                     ("AllocationTime", "int"), ("TermlyAllocationAmount", "money"),
                     ("RefDate", "datetime"), ("RemainingAllocationTime", "int"),
                     ("AllocatedAmount", "money"), ("RemaingAmount", "money")],
    "SUAllocation": [("RefID", "uniqueidentifier"), ("RefType", "int"), ("RefDate", "datetime"),
                      ("PostedDate", "datetime"), ("RefNo", "nvarchar"), ("JournalMemo", "nvarchar"),
                      ("Month", "int"), ("Year", "int"), ("TotalAmount", "money"),
                      ("BranchID", "uniqueidentifier"), ("IsPostedManagement", "bit"),
                      ("DisplayOnBook", "bit"), ("RefOrder", "int"), ("CreatedDate", "datetime"),
                      ("CreatedBy", "nvarchar"), ("ModifiedDate", "datetime"), ("ModifiedBy", "nvarchar"),
                      ("IsPostedFinance", "bit"), ("IsGetSupplyAllocated", "bit")],
    "SUAllocationDetailExpense": [("RefDetailID", "uniqueidentifier"), ("RefID", "uniqueidentifier"),
                                   ("SupplyID", "uniqueidentifier"), ("TotalAllocationAmount", "money"),
                                   ("AllocationAmount", "money"), ("RemainingAmount", "money"),
                                   ("SortOrder", "int")],
    "SUAllocationDetailTable": [("RefDetailID", "uniqueidentifier"), ("RefID", "uniqueidentifier"),
                                 ("SupplyID", "uniqueidentifier"), ("TotalAllocationAmount", "money"),
                                 ("AllocationObjectID", "uniqueidentifier"), ("AllocationRate", "float"),
                                 ("AllocationAmount", "money"), ("CostAccount", "nvarchar"),
                                 ("SortOrder", "int"), ("IsDetailBreak", "bit")],
    "SUAllocationDetailPost": [("RefDetailID", "uniqueidentifier"), ("RefID", "uniqueidentifier"),
                                ("Description", "nvarchar"), ("DebitAccount", "nvarchar"),
                                ("CreditAccount", "nvarchar"), ("Amount", "money"),
                                ("OrganizationUnitID", "uniqueidentifier"), ("UnResonableCost", "bit"),
                                ("SortOrder", "int")],
    "SupplyLedger": [("RefID", "uniqueidentifier"), ("RefDetailID", "uniqueidentifier"),
                      ("SupplyID", "uniqueidentifier"), ("RefType", "int"), ("RefNo", "nvarchar"),
                      ("RefDate", "datetime"), ("PostedDate", "datetime"), ("JournalMemo", "nvarchar"),
                      ("Description", "nvarchar"), ("IncrementAllocationTime", "int"),
                      ("DecrementAllocationTime", "int"), ("IncrementQuantity", "float"),
                      ("DecrementQuantity", "float"), ("IncrementAmount", "money"),
                      ("DecrementAmount", "money"), ("AllocationAmount", "money"),
                      ("TermlyAllocationAmount", "money"), ("BranchID", "uniqueidentifier"),
                      ("OrganizationUnitID", "uniqueidentifier"), ("SupplyCode", "nvarchar"),
                      ("SupplyName", "nvarchar"), ("SortOrder", "int"), ("RefOrder", "int"),
                      ("RefOrderInSubSystem", "int")],
}


class FakeCursor:
    """Mô phỏng ĐÚNG kịch bản người dùng báo lỗi: công ty MỚI, CHƯA từng có
    chứng từ PBCC nào; 2 CCDC ghi tăng ở 2 tháng KHÁC NHAU (26/05 và 30/06/2026),
    y hệt ảnh chụp màn hình MISA thật gửi kèm."""
    def __init__(self):
        self.written = []   # (table, row_dict) - ghi INSERT thật khi preview=False
        self.updates = []   # (sql, params) - các câu UPDATE SUIncrement thật đã chạy
        self.led_inserts = []   # params của các câu INSERT INTO SupplyLedger thật đã chạy

    def execute(self, sql, params=()):
        p = params if isinstance(params, (tuple, list)) else (params,) if params != () else ()
        if sql.startswith("UPDATE SUIncrement SET"):
            self.updates.append((sql, p))
            self._result = []
            return self
        if sql.startswith("INSERT INTO SupplyLedger"):
            cols_order = sql.split("([")[1].split("]) VALUES")[0].split("],[")
            self.led_inserts.append(dict(zip(cols_order, p)))
            self._result = []
            return self
        if "SELECT TOP 1 BranchID, OrganizationUnitID FROM SupplyLedger" in sql:
            self._result = []   # công ty MỚI - chưa có dòng SupplyLedger nào cho CCDC này
            return self
        if "MAX(RefOrderInSubSystem) FROM SupplyLedger" in sql:
            self._result = [(0,)]
            return self
        if "sys.columns c" in sql and "sys.types ty" in sql:
            table = p[0]
            self._result = COLUMNS.get(table, [])
        elif "SELECT name FROM sys.columns WHERE object_id" in sql:
            table = p[0]
            self._result = [(n,) for n, _t in COLUMNS.get(table, [])]
        elif sql.startswith("SELECT TOP 5 ["):
            self._result = []   # công ty MỚI - CHƯA có chứng từ PBCC thật nào để học mẫu
        elif "SYSRefType WHERE MasterTableName" in sql:
            self._result = [(4501, "Phân bổ chi phí công cụ dụng cụ")]
        elif "WHERE RefType<>0" in sql:
            self._result = []   # chưa có dòng SUAllocation thật nào
        elif "SELECT RefNo FROM SUAllocation WHERE RefNo LIKE" in sql:
            self._result = []
        elif "FROM SUIncrement WHERE ISNULL" in sql:
            self._result = [
                ("su-001", "CCDC00001", "Khoen nhua 1", 100000, 4, 25000,
                 datetime.datetime(2026, 5, 26)),
                ("su-002", "CCDC00002", "Khoen nhua 2", 150000, 3, 50000,
                 datetime.datetime(2026, 6, 30)),
            ]
        elif "SELECT COUNT(*), ISNULL(SUM(AllocationAmount),0) FROM" in sql:
            self._result = [(0, 0)]   # công ty mới - chưa phân bổ kỳ nào
        elif "SUIncrementDetailAllocation WHERE SupplyID" in sql:
            self._result = []
        elif "SUAllocationDetailTable WHERE SupplyID" in sql:
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

for fn in ("_misa_pu_reftype", "_misa_hoc_reftype", "_misa_cot_bang_that",
           "_misa_gia_tri_mac_dinh", "_misa_chon_cot", "_misa_gan",
           "_misa_mau_dong_that", "_misa_branch_id", "_misa_phan_bo_ccdc"):
    exec(extract_fn(fn), ns)

_misa_phan_bo_ccdc = ns['_misa_phan_bo_ccdc']

cur = FakeCursor()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur)

# Kịch bản Y HỆT người dùng báo: chạy "Import tự động toàn bộ" khởi động phân bổ
# từ tháng 01/2026 (tu_thang="2026-01") dù 2 CCDC chỉ ghi tăng tháng 05 và 06/2026.
r = _misa_phan_bo_ccdc(1, "TESTDB", preview=True, tu_thang="2026-01", so_thang=12)

so_ct_co_ccdc001_som = [x["so_chung_tu"] for x in r["danh_sach"]
                         if x["ma"] == "CCDC00001" and x["thang"] in ("01/2026", "02/2026", "03/2026", "04/2026")]
so_ct_co_ccdc002_som = [x["so_chung_tu"] for x in r["danh_sach"]
                         if x["ma"] == "CCDC00002" and x["thang"] in ("01/2026", "02/2026", "03/2026",
                                                                        "04/2026", "05/2026")]

assert not so_ct_co_ccdc001_som, (
    f"BUG: CCDC00001 ghi tăng 26/05/2026 nhưng vẫn bị phân bổ ở các tháng TRƯỚC đó: {so_ct_co_ccdc001_som}")
assert not so_ct_co_ccdc002_som, (
    f"BUG: CCDC00002 ghi tăng 30/06/2026 nhưng vẫn bị phân bổ ở các tháng TRƯỚC đó: {so_ct_co_ccdc002_som}")

thang_co_ccdc001 = sorted(set(x["thang"] for x in r["danh_sach"] if x["ma"] == "CCDC00001"))
thang_co_ccdc002 = sorted(set(x["thang"] for x in r["danh_sach"] if x["ma"] == "CCDC00002"))
assert thang_co_ccdc001 and thang_co_ccdc001[0] == "05/2026", thang_co_ccdc001
assert thang_co_ccdc002 and thang_co_ccdc002[0] == "06/2026", thang_co_ccdc002

print("PASS: CCDC00001 (ghi tăng 26/05/2026) chỉ được phân bổ TỪ tháng 05/2026 trở đi:", thang_co_ccdc001)
print("PASS: CCDC00002 (ghi tăng 30/06/2026) chỉ được phân bổ TỪ tháng 06/2026 trở đi:", thang_co_ccdc002)
print("PASS: không còn phân bổ lùi về trước ngày CCDC thật sự tồn tại (sửa đúng lỗi người dùng báo).")

# Đồng thời xác nhận KHÔNG còn bị chặn cứng vì thiếu chứng từ mẫu (build trước đó).
assert r["danh_sach"], "Vẫn phải tạo được chứng từ dù công ty CHƯA có PBCC mẫu nào (build .044)."
print("PASS: vẫn chạy được dù công ty MỚI chưa có PBCC mẫu nào (không bị raise HTTPException).")

# ── Ghi THẬT (preview=False) — Sổ theo dõi CCDC phải được cập nhật lại ──────────────────────
# Người dùng báo: sau khi có đủ chứng từ PBCC thật, "Sổ theo dõi CCDC" vẫn hiện "Giá trị đã
# phân bổ = 0" / "Số kỳ còn lại" y hệt lúc Ghi tăng — vì SUIncrement không được cập nhật lại.
cur2 = FakeCursor()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur2)
r2 = _misa_phan_bo_ccdc(1, "TESTDB", preview=False, tu_thang="2026-01", so_thang=12)

assert len(cur2.updates) == 2, f"Phải UPDATE lại SUIncrement cho đúng 2 CCDC — got {len(cur2.updates)}"
by_id = {}
for sql, params in cur2.updates:
    su_id = params[-1]
    cols_order = [c.split("=")[0].strip("[]") for c in sql.split("SET ")[1].split(" WHERE")[0].split(",")]
    by_id[su_id] = dict(zip(cols_order, params[:-1]))

# CCDC00001: tổng 100.000/4 kỳ = 25.000/kỳ, chạy từ 05/2026 đến 08/2026 (hết dữ liệu mô phỏng)
# = 4 kỳ đã chạy hết -> còn lại 0 kỳ, đã phân bổ đủ 100.000, còn lại 0đ.
u1 = by_id["su-001"]
assert u1["RemainingAllocationTime"] == 0, u1
assert u1["AllocatedAmount"] == 100000, u1
assert u1["RemaingAmount"] == 0, u1
print("PASS: CCDC00001 - SUIncrement được cập nhật ĐÚNG (Số kỳ còn lại=0, Đã phân bổ=100.000, "
      "Còn lại=0) sau khi chạy hết — KHÔNG còn đứng yên ở giá trị lúc Ghi tăng.")

# CCDC00002: tổng 150.000/3 kỳ = 50.000/kỳ, chỉ chạy được 06,07,08/2026 = 3 kỳ -> cũng hết luôn.
u2 = by_id["su-002"]
assert u2["RemainingAllocationTime"] == 0, u2
assert u2["AllocatedAmount"] == 150000, u2
assert u2["RemaingAmount"] == 0, u2
print("PASS: CCDC00002 - SUIncrement được cập nhật ĐÚNG (Số kỳ còn lại=0, Đã phân bổ=150.000, "
      "Còn lại=0) sau khi chạy hết.")

# ── Xác nhận SupplyLedger (nguồn THẬT nuôi "Sổ theo dõi CCDC" — Proc_SU_SelectAll_View_Supply
# đọc SỐNG từ bảng này, KHÔNG phải SUIncrement) được ghi đúng: mỗi kỳ phân bổ = 1 dòng
# RefType=453, DecrementAllocationTime=1 (trừ đúng 1 kỳ), AllocationAmount=tiền kỳ đó.
assert len(cur2.led_inserts) == 7, f"Phải có 7 dòng SupplyLedger (4 kỳ CCDC001 + 3 kỳ CCDC002) — got {len(cur2.led_inserts)}"
led_by_su = {}
for row in cur2.led_inserts:
    assert row["RefType"] == 453, row
    assert row["DecrementAllocationTime"] == 1, row
    led_by_su.setdefault(row["SupplyID"], []).append(row["AllocationAmount"])

assert len(led_by_su["su-001"]) == 4 and sum(led_by_su["su-001"]) == 100000, led_by_su["su-001"]
assert len(led_by_su["su-002"]) == 3 and sum(led_by_su["su-002"]) == 150000, led_by_su["su-002"]
print("PASS: SupplyLedger được ghi đúng 7 dòng RefType=453 (Phân bổ chi phí CCDC), mỗi dòng trừ "
      "đúng 1 kỳ (DecrementAllocationTime=1) và tổng AllocationAmount khớp đúng tổng đã phân bổ — "
      "đây là nguồn SỐNG mà 'Sổ theo dõi CCDC' thật sự cộng dồn (xác nhận qua đọc trực tiếp định "
      "nghĩa Proc_SU_SelectAll_View_Supply lấy được từ CSDL MISA thật của khách hàng).")

print("\nALL DONE")

# ── Test 3: đúng lỗi thật người dùng vừa báo — bấm "Import tự động toàn bộ"
# LẦN 2 với "Từ tháng/năm" vẫn còn giữ giá trị của lần chạy TRƯỚC (form
# không tự xoá) -> tu_thang="2026-05" GIỐNG HỆT lần đầu. CCDC "su-003" có
# TỔNG 6 kỳ (chưa xong hẳn — CHỈ mới 2/6 kỳ, con_lai_ky=4 > 0 nên KHÔNG bị
# chặn bởi lớp an toàn CŨ "hết kỳ" — đây mới đúng là kịch bản lỗi thật:
# công ty CHƯA phân bổ xong, bấm lại vẫn tạo trùng đúng những tháng ĐÃ có
# rồi (05,06/2026) thay vì tiếp nối đúng từ tháng 07/2026).
class FakeCursor3(FakeCursor):
    def execute(self, sql, params=()):
        p = params if isinstance(params, (tuple, list)) else (params,) if params != () else ()
        if "FROM SUIncrement WHERE ISNULL" in sql:
            self._result = [
                ("su-003", "CCDC00003", "May tinh", 300000, 6, 50000,
                 datetime.datetime(2026, 5, 1)),
            ]
            return self
        if "SELECT COUNT(*), ISNULL(SUM(AllocationAmount),0) FROM" in sql:
            # CHỈ mới 2/6 kỳ đã phân bổ (05,06/2026) -> con_lai_ky=4, CHƯA hết.
            self._result = [(2, 100000)]
            return self
        if "JOIN SUAllocation a ON" in sql:
            # (SupplyID, Year, Month) đã có chứng từ PBCC THẬT — đúng kỳ
            # 05/2026 và 06/2026 từ lần chạy trước.
            self._result = [("su-003", 2026, 5), ("su-003", 2026, 6)]
            return self
        return super().execute(sql, params)


cur3 = FakeCursor3()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur3)
r3 = _misa_phan_bo_ccdc(1, "TESTDB", preview=True, tu_thang="2026-05", so_thang=12)
entries_003 = [x for x in r3["danh_sach"] if x.get("ma") == "CCDC00003"]
thang_bo_qua = sorted(x["thang"] for x in entries_003 if "bỏ qua" in x.get("trang_thai", ""))
thang_tao_moi = sorted(x["thang"] for x in entries_003 if x.get("so_chung_tu"))
assert thang_bo_qua == ["05/2026", "06/2026"], (
    f"Phải BÁO 'bỏ qua' ĐÚNG cho tháng 05/2026 và 06/2026 (CCDC00003 ĐÃ CÓ chứng từ thật cho 2 "
    f"tháng này rồi) — got {thang_bo_qua}")
assert "05/2026" not in thang_tao_moi and "06/2026" not in thang_tao_moi, (
    f"KHÔNG được TẠO MỚI chứng từ PBCC cho tháng 05/2026 và 06/2026 — CCDC00003 ĐÃ CÓ chứng từ thật "
    f"cho 2 tháng này rồi (đúng lỗi thật: bấm lại 'Import tự động toàn bộ' với Từ tháng/năm vẫn còn "
    f"giữ giá trị cũ '2026-05', trong khi CCDC CHƯA phân bổ xong hẳn nên không bị lớp an toàn cũ "
    f"'hết kỳ' chặn — tạo trùng đúng 2 tháng đã có) — got {thang_tao_moi}")
assert thang_tao_moi == ["07/2026", "08/2026", "09/2026", "10/2026"], (
    f"Phải tự động BỎ QUA 05,06/2026 (đã có) và TẠO MỚI đúng 4 kỳ còn lại (07-10/2026) — got {thang_tao_moi}")
print("PASS: Test 3 — CCDC CHƯA phân bổ xong hẳn (còn 4/6 kỳ), bấm lại với 'Từ tháng/năm' TRÙNG lần "
      "chạy trước (2026-05, y hệt lỗi thật người dùng báo) KHÔNG còn tạo trùng 2 tháng đã có (05,06) "
      "nữa — tự động bỏ qua rồi tiếp tục đúng 4 kỳ còn lại (07-10/2026) — an toàn dựa vào chính dữ "
      "liệu THẬT đã có trong MISA (SUAllocationDetailExpense JOIN SUAllocation.Month/Year), không "
      "tin riêng tham số 'tháng bắt đầu' truyền vào.")

print("\nALL DONE (test 3)")
