import base64, io, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import openpyxl
import san_tmdt as m

# Đơn hàng sàn TMĐT -> form MISA "Chứng từ bán hàng". Dữ liệu GIẢ, tên cột theo kiểu file xuất của từng sàn.
def xlsx(hang):
    wb = openpyxl.Workbook(); ws = wb.active
    for r in hang:
        ws.append(r)
    b = io.BytesIO(); wb.save(b); return b.getvalue()

shopee = xlsx([["Mã đơn hàng", "Ngày đặt hàng", "Trạng Thái Đơn Hàng", "Tên sản phẩm", "SKU phân loại hàng", "Tên phân loại hàng", "Giá ưu đãi", "Số lượng",
                "Tổng giá bán (sản phẩm)", "Tên Người nhận", "Số điện thoại", "Tỉnh/Thành phố", "Địa chỉ nhận hàng", "Thời gian hoàn thành đơn hàng"],
               ["2411050ABC", "2026-11-01 10:00", "Hoàn thành", "Áo thun", "AT-01", "Đỏ, L", 108000, 2, 216000, "Khách A", "0900000001", "TP. Hồ Chí Minh", "1 Đường A", "2026-11-03 09:00"],
               ["2411050ABC", "2026-11-01 10:00", "Hoàn thành", "Mũ", "MU-01", "", 54000, 1, 54000, "Khách A", "0900000001", "TP. Hồ Chí Minh", "1 Đường A", "2026-11-03 09:00"],
               ["2411050XYZ", "2026-11-02 10:00", "Đã hủy", "Áo thun", "AT-01", "", 108000, 1, 108000, "Khách B", "", "", "", ""]])
dong, ghi = m.doc_file_don_hang(shopee, "Order.all.xlsx", "shopee")
assert len(dong) == 3 and dong[0]["ma_don"] == "2411050ABC" and dong[0]["ten_hang"] == "Áo thun" and dong[0]["phan_loai"] == "Đỏ, L" and dong[0]["ngay"] == "03/11/2026" and dong[0]["thanh_tien"] == 216000
loc = m.loc_don(dong)
assert [x["ma_don"] for x in loc] == ["2411050ABC", "2411050ABC"] and m.tong_hop(loc) == {"so_don": 1, "so_dong": 2, "tong_tien": 270000}
print("PASS 1: Shopee — dò cột tiếng Việt, ghép phân loại, bỏ đơn huỷ.")

tiktok = "Order ID,Order Status,Product Name,Seller SKU,Quantity,SKU Unit Original Price,SKU Subtotal Before Discount,SKU Platform Discount,SKU Seller Discount,SKU Subtotal After Discount,Created Time,Recipient\n" \
         "577000000000000001,Completed,Kem dưỡng,KD-50,1,\"200,000\",\"200,000\",\"10,000\",\"20,000\",\"170,000\",05/11/2026 08:00:00 AM,Người Nhận\n" \
         "577000000000000002,Cancelled,Kem dưỡng,KD-50,1,\"200,000\",\"200,000\",0,0,\"200,000\",05/11/2026 08:00:00 AM,Người Nhận\n"
dong, _g = m.doc_file_don_hang(tiktok.encode("utf-8-sig"), "tiktok.csv", "tiktok")
loc = m.loc_don(dong)
assert len(loc) == 1 and loc[0]["thanh_tien"] == 170000 and loc[0]["sku"] == "KD-50"        # = số khách thanh toán (sau giảm của người bán + TikTok)
print("PASS 2: TikTok — CSV tiếng Anh, số có dấu phẩy ngăn nghìn.")

lazada = xlsx([["orderItemId", "orderNumber", "createTime", "sellerSku", "itemName", "unitPrice", "paidPrice", "status", "customerName"],
               ["9001", "301000000000001", "05 Nov 2026 10:00", "SP-9", "Bình nước", 120000, 120000, "delivered", "C"],
               ["9002", "301000000000002", "2026-11-05", "SP-9", "Bình nước", 120000, 120000, "returned", "D"]])
dong, _g = m.doc_file_don_hang(lazada, "lazada.xlsx", "lazada")
loc = m.loc_don(dong)
assert len(loc) == 1 and loc[0]["ma_don"] == "301000000000001" and loc[0]["ngay"] == "05/11/2026"
print("PASS 3: Lazada — đơn delivered giữ lại, returned bỏ.")

import server
H = server.BAN_HANG_HEADERS
loc = m.loc_don(m.doc_file_don_hang(shopee, "x.xlsx")[0])
rows = m.sang_ban_hang(loc, H, "shopee", 8, True)
g = lambda r, k: r[H.index(k)]
r0 = rows[0]
assert g(r0, "Số chứng từ (*)") == "SP2411050ABC" and g(r0, "Lập kèm hóa đơn") == 1 and g(r0, "Đã lập hóa đơn") == 0
assert g(r0, "Mã hàng (*)") == "AT-01" and g(r0, "Số lượng") == 2 and g(r0, "Thành tiền") == 200000 and g(r0, "Tiền thuế GTGT") == 16000 and g(r0, "% thuế GTGT") == 8
assert g(r0, "TK Tiền/Chi phí/Nợ (*)") == "131" and g(r0, "TK Doanh thu/Có (*)") == "5111" and g(r0, "TK thuế GTGT") == "33311"
assert sum(g(r, "Thành tiền") + g(r, "Tiền thuế GTGT") for r in rows) == 270000          # tổng sau thuế khớp đúng tiền khách trả
print("PASS 4: MISA Chứng từ bán hàng: 1 đơn = 1 chứng từ, tách VAT 8% từ giá đã gồm thuế, tổng khớp.")

# API: đọc + xuất file (thư mục tạm, không ghi ra Desktop thật)
tmp = tempfile.mkdtemp()
server.DATA_DIR = tmp
server.DOWNLOAD_DIR = tmp
server._get_desktop_dir = lambda: os.path.join(tmp, "desktop_khong_co")
r = server.san_doc(1, {"san": "shopee", "ten_file": "Order.all.xlsx", "b64": base64.b64encode(shopee).decode()})
assert r["tong"]["so_don"] == 1 and any("bỏ 1 dòng" in c for c in r["canh_bao"])
assert server.san_ds_file(1, "shopee")["file"][0]["ten"] == "Order.all.xlsx"
import sqlite3
conn = sqlite3.connect(":memory:", check_same_thread=False); conn.row_factory = sqlite3.Row
conn.execute("CREATE TABLE companies (id INTEGER, mst TEXT)"); conn.execute("INSERT INTO companies VALUES (1, '0300000001')")
class K:
    def execute(self, *a): return conn.execute(*a)
    def close(self): pass
server.db = lambda: K()
resp = server.san_xuat(1, {"san": "shopee", "ten_file": "Order.all.xlsx", "tuy_chon": {"thue_suat": "10"}})
wb = openpyxl.load_workbook(resp.path)
ws = wb.active
assert [c.value for c in ws[1]] == H and ws.max_row == 3
assert ws.cell(2, H.index("% thuế GTGT") + 1).value == 10
for bad in ({"san": "abc", "ten_file": "x.xlsx"}, {"san": "shopee", "ten_file": "../../etc/passwd"}):
    try:
        server.san_doc(1, bad); raise SystemExit("phải báo lỗi")
    except server.HTTPException:
        pass
print("PASS 5: API đọc/xuất file, chặn sàn lạ và đường dẫn ngoài thư mục.")


# File Shopee kiểu MỚI (giả lập đúng tiêu đề file xuất thật): kích thước bảng ghi sai, trạng thái dài "Người mua xác nhận đã nhận được hàng...",
# cột "Tổng giá bán (sản phẩm)" đổi tên -> tiền = Giá ưu đãi x Số lượng; bỏ đơn huỷ và trả hàng đã chấp thuận.
H2 = ["Mã đơn hàng", "Mã Kiện Hàng", "Ngày đặt hàng", "Trạng Thái Đơn Hàng", "Trạng thái Trả hàng/Hoàn tiền", "SKU sản phẩm", "Tên sản phẩm", "SKU phân loại hàng",
      "Tên phân loại hàng", "Giá gốc", "Giá ưu đãi", "Số lượng", "Số lượng sản phẩm được hoàn trả", "Tổng số tiền Người mua thanh toán", "Tổng giá trị đơn hàng (VND)",
      "Tổng số tiền người mua thanh toán", "Thời gian hoàn thành đơn hàng", "Tên Người nhận"]
NHAN = "Người mua xác nhận đã nhận được hàng, tuy nhiên Người mua vẫn có thể gửi yêu cầu Trả hàng/Hoàn tiền tới ngày 2026-11-14."
sp2 = xlsx([H2,
            ["261029AAAA0001", "1", "2026-10-29 00:01", NHAN, "", "lens-a", "Lens A", "", "1.00", "250000.00", "134000.00", "2", "0", "268000.00", "246060.00", "246060.00", "2026-11-02 09:27", "x"],
            ["261029AAAA0001", "1", "2026-10-29 00:01", NHAN, "", "qua", "Quà tặng", "", "", "0.00", "0.00", "1", "0", "0.00", "246060.00", "246060.00", "", "x"],
            ["261029BBBB0002", "2", "2026-10-29 09:00", "Đã hủy", "", "lens-a", "Lens A", "", "", "250000.00", "134000.00", "1", "0", "134000.00", "0", "0", "", "y"],
            ["261029CCCC0003", "3", "2026-10-29 10:00", "Hoàn thành", "Đã Chấp Thuận Yêu Cầu", "lens-a", "Lens A", "", "", "250000.00", "134000.00", "1", "1", "134000.00", "0", "0", "", "z"],
            ["261029DDDD0004", "4", "2026-10-29 11:00", "Đã giao", "", "lens-b", "Lens B", "", "", "200000.00", "129000.00", "1", "0", "129000.00", "0", "0", "", "w"],
            ["261030EEEE0005", "5", "2026-10-30 11:00", "Đã giao", "", "lens-b", "Lens B", "", "", "200000.00", "129000.00", "1", "0", "129000.00", "0", "0", "", "w"]])
dong, _g = m.doc_file_don_hang(sp2, "Order.all.20261029_20261029.xlsx", "shopee")
loc = m.loc_don(dong, True, "2026-10-29", "2026-10-29")
assert [x["ma_don"] for x in loc] == ["261029AAAA0001", "261029DDDD0004"] and loc[0]["thanh_tien"] == 268000      # dòng Quà tặng 0đ bị bỏ, [(x["ma_don"], x["thanh_tien"]) for x in loc]
rows = m.sang_hoa_don_gtgt(loc, "shopee", 5, "05/11/2026")
assert [r[0] for r in rows] == [1, 2]                                              # mỗi đơn hàng = 1 hoá đơn
assert rows[0][1:] == ["05/11/2026", "", "", "", "Bán cho người tiêu dùng - Shopee - 261029AAAA0001", "", "", "", "Tiền mặt/Chuyển khoản", "Lens A", "Cái", 2, 127619, 255238, 5, 12762, 268000, "261029AAAA0001"]
assert rows[1][14] == 122857 and rows[1][17] == 122857 + 6143                       # ROUND(129000/1,05) như công thức file mẫu
tt_rows = m.sang_hoa_don_gtgt(m.loc_don(m.doc_file_don_hang(tiktok.encode("utf-8-sig"), "t.csv", "tiktok")[0]), "tiktok", 5)
assert tt_rows[0][10] == "Kem dưỡng-577000000000000001-Tiktok"
lz_rows = m.sang_hoa_don_gtgt(m.loc_don(m.doc_file_don_hang(lazada, "l.xlsx", "lazada")[0]), "lazada", "KCT")
assert lz_rows[0][10] == "Bình nước-301000000000001-LAZADA" and lz_rows[0][14] == 120000 and lz_rows[0][15] == "KCT" and lz_rows[0][16] == 0
print("PASS 6: file Shopee kiểu mới + sheet 'Hóa đơn GTGT (3)' đúng công thức file mẫu (Shopee/TikTok/Lazada, KCT).")

server.san_doc(1, {"san": "shopee", "ten_file": "Order.all.20261029_20261029.xlsx", "b64": base64.b64encode(sp2).decode()})
resp = server.san_xuat_hd(1, {"san": "shopee", "ten_file": "Order.all.20261029_20261029.xlsx", "tu_ngay": "29/10/2026", "den_ngay": "29/10/2026",
                              "tuy_chon": {"thue_suat": "5", "ngay_hd": "2026-11-05"}})
ws = openpyxl.load_workbook(resp.path)["Hóa đơn GTGT (3)"]
assert ws["A1"].value == "0" and [c.value for c in ws[2]][:18] == m.HD_HEADERS and ws.max_row == 4 and ws["B3"].value == "05/11/2026" and ws["S3"].value == "261029AAAA0001"
print("PASS 7: API xuất file import hoá đơn (A1=0, tiêu đề dòng 2, dữ liệu từ dòng 3).")


# Mở bằng Chrome người dùng đang dùng (không mở trình duyệt tự động); file nhận từ thư mục Downloads của Chrome
import webbrowser
mo = []
webbrowser.open = lambda url, new=0: mo.append(url) or True
server._san_chrome = lambda: (None, None)                                                # máy không có Chrome -> trình duyệt mặc định
assert server.san_mo_trinh_duyet(1, {"san": "shopee", "tu_ngay": "2026-11-04", "den_ngay": "2026-11-04"})["ok"] and mo[-1].endswith("#ketoan-xuat=2026-11-04_2026-11-04&p=8686")
mo.clear()
assert server.san_mo_trinh_duyet(1, {"san": "shopee"})["ok"] and mo == ["https://banhang.shopee.vn/portal/sale/order#ketoan-xuat&p=8686"]
# có Google Chrome: mở bằng chrome.exe đúng hồ sơ (tài khoản Gmail) người dùng chọn; tên hồ sơ lạ bị bỏ qua
import json as _js, subprocess as _sp
ud = os.path.join(tmp, "UserData"); os.makedirs(ud)
_js.dump({"profile": {"last_used": "Profile 1", "info_cache": {"Default": {"name": "Cá nhân", "user_name": "a@gmail.com"},
                                                                "Profile 1": {"name": "Shop", "user_name": "shop@gmail.com"}}}}, open(os.path.join(ud, "Local State"), "w"))
server._san_chrome = lambda: ("C:/chrome.exe", ud)
hs = server.san_chrome_ho_so()["ho_so"]
assert [(h["thu_muc"], h["email"], h["dung_gan_nhat"]) for h in hs] == [("Profile 1", "shop@gmail.com", True), ("Default", "a@gmail.com", False)]
lenh = []
class _P:
    def __init__(self, a, **k): lenh.append(a)
server.subprocess.Popen = _P
r = server.san_mo_trinh_duyet(1, {"san": "shopee", "ho_so": "Profile 1"})
assert r["ok"] and lenh[-1] == ["C:/chrome.exe", "--profile-directory=Profile 1", "https://banhang.shopee.vn/portal/sale/order#ketoan-xuat&p=8686"]
server.san_mo_trinh_duyet(1, {"san": "shopee", "ho_so": "x & calc"})
assert lenh[-1] == ["C:/chrome.exe", "https://banhang.shopee.vn/portal/sale/order#ketoan-xuat&p=8686"]
assert "webdriver" not in open(server.__file__, encoding="utf-8").read().split("def san_mo_trinh_duyet")[1].split("def san_bookmarklet")[0]
dl = os.path.join(tmp, "Downloads"); os.makedirs(dl)
server._san_thu_muc_downloads = lambda: dl
open(os.path.join(dl, "Order.all.20261104_20261104.xlsx"), "wb").write(sp2)
open(os.path.join(dl, "baocao_khac.xlsx"), "wb").write(sp2)
ds = server.san_ds_file(2, "shopee")["file"]
assert [(f["ten"], f["nguon"]) for f in ds] == [("Order.all.20261104_20261104.xlsx", "dl")], ds       # chỉ nhận file đơn hàng Shopee trong Downloads
r = server.san_doc(2, {"san": "shopee", "ten_file": "Order.all.20261104_20261104.xlsx", "nguon": "dl"})
assert r["tong_goc"]["so_don"] == 5
from urllib.parse import unquote
bm = server.san_bookmarklet()["ma"]
assert bm.startswith("javascript:(async()=>{") and "\n" not in bm and " " not in bm                       # mã hoá %XX, không còn xuống dòng/khoảng trắng thô
assert "Lịch sử Xuất Báo cáo" in unquote(bm) and "Tải về" in unquote(bm) and "confirm(" in unquote(bm) and unquote(bm).endswith("await __ketoanXuat(false)})();")
# tiện ích Chrome: chỉ chạy trên trang sàn, chỉ tự xuất khi trang do phần mềm mở (#ketoan-xuat); có trong danh sách cập nhật
import json as _j
TI = os.path.join(os.path.dirname(server.__file__), "tien_ich_chrome", "xuat_don_tmdt")
mf = _j.load(open(os.path.join(TI, "manifest.json"), encoding="utf-8"))
assert mf["manifest_version"] == 3 and sorted(mf.get("permissions", [])) == ["cookies", "debugger", "downloads", "storage"] and len(mf.get("description", "")) <= 132
assert all(u.startswith("https://") and any(k in u for k in ("shopee.vn", "tiktok.com", "lazada.vn")) or u == "http://127.0.0.1/*" for u in mf["host_permissions"])   # chỉ cookie của sàn + phần mềm trên máy
assert mf["background"]["service_worker"] == "nen.js" and all(u.startswith("https://") and any(k in u for k in ("shopee", "tiktok", "lazada", "meinvoice", "vietcombank.com.vn", "acb.com.vn", "vietinbank.vn", "techcombank.com")) for c in mf["content_scripts"] for u in c["matches"])
assert all(c["js"] == ["ngan_hang.js"] for c in mf["content_scripts"] if any("vietcombank" in u for u in c["matches"]))      # trang ngân hàng chỉ chạy mã lấy sao kê
assert "ketoan-xuat" in open(os.path.join(TI, "dau.js"), encoding="utf-8").read() and "__ketoanXuat(true,c)" in open(os.path.join(TI, "tu_dong.js"), encoding="utf-8").read()
up = open(os.path.join(os.path.dirname(server.__file__), "update.py"), encoding="utf-8").read()
assert all(f'"tien_ich_chrome/xuat_don_tmdt/{f}"' in up for f in ("manifest.json", "dau.js", "chay.js", "tu_dong.js", "misa.js", "nen.js", "giu_blob.js", "ngan_hang.js"))
print("PASS 8: mở trang bằng trình duyệt mặc định, nhận file từ Downloads, nút dấu trang tự bấm Xuất/Tải về.")

# Cài tiện ích giúp: chép ra thư mục cố định trên ổ máy + mở chrome://extensions đúng hồ sơ
os.environ["LOCALAPPDATA"] = os.path.join(tmp, "Local")
os.makedirs(os.environ["LOCALAPPDATA"])
lenh.clear()
server._san_chrome = lambda: ("C:/chrome.exe", ud)
r = server.san_cai_tien_ich({"ho_so": "Profile 1"})
assert r["da_mo_chrome"] and lenh[-1] == ["C:/chrome.exe", "--profile-directory=Profile 1", "chrome://extensions"]
assert sorted(os.listdir(r["thu_muc"])) == ["chay.js", "dau.js", "giu_blob.js", "manifest.json", "misa.js", "nen.js", "ngan_hang.js", "tu_dong.js"] and r["thu_muc"].startswith(os.environ["LOCALAPPDATA"])
print("PASS 9: cài tiện ích giúp — chép ra ổ máy, mở chrome://extensions đúng hồ sơ.")


# Cảnh báo khi file tải về không bao trùm khoảng ngày đã chọn (vd tải nhầm báo cáo cũ)
r = server.san_doc(1, {"san": "shopee", "ten_file": "Order.all.20261006_20261105.xlsx", "b64": base64.b64encode(sp2).decode(), "tu_ngay": "2026-10-29", "den_ngay": "2026-10-29"})
assert not any("KHÔNG bao trùm" in c for c in r["canh_bao"])
r = server.san_doc(1, {"san": "shopee", "ten_file": "Order.all.20260915_20260914.xlsx", "b64": base64.b64encode(sp2).decode(), "tu_ngay": "2026-10-29", "den_ngay": "2026-10-29"})
assert any("KHÔNG bao trùm" in c for c in r["canh_bao"]), r["canh_bao"]
print("PASS 10: cảnh báo file tải về không bao trùm khoảng ngày đã chọn.")


# Lazada: tiện ích chờ "Các nhiệm vụ chạy thành công" rồi hỏi phần mềm file đã tải xong chưa; phần mềm chép file ra DESKTOP và nhận file dù tên không theo mẫu
import time as _t
moc = int(_t.time() * 1000)
for _f in os.listdir(dl):
    os.utime(os.path.join(dl, _f), (_t.time() - 120, _t.time() - 120))          # file đã có từ trước khi bấm Export All
r = server.san_file_moi("lazada", moc)
assert r == {"co": False, "dang_tai": False}, r                                     # file cũ trong Downloads (tạo trước mốc) không tính
dang = os.path.join(dl, "x9.xlsx.crdownload"); open(dang, "wb").write(b"1")
assert server.san_file_moi("lazada", moc) == {"co": False, "dang_tai": True}
os.remove(dang)
open(os.path.join(dl, "Order_Export_8237220.xlsx"), "wb").write(lazada)
r = server.san_file_moi("lazada", moc)
assert r["co"] and not r["dang_tai"] and r["ten"] == "Order_Export_8237220.xlsx" and "desktop" not in r
desk = os.path.join(tmp, "desk_lz"); os.makedirs(desk)
server._get_desktop_dir = lambda: desk
r = server.san_file_moi("lazada", moc, 1, "2026-10-29_2026-11-06")
assert r["desktop"] == os.path.join(desk, "Lazada_DonHang_2026-10-29_2026-11-06.xlsx") and open(r["desktop"], "rb").read() == lazada
assert any(f["ten"] == "Order_Export_8237220.xlsx" and f["nguon"] == "dl" for f in server.san_ds_file(3, "lazada")["file"])     # màn Hỗ trợ xuất HĐ tự nhận file
try:
    server.san_file_moi("abc", moc); raise SystemExit("phải chặn sàn lạ")
except server.HTTPException:
    pass
print("PASS 11: Lazada — hỏi file mới tải xong trong Downloads, chép ra Desktop, màn hình tự nhận file.")

# Shopee/TikTok: Chrome bật "hỏi nơi lưu" -> người dùng bấm Save lưu thẳng ra Desktop: nhận file ở Desktop (không chép thêm), màn hình vẫn nhận và đọc được
moc2 = int(_t.time() * 1000) + 6000                                                          # sau các file của PASS 11
open(os.path.join(desk, "Book5.xlsx"), "wb").write(sp2); open(os.path.join(desk, "Lazada_DonHang_x.xlsx"), "wb").write(sp2)
for _f in ("Book5.xlsx", "Lazada_DonHang_x.xlsx"):
    os.utime(os.path.join(desk, _f), (moc2 / 1000 + 1, moc2 / 1000 + 1))
assert server.san_file_moi("shopee", moc2) == {"co": False, "dang_tai": False}                 # file khác trên Desktop không bị nhận nhầm
open(os.path.join(desk, "Order.all.20261029_20261106.xlsx.crdownload"), "wb").write(b"1")
os.utime(os.path.join(desk, "Order.all.20261029_20261106.xlsx.crdownload"), (moc2 / 1000 + 1, moc2 / 1000 + 1))
assert server.san_file_moi("shopee", moc2) == {"co": False, "dang_tai": True}
os.rename(os.path.join(desk, "Order.all.20261029_20261106.xlsx.crdownload"), os.path.join(desk, "Order.all.20261029_20261106.xlsx"))
open(os.path.join(desk, "Order.all.20261029_20261106.xlsx"), "wb").write(sp2)
os.utime(os.path.join(desk, "Order.all.20261029_20261106.xlsx"), (moc2 / 1000 + 2, moc2 / 1000 + 2))
r = server.san_file_moi("shopee", moc2, 1, "2026-10-29_2026-11-06")
assert r["co"] and r["desktop"] == os.path.join(desk, "Order.all.20261029_20261106.xlsx") and not os.path.exists(os.path.join(desk, "Shopee_DonHang_2026-10-29_2026-11-06.xlsx"))
r = server.san_ds_file(4, "shopee")["file"]
assert any(f["ten"] == "Order.all.20261029_20261106.xlsx" and f["nguon"] == "dl" for f in r), r
assert server.san_doc(4, {"san": "shopee", "ten_file": "Order.all.20261029_20261106.xlsx", "nguon": "dl"})["tong_goc"]["so_don"] == 5
print("PASS 12: Shopee/TikTok — file lưu thẳng ra Desktop (Chrome hỏi nơi lưu) vẫn được nhận, không nhận nhầm file khác trên Desktop.")

# Chrome bật "Hỏi vị trí lưu": tiện ích tự lấy nội dung file, gửi phần mềm lưu thẳng ra Desktop (không hiện hộp Save As); trùng tên thêm (1); chặn tên lạ
r = server.san_luu_file({"san": "tiktok", "ten": "Tất cả đơn hàng-2026-11-06-20_52.xlsx", "b64": "data:;base64," + base64.b64encode(lazada).decode()})
assert r["desktop"] == os.path.join(desk, "Tất cả đơn hàng-2026-11-06-20_52.xlsx") and open(r["desktop"], "rb").read() == lazada
r2 = server.san_luu_file({"san": "tiktok", "ten": "Tất cả đơn hàng-2026-11-06-20_52.xlsx", "b64": base64.b64encode(b"2").decode()})
assert r2["ten"] == "Tất cả đơn hàng-2026-11-06-20_52 (1).xlsx"
r3 = server.san_luu_file({"san": "lazada", "ten": "..\\..\\x/lazada_blob.xlsx", "b64": base64.b64encode(b"3").decode()})
assert os.path.dirname(r3["desktop"]) == desk and r3["ten"] == "lazada_blob.xlsx"
for bad in ({"san": "tiktok", "ten": "a.exe", "b64": "eA=="}, {"san": "x", "ten": "a.xlsx", "b64": "eA=="}, {"san": "tiktok", "ten": "a.xlsx", "b64": ""}):
    try:
        server.san_luu_file(bad); raise SystemExit("phải báo lỗi")
    except server.HTTPException:
        pass
moc3 = int(os.path.getmtime(r3["desktop"]) * 1000) - 1000
_k = server.san_file_moi("lazada", moc3, 1)
assert _k["desktop"] == r3["desktop"]                 # file tiện ích đã lưu ở Desktop -> nhận luôn, không chép thêm
print("PASS 13: lưu thẳng file tải từ sàn ra Desktop (thay hộp Save As), trùng tên thêm (1), chặn tên/đuôi lạ.")

# Hộp Save As nhớ thư mục lần trước (vd Desktop\NHAP LIEU): file lưu trong thư mục CON của Desktop vẫn được nhận; nút "Lưu ra Desktop" chép file đang chọn ra Desktop
sub = os.path.join(desk, "NHAP LIEU"); os.makedirs(sub, exist_ok=True)
moc4 = int(_t.time() * 1000) + 20000
f_sub = os.path.join(sub, "Tất cả đơn hàng-2026-11-08-20_36.xlsx"); open(f_sub, "wb").write(tiktok_xlsx if "tiktok_xlsx" in dir() else lazada)
os.utime(f_sub, (moc4 / 1000 + 1, moc4 / 1000 + 1))
k = server.san_file_moi("tiktok", moc4)
assert k["co"] and k["desktop"] == f_sub, k
dl2 = server._san_thu_muc_downloads()
open(os.path.join(dl2, "Tất cả đơn hàng-2026-11-09-10_00.xlsx"), "wb").write(lazada)
r = server.san_luu_desktop(4, {"san": "tiktok", "ten": "Tất cả đơn hàng-2026-11-09-10_00.xlsx"})
assert r["desktop"] == os.path.join(desk, "Tất cả đơn hàng-2026-11-09-10_00.xlsx") and not r["da_o_desktop"] and open(r["desktop"], "rb").read() == lazada
r = server.san_luu_desktop(4, {"san": "tiktok", "ten": "Tất cả đơn hàng-2026-11-09-10_00.xlsx"})
assert r["desktop"].endswith("(1).xlsx"), r                       # Desktop đã có bản trùng tên -> thêm (1), không ghi đè
for bad in ({"san": "tiktok", "ten": "khong_co.xlsx"}, {"san": "tiktok", "ten": "a.exe"}, {"san": "x", "ten": "a.xlsx"}):
    try:
        server.san_luu_desktop(4, bad); raise SystemExit("phải báo lỗi")
    except server.HTTPException:
        pass
print("PASS 14b: nhận file lưu trong thư mục con của Desktop; nút Lưu ra Desktop chép file đang chọn, trùng tên thêm (1), chặn tên lạ.")

# Chọn 1 lần nhiều file của cả 3 sàn: tự nhận sàn theo tên cột (kể cả tên file lạ), sắp theo sàn, lưu vào thư mục từng sàn; file lạ báo lỗi
assert m.nhan_dien_san(shopee, "a.xlsx") == "shopee" and m.nhan_dien_san(sp2, "x.xlsx") == "shopee"
assert m.nhan_dien_san(tiktok.encode("utf-8-sig"), "bao_cao.csv") == "tiktok" and m.nhan_dien_san(lazada, "4f1c.xlsx") == "lazada"
assert m.nhan_dien_san(xlsx([["A", "B"], [1, 2]]), "Order.all.20261101_20261105.xlsx") == "shopee"           # không rõ cột -> theo tên file
assert m.nhan_dien_san(xlsx([["A", "B"], [1, 2]]), "Book5.xlsx") == ""
b64 = lambda b: "data:;base64," + base64.b64encode(b).decode()
r = server.san_nhan_nhieu_file(7, {"files": [{"ten": "lz_9f.xlsx", "b64": b64(lazada)}, {"ten": "Book5.xlsx", "b64": b64(xlsx([["A"], [1]]))},
                                             {"ten": "tt.csv", "b64": b64(tiktok.encode("utf-8-sig"))}, {"ten": "sp_moi.xlsx", "b64": b64(sp2)}]})["file"]
assert [(x["ten"], x["san"], x.get("so_don")) for x in r] == [("sp_moi.xlsx", "shopee", 5), ("tt.csv", "tiktok", 2), ("lz_9f.xlsx", "lazada", 2), ("Book5.xlsx", "", None)], r
assert "loi" in r[3] and all(os.path.isfile(os.path.join(server._san_thu_muc(7, x["san"]), x["ten"])) for x in r[:3])
resp = server.san_xuat_hd_gop(7, {"ds": [{"san": x["san"], "ten_file": x["ten"], "nguon": "pm"} for x in r[:3]], "tu_ngay": "", "den_ngay": "", "tuy_chon": {"thue_suat": "5"}})
ws = openpyxl.load_workbook(resp.path)["Hóa đơn GTGT (3)"]
ma = [ws.cell(i, 19).value for i in range(3, ws.max_row + 1)]
assert ma[0] == "261029AAAA0001" and "577000000000000001" in ma and "301000000000001" in ma and ma.index("261029AAAA0001") < ma.index("577000000000000001") < ma.index("301000000000001"), ma
# 2 file của CÙNG 1 sàn có đơn trùng nhau: đơn chỉ xuất 1 lần
server.san_nhan_nhieu_file(8, {"files": [{"ten": "a.xlsx", "b64": b64(sp2)}, {"ten": "b.xlsx", "b64": b64(sp2)}]})
resp = server.san_xuat_hd_gop(8, {"ds": [{"san": "shopee", "ten_file": "a.xlsx", "nguon": "pm"}, {"san": "shopee", "ten_file": "b.xlsx", "nguon": "pm"}], "tuy_chon": {"thue_suat": "5"}})
ws = openpyxl.load_workbook(resp.path)["Hóa đơn GTGT (3)"]
ma = [ws.cell(i, 19).value for i in range(3, ws.max_row + 1)]
assert len(ma) == len(set(ma)), ma
print("PASS 14: chọn 1 lần nhiều file 3 sàn — tự nhận sàn, sắp Shopee→TikTok→Lazada, xuất gộp; 2 file cùng sàn không xuất trùng đơn.")
