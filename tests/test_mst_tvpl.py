import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Nguồn tra tình trạng MST qua thuvienphapluat.vn (Chrome ẩn): mở trang tìm theo MST -> link
# "...-mst-<MST>.html" -> đọc mục "Tình trạng". Chuỗi nguồn: masothue.com -> thuvienphapluat.vn ->
# (tracuunnt nếu bật) -> XInvoice.

MST = "0316267842"
URL_CTY = f"https://thuvienphapluat.vn/ma-so-thue/cong-ty-tnhh-eyeiyagi-mst-{MST}.html"


class _Drv:
    def __init__(self, trang):
        self.trang = trang      # {url: kết quả JS}
        self.url = ""
        self.da_mo = []

    def get(self, url):
        self.url = url
        self.da_mo.append(url)

    def execute_script(self, js, *a):
        kq = dict(self.trang.get(self.url) or {"tieu_de": "Không tìm thấy", "chu": "", "url": self.url})
        kq.setdefault("url", self.url)
        return kq


server.time.sleep = lambda s: None
server._TVPL_KHOANG_CACH_GIAY = (0, 0)
url_tim = server._TVPL_URL_TIM.format(mst=MST)

# 1) trang tìm -> link đúng MST -> đọc tình trạng
d = _Drv({url_tim: {"link": URL_CTY, "chu": "kết quả"},
          URL_CTY: {"tinh_trang": "Đang hoạt động (đã được cấp GCN ĐKT)", "co_mst": True, "chu": "..."}})
kq = server._tvpl_tra_1_mst_bang_trinh_duyet(d, MST, 8)
assert kq == (True, "Đang hoạt động (đã được cấp GCN ĐKT)", False, None), kq
assert d.da_mo == [url_tim, URL_CTY]
print("PASS 1: tìm theo MST -> mở trang công ty -> 'Đang hoạt động'.")

# 2) tình trạng xấu -> cảnh báo
d = _Drv({url_tim: {"link": URL_CTY}, URL_CTY: {"tinh_trang": "NNT ngừng hoạt động và đã đóng MST", "co_mst": True}})
ok, tt, cb, _ = server._tvpl_tra_1_mst_bang_trinh_duyet(d, MST, 8)
assert ok and cb is True, (ok, tt, cb)
print("PASS 2: ngừng hoạt động -> cảnh báo (tô đỏ).")

# 3) trang hiện MST khác / không có link -> thất bại, không đoán
khac = "https://thuvienphapluat.vn/ma-so-thue/cong-ty-khac-mst-0300000001.html"
d = _Drv({url_tim: {"link": khac}, khac: {"tinh_trang": "Đang hoạt động", "co_mst": False}})
ok, tt, cb, ly_do = server._tvpl_tra_1_mst_bang_trinh_duyet(d, MST, 8)
assert not ok and cb is None and "không tìm thấy trang thông tin" in ly_do, ly_do
d = _Drv({url_tim: {"tinh_trang": "Đang hoạt động", "chu": "kết quả rỗng"}})
ok, tt, cb, ly_do = server._tvpl_tra_1_mst_bang_trinh_duyet(d, MST, 8)
assert not ok and cb is None
print("PASS 3: không đúng trang của MST -> không nhận kết quả.")

# 4) tình trạng lạ -> thất bại; bị chặn/giới hạn -> tạm nghỉ
d = _Drv({url_tim: {"link": URL_CTY}, URL_CTY: {"tinh_trang": "abc xyz", "co_mst": True}})
assert not server._tvpl_tra_1_mst_bang_trinh_duyet(d, MST, 8)[0]
d = _Drv({url_tim: {"tieu_de": "Too Many Requests", "chu": ""}})
ok, _, _, ly_do = server._tvpl_tra_1_mst_bang_trinh_duyet(d, MST, 8)
assert not ok and "tạm dừng tra thuvienphapluat.vn" in ly_do and server._tvpl_ly_do_tam_dung()
server._TVPL_TD["nghi_den"] = 0
print("PASS 4: tình trạng lạ không đoán; bị giới hạn tốc độ -> tạm dừng nguồn này.")

# 5) chuỗi nguồn: masothue thất bại -> thuvienphapluat tra được, ghi cache
goc = (server._tra_cuu_mst_qua_masothue_trinh_duyet, server._tra_cuu_mst_qua_tvpl_trinh_duyet,
       server._mst_cache_doc_trong_ngay, server._mst_cache_ghi, server._lay_danh_sach_xinvoice_keys)
ghi = []
server._tra_cuu_mst_qua_masothue_trinh_duyet = lambda m, t: (False, "", None, "lỗi giả")
server._tra_cuu_mst_qua_tvpl_trinh_duyet = lambda m, t: (True, "Tạm ngừng kinh doanh có thời hạn", True, None)
server._mst_cache_doc_trong_ngay = lambda m: None
server._mst_cache_ghi = lambda *a: ghi.append(a)
server._lay_danh_sach_xinvoice_keys = lambda: []
try:
    kq = server._tra_cuu_trang_thai_mst(MST)
    assert kq == {"trang_thai": "Tạm ngừng kinh doanh có thời hạn", "canh_bao": True}, kq
    assert ghi and ghi[0][0] == MST
    server._tra_cuu_mst_qua_tvpl_trinh_duyet = lambda m, t: (False, "", None, "không thấy")
    kq = server._tra_cuu_trang_thai_mst(MST)
    assert kq["canh_bao"] is None and "thuvienphapluat.vn: không thấy" in kq["ly_do_loi"], kq
finally:
    (server._tra_cuu_mst_qua_masothue_trinh_duyet, server._tra_cuu_mst_qua_tvpl_trinh_duyet,
     server._mst_cache_doc_trong_ngay, server._mst_cache_ghi, server._lay_danh_sach_xinvoice_keys) = goc
print("PASS 5: masothue.com không tra được -> dùng thuvienphapluat.vn; lỗi thì ghi rõ lý do.")

print("\nALL DONE")
