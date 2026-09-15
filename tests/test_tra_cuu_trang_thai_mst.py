import os
import re
import sqlite3
import tempfile
import datetime

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

    def get(self, url, headers=None, timeout=None):
        self.calls.append({"url": url, "headers": dict(headers or {})})
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


ns = {'datetime': datetime}
exec(extract_fn('_khong_dau'), ns)
exec(extract_fn('_chuan_mst'), ns)
exec(extract_fn('_phan_loai_trang_thai_mst'), ns)
m = re.search(r'^_MST_CACHE_NGAY\s*=\s*\d+', src, re.M)
exec(m.group(0), ns)
m2 = re.search(r'^_MST_API_NGHI_GIUA_LUOT\s*=\s*[\d.]+', src, re.M)
exec(m2.group(0), ns)

_fake_requests = _FakeRequests()
_fake_settings = _FakeSettings()
_fake_time = _FakeTime()
ns['requests'] = _fake_requests
ns['_get_setting'] = _fake_settings.get
ns['_set_setting'] = _fake_settings.set
ns['time'] = _fake_time

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
exec(extract_fn('_tra_cuu_trang_thai_mst'), ns)
_phan_loai_trang_thai_mst = ns['_phan_loai_trang_thai_mst']
_tra_cuu_trang_thai_mst = ns['_tra_cuu_trang_thai_mst']

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

# Test 7: MST rỗng/"KL" (khách lẻ)/quá ngắn -> KHÔNG gọi mạng, trả canh_bao=None
# (kể cả khi ĐÃ cấu hình client-id/api-key).
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
print("PASS 7: MST rỗng/'KL' (khách lẻ dùng chung mã)/quá ngắn -> bỏ qua hẳn, không gọi mạng.")

# Test 8 (QUAN TRỌNG): CHƯA cấu hình client-id/api-key -> bỏ qua HẲN tính năng
# (canh_bao=None), KHÔNG gọi mạng, KHÔNG lỗi — để xuất Excel vẫn chạy bình thường
# khi người dùng chưa đăng ký API.
_fake_settings.set("xinvoice_client_id", "")
_fake_settings.set("xinvoice_api_key", "")
_fake_requests.calls.clear()
r8 = _tra_cuu_trang_thai_mst("0315696133", timeout=1)
assert r8["canh_bao"] is None
assert len(_fake_requests.calls) == 0, (
    f"Chưa cấu hình client-id/api-key thì KHÔNG được gọi API — got {len(_fake_requests.calls)} lượt gọi")
print("PASS 8: chưa cấu hình client-id/api-key -> bỏ qua hẳn tính năng, không gọi mạng, không lỗi.")

_fake_settings.set("xinvoice_client_id", "demo-client")
_fake_settings.set("xinvoice_api_key", "demo-key")

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
assert len(_fake_requests.calls) == 5, (
    f"Sau ĐÚNG 5 lỗi liên tiếp phải NGỪNG gọi API cho các MST còn lại trong lượt này (tránh treo lâu "
    f"vì hàng loạt timeout) — got {len(_fake_requests.calls)} lượt gọi thật (kỳ vọng đúng 5)")
print("PASS 12: lỗi mạng không làm crash (canh_bao=None, an toàn), và dừng hẳn việc gọi API sau 5 lỗi "
      "liên tiếp trong cùng 1 lượt xuất Excel — không treo lâu vô ích.")

# Test 13 (không hồi quy): status HTTP khác 200 (vd 401 sai client-id/api-key) -> KHÔNG
# suy đoán tình trạng (canh_bao=None), vẫn tính là 1 lượt lỗi cho bộ đếm liên tiếp.
_fake_requests.next_exc = None
_fake_requests.next_status = 401
_fake_requests.next_data = {"message": "Unauthorized"}
_fake_requests.calls.clear()
dem_loi2 = [0]
r13 = _tra_cuu_trang_thai_mst("0311111111", timeout=1, so_lan_that_bai_lien_tiep=dem_loi2)
assert r13["canh_bao"] is None, f"HTTP 401 (sai key) KHÔNG được suy đoán tình trạng — got {r13}"
assert dem_loi2[0] == 1, f"HTTP lỗi vẫn phải tính vào bộ đếm lỗi liên tiếp — got {dem_loi2[0]}"
print("PASS 13: HTTP lỗi (vd 401 sai client-id/api-key) -> canh_bao=None (không suy đoán), vẫn tính "
      "vào bộ đếm lỗi liên tiếp.")

os.unlink(_tmp_db.name)
print("\nALL DONE")
