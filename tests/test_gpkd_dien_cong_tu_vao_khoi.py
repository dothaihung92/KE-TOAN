import json
import os
import subprocess
import sys
import tempfile
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Nút "Điền dữ liệu GPKD" TỰ VÀO ĐÚNG KHỐI: mở cửa sổ phụ -> bấm mục menu "Người đại diện theo pháp luật" -> bấm "Tạo mới" -> điền các ô
# (Chức danh, Họ tên, Giới tính, Ngày sinh, Số giấy tờ, Số nhà, Điện thoại, Email). KHÔNG bấm Lưu/Xóa, không đụng reCAPTCHA/"Đối chiếu".
# Chạy trên cổng GIẢ LẬP (máy chủ cục bộ) có cấu trúc giống cổng thật qua ảnh người dùng gửi; chưa thử cổng thật.
MENU = ('<div id=menu><a href="/ov">Hình thức đăng ký</a> <a href="/dc">Địa chỉ</a> <a id=mdd href="/list">Người đại diện theo pháp luật</a> <a href="/uq">Thông tin về người đại diện theo ủy quyền</a> <a id=mthue href="/thue">Thông tin về thuế</a></div>')
PAGES = {
    "/ov": MENU + "<table><tr><td>Hình thức đăng ký:</td><td>Đăng ký thay đổi</td></tr></table>",
    "/list": MENU + '<table><tr><td>ĐINH THỊ HUỆ</td><td><a href="/sua">Sửa đổi</a></td><td><a id=xoa href="/xoa">Xóa</a></td></tr></table><input type=button id=tm value="Tạo mới" onclick="location=\'/new\'">'
}
XA = {"Hồ Chí Minh": ["", "Phường An Khánh", "Phường Bình Trưng"], "Cần Thơ": ["", "Phường Ninh Kiều"]}


MODE = {"luu": "/luu"}


def trang_new(q, khoa=False):
    """Trang 'Tạo mới' người đại diện — Tỉnh/Thành đổi là GỬI LẠI TRANG (postback toàn trang, giữ giá trị đã nhập) rồi nạp danh sách Xã/Phường tương ứng."""
    g = lambda k, d="": q.get(k, [d])[0]
    tp = g("tp", "Cần Thơ")
    ops = lambda ds, cur: "".join(f"<option{' selected' if x == cur else ''}>{x}</option>" for x in ds)
    nu = "checked" if g("g") == "2" else ""
    nam = "" if nu else "checked"
    kh = " disabled" if khoa else ""
    return MENU + f"""<form id=f method=get action="/new"><table>
<tr><td>Chức danh:</td><td><select id=cd name=cd{kh}>{ops(["", "Giám đốc", "Tổng giám đốc"], g("cd"))}</select></td></tr>
<tr><td>Họ tên:</td><td><input id=ht name=ht value="{g('ht')}"{kh}></td></tr>
<tr><td>Giới tính:</td><td><input type=radio name=g id=gn value=1 {nam}{kh}><label for=gn>Nam</label><input type=radio name=g id=gnu value=2 {nu}{kh}><label for=gnu>Nữ</label></td></tr>
<tr><td>Ngày sinh:</td><td><input id=ns name=ns value="{g('ns')}"{kh}></td></tr>
<tr><td>Số Giấy tờ pháp lý của cá nhân:</td><td><input id=cc name=cc value="{g('cc')}"{kh}></td></tr>
<tr><td>Quốc gia:</td><td><select id=qg name=qg{kh}><option>Việt Nam</option></select></td></tr>
<tr><td>Tỉnh/Thành phố:</td><td><select id=tp name=tp{kh} onchange="this.form.submit()">{ops(["Cần Thơ", "Hồ Chí Minh"], tp)}</select></td></tr>
<tr><td>Xã/Phường/Đặc khu:</td><td><select id=xa name=xa{kh}>{ops(XA[tp], g("xa"))}</select></td></tr>
<tr><td>Số nhà/đường/phố/tổ/xóm/ấp/thôn:</td><td><input id=sn name=sn value="{g('sn')}"></td></tr>
<tr><td>Điện thoại:</td><td><input id=dt name=dt value="{g('dt')}"></td></tr>
<tr><td>E-mail:</td><td><input id=em name=em value="{g('em')}"></td></tr>
</table><div id=recaptcha><input type=checkbox id=rc> Tôi không phải là người máy</div><input type=button value="Đối chiếu với CSDLQG về dân cư" id=doichieu><input type=button value="Lưu" id=luu onclick="location='{MODE['luu']}'"></form>"""


PAGES["/thue"] = MENU + """<div class=sec><div class=tt>Giám đốc/Tổng giám đốc</div><table><tr><th>Họ và tên</th><th>Chức vụ</th></tr><tr><td>VÕ THỊ RI</td><td>Giám đốc/Tổng Giám đốc</td></tr></table><input type=button id=tm_gd value="Tạo mới" onclick="location='/gd_new'"></div>
<div class=sec><div class=tt>Kế toán trưởng/ Phụ trách kế toán</div><table><tr><th>Họ và tên</th></tr><tr><td>ĐINH THỊ HUỆ</td></tr></table><input type=button id=tm_kt value="Tạo mới" onclick="location='/kt_new'"></div>
<div class=sec><div class=tt>Địa chỉ nhận thông báo thuế</div><input type=radio name=dc id=r1><label for=r1>Giống địa chỉ trụ sở chính</label><input type=radio name=dc id=r2 checked><label for=r2>Giống địa chỉ chủ sở hữu</label><input type=radio name=dc id=r3><label for=r3>Địa chỉ khác</label>
<table><tr><td>Ngày bắt đầu hoạt động:</td><td><input id=nbd></td></tr><tr><td>Tổng số lao động:</td><td><input id=ld></td></tr></table><input type=button id=luu value="Lưu"></div>"""
for _n in ("gd", "kt"):
    PAGES["/%s_new" % _n] = MENU + '<form onsubmit="return false"><table><tr><td>Họ và tên:</td><td><input id=ht></td></tr><tr><td>Điện thoại:</td><td><input id=dt></td></tr></table><input type=button id=luu value="Lưu" onclick="location=\'/luu\'"></form>'
PAGES["/luu"] = MENU + "<table><tr><td>ĐINH THỊ HUỆ</td><td><a href=\"/sua\">Sửa đổi</a></td></tr></table>"      # sau khi Lưu, cổng về trang danh sách (không còn ô nhập)
PAGES["/dc"] = MENU + """<form onsubmit="return false"><table><tr><td>Số nhà/đường/phố/tổ/xóm/ấp/thôn:</td><td><input id=sn></td></tr><tr><td>Điện thoại:</td><td><input id=dt></td></tr></table><input type=button value="Lưu" id=luu></form>"""
LOG = []


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        LOG.append(self.path)
        import urllib.parse as _u
        pr = _u.urlparse(self.path)
        html = trang_new(_u.parse_qs(pr.query)) if pr.path == "/new" else trang_new(_u.parse_qs(pr.query), khoa=True) if pr.path == "/luu2" else ("<div style=\"background:#fde;color:#a00\">Nhập mã Captcha sai.</div>" + trang_new(_u.parse_qs(pr.query))) if pr.path == "/luu3" else PAGES.get(pr.path, "404")
        body = ("<meta charset=utf-8>" + html).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        if MODE.get("xfo"):
            self.send_header("X-Frame-Options", "DENY")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


srv = HTTPServer(("127.0.0.1", 0), H)
cong = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()

DL = {"dkkd_dien": 1, "ban": "x", "vao_khoi": "Người đại diện theo pháp luật", "tao_moi": True, "truong": [
    {"ten": "Chức danh", "nhan": "^chức (danh|vụ)", "gia_tri": "Giám đốc", "tien_to": False, "khoi": "Người đại diện theo pháp luật"},
    {"ten": "Họ tên", "nhan": "^họ(,? ?(chữ đệm )?(và )?)? ?tên", "gia_tri": "ĐINH THỊ HUỆ", "tien_to": False, "khoi": "Người đại diện theo pháp luật"},
    {"ten": "Giới tính", "nhan": "^giới tính", "gia_tri": "Nữ", "tien_to": False, "khoi": "Người đại diện theo pháp luật"},
    {"ten": "Ngày sinh", "nhan": "ngày.*sinh", "gia_tri": "12/07/1990", "tien_to": False, "khoi": "Người đại diện theo pháp luật"},
    {"ten": "Số giấy tờ", "nhan": "^(số (giấy tờ|định danh|cccd|căn cước)|số giấy)", "gia_tri": "036190003147", "tien_to": False, "khoi": "Người đại diện theo pháp luật"},
    {"ten": "Số nhà", "nhan": "^số nhà", "gia_tri": "Số nhà 91, Đường 13", "tien_to": False, "khoi": "Người đại diện theo pháp luật"},
    {"ten": "Điện thoại", "nhan": "^điện thoại", "gia_tri": "0900000000", "tien_to": False, "khoi": "Người đại diện theo pháp luật"},
    {"ten": "Thư điện tử", "nhan": "^(e-?mail|thư điện tử)", "gia_tri": "a@b.vn", "tien_to": False, "khoi": "Người đại diện theo pháp luật"},
    {"ten": "Tỉnh/Thành phố", "nhan": "^tỉnh\\/thành", "gia_tri": "Thành phố Hồ Chí Minh", "tien_to": False, "khoi": "Người đại diện theo pháp luật", "chuoi": True},
    {"ten": "Xã/Phường", "nhan": "^xã\\/phường", "gia_tri": "Phường Bình Trưng", "tien_to": False, "khoi": "Người đại diện theo pháp luật", "chuoi": True}]}
js = urllib.parse.unquote(server.dkkd_bookmarklet_dien()[len("javascript:"):])
RUN = r"""
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: process.env.CHROME || undefined });
  const ctx = await b.newContext();
  const pg = await ctx.newPage();
  pg.on('dialog', async d => { console.log('DIALOG ' + d.message()); await d.dismiss(); });
  await pg.goto('http://127.0.0.1:' + process.env.PORT + '/ov');
  await pg.evaluate(d => { Object.defineProperty(navigator, 'clipboard', { value: { readText: async () => d }, configurable: true }); }, process.env.DL);
  await pg.evaluate(process.env.JS);
  const hk = await pg.waitForSelector('#__dkkdKhung iframe', { timeout: 60000 });
  const w = await hk.contentFrame();
  await w.waitForSelector('#__dkkdHoan', { timeout: 60000 });
  const v = id => w.inputValue('#' + id);
  const r = { url: w.url(), cd: await w.$eval('#cd', e => e.options[e.selectedIndex].text), ht: await v('ht'), ns: await v('ns'), cc: await v('cc'), sn: await v('sn'), dt: await v('dt'), em: await v('em'),
    nu: await w.$eval('#gnu', e => e.checked), nam: await w.$eval('#gn', e => e.checked), rc: await w.$eval('#rc', e => e.checked), tp: await w.$eval('#tp', e => e.options[e.selectedIndex].text), xa: await w.$eval('#xa', e => e.options[e.selectedIndex].text), vangXa: await w.$eval('#xa', e => e.style.background),
    panel: await w.innerText('#__dkkdHoan >> xpath=../..'), opener: pg.url() };
  await w.click('#__dkkdHoan');
  r.hoan = { ht: await v('ht'), nam: await w.$eval('#gn', e => e.checked) };
  console.log('@@' + JSON.stringify(r));
  await b.close();
})();
"""
tmp = tempfile.mkdtemp()
f = os.path.join(tmp, "t.js")
open(f, "w", encoding="utf-8").write(RUN)
env = dict(os.environ, NODE_PATH="/opt/node22/lib/node_modules", DL=json.dumps(DL), JS=js, PORT=str(cong))
if os.path.exists("/opt/pw-browsers/chromium"):
    env["CHROME"] = "/opt/pw-browsers/chromium"
p = subprocess.run(["node", f], capture_output=True, text=True, env=env, timeout=180)
dong = [x for x in p.stdout.splitlines() if x.startswith("@@")]
assert dong, p.stdout + p.stderr
r = json.loads(dong[0][2:])
assert r["url"].split("?")[0].endswith("/new"), r["url"]                                     # đã tự vào khối -> Tạo mới
assert r["cd"] == "Giám đốc" and r["ht"] == "ĐINH THỊ HUỆ" and r["ns"] == "12/07/1990" and r["cc"] == "036190003147" and r["sn"] == "Số nhà 91, Đường 13" and r["dt"] == "0900000000" and r["em"] == "a@b.vn", r
assert r["nu"] is True and r["nam"] is False                                     # chọn giới tính Nữ (radio)
assert r["rc"] is False                                                           # không đụng reCAPTCHA
assert r["tp"] == "Hồ Chí Minh" and r["xa"] == "Phường Bình Trưng", (r["tp"], r["xa"])      # chọn Tỉnh/Thành (gửi lại trang) rồi chờ nạp Xã/Phường và chọn đúng; các ô đã điền trước đó vẫn còn
assert r["vangXa"], r["vangXa"]
assert "Đã điền 10 ô" in r["panel"] and "tự bấm Lưu" in r["panel"], r["panel"]
assert r["opener"].endswith("/ov")                                               # cửa sổ gốc không bị chuyển trang
assert "/xoa" not in LOG and "/sua" not in LOG                                   # không bấm Xóa / Sửa đổi của người cũ
assert LOG[:3] == ["/ov", "/ov", "/list"] or "/list" in LOG and "/new" in LOG, LOG
assert r["hoan"] == {"ht": "", "nam": True}, r["hoan"]                           # Hoàn tác trả về như cũ
print("PASS 1: nút tự mở cửa sổ phụ, vào đúng khối 'Người đại diện theo pháp luật', bấm 'Tạo mới', điền 10 ô (kể cả radio giới tính, Tỉnh/Thành rồi Xã/Phường sau khi trang gửi lại), tô vàng; không bấm Xóa/Sửa/Lưu, không đụng reCAPTCHA; Hoàn tác đúng.")
# NHIỀU KHỐI: tick cả Địa chỉ và Người đại diện -> bảng điều khiển ở cửa sổ gốc, khối 1 tự chạy; bấm khối 2 thì dùng LẠI cùng cửa sổ phụ
G1 = {"ten": "Địa chỉ", "vao_khoi": "Địa chỉ", "tao_moi": False, "truong": [
    {"ten": "Số nhà", "nhan": "^số nhà", "gia_tri": "30 Lê Lợi", "tien_to": False, "khoi": "Địa chỉ"},
    {"ten": "Điện thoại", "nhan": "^điện thoại", "gia_tri": "0911111111", "tien_to": False, "khoi": "Địa chỉ"}]}
G2 = dict(DL, ten="Người đại diện theo pháp luật")
DL_NHIEU = {"dkkd_dien": 1, "ban": "x", "nhom": [G1, G2], "truong": G1["truong"] + G2["truong"], "bo_qua": []}
RUN_N = RUN.split("  await pg.evaluate(process.env.JS);")[0] + r"""
  await pg.evaluate(process.env.JS);
  const hk = await pg.waitForSelector('#__dkkdKhung iframe', { timeout: 60000 });
  const w = await hk.contentFrame();
  await w.waitForSelector('#__dkkdHoan', { timeout: 60000 });
  const r = { url1: w.url(), sn1: await w.inputValue('#sn'), dt1: await w.inputValue('#dt'), nut: await pg.$$eval('#__dkkdDongBang', e => e.length), bang: (await pg.innerText('body')).includes('2. Người đại diện theo pháp luật') };
  await w.click('#__dkkdDong');
  const botn = await pg.$$('button');
  let nut2 = null;
  for (const b2 of botn) { if ((await b2.innerText()).startsWith('2.')) nut2 = b2; }
  await nut2.click();
  await w.waitForURL(/\/new$/, { timeout: 60000 });
  await w.waitForSelector('#__dkkdHoan', { timeout: 60000 });
  r.url2 = w.url().split("?")[0]; r.ht2 = await w.inputValue('#ht'); r.cc2 = await w.inputValue('#cc'); r.soTrang = ctx.pages().length;
  console.log('@@' + JSON.stringify(r));
  await b.close();
})();
"""
f2 = os.path.join(tmp, "t3.js")
open(f2, "w", encoding="utf-8").write(RUN_N)
LOG.clear()
env3 = dict(env, DL=json.dumps(DL_NHIEU))
p3 = subprocess.run(["node", f2], capture_output=True, text=True, env=env3, timeout=180)
d3 = [x for x in p3.stdout.splitlines() if x.startswith("@@")]
assert d3, p3.stdout + p3.stderr
r3 = json.loads(d3[0][2:])
assert r3["url1"].endswith("/dc") and r3["sn1"] == "30 Lê Lợi" and r3["dt1"] == "0911111111", r3      # khối 1 (Địa chỉ) tự vào và điền
assert r3["nut"] == 1 and r3["bang"], r3                                                                # bảng nhiều khối ở cửa sổ gốc
assert r3["url2"].endswith("/new") and r3["ht2"] == "ĐINH THỊ HUỆ" and r3["cc2"] == "036190003147", r3  # khối 2 (Người đại diện): menu -> Tạo mới -> điền
assert r3["soTrang"] == 1, r3                                                                           # xử lý NGAY TRONG tab đang mở (khung), không mở thêm tab/cửa sổ
assert "/xoa" not in LOG and "/sua" not in LOG, LOG
print("PASS 2: nhiều khối (Địa chỉ + Người đại diện): khối 1 tự chạy, bảng ở cửa sổ gốc để bấm khối kế tiếp, dùng lại cùng 1 cửa sổ phụ; không bấm Xóa/Sửa.")
# TỰ SANG KHỐI KẾ TIẾP sau khi người dùng bấm Lưu: Người đại diện (khối 1) -> người dùng bấm Lưu -> cổng về danh sách -> phần mềm tự vào khối Địa chỉ và điền
DL_TUDONG = {"dkkd_dien": 1, "ban": "x", "nhom": [G2, G1], "truong": G2["truong"] + G1["truong"], "bo_qua": []}
RUN_T = RUN.split("  await pg.evaluate(process.env.JS);")[0] + r"""
  await pg.evaluate(process.env.JS);
  const hk = await pg.waitForSelector('#__dkkdKhung iframe', { timeout: 60000 });
  const w = await hk.contentFrame();
  await w.waitForSelector('#__dkkdHoan', { timeout: 60000 });
  const r = { url1: w.url().split('?')[0], ht1: await w.inputValue('#ht') };
  await new Promise(ok => setTimeout(ok, 3500));
  r.chuaLuu = w.url().split('?')[0];                      // chưa bấm Lưu thì KHÔNG tự sang khối khác
  await w.click('#luu');                                  // người dùng xác nhận và bấm Lưu
  await w.waitForURL(/\/dc$/, { timeout: 60000 });
  await w.waitForSelector('#__dkkdHoan', { timeout: 60000 });
  r.url2 = w.url().split('?')[0]; r.sn2 = await w.inputValue('#sn'); r.dt2 = await w.inputValue('#dt');
  r.tt = await pg.innerText('body');
  console.log('@@' + JSON.stringify(r));
  await b.close();
})();
"""
f4 = os.path.join(tmp, "t4.js")
open(f4, "w", encoding="utf-8").write(RUN_T)
LOG.clear()
p4 = subprocess.run(["node", f4], capture_output=True, text=True, env=dict(env, DL=json.dumps(DL_TUDONG)), timeout=240)
d4 = [x for x in p4.stdout.splitlines() if x.startswith("@@")]
assert d4, p4.stdout + p4.stderr
r4 = json.loads(d4[0][2:])
assert r4["url1"].endswith("/new") and r4["ht1"] == "ĐINH THỊ HUỆ" and r4["chuaLuu"].endswith("/new"), r4      # khối 1 điền xong, chưa Lưu thì đứng yên
assert r4["url2"].endswith("/dc") and r4["sn2"] == "30 Lê Lợi" and r4["dt2"] == "0911111111", r4              # sau khi Lưu: tự vào khối Địa chỉ và điền
assert "đã Lưu ✓" in r4["tt"], r4["tt"]
assert "/xoa" not in LOG and "/sua" not in LOG, LOG
print("PASS 3: nhiều khối: người dùng bấm Lưu khối 1 (về trang danh sách) thì phần mềm TỰ vào khối kế tiếp và điền; chưa Lưu thì đứng yên.")
# Cổng THẬT sau khi Lưu vẫn ở lại cùng trang nhập (ô bị khóa, "Sửa đổi dữ liệu" bỏ tick) -> vẫn nhận ra đã Lưu và tự sang khối kế tiếp
MODE["luu"] = "/luu2"
LOG.clear()
p5 = subprocess.run(["node", f4], capture_output=True, text=True, env=dict(env, DL=json.dumps(DL_TUDONG)), timeout=240)
d5 = [x for x in p5.stdout.splitlines() if x.startswith("@@")]
assert d5, p5.stdout + p5.stderr
r5 = json.loads(d5[0][2:])
assert r5["chuaLuu"].endswith("/new") and r5["url2"].endswith("/dc") and r5["sn2"] == "30 Lê Lợi", r5
print("PASS 4: sau khi Lưu cổng ở lại trang nhập với các ô bị khóa -> phần mềm vẫn nhận ra đã Lưu và tự sang khối kế tiếp.")
# Bấm Lưu nhưng cổng báo lỗi (vẫn là form nhập đang mở) -> KHÔNG tự sang khối khác
MODE["luu"] = "/luu3"
RUN_L = RUN_T.split("  await w.click('#luu');")[0] + r"""
  await w.click('#luu');
  await new Promise(ok => setTimeout(ok, 4500));
  r.sau = w.url().split('?')[0];
  r.panel = await w.innerText('#__dkkdTT');
  r.htRong = await w.inputValue('#ht');
  await w.click('#__dkkdLai');
  await w.waitForFunction(() => document.getElementById('ht').value === 'ĐINH THỊ HUỆ', null, { timeout: 30000 });
  r.htLai = await w.inputValue('#ht');
  console.log('@@' + JSON.stringify(r));
  await b.close();
})();
"""
f6 = os.path.join(tmp, "t6.js")
open(f6, "w", encoding="utf-8").write(RUN_L)
p6 = subprocess.run(["node", f6], capture_output=True, text=True, env=dict(env, DL=json.dumps(DL_TUDONG)), timeout=240)
d6 = [x for x in p6.stdout.splitlines() if x.startswith("@@")]
assert d6, p6.stdout + p6.stderr
r6 = json.loads(d6[0][2:])
assert r6["sau"].endswith("/luu3"), r6                                 # còn ô nhập mở (lỗi/chưa lưu được) -> đứng yên, không sang khối Địa chỉ
assert "Cổng báo" in r6["panel"] and "Nhập mã Captcha sai" in r6["panel"] and "Điền lại khối này" in r6["panel"], r6["panel"]      # báo lại lỗi của cổng, không biến mất sau khi trang tải lại
assert r6["htRong"] == "" and r6["htLai"] == "ĐINH THỊ HUỆ", r6        # nút "Điền lại khối này" điền lại ngay trên trang đang mở
print("PASS 5: bấm Lưu nhưng cổng vẫn hiện form nhập (lỗi) -> phần mềm không tự sang khối khác.")
# KHỐI THUẾ: bấm đúng nút "Tạo mới" của MỤC (Giám đốc / Kế toán trưởng), chọn radio địa chỉ theo nhãn
TR_GD = [{"ten": "Họ tên", "nhan": "^họ.*tên", "gia_tri": "ĐINH THỊ HUỆ", "tien_to": False, "khoi": "Thông tin về thuế"}, {"ten": "Điện thoại", "nhan": "^điện thoại", "gia_tri": "0900000001", "tien_to": False, "khoi": "Thông tin về thuế"}]
TR_KH = [{"ten": "Địa chỉ nhận thông báo thuế = địa chỉ trụ sở chính", "radio": "Giống địa chỉ trụ sở chính", "gia_tri": "x", "khoi": "Thông tin về thuế", "chuoi": True},
         {"ten": "Ngày bắt đầu hoạt động", "nhan": "^ngày bắt đầu", "gia_tri": "20/08/2019", "tien_to": False, "khoi": "Thông tin về thuế"},
         {"ten": "Tổng số lao động", "nhan": "^(tổng )?số lao động", "gia_tri": "12", "tien_to": False, "khoi": "Thông tin về thuế"}]
GT_GD = {"ten": "Thuế — Giám đốc", "vao_khoi": "Thông tin về thuế", "tao_moi": True, "muc_tao_moi": "Giám đốc/Tổng giám đốc", "truong": TR_GD}
GT_KT = {"ten": "Thuế — Kế toán", "vao_khoi": "Thông tin về thuế", "tao_moi": True, "muc_tao_moi": "Kế toán trưởng/Phụ trách kế toán", "truong": [dict(t, gia_tri="NGUYỄN THỊ KẾ") if t["ten"] == "Họ tên" else t for t in TR_GD]}
GT_KH = {"ten": "Thuế — địa chỉ & khác", "vao_khoi": "Thông tin về thuế", "tao_moi": False, "truong": TR_KH}
RUN_TX = RUN.split("  await pg.evaluate(process.env.JS);")[0] + r"""
  await pg.evaluate(process.env.JS);
  const hk = await pg.waitForSelector('#__dkkdKhung iframe', { timeout: 60000 });
  const w = await hk.contentFrame();
  await w.waitForSelector('#__dkkdHoan', { timeout: 60000 });
  const r = { gdUrl: w.url().split('?')[0], gdHt: await w.inputValue('#ht') };
  await w.click('#luu');
  await w.waitForURL(/\/kt_new$/, { timeout: 60000 });
  await w.waitForSelector('#__dkkdHoan', { timeout: 60000 });
  r.ktHt = await w.inputValue('#ht');
  await w.click('#luu');
  await w.waitForURL(/\/thue$/, { timeout: 60000 });
  await w.waitForSelector('#__dkkdHoan', { timeout: 60000 });
  r.r1 = await w.$eval('#r1', e => e.checked); r.r2 = await w.$eval('#r2', e => e.checked);
  r.nbd = await w.inputValue('#nbd'); r.ld = await w.inputValue('#ld');
  r.tabs = ctx.pages().length;
  console.log('@@' + JSON.stringify(r));
  await b.close();
})();
"""
f7 = os.path.join(tmp, "t7.js")
open(f7, "w", encoding="utf-8").write(RUN_TX)
LOG.clear()
DL_TX = {"dkkd_dien": 1, "ban": "x", "nhom": [GT_GD, GT_KT, GT_KH], "truong": TR_GD + TR_KH, "bo_qua": []}
p7 = subprocess.run(["node", f7], capture_output=True, text=True, env=dict(env, DL=json.dumps(DL_TX)), timeout=300)
d7 = [x for x in p7.stdout.splitlines() if x.startswith("@@")]
assert d7, p7.stdout + p7.stderr
r7 = json.loads(d7[0][2:])
assert r7["gdUrl"].endswith("/gd_new") and r7["gdHt"] == "ĐINH THỊ HUỆ", r7                        # bấm "Tạo mới" của mục Giám đốc (không phải của Kế toán trưởng)
assert r7["ktHt"] == "NGUYỄN THỊ KẾ", r7                                                              # sau Lưu: tự sang mục Kế toán trưởng, bấm "Tạo mới" của mục đó
assert r7["r1"] is True and r7["r2"] is False and r7["nbd"] == "20/08/2019" and r7["ld"] == "12", r7  # chọn radio 'Giống địa chỉ trụ sở chính' + điền ngày bắt đầu, số lao động
assert r7["tabs"] == 1, r7                                                                            # xử lý ngay trong tab đang mở, không mở tab mới
assert "/xoa" not in LOG and "/sua" not in LOG, LOG
print("PASS 6: khối Thông tin về thuế: bấm đúng 'Tạo mới' của mục Giám đốc rồi Kế toán trưởng (tự sang sau khi Lưu), chọn radio địa chỉ theo nhãn, điền ngày bắt đầu/số lao động.")
# Cổng KHÔNG cho hiện trong khung (X-Frame-Options: DENY): tự rơi về mở tab mới và vẫn điền được
MODE["xfo"] = True
MODE["luu"] = "/luu"
RUN_F = RUN.split("  await pg.evaluate(process.env.JS);")[0] + r"""
  const pop = ctx.waitForEvent('page', { timeout: 90000 });
  await pg.evaluate(process.env.JS);
  const w = await pop;
  await w.waitForSelector('#__dkkdHoan', { timeout: 90000 });
  const r = { url: w.url().split('?')[0], ht: await w.inputValue('#ht'), khung: await pg.$$eval('#__dkkdKhung', e => e.length), tabs: ctx.pages().length };
  console.log('@@' + JSON.stringify(r));
  await b.close();
})();
"""
f8 = os.path.join(tmp, "t8.js")
open(f8, "w", encoding="utf-8").write(RUN_F)
p8 = subprocess.run(["node", f8], capture_output=True, text=True, env=dict(env, DL=json.dumps(DL)), timeout=300)
d8 = [x for x in p8.stdout.splitlines() if x.startswith("@@")]
assert d8, p8.stdout + p8.stderr
r8 = json.loads(d8[0][2:])
assert r8["url"].endswith("/new") and r8["ht"] == "ĐINH THỊ HUỆ" and r8["khung"] == 0 and r8["tabs"] == 2, r8
print("PASS 7: cổng chặn khung (X-Frame-Options) -> tự rơi về mở tab mới và vẫn điền đúng.")
print("\nALL DONE")
