import os
import sys
import io
import glob
import time
import shutil
import random
import threading
import urllib.parse
import http.server

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Regression test cho tra MST qua Chrome ẩn (_tra_cuu_mst_qua_tracuunnt_trinh_duyet) — log thật người
# dùng gửi: MỌI MST đều thất bại 6/6 lần, trang trả về đúng câu "Vui lòng nhập đúng mã xác nhận!" dù
# OCR đã được xác minh độc lập là đọc ĐÚNG ảnh nhận được, và thử nghỉ 2-3s giữa các lần thử cũng
# không cải thiện -> ảnh ta đọc không phải ảnh máy chủ dùng để so khi gửi request thô, trong khi
# người dùng gõ tay trên trình duyệt thật vẫn tra được. Cổng này đứng sau cùng loại WAF F5 với
# dichvucong (nơi phần mềm đã phải chuyển sang Chrome ẩn) -> tra bằng Chrome ẩn: đọc ĐÚNG ảnh
# captcha trang đang hiển thị, điền form, bấm CHÍNH nút "Tra cứu" của trang.
#
# Phần A (luôn chạy, không cần Chrome): rơi về cách cũ khi không mở được Chrome, không thử mở lại
# Chrome cho từng MST, Chrome hỏng giữa chừng thì bỏ phiên hỏng, đặt lại bộ đếm lỗi mỗi lượt xuất.
# Phần B (cần Chrome + chromedriver, tự BỎ QUA nếu máy không có): chạy Chrome THẬT với 1 máy chủ
# GIẢ LẬP form tracuunnt (phiên cookie, captcha dùng 1 lần, nút "Tra cứu" gọi JS của trang, alert()
# khi mã sai độ dài) — KHÔNG phải trang thật (sandbox bị chặn mạng tới trang thật), nhưng xác nhận
# đúng toàn bộ phần JS/luồng điều khiển trình duyệt.


def _dat_lai_trang_thai_trinh_duyet():
    st = server._TRACUUNNT_TD
    drv = st["drv"]
    st.update(drv=None, loi_khoi_tao=None, lan_loi_khoi_tao=0.0, lan_dung_cuoi=0.0)
    if drv is not None:
        try:
            drv.quit()
        except Exception:
            pass
    server._tracuunnt_dat_lai_dem_loi()


_goc = {k: getattr(server, k) for k in (
    "_tracuunnt_tao_trinh_duyet", "_tao_session_tracuunnt", "_get_ddddocr", "_ocr_png", "_TRACUUNNT_URL")}


def _khoi_phuc():
    for k, v in _goc.items():
        setattr(server, k, v)
    _dat_lai_trang_thai_trinh_duyet()


class _SessionLoiMang:
    def __init__(self, *a, **kw):
        self.headers = {}

    def get(self, *a, **kw):
        raise ConnectionError("mô phỏng: không kết nối được")


# ============================ PHẦN A ============================
server._get_ddddocr = lambda: object()

# ===== A1: không mở được Chrome -> _tra_cuu_mst_qua_tracuunnt_trinh_duyet trả None, hàm chính rơi
# về cách gửi request trực tiếp cũ VÀ ghi rõ lý do vào thông báo lỗi (để log người dùng gửi biết
# lượt đó KHÔNG chạy qua Chrome). Lượt MST thứ 2 KHÔNG thử mở Chrome lại (mỗi lần thử tốn vài
# giây, nhân lên hàng chục MST sẽ ngốn hết ngân sách thời gian). =====
_dat_lai_trang_thai_trinh_duyet()
so_lan_mo = [0]


def _mo_chrome_loi():
    so_lan_mo[0] += 1
    raise RuntimeError("mô phỏng: máy chưa cài Chrome")


server._tracuunnt_tao_trinh_duyet = _mo_chrome_loi
server._tao_session_tracuunnt = lambda dung_curl_cffi=True: _SessionLoiMang()
try:
    assert server._tra_cuu_mst_qua_tracuunnt_trinh_duyet("0301234567", 8) is None
    ok, tt, cb, ly_do = server._tra_cuu_mst_qua_tracuunnt("0301234567", 8)
    assert ok is False and "lỗi kết nối" in ly_do and "không mở được Chrome ẩn" in ly_do \
        and "chưa cài Chrome" in ly_do, f"Phải rơi về cách cũ và ghi rõ lý do không dùng Chrome — got {ly_do!r}"
    assert so_lan_mo[0] == 1, (
        f"Mở Chrome lỗi thì trong {server._TRACUUNNT_TD_THU_LAI_KHOI_TAO_GIAY}s sau KHÔNG được thử mở lại "
        f"cho từng MST — got {so_lan_mo[0]} lần mở")
finally:
    _khoi_phuc()
print("PASS A1: không mở được Chrome -> rơi về cách gửi request trực tiếp, ghi rõ lý do, không thử mở "
      "Chrome lại cho từng MST.")


# ===== A2: Chrome treo/bị đóng giữa chừng -> trả lỗi (không crash cả lượt xuất Excel), bỏ phiên
# hỏng (quit + drv=None) để lượt sau tự mở Chrome mới. =====
class _DriverHong:
    def __init__(self):
        self.da_quit = False

    def execute_script(self, *a):
        raise RuntimeError("chrome not reachable")

    def get(self, url):
        raise RuntimeError("chrome not reachable")

    def quit(self):
        self.da_quit = True


_dat_lai_trang_thai_trinh_duyet()
drv_hong = _DriverHong()
server._tracuunnt_tao_trinh_duyet = lambda: drv_hong
server._get_ddddocr = lambda: object()
try:
    ok, tt, cb, ly_do = server._tra_cuu_mst_qua_tracuunnt_trinh_duyet("0301234567", 8)
    assert ok is False and "lỗi trình duyệt ẩn" in ly_do, f"got {ly_do!r}"
    assert drv_hong.da_quit and server._TRACUUNNT_TD["drv"] is None, (
        "Chrome hỏng phải bị đóng và bỏ khỏi trạng thái dùng chung để lượt sau mở Chrome mới.")
finally:
    _khoi_phuc()
print("PASS A2: Chrome hỏng giữa chừng -> trả lỗi rõ ràng, bỏ phiên hỏng để lượt sau mở lại.")


# ===== A3: bộ đếm lỗi liên tiếp _TRACUUNNT_STATE trước đây KHÔNG BAO GIỜ được đặt lại giữa các
# lượt xuất Excel -> chạm ngưỡng 1 lần là tắt nguồn tracuunnt LUÔN tới khi khởi động lại phần mềm.
# Phải đặt lại ở đầu mỗi lượt xuất Excel có bật tra MST. =====
with server._TRACUUNNT_STATE["lock"]:
    server._TRACUUNNT_STATE["loi_lien_tiep"] = server._TRACUUNNT_NGUONG_TAT
ok, tt, cb, ly_do = server._tra_cuu_mst_qua_tracuunnt("0301234567", 8)
assert ok is False and "tạm tắt" in ly_do, f"got {ly_do!r}"
server._tracuunnt_dat_lai_dem_loi()
assert server._TRACUUNNT_STATE["loi_lien_tiep"] == 0
src = open(os.path.join(_REPO_ROOT, "server.py"), encoding="utf-8").read()
i_pf = src.index("    def _prefetch_trang_thai_mst(")
than_pf = src[i_pf:src.index("\n    # -----", i_pf)]
assert than_pf.index("_tracuunnt_dat_lai_dem_loi()") < than_pf.index("ThreadPoolExecutor"), (
    "_prefetch_trang_thai_mst (đầu mỗi lượt dò MST khi xuất Excel) phải đặt lại bộ đếm lỗi tracuunnt "
    "TRƯỚC khi bắt đầu tra.")
print("PASS A3: bộ đếm lỗi liên tiếp tracuunnt được đặt lại ở đầu mỗi lượt xuất Excel.")


# ============================ PHẦN B ============================
_KY_TU = "abcdefghjkmnpqrstuvwxyz23456789"
PHIEN = {}
THONG_KE = {"get_form": 0, "get_captcha": 0, "post": 0, "cm": []}
_khoa_tk = threading.Lock()


def _png_tu_ma(ma):
    """Ảnh 'captcha' giả: mỗi ký tự là 1 điểm ảnh có kênh đỏ = mã ký tự (OCR giả đọc lại được)."""
    from PIL import Image
    im = Image.new("RGB", (len(ma), 1), "white")
    for i, ch in enumerate(ma):
        im.putpixel((i, 0), (ord(ch), 0, 0))
    b = io.BytesIO()
    im.save(b, "PNG")
    return b.getvalue()


def _ocr_gia_doc(png):
    from PIL import Image
    im = Image.open(io.BytesIO(png)).convert("RGB")
    return "".join(chr(im.getpixel((x, 0))[0]) for x in range(im.width))


_TRANG = """<html><head><meta charset="utf-8"><title>Tra cứu thông tin người nộp thuế</title>
<script>
function search() {
  var f = document.forms['myform'];
  if (f.captcha.value.length != 5) { alert('Vui lòng nhập mã xác nhận!'); return; }
  f.cm.value = 'cm';
  f.submit();
}
</script></head><body>
<form name="myform" method="post" action="/tcnnt/mstdn.jsp">
<input type="hidden" name="cm" value="">
Mã số thuế <input type="text" name="mst">
Tên <input type="text" name="fullname"> Địa chỉ <input type="text" name="address">
CMT <input type="text" name="cmt">
Mã xác nhận <input type="text" name="captcha"> <img src="/tcnnt/captcha.png">
<input type="button" value="Tra cứu" onclick="search()">
</form>
%s
</body></html>"""


class _MayChuGia(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _phien(self):
        ck = self.headers.get("Cookie") or ""
        for p in ck.split(";"):
            k, _, v = p.strip().partition("=")
            if k == "JSESSIONID" and v in PHIEN:
                return v, False
        sid = "S%06d" % random.randint(0, 999999)
        PHIEN[sid] = {"ma": None}
        return sid, True

    def _tra(self, ma_http, loai, noi_dung, sid, moi):
        self.send_response(ma_http)
        self.send_header("Content-Type", loai)
        self.send_header("Cache-Control", "no-store")
        if moi:
            self.send_header("Set-Cookie", f"JSESSIONID={sid}; Path=/")
        self.send_header("Content-Length", str(len(noi_dung)))
        self.end_headers()
        self.wfile.write(noi_dung)

    def do_GET(self):
        sid, moi = self._phien()
        duong = urllib.parse.urlparse(self.path).path
        if duong == "/tcnnt/mstdn.jsp":
            with _khoa_tk:
                THONG_KE["get_form"] += 1
            self._tra(200, "text/html; charset=utf-8", (_TRANG % "").encode("utf-8"), sid, moi)
        elif duong == "/tcnnt/captcha.png":
            ma = "".join(random.choice(_KY_TU) for _ in range(5))
            PHIEN[sid]["ma"] = ma
            with _khoa_tk:
                THONG_KE["get_captcha"] += 1
            self._tra(200, "image/png", _png_tu_ma(ma), sid, moi)
        else:
            self._tra(404, "text/plain", b"not found", sid, moi)

    def do_POST(self):
        sid, moi = self._phien()
        dai = int(self.headers.get("Content-Length") or 0)
        du_lieu = urllib.parse.parse_qs(self.rfile.read(dai).decode("utf-8"), keep_blank_values=True)
        lay = lambda k: (du_lieu.get(k) or [""])[0]
        ma_dung = PHIEN[sid]["ma"]
        PHIEN[sid]["ma"] = None                      # captcha dùng 1 lần như máy chủ thật
        with _khoa_tk:
            THONG_KE["post"] += 1
            THONG_KE["cm"].append(lay("cm"))
        if lay("cm") != "cm" or not ma_dung or lay("captcha") != ma_dung:
            than = '<p style="color:red">Vui lòng nhập đúng mã xác nhận!</p>'
        else:
            than = ("<table><tr><th>STT</th><th>MST</th><th>Tên người nộp thuế</th><th>Địa chỉ</th>"
                    "<th>Cơ quan thuế</th><th>Trạng thái MST</th></tr>"
                    f"<tr><td>1</td><td>{lay('mst')}</td><td>CÔNG TY GIẢ LẬP</td><td>1 Đường A</td>"
                    "<td>Thuế cơ sở 1</td><td>NNT đang hoạt động</td></tr></table>")
        self._tra(200, "text/html; charset=utf-8", (_TRANG % than).encode("utf-8"), sid, moi)


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
              "--disable-blink-features=AutomationControlled", f"--user-agent={server._DVC_UA}"):
        o.add_argument(a)
    drv = webdriver.Chrome(options=o, service=Service(duong_driver, service_args=["--disable-build-check"]))
    drv.set_page_load_timeout(25)
    drv.set_script_timeout(20)
    return drv


def _tim_cach_mo_chrome():
    for ham in (_tao_chrome_sandbox, _goc["_tracuunnt_tao_trinh_duyet"]):
        try:
            d = ham()
            d.quit()
            return ham
        except Exception:
            continue
    return None


cach_mo_chrome = _tim_cach_mo_chrome()
if cach_mo_chrome is None:
    print("BỎ QUA PHẦN B: máy này không mở được Chrome + chromedriver (phần A vẫn đủ xác nhận logic "
          "rơi về cách cũ).")
    print("\nALL DONE")
    sys.exit(0)

may_chu = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _MayChuGia)
threading.Thread(target=may_chu.serve_forever, daemon=True).start()
server._TRACUUNNT_URL = f"http://127.0.0.1:{may_chu.server_address[1]}/tcnnt/mstdn.jsp"
so_lan_mo_chrome = [0]


def _mo_chrome_dem():
    so_lan_mo_chrome[0] += 1
    return cach_mo_chrome()


server._tracuunnt_tao_trinh_duyet = _mo_chrome_dem
server._get_ddddocr = lambda: object()
KICH_BAN = {"sai_truoc": 0, "ngan_truoc": 0, "luon_sai": False, "so_lan_ocr": 0}


def _ocr_theo_kich_ban(png, _debug=None):
    KICH_BAN["so_lan_ocr"] += 1
    ma = _ocr_gia_doc(png)
    if KICH_BAN["luon_sai"]:
        return ma[:4] + ("a" if ma[4] != "a" else "b")
    if KICH_BAN["ngan_truoc"] > 0:
        KICH_BAN["ngan_truoc"] -= 1
        return ma[:4]
    if KICH_BAN["sai_truoc"] > 0:
        KICH_BAN["sai_truoc"] -= 1
        return ma[:4] + ("a" if ma[4] != "a" else "b")
    return ma


server._ocr_png = _ocr_theo_kich_ban
try:
    _dat_lai_trang_thai_trinh_duyet()

    # ===== B1 (QUAN TRỌNG): đọc ĐÚNG ảnh captcha trang ĐANG HIỂN THỊ (không tải ảnh lần 2 — máy
    # chủ chỉ phát đúng 1 captcha cho lần mở trang), bấm CHÍNH nút "Tra cứu" của trang (JS của
    # trang tự điền cm='cm' như người bấm thật) -> tra được ngay lần đầu. =====
    kq = server._tra_cuu_mst_qua_tracuunnt("0301234567", 8)
    assert kq == (True, "NNT đang hoạt động", False, None), f"got {kq!r}"
    assert THONG_KE["get_captcha"] == 2 and THONG_KE["post"] == 1 and THONG_KE["cm"] == ["cm"], (
        f"Phải đọc ảnh captcha trang đang hiển thị (1 ảnh khi mở trang + 1 ảnh mới trên trang kết quả, "
        f"KHÔNG tải thêm ảnh riêng) và gửi qua nút của trang (cm='cm') — got {THONG_KE}")
    print("PASS B1: Chrome ẩn đọc đúng captcha đang hiển thị, bấm nút 'Tra cứu' của trang, tra được "
          "ngay lần đầu.")

    # ===== B2: sai captcha -> trang trả về vẫn có form + captcha MỚI -> thử lại NGAY trên trang đó
    # (không tải lại trang), lần 2 đúng thì tra được. MST thứ 2 dùng luôn trang kết quả của MST
    # trước (có sẵn form) — không mở lại trang. =====
    KICH_BAN["sai_truoc"] = 1
    get_form_truoc = THONG_KE["get_form"]
    kq = server._tra_cuu_mst_qua_tracuunnt("0309876543", 8)
    assert kq == (True, "NNT đang hoạt động", False, None), f"got {kq!r}"
    assert THONG_KE["get_form"] == get_form_truoc, (
        f"Sai captcha thì phải thử lại ngay trên trang trả về (có form + captcha mới), không tải lại "
        f"trang — got get_form {get_form_truoc} -> {THONG_KE['get_form']}")
    print("PASS B2: sai captcha -> thử lại ngay trên trang trả về như người dùng thật, lần 2 tra được.")

    # ===== B3: trang báo lỗi qua hộp thoại alert() (không chuyển trang) -> đọc được nội dung hộp
    # thoại, đóng nó, mở lại trang lấy captcha mới rồi tra tiếp — không kẹt/treo vì alert. =====
    KICH_BAN["ngan_truoc"] = 1
    get_form_truoc = THONG_KE["get_form"]
    kq = server._tra_cuu_mst_qua_tracuunnt("0305555555", 8)
    assert kq == (True, "NNT đang hoạt động", False, None), f"got {kq!r}"
    assert THONG_KE["get_form"] == get_form_truoc + 1, (
        f"Sau hộp thoại lỗi phải mở lại trang để lấy captcha mới — got {THONG_KE['get_form'] - get_form_truoc}")
    print("PASS B3: lỗi báo qua hộp thoại alert() được xử lý, mở lại trang và tra được.")

    # ===== B4: sai captcha cả 6/6 lần -> thất bại, thông báo lỗi kèm ĐÚNG câu trang trả về và ghi
    # rõ là đã thử qua trình duyệt ẩn (để log người dùng gửi phân biệt được với cách cũ). =====
    KICH_BAN["luon_sai"] = True
    ok, tt, cb, ly_do = server._tra_cuu_mst_qua_tracuunnt("0304444444", 8)
    KICH_BAN["luon_sai"] = False
    assert ok is False and "Vui lòng nhập đúng mã xác nhận" in ly_do and "trình duyệt ẩn" in ly_do, (
        f"got {ly_do!r}")
    print("PASS B4: sai captcha 6/6 -> báo lỗi kèm câu trang trả về, ghi rõ đã thử qua trình duyệt ẩn.")

    # ===== B5: nhiều luồng tra song song (như _prefetch_trang_thai_mst, 3 luồng) dùng CHUNG 1
    # Chrome, tự xếp hàng — đều tra được, chỉ mở Chrome đúng 1 lần cho cả lượt. =====
    ket_qua_luong = {}

    def _tra_luong(mst):
        ket_qua_luong[mst] = server._tra_cuu_mst_qua_tracuunnt(mst, 8)

    ds_luong = [threading.Thread(target=_tra_luong, args=(m,)) for m in ("0311111111", "0312222222", "0313333333")]
    for t in ds_luong:
        t.start()
    for t in ds_luong:
        t.join(120)
    assert all(v[0] is True for v in ket_qua_luong.values()) and len(ket_qua_luong) == 3, f"got {ket_qua_luong!r}"
    assert so_lan_mo_chrome[0] == 1, f"Chỉ được mở Chrome 1 lần cho cả lượt — got {so_lan_mo_chrome[0]}"
    print("PASS B5: 3 luồng song song dùng chung 1 Chrome (tự xếp hàng), đều tra được.")

    # ===== B6: rảnh đủ lâu thì tự đóng Chrome (không để tiến trình Chrome chạy ngầm mãi); lượt sau
    # tự mở Chrome mới. =====
    assert server._tracuunnt_dong_trinh_duyet_neu_ranh(so_giay_ranh=3600) is False
    assert server._tracuunnt_dong_trinh_duyet_neu_ranh(so_giay_ranh=0) is True
    assert server._TRACUUNNT_TD["drv"] is None
    kq = server._tra_cuu_mst_qua_tracuunnt("0306666666", 8)
    assert kq[0] is True and so_lan_mo_chrome[0] == 2, f"got {kq!r}, mở Chrome {so_lan_mo_chrome[0]} lần"
    print("PASS B6: Chrome tự đóng khi rảnh, lượt sau tự mở lại được.")
finally:
    _khoi_phuc()
    may_chu.shutdown()

print("\nALL DONE")
