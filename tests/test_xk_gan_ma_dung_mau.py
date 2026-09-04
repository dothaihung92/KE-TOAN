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
   D34xH30 cm - Gloss Orange", đúng ra phải là "... - Matte White"."""
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

# ===== Đối chứng: 2 mã THẬT SỰ là CÙNG 1 sản phẩm (không có gì phân biệt
# thêm ngoài kích thước, vd 1 mã phần mềm sinh + 1 mã cũ trong MISA) vẫn
# PHẢI ưu tiên mã XUẤT HIỆN TRƯỚC như thiết kế gốc (không đổi hành vi khi
# không có tín hiệu phân biệt nào để dùng). =====
ton3 = _ton_list([
    {"ma": "HH00001-8", "ten": "Chậu Polystone D40xH50 cm", "dvt": "Cái", "ton": 50, "gia": 100000},
    {"ma": "MH215-0", "ten": "Chậu Polystone D40xH50 cm", "dvt": "Cái", "ton": 50, "gia": 100000},
])
it3 = {"ten_sp": "Chậu nhựa-Polystone planter (Kích thước:D40xH50 cm), hàng mới 100%, xuất xứ Việt Nam#&VN",
       "sl": 5, "tt": 500000}
ket3 = server._xk_gan_1_muc(it3, ton3, {})
print("Đối chứng (2 mã CÙNG sản phẩm, không có gì phân biệt):", [(r["ma"], r.get("sl")) for r in ket3])
assert len(ket3) == 1 and ket3[0]["ma"] == "HH00001-8", (
    f"Khi 2 mã THẬT SỰ cùng 1 sản phẩm (không có tín hiệu phân biệt nào khác ngoài kích thước) vẫn phải "
    f"ưu tiên mã XUẤT HIỆN TRƯỚC trong file tồn kho như thiết kế gốc — được {ket3}")

print("\nPASS: _xk_gan_1_muc không còn gán nhầm màu khi nhiều mã cùng kích thước, vẫn giữ đúng quy tắc "
      "'ưu tiên mã đứng trước' khi 2 mã thật sự là cùng 1 sản phẩm không có gì phân biệt thêm.")
print("\nTẤT CẢ TEST PASS")
