import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Regression: người dùng báo tra cứu hàng loạt log lặp mãi (hơn 600 lần):
# "lỗi mạng (HTTPError: Failed to perform, curl: (92) HTTP/2 stream 1247 was
# not closed cleanly: INTERNAL_ERROR (err 2)...), đợi 3s rồi thử lại".
# Nguyên nhân: cứ thử lại trên ĐÚNG session/kết nối HTTP/2 đã hỏng. Sửa: gặp
# lỗi luồng HTTP/2 -> dựng lại Session (giữ header/token + cookie), ép HTTP/1.1.

LOI_92 = Exception("Failed to perform, curl: (92) HTTP/2 stream 1247 was not closed cleanly: "
                   "INTERNAL_ERROR (err 2). See https://curl.se/libcurl/c/libcurl-errors.html first")

# 1) Nhận diện lỗi
assert server._la_loi_http2_stream(LOI_92)
assert server._la_loi_http2_stream("curl: (16) Error in the HTTP2 framing layer")
assert not server._la_loi_http2_stream(Exception("Read timed out"))
assert not server._la_loi_http2_stream(Exception("Connection reset by peer"))
print("PASS 1: nhận diện đúng lỗi luồng HTTP/2 (curl 92/16), không nhầm lỗi mạng khác.")


class _Resp:
    def __init__(self, status, data):
        self.status_code = status
        self._d = data
        self.headers = {}

    def raise_for_status(self):
        pass

    def json(self):
        return self._d


class _SessHong:
    """Session cũ: luôn ném lỗi curl 92."""
    def __init__(self):
        self.headers = {"Authorization": "Bearer TOKEN-XYZ", "Accept": "application/json"}
        self.cookies = {}
        self.calls = 0
        self.closed = False

    def get(self, *a, **k):
        self.calls += 1
        raise LOI_92

    def close(self):
        self.closed = True


DATA = {"datas": [{"khhdon": "K1", "shdon": "1", "nbmst": "0300000000"}], "total": 1, "state": None}


class _SessTot:
    def __init__(self, *a, **k):
        self.headers = {}
        self.cookies = {}
        self.calls = 0

    def get(self, *a, **k):
        self.calls += 1
        return _Resp(200, DATA)


orig_sleep = server.time.sleep
orig_rs = server.requests.Session
sleeps = []
server.time.sleep = lambda s: sleeps.append(s)
server.requests.Session = _SessTot
try:
    c = server.GDTClient()
    c.impersonate = False   # môi trường test: dựng lại bằng requests.Session (đã giả lập)
    cu = _SessHong()
    c.session = cu
    logs = []
    results, total = c._fetch_paginated(
        "https://hoadondientu.gdt.gov.vn/api/query/invoices/purchase",
        "tdlap=ge=2026-08-01T00:00:00", "Tìm kiếm (hóa đơn mua vào)", want_total=True,
        progress=logs.append)
finally:
    server.time.sleep = orig_sleep
    server.requests.Session = orig_rs

assert len(results) == 1 and total == 1, (results, total)
assert cu.calls == 1, f"Phải bỏ session hỏng ngay sau lỗi HTTP/2 đầu tiên — gọi {cu.calls} lần"
assert cu.closed, "Session cũ phải được đóng"
assert c.session is not cu and c.session.calls == 1
assert c.session.headers.get("Authorization") == "Bearer TOKEN-XYZ", "Phải giữ token khi dựng lại session"
assert any("kết nối mới" in m for m in logs), logs
print("PASS 2: lỗi curl 92 -> dựng lại session (giữ token), lượt sau lấy được dữ liệu, không lặp mãi.")

# 3) Với curl_cffi thật (nếu có cài): session mới phải ép HTTP/1.1
try:
    from curl_cffi import CurlHttpVersion  # noqa
    co_cffi = True
except Exception:
    co_cffi = False
if co_cffi:
    c3 = server.GDTClient()
    if c3.impersonate:
        c3.session.headers.update({"Authorization": "Bearer T3"})
        c3.session.cookies.set("TS0114b13e", "abc", domain="hoadondientu.gdt.gov.vn")
        assert c3._xu_ly_loi_http2(LOI_92) is True
        assert c3._http11 and c3.impersonate
        assert c3.session.http_version == CurlHttpVersion.V1_1, c3.session.http_version
        assert c3.session.headers.get("Authorization") == "Bearer T3"
        assert dict(c3.session.cookies).get("TS0114b13e") == "abc"
        assert c3._xu_ly_loi_http2(LOI_92) is False, "Đã ở HTTP/1.1 thì không dựng lại liên tục"
        print("PASS 3: curl_cffi -> session mới ép HTTP/1.1, giữ token + cookie WAF.")

print("\nALL DONE")
