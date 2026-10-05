import os, sys, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server, van_ban_lao_dong as v

# LAO ĐỘNG PART-TIME (HĐLĐ làm việc không trọn thời gian): cột "Part-time" (tick) + "Lương theo giờ" ở Danh Sách Nhân Viên;
# Bảng Lương tính lương = giờ làm THỰC TẾ × lương giờ, không phụ cấp; dưới ngưỡng thì không BHXH, từ ngưỡng trở lên thì phải đóng; hợp đồng riêng.
H = server.NV_HEADERS
assert "Part-time" in H and "Lương theo giờ" in H and H.index("Part-time") < H.index("Lương theo giờ") < H.index("Lương Cơ bản")
def R(**k):
    r = [''] * len(H)
    for a, b in k.items():
        r[H.index(a)] = b
    return r
rows = [R(**{'Mã NV': '1', 'Họ và tên': 'Toàn thời gian', 'Đóng BHXH': 'x', 'Tháng/Năm vào làm': '01/2025', 'Lương Cơ bản': 6000000, 'PC Tiền cơm': 730000, 'Chức vụ': 'Nhân viên'}),
        R(**{'Mã NV': '2', 'Họ và tên': 'Bán thời gian', 'Đóng BHXH': 'x', 'Tháng/Năm vào làm': '01/2025', 'Part-time': 'x', 'Lương theo giờ': 26000, 'PC Tiền cơm': 730000, 'Chức vụ': 'Bảo vệ'})]
dong = server._luong_dong_tu_nhan_vien(H, rows, 0, 2026, 3)
assert [d["part_time"] for d in dong] == [0, 1] and dong[1]["luong_gio"] == 26000 and dong[0]["luong_gio"] == "" or dong[0]["luong_gio"] == 0

ts = server._luong_chuan_tham_so(None, 2026)
assert ts["nguong_part_time"] == 2530000 and server._luong_chuan_tham_so(None, 2025)["nguong_part_time"] == 2340000
assert server._luong_chuan_tham_so({"nguong_part_time": 2500000}, 2026)["nguong_part_time"] == 2500000
pt = dict(dong[1])
# chưa nhập giờ làm = 0 giờ = 0 đồng (không tự đặt giờ)
t0 = server._luong_tinh_dong(pt, ts, "03")
assert t0["luong"] == 0 and t0["tt_luong"] == 0 and t0["chi_phi_luong"] == 0
# 40 giờ × 26.000 = 1.040.000: không phụ cấp (dù NV có phụ cấp tiền cơm), không BHXH, không canh_bao_bh, không thoi_vu
pt["gio_lam"] = 40
t1 = server._luong_tinh_dong(pt, ts, "03")
assert t1["luong"] == 1040000 and t1["tt_tien_com"] == 0 and t1["xang_xe"] == 0 and t1["dien_thoai"] == 0 and t1["tt_trang_phuc"] == 0
assert t1["bhxh_dn"] == 0 and t1["bhxh_nld"] == 0 and t1["dong_bh"] == 0 and t1["pt_phai_dong_bh"] is False and not t1["canh_bao_bh"] and not t1["thoi_vu"]
assert t1["chi_phi_luong"] == 1040000 and t1["tt_luong"] == 1040000 and t1["thue_tncn"] == 0 and t1["luong_pt"] == 1040000
# 100 giờ × 26.000 = 2.600.000 >= 2.530.000 -> thuộc đối tượng đóng BHXH: tự tính BH trên lương thực tế
pt["gio_lam"] = 100
t2 = server._luong_tinh_dong(pt, ts, "03")
assert t2["luong"] == 2600000 and t2["pt_phai_dong_bh"] is True and t2["dong_bh"] == 1
assert round(t2["bhxh_nld"]) == 208000 and round(t2["bhxh_dn"]) == 455000, (t2["bhxh_nld"], t2["bhxh_dn"])
# ngay dưới ngưỡng (2.529.000) không đóng
pt["gio_lam"] = 2529000 / 26000
assert server._luong_tinh_dong(pt, ts, "03")["pt_phai_dong_bh"] is False
# người toàn thời gian không đổi: vẫn tính theo công chuẩn + phụ cấp
ft = server._luong_tinh_dong(dong[0], ts, "03")
assert ft["luong"] > 0 and ft["tt_tien_com"] > 0 and ft["dong_bh"] == 1 and ft["part_time"] == 0

# xuất Excel bảng lương: dòng part-time ghi lương theo giờ làm thực tế (không phụ cấp), không lỗi
import openpyxl
pt = dict(dong[1], gio_lam=100)
path, _ = server._luong_xuat_excel(2026, ts, {"03": [pt, dong[0]]})
ws = openpyxl.load_workbook(path).active
dong_xl = [[c.value for c in row] for row in ws.iter_rows(min_row=3, max_row=4)]
ten_cot = {str(c.value or "").strip(): c.column - 1 for c in ws[2]}
assert any(isinstance(x, (int, float)) and abs(x - 2600000) < 1 for x in dong_xl[0]), "lương part-time = 2.600.000 (100 giờ × 26.000)"

# kế hoạch chi phí cả năm KHÔNG tự phân bổ tháng làm/không làm cho part-time: bị loại khỏi pool + có cảnh báo
src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py"), encoding="utf-8").read()
assert 'if not r.get("part_time")]' in src and "phần mềm không tự chọn tháng làm/không làm" in src

# nhận diện cột khi import danh sách
cot = {t: d for d, ks in server._NV_TU_KHOA for t in ks}
assert cot["part time"] == "Part-time" and cot["luong theo gio"] == "Lương theo giờ"

# ghép dữ liệu cho hợp đồng
nv = v.gop_nhan_vien(H, rows, {}, 2026)
assert [(n["ten"], n["part_time"], n["luong_gio"]) for n in nv] == [("Toàn thời gian", False, 0.0), ("Bán thời gian", True, 26000.0)]

# HỢP ĐỒNG PART-TIME: tên, thời giờ làm việc, lương giờ, câu BHXH
CTY = {"ten": "CÔNG TY TNHH THỬ", "mst": "0300000001", "dia_chi": "1 Lê Lợi, Quận 1, Thành phố Hồ Chí Minh", "nguoi_ky": "Hồ Thị Cẩm Vân"}
def van_ban(h):
    import re
    return re.sub(r"<[^>]+>", "", h).replace("&nbsp;", " ")
tc = {"pt_gio_ngay": "2", "pt_lich": "từ Thứ Hai đến Thứ Sáu"}
h = v.dung_hop_dong_part_time(nv[1], CTY, tc, 0, nam=2026)
t = van_ban(h)
assert "LÀM VIỆC KHÔNG TRỌN THỜI GIAN" in t and "HỢP ĐỒNG LAO ĐỘNG" in t
assert "2 giờ/ngày" in t and "từ Thứ Hai đến Thứ Sáu" in t and "10 giờ/tuần" in t and "ngắn hơn" in t
assert "theo giờ" in t and "26.000 đồng/giờ" in t and "dưới 2.530.000 đồng/tháng" in t and "Phụ cấp lương và các khoản bổ sung khác: không có" in t
assert "Do thời giờ làm việc và mức tiền lương tháng không đạt mức tối thiểu làm căn cứ đóng bảo hiểm xã hội bắt buộc theo quy định của Luật Bảo hiểm xã hội, Người lao động không thuộc đối tượng tham gia bảo hiểm xã hội, bảo hiểm y tế, bảo hiểm thất nghiệp bắt buộc." in t
assert "HĐPT-2026" in t
# lương dự kiến từ ngưỡng trở lên thì KHÔNG ghi câu "không thuộc đối tượng"
h2 = v.dung_hop_dong_part_time(nv[1], CTY, {"pt_gio_ngay": "4", "pt_ngay_tuan": 6}, 0, nam=2026)
t2_ = van_ban(h2)
assert "không thuộc đối tượng tham gia" not in t2_ and "thuộc đối tượng tham gia bảo hiểm xã hội bắt buộc: Công ty và Người lao động cùng tham gia" in t2_
cb = v.kiem_tra_part_time([nv[1]], v.gop_tuy_chon(CTY, {"pt_gio_ngay": "4", "pt_ngay_tuan": 6}), 2026)
assert any(c["muc"] == "loi" and "thuộc đối tượng tham gia BHXH bắt buộc" in c["nd"] for c in cb)
# thiếu dữ liệu / sai: cảnh báo
cb = v.kiem_tra_part_time([dict(nv[1], luong_gio=0)], v.gop_tuy_chon(CTY, {}), 2026)
assert any("chưa ghi số giờ" in c["nd"] for c in cb) and any("chưa có lương theo giờ" in c["nd"] for c in cb)
cb = v.kiem_tra_part_time([nv[1]], v.gop_tuy_chon(CTY, {"pt_gio_ngay": "8"}), 2026)
assert any("không ngắn hơn" in c["nd"] for c in cb)
cb = v.kiem_tra_part_time([dict(nv[1], luong_gio=20000)], v.gop_tuy_chon(CTY, {"pt_gio_ngay": "2"}), 2026)
assert any("thấp hơn mức lương tối thiểu giờ" in c["nd"] for c in cb)
assert v.luong_toi_thieu_gio(2026, 1) == 25500 and v.luong_toi_thieu_gio(2024, 1) == 23800
# nhiều hợp đồng
assert v.dung_hop_dong_part_time_nhieu(nv[1:], CTY, tc, nam=2026).count('<section class="vb-trang">') == 1
print("PASS")
