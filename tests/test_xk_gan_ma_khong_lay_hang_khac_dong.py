import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server as s

# Dò mã hàng: KHÔNG được gắn sang HÀNG KHÁC chỉ vì trùng kích thước (COMFORT -> VENUS cùng 200X160X23, ĐI VĂNG -> NB EVITA
# cùng 200X160X28, 'BỘ GA ... (Gồm ... vỏ gối 50x70cm ...)' -> 'Vỏ gối 50x70'), kể cả khi "mã đã học" (hoc_ma) từ lần gán SAI cũ
# chỉ vào hàng khác, và kể cả khi hàng đúng HẾT tồn (phải để trống phần thiếu, không lấy hàng khác bù). Dữ liệu giả.
def t(ma, ten, ton, gia=1000, dau_ky=0):
    return {"ma": ma, "ten": ten, "dvt": "PCS", "ton": ton, "gia": gia, "dau_ky": dau_ky}
TON = [t("MH35", "NỆM DUN COMFORT STE IPS 200X160X23", 3), t("MH06", "NỆM DUN VENUS SUPREME (N) 200X160X23", 6),
       t("HH26", "NỆM DUN VENUS SUPREME (N) 200X160X23CM", 15), t("MH10", "ĐI VĂNG DUN W/FABR. BRAGA8(N)200X160X28", 3),
       t("MH18", "NỆM DUN NB EVITA (N) 200X160X28", 3),
       t("HH104", "Bộ ga 1.8mx2m (Gồm: 1 ga 1.8mx2m, 2 vỏ gối 50x70cm, 1 vỏ chăn 2.2mx2m, 1 ruột chăn 2.2mx2m)", 2),
       t("MH82", "Vỏ gối 50x70", 36), t("HH109", "NỆM DUN LW NEO FRESH 220X200X15CM VN", 1),
       t("HH111", "GỐI DUN NEO TS COMF LTX CT60X40X12.5 VN", 16)]
HOC = {s._chuan_ten_hang_xk("NỆM DUN COMFORT STE IPS 200X160X23CM"): "MH06", s._chuan_ten_hang_xk("ĐI VĂNG DUN W/FABR. BRAGA8 200X160X28CM"): "MH18",
       s._chuan_ten_hang_xk("BỘ GA 1.8mx2m (Gồm: 1 Ga1.8mx2m, 2 vỏ gối 50x70cm, 1 vỏ chăn 2.2mx2m, 1 ruột chăn 2.2mx2m)"): "MH82"}
def dong(ten, sl, ma=""):
    return {"sohd": "1", "ngay": "01/07/2026", "ten_sp": ten, "dvt": "CÁI", "sl": sl, "dgia": 100, "tt": 100 * sl, "ma": ma, "ten_xk": "", "dvt_xk": "", "sl_kho": "", "gia_xk": ""}
BAN = [dong("NỆM DUN COMFORT STE IPS 200X160X23CM", 4), dong("ĐI VĂNG DUN W/FABR. BRAGA8 200X160X28CM", 1),
       dong("BỘ GA 1.8mx2m (Gồm: 1 Ga1.8mx2m, 2 vỏ gối 50x70cm, 1 vỏ chăn 2.2mx2m, 1 ruột chăn 2.2mx2m)", 2),
       dong("NỆM DUN VENUS SUPREME 200X160X23CM", 2), dong("NỆM DUN LW NEO FRESH 200X220X15CM", 1),
       dong("GỐI DUN NEO TS COMF LTX CT 60X40X12.5CM", 2)]

def chay(ban):
    out = s._xk_gan_ma_truc_tiep([dict(x) for x in TON], [dict(x) for x in ban], dict(HOC))
    kq = {}
    for r in out:
        kq.setdefault(r["ten_sp"], []).append((r.get("ma") or "", r.get("sl_kho") if r.get("sl_kho") not in (None, "") else r.get("sl")))
    return out, kq

out, kq = chay(BAN)
assert kq["NỆM DUN COMFORT STE IPS 200X160X23CM"] == [("MH35", 3), ("", 1)], kq          # hết tồn COMFORT: 1 cái để trống, KHÔNG lấy VENUS bù
assert kq["ĐI VĂNG DUN W/FABR. BRAGA8 200X160X28CM"] == [("MH10", 1)], kq                # mã đã học MH18 (NB EVITA) bị bỏ qua
assert kq["BỘ GA 1.8mx2m (Gồm: 1 Ga1.8mx2m, 2 vỏ gối 50x70cm, 1 vỏ chăn 2.2mx2m, 1 ruột chăn 2.2mx2m)"] == [("HH104", 2)], kq
assert kq["NỆM DUN VENUS SUPREME 200X160X23CM"][0][0] in ("MH06", "HH26"), kq
print("PASS 1: không gắn sang hàng khác cùng kích thước, kể cả mã đã học sai / hàng đúng hết tồn.")

assert kq["NỆM DUN LW NEO FRESH 200X220X15CM"] == [("HH109", 1)], kq                    # kích thước đảo chiều 200X220 = 220X200
assert kq["GỐI DUN NEO TS COMF LTX CT 60X40X12.5CM"] == [("HH111", 2)], kq             # chỉ khác đuôi 'CM'/'VN'
print("PASS 2: nhận kích thước ghi đảo chiều và tên chỉ khác đuôi CM/VN.")

# dữ liệu ĐANG CÓ mã sai từ lần dò lỗi trước (COMFORT gắn MH06 VENUS) -> bấm Dò mã lại tự sửa
out2, kq2 = chay([dong("NỆM DUN COMFORT STE IPS 200X160X23CM", 2, ma="MH06"), dong("ĐI VĂNG DUN W/FABR. BRAGA8 200X160X28CM", 1, ma="MH18"),
                  dong("BỘ GA 1.8mx2m (Gồm: 1 Ga1.8mx2m, 2 vỏ gối 50x70cm, 1 vỏ chăn 2.2mx2m, 1 ruột chăn 2.2mx2m)", 1, ma="MH82")])
assert kq2["NỆM DUN COMFORT STE IPS 200X160X23CM"] == [("MH35", 2)] and kq2["ĐI VĂNG DUN W/FABR. BRAGA8 200X160X28CM"] == [("MH10", 1)], kq2
assert kq2["BỘ GA 1.8mx2m (Gồm: 1 Ga1.8mx2m, 2 vỏ gối 50x70cm, 1 vỏ chăn 2.2mx2m, 1 ruột chăn 2.2mx2m)"] == [("HH104", 1)], kq2
assert not s._xk_kiem_tra_vuot_ton(TON, out2) and not s._xk_kiem_tra_vuot_ton(TON, out)
print("PASS 3: mã sai đang có (khác dòng sản phẩm) được tự dò lại đúng hàng; không vượt tồn.")

# mã gán tay cố ý khác tên nhưng gần giống (bán 'Bộ ga 1.8mx2m' xuất kho theo món lẻ 'Ga 1.8mx2m') -> giữ nguyên
TON.append(t("MH78", "Ga 1.8mx2m", 11))
out3, kq3 = chay([dong("Ga 1.8mx2m bộ", 1, ma="MH78")])
assert kq3["Ga 1.8mx2m bộ"] == [("MH78", 1)], kq3
print("PASS 4: mã gán tay gần đúng tên vẫn được giữ.")
