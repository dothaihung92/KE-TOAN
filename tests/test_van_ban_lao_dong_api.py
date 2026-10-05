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


# --- Kho chữ ký: chỉ chữ ký do chính người đó cung cấp + ĐÃ xác nhận đồng ý mới được lưu/gắn vào văn bản
import base64, io as _io
from PIL import Image, ImageDraw
def anh(nen=(255, 255, 255, 255), size=(400, 160)):
    im = Image.new("RGBA", size, nen); d = ImageDraw.Draw(im)
    d.line([(60, 120), (140, 30), (220, 130), (330, 50)], fill=(10, 20, 120, 255), width=5)
    b = _io.BytesIO(); im.save(b, "PNG"); return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()
def giai(uri):
    return Image.open(_io.BytesIO(base64.b64decode(uri.split(",", 1)[1]))).convert("RGBA")
server.nhap_lieu_get = lambda cid, loai="in": {"header": HDR, "rows": ROWS} if loai == "nv" else {"header": [], "rows": []}
server._luong_doc_nam = lambda cid, nam: (server._luong_chuan_tham_so(None, nam), bl, "", [nam])
ds = server.chu_ky_danh_sach(7, 2026)
assert ds["giam_doc"]["khoa"] == "gd:cty7" and ds["giam_doc"]["ten"] == "Hồ Thị Cẩm Vân" and len(ds["nhan_vien"]) == 5 and not any(m["co_anh"] for m in ds["nhan_vien"])
k2 = ds["nhan_vien"][1]["khoa"]
assert k2 == "cccd:079190000102", k2
# lưu ảnh bắt buộc kèm xác nhận đồng ý
for loi in ({"khoa": k2, "ten": "Nhân Viên 2", "anh": anh(), "xac_nhan": False}, {"khoa": "abc", "anh": anh(), "xac_nhan": True}, {"khoa": k2, "ten": "x", "anh": "data:text/html;base64,AAAA", "xac_nhan": True},
            {"khoa": k2, "ten": "x", "xac_nhan": True}):
    try:
        run(server.chu_ky_luu(7, Req(loi))); raise SystemExit("phải lỗi: %s" % loi)
    except HTTPException as e:
        assert e.status_code == 400
trang = _io.BytesIO(); Image.new("RGB", (200, 80), "white").save(trang, "PNG")
try:   # ảnh trắng toàn bộ (không có nét ký)
    run(server.chu_ky_luu(7, Req({"khoa": k2, "ten": "x", "anh": "data:image/png;base64," + base64.b64encode(trang.getvalue()).decode(), "xac_nhan": True}))); raise SystemExit("phải lỗi")
except HTTPException as e:
    assert e.status_code == 400 and "trống" in e.detail
rs = run(server.chu_ky_luu(7, Req({"khoa": k2, "ten": "Nhân Viên 2", "anh": anh(), "xac_nhan": True})))
im = giai(rs["anh"])
assert im.getpixel((0, 0))[3] == 0 and im.width <= 480 and im.height <= 160 and im.width < 400, "nền trắng thành trong suốt + cắt sát nét ký"
assert im.getchannel("A").getextrema()[1] > 200, "nét ký vẫn đặc"
run(server.chu_ky_luu(7, Req({"khoa": "giam_doc", "ten": "Hồ Thị Cẩm Vân", "anh": anh((0, 0, 0, 0)), "xac_nhan": True})))      # khoá cũ "giam_doc" tự đổi sang khoá chung theo tên người đại diện
ds = server.chu_ky_danh_sach(7, 2026)
assert ds["giam_doc"]["co_anh"] and ds["giam_doc"]["xac_nhan"] and ds["nhan_vien"][1]["co_anh"] and ds["nhan_vien"][1]["anh"].startswith("data:image/png;base64,")
# tự gắn vào hợp đồng: chữ ký người lao động + giám đốc; chỉ khi đã xác nhận
r = run(server.van_ban_xem_truoc(7, Req({"loai": "hd", "nam": 2026, "tu": 1, "den": 3})))
assert r["so_chu_ky"] == 4 and r["html"].count('src="data:image/png') == 4, "giám đốc ký cả 3 hợp đồng + chữ ký NV2"
sec = r["html"].split('<section class="vb-trang">')
assert [x.count("<img") for x in sec[1:]] == [1, 2, 1], "chữ ký NV2 chỉ nằm ở hợp đồng của NV2"
rq = run(server.van_ban_xem_truoc(7, Req({"loai": "qc", "nam": 2026})))
assert rq["so_chu_ky"] == 1, "quy chế: chữ ký giám đốc"
rt = run(server.van_ban_xem_truoc(7, Req({"loai": "tl", "nam": 2026})))
assert rt["so_chu_ky"] == 2, "thang lương: chữ ký giám đốc ở cuối bảng và cuối phụ lục"
r_tat = run(server.van_ban_xem_truoc(7, Req({"loai": "hd", "nam": 2026, "tu": 1, "den": 3, "tuy_chon": {"gan_chu_ky": False}})))
assert r_tat["so_chu_ky"] == 0, "tắt tự gắn chữ ký"
# bỏ xác nhận -> không gắn nữa (ảnh vẫn giữ trong kho)
run(server.chu_ky_luu(7, Req({"khoa": k2, "ten": "Nhân Viên 2", "xac_nhan": False})))
assert run(server.van_ban_xem_truoc(7, Req({"loai": "hd", "nam": 2026, "tu": 1, "den": 3})))["so_chu_ky"] == 3, "bỏ đồng ý: chỉ còn chữ ký giám đốc"
assert server.chu_ky_danh_sach(7, 2026)["nhan_vien"][1]["co_anh"] and not server.chu_ky_danh_sach(7, 2026)["nhan_vien"][1]["xac_nhan"]
run(server.chu_ky_luu(7, Req({"khoa": k2, "ten": "Nhân Viên 2", "xac_nhan": True})))
# Word: ảnh chữ ký nằm trong file .docx
resp = run(server.van_ban_word(7, Req({"html": run(server.van_ban_xem_truoc(7, Req({"loai": "hd", "nam": 2026, "tu": 2, "den": 2})))["html"], "ten_file": "HD_CK"})))
zz = zipfile.ZipFile(resp.path)
assert sum(1 for n in zz.namelist() if n.startswith("word/media/")) == 2 and b"<w:drawing>" in zz.read("word/document.xml")
# chữ ký cho bản in bảng lương: chỉ người ĐÃ xác nhận; khớp theo mã gốc hoặc họ tên ở phía giao diện
ci = server.chu_ky_cho_in(7, 2026)
assert ci["giam_doc"].startswith("data:image/png") and [(x["ma"], x["ten"]) for x in ci["nhan_vien"]][:1] == [("NV2", "Nhân Viên 2")] and all(x["anh"].startswith("data:image/png") for x in ci["nhan_vien"])
run(server.chu_ky_luu(7, Req({"khoa": k2, "ten": "Nhân Viên 2", "xac_nhan": False})))
assert "NV2" not in [x["ma"] for x in server.chu_ky_cho_in(7, 2026)["nhan_vien"]], "bỏ đồng ý -> không gắn vào bản in"
run(server.chu_ky_luu(7, Req({"khoa": k2, "ten": "Nhân Viên 2", "xac_nhan": True})))
# xoá chữ ký
server.chu_ky_xoa(7, k2)
assert not server.chu_ky_danh_sach(7, 2026)["nhan_vien"][1]["co_anh"]
# người đổi mã (2 -> 2-001) vẫn dùng chung 1 chữ ký (khoá theo mã gốc / CCCD)
import van_ban_lao_dong as _v
assert _v.khoa_chu_ky("2-001", "A") == _v.khoa_chu_ky("2", "A") == "ma:2" and _v.khoa_chu_ky("", "Trần Văn Á") == "ten:tran van a"
assert _v.khoa_nguoi({"cccd": "079 190 000 102", "ten": "X"}) == "cccd:079190000102" and _v.khoa_nguoi({"cccd": "123", "ten": "Trần Văn Á"}) == "ten:tran van a"

# KHO CHUNG nhiều công ty: cùng người (CCCD) ở công ty khác dùng lại đúng chữ ký đã lưu; chữ ký GIÁM ĐỐC là của riêng từng công ty
run(server.chu_ky_luu(7, Req({"khoa": k2, "ten": "Nhân Viên 2", "anh": anh(), "xac_nhan": True})))
conn.execute("INSERT INTO companies VALUES (8, 'CÔNG TY KHÁC', '0300000002', '9 Trần Hưng Đạo', 'Hồ Thị Cẩm Vân')")
ds8 = server.chu_ky_danh_sach(8, 2026)
assert not ds8["giam_doc"]["co_anh"] and ds8["giam_doc"]["khoa"] == "gd:cty8", "giám đốc CÙNG TÊN ở công ty khác cũng KHÔNG lấy chữ ký giám đốc của công ty 7"
assert ds8["nhan_vien"][1]["co_anh"] and ds8["tong_kho_chung"] == 2, "công ty khác thấy chữ ký người lao động trong kho chung"
assert "gd:cty7" not in [d["khoa"] for d in ds8["da_luu"]] and not any(d["khoa"].startswith("gd:") for d in ds8["da_luu"]), "chữ ký giám đốc không hiện ở mục chưa gán của công ty khác"
rk = run(server.van_ban_xem_truoc(8, Req({"loai": "hd", "nam": 2026, "tu": 2, "den": 2})))
assert rk["so_chu_ky"] == 1, "hợp đồng ở công ty khác chỉ gắn chữ ký người lao động (CCCD), không gắn chữ ký giám đốc của công ty khác"
run(server.chu_ky_luu(8, Req({"khoa": "giam_doc", "ten": "Hồ Thị Cẩm Vân", "anh": anh(), "xac_nhan": True})))
assert server.chu_ky_danh_sach(8, 2026)["giam_doc"]["co_anh"] and server.chu_ky_danh_sach(7, 2026)["giam_doc"]["co_anh"], "mỗi công ty 1 chữ ký giám đốc riêng"
conn.execute("UPDATE companies SET nguoi_ky='Người Khác' WHERE id=8")
# khoá giám đốc cũ theo TÊN (bản trước): chuyển cho công ty duy nhất trùng tên; trùng nhiều công ty thì không đoán
conn.execute("INSERT INTO chu_ky_chung (khoa, ten, anh, xac_nhan, updated_at) VALUES ('gd:ten rieng', 'Tên Riêng', ?, 1, '')", (anh(),))
conn.execute("INSERT INTO companies VALUES (9, 'CTY 9', '0300000009', 'x', 'Tên Riêng')")
conn.execute("INSERT INTO chu_ky_chung (khoa, ten, anh, xac_nhan, updated_at) VALUES ('gd:trung ten', 'Trùng Tên', ?, 1, '')", (anh(),))
conn.execute("INSERT INTO companies VALUES (10, 'CTY 10', '0300000010', 'x', 'Trùng Tên')"); conn.execute("INSERT INTO companies VALUES (11, 'CTY 11', '0300000011', 'x', 'Trùng Tên')")
server._ck_doc_het(7)
ks = {r[0] for r in conn.execute("SELECT khoa FROM chu_ky_chung")}
assert "gd:cty9" in ks and "gd:ten rieng" not in ks, "chuyển khoá cũ cho công ty duy nhất trùng tên"
assert "gd:trung ten" in ks and "gd:cty10" not in ks and "gd:cty11" not in ks, "trùng nhiều công ty: không đoán, không công ty nào dùng"
conn.execute("DELETE FROM chu_ky_chung WHERE khoa IN ('gd:cty9','gd:trung ten')"); conn.execute("DELETE FROM companies WHERE id IN (9,10,11)")
# khoá cũ theo công ty (bản trước) vẫn được đọc
conn.execute("INSERT INTO chu_ky (company_id, khoa, ten, anh, xac_nhan, updated_at) VALUES (7, 'ma:nv3', 'Nhân Viên 3', ?, 1, '')", (anh(),))
assert server.chu_ky_danh_sach(7, 2026)["nhan_vien"][2]["co_anh"] and "ma:nv3" in server._vb_chu_ky_dict(7)

# lưu NHIỀU chữ ký 1 lần (bắt buộc xác nhận)
muc = [{"khoa": ds["nhan_vien"][3]["khoa"], "ten": "Nhân Viên 4", "anh": anh()}, {"khoa": ds["nhan_vien"][4]["khoa"], "ten": "Nhân Viên 5", "anh": anh()}, {"khoa": "abc", "ten": "Sai khoá", "anh": anh()}]
try:
    run(server.chu_ky_luu_nhieu(7, Req({"muc": muc}))); raise SystemExit("phải lỗi: chưa xác nhận")
except HTTPException as e:
    assert e.status_code == 400
kq = run(server.chu_ky_luu_nhieu(7, Req({"xac_nhan": True, "muc": muc})))
assert kq["da_luu"] == 2 and len(kq["loi"]) == 1 and kq["loi"][0]["ten"] == "Sai khoá"
ds7 = server.chu_ky_danh_sach(7, 2026)
assert ds7["nhan_vien"][3]["co_anh"] and ds7["nhan_vien"][3]["xac_nhan"] and ds7["nhan_vien"][4]["co_anh"]
try:
    run(server.chu_ky_luu_nhieu(7, Req({"xac_nhan": True, "muc": []}))); raise SystemExit("phải lỗi: không có gì để lưu")
except HTTPException as e:
    assert e.status_code == 400

# chữ ký NHIỀU HƠN danh sách nhân viên: file chưa ghép được GIỮ LẠI (chưa gán), gắn sau cho người mới thêm
kq = run(server.chu_ky_luu_nhieu(7, Req({"xac_nhan": True, "muc": [], "du": [{"ten": "chu_ky_20.png", "anh": anh()}, {"ten": "chu_ky_21.png", "anh": anh()}, {"ten": "hong.png", "anh": "data:text/plain;base64,AA=="}]})))
assert kq["da_giu"] == 2 and kq["da_luu"] == 0 and len(kq["loi"]) == 1
du = server.chu_ky_danh_sach(7, 2026)["du"]
assert [d["ten"] for d in du] == ["chu_ky_20.png", "chu_ky_21.png"] and du[0]["anh"].startswith("data:image/png")
assert [d["ten"] for d in server.chu_ky_danh_sach(8, 2026)["du"]] == ["chu_ky_20.png", "chu_ky_21.png"], "kho chưa gán dùng chung các công ty"
assert "chu_ky_20.png" not in str(server._vb_chu_ky_dict(7).keys()), "chưa gán cho ai thì không gắn vào văn bản"
ROWS.append([6, "NV6", "Nhân Viên 6", "01/01/1990", "Địa chỉ 6", "079190000106", "01/01/2020", "01/2025", "x", "", "Kế toán", 6_000_000, 730000, 0, 0, 0])      # người mới thêm vào danh sách
k6 = server.chu_ky_danh_sach(7, 2026)["nhan_vien"][5]["khoa"]
assert k6 == "cccd:079190000106" and not server.chu_ky_danh_sach(7, 2026)["nhan_vien"][5]["co_anh"]
try:
    run(server.chu_ky_gan_du(7, Req({"id": du[0]["id"], "khoa": k6, "ten": "Nhân Viên 6", "xac_nhan": False}))); raise SystemExit("phải lỗi: chưa xác nhận")
except HTTPException as e:
    assert e.status_code == 400
run(server.chu_ky_gan_du(7, Req({"id": du[0]["id"], "khoa": k6, "ten": "Nhân Viên 6", "xac_nhan": True})))
ds6 = server.chu_ky_danh_sach(7, 2026)
assert ds6["nhan_vien"][5]["co_anh"] and ds6["nhan_vien"][5]["xac_nhan"] and [d["ten"] for d in ds6["du"]] == ["chu_ky_21.png"], "gắn xong thì rời khỏi kho chưa gán"
try:
    run(server.chu_ky_gan_du(7, Req({"id": du[0]["id"], "khoa": k6, "ten": "x", "xac_nhan": True}))); raise SystemExit("phải lỗi: đã gán rồi")
except HTTPException as e:
    assert e.status_code == 404
server.chu_ky_xoa_du(7, ds6["du"][0]["id"])
assert server.chu_ky_danh_sach(7, 2026)["du"] == []
ROWS.pop()

# chữ ký ĐÃ GÁN ở công ty khác (người không có trong danh sách này) vẫn dùng lại được: sao chép, không di chuyển
run(server.chu_ky_luu(8, Req({"khoa": "cccd:999000111", "ten": "Người Ở Cty Khác", "anh": anh(), "xac_nhan": True})))
dl = server.chu_ky_danh_sach(7, 2026)["da_luu"]
assert "cccd:999000111" in [d["khoa"] for d in dl] and dl[0]["anh"].startswith("data:image/png"), "công ty này thấy chữ ký đã gán ở công ty khác"
assert not {d["khoa"] for d in dl} & {m["khoa"] for m in server.chu_ky_danh_sach(7, 2026)["nhan_vien"]}, "không lặp người đã có trong danh sách"
ROWS.append([6, "NV6", "Nhân Viên 6", "01/01/1990", "Địa chỉ 6", "079190000106", "01/01/2020", "01/2025", "x", "", "Kế toán", 6_000_000, 730000, 0, 0, 0])
try:
    run(server.chu_ky_dung_lai(7, Req({"nguon_khoa": "cccd:999000111", "khoa": k6, "ten": "Nhân Viên 6", "xac_nhan": False}))); raise SystemExit("phải lỗi: chưa xác nhận cùng một người")
except HTTPException as e:
    assert e.status_code == 400
try:
    run(server.chu_ky_dung_lai(7, Req({"nguon_khoa": "cccd:khong-co", "khoa": k6, "ten": "x", "xac_nhan": True}))); raise SystemExit("phải lỗi: nguồn không tồn tại")
except HTTPException as e:
    assert e.status_code == 404
run(server.chu_ky_dung_lai(7, Req({"nguon_khoa": "cccd:999000111", "khoa": k6, "ten": "Nhân Viên 6", "xac_nhan": True})))
d7 = server.chu_ky_danh_sach(7, 2026)
assert d7["nhan_vien"][5]["co_anh"] and d7["nhan_vien"][5]["xac_nhan"], "người này đã có chữ ký dùng lại"
assert "cccd:999000111" in [d["khoa"] for d in d7["da_luu"]], "chữ ký gốc vẫn còn trong kho (sao chép, không di chuyển)"
# xoá chữ ký "đã gắn ở công ty khác" khỏi danh sách chưa gán của công ty NÀY: chỉ ẩn ở đây, công ty cũ + kho chung giữ nguyên
run(server.chu_ky_luu(8, Req({"khoa": "cccd:888000222", "ten": "Người Khác 2", "anh": anh(), "xac_nhan": True})))
assert "cccd:888000222" in [d["khoa"] for d in server.chu_ky_danh_sach(7, 2026)["da_luu"]]
server.chu_ky_an_da_luu(7, "cccd:888000222")
assert "cccd:888000222" not in [d["khoa"] for d in server.chu_ky_danh_sach(7, 2026)["da_luu"]], "đã ẩn ở công ty này"
assert server.chu_ky_danh_sach(8, 2026)["tong_kho_chung"] == server.chu_ky_danh_sach(7, 2026)["tong_kho_chung"] and "cccd:888000222" in server._ck_doc_het(7)[0], "kho chung giữ nguyên"
ROWS.pop()

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
# HỢP ĐỒNG PART-TIME (loai 'pt'): chỉ những người tick Part-time; hợp đồng toàn thời gian / quy chế / thang lương không gồm họ
HDR_PT = HDR + ['Part-time', 'Lương theo giờ']
ROWS_PT = [r + ['', ''] for r in ROWS[:2]] + [ROWS[2] + ['x', 26000]]
server.nhap_lieu_get = lambda cid, loai="in": {"header": HDR_PT, "rows": ROWS_PT} if loai == "nv" else {"header": [], "rows": []}
server._luong_doc_nam = lambda cid, nam: (server._luong_chuan_tham_so(None, nam), {}, "", [nam])
dpt = server.van_ban_du_lieu(7, 2026)
assert [(n["ten"], n["part_time"], n["luong_gio"]) for n in dpt["nhan_vien"]] == [("Nhân Viên 1", False, 0), ("Nhân Viên 2", False, 0), ("Nhân Viên 3", True, 26000.0)]
rp = run(server.van_ban_xem_truoc(7, Req({"loai": "pt", "nam": 2026, "tuy_chon": {"pt_gio_ngay": "2"}})))
assert rp["so_van_ban"] == 1 and "NHÂN VIÊN 3" in rp["html"] and "NHÂN VIÊN 1" not in rp["html"] and "KHÔNG TRỌN THỜI GIAN" in rp["html"] and "26.000 đồng/giờ" in rp["html"]
assert any("Ngưỡng 2.530.000" in c["nd"] for c in rp["canh_bao"])
rh = run(server.van_ban_xem_truoc(7, Req({"loai": "hd", "nam": 2026})))
assert rh["so_van_ban"] == 2 and "NHÂN VIÊN 3" not in rh["html"], "hợp đồng toàn thời gian không gồm người part-time"
assert "NHÂN VIÊN 3" not in run(server.van_ban_xem_truoc(7, Req({"loai": "tl", "nam": 2026})))["html"] and "Nhân Viên 3" not in run(server.van_ban_xem_truoc(7, Req({"loai": "qc", "nam": 2026})))["html"]
server.nhap_lieu_get = lambda cid, loai="in": {"header": HDR, "rows": ROWS} if loai == "nv" else {"header": [], "rows": []}
try:
    run(server.van_ban_xem_truoc(7, Req({"loai": "pt", "nam": 2026}))); raise SystemExit("phải lỗi: chưa có người part-time")
except HTTPException as e:
    assert e.status_code == 404
# update.py phải tải kèm module mới (nếu không, máy người dùng cập nhật xong sẽ thiếu file -> không khởi động được)
import update
assert "van_ban_lao_dong.py" in update.FILES
print("PASS")
