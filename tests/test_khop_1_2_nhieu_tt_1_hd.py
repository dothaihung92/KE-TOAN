import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import datetime, itertools
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

def extract_fn(name):
    idx = src.index('def ' + name + '(')
    i = src.index(':', idx)
    lines = src[i+1:].split('\n')
    body = []
    started = False
    for ln in lines:
        if ln.strip() == '' and not started:
            body.append(ln); continue
        if ln and not ln[0].isspace() and started:
            break
        if ln.strip():
            started = True
        body.append(ln)
    return src[idx:i+1] + '\n'.join(body)


ns = {'datetime': datetime, 'itertools': itertools}
for fn in ("_misa_ngay_str", "_misa_khop_1_2"):
    exec(extract_fn(fn), ns)
_misa_khop_1_2 = ns['_misa_khop_1_2']


def hd(inv_no, inv_date, so_tien):
    return {"inv_no": inv_no, "inv_date": inv_date, "so_tien": so_tien, "gt": 0.0, "vat": 0.0}


def tt(date, so_tien):
    return {"date": date, "so_tien": so_tien}


# Kịch bản Y HỆT sổ cái 331 thật của COCOBETE (Chi tiết công nợ phải trả):
# HĐ 393, ngày 17/12/2025, 18.900.000đ — được trả bằng 2 UNC RIÊNG BIỆT:
#   18/12/2025: 10.000.000đ, 22/12/2025: 8.900.000đ (không khoản nào khớp
#   riêng lẻ, chỉ TỔNG 2 khoản mới đúng bằng hóa đơn).
hd_393 = hd("393", datetime.datetime(2025, 12, 17), 18900000)
tt_1 = tt(datetime.datetime(2025, 12, 18), 10000000)
tt_2 = tt(datetime.datetime(2025, 12, 22), 8900000)

doi_tuong_hd = {"ao-1": {"ma": "0317826028", "ten": "CÔNG TY TNHH SX TM XNK COCOBETE", "hoa_don": [hd_393]}}
doi_tuong_tt = {"ao-1": [tt_1, tt_2]}

tang1, tang2, khong_ro, tam_ung = _misa_khop_1_2(doi_tuong_hd, doi_tuong_tt)

assert not khong_ro, f"Không được còn 'không rõ' — có đúng 1 tổ hợp 2 khoản TT khớp đúng: {khong_ro}"
assert not tang1, f"HĐ 393 không khớp 1-1 với khoản nào (không khoản nào bằng 18.900.000đ) — tang1={tang1}"
assert len(tang2) == 1, f"Phải khớp đúng 1 hóa đơn ở Tầng 2 (chiều 'nhiều TT -> 1 HĐ') — got {tang2}"
g = tang2[0]
assert g["hoa_don"] == [{"inv_no": "393", "inv_date": "2025-12-17", "so_tien": 18900000}], g
assert g["so_tien"] == 18900000, g
assert g["lech"] == 0, g
assert hd_393["matched"] is True
assert tt_1["matched"] is True and tt_2["matched"] is True

print("PASS: HĐ 393 (18.900.000đ) khớp ĐÚNG với TỔ HỢP 2 khoản thanh toán riêng biệt "
      f"(18/12 10tr + 22/12 8.9tr) — ngay_thanh_toan='{g['ngay_thanh_toan']}', không còn báo 'treo' nữa.")

# ── Trường hợp NGƯỢC LẠI: chỉ 1 khoản thanh toán trùng NGẪU NHIÊN 1 phần —
# không đủ 2 khoản cộng đúng -> hóa đơn vẫn phải treo bình thường (không suy
# rộng quá tay khi thật sự chưa trả đủ).
hd_x = hd("X01", datetime.datetime(2025, 12, 17), 18900000)
tt_x = tt(datetime.datetime(2025, 12, 18), 10000000)
doi_tuong_hd2 = {"ao-2": {"ma": "Y", "ten": "Y", "hoa_don": [hd_x]}}
doi_tuong_tt2 = {"ao-2": [tt_x]}
tang1b, tang2b, khong_rob, tam_ungb = _misa_khop_1_2(doi_tuong_hd2, doi_tuong_tt2)
assert not tang2b and not khong_rob, f"Chỉ có 1 khoản TT (không đủ tổ hợp) không được tự khớp — {tang2b}, {khong_rob}"
assert hd_x["matched"] is False
print("PASS: hóa đơn thật sự CHƯA trả đủ (chỉ có 1 khoản TT lẻ, không đủ tổ hợp) vẫn đúng chưa khớp, "
      "không suy rộng quá tay.")

print("\nALL DONE")
