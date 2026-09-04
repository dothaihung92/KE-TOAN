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


# Kịch bản Y HỆT "Chi tiết công nợ phải thu" thật của KH MOV:
#   BH008 (17/10/2025, 4.620.000đ) và BH006 (25/10/2025, 4.620.000đ) — 2 hóa
#   đơn TRÙNG GIÁ TRỊ. 3 khoản tiền về: cọc 16/10 (2.000.000đ, TRƯỚC cả 2 hóa
#   đơn), 04/11 (2.620.000đ, "đợt cuối"), 18/11 (4.620.000đ, đúng bằng CẢ 2
#   hóa đơn nên gây "không rõ" ở Tầng 1). Thực tế đúng: BH008 khớp THẲNG với
#   khoản 18/11 (đúng số tiền, không cần tổ hợp); BH006 khớp bằng tổ hợp cọc
#   16/10 + 04/11 (2.000.000 + 2.620.000 = 4.620.000).
bh008 = hd("BH008", datetime.datetime(2025, 10, 17), 4620000)
bh006 = hd("BH006", datetime.datetime(2025, 10, 25), 4620000)
coc = tt(datetime.datetime(2025, 10, 16), 2000000)
dot_cuoi = tt(datetime.datetime(2025, 11, 4), 2620000)
tt_1811 = tt(datetime.datetime(2025, 11, 18), 4620000)

doi_tuong_hd = {"ao-mov": {"ma": "MOV", "ten": "CÔNG TY CỔ PHẦN TRUYỀN THÔNG MOV",
                           "hoa_don": [bh008, bh006]}}
doi_tuong_tt = {"ao-mov": [coc, dot_cuoi, tt_1811]}

tang1, tang2, khong_ro, tam_ung = _misa_khop_1_2(doi_tuong_hd, doi_tuong_tt)

assert bh008["matched"] is True, "BH008 phải khớp được (18/11 đúng số tiền)"
assert bh006["matched"] is True, (
    "BUG: BH006 ĐÃ được trả đủ (cọc 16/10 + đợt cuối 04/11 = 4.620.000đ, đúng "
    "sổ cái thật) nhưng KHÔNG được ghi nhận là đã khớp — sẽ bị đề xuất tạo "
    "'Điều chỉnh công nợ treo' NHẦM dù công nợ đã về 0.")
assert not khong_ro, f"Không được còn 'không rõ' sau khi trạng thái đã ổn định — {khong_ro}"
assert coc["matched"] and dot_cuoi["matched"] and tt_1811["matched"]

# Xác nhận CẢ 2 hóa đơn đều khớp (1 hóa đơn khớp thẳng Tầng 1 với khoản
# 18/11, hóa đơn còn lại khớp qua Tầng 2c hoặc Tầng 2b/tạm ứng bằng tổ hợp
# cọc+đợt cuối — 2 hóa đơn CÙNG giá trị nên phần mềm gán bên nào cho khoản
# nào/qua cơ chế nào không quan trọng, miễn là CẢ 2 đều khớp xong).
matched_invs = ({x["inv_no"] for x in tang1} | {h["inv_no"] for x in tang2 for h in x["hoa_don"]}
               | {h["inv_no"] for x in tam_ung for h in x["hoa_don"]})
assert matched_invs == {"BH008", "BH006"}, f"Cả 2 hóa đơn phải khớp xong — got {matched_invs}"
tong_da_khop = (sum(x["so_tien"] for x in tang1) + sum(h["so_tien"] for x in tang2 for h in x["hoa_don"])
               + sum(h["so_tien"] for x in tam_ung for h in x["hoa_don"]))
assert tong_da_khop == 9240000, f"Tổng đã khớp phải đúng bằng tổng 2 hóa đơn (9.240.000đ) — got {tong_da_khop}"

print(f"PASS: cả 2 hóa đơn BH008/BH006 (cùng giá trị 4.620.000đ) đều khớp xong hết — "
      f"1 hóa đơn khớp thẳng Tầng 1 (khoản 18/11), hóa đơn còn lại khớp Tầng 2c bằng tổ hợp "
      f"cọc 16/10 + đợt cuối 04/11 — sau khi lượt trước giải quyết xong 1 bên, lượt sau tự "
      f"giải tỏa hết mơ hồ cho bên còn lại (fix vòng lặp tới điểm ổn định, đúng bài học từ "
      f"báo cáo Chi tiết công nợ phải thu KH MOV, KHÔNG còn 'không rõ' hay bỏ sót nữa).")

print("\nALL DONE")
