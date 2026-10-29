import os, sys, json, time
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Ca thật: tra cứu máy tính tiền rất lâu so với làm tay trên trang Thuế. Mã captcha chỉ dùng được cho 1 lượt tra cứu: lượt sau trang Thuế
# trả 429 -> bản cũ coi là "giới hạn tốc độ": chờ 2s + bắt MỌI luồng nghỉ + gọi thêm 1 lượt 429 nữa rồi mới xin mã. Nay: mã đã dùng được
# rồi mà bị 429 -> xin mã mới NGAY. 429 với mã chưa dùng được lần nào (giới hạn tốc độ thật) vẫn chờ như cũ.
ngu = []
server.time.sleep = lambda s: ngu.append(s)
server._ngu_ktra_huy = lambda s, cc=None: ngu.append(s)

class R:
    def __init__(self, code, body): self.status_code, self._b, self.headers = code, body, {}
    @property
    def text(self): return json.dumps(self._b)
    def json(self): return self._b
    def raise_for_status(self):
        if self.status_code >= 400: raise Exception(self.status_code)

class S:
    """Trang Thuế giả: mỗi mã captcha chỉ tra cứu được 1 lượt."""
    def __init__(self): self.headers, self.da_dung, self.goi = {}, set(), []
    def get(self, url, headers=None, timeout=None):
        self.goi.append(url)
        if "cvalue=" not in url:
            return R(429, {"message": "Too Many Requests"})
        ma = url.split("cvalue=")[1].split("&")[0]
        if ma in self.da_dung:
            return R(429, {"message": "Too Many Requests"})
        self.da_dung.add(ma)
        return R(200, {"datas": [{"shdon": len(self.da_dung), "khhdon": "C", "khmshdon": 1, "nbmst": "1"}], "total": 1, "state": None})

U = "https://hoadondientu.gdt.gov.vn/api/sco-query/invoices/sold"
c = server.GDTClient.__new__(server.GDTClient); c.session = S(); c.token = "T"
so = iter(range(1, 100))
c.captcha_cb = lambda cancel_check=None: ("K", "M%d" % next(so))
server._COOLDOWN_TOAN_CUC["den"] = 0
assert len(c._fetch_paginated(U, "a", "x")) == 1          # lần đầu: chưa có mã -> 429, 429 -> xin mã (như cũ)
ngu.clear(); n0 = len(c.session.goi); server._COOLDOWN_TOAN_CUC["den"] = 0
for i in range(5):                                         # 5 lượt tra cứu tiếp theo (5 đoạn 10 ngày)
    assert len(c._fetch_paginated(U, "b%d" % i, "x")) == 1
assert len(c.session.goi) - n0 == 10, "mỗi lượt: 1 lần 429 (mã cũ) + 1 lần thành công, không có lượt 429 thứ 2"
assert not [x for x in ngu if x >= 2], ngu                 # không chờ 2s nào
assert server._COOLDOWN_TOAN_CUC["den"] == 0              # không bắt các luồng khác nghỉ
cap = c._trang_thai_captcha()
assert cap["so_lan_hoi"] == 6 and cap["giay_cho"] >= 0
print("PASS 1: mã captcha đã dùng hết lượt -> xin mã mới ngay, không chờ 2s, không bắt mọi luồng nghỉ; đếm số lần hỏi mã.")

# 429 với mã MỚI chưa dùng được lần nào = giới hạn tốc độ thật -> vẫn chờ 2s như cũ
class S2(S):
    def __init__(self): super().__init__(); self.lan = 0
    def get(self, url, headers=None, timeout=None):
        self.lan += 1
        if self.lan == 2:
            return R(429, {"message": "Too Many Requests"})
        return super().get(url, headers, timeout)
c2 = server.GDTClient.__new__(server.GDTClient); c2.session = S2(); c2.token = "T"
so2 = iter(range(1, 100))
c2.captcha_cb = lambda cancel_check=None: ("K", "N%d" % next(so2))
ngu.clear()
assert len(c2._fetch_paginated(U, "a", "x")) == 1
assert 2 in ngu, ngu
print("PASS 2: 429 khi mã chưa dùng được lần nào (giới hạn tốc độ thật) vẫn chờ 2s như cũ.")

# Dòng TIẾN ĐỘ chung: số đoạn xong/tổng, số hóa đơn đã lấy, ước thời gian còn lại, số lần hỏi mã
c3 = server.GDTClient.__new__(server.GDTClient); c3.session = S(); c3.token = "T"
so3 = iter(range(1, 100))
c3.captcha_cb = lambda cancel_check=None: ("K", "P%d" % next(so3))
td = []
kq = c3.query_invoices("01/07/2026", "30/09/2026", loai="sold", he_thong="sco-query", progress=td.append)
tong = [x for x in td if x.startswith("[TIẾN ĐỘ chung]")]
assert tong[0].startswith("[TIẾN ĐỘ chung] xong 0/10 đoạn"), tong[0]
assert "xong 3/10 đoạn 10 ngày — đã lấy 3 hóa đơn" in tong[3] and "còn 7 đoạn, ước ~" in tong[3], tong[3]
assert tong[-1].startswith("[TIẾN ĐỘ chung] ✓ xong 10/10 đoạn") and "hỏi mã captcha" in tong[-1], tong[-1]
html = open(os.path.join(_REPO_ROOT, "static", "index.html"), encoding="utf-8").read()
assert "(THÁNG|ĐOẠN|TIẾN ĐỘ)" in html
print("PASS 3: tra cứu hiện dòng tiến độ chung: xong k/N đoạn, đã lấy bao nhiêu hóa đơn, ước còn bao lâu, đã hỏi mã mấy lần.")

# Đoạn máy tính tiền ĐẦU TIÊN: lúc bắt đầu chưa biết trang Thuế đòi captcha -> bản cũ vẫn dò lặp 3-4 lần (mỗi lần thêm 1 lần nhập mã)
c4 = server.GDTClient.__new__(server.GDTClient); c4.session = S(); c4.token = "T"
so4 = iter(range(1, 100))
c4.captcha_cb = lambda cancel_check=None: ("K", "Q%d" % next(so4))
sao = []
c4._ban_sao_phien_moi = lambda: sao.append(1) or (_ for _ in ()).throw(RuntimeError("không dò lặp"))
res, total, loi, tb = c4._query_one_range_on_dinh("01/07/2026", "10/07/2026", "sold", 50, "sco-query")
assert len(res) == 1 and c4._trang_thai_captcha()["so_lan_hoi"] == 1 and sao == [], sao
print("PASS 4: đoạn máy tính tiền đầu tiên không dò lặp nữa khi trang Thuế vừa đòi captcha (đỡ 2-3 lần nhập mã).")
