import datetime
import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test cho _misa_khop_1_2()/_hd_so_trong_mo_ta() trong server.py — người dùng báo:
# "kiểm tra lại đối chiếu công nợ sao phần mềm lại điều chỉnh công nợ Điều chỉnh công nợ treo HĐ
# 5947 - CÔNG TY CỔ PHẦN THƯƠNG MẠI SATORI ở trên đã ck thanh toán hết rồi mà hãy kiểm tra lại".
#
# Dữ liệu tái hiện từ file CHI_TIET_CONG_NO_PHAI_TRA.xlsx người dùng gửi: HĐ 5947 (451.126đ,
# 19/03/2026) và HĐ 1906 (451.126đ, 30/01/2026, cùng giá trị) — HĐ 1906 được trả đúng cửa sổ ngày
# mặc định (khoản 24/02), còn HĐ 5947 được trả bằng khoản chuyển khoản 24/06/2026 (451.127đ, nội
# dung ghi rõ "tt hd nuoc 5947 - cty cp thuong mai satori") — nhưng 24/06 cách ngày hóa đơn
# 19/03/2026 tới ~97 ngày, NGOÀI cửa sổ mặc định cua_so_thang=3 (~90 ngày) của trong_cua_so(), nên
# trước khi sửa, HĐ 5947 rơi vào "chưa khớp" dù nội dung chuyển khoản đã ghi RÕ số hóa đơn -> bị
# Tầng 3 coi là "treo" và tạo bút toán "Điều chỉnh công nợ treo" SAI, dù thực tế đã thanh toán đủ.


def extract_fn(name):
    idx = src.index('def ' + name + '(')
    i = src.index(':', idx)
    lines = src[i + 1:].split('\n')
    body = []
    started = False
    for ln in lines:
        if ln.strip() == '' and not started:
            body.append(ln)
            continue
        if ln and not ln[0].isspace() and started:
            break
        if ln.strip():
            started = True
        body.append(ln)
    return src[idx:i + 1] + '\n'.join(body)


ns = {'datetime': datetime, 'itertools': __import__('itertools')}
exec(extract_fn('_misa_ngay_str'), ns)
exec(extract_fn('_hd_so_trong_mo_ta'), ns)
exec(extract_fn('_misa_khop_1_2'), ns)
_misa_khop_1_2 = ns['_misa_khop_1_2']
_hd_so_trong_mo_ta = ns['_hd_so_trong_mo_ta']


def _hd(ref_id, inv_no, ngay, so_tien):
    return {"ref_id": ref_id, "inv_no": inv_no, "inv_date": ngay, "so_tien": so_tien,
            "gt": round(so_tien / 1.1, 2), "vat": round(so_tien - so_tien / 1.1, 2)}


def _tt(ref_id, ngay, so_tien, mo_ta=""):
    return {"ref_id": ref_id, "date": ngay, "so_tien": so_tien, "nguon": "ngan_hang",
            "mo_ta": mo_ta, "so_ct": ""}


def lam_du_lieu_satori():
    doi_tuong_hd = {"AO1": {"ma": "SATORI", "ten": "CÔNG TY CỔ PHẦN THƯƠNG MẠI SATORI", "hoa_don": [
        _hd("r1906", "1906", datetime.datetime(2026, 1, 30), 451126.0),
        _hd("r5947", "5947", datetime.datetime(2026, 3, 19), 451126.0),
    ]}}
    doi_tuong_tt = {"AO1": [
        _tt("p1", datetime.datetime(2026, 1, 6), 951126.0, "chuyen tien"),
        _tt("p2", datetime.datetime(2026, 2, 24), 451126.0, "tt hang hoa dot 1"),
        _tt("p3", datetime.datetime(2026, 6, 24), 451127.0,
            "tt hd nuoc 5947 - cty cp thuong mai satori"),
    ]}
    return doi_tuong_hd, doi_tuong_tt


# ----- Test 1 (ca thật SATORI/HĐ 5947): thanh toán ghi RÕ số hóa đơn trong nội dung nhưng đến
# NGOÀI cửa sổ ngày mặc định (3 tháng) -> vẫn phải khớp đúng, không được rơi "chưa khớp"/"treo". -----
doi_tuong_hd, doi_tuong_tt = lam_du_lieu_satori()
tang1, tang2, khong_ro, tam_ung = _misa_khop_1_2(doi_tuong_hd, doi_tuong_tt)
hd5947 = doi_tuong_hd["AO1"]["hoa_don"][1]
assert hd5947["inv_no"] == "5947"
assert hd5947["matched"] is True, (
    "HĐ 5947 PHẢI được khớp nhờ nội dung chuyển khoản ghi rõ số hóa đơn, dù thanh toán đến "
    "ngoài cửa sổ ngày mặc định — hiện matched=%r (đây chính là bug 'Điều chỉnh công nợ treo' "
    "SAI mà người dùng báo)" % hd5947["matched"])
assert any(e["inv_no"] == "5947" and e["ngay_thanh_toan"] == "2026-06-24" for e in tang1), (
    "Phải có bản ghi khớp HĐ 5947 với đúng khoản thanh toán 24/06/2026 trong tang1 — got %r" % tang1)
print("PASS 1: HĐ 5947 (SATORI) được khớp đúng nhờ số hóa đơn ghi rõ trong nội dung chuyển khoản, dù ngoài cửa sổ ngày mặc định.")

# ----- Test 2 (không hồi quy): HĐ 1906 vẫn khớp đúng bình thường theo Tầng 1 (cửa sổ ngày), cùng
# giá trị với HĐ 5947 nhưng KHÔNG bị nhầm lẫn giữa 2 hóa đơn. -----
hd1906 = doi_tuong_hd["AO1"]["hoa_don"][0]
assert hd1906["matched"] is True, "HĐ 1906 phải khớp bình thường qua Tầng 1 (trong cửa sổ ngày)"
assert any(e["inv_no"] == "1906" and e["ngay_thanh_toan"] == "2026-02-24" for e in tang1), (
    "HĐ 1906 phải khớp đúng khoản thanh toán 24/02/2026 (không bị lẫn với khoản của HĐ 5947)")
print("PASS 2: HĐ 1906 (cùng giá trị với HĐ 5947) vẫn khớp đúng theo Tầng 1 bình thường, không bị lẫn.")

# ----- Test 3 (_hd_so_trong_mo_ta trực tiếp): các ca biên — số hóa đơn quá ngắn bị bỏ qua (tránh
# trùng ngẫu nhiên), số 0 đứng đầu không làm sai lệch, không có trong mô tả thì trả False. -----
assert _hd_so_trong_mo_ta("5947", "tt hd nuoc 5947 - cty abc") is True
assert _hd_so_trong_mo_ta("05947", "tt hd nuoc 5947 - cty abc") is True  # 0 dau khong lam sai lech
assert _hd_so_trong_mo_ta("5947", "tt hd nuoc 59473 - cty abc") is False  # dung ranh gioi so
assert _hd_so_trong_mo_ta("5947", "khong lien quan") is False
assert _hd_so_trong_mo_ta("12", "hd so 12 thanh toan") is False  # qua ngan (<3 chu so) -> bo qua
print("PASS 3: _hd_so_trong_mo_ta() nhận đúng ranh giới số hóa đơn, bỏ qua số quá ngắn tránh trùng ngẫu nhiên.")

# ----- Test 4 (không hồi quy/an toàn): thanh toán ghi số hóa đơn SAI nhưng số tiền cũng SAI lệch
# quá dung_sai -> KHÔNG được ép khớp bừa (vẫn phải đúng cả số hóa đơn LẪN số tiền gần đúng). -----
doi_tuong_hd2, doi_tuong_tt2 = lam_du_lieu_satori()
doi_tuong_tt2["AO1"][2]["so_tien"] = 200000.0  # lech qua xa so voi 451.126d cua HD 5947
tang1b, tang2b, khong_rob, tam_ungb = _misa_khop_1_2(doi_tuong_hd2, doi_tuong_tt2)
hd5947b = doi_tuong_hd2["AO1"]["hoa_don"][1]
assert hd5947b["matched"] is False, (
    "Nếu số tiền lệch quá xa (ngoài dung_sai) thì KHÔNG được khớp bừa dù mô tả có nhắc số hóa đơn")
print("PASS 4: không khớp bừa khi số tiền lệch quá xa dung_sai dù nội dung có nhắc đúng số hóa đơn.")

print("\nALL DONE")
