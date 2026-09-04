import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: _xk_gan_ma_truc_tiep (nút "🔍 Dò mã hàng tự động" khi
GIATHANH đã có dữ liệu) khi TÁCH DÒNG (1 mã không đủ tồn cho hết số lượng
cần bán) PHẢI ghi ĐÚNG số lượng CÒN LẠI của từng dòng con vào cột "Số
lượng" (sl) — KHÔNG được giữ nguyên "Số lượng" GỐC (trước khi tách) cho cả
2 dòng, dù "Thành tiền" (tt) đã tách đúng tỉ lệ từ trước.

Đúng ca thật người dùng báo cáo (kèm ảnh chụp file kết xuất): hóa đơn
"Chậu nhựa-Polystone planter, D36xH20 cm - LIGHT GREY (Kích thước:D36xH20
cm), hàng mới 100%, xuất xứ Việt Nam#&VN" bán 144 cái, chỉ đủ tồn gán 138
cái cho 1 mã, còn thiếu 6 cái phải tách dòng riêng — nhưng CẢ 2 dòng
(dòng đã gán 138 lẫn dòng còn thiếu 6) đều hiện "Số lượng" = 144 (giữ
nguyên số gốc), khiến tổng "Số lượng" cộng dồn ra 288 (gấp đôi số thật đã
bán), trong khi cột "Thành tiền" đã đúng theo tỉ lệ (44.536.768 và
1.936.381 — khớp đúng 138 và 6 cái)."""
import sys
sys.path.insert(0, _REPO_ROOT)
import server


ten_sp = ("Chậu nhựa-Polystone planter, D36xH20 cm - LIGHT GREY (Kích thước:D36xH20 cm), hàng mới 100%, "
          "xuất xứ Việt Nam#&VN")
ton_rows = [{"ma": "TPVT00100", "ten": "Chậu Polystone D36xH20 cm - Light Grey", "dvt": "Cái",
             "ton": 138, "gia": 322730}]
# Dòng nguồn CHƯA có mã (giống dữ liệu thật trước khi bấm "Dò mã hàng tự động").
giathanh_cu = [{
    "sohd": "308550168530", "ngay": "20/05/2026", "ten_sp": ten_sp, "dvt": "PCE",
    "sl": 144, "dgia": 322730, "tt": 46473120,
    "ma": "", "ten_xk": "", "dvt_xk": "", "sl_kho": None, "gia_xk": None,
}]

out = server._xk_gan_ma_truc_tiep(ton_rows, giathanh_cu, {})
print("Kết quả tách dòng:")
for r in out:
    print(f"  sl={r.get('sl')}, sl_kho={r.get('sl_kho')}, ma={r.get('ma')!r}, tt={r.get('tt')}")

assert len(out) == 2, f"Phải tách đúng thành 2 dòng (đã gán + còn thiếu) — được {len(out)} dòng: {out}"
dong_da_gan = next(r for r in out if r.get("ma"))
dong_thieu = next(r for r in out if not r.get("ma"))

assert dong_da_gan["sl"] == 138, (
    f"Dòng ĐÃ GÁN mã (đủ tồn 138) PHẢI hiện 'Số lượng' = 138 (KHÔNG phải 144 gốc) — "
    f"được sl={dong_da_gan['sl']}")
assert dong_da_gan["sl_kho"] == 138
assert dong_thieu["sl"] == 6, (
    f"Dòng CÒN THIẾU (chưa gán mã) PHẢI hiện 'Số lượng' = 6 (144-138, số CÒN LẠI thật sự), KHÔNG phải "
    f"144 gốc — được sl={dong_thieu['sl']}")

tong_sl = sum(r["sl"] for r in out)
assert tong_sl == 144, (
    f"Tổng 'Số lượng' cộng dồn cả 2 dòng tách PHẢI đúng bằng 144 (số lượng gốc đã bán), KHÔNG được ra "
    f"288 (144+144, đúng lỗi thật đã báo cáo) — được tổng={tong_sl}")
print(f"\nPASS: tách dòng ghi đúng 'Số lượng' còn lại cho từng dòng con (138 + 6 = 144), "
      f"không còn giữ nguyên 144 ở cả 2 dòng gây tổng sai gấp đôi.")
print("\nTẤT CẢ TEST PASS")
