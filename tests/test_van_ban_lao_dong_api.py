import os, sys, io, asyncio, sqlite3, zipfile, tempfile, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server
from fastapi import HTTPException

# API Hợp đồng lao động / Quy chế lương / Thang bảng lương: lấy dữ liệu từ Danh Sách NV + Bảng Lương, in hàng loạt từ-đến, xuất Word từ HTML đã sửa.
HDR = ['STT', 'Mã NV', 'Họ và tên', 'Ngày sinh', 'Địa chỉ hiện đang cư trú', 'CCCD', 'Ngày cấp', 'Tháng/Năm vào làm', 'Đóng BHXH', 'Tháng/Năm nghỉ việc',
       'Chức vụ', 'Lương Cơ bản', 'PC Tiền cơm', 'PC Xăng xe', 'PC Điện thoại', 'PC Trang phục']
ROWS = [[i, 'NV%d' % i, 'Nhân Viên %d' % i, '01/01/1990', 'Địa chỉ %d' % i, '0791900001%02d' % i, '01/01/2020', '01/2025', 'x', '', 'Kế toán' if i % 2 else 'Kinh doanh', 6_000_000 + i * 100_000, 730000, 0, 0, 0] for i in range(1, 6)]
conn = sqlite3.connect(":memory:", check_same_thread=False); conn.row_factory = sqlite3.Row
conn.execute("CREATE TABLE companies (id INTEGER, ten TEXT, mst TEXT, dia_chi TEXT, nguoi_ky TEXT)")
conn.execute("INSERT INTO companies VALUES (7, 'CÔNG TY TNHH THỬ', '0300000001', '1 Lê Lợi, Quận 1, Thành phố Hồ Chí Minh', 'Hồ Thị Cẩm Vân')")
class KhongDong:
    def __init__(self, c): self.c = c
    def execute(self, *a): return self.c.execute(*a)
    def commit(self): self.c.commit()
    def close(self): pass
server.db = lambda: KhongDong(conn)
server.nhap_lieu_get = lambda cid, loai="in": {"header": HDR, "rows": ROWS} if loai == "nv" else {"header": [], "rows": []}
bl = {"03": [{"ma": "NV2", "ten": "Nhân Viên 2", "luong_cb": 9_000_000, "tien_com": 730000, "muc_xang": 0, "muc_dt": 0, "trang_phuc": 0}]}
server._luong_doc_nam = lambda cid, nam: (server._luong_chuan_tham_so(None, nam), bl, "", [nam])
server.DOWNLOAD_DIR = tempfile.mkdtemp()
server._copy_ra_desktop = lambda p, f: None
class Req:
    def __init__(self, b): self.b = b
    async def json(self): return self.b
run = lambda coro: asyncio.run(coro)

d = server.van_ban_du_lieu(7, 2026)
assert d["cty"]["ten"] == "CÔNG TY TNHH THỬ" and len(d["nhan_vien"]) == 5 and d["tuy_chon"]["nguoi_ky"] == "Hồ Thị Cẩm Vân" and d["tuy_chon"]["dia_danh"] == "TP. Hồ Chí Minh"
assert d["nhan_vien"][1]["luong_cb"] == 9_000_000 and ".vb-trang" in d["css"] and d["trang"]["tl"]["ngang"] is True and d["trang"]["hd"]["ngang"] is False
assert server.van_ban_du_lieu(7, 2026)["canh_bao"], "có cảnh báo (vd lương Danh sách NV ≠ Bảng lương)"
try:
    server.van_ban_du_lieu(99, 2026); raise SystemExit("phải lỗi: công ty không tồn tại")
except HTTPException as e:
    assert e.status_code == 404

# in hàng loạt: từ NV2 đến NV4 (3 hợp đồng); đảo đầu-cuối vẫn đúng
r = run(server.van_ban_xem_truoc(7, Req({"loai": "hd", "nam": 2026, "tu": 2, "den": 4, "tuy_chon": {"nguoi_ky": "Hồ Thị Cẩm Vân", "ong_ba_ky": "Bà", "so_bat_dau": 10}})))
assert r["so_van_ban"] == 3 and r["html"].count('<section class="vb-trang">') == 3 and "NHÂN VIÊN 2" in r["html"] and "NHÂN VIÊN 4" in r["html"] and "NHÂN VIÊN 1" not in r["html"] and "NHÂN VIÊN 5" not in r["html"]
assert "9.000.000 đồng/tháng" in r["html"], "lương NV2 lấy từ Bảng lương (9.000.000) thay vì Danh sách (6.200.000)"
assert "Số: 10/HĐLĐ-2026" in r["html"] and "Số: 12/HĐLĐ-2026" in r["html"] and "ngày 01 tháng 01 năm 2026" in r["html"], "năm lập 2026 -> hợp đồng ghi năm 2026 dù vào làm 2025"
r2 = run(server.van_ban_xem_truoc(7, Req({"loai": "hd", "nam": 2026, "tu": 4, "den": 2})))
assert r2["so_van_ban"] == 3
assert all("Nhân Viên 1:" not in c["nd"] and "Nhân Viên 5:" not in c["nd"] for c in r["canh_bao"]), "cảnh báo chỉ của những người đang in"
try:
    run(server.van_ban_xem_truoc(7, Req({"loai": "hd", "nam": 2026, "tu": 50, "den": 60}))); raise SystemExit("phải lỗi")
except HTTPException as e:
    assert e.status_code == 400
try:
    run(server.van_ban_xem_truoc(7, Req({"loai": "xx"}))); raise SystemExit("phải lỗi")
except HTTPException as e:
    assert e.status_code == 400

qc = run(server.van_ban_xem_truoc(7, Req({"loai": "qc", "nam": 2026, "tuy_chon": {"ngay": "02/01/2026", "ngay_tra": "10", "buoc_pct": "7"}})))
assert "QUYẾT ĐỊNH" in qc["html"] and "5.310.000" in qc["html"] and "ngày 10 của tháng sau" in qc["html"] and "cao hơn bậc liền kề trước 7%" in qc["html"]
tl = run(server.van_ban_xem_truoc(7, Req({"loai": "tl", "nam": 2026, "tuy_chon": {"vung": "2", "so_bac": "5"}})))
assert "4.730.000" in tl["html"] and tl["trang"]["ngang"] is True and "Nhân viên kế toán; Nhân viên kinh doanh" in tl["html"] and "NĂM 2026" in tl["html"]
for ten in ("Giám đốc", "Phó giám đốc; Kế toán trưởng", "Phân xưởng sản xuất"):
    assert ten in tl["html"], "nhóm chức danh mặc định: " + ten

# --- thang lương lưu THEO TỪNG NĂM + dò lương cơ bản theo năm + danh sách chức vụ cho Danh Sách Nhân Viên
d0 = server.van_ban_du_lieu(7, 2026)
assert d0["chuc_danh"] == ["Giám đốc", "Phó giám đốc", "Kế toán trưởng", "Nhân viên kế toán", "Nhân viên kinh doanh", "Phân xưởng sản xuất"], d0["chuc_danh"]
assert server.van_ban_chuc_danh(7, 2026)["chuc_danh"] == d0["chuc_danh"]
# Bảng lương năm 2026 chỉ có Nhân Viên 2 (lương 9.000.000): thang lương/quy chế chỉ lấy người có trong Bảng lương năm đó
assert tl["html"].count("Nhân Viên") == 1 and "Nhân Viên 2" in tl["html"] and "Nhân Viên 1" not in tl["html"]
dl = run(server.van_ban_do_luong(7, Req({"nam": 2026, "tuy_chon": {"nhom_tuy_chinh": "Giám đốc\nNhân viên kế toán; Nhân viên kinh doanh | 1"}})))
assert dl["co_bang_luong"] and dl["luong_toi_thieu"] == 5_310_000
assert [b["ten"] for b in dl["bang"]][:2] == ["Giám đốc", "Nhân viên kế toán; Nhân viên kinh doanh"] and dl["bang"][0]["bac_1"] == 5_310_000
assert dl["nhom_tuy_chinh"].splitlines()[0] == "Giám đốc | 5310000"
ln = server.van_ban_luong_theo_nam(7, 2026)
assert [(x["ten"], x["luong_cb"], x["tien_com"]) for x in ln["nguoi"]] == [("Nhân Viên 2", 9_000_000, 730000)], "chỉ người có trong Bảng lương năm đó"
# tạo xem trước thang lương đã LƯU cấu hình của năm 2026; năm 2027 chưa lưu thì kế thừa nhóm nhưng bỏ mức bậc 1 cố định (tự dò lại theo năm)
run(server.van_ban_xem_truoc(7, Req({"loai": "tl", "nam": 2026, "tuy_chon": {"nhom_tuy_chinh": "Giám đốc | 8000000\nNhân viên kinh doanh", "buoc_pct": "6"}})))
d26 = server.van_ban_du_lieu(7, 2026)
assert d26["tuy_chon"]["nhom_tuy_chinh"] == "Giám đốc | 8000000\nNhân viên kinh doanh" and float(d26["tuy_chon"]["buoc_pct"]) == 6 and d26["thang_luong_nam_goc"] == 2026
assert d26["chuc_danh"] == ["Giám đốc", "Nhân viên kinh doanh"]
d27 = server.van_ban_du_lieu(7, 2027)
assert d27["tuy_chon"]["nhom_tuy_chinh"] == "Giám đốc\nNhân viên kinh doanh" and d27["thang_luong_nam_goc"] == 2026, "năm mới: giữ nhóm, bỏ '| mức' cũ"
# quy chế/hợp đồng dùng lại cấu hình đã lưu (bước % bậc lương) mà không cần gửi lại
qc2 = run(server.van_ban_xem_truoc(7, Req({"loai": "qc", "nam": 2026, "tuy_chon": {"ngay": "02/01/2026"}})))
assert "cao hơn bậc liền kề trước 6%" in qc2["html"], "Quy chế thống nhất với thang lương đã lưu"
# Excel dùng cấu hình đã lưu
xl2 = run(server.van_ban_excel_thang_luong(7, Req({"nam": 2026})))
ws2 = __import__("openpyxl").load_workbook(xl2.path)["Thang bảng lương"]
assert any(c.value == "HỆ THỐNG THANG LƯƠNG, BẢNG LƯƠNG NĂM 2026" for r in ws2.iter_rows() for c in r)

# xuất Word từ HTML đã SỬA TAY: file lưu ra DOWNLOAD_DIR, đúng nội dung đã sửa + canh chỉnh
html_sua = r["html"].replace("Điều 5. Điều khoản thi hành", "Điều 5. Điều khoản thi hành (đã sửa tay)")
resp = run(server.van_ban_word(7, Req({"html": html_sua, "trang": {"font": "Tahoma", "size": 12, "line": 1.5, "le": [20, 20, 30, 15]}, "ten_file": "Hợp đồng lao động 2026/..\\x"})))
assert resp.path.endswith(".docx") and os.path.dirname(resp.path) == server.DOWNLOAD_DIR and ".." not in os.path.basename(resp.path) and "/" not in os.path.basename(resp.path)
z = zipfile.ZipFile(resp.path)
x = z.read("word/document.xml").decode("utf8")
assert "(đã sửa tay)" in x and x.count("HỢP ĐỒNG LAO ĐỘNG") == 3 and 'w:ascii="Tahoma"' in z.read("word/styles.xml").decode("utf8")
try:
    run(server.van_ban_word(7, Req({"html": "  "}))); raise SystemExit("phải lỗi")
except HTTPException as e:
    assert e.status_code == 400

# Excel thang bảng lương
xl = run(server.van_ban_excel_thang_luong(7, Req({"nam": 2026, "tuy_chon": {"vung": 1}})))
import openpyxl
wb = openpyxl.load_workbook(xl.path)
assert os.path.basename(xl.path) == "ThangBangLuong_2026.xlsx" and "Thang bảng lương" in wb.sheetnames
# công ty chưa có nhân viên
server.nhap_lieu_get = lambda cid, loai="in": {"header": [], "rows": []}
server._luong_doc_nam = lambda cid, nam: (server._luong_chuan_tham_so(None, nam), {}, "", [])
try:
    run(server.van_ban_xem_truoc(7, Req({"loai": "qc", "nam": 2026}))); raise SystemExit("phải lỗi")
except HTTPException as e:
    assert e.status_code == 404
# update.py phải tải kèm module mới (nếu không, máy người dùng cập nhật xong sẽ thiếu file -> không khởi động được)
import update
assert "van_ban_lao_dong.py" in update.FILES
print("PASS")
