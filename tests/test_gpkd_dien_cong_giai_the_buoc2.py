import json, os, subprocess, sys, tempfile, threading, urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Nút "Điền dữ liệu GPKD" — khối "Chấm dứt hoạt động" (giải thể bước 2): chọn Loại hình chấm dứt hoạt động, điền Lý do giải thể.
# Cổng GIẢ LẬP theo ảnh người dùng gửi; không bấm Lưu; không đụng ô "Dừng thực hiện thủ tục". Chưa thử trên cổng thật.
LOG = []
MENU = '<div id=menu><a href="/ov">Thông tin về hồ sơ</a> <a href="/gt">Chấm dứt hoạt động</a> <a href="/uq">Thông tin Ủy quyền</a></div>'
PAGES = {"/ov": MENU + "<table><tr><td>Hình thức đăng ký:</td><td>Đăng ký thay đổi nội dung đăng ký doanh nghiệp/đơn vị trực thuộc</td></tr></table>" + "x" * 100,
         "/gt": MENU + """<div>Chấm dứt hoạt động</div><table>
<tr><td>Dừng thực hiện thủ tục đăng ký doanh nghiệp:</td><td><input type=checkbox id=dung></td></tr>
<tr><td>Loại hình chấm dứt hoạt động*:</td><td><select id=lh><option value="">--</option><option value="1">Doanh nghiệp nộp hồ sơ giải thể</option><option value="2">Doanh nghiệp bị thu hồi</option></select></td></tr>
<tr><td>Lý do giải thể*:</td><td><textarea id=ld></textarea></td></tr></table><input type=button id=luu value="Lưu"><input type=button value="Trở về">"""}


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        LOG.append(self.path)
        b = ("<meta charset=utf-8>" + PAGES.get(urllib.parse.urlparse(self.path).path, PAGES["/ov"])).encode("utf-8")
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(b)

    def log_message(self, *a):
        pass


srv = HTTPServer(("127.0.0.1", 0), H); cong = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
K = "Chấm dứt hoạt động"
DL = {"dkkd_dien": 1, "ban": "x", "truong": [], "nhac": [], "bo_qua": [], "nhom": [{"ten": K, "vao_khoi": K, "tao_moi": False, "truong": [
    {"ten": "Loại hình chấm dứt hoạt động", "nhan": "^loại hình chấm dứt", "gia_tri": "Doanh nghiệp nộp hồ sơ giải thể", "tien_to": False, "khoi": K},
    {"ten": "Lý do giải thể", "nhan": "^lý do giải thể", "gia_tri": "Không hoạt động nữa", "tien_to": False, "khoi": K}]}]}
js = urllib.parse.unquote(server.dkkd_bookmarklet_dien()[len("javascript:"):])
RUN = r"""
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: process.env.CHROME || undefined });
  const pg = await (await b.newContext()).newPage();
  pg.on('dialog', async d => { console.log('DIALOG ' + d.message()); await d.dismiss(); });
  await pg.goto('http://127.0.0.1:' + process.env.PORT + '/ov');
  await pg.evaluate(d => { Object.defineProperty(navigator, 'clipboard', { value: { readText: async () => d }, configurable: true }); }, process.env.DL);
  await pg.evaluate(process.env.JS);
  const w = (await (await pg.waitForSelector('#__dkkdKhung iframe', { timeout: 60000 })).contentFrame());
  await w.waitForSelector('#__dkkdHoan', { timeout: 60000 });
  console.log('@@' + JSON.stringify({ lh: await w.$eval('#lh', e => e.options[e.selectedIndex].text), ld: await w.inputValue('#ld'), dung: await w.isChecked('#dung') }));
  await b.close();
})();
"""
f = os.path.join(tempfile.mkdtemp(), "t.js"); open(f, "w", encoding="utf-8").write(RUN)
env = dict(os.environ, NODE_PATH="/opt/node22/lib/node_modules", DL=json.dumps(DL), JS=js, PORT=str(cong))
if os.path.exists("/opt/pw-browsers/chromium"):
    env["CHROME"] = "/opt/pw-browsers/chromium"
p = subprocess.run(["node", f], capture_output=True, text=True, env=env, timeout=200)
dong = [x for x in p.stdout.splitlines() if x.startswith("@@")]
assert dong, p.stdout + p.stderr
r = json.loads(dong[0][2:])
assert r == {"lh": "Doanh nghiệp nộp hồ sơ giải thể", "ld": "Không hoạt động nữa", "dung": False}, r
assert "/gt" in LOG and not any("luu" in x for x in LOG), LOG
print("PASS: nút bookmark vào khối 'Chấm dứt hoạt động', chọn loại hình giải thể + điền lý do; không bấm Lưu, không tick 'Dừng thực hiện'.")
print("\nALL DONE")
