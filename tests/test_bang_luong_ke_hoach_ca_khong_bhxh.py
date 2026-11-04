import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Kế hoạch chi phí lương cả năm: người có "Tháng/Năm vào làm" nhưng KHÔNG tick Đóng BHXH vẫn phải lên bảng lương khi chọn "Đưa cả người không đóng BHXH"
# (trước đây họ chỉ được lấy khi cần bù mục tiêu nên bị sót khỏi bảng lương). Dữ liệu giả.
H = server.NV_HEADERS
def R(**k):
    r = [''] * len(H)
    for a, b in k.items(): r[H.index(a)] = b
    return r
def nv(ma, ten, vao, bh='x', nghi=''):
    return R(**{'Mã NV': ma, 'Họ và tên': ten, 'Tháng/Năm vào làm': vao, 'Tháng/Năm nghỉ việc': nghi, 'Đóng BHXH': bh, 'Chức vụ': 'NV', 'Lương Cơ bản': 5_000_000,
                'PC Tiền cơm': 730000, 'PC Xăng xe': 500000, 'PC Điện thoại': 500000})
rows = [nv('1', 'Người A', '01/01/2026'), nv('2', 'Người B', '01/01/2026'), nv('3', 'Người C không BHXH', '01/01/2026', bh=''), nv('4', 'Người D chưa vào làm', '01/09/2026', bh='')]
pool = lambda t: [r for r in server._luong_dong_tu_nhan_vien(H, rows, 0, 2026, int(t), None) if not r.get('part_time')]
def chay(muc, ca, full):
    th, tom = server._luong_ke_hoach(pool, 2026, 1, 3, muc, None, 50.0, 0, random.Random(1), full, None, None, 12000000, du_bhxh=True, du_ca_khong_bh=ca)
    return th, tom, {t: {r['ten'] for r in rs} for t, rs in th.items()}

for full in (True, False):
    th, tom, ds = chay(60_000_000, False, full)
    assert all('Người C không BHXH' not in ds[t] for t in ds), (full, ds)      # cách cũ: chỉ có người đóng BHXH
    th, tom, ds = chay(60_000_000, True, full)
    for t in ds:
        assert {'Người A', 'Người B', 'Người C không BHXH'} <= ds[t], (full, t, ds[t])
        assert 'Người D chưa vào làm' not in ds[t]                                  # chưa tới tháng vào làm -> không lên bảng lương
    c = [r for r in th['01'] if r['ten'] == 'Người C không BHXH'][0]
    assert not c.get('dong_bh'), c
print("PASS: người không đóng BHXH nhưng đã có ngày vào làm lên bảng lương từng tháng khi chọn 'Đưa cả người không đóng BHXH'; người chưa vào làm vẫn không lên.")
