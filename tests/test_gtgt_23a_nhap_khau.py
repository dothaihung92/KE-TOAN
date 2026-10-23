import os, sys, sqlite3, datetime, tempfile
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Bước 6 (Tờ khai 01/GTGT): [23a]/[24a] (hàng nhập khẩu) phải lấy từ dòng mua hàng TỜ KHAI NHẬP KHẨU trong MISA — trước đây luôn 0.
class Cur:
    def __init__(self, loi_cot_nk=False): self.sqls = []; self.loi = loi_cot_nk
    def execute(self, sql, params=()):
        self.sql = sql; self.sqls.append(sql)
        if self.loi and "ImportTaxRatePrice" in sql:
            raise Exception("Invalid column name 'ImportTaxRatePrice'")
        return self
    def fetchone(self):
        q = self.sql
        if "FROM PUVoucherDetail" in q and "ImportTaxRatePrice" in q: return (452119576, 45211958)
        if "FROM PUVoucherDetail" in q: return (1500000000, 120000000)
        if "FROM PUServiceDetail" in q: return (756321461, 16506235)
        return (0, 0)
    def fetchall(self):
        q = self.sql
        if "FROM PUVoucherDetail" in q and "GROUP BY" in q:
            base = [("r1", "b", 302, "a1", "108500567010", "", datetime.datetime(2026, 8, 10), "NCC NN", "", 10, 452119576, 45211958),
                    ("r2", "b", 302, "a2", "123", "C26TAA", datetime.datetime(2026, 8, 11), "NCC VN", "0300000001", 8, 1047880424, 74788042)]
            return [x + (1 if x[0] == "r1" else 0,) for x in base] if "ImportTaxRatePrice" in q else base
        if "FROM PUServiceDetail" in q and "GROUP BY" in q:
            return [("r3", "b", 330, "a3", "6357", "", datetime.datetime(2026, 8, 10), "UNI", "0318581564", 8, 5610241, 448820)]
        if "SELECT DISTINCT d.InvNo" in q:
            return [("108500567010",), ("123",)]
        return []

tu, den = datetime.datetime(2026, 7, 1), datetime.datetime(2026, 9, 30, 23, 59, 59)
ct = server._misa_tinh_chi_tieu_gtgt_tu_misa(Cur(), tu, den)
assert ct["ct23"] == 1500000000 + 756321461 and ct["ct23a"] == 452119576 and ct["ct24a"] == 45211958, ct
assert ct["ct25"] == ct["ct24"] == 136506235
ct2 = server._misa_tinh_chi_tieu_gtgt_tu_misa(Cur(loi_cot_nk=True), tu, den)
assert ct2["ct23a"] == 0 and ct2["ct23"] == ct["ct23"]
print("PASS 1: [23a]/[24a] = dòng nhập khẩu (ImportTaxRatePrice/ImportTaxAmount/IsImportPurchase) đã ghi sổ trong kỳ; CSDL thiếu cột -> 0, không lỗi.")

cols = {k.lower(): (k, "nvarchar") for k in ("RefDetailID", "RefID", "AppendixID", "VoucherRefID", "InvNo", "TurnOverAmount", "TaxAmount", "IsVoucherImport", "SortOrder")}
_, r012 = server._misa_dien_chi_tiet_hoa_don_gtgt(Cur(), {}, cols, tu, den, "tk", "a1", "a2")
co = {x["InvNo"]: x["IsVoucherImport"] for x in r012}
assert co == {"108500567010": True, "123": False, "6357": False}, co
_, r012b = server._misa_dien_chi_tiet_hoa_don_gtgt(Cur(loi_cot_nk=True), {}, cols, tu, den, "tk", "a1", "a2")
assert len(r012b) == 3 and not any(x["IsVoucherImport"] for x in r012b)
print("PASS 2: phụ lục BKMV — dòng tờ khai nhập khẩu IsVoucherImport=True, hóa đơn thường False; CSDL thiếu cột vẫn ghi đủ dòng.")

fdb = os.path.join(tempfile.mkdtemp(), "t.db")
c = sqlite3.connect(fdb)
c.execute("CREATE TABLE tokhai_nhap (id INTEGER PRIMARY KEY, company_id INTEGER, so_tk TEXT, ngay_dk TEXT, nguoi_xk TEXT, items_json TEXT, updated_at TEXT)")
c.executemany("INSERT INTO tokhai_nhap (company_id, so_tk, ngay_dk) VALUES (?,?,?)",
              [(1, "108500567010", "2026-08-10"), (1, "108574481520", "2026-09-04"), (1, "107000000000", "2026-04-01")])
c.commit(); c.close()
orig = server.db
def db():
    k = sqlite3.connect(fdb); k.row_factory = sqlite3.Row; return k
server.db = db
try:
    cb = server._canh_bao_to_khai_nhap_chua_vao_misa(1, Cur(), tu, den)
finally:
    server.db = orig
assert cb and "108574481520" in cb and "108500567010" not in cb and "107000000000" not in cb, cb
print("PASS 3: cảnh báo tờ khai nhập trong kỳ chưa có trong MISA (108574481520); tờ khai đã ghi / ngoài kỳ không báo.")

src = open(os.path.join(_REPO_ROOT, "server.py"), encoding="utf-8").read()
f = src[src.index("def _misa_tao_to_khai_khau_tru_gtgt("):]
f = f[:f.index("\n@app.")]
assert '"ct23a": ct.get("ct23a")' in f and "_canh_bao_to_khai_nhap_chua_vao_misa(cid, cur" in f
print("PASS 4: kết quả bước 6 trả [23a]/[24a] + cảnh báo tờ khai nhập để hiện trên màn hình.")
print("ALL DONE")
