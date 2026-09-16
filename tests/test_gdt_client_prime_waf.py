import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Regression test cho GDTClient.prime()/_xsrf() (server.py) — người dùng
# khẳng định lại lỗi 403 "Hệ thống phát hiện hành vi không hợp lệ. Yêu cầu
# đã bị chặn." KHÔNG PHẢI do đăng nhập quá nhanh (đã sửa ở bản trước: nghỉ
# giữa các lần thử + nghỉ đọc/gõ captcha), mà do hệ thống Thuế phát hiện
# request đến từ PHẦN MỀM chứ không phải trình duyệt thật — yêu cầu "chỉnh
# lại đăng nhập như người thật".
#
# So sánh với DVCClient (dichvucong.gdt.gov.vn, dùng CHUNG 1 hạ tầng WAF F5
# BIG-IP với hoadondientu.gdt.gov.vn, đã có sẵn cơ chế .prime() hoạt động
# tốt) phát hiện GDTClient THIẾU HẲN bước quan trọng: trình duyệt thật LUÔN
# "ghé" trang chủ TRƯỚC (nhận cookie phiên/WAF/XSRF-TOKEN) rồi mới gọi các
# API captcha/đăng nhập — GDTClient TRƯỚC ĐÂY gọi THẲNG API mà không hề có
# bước điều hướng trang nào trước đó, tự bản thân việc đó đã là 1 dấu hiệu
# rõ ràng của request tự động (không phải trình duyệt), bất kể đã giả lập
# đúng vân tay TLS hay nghỉ đúng nhịp hay chưa.


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
    def __init__(self):
        self.calls = []
        self.cookies = _FakeCookies()
        self.headers = {}
        self.next_json = {}

    def get(self, url, timeout=None, headers=None):
        self.calls.append({"method": "GET", "url": url, "headers": dict(headers or {})})
        return _FakeResp(200, self.next_json)

    def post(self, url, json=None, timeout=None, headers=None):
        self.calls.append({"method": "POST", "url": url, "headers": dict(headers or {}), "body": json})
        return _FakeResp(200, self.next_json)


# ===== Test 1 (QUAN TRỌNG — đúng ý người dùng "đăng nhập như người thật"):
# get_captcha() lần ĐẦU TIÊN phải TỰ ĐỘNG "ghé" trang chủ hoadondientu.gdt.gov.vn
# TRƯỚC (như trình duyệt thật mở trang rồi mới bấm đăng nhập), SAU ĐÓ mới
# gọi API /api/captcha — không được gọi thẳng API mà bỏ qua bước này. =====
c1 = server.GDTClient()
fs1 = _FakeSession()
c1.session = fs1
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

# ===== Test 3 (QUAN TRỌNG): login() PHẢI gửi kèm header X-XSRF-TOKEN đúng
# giá trị cookie XSRF-TOKEN hiện có trong session (mẫu bảo vệ CSRF phổ biến
# ở các cổng Spring+Angular của Thuế — đã áp dụng đúng cho DVCClient, GDTClient
# TRƯỚC ĐÂY hoàn toàn KHÔNG có) — thiếu header này dù cookie có sẵn cũng là
# 1 dấu hiệu request KHÔNG xuất phát từ chính trang web đó. =====
c3 = server.GDTClient()
fs3 = _FakeSession()
c3.session = fs3
fs3.cookies["XSRF-TOKEN"] = "xsrf-abc-123"
fs3.next_json = {"token": "fake-token-xyz"}
tok = c3.login(username="0300000000", password="matkhau", cvalue="AB12", ckey="ckey1")
assert tok == "fake-token-xyz"
post_call = next(c for c in fs3.calls if c["method"] == "POST")
assert post_call["headers"].get("X-XSRF-TOKEN") == "xsrf-abc-123", (
    f"login() phải gửi kèm header X-XSRF-TOKEN đúng giá trị cookie XSRF-TOKEN hiện có — got "
    f"{post_call['headers']}")
assert post_call["headers"].get("X-Requested-With") == "XMLHttpRequest", (
    f"login() phải gửi kèm header X-Requested-With: XMLHttpRequest (đúng kiểu gọi AJAX/XHR từ trang, "
    f"khác hẳn 1 lượt POST trần) — got {post_call['headers']}")
print("PASS 3: login() gửi kèm đúng header X-XSRF-TOKEN (từ cookie phiên hiện có) và X-Requested-With "
      "— 2 dấu hiệu quan trọng khẳng định request xuất phát từ chính trang, GDTClient trước đây hoàn "
      "toàn thiếu.")

# ===== Test 4 (không hồi quy): CHƯA có cookie XSRF-TOKEN (vd trang chủ chưa
# từng cấp, hoặc lỗi khi 'ghé' trang chủ) -> login() vẫn hoạt động bình
# thường, KHÔNG gửi header X-XSRF-TOKEN rỗng vô nghĩa, KHÔNG lỗi/crash. =====
c4 = server.GDTClient()
fs4 = _FakeSession()
c4.session = fs4
fs4.next_json = {"token": "fake-token-2"}
tok4 = c4.login(username="0300000000", password="matkhau", cvalue="CD34", ckey="ckey2")
assert tok4 == "fake-token-2"
post_call4 = next(c for c in fs4.calls if c["method"] == "POST")
assert "X-XSRF-TOKEN" not in post_call4["headers"], (
    f"Chưa có cookie XSRF-TOKEN nào -> KHÔNG được tự gửi header X-XSRF-TOKEN rỗng vô nghĩa — got "
    f"{post_call4['headers']}")
print("PASS 4: chưa có cookie XSRF-TOKEN -> login() vẫn hoạt động bình thường, không gửi header rỗng "
      "vô nghĩa, không lỗi.")

# ===== Test 5 (QUAN TRỌNG): gọi login() TRỰC TIẾP (không gọi get_captcha()
# trước, vd endpoint /api/solve-login gọi thẳng login() sau khi tự OCR) ->
# VẪN phải tự 'ghé' trang chủ trước nếu client CHƯA từng primed. =====
c5 = server.GDTClient()
fs5 = _FakeSession()
c5.session = fs5
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
