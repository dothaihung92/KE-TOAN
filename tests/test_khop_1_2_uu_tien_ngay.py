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


# Kịch bản Y HỆT sổ cái 331 thật của COCOBETE (file CHI_TIET_CONG_NO_PHAI_TRA.xlsx):
# - Hóa đơn NK...-5 ngày 23/10/2025, 7.875.000đ
# - Hóa đơn NK...-6 ngày 30/10/2025, 7.875.000đ (TRÙNG giá trị hóa đơn trên)
# - 1 khoản chuyển khoản ngân hàng ngày 25/10/2025, 7.875.000đ
# Thực tế (đã xác nhận qua sổ cái MISA thật): khoản CK 25/10 trả cho hóa đơn
# 23/10 (đã tồn tại trước ngày trả); hóa đơn 30/10 (xuất SAU ngày CK, chỉ lọt
# vào ứng viên nhờ độ nới "cho thanh toán trước ngày HĐ" mặc định 7 ngày,
# 30/10 - 7 = 23/10 <= 25/10) được người dùng cho biết đã trả RIÊNG bằng
# chuyển khoản cá nhân, không nằm trong sao kê ngân hàng công ty -> KHÔNG
# được là ứng viên khớp ở đây.
hd_23 = hd("HD210", datetime.datetime(2025, 10, 23), 7875000)
hd_30 = hd("HD234", datetime.datetime(2025, 10, 30), 7875000)
tt_25 = tt(datetime.datetime(2025, 10, 25), 7875000)

doi_tuong_hd = {"ao-1": {"ma": "0317826028", "ten": "CÔNG TY TNHH SX TM XNK COCOBETE", "hoa_don": [hd_23, hd_30]}}
doi_tuong_tt = {"ao-1": [tt_25]}

tang1, tang2, khong_ro, tam_ung = _misa_khop_1_2(doi_tuong_hd, doi_tuong_tt)

assert not khong_ro, f"Không được còn 'không rõ' — đã có đúng 1 ứng viên hợp lệ theo thứ tự ngày: {khong_ro}"
assert len(tang1) == 1, f"Phải khớp Tầng 1 đúng 1 hóa đơn — got {tang1}"
assert tang1[0]["inv_no"] == "HD210", f"Phải khớp đúng hóa đơn ĐÃ TỒN TẠI trước ngày thanh toán (HD210, 23/10), " \
    f"KHÔNG phải hóa đơn xuất SAU (HD234, 30/10) — got {tang1[0]['inv_no']}"
assert hd_23["matched"] is True
assert hd_30["matched"] is False, "Hóa đơn 30/10 (trả bằng kênh khác, ngoài sao kê NH) phải vẫn treo, KHÔNG bị khớp nhầm."
assert tt_25["matched"] is True

print("PASS: khoản CK 25/10 (7.875.000đ) khớp ĐÚNG hóa đơn 23/10 (đã tồn tại trước ngày trả), "
      "KHÔNG còn báo 'Nhiều hóa đơn trùng giá trị' dù có 2 hóa đơn cùng giá trị.")
print("PASS: hóa đơn 30/10 (xuất SAU ngày CK, thực trả bằng kênh khác ngoài sao kê NH) "
      "vẫn treo lại (matched=False) để rơi đúng vào Tầng 3, không bị gán nhầm.")

# ── Trường hợp NGƯỢC LẠI: cả 2 hóa đơn trùng giá trị đều xuất SAU ngày TT
# (chỉ lọt vào nhờ độ nới) — vẫn phải báo "không rõ" như cũ (không có ứng
# viên "bình thường" nào để ưu tiên, không đoán bừa).
hd_a = hd("HDA", datetime.datetime(2025, 10, 27), 5000000)
hd_b = hd("HDB", datetime.datetime(2025, 10, 29), 5000000)
tt_2 = tt(datetime.datetime(2025, 10, 25), 5000000)
doi_tuong_hd2 = {"ao-2": {"ma": "X", "ten": "X", "hoa_don": [hd_a, hd_b]}}
doi_tuong_tt2 = {"ao-2": [tt_2]}
tang1b, tang2b, khong_rob, tam_ungb = _misa_khop_1_2(doi_tuong_hd2, doi_tuong_tt2)
assert len(khong_rob) == 1 and "cả hóa đơn" in khong_rob[0]["loai_vuong"], khong_rob
assert not tang1b, tang1b
print("PASS: khi CẢ 2 ứng viên đều xuất SAU ngày thanh toán (không có ứng viên 'bình thường' nào) "
      "vẫn báo đúng 'không rõ' như cũ, không đoán bừa.")

print("\nALL DONE")
