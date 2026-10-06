import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Kế hoạch chi phí lương cả năm: "Luôn đưa đủ người có BHXH" — mọi người tick Đóng BHXH đang làm trong tháng PHẢI có trong bảng lương tháng đó
# (trước đây phần mềm chỉ lấy đủ số người cần tới khi đạt mục tiêu -> người cuối danh sách như mã 9, 10, 11 bị sót dù có BHXH và đang làm việc).
H = server.NV_HEADERS
def R(**k):
    r = [''] * len(H)
    for a, b in k.items(): r[H.index(a)] = b
    return r
def nv(ma, ten, vao, nghi='', bh='x', luong=5_100_000):
    return R(**{'Mã NV': ma, 'Họ và tên': ten, 'Tháng/Năm vào làm': vao, 'Tháng/Năm nghỉ việc': nghi, 'Đóng BHXH': bh, 'Chức vụ': 'Bảo vệ', 'Lương Cơ bản': luong,
                'PC Tiền cơm': 730000, 'PC Xăng xe': 500000, 'PC Điện thoại': 500000})
rows = [nv('1', 'Dương Thị Hiền', '01/01/2025'), nv('2', 'Nguyễn Văn Khoan', '01/01/2025'), nv('3', 'Lý Thị Thu Hiền', '01/01/2025', '01/04/2026'),
        nv('4', 'Lê Đức Tấn', '01/01/2025'), nv('5', 'Huỳnh Văn Vinh', '01/01/2025', '01/05/2025'), nv('6', 'Lâm Thái Huy', '01/01/2025'), nv('7', 'Phạm Bảo Vương', '01/01/2025'),
        nv('8', 'Đặng Ngọc Thanh', '01/01/2025', '01/04/2025'), nv('9', 'Vũ Hồng Anh', '01/01/2025', '01/05/2025'), nv('10', 'Lưu Văn Thoại', '01/01/2025', '01/05/2025'),
        nv('11', 'Trần Quốc Huy', '01/03/2025')]
pool = lambda t: [r for r in server._luong_dong_tu_nhan_vien(H, rows, 0, 2025, int(t), None) if not r.get('part_time')]
def chay(muc, du, full=True):
    th, tom = server._luong_ke_hoach(pool, 2025, 1, 12, muc, None, 50.0, 0, random.Random(1), full, None, None, 12000000, du_bhxh=du)
    return th, tom, {t: {r['ma'] for r in rs} for t, rs in th.items()}
tong = lambda th: sum(r['chi_phi_luong'] for rs in th.values() for r in rs)

# 1) cách cũ (không bắt buộc): mục tiêu thấp -> chỉ lấy vài người đầu danh sách, 9/10/11 bị sót
th, tom, ds = chay(640_000_000, False)
assert tong(th) == 640_000_000 and not any({'9', '10', '11'} & ds[t] for t in ds)
# 2) bắt buộc: mọi người có BHXH đang làm đều có mặt đúng tháng (9, 10 tới hết T5? — nghỉ việc 01/05/2025: còn tháng 5 nhưng hết BHXH; 11 từ T3)
th, tom, ds = chay(782_614_653, True)
for t in ("01", "02"):
    assert {'1', '2', '3', '4', '5', '6', '7', '8', '9', '10'} <= ds[t], (t, ds[t])
assert {'1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11'} <= ds["03"]
assert {'1', '2', '3', '4', '5', '6', '7', '9', '10', '11'} <= ds["04"] and '8' not in ds["04"], "T4: mã 8 nghỉ từ 01/04 -> không còn trên bảng lương"
assert '11' not in ds["01"] and '11' not in ds["02"] and '11' in ds["03"] and all('11' in ds[t] for t in ds if t >= "03")
for t in ("06", "12"):
    assert ds[t] == {'1', '2', '3', '4', '6', '7', '11'}, (t, ds[t])      # chỉ người còn làm việc (5, 8, 9, 10 đã nghỉ)
assert tong(th) == 782_614_653, "mục tiêu đủ: vẫn khớp từng đồng"
assert not any("VƯỢT mục tiêu" in c for c in tom["canh_bao"])
# 3) mục tiêu thấp hơn lương đủ công của những người có BHXH: vẫn đưa đủ + cảnh báo vượt (không âm thầm bỏ người, không thưởng/tăng ca âm)
th, tom, ds = chay(500_000_000, True)
assert {'9', '10', '11'} <= ds["03"] and tong(th) > 500_000_000
assert any("VƯỢT mục tiêu" in c and "tick Đóng BHXH" in c for c in tom["canh_bao"])
assert all(r["thuong_bh"] >= 0 and r["tang_ca"] >= 0 for rs in th.values() for r in rs)
# 4) không full công (đủ công + bù thưởng/tăng ca): cũng đưa đủ người
th, tom, ds = chay(782_614_653, True, full=False)
assert {'9', '10'} <= ds["02"] and '11' in ds["04"]
# 5) người KHÔNG tick BHXH không bị ép: chỉ thêm khi cần
rows.append(nv('12', 'Không BHXH', '01/01/2025', bh=''))
th, tom, ds = chay(782_614_653, True)
assert tong(th) == 782_614_653
print("PASS")
