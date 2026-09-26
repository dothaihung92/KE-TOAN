import os
import sys
import glob
import time
import shutil
import threading
import urllib.parse
import http.server

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Regression test cho tra MST qua masothue.com bằng Chrome ẩn (_tra_cuu_mst_qua_masothue_trinh_duyet)
# — người dùng yêu cầu thử lại masothue.com vì tracuunnt.gdt.gov.vn đang bị giới hạn tốc độ ("Too
# Many Requests"). Bản cũ (đã gỡ) gửi request thô nên bị Cloudflare chặn/hủy phiên; bản này chạy
# qua CHÍNH Chrome ẩn dùng chung với tracuunnt, và chỉ đọc đúng ô "Tình trạng" + đối chiếu ô "Mã
# số thuế" (bản cũ quét từ khoá trên TOÀN trang, dễ bắt nhầm chữ "ngừng hoạt động" ở mục khác).
#
# Phần A (luôn chạy): chuỗi nguồn trong _tra_cuu_trang_thai_mst, tạm nghỉ/tạm tắt.
# Phần B (cần Chrome + chromedriver, tự BỎ QUA nếu không có): Chrome THẬT với máy chủ GIẢ LẬP các
# kiểu trang của masothue.com — KHÔNG phải trang thật (sandbox bị chặn mạng tới masothue.com).

_goc = {k: getattr(server, k) for k in (
    "_tracuunnt_tao_trinh_duyet", "_tra_cuu_mst_qua_tracuunnt", "_tra_cuu_mst_qua_masothue_trinh_duyet",
    "_MASOTHUE_URL_TIM", "_MASOTHUE_KHOANG_CACH_GIAY", "_MST_API_NGHI_GIUA_LUOT", "_XINVOICE_TAM_DUNG")}


def _dat_lai():
    st = server._TRACUUNNT_TD
    drv = st["drv"]
    st.update(drv=None, loi_khoi_tao=None, lan_loi_khoi_tao=0.0, lan_dung_cuoi=0.0, lan_gui_cuoi=0.0)
    if drv is not None:
        try:
            drv.quit()
        except Exception:
            pass
    server._MASOTHUE_TD.update(lan_mo_cuoi=0.0, nghi_den=0.0, loi_lien_tiep=0, ly_do_nghi="")


def _khoi_phuc():
    for k, v in _goc.items():
        setattr(server, k, v)
    _dat_lai()


# ============================ PHẦN A ============================
server._MST_API_NGHI_GIUA_LUOT = 0
server._XINVOICE_TAM_DUNG = True
try:
    # ===== A1: tracuunnt thất bại (vd đang bị giới hạn tốc độ) -> tra tiếp qua masothue.com, tra
    # được thì trả kết quả của masothue.com, không còn lỗi. =====
    server._tra_cuu_mst_qua_tracuunnt = lambda m, t: (False, "", None, "đang giới hạn tốc độ (Too Many Requests)")
    server._tra_cuu_mst_qua_masothue_trinh_duyet = lambda m, t: (
        True, "Đang hoạt động (đã được cấp GCN ĐKT)", False, None)
    kq = server._tra_cuu_trang_thai_mst("0301234567")
    assert kq == {"trang_thai": "Đang hoạt động (đã được cấp GCN ĐKT)", "canh_bao": False}, f"got {kq!r}"

    # ===== A2: cả 2 nguồn thất bại -> lý do ghi đủ cả 2 nguồn. =====
    server._tra_cuu_mst_qua_masothue_trinh_duyet = lambda m, t: (False, "", None, "Cloudflare chặn")
    kq = server._tra_cuu_trang_thai_mst("0301234567")
    assert kq["canh_bao"] is None and "tracuunnt.gdt.gov.vn: đang giới hạn" in kq["ly_do_loi"] \
        and "masothue.com: Cloudflare chặn" in kq["ly_do_loi"], f"got {kq!r}"

    # ===== A3: không mở được Chrome (None) -> bỏ qua masothue.com, lý do giữ nguyên như trước. =====
    server._tra_cuu_mst_qua_masothue_trinh_duyet = lambda m, t: None
    kq = server._tra_cuu_trang_thai_mst("0301234567")
    assert kq["ly_do_loi"] == "tracuunnt.gdt.gov.vn: đang giới hạn tốc độ (Too Many Requests)", f"got {kq!r}"

    # ===== A4: tracuunnt tra được -> KHÔNG gọi masothue.com (không tốn thêm lượt truy cập). =====
    goi = []
    server._tra_cuu_mst_qua_tracuunnt = lambda m, t: (True, "NNT đang hoạt động", False, None)
    server._tra_cuu_mst_qua_masothue_trinh_duyet = lambda m, t: goi.append(m)
    kq = server._tra_cuu_trang_thai_mst("0301234567")
    assert kq["trang_thai"] == "NNT đang hoạt động" and goi == [], f"got {kq!r}, goi={goi}"
finally:
    _khoi_phuc()
print("PASS A1-A4: chuỗi nguồn tracuunnt -> masothue.com (Chrome ẩn) -> XInvoice đúng thứ tự, gộp lý do "
      "lỗi đủ các nguồn, không gọi masothue khi tracuunnt đã tra được.")

# ===== A5: đang tạm nghỉ (bị giới hạn/chặn) hoặc đã thất bại liên tiếp quá ngưỡng -> trả lỗi NGAY,
# không mở Chrome/không truy cập trang; đầu mỗi lượt xuất Excel bộ đếm được đặt lại. =====
so_lan_mo = [0]
server._tracuunnt_tao_trinh_duyet = lambda: so_lan_mo.__setitem__(0, so_lan_mo[0] + 1)
try:
    server._masothue_tam_nghi("masothue.com đang giới hạn tốc độ (Too Many Requests)")
    ok, tt, cb, ly_do = server._tra_cuu_mst_qua_masothue_trinh_duyet("0301234567", 8)
    assert ok is False and "tạm dừng tra masothue.com tới" in ly_do and so_lan_mo[0] == 0, f"got {ly_do!r}"
    _dat_lai()
    server._MASOTHUE_TD["loi_lien_tiep"] = server._MASOTHUE_NGUONG_TAT
    ok, tt, cb, ly_do = server._tra_cuu_mst_qua_masothue_trinh_duyet("0301234567", 8)
    assert ok is False and "tạm tắt" in ly_do and so_lan_mo[0] == 0, f"got {ly_do!r}"
    server._tracuunnt_dat_lai_dem_loi()
    assert server._MASOTHUE_TD["loi_lien_tiep"] == 0
finally:
    _khoi_phuc()
print("PASS A5: đang tạm nghỉ/tạm tắt thì không truy cập masothue.com; bộ đếm đặt lại mỗi lượt xuất Excel.")


# ============================ PHẦN B ============================
THONG_KE = {"lan_mo": []}


def _trang_cty(mst, tinh_trang):
    return f"""<html><head><meta charset="utf-8"><title>{mst} - CÔNG TY GIẢ LẬP</title></head><body>
<div class="sidebar"><h3>Doanh nghiệp mới cập nhật</h3>
<p>CÔNG TY KHÁC 0399999999 — Ngừng hoạt động và đã đóng MST</p></div>
<table class="table-taxinfo">
<tr><th colspan="2">CÔNG TY GIẢ LẬP {mst}</th></tr>
<tr><td><i class="fa fa-hashtag"></i> Mã số thuế</td><td>{mst}</td></tr>
<tr><td>Địa chỉ</td><td>1 Đường A, TP Hồ Chí Minh</td></tr>
<tr><td><i class="fa fa-info"></i> Tình trạng</td><td><a href="#">{tinh_trang}</a></td></tr>
</table></body></html>"""


def _tinh_trang_gia(mst):
    return ("Ngừng hoạt động và đã đóng MST" if mst == "0317777777"
            else "Đang hoạt động (đã được cấp GCN ĐKT)")


class _MayChuGia(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _tra(self, ma, noi_dung, loai="text/html; charset=utf-8", them=None):
        b = noi_dung.encode("utf-8")
        self.send_response(ma)
        self.send_header("Content-Type", loai)
        for k, v in (them or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path == "/favicon.ico":
            return self._tra(404, "", "text/plain")
        THONG_KE["lan_mo"].append((time.time(), self.path))
        if u.path == "/Search/":
            q = urllib.parse.parse_qs(u.query).get("q", [""])[0]
            if q == "0311111111":      # tìm đúng MST -> chuyển thẳng tới trang công ty (như trang thật)
                return self._tra(302, "", them={"Location": f"/{q}-cong-ty-gia-lap"})
            if q == "0312222222":      # ra trang danh sách kết quả -> phải tự mở đúng link
                return self._tra(200, f"""<html><head><meta charset="utf-8"><title>Tìm kiếm</title></head>
<body><a href="/0319999999-cong-ty-khac">CÔNG TY KHÁC</a> <a href="/{q}-cong-ty-gia-lap">CÔNG TY GIẢ LẬP</a>
</body></html>""")
            if q == "0313333333":      # trang kiểm tra JS của Cloudflare, tự chuyển sau 1,5 giây
                return self._tra(200, f"""<html><head><title>Just a moment...</title></head><body>
Checking your browser before accessing masothue.com.
<script>setTimeout(function(){{ location.href = '/{q}-cong-ty-gia-lap'; }}, 1500);</script></body></html>""")
            if q == "0314444444":
                return self._tra(429, "Too Many Requests", "text/plain")
            if q == "0315555555":
                return self._tra(403, """<html><head><title>Attention Required! | Cloudflare</title></head>
<body>Sorry, you have been blocked. You are unable to access masothue.com</body></html>""")
            if q == "0316666666":      # trang lại hiện thông tin 1 MST KHÁC
                return self._tra(200, _trang_cty("0319999999", "Đang hoạt động (đã được cấp GCN ĐKT)"))
            return self._tra(200, _trang_cty(q, _tinh_trang_gia(q)))
        mst = u.path.strip("/").split("-")[0]
        return self._tra(200, _trang_cty(mst, _tinh_trang_gia(mst)))


def _tao_chrome_sandbox():
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    cac_chrome = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"))
    duong_driver = shutil.which("chromedriver")
    if not cac_chrome or not duong_driver:
        raise RuntimeError("không có Chromium/chromedriver dựng sẵn")
    o = Options()
    o.binary_location = cac_chrome[-1]
    for a in ("--headless=new", "--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu",
              f"--user-agent={server._DVC_UA}"):
        o.add_argument(a)
    drv = webdriver.Chrome(options=o, service=Service(duong_driver, service_args=["--disable-build-check"]))
    drv.set_page_load_timeout(25)
    drv.set_script_timeout(20)
    return drv


cach_mo = None
for _ham in (_tao_chrome_sandbox, _goc["_tracuunnt_tao_trinh_duyet"]):
    try:
        _ham().quit()
        cach_mo = _ham
        break
    except Exception:
        continue
if cach_mo is None:
    print("BỎ QUA PHẦN B: máy này không mở được Chrome + chromedriver.")
    print("\nALL DONE")
    sys.exit(0)

may_chu = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _MayChuGia)
threading.Thread(target=may_chu.serve_forever, daemon=True).start()
server._MASOTHUE_URL_TIM = f"http://127.0.0.1:{may_chu.server_address[1]}/Search/?q={{mst}}&type=auto"
server._tracuunnt_tao_trinh_duyet = cach_mo
server._MASOTHUE_KHOANG_CACH_GIAY = 0.0
tra = server._tra_cuu_mst_qua_masothue_trinh_duyet
try:
    _dat_lai()

    # ===== B1 (QUAN TRỌNG): tìm theo MST -> chuyển thẳng tới trang công ty -> đọc ĐÚNG ô "Tình
    # trạng" ("Đang hoạt động"), KHÔNG bị bắt nhầm chữ "Ngừng hoạt động" ở mục bên cạnh trang (bản
    # cũ quét từ khoá toàn trang sẽ tô đỏ nhầm công ty đang hoạt động bình thường). =====
    kq = tra("0311111111", 8)
    assert kq == (True, "Đang hoạt động (đã được cấp GCN ĐKT)", False, None), f"got {kq!r}"
    print("PASS B1: đọc đúng ô 'Tình trạng' của đúng công ty, không bắt nhầm chữ ở mục khác trên trang.")

    # ===== B2: trang danh sách kết quả -> tự mở đúng link của MST cần tra (không lấy link đầu). =====
    kq = tra("0312222222", 8)
    assert kq[0] is True, f"got {kq!r}"
    assert THONG_KE["lan_mo"][-1][1].startswith("/0312222222-"), f"got {THONG_KE['lan_mo'][-2:]}"
    print("PASS B2: trang danh sách kết quả -> mở đúng link của MST cần tra.")

    # ===== B3: trang kiểm tra JavaScript của Cloudflare ("Just a moment...") -> Chrome tự chạy, chờ
    # qua rồi đọc được trang công ty (đúng lý do bản request thô cũ không làm được). =====
    kq = tra("0313333333", 8)
    assert kq[0] is True, f"got {kq!r}"
    print("PASS B3: chờ qua trang kiểm tra JavaScript của Cloudflare rồi tra được.")

    # ===== B4: MST có tình trạng xấu -> canh_bao=True (tô đỏ). =====
    kq = tra("0317777777", 8)
    assert kq[0] is True and kq[2] is True and "Ngừng hoạt động" in kq[1], f"got {kq!r}"
    print("PASS B4: tình trạng 'Ngừng hoạt động' được nhận diện là cảnh báo.")

    # ===== B5: trang hiện thông tin của MST KHÁC -> không được lấy (tránh gán tình trạng nhầm công ty). =====
    kq = tra("0316666666", 8)
    assert kq[0] is False and "MST khác" in kq[3], f"got {kq!r}"
    print("PASS B5: trang hiện MST khác -> không lấy tình trạng của công ty khác.")

    # ===== B6: "Too Many Requests" -> dừng, tạm nghỉ; MST kế tiếp không truy cập trang nữa. =====
    kq = tra("0314444444", 8)
    assert kq[0] is False and "Too Many Requests" in kq[3] and "tạm dừng" in kq[3], f"got {kq!r}"
    n = len(THONG_KE["lan_mo"])
    kq = tra("0311111111", 8)
    assert kq[0] is False and len(THONG_KE["lan_mo"]) == n, "Đang tạm nghỉ thì không được truy cập trang."
    _dat_lai()
    print("PASS B6: 'Too Many Requests' -> tạm nghỉ, không truy cập tiếp.")

    # ===== B7: Cloudflare chặn hẳn ("Sorry, you have been blocked") -> báo rõ, tạm nghỉ. =====
    kq = tra("0315555555", 8)
    assert kq[0] is False and "Cloudflare" in kq[3] and "tạm dừng" in kq[3], f"got {kq!r}"
    _dat_lai()
    print("PASS B7: Cloudflare chặn hẳn -> báo rõ lý do, tạm nghỉ.")

    # ===== B8: giãn cách tối thiểu giữa 2 lần mở trang masothue.com. =====
    server._MASOTHUE_KHOANG_CACH_GIAY = 1.5
    n = len(THONG_KE["lan_mo"])
    assert tra("0311111111", 8)[0] is True and tra("0318888888", 8)[0] is True
    lan_tim = [t for t, p in THONG_KE["lan_mo"][n:] if p.startswith("/Search/")]
    assert len(lan_tim) == 2 and lan_tim[1] - lan_tim[0] >= 1.4, f"got {lan_tim}"
    print("PASS B8: 2 lần mở trang masothue.com được giãn cách đúng khoảng tối thiểu.")
finally:
    _khoi_phuc()
    may_chu.shutdown()

print("\nALL DONE")
