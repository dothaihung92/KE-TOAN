import os, sys, asyncio, sqlite3, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server
from fastapi import HTTPException

# Hợp đồng lao động / thử việc lấy từ NGƯỜI CÓ TRONG BẢNG LƯƠNG năm lập (đúng thời điểm làm việc); người trong Danh Sách NV nhưng không có trong Bảng Lương năm đó thì không lập.
H = server.NV_HEADERS
def nv(ma, ten, vao, tv_tu='', tv_den=''):
    r = [''] * len(H)
    for a, b in {'Mã NV': ma, 'Họ và tên': ten, 'CCCD': '0791900001' + ma.zfill(2), 'Tháng/Năm vào làm': vao, 'Đóng BHXH': 'x', 'Chức vụ': 'Bảo vệ',
                 'Lương Cơ bản': 5_310_000, 'Thử việc từ': tv_tu, 'Thử việc đến': tv_den}.items():
        r[H.index(a)] = b
    return r
ROWS = [nv('1', 'Có Đủ Năm', '01/2024'), nv('2', 'Vào Tháng Năm', '01/2025'), nv('3', 'Không Có Trong Bảng Lương', '01/2024'),
        nv('4', 'Thử Việc Trong Bảng', '01/06/2025', '01/04/2025', '31/05/2025'), nv('5', 'Vào Làm Đúng Ngày', '15/03/2025')]
def bl(ma, ten): return {"ma": ma, "ten": ten, "luong_cb": 5_310_000, "chuc_vu": "Bảo vệ", "dong_bh": True}
BL = {2025: {"01": [bl('1', 'Có Đủ Năm')], "02": [bl('1', 'Có Đủ Năm')], "05": [bl('1', 'Có Đủ Năm'), bl('2', 'Vào Tháng Năm')],
             "04": [bl('1', 'Có Đủ Năm'), bl('4', 'Thử Việc Trong Bảng')], "03": [bl('1', 'Có Đủ Năm'), bl('5', 'Vào Làm Đúng Ngày')]}}
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
def tao(loai, nam=2025, **tc):
    return asyncio.run(server.van_ban_xem_truoc(7, Req({"loai": loai, "nam": nam, "tuy_chon": tc})))

d = server.van_ban_du_lieu(7, 2025)
ten = lambda ds: [n["ten"] for n in ds]
assert set(ten(d["nhan_vien_hd"])) == {"Có Đủ Năm", "Vào Tháng Năm", "Thử Việc Trong Bảng", "Vào Làm Đúng Ngày"}, ten(d["nhan_vien_hd"])
assert "Không Có Trong Bảng Lương" not in ten(d["nhan_vien_hd"]) + ten(d["nhan_vien_tv"])
assert any("Không Có Trong Bảng Lương" in c["nd"] and "CÓ TRONG BẢNG LƯƠNG" in c["nd"] for c in d["canh_bao"]), d["canh_bao"]
r = tao("hd", loai_hd="kxdth"); h = r["html"]
assert r["so_van_ban"] == 4 and "KHÔNG CÓ TRONG BẢNG LƯƠNG" not in h
sec = lambda h, t: (lambda i: (lambda s: s[:s.index("</section>")])(h[h.rindex("<section", 0, i):]))(h.index(t.upper() + "</b>&nbsp;&nbsp;&nbsp;Quốc tịch"))
assert "ngày 01 tháng 01 năm 2025" in sec(h, "Có Đủ Năm"), "có từ tháng 1 của bảng lương: 01/01/2025"
# vào làm 01/2025 (Danh Sách NV) nhưng chỉ có trong Bảng Lương từ tháng 5: hợp đồng bắt đầu 01/05/2025 (thời điểm làm việc thực tế)
assert "ngày 01 tháng 05 năm 2025" in sec(h, "Vào Tháng Năm") and "HĐLĐ-2025" in sec(h, "Vào Tháng Năm")
assert "ngày 15 tháng 03 năm 2025" in sec(h, "Vào Làm Đúng Ngày"), "vào làm 15/03 đúng tháng có trong bảng lương: giữ đúng ngày"
assert any("Không Có Trong Bảng Lương" in c["nd"] for c in r["canh_bao"])
# ô nhập tay Ngày bắt đầu vẫn được ưu tiên
assert "ngày 01 tháng 02 năm 2025" in sec(tao("hd", loai_hd="kxdth", bat_dau="01/02/2025")["html"], "Vào Tháng Năm")
# thử việc: chỉ người có trong Bảng Lương năm đó
ROWS.append(nv('6', 'Thử Việc Không Trong Bảng', '01/07/2025', '01/05/2025', '30/06/2025'))
d = server.van_ban_du_lieu(7, 2025)
assert ten(d["nhan_vien_tv"])[0] == "Thử Việc Trong Bảng" and "Thử Việc Không Trong Bảng" not in ten(d["nhan_vien_tv"]) and "Không Có Trong Bảng Lương" not in ten(d["nhan_vien_tv"]), ten(d["nhan_vien_tv"])
r = tao("tv"); assert "THỬ VIỆC KHÔNG TRONG BẢNG" not in r["html"].upper() and "THỬ VIỆC TRONG BẢNG" in r["html"].upper()
# Số hợp đồng + STT của danh sách chọn khớp văn bản
for n in server.van_ban_du_lieu(7, 2025)["nhan_vien_hd"]:
    one = asyncio.run(server.van_ban_xem_truoc(7, Req({"loai": "hd", "nam": 2025, "tu": n["stt"], "den": n["stt"], "tuy_chon": {"loai_hd": "kxdth"}})))
    assert n["ten"].upper() + "</b>&nbsp;&nbsp;&nbsp;Quốc tịch" in one["html"]
# năm chưa có Bảng Lương: lấy theo Danh Sách NV + ghi chú, không bỏ ai
d = server.van_ban_du_lieu(7, 2026)
assert "Không Có Trong Bảng Lương" in ten(d["nhan_vien_hd"]) and any("chưa có Bảng Lương" in c["nd"] for c in d["canh_bao"]), d["canh_bao"]
# người chỉ có trong Bảng Lương (chưa vào Danh Sách NV) vẫn có hợp đồng; người trong Danh Sách NV nhưng không có trong Bảng Lương thì không
BL[2027] = {"01": [bl('99', 'Người Lạ Khác')]}
ROWS[:] = [nv('1', 'Có Đủ Năm', '01/2024')]
r = tao("hd", nam=2027, loai_hd="kxdth")
assert "NGƯỜI LẠ KHÁC" in r["html"] and "CÓ ĐỦ NĂM" not in r["html"] and r["so_van_ban"] == 1
# Bảng Lương năm chỉ có lao động part-time: không có người toàn thời gian nào để lập hợp đồng -> báo rõ
BL[2027] = {"01": [dict(bl('98', 'Chỉ Part-time'), part_time=1, gio_lam=10.0)]}
try:
    tao("hd", nam=2027); raise SystemExit("phải lỗi")
except HTTPException as e:
    assert e.status_code == 404 and "Bảng Lương" in e.detail, e.detail
print("PASS: hợp đồng lấy theo người có trong Bảng Lương")
