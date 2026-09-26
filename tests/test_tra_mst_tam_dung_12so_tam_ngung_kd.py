import os
import sys
import time

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Regression test cho 3 lỗi/yêu cầu từ log thật lượt xuất Excel 35 MST:
#  1) MST 0317657700: masothue.com dò ra "Tạm ngừng KD có thời hạn" (XInvoice: "NNT tạm ngừng KD có
#     thời hạn") nhưng bị báo "tình trạng lạ chưa nhận diện được" -> MST bỏ trống dù đã tra ra (bộ
#     phân loại chỉ biết cụm đầy đủ "tạm ngừng kinh doanh", không biết viết tắt "KD").
#  2) MST 12 số 079183039914 (hộ kinh doanh dùng số định danh cá nhân làm MST —
#     https://masothue.com/079183039914-ho-kinh-doanh-nhua-mai-hoa) bị cắt còn 10 số '0791830399'
#     -> masothue.com đưa sang công ty khác (VNG 0303490096), XInvoice báo 404.
#  3) Người dùng yêu cầu "tạm ngưng chạy tracuunnt.gdt.gov.vn" (trang liên tục "Too Many Requests").

# ===== 1: nhận diện "tạm ngừng KD" (viết tắt) là CẢNH BÁO; "tạm ngừng hoạt động" không bị ghi nhầm
# thành "ngừng hoạt động" hẳn. =====
pl = server._phan_loai_trang_thai_mst
assert pl("Tạm ngừng KD có thời hạn") == ("Tạm ngừng kinh doanh", True)
assert pl("NNT tạm ngừng KD có thời hạn") == ("Tạm ngừng kinh doanh", True)
assert pl("Tạm ngừng hoạt động") == ("Tạm ngừng hoạt động", True)
assert pl("NNT ngừng hoạt động và đã đóng MST")[1] is True
assert pl("Đang hoạt động (đã được cấp GCN ĐKT)") == ("Đang hoạt động", False)
print("PASS 1: 'Tạm ngừng KD có thời hạn' được nhận diện là cảnh báo (tô đỏ).")

# ===== 2: khoá MST tra tình trạng — 12 số (định danh cá nhân) GIỮ NGUYÊN; 13 số (đơn vị trực thuộc)
# vẫn quy về 10 số gốc như trước; 10 số giữ nguyên. =====
assert server._mst_tra_cuu("079183039914") == "079183039914"
assert server._mst_tra_cuu("0312345678-001") == "0312345678"
assert server._mst_tra_cuu("0317657700") == "0317657700"
assert server._masothue_dung_mst({"tinh_trang": "Đang hoạt động", "mst_trang": "079183039914"}, "079183039914")
assert not server._masothue_dung_mst({"tinh_trang": "Đang hoạt động", "mst_trang": "0303490096"}, "079183039914")
print("PASS 2: MST 12 số giữ nguyên khi tra, MST chi nhánh 13 số vẫn quy về 10 số gốc.")


# ===== 3: đi đúng luồng trang masothue.com (driver giả, không cần Chrome) với ĐÚNG 2 MST lỗi thật. =====
class _DriverGia:
    def __init__(self, trang):
        self.trang = trang          # mst -> (mst_trang, tinh_trang)
        self.current_url = "about:blank"
        self.mst_da_mo = None

    def get(self, url):
        self.current_url = url
        self.mst_da_mo = url.split("q=")[1].split("&")[0] if "q=" in url else None

    def execute_script(self, js, *args):
        if js is server._JS_MASOTHUE_O_TIM:
            return None                           # không có ô tìm kiếm -> đi đường mở thẳng /Search/
        if js is server._JS_MASOTHUE_DOC:
            mst_trang, tinh_trang = self.trang.get(self.mst_da_mo, ("0303490096", "Đang hoạt động"))
            return {"tieu_de": mst_trang, "url": self.current_url, "tinh_trang": tinh_trang,
                    "mst_trang": mst_trang, "link": "", "chu": "", "co_mst": True, "cac_dong": []}
        return None


_goc = {k: getattr(server, k) for k in ("_MASOTHUE_KHOANG_CACH_GIAY", "_MASOTHUE_URL_TRANG_CHU")}
server._MASOTHUE_KHOANG_CACH_GIAY = 0.0
server._MASOTHUE_URL_TRANG_CHU = "http://trang-chu-gia/"
try:
    drv = _DriverGia({"0317657700": ("0317657700", "Tạm ngừng KD có thời hạn"),
                      "079183039914": ("079183039914", "Đang hoạt động")})
    kq = server._masothue_tra_1_mst_bang_trinh_duyet(drv, "0317657700", 8)
    assert kq == (True, "Tạm ngừng KD có thời hạn", True, None), f"got {kq!r}"
    kq = server._masothue_tra_1_mst_bang_trinh_duyet(drv, "079183039914", 8)
    assert kq == (True, "Đang hoạt động", False, None), f"got {kq!r}"
    # Đối chứng đúng lỗi cũ: tra bằng MST đã bị cắt 10 số -> trang của công ty khác -> không lấy.
    kq = server._masothue_tra_1_mst_bang_trinh_duyet(drv, "0791830399", 8)
    assert kq[0] is False and "0303490096" in kq[3], f"got {kq!r}"
finally:
    for k, v in _goc.items():
        setattr(server, k, v)
    server._MASOTHUE_TD["lan_mo_cuoi"] = 0.0
print("PASS 3: luồng masothue.com lấy được 'Tạm ngừng KD có thời hạn' (0317657700) và hộ kinh doanh "
      "MST 12 số (079183039914).")

# ===== 4: _tra_cuu_trang_thai_mst truyền ĐỦ 12 số xuống nguồn tra; tracuunnt ĐANG TẠM DỪNG -> không
# gọi; không nguồn nào chạy được thì ghi rõ lý do. =====
assert server._TRACUUNNT_TAM_DUNG is True, "Người dùng yêu cầu tạm ngưng tracuunnt.gdt.gov.vn"
_goc2 = {k: getattr(server, k) for k in (
    "_tra_cuu_mst_qua_masothue_trinh_duyet", "_tra_cuu_mst_qua_tracuunnt", "_mst_cache_doc_trong_ngay",
    "_mst_cache_ghi", "_MST_API_NGHI_GIUA_LUOT", "_XINVOICE_TAM_DUNG", "_lay_danh_sach_xinvoice_keys")}
goi = []
server._mst_cache_doc_trong_ngay = lambda m: None
server._mst_cache_ghi = lambda m, t, c: None
server._MST_API_NGHI_GIUA_LUOT = 0
server._lay_danh_sach_xinvoice_keys = lambda: []
server._tra_cuu_mst_qua_tracuunnt = lambda m, t: (goi.append(("tracuunnt", m)), (False, "", None, "x"))[1]
try:
    server._tra_cuu_mst_qua_masothue_trinh_duyet = lambda m, t: (
        goi.append(("masothue", m)), (True, "Đang hoạt động", False, None))[1]
    kq = server._tra_cuu_trang_thai_mst("079183039914")
    assert kq == {"trang_thai": "Đang hoạt động", "canh_bao": False}, kq
    assert goi == [("masothue", "079183039914")], f"Phải tra đủ 12 số — got {goi}"

    goi.clear()
    server._tra_cuu_mst_qua_masothue_trinh_duyet = lambda m, t: (
        goi.append(("masothue", m)), (False, "", None, "lỗi"))[1]
    kq = server._tra_cuu_trang_thai_mst("0317657700")
    assert goi == [("masothue", "0317657700")], f"tracuunnt đang tạm dừng -> KHÔNG được gọi — got {goi}"
    assert kq["ly_do_loi"] == "masothue.com: lỗi", kq

    goi.clear()
    server._tra_cuu_mst_qua_masothue_trinh_duyet = lambda m, t: None    # không mở được Chrome
    server._XINVOICE_TAM_DUNG = True
    kq = server._tra_cuu_trang_thai_mst("0317657700")
    assert kq["canh_bao"] is None and "không có nguồn tra MST nào chạy được" in kq["ly_do_loi"], kq
    assert goi == [], goi
finally:
    for k, v in _goc2.items():
        setattr(server, k, v)
print("PASS 4: tra đủ 12 số; tracuunnt đang tạm dừng không bị gọi; không nguồn nào chạy được thì ghi rõ.")

# ===== 5: export_excel dùng cùng khoá 12 số khi gom/khử trùng MST và lưu kết quả trong lượt. =====
src = open(os.path.join(_REPO_ROOT, "server.py"), encoding="utf-8").read()
i = src.index("def export_excel(")
than = src[i:src.index("\n@app.", i)]
i_c = than.index("    def _lay_trang_thai_mst_cached(")
i_p = than.index("    def _prefetch_trang_thai_mst(")
i_h = than.index("    # ----- BẢNG KÊ MUA VÀO")
assert "_chuan_mst(mst)[:10]" not in than[i_c:i_h] and than[i_c:i_h].count("_mst_tra_cuu(mst)") == 3, (
    "Gom/khử trùng MST khi dò tình trạng trong export_excel phải dùng _mst_tra_cuu (giữ 12 số).")
print("PASS 5: xuất Excel gom/khử trùng MST theo cùng khoá 12 số.")

print("\nALL DONE")
