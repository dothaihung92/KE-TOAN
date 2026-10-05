import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server, van_ban_lao_dong as v, openpyxl

# Danh Sách Nhân Viên: 1 người có nhiều dòng (gốc + dòng thay đổi lương mã-001, -002 có "Tháng/Năm thay đổi lương"); từ tháng đó Bảng Lương dùng lương + mã mới.
HDR = ['STT', 'Mã NV', 'Họ và tên', 'Ngày sinh', 'Địa chỉ hiện đang cư trú', 'CCCD', 'Ngày cấp', 'Tháng/Năm vào làm', 'Đóng BHXH', 'Tháng/Năm nghỉ việc',
       'Chức vụ', 'Tháng/Năm thay đổi lương', 'Lương Cơ bản', 'PC Tiền cơm', 'PC Xăng xe', 'PC Điện thoại', 'PC Trang phục']
assert server.NV_HEADERS[10:16] == ['Chức vụ', 'Tháng/Năm thay đổi lương', 'Thử việc từ', 'Thử việc đến', 'Part-time', 'Lương theo giờ'] and server.NV_HEADERS[16] == 'Lương Cơ bản', "cột mới nằm ngay sau Chức vụ"
R = lambda stt, ma, ten, doi, luong, nghi="": [stt, ma, ten, '', '', '079090000123', '', '12/2024', 'x', nghi, 'Kinh doanh', doi, luong, 700000, 500000, 0, 0]
ROWS = [R(1, '2', 'Trần Minh Hùng', '', 5_310_000), R(2, '2-001', 'Trần Minh Hùng', '01/2027', 6_000_000), R(3, '2-002', 'Trần Minh Hùng', '07/2027', 7_000_000),
        R(4, '3', 'Nguyễn Giang Nam', '', 5_310_000)]

def ma_luong(nam, thang):
    kq = server._luong_dong_tu_nhan_vien(HDR, ROWS, 0, nam, thang)
    return [(r["ma"], r["luong_cb"]) for r in kq]
assert ma_luong(2026, 12) == [("2", 5_310_000), ("3", 5_310_000)], "trước ngày thay đổi: dòng gốc"
assert ma_luong(2027, 1) == [("2-001", 6_000_000), ("3", 5_310_000)], "từ 01/2027: lương + mã mới, không lấy mã cũ"
assert ma_luong(2027, 6) == [("2-001", 6_000_000), ("3", 5_310_000)]
assert ma_luong(2027, 7) == [("2-002", 7_000_000), ("3", 5_310_000)]
assert ma_luong(2030, 1)[0] == ("2-002", 7_000_000)
assert [r["ma"] for r in server._luong_dong_tu_nhan_vien(HDR, ROWS)] == ["2-002", "3"], "không chỉ định tháng: dòng mới nhất, mỗi người 1 dòng"
assert len(server._luong_dong_tu_nhan_vien(HDR, ROWS, 0, 2027, 3)) == 2, "không bị đếm 3 người (không nhân đôi nhân viên)"
# kể cả khi chỉ có dòng thay đổi ở tương lai thì người đó chưa lên bảng lương; dòng thay đổi gõ mã khác (không đuôi) vẫn gộp theo họ tên
r2 = [R(1, '5', 'A', '', 1_000_000), R(2, '9', 'A', '03/2027', 2_000_000), R(3, '6', 'B', '05/2027', 3_000_000)]
assert [(x["ma"], x["luong_cb"]) for x in server._luong_dong_tu_nhan_vien(HDR, r2, 0, 2027, 2)] == [("5", 1_000_000)]
assert [(x["ma"], x["luong_cb"]) for x in server._luong_dong_tu_nhan_vien(HDR, r2, 0, 2027, 4)] == [("9", 2_000_000)]
# 2 người khác nhau có mã dạng NV-001 / NV-002 (không ghi tháng thay đổi) vẫn là 2 người
r3 = [R(1, 'NV-001', 'A', '', 1), R(2, 'NV-002', 'B', '', 2)]
assert len(server._luong_dong_tu_nhan_vien(HDR, r3, 0, 2027, 4)) == 2
# danh sách cũ chưa có cột -> hành vi như trước
HDR_CU = [h for h in HDR if h != 'Tháng/Năm thay đổi lương']
assert len(server._luong_dong_tu_nhan_vien(HDR_CU, [x[:11] + x[12:] for x in ROWS], 0, 2027, 3)) == 4

# người phụ thuộc khai theo mã gốc "2" vẫn tính cho "2-001"; mã NV-001 / NV-002 không lẫn nhau
npt = server._luong_npt_doc({"header": server.NPT_HEADERS, "rows": [["", "2", "Trần Minh Hùng", "Bé An", "01/01/2015", "", "Con", "01/2025", ""], ["", "NV-001", "A", "Bé B", "", "", "Con", "01/2025", ""]]})
assert server._luong_so_npt_thang(npt, "2-001", "Trần Minh Hùng", 2027, 3) == 1 and server._luong_so_npt_thang(npt, "2", "Trần Minh Hùng", 2027, 3) == 1
assert server._luong_so_npt_thang(npt, "NV-002", "B", 2027, 3) == 0 and server._luong_so_npt_thang(npt, "NV-001", "A", 2027, 3) == 1

# quyết toán TNCN + Excel cả năm: đổi mã giữa năm (2 -> 2-001) vẫn là MỘT người
TS = server._luong_chuan_tham_so(None, 2027)
dong = lambda ma, luong: server._luong_chuan_dong_nhap({"ma": ma, "ten": "Trần Minh Hùng", "chuc_vu": "KD", "luong_cb": luong, "tien_com": 730_000, "dong_bh": 1})
thang_nhap = {"%02d" % t: [dong("2" if t < 7 else "2-001", 5_310_000 if t < 7 else 6_000_000)] for t in range(1, 13)}
thang_tinh = {t: server._luong_tinh_thang(r, TS, t, 2027) for t, r in thang_nhap.items()}
tong = server._luong_qt_tong_hop(TS, thang_tinh, ["Mã NV", "Họ và tên", "CCCD"], [["2", "Trần Minh Hùng", "079090000123"], ["2-001", "Trần Minh Hùng", "079090000123"]], None, 2027)
assert len(tong["g1"]) == 1 and tong["g1"][0]["ten"] == "Trần Minh Hùng", "1 người, không bị tách 2 người khi đổi mã"
path, fname, tt = server._luong_xuat_excel_nam_gop(2027, TS, thang_tinh, "CÔNG TY THỬ", "0300000001")
assert tt["so_nguoi"] == 1, tt

# Văn bản (hợp đồng/quy chế/thang lương): mỗi người 1 dòng, phiên bản lương hiệu lực đến hết năm đang lập
nv27 = v.gop_nhan_vien(HDR, ROWS, {}, 2027)
assert [(n["ma"], n["luong_cb"]) for n in nv27] == [("2-002", 7_000_000), ("3", 5_310_000)]
nv26 = v.gop_nhan_vien(HDR, ROWS, {}, 2026)
assert [(n["ma"], n["luong_cb"]) for n in nv26] == [("2", 5_310_000), ("3", 5_310_000)]
assert v.ma_goc_phien_ban("2-001") == "2" and v.ma_goc_phien_ban("NV-1") == "NV-1" and v.ma_goc_phien_ban("12") == "12"
# import Excel danh sách nhân viên nhận cột "Tháng/Năm thay đổi lương"
assert any(c == "Tháng/Năm thay đổi lương" for c, _k in server._NV_TU_KHOA)
print("PASS")

# Dòng phiên bản mã gốc-001 CHƯA ghi "Tháng/Năm thay đổi lương" nhưng có "Tháng/Năm vào làm": hiệu lực từ tháng vào làm (vd 2 = part-time từ 01/2024, 2-001 = toàn thời gian đóng BHXH từ 12/2024)
H2 = server.NV_HEADERS
def R2(**k):
    r = [''] * len(H2)
    for a, b in k.items():
        r[H2.index(a)] = b
    return r
rows2 = [R2(**{'Mã NV': '2', 'Họ và tên': 'Trần Minh Hùng', 'CCCD': '079079015954', 'Tháng/Năm vào làm': '01/2024', 'Part-time': 'x', 'Lương theo giờ': 25000, 'Chức vụ': 'NVKD'}),
         R2(**{'Mã NV': '2-001', 'Họ và tên': 'Trần Minh Hùng', 'CCCD': '079079015954', 'Tháng/Năm vào làm': '12/2024', 'Đóng BHXH': 'x', 'Lương Cơ bản': 5310000, 'Chức vụ': 'NVKD'})]
for t, (ma, pt, bh) in {1: ('2', 1, 0), 11: ('2', 1, 0), 12: ('2-001', 0, 1)}.items():
    r = server._luong_dong_tu_nhan_vien(H2, rows2, 0, 2024, t)
    assert [(x['ma'], x['part_time'], x['dong_bh']) for x in r] == [(ma, pt, bh)], (t, r)
assert [x['ma'] for x in server._luong_dong_tu_nhan_vien(H2, rows2, 0, 2025, 3)] == ['2-001'], "các năm sau dùng phiên bản mới nhất"
# dòng -001 không ghi vào làm: vẫn là dòng riêng (như trước)
rows3 = [rows2[0], R2(**{'Mã NV': '2-001', 'Họ và tên': 'Trần Minh Hùng', 'Lương Cơ bản': 5310000})]
assert len(server._luong_dong_tu_nhan_vien(H2, rows3, 0, 2024, 5)) == 2
print("PASS thêm: dòng -001 hiệu lực từ tháng vào làm")
