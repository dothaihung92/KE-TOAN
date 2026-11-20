import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server
# Ca thật: HĐ 99 (MST 0317894853) Bảng kê 780.000 (2 dòng TK Nợ 1561) nhưng MISA có chứng từ NHẬP KHO 780.000 + chứng từ MUA DỊCH VỤ cũ 410.000 -> tổng 1.190.000 báo LỆCH;
# HĐ 110 (MST 0318011620): Bảng kê 250.000, MISA có nhập kho 250.000 + dịch vụ 250.000 = 500.000. Phần mềm phải chỉ ĐÚNG chứng từ dư, không nói chung chung "Import lại".
H = ["Ký hiệu", "Số HĐ", "Ngày", "Người bán", "MST bán", "STT", "Mã vt", "Tên hàng hóa/dịch vụ", "ĐVT", "Số lượng", "Đơn giá", "Thành tiền", "Thuế suất", "Tiền thuế GTGT", "Trị giá tính thuế NK", "Thuế suất NK", "Tiền thuế NK", "Nợ", "Có"]
R = [["C26TTT", "99", "06/03/2026", "TÂN TIẾN", "0317894853", "1", None, "Quạt đứng", "Cái", 1, 410000, 410000, "8%", 32800, None, None, None, "1561", "331"],
     ["C26TTT", "99", "06/03/2026", "TÂN TIẾN", "0317894853", "2", None, "Quạt treo", "Cái", 1, 370000, 370000, "8%", 29600, None, None, None, "1561", "331"],
     ["C26TVN", "110", "08/04/2026", "ONEST", "0318011620", "1", None, "gia công inox", "tấm", 2, 125000, 250000, "8%", 20000, None, None, None, "1561", "331"],
     ["C26TXX", "5", "08/04/2026", "DV CO", "0300000001", "1", None, "phí dịch vụ", "lần", 1, 100000, 100000, "8%", 8000, None, None, None, "6427", "331"]]
server._doc_nhap_lieu = lambda cid, loai: (H, R)
bk = {(e["so_hd"]): e for e in server._hoa_don_tu_bang_ke(1, "in")}
assert bk["99"]["no"] == {"1561"} and round(bk["99"]["ds"]) == 780000 and bk["5"]["no"] == {"6427"}, bk
x99 = {"mst": "0317894853", "so_hd": "99", "doanh_so_nguon": 780000, "thue_nguon": 62400, "doanh_so_misa": 1190000, "thue_misa": 95200,
       "misa_nk": 780000, "misa_dv": 410000, "misa_thue_nk": 62400, "misa_thue_dv": 32800}
t = server._ghi_chu_ghi_trung_nk_dv(x99, bk["99"])
assert "Mua dịch vụ 410.000" in t and "XOÁ chứng từ Mua dịch vụ" in t and "1.190.000" in t and "780.000" in t and "1561" in t, t
x110 = {"mst": "0318011620", "so_hd": "110", "doanh_so_nguon": 250000, "thue_nguon": 20000, "doanh_so_misa": 500000, "thue_misa": 40000,
        "misa_nk": 250000, "misa_dv": 250000, "misa_thue_nk": 20000, "misa_thue_dv": 20000}
t = server._ghi_chu_ghi_trung_nk_dv(x110, bk["110"])
assert "XOÁ chứng từ Mua dịch vụ" in t and "250.000" in t and "500.000" in t, t
# Bảng kê ghi DỊCH VỤ (TK Nợ 6xx) mà MISA có thêm chứng từ nhập kho -> chứng từ nhập kho là dư
x5 = {"mst": "0300000001", "so_hd": "5", "doanh_so_nguon": 100000, "thue_nguon": 8000, "doanh_so_misa": 160000, "thue_misa": 12800, "misa_nk": 60000, "misa_dv": 100000, "misa_thue_nk": 4800, "misa_thue_dv": 8000}
t = server._ghi_chu_ghi_trung_nk_dv(x5, bk["5"])
assert "XOÁ chứng từ Mua hàng nhập kho/không qua kho" in t, t
# chỉ 1 loại chứng từ -> không phải ca ghi trùng (giữ hướng dẫn cũ)
assert server._ghi_chu_ghi_trung_nk_dv(dict(x99, misa_dv=0), bk["99"]) == ""
print("PASS: lệch do MISA ghi 1 hóa đơn ở cả chứng từ nhập kho lẫn Mua dịch vụ -> chỉ đúng chứng từ dư cần xoá (ca HĐ 99, 110)")
