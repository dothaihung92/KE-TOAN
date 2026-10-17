import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Ca thật (tra cứu hàng loạt 103 công ty): 1 công ty bị "curl: (56) Connection closed abruptly" và thử lại 239+ lần mỗi 3 giây trong khi
# các luồng khác vẫn lấy captcha/đăng nhập liên tục -> các công ty khác bị "Lỗi lấy captcha: Connection aborted" và bị bỏ qua.
# Nay: chờ tăng dần (3,6,12,24,48,60s), 1 truy vấn bỏ cuộc sau KET_NOI_TOI_DA_LIEN_TIEP lần liên tiếp, mọi luồng nghỉ chung khi có ngắt kết nối.
ngu = []
dong_ho = [5000.0]
server.time.time = lambda: dong_ho[0]
def _ngu(giay, cancel_check=None):
    ngu.append(giay); dong_ho[0] += giay
server._ngu_ktra_huy = _ngu
server.time.sleep = lambda s: None

assert [server._cho_thu_lai_ket_noi(n) for n in range(1, 9)] == [3, 6, 12, 24, 48, 60, 60, 60]
print("PASS 1: chờ tăng dần 3,6,12,24,48,60,60,60s (không còn cố định 3s).")


class Hong:
    """session luôn bị trang Thuế ngắt kết nối."""
    def __init__(self): self.n = 0; self.headers = {}
    def get(self, *a, **k):
        self.n += 1
        raise ConnectionError("Failed to perform, curl: (56) Connection closed abruptly.")


c = server.GDTClient.__new__(server.GDTClient)
c.token = "T"; c.impersonate = False; c._http11 = False
c.session = Hong()
c._dung_lai_session = lambda ep_http11=True: None
c._phien_moi_hoan_toan = lambda: None            # không mở kết nối thật trong test
thong_bao = []
try:
    c._fetch_paginated("https://x/api/sco-query/invoices/purchase", "tdlap=ge=01/10/2026", "Tim", progress=thong_bao.append)
    assert False, "phải bỏ cuộc"
except Exception as e:
    assert "Mất kết nối liên tục" in str(e) and server._la_loi_ket_noi(e), str(e)
assert c.session.n == server.KET_NOI_TOI_DA_LIEN_TIEP, c.session.n          # 8 lần, không phải 239
assert ngu[:5] == [3, 6, 12, 24, 48]
print("PASS 2: truy vấn bị ngắt kết nối liên tục bỏ cuộc sau", server.KET_NOI_TOI_DA_LIEN_TIEP, "lần (không còn thử vô hạn), lỗi vẫn được nhận diện là lỗi kết nối.")

# cooldown dùng chung: có ngắt kết nối -> luồng KHÁC cũng phải nghỉ trước khi gọi
ngu.clear(); dong_ho[0] = 9000.0
server._COOLDOWN_TOAN_CUC["den"] = 0.0
server._bao_ngat_ket_noi(30)
server._cho_het_cooldown(None, thong_bao.append)
assert ngu == [30.0] and any("tạm nghỉ" in t for t in thong_bao)
ngu.clear(); server._cho_het_cooldown(None); assert ngu == []                  # hết cooldown thì không nghỉ nữa
print("PASS 3: có ngắt kết nối -> mọi luồng cùng nghỉ (cooldown dùng chung), hết hạn thì chạy tiếp.")

# _dem_tong_nhanh: bỏ cuộc trả None (không chắc -> dò đầy đủ)
c.session = Hong()
assert c._dem_tong_nhanh("https://x/api/sco-query/invoices/purchase", "tdlap=ge=01/10/2026", "Tim") is None
assert c.session.n == server.KET_NOI_TOI_DA_LIEN_TIEP
print("PASS 4: đếm nhanh bị ngắt kết nối liên tục -> trả 'không chắc' sau", server.KET_NOI_TOI_DA_LIEN_TIEP, "lần.")

# đăng nhập tự động: gặp ngắt kết nối thì báo cooldown chung và chờ cooldown trước lần thử sau
class CapHong:
    token = None
    def __init__(self): self.n = 0
    def _dung_lai_session(self, ep_http11=False): pass
    def get_captcha(self): self.n += 1; raise Exception("('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))")
cap = CapHong()
server.get_client = lambda cid: cap
class DbGia:
    def execute(self, *a):
        class R:
            def fetchone(s): return {"password": "x", "username": "u", "mst": "1"}
        return R()
    def close(self): pass
server.db = lambda: DbGia()
ngu.clear(); server._COOLDOWN_TOAN_CUC["den"] = 0.0
ok, tb, so_lan, _ = server._tu_dong_dang_nhap(1, so_lan=3)
assert not ok and cap.n == 3 and server._la_loi_ket_noi(tb)
assert server._COOLDOWN_TOAN_CUC["den"] > dong_ho[0] - 200
print("PASS 5: đăng nhập gặp ngắt kết nối -> báo cooldown chung; kết quả vẫn là lỗi kết nối (để tra cứu hàng loạt tự thử lại cuối đợt).")

src = open(os.path.join(os.path.dirname(server.__file__), "server.py"), encoding="utf-8").read()
assert '(FETCH_JOBS.get(cid) or {})["ket_noi_loi"] = True' in src and "if _la_loi_ket_noi(es) and lan_thu >= 1:" in src
assert "if (FETCH_JOBS.get(cid) or {}).get(\"ket_noi_loi\"):" in src
print("PASS 6: tra cứu 1 công ty bị ngắt kết nối dai dẳng chỉ thử 2 lượt rồi đánh dấu để tra cứu hàng loạt thử lại cuối đợt.")
print("ALL DONE")
