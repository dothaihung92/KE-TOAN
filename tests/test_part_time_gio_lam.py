import os, sys, io, asyncio, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server, openpyxl
from fastapi import HTTPException

# File MẪU + IMPORT giờ làm của lao động part-time (giờ theo tháng và/hoặc theo ngày; mỗi ngày tối đa 8 giờ, quá thì BÁO LỖI, không tự dồn sang ngày khác)
H = server.NV_HEADERS
def R(**k):
    r = [''] * len(H)
    for a, b in k.items():
        r[H.index(a)] = b
    return r
rows = [R(**{'Mã NV': '1', 'Họ và tên': 'Toàn Thời Gian', 'Đóng BHXH': 'x', 'Tháng/Năm vào làm': '01/2025', 'Lương Cơ bản': 6000000}),
        R(**{'Mã NV': 'P1', 'Họ và tên': 'Lê Bán Thời', 'Part-time': 'x', 'Lương theo giờ': 26000, 'Tháng/Năm vào làm': '03/2026', 'Tháng/Năm nghỉ việc': '08/2026'}),
        R(**{'Mã NV': 'P2', 'Họ và tên': 'Phạm Giờ Giấc', 'Part-time': 'x', 'Lương theo giờ': 30000, 'Tháng/Năm vào làm': '01/2025'})]
server.nhap_lieu_get = lambda cid, loai="in": {"header": H, "rows": rows} if loai == "nv" else {"header": [], "rows": []}
server.DOWNLOAD_DIR = tempfile.mkdtemp()
server._copy_ra_desktop = lambda p, f: None

ds = server._pt_nguoi_trong_nam(7, 2026)
assert sorted(e["ten"] for e in ds.values()) == ["Lê Bán Thời", "Phạm Giờ Giấc"] and ds["p1"]["thang"] == [3, 4, 5, 6, 7, 8] and ds["p2"]["thang"] == list(range(1, 13))

# mẫu: chỉ người part-time, ô ngoài khoảng làm việc tô xám
resp = server.bang_luong_mau_gio_lam(7, 2026)
wb = openpyxl.load_workbook(resp.path)
ws = wb["Giờ theo tháng"]
assert [c.value for c in ws[1]][:4] == ["Mã NV", "Họ và tên", "Lương theo giờ", "T1"]
nguoi = {ws.cell(r, 1).value: r for r in range(2, 6) if ws.cell(r, 2).value}
assert set(nguoi) == {"P1", "P2"}
CT = lambda m: 3 + m           # cột của tháng m
assert ws.cell(nguoi["P1"], CT(1)).fill.fgColor.rgb.endswith("DDDDDD") and not ws.cell(nguoi["P1"], CT(3)).fill.fgColor.rgb.endswith("DDDDDD")
w2 = wb["Giờ theo ngày"]
assert sum(1 for r in range(2, 40) if w2.cell(r, 1).value == "P1") == 6 and sum(1 for r in range(2, 40) if w2.cell(r, 1).value == "P2") == 12

def import_(wb2):
    b = io.BytesIO(); wb2.save(b)
    class Up:
        async def read(self): return b.getvalue()
    class Req:
        async def form(self_): return {"file": Up(), "nam": "2026"}
    return asyncio.run(server.bang_luong_nhap_gio_lam(7, Req()))

# giờ theo tháng: P1 T3=43,3 ; T4=30 ; T2 (ngoài khoảng làm việc) ; T5=9999 (vượt tối đa) ; P2 T1=40 ; thêm người toàn thời gian + người lạ
ws.cell(nguoi["P1"], CT(3)).value = "43,3"; ws.cell(nguoi["P1"], CT(4)).value = 30
ws.cell(nguoi["P1"], CT(2)).value = 20
ws.cell(nguoi["P1"], CT(5)).value = 9999
ws.cell(nguoi["P2"], CT(1)).value = 40
ws.append(["1", "Toàn Thời Gian", None, 10]); ws.append(["X9", "Người Lạ", None, 5])
kq = import_(wb)
gio = {e["ma"]: e for e in kq["gio"]}
assert gio["P1"]["thang"] == {"03": 43.3, "04": 30.0} and gio["P2"]["thang"] == {"01": 40.0} and set(gio) == {"P1", "P2"}
ld = " ".join(kq["loi"]); cb = " ".join(kq["canh_bao"])
assert "vượt tối đa 8 giờ" in ld and "Người Lạ" in ld and "Toàn Thời Gian" in ld, kq["loi"]
assert "ngoài khoảng vào làm/nghỉ việc" in cb, kq["canh_bao"]

# giờ theo NGÀY: mỗi ngày tối đa 8 giờ; có dữ liệu theo ngày thì dùng (tổng giờ = cộng ngày), ghi đè giờ theo tháng
for r in range(2, 40):
    if w2.cell(r, 1).value == "P1" and w2.cell(r, 3).value == 3:
        for d, v in ((2, 2), (3, 2), (4, "2,5"), (5, 8)):
            w2.cell(r, 3 + d).value = v
    if w2.cell(r, 1).value == "P1" and w2.cell(r, 3).value == 4:
        w2.cell(r, 3 + 7).value = 9          # 9 giờ trong 1 ngày -> lỗi, không tự dồn sang ngày khác
    if w2.cell(r, 1).value == "P2" and w2.cell(r, 3).value == 2:
        w2.cell(r, 3 + 31).value = 4         # tháng 2/2026 không có ngày 31
kq = import_(wb)
gio = {e["ma"]: e for e in kq["gio"]}
assert gio["P1"]["ngay"] == {"03": {"2": 2.0, "3": 2.0, "4": 2.5, "5": 8.0}} and gio["P1"]["thang"]["03"] == 14.5, "tổng = cộng các ngày, thay giờ theo tháng 43,3"
assert gio["P1"]["thang"]["04"] == 30.0 and "04" not in gio["P1"]["ngay"], "ngày vượt 8 giờ: bỏ cả dòng theo ngày, giữ giờ theo tháng"
assert any("(ngày 7): 9 giờ vượt tối đa 8 giờ/ngày" in x and "không tự dồn" in x for x in kq["loi"]) and any("không có ngày 31" in x for x in kq["loi"])
assert any("43,3" in x or "43.3" in x for x in kq["canh_bao"]) or any("khác giờ theo tháng" in x for x in kq["canh_bao"])
# file không có sheet hợp lệ: không lỗi, rỗng
assert import_(openpyxl.Workbook())["so_nguoi"] == 0
print("PASS")
