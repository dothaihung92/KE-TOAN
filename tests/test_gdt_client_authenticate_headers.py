import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Regression test cho GDTClient.get_captcha()/login() (server.py) — người
# dùng đã tự lấy 1 request "authenticate" THẬT THÀNH CÔNG từ DevTools (Copy
# as cURL) trên máy họ, cho phép so sánh CHÍNH XÁC với request GDTClient
# đang gửi, thay vì đoán. Kết quả so sánh (xác nhận qua đúng cURL thật đó):
#   - Request thật CÓ 3 header GDTClient trước đây KHÔNG hề gửi: "action"
#     (luôn rỗng), "end-point" (luôn "/"), "request-id" (1 UUID ngẫu nhiên
#     KHÁC NHAU mỗi lượt gọi) — do chính mã Angular của trang tự gắn vào
#     MỌI request qua HTTP interceptor, không liên quan chống bot.
#   - Request thật KHÔNG CÓ header "X-Requested-With: XMLHttpRequest" và
#     KHÔNG CÓ cookie/header XSRF-TOKEN nào (2 điều GDTClient từng LỠ thêm ở
#     bản vá trước, suy đoán sai — borrow nhầm từ DVCClient/dichvucong.gdt.gov.vn,
#     2 trang KHÔNG dùng chung 1 mẫu request).
# Xác nhận thực tế: CHỈ cần sửa đúng các header này là đăng nhập tay được
# ngay — không cần thêm bước "ghé trang chủ trước" (prime), không cần nghỉ
# giữa các lần thử, không cần dự phòng bằng trình duyệt thật — các cơ chế
# đó đã bị BỎ (revert) theo đúng yêu cầu người dùng sau khi xác nhận chỉ
# header là nguyên nhân thật.


class _FakeCookies(dict):
    def get(self, k, default=""):
        return dict.get(self, k, default)


class _FakeResp:
    def __init__(self, status_code, data):
        self.status_code = status_code
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data

    @property
    def text(self):
        return str(self._data)


class _FakeSession:
    """self.headers mô phỏng requests.Session.headers (header MẶC ĐỊNH áp
    dụng cho MỌI request, gắn 1 lần trong GDTClient.__init__) — mỗi lượt
    .get()/.post() ghi lại header THỰC SỰ sẽ được gửi đi = self.headers HOÀ
    TRỘN VỚI headers riêng của lượt đó (đúng hành vi requests.Session thật)."""
    def __init__(self):
        self.calls = []
        self.cookies = _FakeCookies()
        self.headers = {}
        self.next_json = {}

    def get(self, url, timeout=None, headers=None):
        self.calls.append({"method": "GET", "url": url, "headers": {**self.headers, **(headers or {})}})
        return _FakeResp(200, self.next_json)

    def post(self, url, json=None, timeout=None, headers=None):
        self.calls.append({"method": "POST", "url": url, "headers": {**self.headers, **(headers or {})}, "body": json})
        return _FakeResp(200, self.next_json)


def _new_client_with_fake_session():
    """Tạo 1 GDTClient rồi THAY session thật (curl_cffi/requests, không kiểm
    soát được) bằng _FakeSession — nhưng vẫn phải tự áp lại đúng bộ header
    CỐ ĐỊNH (GDTClient.HEADERS) lên session giả, vì bước đó thật ra đã chạy
    trong __init__() lên session THẬT (đã bị thay thế) trước khi test kịp
    can thiệp — nếu không session giả sẽ "quên" mất các header cố định này."""
    c = server.GDTClient()
    fs = _FakeSession()
    fs.headers.update(server.GDTClient.HEADERS)
    c.session = fs
    return c, fs


# ===== Test 1 (QUAN TRỌNG — đúng cURL thật từ DevTools): login() PHẢI gửi
# kèm header "request-id" (1 UUID, sinh MỚI mỗi lượt gọi); session PHẢI có
# sẵn "action"/"end-point" (từ HEADERS cố định) — đúng NGUYÊN VĂN request
# thật. login() KHÔNG được tự thêm "X-Requested-With"/"X-XSRF-TOKEN" (2
# header KHÔNG có trong request thật — suy đoán sai trước đó, đã bỏ). =====
c1, fs1 = _new_client_with_fake_session()
fs1.next_json = {"token": "fake-token-xyz"}
tok = c1.login(username="0300000000", password="matkhau", cvalue="AB12", ckey="ckey1")
assert tok == "fake-token-xyz"
assert len(fs1.calls) == 1, f"login() chỉ được gọi ĐÚNG 1 lượt mạng (không còn 'ghé trang chủ' trước) — got {fs1.calls}"
post_call = fs1.calls[0]
rid = post_call["headers"].get("request-id")
assert rid and len(rid) >= 32, (
    f"login() phải gửi kèm header 'request-id' dạng UUID (đúng như request thật từ DevTools) — got "
    f"{post_call['headers']}")
assert post_call["headers"].get("action") == "", (
    f"Phải có sẵn header 'action' rỗng (từ session, do trang thật tự gắn cố định) — got "
    f"{post_call['headers']}")
assert post_call["headers"].get("end-point") == "/", (
    f"Phải có sẵn header 'end-point: /' (từ session, do trang thật tự gắn cố định) — got "
    f"{post_call['headers']}")
assert "X-Requested-With" not in post_call["headers"], (
    f"KHÔNG được tự thêm header 'X-Requested-With' — request thật (cURL từ DevTools) KHÔNG có header "
    f"này — got {post_call['headers']}")
assert "X-XSRF-TOKEN" not in post_call["headers"], (
    f"KHÔNG được tự thêm header 'X-XSRF-TOKEN' — request thật (cURL từ DevTools) không có cookie/header "
    f"XSRF-TOKEN nào (khác hẳn DVCClient/dichvucong.gdt.gov.vn) — got {post_call['headers']}")
print("PASS 1: login() gửi đúng header 'request-id' (UUID) + có sẵn 'action'/'end-point', KHÔNG tự "
      "thêm 'X-Requested-With'/'X-XSRF-TOKEN' — khớp đúng NGUYÊN VĂN request thật từ DevTools, chỉ 1 "
      "lượt gọi mạng duy nhất (không còn bước 'ghé trang chủ' trước).")

# ===== Test 2 (QUAN TRỌNG): mỗi lượt gọi PHẢI có "request-id" KHÁC NHAU
# (UUID ngẫu nhiên mới mỗi lần, đúng cách trang thật tự sinh). =====
c2, fs2 = _new_client_with_fake_session()
fs2.next_json = {"key": "k2", "content": "<svg></svg>"}
c2.get_captcha()
fs2.next_json = {"token": "fake-token-2"}
c2.login(username="0300000000", password="matkhau", cvalue="CD34", ckey="ckey2")
assert len(fs2.calls) == 2, f"get_captcha()+login() chỉ được 2 lượt gọi mạng — got {fs2.calls}"
rid_calls = [c["headers"].get("request-id") for c in fs2.calls]
assert all(rid_calls) and rid_calls[0] != rid_calls[1], (
    f"Mỗi lượt gọi (captcha, login) phải có request-id KHÁC NHAU (UUID mới mỗi lần) — got {rid_calls}")
print("PASS 2: mỗi lượt gọi (captcha, login) có request-id KHÁC NHAU (UUID mới mỗi lần), và chỉ đúng "
      "2 lượt gọi mạng cho cả 2 bước (không còn 'ghé trang chủ' trước mỗi bước).")

print("\nALL DONE")
