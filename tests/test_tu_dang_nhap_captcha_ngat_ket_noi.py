import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Regression: tra cứu hàng loạt chạy được vài công ty thì các công ty sau báo
# "Tự đăng nhập thất bại: Lỗi lấy captcha: ('Connection aborted.', RemoteDisconnected(...))"
# dù vào tra cứu riêng 1 công ty vẫn được. Nguyên nhân:
#  (1) get_captcha() gặp lỗi kết nối thoáng qua với curl_cffi -> hạ cấp VĨNH VIỄN về
#      requests.Session (bị WAF ngắt: "Connection aborted/RemoteDisconnected") và kẹt luôn;
#  (2) _tu_dong_dang_nhap() bỏ cuộc NGAY lần lấy captcha lỗi đầu tiên.

LOI_KN = Exception("('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))")
LOI_CURL = Exception("Failed to perform, curl: (56) Recv failure: Connection reset by peer")

assert server._la_loi_ket_noi(LOI_KN) and server._la_loi_ket_noi(LOI_CURL)
assert not server._la_loi_ket_noi(Exception("HTTP Error 404: Not Found"))
print("PASS 1: phân biệt lỗi kết nối với lỗi mã HTTP.")


class _Resp:
    status_code = 200
    text = ""

    def raise_for_status(self):
        pass

    def json(self):
        return {"key": "K", "content": "<svg/>"}


class _SessLoi:
    def __init__(self, *a, **k):
        self.headers = {}
        self.cookies = {}

    def get(self, *a, **k):
        raise LOI_KN

    def close(self):
        pass


class _SessTot(_SessLoi):
    def get(self, *a, **k):
        return _Resp()


# 2) curl_cffi lỗi kết nối, requests cũng lỗi -> KHÔNG kẹt ở requests, trả lại phiên curl_cffi
c = server.GDTClient()
c.impersonate = True
c.session = _SessLoi()
goc_rs = server.requests.Session
goc_dung = server.GDTClient._dung_lai_session
server.requests.Session = _SessLoi
server.GDTClient._dung_lai_session = lambda self, ep_http11=True: setattr(self, "session", _SessLoi())
try:
    try:
        c.get_captcha()
        raise AssertionError("phải báo lỗi")
    except AssertionError:
        raise
    except Exception:
        pass
finally:
    server.requests.Session = goc_rs
assert c.impersonate is True, "Không được kẹt ở requests.Session khi requests cũng lỗi"
print("PASS 2: lỗi kết nối cả 2 cách -> giữ curl_cffi (không hạ cấp vĩnh viễn).")

# 3) curl_cffi lỗi kết nối, kết nối curl_cffi MỚI thì được -> không hạ cấp
c2 = server.GDTClient()
c2.impersonate = True
c2.session = _SessLoi()
server.GDTClient._dung_lai_session = lambda self, ep_http11=True: setattr(self, "session", _SessTot())
try:
    assert c2.get_captcha()["key"] == "K"
finally:
    server.GDTClient._dung_lai_session = goc_dung
assert c2.impersonate is True and isinstance(c2.session, _SessTot)
print("PASS 3: mở kết nối curl_cffi mới thì lấy được captcha, vẫn giả lập Chrome.")


# 4) _tu_dong_dang_nhap: lỗi kết nối khi lấy captcha -> chờ rồi thử lại, không bỏ cuộc ngay
class _Conn:
    def execute(self, *a):
        return self

    def fetchone(self):
        return {"password": "pw", "username": "u", "mst": "0300000000"}

    def close(self):
        pass


class _Client:
    def __init__(self):
        self.lan = 0
        self.dang_nhap = 0
        self._token_dead = True

    def get_captcha(self):
        self.lan += 1
        if self.lan <= 2:
            raise LOI_KN
        return {"key": "K", "content": "<svg/>"}

    def _dung_lai_session(self, ep_http11=True):
        pass

    def login(self, **k):
        self.dang_nhap += 1


cl = _Client()
goc = (server.db, server.get_client, server._solve_captcha, server.time.sleep)
ngu = []
server.db = lambda: _Conn()
server.get_client = lambda cid: cl
server._solve_captcha = lambda content, drv=None: "abcd"
server.time.sleep = lambda s: ngu.append(s)
try:
    tb = []
    ok, msg, lan, _ = server._tu_dong_dang_nhap(1, so_lan=8, progress=tb.append)
finally:
    server.db, server.get_client, server._solve_captcha, server.time.sleep = goc
assert ok and lan == 3 and cl.dang_nhap == 1, (ok, msg, lan)
assert ngu == [5, 10], ngu
assert any("ngắt kết nối" in t for t in tb)
print("PASS 4: tự đăng nhập thử lại khi lấy captcha bị ngắt kết nối (chờ 5s, 10s) rồi thành công.")

# 5) lỗi KHÔNG phải kết nối -> vẫn báo lỗi ngay như cũ
cl2 = _Client()
cl2.get_captcha = lambda: (_ for _ in ()).throw(Exception("HTTP Error 404: Not Found"))
server.db = lambda: _Conn()
server.get_client = lambda cid: cl2
try:
    ok, msg, lan, _ = server._tu_dong_dang_nhap(1, so_lan=8)
finally:
    server.db, server.get_client, server._solve_captcha, server.time.sleep = goc
assert not ok and lan == 1 and "404" in msg
print("PASS 5: lỗi mã HTTP vẫn báo ngay như cũ.")

print("\nALL DONE")
