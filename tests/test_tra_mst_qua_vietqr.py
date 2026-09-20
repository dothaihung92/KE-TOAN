import os
import re

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test — người dùng hỏi tiếp "hãy kiểm tra ngoài trang
# tracuunnt.gdt.gov.vn còn trang nào cung cấp api tra thông tin mst không",
# rồi xác nhận dùng api.vietqr.io (dán JSON thật GET .../v2/business/{mst}):
#   {"code":"00","desc":"Success - Thành công",
#    "data":{"id":"0315458241","name":"...","status":"NNT đang hoạt động"},
#    "metadata":{"disclaimer":"... 11 ngày trước","source":"gdt.gov.vn",...}}
# Nguồn này KHÔNG cần captcha/đăng nhập -> không phụ thuộc ddddocr có nạp
# được trên máy hay không (vấn đề đang vướng ở tracuunnt.gdt.gov.vn) -> đặt
# làm nguồn ưu tiên CAO NHẤT, trước cả tracuunnt.gdt.gov.vn.


def _than_ham(ten):
    i = src.index('def ' + ten + '(')
    j = src.index('\ndef ', i + 10)
    return src[i:j]


def _nap(*ten_ham):
    ns = {'threading': __import__('threading'), 'requests': None}
    exec('import unicodedata, re, json', ns)
    for t in ten_ham:
        exec(_than_ham(t), ns)
    m = re.search(r'^_VIETQR_STATE\s*=\s*\{.*\}', src, re.M)
    exec(m.group(0), ns)
    m2 = re.search(r'^_VIETQR_NGUONG_TAT\s*=\s*\d+', src, re.M)
    exec(m2.group(0), ns)
    return ns


class _FakeResp:
    def __init__(self, status_code, data=None, la_json=True):
        self.status_code = status_code
        self._data = data
        self._la_json = la_json

    def json(self):
        if not self._la_json:
            raise ValueError("not json")
        return self._data


class _FakeRequests:
    def __init__(self, fn):
        self._fn = fn

    def get(self, url, timeout=None):
        return self._fn(url, timeout)


# ===== Test 1 (QUAN TRỌNG — đúng ĐÚNG JSON THẬT người dùng dán): phải đọc
# đúng data.status làm trang_thai_goc, và phân loại đúng "NNT đang hoạt động"
# là KHÔNG cảnh báo. =====
ns = _nap('_khong_dau', '_phan_loai_trang_thai_mst', '_vietqr_danh_dau', '_tra_cuu_mst_qua_vietqr')
fn = ns['_tra_cuu_mst_qua_vietqr']

JSON_MAU_THAT = {
    "code": "00", "desc": "Success - Thành công",
    "data": {"id": "0315458241", "name": "CÔNG TY TNHH THƯƠNG MẠI DỊCH VỤ KINH DOANH PHỤ TÙNG Ô TÔ ANH KHÔI",
             "internationalName": None, "shortName": None,
             "address": "27J5 Đường DN12, Khu Phố 4, Khu dân cư An Sương, Phường Đông Hưng Thuận, TP Hồ Chí Minh",
             "status": "NNT đang hoạt động"},
    "metadata": {"disclaimer": "Dữ liệu tổng hợp từ Trang thông tin điện tử của Cục Thuế 11 ngày trước",
                 "source": "https://www.gdt.gov.vn", "updatedAt": "2026-09-09T11:39:11.000Z",
                 "contact": "idkit@cas.so"}
}

ns['requests'] = _FakeRequests(lambda url, timeout: (
    _FakeResp(200, JSON_MAU_THAT) if url == "https://api.vietqr.io/v2/business/0315458241"
    else (_ for _ in ()).throw(AssertionError("URL sai: " + url))
))
r1 = fn("0315458241", 20)
assert r1 == (True, "NNT đang hoạt động", False, None), f"Phải đọc đúng JSON thật, got {r1}"
print("PASS 1: đọc đúng JSON thật người dùng gửi, dò ra 'NNT đang hoạt động' và phân loại KHÔNG cảnh báo.")

# ===== Test 2 (đúng ca thật — MST bị cảnh báo): status ghi tình trạng xấu
# thì phải cảnh báo (tô đỏ), không suy đoán "bình thường". =====
json_khoa = {**JSON_MAU_THAT, "data": {**JSON_MAU_THAT["data"], "status": "NNT đã bị khóa mã số thuế"}}
ns['requests'] = _FakeRequests(lambda url, timeout: _FakeResp(200, json_khoa))
r2 = fn("0315458241", 20)
assert r2[0] is True and r2[2] is True, f"MST đã khoá phải ra canh_bao=True, got {r2}"
print("PASS 2: MST có tình trạng xấu (đã khoá MST) được nhận diện đúng là CẢNH BÁO.")

# ===== Test 3 (AN TOÀN — không suy đoán): code != "00", HTTP lỗi, JSON hỏng,
# thiếu status, hoặc status lạ chưa nhận diện -> đều phải trả THẤT BẠI (để
# rơi xuống nguồn sau), tuyệt đối không suy đoán "đang hoạt động". =====
ns['requests'] = _FakeRequests(lambda url, timeout: _FakeResp(200, {"code": "01", "desc": "Not found"}))
assert fn("0000000000", 20)[0] is False, "code != '00' phải trả thất bại."

ns['requests'] = _FakeRequests(lambda url, timeout: _FakeResp(404))
assert fn("0000000000", 20)[0] is False, "HTTP khác 200 phải trả thất bại."

ns['requests'] = _FakeRequests(lambda url, timeout: _FakeResp(200, la_json=False))
assert fn("0000000000", 20)[0] is False, "JSON hỏng phải trả thất bại, không văng lỗi."

ns['requests'] = _FakeRequests(lambda url, timeout: _FakeResp(200, {"code": "00", "data": {"id": "x", "status": ""}}))
assert fn("0000000000", 20)[0] is False, "Thiếu trường status phải trả thất bại."

ns['requests'] = _FakeRequests(lambda url, timeout: _FakeResp(200, {"code": "00", "data": {"status": "Tình trạng lạ chưa từng thấy"}}))
r_la = fn("0000000000", 20)
assert r_la[0] is False and r_la[2] is None, f"Tình trạng lạ (không khớp từ khoá nào) phải trả thất bại, canh_bao=None (không suy đoán), got {r_la}"

def _nem_loi(url, timeout):
    raise ConnectionError("mất mạng")
ns['requests'] = _FakeRequests(_nem_loi)
assert fn("0000000000", 20)[0] is False, "Lỗi kết nối phải trả thất bại, không văng exception ra ngoài."
print("PASS 3: mọi trường hợp lỗi/dữ liệu bất thường đều trả thất bại an toàn, không suy đoán 'đang hoạt động'.")

# ===== Test 4 (đúng ca thật — tránh lãng phí lượt gọi hàng loạt): phải có
# ngưỡng tạm tắt khi lỗi liên tiếp, giống cơ chế đã áp dụng cho tracuunnt. =====
than_vietqr = _than_ham('_tra_cuu_mst_qua_vietqr')
assert '_VIETQR_NGUONG_TAT' in src and '_vietqr_danh_dau(' in than_vietqr, (
    "Phải có bộ đếm lỗi liên tiếp + ngưỡng tạm tắt nguồn này trong 1 lượt xuất Excel.")
print("PASS 4: có ngưỡng tạm tắt khi lỗi liên tiếp, tránh lãng phí lượt gọi cho hàng trăm MST còn lại.")

# ===== Test 5 (QUAN TRỌNG — đúng yêu cầu thứ tự ưu tiên): api.vietqr.io phải
# được thử TRƯỚC tracuunnt.gdt.gov.vn (và cả XInvoice/masothue) — vì KHÔNG
# phụ thuộc ddddocr, nhanh/chắc chắn hơn hẳn nguồn cần giải captcha. =====
than_chinh = _than_ham('_tra_cuu_trang_thai_mst')
vt_vietqr = than_chinh.find('_tra_cuu_mst_qua_vietqr(')
vt_tracuunnt = than_chinh.find('_tra_cuu_mst_qua_tracuunnt(')
vt_xinvoice = than_chinh.find('_goi_1_lan_xinvoice(')
vt_masothue = than_chinh.find('_tra_cuu_masothue(')
assert 0 < vt_vietqr < vt_tracuunnt < vt_xinvoice < vt_masothue, (
    "Thứ tự ưu tiên phải là: api.vietqr.io (không captcha) -> tracuunnt.gdt.gov.vn -> XInvoice -> masothue.com.")
assert 'if not thanh_cong:' in than_chinh[vt_tracuunnt - 200:vt_tracuunnt], (
    "Chỉ thử tracuunnt.gdt.gov.vn khi VietQR đã THẤT BẠI (thanh_cong=False) — tra được ở VietQR rồi thì "
    "không cần thử thêm nguồn khác, tránh lãng phí gọi mạng/giải captcha vô ích.")
print("PASS 5: api.vietqr.io được thử TRƯỚC tracuunnt.gdt.gov.vn/XInvoice/masothue.com, chỉ rơi xuống khi VietQR thất bại.")

# ===== Test 6 (không hồi quy — thông báo lỗi cuối gộp đủ cả 4 nguồn): thiếu
# lý do của 1 nguồn sẽ khiến người dùng chẩn đoán "cụt", không biết nguồn đó
# có được thử hay không. =====
assert 'api.vietqr.io: {ly_do_loi_vietqr}' in src, (
    "Thông báo lỗi cuối cùng (khi cả 4 nguồn đều thất bại) phải kèm lý do của api.vietqr.io.")
print("PASS 6: thông báo lỗi cuối cùng gộp đủ lý do của cả 4 nguồn (VietQR + tracuunnt + XInvoice + masothue.com).")

# ===== Test 7 (không hồi quy — endpoint chẩn đoán riêng): phải có endpoint
# chẩn đoán nhanh cho VietQR, không cần biết id công ty nào (API công khai). =====
assert '/api/chan-doan-mst-vietqr' in src and 'def chan_doan_mst_vietqr' in src, (
    "Phải có endpoint chẩn đoán riêng cho api.vietqr.io.")
than_cd = _than_ham('chan_doan_mst_vietqr')
assert '_tra_cuu_mst_qua_vietqr(' in than_cd, "Endpoint chẩn đoán phải gọi đúng hàm tra cứu thật (không phải mô phỏng riêng)."
print("PASS 7: có endpoint chẩn đoán riêng /api/chan-doan-mst-vietqr, không cần biết id công ty nào.")

print("\nALL DONE")
