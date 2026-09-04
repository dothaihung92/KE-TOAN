import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: _xk_gan_ma_truc_tiep — khi 1 dòng có "Mã hàng kho" RÁC
(không tồn tại trong Tồn kho hiện có, xem test_xk_ma_rac_khong_ton_tai.py)
NHƯNG dò lại (_xk_gan_1_muc) KHÔNG đủ tin cậy để tự gán lại (tên bán/tên
kho viết khác hẳn nhau, điểm giống tên chưa đạt ngưỡng "mạnh") thì PHẢI XOÁ
mã rác đi (để trống, mờ hồ, có gợi ý) — KHÔNG được giữ nguyên mã rác cũ.

Đúng ca thật người dùng gửi lại (file KetXuatGiaThanh MỚI, upload SAU khi
build .159/.160 đã sửa lỗi mã rác) — "đã up bảng mới dò mã hàng mới vẫn
bị": dòng "GẠCH ỐP LÁT 600*1200MM" (mã cũ rác "Gạch men 600x1200 mm", xem
test_xk_ma_rac_khong_ton_tai.py) VẪN y hệt như cũ sau khi bấm "Dò mã hàng
tự động" lại — vì bản .159/.160 CHỈ mới xử lý đúng trường hợp dò lại được
tự tin (ten_sp TRÙNG/gần trùng hẳn tên Tồn kho) — ca thật này "GẠCH ỐP LÁT
600*1200MM" (tên bán) khác hẳn cách viết "Gạch men 600x1200 mm" (tên kho)
nên _xk_gan_1_muc chỉ đạt điểm giống tên 0,743 (CHƯA đạt ngưỡng "mạnh" để
tự gán) — nhánh "không đủ tin cậy" của _xk_gan_ma_truc_tiep TRƯỚC ĐÂY xử
lý bằng cách "giữ NGUYÊN dòng gốc" — ĐÚNG cho dòng CHƯA TỪNG có mã, nhưng
SAI cho dòng đang có mã RÁC (giữ luôn cả mã rác), khiến MISA vẫn từ chối
ghi sổ y hệt như trước dù đã bấm dò mã lại nhiều lần."""
import sys
sys.path.insert(0, _REPO_ROOT)
import server

# Tên bán ("Tên Sản Phẩm") viết khác hẳn tên Tồn kho -> _xk_gan_1_muc không
# đủ tin cậy để tự gán (giống thật: "GẠCH ỐP LÁT 600*1200MM" bán vs "Gạch
# men 600x1200 mm" trong Tồn kho).
ton_rows = [
    {"ma": "HH00087-8", "ten": "Gạch men 600x1200 mm", "dvt": "m2", "ton": 79.2, "gia": 140878},
    {"ma": "HH00026-8", "ten": "Gạch 60x120", "dvt": "Hộp", "ton": 110, "gia": 149364},
]
giathanh_cu = [{
    "sohd": "3", "ngay": "07/05/2024", "ten_sp": "GẠCH ỐP LÁT 600*1200MM", "dvt": "M2",
    "sl": 61.92, "dgia": 288000, "tt": 17832960,
    # "Mã hàng kho" đang là RÁC — chính TÊN hàng, không phải mã thật — và dò
    # lại KHÔNG đủ tin cậy để tự sửa (khác test_xk_ma_rac_khong_ton_tai.py).
    "ma": "Gạch men 600x1200 mm", "ten_xk": "Gạch men 600x1200 mm", "dvt_xk": "Cái",
    "sl_kho": 61.92, "gia_xk": 140878,
}]

out = server._xk_gan_ma_truc_tiep(ton_rows, giathanh_cu, {})
print("Kết quả:", out)

assert len(out) == 1
dong = out[0]
assert dong["ma"] == "", (
    f"Mã 'Gạch men 600x1200 mm' KHÔNG tồn tại trong Tồn kho VÀ dò lại KHÔNG đủ tin cậy để tự gán -> PHẢI "
    f"XOÁ mã rác (để trống, mờ hồ), KHÔNG được giữ nguyên mã rác cũ (MISA vẫn sẽ từ chối ghi sổ) — "
    f"được ma={dong['ma']!r}")
assert dong["ten_xk"] == "" and dong["dvt_xk"] == "" and dong["gia_xk"] == "" and dong["sl_kho"] == "", (
    f"Xoá mã rác thì PHẢI xoá luôn Tên/ĐVT/Đơn giá/SL kho đi kèm (đều là dữ liệu ăn theo mã rác) — được {dong}")
assert dong.get("mo_ho") is True, "Dòng phải được đánh dấu 'mờ hồ' để hiện đỏ, người dùng biết mà tự chọn"
goi_y_ma = [g["ma"] for g in (dong.get("goi_y") or [])]
assert "HH00087-8" in goi_y_ma, (
    f"Danh sách gợi ý PHẢI có đúng mã thật 'HH00087-8' (Gạch men 600x1200 mm, điểm giống tên cao nhất) để "
    f"người dùng tự chọn — được goi_y={goi_y_ma}")
# Số lượng/Thành tiền/Tên Sản Phẩm gốc (bên bán) KHÔNG được đụng tới.
assert dong["sl"] == 61.92 and dong["tt"] == 17832960 and dong["ten_sp"] == "GẠCH ỐP LÁT 600*1200MM"

print("\nPASS: _xk_gan_ma_truc_tiep giờ XOÁ đúng 'Mã hàng kho' RÁC khi dò lại không đủ tin cậy để tự sửa "
      "(thay vì giữ nguyên mã rác cũ), kèm gợi ý đúng mã thật cho người dùng tự chọn.")
print("\nTẤT CẢ TEST PASS")
