import os, sys, json, sqlite3, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Người dùng: "mua vào thì phần mềm không xử lý các hóa đơn thiếu". Nguyên nhân thật (file BangKe_HoaDon T09/2026): HĐ 1706/1759/185/1264
# của NCC mới có cột TK Nợ TRỐNG -> Import MISA (nhập kho/dịch vụ/Danh mục hàng hóa) lọc theo đầu TK Nợ nên bỏ qua im lặng.
# Nay tự điền TK Nợ dự đoán (cùng NCC > TK hay dùng của công ty > 1561 hàng / 6427 dịch vụ), có Có=331, và báo lại để kiểm tra.
hd = ["Ký hiệu", "Số HĐ", "Ngày", "Người bán", "MST bán", "STT", "Mã vt", "Tên hàng hóa/dịch vụ", "ĐVT", "Số lượng", "Đơn giá",
      "Thành tiền", "Thuế suất", "Tiền thuế GTGT", "Nợ", "Có"]
rows = [
    ["C26TYY", "1706", "09/09/2026", "HOA HỒNG PHÁT", "0318961005", "1", "HH00114", "Bột ngọt 1kg", "Thùng", 208, 877403, 182500000, "8%", 14600000, "", ""],
    ["C26TYY", "1759", "15/09/2026", "HOA HỒNG PHÁT", "0318961005", "1", "HH00113", "Bột ngọt 5kg", "Thùng", 100, 956481, 95648148, "8%", 7651852, "", ""],
    ["C26TKN", "1264", "22/09/2026", "KHÁNH NGỌC", "0313517406", "1", "GI034", "Giấy A4", "Ream", 5, 55000, 275000, "8%", 22000, "", "331"],
    ["C26TVS", "7810", "03/09/2026", "VISNAM", "0401486901", "1", "", "Phần mềm hóa đơn", "", "", "", 6900000, "KCT", 0, "", ""],
    ["C26TNT", "3513", "03/09/2026", "NAM TIẾN HUY", "0317743519", "1", "TP1", "Nước tương", "Chai", 1200, 5333, 6399600, "8%", 511968, "1561", "331"],
    ["C26TSA", "4243", "03/09/2026", "SATORI", "0319340593", "1", "TP2", "Nước 1.5l", "Thùng", 200, 0, 0, "8%", 0, "", ""],   # 0đ: bỏ qua
    ["C26TSA", "5451", "17/09/2026", "SATORI", "0319340593", "1", "MHDV", "Hỗ trợ thị trường (CK)", "", 0, 0, -10980720, "8%", -878458, "6427", "331"],
]
# công ty đã học: hàng hay dùng 156, dịch vụ 642
server._get_map_no = lambda cid: {"a": "1561", "b": "1561", "c": "152"}
server._get_map_no_item = lambda cid: {("m", "x"): "6428", ("m", "y"): "6428", ("m", "z"): "6427"}
moi, ds = server._dien_tk_no_bang_ke_dau_vao(1, hd, rows)
no = {r[1]: r[14] for r in moi}
co = {r[1]: r[15] for r in moi}
assert no["1706"] == "1561" and no["1759"] == "1561" and co["1706"] == "331", (no, co)   # NCC mới -> TK hàng hay dùng nhất
assert no["1264"] == "1561" and co["1264"] == "331"
assert no["7810"] == "6428", no                                                           # dịch vụ -> TK 6xx hay dùng nhất đã học
assert no["3513"] == "1561" and no["5451"] == "6427"                                      # có sẵn thì giữ nguyên
assert no["4243"] == "", "dòng 0đ không điền"
assert [x[0] for x in ds] == ["1706", "1759", "1264", "7810"], ds
assert rows[0][14] == "", "không sửa dữ liệu gốc"
print("PASS 1: tự điền TK Nợ/Có cho dòng trống (hàng 1561, dịch vụ 6428 theo TK đã học), giữ nguyên dòng có sẵn, bỏ qua dòng 0đ.")

# ưu tiên TK Nợ của CHÍNH NCC đó đã có trong Bảng kê
rows2 = rows + [["C26TYY", "1800", "20/09/2026", "HOA HỒNG PHÁT", "0318961005", "1", "HH9", "Bột ngọt 2kg", "Thùng", 1, 100, 100000, "8%", 8000, "1521", "331"]]
moi2, ds2 = server._dien_tk_no_bang_ke_dau_vao(1, hd, rows2)
assert {r[1]: r[14] for r in moi2}["1706"] == "1521"
print("PASS 2: ưu tiên TK Nợ cùng NCC đã có trong Bảng kê.")

# chưa học gì -> 1561 / 6427
server._get_map_no = lambda cid: {}
server._get_map_no_item = lambda cid: {}
assert server._tk_no_mac_dinh_hoc(1) == ("1561", "6427")
print("PASS 3: chưa học gì -> mặc định 1561 / 6427.")

# bước 0 của Import tự động: lưu lại vào Bảng kê đã lưu
_duong = tempfile.mktemp(suffix=".db")
def _db():
    c = sqlite3.connect(_duong); c.row_factory = sqlite3.Row; return c
server.db = _db
c0 = _db()
c0.execute("CREATE TABLE nhap_lieu (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, loai TEXT, header_json TEXT, rows_json TEXT, updated_at TEXT, UNIQUE(company_id, loai))")
c0.execute("INSERT INTO nhap_lieu (company_id, loai, header_json, rows_json) VALUES (1,'in',?,?)", (json.dumps(hd), json.dumps(rows)))
c0.commit(); c0.close()
server._doc_du_lieu_cty = lambda cid: {}
server._ghi_du_lieu_cty = lambda cid, d: None
r = server._misa_chuan_bi_bang_ke_dau_vao(1, preview=True)
assert r["so_tk_no_du_doan"] == 4 and "kiểm tra lại" in r["ghi_chu"], r
saved = json.loads(_db().execute("SELECT rows_json FROM nhap_lieu WHERE loai='in'").fetchone()[0])
assert saved[0][14] == "1561" and saved[3][14] == "6427"
r2 = server._misa_chuan_bi_bang_ke_dau_vao(1, preview=True)
assert r2["so_tk_no_du_doan"] == 0
assert "tự điền TK Nợ dự đoán 4 dòng" in server._misa_tom_tat_buoc(r)
print("PASS 4: bước 0 lưu lại Bảng kê, chạy lại thì không còn dòng trống; tóm tắt hiện rõ.")
print("\nALL DONE")
