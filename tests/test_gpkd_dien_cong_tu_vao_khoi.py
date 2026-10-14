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
MENU = ('<div id=menu><a href="/ov">Hình thức đăng ký</a> <a href="/dc">Địa chỉ</a> <a id=mdd href="/list">Người đại diện theo pháp luật</a> <a href="/uq">Thông tin về người đại diện theo ủy quyền</a></div>')
PAGES = {
    "/ov": MENU + "<table><tr><td>Hình thức đăng ký:</td><td>Đăng ký thay đổi</td></tr></table>",
    "/list": MENU + '<table><tr><td>ĐINH THỊ HUỆ</td><td><a href="/sua">Sửa đổi</a></td><td><a id=xoa href="/xoa">Xóa</a></td></tr></table><input type=button id=tm value="Tạo mới" onclick="location=\'/new\'">',
    "/new": MENU + """<form onsubmit="return false"><table>
<tr><td>Chức danh:</td><td><select id=cd><option></option><option>Giám đốc</option><option>Tổng giám đốc</option></select></td></tr>
<tr><td>Họ tên:</td><td><input id=ht></td></tr>
<tr><td>Giới tính:</td><td><input type=radio name=g id=gn value=1 checked><label for=gn>Nam</label><input type=radio name=g id=gnu value=2><label for=gnu>Nữ</label></td></tr>
<tr><td>Ngày sinh:</td><td><input id=ns></td></tr>
<tr><td>Số Giấy tờ pháp lý của cá nhân:</td><td><input id=cc></td></tr>
<tr><td>Quốc gia:</td><td><select id=qg><option>Việt Nam</option></select></td></tr>
<tr><td>Tỉnh/Thành phố:</td><td><select id=tp><option>Cần Thơ</option><option>Hồ Chí Minh</option></select></td></tr>
<tr><td>Số nhà/đường/phố/tổ/xóm/ấp/thôn:</td><td><input id=sn></td></tr>
<tr><td>Điện thoại:</td><td><input id=dt></td></tr>
<tr><td>E-mail:</td><td><input id=em></td></tr>
</table><div id=recaptcha><input type=checkbox id=rc> Tôi không phải là người máy</div><input type=button value="Đối chiếu với CSDLQG về dân cư" id=doichieu><input type=button value="Lưu" id=luu></form>""",
}
LOG = []


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        LOG.append(self.path)
        body = ("<meta charset=utf-8>" + PAGES.get(self.path, "404")).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
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
    {"ten": "Thư điện tử", "nhan": "^(e-?mail|thư điện tử)", "gia_tri": "a@b.vn", "tien_to": False, "khoi": "Người đại diện theo pháp luật"}]}
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
  const pop = ctx.waitForEvent('page');
  await pg.evaluate(process.env.JS);
  const w = await pop;
  await w.waitForSelector('#__dkkdHoan', { timeout: 60000 });
  const v = id => w.inputValue('#' + id);
  const r = { url: w.url(), cd: await w.$eval('#cd', e => e.options[e.selectedIndex].text), ht: await v('ht'), ns: await v('ns'), cc: await v('cc'), sn: await v('sn'), dt: await v('dt'), em: await v('em'),
    nu: await w.$eval('#gnu', e => e.checked), nam: await w.$eval('#gn', e => e.checked), rc: await w.$eval('#rc', e => e.checked), tp: await w.$eval('#tp', e => e.options[e.selectedIndex].text),
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
assert r["url"].endswith("/new"), r["url"]                                     # đã tự vào khối -> Tạo mới
assert r["cd"] == "Giám đốc" and r["ht"] == "ĐINH THỊ HUỆ" and r["ns"] == "12/07/1990" and r["cc"] == "036190003147" and r["sn"] == "Số nhà 91, Đường 13" and r["dt"] == "0900000000" and r["em"] == "a@b.vn", r
assert r["nu"] is True and r["nam"] is False                                     # chọn giới tính Nữ (radio)
assert r["rc"] is False and r["tp"] == "Cần Thơ"                                 # không đụng reCAPTCHA; ô Tỉnh/Thành không có trong dữ liệu -> để người dùng chọn
assert "Đã điền 8 ô" in r["panel"] and "tự bấm Lưu" in r["panel"], r["panel"]
assert r["opener"].endswith("/ov")                                               # cửa sổ gốc không bị chuyển trang
assert "/xoa" not in LOG and "/sua" not in LOG                                   # không bấm Xóa / Sửa đổi của người cũ
assert LOG[:3] == ["/ov", "/ov", "/list"] or "/list" in LOG and "/new" in LOG, LOG
assert r["hoan"] == {"ht": "", "nam": True}, r["hoan"]                           # Hoàn tác trả về như cũ
print("PASS 1: nút tự mở cửa sổ phụ, vào đúng khối 'Người đại diện theo pháp luật', bấm 'Tạo mới', điền 8 ô (kể cả radio giới tính), tô vàng; không bấm Xóa/Sửa/Lưu, không đụng reCAPTCHA; Hoàn tác đúng.")
print("\nALL DONE")
