import os, sys, asyncio, sqlite3, tempfile, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server
import van_ban_lao_dong as vbld

# Hợp đồng lao động: người có mã phiên bản (gốc-001, -002...) đổi LƯƠNG -> hợp đồng theo mức lương ban đầu + tự tạo PHỤ LỤC HỢP ĐỒNG ghi mức lương mới, áp dụng từ ngày nào.
H = server.NV_HEADERS
def R(**k):
    r = [''] * len(H)
    for a, b in k.items(): r[H.index(a)] = b
    return r
ROWS = [
    R(**{'STT': 1, 'Mã NV': '1', 'Họ và tên': 'Dương Thị Hiền', 'CCCD': '079190000101', 'Tháng/Năm vào làm': '03/2022', 'Đóng BHXH': 'x', 'Chức vụ': 'Giám đốc', 'Lương Cơ bản': 6_000_000}),
    R(**{'STT': 2, 'Mã NV': '1-001', 'Họ và tên': 'Dương Thị Hiền', 'CCCD': '079190000101', 'Tháng/Năm vào làm': '05/2025', 'Đóng BHXH': 'x', 'Chức vụ': 'Giám đốc', 'Lương Cơ bản': 7_000_000}),
    R(**{'STT': 3, 'Mã NV': '1-002', 'Họ và tên': 'Dương Thị Hiền', 'CCCD': '079190000101', 'Tháng/Năm vào làm': '15/10/2025', 'Đóng BHXH': 'x', 'Chức vụ': 'Giám đốc', 'Lương Cơ bản': 8_000_000}),
    # chỉ đổi chức vụ, lương giữ nguyên -> KHÔNG có phụ lục
    R(**{'STT': 4, 'Mã NV': '2', 'Họ và tên': 'Lê Đức Tấn', 'CCCD': '079190000102', 'Tháng/Năm vào làm': '01/2024', 'Đóng BHXH': 'x', 'Chức vụ': 'Bảo vệ', 'Lương Cơ bản': 5_310_000}),
    R(**{'STT': 5, 'Mã NV': '2-001', 'Họ và tên': 'Lê Đức Tấn', 'CCCD': '079190000102', 'Tháng/Năm vào làm': '07/2025', 'Đóng BHXH': 'x', 'Chức vụ': 'Quản lý', 'Lương Cơ bản': 5_310_000}),
    # part-time -> toàn thời gian (2-001 kiểu cũ): hợp đồng toàn thời gian từ ngày chuyển, không phụ lục
    R(**{'STT': 6, 'Mã NV': '3', 'Họ và tên': 'Nguyễn Văn Khoan', 'CCCD': '079190000103', 'Tháng/Năm vào làm': '01/2024', 'Part-time': 'x', 'Lương theo giờ': 25_000}),
    R(**{'STT': 7, 'Mã NV': '3-001', 'Họ và tên': 'Nguyễn Văn Khoan', 'CCCD': '079190000103', 'Tháng/Năm vào làm': '12/2024', 'Đóng BHXH': 'x', 'Chức vụ': 'Bảo vệ', 'Lương Cơ bản': 5_500_000}),
    # đổi lương năm trước -> hợp đồng 2025 đã theo lương mới, không phụ lục
    R(**{'STT': 8, 'Mã NV': '4', 'Họ và tên': 'Lý Thị Thu Hiền', 'CCCD': '079190000104', 'Tháng/Năm vào làm': '01/2023', 'Đóng BHXH': 'x', 'Chức vụ': 'Kế toán', 'Lương Cơ bản': 5_000_000}),
    R(**{'STT': 9, 'Mã NV': '4-001', 'Họ và tên': 'Lý Thị Thu Hiền', 'CCCD': '079190000104', 'Tháng/Năm vào làm': '06/2024', 'Đóng BHXH': 'x', 'Chức vụ': 'Kế toán', 'Lương Cơ bản': 5_600_000}),
    # đổi lương năm sau -> chưa có trong hợp đồng 2025
    R(**{'STT': 10, 'Mã NV': '5', 'Họ và tên': 'Trần Quốc Huy', 'CCCD': '079190000105', 'Tháng/Năm vào làm': '02/2025', 'Đóng BHXH': 'x', 'Chức vụ': 'Bảo vệ', 'Lương Cơ bản': 5_400_000}),
    R(**{'STT': 11, 'Mã NV': '5-001', 'Họ và tên': 'Trần Quốc Huy', 'CCCD': '079190000105', 'Tháng/Năm vào làm': '01/2026', 'Đóng BHXH': 'x', 'Chức vụ': 'Bảo vệ', 'Lương Cơ bản': 6_000_000}),
]
BL = {}
nam = 2025

# --- thuần: lịch sử lương
ls = vbld.lich_su_luong_hop_dong(H, ROWS, BL, nam)
x = ls[("ma", "1")]
assert x["vao_lam"] == "03/2022" and x["ban_dau"]["luong_cb"] == 6_000_000 and x["ban_dau"]["ma"] == "1"
assert [(d["tu"], d["cu"]["luong_cb"], d["nv"]["luong_cb"]) for d in x["dieu_chinh"]] == [
    (datetime.date(2025, 5, 1), 6_000_000, 7_000_000), (datetime.date(2025, 10, 15), 7_000_000, 8_000_000)], x["dieu_chinh"]
assert ls[("ma", "2")]["dieu_chinh"] == [], "chỉ đổi chức vụ: không phụ lục"
assert ("ma", "3") not in ls, "chỉ 1 phiên bản toàn thời gian (dòng part-time không tính)"
assert ls[("ma", "4")]["ban_dau"]["luong_cb"] == 5_600_000 and ls[("ma", "4")]["dieu_chinh"] == [], "đổi lương năm trước: hợp đồng theo lương mới"
assert ls[("ma", "5")]["ban_dau"]["luong_cb"] == 5_400_000 and ls[("ma", "5")]["dieu_chinh"] == [], "đổi lương năm sau: chưa có phụ lục"
# Bảng lương tháng áp dụng là số thực trả -> ưu tiên
ls2 = vbld.lich_su_luong_hop_dong(H, ROWS, {"05": [{"ma": "1-001", "ten": "Dương Thị Hiền", "luong_cb": 7_200_000}]}, nam)
assert ls2[("ma", "1")]["dieu_chinh"][0]["nv"]["luong_cb"] == 7_200_000 and ls2[("ma", "1")]["dieu_chinh"][1]["cu"]["luong_cb"] == 7_200_000
assert vbld.lich_su_luong_hop_dong(H, [r for r in ROWS if '-' not in str(r[H.index('Mã NV')])], BL, nam) == {}, "không có mã phiên bản: không có gì"
print("PASS 1: lịch sử lương theo mã phiên bản")

# --- API: hợp đồng + phụ lục
conn = sqlite3.connect(":memory:", check_same_thread=False); conn.row_factory = sqlite3.Row
conn.execute("CREATE TABLE companies (id INTEGER, ten TEXT, mst TEXT, dia_chi TEXT, nguoi_ky TEXT)")
conn.execute("INSERT INTO companies VALUES (7, 'CÔNG TY TNHH THỬ', '0300000001', '1 Lê Lợi, Quận 1, Thành phố Hồ Chí Minh', 'Dương Thị Hiền')")
class KhongDong:
    def __init__(self, c): self.c = c
    def execute(self, *a): return self.c.execute(*a)
    def commit(self): self.c.commit()
    def close(self): pass
server.db = lambda: KhongDong(conn)
server.nhap_lieu_get = lambda cid, loai="in": {"header": H, "rows": ROWS} if loai == "nv" else {"header": [], "rows": []}
server._luong_doc_nam = lambda cid, nam: (server._luong_chuan_tham_so(None, nam), BL, "", [nam])
server._vb_chu_ky_dict = lambda cid: {}
server._pt_nguoi_trong_nam = lambda cid, nam: set()
server.DOWNLOAD_DIR = tempfile.mkdtemp()
class Req:
    def __init__(self, b): self.b = b
    async def json(self): return self.b
r = asyncio.run(server.van_ban_xem_truoc(7, Req({"loai": "hd", "nam": nam, "tuy_chon": {"nguoi_ky": "Dương Thị Hiền"}})))
h = r["html"]
assert r["so_van_ban"] == 5 and r["so_phu_luc"] == 2, (r["so_van_ban"], r["so_phu_luc"])
assert h.count('<section class="vb-trang">') == 7 and h.count("PHỤ LỤC HỢP ĐỒNG LAO ĐỘNG</b>") == 2
# hợp đồng của Dương Thị Hiền: lương ban đầu 6.000.000, bắt đầu 01/01/2025 (vào làm 03/2022), phụ lục ngay sau
i_hd = h.index("DƯƠNG THỊ HIỀN</b>&nbsp;&nbsp;&nbsp;Quốc tịch")
sec = h[h.rindex('<section', 0, i_hd):]
hd1 = sec[:sec.index('</section>')]
assert "6.000.000 đồng/tháng" in hd1 and "7.000.000" not in hd1 and "ngày 01 tháng 01 năm 2025" in hd1
so_hd = hd1.split("Số: ")[1].split("<")[0]
pl = sec[sec.index('</section>'):]
assert pl.index("PHỤ LỤC HỢP ĐỒNG LAO ĐỘNG") < pl.index("PHỤ LỤC HỢP ĐỒNG LAO ĐỘNG", pl.index("PHỤ LỤC HỢP ĐỒNG LAO ĐỘNG") + 5)
pl1 = pl[pl.index('<section'):pl.index('</section>', pl.index('<section'))]
assert f"Căn cứ Hợp đồng lao động số {so_hd} ký ngày 01/01/2025" in pl1 and "Số: 01/2025/PL-" + so_hd in pl1
assert "Mức lương trước khi điều chỉnh: 6.000.000 đồng/tháng" in pl1 and "<b>7.000.000 đồng/tháng</b>" in pl1 and "kể từ <b>ngày 01 tháng 05 năm 2025</b>" in pl1
assert "bảo hiểm thất nghiệp kể từ ngày áp dụng là 7.000.000 đồng/tháng" in pl1 and "ngày 01 tháng 05 năm 2025" in pl1.split("PHỤ LỤC")[0], "ngày lập phụ lục = ngày áp dụng"
assert "Chức danh chuyên môn" not in pl1, "chức vụ không đổi thì không ghi"
assert "Mức lương trước khi điều chỉnh: 7.000.000" in h and "<b>8.000.000 đồng/tháng</b>" in h and "kể từ <b>ngày 15 tháng 10 năm 2025</b>" in h
assert "LÊ ĐỨC TẤN" in h and "NGUYỄN VĂN KHOAN" in h
i_k = h.index("NGUYỄN VĂN KHOAN</b>&nbsp;&nbsp;&nbsp;Quốc tịch"); hk = h[h.rindex('<section', 0, i_k):]; hk = hk[:hk.index('</section>')]
assert "5.500.000 đồng/tháng" in hk and "ngày 01 tháng 01 năm 2025" in hk, "chuyển part-time -> toàn thời gian 12/2024: hợp đồng 2025 từ 01/01/2025"
# lương phụ lục thấp hơn tối thiểu vùng -> báo lỗi
ROWS[2][H.index('Lương Cơ bản')] = 4_000_000
r = asyncio.run(server.van_ban_xem_truoc(7, Req({"loai": "hd", "nam": nam, "tuy_chon": {}})))
assert any(c["muc"] == "loi" and "phụ lục từ 15/10/2025" in c["nd"] for c in r["canh_bao"]), r["canh_bao"]
# in 1 người không có phiên bản: không phụ lục
r = asyncio.run(server.van_ban_xem_truoc(7, Req({"loai": "hd", "nam": nam, "tu": 4, "den": 4, "tuy_chon": {}})))
assert r["so_phu_luc"] == 0 and r["html"].count('<section class="vb-trang">') == 1
# Word: phụ lục ra trang riêng
data = server.vbld.html_sang_docx(h, {})
assert data[:2] == b"PK"
print("PASS 2: hợp đồng lao động kèm phụ lục điều chỉnh lương")

# danh sách chọn Từ/Đến của màn hình phải cùng thứ tự (STT) với hợp đồng dựng ra
ROWS[2][H.index('Lương Cơ bản')] = 8_000_000
ROWS.append(R(**{'STT': 12, 'Mã NV': '6', 'Họ và tên': 'Huỳnh Văn Vinh', 'CCCD': '079190000106', 'Tháng/Năm vào làm': '03/2025', 'Đóng BHXH': 'x', 'Chức vụ': 'Bảo vệ', 'Lương Cơ bản': 5_400_000}))
ROWS.append(R(**{'STT': 13, 'Mã NV': '7', 'Họ và tên': 'Phạm Bảo Vương', 'CCCD': '079190000107', 'Tháng/Năm vào làm': '02/2025', 'Đóng BHXH': 'x', 'Chức vụ': 'Bảo vệ', 'Lương Cơ bản': 5_400_000}))
ROWS.append(R(**{'STT': 14, 'Mã NV': '7-001', 'Họ và tên': 'Phạm Bảo Vương', 'CCCD': '079190000107', 'Tháng/Năm vào làm': '08/2025', 'Đóng BHXH': 'x', 'Chức vụ': 'Bảo vệ', 'Lương Cơ bản': 5_800_000}))
d = server.van_ban_du_lieu(7, nam)
for n in d["nhan_vien_hd"]:
    r = asyncio.run(server.van_ban_xem_truoc(7, Req({"loai": "hd", "nam": nam, "tu": n["stt"], "den": n["stt"], "tuy_chon": {}})))
    assert n["ten"].upper() + "</b>&nbsp;&nbsp;&nbsp;Quốc tịch" in r["html"], (n, "STT lệch giữa danh sách chọn và hợp đồng")
vuong = next(n for n in d["nhan_vien_hd"] if n["ten"] == "Phạm Bảo Vương")
vinh = next(n for n in d["nhan_vien_hd"] if n["ten"] == "Huỳnh Văn Vinh")
assert vuong["stt"] < vinh["stt"] and vuong["luong_cb"] == 5_400_000, "Vương vào làm 02/2025 (dòng gốc) xếp trước Vinh 03/2025, lương hợp đồng = lương ban đầu"
print("PASS 3: danh sách chọn cùng thứ tự với hợp đồng")
print("ALL DONE")
