import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Điều 33 khoản 5 Luật BHXH 2024: người lao động KHÔNG LƯƠNG từ 14 ngày làm việc trở lên trong tháng thì tháng đó không đóng BHXH.
# Tiêu chí là số ngày KHÔNG LƯƠNG (công chuẩn − ngày làm), không phải "làm dưới 14 ngày".
f = server._luong_mien_bh_ngay
assert f(26, 12) and not f(26, 13), "công chuẩn 26: làm <= 12 ngày mới được miễn; làm 13 (không lương 13) vẫn đóng"
assert f(24, 10) and not f(24, 11), "công chuẩn 24: làm <= 10 ngày"
assert f(22, 8) and not f(22, 9)
assert not f(12, 0) and not f(13, 0) and f(14, 0), "tháng có ít hơn 14 ngày công chuẩn thì không thể miễn"
assert server._luong_ngay_lam_toi_da_mien_bh(26) == 12 and server._luong_ngay_lam_toi_da_mien_bh(24) == 10

TS = server._luong_chuan_tham_so(None, 2026)
base = {"ma": "1", "ten": "A", "chuc_vu": "KD", "luong_cb": 5_310_000, "tien_com": 700_000, "muc_xang": 500_000, "muc_dt": 0, "trang_phuc": 0, "ngay_cong": 26}
t = lambda **kw: server._luong_tinh_dong(dict(base, **kw), TS, "05")
r12, r13 = t(dong_bh=0, ngay_lam=12), t(dong_bh=0, ngay_lam=13)
assert r12["thoi_vu"] is True and r12["canh_bao_bh"] is False and r12["bhxh_nld"] == 0
assert r13["thoi_vu"] is False and r13["canh_bao_bh"] is True, "làm 13/26 ngày mà không đóng BHXH -> cảnh báo phải đóng"
assert t(dong_bh=1, ngay_lam=5)["thoi_vu"] is False, "đã tick đóng BHXH thì không bao giờ là 'thời vụ'"
r24a, r24b = t(dong_bh=0, ngay_lam=10, ngay_cong=24), t(dong_bh=0, ngay_lam=11, ngay_cong=24)
assert r24a["thoi_vu"] is True and r24b["thoi_vu"] is False and r24b["canh_bao_bh"] is True
# thuế 10% chỉ áp dụng cho người được miễn BHXH theo quy tắc trên
assert r12["thue_tncn"] == (server._luong_lam_tron(r12["tn_chiu_thue"] * 0.1) if r12["tn_chiu_thue"] >= TS["nguong_khau_tru_10"] else 0)
assert r13["giam_tru_ban_than"] > 0, "làm 13/26 ngày không BHXH: không bị coi là thời vụ nên vẫn được giảm trừ gia cảnh"

# kế hoạch chi phí lương cả năm (không tick Làm full ngày công): người làm ít ngày không BHXH phải không lương >= 14 ngày làm việc ở từng tháng
pool = [server._luong_chuan_dong_nhap(dict(base, ma=str(i), ten="NV%d" % i, dong_bh=1 if i <= 3 else 0, ngay_cong=0)) for i in range(1, 8)]
for muc_tieu in (9_000_000, 16_000_000, 31_000_000):
    th, tom = server._luong_ke_hoach(pool, 2026, 1, 12, muc_tieu, None, rng=random.Random(7))
    for t_, rows in th.items():
        for r in rows:
            if r["dong_bh"] == 0:
                assert r["ngay_cong_hd"] - r["ngay_lam_hd"] >= 14, (t_, r["ngay_cong_hd"], r["ngay_lam_hd"])
                assert r["ngay_lam_hd"] <= r["ngay_cong_hd"] - 14
            else:
                assert r["thoi_vu"] is False
print("PASS")
