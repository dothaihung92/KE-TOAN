import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server
from fastapi import HTTPException

# "Chi phí lương cả năm" thêm ô "Tổng thu nhập chịu thuế": cuối năm RA ĐÚNG CẢ HAI số (tổng chi phí lương và tổng thu nhập chịu thuế). Dữ liệu giả.
H = server.NV_HEADERS
def R(**k):
    r = [''] * len(H)
    for a, b in k.items(): r[H.index(a)] = b
    return r
def nv(ma, ten):
    return R(**{'Mã NV': ma, 'Họ và tên': ten, 'Tháng/Năm vào làm': '01/01/2026', 'Đóng BHXH': 'x', 'Chức vụ': 'NV', 'Lương Cơ bản': 6_000_000,
                'PC Tiền cơm': 730000, 'PC Xăng xe': 500000, 'PC Điện thoại': 500000, 'PC Trang phục': 300000})
rows = [nv(str(i), f'NV {i}') for i in range(1, 7)]
pool = lambda t: [r for r in server._luong_dong_tu_nhan_vien(H, rows, 0, 2026, int(t), None) if not r.get('part_time')]
def chay(muc, ct, full=True, seed=3):
    return server._luong_ke_hoach(pool, 2026, 1, 12, muc, None, 50.0, 0, random.Random(seed), full, None, None, 12000000, du_bhxh=True, muc_tieu_ct=ct)

th0, tom0 = chay(600_000_000, 0)
ct0, cp0 = tom0['tong_chiu_thue'], tom0['tong_chi_phi']
assert cp0 == 600_000_000, cp0
# 1) muốn TĂNG thu nhập chịu thuế
for ct in (ct0 + 5_000_000, ct0 + 20_000_000):
    th, tom = chay(600_000_000, ct)
    cp = sum(r['chi_phi_luong'] for rs in th.values() for r in rs)
    cht = round(sum(r['tn_chiu_thue'] for rs in th.values() for r in rs))
    assert cp == 600_000_000 and cht == ct and tom['khop_chiu_thue'], (ct, cp, cht, tom['canh_bao'])
    assert tom['tong_chiu_thue'] == ct and tom['tong_chi_phi'] == 600_000_000
    assert tom['tong_thue'] == 0, tom['tong_thue']              # còn trong mức giảm trừ nên không phát sinh thuế
# 2) muốn GIẢM thu nhập chịu thuế (chuyển sang phụ cấp tới mức trần)
if ct0 > 3_000_000:
    th, tom = chay(600_000_000, ct0 - 3_000_000)
    cp = sum(r['chi_phi_luong'] for rs in th.values() for r in rs)
    cht = round(sum(r['tn_chiu_thue'] for rs in th.values() for r in rs))
    assert cp == 600_000_000 and cht == ct0 - 3_000_000, (cp, cht, tom['canh_bao'])
    for rs in th.values():
        for r in rs:
            assert r['tien_com'] <= 730000 + 1 and r['muc_dt'] <= 1_000_000 + 1 and r['trang_phuc'] <= 416_001, r
# 3) lớn hơn tổng chi phí -> báo lỗi
try:
    chay(600_000_000, 700_000_000); assert False
except HTTPException as e:
    assert e.status_code == 400
# 4) không nhập -> y như cũ
th, tom = chay(600_000_000, 0)
assert tom['muc_tieu_ct'] == 0 and tom['khop_chiu_thue'] is False
# 5) có tháng chuyển khoản theo file: TT lương tháng đó vẫn khớp, 2 tổng vẫn đúng
def chay_ck(muc, ct):
    return server._luong_ke_hoach(pool, 2026, 1, 12, muc, None, 50.0, 0, random.Random(3), True, None, {"03": 30_000_000}, 12000000, du_bhxh=True, muc_tieu_ct=ct)
thk, tk0 = chay_ck(600_000_000, 0)
ctk = tk0['tong_chiu_thue'] + 4_000_000
thk, tk = chay_ck(600_000_000, ctk)
assert tk['ck']['03']['tt_luong'] == 30_000_000 and tk['ck']['03']['khop'], tk['ck']
assert sum(r['chi_phi_luong'] for rs in thk.values() for r in rs) == tk['tong_chi_phi'] and tk['tong_chiu_thue'] == ctk and tk['khop_chiu_thue'], (tk['tong_chiu_thue'], ctk, tk['canh_bao'])
print("PASS: nhập thêm Tổng thu nhập chịu thuế -> bảng lương cuối năm ra đúng cả tổng chi phí lương lẫn tổng thu nhập chịu thuế (tăng/giảm, không vượt trần phụ cấp, không phát sinh thuế khi còn chỗ)")
