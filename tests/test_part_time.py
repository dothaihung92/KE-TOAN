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
assert t1["bhxh_dn"] == 0 and t1["bhxh_nld"] == 0 and t1["dong_bh"] == 0 and t1["pt_phai_dong_bh"] is False and not t1["canh_bao_bh"]
# part-time dưới ngưỡng BHXH: khấu trừ 10% MỌI khoản chi trả (không giảm trừ, không xét ngưỡng khấu trừ) và vào bảng kê 05-2 (cờ thoi_vu)
assert t1["thoi_vu"] is True and t1["thue_tncn"] == 104000 and t1["thue_tru_luong"] == 104000 and t1["tn_tinh_thue"] == 1040000
assert t1["chi_phi_luong"] == 1040000 and t1["tt_luong"] == 936000 and t1["luong_pt"] == 1040000
# người part-time CHỈ có lương theo giờ: thưởng bán hàng / thưởng T13 / tăng ca / phụ cấp đã nhập sẵn (dữ liệu cũ) KHÔNG được cộng vào chi phí lương và thực lãnh
pt3 = dict(dong[1], gio_lam=18, luong_gio=25000, thuong_bh=1774666, thuong_t13=500000, tang_ca=1361000, tien_com=730000, muc_xang=500000, luong_cb=5310000)
t_ = server._luong_tinh_dong(pt3, ts, "01")
assert t_["luong"] == 450000 and t_["chi_phi_luong"] == 450000 and t_["thue_tncn"] == 45000 and t_["tt_luong"] == 405000 and t_["bhxh_nld"] == 0, (t_["chi_phi_luong"], t_["tt_luong"])
assert t_["tn_chiu_thue"] == 450000 and t_["tn_khong_chiu_thue"] == 0
# 100 giờ × 26.000 = 2.600.000 >= 2.530.000 -> thuộc đối tượng đóng BHXH: tự tính BH trên lương thực tế
pt["gio_lam"] = 100
t2 = server._luong_tinh_dong(pt, ts, "03")
assert t2["luong"] == 2600000 and t2["pt_phai_dong_bh"] is True and t2["dong_bh"] == 1
assert t2["thoi_vu"] is False, "đạt ngưỡng BHXH: có hợp đồng lao động -> tính như người thường (lũy tiến), không khấu trừ 10%"
assert round(t2["bhxh_nld"]) == 208000 and round(t2["bhxh_dn"]) == 455000, (t2["bhxh_nld"], t2["bhxh_dn"])
# ngay dưới ngưỡng (2.529.000) không đóng
pt["gio_lam"] = 2529000 / 26000
assert server._luong_tinh_dong(pt, ts, "03")["pt_phai_dong_bh"] is False
# tắt tham số "part-time khấu trừ 10%": như người thường (dưới ngưỡng khấu trừ thì không trừ)
ts_tat = server._luong_chuan_tham_so({"pt_thue_10": False}, 2026)
assert ts_tat["pt_thue_10"] is False and ts["pt_thue_10"] is True
tt_ = server._luong_tinh_dong(dict(dong[1], gio_lam=40), ts_tat, "03")
assert tt_["thoi_vu"] is False and tt_["thue_tncn"] == 0 and tt_["tt_luong"] == 1040000
# ghi nhận vào bảng kê 05-2 (quyết toán): người part-time có thuế 10% -> phụ lục 05-2
hang = {"01": [server._luong_tinh_dong(dict(dong[1], gio_lam=40), ts, "01")]}
qt = server._luong_qt_tong_hop(ts, hang, H, rows, None, 2026)
assert [(p["ten"], p["ct11"], p["ct15"]) for p in qt["g2"]] == [("Bán thời gian", 1040000, 104000)], qt["canh_bao"]
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
tc = {"pt_gio_ngay": "2", "pt_ngay_tuan": 5, "pt_lich": "từ Thứ Hai đến Thứ Sáu"}
h = v.dung_hop_dong_part_time(nv[1], CTY, tc, 0, nam=2026)
t = van_ban(h)
assert "LÀM VIỆC KHÔNG TRỌN THỜI GIAN" in t and "HỢP ĐỒNG LAO ĐỘNG" in t
assert "theo lịch sắp xếp của Công ty" in t and "chỉ làm việc khi Công ty có lịch sắp xếp" in t and "khoảng 2 giờ/ngày" in t and "10 giờ/tuần" in t and "ngắn hơn" in t
assert "Loại hợp đồng" not in t and "Xác định thời hạn" not in t and "Địa điểm làm việc" not in t, "không có mục loại hợp đồng, không có dòng địa điểm làm việc"
assert "Thời hạn hợp đồng" not in t and "Điều 1. Chức danh và công việc phải làm" in t and "1. Chức danh chuyên môn / chức vụ: Bảo vệ." in t and "2. Công việc phải làm:" in t, "đã bỏ dòng thời hạn hợp đồng"
# ngày hợp đồng + ngày ký = ngày bắt đầu làm việc đầu tiên (vào làm 01/2025), không dời sang 01/01 của năm lập (2026)
assert "ngày 01 tháng 01 năm 2025" in t and "Số: 01/HĐPT-2025" in t and "năm 2026" not in t.split("Điều 1")[0]
t_c = van_ban(v.dung_hop_dong_part_time(dict(nv[1], vao_lam="15/03/2023"), CTY, {}, 0, nam=2026))
assert "ngày 15 tháng 03 năm 2023" in t_c and "HĐPT-2023" in t_c and "có hiệu lực kể từ ngày 15 tháng 03 năm 2023" in t_c
t_u = van_ban(v.dung_hop_dong_part_time(nv[1], CTY, {"ngay_ky": "20/01/2025", "bat_dau": "10/01/2025"}, 0, nam=2026))
assert "ngày 20 tháng 01 năm 2025" in t_u and "có hiệu lực kể từ ngày 10 tháng 01 năm 2025" in t_u, "người dùng nhập tay thì theo ô nhập"
# chưa có giờ/tháng dự kiến: không in dòng "Số giờ làm việc dự kiến: ........"
t_trong = van_ban(v.dung_hop_dong_part_time(nv[1], CTY, {}, 0, nam=2026))
assert "dự kiến: ........" not in t_trong and "Số giờ làm việc dự kiến" not in t_trong and "theo lịch sắp xếp của Công ty" in t_trong and "từ Thứ Hai" not in t_trong
assert "2. Tiền lương thực nhận hằng tháng" in t_trong or "3. Tiền lương thực nhận" in t_trong
assert "theo giờ" in t and "26.000 đồng/giờ" in t and "dưới 2.340.000 đồng/tháng" in t and "Phụ cấp lương và các khoản bổ sung khác: không có" in t
assert "Do thời giờ làm việc và mức tiền lương tháng không đạt mức tối thiểu làm căn cứ đóng bảo hiểm xã hội bắt buộc theo quy định của Luật Bảo hiểm xã hội, Người lao động không thuộc đối tượng tham gia bảo hiểm xã hội, bảo hiểm y tế, bảo hiểm thất nghiệp bắt buộc." in t
# lương dự kiến từ ngưỡng trở lên thì KHÔNG ghi câu "không thuộc đối tượng"
h2 = v.dung_hop_dong_part_time(nv[1], CTY, {"pt_gio_ngay": "4", "pt_ngay_tuan": 6}, 0, nam=2026)
t2_ = van_ban(h2)
assert "không thuộc đối tượng tham gia" not in t2_ and "thuộc đối tượng tham gia bảo hiểm xã hội bắt buộc: Công ty và Người lao động cùng tham gia" in t2_
cb = v.kiem_tra_part_time([nv[1]], v.gop_tuy_chon(CTY, {"pt_gio_ngay": "4", "pt_ngay_tuan": 6}), 2026)
assert any(c["muc"] == "loi" and "thuộc đối tượng tham gia BHXH bắt buộc" in c["nd"] for c in cb)
# thiếu dữ liệu / sai: cảnh báo
cb = v.kiem_tra_part_time([dict(nv[1], luong_gio=0)], v.gop_tuy_chon(CTY, {}), 2026)
assert not any("chưa ghi số giờ" in c["nd"] for c in cb) and any("chưa có lương theo giờ" in c["nd"] for c in cb), "giờ theo lịch sắp xếp: không bắt buộc ghi giờ/ngày"
cb = v.kiem_tra_part_time([nv[1]], v.gop_tuy_chon(CTY, {"pt_gio_ngay": "8"}), 2026)
assert any("không ngắn hơn" in c["nd"] for c in cb)
cb = v.kiem_tra_part_time([dict(nv[1], luong_gio=20000)], v.gop_tuy_chon(CTY, {"pt_gio_ngay": "2"}), 2026)
assert any("thấp hơn mức lương tối thiểu giờ" in c["nd"] for c in cb)
assert v.luong_toi_thieu_gio(2026, 1) == 25500 and v.luong_toi_thieu_gio(2024, 1) == 23800
# nhiều hợp đồng
assert v.dung_hop_dong_part_time_nhieu(nv[1:], CTY, tc, nam=2026).count('<section class="vb-trang">') == 1
# THÁNG LÀM của người part-time theo Danh Sách NV: từ "Tháng/Năm vào làm" đến "Tháng/Năm nghỉ việc"; trống = như người thường
ptr = [R(**{'Mã NV': '9', 'Họ và tên': 'PT', 'Part-time': 'x', 'Lương theo giờ': 26000, 'Tháng/Năm vào làm': '03/2026', 'Tháng/Năm nghỉ việc': '08/2026', 'Chức vụ': 'Bảo vệ'})]
co = [t for t in range(1, 13) if server._luong_dong_tu_nhan_vien(H, ptr, 0, 2026, t)]
assert co == [3, 4, 5, 6, 7, 8], co
assert all(server._luong_dong_tu_nhan_vien(H, ptr, 0, 2026, t)[0]["part_time"] == 1 for t in co)
assert not server._luong_dong_tu_nhan_vien(H, ptr, 0, 2025, 12) and not server._luong_dong_tu_nhan_vien(H, ptr, 0, 2027, 1)
ptr2 = [R(**{'Mã NV': '9', 'Họ và tên': 'PT', 'Part-time': 'x', 'Lương theo giờ': 26000})]
assert all(server._luong_dong_tu_nhan_vien(H, ptr2, 0, 2026, t) for t in range(1, 13)), "không ghi vào làm/nghỉ việc: như bình thường (cả năm)"

# kế hoạch cả năm: người part-time được THÊM vào từng tháng đúng khoảng làm việc, giờ làm để trống (0 đồng)
import asyncio
rows_kh = [R(**{'Mã NV': '1', 'Họ và tên': 'Toàn thời gian', 'Đóng BHXH': 'x', 'Tháng/Năm vào làm': '01/2025', 'Lương Cơ bản': 6000000, 'Chức vụ': 'Nhân viên'})] + ptr
server.nhap_lieu_get = lambda cid, loai="in": {"header": H, "rows": rows_kh} if loai == "nv" else {"header": [], "rows": []}
class Req:
    def __init__(self, b): self.b = b
    async def json(self): return self.b
kq = asyncio.run(server.bang_luong_ke_hoach(7, Req({"nam": 2026, "tu_thang": 1, "den_thang": 12, "muc_tieu": 120000000, "seed": 1})))
for t, rs in kq["thang"].items():
    ten_pt = [r for r in rs if r.get("part_time")]
    assert bool(ten_pt) == (3 <= int(t) <= 8), (t, len(ten_pt))
    assert all(r["gio_lam"] == "" and r["chi_phi_luong"] == 0 for r in ten_pt), "giờ làm để trống, không tự đặt"
assert any("part-time" in c.lower() for c in kq["tom_tat"]["canh_bao"])
# đối chiếu theo NĂM LẬP của văn bản (không theo ngày hôm nay): hợp đồng năm 2025 dùng lương tối thiểu 2025 (4.960.000), không báo lỗi lương 5.100.000
assert server._vb_tc_kiem_tra({"ngay": "05/10/2026"}, 2025, "hd")["ngay"] == "01/01/2025" and server._vb_tc_kiem_tra({"ngay_ky": "15/03/2025"}, 2025, "pt")["ngay"] == "15/03/2025"
assert server._vb_tc_kiem_tra({"ngay": "02/01/2026"}, 2026, "qc")["ngay"] == "02/01/2026", "quy chế/thang lương giữ ngày ban hành"
nv_l = [dict(nv[0], luong_cb=5100000.0, tien_com=0.0, xang_xe=0.0, dien_thoai=0.0, trang_phuc=0.0)]
cb25 = v.kiem_tra(nv_l, 2025, v.gop_tuy_chon(CTY, server._vb_tc_kiem_tra({"ngay": "05/10/2026"}, 2025, "hd")), {})
assert not any("thấp hơn lương tối thiểu" in c["nd"] for c in cb25), cb25
cb26 = v.kiem_tra(nv_l, 2026, v.gop_tuy_chon(CTY, {"ngay": "05/10/2026"}), {})
assert any("thấp hơn lương tối thiểu" in c["nd"] for c in cb26)
# hợp đồng lao động / thử việc: xếp theo ngày bắt đầu TĂNG DẦN, STT + số hợp đồng theo thứ tự mới
ds_s = [dict(ten="C", stt=1, vao_lam="15/05/2025", thu_viec_tu="20/04/2025"), dict(ten="A", stt=2, vao_lam="01/2024", thu_viec_tu=""), dict(ten="B", stt=3, vao_lam="03/2025", thu_viec_tu="01/03/2025"),
        dict(ten="D", stt=4, vao_lam="", thu_viec_tu="10/01/2025"), dict(ten="E", stt=5, vao_lam="03/2025", thu_viec_tu="")]
hd_s = server._vb_sap_theo_ngay(ds_s, 2025, "hd")
assert [(n["stt"], n["ten"]) for n in hd_s] == [(1, "A"), (2, "D"), (3, "B"), (4, "E"), (5, "C")], [(n["stt"], n["ten"]) for n in hd_s]     # A (vào làm 2024 -> 01/01/2025), D (không ghi -> 01/01/2025), B, E (03/2025), C (15/05)
tv_s = server._vb_sap_theo_ngay(ds_s, 2025, "tv")
assert [(n["stt"], n["ten"]) for n in tv_s] == [(1, "D"), (2, "B"), (3, "C"), (4, "A"), (5, "E")], "xếp theo ngày bắt đầu thử việc; người chưa có thử việc xếp cuối, giữ thứ tự cũ"
assert [n["stt"] for n in ds_s] == [1, 2, 3, 4, 5], "không đổi danh sách gốc"
h_hd = v.dung_hop_dong_nhieu(hd_s, CTY, {}, nam=2025)
sp = __import__("re").findall(r"Số: (\d+)/HĐLĐ-2025.*?ngày (\d+) tháng (\d+) năm 2025", h_hd, flags=__import__("re").S)
assert [x[0] for x in sp] == ["01", "02", "03", "04", "05"] and [(x[2]) for x in sp] == ["01", "01", "03", "03", "05"], sp
print("PASS")
