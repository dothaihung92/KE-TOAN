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


def ck_tt(rows):
    """Tổng TT lương của NHÓM CHUYỂN KHOẢN (người tick CK)."""
    return sum(r["tt_luong"] for r in rows if server._luong_la_chuyen_khoan(r["ghi_chu"]))


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


# ===== 1: đọc file: tháng của mỗi khoản = THÁNG NGÀY HẠCH TOÁN (không đọc kỳ lương trong diễn giải, kể cả khi diễn giải ghi kỳ khác/sai/thiếu) =====
kq = server._luong_doc_so_ck(tao_file(), 2025)
gd = {x["so_ct"]: x for x in kq["giao_dich"]}
assert "TM1" not in gd and len(gd) == 8, "Khoản tiền mặt (TK đối ứng 111x) không tính"
assert gd["UNC1"]["thang"] == "06" and gd["UNC1"]["loai"] == "ung"
assert gd["UNC2"]["thang"] == "06" and gd["UNC3"]["thang"] == "06", "'LUONG T5' chi ngày 17/6 -> tháng 6 (theo ngày hạch toán, không theo diễn giải)"
assert gd["UNC4"]["thang"] == "07" and gd["UNC5"]["thang"] == "07", "Diễn giải 'T7 2026' hoặc không ghi kỳ đều theo ngày hạch toán"
assert gd["UNC6"]["thang"] == "10" and gd["UNC6"]["loai"] == "thuong", "'QUI 3' chi ngày 18/10 -> tháng 10"
assert gd["UNC7"]["thang"] == "12" and gd["UNC7"]["ten"] == "NGUYEN NGOC TUYEN"
assert gd["UNC8"]["thang"] == "" and gd["UNC8"]["nam_ky"] == 2026, "Ngày hạch toán 3/1/2026 -> ngoài năm 2025, không tính"
assert not any("doan" in x for x in kq["giao_dich"])
assert kq["theo_thang"] == {"06": 3_500_000 + 22_894_000 + 5_216_000, "07": 2_500_000 + 3_000_000, "10": 20_000_000, "12": 4_500_000}
assert kq["tong"] == sum(d[4] for d in DONG if d[3] == "1121") and any("không phải chuyển khoản" in c for c in kq["canh_bao"])
assert any("ngoài năm 2025" in c for c in kq["canh_bao"])
kq26 = server._luong_doc_so_ck(tao_file(), 2026)
assert kq26["theo_thang"] == {"01": 5_000_000}
for hong in (b"khong phai file", tao_file(tieu_de=False), tao_file(dong=[(D(2025, 1, 1), "TM", "x", "1111", 5)])):
    try:
        server._luong_doc_so_ck(hong, 2025)
        raise SystemExit("phải báo lỗi")
    except HTTPException as e:
        assert e.status_code == 400
print("PASS 1: đọc file sao kê: tháng theo ngày hạch toán, bỏ tiền mặt, ngoài năm, lỗi rõ.")

# ===== 2: dựng bảng lương khớp ĐÚNG số chuyển khoản từng tháng (tổng chi phí cả năm để trống) =====
dong_nv = {"luong_cb": 5_310_000, "tien_com": 700_000, "muc_xang": 500_000, "pc_chuc_vu": 500_000, "muc_dt": 500_000, "trang_phuc": 400_000}
pool = lambda t: [server._luong_chuan_dong_nhap(dict(dong_nv, ma=str(i), ten=f"NV{i}", dong_bh=1 if i < 4 else 0, ghi_chu="CK")) for i in range(2, 9)]
ck = {"05": 28_110_000, "06": 36_295_000, "07": 76_022_222, "08": 29_000_000, "09": 48_900_000, "10": 24_000_000, "11": 31_100_000, "12": 44_200_000}
for full in (False, True):
    th, tom = server._luong_ke_hoach(pool, 2025, 5, 12, 0, None, 50, 0, random.Random(2), full, None, ck)
    assert sorted(th) == sorted(ck)
    for t, so in ck.items():
        assert ck_tt(th[t]) == so, (full, t)
        assert tom["ck"][t]["khop"] and tom["ck"][t]["file"] == so and tom["ck"][t]["tt_luong"] == so
        assert len({(r["ma"]) for r in th[t]}) == len(th[t]) == 7, "Bảng lương có đủ 7 lao động: người chuyển khoản + người trả tiền mặt"
        tm = [r for r in th[t] if not server._luong_la_chuyen_khoan(r["ghi_chu"])]
        assert tom["ck"][t]["so_nguoi_ck"] == 7 - len(tm) and tom["ck"][t]["so_nguoi_tm"] == len(tm)
        assert all(r["ngay_lam_hd"] == r["ngay_cong_hd"] and r["thuong_bh"] == 0 and r["tang_ca"] == 0 for r in tm), "Người trả tiền mặt: lương đủ công theo danh sách"
        assert abs(tom["ck"][t]["tt_tien_mat"] - sum(r["tt_luong"] for r in tm)) < 1
    assert tom["tong_chi_phi"] == sum(r["chi_phi_luong"] for rows in th.values() for r in rows)
    assert tom["tong_chi_phi"] > sum(ck.values()), "Tổng bảng lương LỚN HƠN số chuyển khoản (có thêm lao động trả tiền mặt + BH)"
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
        assert ck_tt(th[t]) == so, (t, so, ck_tt(th[t]))
print("PASS 3: 25 bộ số ngẫu nhiên: TT lương chuyển khoản luôn khớp từng đồng.")

# ===== 4: có cả tổng chi phí lương cả năm: tháng có file theo file, các tháng còn lại chia phần còn lại -> tổng ĐÚNG mục tiêu =====
ck2 = {"05": 28_110_000, "06": 36_295_000}
th, tom = server._luong_ke_hoach(pool, 2025, 5, 8, 200_000_000, None, 50, 0, random.Random(3), False, None, ck2)
assert sorted(th) == ["05", "06", "07", "08"]
assert ck_tt(th["05"]) == 28_110_000 and ck_tt(th["06"]) == 36_295_000
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
assert any("khác chi phí lương suy ra từ file" in c for c in tom["canh_bao"])      # không full công: giữ nguyên hành vi cũ

# ===== 4b: FULL CÔNG + mọi tháng đều có file + tổng nhập LỚN HƠN số suy ra từ file: phần chênh đẩy vào nhóm lao động TIỀN MẶT, TT lương CK vẫn khớp,
# không phát sinh thuế, tổng ĐÚNG mục tiêu; vượt sức chứa thì báo rõ số còn thiếu (trước đây im lặng chỉ ra số theo file) =====
tp = {"tien_com": 730000, "trang_phuc": 416000, "muc_dt": 6000000, "muc_xang": 8000000}
for muc in (130_000_000, 150_000_000):
    th, tom = server._luong_ke_hoach(pool, 2025, 5, 6, muc, None, 50, 0, random.Random(3), True, tp, ck2)
    assert tom["tong_chi_phi"] == muc == sum(r["chi_phi_luong"] for rows in th.values() for r in rows), (muc, tom["tong_chi_phi"])
    assert tom["tong_thue"] == 0 and not any("chỉ dựng được" in c for c in tom["canh_bao"])
    assert ck_tt(th["05"]) == 28_110_000 and ck_tt(th["06"]) == 36_295_000 and all(v["khop"] for v in tom["ck"].values())
    assert tom["chiu_thue_nam_max"] <= tom["nguong_chiu_thue"], "mỗi người vẫn dưới ngưỡng giảm trừ bản thân"
th, tom = server._luong_ke_hoach(pool, 2025, 5, 6, 999_000_000, None, 50, 0, random.Random(3), True, tp, ck2)
assert tom["tong_chi_phi"] < 999_000_000 and tom["tong_thue"] == 0 and all(v["khop"] for v in tom["ck"].values())
assert any("chỉ dựng được" in c and "còn thiếu" in c for c in tom["canh_bao"]), "báo rõ vì sao không đạt mục tiêu"
print("PASS 4b: full công + file chuyển khoản phủ mọi tháng: phần chênh so với tổng nhập được đẩy vào lao động tiền mặt, vượt sức chứa thì báo số thiếu.")

# ===== 4c: ước tính cần thêm bao nhiêu người để đạt tổng nhập; thêm đúng số người đó thì đạt mục tiêu =====
ck6 = {"01": 22_500_000, "02": 38_500_000, "03": 34_000_000, "04": 25_000_000, "05": 49_876_000, "06": 29_500_000}
th, tom = server._luong_ke_hoach(pool, 2026, 1, 6, 1_250_000_000, None, 60, 0, random.Random(3), True, tp, ck6)
ct = tom["can_them_nguoi"]
assert ct and ct["so_nguoi"] >= 1 and ct["thieu"] == 1_250_000_000 - tom["tong_chi_phi"] and any(c.startswith("➕ Ước tính cần thêm khoảng %d người" % ct["so_nguoi"]) for c in tom["canh_bao"])
pool_them = lambda t: pool(t) + [server._luong_chuan_dong_nhap(dict(dong_nv, ma=str(100 + i), ten=f"X{i}", dong_bh=1, ghi_chu="CK")) for i in range(ct["so_nguoi"])]
th2, tom2 = server._luong_ke_hoach(pool_them, 2026, 1, 6, 1_250_000_000, None, 60, 0, random.Random(3), True, tp, ck6)
assert tom2["tong_chi_phi"] == 1_250_000_000 and tom2["can_them_nguoi"] is None and tom2["tong_thue"] == 0
print("PASS 4c: ước tính số người cần thêm; thêm đúng số đó thì đạt đúng mục tiêu, không phát sinh thuế.")
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
assert kq["theo_thang"]["06"] == 31_610_000
try:
    asyncio.run(server.bang_luong_nhap_chuyen_khoan(1, ReqForm({})))
    raise SystemExit("phải báo lỗi")
except HTTPException as e:
    assert e.status_code == 400
hd = ["Mã NV", "Họ và tên", "Chức vụ", "Lương Cơ bản", "PC Tiền cơm", "PC Xăng xe", "PC Chức vụ", "PC Điện thoại", "PC Trang phục", "Đóng BHXH"]
server.nhap_lieu_get = lambda cid, loai="nv": {"header": hd, "rows": [[str(i), f"NV{i}", "KD", 5310000, 700000, 500000, 500000, 500000, 400000, "x"] for i in range(2, 9)]}
out = asyncio.run(server.bang_luong_ke_hoach(1, Req({"nam": 2025, "tu_thang": 5, "den_thang": 6, "muc_tieu": "", "ck_theo_thang": {"05": 28_110_000, "06": "36295000"}, "seed": 4})))
assert ck_tt(out["thang"]["05"]) == 28_110_000 and ck_tt(out["thang"]["06"]) == 36_295_000
assert out["tom_tat"]["ck"]["06"]["khop"] is True
print("PASS 5: API đọc file + lập kế hoạch theo ck_theo_thang.")

# ===== 6: CHIA RA NHIỀU NGƯỜI: mức tối đa mỗi người nhỏ hơn -> số người chuyển khoản không giảm; vượt mức thì có cảnh báo =====
ck6 = {"06": 40_110_000}
so_nguoi = []
for toi_da in (20_000_000, 12_000_000, 8_000_000):
    th, tom = server._luong_ke_hoach(pool, 2025, 6, 6, 0, None, 50, 0, random.Random(4), True, None, ck6, toi_da)
    so_nguoi.append(tom["ck"]["06"]["so_nguoi_ck"])
    assert ck_tt(th["06"]) == 40_110_000 and tom["ck"]["06"]["ck_cao_nhat"] == max(r["tt_luong"] for r in th["06"] if server._luong_la_chuyen_khoan(r["ghi_chu"]))
    if tom["ck"]["06"]["ck_cao_nhat"] > toi_da:
        assert any("trên mức tối đa" in c for c in tom["canh_bao"]), "Có người vượt mức tối đa -> phải cảnh báo"
assert so_nguoi == sorted(so_nguoi) and so_nguoi[-1] >= 5, so_nguoi
print("PASS 6: chuyển khoản chia ra nhiều người theo mức tối đa mỗi người (số người tăng khi mức tối đa giảm); vượt mức thì cảnh báo.")
th, tom = server._luong_ke_hoach(pool, 2025, 6, 6, 0, None, 50, 0, random.Random(4), True, None, {"06": 90_000_000}, 12_000_000)
assert ck_tt(th["06"]) == 90_000_000 and any("mức tối đa" in c for c in tom["canh_bao"]), "Quá lớn so với số người -> vẫn khớp + cảnh báo"
print("PASS 6b: số chuyển khoản quá lớn so với số người: vẫn khớp + cảnh báo mức tối đa.")

# ===== 7: hạch toán MISA có FILE chuyển khoản: KHÔNG hạch toán khoản chuyển khoản (đã hạch toán NH từ trước), chỉ hạch toán phần tiền mặt còn lại (Có 1111) =====
rows6 = server._luong_ke_hoach(pool, 2025, 6, 6, 0, None, 50, 0, random.Random(4), True, None, ck6, 12_000_000)[0]["06"]
g = server._luong_misa_tong(rows6)
for tach in (True, False):
    ds = server._luong_misa_chung_tu(2025, {"06": rows6}, {"tach_ck": tach, "ck_file": {"06": 40_110_000}}, 1)
    tt = [d for c in ds for d in c["dong"] if d["dien_giai"].startswith("TT lương")]
    assert not any(d["co"].startswith("112") or d["loai"] == "nh" for c in ds for d in c["dong"]), "Không có dòng chuyển khoản (Có 112x)"
    assert len(tt) == 1 and tt[0]["co"] == "1111" and tt[0]["so_tien"] == g["tt_luong"] - 40_110_000 > 0, tach
# số CK theo file lớn hơn tổng thực lãnh -> không còn dòng thanh toán nào (không âm)
ds = server._luong_misa_chung_tu(2025, {"06": rows6}, {"ck_file": {"6": 999_999_999}}, 1)
assert not any(d["dien_giai"].startswith("TT lương") for c in ds for d in c["dong"])
# file chỉ có tháng khác -> tháng này theo hành vi cũ (không có file, bỏ qua tick -> TT lương 1111 tất cả)
ds = server._luong_misa_chung_tu(2025, {"06": rows6}, {"tach_ck": False, "ck_file": {"07": 5}}, 1)
tt = [d for c in ds for d in c["dong"] if d["dien_giai"].startswith("TT lương")]
assert len(tt) == 1 and tt[0]["so_tien"] == g["tt_luong"]
# không có file: hành vi cũ (tick CK -> chỉ tiền mặt của người không tick)
ds = server._luong_misa_chung_tu(2025, {"06": rows6}, {"tach_ck": True}, 1)
assert not any(d["co"].startswith("112") for c in ds for d in c["dong"])
print("PASS 7: hạch toán MISA theo file: không hạch toán khoản chuyển khoản, chỉ hạch toán phần tiền mặt (Có 1111).")

print("\nALL DONE")
