import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: _gen_giathanh_export_rows (dựng cột "Tồn kho" chạy dần
trong file KetXuatGiaThanh_...xlsx xuất ra) KHÔNG được hiện Tồn kho ÂM SAI
khi 1 dòng bán bị TÁCH DÒNG (1 mã không đủ tồn cho hết số lượng, xem
_xk_gan_1_muc/_xk_gan_ma_truc_tiep) — trước đây trừ theo "sl" (Số lượng
BÁN GỐC trên hóa đơn, GIỮ NGUYÊN ở cả 2 dòng tách theo _xk_gan_ma_truc_tiep)
thay vì "sl_kho" (số lượng THỰC XUẤT từ ĐÚNG mã của dòng đó), khiến 1 mã bị
trừ NHẦM 2 LẦN đầy đủ "sl" dù thực tế mỗi dòng chỉ xuất 1 phần — ra Tồn kho
ÂM trên file xuất dù việc gán mã (con_lai) chưa hề vượt tồn thật.

Đúng ảnh chụp người dùng gửi: bấm "Dò mã hàng tự động" xong, cột "Tồn kho"
trên file Excel xuất ra hiện âm (-26, -20, -4, -9, -3...) cho nhiều mã.

Lưu ý: lưới trên MÀN HÌNH (hàm JS xkRowsToNl) đã trừ đúng theo sl_kho từ
trước (một đợt sửa lỗi liên quan khác) — bài test này khoá lại đúng hành vi
tương ứng ở PHÍA PYTHON (hàm dựng file Excel xuất ra), vốn đã bị LỆCH khỏi
JS (dùng "sl" thay vì "sl_kho"), là đúng nguyên nhân ảnh chụp người dùng
gửi (xem trên màn hình có thể đã đúng nhưng file xuất ra vẫn sai)."""
import sys
sys.path.insert(0, _REPO_ROOT)
import server


# 1 mã CHỈ có 30 tồn kho.
ton_rows = [{"ma": "MH100", "ten": "Chậu Polystone", "dvt": "Cái", "ton": 30}]

# Mô phỏng ĐÚNG kết quả của _xk_gan_ma_truc_tiep khi 1 dòng bán 30 SP bị
# TÁCH thành 2 dòng (mã MH100 chỉ đủ 30 cho CẢ dòng thật ra vừa đủ — đổi
# thành kịch bản tách 2 mã CÙNG 1 mã do gán 2 lần dò khác nhau vẫn giữ
# nguyên 'sl' gốc): 2 dòng CÙNG mã MH100, mỗi dòng "sl"=30 (GIỮ NGUYÊN số
# lượng bán gốc, đúng hành vi _xk_gan_ma_truc_tiep) nhưng "sl_kho" khác
# nhau (20 và 10 — tổng vừa đúng 30, KHÔNG vượt tồn thật).
giathanh_rows = [
    {"sohd": "1", "ngay": "01/01/2026", "ten_sp": "Chậu A", "dvt": "Cái",
     "sl": 30, "dgia": 100000, "tt": 3000000,
     "ma": "MH100", "ten_xk": "Chậu Polystone", "dvt_xk": "Cái", "sl_kho": 20, "gia_xk": 90000},
    {"sohd": "1", "ngay": "01/01/2026", "ten_sp": "Chậu A", "dvt": "Cái",
     "sl": 30, "dgia": 100000, "tt": 3000000,
     "ma": "MH100", "ten_xk": "Chậu Polystone", "dvt_xk": "Cái", "sl_kho": 10, "gia_xk": 90000},
]

out = server._gen_giathanh_export_rows(ton_rows, giathanh_rows)
ton_dong1, ton_dong2 = out[0][0], out[1][0]
print("Tồn kho dòng 1 (sau khi trừ 20):", ton_dong1)
print("Tồn kho dòng 2 (sau khi trừ tiếp 10):", ton_dong2)

assert ton_dong1 == 10, (
    f"Dòng 1 (sl_kho=20, tồn gốc 30) -> Tồn kho PHẢI = 10 (30-20), KHÔNG được trừ theo 'sl'=30 "
    f"(sẽ ra 0) — được {ton_dong1}")
assert ton_dong2 == 0, (
    f"Dòng 2 (sl_kho=10, sau dòng 1 còn 10) -> Tồn kho PHẢI = 0 (10-10), KHÔNG được trừ theo 'sl'=30 "
    f"lần nữa (sẽ ra -30, ÂM SAI đúng lỗi thật đã báo cáo) — được {ton_dong2}")
print("PASS: Tồn kho chạy dần trừ đúng theo sl_kho (số lượng THỰC XUẤT của đúng mã đó), "
      "không còn hiện âm sai khi dòng bán bị tách mã.")

print("\nTẤT CẢ TEST PASS")
