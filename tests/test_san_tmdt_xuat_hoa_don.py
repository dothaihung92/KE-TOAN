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
assert len(dong) == 3 and dong[0]["ma_don"] == "2411050ABC" and dong[0]["ten_hang"] == "Áo thun (Đỏ, L)" and dong[0]["ngay"] == "03/11/2026" and dong[0]["thanh_tien"] == 216000
loc = m.loc_don(dong)
assert [x["ma_don"] for x in loc] == ["2411050ABC", "2411050ABC"] and m.tong_hop(loc) == {"so_don": 1, "so_dong": 2, "tong_tien": 270000}
print("PASS 1: Shopee — dò cột tiếng Việt, ghép phân loại, bỏ đơn huỷ.")

tiktok = "Order ID,Order Status,Product Name,Seller SKU,Quantity,SKU Unit Original Price,SKU Subtotal After Discount,Created Time,Recipient\n" \
         "577000000000000001,Completed,Kem dưỡng,KD-50,1,\"200,000\",\"180,000\",05/11/2026 08:00:00 AM,Người Nhận\n" \
         "577000000000000002,Cancelled,Kem dưỡng,KD-50,1,\"200,000\",\"180,000\",05/11/2026 08:00:00 AM,Người Nhận\n"
dong, _g = m.doc_file_don_hang(tiktok.encode("utf-8-sig"), "tiktok.csv", "tiktok")
loc = m.loc_don(dong)
assert len(loc) == 1 and loc[0]["thanh_tien"] == 180000 and loc[0]["sku"] == "KD-50" and loc[0]["ngay"] == "05/11/2026"
print("PASS 2: TikTok — CSV tiếng Anh, số có dấu phẩy ngăn nghìn.")

lazada = xlsx([["Order Item Id", "Order Number", "Created at", "Seller SKU", "Item Name", "Unit Price", "Paid Price", "Status", "Customer Name"],
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
