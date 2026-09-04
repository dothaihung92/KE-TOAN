import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: _xk_gan_ma_truc_tiep (hàm THẬT SỰ được gọi khi bấm nút
"🔍 Dò mã hàng tự động" lúc GIATHANH đã có dữ liệu sẵn — xem xk_tao_giathanh)
PHẢI tự sửa lại mã hàng ĐÃ GÁN SAI từ 1 lần dò lỗi TRƯỚC, không được giữ
NGUYÊN mãi mãi chỉ vì dòng đó "đã có mã".

Đúng ca thật người dùng báo cáo LẦN THỨ 3 liên tiếp cho cùng 1 lỗi:
- Lần 1 (build .149 trở về trước): "(D210xH62 cm - MTBK)" gán nhầm
  "... MTWT" — sửa ở _xk_gan_1_muc (ưu tiên _ma_ngoac_khop_xk, xem
  test_xk_gan_ma_dung_mau.py Ca 3).
- Lần 2 (build .150): fix Ca 3 ĐÚNG cho "D210xH62" (chưa từng dò sai) —
  nhưng "D180xH50"/"D150xH47"/"D120xH40" (ĐÃ dò sai ở 1 lần dò TRƯỚC bản
  .150) VẪN sai — vì mã sai đã "học" vào hoc_ma, đè lên fix mới — sửa ở
  _xk_gan_1_muc (chỉ tin hoc_ma khi KHÔNG có tín hiệu mã-trong-ngoặc chắc
  chắn hơn, xem test_xk_gan_ma_dung_mau.py Ca 4).
- Lần 3 (build .152): fix Ca 4 VẪN không đủ — vì nút "Dò mã hàng tự động"
  THẬT SỰ đang gọi (khi GIATHANH đã có dữ liệu, tức HẦU HẾT trường hợp
  thực tế) là _xk_gan_ma_truc_tiep, KHÔNG PHẢI _gen_xk_giathanh — hàm này
  có cơ chế RIÊNG, độc lập: "dòng đã có mã thì GIỮ NGUYÊN, chỉ xử lý dòng
  trống" — không hề đưa dòng có mã (dù sai) qua _xk_gan_1_muc để hưởng các
  fix ở Ca 3/Ca 4, nên "(D180xH50 cm - MTBK)" cứ mãi gán nhầm y hệt sau cả
  2 lần sửa trước — đúng nguyên nhân người dùng báo lại lần 3."""
import sys
sys.path.insert(0, _REPO_ROOT)
import server


ton_rows = [
    {"ma": "HH00009-8", "ten": "Chậu Polystone D180xH50 cm - MTBK", "dvt": "Cái", "ton": 2, "gia": 3480000},
    {"ma": "HH00010-8", "ten": "Chậu Polystone D180xH50 cm - MTWT", "dvt": "Cái", "ton": 3, "gia": 3480000},
]
ten_mtbk = ("Chậu nhựa-Polystone planter (D180xH50 cm - MTBK)-MATTE BLACK,kích thước:180x180x50(cm), "
            "hàng mới 100%, xuất xứ Việt Nam#&VN")
ten_mtwt = ("Chậu nhựa-Polystone planter (D180xH50 cm - MTWT)-MATTE WHITE,kích thước:180x180x50(cm), "
            "hàng mới 100%, xuất xứ Việt Nam#&VN")
# ĐÚNG dữ liệu thật gửi lại: GIATHANH đã có sẵn, mã màu bị ĐẢO NGƯỢC từ 1
# lần dò lỗi trước (MTBK->mã MTWT, MTWT->mã MTBK), kèm "Tên hàng xuất kho"
# SAI THEO (đúng những gì thật sự lưu trong file, không phải chỉ riêng cột
# "Mã hàng kho").
giathanh_cu = [
    {"sohd": "1", "ngay": "12/05/2026", "ten_sp": ten_mtbk, "dvt": "PCE", "sl": 2,
     "dgia": 5534926.56, "tt": 11069853.12,
     "ma": "HH00010-8", "ten_xk": "Chậu Polystone D180xH50 cm - MTWT", "dvt_xk": "Cái",
     "sl_kho": 2, "gia_xk": 3480000},
    {"sohd": "1", "ngay": "12/05/2026", "ten_sp": ten_mtwt, "dvt": "PCE", "sl": 3,
     "dgia": 5534926.56, "tt": 16604780,
     "ma": "HH00009-8", "ten_xk": "Chậu Polystone D180xH50 cm - MTBK", "dvt_xk": "Cái",
     "sl_kho": 3, "gia_xk": 3480000},
]

out = server._xk_gan_ma_truc_tiep(ton_rows, giathanh_cu, {})
print("Kết quả:")
for r in out:
    print(" -", r["ten_sp"][:60], "|", r["ma"], "|", r.get("ten_xk"), "| sl_kho=", r.get("sl_kho"))

dong_mtbk = next(r for r in out if r["ten_sp"] == ten_mtbk)
dong_mtwt = next(r for r in out if r["ten_sp"] == ten_mtwt)

assert dong_mtbk["ma"] == "HH00009-8", (
    f"Bấm lại 'Dò mã hàng tự động' PHẢI TỰ SỬA mã sai cũ 'HH00010-8' (MTWT) thành đúng 'HH00009-8' "
    f"(MTBK) cho dòng '(D180xH50 cm - MTBK)', KHÔNG được giữ nguyên chỉ vì dòng đã có mã — được {dong_mtbk}")
assert dong_mtbk["ten_xk"] == "Chậu Polystone D180xH50 cm - MTBK", (
    f"'Tên hàng xuất kho' cũng PHẢI cập nhật theo mã MỚI, không được giữ chữ của mã SAI cũ — "
    f"được {dong_mtbk}")
assert dong_mtwt["ma"] == "HH00010-8", (
    f"Dòng '(D180xH50 cm - MTWT)' PHẢI TỰ SỬA mã sai cũ 'HH00009-8' (MTBK) thành đúng 'HH00010-8' "
    f"(MTWT) — được {dong_mtwt}")
assert dong_mtwt["ten_xk"] == "Chậu Polystone D180xH50 cm - MTWT", (
    f"'Tên hàng xuất kho' của dòng MTWT cũng phải cập nhật đúng — được {dong_mtwt}")
assert dong_mtbk["sl_kho"] == 2 and dong_mtwt["sl_kho"] == 3, (
    f"Không được tách dòng dây chuyền — mỗi dòng phải đủ đúng số lượng gốc của nó — "
    f"MTBK sl_kho={dong_mtbk.get('sl_kho')}, MTWT sl_kho={dong_mtwt.get('sl_kho')}")

print("\nPASS: nút 'Dò mã hàng tự động' (khi GIATHANH đã có dữ liệu, tức _xk_gan_ma_truc_tiep) giờ TỰ "
      "SỬA được mã hàng đã gán sai từ lần dò lỗi trước, không còn giữ mãi mã sai chỉ vì dòng đã có mã — "
      "cả cột Mã hàng kho lẫn Tên hàng xuất kho đều được cập nhật đúng.")
print("\nTẤT CẢ TEST PASS")
