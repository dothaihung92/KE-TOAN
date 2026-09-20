import os
import re
import json
import sqlite3
import tempfile
import datetime
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


ns = {'datetime': datetime, 'json': json, 'threading': threading}
exec(extract_fn('_khong_dau'), ns)
exec(extract_fn('_chuan_mst'), ns)
exec(extract_fn('_phan_loai_trang_thai_mst'), ns)
m = re.search(r'^_MST_CACHE_NGAY\s*=\s*\d+', src, re.M)
exec(m.group(0), ns)
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
exec(extract_fn('_tra_cuu_masothue'), ns)

_tmp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
_tmp_db.close()


def _fresh_db():
    conn = sqlite3.connect(_tmp_db.name, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS mst_status_cache (
        mst TEXT PRIMARY KEY, trang_thai_goc TEXT, canh_bao INTEGER, checked_at TEXT
    )""")
    return conn


ns['db'] = _fresh_db
# Stub 2 nguồn thử TRƯỚC XInvoice (VietQR rồi tracuunnt.gdt.gov.vn — xem
# _tra_cuu_trang_thai_mst) LUÔN thất bại: các test dưới đây kiểm tra hành vi
# RIÊNG của chuỗi XInvoice/masothue.com (cấu hình key, chuyển key, dự
# phòng...), không liên quan tới 2 nguồn đó — mỗi nguồn có test riêng
# (test_tra_mst_qua_vietqr.py / test_tra_mst_qua_tracuunnt.py).
ns['_tra_cuu_mst_qua_vietqr'] = lambda mst_c, timeout: (False, "", None, "stub: tắt trong test này")
ns['_tra_cuu_mst_qua_tracuunnt'] = lambda mst_c, timeout: (False, "", None, "stub: tắt trong test này")
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

_conn0 = _fresh_db()
_conn0.execute("DELETE FROM mst_status_cache")
_conn0.commit()
_conn0.close()

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

# ===== Test 7-13: _tra_cuu_trang_thai_mst() — luồng cấu hình + cache + gọi API (mock). =====

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

# Test 8a (QUAN TRỌNG — tính năng dự phòng masothue.com): CHƯA cấu hình
# client-id/api-key XInvoice nào -> KHÔNG còn "bỏ qua hẳn" như trước nữa, mà
# TỰ ĐỘNG dự phòng tra qua trang công khai masothue.com (không cần đăng ký),
# đúng yêu cầu người dùng "nếu api không tra được hết thì hãy tra qua
# masothue.com" — áp dụng cả khi HOÀN TOÀN chưa có key nào, không chỉ khi
# key đã cấu hình bị hết hạn mức.
_fake_settings.set("xinvoice_client_id", "")
_fake_settings.set("xinvoice_api_key", "")
_fake_settings.set("xinvoice_api_keys", "")
_fake_requests.calls.clear()
_fake_requests.next_exc = None
_fake_requests.next_responses = None
_fake_requests.next_status = 200
_fake_requests.next_data = {"status": "Người nộp thuế đã bị khóa mã số thuế"}
r8a = _tra_cuu_trang_thai_mst("0315696199", timeout=1)
assert r8a["canh_bao"] is True, (
    f"Chưa cấu hình key XInvoice nào -> PHẢI tự động dự phòng tra qua masothue.com, không được để "
    f"trống — got {r8a}")
assert len(_fake_requests.calls) == 1, (
    f"Chưa có key XInvoice -> 0 lượt gọi XInvoice, CHỈ gọi thẳng 1 lượt masothue.com dự phòng "
    f"— got {len(_fake_requests.calls)} lượt gọi")
assert "masothue.com" in _fake_requests.calls[0]["url"], (
    f"Phải gọi đúng masothue.com — got {_fake_requests.calls[0]['url']}")
print("PASS 8a: chưa cấu hình key XInvoice nào -> tự động dự phòng tra qua masothue.com, lấy được tình "
      "trạng thật thay vì để trống như trước.")

# Test 8b: chưa cấu hình key + masothue.com CŨNG không dò được (vd trang lỗi/
# không có dữ liệu MST) -> canh_bao=None (an toàn, không suy đoán), không lỗi/
# crash, không chặn xuất Excel — CẢ HAI cách đều không tra được mới chịu thua.
_fake_requests.calls.clear()
_fake_requests.next_status = 500
_fake_requests.next_data = None
r8b = _tra_cuu_trang_thai_mst("0315696188", timeout=1)
assert r8b["canh_bao"] is None
assert len(_fake_requests.calls) == 1, f"got {len(_fake_requests.calls)}"
print("PASS 8b: chưa cấu hình key XInvoice + masothue.com cũng lỗi -> canh_bao=None an toàn, không "
      "crash, không chặn xuất Excel.")

_fake_settings.set("xinvoice_client_id", "demo-client")
_fake_settings.set("xinvoice_api_key", "demo-key")
_fake_requests.next_status = 200
_fake_requests.next_data = None

# Test 9: cache MISS (đã có cấu hình) -> gọi API đúng 1 lần, đúng URL/header, phân
# loại đúng, LƯU vào cache.
_fake_requests.calls.clear()
_fake_requests.next_status = 200
_fake_requests.next_data = {"status": "Người nộp thuế đã bị khóa mã số thuế"}
r9 = _tra_cuu_trang_thai_mst("0315696133", timeout=1)
assert r9["canh_bao"] is True, f"Phải phân loại đúng từ trường 'status' trả về — got {r9}"
assert len(_fake_requests.calls) == 1, f"Cache MISS phải gọi API đúng 1 lần — got {len(_fake_requests.calls)}"
call = _fake_requests.calls[0]
assert call["url"] == "https://api.xinvoice.vn/gdt-api/tax-payer/0315696133", f"Sai URL — got {call['url']}"
assert call["headers"].get("client-id") == "demo-client"
assert call["headers"].get("api-key") == "demo-key"
print("PASS 9: cache MISS -> gọi đúng API XInvoice (URL + header client-id/api-key), phân loại đúng "
      "theo trường 'status'.")

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
# (đã cấu hình đúng 1 key XInvoice -> key đó hết hạn mức, rồi PHẢI tự động
# dự phòng qua masothue.com — ở đây masothue.com CŨNG lỗi, để giữ nguyên ý
# định gốc của test: xác nhận KHÔNG chờ+thử lại XInvoice vô ích, chỉ đúng 1
# lượt XInvoice + 1 lượt masothue dự phòng rồi mới chịu thua hẳn.)
_fake_requests.calls.clear()
_fake_time.sleeps.clear()
_fake_requests.next_exc = None
_fake_requests.next_responses = [
    (429, {"success": False,
          "error": "Exceeded free tier limit. Please try again later or upgrade your plan."}, {}),
    (500, {"message": "masothue loi"}, {}),
]
dem_loi_9c = [0]
r9c = _tra_cuu_trang_thai_mst("0388887777", timeout=1, so_lan_that_bai_lien_tiep=dem_loi_9c)
assert r9c["canh_bao"] is None
assert len(_fake_requests.calls) == 2, (
    f"429 HẾT HẠN MỨC GÓI KHÔNG được chờ+thử lại XInvoice (vô ích, hạn mức tính theo ngày/tháng) — chỉ "
    f"1 lượt gọi XInvoice, rồi tự động dự phòng thêm ĐÚNG 1 lượt masothue.com (ở đây cũng lỗi) — got "
    f"{len(_fake_requests.calls)} lượt gọi")
assert dem_loi_9c[0] == 1, "Vẫn phải tính vào bộ đếm lỗi liên tiếp để sớm dừng gọi mạng cho các MST còn lại"
assert "HẾT HẠN MỨC GÓI" in (r9c.get("ly_do_loi") or ""), (
    f"ly_do_loi phải ghi rõ 'HẾT HẠN MỨC GÓI' (khác hẳn 'hết hạn'/sai key) để người dùng tự biết đúng "
    f"nguyên nhân cần đợi gói làm mới hoặc nâng cấp trên xinvoice.vn — got {r9c}")
print("PASS 9c: 429 do HẾT HẠN MỨC GÓI (free tier, đúng nguyên văn lỗi thật người dùng gặp) -> nhận "
      "diện đúng, KHÔNG chờ+thử lại XInvoice vô ích, thất bại ngay rồi tự động dự phòng masothue.com "
      "(ở đây cũng lỗi), ly_do_loi ghi rõ nguyên nhân là hết hạn mức gói (không phải hết hạn/sai key).")
_fake_requests.next_responses = None
_fake_requests.next_status = 200   # trả về trạng thái mặc định cho các test sau
_fake_requests.next_data = None

# Test 10: cache HIT (vừa tra ở Test 9) -> KHÔNG gọi mạng lại, trả đúng kết quả đã lưu.
_fake_requests.calls.clear()
r10 = _tra_cuu_trang_thai_mst("0315696133", timeout=1)
assert r10["canh_bao"] is True
assert len(_fake_requests.calls) == 0, (
    f"MST đã tra cứu gần đây (còn trong hạn cache _MST_CACHE_NGAY ngày) KHÔNG được gọi lại API "
    f"— got {len(_fake_requests.calls)} lượt gọi")
print("PASS 10: cache HIT (MST vừa tra) -> không gọi lại API, dùng lại kết quả đã lưu (giảm số lượt "
      "gọi API có thể tính phí).")

# Test 11: cache đã QUÁ HẠN (checked_at cũ hơn _MST_CACHE_NGAY ngày) -> tra lại THẬT SỰ.
conn11 = _fresh_db()
qua_han = (datetime.datetime.now() - datetime.timedelta(days=ns['_MST_CACHE_NGAY'] + 1)).isoformat()
conn11.execute("UPDATE mst_status_cache SET checked_at=? WHERE mst=?", (qua_han, "0315696133"))
conn11.commit()
conn11.close()
_fake_requests.calls.clear()
_fake_requests.next_data = {"status": "Người nộp thuế đang hoạt động (đã cấp GCN ĐKT)"}
r11 = _tra_cuu_trang_thai_mst("0315696133", timeout=1)
assert r11["canh_bao"] is False, f"Sau khi tra lại, tình trạng đã đổi thành 'đang hoạt động' — got {r11}"
assert len(_fake_requests.calls) == 1, "Cache quá hạn PHẢI tra lại thật sự (gọi API lại)"
print("PASS 11: cache đã quá hạn (_MST_CACHE_NGAY ngày) -> tự động tra lại thật sự, cập nhật kết quả "
      "mới.")

# Test 12 (an toàn/không hồi quy — QUAN TRỌNG): lỗi mạng/API (mất kết nối/timeout/sai
# client-id-api-key -> 401) -> KHÔNG được crash, trả canh_bao=None (không suy đoán khi
# không tra cứu được), và bộ đếm lỗi liên tiếp phải hoạt động: sau nhiều lỗi liên tiếp
# trong CÙNG 1 lượt xuất Excel, DỪNG gọi API cho các MST còn lại (tránh treo lâu vì
# hàng loạt MST timeout/401 liên tục).
conn12 = _fresh_db()
conn12.execute("DELETE FROM mst_status_cache")
conn12.commit()
conn12.close()
_fake_requests.calls.clear()
_fake_requests.next_data = None
_fake_requests.next_exc = Exception("mạng lỗi giả lập")
dem_loi = [0]
ket_qua_12 = []
for i in range(8):
    mst_gia = f"031569613{i % 10}"  # nhiều MST khác nhau -> không trùng cache
    ket_qua_12.append(_tra_cuu_trang_thai_mst(mst_gia + "0", timeout=1, so_lan_that_bai_lien_tiep=dem_loi))
assert all(kq["canh_bao"] is None for kq in ket_qua_12), (
    "Lỗi mạng KHÔNG được crash và KHÔNG được suy đoán canh_bao — phải luôn là None")
# Mỗi lượt lỗi (trước khi bộ đếm đạt 5) giờ làm ĐÚNG 2 lượt gọi mạng thật: 1
# lượt XInvoice (lỗi) + 1 lượt masothue.com dự phòng (cũng lỗi, vì next_exc
# áp dụng cho MỌI lượt gọi) -> 5 lượt lỗi liên tiếp x 2 = 10 lượt gọi thật,
# rồi bộ đếm đạt 5 mới NGỪNG hẳn (3 lượt còn lại không gọi mạng nữa).
assert len(_fake_requests.calls) == 10, (
    f"Sau ĐÚNG 5 lượt lỗi liên tiếp (mỗi lượt thử cả XInvoice lẫn masothue.com dự phòng, 2 lượt gọi "
    f"mạng/lượt) phải NGỪNG gọi mạng cho các MST còn lại trong lượt này (tránh treo lâu vì hàng loạt "
    f"timeout) — got {len(_fake_requests.calls)} lượt gọi thật (kỳ vọng đúng 10)")
assert all("Lỗi kết nối" in (kq.get("ly_do_loi") or "") for kq in ket_qua_12[:5]), (
    f"Mỗi lượt lỗi kết nối THẬT SỰ (5 lượt đầu, trước khi ngừng gọi mạng) phải kèm ly_do_loi cụ thể để "
    f"người dùng biết nguyên nhân thật (không chỉ thấy trống không rõ vì sao) — got {ket_qua_12[:5]}")
print("PASS 12: lỗi mạng không làm crash (canh_bao=None, an toàn), dừng hẳn việc gọi API sau 5 lỗi "
      "liên tiếp trong cùng 1 lượt xuất Excel, và mỗi lượt lỗi đều kèm ly_do_loi cụ thể để chẩn đoán.")

# Test 13 (không hồi quy — QUAN TRỌNG): status HTTP khác 200 (vd 401 sai client-id/
# api-key) -> KHÔNG suy đoán tình trạng (canh_bao=None), vẫn tính là 1 lượt lỗi cho bộ
# đếm liên tiếp, VÀ trả kèm ly_do_loi ghi rõ "HTTP 401" để người dùng tự biết đây là do
# client-id/api-key sai/hết hạn — đúng câu hỏi người dùng đã hỏi "này là do api hết hạn
# nên chặn phải không".
_fake_requests.next_exc = None
_fake_requests.next_status = 401
_fake_requests.next_data = {"message": "Unauthorized"}
_fake_requests.calls.clear()
dem_loi2 = [0]
r13 = _tra_cuu_trang_thai_mst("0311111111", timeout=1, so_lan_that_bai_lien_tiep=dem_loi2)
assert r13["canh_bao"] is None, f"HTTP 401 (sai key) KHÔNG được suy đoán tình trạng — got {r13}"
assert dem_loi2[0] == 1, f"HTTP lỗi vẫn phải tính vào bộ đếm lỗi liên tiếp — got {dem_loi2[0]}"
assert "HTTP 401" in (r13.get("ly_do_loi") or ""), (
    f"Phải trả kèm ly_do_loi ghi rõ mã lỗi HTTP thật (401) để người dùng tự chẩn đoán được nguyên nhân "
    f"— got {r13}")
assert len(_fake_requests.calls) == 2, (
    f"1 lượt XInvoice (401) rồi tự động dự phòng thêm 1 lượt masothue.com (ở đây cũng trả 401, mặc "
    f"định của fake) — got {len(_fake_requests.calls)} lượt gọi")
print("PASS 13: HTTP lỗi (vd 401 sai client-id/api-key) -> canh_bao=None (không suy đoán), vẫn tính "
      "vào bộ đếm lỗi liên tiếp, VÀ trả kèm ly_do_loi ghi rõ 'HTTP 401' để chẩn đoán đúng nguyên nhân "
      "(sau khi đã thử dự phòng masothue.com cũng không được).")

# ===== Test 13b (ca thật người dùng báo — CỰC KỲ QUAN TRỌNG, bug thật): lượt tra THẤT
# BẠI (lỗi mạng/HTTP lỗi) KHÔNG được lưu vào cache DB — trước đây LUÔN lưu cache dù
# thành công hay thất bại, khiến 1 MST lỡ gặp lỗi 1 lần bị "kẹt cứng" ở trạng thái trống
# suốt 14 ngày (lần xuất Excel SAU đọc trúng cache "trống" đó, KHÔNG thử lại nữa dù còn
# nguyên ngân sách thời gian) — đúng log thật người dùng gửi: xuất Excel LẦN 2 chỉ mất
# 0.4 giây cho 234 MST (quá nhanh, toàn cache hit) nhưng VẪN ĐÚNG 34 MST không dò được y
# hệt lần 1, và KHÔNG hề in ra "VÍ DỤ LỖI GẶP PHẢI" nào (vì được trả thẳng từ cache, không
# hề thử gọi mạng lại trong lượt 2) — "sẽ tự bổ sung ở lần xuất Excel sau" đã KHÔNG XẢY RA
# THẬT như đã hứa với người dùng. =====
conn13b = _fresh_db()
conn13b.execute("DELETE FROM mst_status_cache")
conn13b.commit()
conn13b.close()
_fake_requests.next_exc = None
_fake_requests.next_status = 401
_fake_requests.next_data = {"message": "Unauthorized"}
_fake_requests.calls.clear()
mst_that_bai = "0319998888"
r13b_lan1 = _tra_cuu_trang_thai_mst(mst_that_bai, timeout=1)   # lượt 1: thất bại (401)
assert r13b_lan1["canh_bao"] is None
conn13b2 = _fresh_db()
row13b = conn13b2.execute(
    "SELECT * FROM mst_status_cache WHERE mst=?", (ns['_chuan_mst'](mst_that_bai)[:10],)).fetchone()
conn13b2.close()
assert row13b is None, (
    f"Lượt tra THẤT BẠI KHÔNG được lưu vào bảng mst_status_cache (để lần sau còn thử lại được) "
    f"— got 1 dòng cache: {dict(row13b) if row13b else None}")
# Lượt 2 (mô phỏng lần xuất Excel SAU, MST này giờ đã hoạt động bình thường trở lại) ->
# PHẢI thử gọi mạng lại THẬT SỰ (không bị "kẹt cứng" trả về cache trống của lượt 1).
_fake_requests.calls.clear()
_fake_requests.next_status = 200
_fake_requests.next_data = {"status": "Người nộp thuế đang hoạt động (đã cấp GCN ĐKT)"}
r13b_lan2 = _tra_cuu_trang_thai_mst(mst_that_bai, timeout=1)
assert r13b_lan2["canh_bao"] is False, (
    f"Lượt 2 (lần xuất Excel SAU) PHẢI thử gọi mạng lại thật sự, không bị kẹt ở kết quả trống của "
    f"lượt 1 thất bại trước đó — got {r13b_lan2}")
assert len(_fake_requests.calls) == 1, (
    f"Lượt 2 phải THẬT SỰ gọi mạng (không được coi là 'đã tra rồi' từ cache của lượt 1 thất bại) "
    f"— got {len(_fake_requests.calls)} lượt gọi")
print("PASS 13b: lượt tra THẤT BẠI (lỗi mạng/HTTP lỗi) KHÔNG bị lưu vào cache 14 ngày — lần xuất Excel "
      "SAU vẫn thử tra lại thật sự (đúng như đã hứa 'sẽ tự bổ sung ở lần xuất Excel sau'), không còn bị "
      "kẹt cứng ở trạng thái trống.")

# ===== Test 14-15: chi_dung_cache — ca thật người dùng báo tiếp "chạy lâu quá" với
# bảng kê ~992 hóa đơn nhiều trăm nhà cung cấp khác nhau: export_excel giới hạn
# _MST_NGAN_SACH_GIAY giây cho việc tra MST MỚI, hết ngân sách thì gọi với
# chi_dung_cache=True — CHỈ dùng cache đã có (kể cả quá hạn), TUYỆT ĐỐI không gọi
# mạng thêm, để cả lượt xuất Excel không bị "treo" vô hạn theo số lượng nhà cung
# cấp khác nhau. =====
_fake_requests.next_exc = None
_fake_requests.next_status = 200

# Test 14: chi_dung_cache=True + MST CHƯA từng có cache -> KHÔNG gọi mạng, trả
# canh_bao=None (để trống, không suy đoán) — không chặn xuất Excel.
conn14 = _fresh_db()
conn14.execute("DELETE FROM mst_status_cache")
conn14.commit()
conn14.close()
_fake_requests.calls.clear()
r14 = _tra_cuu_trang_thai_mst("0316888888", timeout=1, chi_dung_cache=True)
assert r14["canh_bao"] is None
assert len(_fake_requests.calls) == 0, (
    f"chi_dung_cache=True (đã hết ngân sách thời gian) + MST chưa từng tra -> TUYỆT ĐỐI không được gọi "
    f"mạng — got {len(_fake_requests.calls)} lượt gọi")
assert "ngân sách thời gian" in (r14.get("ly_do_loi") or ""), (
    f"PHẢI kèm ly_do_loi ghi rõ nguyên nhân 'hết ngân sách thời gian' — để người dùng biết TẠI SAO MST "
    f"này vẫn chưa dò được (đúng câu hỏi người dùng 'sao vẫn còn?') thay vì im lặng không rõ lý do "
    f"— got {r14}")
print("PASS 14: hết ngân sách thời gian (chi_dung_cache=True) + MST chưa từng tra -> để trống, không "
      "gọi mạng thêm (không làm treo lâu cả lượt xuất Excel), kèm ly_do_loi ghi rõ nguyên nhân.")

# Test 15: chi_dung_cache=True + MST ĐÃ có cache (dù cache đã QUÁ HẠN _MST_CACHE_NGAY
# ngày) -> vẫn dùng cache cũ đó làm dự phòng (còn hơn để trống), KHÔNG gọi mạng.
_fake_requests.calls.clear()
_fake_requests.next_data = {"status": "Người nộp thuế đã bị khóa mã số thuế"}
r15a = _tra_cuu_trang_thai_mst("0316999999", timeout=1)   # tra bình thường trước để có cache
assert r15a["canh_bao"] is True
qua_han15 = (datetime.datetime.now() - datetime.timedelta(days=ns['_MST_CACHE_NGAY'] + 5)).isoformat()
conn15 = _fresh_db()
conn15.execute("UPDATE mst_status_cache SET checked_at=? WHERE mst=?", (qua_han15, "0316999999"))
conn15.commit()
conn15.close()
_fake_requests.calls.clear()
r15b = _tra_cuu_trang_thai_mst("0316999999", timeout=1, chi_dung_cache=True)
assert r15b["canh_bao"] is True, (
    f"chi_dung_cache=True nhưng ĐÃ có cache cũ (dù quá hạn) -> phải dùng cache cũ làm dự phòng, "
    f"không được để trống — got {r15b}")
assert len(_fake_requests.calls) == 0, "chi_dung_cache=True TUYỆT ĐỐI không được gọi mạng dù cache quá hạn"
print("PASS 15: hết ngân sách thời gian nhưng MST đã có cache cũ (dù quá hạn 14 ngày) -> vẫn dùng cache "
      "cũ làm dự phòng thay vì để trống, không gọi mạng thêm.")

# ===== Test 16-20: nhiều cặp client-id/api-key (yêu cầu người dùng: "hãy thử
# tạo thêm api thứ 2 tôi sẽ tạo thêm key để gắn vào hết key này có thể chạy
# qua key khác") — tự động CHUYỂN SANG key kế tiếp khi key đang dùng báo lỗi
# DO CHÍNH key đó (401 sai/hết hạn, hoặc 429 hết hạn mức gói riêng của key),
# nhưng KHÔNG chuyển key khi lỗi là lỗi CHUNG (HTTP khác/lỗi mạng — đổi key
# cũng vô ích). =====
_fake_time.sleeps.clear()

# Test 16 (QUAN TRỌNG): key 1 báo 401 (sai/hết hạn) -> PHẢI tự chuyển ngay
# sang key 2 trong CÙNG lượt gọi này, key 2 thành công -> trả đúng kết quả,
# không phải để trống/thất bại dù đã có key 2 dùng được.
conn16 = _fresh_db()
conn16.execute("DELETE FROM mst_status_cache")
conn16.commit()
conn16.close()
_set_xinvoice_keys([{"client_id": "key1-id", "api_key": "key1-secret"},
                    {"client_id": "key2-id", "api_key": "key2-secret"}])
_fake_requests.calls.clear()
_fake_requests.next_exc = None
_fake_requests.next_responses = [
    (401, {"message": "Unauthorized"}, {}),
    (200, {"status": "Người nộp thuế đang hoạt động (đã cấp GCN ĐKT)"}, {}),
]
r16 = _tra_cuu_trang_thai_mst("0321111111", timeout=1)
assert r16["canh_bao"] is False, (
    f"Key 1 lỗi 401 nhưng key 2 dùng được -> PHẢI tự chuyển key NGAY và lấy được kết quả thật, "
    f"không được để trống — got {r16}")
assert len(_fake_requests.calls) == 2, (
    f"Phải thử ĐÚNG 2 lượt (key 1 thất bại rồi tự chuyển sang key 2) — got {len(_fake_requests.calls)}")
assert _fake_requests.calls[0]["headers"].get("client-id") == "key1-id", "Lượt 1 phải dùng key 1"
assert _fake_requests.calls[1]["headers"].get("client-id") == "key2-id", "Lượt 2 phải tự chuyển sang key 2"
assert ns['_XINVOICE_KEY_STATE']['idx'] == 1, (
    "Sau khi key 1 lỗi do CHÍNH key đó, phải NHỚ lại (idx=1) để các MST SAU bắt đầu ngay từ key 2, "
    "khỏi phải dò lại qua key 1 đã hỏng cho từng MST")
print("PASS 16: key 1 lỗi 401 (sai/hết hạn) -> tự động chuyển NGAY sang key 2 trong cùng lượt gọi, "
      "lấy được kết quả thật, đúng yêu cầu người dùng 'hết key này chạy qua key khác'.")

# Test 17: MST KHÁC (chưa có cache) tra tiếp ngay sau đó -> phải bắt đầu THẲNG
# từ key 2 (nhớ từ Test 16, idx=1), CHỈ 1 lượt gọi (không dò lại qua key 1
# đã biết hỏng).
_fake_requests.calls.clear()
_fake_requests.next_responses = [
    (200, {"status": "Người nộp thuế đang hoạt động (đã cấp GCN ĐKT)"}, {}),
]
r17 = _tra_cuu_trang_thai_mst("0321111112", timeout=1)
assert r17["canh_bao"] is False
assert len(_fake_requests.calls) == 1, (
    f"Phải bắt đầu THẲNG từ key 2 (đã nhớ từ lần trước) -> chỉ 1 lượt gọi, không dò lại qua key 1 "
    f"đã biết hỏng — got {len(_fake_requests.calls)} lượt gọi")
assert _fake_requests.calls[0]["headers"].get("client-id") == "key2-id", (
    "Phải dùng THẲNG key 2 (nhớ từ lần chuyển key trước), không thử lại key 1")
print("PASS 17: MST khác tra ngay sau đó -> bắt đầu THẲNG từ key đang hoạt động (đã nhớ từ lần trước), "
      "không lãng phí lượt gọi dò lại qua key đã biết hỏng.")

# Test 18: CẢ 2 key đều hết hạn mức gói (429 quota) -> thử lần lượt cả 2 rồi
# thất bại HẲN (không lặp vô hạn), ly_do_loi phải nêu rõ đã thử CẢ 2 key.
conn18 = _fresh_db()
conn18.execute("DELETE FROM mst_status_cache")
conn18.commit()
conn18.close()
_set_xinvoice_keys([{"client_id": "keyA-id", "api_key": "keyA-secret"},
                    {"client_id": "keyB-id", "api_key": "keyB-secret"}])
loi_quota = {"success": False,
            "error": "Exceeded free tier limit. Please try again later or upgrade your plan."}
_fake_requests.calls.clear()
_fake_requests.next_responses = [
    (429, loi_quota, {}),
    (429, loi_quota, {}),
    (500, {"message": "masothue loi"}, {}),
]
r18 = _tra_cuu_trang_thai_mst("0321111113", timeout=1)
assert r18["canh_bao"] is None
assert len(_fake_requests.calls) == 3, (
    f"Phải thử ĐÚNG 2 key (mỗi key 1 lượt, hết hạn mức gói không chờ+thử lại) rồi tự động dự phòng "
    f"thêm ĐÚNG 1 lượt masothue.com (ở đây cũng lỗi) — got {len(_fake_requests.calls)}")
assert "2 key" in (r18.get("ly_do_loi") or ""), (
    f"ly_do_loi phải nêu rõ đã thử CẢ 2 key đều hết hạn mức để người dùng biết cần thêm key khác "
    f"— got {r18}")
print("PASS 18: cả 2 key đều hết hạn mức gói (429 quota) -> thử lần lượt từng key, rồi tự động dự "
      "phòng thêm masothue.com (ở đây cũng lỗi) rồi mới thất bại hẳn (không lặp vô hạn), ly_do_loi "
      "nêu rõ đã thử cả 2 key.")

# Test 19 (không hồi quy — QUAN TRỌNG): lỗi CHUNG (vd HTTP 404 — MST không
# tồn tại) KHÔNG PHẢI do lỗi của riêng 1 key -> KHÔNG được lãng phí thử key
# khác (đổi key cũng vô ích, tốn thêm lượt gọi API vô nghĩa).
conn19 = _fresh_db()
conn19.execute("DELETE FROM mst_status_cache")
conn19.commit()
conn19.close()
_set_xinvoice_keys([{"client_id": "keyC-id", "api_key": "keyC-secret"},
                    {"client_id": "keyD-id", "api_key": "keyD-secret"}])
_fake_requests.calls.clear()
_fake_requests.next_responses = [(404, {"message": "Not Found"}, {}), (500, {"message": "masothue loi"}, {})]
r19 = _tra_cuu_trang_thai_mst("0321111114", timeout=1)
assert r19["canh_bao"] is None
assert len(_fake_requests.calls) == 2, (
    f"Lỗi CHUNG (vd HTTP 404, không phải lỗi riêng của key) KHÔNG được thử key khác -> chỉ 1 lượt gọi "
    f"XInvoice, rồi tự động dự phòng thêm 1 lượt masothue.com (ở đây cũng lỗi) — got "
    f"{len(_fake_requests.calls)}")
assert "HTTP 404" in (r19.get("ly_do_loi") or ""), f"ly_do_loi phải ghi rõ HTTP 404 — got {r19}"
print("PASS 19: lỗi CHUNG (HTTP 404, không phải lỗi riêng của 1 key) -> KHÔNG lãng phí thử key XInvoice "
      "khác, chỉ 1 lượt gọi, rồi vẫn tự động dự phòng masothue.com (ở đây cũng lỗi) trước khi thất bại "
      "hẳn.")

# Test 20 (không hồi quy): lỗi kết nối/mạng (exception) cũng là lỗi CHUNG ->
# tương tự Test 19, KHÔNG được thử key khác.
conn20 = _fresh_db()
conn20.execute("DELETE FROM mst_status_cache")
conn20.commit()
conn20.close()
_fake_requests.calls.clear()
_fake_requests.next_responses = None
_fake_requests.next_exc = Exception("mạng lỗi giả lập")
r20 = _tra_cuu_trang_thai_mst("0321111115", timeout=1)
assert r20["canh_bao"] is None
assert len(_fake_requests.calls) == 2, (
    f"Lỗi kết nối/mạng (lỗi CHUNG, không phải lỗi riêng của key) KHÔNG được thử key XInvoice khác -> "
    f"chỉ 1 lượt gọi XInvoice, rồi tự động dự phòng thêm 1 lượt masothue.com (ở đây cũng lỗi kết nối "
    f"y hệt, vì next_exc áp dụng cho mọi lượt gọi) — got {len(_fake_requests.calls)}")
assert "Lỗi kết nối" in (r20.get("ly_do_loi") or ""), f"ly_do_loi phải ghi rõ lỗi kết nối — got {r20}"
print("PASS 20: lỗi kết nối/mạng (lỗi CHUNG) -> KHÔNG lãng phí thử key XInvoice khác, chỉ 1 lượt gọi "
      "XInvoice, vẫn tự động dự phòng thêm masothue.com trước khi thất bại hẳn.")
_fake_requests.next_exc = None

# ===== Test 21-22 (CHÍNH tính năng vừa yêu cầu người dùng — "hãy chỉnh thêm
# nếu api khong tra được hết thì hãy tra qua masothue.com", đúng log thật:
# "17 MST chưa lấy được tình trạng... ĐÃ HẾT HẠN MỨC/SAI cả 2 key đã cấu
# hình"): khi API XInvoice đã cấu hình nhưng KHÔNG dùng được (hết hạn mức/
# lỗi), tự động DỰ PHÒNG qua masothue.com thay vì chịu để trống. =====

# Test 21 (QUAN TRỌNG — đúng ca thật): đã cấu hình 1 key XInvoice nhưng HẾT
# HẠN MỨC GÓI (429 quota) -> PHẢI tự động dự phòng qua masothue.com và LẤY
# ĐƯỢC kết quả thật (thay vì để trống như trước khi có tính năng dự phòng
# này), và kết quả dự phòng thành công đó PHẢI được lưu cache bình thường.
conn21 = _fresh_db()
conn21.execute("DELETE FROM mst_status_cache")
conn21.commit()
conn21.close()
_set_xinvoice_keys([{"client_id": "keyE-id", "api_key": "keyE-secret"}])
_fake_requests.calls.clear()
_fake_requests.next_exc = None
_fake_requests.next_responses = [
    (429, loi_quota, {}),
    (200, {"status": "Người nộp thuế đang hoạt động (đã cấp GCN ĐKT)"}, {}),
]
r21 = _tra_cuu_trang_thai_mst("0321111116", timeout=1)
assert r21["canh_bao"] is False, (
    f"XInvoice hết hạn mức gói -> PHẢI tự động dự phòng masothue.com và lấy được tình trạng thật, "
    f"không được để trống — got {r21}")
assert len(_fake_requests.calls) == 2, (
    f"Phải thử 1 lượt XInvoice (hết hạn mức) rồi 1 lượt masothue.com dự phòng — got "
    f"{len(_fake_requests.calls)}")
assert "masothue.com" in _fake_requests.calls[1]["url"], "Lượt 2 phải là gọi masothue.com dự phòng"
assert "ly_do_loi" not in r21, (
    f"Đã lấy được kết quả thật từ masothue.com (dự phòng thành công) -> KHÔNG được còn báo ly_do_loi "
    f"(đã có dữ liệu thật, không còn là lỗi nữa) — got {r21}")
conn21b = _fresh_db()
row21 = conn21b.execute("SELECT * FROM mst_status_cache WHERE mst=?", ("0321111116",)).fetchone()
conn21b.close()
assert row21 is not None and bool(row21["canh_bao"]) is False, (
    "Kết quả dự phòng thành công từ masothue.com PHẢI được lưu cache như bình thường")
print("PASS 21: XInvoice hết hạn mức gói (429 quota, đúng ca thật người dùng báo) -> tự động dự phòng "
      "tra qua masothue.com và lấy được tình trạng thật, không còn để trống nữa, đúng yêu cầu người "
      "dùng 'nếu api không tra được hết thì hãy tra qua masothue.com'; kết quả dự phòng cũng được lưu "
      "cache bình thường.")

# Test 22 (không hồi quy — QUAN TRỌNG): dự phòng masothue.com trả về HTTP 200
# nhưng NỘI DUNG không khớp được tình trạng nào (trang lỗi/đổi cấu trúc/MST
# không có dữ liệu) -> PHẢI coi là THẤT BẠI (không suy đoán canh_bao=True/
# False bừa), và KHÔNG được lưu cache (tránh lặp lại đúng bug "kẹt cứng" 34
# MST đã gặp trước đây với nguồn XInvoice).
conn22 = _fresh_db()
conn22.execute("DELETE FROM mst_status_cache")
conn22.commit()
conn22.close()
_fake_requests.calls.clear()
_fake_requests.next_responses = [
    (404, {"message": "Not Found"}, {}),
    (200, {"noi_dung": "trang khong co du lieu khop mst nao"}, {}),
]
r22 = _tra_cuu_trang_thai_mst("0321111117", timeout=1)
assert r22["canh_bao"] is None
assert len(_fake_requests.calls) == 2
conn22b = _fresh_db()
row22 = conn22b.execute("SELECT * FROM mst_status_cache WHERE mst=?", ("0321111117",)).fetchone()
conn22b.close()
assert row22 is None, (
    f"Dự phòng masothue.com trả 200 nhưng KHÔNG khớp tình trạng nào -> phải coi là thất bại, KHÔNG lưu "
    f"cache (tránh lặp lại bug 'kẹt cứng' đã sửa trước đây) — got {dict(row22) if row22 else None}")
print("PASS 22: dự phòng masothue.com trả về nội dung không khớp tình trạng nào -> coi là thất bại an "
      "toàn (canh_bao=None), KHÔNG lưu cache để còn thử lại lần sau.")
_fake_requests.next_responses = None

# ===== Test 23 (người dùng hỏi lại "sao vẫn còn?" sau khi thấy log báo N MST
# chưa lấy được tình trạng nhưng KHÔNG có dòng "VÍ DỤ LỖI GẶP PHẢI" nào —
# nguyên nhân: các MST đó rơi vào bộ đếm lỗi liên tiếp (circuit breaker) đã
# kích hoạt, nhánh này TRƯỚC ĐÂY hoàn toàn không ghi ly_do_loi, nên
# _prefetch_trang_thai_mst() không có gì để hiện làm ví dụ) — giờ nhánh này
# PHẢI kèm ly_do_loi rõ ràng để _prefetch_trang_thai_mst() còn hiện được
# "VÍ DỤ LỖI GẶP PHẢI" giải thích đúng nguyên nhân cho người dùng. =====
conn23 = _fresh_db()
conn23.execute("DELETE FROM mst_status_cache")
conn23.commit()
conn23.close()
_set_xinvoice_keys([{"client_id": "keyF-id", "api_key": "keyF-secret"}])
dem_loi23 = [5]   # mô phỏng bộ đếm ĐÃ đạt ngưỡng 5 lỗi liên tiếp từ các MST trước đó
_fake_requests.calls.clear()
r23 = _tra_cuu_trang_thai_mst("0321111118", timeout=1, so_lan_that_bai_lien_tiep=dem_loi23)
assert r23["canh_bao"] is None
assert len(_fake_requests.calls) == 0, (
    f"Bộ đếm lỗi liên tiếp đã đạt ngưỡng -> KHÔNG được gọi mạng nữa (cả XInvoice lẫn masothue.com) "
    f"— got {len(_fake_requests.calls)} lượt gọi")
assert "5 lỗi liên tiếp" in (r23.get("ly_do_loi") or ""), (
    f"PHẢI kèm ly_do_loi ghi rõ đã dừng do 5 lỗi liên tiếp — để _prefetch_trang_thai_mst() còn hiện "
    f"được 'VÍ DỤ LỖI GẶP PHẢI' giải thích đúng nguyên nhân cho người dùng (trước đây nhánh này im "
    f"lặng hoàn toàn, khiến log báo còn N MST chưa dò được nhưng KHÔNG có ví dụ lỗi nào kèm theo, "
    f"người dùng phải hỏi lại 'sao vẫn còn?') — got {r23}")
print("PASS 23: bộ đếm lỗi liên tiếp đã đạt ngưỡng (circuit breaker) -> giờ vẫn kèm ly_do_loi rõ ràng "
      "('đã dừng gọi mạng sau 5 lỗi liên tiếp') thay vì im lặng, để người dùng biết đúng nguyên nhân "
      "khi thấy MST còn trống.")

# ===== Test 24-25 (bug THẬT vừa phát hiện qua log người dùng gửi: "CHI TIẾT
# TỪNG MST" toàn "không rõ lý do" cho ĐỦ cả 8 MST, dù đã có log chẩn đoán chi
# tiết — thời gian chạy CHỈ 6.0s cho 234 MST, quá nhanh so với gọi mạng thật
# -> dấu hiệu CACHE HIT, không hề thử mạng lại): _goi_1_lan_xinvoice() TRƯỚC
# ĐÂY coi HTTP 200 là "tra THÀNH CÔNG" dù trường "status" trả về KHÔNG khớp
# được tình trạng nào (canh_bao=None) — LƯU CACHE kết quả rỗng đó, khiến MST
# "kẹt cứng" y hệt bug cache-khi-thất-bại đã sửa trước đây, nhưng qua đường
# 200 "thành công rỗng" thay vì lỗi HTTP nên KHÔNG đi qua nhánh có ly_do_loi
# -> cache-hit lần sau trả thẳng {"trang_thai":"","canh_bao":None} không kèm
# ly_do_loi -> _prefetch_trang_thai_mst() phải tự điền "không rõ lý do". =====

# Test 24: XInvoice trả 200 nhưng "status" KHÔNG khớp từ khoá nào (canh_bao=
# None) -> PHẢI coi là THẤT BẠI (không phải thành công), tự động dự phòng
# masothue.com (ở đây cũng không khớp) -> canh_bao=None, ly_do_loi PHẢI ghi
# rõ nguyên nhân (không phải "không rõ lý do"), và TUYỆT ĐỐI KHÔNG được lưu
# cache (để lần sau còn thử lại, không bị kẹt cứng suốt 14 ngày).
conn24 = _fresh_db()
conn24.execute("DELETE FROM mst_status_cache")
conn24.commit()
conn24.close()
_set_xinvoice_keys([{"client_id": "keyG-id", "api_key": "keyG-secret"}])
_fake_requests.calls.clear()
_fake_requests.next_exc = None
_fake_requests.next_responses = [
    (200, {"status": "Trạng thái không xác định XYZ"}, {}),
    (200, {"noi_dung": "trang masothue cung khong khop"}, {}),
]
r24 = _tra_cuu_trang_thai_mst("0321111119", timeout=1)
assert r24["canh_bao"] is None
assert len(_fake_requests.calls) == 2, (
    f"HTTP 200 nhưng không khớp tình trạng nào -> PHẢI coi là thất bại (không phải thành công), tự "
    f"động dự phòng thêm 1 lượt masothue.com — got {len(_fake_requests.calls)} lượt gọi")
assert (r24.get("ly_do_loi") or "") and "không rõ lý do" not in (r24.get("ly_do_loi") or ""), (
    f"PHẢI kèm ly_do_loi cụ thể (vd 'XInvoice trả về 200 nhưng không xác định được tình trạng'), "
    f"KHÔNG được để trống/rơi vào 'không rõ lý do' — got {r24}")
conn24b = _fresh_db()
row24 = conn24b.execute("SELECT * FROM mst_status_cache WHERE mst=?", ("0321111119",)).fetchone()
conn24b.close()
assert row24 is None, (
    f"HTTP 200 'thành công rỗng' (không khớp tình trạng nào) TUYỆT ĐỐI KHÔNG được lưu cache — nếu "
    f"không sẽ tái diễn đúng bug 'kẹt cứng 14 ngày' đã gặp thật (log toàn 'không rõ lý do' cho cả 8 "
    f"MST, chạy chỉ 6.0s vì toàn cache hit) — got {dict(row24) if row24 else None}")
print("PASS 24: XInvoice trả HTTP 200 nhưng 'status' không khớp tình trạng nào -> coi là THẤT BẠI "
      "(không phải thành công rỗng), tự động dự phòng masothue.com, kèm ly_do_loi cụ thể, KHÔNG lưu "
      "cache — sửa đúng bug thật khiến 8 MST bị 'kẹt cứng không rõ lý do'.")

# Test 25: XInvoice 200 không khớp (như Test 24), nhưng masothue.com dự
# phòng LẦN NÀY thành công -> PHẢI lấy được kết quả thật (không bị chặn bởi
# XInvoice "thành công rỗng" trước đó), và kết quả dự phòng phải được lưu
# cache bình thường.
_fake_requests.calls.clear()
_fake_requests.next_responses = [
    (200, {"status": "Trạng thái không xác định XYZ"}, {}),
    (200, {"status": "Người nộp thuế đang hoạt động (đã cấp GCN ĐKT)"}, {}),
]
r25 = _tra_cuu_trang_thai_mst("0321111120", timeout=1)
assert r25["canh_bao"] is False, (
    f"XInvoice 200 không khớp -> dự phòng masothue.com thành công -> PHẢI lấy được tình trạng thật "
    f"— got {r25}")
assert "ly_do_loi" not in r25, f"Đã dự phòng thành công -> không còn là lỗi nữa — got {r25}"
conn25 = _fresh_db()
row25 = conn25.execute("SELECT * FROM mst_status_cache WHERE mst=?", ("0321111120",)).fetchone()
conn25.close()
assert row25 is not None and bool(row25["canh_bao"]) is False, (
    "Kết quả dự phòng thành công từ masothue.com (sau khi XInvoice 200 rỗng) PHẢI được lưu cache bình "
    "thường")
print("PASS 25: XInvoice 200 không khớp tình trạng -> tự động dự phòng masothue.com và lấy được kết "
      "quả thật, có lưu cache bình thường.")
_fake_requests.next_responses = None

os.unlink(_tmp_db.name)
print("\nALL DONE")
