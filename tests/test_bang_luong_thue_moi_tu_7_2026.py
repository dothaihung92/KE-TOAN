import os
import sys
import asyncio
import sqlite3
import tempfile
import json

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Yêu cầu người dùng (Bảng Lương): "tính thêm công thức TNCN từ tháng 7/2026 có sự thay đổi tính thuế TNCN —
# khi tính lương tới tháng này thì phần mềm tự động đổi cách tính". Luật Thuế TNCN 2025: giảm trừ bản thân
# 15.500.000, người phụ thuộc 6.200.000, biểu lũy tiến 5 bậc (10tr 5% / 30tr 10% / 60tr 20% / 100tr 30% / >100tr 35%).

cc = server._luong_thue_tncn
MOI = server._LUONG_THUE_MOI["bac_thue"]
CU = server._LUONG_THAM_SO_MAC_DINH["bac_thue"]

# ===== 1: biểu 5 bậc: mốc tối đa từng bậc đúng luật (0,5tr / 3,5tr... cộng dồn) và các điểm giữa. =====
assert cc(10_000_000, MOI) == 500_000                      # bậc 1 tối đa 0,5 triệu
assert cc(30_000_000, MOI) == 2_500_000                    # + 10% x 20tr
assert cc(60_000_000, MOI) == 8_500_000                    # + 20% x 30tr
assert cc(100_000_000, MOI) == 20_500_000                  # + 30% x 40tr = 20,5 triệu
assert cc(120_000_000, MOI) == 27_500_000                  # + 35% x 20tr
assert cc(24_500_000, MOI) == 1_950_000 and cc(0, MOI) == 0 and cc(-5, MOI) == 0
assert cc(29_000_000, CU) == 4_150_000                     # biểu cũ 7 bậc vẫn như file mẫu
print("PASS 1: biểu 5 bậc mới đúng (0,5tr / 2,5tr / 8,5tr / 20,5tr...), biểu 7 bậc cũ không đổi.")

# ===== 2: mặc định năm 2026: từ tháng 7 đổi sang bộ thuế mới; năm 2025 không đổi; năm 2027 áp dụng cả năm. =====
t26 = server._luong_chuan_tham_so(None, 2026)
assert t26["giam_tru_ban_than"] == 11_000_000 and t26["bac_thue"][-1] == [80_000_000, 35]
tm = t26["thue_moi"]
assert tm["tu_thang"] == 7 and tm["giam_tru_ban_than"] == 15_500_000 and tm["giam_tru_npt"] == 6_200_000
assert tm["bac_thue"] == [[0, 5], [10_000_000, 10], [30_000_000, 20], [60_000_000, 30], [100_000_000, 35]]
assert server._luong_chuan_tham_so(None, 2025)["thue_moi"] is None
t27 = server._luong_chuan_tham_so(None, 2027)
assert t27["thue_moi"] is None and t27["giam_tru_ban_than"] == 15_500_000 and t27["giam_tru_npt"] == 6_200_000
assert t27["bac_thue"] == tm["bac_thue"], "Năm sau 2026: áp dụng bộ thuế mới cả năm"
assert server._luong_chuan_tham_so(None)["thue_moi"] is None      # không có năm -> như cũ
print("PASS 2: 2026 tự đổi từ tháng 7; 2025 giữ nguyên; 2027 trở đi áp dụng thuế mới cả năm.")

# ===== 3: tính lương: T6/2026 theo thuế cũ, T7/2026 tự theo thuế mới (cùng 1 người, cùng số liệu). =====
dong = {"ma": "1", "ten": "A", "luong_cb": 40_000_000, "ngay_cong": 26, "dong_bh": 0, "so_npt": 0}
t6 = server._luong_tinh_dong(dong, t26, "06")
t7 = server._luong_tinh_dong(dong, t26, "07")
t12 = server._luong_tinh_dong(dong, t26, "12")
assert t6["giam_tru_ban_than"] == 11_000_000 and t6["tn_tinh_thue"] == 29_000_000 and t6["thue_tncn"] == 4_150_000
assert t7["giam_tru_ban_than"] == 15_500_000 and t7["tn_tinh_thue"] == 24_500_000 and t7["thue_tncn"] == 1_950_000
assert t12["thue_tncn"] == 1_950_000
assert t7["tt_luong"] == 40_000_000 - 1_950_000 and t6["tt_luong"] == 40_000_000 - 4_150_000
# có người phụ thuộc: cũ trừ 4,4tr/người, mới trừ 6,2tr/người
d1 = dict(dong, so_npt=1)
a, b = server._luong_tinh_dong(d1, t26, "06"), server._luong_tinh_dong(d1, t26, "07")
assert a["tien_giam_tru_npt"] == 4_400_000 and a["thue_tncn"] == 3_270_000, a["thue_tncn"]
assert b["tien_giam_tru_npt"] == 6_200_000 and b["tn_tinh_thue"] == 18_300_000 and b["thue_tncn"] == 1_330_000, b
# thu nhập thấp: 15,5tr giảm trừ mới -> không còn thuế
thap = dict(dong, luong_cb=15_000_000)
assert server._luong_tinh_dong(thap, t26, "06")["thue_tncn"] > 0 and server._luong_tinh_dong(thap, t26, "07")["thue_tncn"] == 0
# không truyền tháng (hoặc tham số không năm) -> giữ cách tính cũ
assert server._luong_tinh_dong(dong, t26)["thue_tncn"] == 4_150_000
assert server._luong_tinh_dong(dong, server._luong_chuan_tham_so(None), "07")["thue_tncn"] == 4_150_000
print("PASS 3: T6/2026 thuế cũ, từ T7/2026 tự đổi sang giảm trừ 15,5tr/6,2tr + biểu 5 bậc.")

# ===== 4: người dùng chỉnh/tắt bộ thuế mới trong Tham số năm được lưu đúng (không bị ghi đè bởi mặc định). =====
sua = server._luong_chuan_tham_so({"thue_moi": {"tu_thang": "9", "giam_tru_ban_than": "16.000.000",
                                                "bac_thue": [[0, 7]]}}, 2026)["thue_moi"]
assert sua["tu_thang"] == 9 and sua["giam_tru_ban_than"] == 16_000_000 and sua["giam_tru_npt"] == 6_200_000
assert sua["bac_thue"] == [[0, 7]]
assert server._luong_tinh_dong(dong, dict(server._luong_chuan_tham_so({"thue_moi": sua}, 2026)), "08")["giam_tru_ban_than"] == 11_000_000
assert server._luong_chuan_tham_so({"thue_moi": None}, 2026)["thue_moi"] is None          # tắt: không đổi giữa năm
assert server._luong_chuan_tham_so({"thue_moi": {"tu_thang": 0}}, 2026)["thue_moi"] is None   # tháng sai -> bỏ
print("PASS 4: chỉnh/tắt bộ thuế mới trong tham số năm được giữ đúng.")


# ===== 5: API: năm 2026 dữ liệu đã lưu trước đây (chưa có thue_moi) tự nhận bộ thuế mới từ tháng 7; lưu/tải giữ nguyên. =====
class _Req:
    def __init__(self, body): self._b = body
    async def json(self): return self._b


_duong = tempfile.mktemp(suffix=".sqlite3")


def _db_tam():
    c = sqlite3.connect(_duong)
    c.row_factory = sqlite3.Row
    return c


_goc = server.db
server.db = _db_tam
try:
    c0 = _db_tam()
    server._luong_dam_bao_bang(c0)
    cu_ts = json.dumps({"giam_tru_ban_than": 11000000, "giam_tru_npt": 4400000, "ngay_cong_chuan": 26})
    c0.execute("INSERT INTO bang_luong (company_id, nam, tham_so_json, thang_json) VALUES (1, 2026, ?, ?)",
               (cu_ts, json.dumps({"06": [dong], "07": [dong]})))
    c0.commit(); c0.close()
    g = server.bang_luong_get(1, nam=2026)
    assert g["thang"]["06"][0]["thue_tncn"] == 4_150_000 and g["thang"]["07"][0]["thue_tncn"] == 1_950_000
    assert g["tham_so"]["thue_moi"]["tu_thang"] == 7
    asyncio.run(server.bang_luong_luu(1, _Req({"tham_so": g["tham_so"], "thang": {"07": [dong]}}), nam=2026))
    g2 = server.bang_luong_get(1, nam=2026)
    assert g2["thang"]["07"][0]["thue_tncn"] == 1_950_000 and g2["tham_so"]["thue_moi"]["giam_tru_ban_than"] == 15_500_000
    # tắt bộ thuế mới -> lưu -> tháng 7 tính lại theo thuế cũ
    ts_tat = dict(g2["tham_so"], thue_moi=None)
    asyncio.run(server.bang_luong_luu(1, _Req({"tham_so": ts_tat, "thang": {"07": [dong]}}), nam=2026))
    assert server.bang_luong_get(1, nam=2026)["thang"]["07"][0]["thue_tncn"] == 4_150_000
    kq = asyncio.run(server.bang_luong_tinh(_Req({"nam": 2026, "thang": "08", "tham_so": {}, "rows": [dong]})))
    assert kq["rows"][0]["thue_tncn"] == 1_950_000 and kq["tham_so"]["thue_moi"]["tu_thang"] == 7
    # năm 2027 tạo mới: dùng thuế mới ngay từ tháng 1
    kq27 = asyncio.run(server.bang_luong_tinh(_Req({"nam": 2027, "thang": "01", "tham_so": {}, "rows": [dong]})))
    assert kq27["rows"][0]["thue_tncn"] == 1_950_000
finally:
    server.db = _goc
print("PASS 5: dữ liệu 2026 đã lưu tự nhận thuế mới từ T7; lưu/tải/tắt đúng; 2027 dùng thuế mới từ T1.")

# ===== 6: Excel xuất ra: công thức thuế từng dòng theo đúng bộ thuế của tháng (T6 cũ, T7 mới); tính lại độc lập. =====
import openpyxl
_dl = server.DOWNLOAD_DIR
server.DOWNLOAD_DIR = tempfile.mkdtemp()
try:
    duong, _ = server._luong_xuat_excel(2026, t26, {"06": [d1], "07": [d1]})
    ws = openpyxl.load_workbook(duong).active
    cot = [c[0] for c in server._LUONG_COT_EXCEL]
    ch = lambda r, k: ws.cell(r, cot.index(k) + 1).value
    assert ch(3, "giam_tru_bt") == 11_000_000 and ch(4, "giam_tru_bt") == 15_500_000
    assert "80000000" in ch(3, "thue_tncn") and "100000000" in ch(4, "thue_tncn") and "80000000" not in ch(4, "thue_tncn")
    assert "*4400000" in ch(3, "tien_npt") and "*6200000" in ch(4, "tien_npt")
    try:
        import formulas
    except Exception:
        formulas = None
    if formulas:
        xl = formulas.ExcelModel().loads(duong).finish()
        sol = xl.calculate()
        def gia_tri(r, k):
            ten = "'[%s]%s'!%s%d" % (os.path.basename(duong), ws.title.upper(), openpyxl.utils.get_column_letter(cot.index(k) + 1), r)
            return float(list(sol[ten].value[0])[0])
        assert round(gia_tri(3, "thue_tncn")) == 3_270_000 and round(gia_tri(4, "thue_tncn")) == 1_330_000
        print("  (đã tính lại công thức Excel độc lập: T6 = 3.270.000, T7 = 1.330.000)")
finally:
    server.DOWNLOAD_DIR = _dl
print("PASS 6: Excel xuất ra dùng đúng giảm trừ + biểu thuế theo từng tháng.")

print("\nALL DONE")
