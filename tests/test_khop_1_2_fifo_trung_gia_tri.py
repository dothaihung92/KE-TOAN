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


# Theo yêu cầu người dùng: "hóa đơn trùng giá trị nhưng khác số là việc bình
# thường" — 3 hóa đơn CÙNG giá trị (mua lặp lại đều đặn), 3 khoản thanh toán
# CŨNG cùng giá trị, mỗi khoản đến SAU đúng 1 hóa đơn — phải tự khớp theo
# FIFO (hóa đơn CŨ NHẤT khớp khoản thanh toán tương ứng), KHÔNG còn báo
# "không rõ" nữa.
hd1 = hd("HD01", datetime.datetime(2025, 1, 5), 3000000)
hd2 = hd("HD02", datetime.datetime(2025, 2, 5), 3000000)
hd3 = hd("HD03", datetime.datetime(2025, 3, 5), 3000000)
tt1 = tt(datetime.datetime(2025, 1, 10), 3000000)
tt2 = tt(datetime.datetime(2025, 2, 10), 3000000)
tt3 = tt(datetime.datetime(2025, 3, 10), 3000000)

doi_tuong_hd = {"ao-x": {"ma": "X", "ten": "NCC LẶP LẠI HÀNG THÁNG", "hoa_don": [hd1, hd2, hd3]}}
doi_tuong_tt = {"ao-x": [tt1, tt2, tt3]}

tang1, tang2, khong_ro, tam_ung = _misa_khop_1_2(doi_tuong_hd, doi_tuong_tt)

assert not khong_ro, f"Hóa đơn trùng giá trị khác số là BÌNH THƯỜNG — không được báo 'không rõ' nữa: {khong_ro}"
assert len(tang1) == 3, f"Cả 3 hóa đơn phải tự khớp hết theo FIFO — got {tang1}"
by_inv = {x["inv_no"]: x for x in tang1}
assert by_inv["HD01"]["ngay_thanh_toan"] == "2025-01-10"
assert by_inv["HD02"]["ngay_thanh_toan"] == "2025-02-10"
assert by_inv["HD03"]["ngay_thanh_toan"] == "2025-03-10"
print("PASS: 3 hóa đơn trùng giá trị (khác số, mua lặp lại hàng tháng) tự khớp ĐÚNG theo thứ tự "
      "FIFO với 3 khoản thanh toán cùng giá trị — không còn bị báo 'không rõ' nữa (đúng yêu cầu: "
      "trùng giá trị khác số là chuyện bình thường).")

# ── Trường hợp SỐ LƯỢNG hóa đơn và thanh toán KHÔNG khớp nhau (2 hóa đơn
# trùng giá trị, nhưng chỉ có 1 khoản thanh toán) — FIFO chọn hóa đơn CŨ
# NHẤT, hóa đơn còn lại vẫn treo bình thường (không suy đoán bừa là ĐÃ trả
# nốt, chỉ 1 khoản thì chỉ trả được 1 hóa đơn).
hd_a = hd("HDA", datetime.datetime(2025, 5, 1), 2000000)
hd_b = hd("HDB", datetime.datetime(2025, 5, 15), 2000000)
tt_a = tt(datetime.datetime(2025, 5, 20), 2000000)
doi_tuong_hd2 = {"ao-y": {"ma": "Y", "ten": "Y", "hoa_don": [hd_a, hd_b]}}
doi_tuong_tt2 = {"ao-y": [tt_a]}
tang1b, tang2b, khong_rob, tam_ungb = _misa_khop_1_2(doi_tuong_hd2, doi_tuong_tt2)
assert not khong_rob, khong_rob
assert len(tang1b) == 1 and tang1b[0]["inv_no"] == "HDA", (
    f"Chỉ có 1 khoản thanh toán -> phải khớp hóa đơn CŨ NHẤT (HDA), hóa đơn kia (HDB) vẫn treo "
    f"chờ khoản khác — got {tang1b}")
assert hd_a["matched"] is True and hd_b["matched"] is False
print("PASS: 2 hóa đơn trùng giá trị nhưng chỉ 1 khoản thanh toán -> khớp ĐÚNG hóa đơn cũ nhất "
      "(FIFO), hóa đơn còn lại vẫn treo bình thường chờ khoản thanh toán khác — không đoán bừa "
      "là đã trả nốt.")

print("\nALL DONE")
