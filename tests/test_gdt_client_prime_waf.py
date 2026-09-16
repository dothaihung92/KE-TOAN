import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Regression test cho GDTClient.prime()/headers (server.py) — người dùng
# khẳng định lại lỗi 403 "Hệ thống phát hiện hành vi không hợp lệ. Yêu cầu
# đã bị chặn." KHÔNG PHẢI do đăng nhập quá nhanh, cũng KHÔNG PHẢI chặn theo
# IP (đăng nhập tay qua trình duyệt thật của họ vẫn bình thường) — theo yêu
# cầu, người dùng đã tự lấy 1 request "authenticate" THẬT THÀNH CÔNG từ
# DevTools (Copy as cURL) trên máy họ, gửi lại để so sánh CHÍNH XÁC với
# những gì GDTClient đang gửi, thay vì đoán tiếp.
#
# Kết quả so sánh (xác nhận qua đúng cURL thật đó, không phải đoán):
#   - Request thật CÓ 3 header GDTClient trước đây KHÔNG hề gửi: "action"
#     (luôn rỗng), "end-point" (luôn "/"), "request-id" (1 UUID ngẫu nhiên
#     KHÁC NHAU mỗi lượt gọi) — đều do chính mã Angular của trang tự gắn
#     vào MỌI request qua HTTP interceptor, không liên quan chống bot.
#   - Request thật KHÔNG CÓ header "X-Requested-With: XMLHttpRequest" (suy
#     đoán sai trước đó, borrow từ DVCClient — fetch()/Angular HttpClient
#     hiện đại KHÔNG tự thêm header này như jQuery $.ajax cũ) — GDTClient
#     trước đây LỠ THÊM header này, tự nó cũng là 1 điểm khác biệt.
#   - Request thật KHÔNG CÓ cookie/header XSRF-TOKEN nào cả (suy đoán sai
#     trước đó, cũng borrow từ DVCClient) — đã bỏ hẳn _xsrf()/X-XSRF-TOKEN
#     khỏi GDTClient (chỉ DVCClient/dichvucong.gdt.gov.vn mới dùng đúng mẫu
#     đó, đã xác nhận qua thực tế trước đây — 2 trang KHÔNG giống hệt nhau).
#   - Request thật CÓ 3 cookie tên dạng chuỗi hex 32 ký tự ngẫu nhiên (dấu
#     hiệu đặc trưng của SDK chống bot chạy JS, kiểu F5 Bot Defense) — CỐ
#     Ý KHÔNG cố tái tạo/giả mạo các cookie này (đó là lớp chống bot THẬT
#     SỰ, việc lách qua nó không phải việc nên làm).


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
    dụng cho MỌI request) — mỗi lượt .get()/.post() ghi lại header THỰC SỰ
    sẽ được gửi đi = self.headers HOÀ TRỘN VỚI headers riêng của lượt đó
    (đúng hành vi requests.Session thật), để test được cả những header cố
    định gắn qua self.session.headers.update(...) trong GDTClient.__init__
    (vd "action"/"end-point") lẫn header riêng từng lượt (vd "request-id")."""
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
    CỐ ĐỊNH (GDTClient.HEADERS, gồm cả "action"/"end-point" mới thêm) lên
    session giả, vì bước đó thật ra đã chạy trong __init__() lên session
    THẬT (đã bị thay thế) trước khi test kịp can thiệp — nếu không session
    giả sẽ "quên" mất các header cố định này."""
    c = server.GDTClient()
    fs = _FakeSession()
    fs.headers.update(server.GDTClient.HEADERS)
    c.session = fs
    return c, fs


# ===== Test 1 (QUAN TRỌNG — đúng ý người dùng "đăng nhập như người thật"):
# get_captcha() lần ĐẦU TIÊN phải TỰ ĐỘNG "ghé" trang chủ hoadondientu.gdt.gov.vn
# TRƯỚC (như trình duyệt thật mở trang rồi mới bấm đăng nhập), SAU ĐÓ mới
# gọi API /api/captcha — không được gọi thẳng API mà bỏ qua bước này. =====
c1, fs1 = _new_client_with_fake_session()
fs1.next_json = {"key": "k1", "content": "<svg></svg>"}
d1 = c1.get_captcha()
assert len(fs1.calls) == 2, (
    f"Lần gọi get_captcha() ĐẦU TIÊN phải có ĐÚNG 2 lượt gọi mạng: (1) ghé trang chủ trước — 'prime', "
    f"(2) gọi API /api/captcha — got {len(fs1.calls)} lượt: {fs1.calls}")
assert fs1.calls[0]["method"] == "GET" and fs1.calls[0]["url"] == "https://hoadondientu.gdt.gov.vn/", (
    f"Lượt gọi ĐẦU TIÊN phải là ghé trang chủ (y hệt trình duyệt thật mở trang trước khi đăng nhập) "
    f"— got {fs1.calls[0]}")
assert fs1.calls[0]["headers"].get("Sec-Fetch-Mode") == "navigate", (
    f"Lượt ghé trang chủ phải có header Sec-Fetch-Mode=navigate (đúng kiểu trình duyệt ĐIỀU HƯỚNG "
    f"trang, khác hẳn 1 lượt gọi API/XHR thường) — got {fs1.calls[0]['headers']}")
assert fs1.calls[1]["url"].endswith("/api/captcha"), f"Lượt 2 phải là gọi đúng API captcha — got {fs1.calls[1]}"
assert c1.primed is True, "Sau khi get_captcha() lần đầu, client phải được đánh dấu đã 'primed'"
assert d1 == fs1.next_json
print("PASS 1: get_captcha() lần đầu TỰ ĐỘNG ghé trang chủ trước (như trình duyệt thật mở trang), "
      "rồi mới gọi API captcha — đúng yêu cầu 'chỉnh lại đăng nhập như người thật'.")

# ===== Test 2 (không hồi quy — QUAN TRỌNG): gọi get_captcha() LẦN THỨ 2 trở
# đi (CÙNG client, CÙNG phiên làm việc) -> KHÔNG được ghé lại trang chủ nữa
# (chỉ cần 1 lần, giữ nguyên session/cookie đã có) — chỉ có ĐÚNG 1 lượt gọi
# API captcha thêm. =====
fs1.calls.clear()
d1b = c1.get_captcha()
assert len(fs1.calls) == 1, (
    f"Lần gọi get_captcha() THỨ 2 trở đi KHÔNG được ghé lại trang chủ (đã 'primed' từ lần đầu) — chỉ "
    f"1 lượt gọi API captcha — got {len(fs1.calls)}: {fs1.calls}")
assert fs1.calls[0]["url"].endswith("/api/captcha")
print("PASS 2: các lần gọi get_captcha() SAU lần đầu không ghé lại trang chủ nữa (giữ nguyên cookie "
      "phiên đã có), tránh tốn thêm lượt gọi không cần thiết.")

# ===== Test 3 (QUAN TRỌNG — đúng cURL thật người dùng gửi từ DevTools):
# login() PHẢI gửi kèm header "request-id" (1 UUID, sinh MỚI mỗi lượt gọi)
# và session PHẢI có sẵn "action"/"end-point" (từ HEADERS cố định) — đúng
# NGUYÊN VĂN những gì trình duyệt thật gửi. login() KHÔNG được tự thêm
# "X-Requested-With"/"X-XSRF-TOKEN" (2 header KHÔNG có trong request thật —
# suy đoán sai trước đó, đã bỏ). =====
c3, fs3 = _new_client_with_fake_session()
fs3.next_json = {"token": "fake-token-xyz"}
tok = c3.login(username="0300000000", password="matkhau", cvalue="AB12", ckey="ckey1")
assert tok == "fake-token-xyz"
post_call = next(c for c in fs3.calls if c["method"] == "POST")
rid = post_call["headers"].get("request-id")
assert rid and len(rid) >= 32, (
    f"login() phải gửi kèm header 'request-id' dạng UUID (đúng như request thật từ DevTools) — got "
    f"{post_call['headers']}")
assert "X-Requested-With" not in post_call["headers"], (
    f"KHÔNG được tự thêm header 'X-Requested-With' — request thật (cURL từ DevTools) KHÔNG có header "
    f"này, thêm vào là 1 điểm khác biệt so với trình duyệt thật — got {post_call['headers']}")
assert "X-XSRF-TOKEN" not in post_call["headers"], (
    f"KHÔNG được tự thêm header 'X-XSRF-TOKEN' — request thật (cURL từ DevTools) không có cookie/header "
    f"XSRF-TOKEN nào (khác hẳn DVCClient/dichvucong.gdt.gov.vn) — got {post_call['headers']}")
print("PASS 3: login() gửi đúng header 'request-id' (UUID) và KHÔNG tự thêm 'X-Requested-With'/"
      "'X-XSRF-TOKEN' — khớp đúng NGUYÊN VĂN request thật lấy từ DevTools, không còn suy đoán.")

# ===== Test 4 (QUAN TRỌNG — đúng cURL thật): mỗi lượt gọi PHẢI có "request-id"
# KHÁC NHAU (UUID ngẫu nhiên mới mỗi lần, đúng cách trang thật tự sinh), và
# session PHẢI có sẵn header cố định "action"/"end-point" (do trang tự gắn
# vào MỌI request, không đổi giữa các lượt). =====
c4, fs4 = _new_client_with_fake_session()
fs4.next_json = {"key": "k4", "content": "<svg></svg>"}
c4.get_captcha()
fs4.next_json = {"token": "fake-token-2"}
c4.login(username="0300000000", password="matkhau", cvalue="CD34", ckey="ckey2")
rid_calls = [c["headers"].get("request-id") for c in fs4.calls if "request-id" in c["headers"]]
assert len(rid_calls) == 2 and rid_calls[0] != rid_calls[1], (
    f"Mỗi lượt gọi (captcha, login) phải có request-id KHÁC NHAU (UUID mới mỗi lần, đúng cách trang "
    f"thật tự sinh, không phải 1 giá trị cố định dùng lại) — got {rid_calls}")
for c in fs4.calls:
    if c["url"].endswith("/api/captcha") or c["url"].endswith("/authenticate"):
        assert c["headers"].get("action") == "", (
            f"Mọi lượt gọi API phải có sẵn header 'action' rỗng (từ session, do trang thật tự gắn cố "
            f"định) — got {c['headers']}")
        assert c["headers"].get("end-point") == "/", (
            f"Mọi lượt gọi API phải có sẵn header 'end-point: /' (từ session, do trang thật tự gắn cố "
            f"định) — got {c['headers']}")
print("PASS 4: mỗi lượt gọi có request-id KHÁC NHAU (UUID mới mỗi lần), và có sẵn header cố định "
      "'action'/'end-point' đúng như trang thật — khớp đúng cURL DevTools người dùng gửi.")

# ===== Test 5 (QUAN TRỌNG): gọi login() TRỰC TIẾP (không gọi get_captcha()
# trước, vd endpoint /api/solve-login gọi thẳng login() sau khi tự OCR) ->
# VẪN phải tự 'ghé' trang chủ trước nếu client CHƯA từng primed. =====
c5, fs5 = _new_client_with_fake_session()
fs5.next_json = {"token": "fake-token-3"}
assert c5.primed is False
c5.login(username="0300000000", password="matkhau", cvalue="EF56", ckey="ckey3")
assert c5.primed is True
assert any(call["method"] == "GET" and call["url"] == "https://hoadondientu.gdt.gov.vn/" for call in fs5.calls), (
    f"login() gọi TRỰC TIẾP (chưa từng get_captcha() trước) vẫn phải tự ghé trang chủ trước nếu client "
    f"chưa 'primed' — got {fs5.calls}")
print("PASS 5: login() gọi trực tiếp (không qua get_captcha() trước) vẫn tự ghé trang chủ trước nếu "
      "client chưa từng 'primed' trong phiên làm việc này.")

print("\nALL DONE")
