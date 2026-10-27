import os, sys, time
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server
server.time.sleep = lambda s: None
import time as _t
_goc = _t.sleep; _t.sleep = lambda s: None

# Ca thật: file "SaiMatKhau" liệt kê hàng chục công ty mật khẩu đúng, lý do thật là net::ERR_CONNECTION_TIMED_OUT (mạng/cổng), không phải sai mật khẩu.
LOI = {"pass1": {"loi": "Message: unknown error: net::ERR_CONNECTION_TIMED_OUT\n (Session info: chrome=156)"}, "pass2": "(không có pass2)"}
assert server._dvc_la_loi_mang(LOI)
assert not server._dvc_la_loi_mang({"pass1": {"da_thu": ["abcd"]}, "pass2": "(không có pass2)"})

class D:
    def get(self, u): pass
n = {"c": 0}
def fake(drv, mst, a, b):
    n["c"] += 1
    return (True, 1, {}) if n["c"] == 3 else (False, 0, LOI)
server._dvc_browser_login_2pass = fake
r = server._dvc_dang_nhap_thu_lai(D(), "0317225940", "p", "")
assert r[0] and r[3] is False and n["c"] == 3, r                      # mạng chập chờn -> thử lại rồi vào được
n["c"] = -99
r = server._dvc_dang_nhap_thu_lai(D(), "0317225940", "p", "")
assert not r[0] and r[3] is True, r                                   # mạng hỏng dai dẳng -> báo lỗi mạng, không phải sai pass
server._dvc_browser_login_2pass = lambda *a: (False, 0, {"pass1": {"da_thu": ["x", "y"]}, "pass2": "(không có pass2)"})
r = server._dvc_dang_nhap_thu_lai(D(), "1", "p", "")
assert not r[0] and r[3] is False
print("PASS: lỗi mạng/timeout khi đăng nhập DVC -> thử lại, rồi xếp 'lỗi mạng' (không phải sai mật khẩu); sai mật khẩu thật vẫn báo sai mật khẩu.")
