import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: "📥 Kết xuất Excel" ở màn Đối chiếu tổng giá trị & VAT —
gộp đủ 3 danh sách (thiếu/lệch/thừa) của CẢ Bán hàng lẫn Mua hàng thành các
dòng phẳng đúng thứ tự cột _DOI_CHIEU_XUAT_HEADERS, đúng yêu cầu người
dùng: "Chổ kiểm tra hãy thêm nút kết xuất excel để dò check lệch đầu vào và
đầu ra" (sau khi báo cáo "vẫn import thiếu và báo thừa hoá đơn")."""
import sys
sys.path.insert(0, _REPO_ROOT)
import server

dc = {
    "ban_hang": {
        "thieu": [{"mst": "", "so_hd": "1", "ngay": "2026-01-09",
                   "doanh_so_nguon": 581338473, "thue_nguon": 0}],
        "lech": [],
        "thua": [],
    },
    "mua_hang": {
        "thieu": [],
        "lech": [{"mst": "0316491058", "so_hd": "22", "ngay": "2026-02-05",
                  "doanh_so_nguon": 1000000, "doanh_so_misa": 900000,
                  "thue_nguon": 100000, "thue_misa": 90000, "chenh_lech": -100000}],
        "thua": [{"mst": "038303003080", "so_hd": "2843", "ngay": "2026-03-18",
                  "doanh_so_misa": 570564, "thue_misa": 0}],
    },
}

rows = server._doi_chieu_xuat_rows(dc)
print("Rows:", rows)
assert len(rows) == 3, f"Phải gộp đúng 3 dòng (1 thiếu Bán hàng + 1 lệch Mua hàng + 1 thừa Mua hàng) — được {len(rows)}"

r_thieu = next(r for r in rows if r[1] == "THIẾU trong MISA")
assert r_thieu[0] == "Bán hàng" and r_thieu[3] == "1" and r_thieu[5] == 581338473 and r_thieu[6] == "", (
    f"Dòng THIẾU phải đúng loại/số HĐ/doanh số nguồn, doanh số MISA để trống — được {r_thieu}")

r_lech = next(r for r in rows if r[1] == "LỆCH")
assert r_lech[0] == "Mua hàng" and r_lech[5] == 1000000 and r_lech[6] == 900000 and r_lech[9] == -100000, (
    f"Dòng LỆCH phải đúng cả doanh số nguồn LẪN MISA + chênh lệch — được {r_lech}")

r_thua = next(r for r in rows if r[1].startswith("THỪA"))
assert r_thua[0] == "Mua hàng" and r_thua[5] == "" and r_thua[6] == 570564, (
    f"Dòng THỪA phải để trống doanh số nguồn (không có), chỉ có doanh số MISA — được {r_thua}")

assert len(server._DOI_CHIEU_XUAT_HEADERS) == len(rows[0]), (
    f"Số cột mỗi dòng phải khớp đúng số cột header — headers={len(server._DOI_CHIEU_XUAT_HEADERS)}, "
    f"dòng={len(rows[0])}")

print("PASS: _doi_chieu_xuat_rows gộp đúng cả 3 loại (thiếu/lệch/thừa) của cả Bán hàng lẫn Mua hàng.")
print("\nTẤT CẢ TEST PASS")
