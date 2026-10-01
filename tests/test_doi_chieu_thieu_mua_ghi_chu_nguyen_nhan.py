import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Người dùng báo đối chiếu đầu vào "THIẾU trong MISA" 11 hóa đơn (1706, 1759, 185, 1264 + các HĐ điều chỉnh âm của Satori).
# Dữ liệu thật: 4 HĐ dương nằm trong Bảng kê đầu vào nhưng cột TK Nợ để TRỐNG (NCC mới, chưa học TK) -> Import bỏ qua dòng;
# các HĐ âm là hóa đơn điều chỉnh/giảm. Đối chiếu đúng là THIẾU — nay kèm GHI CHÚ NGUYÊN NHÂN để biết cách xử lý.
hd = ["Ký hiệu", "Số HĐ", "Ngày", "Người bán", "MST bán", "Nợ", "Có"]
rows = [["C26TYY", "1706", "09/09/2026", "HOA HỒNG PHÁT", "0318961005", "", "331"],
        ["C26TYY", "1707", "09/09/2026", "HOA HỒNG PHÁT", "0318961005", "1561", "331"],
        ["C26TSA", "5451", "17/09/2026", "SATORI", "0319340593", "6427", "331"]]
server._doc_nhap_lieu = lambda cid, loai="in": (hd, rows)
ds = [{"mst": "0318961005", "so_hd": "1706", "doanh_so_nguon": 182500000, "thue_nguon": 14600000},
      {"mst": "0318961005", "so_hd": "1707", "doanh_so_nguon": 1000, "thue_nguon": 80},
      {"mst": "0319340593", "so_hd": "5451", "doanh_so_nguon": -10980720, "thue_nguon": -878458},
      {"mst": "0313517406", "so_hd": "1264", "doanh_so_nguon": 975000, "thue_nguon": 78000}]
server._doi_chieu_ghi_chu_thieu_mua(1, ds)
assert "CHƯA có TK Nợ" in ds[0]["ghi_chu"], ds[0]
assert "chưa ghi vào MISA" in ds[1]["ghi_chu"] and "1561" in ds[1]["ghi_chu"], ds[1]
assert "điều chỉnh/giảm" in ds[2]["ghi_chu"] and "6427" not in ds[2]["ghi_chu"].split("|")[0], ds[2]
assert "Chưa có trong Bảng kê" in ds[3]["ghi_chu"], ds[3]
print("PASS 1: ghi chú nguyên nhân cho HĐ mua vào THIẾU (thiếu TK Nợ / chưa ghi / HĐ điều chỉnh âm / chưa có trong bảng kê).")

dc = {"mua_hang": {"thieu": ds}, "ban_hang": {"lech": [{"mst": "x", "so_hd": "10216", "ngay": "2026-09-24", "doanh_so_nguon": 1, "doanh_so_misa": 2,
                                                         "thue_nguon": 3, "thue_misa": 4, "chenh_lech": -2}]}}
rr = server._doi_chieu_xuat_rows(dc)
assert all(len(r) == len(server._DOI_CHIEU_XUAT_HEADERS) for r in rr) and server._DOI_CHIEU_XUAT_HEADERS[-1] == "Ghi chú"
assert [r for r in rr if r[3] == "1706"][0][-1].startswith("Bảng kê đầu vào CHƯA có TK Nợ")
print("PASS 2: xuất Excel có cột 'Ghi chú'.")
print("\nALL DONE")
