import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Kết nối bị trang Thuế ngắt nhiều lần liên tiếp: thử lại trên đúng phiên/kết nối hỏng thì lỗi mãi. Nay đóng HẲN phiên cũ (kết nối + cookie)
# và mở phiên MỚI hoàn toàn như đóng/mở lại trình duyệt: vào lại trang chủ bình thường, giữ token đăng nhập. Không đổi IP, không giấu gì.
class Phien:
    cai = []
    def __init__(self, *a, **k):
        self.headers = {}; self.cookies = {}; self.da_dong = False; self.goi = []
        Phien.cai.append(self)
    def get(self, url, **k): self.goi.append((url, k.get("headers") or {})); return None
    def close(self): self.da_dong = True

goc = server.requests.Session
server.requests.Session = Phien
try:
    c = server.GDTClient.__new__(server.GDTClient)
    c.impersonate = False; c._http11 = False; c.token = "TK"
    cu = Phien(); cu.cookies = {"TS01": "cu"}; cu.headers = {"Authorization": "Bearer TK", "Accept": "application/json", "Origin": "https://hoadondientu.gdt.gov.vn"}
    c.session = cu
    c._phien_moi_hoan_toan()
    moi = c.session
    assert moi is not cu and cu.da_dong, "đóng phiên cũ"
    assert moi.headers.get("Authorization") == "Bearer TK" and moi.headers.get("Origin"), "giữ token + header chung"
    assert "TS01" not in moi.cookies, "không mang cookie cũ"
    assert moi.goi and moi.goi[0][0] == "https://hoadondientu.gdt.gov.vn/" and moi.goi[0][1].get("Sec-Fetch-Mode") == "navigate", "vào lại trang chủ như mở trang bình thường"
finally:
    server.requests.Session = goc
print("PASS 1: đóng phiên cũ, mở phiên mới (không cookie cũ), giữ token, vào lại trang chủ như mở trình duyệt mới.")

# _fetch_paginated: ngắt kết nối lần 2, 4, 6... -> mở phiên mới hoàn toàn
server._ngu_ktra_huy = lambda giay, cancel_check=None: None
server.time.sleep = lambda s: None
mo = []
class Hong:
    def __init__(self): self.n = 0; self.headers = {}
    def get(self, *a, **k): self.n += 1; raise ConnectionError("Failed to perform, curl: (56) Connection closed abruptly.")
c = server.GDTClient.__new__(server.GDTClient)
c.impersonate = False; c._http11 = False; c.token = "T"; c.session = Hong()
c._phien_moi_hoan_toan = lambda: mo.append(c.session.n)
c._dung_lai_session = lambda ep_http11=True: None
try:
    c._fetch_paginated("https://x/api/sco-query/invoices/purchase", "s", "a")
except Exception:
    pass
assert mo == [2, 4, 6], mo
print("PASS 2: ngắt kết nối liên tiếp lần 2, 4, 6 -> mở phiên mới hoàn toàn (không chỉ thử lại trên phiên hỏng).")

# đăng nhập tự động: ngắt kết nối khi lấy captcha -> phiên mới hoàn toàn
gc = []
class Cap:
    token = None
    def __init__(self): self.n = 0
    def _dung_lai_session(self, ep_http11=False): pass
    def _phien_moi_hoan_toan(self): gc.append(self.n)
    def get_captcha(self): self.n += 1; raise Exception("('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))")
cap = Cap(); server.get_client = lambda cid: cap
class DbGia:
    def execute(self, *a):
        class R:
            def fetchone(s): return {"password": "x", "username": "u", "mst": "1"}
        return R()
    def close(self): pass
server.db = lambda: DbGia()
server._COOLDOWN_TOAN_CUC["den"] = 0.0
ok, tb, *_ = server._tu_dong_dang_nhap(1, so_lan=3)
assert not ok and gc == [1, 2], gc
print("PASS 3: tự đăng nhập bị ngắt kết nối khi lấy captcha -> mở phiên mới hoàn toàn trước lần thử sau.")
print("ALL DONE")
