import os, sys, json, time
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server
server.time.sleep = (lambda f: (lambda s: f(min(s, 0.02))))(time.sleep)
server._ngu_ktra_huy = lambda s, cc=None: None

# Ca thật: tra cứu 1 THÁNG máy tính tiền (24 hóa đơn) mà bị hỏi captcha 7-10 lần. Mỗi công ty/lượt đầu: gọi thử KHÔNG mã -> 401 ->
# bị hiểu là hết token -> đăng nhập lại -> 401 -> mới xin mã (thêm lượt + thêm lần hỏi). Khi đã biết máy tính tiền đòi mã cho mọi lượt
# thì phải xin mã NGAY, không gọi thử không mã.
class R:
    def __init__(self, code, body): self.status_code, self._b, self.headers = code, body, {}
    @property
    def text(self): return json.dumps(self._b)
    def json(self): return self._b
    def raise_for_status(self):
        if self.status_code >= 400: raise Exception(self.status_code)

class S:
    def __init__(self, token_ok=True): self.headers, self.goi, self.token_ok = {}, [], token_ok
    def get(self, url, headers=None, timeout=None):
        self.goi.append(url)
        if "cvalue=" not in url or not self.token_ok:
            return R(401, {})
        return R(200, {"datas": [{"shdon": "1", "khhdon": "C", "khmshdon": 1, "nbmst": "1"}], "total": 1, "state": None})

U = "https://hoadondientu.gdt.gov.vn/api/sco-query/invoices/sold"
def moi(token_ok=True):
    c = server.GDTClient.__new__(server.GDTClient); c.session = S(token_ok); c.token = "T"
    hoi, lydo = [], []
    c.captcha_cb = lambda cancel_check=None: hoi.append(1) or ("K", "OK%d" % len(hoi))
    return c, hoi, lydo

# 1) chưa biết -> gọi thử không mã như cũ (401 chưa-đăng-nhập-lại = TOKEN_EXPIRED)
server._MTT_DOI_CAPTCHA["co"] = False
c, hoi, _ = moi()
try:
    c._fetch_paginated(U, "a", "x"); assert False
except Exception as e:
    assert "TOKEN_EXPIRED" in str(e) and not hoi and "cvalue=" not in c.session.goi[0]
print("PASS 1: chưa biết trang Thuế đòi mã -> hành vi cũ (gọi thử không mã).")

# 2) sau khi MỘT lượt dùng được mã -> cờ bật; lượt của client khác xin mã NGAY, lượt gọi ĐẦU đã kèm mã (không có lượt gọi thử không mã)
c1, hoi1, _ = moi()
c1.session.get = S().get                       # giả lập: mã nào cũng được, để có 1 lượt thành công kèm mã
c1._qs_captcha = lambda: ("&ckey=K&cvalue=OK", 0)
assert len(c1._fetch_paginated(U, "a", "x")) == 1 and server._MTT_DOI_CAPTCHA["co"] is True
c2, hoi2, _ = moi()
nhan = []
assert len(c2._fetch_paginated(U, "a", "x", progress=nhan.append)) == 1
assert hoi2 == [1] and len(c2.session.goi) == 1 and "cvalue=OK1" in c2.session.goi[0], (hoi2, c2.session.goi)
assert any("máy tính tiền đòi mã cho mỗi lượt tra cứu — hỏi trước" in t for t in nhan), nhan
print("PASS 2: đã biết máy tính tiền đòi mã -> xin mã trước, lượt gọi đầu tiên đã kèm mã (không gọi thử, không đăng nhập lại), 1 lần hỏi.")

# 3) token thật sự hết hạn (401 dù có mã): chỉ hỏi thêm tối đa 1 lần rồi báo TOKEN_EXPIRED để đăng nhập lại
c3, hoi3, _ = moi(token_ok=False)
try:
    c3._fetch_paginated(U, "a", "x"); assert False
except Exception as e:
    assert "TOKEN_EXPIRED" in str(e) and len(hoi3) <= 2, hoi3
print("PASS 3: token hết hạn thật: hỏi mã tối đa 2 lần rồi mới báo hết token (không hỏi 5-6 lần).")

# 4) hệ thống thường (query) không bị hỏi mã trước
c4, hoi4, _ = moi()
c4.session.get = lambda url, headers=None, timeout=None: R(200, {"datas": [], "total": 0, "state": None})
c4._fetch_paginated("https://hoadondientu.gdt.gov.vn/api/query/invoices/sold", "a", "x")
assert hoi4 == []
print("PASS 4: hóa đơn điện tử thường không bị xin mã trước.")
