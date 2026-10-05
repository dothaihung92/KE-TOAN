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
# cột cuối = TỔNG TIỀN (tổng giờ × lương giờ) + cột cảnh báo ngưỡng + ô ngưỡng + tô đỏ ô tháng vượt ngưỡng
wb3 = openpyxl.load_workbook(server.bang_luong_mau_gio_lam(7, 2026).path)
w3 = wb3["Giờ theo tháng"]
assert w3.cell(1, 16).value == "Tổng tiền (đ)" and w3.cell(1, 17).value == "Cảnh báo ngưỡng" and w3.cell(2, 19).value == 2530000
r1 = next(r for r in range(2, 6) if w3.cell(r, 1).value == "P1")
assert w3.cell(r1, 16).value == f"=SUM(D{r1}:O{r1})*C{r1}" and "vượt ngưỡng" in w3.cell(r1, 17).value and "$S$2" in w3.cell(r1, 17).value
assert any("D2:O500" in str(rng.sqref) for rng in w3.conditional_formatting) and "ngưỡng" in w3.cell(w3.max_row, 1).value
# import: thông báo từng tháng vượt ngưỡng + tổng tiền
r2 = next(r for r in range(2, 6) if w3.cell(r, 1).value == "P2")
w3.cell(r2, 4).value = 100; w3.cell(r2, 5).value = 40          # P2 30.000/giờ: T1 = 3.000.000 (vượt), T2 = 1.200.000
w3.cell(r1, 6).value = 43.3
kq3 = import_(wb3)
assert any("⚠ Phạm Giờ Giấc tháng 1" in x and "3.000.000" in x and "phải đóng BHXH" in x for x in kq3["canh_bao"]), kq3["canh_bao"]
assert not any("tháng 2" in x and "Phạm" in x for x in kq3["canh_bao"]) and not any("Lê Bán Thời tháng" in x and "⚠" in x for x in kq3["canh_bao"])
assert kq3["tong_tien"] == {"Phạm Giờ Giấc": 4200000, "Lê Bán Thời": round(43.3 * 26000)} and not any("dòng 5" in x or "dòng 6" in x for x in kq3["loi"]), kq3["loi"]
# người có trong file (kể cả không giờ) + tháng có dữ liệu lỗi (để giao diện không coi là "không làm")
wb4 = openpyxl.load_workbook(server.bang_luong_mau_gio_lam(7, 2026).path)
w4 = wb4["Giờ theo tháng"]
r1 = next(r for r in range(2, 6) if w4.cell(r, 1).value == "P1")
w4.cell(r1, 6).value = 20; w4.cell(r1, 7).value = 9999        # T3 hợp lệ, T4 vượt tối đa -> lỗi
kq4 = import_(wb4)
assert sorted(e["ma"] for e in kq4["nguoi_trong_file"]) == ["P1", "P2"], "P2 có trong file dù không có giờ"
assert kq4["thang_loi"] == {"P1": ["04"]} and [e["ma"] for e in kq4["gio"]] == ["P1"]
# HỢP ĐỒNG PART-TIME chỉ liệt kê người ĐANG làm part-time trong năm (đúng dòng part-time của họ), kể cả người chuyển sang toàn thời gian giữa năm
rows_hd = [R(**{'Mã NV': '2', 'Họ và tên': 'Trần Minh Hùng', 'Tháng/Năm vào làm': '01/2024', 'Part-time': 'x', 'Lương theo giờ': 25000}),
           R(**{'Mã NV': '2-001', 'Họ và tên': 'Trần Minh Hùng', 'Tháng/Năm vào làm': '12/2024', 'Đóng BHXH': 'x', 'Lương Cơ bản': 5310000}),
           R(**{'Mã NV': '3', 'Họ và tên': 'Nguyễn Giang Nam', 'Tháng/Năm vào làm': '12/2024', 'Đóng BHXH': 'x', 'Lương Cơ bản': 5310000})]
server.nhap_lieu_get = lambda cid, loai="in": {"header": H, "rows": rows_hd} if loai == "nv" else {"header": [], "rows": []}
server._luong_doc_nam = lambda cid, nam: (server._luong_chuan_tham_so(None, nam), {}, "", [nam])
p24 = server._vb_nv_part_time(7, 2024)
assert [(n["stt"], n["ma"], n["ten"], n["luong_gio"]) for n in p24] == [(1, "2", "Trần Minh Hùng", 25000.0)], p24
assert server._vb_nv_part_time(7, 2025) == [], "năm 2025 người này đã là toàn thời gian (2-001): không còn hợp đồng part-time"
# NGÀY BẮT ĐẦU LÀM VIỆC ĐẦU TIÊN (ngày hợp đồng/ký) = tháng đầu tiên có giờ làm trong Bảng Lương (mọi năm đã lưu); có giờ theo ngày thì ngày nhỏ nhất
bl_nam = {2025: {"02": [{"ma": "2", "ten": "Trần Minh Hùng", "gio_lam": 0.0, "part_time": 1}], "07": [{"ma": "2", "ten": "Trần Minh Hùng", "gio_lam": 12.0, "gio_ngay": "9:2;4:1;20:9"}],
                   "09": [{"ma": "2", "ten": "Trần Minh Hùng", "gio_lam": 8.0}]},
          2024: {"11": [{"ma": "", "ten": "Nguyễn Giang Nam", "gio_lam": 5.0}]}}
server._luong_doc_nam = lambda cid, nam: (server._luong_chuan_tham_so(None, nam), bl_nam.get(nam, {}), "", [2024, 2025])
rows_hd2 = [R(**{'Mã NV': '2', 'Họ và tên': 'Trần Minh Hùng', 'Part-time': 'x', 'Lương theo giờ': 25000}),                  # vào làm để trống
            R(**{'Mã NV': '5', 'Họ và tên': 'Nguyễn Giang Nam', 'Part-time': 'x', 'Lương theo giờ': 25000, 'Tháng/Năm vào làm': '01/2025'}),
            R(**{'Mã NV': '6', 'Họ và tên': 'Chưa Có Giờ', 'Part-time': 'x', 'Lương theo giờ': 25000, 'Tháng/Năm vào làm': '15/03/2025'})]
server.nhap_lieu_get = lambda cid, loai="in": {"header": H, "rows": rows_hd2} if loai == "nv" else {"header": [], "rows": []}
pp = {n["ten"]: n for n in server._vb_nv_part_time(7, 2025)}
assert pp["Trần Minh Hùng"]["ngay_bat_dau_lam"] == "04/07/2025", "tháng 2 giờ = 0 bỏ qua; tháng 7 đầu tiên có giờ, ngày nhỏ nhất theo giờ từng ngày = 4"
assert pp["Nguyễn Giang Nam"]["ngay_bat_dau_lam"] == "01/11/2024", "lấy cả năm trước: tháng đầu tiên có giờ (khớp theo họ tên khi dòng bảng lương chưa có mã)"
assert "ngay_bat_dau_lam" not in pp["Chưa Có Giờ"], "chưa có giờ nào: dùng Tháng/Năm vào làm"
CTY2 = {"ten": "CÔNG TY A", "mst": "031", "dia_chi": "1 Lê Lợi", "nguoi_ky": "Giám Đốc"}
import van_ban_lao_dong as _v
t_a = _v.dung_hop_dong_part_time(pp["Trần Minh Hùng"], CTY2, {}, 0, nam=2025)
assert "ngày 04 tháng 07 năm 2025" in t_a and "Số: 01/HĐPT-2025" in t_a
t_b = _v.dung_hop_dong_part_time(pp["Chưa Có Giờ"], CTY2, {}, 0, nam=2025)
assert "ngày 15 tháng 03 năm 2025" in t_b
# thứ tự theo ngày bắt đầu làm việc đầu tiên TĂNG DẦN (STT, số hợp đồng đi theo thứ tự thời gian), cùng ngày giữ thứ tự danh sách
rows_ss = [R(**{'Mã NV': 'A', 'Họ và tên': 'Muộn Nhất', 'Part-time': 'x', 'Lương theo giờ': 25000, 'Tháng/Năm vào làm': '01/04/2025'}),
           R(**{'Mã NV': 'B', 'Họ và tên': 'Sớm Nhất', 'Part-time': 'x', 'Lương theo giờ': 25000, 'Tháng/Năm vào làm': '01/01/2025'}),
           R(**{'Mã NV': 'C', 'Họ và tên': 'Giữa', 'Part-time': 'x', 'Lương theo giờ': 25000, 'Tháng/Năm vào làm': '03/2025'}),
           R(**{'Mã NV': 'D', 'Họ và tên': 'Cùng Ngày Sau', 'Part-time': 'x', 'Lương theo giờ': 25000, 'Tháng/Năm vào làm': '03/2025'})]
server.nhap_lieu_get = lambda cid, loai="in": {"header": H, "rows": rows_ss} if loai == "nv" else {"header": [], "rows": []}
server._luong_doc_nam = lambda cid, nam: (server._luong_chuan_tham_so(None, nam), {}, "", [nam])
ss = server._vb_nv_part_time(7, 2025)
assert [(n["stt"], n["ten"]) for n in ss] == [(1, "Sớm Nhất"), (2, "Giữa"), (3, "Cùng Ngày Sau"), (4, "Muộn Nhất")], [(n["stt"], n["ten"]) for n in ss]
ht = _v.dung_hop_dong_part_time_nhieu(ss, CTY2, {}, nam=2025)
import re as _re
thu_tu = _re.findall(r"Số: (\d+)/HĐPT-2025.*?ngày (\d+ tháng \d+ năm 2025)", ht, flags=_re.S)
assert [x[1] for x in thu_tu] == ["01 tháng 01 năm 2025", "01 tháng 03 năm 2025", "01 tháng 03 năm 2025", "01 tháng 04 năm 2025"] and [x[0] for x in thu_tu] == ["01", "02", "03", "04"], thu_tu
print("PASS")
