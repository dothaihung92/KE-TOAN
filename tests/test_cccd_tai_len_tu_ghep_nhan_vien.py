import asyncio
import base64
import io
import os
import sys
import tempfile

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import cccd_doc as c
import server
from PIL import Image

# Dữ liệu GIẢ (không phải người thật). Số 012345678901: 9 số cuối 345678901, số kiểm tra MRZ = 3.
TRUOC = ["CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", "CAN CUOC CONG DAN", "Citizen Identity Card", "012345678901", "SO / No.:",
         "Ho va ten / Full name:", "NGUYEN VAN MAU", "Ngay sinh / Date of birth:", "15/03/1990", "Que quan / Place of origin:"]
SAU = ["Dac diem nhan dang / Personal identification", "Ngay.thang.nam/Date.month,year05/06/2021", "CUC TRUONG CUC CANH SAT",
       "Ngon tro trai", "IDVNM3456789013012345678901<<5", "9003153M3103157VNM<<<<<<<<<<<2", "NGUYEN<<VAN<MAU<<<<<<<<<<<<<<<<"]

t = c.phan_tich_dong(TRUOC)
assert (t["mat"], t["so"], t["ten"], t["ngay_sinh"]) == ("truoc", "012345678901", "NGUYEN VAN MAU", "15/03/1990"), t
s = c.phan_tich_dong(SAU)
assert (s["mat"], s["so"], s["ten"], s["ngay_cap"], s["mrz_ok"]) == ("sau", "012345678901", "NGUYEN VAN MAU", "05/06/2021", True), s
assert s["ngay_sinh"] == "15/03/1990"                       # lấy từ dòng MRZ 2 khi mặt sau
assert c.phan_tich_dong(["Hóa đơn bán hàng", "Tổng cộng 120.000"])["mat"] == ""   # không phải CCCD
assert c.chuan_so(12345678901) == "012345678901" and c.chuan_so("0123 4567 8901") == "012345678901"
assert c.chuan_ten("Nguyễn Văn  Mậu") == "NGUYEN VAN MAU"

H = ["STT", "Mã NV", "Họ và tên", "Ngày sinh", "Địa chỉ hiện đang cư trú", "CCCD", "Ngày cấp"]
docs = [{"id": 0, **t}, {"id": 1, **s}]

# 1) khớp theo SỐ (kể cả Excel mất số 0 đầu); mặt trước + sau thành 1 người; chỉ điền ô trống
rows = [[1, "NV01", "Trần Thị B", "", "", "", ""], [2, "NV02", "Nguyễn Văn Mẫu", "", "", 12345678901, "07/07/2020"]]
g = c.ghep(docs, H, rows)["nhom"]
assert len(g) == 1 and g[0]["row"] == 1 and g[0]["cach"] == "so" and g[0]["truoc"] == [0] and g[0]["sau"] == [1]
assert g[0]["dien"] == {"Ngày sinh": "15/03/1990"}, g[0]["dien"]          # CCCD và Ngày cấp đã có -> KHÔNG ghi đè

# 2) khớp theo HỌ TÊN khi ô CCCD trống; mặt sau MRZ mất số vẫn ghép được theo tên
rows2 = [[1, "NV01", "Nguyễn Văn Mẫu", "", "", "", ""]]
g = c.ghep(docs, H, rows2)["nhom"]
assert g[0]["row"] == 0 and g[0]["cach"] == "ten" and g[0]["dien"] == {"CCCD": "012345678901", "Ngày sinh": "15/03/1990", "Ngày cấp": "05/06/2021"}
sau_khong_so = {"id": 1, "mat": "sau", "so": "", "ten": "NGUYEN VAN MAU", "ngay_cap": "05/06/2021", "ngay_sinh": ""}
g = c.ghep([docs[0], sau_khong_so], H, rows2)["nhom"]
assert len(g) == 1 and g[0]["truoc"] == [0] and g[0]["sau"] == [1]

# 3) 2 người trùng tên: không tự gắn, hiện ứng viên; trùng tên nhưng khác số CCCD -> không gắn
rows3 = [[1, "A", "Nguyễn Văn Mẫu", "", "", "", ""], [2, "B", "Nguyễn Văn Mẫu", "", "", "", ""]]
g = c.ghep(docs, H, rows3)["nhom"][0]
assert g["row"] == -1 and g["ung_vien"] == [0, 1] and g["canh_bao"]
rows4 = [[1, "A", "Nguyễn Văn Mẫu", "", "", "999999999999", ""]]
g = c.ghep(docs, H, rows4)["nhom"][0]
assert g["row"] == -1 and g["ung_vien"] == [0] and any("khác số" in x for x in g["canh_bao"])

# 4) OCR sai 1 chữ: gần đúng, có cảnh báo; tên xa -> không gắn
doc_sai = [{"id": 0, **{**t, "ten": "NGUYEN VAN MAL"}}]
g = c.ghep(doc_sai, H, rows2)["nhom"][0]
assert g["row"] == -1 or g["cach"] in ("so", "ten", "gan_dung")
g = c.ghep([{"id": 0, "mat": "sau", "so": "", "ten": "NGUYEN VAN MAL", "ngay_cap": "", "ngay_sinh": ""}], H, rows2)["nhom"][0]
assert g["row"] == 0 and g["cach"] == "gan_dung" and g["canh_bao"]
g = c.ghep([{"id": 0, "mat": "sau", "so": "", "ten": "LE QUANG HUY", "ngay_cap": "", "ngay_sinh": ""}], H, rows2)["nhom"][0]
assert g["row"] == -1

# 5) 2 người khác nhau, ảnh lẫn lộn thứ tự: không nhập nhằng
t2 = {"mat": "truoc", "so": "098765432109", "ten": "LE THI HOA", "ngay_sinh": "", "ngay_cap": ""}
s2 = {"mat": "sau", "so": "098765432109", "ten": "LE THI HOA", "ngay_sinh": "", "ngay_cap": ""}
rows5 = [[1, "A", "Nguyễn Văn Mẫu", "", "", "", ""], [2, "B", "Lê Thị Hoa", "", "", "", ""]]
g = c.ghep([{"id": 3, **s2}, {"id": 0, **t}, {"id": 2, **t2}, {"id": 1, **s}], H, rows5)["nhom"]
tim = {x["so"]: x for x in g}
assert len(g) == 2 and tim["012345678901"]["row"] == 0 and tim["098765432109"]["row"] == 1
assert tim["098765432109"]["truoc"] == [2] and tim["098765432109"]["sau"] == [3]

# 6) file không phải ảnh -> báo lỗi, không văng
assert c.doc_anh(b"khong phai anh")["mat"] == "" and c.doc_anh(b"")["canh_bao"]

# 7) lưu / xem / xoá ảnh theo số CCCD (cục bộ trong DB), kiểm tra file rác bị bỏ qua
td = tempfile.mkdtemp()
server.DB_PATH = os.path.join(td, "t.db")
server.DATA_DIR = td
server.init_db()


def uri(mau, kt=(3000, 2000)):
    b = io.BytesIO()
    Image.new("RGB", kt, mau).save(b, "PNG")
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()


r = server.nhap_lieu_cccd_luu.__wrapped__ if hasattr(server.nhap_lieu_cccd_luu, "__wrapped__") else server.nhap_lieu_cccd_luu
kq = asyncio.run(r(1, {"items": [{"so": "012345678901", "ten": "NGUYEN VAN MAU", "truoc": uri("red"), "sau": uri("blue")},
                                 {"so": "123", "truoc": uri("red")},
                                 {"so": "098765432109", "truoc": "data:image/png;base64,AAAA", "sau": "khong phai"}]}))
assert kq["so_anh"] == 2, kq
ds = server.nhap_lieu_cccd_ds(1)["ds"]
assert ds == [{"so": "012345678901", "ten": "NGUYEN VAN MAU", "truoc": True, "sau": True}], ds
assert server.nhap_lieu_cccd_ds(2)["ds"] == []                                   # công ty khác không thấy
im = Image.open(io.BytesIO(server.nhap_lieu_cccd_anh(1, "012345678901", "truoc").body))
assert max(im.size) == 1600 and im.format == "JPEG"                              # đã thu nhỏ
hd = server.nhap_lieu_cccd_anh(1, "012345678901", "sau", tai=1).headers
assert hd["content-disposition"] == 'attachment; filename="CCCD_012345678901_mat_sau.jpg"'
server.nhap_lieu_cccd_xoa(1, "012345678901", mat="truoc")                         # xoá riêng 1 mặt
assert server.nhap_lieu_cccd_ds(1)["ds"] == [{"so": "012345678901", "ten": "NGUYEN VAN MAU", "truoc": False, "sau": True}]
server.nhap_lieu_cccd_xoa(1, "012345678901")
assert server.nhap_lieu_cccd_ds(1)["ds"] == []

# 8) Ca thật "Lỗi ghép: Internal Server Error": máy cập nhật bằng update.py CŨ (chưa có cccd_doc.py trong danh sách file)
#    -> server tự tải bù cccd_doc.py rồi nạp; update.py mới đứng ĐẦU danh sách và tự chạy lại khi chính nó vừa đổi.
import importlib, shutil, update
thu_muc = tempfile.mkdtemp()
goc_base, goc_tai = server.BASE_DIR, update._tai_raw
noi_dung = open(os.path.join(_REPO_ROOT, "cccd_doc.py"), "rb").read()
sys.modules.pop("cccd_doc", None)
sys.path.insert(0, thu_muc)
sys.path[:] = [x for x in sys.path if os.path.abspath(x or ".") != _REPO_ROOT] + []
try:
    server.BASE_DIR = thu_muc
    update._tai_raw = lambda path, timeout=20: noi_dung if path == "cccd_doc.py" else b""
    m = server._cccd_mod()
    assert os.path.exists(os.path.join(thu_muc, "cccd_doc.py")) and m.chuan_so("12345678901") == "012345678901"
finally:
    server.BASE_DIR, update._tai_raw = goc_base, goc_tai
    sys.path.insert(0, _REPO_ROOT)
up = open(os.path.join(_REPO_ROOT, "update.py"), encoding="utf-8").read()
assert update.FILES[0] == "update.py" and "cccd_doc.py" in update.FILES and 'HDDT_UPDATE_LAN2' in up
html = open(os.path.join(_REPO_ROOT, "static", "index.html"), encoding="utf-8").read()
assert "${nvCccdNut(ri)}" in html and "function nvCccdMo(" in html and "function nvCccdUp(" in html
print("PASS: CCCD tải lên -> đọc mặt trước/sau, ghép đúng người theo số/họ tên, chỉ điền ô trống, lưu cục bộ theo công ty.")
