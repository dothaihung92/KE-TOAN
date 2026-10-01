import os, sys, json, sqlite3, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# HĐ chiết khấu NCC (Satori 5451, 6036...) hạch toán Nợ 331 / Có 6427 SỐ DƯƠNG: KHÔNG còn đi vào chứng từ mua dịch vụ ghi âm mà ghi thành
# Chứng từ nghiệp vụ khác (xem tests/test_chiet_khau_ncc_nghiep_vu_khac.py). Dòng Nợ 6xx / Có 331 (kể cả ghi âm cũ) vẫn vào mua dịch vụ như trước.
hd = ["Ký hiệu", "Số HĐ", "Ngày", "Người bán", "MST bán", "STT", "Mã vt", "Tên hàng hóa/dịch vụ", "ĐVT", "Số lượng", "Đơn giá",
      "Thành tiền", "Thuế suất", "Tiền thuế GTGT", "Trị giá tính thuế NK", "Thuế suất NK", "Tiền thuế NK", "Nợ", "Có"]
rows = [
    ["C26TSA", "5451", "17/09/2026", "SATORI", "0319340593", "1", "MHDV", "Hỗ trợ thị trường", "", "", "", 10980720, "8%", 878458, None, None, None, 331, 6427],
    ["C26TSA", "6206", "24/09/2026", "SATORI", "0319340593", "1", "MHDV", "Hỗ trợ khác", "", "", "", -16947150, "8%", -1355772, None, None, None, "6427", "331"],
    ["C26TVS", "7810", "03/09/2026", "VISNAM", "0401486901", "1", "MHDV", "Phần mềm", "", "", "", 6900000, "KCT", 0, None, None, None, "6428", "331"],
    ["C26TNT", "3513", "03/09/2026", "NAM TIẾN", "0317743519", "1", "TP1", "Nước tương", "Chai", 1, 100, 100, "8%", 8, None, None, None, "331", "1561"],
]
dv = server._gen_mua_hang_dv(1, hd, rows)
by = {r[33]: r for r in dv}
assert set(by) == {"6206", "7810"}, set(by)                 # Nợ 331 (dù Có 6427 hay 1561) không vào mua dịch vụ
assert by["6206"][16] == "6427" and by["6206"][17] == "331" and by["6206"][21] == -16947150
assert by["7810"][16] == "6428" and by["7810"][21] == 6900000
print("PASS 1: Nợ 331 không vào mua dịch vụ ghi âm; Nợ 6xx/Có 331 (kể cả âm) và dịch vụ thường giữ nguyên.")

# Nhóm chiết khấu NCC: Có 6xx / Có trống / Có 331; Nợ 331/Có 15x, Có 112 (thanh toán) KHÔNG phải chiết khấu
rows_ck = rows[:1] + [
    ["C26TSA", "6036", "23/09/2026", "SATORI", "0319340593", "1", "MHDV", "HT", None, 0, 0, -13340460, "8%", -1067237, None, None, None, "331", ""],
    ["C26TSA", "6212", "24/09/2026", "SATORI", "0319340593", "1", "MHDV", "HT", None, 0, 0, 19585710, "8%", 1566857, None, None, None, 331, 331],
    ["C26TXX", "1000", "01/09/2026", "NCC X", "0301234567", "1", "X", "Thanh toán", "", 1, 100, 100, "8%", 8, None, None, None, "331", "112"],
    ["C26TNT", "3513", "03/09/2026", "NAM TIẾN", "0317743519", "1", "TP1", "Nước tương", "Chai", 1, 100, 100, "8%", 8, None, None, None, "331", "1561"]]
dd = server._dong_chiet_khau_ncc(hd, rows_ck)
assert [x["so_hd"] for x in dd] == ["5451", "6036", "6212"] and all(x["tk_cp"] == "6427" for x in dd), dd
assert dd[1]["net"] == 13340460 and dd[1]["vat"] == 1067237
print("PASS 2: nhận diện hóa đơn chiết khấu NCC (Có 6xx/trống/331), trị tuyệt đối; bỏ Nợ 331/Có 112, Có 15x.")

# Bước 4e: dòng Bảng kê không nhóm nào nhận (Nợ lạ) được liệt kê, Nợ 331 chiết khấu thì KHÔNG bị coi là lạ
rows_la = rows + [["C26TXX", "999", "01/09/2026", "NCC X", "0301234567", "1", "X", "Hàng lạ", "Cái", 1, 100, 100, "8%", 8, None, None, None, "9999", "331"],
                  ["C26TXX", "1000", "01/09/2026", "NCC X", "0301234567", "1", "X", "Phí NH", "", 1, 100, 100, "8%", 8, None, None, None, "331", "112"]]
_f = tempfile.mktemp(suffix=".db")
def _db():
    c = sqlite3.connect(_f); c.row_factory = sqlite3.Row; return c
server.db = _db
c0 = _db()
c0.execute("CREATE TABLE nhap_lieu (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, loai TEXT, header_json TEXT, rows_json TEXT, updated_at TEXT, UNIQUE(company_id, loai))")
c0.execute("INSERT INTO nhap_lieu (company_id, loai, header_json, rows_json) VALUES (1,'in',?,?)", (json.dumps(hd), json.dumps(rows_la)))
c0.commit(); c0.close()
kq = server._dong_bang_ke_dau_vao_khong_nhan_dang(1)
assert kq["so_dong_khong_nhan_dang"] == 3 and {d["so_hd"] for d in kq["danh_sach"]} == {"999", "1000", "3513"}, kq
print("PASS 3: 4e liệt kê đúng 3 dòng Nợ/Có lạ (Nợ 9999; Nợ 331 với Có 112 hoặc 1561); Nợ 331/Có 6427 không bị coi là lạ.")
print("\nALL DONE")
