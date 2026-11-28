import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Tên bán lẻ/sàn TMĐT viết khác hẳn tên tồn kho nhập khẩu (mô tả + mã CAS + 12pcs/carton...) -> khớp theo TỪ KHOÁ + kích cỡ + hương/màu, KHÔNG đoán bừa hương khác.
def ton(ma, ten, dvt="Hộp", sl=1000, gia=30000):
    t = {"ma": ma, "ten": ten, "dvt": dvt, "ton": sl, "gia": gia}
    return dict(t, con_lai=sl, ten_chuan=server._chuan_ten_hang_xk(ten))

TL = lambda: [
    ton("MH381", "Sáp thơm - King's Stella Kakao Friends Fresh Gel 180g, hương Lacosta, 12pcs/carton, mã CAS: 61788-85-0; 9000-07-1; 7732-18-5"),
    ton("MH226", "Sáp thơm - King's Stella Kakao Friends Fresh Gel 180g, hương Lacosta, 12pcs/carton, mã CAS: 61788-85-0, hàng mới 100%", sl=100),
    ton("HH00046-8", "Sáp thơm - King's Stella Kakao Friends Fresh Gel 180g, hương Nho, 12pcs/carton, mã CAS: 61788-85-0; 9000-07-1; 7732-18-5"),
    ton("MH382", "Sáp thơm - King's Stella Kakao Friends Fresh Gel 180g, hương Đào, 12pcs/carton, mã CAS: 61788-85-0; 9000-07-1; 7732-18-5"),
    ton("HH00056-8", "Xịt Bọt Bảo Vệ Và Làm Bóng - President's Wax One Spray 450ml, hiệu: King's Stella Group Co., Ltd, hàng mới 100%", "Chai"),
    ton("MH76", "Xịt Thơm Không Khí - King's Stella Horeca 300ml, hương chanh, 12pcs/carton, mã CAS: 68476-85-7", "Chai"),
    ton("MH75", "Xịt Thơm Không Khí - King's Stella Horeca 300ml, hương bó hoa trắng, 12pcs/carton, mã CAS: 68476-85-7", "Chai"),
]
def gan(ten, sl=10):
    tl = TL()
    ket = server._xk_gan_1_muc({"ten_sp": ten, "sl": sl, "tt": sl * 40000}, tl, {})
    return [(k.get("ma"), k.get("sl")) for k in ket], tl

# 1) tên sàn + hương Lacosta (đuôi mã đơn) -> đúng mã hương Lacosta (MH381 đứng trước), KHÔNG lấy hương Nho/Đào
k, _ = gan("Sáp Thơm Kakao Hương Nước Hoa Cao Cấp King's Stella KAKAO FRIENDS 180g- Hương Lacosta-2608258EJ5MY3F")
assert k == [("MH381", 10)], k
# 2) hương viết tiếng Anh trong ngoặc ('# Peachy Peach' = Đào)
k, _ = gan("Sáp Thơm King's Stella x KAKAO FRIENDS Fresh Gel 180 g. (King's Stella x KAKAO FRIENDS Fresh Gel 180 g. # Peachy Peach)")
assert k == [("MH382", 10)], k
# 3) tên khác hẳn nhưng cùng mặt hàng, không hương: 'Xịt Bóng President's WaxOne Spray 450 ml. # Brut' -> HH00056-8
k, _ = gan("Xịt Bóng President's WaxOne Spray 450 ml. # Brut")
assert k == [("HH00056-8", 10)], k
# 4) hương KHÔNG có trong tồn (Lavender) -> để trống, không gán nhầm hương khác
k, _ = gan("Xịt thơm không khí King's Stella Horeca 300ml. Hương Lavender (King's Stella HoReCa 300 ml. # Lavender)")
assert k == [(("") , 10)], k
# 5) tên sàn chung chung KHÔNG nói hương -> được xuất lần lượt trong cùng dòng sản phẩm (không để trống)
k, _ = gan("Xịt Phòng Khử Mùi Không Khí Ẩm Mốc King's Stella Horeca 300ml, Thơm Như Khách Sạn, Quán Cafe")
assert k and k[0][0] in ("MH76", "MH75"), k
# 6) khác KÍCH CỠ -> không gán (tên bán 180g không được lấy hàng 300ml)
k, _ = gan("Xịt Thơm Không Khí King's Stella Horeca 180g Hương chanh")
assert k == [("", 10)], k
# 7) trừ tồn dần: Lacosta bán 1050 -> hết MH381 (1000) rồi sang MH226 (50), cùng hương, không âm
tl = TL()
ket = server._xk_gan_1_muc({"ten_sp": "Sáp Thơm King's Stella KAKAO FRIENDS 180g- Hương Lacosta-2608258EJ5MY3F", "sl": 1050, "tt": 1050 * 40000}, tl, {})
assert [(k["ma"], k["sl"]) for k in ket] == [("MH381", 1000), ("MH226", 50)], ket      # cùng hương Lacosta: dùng hết mã khớp tên nhất rồi sang mã tương đương; tổng = 1050
assert all(t["con_lai"] >= 0 for t in tl)
print("PASS: khớp từ khoá tên bán lẻ/sàn vs tên tồn nhập khẩu (hương/kích cỡ đúng, không đoán bừa, trừ tồn dần).")
