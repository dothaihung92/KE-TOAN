import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# File import Chứng từ bán hàng (_gen_ban_hang): khách nước ngoài (MST ghi 'KL') ghi Mã khách hàng THEO TÊN; 'KL' chỉ cho người tiêu dùng.
h = ["Ngày lập", "Số hóa đơn", "MST người mua", "Tên người mua", "Mặt hàng", "Doanh số bán chưa thuế", "Thuế GTGT", "Ký hiệu HĐ", "Ký hiệu mẫu", "Thành tiền USD"]
rows = [["25/09/2026", "22", "KL", "BARON LTD", "Chậu", 307883584, 0, "C26TUE", "1", 12000],      # xuất khẩu (USD) -> mã theo tên
        ["26/09/2026", "23", "", "Bán cho người tiêu dùng", "x", 5, 0, "C26TUE", "1", ""],
        ["27/09/2026", "24", "0312345678", "Cty A", "x", 5, 0, "C26TUE", "1", ""],
        ["28/09/2026", "25", "", "Anh Nguyễn Văn B", "x", 5, 0, "C26TUE", "1", ""]]               # không MST, không xuất khẩu -> KL
o = server._gen_ban_hang(1, h, rows)
assert [x[15] for x in o] == ["BARONLTD", "KL", "0312345678", "KL"], [x[15] for x in o]
assert o[0][18] == "" and o[2][18] == "0312345678"
print("PASS: khách nước ngoài ghi mã theo tên, không ghi KL.")
print("\nALL DONE")
