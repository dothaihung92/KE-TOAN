import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Ca thật (CÔNG TY TNHH CƠ KHÍ - VẬN TẢI THIÊN PHÚC): "Chi phí lương cả năm 2025" đưa Lưu Văn Khoa (vào làm 01/02/2025, có BHXH) và
# Hứa Minh Tuấn (vào làm 01/07/2026) vào bảng lương tháng 1/2025. Người chưa tới tháng vào làm không được lên bảng lương.
H = ["STT", "Mã NV", "Họ và tên", "Tháng/Năm vào làm", "Đóng BHXH", "Tháng/Năm nghỉ việc", "Chức vụ", "Lương Cơ bản", "PC Tiền cơm"]
R = [[1, "1", "Lê Thị Huyền Trang", "01/01/2025", "x", "", "Kế Toán", 5000000, 730000],
     [2, "1-001", "Lê Thị Huyền Trang", "01/2026", "x", "", "Kế Toán", 5310000, 730000],
     [3, "2", "Lưu Văn Khoa", "01/02/2025", "x", "", "Tài Xế", 5000000, 730000],
     [4, "2-001", "Lưu Văn Khoa", "01/2026", "x", "", "Tài Xế", 5310000, 730000],
     [5, "3", "Hứa Minh Tuấn", "01/07/2026", "x", "", "Tài xế", 5310000, 730000]]
def ten(nam, thang):
    return sorted(x["ten"] for x in server._luong_dong_tu_nhan_vien(H, R, 0, nam, thang))
assert ten(2025, 1) == ["Lê Thị Huyền Trang"], ten(2025, 1)
assert ten(2025, 2) == ["Lê Thị Huyền Trang", "Lưu Văn Khoa"] and ten(2025, 12) == ten(2025, 2)
assert ten(2026, 6) == ["Lê Thị Huyền Trang", "Lưu Văn Khoa"] and "Hứa Minh Tuấn" in ten(2026, 7)
k = [x for x in server._luong_dong_tu_nhan_vien(H, R, 0, 2025, 2) if x["ten"] == "Lưu Văn Khoa"][0]
assert k["dong_bh"] == 1
print("PASS 1: T1/2025 chỉ Trang; Khoa lên bảng lương từ T2/2025 (đóng BHXH); Tuấn từ T7/2026 — không có trong năm 2025.")

import random
th, tom = server._luong_ke_hoach(lambda t: server._luong_dong_tu_nhan_vien(H, R, 0, 2025, int(t)), 2025, 1, 12, 120_000_000, None, rng=random.Random(1))
assert all(r["ten"] == "Lê Thị Huyền Trang" for r in th["01"]), [r["ten"] for r in th["01"]]
assert not any(r["ten"] == "Hứa Minh Tuấn" for rows in th.values() for r in rows)
print("PASS 2: Chi phí lương cả năm 2025 không đưa Khoa vào T1, không đưa Tuấn vào năm 2025.")
print("ALL DONE")
