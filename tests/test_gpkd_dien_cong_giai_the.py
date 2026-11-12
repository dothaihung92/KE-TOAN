import json, os, subprocess, sys, tempfile, threading, urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Nút "Điền dữ liệu GPKD" — khối "Thông tin quyết định giải thể" của cổng (hồ sơ giải thể): Số quyết định, Ngày quyết định, Lý do giải thể (ô nhiều dòng).
# Cổng GIẢ LẬP theo ảnh người dùng gửi; không bấm Lưu; không đụng ô "Dừng thực hiện thủ tục". Chưa thử trên cổng thật.
LOG = []
MENU = '<div id=menu><a href="/ov">Thông tin về hồ sơ</a> <a href="/gt">Thông tin quyết định giải thể</a> <a href="/uq">Thông tin Ủy quyền</a></div>'
PAGES = {"/ov": MENU + "<table><tr><td>Hình thức đăng ký:</td><td>Đăng ký thay đổi nội dung đăng ký doanh nghiệp/đơn vị trực thuộc</td></tr></table>" + "x" * 100,
         "/gt": MENU + """<div>Thông tin thông báo giải thể</div><table>
<tr><td>Số quyết định*:</td><td><input id=sqd></td></tr><tr><td>Ngày quyết định*:</td><td><input id=nqd></td></tr>
<tr><td>Lý do giải thể:</td><td><textarea id=ld></textarea></td></tr></table><input type=button id=luu value="Lưu"><input type=button value="Trở về">"""}


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        LOG.append(self.path)
        b = ("<meta charset=utf-8>" + PAGES.get(urllib.parse.urlparse(self.path).path, PAGES["/ov"])).encode("utf-8")
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(b)

    def log_message(self, *a):
        pass


srv = HTTPServer(("127.0.0.1", 0), H); cong = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
K = "Thông tin quyết định giải thể"
DL = {"dkkd_dien": 1, "ban": "x", "truong": [], "nhac": [], "bo_qua": [], "nhom": [{"ten": K, "vao_khoi": K, "tao_moi": False, "truong": [
    {"ten": "Số quyết định", "nhan": "^số quyết định", "gia_tri": "01/QĐ", "tien_to": False, "khoi": K},
    {"ten": "Ngày quyết định", "nhan": "^ngày quyết định", "gia_tri": "24/08/2026", "tien_to": False, "khoi": K},
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
  console.log('@@' + JSON.stringify({ sqd: await w.inputValue('#sqd'), nqd: await w.inputValue('#nqd'), ld: await w.inputValue('#ld') }));
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
assert r == {"sqd": "01/QĐ", "nqd": "24/08/2026", "ld": "Không hoạt động nữa"}, r
assert "/gt" in LOG and not any("luu" in x for x in LOG), LOG
print("PASS: nút bookmark vào khối 'Thông tin quyết định giải thể' và điền Số quyết định, Ngày quyết định, Lý do giải thể; không bấm Lưu.")
print("\nALL DONE")
