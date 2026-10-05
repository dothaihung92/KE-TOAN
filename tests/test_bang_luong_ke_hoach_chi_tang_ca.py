import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# "Bù bằng tăng ca" 100% = CHỈ bù bằng tăng ca (tối đa 40 giờ/người/tháng), KHÔNG có thưởng bán hàng; không đủ chỗ tăng ca thì báo còn thiếu (không dồn vào thưởng).
dong = {"luong_cb": 5_310_000, "tien_com": 700_000, "muc_xang": 500_000, "muc_dt": 500_000, "trang_phuc": 400_000}
pool = [server._luong_chuan_dong_nhap(dict(dong, ma=str(i), ten=f"NV{i}", dong_bh=1)) for i in range(1, 6)]
ts = server._luong_chuan_tham_so(None, 2025)

def chay(muc, ty, full=False, seed=3):
    return server._luong_ke_hoach(pool, 2025, 9, 12, muc, None, ty, 0, random.Random(seed), full)

# 4 tháng, 5 người đủ công; mục tiêu cao hơn lương đủ công một chút -> phần thiếu bù bằng tăng ca
f = sum(server._luong_tinh_dong(dict(r, ngay_cong=0, ngay_lam="", dong_bh=1), ts, "09")["chi_phi_luong"] for r in pool)
muc = int(f * 4 + 6_000_000)
th, tom = chay(muc, 100)
rows = [r for rs in th.values() for r in rs]
assert sum(r["chi_phi_luong"] for r in rows) == muc, "tổng khớp đúng mục tiêu"
assert all(r["thuong_bh"] == 0 for r in rows), "100% tăng ca: không có thưởng bán hàng"
assert sum(r["tang_ca"] for r in rows) > 0
for r in rows:
    gio_don = r["luong_cb"] / r["ngay_cong_hd"] / 8.0 * ts["he_so_tang_ca"]
    assert r["tang_ca"] <= int(40 * gio_don) + 1, "tăng ca không quá 40 giờ/người/tháng"
# 50%: vẫn có cả thưởng bán hàng như trước
th50, _ = chay(muc, 50)
assert any(r["thuong_bh"] > 0 for rs in th50.values() for r in rs)
# mục tiêu quá lớn so với sức chứa tăng ca: KHÔNG dồn vào thưởng; báo còn thiếu
th2, tom2 = chay(int(f * 4 + 60_000_000), 100)
assert all(r["thuong_bh"] == 0 for rs in th2.values() for r in rs)
assert sum(r["chi_phi_luong"] for rs in th2.values() for r in rs) < int(f * 4 + 60_000_000)
assert any("tăng ca tối đa 40 giờ" in c and "THIẾU" in c for c in tom2["canh_bao"]), tom2["canh_bao"]
# full công + 100%: cũng không có thưởng
th3, tom3 = chay(int(f * 4 + 6_000_000), 100, full=True)
assert all(r["thuong_bh"] == 0 for rs in th3.values() for r in rs)
print("PASS")
