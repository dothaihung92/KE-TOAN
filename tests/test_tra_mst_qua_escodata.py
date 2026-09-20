import os
import re

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test — người dùng gửi tài liệu + JSON THẬT của API công khai
# escodata.net (GET https://escodata.net/api-mst/{mst}.htm, KHÔNG cần API
# key), chọn tích hợp làm nguồn DỰ PHÒNG THÊM (không thay thế nguồn nào),
# đặt ở giữa VietQR (ưu tiên 1) và XInvoice (dự phòng cuối, cần key/có thể
# hết hạn mức gói free tier):
#   {"error":0,"error_text":"...thành công..!",
#    "data":{"ten":"...","mst":"...","dc":"...","daidien":"...",
#            "tinhtrang":"Đang hoạt động (đã được cấp GCN ĐKT)",...}}
# Nguồn KHÔNG chính thức (như masothue.com/tracuunnt.gdt.gov.vn trước đây,
# đã bị BỎ vì "không đúng được") nên có circuit-breaker riêng để tự tạm tắt
# nếu gặp vấn đề tương tự khi gọi dồn dập.


def _than_ham(ten):
    i = src.index('def ' + ten + '(')
    j = src.index('\ndef ', i + 10)
    return src[i:j]


class _FakeTime:
    """Thay cho module time thật — ghi lại các lượt sleep() thay vì chờ
    thật, để test chạy nhanh dù _tra_cuu_mst_qua_escodata giờ nghỉ theo
    Retry-After khi gặp 429 tạm thời trước khi thử lại."""
    def __init__(self):
        self.sleeps = []

    def sleep(self, s):
        self.sleeps.append(s)


def _nap(*ten_ham):
    ns = {'threading': __import__('threading'), 'requests': None}
    exec('import unicodedata, re, json', ns)
    for t in ten_ham:
        exec(_than_ham(t), ns)
    m = re.search(r'^_ESCODATA_STATE\s*=\s*\{.*\}', src, re.M)
    exec(m.group(0), ns)
    m2 = re.search(r'^_ESCODATA_NGUONG_TAT\s*=\s*\d+', src, re.M)
    exec(m2.group(0), ns)
    ns['_fake_time'] = _FakeTime()
    ns['time'] = ns['_fake_time']
    return ns


class _FakeResp:
    def __init__(self, status_code, data=None, la_json=True, headers=None):
        self.status_code = status_code
        self._data = data
        self._la_json = la_json
        self.headers = headers or {}

    def json(self):
        if not self._la_json:
            raise ValueError("not json")
        return self._data


class _FakeRequests:
    def __init__(self, fn):
        self._fn = fn

    def get(self, url, timeout=None, headers=None):
        return self._fn(url, timeout)


class _FakeRequestsQueue:
    """Trả về LẦN LƯỢT các response trong hàng đợi theo từng lượt gọi — dùng
    để mô phỏng 429 rồi 200 ở lượt thử lại."""
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, timeout=None, headers=None):
        self.calls.append(url)
        return self.responses.pop(0)


# ===== Test 1 (QUAN TRỌNG — đúng ĐÚNG JSON THẬT người dùng dán): phải đọc
# đúng data.tinhtrang làm trang_thai_goc, và phân loại đúng "Đang hoạt động
# (đã được cấp GCN ĐKT)" là KHÔNG cảnh báo. =====
ns = _nap('_khong_dau', '_phan_loai_trang_thai_mst', '_escodata_danh_dau', '_tra_cuu_mst_qua_escodata')
fn = ns['_tra_cuu_mst_qua_escodata']

JSON_MAU_THAT = {
    "error": 0, "error_text": "Lấy dữ liệu doanh nghiệp từ mã số thuế thành thành công..!",
    "data": {"ten": "CÔNG TY TNHH MARINE DIGITALE", "mst": "0316956049",
             "dc": "490A Điện Biên Phủ, Phường 21, Quận Bình Thạnh, Thành phố Hồ Chí Minh",
             "daidien": "PHẠM THÙY LINH", "capphep": "2021-09-05", "hoatdong": "2021-09-05",
             "tinhtrang": "Đang hoạt động (đã được cấp GCN ĐKT)",
             "latitude": "10.8011238", "longitude": "106.712847",
             "Links_Map": "https://www.google.com/maps/place/10.8011238+106.712847/@10.8011238,106.712847,17z",
             "nganhnghe": ["Sản xuất sản phẩm khác từ gỗ", "In ấn"]}
}

ns['requests'] = _FakeRequests(lambda url, timeout: (
    _FakeResp(200, JSON_MAU_THAT) if url == "https://escodata.net/api-mst/0316956049.htm"
    else (_ for _ in ()).throw(AssertionError("URL sai: " + url))
))
r1 = fn("0316956049", 20)
assert r1 == (True, "Đang hoạt động (đã được cấp GCN ĐKT)", False, None), f"Phải đọc đúng JSON thật, got {r1}"
print("PASS 1: đọc đúng JSON thật người dùng gửi, dò ra 'Đang hoạt động (đã được cấp GCN ĐKT)' và phân "
      "loại KHÔNG cảnh báo.")

# ===== Test 2 (đúng ca thật — MST bị cảnh báo): tinhtrang ghi tình trạng xấu
# thì phải cảnh báo (tô đỏ), không suy đoán "bình thường". =====
json_khoa = {**JSON_MAU_THAT, "data": {**JSON_MAU_THAT["data"], "tinhtrang": "NNT đã bị khóa mã số thuế"}}
ns['requests'] = _FakeRequests(lambda url, timeout: _FakeResp(200, json_khoa))
r2 = fn("0316956049", 20)
assert r2[0] is True and r2[2] is True, f"MST đã khoá phải ra canh_bao=True, got {r2}"
print("PASS 2: MST có tình trạng xấu (đã khoá MST) được nhận diện đúng là CẢNH BÁO.")

# ===== Test 3 (AN TOÀN — không suy đoán): error != 0, HTTP lỗi, JSON hỏng,
# thiếu tinhtrang, hoặc tinhtrang lạ chưa nhận diện -> đều phải trả THẤT BẠI
# (để rơi xuống nguồn sau), tuyệt đối không suy đoán "đang hoạt động". =====
ns['requests'] = _FakeRequests(lambda url, timeout: _FakeResp(200, {"error": 1, "error_text": "Không tìm thấy MST"}))
assert fn("0000000000", 20)[0] is False, "error != 0 phải trả thất bại."

ns['requests'] = _FakeRequests(lambda url, timeout: _FakeResp(404))
assert fn("0000000000", 20)[0] is False, "HTTP khác 200 phải trả thất bại."

ns['requests'] = _FakeRequests(lambda url, timeout: _FakeResp(200, la_json=False))
assert fn("0000000000", 20)[0] is False, "JSON hỏng phải trả thất bại, không văng lỗi."

ns['requests'] = _FakeRequests(lambda url, timeout: _FakeResp(200, {"error": 0, "data": {"mst": "x", "tinhtrang": ""}}))
assert fn("0000000000", 20)[0] is False, "Thiếu trường tinhtrang phải trả thất bại."

ns['requests'] = _FakeRequests(lambda url, timeout: _FakeResp(200, {"error": 0, "data": {"tinhtrang": "Tình trạng lạ chưa từng thấy"}}))
r_la = fn("0000000000", 20)
assert r_la[0] is False and r_la[2] is None, f"Tình trạng lạ (không khớp từ khoá nào) phải trả thất bại, canh_bao=None (không suy đoán), got {r_la}"

def _nem_loi(url, timeout):
    raise ConnectionError("mất mạng")
ns['requests'] = _FakeRequests(_nem_loi)
assert fn("0000000000", 20)[0] is False, "Lỗi kết nối phải trả thất bại, không văng exception ra ngoài."
print("PASS 3: mọi trường hợp lỗi/dữ liệu bất thường đều trả thất bại an toàn, không suy đoán 'đang hoạt động'.")

# ===== Test 4 (đúng ca thật — tránh lãng phí lượt gọi hàng loạt): phải có
# ngưỡng tạm tắt khi lỗi liên tiếp, giống cơ chế đã áp dụng cho VietQR. =====
than_escodata = _than_ham('_tra_cuu_mst_qua_escodata')
assert '_ESCODATA_NGUONG_TAT' in src and '_escodata_danh_dau(' in than_escodata, (
    "Phải có bộ đếm lỗi liên tiếp + ngưỡng tạm tắt nguồn này trong 1 lượt xuất Excel.")
print("PASS 4: có ngưỡng tạm tắt khi lỗi liên tiếp, tránh lãng phí lượt gọi cho hàng trăm MST còn lại.")

# ===== Test 4b (không hồi quy — cùng bài học rút ra từ api.vietqr.io: sau
# khi bỏ cache dài hạn, mỗi lượt xuất Excel đều tra lại TẤT CẢ MST qua mạng):
# 429 phải được THỬ LẠI đúng 1 lần (theo Retry-After, mặc định 2 giây) trước
# khi chịu thua hẳn. =====
ns4b = _nap('_khong_dau', '_phan_loai_trang_thai_mst', '_escodata_danh_dau', '_tra_cuu_mst_qua_escodata')
fn4b = ns4b['_tra_cuu_mst_qua_escodata']
freq = _FakeRequestsQueue([
    _FakeResp(429, headers={"Retry-After": "3"}),
    _FakeResp(200, JSON_MAU_THAT),
])
ns4b['requests'] = freq
r4b = fn4b("0316956049", 20)
assert r4b == (True, "Đang hoạt động (đã được cấp GCN ĐKT)", False, None), (
    f"429 tạm thời PHẢI được thử lại đúng 1 lần rồi lấy được kết quả thật, không được bỏ cuộc ngay "
    f"— got {r4b}")
assert len(freq.calls) == 2, f"Phải gọi ĐÚNG 2 lượt (429 rồi thử lại thành công) — got {len(freq.calls)}"
assert ns4b['_fake_time'].sleeps == [3], (
    f"Phải nghỉ đúng theo Retry-After (3s) trước khi thử lại — got {ns4b['_fake_time'].sleeps}")
print("PASS 4b: gặp 429 (giới hạn tốc độ tạm thời) -> nghỉ đúng theo Retry-After rồi thử lại thành "
      "công, không bỏ cuộc ngay.")

# ===== Test 5 (QUAN TRỌNG — đúng yêu cầu thứ tự ưu tiên): escodata.net phải
# được thử SAU api.vietqr.io (chỉ khi VietQR đã thất bại) nhưng TRƯỚC
# XInvoice (dự phòng cuối, cần key/có thể hết hạn mức gói free tier). =====
than_chinh = _than_ham('_tra_cuu_trang_thai_mst')
vt_vietqr = than_chinh.find('_tra_cuu_mst_qua_vietqr(')
vt_escodata = than_chinh.find('_tra_cuu_mst_qua_escodata(')
vt_xinvoice = than_chinh.find('_goi_1_lan_xinvoice(')
assert 0 < vt_vietqr < vt_escodata < vt_xinvoice, (
    "Thứ tự ưu tiên phải là: api.vietqr.io -> escodata.net -> XInvoice (dự phòng cuối).")
assert 'if not thanh_cong:' in than_chinh[vt_escodata - 100:vt_escodata], (
    "Chỉ thử escodata.net khi VietQR đã THẤT BẠI (thanh_cong=False) — tra được ở VietQR rồi thì không "
    "cần thử thêm nguồn khác, tránh lãng phí gọi mạng vô ích.")
print("PASS 5: escodata.net được thử SAU api.vietqr.io nhưng TRƯỚC XInvoice, chỉ rơi xuống khi VietQR "
      "đã thất bại.")

# ===== Test 6 (không hồi quy — thông báo lỗi cuối gộp đủ cả 3 nguồn): thiếu
# lý do của 1 nguồn sẽ khiến người dùng chẩn đoán "cụt", không biết nguồn đó
# có được thử hay không. =====
assert 'escodata.net: {ly_do_loi_escodata}' in src, (
    "Thông báo lỗi cuối cùng (khi cả 3 nguồn đều thất bại) phải kèm lý do của escodata.net.")
print("PASS 6: thông báo lỗi cuối cùng gộp đủ lý do của cả 3 nguồn (VietQR + escodata.net + XInvoice).")

# ===== Test 7 (không hồi quy — endpoint chẩn đoán riêng): phải có endpoint
# chẩn đoán nhanh cho escodata.net, không cần biết id công ty nào (API công
# khai). =====
assert '/api/chan-doan-mst-escodata' in src and 'def chan_doan_mst_escodata' in src, (
    "Phải có endpoint chẩn đoán riêng cho escodata.net.")
than_cd = _than_ham('chan_doan_mst_escodata')
assert '_tra_cuu_mst_qua_escodata(' in than_cd, "Endpoint chẩn đoán phải gọi đúng hàm tra cứu thật (không phải mô phỏng riêng)."
print("PASS 7: có endpoint chẩn đoán riêng /api/chan-doan-mst-escodata, không cần biết id công ty nào.")

print("\nALL DONE")
