import os, sys, asyncio, sqlite3, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Năm sau đổi lương (vd 2025: 5.300.000 -> 2026: 5.682.000): hợp đồng năm trước CÒN HIỆU LỰC thì chỉ lập PHỤ LỤC điều chỉnh lương (căn cứ hợp đồng cũ),
# hết hạn (xác định thời hạn 12 tháng) thì lập hợp đồng mới + giải thích; ký quá 2 lần hợp đồng xác định thời hạn -> báo lỗi Điều 20.
H = server.NV_HEADERS
def R(**k):
    r = [''] * len(H)
    for a, b in k.items(): r[H.index(a)] = b
    return r
def nv(ma, ten, vao, luong):
    return R(**{'Mã NV': ma, 'Họ và tên': ten, 'CCCD': '0791900001' + ma.zfill(2), 'Tháng/Năm vào làm': vao, 'Đóng BHXH': 'x', 'Chức vụ': 'Bảo vệ', 'Lương Cơ bản': luong})
ROWS = [nv('1', 'Lâm Thái Huy', '03/2022', 5_300_000), nv('2', 'Phạm Bảo Vương', '01/2024', 5_300_000), nv('3', 'Huỳnh Văn Vinh', '03/2026', 5_682_000),
        nv('4', 'Đặng Ngọc Thanh', '06/2024', 5_682_000)]
def bl(ma, ten, luong): return {"ma": ma, "ten": ten, "luong_cb": luong, "chuc_vu": "Bảo vệ", "dong_bh": True}
BL = {2025: {"%02d" % t: [bl('1', 'Lâm Thái Huy', 5_300_000), bl('2', 'Phạm Bảo Vương', 5_300_000)] for t in range(1, 13)},
      2026: {"01": [bl('1', 'Lâm Thái Huy', 5_682_000), bl('2', 'Phạm Bảo Vương', 5_300_000), bl('4', 'Đặng Ngọc Thanh', 5_682_000)]}}
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
server._luong_doc_nam = lambda cid, nam: (server._luong_chuan_tham_so(None, nam), BL.get(nam, {}), "", sorted(BL, reverse=True))
server._vb_chu_ky_dict = lambda cid: {}
server._pt_nguoi_trong_nam = lambda cid, nam: set()
server.DOWNLOAD_DIR = tempfile.mkdtemp()
class Req:
    def __init__(self, b): self.b = b
    async def json(self): return self.b
def tao(nam, **tc):
    return asyncio.run(server.van_ban_xem_truoc(7, Req({"loai": "hd", "nam": nam, "tuy_chon": tc})))
def doan(h, ten):
    i = h.index(ten.upper() + "</b>")
    s = h[h.rindex('<section', 0, i):]
    return s[:s.index('</section>')]

# 1) chưa lưu cấu hình năm 2025, đang chọn KHÔNG xác định thời hạn -> giả định hợp đồng 2025 cũng vậy -> 2026 chỉ phụ lục
r = tao(2026, loai_hd="kxdth")
h = r["html"]
assert r["so_phu_luc"] == 1 and r["so_van_ban"] == 2, (r["so_van_ban"], r["so_phu_luc"])
p = doan(h, "Lâm Thái Huy")
assert "PHỤ LỤC HỢP ĐỒNG LAO ĐỘNG" in p
assert "Căn cứ Hợp đồng lao động số 01/HĐLĐ-2025 ký ngày 01/01/2025" in p and "Số: 01/2026/PL-01/HĐLĐ-2025" in p
assert "Mức lương trước khi điều chỉnh: 5.300.000 đồng/tháng" in p and "<b>5.682.000 đồng/tháng</b>" in p and "kể từ <b>ngày 01 tháng 01 năm 2026</b>" in p
assert h.count("LÂM THÁI HUY</b>&nbsp;&nbsp;&nbsp;Quốc tịch") == 0, "không lập hợp đồng mới cho người còn hợp đồng"
assert "PHẠM BẢO VƯƠNG" not in h, "lương không đổi, hợp đồng còn hiệu lực: không có văn bản"
assert "HUỲNH VĂN VINH</b>&nbsp;&nbsp;&nbsp;Quốc tịch" in h, "vào làm 2026: hợp đồng mới"
assert "ĐẶNG NGỌC THANH</b>&nbsp;&nbsp;&nbsp;Quốc tịch" in h, "chưa có trong Bảng lương năm trước: hợp đồng mới"
nd = " | ".join(c["nd"] for c in r["canh_bao"])
assert "2 người có hợp đồng lao động từ năm trước CÒN HIỆU LỰC" in nd and "Phạm Bảo Vương" in nd and "GIẢ ĐỊNH" in nd, nd
print("PASS 1: hợp đồng còn hiệu lực -> chỉ phụ lục điều chỉnh lương")

# 2) đang chọn xác định thời hạn 12 tháng -> hợp đồng 2025 hết hạn 31/12/2025 -> hợp đồng mới + giải thích
r = tao(2026, loai_hd="xdth", so_thang=12)
h = r["html"]
assert r["so_phu_luc"] == 0 and "LÂM THÁI HUY</b>&nbsp;&nbsp;&nbsp;Quốc tịch" in h and "5.682.000 đồng/tháng" in doan(h, "Lâm Thái Huy")
nd = " | ".join(c["nd"] for c in r["canh_bao"])
assert "HẾT HẠN trước 01/01/2026" in nd and "Lâm Thái Huy (năm 2025: 01/01/2025 – 31/12/2025)" in nd and "Không xác định thời hạn" in nd, nd
print("PASS 2: hợp đồng 12 tháng đã hết hạn -> hợp đồng mới + giải thích")

# 3) năm 2025 đã lập với KHÔNG xác định thời hạn (phần mềm lưu lại) -> 2026 dù đang chọn 12 tháng vẫn biết hợp đồng cũ còn hiệu lực
r25 = tao(2025, loai_hd="kxdth")
assert "Số: 01/HĐLĐ-2025" in r25["html"]
r = tao(2026, loai_hd="xdth", so_thang=12)
assert r["so_phu_luc"] == 1 and "Căn cứ Hợp đồng lao động số 01/HĐLĐ-2025" in r["html"] and not any("GIẢ ĐỊNH" in c["nd"] for c in r["canh_bao"])
# 36 tháng (lưu ở 2025) -> còn hiệu lực, báo hết hạn đúng năm
tao(2025, loai_hd="xdth", so_thang=36)
r = tao(2026, loai_hd="xdth", so_thang=12)
assert r["so_phu_luc"] == 1
print("PASS 3: dùng loại hợp đồng đã lưu của năm gốc")

# 4) 2 hợp đồng 12 tháng liên tiếp (2024, 2025) -> 2026 phải không xác định thời hạn (Điều 20)
BL[2024] = {"01": [bl('2', 'Phạm Bảo Vương', 5_000_000)]}
tao(2024, loai_hd="xdth", so_thang=12); tao(2025, loai_hd="xdth", so_thang=12)
r = tao(2026, loai_hd="xdth", so_thang=12)
assert any(c["muc"] == "loi" and "Điều 20" in c["nd"] and "Phạm Bảo Vương" in c["nd"] for c in r["canh_bao"]), r["canh_bao"]
assert any("Điều 20" in c["nd"] and "Lâm Thái Huy" in c["nd"] for c in r["canh_bao"]), "Huy có trong danh sách hợp đồng phần mềm đã lập năm 2024 -> cũng đã 2 hợp đồng"
assert not any("Điều 20" in c["nd"] and "Huỳnh Văn Vinh" in c["nd"] for c in r["canh_bao"]), "Vinh vào làm 2026: hợp đồng đầu tiên"
print("PASS 4: cảnh báo ký quá 2 hợp đồng xác định thời hạn")

# 5) đúng dữ liệu người dùng: KHÔNG có Bảng Lương, Danh Sách NV ghi dòng gốc vào làm 01/01/2025 (5.300.000) + dòng -001 vào làm 01/2026 (5.682.000)
ROWS[:] = [nv('1', 'Dương Thị Hiền', '01/01/2025', 5_300_000), nv('1-001', 'Dương Thị Hiền', '01/2026', 5_682_000),
           nv('2', 'Nguyễn Văn Khoan', '01/01/2025', 5_300_000)]
BL.clear()
conn.execute("DELETE FROM hop_dong_cfg")
r25 = tao(2025, loai_hd="kxdth")
assert r25["so_phu_luc"] == 0 and "5.300.000 đồng/tháng" in doan(r25["html"], "Dương Thị Hiền") and "5.682.000" not in r25["html"], "2025: hợp đồng lương cũ, chưa có phụ lục"
r = tao(2026, loai_hd="kxdth")
p = doan(r["html"], "Dương Thị Hiền")
assert r["so_phu_luc"] == 1 and "PHỤ LỤC HỢP ĐỒNG LAO ĐỘNG" in p and "Căn cứ Hợp đồng lao động số 01/HĐLĐ-2025 ký ngày 01/01/2025" in p
assert "Mức lương trước khi điều chỉnh: 5.300.000" in p and "<b>5.682.000 đồng/tháng</b>" in p and "kể từ <b>ngày 01 tháng 01 năm 2026</b>" in p
assert "NGUYỄN VĂN KHOAN" not in r["html"] and r["so_van_ban"] == 0, "Khoan: hợp đồng 2025 còn hiệu lực, lương không đổi -> không có văn bản"
# đã lập 2025 với 12 tháng -> 2026 hợp đồng mới (hết hạn) dù đang chọn không xác định thời hạn
tao(2025, loai_hd="xdth", so_thang=12)
r = tao(2026, loai_hd="kxdth")
assert r["so_phu_luc"] == 0 and "DƯƠNG THỊ HIỀN</b>&nbsp;&nbsp;&nbsp;Quốc tịch" in r["html"] and any("HẾT HẠN" in c["nd"] for c in r["canh_bao"])
print("PASS 5: chỉ có Danh Sách NV (dòng -001 nâng lương) vẫn tự làm phụ lục")
print("ALL DONE")
