import os, sys, asyncio, sqlite3, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server
from fastapi import HTTPException

# Lập hợp đồng năm 2025: người vào làm 03/2026 KHÔNG được có hợp đồng ghi năm 2026 trong danh sách năm 2025; người nghỉ từ năm 2024 cũng không.
H = server.NV_HEADERS
def nv(ma, ten, vao, nghi=''):
    r = [''] * len(H)
    for a, b in {'Mã NV': ma, 'Họ và tên': ten, 'CCCD': '0791900001' + ma.zfill(2), 'Tháng/Năm vào làm': vao, 'Tháng/Năm nghỉ việc': nghi,
                 'Đóng BHXH': 'x', 'Chức vụ': 'Bảo vệ', 'Lương Cơ bản': 5_310_000, 'Thử việc từ': '', }.items():
        r[H.index(a)] = b
    return r
ROWS = [nv('1', 'Dương Thị Hiền', '01/01/2025'), nv('12', 'Huỳnh Văn Sĩ', '05/2025', '01/09/2025'), nv('13', 'Nguyễn Văn Cảnh', '03/2026'),
        nv('14', 'Nguyễn Mạnh Hùng', '01/2023', '01/12/2024'), nv('15', 'Huỳnh Thị Ngọc Lợi', '')]
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
server._luong_doc_nam = lambda cid, nam: (server._luong_chuan_tham_so(None, nam), {}, "", [])
server._vb_chu_ky_dict = lambda cid: {}
_pt_goc = server._pt_nguoi_trong_nam
server._pt_nguoi_trong_nam = lambda cid, nam: set()
server.DOWNLOAD_DIR = tempfile.mkdtemp()
class Req:
    def __init__(self, b): self.b = b
    async def json(self): return self.b

d = server.van_ban_du_lieu(7, 2025)
assert [n["ten"] for n in d["nhan_vien_hd"]] == ['Huỳnh Thị Ngọc Lợi', 'Dương Thị Hiền', 'Huỳnh Văn Sĩ'] or \
       sorted(n["ten"] for n in d["nhan_vien_hd"]) == sorted(['Dương Thị Hiền', 'Huỳnh Văn Sĩ', 'Huỳnh Thị Ngọc Lợi']), d["nhan_vien_hd"]
assert not any(n["ten"] in ("Nguyễn Văn Cảnh", "Nguyễn Mạnh Hùng") for n in d["nhan_vien_hd"] + d["nhan_vien_tv"])
r = asyncio.run(server.van_ban_xem_truoc(7, Req({"loai": "hd", "nam": 2025, "tuy_chon": {"loai_hd": "kxdth"}})))
assert r["so_van_ban"] == 3 and "HĐLĐ-2026" not in r["html"] and "năm 2026" not in r["html"] and "NGUYỄN VĂN CẢNH" not in r["html"] and "NGUYỄN MẠNH HÙNG" not in r["html"]
r = asyncio.run(server.van_ban_xem_truoc(7, Req({"loai": "tv", "nam": 2025, "tuy_chon": {}})))
assert "NGUYỄN VĂN CẢNH" not in r["html"]
# năm 2026: Cảnh có hợp đồng 2026; Sĩ (nghỉ 09/2025) và Hùng không có
d = server.van_ban_du_lieu(7, 2026)
assert sorted(n["ten"] for n in d["nhan_vien_hd"]) == sorted(['Dương Thị Hiền', 'Nguyễn Văn Cảnh', 'Huỳnh Thị Ngọc Lợi'])
r = asyncio.run(server.van_ban_xem_truoc(7, Req({"loai": "hd", "nam": 2026, "tuy_chon": {"loai_hd": "xdth", "so_thang": 12}})))
assert "NGUYỄN VĂN CẢNH" in r["html"] and "ngày 01 tháng 03 năm 2026" in r["html"]
# năm không có ai đang làm -> báo rõ (người không ghi ngày vào làm vẫn giữ lại)
assert [n["ten"] for n in server.van_ban_du_lieu(7, 2020)["nhan_vien_hd"]] == ['Huỳnh Thị Ngọc Lợi']
ROWS.pop()
try:
    asyncio.run(server.van_ban_xem_truoc(7, Req({"loai": "hd", "nam": 2020, "tuy_chon": {}})))
    raise SystemExit("phải lỗi")
except HTTPException as e:
    assert e.status_code == 404 and "Năm 2020" in e.detail
print("PASS: hợp đồng chỉ gồm người có làm việc trong năm lập")

# HỢP ĐỒNG PART-TIME: tương tự — lập năm 2025 không có người vào làm 2026, người chỉ bắt đầu có giờ làm từ 2026, người nghỉ từ 2024
def pt(ma, ten, vao, nghi=''):
    r = [''] * len(H)
    for a, b in {'Mã NV': ma, 'Họ và tên': ten, 'Tháng/Năm vào làm': vao, 'Tháng/Năm nghỉ việc': nghi, 'Part-time': 'x', 'Lương theo giờ': 25_000}.items():
        r[H.index(a)] = b
    return r
ROWS[:] = [pt('P1', 'Nguyễn Văn Thơ', '01/2025'), pt('P2', 'Nguyễn Văn Được', '03/2026'), pt('P3', 'Đặng Văn Tèo', '01/2025'),
           pt('P4', 'Trương Thanh Bình', '01/2024', '01/12/2024')]
BLP = {2025: {"05": [{"ma": "P1", "ten": "Nguyễn Văn Thơ", "gio_lam": 40.0, "part_time": 1}]},
       2026: {"02": [{"ma": "P3", "ten": "Đặng Văn Tèo", "gio_lam": 35.0, "part_time": 1}], "04": [{"ma": "P2", "ten": "Nguyễn Văn Được", "gio_lam": 42.0, "part_time": 1}]}}
server._luong_doc_nam = lambda cid, nam: (server._luong_chuan_tham_so(None, nam), BLP.get(nam, {}), "", [2026, 2025])
server._pt_nguoi_trong_nam = _pt_goc
server._luong_npt_doc = lambda d: {}
d = server.van_ban_du_lieu(7, 2025)
assert [n["ten"] for n in d["nhan_vien_pt"]] == ["Nguyễn Văn Thơ"], d["nhan_vien_pt"]
r = asyncio.run(server.van_ban_xem_truoc(7, Req({"loai": "pt", "nam": 2025, "tuy_chon": {}})))
assert r["so_van_ban"] == 1 and "NGUYỄN VĂN THƠ" in r["html"] and "2026" not in r["html"] and "ĐẶNG VĂN TÈO" not in r["html"] and "NGUYỄN VĂN ĐƯỢC" not in r["html"]
d = server.van_ban_du_lieu(7, 2026)
assert [n["ten"] for n in d["nhan_vien_pt"]] == ["Nguyễn Văn Thơ", "Đặng Văn Tèo", "Nguyễn Văn Được"], d["nhan_vien_pt"]
print("PASS: hợp đồng part-time chỉ gồm người có làm việc trong năm lập")

# HỢP ĐỒNG THỬ VIỆC: tương tự — thử việc năm khác không lẫn vào năm lập; chưa ghi ngày thử việc thì KHÔNG lấy ngày hôm nay (2026) khi đang lập 2025
def tvr(ma, ten, vao, tv_tu='', tv_den='', nghi=''):
    r = nv(ma, ten, vao, nghi)
    r[H.index('Thử việc từ')], r[H.index('Thử việc đến')] = tv_tu, tv_den
    return r
ROWS[:] = [tvr('1', 'Thử Việc 2025', '01/12/2025', '01/11/2025', '30/11/2025'), tvr('2', 'Thử Việc 2024', '01/2024', '01/12/2023', '31/12/2023'),
           tvr('3', 'Vào Làm 2026', '03/2026', '01/02/2026', '28/02/2026'), tvr('4', 'Không Ghi Ngày', '01/2022'),
           tvr('5', 'Thử Cuối Năm', '15/01/2026', '15/12/2025', '14/01/2026')]
server._luong_doc_nam = lambda cid, nam: (server._luong_chuan_tham_so(None, nam), {}, "", [])
d = server.van_ban_du_lieu(7, 2025)
assert [n["ten"] for n in d["nhan_vien_tv"]] == ['Thử Việc 2025', 'Thử Cuối Năm', 'Không Ghi Ngày'], d["nhan_vien_tv"]
assert "Thử Việc 2024" in [n["ten"] for n in d["nhan_vien_hd"]], "hợp đồng lao động 2025 vẫn có người thử việc từ 2024"
r = asyncio.run(server.van_ban_xem_truoc(7, Req({"loai": "tv", "nam": 2025, "tuy_chon": {}})))
h = r["html"]
assert r["so_van_ban"] == 3 and "THỬ VIỆC 2024" not in h and "VÀO LÀM 2026" not in h and "HĐTV-2026" not in h, h[:300]
i = h.index("KHÔNG GHI NGÀY"); sec = h[h.rindex("<section", 0, i):]; sec = sec[:sec.index("</section>")]
assert "ngày 01 tháng 01 năm 2025" in sec and "năm 2026" not in sec, "chưa ghi ngày thử việc: 01/01 năm lập, không phải hôm nay"
assert [n["ten"] for n in server.van_ban_du_lieu(7, 2026)["nhan_vien_tv"]] == ['Vào Làm 2026', 'Không Ghi Ngày']
print("PASS: hợp đồng thử việc chỉ gồm người thử việc trong năm lập")
