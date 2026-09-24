import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Regression test cho GDTClient._ha_cap_session()/get_captcha() (server.py) — người dùng báo (kèm
# 2 ảnh chụp): máy macOS bị lỗi ngay bước ĐẦU TIÊN "Lấy mã" (captcha) khi tra cứu hóa đơn điện tử —
# toast "Lỗi lấy captcha: Lỗi lấy captcha: HTTP Error 404:". Nguyên nhân nhiều khả năng: GDTClient
# dùng curl_cffi (impersonate Chrome, né WAF F5) — thư viện này có PHẦN GỐC biên dịch sẵn theo từng
# hệ điều hành/kiến trúc CPU, có thể không tương thích tốt trên 1 số máy macOS cụ thể dù cài đặt/
# import thành công (lỗi chỉ lộ ra lúc THỰC SỰ gửi request, không phải lúc import — nên fallback cũ
# ở __init__ (bắt lỗi IMPORT) không bắt được ca này).
#
# Fix: get_captcha() bắt lỗi RUNTIME khi đang impersonate, tự hạ cấp về requests.Session() thường
# (_ha_cap_session) rồi thử lại 1 lần — mất khả năng né WAF nhưng còn hơn không dùng được luôn. Việc
# hạ cấp áp dụng cho CẢ client (self.impersonate=False, self.session thay hẳn), nên mọi lượt gọi
# tiếp theo (login/query_invoices...) của CÙNG client cũng tự động dùng session đã hạ cấp, không cần
# sửa thêm nơi nào khác.


class FakeResp:
    def __init__(self, status, json_data=None, text=""):
        self.status_code = status
        self._json = json_data
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception("HTTP Error %d: mock lỗi curl_cffi native trên macOS" % self.status_code)

    def json(self):
        if self._json is None:
            raise ValueError("no json")
        return self._json


class FakeSessionLoi:
    """Mô phỏng curl_cffi lỗi RUNTIME (không phải lỗi import) — đúng ca thật báo cáo: import/khởi
    tạo thành công (self.impersonate=True) nhưng request THẬT lại lỗi/trả về bất thường (404)."""
    def get(self, url, timeout=None, headers=None):
        raise Exception("HTTP Error 404: mock lỗi curl_cffi native trên macOS")


class FakeSessionTot:
    """Đứng thay cho requests.Session() SAU khi hạ cấp — hoạt động bình thường."""
    def __init__(self, *a, **kw):
        self.headers = {}
        self.calls = 0

    def get(self, url, timeout=None, headers=None):
        self.calls += 1
        return FakeResp(200, json_data={"key": "abc123",
                                         "content": "data:image/svg+xml;base64,PHN2Zz48L3N2Zz4="})


class FakeSessionLuonLoi:
    """Đứng thay cho requests.Session() SAU khi hạ cấp nhưng VẪN lỗi (ca xấu nhất — không phải do
    curl_cffi, mà do mạng/máy chủ thật sự có vấn đề) — phải NÉM LỖI lên trên, không được nuốt gọn/
    giả vờ thành công."""
    def __init__(self, *a, **kw):
        self.headers = {}

    def get(self, url, timeout=None, headers=None):
        raise Exception("HTTP Error 404: vẫn lỗi thật sau khi đã hạ cấp")


# ===== Test 1 (QUAN TRỌNG — đúng bug thật): curl_cffi lỗi RUNTIME ở get_captcha() -> PHẢI tự hạ
# cấp về requests.Session() và thử lại, LẤY ĐƯỢC captcha thành công thay vì ném lỗi lên người dùng
# ngay từ lần thử đầu tiên. =====
c = server.GDTClient()
c.impersonate = True
c.session = FakeSessionLoi()

_orig_session_cls = server.requests.Session
server.requests.Session = FakeSessionTot
try:
    cap = c.get_captcha()
finally:
    server.requests.Session = _orig_session_cls

assert cap.get("key") == "abc123", f"Phải lấy được captcha THÀNH CÔNG sau khi tự hạ cấp — got {cap}"
assert c.impersonate is False, (
    "Sau khi hạ cấp, self.impersonate PHẢI = False (đánh dấu đã hạ cấp, không né WAF được nữa) — "
    f"got {c.impersonate}")
assert isinstance(c.session, FakeSessionTot) and c.session.calls == 1, (
    "self.session PHẢI được THAY HẲN bằng session mới (requests.Session()) sau khi hạ cấp, và đã "
    "gọi đúng 1 lần để lấy captcha thành công.")
print("PASS 1: curl_cffi lỗi runtime (đúng ca thật macOS 'HTTP Error 404') -> tự hạ cấp về "
      "requests.Session() và thử lại, lấy được captcha thành công.")

# ===== Test 2 (không hồi quy — QUAN TRỌNG): sau khi ĐÃ hạ cấp (impersonate=False), các lượt gọi
# get_captcha() TIẾP THEO của CÙNG client tự động dùng session đã hạ cấp — KHÔNG cần hạ cấp lại mỗi
# lần (tránh tạo requests.Session() mới liên tục vô ích). =====
cap2 = c.get_captcha()
assert cap2.get("key") == "abc123"
assert c.session.calls == 2, (
    f"Lượt gọi thứ 2 phải dùng LẠI đúng session đã hạ cấp từ trước (không tạo mới) — got "
    f"calls={c.session.calls}")
print("PASS 2: các lượt gọi sau khi đã hạ cấp dùng lại đúng session cũ, không hạ cấp lặp lại vô ích.")

# ===== Test 3 (QUAN TRỌNG — không hồi quy, ca xấu nhất): nếu ĐÃ hạ cấp rồi mà VẪN lỗi (không phải
# do curl_cffi — lỗi thật sự khác, VD mạng/máy chủ) -> PHẢI ném lỗi lên người dùng như cũ, KHÔNG
# được lặp vô hạn/nuốt lỗi giả vờ thành công. =====
c3 = server.GDTClient()
c3.impersonate = False   # đã ở trạng thái KHÔNG impersonate (như trước khi có fix này)
c3.session = FakeSessionLuonLoi()
loi = None
try:
    c3.get_captcha()
except Exception as e:
    loi = e
assert loi is not None, "Đã hạ cấp (impersonate=False) mà vẫn lỗi -> PHẢI ném lỗi lên, không được nuốt gọn."
assert "404" in str(loi), f"Phải giữ nguyên thông tin lỗi thật để người dùng/hỗ trợ kỹ thuật biết — got {loi}"
print("PASS 3: khi đã ở requests.Session() thường (không impersonate) mà vẫn lỗi -> ném lỗi lên "
      "bình thường như trước, không lặp vô hạn/nuốt lỗi giả vờ thành công.")

print("\nALL DONE")
