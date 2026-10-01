import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# NCC xuất hóa đơn chiết khấu (HĐ âm của Satori: 5451, 6036...). Người dùng hạch toán Nợ 331 / Có 6427 trong bảng chi tiết;
# trước đây _gen_mua_hang_dv chỉ nhận Nợ 6xx nên dòng này bị bỏ qua im lặng -> "THIẾU trong MISA". Nay nhận Nợ 331/Có 6xx
# (số dương hay âm đều được) và ghi chứng từ mua dịch vụ GHI ÂM (Nợ 6427 âm / Có 331 âm), cùng bút toán với Nợ 331/Có 6427.
hd = ["Ký hiệu", "Số HĐ", "Ngày", "Người bán", "MST bán", "STT", "Mã vt", "Tên hàng hóa/dịch vụ", "ĐVT", "Số lượng", "Đơn giá",
      "Thành tiền", "Thuế suất", "Tiền thuế GTGT", "Nợ", "Có"]
rows = [
    ["C26TSA", "5451", "17/09/2026", "SATORI", "0319340593", "1", "MHDV", "Hỗ trợ thị trường", "", "", "", 10980720, "8%", 878458, "331", "6427"],      # N331/C6427 dương
    ["C26TSA", "6036", "23/09/2026", "SATORI", "0319340593", "1", "MHDV", "Hỗ trợ phát triển", "", "", "", -13340460, "8%", -1067237, "331", "6427"],  # N331/C6427 âm
    ["C26TSA", "6206", "24/09/2026", "SATORI", "0319340593", "1", "MHDV", "Hỗ trợ khác", "", "", "", -16947150, "8%", -1355772, "6427", "331"],        # Nợ 6427/Có 331 âm (như cũ)
    ["C26TVS", "7810", "03/09/2026", "VISNAM", "0401486901", "1", "MHDV", "Phần mềm", "", "", "", 6900000, "KCT", 0, "6428", "331"],                     # dịch vụ thường
    ["C26TNT", "3513", "03/09/2026", "NAM TIẾN", "0317743519", "1", "TP1", "Nước tương", "Chai", 1, 100, 100, "8%", 8, "331", "1561"],                  # Nợ 331/Có 1561: KHÔNG phải chi phí -> không lấy
]
out = server._gen_mua_hang_dv(1, hd, rows)
assert len(out) == 4, [r[33] for r in out]
by = {r[33]: r for r in out}                   # cột 34 = số HĐ
for so in ("5451", "6036", "6206"):
    r = by[so]
    assert r[16] == "6427" and r[17] == "331", (so, r[16], r[17])
    assert r[21] < 0 and r[22] < 0 and r[28] < 0, (so, r[21], r[22], r[28])
assert by["5451"][21] == -10980720 and by["5451"][28] == -878458
assert by["6036"][21] == -13340460 and by["6036"][28] == -1067237
assert by["7810"][16] == "6428" and by["7810"][21] == 6900000
print("PASS: HĐ chiết khấu NCC hạch toán Nợ 331/Có 6427 (dương hay âm) và Nợ 6427/Có 331 âm đều vào mua dịch vụ ghi ÂM; HĐ thường giữ nguyên.")
print("\nALL DONE")

# Ca thật: file NhapLieu_DauVao.xlsx người dùng gửi — Nợ/Có nhập dạng SỐ (331, 6427) chứ không phải chuỗi, và 4 HĐ (1706, 1759, 185, 1264)
# còn trống Nợ -> Import nhập kho bỏ qua. Sau khi điền TK Nợ trống, nhập kho phải nhận thêm đúng 5 dòng, DV vẫn nhận 7 HĐ chiết khấu (ghi âm).
server._get_map_no = lambda cid: {}
server._get_map_no_item = lambda cid: {}
rows_so = [
    ["C26TYY", "1706", "09/09/2026", "HOA HỒNG PHÁT", "0318961005", "1", "HH00114", "Bột ngọt 1kg", "Thùng", 208, 877403.85, 182500000, "8%", 14600000, None, None, None, None, "331"],
    ["C26TKN", "1264", "22/09/2026", "KHÁNH NGỌC", "0313517406", "1", "GI034", "Giấy A4", "Ream", 5, 55000, 275000, "8%", 22000, None, None, None, None, "331"],
    ["C26TSA", "5451", "17/09/2026", "SATORI", "0319340593", "1", "MHDV", "Hỗ trợ (CK)", None, 0, 0, 10980720, "8%", 878458, None, None, None, 331, 6427],
    ["C26TNT", "3513", "03/09/2026", "NAM TIẾN", "0317743519", "1", "TP1", "Nước tương", "Chai", 1200, 5333, 6399600, "8%", 511968, None, None, None, "1561", "331"],
]
hd_so = hd + ["Trị giá tính thuế NK", "Thuế suất NK", "Tiền thuế NK"]
hd_so = ["Ký hiệu", "Số HĐ", "Ngày", "Người bán", "MST bán", "STT", "Mã vt", "Tên hàng hóa/dịch vụ", "ĐVT", "Số lượng", "Đơn giá", "Thành tiền",
         "Thuế suất", "Tiền thuế GTGT", "Trị giá tính thuế NK", "Thuế suất NK", "Tiền thuế NK", "Nợ", "Có"]
assert len(server._gen_mua_hang_nk(1, hd_so, rows_so)) == 1            # chỉ HĐ 3513 có Nợ
moi_so, ds_so = server._dien_tk_no_bang_ke_dau_vao(1, hd_so, rows_so)
assert len(server._gen_mua_hang_nk(1, hd_so, moi_so)) == 3             # + 1706, 1264
dv_so = server._gen_mua_hang_dv(1, hd_so, moi_so)
assert len(dv_so) == 1 and dv_so[0][16] == "6427" and dv_so[0][17] == "331" and dv_so[0][21] == -10980720
print("PASS 2: file thật (Nợ/Có dạng số 331/6427 + 4 HĐ trống Nợ): nhập kho nhận thêm HĐ trống Nợ sau khi điền, HĐ chiết khấu vào DV ghi âm.")
print("\nALL DONE")
