import io
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import openpyxl
import server

# Hỗ trợ thay đổi GPKD: mở link hồ sơ trên cổng đăng ký kinh doanh bằng Chrome riêng đã đăng nhập,
# đọc các cặp "Tiêu đề : Giá trị", đi theo link các khối của CÙNG hồ sơ (an toàn, chỉ đọc), xuất Excel.

G = "https://dangkyquamang.dkkd.gov.vn/egazette/Forms/DW_DOCUMENTEdit.aspx?h=720"
DC = "https://dangkyquamang.dkkd.gov.vn/egazette/Forms/DW_Address.aspx?h=720"
NN = "https://dangkyquamang.dkkd.gov.vn/egazette/Forms/DW_Nganh.aspx?h=720&tab=2"

# 1) lọc link: cùng host + cùng mã hồ sơ; bỏ link nguy hiểm / hồ sơ khác / trang ngoài
ok = server._dkkd_link_cung_ho_so
assert ok(G, DC, "Địa chỉ trụ sở") and ok(G, NN, "Ngành nghề kinh doanh")
assert ok(G, DC, "Thông tin đăng ký thuế")
assert not ok(G, DC.replace("h=720", "h=721"), "Địa chỉ")                       # hồ sơ khác
assert not ok(G, "https://example.com/x.aspx?h=720", "Địa chỉ")                 # trang ngoài
assert not ok(G, DC + "&act=delete", "Địa chỉ")
for ten in ("Xóa hồ sơ", "Nộp hồ sơ", "Gửi hồ sơ", "Hủy", "Ký số", "Đăng xuất", "In"):
    assert not ok(G, DC, ten), ten
assert not ok("https://dangkyquamang.dkkd.gov.vn/home.aspx", DC, "Địa chỉ")    # link gốc không có mã hồ sơ -> không đi theo
print("PASS 1: chỉ đi theo link cùng hồ sơ, bỏ link xoá/nộp/gửi/huỷ/ký/thoát/in.")


class _Drv:
    def __init__(self, trang):
        self.trang, self.url, self.da_mo = trang, "", []

    def get(self, u):
        self.url = u
        self.da_mo.append(u)

    def execute_script(self, js, *a):
        return dict(self.trang.get(self.url, {"cap": []}), url=self.url)


server.time.sleep = lambda s: None
d = _Drv({
    G: {"khoi": "Thông tin chung", "cap": [["Tên doanh nghiệp", "CÔNG TY TNHH ABC"], ["Mã số DN", "0316267842"]],
        "links": [[DC, "Địa chỉ"], [NN, "Ngành nghề"], [DC + "&act=x", "Xóa"], ["https://khac.vn/a?h=720", "x"]]},
    DC: {"khoi": "Địa chỉ", "cap": [["Địa chỉ trụ sở", "1 Lê Lợi"]], "links": [[G, "Thông tin chung"]]},
    NN: {"khoi": "Ngành nghề", "cap": [["Ngành chính", "6201"]], "links": []},
})
dong, loi = server.dkkd_lay_ho_so(d, G, theo_khoi=True)
assert loi is None and d.da_mo == [G, DC, NN], d.da_mo
assert [(x["khoi"], x["truong"], x["gia_tri"]) for x in dong] == [
    ("Thông tin chung", "Tên doanh nghiệp", "CÔNG TY TNHH ABC"), ("Thông tin chung", "Mã số DN", "0316267842"),
    ("Địa chỉ", "Địa chỉ trụ sở", "1 Lê Lợi"), ("Ngành nghề", "Ngành chính", "6201")]
d2 = _Drv(d.trang)
dong2, _ = server.dkkd_lay_ho_so(d2, G, theo_khoi=False)
assert d2.da_mo == [G] and len(dong2) == 2
print("PASS 2: đọc hồ sơ + các khối cùng hồ sơ, không mở lại trang đã đọc; tắt 'theo khối' chỉ đọc 1 trang.")

# 3) chưa đăng nhập -> báo lỗi rõ
d3 = _Drv({G: {"cap": [], "co_o_mat_khau": True}})
dong3, loi3 = server.dkkd_lay_ho_so(d3, G)
assert dong3 == [] and "đăng nhập" in loi3
print("PASS 3: trang đăng nhập -> báo cần đăng nhập.")

# 4) Excel: Chi tiết + Tổng hợp (1 hồ sơ 1 dòng)
G2 = G.replace("h=720", "h=800")
data = server.dkkd_xuat_excel({G: dong, G2: [{"khoi": "Thông tin chung", "url": G2, "truong": "Mã số DN", "gia_tri": "0300000001"}]})
wb = openpyxl.load_workbook(io.BytesIO(data))
ct = [[c.value for c in r] for r in wb["Chi tiết"].iter_rows()]
assert ct[0] == ["Link hồ sơ", "Khối", "Trường", "Giá trị"] and len(ct) == 6
th = [[c.value for c in r] for r in wb["Tổng hợp"].iter_rows()]
assert th[0] == ["Link hồ sơ", "Tên doanh nghiệp", "Mã số DN", "Địa chỉ trụ sở", "Ngành chính"]
assert th[1][2] == "0316267842" and th[2] == [G2, None, "0300000001", None, None]
print("PASS 4: xuất Excel 2 sheet Chi tiết / Tổng hợp.")

# 5) endpoint: link không hợp lệ -> 400; giao diện đã bỏ TMĐT, có GPKD
try:
    server.dkkd_lay_du_lieu({"links": "abc\n  \nftp://x"})
    raise AssertionError("phải báo lỗi")
except server.HTTPException as e:
    assert e.status_code == 400
html = open(os.path.join(_REPO_ROOT, "static", "index.html"), encoding="utf-8").read()
src = open(os.path.join(_REPO_ROOT, "server.py"), encoding="utf-8").read()
assert "moTmdt" not in html and "Hỗ trợ xuất hoá đơn TMĐT" not in html and "/api/tmdt/" not in src
assert 'onclick="moGpkd()"' in html and "Hỗ trợ thay đổi GPKD" in html
i0 = src.index("# HỖ TRỢ THAY ĐỔI GPKD")
khoi = src[i0:src.index('if __name__ == "__main__":', i0)]
assert ".click()" not in khoi and ".submit(" not in khoi, "chỉ đọc: không bấm nút/gửi form"
print("PASS 5: bỏ TMĐT; mục GPKD có trên giao diện; không bấm nút/gửi form.")

print("\nALL DONE")
