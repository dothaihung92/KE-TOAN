import os, sys, json, time
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server
server.time.sleep = (lambda f: (lambda s: f(min(s, 0.05))))(time.sleep)

# Ca thật: máy tính tiền "Token hết hạn giữa chừng -> đăng nhập lại thành công" rồi lại 401 và bỏ cuộc "Token hết hạn, cần đăng nhập lại".
# Token vừa cấp: 401 tiếp theo (chưa gửi mã) là đòi captcha -> phải xin mã người dùng, không báo TOKEN_EXPIRED.
class R:
    def __init__(self, code, body): self.status_code, self._b, self.headers = code, body, {}
    @property
    def text(self): return json.dumps(self._b)
    def json(self): return self._b
    def raise_for_status(self):
        if self.status_code >= 400: raise Exception(self.status_code)

class S:
    def __init__(self): self.headers = {}
    def get(self, url, headers=None, timeout=None):
        if "cvalue=OK" in url:
            return R(200, {"datas": [{"shdon": 1, "khhdon": "C", "khmshdon": 1, "nbmst": "1"}], "total": 1, "state": None})
        return R(401, {})

U = "https://hoadondientu.gdt.gov.vn/api/sco-query/invoices/sold"
c = server.GDTClient.__new__(server.GDTClient); c.session = S(); c.token = "T"; c._dn_lai_luc = time.time()
hoi = []
c.captcha_cb = lambda cancel_check=None: hoi.append(1) or ("K", "OK")
assert len(c._fetch_paginated(U, "s", "x")) == 1 and len(hoi) == 1
print("PASS 1: 401 ngay sau khi đăng nhập lại (máy tính tiền) -> xin mã captcha, lấy được dữ liệu.")

c2 = server.GDTClient.__new__(server.GDTClient); c2.session = S(); c2.token = "T"   # chưa đăng nhập lại -> 401 thật là token hết hạn
c2.captcha_cb = lambda cancel_check=None: ("K", "OK")
try:
    c2._fetch_paginated(U, "s", "x"); assert False
except Exception as e:
    assert "TOKEN_EXPIRED" in str(e)
print("PASS 2: 401 khi chưa vừa đăng nhập lại vẫn là TOKEN_EXPIRED như cũ.")
