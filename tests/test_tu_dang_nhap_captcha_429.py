import os, sys
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Ca thật: "Token hết hạn — tự đăng nhập lại thất bại (Lỗi lấy captcha: 429 Client Error: Too Many Requests ... /api/captcha)".
# Trang Thuế giới hạn tốc độ riêng cho /api/captcha: tự đăng nhập phải NGHỈ rồi thử lại (20s, 40s...), không bỏ cuộc ngay ở lần 429 đầu.
L429 = Exception("429 Client Error: Too Many Requests for url: https://hoadondientu.gdt.gov.vn/api/captcha")


class _Conn:
    def execute(self, *a): return self
    def fetchone(self): return {"password": "pw", "username": "u", "mst": "0300000000"}
    def close(self): pass


class _Client:
    def __init__(self, so_429):
        self.lan = 0; self.dang_nhap = 0; self.so_429 = so_429
    def get_captcha(self):
        self.lan += 1
        if self.lan <= self.so_429:
            raise L429
        return {"key": "K", "content": "<svg/>"}
    def _dung_lai_session(self, ep_http11=True): pass
    def login(self, **k): self.dang_nhap += 1


def chay(so_429, so_lan=5):
    cl = _Client(so_429)
    goc = (server.db, server.get_client, server._solve_captcha, server.time.sleep)
    ngu = []
    server.db = lambda: _Conn(); server.get_client = lambda cid: cl
    server._solve_captcha = lambda content, drv=None: "abcd"; server.time.sleep = lambda s: ngu.append(s)
    try:
        tb = []
        kq = server._tu_dong_dang_nhap(1, so_lan=so_lan, progress=tb.append)
    finally:
        server.db, server.get_client, server._solve_captcha, server.time.sleep = goc
    return kq, cl, ngu, tb


(ok, msg, lan, _), cl, ngu, tb = chay(2)
assert ok and lan == 3 and cl.dang_nhap == 1, (ok, msg, lan)
assert [x for x in ngu if float(x).is_integer()] == [20, 40], ngu
assert any("429" in t for t in tb)
(ok, msg, lan, _), cl, ngu, tb = chay(99, so_lan=3)
assert not ok and "429" in msg and lan == 3 and cl.dang_nhap == 0, (ok, msg, lan)
print("PASS: 429 khi lấy captcha đăng nhập -> nghỉ 20s/40s rồi thử lại; hết số lần mới báo lỗi.")
