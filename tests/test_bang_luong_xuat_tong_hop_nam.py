import os, sys, random, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server, openpyxl
# Excel "Tổng hợp cả năm": cột đánh số + công thức (6)=(1)-(2)-(3)-(4)-(5), (9), (11); tổng = SUM. Dữ liệu giả.
H = server.NV_HEADERS
def R(**k):
    r = [''] * len(H)
    for a, b in k.items(): r[H.index(a)] = b
    return r
rows = [R(**{'Mã NV': str(i), 'Họ và tên': f'NV {i}', 'Tháng/Năm vào làm': '01/01/2026', 'Đóng BHXH': 'x', 'Chức vụ': 'NV', 'Lương Cơ bản': 6_000_000,
             'PC Tiền cơm': 730000, 'PC Xăng xe': 500000, 'PC Điện thoại': 500000, 'PC Trang phục': 300000}) for i in range(1, 4)]
pool = lambda t: [r for r in server._luong_dong_tu_nhan_vien(H, rows, 0, 2026, int(t), None) if not r.get('part_time')]
th, tom = server._luong_ke_hoach(pool, 2026, 1, 3, 40_000_000, None, 50.0, 0, random.Random(1), True, None, None, 12000000, du_bhxh=True)
server.DOWNLOAD_DIR = tempfile.mkdtemp()
path, fname, tt = server._luong_xuat_excel_tong_hop_nam(2026, th, "CTY TEST", "0123456789")
ws = openpyxl.load_workbook(path)["Tổng hợp cả năm"]
assert tt["so_nguoi"] == 3 and ws["C4"].value == "(1)" and "(6) = (1)" in ws["H4"].value, (tt, ws["H4"].value)
assert ws["H5"].value == "=C5-D5-E5-F5-G5" and ws["K5"].value == "=H5-I5-J5" and ws["M5"].value == "=C5-I5-L5", (ws["H5"].value, ws["K5"].value, ws["M5"].value)
assert ws["C8"].value == "=SUM(C5:C7)" and ws["B8"].value == "TỔNG CỘNG"
tong = sum(r["chi_phi_luong"] for rs in th.values() for r in rs)
assert abs(sum(ws[f"C{i}"].value for i in (5, 6, 7)) - tong) < 1, tong
ct = sum(r["tn_chiu_thue"] for rs in th.values() for r in rs)
tinh = sum(ws[f"C{i}"].value - ws[f"D{i}"].value - ws[f"E{i}"].value - ws[f"F{i}"].value - ws[f"G{i}"].value for i in (5, 6, 7))
assert abs(tinh - ct) < 3, (tinh, ct)
print("PASS: xuất Excel tổng hợp cả năm có cột đánh số + công thức (6)/(9)/(11) + dòng SUM; khớp tổng thu nhập chịu thuế của bảng lương")
