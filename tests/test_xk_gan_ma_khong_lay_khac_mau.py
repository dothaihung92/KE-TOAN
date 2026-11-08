import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Dò mã xuất kho: mã ĐÚNG màu hết tồn thì KHÔNG được lấy mã cùng kích thước KHÁC màu, và hàng lẻ không lấy mã BỘ.
# Ca thật (KetXuatGiaThanh 08/11/2026 + Tồn kho Q3/2026): 'D34xH30 - Matte White' -> 'D34xH30 - ORANGE', 'D35xH45 - Matte White'
# -> '... Matte Black', 'D31xH40 - Gloss Blue' -> '... GLOSS OLIVE', 'L80 ... Greystone' x65 ăn hết 'L80 ... SBW' làm dòng SBW thật
# bị trống, 'D22xH35 cm' (Cái) -> 'Bộ 3 D36/D29/D22'.
def ton(ma, ten, sl, dvt="Cái"):
    return {"ma": ma, "ten": ten, "dvt": dvt, "ton": sl, "gia": 100, "kho": "HH", "kho_ro": True, "ton_kho_min": sl, "dau_ky": sl}

T = [ton("MH18", "Chậu Polystone D34xH30 cm - ORANGE", 2), ton("MH316", "Chậu Polystone D35xH45 cm - Matte Black", 4),
     ton("MH152", "Chậu Polystone D31xH40 cm - GLOSS OLIVE", 2), ton("MH608", "Chậu Polystone D31xH40 cm - Gloss Blue", 4),
     ton("MH303", "Chậu Polystone L80xW30xH40 cm -  SBW", 80), ton("TPVT00096", "Chậu Polystone D22xH35 cm", 1),
     ton("MH01", "Chậu Polystone D36xH45 cm, D29xH40 cm, D22xH35 cm", 49, "Bộ 3"),
     ton("HH00026-8", "Chậu Polystone L70xW30xH40 - GS", 1), ton("MH19", "Chậu Polystone D36xH30 cm - CREAM", 1)]
gt = [{"sohd": "16", "ten_sp": t, "dvt": "Cái", "sl": n, "tt": n * 1000} for t, n in [
    ("Chậu Polystone D34xH30 cm - Matte White", 2), ("Chậu Polystone D35xH45 cm - Matte White", 3),
    ("Chậu Polystone D31xH40 cm - Gloss Blue", 6), ("Chậu Polystone L80xW30xH40 cm - Greystone", 65),
    ("Chậu Polystone L80xW30xH40 cm - SBW", 49), ("Chậu Polystone D22xH35 cm", 2),
    ("Chậu polystone L70xW30xH40 cm - Greystone", 1), ("Chậu Polystone D36xH30 cm - Gloss Cream", 1)]]
out = server._xk_gan_ma_truc_tiep(T, gt)
out = out[0] if isinstance(out, tuple) else out
ma = {}
for r in out:
    ma.setdefault(r["ten_sp"], []).append((r.get("ma") or "", r.get("sl_kho") or r.get("sl")))
assert all(m == "" for m, _ in ma["Chậu Polystone D34xH30 cm - Matte White"]), ma
assert all(m == "" for m, _ in ma["Chậu Polystone D35xH45 cm - Matte White"]), ma
assert {m for m, _ in ma["Chậu Polystone D31xH40 cm - Gloss Blue"]} == {"MH608", ""}, ma           # 4 đúng màu, 2 còn thiếu để trống
assert all(m == "" for m, _ in ma["Chậu Polystone L80xW30xH40 cm - Greystone"]), ma
assert ma["Chậu Polystone L80xW30xH40 cm - SBW"] == [("MH303", 49)], ma
assert {m for m, _ in ma["Chậu Polystone D22xH35 cm"]} == {"TPVT00096", ""}, ma                   # không lấy Bộ 3
assert ma["Chậu polystone L70xW30xH40 cm - Greystone"][0][0] == "HH00026-8", "Greystone = GS"
assert ma["Chậu Polystone D36xH30 cm - Gloss Cream"][0][0] == "MH19", "Gloss Cream = CREAM"
print("PASS: không gắn mã khác màu / mã bộ cho hàng lẻ; GS=Greystone, CREAM=Gloss Cream vẫn khớp.")
print("\nALL DONE")
