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

# 2) Không xuất trùng = bill MISA ĐÃ có hoá đơn (sổ có số hoá đơn). Bill chưa có số hoá đơn trong MISA thì được lập lại.
try:                                            # chưa đồng bộ hoá đơn đầu ra SAU lần xuất -> chưa biết MISA có chưa -> KHÔNG xuất lại
    server.san_xuat_hd(1, B); raise SystemExit("phải chặn xuất lại khi chưa đồng bộ")
except server.HTTPException as e:
    assert e.status_code == 409 and e.detail.startswith("XUAT_LAI|3|") and "Không có đơn MỚI" in e.detail, e.detail
import time as _tm
server._san_gdt_luc_luu(1, _tm.time() + 1)      # đồng bộ xong (sau lần xuất) mà trang Thuế vẫn không có hoá đơn
r = server.san_xuat_hd(1, B)                    # -> xuất lại 3 đơn, sổ không bị nhân đôi dòng
ws = openpyxl.load_workbook(r.path)["Hóa đơn GTGT (3)"]
assert ws.max_row == 5 and len(server._san_so_doc(1, "shopee")["don"]["BILL000001"]["dong"]) == 1
so_ = server._san_so_doc(1, "shopee")
for ma, sh in (("BILL000001", "00000001"), ("BILL000002", "00000002"), ("BILL000003", "00000003")):
    so_["don"][ma]["so_hd"] = sh
server._san_so_luu(1, "shopee", so_)
try:
    server.san_xuat_hd(1, B); raise SystemExit("phải chặn xuất trùng")
except server.HTTPException as e:
    assert "Không có đơn MỚI" in e.detail
f1b = xlsx([H, dong("BILL000001", HT, "", "a", "Lens A", 134000, 2), dong("BILL000004", "Đã giao", "", "d", "Lens D", 50000, 1)])
r = server.san_xuat_hd(1, dict(B, b64=base64.b64encode(f1b).decode(), ten_file="Order.all.20261029_20261030.xlsx"))
ws = openpyxl.load_workbook(r.path)["Hóa đơn GTGT (3)"]
assert ws.max_row == 3 and ws["S3"].value == "BILL000004" and r.headers["X-Trung"] == "1"
print("PASS 2: bill MISA đã có hoá đơn thì bỏ; bill chưa có thì lập lại để xuất.")

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

# 12) chỉ xuất đơn ĐÃ GIAO thành công; chờ giao / đang giao để lần cập nhật sau
fx = xlsx([H, dong("BILL000010", "Chờ giao hàng", "", "x", "Lens X", 10000, 1), dong("BILL000011", "Đang giao", "", "y", "Lens Y", 10000, 1),
           dong("BILL000012", "Chờ lấy hàng", "", "z", "Lens Z", 10000, 1), dong("BILL000013", "Hoàn thành", "", "w", "Lens W", 10000, 1), dong("BILL000014", HT, "", "v", "Lens V", 10000, 1)])
rows = m.loc_don(m.doc_file_don_hang(fx, "Order.all.20261029_20261029.xlsx", "shopee")[0], True, "2026-10-29", "2026-10-29")
assert sorted({x["ma_don"] for x in rows}) == ["BILL000013", "BILL000014"], sorted({x["ma_don"] for x in rows})
print("PASS 12: chỉ xuất đơn đã giao thành công, chờ giao/đang giao để sau.")

# 13) đối chiếu theo HOÁ ĐƠN ĐẦU RA đã tra cứu từ trang Thuế (bảng invoices): bill đã có hoá đơn thì không xuất lại
conn.execute("CREATE TABLE invoices (id INTEGER PRIMARY KEY, company_id INTEGER, loai TEXT, khhdon TEXT, shdon TEXT, tdlap TEXT, tthai TEXT, tgtcthue REAL, tgtthue REAL, raw TEXT, detail_json TEXT)")
conn.execute("INSERT INTO invoices (company_id,loai,khhdon,shdon,tdlap,tthai,raw,detail_json) VALUES (1,'sold','C26MYY','1234','2026-11-05T00:00:00','1','{\"nmtnmua\":\"Bán cho người tiêu dùng - Shopee - BILL000020\"}','')")
conn.execute("INSERT INTO invoices (company_id,loai,khhdon,shdon,tdlap,tthai,raw,detail_json) VALUES (1,'sold','C26MYY','1235','2026-11-05T00:00:00','6','{\"nmtnmua\":\"Bán cho người tiêu dùng - Shopee - BILL000021\"}','')")
conn.execute("INSERT INTO invoices (company_id,loai,khhdon,shdon,tdlap,tthai,raw,detail_json) VALUES (1,'sold','C26MYY','1236','2026-11-05T00:00:00','1','{}','{\"x\":\"Bán cho người tiêu dùng - Shopee - BILL000022\"}')")
g = server._san_bill_gdt(1, "shopee", m)
assert sorted(g) == ["BILL000020", "BILL000022"] and g["BILL000020"]["so_hd"] == "00001234", g
assert g["BILL000020"]["ngay_hd"] == "05/11/2026" and g["BILL000020"]["thong_tin"].endswith("BILL000020") and "chua_thue" in g["BILL000020"]   # hoá đơn huỷ (6) không tính
f13 = xlsx([H, dong("BILL000020", "Đã giao", "", "a", "A", 10000, 1), dong("BILL000021", "Đã giao", "", "b", "B", 10000, 1), dong("BILL000022", "Hoàn thành", "", "c", "C", 10000, 1)])
r = server.san_xuat_hd(1, dict(B, b64=base64.b64encode(f13).decode(), ten_file="Order.all.13.xlsx"))
ws = openpyxl.load_workbook(r.path)["Hóa đơn GTGT (3)"]
assert ws.max_row == 3 and ws["S3"].value == "BILL000021" and r.headers["X-Trung"] == "2"
print("PASS 13: bill đã có hoá đơn đầu ra (Tra cứu hoá đơn) bị loại; hoá đơn huỷ thì xuất lại.")

# 14) đồng bộ hoá đơn đầu ra: chưa đăng nhập -> tự đăng nhập bằng mật khẩu đã lưu rồi tra cứu bán ra (thường + MTT) theo ngày dd/mm/yyyy
import time as _t
conn.execute("ALTER TABLE companies ADD COLUMN password TEXT"); conn.execute("UPDATE companies SET password='x' WHERE id=1")
class _C: token = None
server.get_client = lambda cid: _C()
cal = {}
server._tu_dong_dang_nhap = lambda cid, so_lan=5, drv=None, progress=None: (cal.setdefault("dn", True) and (True, "ok", 1, []))
server._run_fetch_job = lambda cid, body: (cal.update(body=body), server.FETCH_JOBS[cid].update(running=False))
server._xoa_loi_tra_cuu = lambda cid: None
assert server.san_dong_bo_gdt(1, {"san": "shopee", "tu_ngay": "2026-10-29", "den_ngay": "2026-11-05"})["can_dang_nhap"]
server._mo_trinh_duyet_captcha = lambda: None
r = server.san_dong_bo_gdt(1, {"san": "shopee", "tu_ngay": "2026-10-29", "den_ngay": "2026-11-05", "dung_may_chu": True})
for _ in range(50):
    if "body" in cal: break
    _t.sleep(0.1)
assert r["started"] and cal["dn"] and cal["body"]["tu_ngay"] == "29/10/2026" and cal["body"]["den_ngay"] == "05/11/2026" and cal["body"]["chi_danh_sach"] is True and cal["body"]["loai_list"] == ["sold"] and cal["body"]["he_thong_list"] == ["query", "sco-query"], cal
print("PASS 14: đồng bộ hoá đơn đầu ra tự đăng nhập rồi tra cứu bán ra theo ngày đã chọn.")

# 15) hoá đơn điều chỉnh âm đã có trên trang Thuế -> bill không còn nằm trong danh sách cần điều chỉnh
so_ = server._san_so_doc(1, "shopee")
so_["don"]["BILL000020"] = {"lo": "x", "san": "shopee", "ngay_hd": "05/11/2026", "ngay_dat": "", "ts": 5.0, "kct": False, "dong": [{"ten": "A", "sku": "a", "sl": 1.0, "tien": 10000, "thanh": 9524, "thue": 476}],
                            "tra": [1.0], "da_dc": [0.0], "so_hd": "00001234", "ky_hieu": "C26MYY", "ngay_so_hd": "", "can_dc": {"ngay": "06/11/2026", "ly_do": "huỷ"}}
server._san_so_luu(1, "shopee", so_)
assert "BILL000020" in [x["ma_don"] for x in m.ds_can_dieu_chinh(server._san_so_doc(1, "shopee"))]
conn.execute("INSERT INTO invoices (company_id,loai,khhdon,shdon,tdlap,tthai,tgtcthue,tgtthue,raw,detail_json) VALUES (1,'sold','C26MYY','1300','2026-11-06T00:00:00','3',-9524,-476,'{\"nmtnmua\":\"Bán cho người tiêu dùng - Shopee - BILL000020\"}','')")
da = server._san_tu_quet_misa(1, "shopee")
assert "BILL000020" in da and "BILL000020" not in [x["ma_don"] for x in m.ds_can_dieu_chinh(server._san_so_doc(1, "shopee"))]     # hoá đơn điều chỉnh (tthai 3) không bị tính là hoá đơn gốc
print("PASS 15: bill đã có hoá đơn điều chỉnh âm trên trang Thuế thì không xuất điều chỉnh nữa.")

# 16) Người mua ghi đúng TÊN SÀN: "... - TikTok - <mã>", "... - Lazada - <mã>"; nhận lại được cả "TikTok- mã" / "TikTok Shop - mã"
rows = m.sang_hoa_don_gtgt([{"ma_don": "5771234567890123456", "ten_hang": "X", "so_luong": 1, "thanh_tien": 105000, "sku": "", "ngay": "05/11/2026"}], "tiktok", 5, "05/11/2026", "Cái")
assert rows[0][5] == "Bán cho người tiêu dùng - TikTok - 5771234567890123456", rows[0][5]
rows = m.sang_hoa_don_gtgt([{"ma_don": "9988776655", "ten_hang": "X", "so_luong": 1, "thanh_tien": 105000, "sku": "", "ngay": "05/11/2026"}], "lazada", 5, "05/11/2026", "Cái")
assert rows[0][5] == "Bán cho người tiêu dùng - Lazada - 9988776655"
for t in ("Bán cho người tiêu dùng - TikTok- 5771234567890123456", "Bán cho người tiêu dùng - TikTok Shop - 5771234567890123456", "bán cho người tiêu dùng - tiktok - 5771234567890123456"):
    assert m.bill_tu_hoa_don(t, "tiktok") == "5771234567890123456" and m.bill_tu_hoa_don(t, "shopee") == "", t
assert m.bill_tu_hoa_don("Bán cho người tiêu dùng - Lazada - 9988776655", "lazada") == "9988776655"
print("PASS 16: Người mua ghi đúng tên sàn (Shopee/TikTok/Lazada) và nhận lại đúng sàn khi đồng bộ.")

# 17) tài khoản sàn theo công ty: lưu (mã hoá), mở trang kèm mã dùng 1 lần, tiện ích đổi mã lấy tài khoản đúng 1 lần
server._san_chrome = lambda: (None, None)
import webbrowser as _wb; _wb.open = lambda *a, **k: True
r = server.san_tk_luu(1, {"san": "shopee", "user": "0900111222", "pass": "mk!@#", "ten_shop": "eyeiyagi"})
t = server.san_tk_xem(1, "shopee")
assert t["co"] and t["user"] == "0900111222" and "pass" not in t and "mk!@#" not in open(server._san_tk_duong_dan(1), encoding="utf-8").read()
r = server.san_mo_trinh_duyet(1, {"san": "shopee", "tu_ngay": "2026-11-04", "den_ngay": "2026-11-05"})
import re as _re
mk = _re.search(r"&kt=([\w-]+)&p=(\d+)$", r["url"]); assert mk and "#ketoan-xuat=2026-11-04_2026-11-05&kt=" in r["url"], r["url"]
v = server.san_tk_mot_lan(mk.group(1)); assert v["user"] == "0900111222" and v["pass"] == "mk!@#" and v["ten_shop"] == "eyeiyagi"
try:
    server.san_tk_mot_lan(mk.group(1)); raise SystemExit("mã phải chỉ dùng 1 lần")
except server.HTTPException:
    pass
server.san_tk_luu(1, {"san": "shopee", "user": "0900111222", "pass": "", "ten_shop": "eyeiyagi"})       # để trống mật khẩu = giữ mật khẩu cũ
assert server._san_mo_khoa(server._san_tk_doc(1)["shopee"]["pass"]) == "mk!@#"
r = server.san_mo_trinh_duyet(1, {"san": "tiktok", "tu_ngay": "2026-11-04", "den_ngay": "2026-11-05"}); assert "&kt=" not in r["url"]     # sàn chưa lưu tài khoản: không kèm mã
server.san_tk_xoa(1, "shopee"); assert not server.san_tk_xem(1, "shopee")["co"]
print("PASS 17: tài khoản sàn theo công ty: lưu mã hoá, mã dùng 1 lần cho tiện ích tự đăng nhập.")

# 18) file TikTok thật: dòng mô tả cột ngay dưới tiêu đề, Order Substatus quyết định đã giao; "Đang trung chuyển" chưa xuất; "Đã hoàn tất" xuất
HT_ = ["Order ID", "Order Status", "Order Substatus", "Cancelation/Return Type", "Seller SKU", "Product Name", "Variation", "Quantity", "Sku Quantity of return",
       "SKU Unit Original Price", "SKU Subtotal Before Discount", "SKU Seller Discount", "SKU Subtotal After Discount", "Created Time", "Delivered Time"]
MT_ = ["Platform unique order ID.", "Current order status.", None, "The filed to explain the order is in cancellation or in return/refund.", None, None, None, None, None, None, None, None, None, "Order created time.", None]
def tk_(ma, st, sub, huy=None):
    return [ma, st, sub, huy, "jeju", "Lens Jeju", "2.25", "1", "0", "160000", "160000", "63684", "91540", "30/10/2026 10:00:00", "01/11/2026 10:00:00"]
ft = xlsx([HT_, MT_, tk_("587000000000000001", "Đã vận chuyển", "Đã giao"), tk_("587000000000000002", "Đã vận chuyển", "Đang trung chuyển"),
           tk_("587000000000000003", "Đã hủy", "Đã hủy", "Cancel"), tk_("587000000000000004", "Đã vận chuyển", "Đã hoàn tất"), tk_("587000000000000005", "Cần vận chuyển", "Đang chờ vận chuyển")])
d_, _ = m.doc_file_don_hang(ft, "Tất cả đơn hàng-2026-11-06-00_21.xlsx", "tiktok")
assert len(d_) == 5 and d_[0]["trang_thai"] == "Đã giao" and d_[0]["thanh_tien"] == 91540      # = SKU Subtotal After Discount (khách thanh toán)
l_ = m.loc_don(d_, True, "2026-10-29", "2026-11-06")
assert sorted(x["ma_don"] for x in l_) == ["587000000000000001", "587000000000000004"], [x["ma_don"] for x in l_]
assert m.la_hop_le({"trang_thai": "Đang trung chuyển"})[0] and not m.la_hop_le({"trang_thai": "Đã hủy"})[0]      # "chuyển" không bị hiểu là "huỷ"
import re as _re2
assert _re2.search(server._SAN_TEN_FILE["tiktok"], "Tất cả đơn hàng-2026-11-06-00_21.xlsx", _re2.I) and not _re2.search(server._SAN_TEN_FILE["tiktok"], "Order.all.20261029_20261105.xlsx", _re2.I)
print("PASS 18: file TikTok (Order Substatus, dòng mô tả) chỉ xuất đơn đã giao/đã hoàn tất; nhận đúng tên file TikTok.")

# 19) XUẤT GỘP nhiều sàn vào 1 file: số thứ tự hoá đơn nối tiếp, mỗi sàn ghi sổ riêng; sàn chưa có file thì bỏ qua
server._san_gdt_luc_luu(1, 0)
fs = xlsx([H, dong("BILL000090", "Đã giao", "", "a", "Lens A", 105000, 1), dong("BILL000091", "Hoàn thành", "", "b", "Lens B", 210000, 1)])
d_sp = server._san_thu_muc(1, "shopee"); open(os.path.join(d_sp, "Order.all.gop.xlsx"), "wb").write(fs)
d_tt = server._san_thu_muc(1, "tiktok"); open(os.path.join(d_tt, "Tất cả đơn hàng-gop.xlsx"), "wb").write(ft)
r = server.san_xuat_hd_gop(1, {"ds": [{"san": "shopee", "ten_file": "Order.all.gop.xlsx", "nguon": "pm"}, {"san": "tiktok", "ten_file": "Tất cả đơn hàng-gop.xlsx", "nguon": "pm"}, {"san": "lazada"}],
                               "tu_ngay": "2026-10-29", "den_ngay": "2026-11-06", "chi_hoan_thanh": True, "tuy_chon": {"thue_suat": "5"}})
ws = openpyxl.load_workbook(r.path)["Hóa đơn GTGT (3)"]
hang = [[c.value for c in row] for row in ws.iter_rows(min_row=3)]
assert [h_[0] for h_ in hang] == list(range(1, len(hang) + 1)) and len(hang) >= 4, [(h_[0], h_[5]) for h_ in hang]      # lazada: lấy file mới nhất có sẵn của sàn
assert hang[0][5].endswith("Shopee - BILL000090") and hang[2][5].startswith("Bán cho người tiêu dùng - TikTok - 5870000000000000")
assert "GOP_Shopee_TikTok" in r.path and "TikTok: 2 đơn mới" in __import__("urllib.parse").parse.unquote(r.headers["X-Gop"])
assert "BILL000090" in server._san_so_doc(1, "shopee")["don"] and "587000000000000001" in server._san_so_doc(1, "tiktok")["don"]
try:                                                # vừa xuất, chưa đồng bộ lại -> không xuất trùng
    server.san_xuat_hd_gop(1, {"ds": [{"san": "shopee", "ten_file": "Order.all.gop.xlsx", "nguon": "pm"}, {"san": "tiktok", "ten_file": "Tất cả đơn hàng-gop.xlsx", "nguon": "pm"}, {"san": "lazada"}],
                               "tu_ngay": "2026-10-29", "den_ngay": "2026-11-06", "tuy_chon": {}}); raise SystemExit("phải chặn trùng")
except server.HTTPException as e:
    assert "Không có đơn MỚI" in e.detail
print("PASS 19: xuất GỘP Shopee + TikTok vào 1 file, số thứ tự nối tiếp, không xuất trùng.")

# 20) TikTok: thành tiền = số khách thanh toán ("Tổng cộng" trên trang đơn) = sau giảm giá người bán + TikTok, trừ giảm giá nền tảng thanh toán (cả đơn, phân bổ theo dòng)
HP_ = HT_ + ["Payment platform discount"]
def tp_(ma, sau, gtt):
    r = tk_(ma, "Đã vận chuyển", "Đã giao"); r[12] = str(sau); return r + [str(gtt)]
fp = xlsx([HP_, MT_ + [None], tp_("586987497419539500", 113525, 2270), tp_("586980188891284969", 88000, 5280), tp_("586980188891284969", 88000, 5280), tp_("586980188891284969", 88000, 5280)])
d_, _ = m.doc_file_don_hang(fp, "Tất cả đơn hàng-x.xlsx", "tiktok")
t_ = {}
for x in d_:
    t_[x["ma_don"]] = t_.get(x["ma_don"], 0) + x["thanh_tien"]
assert t_ == {"586987497419539500": 111255, "586980188891284969": 258720}, t_
print("PASS 20: TikTok lấy đúng số khách thanh toán (trừ cả giảm giá TikTok và nền tảng thanh toán).")

# 21) chỉ 1 sàn có đơn mới vẫn xuất; tất cả đã xuất file mà chưa có hoá đơn đầu ra -> báo XUAT_LAI để hỏi người dùng, xác nhận thì xuất lại
G = {"ds": [{"san": "shopee", "ten_file": "Order.all.gop.xlsx", "nguon": "pm"}, {"san": "tiktok", "ten_file": "Tất cả đơn hàng-gop.xlsx", "nguon": "pm"}],
     "tu_ngay": "2026-10-29", "den_ngay": "2026-11-06", "tuy_chon": {}}
try:
    server.san_xuat_hd_gop(1, G); raise SystemExit("phải hỏi xuất lại")
except server.HTTPException as e:
    assert e.status_code == 409 and e.detail.startswith("XUAT_LAI|4|"), e.detail
r = server.san_xuat_hd_gop(1, dict(G, xuat_lai=True))
ws = openpyxl.load_workbook(r.path)["Hóa đơn GTGT (3)"]
assert ws.max_row - 2 >= 4 and "GOP_Shopee_TikTok" in r.path
fs2 = xlsx([H, dong("BILL000095", "Đã giao", "", "a", "Lens A", 105000, 1)]); open(os.path.join(d_sp, "Order.all.gop2.xlsx"), "wb").write(fs2)
r = server.san_xuat_hd_gop(1, dict(G, ds=[{"san": "shopee", "ten_file": "Order.all.gop2.xlsx", "nguon": "pm"}, G["ds"][1]]))      # TikTok không có đơn mới: vẫn xuất phần Shopee
ws = openpyxl.load_workbook(r.path)["Hóa đơn GTGT (3)"]
assert ws.max_row == 3 and ws["S3"].value == "BILL000095" and "XUAT_HOA_DON_Shopee_" in r.path
print("PASS 21: chỉ 1 sàn có đơn mới vẫn xuất; đơn đã xuất chưa có hoá đơn đầu ra thì hỏi để xuất lại.")

# 22) TikTok: phí vận chuyển khách trả (sau giảm) thêm thành dòng "Phí vận chuyển" -> tổng hoá đơn = "Tổng cộng" khách thanh toán
HV_ = HT_ + ["Shipping Fee After Discount"]
def tv_(ma, sau, phi):
    r = tk_(ma, "Đã vận chuyển", "Đã giao"); r[12] = str(sau); return r + [str(phi)]
fv = xlsx([HV_, MT_ + [None], tv_("586962972193097090", 59999, 15100), tv_("586962972193097090", 59999, 15100), tv_("586984612138484754", 283738, 600), tv_("586000000000000009", 100000, 0)])
d_, _ = m.doc_file_don_hang(fv, "Tất cả đơn hàng-y.xlsx", "tiktok")
t_ = {}
for x in d_:
    t_[x["ma_don"]] = t_.get(x["ma_don"], 0) + x["thanh_tien"]
assert t_ == {"586962972193097090": 135098, "586984612138484754": 284338, "586000000000000009": 100000}, t_
assert [x["ten_hang"] for x in d_].count("Phí vận chuyển") == 2 and d_[2]["ten_hang"] == "Phí vận chuyển"
print("PASS 22: TikTok thêm dòng Phí vận chuyển khách trả, tổng = Tổng cộng trên trang đơn.")

# 23) dòng Phí vận chuyển thuế suất 8% (hàng hoá theo thuế suất chọn, vd 5%); tổng vẫn = số khách trả
r_ = m.sang_hoa_don_gtgt([x for x in d_ if x["ma_don"] == "586962972193097090"], "tiktok", 5, "06/11/2026", "Cái")
assert [h_[15] for h_ in r_] == [5, 5, 8] and r_[2][14] == round(15100 / 1.08) and r_[2][16] == 15100 - round(15100 / 1.08) and r_[2][17] == 15100, r_[2]
so_t = m.so_moi(); m.ghi_so_xuat(so_t, [x for x in d_ if x["ma_don"] == "586962972193097090"], "tiktok", 5, "06/11/2026", "hd20261106000000000001")
assert so_t["don"]["586962972193097090"]["dong"][2]["ts"] == 8.0
print("PASS 23: Phí vận chuyển xuất thuế suất 8%.")

# 24) dòng / đơn 0đ (quà tặng) không đưa vào hoá đơn
f0 = xlsx([HT_, MT_, tk_("586000000000000020", "Đã vận chuyển", "Đã giao"), tk_("586000000000000021", "Đã vận chuyển", "Đã giao")])
d0, _ = m.doc_file_don_hang(f0, "Tất cả đơn hàng-0.xlsx", "tiktok")
d0[1]["thanh_tien"] = 0; d0.append(dict(d0[0], ten_hang="Quà tặng", thanh_tien=0))
l0 = m.loc_don(d0, True, "2026-10-29", "2026-11-06")
assert [(x["ma_don"], x["ten_hang"]) for x in l0] == [("586000000000000020", "Lens Jeju")], l0
print("PASS 24: bỏ dòng/đơn 0đ.")

# 25) Lazada (file thật dạng orderItemId/orderNumber/paidPrice/status): chỉ 'delivered' được xuất, 'confirmed' chờ, 'canceled' bỏ; file tên mã hash được nhận
HL_ = ["orderItemId", "orderNumber", "createTime", "sellerSku", "paidPrice", "unitPrice", "shippingFee", "itemName", "variation", "status"]
fl = xlsx([HL_, ["1", "530133200564216", "26 Oct 2026 10:00", "s1", "176500.00", "200000.00", "0.00", "Lens A", "", "delivered"],
           ["2", "530133200564216", "26 Oct 2026 10:00", "s2", "100000.00", "120000.00", "10000.00", "Lens B", "", "delivered"],
           ["3", "533639145244145", "28 Oct 2026 11:57", "s1", "65600.00", "80000.00", "0.00", "Lens A", "", "confirmed"],
           ["4", "533672744444145", "28 Oct 2026 11:57", "s1", "80000.00", "80000.00", "0.00", "Lens A", "", "canceled"]])
dl_, _ = m.doc_file_don_hang(fl, "48144ed3b959cad9a82d48f877626e9c.xlsx", "lazada")
assert not m.la_hop_le([x for x in dl_ if x["ma_don"] == "533672744444145"][0])[0] and [x["ten_hang"] for x in dl_].count("Phí vận chuyển") == 1
ll_ = m.loc_don(dl_, True, "2026-10-01", "2026-11-06")
assert sorted({x["ma_don"] for x in ll_}) == ["530133200564216"] and m.tong_hop(ll_)["tong_tien"] == 286500, m.tong_hop(ll_)      # 176.500 + 100.000 + phí ship 10.000
assert _re2.search(server._SAN_TEN_FILE["lazada"], "48144ed3b959cad9a82d48f877626e9c.xlsx") and not _re2.search(server._SAN_TEN_FILE["lazada"], "Order.all.1.xlsx", _re2.I) \
    and not _re2.search(server._SAN_TEN_FILE["lazada"], "Tất cả đơn hàng-2026.xlsx", _re2.I)
print("PASS 25: Lazada — đọc file thật, chỉ xuất đơn delivered, cộng phí ship, nhận file tên mã hash.")
