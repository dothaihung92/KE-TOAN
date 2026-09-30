import os
import sys
import asyncio
import random

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Yêu cầu: trong "Chi phí lương cả năm" thêm tick "Làm full ngày công" — mọi người đi làm ĐỦ CÔNG (không có người < 14 ngày, không khấu trừ 10% thuế),
# thu nhập chịu thuế mỗi người cả năm dưới 132tr (11tr x 12, giảm trừ bản thân) để không phát sinh thuế TNCN lũy tiến; phần thiếu để đạt mục tiêu thì
# ĐẨY các phụ cấp KHÔNG chịu thuế (cơm/trang phục/điện thoại) lên trước, rồi mới thưởng bán hàng + tăng ca.

TS = server._luong_chuan_tham_so(None, 2025)
dong = {"luong_cb": 5_310_000, "tien_com": 700_000, "muc_xang": 500_000, "pc_chuc_vu": 500_000, "muc_dt": 500_000, "trang_phuc": 400_000}
TRAN = {"tien_com": 730_000, "trang_phuc": 416_000, "muc_dt": 1_000_000}
pool = [server._luong_chuan_dong_nhap(dict(dong, ma=str(i), ten=f"NV{i}", dong_bh=0)) for i in range(2, 9)]


def chay(muc, tu=9, den=12, p=None, nam=2025, seed=1, **kw):
    return server._luong_ke_hoach(p or pool, nam, tu, den, muc, None, 50, 0, random.Random(seed), True, **kw)


def kiem(th, tom, muc):
    assert sum(r["chi_phi_luong"] for rows in th.values() for r in rows) == muc, "Tổng chi phí lương khớp ĐÚNG mục tiêu"
    assert tom["tong_chi_phi"] == muc
    return sum(r["chi_phi_luong"] for rows in th.values() for r in rows)


# ===== 1: ví dụ người dùng: 9–12, 50tr: 1 người làm đủ công, không thuế, không khấu trừ 10%, dưới 132tr =====
th, tom = chay(50_000_000)
kiem(th, tom, 50_000_000)
assert tom["full_cong"] is True and tom["thoi_vu"] == 0 and tom["so_nguoi"] == 1 and tom["tong_thue"] == 0
for t, rows in th.items():
    for r in rows:
        assert r["ngay_lam"] == "" and r["ngay_lam_hd"] == r["ngay_cong_hd"], "Đủ công (không có người làm dưới 14 ngày)"
        assert not r["thoi_vu"] and r["thue_tncn"] == 0 and r["thue_tru_luong"] == 0
        assert r["tn_chiu_thue"] <= 11_000_000, "Mỗi tháng thu nhập chịu thuế <= giảm trừ bản thân"
assert tom["chiu_thue_nam_max"] <= tom["nguong_chiu_thue"] == 4 * 11_000_000
print("PASS 1: full công: tổng đúng mục tiêu, đủ công, không thuế 10%, thu nhập chịu thuế <= giảm trừ bản thân.")

# ===== 2: phụ cấp KHÔNG chịu thuế được ĐẨY lên trước (tới trần), thưởng + tăng ca chỉ bù phần còn thiếu =====
th, tom = chay(50_000_000)
for rows in th.values():
    r = rows[0]
    assert (r["tien_com"], r["trang_phuc"], r["muc_dt"]) == (730_000, 416_000, 1_000_000), "Đã đẩy các phụ cấp không thuế lên tới trần"
    assert r["muc_xang"] == 500_000 and r["pc_chuc_vu"] == 500_000 and r["luong_cb"] == 5_310_000, "Lương CB + phụ cấp chịu thuế giữ nguyên"
# mục tiêu nhỏ (chỉ cần đẩy phụ cấp, chưa phải thưởng/tăng ca): 1 người 7.91tr + tối đa 546k đẩy lên
th, tom = chay(8_300_000 * 4)
kiem(th, tom, 8_300_000 * 4)
assert tom["tong_thuong_bh"] == 0 and tom["tong_tang_ca"] == 0, "Phụ cấp không chịu thuế đẩy đủ rồi nên KHÔNG cần thưởng/tăng ca"
r = th["09"][0]
assert r["tien_com"] + r["trang_phuc"] + r["muc_dt"] - (700_000 + 400_000 + 500_000) == 8_300_000 - 7_910_000
print("PASS 2: đẩy phụ cấp không chịu thuế trước; thưởng/tăng ca chỉ khi phụ cấp đã tới trần.")

# ===== 3: nhiều mục tiêu ngẫu nhiên: luôn khớp tổng, không thuế, mỗi người <= ngưỡng năm, phụ cấp <= trần =====
rng = random.Random(7)
for _ in range(40):
    tu = rng.randint(1, 10)
    den = rng.randint(tu, min(12, tu + 3))
    muc = rng.randrange(20_000_000, 250_000_000, 1_000)
    th, tom = chay(muc, tu, den, seed=rng.randint(1, 999))
    if tom["canh_bao"] and any("chưa đủ sức chứa" in c for c in tom["canh_bao"]):
        continue
    kiem(th, tom, muc)
    assert tom["tong_thue"] == 0 and tom["chiu_thue_nam_max"] <= tom["nguong_chiu_thue"]
    for rows in th.values():
        for r in rows:
            assert r["tien_com"] <= 730_000 and r["trang_phuc"] <= 416_000 and r["muc_dt"] <= 1_000_000 and not r["thoi_vu"]
print("PASS 3: 40 mục tiêu ngẫu nhiên: khớp tổng, không thuế, dưới ngưỡng, phụ cấp không vượt trần.")

# ===== 4: người được đóng BHXH được chọn trước; người không tick vẫn có thể làm đủ công (kèm cảnh báo BHXH) =====
p4 = [server._luong_chuan_dong_nhap(dict(dong, ma=str(i), ten=f"NV{i}", dong_bh=1 if i == 5 else 0)) for i in range(2, 9)]
th, tom = chay(50_000_000, p=p4)
assert th["09"][0]["ma"] == "5" and th["09"][0]["dong_bh"] == 1
assert not any("CHƯA tick" in c for c in tom["canh_bao"]), "Chỉ người có BHXH làm -> không cảnh báo"
th, tom = chay(50_000_000)                                  # không ai được tick
assert sum("CHƯA tick 'Đóng BHXH'" in c for c in tom["canh_bao"]) == 1, "Cảnh báo BHXH chỉ 1 lần (không lặp mỗi tháng)"
print("PASS 4: ưu tiên người có BHXH; cảnh báo 1 lần khi người làm đủ công chưa tick Đóng BHXH.")

# ===== 5: mục tiêu quá lớn (hết sức chứa) -> vẫn khớp tổng nhưng cảnh báo vượt ngưỡng =====
th, tom = chay(900_000_000)
kiem(th, tom, 900_000_000)
assert any("chưa đủ sức chứa" in c and "vượt ngưỡng chịu thuế" in c for c in tom["canh_bao"]) and tom["tong_thue"] > 0
assert tom["chiu_thue_nam_max"] > tom["nguong_chiu_thue"]
print("PASS 5: hết sức chứa -> vẫn khớp tổng + cảnh báo rõ vượt ngưỡng.")

# ===== 6: trần phụ cấp tùy chỉnh (0 = không đẩy phụ cấp đó); mục tiêu < lương 1 người -> lỗi rõ =====
th, tom = chay(50_000_000, tran_pc={"tien_com": "0", "trang_phuc": "", "muc_dt": "600.000".replace(".", "")})
r = th["09"][0]
assert r["tien_com"] == 700_000, "Trần 0 -> giữ nguyên mức trong Danh Sách Nhân Viên (không bị hạ xuống)"
assert r["trang_phuc"] == 416_000 and r["muc_dt"] == 600_000
try:
    chay(2_000_000, 9, 9)
    raise SystemExit("phải báo lỗi")
except server.HTTPException as e:
    assert e.status_code == 400 and "nhỏ hơn" in e.detail
print("PASS 6: trần phụ cấp tùy chỉnh; mục tiêu quá nhỏ báo lỗi rõ.")

# ===== 7: năm 2026 (giảm trừ bản thân 15,5tr): ngưỡng theo năm + không thuế =====
th, tom = chay(80_000_000, 9, 12, nam=2026)
kiem(th, tom, 80_000_000)
assert tom["nguong_chiu_thue"] == 4 * 15_500_000 and tom["tong_thue"] == 0
print("PASS 7: năm 2026 dùng giảm trừ bản thân mới cho ngưỡng.")

# ===== 8: API nhận full_cong + tran_pc; không tick thì cách cũ (có người < 14 ngày) =====
class Req:
    def __init__(self, b): self._b = b
    async def json(self): return self._b

hd = ["Mã NV", "Họ và tên", "Chức vụ", "Lương Cơ bản", "PC Tiền cơm", "PC Xăng xe", "PC Chức vụ", "PC Điện thoại", "PC Trang phục", "Đóng BHXH"]
rows_nv = [[str(i), f"NV{i}", "KD", 5310000, 700000, 500000, 500000, 500000, 400000, ""] for i in range(2, 9)]
server.nhap_lieu_get = lambda cid, loai="nv": {"header": hd, "rows": rows_nv}
kq = asyncio.run(server.bang_luong_ke_hoach(1, Req({"nam": 2025, "tu_thang": 9, "den_thang": 12, "muc_tieu": 50_000_000, "full_cong": True,
                                                     "tran_pc": {"tien_com": 730000, "trang_phuc": 416000, "muc_dt": 1000000}, "seed": 3})))
assert kq["tom_tat"]["full_cong"] and kq["tom_tat"]["thoi_vu"] == 0 and kq["tom_tat"]["tong_thue"] == 0
kq2 = asyncio.run(server.bang_luong_ke_hoach(1, Req({"nam": 2025, "tu_thang": 9, "den_thang": 12, "muc_tieu": 50_000_000, "seed": 3})))
assert not kq2["tom_tat"]["full_cong"] and kq2["tom_tat"]["thoi_vu"] > 0, "Không tick: cách cũ (người làm dưới 14 ngày)"
print("PASS 8: API nhận full_cong/tran_pc; không tick vẫn theo cách cũ.")

print("\nALL DONE")
