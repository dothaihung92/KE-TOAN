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
        self.code = code; self.msg = msg; self.detail = msg
        super().__init__(f"{code}: {msg}")

ns = {'datetime': datetime, 'HTTPException': FakeHTTPException}
exec(extract_fn('_misa_tom_tat_buoc'), ns)
exec(extract_fn('_misa_import_tu_dong'), ns)
_misa_import_tu_dong = ns['_misa_import_tu_dong']

goi = []  # ghi lại thứ tự + tham số các bước được gọi

def mk(ten, **extra_check):
    def fn(*a, **k):
        goi.append((ten, k))
        return {"so_them": 0, "danh_sach": []}
    return fn

ns['_misa_ghi_khncc'] = lambda cid, database, preview=True: (goi.append(("khncc", {})), {"so_them": 0, "danh_sach": []})[1]
ns['_misa_ghi_ban_hang'] = mk("ban_hang")
ns['nhap_lieu_get'] = lambda cid, loai: {"header": [], "rows": []}
ns['_gen_danh_muc'] = lambda *a, **k: ([], 0)
ns['_luu_danh_muc'] = lambda *a, **k: None
ns['_misa_ghi_hang_hoa'] = mk("hang_hoa")
ns['_misa_ghi_mua_hang'] = mk("mua_hang")
ns['_misa_ghi_mua_hang_dv'] = mk("mua_hang_dv")
ns['_misa_ghi_tang_ccdc'] = mk("ghi_tang_ccdc")
ns['_misa_ghi_tang_tscd'] = mk("ghi_tang_tscd")
ns['_misa_phan_bo_ccdc'] = mk("phan_bo_ccdc")
ns['_misa_khau_hao_tscd'] = mk("khau_hao_tscd")

def gtgt_stub(cid, database, preview=True, tu_quy=None, tu_nam=None, so_quy=4):
    goi.append(("to_khai_gtgt", {"preview": preview, "tu_quy": tu_quy, "tu_nam": tu_nam, "so_quy": so_quy}))
    return {"so_quy": 1, "danh_sach": [{}]}
ns['_misa_tao_to_khai_khau_tru_gtgt'] = gtgt_stub


def doi_chieu_stub(cid, database):
    goi.append(("doi_chieu", {}))
    return {"ban_hang": {"tong_hd_nguon": 0, "khop": 0, "thieu": [], "lech": []},
            "mua_hang": {"tong_hd_nguon": 0, "khop": 0, "thieu": [], "lech": []},
            "doc_duoc": {"ban_hang": True, "mua_hang_nk_kqk": True, "mua_hang_dv": True}}
ns['_misa_doi_chieu_import_toan_bo'] = doi_chieu_stub

exec(extract_fn('_misa_import_tu_dong'), ns)
_misa_import_tu_dong = ns['_misa_import_tu_dong']

r = _misa_import_tu_dong(1, "TESTDB", preview=False, ghi_de=False)
print("Các bước đã chạy:", [g[0] for g in goi])
print("Các bước trong 'cac_buoc':", [b["ten"] for b in r["cac_buoc"]])

assert goi[-2][0] == "to_khai_gtgt", f"Tờ khai GTGT phải là BƯỚC GHI CUỐI CÙNG (trước bước Đối chiếu chỉ đọc), got {goi[-2][0]}"
assert goi[-2][1] == {"preview": False, "tu_quy": None, "tu_nam": None, "so_quy": 4}, goi[-2][1]
print("PASS: Tờ khai GTGT + Khấu trừ chạy ở BƯỚC GHI CUỐI CÙNG, preview truyền đúng, tu_quy/tu_nam=None -> so_quy mặc định 4 (tự tiếp nối)")

assert goi[-1][0] == "doi_chieu", f"Đối chiếu tổng giá trị & VAT phải chạy SAU Tờ khai GTGT (bước 7, chỉ đọc) — got {goi[-1][0]}"
print("PASS: Đối chiếu tổng giá trị & VAT (bước 7, chỉ đọc) chạy SAU CÙNG, sau cả Tờ khai GTGT.")

ten_buoc_gtgt = next(b["ten"] for b in r["cac_buoc"] if "Tờ khai GTGT" in b["ten"])
assert "6" in ten_buoc_gtgt, f"Tên bước Tờ khai GTGT phải là '6. Tờ khai GTGT...', got {ten_buoc_gtgt}"
ten_buoc_cuoi = r["cac_buoc"][-1]["ten"]
assert "Đối chiếu" in ten_buoc_cuoi and "7" in ten_buoc_cuoi, (
    f"Bước cuối trong kết quả trả về phải là '7. Đối chiếu tổng giá trị & VAT', got {ten_buoc_cuoi}")
print(f"PASS: Bước cuối trong kết quả trả về đúng tên: '{ten_buoc_cuoi}' (sau '{ten_buoc_gtgt}')")

# Test 2: có truyền đủ tu_quy/tu_nam/den_quy/den_nam -> so_quy phải tự tính đúng
goi.clear()
r2 = _misa_import_tu_dong(1, "TESTDB", preview=True, ghi_de=False,
                          tu_quy=3, tu_nam=2024, den_quy=2, den_nam=2025)
# Từ Q3/2024 đến Q2/2025 = Q3/24,Q4/24,Q1/25,Q2/25 = 4 quý
# preview=True -> bước 7 (Đối chiếu) KHÔNG chạy (xem Test 3), nên bước cuối
# cùng thật sự gọi giờ là to_khai_gtgt, không còn phải lùi -2 để bỏ qua doi_chieu.
assert goi[-1][0] == "to_khai_gtgt", f"preview=True -> Tờ khai GTGT phải là bước GHI cuối cùng thật sự được gọi (Đối chiếu bị bỏ qua) — got {goi[-1][0]}"
assert goi[-1][1] == {"preview": True, "tu_quy": 3, "tu_nam": 2024, "so_quy": 4}, goi[-1][1]
print("PASS: tu_quy=3/tu_nam=2024 -> den_quy=2/den_nam=2025 tự tính so_quy=4 đúng")

# Test 3 (MỚI): preview=True -> bước 7 Đối chiếu tổng giá trị & VAT KHÔNG
# được chạy, vì lúc preview MISA CHƯA có dữ liệu thật nào (mới chỉ tính
# "Sẽ ghi bao nhiêu"), đối chiếu lúc này sẽ báo sai hàng loạt "thiếu" dù
# chưa hề có lỗi gì (đúng phản hồi người dùng: "phần kiểm tra chêch lệch
# khi đang import hãy bỏ hiện phần này vì dữ liệu chưa import nên dữ liệu
# sẽ báo thiếu").
assert "doi_chieu" not in [g[0] for g in goi], (
    f"preview=True KHÔNG được gọi _misa_doi_chieu_import_toan_bo (MISA chưa có dữ liệu thật, đối "
    f"chiếu lúc này vô nghĩa và gây hiểu nhầm) — got {[g[0] for g in goi]}")
ten_cac_buoc2 = [b["ten"] for b in r2["cac_buoc"]]
assert not any("Đối chiếu" in t for t in ten_cac_buoc2), (
    f"preview=True -> 'cac_buoc' trả về KHÔNG được có bước Đối chiếu — got {ten_cac_buoc2}")
print("PASS: Test 3 — preview=True KHÔNG chạy bước 7 Đối chiếu tổng giá trị & VAT (chỉ chạy khi đã "
      "THẬT SỰ ghi vào MISA, preview=False) — sửa đúng phản hồi người dùng.")

print("\nALL DONE")
