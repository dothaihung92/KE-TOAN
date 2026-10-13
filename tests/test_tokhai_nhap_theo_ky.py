import os, sys, sqlite3, json, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Import & xem tờ khai nhập khẩu THEO KỲ BÁO CÁO:
#  - Import: chỉ nhận tờ khai có ngày đăng ký TRONG kỳ (tu→den); tờ khai ngoài kỳ bị bỏ qua, nêu rõ.
#  - Xem/Xoá: có tu/den -> chỉ hiện tờ khai trong kỳ; để trống (vd tra cứu nguyên năm) -> hiện tất cả.
conn = sqlite3.connect(":memory:", check_same_thread=False); conn.row_factory = sqlite3.Row
conn.execute("CREATE TABLE tokhai_nhap (company_id INTEGER, so_tk TEXT, ngay_dk TEXT, nguoi_xk TEXT, items_json TEXT, updated_at TEXT, PRIMARY KEY(company_id, so_tk))")
class KhongDong:
    def __init__(self, c): self.c = c
    def execute(self, *a): return self.c.execute(*a)
    def commit(self): self.c.commit()
    def close(self): pass
server.db = lambda: KhongDong(conn)

def nk(so, ngay):
    conn.execute("INSERT OR REPLACE INTO tokhai_nhap VALUES (7,?,?,'XK',?, '')",
                 (so, ngay, json.dumps([{"ten": "H", "tien_thue_gtgt": 1}])))

# Q3/2026 = 01/07 → 30/09; có tờ khai Q2, Q3, Q4
nk("TK_Q2", "2026-06-28"); nk("TK_Q3a", "2026-07-15"); nk("TK_Q3b", "2026-09-30"); nk("TK_Q4", "2026-10-02")

# 1) Xem theo kỳ Q3 -> chỉ 2 tờ khai trong quý 3
r = server.list_tokhai_nhap(7, tu="2026-07-01", den="2026-09-30")
assert r["loc_ky"] is True and r["tong_tat_ca"] == 4
assert sorted(x["so_tk"] for x in r["ds"]) == ["TK_Q3a", "TK_Q3b"], r["ds"]
print("PASS 1: xem theo kỳ Q3 chỉ hiện tờ khai đăng ký trong quý 3.")

# 2) Không truyền kỳ (tra cứu nguyên năm / xem tất cả) -> hiện hết
r = server.list_tokhai_nhap(7)
assert r["loc_ky"] is False and len(r["ds"]) == 4 and r["tong_tat_ca"] == 4
# cả năm 2026
r = server.list_tokhai_nhap(7, tu="2026-01-01", den="2026-12-31")
assert len(r["ds"]) == 4
print("PASS 2: không lọc kỳ / tra cứu cả năm -> hiện tất cả tờ khai trong khoảng đó.")

# 3) Import chỉ nhận tờ khai TRONG kỳ Q3 (bỏ qua ngoài kỳ)
conn.execute("DELETE FROM tokhai_nhap")
cac_tk = {"IMP_Q2": "2026-06-20", "IMP_Q3": "2026-08-10", "IMP_Q4": "2026-11-01"}
def fake_parse(wb):
    so = wb  # ở test, "wb" chính là số tờ khai (fake load_workbook trả về số TK)
    return {"so_tk": so, "ngay_dk": cac_tk[so], "nguoi_xk": "XK",
            "items": [{"ten": "H", "tien_thue_gtgt": 1}]}
server._parse_tokhai_nhap = fake_parse
# endpoint dùng `import openpyxl` cục bộ -> thay trong sys.modules để nhận bản giả;
# load_workbook đọc BytesIO (chứa số tờ khai đã encode) trả lại số TK
import types as _types
_fake_op = _types.ModuleType("openpyxl")
_fake_op.load_workbook = lambda bio, data_only=True: bio.getvalue().decode()
sys.modules["openpyxl"] = _fake_op

class FakeUpload:
    def __init__(self, so): self.filename = so + ".xlsx"; self._so = so
    async def read(self): return self._so.encode()   # bytes mang theo số tờ khai

class FakeForm:
    def __init__(self, ups, tu, den): self._ups = ups; self._kv = {"tu": tu, "den": den}
    def getlist(self, k): return self._ups if k == "files" else []
    def get(self, k): return self._kv.get(k)
class FakeReq:
    def __init__(self, form): self._f = form
    async def form(self): return self._f

async def chay(tu, den):
    ups = [FakeUpload(s) for s in cac_tk]
    return await server.import_tokhai_nhap(7, FakeReq(FakeForm(ups, tu, den)))

res = asyncio.get_event_loop().run_until_complete(chay("2026-07-01", "2026-09-30"))
assert res["so_to_khai"] == 1 and res["so_ngoai_ky"] == 2, res
got = server.list_tokhai_nhap(7)
assert [x["so_tk"] for x in got["ds"]] == ["IMP_Q3"], got["ds"]
assert any("IMP_Q2" in x for x in res["ngoai_ky"]) and any("IMP_Q4" in x for x in res["ngoai_ky"]), res["ngoai_ky"]
print("PASS 3: import chỉ nhận tờ khai trong kỳ (Q3), bỏ qua tờ khai Q2/Q4 và nêu rõ.")

print("ALL DONE")
