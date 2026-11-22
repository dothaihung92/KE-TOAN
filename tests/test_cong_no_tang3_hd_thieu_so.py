import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server
f = server._misa_tt_tinh_vao_so_du
hd = [{"inv_no": "131", "so_tien": 22096800}, {"inv_no": "136", "so_tien": 4978800}]
# ca Đại Tùng: nội dung nêu HĐ 131 + 222, sổ chỉ có 131 -> chỉ tính 22.096.800, KHÔNG dùng 16.070.200 dư để che HĐ 136
tt = {"so_tien": 38167000, "mo_ta": "Cty Thiet Bi Sai Gon tt hd 131 222 cty DAI TUNG CKN 217425"}
assert f(tt, hd) == 22096800, f(tt, hd)
so_du = sum(h["so_tien"] for h in hd) - f(tt, hd)
assert so_du == 4978800 > 20000, so_du      # => không bị chặn Tầng 3, HĐ 136 lọt vào đề xuất điều chỉnh tiền mặt
# nêu đủ số hóa đơn đều có trong sổ -> tính nguyên khoản
assert f({"so_tien": 27075600, "mo_ta": "tt hd 131 va 136"}, hd) == 27075600
# không nêu số hóa đơn -> tính nguyên khoản (giữ hành vi cũ: tổng thể đã đủ thì không điều chỉnh)
assert f({"so_tien": 30000000, "mo_ta": "thanh toan tien hang"}, hd) == 30000000
# số ngắn (<3 chữ số) / ngày tháng không bị coi là số hóa đơn
assert f({"so_tien": 100, "mo_ta": "tt hd ngay 05/06/2025"}, hd) == 100
# nêu 2 số, thiếu 1 (222), có 136 -> chỉ tính phần của HĐ có trong sổ
assert f({"so_tien": 99, "mo_ta": "hd 136 222"}, hd) == 99      # min(tiền, 4.978.800)
assert f({"so_tien": 9000000, "mo_ta": "hd 136, 222"}, hd) == 4978800
# nối dây vào vòng tính số dư
sv = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py"), encoding="utf8").read()
assert "_misa_tt_tinh_vao_so_du(tt, d[\"hoa_don\"])" in sv
print("PASS: Tầng 3 — khoản chi nêu số HĐ thiếu trong sổ không còn che hóa đơn thật sự chưa trả (ca Đại Tùng HĐ 4.978.800)")
