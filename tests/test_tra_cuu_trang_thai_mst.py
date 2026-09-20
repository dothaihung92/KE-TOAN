import os
import re
import json
import threading

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test cho tính năng "dò tình trạng hoạt động MST khi xuất Excel"
# (_phan_loai_trang_thai_mst / _tra_cuu_trang_thai_mst trong server.py) — người dùng
# yêu cầu: "hãy thêm chức năng dò mst còn đang hoạt động hay không hoặc công ty cần
# xác minh địa chỉ kinh doanh khi kết xuất ra excel thêm 1 cột trạng thái mst ở
# cuối công ty nào bị khoá mst hoặc báo chờ xác minh tình trạng hoạt động tại địa
# chỉ thì trong file excel tô đỏ dòng đó" — sau khi tìm hiểu (không tự vào được
# masothue.com/tracuunnt.gdt.gov.vn từ môi trường sandbox), người dùng chọn dùng API
# CHÍNH THỨC của XInvoice (api.xinvoice.vn/gdt-api/tax-payer/{mst}, cần client-id +
# api-key tự đăng ký) thay cho việc đọc HTML masothue.com ban đầu.
#
# QUAN TRỌNG (đổi ý nghĩa lớn — vừa bỏ hẳn cache): trước đây có cache DB dài hạn
# (bảng mst_status_cache, 14 ngày, sau đó rút xuống 1 ngày riêng cho MST "CÓ CẢNH
# BÁO"), nhưng người dùng vẫn tiếp tục báo "phần mềm báo sai" (tra ra 'NNT ngừng
# hoạt động...' dù MST đó THẬT SỰ đang hoạt động bình thường) và yêu cầu thẳng:
# "hãy bỏ cache 14 ngày đi, không cần lưu, cứ dò ở thời điểm hiện tại" — nên
# _tra_cuu_trang_thai_mst() giờ KHÔNG còn đọc/ghi bất kỳ cache dài hạn nào nữa,
# LUÔN tra cứu thật sự qua mạng mỗi lần được gọi (trừ dedup trong bộ nhớ CHỈ trong
# CÙNG 1 lượt xuất Excel — xem _mst_status_local ở export_excel, không phải cache
# dài hạn nên KHÔNG có trong phạm vi test file này).


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


class _FakeResp:
    def __init__(self, status_code, data=None, headers=None):
        self.status_code = status_code
        self._data = data
        self.headers = headers or {}

    def json(self):
        return self._data

    @property
    def text(self):
        import json as _json
        try:
            return _json.dumps(self._data, ensure_ascii=False) if self._data is not None else ""
        except Exception:
            return ""


class _FakeRequests:
    """Thay cho module requests thật — kiểm soát được nội dung trả về/lỗi mạng
    để test KHÔNG cần gọi mạng thật (không thể test trực tiếp API XInvoice từ
    môi trường sandbox hiện tại — bị chặn egress proxy). next_responses: hàng
    đợi (status, data, headers) trả về LẦN LƯỢT theo từng lượt gọi (dùng để mô
    phỏng 429 rồi 200 ở lượt thử lại) — hết hàng đợi thì fallback về
    next_status/next_data (giữ tương thích các test cũ chỉ cần 1 kết quả cố định)."""
    def __init__(self):
        self.calls = []
        self.next_status = 200
        self.next_data = None
        self.next_exc = None
        self.next_responses = None

    def get(self, url, headers=None, timeout=None, params=None):
        self.calls.append({"url": url, "headers": dict(headers or {}), "params": dict(params or {})})
        if self.next_exc is not None:
            raise self.next_exc
        if self.next_responses:
            status, data, hdrs = self.next_responses.pop(0)
            return _FakeResp(status, data, hdrs)
        return _FakeResp(self.next_status, self.next_data)


class _FakeTime:
    """Thay cho module time thật — ghi lại các lượt sleep() thay vì chờ thật,
    để test chạy nhanh dù _tra_cuu_trang_thai_mst giờ có nghỉ giữa các lượt gọi
    API thật (né giới hạn tốc độ) + chờ theo Retry-After khi gặp 429."""
    def __init__(self):
        self.sleeps = []

    def sleep(self, s):
        self.sleeps.append(s)


class _FakeSettings:
    """Thay cho _get_setting/_set_setting thật (bảng app_settings) — dict trong
    bộ nhớ, đủ để test luồng đọc client-id/api-key đã cấu hình."""
    def __init__(self):
        self.store = {}

    def get(self, key, default=""):
        return self.store.get(key, default)

    def set(self, key, value):
        self.store[key] = value


ns = {'json': json, 'threading': threading}
exec(extract_fn('_khong_dau'), ns)
exec(extract_fn('_chuan_mst'), ns)
exec(extract_fn('_phan_loai_trang_thai_mst'), ns)
m2 = re.search(r'^_MST_API_NGHI_GIUA_LUOT\s*=\s*[\d.]+', src, re.M)
exec(m2.group(0), ns)
m3 = re.search(r'^_XINVOICE_KEY_STATE\s*=\s*\{.*\}', src, re.M)
exec(m3.group(0), ns)

_fake_requests = _FakeRequests()
_fake_settings = _FakeSettings()
_fake_time = _FakeTime()
ns['requests'] = _fake_requests
ns['_get_setting'] = _fake_settings.get
ns['_set_setting'] = _fake_settings.set
ns['time'] = _fake_time
exec(extract_fn('_lay_danh_sach_xinvoice_keys'), ns)
exec(extract_fn('_goi_1_lan_xinvoice'), ns)

# Stub nguồn ưu tiên số 1 (VietQR, thử TRƯỚC XInvoice — xem
# _tra_cuu_trang_thai_mst) LUÔN thất bại: các test dưới đây kiểm tra hành vi
# RIÊNG của chuỗi XInvoice (cấu hình key, chuyển key, dự phòng...), không
# liên quan tới VietQR — nguồn đó có test riêng (test_tra_mst_qua_vietqr.py).
# (tracuunnt.gdt.gov.vn và masothue.com đã BỊ BỎ theo yêu cầu người dùng
# "không đúng được" — không còn trong chuỗi nữa. Đã bỏ luôn cache DB dài hạn
# — không cần bind ns['db'] nữa, hàm không còn gọi db() ở đâu cả.)
ns['_tra_cuu_mst_qua_vietqr'] = lambda mst_c, timeout: (False, "", None, "stub: tắt trong test này")
exec(extract_fn('_tra_cuu_trang_thai_mst'), ns)
_phan_loai_trang_thai_mst = ns['_phan_loai_trang_thai_mst']
_tra_cuu_trang_thai_mst = ns['_tra_cuu_trang_thai_mst']


def _set_xinvoice_keys(danh_sach):
    """Cấu hình NHIỀU cặp client-id/api-key (định dạng mới, dùng cho test tính
    năng "hết key này chạy qua key khác") — xoá luôn cấu hình 1-cặp CŨ để
    không lẫn lộn, và reset _XINVOICE_KEY_STATE["idx"] về 0 (giống hệt
    POST /api/settings/xinvoice-mst-api thật sự làm khi lưu cấu hình mới)."""
    _fake_settings.set("xinvoice_client_id", "")
    _fake_settings.set("xinvoice_api_key", "")
    _fake_settings.set("xinvoice_api_keys", json.dumps(danh_sach, ensure_ascii=False))
    with ns['_XINVOICE_KEY_STATE']['lock']:
        ns['_XINVOICE_KEY_STATE']['idx'] = 0

# ===== Test 1-6: _phan_loai_trang_thai_mst() — phân loại theo nội dung trường
# "status" trả về từ API, các ca thường gặp (đúng cụm mô tả chính thức của Tổng
# cục Thuế). =====
_, cb = _phan_loai_trang_thai_mst("Người nộp thuế đang hoạt động (đã cấp GCN ĐKT)")
assert cb is False, f"'đang hoạt động' PHẢI được coi là bình thường (canh_bao=False) — got {cb}"
print("PASS 1: 'đang hoạt động' -> canh_bao=False (bình thường, không tô đỏ).")

nhan, cb = _phan_loai_trang_thai_mst(
    "NNT đang trong quá trình chờ xác minh tình trạng hoạt động tại địa chỉ đã đăng ký")
assert cb is True, f"'chờ xác minh tình trạng hoạt động tại địa chỉ' PHẢI cảnh báo (canh_bao=True) — got {cb}"
assert "xác minh" in nhan.lower()
print("PASS 2: 'chờ xác minh tình trạng hoạt động tại địa chỉ' -> canh_bao=True (đúng yêu cầu người dùng).")

_, cb = _phan_loai_trang_thai_mst("Người nộp thuế đã bị khóa mã số thuế")
assert cb is True, f"'đã bị khóa mã số thuế' PHẢI cảnh báo — got {cb}"
print("PASS 3: 'đã bị khóa mã số thuế' -> canh_bao=True.")

_, cb = _phan_loai_trang_thai_mst("NNT ngừng hoạt động nhưng chưa hoàn thành thủ tục đóng mã số thuế")
assert cb is True, f"'ngừng hoạt động' PHẢI cảnh báo — got {cb}"
print("PASS 4: 'ngừng hoạt động nhưng chưa hoàn thành thủ tục đóng MST' -> canh_bao=True.")

_, cb = _phan_loai_trang_thai_mst("Không hoạt động tại địa chỉ đã đăng ký")
assert cb is True, f"'không hoạt động tại địa chỉ đã đăng ký' PHẢI cảnh báo — got {cb}"
print("PASS 5: 'không hoạt động tại địa chỉ đã đăng ký' -> canh_bao=True.")

_, cb = _phan_loai_trang_thai_mst("")
assert cb is None, f"KHÔNG có dữ liệu tình trạng -> canh_bao=None (KHÔNG suy đoán/không tô đỏ) — got {cb}"
print("PASS 6: không có dữ liệu tình trạng -> canh_bao=None, không suy đoán bừa.")

# ===== Test 6b (bug THẬT người dùng vừa báo qua log xuất Excel — "kiểm tra
# lại sao phần mềm không kiểm tra đủ thông tin"): nhiều MST thật (vd
# 0106869738-005, 0315482212, 0316642412) trả về tình trạng VIẾT TẮT "NNT
# ngừng HĐ nhưng chưa hoàn thành thủ tục chấm dứt hiệu lực MST" ("HĐ" =
# "hoạt động", "MST" = "mã số thuế") — các cụm từ khoá ĐẦY ĐỦ ở Test 4 KHÔNG
# khớp được cụm viết tắt này, trước đây rơi vào "tình trạng lạ chưa nhận
# diện được" (canh_bao=None, coi là THẤT BẠI) dù MST thật sự đang ở tình
# trạng xấu này -> PHẢI nhận diện được cả biến thể viết tắt. =====
nhan6b, cb6b = _phan_loai_trang_thai_mst(
    "NNT ngừng HĐ nhưng chưa hoàn thành thủ tục chấm dứt hiệu lực MST")
assert cb6b is True, (
    f"Biến thể VIẾT TẮT 'ngừng HĐ...chấm dứt hiệu lực MST' PHẢI được nhận diện là CẢNH BÁO (canh_bao=True) "
    f"giống hệt cụm đầy đủ 'ngừng hoạt động...đóng mã số thuế' — got {cb6b}")
assert "ngừng hoạt động" in nhan6b.lower(), f"got {nhan6b}"
print("PASS 6b: biến thể viết tắt 'ngừng HĐ...chấm dứt hiệu lực MST' -> canh_bao=True (khớp đúng như "
      "cụm đầy đủ), sửa đúng bug thật khiến các MST như 0106869738-005/0315482212/0316642412 không "
      "được nhận diện đúng tình trạng.")

# ===== Test 7-13: _tra_cuu_trang_thai_mst() — luồng cấu hình + gọi API (mock),
# KHÔNG còn cache dài hạn — luôn tra thật tại thời điểm gọi. =====

# Test 7 (QUAN TRỌNG — chẩn đoán "sao vẫn còn?"): MST rỗng/"KL" (khách lẻ)/
# quá ngắn -> KHÔNG gọi mạng, trả canh_bao=None (kể cả khi ĐÃ cấu hình
# client-id/api-key). "" và "KL" là CHỦ Ý bỏ qua (không phải lỗi) nên KHÔNG
# kèm ly_do_loi; còn "123" (có chữ nhưng KHÔNG đủ 9-10 chữ số — dấu hiệu dữ
# liệu MST trên hóa đơn gốc bị lỗi/thiếu/sai định dạng) PHẢI kèm ly_do_loi
# để _prefetch_trang_thai_mst() còn hiện được trong "VÍ DỤ LỖI GẶP PHẢI" —
# tránh tình trạng người dùng thấy còn MST trống nhưng không có ví dụ lỗi
# nào để biết nguyên nhân.
_fake_settings.set("xinvoice_client_id", "demo-client")
_fake_settings.set("xinvoice_api_key", "demo-key")
_fake_requests.calls.clear()
r7a = _tra_cuu_trang_thai_mst("", timeout=1)
r7b = _tra_cuu_trang_thai_mst("KL", timeout=1)
r7c = _tra_cuu_trang_thai_mst("123", timeout=1)
assert r7a["canh_bao"] is None and r7b["canh_bao"] is None and r7c["canh_bao"] is None
assert len(_fake_requests.calls) == 0, (
    f"MST rỗng/'KL'/quá ngắn KHÔNG được gọi mạng (tránh tra cứu vô nghĩa cho khách lẻ dùng chung mã) "
    f"— got {len(_fake_requests.calls)} lượt gọi")
assert "ly_do_loi" not in r7a and "ly_do_loi" not in r7b, (
    f"MST rỗng/'KL' là CHỦ Ý bỏ qua (khách lẻ dùng chung mã), KHÔNG phải lỗi -> không kèm ly_do_loi "
    f"— got r7a={r7a}, r7b={r7b}")
assert "không hợp lệ" in (r7c.get("ly_do_loi") or ""), (
    f"MST '123' (không đủ 9-10 chữ số) -> PHẢI kèm ly_do_loi ghi rõ 'không hợp lệ' để người dùng biết "
    f"nguyên nhân (dữ liệu MST trên hóa đơn gốc bị lỗi/thiếu), thay vì chỉ thấy trống không rõ vì sao "
    f"— got {r7c}")
print("PASS 7: MST rỗng/'KL' (khách lẻ dùng chung mã) -> bỏ qua hẳn, không gọi mạng, không kèm "
      "ly_do_loi (chủ ý, không phải lỗi); MST quá ngắn/sai định dạng -> vẫn bỏ qua nhưng kèm ly_do_loi "
      "rõ ràng để chẩn đoán.")

# Test 8 (không hồi quy sau khi BỎ tracuunnt.gdt.gov.vn/masothue.com theo yêu
# cầu người dùng "không đúng được"): CHƯA cấu hình client-id/api-key XInvoice
# nào, VÀ VietQR (nguồn duy nhất còn lại phía trước XInvoice) cũng thất bại
# (bị stub thất bại trong file test này) -> KHÔNG còn nguồn nào để thử ->
# canh_bao=None an toàn (không suy đoán), KHÔNG gọi mạng lần nào (không có
# key nên vòng lặp XInvoice không chạy, không còn masothue.com dự phòng nữa).
_fake_settings.set("xinvoice_client_id", "")
_fake_settings.set("xinvoice_api_key", "")
_fake_settings.set("xinvoice_api_keys", "")
_fake_requests.calls.clear()
_fake_requests.next_exc = None
_fake_requests.next_responses = None
_fake_requests.next_status = 200
_fake_requests.next_data = {"status": "Người nộp thuế đã bị khóa mã số thuế"}
r8a = _tra_cuu_trang_thai_mst("0315696199", timeout=1)
assert r8a["canh_bao"] is None, (
    f"Chưa cấu hình key XInvoice nào + VietQR cũng thất bại -> không còn nguồn nào để thử, phải trả "
    f"canh_bao=None an toàn (không suy đoán) — got {r8a}")
assert len(_fake_requests.calls) == 0, (
    f"Chưa có key XInvoice (không còn masothue.com dự phòng) -> KHÔNG được gọi mạng lần nào "
    f"— got {len(_fake_requests.calls)} lượt gọi")
print("PASS 8: chưa cấu hình key XInvoice nào + VietQR thất bại -> không còn nguồn nào để thử (đã bỏ "
      "tracuunnt.gdt.gov.vn/masothue.com), trả canh_bao=None an toàn, không gọi mạng thừa.")

_fake_settings.set("xinvoice_client_id", "demo-client")
_fake_settings.set("xinvoice_api_key", "demo-key")
_fake_requests.next_status = 200
_fake_requests.next_data = None

# Test 9: gọi API đúng 1 lần, đúng URL/header, phân loại đúng theo trường
# "status" trả về.
_fake_requests.calls.clear()
_fake_requests.next_status = 200
_fake_requests.next_data = {"status": "Người nộp thuế đã bị khóa mã số thuế"}
r9 = _tra_cuu_trang_thai_mst("0315696133", timeout=1)
assert r9["canh_bao"] is True, f"Phải phân loại đúng từ trường 'status' trả về — got {r9}"
assert len(_fake_requests.calls) == 1, f"Phải gọi API đúng 1 lần — got {len(_fake_requests.calls)}"
call = _fake_requests.calls[0]
assert call["url"] == "https://api.xinvoice.vn/gdt-api/tax-payer/0315696133", f"Sai URL — got {call['url']}"
assert call["headers"].get("client-id") == "demo-client"
assert call["headers"].get("api-key") == "demo-key"
print("PASS 9: gọi đúng API XInvoice (URL + header client-id/api-key), phân loại đúng theo trường "
      "'status'.")

# Test 9b (ca thật người dùng báo — QUAN TRỌNG): bảng kê ~880 hóa đơn chỉ dò được
# ~50 dòng, còn lại trống hết dù cùng client-id/api-key -> dấu hiệu bị GIỚI HẠN TỐC
# ĐỘ (429) do gọi API quá nhanh liên tiếp cho hàng trăm MST khác nhau. Xác nhận: gặp
# 429 kèm Retry-After -> phải NGHỈ đúng theo đó rồi THỬ LẠI 1 lần (không bỏ cuộc
# ngay), và vẫn phải nghỉ 1 chút TRƯỚC mỗi lượt gọi API thật để né giới hạn tốc độ
# ngay từ đầu.
_fake_requests.calls.clear()
_fake_time.sleeps.clear()
_fake_requests.next_responses = [
    (429, {"message": "Too Many Requests"}, {"Retry-After": "3"}),
    (200, {"status": "Người nộp thuế đang hoạt động (đã cấp GCN ĐKT)"}, {}),
]
r9b = _tra_cuu_trang_thai_mst("0399998888", timeout=1)
assert r9b["canh_bao"] is False, (
    f"Gặp 429 rồi thử lại thành công -> PHẢI lấy được tình trạng thật, không phải bỏ cuộc — got {r9b}")
assert len(_fake_requests.calls) == 2, (
    f"429 phải được THỬ LẠI đúng 1 lần (không bỏ cuộc ngay ở lần đầu) — got {len(_fake_requests.calls)} lượt gọi")
assert 3 in _fake_time.sleeps, (
    f"Phải NGHỈ đúng theo Retry-After (3s) khi gặp 429 trước khi thử lại — got các lượt nghỉ {_fake_time.sleeps}")
assert _fake_time.sleeps[0] == ns['_MST_API_NGHI_GIUA_LUOT'], (
    f"Phải nghỉ 1 chút TRƯỚC lượt gọi API thật đầu tiên (né giới hạn tốc độ ngay từ đầu) "
    f"— got {_fake_time.sleeps}")
print("PASS 9b: gặp 429 (giới hạn tốc độ, đúng ca thật ~830/880 dòng bị trống) -> nghỉ đúng theo "
      "Retry-After rồi thử lại thành công, không bỏ cuộc ngay; luôn nghỉ 1 chút trước mỗi lượt gọi "
      "API thật để né giới hạn tốc độ ngay từ đầu.")
_fake_requests.next_responses = None

# Test 9c (ca thật người dùng báo tiếp — QUAN TRỌNG): 429 do HẾT HẠN MỨC GÓI (free
# tier XInvoice) — đúng NGUYÊN VĂN lỗi thật người dùng gặp: "Exceeded free tier
# limit. Please try again later or upgrade your plan." — PHẢI nhận diện ra đây KHÁC
# với 429 giới hạn tốc độ tạm thời (Test 9b): KHÔNG chờ+thử lại (chờ vài giây không
# giải quyết được hạn mức theo ngày/tháng, chỉ tốn thêm thời gian vô ích), thất bại
# NGAY, và ly_do_loi phải ghi rõ "HẾT HẠN MỨC GÓI" để người dùng tự biết cần đợi gói
# làm mới hoặc nâng cấp, KHÔNG PHẢI do "hết hạn"/sai client-id-api-key.
# (đã cấu hình đúng 1 key XInvoice -> key đó hết hạn mức -> đã bỏ
# masothue.com dự phòng nên chịu thua ngay sau ĐÚNG 1 lượt gọi XInvoice.)
_fake_requests.calls.clear()
_fake_time.sleeps.clear()
_fake_requests.next_exc = None
_fake_requests.next_responses = [
    (429, {"success": False,
          "error": "Exceeded free tier limit. Please try again later or upgrade your plan."}, {}),
]
dem_loi_9c = [0]
r9c = _tra_cuu_trang_thai_mst("0388887777", timeout=1, so_lan_that_bai_lien_tiep=dem_loi_9c)
assert r9c["canh_bao"] is None
assert len(_fake_requests.calls) == 1, (
    f"429 HẾT HẠN MỨC GÓI KHÔNG được chờ+thử lại XInvoice (vô ích, hạn mức tính theo ngày/tháng) — chỉ "
    f"ĐÚNG 1 lượt gọi XInvoice rồi chịu thua ngay (không còn masothue.com dự phòng nữa) — got "
    f"{len(_fake_requests.calls)} lượt gọi")
assert dem_loi_9c[0] == 1, "Vẫn phải tính vào bộ đếm lỗi liên tiếp để sớm dừng gọi mạng cho các MST còn lại"
assert "HẾT HẠN MỨC GÓI" in (r9c.get("ly_do_loi") or ""), (
    f"ly_do_loi phải ghi rõ 'HẾT HẠN MỨC GÓI' (khác hẳn 'hết hạn'/sai key) để người dùng tự biết đúng "
    f"nguyên nhân cần đợi gói làm mới hoặc nâng cấp trên xinvoice.vn — got {r9c}")
print("PASS 9c: 429 do HẾT HẠN MỨC GÓI (free tier, đúng nguyên văn lỗi thật người dùng gặp) -> nhận "
      "diện đúng, KHÔNG chờ+thử lại XInvoice vô ích, thất bại ngay (đã bỏ masothue.com dự phòng), "
      "ly_do_loi ghi rõ nguyên nhân là hết hạn mức gói (không phải hết hạn/sai key).")
_fake_requests.next_responses = None
_fake_requests.next_status = 200   # trả về trạng thái mặc định cho các test sau
_fake_requests.next_data = None

# ===== Test 10 (bug THẬT người dùng vừa báo tiếp — CỰC KỲ QUAN TRỌNG: "vẫn tra
# mst NNT ngừng hoạt động nhưng chưa hoàn thành thủ tục đóng mã số thuế nhưng đã
# dò mst này không bị gì hết vẫn hoạt động bình thường hãy có cache 14 ngày đi
# ko cần lưu cứ dò ở thời điểm hiện tại"): kể cả sau khi đã sửa cache "CÓ CẢNH
# BÁO" hết hạn sớm hơn (1 ngày, bản vá trước), người dùng vẫn thấy báo sai vì
# cache CŨ (ghi từ TRƯỚC bản vá) vẫn còn hiệu lực. Giải pháp cuối cùng theo
# đúng yêu cầu người dùng: BỎ HẲN cache dài hạn — LUÔN tra cứu THẬT SỰ tại thời
# điểm gọi, không lưu/dùng lại kết quả cũ giữa các lần gọi khác nhau. =====
_fake_requests.calls.clear()
_fake_requests.next_status = 200
_fake_requests.next_data = {"status": "NNT ngừng hoạt động nhưng chưa hoàn thành thủ tục đóng mã số thuế"}
r10a = _tra_cuu_trang_thai_mst("0313415034", timeout=1)   # đúng MST thật người dùng báo (BROTHER INTERNATIONAL)
assert r10a["canh_bao"] is True, f"got {r10a}"
assert len(_fake_requests.calls) == 1

_fake_requests.calls.clear()
_fake_requests.next_data = {"status": "NNT đang hoạt động"}
r10b = _tra_cuu_trang_thai_mst("0313415034", timeout=1)   # gọi lại NGAY sau đó, CÙNG 1 MST
assert r10b["canh_bao"] is False, (
    f"KHÔNG được cache lại kết quả cũ — gọi lại PHẢI LUÔN tra cứu THẬT SỰ tại thời điểm hiện tại và lấy "
    f"đúng tình trạng MỚI NHẤT, đúng ca thật người dùng báo (MST đã hoạt động bình thường trở lại nhưng "
    f"phần mềm vẫn báo sai do cache cũ) — got {r10b}")
assert len(_fake_requests.calls) == 1, (
    f"KHÔNG còn cache -> PHẢI gọi mạng lại THẬT SỰ mỗi lần gọi (không được trả thẳng kết quả cũ của lần "
    f"trước) — got {len(_fake_requests.calls)} lượt gọi")
print("PASS 10: KHÔNG còn cache dài hạn — gọi lại CÙNG 1 MST luôn tra cứu THẬT SỰ tại thời điểm hiện "
      "tại, lấy đúng tình trạng mới nhất, đúng yêu cầu người dùng 'không cần lưu cứ dò ở thời điểm hiện "
      "tại' — sửa dứt điểm bug báo sai kéo dài do cache cũ.")

# Test 11 (an toàn/không hồi quy — QUAN TRỌNG): lỗi mạng/API (mất kết nối/timeout/sai
# client-id-api-key -> 401) -> KHÔNG được crash, trả canh_bao=None (không suy đoán khi
# không tra cứu được), và bộ đếm lỗi liên tiếp phải hoạt động: sau nhiều lỗi liên tiếp
# trong CÙNG 1 lượt xuất Excel, DỪNG gọi API cho các MST còn lại (tránh treo lâu vì
# hàng loạt MST timeout/401 liên tục).
_fake_requests.calls.clear()
_fake_requests.next_data = None
_fake_requests.next_exc = Exception("mạng lỗi giả lập")
dem_loi = [0]
ket_qua_11 = []
for i in range(8):
    mst_gia = f"031569613{i % 10}"  # nhiều MST khác nhau
    ket_qua_11.append(_tra_cuu_trang_thai_mst(mst_gia + "0", timeout=1, so_lan_that_bai_lien_tiep=dem_loi))
assert all(kq["canh_bao"] is None for kq in ket_qua_11), (
    "Lỗi mạng KHÔNG được crash và KHÔNG được suy đoán canh_bao — phải luôn là None")
# Mỗi lượt lỗi (trước khi bộ đếm đạt 5) làm ĐÚNG 1 lượt gọi mạng thật (chỉ
# XInvoice — đã bỏ masothue.com dự phòng) -> 5 lượt lỗi liên tiếp = 5 lượt gọi
# thật, rồi bộ đếm đạt 5 mới NGỪNG hẳn (3 lượt còn lại không gọi mạng nữa).
assert len(_fake_requests.calls) == 5, (
    f"Sau ĐÚNG 5 lượt lỗi liên tiếp (1 lượt gọi mạng XInvoice/lượt, đã bỏ masothue.com dự phòng) phải "
    f"NGỪNG gọi mạng cho các MST còn lại trong lượt này (tránh treo lâu vì hàng loạt timeout) — got "
    f"{len(_fake_requests.calls)} lượt gọi thật (kỳ vọng đúng 5)")
assert all("Lỗi kết nối" in (kq.get("ly_do_loi") or "") for kq in ket_qua_11[:5]), (
    f"Mỗi lượt lỗi kết nối THẬT SỰ (5 lượt đầu, trước khi ngừng gọi mạng) phải kèm ly_do_loi cụ thể để "
    f"người dùng biết nguyên nhân thật (không chỉ thấy trống không rõ vì sao) — got {ket_qua_11[:5]}")
print("PASS 11: lỗi mạng không làm crash (canh_bao=None, an toàn), dừng hẳn việc gọi API sau 5 lỗi "
      "liên tiếp trong cùng 1 lượt xuất Excel, và mỗi lượt lỗi đều kèm ly_do_loi cụ thể để chẩn đoán.")

# Test 12 (không hồi quy — QUAN TRỌNG): status HTTP khác 200 (vd 401 sai client-id/
# api-key) -> KHÔNG suy đoán tình trạng (canh_bao=None), vẫn tính là 1 lượt lỗi cho bộ
# đếm liên tiếp, VÀ trả kèm ly_do_loi ghi rõ "HTTP 401" để người dùng tự biết đây là do
# client-id/api-key sai/hết hạn — đúng câu hỏi người dùng đã hỏi "này là do api hết hạn
# nên chặn phải không".
_fake_requests.next_exc = None
_fake_requests.next_status = 401
_fake_requests.next_data = {"message": "Unauthorized"}
_fake_requests.calls.clear()
dem_loi2 = [0]
r12 = _tra_cuu_trang_thai_mst("0311111111", timeout=1, so_lan_that_bai_lien_tiep=dem_loi2)
assert r12["canh_bao"] is None, f"HTTP 401 (sai key) KHÔNG được suy đoán tình trạng — got {r12}"
assert dem_loi2[0] == 1, f"HTTP lỗi vẫn phải tính vào bộ đếm lỗi liên tiếp — got {dem_loi2[0]}"
assert "HTTP 401" in (r12.get("ly_do_loi") or ""), (
    f"Phải trả kèm ly_do_loi ghi rõ mã lỗi HTTP thật (401) để người dùng tự chẩn đoán được nguyên nhân "
    f"— got {r12}")
assert len(_fake_requests.calls) == 1, (
    f"ĐÚNG 1 lượt gọi XInvoice (401), đã bỏ masothue.com dự phòng — got {len(_fake_requests.calls)} lượt gọi")
print("PASS 12: HTTP lỗi (vd 401 sai client-id/api-key) -> canh_bao=None (không suy đoán), vẫn tính "
      "vào bộ đếm lỗi liên tiếp, VÀ trả kèm ly_do_loi ghi rõ 'HTTP 401' để chẩn đoán đúng nguyên nhân.")

# ===== Test 12b (ca thật người dùng báo — lượt tra THẤT BẠI rồi gọi lại ngay
# sau đó, mô phỏng lần xuất Excel SAU, MST này giờ đã hoạt động bình thường
# trở lại): KHÔNG còn cache nên chắc chắn KHÔNG thể bị "kẹt cứng" ở kết quả
# thất bại cũ — PHẢI luôn thử gọi mạng lại thật sự. =====
_fake_requests.next_exc = None
_fake_requests.next_status = 401
_fake_requests.next_data = {"message": "Unauthorized"}
_fake_requests.calls.clear()
mst_that_bai = "0319998888"
r12b_lan1 = _tra_cuu_trang_thai_mst(mst_that_bai, timeout=1)   # lượt 1: thất bại (401)
assert r12b_lan1["canh_bao"] is None
_fake_requests.calls.clear()
_fake_requests.next_status = 200
_fake_requests.next_data = {"status": "Người nộp thuế đang hoạt động (đã cấp GCN ĐKT)"}
r12b_lan2 = _tra_cuu_trang_thai_mst(mst_that_bai, timeout=1)   # lượt 2: thử lại
assert r12b_lan2["canh_bao"] is False, (
    f"Lượt 2 PHẢI thử gọi mạng lại thật sự, không bị kẹt ở kết quả trống của lượt 1 thất bại trước đó "
    f"— got {r12b_lan2}")
assert len(_fake_requests.calls) == 1, (
    f"Lượt 2 phải THẬT SỰ gọi mạng (không có cache 'đã tra rồi' từ lượt 1 thất bại) "
    f"— got {len(_fake_requests.calls)} lượt gọi")
print("PASS 12b: lượt tra THẤT BẠI rồi gọi lại ngay sau đó -> luôn thử tra lại thật sự (không còn cache "
      "dài hạn nên chắc chắn không bị kẹt cứng ở trạng thái trống).")

# ===== Test 13-14: chi_dung_cache — ca thật người dùng báo tiếp "chạy lâu quá" với
# bảng kê ~992 hóa đơn nhiều trăm nhà cung cấp khác nhau: export_excel giới hạn
# _MST_NGAN_SACH_GIAY giây cho việc tra MST, hết ngân sách thì gọi với
# chi_dung_cache=True — TUYỆT ĐỐI không gọi mạng thêm cho MST đó trong lượt này (để
# trống an toàn), để cả lượt xuất Excel không bị "treo" vô hạn theo số lượng nhà
# cung cấp khác nhau. Không còn cache dài hạn để "dùng dự phòng" nữa — chi_dung_cache
# luôn nghĩa là để trống, bất kể MST này đã từng tra trước đó hay chưa. =====
_fake_requests.next_exc = None
_fake_requests.next_status = 200

# Test 13: chi_dung_cache=True + MST CHƯA từng tra trong lượt này -> KHÔNG gọi
# mạng, trả canh_bao=None (để trống, không suy đoán) — không chặn xuất Excel.
_fake_requests.calls.clear()
r13 = _tra_cuu_trang_thai_mst("0316888888", timeout=1, chi_dung_cache=True)
assert r13["canh_bao"] is None
assert len(_fake_requests.calls) == 0, (
    f"chi_dung_cache=True (đã hết ngân sách thời gian) -> TUYỆT ĐỐI không được gọi mạng "
    f"— got {len(_fake_requests.calls)} lượt gọi")
assert "ngân sách thời gian" in (r13.get("ly_do_loi") or ""), (
    f"PHẢI kèm ly_do_loi ghi rõ nguyên nhân 'hết ngân sách thời gian' — để người dùng biết TẠI SAO MST "
    f"này vẫn chưa dò được (đúng câu hỏi người dùng 'sao vẫn còn?') thay vì im lặng không rõ lý do "
    f"— got {r13}")
print("PASS 13: hết ngân sách thời gian (chi_dung_cache=True) -> để trống, không gọi mạng thêm (không "
      "làm treo lâu cả lượt xuất Excel), kèm ly_do_loi ghi rõ nguyên nhân.")

# Test 14 (đổi ý nghĩa sau khi bỏ hẳn cache): chi_dung_cache=True dù MST này ĐÃ
# từng tra THÀNH CÔNG trước đó (ở 1 lệnh gọi khác trong CÙNG lượt test này) ->
# vẫn phải để trống (canh_bao=None), KHÔNG được dùng lại kết quả cũ — vì không
# còn cache để "dự phòng" nữa (đúng yêu cầu người dùng "không cần lưu cứ dò ở
# thời điểm hiện tại").
_fake_requests.calls.clear()
_fake_requests.next_data = {"status": "Người nộp thuế đã bị khóa mã số thuế"}
r14a = _tra_cuu_trang_thai_mst("0316999999", timeout=1)   # tra bình thường trước, THÀNH CÔNG
assert r14a["canh_bao"] is True
_fake_requests.calls.clear()
r14b = _tra_cuu_trang_thai_mst("0316999999", timeout=1, chi_dung_cache=True)
assert r14b["canh_bao"] is None, (
    f"chi_dung_cache=True -> PHẢI để trống (không còn cache để dùng dự phòng nữa) — got {r14b}")
assert len(_fake_requests.calls) == 0, "chi_dung_cache=True TUYỆT ĐỐI không được gọi mạng dù đã tra thành công trước đó"
print("PASS 14: chi_dung_cache=True -> luôn để trống an toàn (không còn cache dài hạn để dùng dự phòng "
      "nữa), kể cả khi MST này đã từng tra thành công trước đó trong CÙNG lượt.")

# ===== Test 15-19: nhiều cặp client-id/api-key (yêu cầu người dùng: "hãy thử
# tạo thêm api thứ 2 tôi sẽ tạo thêm key để gắn vào hết key này có thể chạy
# qua key khác") — tự động CHUYỂN SANG key kế tiếp khi key đang dùng báo lỗi
# DO CHÍNH key đó (401 sai/hết hạn, hoặc 429 hết hạn mức gói riêng của key),
# nhưng KHÔNG chuyển key khi lỗi là lỗi CHUNG (HTTP khác/lỗi mạng — đổi key
# cũng vô ích). =====
_fake_time.sleeps.clear()

# Test 15 (QUAN TRỌNG): key 1 báo 401 (sai/hết hạn) -> PHẢI tự chuyển ngay
# sang key 2 trong CÙNG lượt gọi này, key 2 thành công -> trả đúng kết quả,
# không phải để trống/thất bại dù đã có key 2 dùng được.
_set_xinvoice_keys([{"client_id": "key1-id", "api_key": "key1-secret"},
                    {"client_id": "key2-id", "api_key": "key2-secret"}])
_fake_requests.calls.clear()
_fake_requests.next_exc = None
_fake_requests.next_responses = [
    (401, {"message": "Unauthorized"}, {}),
    (200, {"status": "Người nộp thuế đang hoạt động (đã cấp GCN ĐKT)"}, {}),
]
r15 = _tra_cuu_trang_thai_mst("0321111111", timeout=1)
assert r15["canh_bao"] is False, (
    f"Key 1 lỗi 401 nhưng key 2 dùng được -> PHẢI tự chuyển key NGAY và lấy được kết quả thật, "
    f"không được để trống — got {r15}")
assert len(_fake_requests.calls) == 2, (
    f"Phải thử ĐÚNG 2 lượt (key 1 thất bại rồi tự chuyển sang key 2) — got {len(_fake_requests.calls)}")
assert _fake_requests.calls[0]["headers"].get("client-id") == "key1-id", "Lượt 1 phải dùng key 1"
assert _fake_requests.calls[1]["headers"].get("client-id") == "key2-id", "Lượt 2 phải tự chuyển sang key 2"
assert ns['_XINVOICE_KEY_STATE']['idx'] == 1, (
    "Sau khi key 1 lỗi do CHÍNH key đó, phải NHỚ lại (idx=1) để các MST SAU bắt đầu ngay từ key 2, "
    "khỏi phải dò lại qua key 1 đã hỏng cho từng MST")
print("PASS 15: key 1 lỗi 401 (sai/hết hạn) -> tự động chuyển NGAY sang key 2 trong cùng lượt gọi, "
      "lấy được kết quả thật, đúng yêu cầu người dùng 'hết key này chạy qua key khác'.")

# Test 16: MST KHÁC tra tiếp ngay sau đó -> phải bắt đầu THẲNG từ key 2 (nhớ
# từ Test 15, idx=1), CHỈ 1 lượt gọi (không dò lại qua key 1 đã biết hỏng).
_fake_requests.calls.clear()
_fake_requests.next_responses = [
    (200, {"status": "Người nộp thuế đang hoạt động (đã cấp GCN ĐKT)"}, {}),
]
r16 = _tra_cuu_trang_thai_mst("0321111112", timeout=1)
assert r16["canh_bao"] is False
assert len(_fake_requests.calls) == 1, (
    f"Phải bắt đầu THẲNG từ key 2 (đã nhớ từ lần trước) -> chỉ 1 lượt gọi, không dò lại qua key 1 "
    f"đã biết hỏng — got {len(_fake_requests.calls)} lượt gọi")
assert _fake_requests.calls[0]["headers"].get("client-id") == "key2-id", (
    "Phải dùng THẲNG key 2 (nhớ từ lần chuyển key trước), không thử lại key 1")
print("PASS 16: MST khác tra ngay sau đó -> bắt đầu THẲNG từ key đang hoạt động (đã nhớ từ lần trước), "
      "không lãng phí lượt gọi dò lại qua key đã biết hỏng.")

# Test 17: CẢ 2 key đều hết hạn mức gói (429 quota) -> thử lần lượt cả 2 rồi
# thất bại HẲN (không lặp vô hạn), ly_do_loi phải nêu rõ đã thử CẢ 2 key.
_set_xinvoice_keys([{"client_id": "keyA-id", "api_key": "keyA-secret"},
                    {"client_id": "keyB-id", "api_key": "keyB-secret"}])
loi_quota = {"success": False,
            "error": "Exceeded free tier limit. Please try again later or upgrade your plan."}
_fake_requests.calls.clear()
_fake_requests.next_responses = [
    (429, loi_quota, {}),
    (429, loi_quota, {}),
]
r17 = _tra_cuu_trang_thai_mst("0321111113", timeout=1)
assert r17["canh_bao"] is None
assert len(_fake_requests.calls) == 2, (
    f"Phải thử ĐÚNG 2 key (mỗi key 1 lượt, hết hạn mức gói không chờ+thử lại), đã bỏ masothue.com dự "
    f"phòng nên thất bại hẳn ngay sau đó — got {len(_fake_requests.calls)}")
assert "2 key" in (r17.get("ly_do_loi") or ""), (
    f"ly_do_loi phải nêu rõ đã thử CẢ 2 key đều hết hạn mức để người dùng biết cần thêm key khác "
    f"— got {r17}")
print("PASS 17: cả 2 key đều hết hạn mức gói (429 quota) -> thử lần lượt từng key rồi thất bại hẳn "
      "(không lặp vô hạn, đã bỏ masothue.com dự phòng), ly_do_loi nêu rõ đã thử cả 2 key.")

# Test 18 (không hồi quy — QUAN TRỌNG): lỗi CHUNG (vd HTTP 404 — MST không
# tồn tại) KHÔNG PHẢI do lỗi của riêng 1 key -> KHÔNG được lãng phí thử key
# khác (đổi key cũng vô ích, tốn thêm lượt gọi API vô nghĩa).
_set_xinvoice_keys([{"client_id": "keyC-id", "api_key": "keyC-secret"},
                    {"client_id": "keyD-id", "api_key": "keyD-secret"}])
_fake_requests.calls.clear()
_fake_requests.next_responses = [(404, {"message": "Not Found"}, {})]
r18 = _tra_cuu_trang_thai_mst("0321111114", timeout=1)
assert r18["canh_bao"] is None
assert len(_fake_requests.calls) == 1, (
    f"Lỗi CHUNG (vd HTTP 404, không phải lỗi riêng của key) KHÔNG được thử key khác -> ĐÚNG 1 lượt gọi "
    f"XInvoice, đã bỏ masothue.com dự phòng nên thất bại hẳn ngay sau đó — got "
    f"{len(_fake_requests.calls)}")
assert "HTTP 404" in (r18.get("ly_do_loi") or ""), f"ly_do_loi phải ghi rõ HTTP 404 — got {r18}"
print("PASS 18: lỗi CHUNG (HTTP 404, không phải lỗi riêng của 1 key) -> KHÔNG lãng phí thử key XInvoice "
      "khác, chỉ ĐÚNG 1 lượt gọi rồi thất bại hẳn (đã bỏ masothue.com dự phòng).")

# Test 19 (không hồi quy): lỗi kết nối/mạng (exception) cũng là lỗi CHUNG ->
# tương tự Test 18, KHÔNG được thử key khác.
_fake_requests.calls.clear()
_fake_requests.next_responses = None
_fake_requests.next_exc = Exception("mạng lỗi giả lập")
r19 = _tra_cuu_trang_thai_mst("0321111115", timeout=1)
assert r19["canh_bao"] is None
assert len(_fake_requests.calls) == 1, (
    f"Lỗi kết nối/mạng (lỗi CHUNG, không phải lỗi riêng của key) KHÔNG được thử key XInvoice khác -> "
    f"chỉ ĐÚNG 1 lượt gọi XInvoice, đã bỏ masothue.com dự phòng nên thất bại hẳn ngay sau đó — got "
    f"{len(_fake_requests.calls)}")
assert "Lỗi kết nối" in (r19.get("ly_do_loi") or ""), f"ly_do_loi phải ghi rõ lỗi kết nối — got {r19}"
print("PASS 19: lỗi kết nối/mạng (lỗi CHUNG) -> KHÔNG lãng phí thử key XInvoice khác, chỉ ĐÚNG 1 lượt "
      "gọi rồi thất bại hẳn (đã bỏ masothue.com dự phòng).")
_fake_requests.next_exc = None

# ===== Test 20 (người dùng hỏi lại "sao vẫn còn?" sau khi thấy log báo N MST
# chưa lấy được tình trạng nhưng KHÔNG có dòng "VÍ DỤ LỖI GẶP PHẢI" nào —
# nguyên nhân: các MST đó rơi vào bộ đếm lỗi liên tiếp (circuit breaker) đã
# kích hoạt, nhánh này TRƯỚC ĐÂY hoàn toàn không ghi ly_do_loi, nên
# _prefetch_trang_thai_mst() không có gì để hiện làm ví dụ) — giờ nhánh này
# PHẢI kèm ly_do_loi rõ ràng để _prefetch_trang_thai_mst() còn hiện được
# "VÍ DỤ LỖI GẶP PHẢI" giải thích đúng nguyên nhân cho người dùng. =====
_set_xinvoice_keys([{"client_id": "keyF-id", "api_key": "keyF-secret"}])
dem_loi20 = [5]   # mô phỏng bộ đếm ĐÃ đạt ngưỡng 5 lỗi liên tiếp từ các MST trước đó
_fake_requests.calls.clear()
r20 = _tra_cuu_trang_thai_mst("0321111118", timeout=1, so_lan_that_bai_lien_tiep=dem_loi20)
assert r20["canh_bao"] is None
assert len(_fake_requests.calls) == 0, (
    f"Bộ đếm lỗi liên tiếp đã đạt ngưỡng -> KHÔNG được gọi mạng nữa (VietQR lẫn XInvoice) "
    f"— got {len(_fake_requests.calls)} lượt gọi")
assert "5 lỗi liên tiếp" in (r20.get("ly_do_loi") or ""), (
    f"PHẢI kèm ly_do_loi ghi rõ đã dừng do 5 lỗi liên tiếp — để _prefetch_trang_thai_mst() còn hiện "
    f"được 'VÍ DỤ LỖI GẶP PHẢI' giải thích đúng nguyên nhân cho người dùng (trước đây nhánh này im "
    f"lặng hoàn toàn, khiến log báo còn N MST chưa dò được nhưng KHÔNG có ví dụ lỗi nào kèm theo, "
    f"người dùng phải hỏi lại 'sao vẫn còn?') — got {r20}")
print("PASS 20: bộ đếm lỗi liên tiếp đã đạt ngưỡng (circuit breaker) -> giờ vẫn kèm ly_do_loi rõ ràng "
      "('đã dừng gọi mạng sau 5 lỗi liên tiếp') thay vì im lặng, để người dùng biết đúng nguyên nhân "
      "khi thấy MST còn trống.")

# ===== Test 21 (bug THẬT vừa phát hiện qua log người dùng gửi: "CHI TIẾT
# TỪNG MST" toàn "không rõ lý do" cho ĐỦ cả 8 MST, dù đã có log chẩn đoán chi
# tiết): _goi_1_lan_xinvoice() TRƯỚC ĐÂY coi HTTP 200 là "tra THÀNH CÔNG" dù
# trường "status" trả về KHÔNG khớp được tình trạng nào (canh_bao=None) —
# PHẢI coi là THẤT BẠI (không phải thành công rỗng), kèm ly_do_loi cụ thể
# (không rơi vào "không rõ lý do"). =====
_set_xinvoice_keys([{"client_id": "keyG-id", "api_key": "keyG-secret"}])
_fake_requests.calls.clear()
_fake_requests.next_exc = None
_fake_requests.next_responses = [
    (200, {"status": "Trạng thái không xác định XYZ"}, {}),
]
r21 = _tra_cuu_trang_thai_mst("0321111119", timeout=1)
assert r21["canh_bao"] is None
assert len(_fake_requests.calls) == 1, (
    f"HTTP 200 nhưng không khớp tình trạng nào -> PHẢI coi là thất bại (không phải thành công), đã bỏ "
    f"masothue.com dự phòng nên chỉ ĐÚNG 1 lượt gọi — got {len(_fake_requests.calls)} lượt gọi")
assert (r21.get("ly_do_loi") or "") and "không rõ lý do" not in (r21.get("ly_do_loi") or ""), (
    f"PHẢI kèm ly_do_loi cụ thể (vd 'XInvoice trả về 200 nhưng không xác định được tình trạng'), "
    f"KHÔNG được để trống/rơi vào 'không rõ lý do' — got {r21}")
print("PASS 21: XInvoice trả HTTP 200 nhưng 'status' không khớp tình trạng nào -> coi là THẤT BẠI "
      "(không phải thành công rỗng), kèm ly_do_loi cụ thể — sửa đúng bug thật khiến 8 MST bị 'kẹt cứng "
      "không rõ lý do'.")
_fake_requests.next_responses = None

print("\nALL DONE")
