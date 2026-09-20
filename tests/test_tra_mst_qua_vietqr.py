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
# được trên máy hay không -> đặt làm nguồn ưu tiên CAO NHẤT. (tracuunnt.gdt.
# gov.vn đã BỊ BỎ theo yêu cầu người dùng "không đúng được"; masothue.com
# cũng từng bị bỏ vì lý do tương tự nhưng người dùng tự kiểm tra lại xác
# nhận "chạy được" nên đã thêm lại làm dự phòng thứ 2 — xem
# test_tra_mst_qua_masothue.py — trước khi rơi xuống XInvoice.)


def _than_ham(ten):
    i = src.index('def ' + ten + '(')
    j = src.index('\ndef ', i + 10)
    return src[i:j]


class _FakeTime:
    """Thay cho module time thật — ghi lại các lượt sleep() thay vì chờ
    thật, để test chạy nhanh dù _tra_cuu_mst_qua_vietqr giờ nghỉ theo
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
    m = re.search(r'^_VIETQR_STATE\s*=\s*\{.*\}', src, re.M)
    exec(m.group(0), ns)
    m2 = re.search(r'^_VIETQR_NGUONG_TAT\s*=\s*\d+', src, re.M)
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

    def get(self, url, timeout=None):
        return self._fn(url, timeout)


class _FakeRequestsQueue:
    """Trả về LẦN LƯỢT các response trong hàng đợi theo từng lượt gọi — dùng
    để mô phỏng 429 rồi 200 ở lượt thử lại (khác _FakeRequests ở trên, vốn
    chỉ trả về 1 kết quả cố định qua callback)."""
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, timeout=None):
        self.calls.append(url)
        return self.responses.pop(0)


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

# ===== Test 3b (không hồi quy — cùng lỗi trùng lặp tiền tố đã phát hiện ở
# escodata.net "escodata.net: escodata.net: ..."): ly_do_loi do
# _tra_cuu_mst_qua_vietqr() TỰ trả về KHÔNG được tự ý kèm sẵn tiền tố
# "api.vietqr.io: " — vì _tra_cuu_trang_thai_mst() (nơi gộp lỗi cuối cùng của
# cả 3 nguồn) ĐÃ tự thêm tiền tố "api.vietqr.io: " rồi, kèm sẵn nữa sẽ bị LẶP
# tiền tố 2 LẦN. =====
ns3b = _nap('_khong_dau', '_phan_loai_trang_thai_mst', '_vietqr_danh_dau', '_tra_cuu_mst_qua_vietqr')
fn3b = ns3b['_tra_cuu_mst_qua_vietqr']
ns3b['requests'] = _FakeRequests(lambda url, timeout: _FakeResp(200, {"code": "01", "desc": "Không tìm thấy MST"}))
r3b = fn3b("0000000000", 20)
assert r3b[0] is False
assert r3b[3] == "Không tìm thấy MST", (
    f"ly_do_loi KHÔNG được tự kèm sẵn tiền tố 'api.vietqr.io: ' (nơi gộp lỗi cuối cùng ở "
    f"_tra_cuu_trang_thai_mst() đã tự thêm rồi, kèm sẵn nữa sẽ bị lặp 2 lần "
    f"'api.vietqr.io: api.vietqr.io: ...') — got {r3b[3]!r}")
print("PASS 3b: ly_do_loi trả về KHÔNG tự kèm sẵn tiền tố 'api.vietqr.io: ' — tránh lặp tiền tố 2 lần "
      "khi _tra_cuu_trang_thai_mst() gộp lỗi cuối cùng của cả 3 nguồn.")

# ===== Test 4 (đúng ca thật — tránh lãng phí lượt gọi hàng loạt): phải có
# ngưỡng tạm tắt khi lỗi liên tiếp, giống cơ chế đã áp dụng cho tracuunnt. =====
than_vietqr = _than_ham('_tra_cuu_mst_qua_vietqr')
assert '_VIETQR_NGUONG_TAT' in src and '_vietqr_danh_dau(' in than_vietqr, (
    "Phải có bộ đếm lỗi liên tiếp + ngưỡng tạm tắt nguồn này trong 1 lượt xuất Excel.")
print("PASS 4: có ngưỡng tạm tắt khi lỗi liên tiếp, tránh lãng phí lượt gọi cho hàng trăm MST còn lại.")

# ===== Test 4b (không hồi quy — bug THẬT người dùng vừa báo tiếp qua log xuất
# Excel: rất nhiều MST bị "api.vietqr.io HTTP 429" ngay sau khi bỏ hẳn cache
# dài hạn, vì giờ MỖI lượt xuất Excel đều tra lại TẤT CẢ MST qua mạng thay vì
# chỉ những MST chưa có cache): 429 phải được THỬ LẠI đúng 1 lần (theo
# Retry-After, mặc định 2 giây nếu không có) trước khi chịu thua hẳn — giống
# hệt cách XInvoice đã xử lý 429 tạm thời (xem _goi_1_lan_xinvoice) — tránh
# lãng phí cơ hội khi đây chỉ là giới hạn tốc độ THOÁNG QUA, không phải hạn
# mức cứng theo ngày/tháng (api.vietqr.io được quảng cáo "miễn phí, không
# hạn mức"). =====
ns4b = _nap('_khong_dau', '_phan_loai_trang_thai_mst', '_vietqr_danh_dau', '_tra_cuu_mst_qua_vietqr')
fn4b = ns4b['_tra_cuu_mst_qua_vietqr']
freq = _FakeRequestsQueue([
    _FakeResp(429, headers={"Retry-After": "3"}),
    _FakeResp(200, JSON_MAU_THAT),
])
ns4b['requests'] = freq
r4b = fn4b("0315458241", 20)
assert r4b == (True, "NNT đang hoạt động", False, None), (
    f"429 tạm thời PHẢI được thử lại đúng 1 lần rồi lấy được kết quả thật, không được bỏ cuộc ngay "
    f"— got {r4b}")
assert len(freq.calls) == 2, f"Phải gọi ĐÚNG 2 lượt (429 rồi thử lại thành công) — got {len(freq.calls)}"
assert ns4b['_fake_time'].sleeps == [3], (
    f"Phải nghỉ đúng theo Retry-After (3s) trước khi thử lại — got {ns4b['_fake_time'].sleeps}")
print("PASS 4b: gặp 429 (giới hạn tốc độ tạm thời — ca thật khi bỏ cache khiến mọi lượt xuất Excel đều "
      "tra lại TẤT CẢ MST) -> nghỉ đúng theo Retry-After rồi thử lại thành công, không bỏ cuộc ngay.")

# ===== Test 5 (QUAN TRỌNG — đúng yêu cầu thứ tự ưu tiên): api.vietqr.io phải
# được thử TRƯỚC XInvoice — vì KHÔNG phụ thuộc ddddocr, nhanh/chắc chắn hơn
# hẳn. (tracuunnt.gdt.gov.vn đã BỊ BỎ theo yêu cầu người dùng "không đúng
# được" — không còn trong chuỗi nữa; masothue.com nằm GIỮA VietQR và
# XInvoice, xem test_tra_mst_qua_masothue.py để kiểm tra đúng vị trí đó.) =====
than_chinh = _than_ham('_tra_cuu_trang_thai_mst')
vt_vietqr = than_chinh.find('_tra_cuu_mst_qua_vietqr(')
vt_xinvoice = than_chinh.find('_goi_1_lan_xinvoice(')
assert 0 < vt_vietqr < vt_xinvoice, (
    "Thứ tự ưu tiên phải là: api.vietqr.io (không captcha) -> XInvoice (dự phòng).")
print("PASS 5: api.vietqr.io được thử TRƯỚC XInvoice, chỉ rơi xuống XInvoice khi VietQR thất bại.")

# ===== Test 6 (không hồi quy — thông báo lỗi cuối không bỏ sót lý do của
# VietQR): thiếu lý do của 1 nguồn sẽ khiến người dùng chẩn đoán "cụt",
# không biết nguồn đó có được thử hay không. (Việc gộp đủ lý do của CẢ 3
# nguồn — VietQR + masothue.com + XInvoice — được kiểm tra đầy đủ hơn ở
# test_tra_mst_qua_masothue.py Test 6, vì file đó còn xác nhận cả phần
# masothue.com trong thông báo gộp.) =====
assert 'api.vietqr.io: {ly_do_loi_vietqr}' in src, (
    "Thông báo lỗi cuối cùng (khi các nguồn đều thất bại) phải kèm lý do của api.vietqr.io.")
print("PASS 6: thông báo lỗi cuối cùng không bỏ sót lý do của api.vietqr.io.")

# ===== Test 7 (không hồi quy — endpoint chẩn đoán riêng): phải có endpoint
# chẩn đoán nhanh cho VietQR, không cần biết id công ty nào (API công khai). =====
assert '/api/chan-doan-mst-vietqr' in src and 'def chan_doan_mst_vietqr' in src, (
    "Phải có endpoint chẩn đoán riêng cho api.vietqr.io.")
than_cd = _than_ham('chan_doan_mst_vietqr')
assert '_tra_cuu_mst_qua_vietqr(' in than_cd, "Endpoint chẩn đoán phải gọi đúng hàm tra cứu thật (không phải mô phỏng riêng)."
print("PASS 7: có endpoint chẩn đoán riêng /api/chan-doan-mst-vietqr, không cần biết id công ty nào.")

print("\nALL DONE")
