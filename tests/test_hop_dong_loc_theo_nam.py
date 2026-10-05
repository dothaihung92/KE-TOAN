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
