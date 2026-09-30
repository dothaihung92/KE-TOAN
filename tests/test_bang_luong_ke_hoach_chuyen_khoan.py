import os
import sys
import io
import asyncio
import random
import datetime

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server
import openpyxl
from fastapi import HTTPException

# Yêu cầu: trong "Chi phí lương cả năm" thêm mục import file thanh toán lương chuyển khoản (Sổ chi tiết TK 334 của MISA: Nợ 334 / Có 1121); phần mềm
# dựa vào file để dựng bảng lương từng tháng sao cho TT lương chuyển khoản KHỚP số đã chuyển, vẫn theo cấu trúc kế hoạch đã làm.

D = datetime.datetime
HEADER = ["Ngày hạch toán", "Ngày chứng từ", "Số chứng từ", "Diễn giải", "Tài khoản", "TK đối ứng", "Phát sinh Nợ", "Phát sinh Có", "Dư Nợ", "Dư Có",
          "Mã mục thu/chi", "Tên mục thu/chi"]
DONG = [
    (D(2025, 6, 16), "UNC1", "CONG TY TNHH ABC THANH TOAN LUONG UNG T6 2025--", "1121", 3_500_000),
    (D(2025, 6, 17), "UNC2", "THANH TOAN LUONG T5 2025-160625-20:10:01 724112--", "1121", 22_894_000),
    (D(2025, 6, 17), "UNC3", "THANH TOAN LUON TAN TAN T5 2025-160625-20:12:02 727447--", "1121", 5_216_000),
    (D(2025, 7, 5), "UNC4", "THANH TOAN LUONG UNG T7 2026-040725-20:54:18 367994--", "1121", 2_500_000),      # năm trong diễn giải gõ sai
    (D(2025, 7, 28), "UNC5", "THANH TOAN LUONG KETOAN-280725-17:20:16 656794-DO THAI HUNG-DO THAI HUNG", "1121", 3_000_000),   # không ghi kỳ
    (D(2025, 10, 18), "UNC6", "THANH TOAN THUONG DOANH SO QUI 3-171025-19:21:39 168514--", "1121", 20_000_000),
    (D(2025, 12, 31), "UNC7", "THANH TOAN LUONG T12-311225-19:01:30 899280-NGUYEN NGOC TUYEN-NGUYEN NGOC TUYEN", "1121", 4_500_000),
    (D(2026, 1, 3), "UNC8", "THANH TOAN LUONG T12 2025--", "1121", 5_000_000),                                    # trả T12/2025 vào tháng 1/2026
    (D(2025, 8, 4), "TM1", "TRA LUONG TIEN MAT T7", "1111", 9_000_000),                                          # tiền mặt -> bỏ qua
]


def tao_file(dong=DONG, tieu_de=True):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["SỔ CHI TIẾT CÁC TÀI KHOẢN"])
    ws.append(["Tài khoản: 3341; Năm 2025"])
    if tieu_de:
        ws.append(HEADER)
    for ngay, so, dg, du, tien in dong:
        ws.append([ngay, ngay, so, dg, "3341", du, tien, 0, 0, -tien, None, None])
    ws.append([None, None, "", "Cộng", "3341", None, sum(d[4] for d in dong), 0])
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


# ===== 1: đọc file: kỳ lương lấy từ diễn giải (năm gõ sai bỏ qua; quý -> tháng cuối quý; không ghi kỳ -> tháng trước + đánh dấu) =====
kq = server._luong_doc_so_ck(tao_file(), 2025)
gd = {x["so_ct"]: x for x in kq["giao_dich"]}
assert "TM1" not in gd and len(gd) == 8, "Khoản tiền mặt (TK đối ứng 111x) không tính"
assert (gd["UNC1"]["thang"], gd["UNC1"]["loai"]) == ("06", "ung"), "Ứng lương T6 chi ngày 16/6 -> kỳ T6"
assert gd["UNC2"]["thang"] == "05" and gd["UNC3"]["thang"] == "05", "Lương T5 chi vào tháng 6 -> kỳ T5"
assert gd["UNC4"]["thang"] == "07" and gd["UNC4"]["nam_ky"] == 2025, "Diễn giải ghi 'T7 2026' (gõ sai) -> vẫn kỳ T7/2025 theo ngày chi"
assert gd["UNC5"]["doan"] is True and gd["UNC5"]["thang"] == "06" and gd["UNC5"]["ten"] == "DO THAI HUNG", "Không ghi kỳ -> tháng trước ngày chi + đánh dấu"
assert gd["UNC6"]["thang"] == "09" and gd["UNC6"]["loai"] == "thuong", "Thưởng doanh số QUÝ 3 -> tháng 9"
assert gd["UNC7"]["thang"] == "12" and gd["UNC7"]["ten"] == "NGUYEN NGOC TUYEN"
assert gd["UNC8"]["thang"] == "12" and gd["UNC8"]["nam_ky"] == 2025, "Lương T12/2025 trả vào tháng 1/2026 vẫn thuộc kỳ T12/2025"
assert kq["theo_thang"] == {"05": 28_110_000, "06": 3_500_000 + 3_000_000, "07": 2_500_000, "09": 20_000_000, "12": 9_500_000}
assert kq["tong"] == sum(d[4] for d in DONG if d[3] == "1121") and any("tiền mặt" in c or "không phải chuyển khoản" in c for c in kq["canh_bao"])
assert any("THÁNG TRƯỚC" in c for c in kq["canh_bao"])
kq24 = server._luong_doc_so_ck(tao_file(), 2024)
assert kq24["theo_thang"] == {} and all(x["thang"] == "" for x in kq24["giao_dich"]) and any("năm khác" in c for c in kq24["canh_bao"])
for hong in (b"khong phai file", tao_file(tieu_de=False), tao_file(dong=[(D(2025, 1, 1), "TM", "x", "1111", 5)])):
    try:
        server._luong_doc_so_ck(hong, 2025)
        raise SystemExit("phải báo lỗi")
    except HTTPException as e:
        assert e.status_code == 400
print("PASS 1: đọc file sao kê: kỳ lương từ diễn giải, bỏ tiền mặt, năm gõ sai, quý, không ghi kỳ, lỗi rõ.")

# ===== 2: dựng bảng lương khớp ĐÚNG số chuyển khoản từng tháng (tổng chi phí cả năm để trống) =====
dong_nv = {"luong_cb": 5_310_000, "tien_com": 700_000, "muc_xang": 500_000, "pc_chuc_vu": 500_000, "muc_dt": 500_000, "trang_phuc": 400_000}
pool = lambda t: [server._luong_chuan_dong_nhap(dict(dong_nv, ma=str(i), ten=f"NV{i}", dong_bh=1 if i < 4 else 0, ghi_chu="CK")) for i in range(2, 9)]
ck = {"05": 28_110_000, "06": 36_295_000, "07": 76_022_222, "08": 29_000_000, "09": 48_900_000, "10": 24_000_000, "11": 31_100_000, "12": 44_200_000}
for full in (False, True):
    th, tom = server._luong_ke_hoach(pool, 2025, 5, 12, 0, None, 50, 0, random.Random(2), full, None, ck)
    assert sorted(th) == sorted(ck)
    for t, so in ck.items():
        assert sum(r["tt_luong"] for r in th[t]) == so, (full, t)
        assert tom["ck"][t]["khop"] and tom["ck"][t]["file"] == so
        assert all(server._luong_la_chuyen_khoan(r["ghi_chu"]) for r in th[t]), "Mọi người trong tháng có chuyển khoản đều tick CK"
    assert tom["tong_chi_phi"] == sum(r["chi_phi_luong"] for rows in th.values() for r in rows)
    if full:
        assert tom["tong_thue"] == 0 and tom["thoi_vu"] == 0
print("PASS 2: mỗi tháng TT lương chuyển khoản = đúng số trong file (cả chế độ thường và full công).")

# ===== 3: nhiều bộ số ngẫu nhiên: luôn khớp từng đồng =====
rng = random.Random(11)
for _ in range(25):
    ck_r = {"%02d" % m: rng.randrange(8_000_000, 90_000_000) for m in rng.sample(range(1, 13), rng.randint(1, 4))}
    th, tom = server._luong_ke_hoach(pool, 2025, 1, 12, 0, None, 50, 0, random.Random(rng.randint(1, 999)), rng.random() < 0.5, None, ck_r)
    assert sorted(th) == sorted(ck_r)
    for t, so in ck_r.items():
        assert sum(r["tt_luong"] for r in th[t]) == so, (t, so, sum(r["tt_luong"] for r in th[t]))
print("PASS 3: 25 bộ số ngẫu nhiên: TT lương chuyển khoản luôn khớp từng đồng.")

# ===== 4: có cả tổng chi phí lương cả năm: tháng có file theo file, các tháng còn lại chia phần còn lại -> tổng ĐÚNG mục tiêu =====
ck2 = {"05": 28_110_000, "06": 36_295_000}
th, tom = server._luong_ke_hoach(pool, 2025, 5, 8, 200_000_000, None, 50, 0, random.Random(3), False, None, ck2)
assert sorted(th) == ["05", "06", "07", "08"]
assert sum(r["tt_luong"] for r in th["05"]) == 28_110_000 and sum(r["tt_luong"] for r in th["06"]) == 36_295_000
assert sum(r["chi_phi_luong"] for rows in th.values() for r in rows) == 200_000_000 == tom["tong_chi_phi"]
# tháng chỉ nhập file (không tổng): các tháng không có chuyển khoản bị bỏ qua + báo
th, tom = server._luong_ke_hoach(pool, 2025, 5, 8, 0, None, 50, 0, random.Random(3), False, None, ck2)
assert sorted(th) == ["05", "06"] and any("bỏ qua" in c for c in tom["canh_bao"])
# tổng nhập nhỏ hơn phần đã cần cho tháng có chuyển khoản -> báo lỗi rõ
try:
    server._luong_ke_hoach(pool, 2025, 5, 8, 50_000_000, None, 50, 0, random.Random(3), False, None, ck2)
    raise SystemExit("phải báo lỗi")
except HTTPException as e:
    assert e.status_code == 400 and "đã đạt/vượt" in e.detail
# mọi tháng đều có file, tổng nhập khác -> file được ưu tiên + cảnh báo
th, tom = server._luong_ke_hoach(pool, 2025, 5, 6, 999_000_000, None, 50, 0, random.Random(3), False, None, ck2)
assert any("khác chi phí lương suy ra từ file" in c for c in tom["canh_bao"])
# không có file và không có tổng -> lỗi như cũ
try:
    server._luong_ke_hoach(pool, 2025, 5, 6, 0, None, 50, 0, random.Random(3))
    raise SystemExit("phải báo lỗi")
except HTTPException as e:
    assert e.status_code == 400 and "lớn hơn 0" in e.detail
print("PASS 4: có tổng năm: tháng có file theo file, tháng còn lại chia phần còn lại (tổng đúng); các nhánh lỗi/cảnh báo.")

# ===== 5: API: /nhap-chuyen-khoan (upload) + /ke-hoach nhận ck_theo_thang =====
class Up:
    def __init__(self, b): self._b = b
    async def read(self): return self._b

class ReqForm:
    def __init__(self, f): self._f = f
    async def form(self): return self._f

class Req:
    def __init__(self, b): self._b = b
    async def json(self): return self._b

kq = asyncio.run(server.bang_luong_nhap_chuyen_khoan(1, ReqForm({"file": Up(tao_file()), "nam": "2025"})))
assert kq["theo_thang"]["05"] == 28_110_000
try:
    asyncio.run(server.bang_luong_nhap_chuyen_khoan(1, ReqForm({})))
    raise SystemExit("phải báo lỗi")
except HTTPException as e:
    assert e.status_code == 400
hd = ["Mã NV", "Họ và tên", "Chức vụ", "Lương Cơ bản", "PC Tiền cơm", "PC Xăng xe", "PC Chức vụ", "PC Điện thoại", "PC Trang phục", "Đóng BHXH"]
server.nhap_lieu_get = lambda cid, loai="nv": {"header": hd, "rows": [[str(i), f"NV{i}", "KD", 5310000, 700000, 500000, 500000, 500000, 400000, "x"] for i in range(2, 9)]}
out = asyncio.run(server.bang_luong_ke_hoach(1, Req({"nam": 2025, "tu_thang": 5, "den_thang": 6, "muc_tieu": "", "ck_theo_thang": {"05": 28_110_000, "06": "36295000"}, "seed": 4})))
assert sum(r["tt_luong"] for r in out["thang"]["05"]) == 28_110_000 and sum(r["tt_luong"] for r in out["thang"]["06"]) == 36_295_000
assert out["tom_tat"]["ck"]["06"]["khop"] is True
print("PASS 5: API đọc file + lập kế hoạch theo ck_theo_thang.")

print("\nALL DONE")
