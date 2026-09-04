import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: _xk_gan_1_muc (dùng chung bởi _gen_xk_giathanh/
_xk_gan_ma_truc_tiep/_xk_gan_ma_lo_moi) KHÔNG được gán nhầm mã hàng khi
nhiều mã trong Tồn kho CÙNG kích thước nhưng KHÁC MÀU — trước đây
_kich_thuoc_khop_xk (so khớp kích thước) coi TẤT CẢ mã cùng kích thước là
'mạnh' như nhau, không so cả tên nên không phân biệt được màu, rồi chỉ lấy
mã XUẤT HIỆN TRƯỚC trong file tồn kho — gán sai màu dù đúng kích thước.

Đúng 2 ca thật người dùng báo cáo:
1) "Chậu nhựa-Polystone planter, Gloss WHITE (Kích thước:D35xH45 cm),
   hàng mới 100%, xuất xứ Việt Nam#&VN" bị gán nhầm "Chậu Polystone
   D35xH45 cm - Gloss Yellow", đúng ra phải là "... - Gloss White".
2) "Chậu nhựa-Polystone planter, MATTE WHITE (Kích thước:D34xH30 cm),
   hàng mới 100%, xuất xứ Việt Nam#&VN" bị gán nhầm "Chậu Polystone
   D34xH30 cm - Gloss Orange", đúng ra phải là "... - Matte White".
3) "Chậu nhựa-Polystone planter (D210xH62 cm - MTBK)-MATTE BLACK,kích
   thước:210x210x62(cm), hàng mới 100%, xuất xứ Việt Nam#&VN" bị gán nhầm
   "Chậu Polystone D210xH62 cm - MTWT", đúng ra phải là "... - MTBK" — KHÁC
   2 ca trên (màu viết chữ thường ngoài ngoặc): ở đây mã màu viết TẮT nằm
   NGAY TRONG NGOẶC cùng kích thước ('(D210xH62 cm - MTBK)'), mà
   _chuan_ten_hang_xk lại CẮT BỎ hẳn nội dung trong ngoặc trước khi so điểm
   giống tên -> điểm giống tên giữa 'MTBK' và 'MTWT' HOÀ NHAU (thậm chí
   'MTWT' còn nhỉnh hơn) nên vẫn chọn nhầm nếu chỉ dựa điểm giống tên — phải
   ưu tiên _ma_ngoac_khop_xk (so đúng cụm liền trong ngoặc, phân biệt được
   'MTBK' khác 'MTWT') TRƯỚC điểm giống tên mới đúng."""
import sys
sys.path.insert(0, _REPO_ROOT)
import server


def _ton_list(items):
    return [dict(it, con_lai=it["ton"], ten_chuan=server._chuan_ten_hang_xk(it["ten"]))
            for it in items]


# ===== Ca 1: Gloss White vs Gloss Yellow (cùng kích thước D35xH45) =====
# Mã SAI (Gloss Yellow) cố tình đứng TRƯỚC mã ĐÚNG (Gloss White) trong file
# tồn kho — đúng tình huống lỗi thật (trước đây cứ lấy mã đứng trước).
ton1 = _ton_list([
    {"ma": "MA-YELLOW", "ten": "Chậu Polystone D35xH45 cm - Gloss Yellow", "dvt": "Cái", "ton": 50, "gia": 100000},
    {"ma": "MA-WHITE", "ten": "Chậu Polystone D35xH45 cm - Gloss White", "dvt": "Cái", "ton": 50, "gia": 100000},
])
it1 = {"ten_sp": "Chậu nhựa-Polystone planter, Gloss WHITE (Kích thước:D35xH45 cm), hàng mới 100%, "
                 "xuất xứ Việt Nam#&VN", "sl": 5, "tt": 500000}
ket1 = server._xk_gan_1_muc(it1, ton1, {})
print("Ca 1 (Gloss White):", [(r["ma"], r.get("sl")) for r in ket1])
assert len(ket1) == 1 and ket1[0]["ma"] == "MA-WHITE", (
    f"'Gloss WHITE' PHẢI gán đúng mã 'MA-WHITE' (Gloss White), KHÔNG được gán nhầm 'MA-YELLOW' (Gloss "
    f"Yellow) dù mã đó đứng trước trong file tồn kho — được {ket1}")

# ===== Ca 2: Matte White vs Gloss Orange (cùng kích thước D34xH30) =====
# Mã SAI (Gloss Orange) cố tình đứng TRƯỚC mã ĐÚNG (Matte White).
ton2 = _ton_list([
    {"ma": "MA-ORANGE", "ten": "Chậu Polystone D34xH30 cm - Gloss Orange", "dvt": "Cái", "ton": 50, "gia": 100000},
    {"ma": "MA-MATTEWHITE", "ten": "Chậu Polystone D34xH30 cm - Matte White", "dvt": "Cái", "ton": 50, "gia": 100000},
])
it2 = {"ten_sp": "Chậu nhựa-Polystone planter, MATTE WHITE (Kích thước:D34xH30 cm), hàng mới 100%, "
                 "xuất xứ Việt Nam#&VN", "sl": 5, "tt": 500000}
ket2 = server._xk_gan_1_muc(it2, ton2, {})
print("Ca 2 (Matte White):", [(r["ma"], r.get("sl")) for r in ket2])
assert len(ket2) == 1 and ket2[0]["ma"] == "MA-MATTEWHITE", (
    f"'MATTE WHITE' PHẢI gán đúng mã 'MA-MATTEWHITE' (Matte White), KHÔNG được gán nhầm 'MA-ORANGE' "
    f"(Gloss Orange) dù mã đó đứng trước trong file tồn kho — được {ket2}")

# ===== Ca 3: mã màu viết TẮT nằm NGAY TRONG NGOẶC cùng kích thước (khác
# hẳn Ca 1/2 — màu viết chữ thường NGOÀI ngoặc) — '(D210xH62 cm - MTBK)' bị
# _chuan_ten_hang_xk CẮT BỎ hẳn trước khi so điểm giống tên, khiến điểm giữa
# 'MTBK' (đúng) và 'MTWT' (sai) gần như hoà nhau (thậm chí 'MTWT' còn nhỉnh
# hơn 1 chút) — PHẢI ưu tiên _ma_ngoac_khop_xk (so đúng cụm liền trong
# ngoặc) TRƯỚC điểm giống tên mới phân biệt đúng được. Mã SAI (MTWT) cố
# tình đứng TRƯỚC mã ĐÚNG (MTBK) trong file tồn kho.
ton3 = _ton_list([
    {"ma": "MA-MTWT", "ten": "Chậu Polystone D210xH62 cm - MTWT", "dvt": "Cái", "ton": 50, "gia": 100000},
    {"ma": "MA-MTBK", "ten": "Chậu Polystone D210xH62 cm - MTBK", "dvt": "Cái", "ton": 50, "gia": 100000},
])
it3 = {"ten_sp": "Chậu nhựa-Polystone planter (D210xH62 cm - MTBK)-MATTE BLACK,kích thước:210x210x62(cm), "
                 "hàng mới 100%, xuất xứ Việt Nam#&VN", "sl": 5, "tt": 500000}
ket3 = server._xk_gan_1_muc(it3, ton3, {})
print("Ca 3 (MTBK trong ngoặc):", [(r["ma"], r.get("sl")) for r in ket3])
assert len(ket3) == 1 and ket3[0]["ma"] == "MA-MTBK", (
    f"'(D210xH62 cm - MTBK)' PHẢI gán đúng mã 'MA-MTBK', KHÔNG được gán nhầm 'MA-MTWT' dù mã đó đứng "
    f"trước trong file tồn kho và điểm giống tên (sau khi cắt bỏ nội dung trong ngoặc) gần như hoà/nhỉnh "
    f"hơn — được {ket3}")

# ===== Đối chứng: 2 mã THẬT SỰ là CÙNG 1 sản phẩm (không có gì phân biệt
# thêm ngoài kích thước, vd 1 mã phần mềm sinh + 1 mã cũ trong MISA) vẫn
# PHẢI ưu tiên mã XUẤT HIỆN TRƯỚC như thiết kế gốc (không đổi hành vi khi
# không có tín hiệu phân biệt nào để dùng). =====
ton4 = _ton_list([
    {"ma": "HH00001-8", "ten": "Chậu Polystone D40xH50 cm", "dvt": "Cái", "ton": 50, "gia": 100000},
    {"ma": "MH215-0", "ten": "Chậu Polystone D40xH50 cm", "dvt": "Cái", "ton": 50, "gia": 100000},
])
it4 = {"ten_sp": "Chậu nhựa-Polystone planter (Kích thước:D40xH50 cm), hàng mới 100%, xuất xứ Việt Nam#&VN",
       "sl": 5, "tt": 500000}
ket4 = server._xk_gan_1_muc(it4, ton4, {})
print("Đối chứng (2 mã CÙNG sản phẩm, không có gì phân biệt):", [(r["ma"], r.get("sl")) for r in ket4])
assert len(ket4) == 1 and ket4[0]["ma"] == "HH00001-8", (
    f"Khi 2 mã THẬT SỰ cùng 1 sản phẩm (không có tín hiệu phân biệt nào khác ngoài kích thước) vẫn phải "
    f"ưu tiên mã XUẤT HIỆN TRƯỚC trong file tồn kho như thiết kế gốc — được {ket4}")

print("\nPASS: _xk_gan_1_muc không còn gán nhầm màu khi nhiều mã cùng kích thước, vẫn giữ đúng quy tắc "
      "'ưu tiên mã đứng trước' khi 2 mã thật sự là cùng 1 sản phẩm không có gì phân biệt thêm.")
print("\nTẤT CẢ TEST PASS")
