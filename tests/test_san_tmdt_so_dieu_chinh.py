import base64, io, os, sys, tempfile, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import openpyxl
import san_tmdt as m
import server

# Sổ đơn đã xuất + không xuất trùng + phát hiện trả hàng/huỷ + hoá đơn điều chỉnh âm + cập nhật số hoá đơn từ MISA + cửa sổ ngày 30 ngày. Dữ liệu GIẢ.
def xlsx(hang):
    wb = openpyxl.Workbook(); ws = wb.active
    for r in hang:
        ws.append(r)
    b = io.BytesIO(); wb.save(b); return b.getvalue()
H = ["Mã đơn hàng", "Ngày đặt hàng", "Trạng Thái Đơn Hàng", "Trạng thái Trả hàng/Hoàn tiền", "SKU sản phẩm", "Tên sản phẩm", "Tên phân loại hàng", "Giá ưu đãi", "Số lượng",
     "Số lượng sản phẩm được hoàn trả", "Tổng giá bán (sản phẩm)", "Tên Người nhận"]
HT = "Người mua xác nhận đã nhận được hàng, tuy nhiên Người mua vẫn có thể gửi yêu cầu Trả hàng/Hoàn tiền tới ngày 2026-11-14."
def dong(ma, tt, tra, sku, ten, gia, sl, sl_tra=0):
    return [ma, "2026-10-29 10:00", tt, tra, sku, ten, "", gia, sl, sl_tra, gia * sl, "Khách"]
f1 = xlsx([H, dong("BILL000001", HT, "", "a", "Lens A", 134000, 2), dong("BILL000002", HT, "", "b", "Lens B", 129000, 1), dong("BILL000003", "Đã giao", "", "c", "Lens C", 100000, 3)])

tmp = tempfile.mkdtemp(); server.DATA_DIR = tmp; server.DOWNLOAD_DIR = tmp
server._get_desktop_dir = lambda: os.path.join(tmp, "khong_co")
import sqlite3
conn = sqlite3.connect(":memory:", check_same_thread=False); conn.row_factory = sqlite3.Row
conn.execute("CREATE TABLE companies (id INTEGER, mst TEXT)"); conn.execute("INSERT INTO companies VALUES (1, '0300000001')")
class K:
    def execute(self, *a): return conn.execute(*a)
    def close(self): pass
server.db = lambda: K()
B = {"san": "shopee", "ten_file": "Order.all.20261029_20261029.xlsx", "b64": base64.b64encode(f1).decode(), "tu_ngay": "2026-10-29", "den_ngay": "2026-10-29", "tuy_chon": {"thue_suat": "5", "ngay_hd": "2026-11-05"}}

# 1) xuất lần đầu: 3 đơn, Người mua = "Bán cho người tiêu dùng - Shopee - <mã bill>", có bộ lọc mọi cột
r = server.san_xuat_hd(1, B)
ws = openpyxl.load_workbook(r.path)["Hóa đơn GTGT (3)"]
assert ws.max_row == 5 and ws["F3"].value == "Bán cho người tiêu dùng - Shopee - BILL000001" and ws["F5"].value == "Bán cho người tiêu dùng - Shopee - BILL000003"
assert ws.auto_filter.ref == "A2:S5"
so = server._san_so_doc(1, "shopee")
assert sorted(so["don"]) == ["BILL000001", "BILL000002", "BILL000003"] and so["don"]["BILL000001"]["dong"][0]["thanh"] == round(268000 / 1.05)
print("PASS 1: xuất hoá đơn, Người mua có sàn + mã bill, bộ lọc mọi cột, ghi sổ.")

# 2) TUYỆT ĐỐI không xuất trùng
try:
    server.san_xuat_hd(1, B); raise SystemExit("phải chặn xuất trùng")
except server.HTTPException as e:
    assert "đã xuất hoá đơn" in e.detail
f1b = xlsx([H, dong("BILL000001", HT, "", "a", "Lens A", 134000, 2), dong("BILL000004", "Đã giao", "", "d", "Lens D", 50000, 1)])
r = server.san_xuat_hd(1, dict(B, b64=base64.b64encode(f1b).decode(), ten_file="Order.all.20261029_20261030.xlsx"))
ws = openpyxl.load_workbook(r.path)["Hóa đơn GTGT (3)"]
assert ws.max_row == 3 and ws["S3"].value == "BILL000004" and r.headers["X-Trung"] == "1"
print("PASS 2: không xuất trùng (đơn cũ bị bỏ, chỉ xuất đơn mới).")

# 3) Shopee cập nhật: BILL000002 bị huỷ, BILL000003 trả 1/3 -> phát hiện, thông báo cần điều chỉnh
f2 = xlsx([H, dong("BILL000001", HT, "", "a", "Lens A", 134000, 2), dong("BILL000002", "Đã hủy", "", "b", "Lens B", 129000, 1),
           dong("BILL000003", "Hoàn thành", "Đã Chấp Thuận Yêu Cầu", "c", "Lens C", 100000, 3, 1)])
d = server.san_doc(1, dict(B, b64=base64.b64encode(f2).decode(), ten_file="Order.all.20261029_20261105.xlsx"))
assert sorted(d["moi_phat_hien"]) == ["BILL000002", "BILL000003"], d["moi_phat_hien"]
dc = {x["ma_don"]: x for x in d["can_dieu_chinh"]}
assert dc["BILL000002"]["ly_do"].startswith("huỷ") and dc["BILL000003"]["dong"][0]["sl_tra"] == 1 and dc["BILL000003"]["ly_do"] == "trả hàng một phần"
assert d["tom_tat"]["can_dieu_chinh"] == 2 and d["trung"] == 2
print("PASS 3: phát hiện đơn đã xuất nay bị huỷ / trả một phần -> báo cần điều chỉnh.")

# 4) chưa có số hoá đơn gốc -> không lập điều chỉnh, báo thiếu
try:
    server.san_xuat_dc(1, {"san": "shopee"}); raise SystemExit("phải báo thiếu số HĐ gốc")
except server.HTTPException as e:
    assert "CHƯA có số hoá đơn gốc" in e.detail

# 5) cập nhật số hoá đơn từ file danh sách MISA (người mua chứa mã bill)
misa = xlsx([["Danh sách hóa đơn"], [], ["STT", "Ký hiệu hóa đơn", "Số hóa đơn", "Ngày hóa đơn", "Người mua hàng", "Tổng tiền", "Trạng thái hóa đơn"],
             [1, "C26TAA", 101, "2026-11-05", "Bán cho người tiêu dùng - Shopee - BILL000001", 268000, "Đã phát hành"],
             [2, "C26TAA", "00000102", "05/11/2026", "Bán cho người tiêu dùng - Shopee - BILL000002", 129000, "Đã phát hành"],
             [3, "C26TAA", "00000103", "05/11/2026", "Bán cho người tiêu dùng - Shopee - BILL000003", 300000, "Đã phát hành"],
             [4, "C26TAA", "00000104", "05/11/2026", "Bán cho người tiêu dùng - Shopee - BILL999999", 1, "Đã phát hành"],
             [5, "C26TAA", "00000105", "05/11/2026", "Công ty ABC", 1, "Đã phát hành"]])
r = server.san_cap_nhat_so_hd(1, {"san": "shopee", "ten_file": "ds_hd.xlsx", "b64": base64.b64encode(misa).decode()})
assert r["hoa_don_trong_file"] == 4 and r["cap_nhat"] == 3 and r["khong_khop"] == 1 and r["tom_tat"]["co_so_hd"] == 3
so = server._san_so_doc(1, "shopee")
assert so["don"]["BILL000001"]["so_hd"] == "00000101" and so["don"]["BILL000001"]["ky_hieu"] == "C26TAA" and so["don"]["BILL000001"]["ngay_so_hd"] == "05/11/2026"
print("PASS 4: cập nhật số hoá đơn từ danh sách MISA theo mã bill.")

# 6) hoá đơn điều chỉnh GIẢM: số lượng/thành tiền âm, trỏ về hoá đơn gốc, tiêu đề dòng 9, bộ lọc mọi cột; đánh dấu đã điều chỉnh
r = server.san_xuat_dc(1, {"san": "shopee", "tuy_chon": {"ngay_hd": "2026-11-06"}})
ws = openpyxl.load_workbook(r.path).active
tieu = [c.value for c in ws[9]]
assert tieu[:21] == m.HD_DC_BASE and "Thuế suất GTGT (%)" in tieu and ws.auto_filter.ref.startswith("A9:")
g = lambda row, k: ws.cell(row, tieu.index(k) + 1).value
assert ws.max_row == 11
r10, r11 = [g(10, "Số hóa đơn bị điều chỉnh (*)"), g(10, "Số lượng"), g(10, "Thành tiền")], [g(11, "Số hóa đơn bị điều chỉnh (*)"), g(11, "Số lượng"), g(11, "Thành tiền")]
assert r10 == ["00000102", -1, -round(129000 / 1.05)] and r11 == ["00000103", -1, -round(round(300000 / 1.05) / 3)], (r10, r11)
assert g(10, "Ký hiệu HĐ bị điều chỉnh (*)") == "C26TAA" and g(10, "Người mua hàng") == "Bán cho người tiêu dùng - Shopee - BILL000002" and g(10, "Ngày hóa đơn") == "06/11/2026"
assert g(10, "Tổng tiền hàng") == -round(129000 / 1.05) and g(10, "Tiền thuế GTGT") == -round(round(129000 / 1.05) * 0.05)
assert server._san_so_tom_tat(server._san_so_doc(1, "shopee"))["can_dieu_chinh"] == 0                # đã điều chỉnh -> hết thông báo
try:
    server.san_xuat_dc(1, {"san": "shopee"}); raise SystemExit("không được điều chỉnh trùng")
except server.HTTPException:
    pass
print("PASS 5: hoá đơn điều chỉnh giảm đúng mẫu MISA, không điều chỉnh trùng.")

# 7) trả thêm sau đó (trả 2/3) -> chỉ điều chỉnh phần phát sinh thêm
f3 = xlsx([H, dong("BILL000003", "Hoàn thành", "Đã Chấp Thuận Yêu Cầu", "c", "Lens C", 100000, 3, 2)])
d = server.san_doc(1, dict(B, b64=base64.b64encode(f3).decode(), ten_file="Order.all.20261029_20261106.xlsx"))
assert d["moi_phat_hien"] == ["BILL000003"] and d["can_dieu_chinh"][0]["dong"][0]["sl_tra"] == 1
print("PASS 6: trả thêm -> chỉ phần phát sinh thêm cần điều chỉnh.")

# 8) gỡ lô vừa xuất (import MISA lỗi) -> xuất lại được
n = server.san_go_lo(1, {"san": "shopee"})["da_go"]
assert n == 1 and "BILL000004" not in server._san_so_doc(1, "shopee")["don"]
print("PASS 7: gỡ lô xuất gần nhất.")

# 9) cửa sổ ngày: từ = max(ngày bắt đầu đã lưu, hôm nay - 30), đến = hôm nay
d0 = datetime.date(2026, 11, 5)
assert m.khoang_ngay("2026-10-29", d0) == (datetime.date(2026, 10, 29), d0)
assert m.khoang_ngay("2026-10-29", datetime.date(2026, 11, 28)) == (datetime.date(2026, 10, 29), datetime.date(2026, 11, 28))
assert m.khoang_ngay("2026-10-29", datetime.date(2026, 11, 29)) == (datetime.date(2026, 10, 30), datetime.date(2026, 11, 29))
kh = server.san_khoang_luu(1, {"san": "shopee", "tu": "2026-10-29"})
assert kh["tu_goc"] == "2026-10-29" and kh["den"] == datetime.date.today().isoformat()
print("PASS 8: cửa sổ ngày trượt 30 ngày, lưu ngày bắt đầu.")

# 10) danh sách MISA KHÔNG có cột Ký hiệu (như màn "HĐ khởi tạo từ máy tính tiền"): dùng ký hiệu mặc định đã lưu
misa2 = xlsx([["Ngày HĐ", "Số hóa đơn", "Khách hàng", "Thanh toán", "Tổng tiền", "Trạng thái HĐ"],
              ["04/11/2026", "00034709", "Bán cho người tiêu dùng - Shopee - BILL000004", "", 50000, "HĐ mới"],
              ["04/11/2026", "00034708", "Bán cho người tiêu dùng", "", 234000, "HĐ mới"]])
ds = m.doc_ds_hoa_don_misa(misa2, "ds.xlsx")
assert len(ds) == 1 and ds[0]["ma_don"] == "BILL000004" and ds[0]["so_hd"] == "00034709" and ds[0]["ky_hieu"] == "" and ds[0]["ngay_hd"] == "04/11/2026"
server._san_so_doc(1, "shopee")
server.san_xuat_hd(1, dict(B, b64=base64.b64encode(xlsx([H, dong("BILL000004", "Đã giao", "", "d", "Lens D", 50000, 1)])).decode(), ten_file="Order.all.x.xlsx"))
server.san_ky_hieu(1, {"san": "shopee", "ky_hieu": "C26MYY"})
r = server.san_cap_nhat_so_hd(1, {"san": "shopee", "ten_file": "ds2.xlsx", "b64": base64.b64encode(misa2).decode()})
d4 = server._san_so_doc(1, "shopee")["don"]["BILL000004"]
assert d4["so_hd"] == "00034709" and d4["ky_hieu"] == "C26MYY"
print("PASS 9: danh sách MISA không có cột ký hiệu -> dùng ký hiệu mặc định.")

# 11) quét Downloads: thử từng file Excel, báo cáo file nào nhận / không nhận
dl = os.path.join(tmp, "Downloads"); os.makedirs(dl)
server._san_thu_muc_downloads = lambda: dl
open(os.path.join(dl, "DS_HD_MISA.xlsx"), "wb").write(xlsx([["Ngày HĐ", "Số hóa đơn", "Khách hàng"], ["04/11/2026", "00034799", "Bán cho người tiêu dùng - Shopee - BILL000004"]]))
open(os.path.join(dl, "khac.xlsx"), "wb").write(xlsx([["a", "b"], [1, 2]]))
open(os.path.join(dl, "Order.all.1.xlsx"), "wb").write(f1)
q = server.san_quet_misa(1, {"san": "shopee"})
ten = {x["ten"]: x["kq"] for x in q["bao_cao"]}
assert "DS_HD_MISA.xlsx" in ten and "khac.xlsx" in ten and "Order.all.1.xlsx" not in ten and q["hoa_don"] == 1
assert server._san_so_doc(1, "shopee")["don"]["BILL000004"]["so_hd"] == "00034799"
print("PASS 11: quét file MISA trong Downloads, báo cáo từng file.")
