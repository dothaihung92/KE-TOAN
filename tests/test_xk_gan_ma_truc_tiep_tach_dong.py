import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: _xk_gan_ma_truc_tiep (dò mã TRỰC TIẾP trên GIATHANH đang
có, dùng bởi xk_tao_giathanh khi bảng Xuất Kho KHÔNG rỗng — và bởi luồng
'↺ Gỡ mã hàng' + 'Dò mã hàng tự động' để tính lại HOÀN TOÀN từ đầu) nay PHẢI
hỗ trợ TÁCH DÒNG (1 dòng cần nhiều mã mới đủ SL kho) giống hệt dò mã từ Chi
tiết bán ra (_gen_xk_giathanh) — trước khi sửa, hàm này chỉ gán được đúng 1
mã, dòng nào cần tách phải để trống hẳn (kém hơn), khiến sau khi '↺ Gỡ mã
hàng' rồi 'Dò mã hàng tự động' lại RA KẾT QUẢ TỆ HƠN trước khi gỡ.

CẬP NHẬT: trước đây test này khẳng định 'sl' (Số lượng) phải GIỮ NGUYÊN số
gốc (5) trên CẢ 2 dòng tách — nhưng đúng đây chính là lỗi người dùng báo lại
sau đó kèm ảnh chụp file thật (D36xH20 cm - LIGHT GREY, bán 144, tách
138+6 nhưng CẢ 2 dòng đều hiện 'Số lượng'=144, cộng dồn sai gấp đôi). Đã
sửa lại: mỗi dòng tách PHẢI ghi ĐÚNG phần số lượng CÒN LẠI của riêng nó vào
'sl' (giống hệt 'sl_kho'), xem test_xk_tach_dong_so_luong_dung.py."""
import sys
sys.path.insert(0, _REPO_ROOT)
import server

ton_rows = [
    {"ma": "MA1", "ten": "Chau ABC", "dvt": "Cai", "ton": 3, "gia": 100000},
    {"ma": "MA2", "ten": "Chau ABC", "dvt": "Cai", "ton": 4, "gia": 100000},
]

# Mô phỏng đúng luồng "↺ Gỡ mã hàng": 1 dòng GIATHANH đã gỡ trắng mã/sl_kho,
# CHỈ còn lại 'sl' (Số lượng bán gốc) = 5 -> không mã đơn nào (3 hay 4) đủ
# nguyên 5, PHẢI tách dòng (3 từ MA1 + 2 từ MA2, đúng thứ tự trong Tồn kho).
giathanh_cu = [{
    "khhdon": "", "sohd": "H1", "ngay": "10/05/2026", "ten_sp": "Chau ABC",
    "dvt": "Cai", "sl": 5, "dgia": 100000, "tt": 500000,
    "ma": "", "ten_xk": "", "dvt_xk": "", "gia_xk": "", "sl_kho": "",
    "goi_y": [], "mo_ho": False, "thieu_ton": False,
}]

ket = server._xk_gan_ma_truc_tiep(ton_rows, giathanh_cu, {})
print("Kết quả dò mã trực tiếp (sau khi Gỡ mã hàng, dòng cần tách):", ket)

assert len(ket) == 2, f"Dòng H1 (SL=5, không mã đơn nào đủ) phải bị TÁCH thành 2 dòng — được {len(ket)}: {ket}"
ma1 = next(r for r in ket if r["ma"] == "MA1")
ma2 = next(r for r in ket if r["ma"] == "MA2")
assert ma1["sl_kho"] == 3 and ma2["sl_kho"] == 2, (
    f"Tách phải đúng 3 (MA1, hết tồn) + 2 (MA2, bù thiếu), ghi vào 'sl_kho' — được MA1.sl_kho={ma1['sl_kho']}, "
    f"MA2.sl_kho={ma2['sl_kho']}")
assert ma1["sl"] == 3 and ma2["sl"] == 2, (
    f"'sl' (Số lượng) PHẢI đúng bằng phần CÒN LẠI đã tách của từng dòng (giống hệt 'sl_kho'), KHÔNG được "
    f"giữ nguyên số gốc 5 trên cả 2 dòng (lỗi thật đã báo cáo, xem test_xk_tach_dong_so_luong_dung.py) — "
    f"được MA1.sl={ma1['sl']}, MA2.sl={ma2['sl']}")
assert ma1["sohd"] == "H1" and ma2["sohd"] == "H1", "Cả 2 dòng tách phải giữ đúng Số HĐ gốc H1"

print("PASS: _xk_gan_ma_truc_tiep (dùng cho 'Dò mã hàng tự động' xử lý trực tiếp GIATHANH đang có, và "
      "luồng '↺ Gỡ mã hàng' tính lại từ đầu) nay hỗ trợ TÁCH DÒNG đúng như dò từ Chi tiết bán ra — không "
      "còn kém hơn sau khi đổi sang xử lý trực tiếp trên bảng Xuất Kho thay vì rebuild lại từ ctbr.")

print("\nTẤT CẢ TEST PASS")
