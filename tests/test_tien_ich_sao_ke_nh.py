import json, os, subprocess, sys, tempfile, threading, urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Tiện ích Chrome — lấy sao kê ngân hàng trên trang internet banking GIẢ LẬP (chưa thử trên trang thật của Vietcombank/ACB/VietinBank/Techcombank):
# trang đăng nhập -> chỉ nhắc tự đăng nhập (không đụng ô mật khẩu); trang chủ -> tự bấm menu "Sao kê tài khoản";
# trang sao kê -> điền Từ ngày/Đến ngày, bấm Tra cứu, bấm Xuất Excel đúng 1 lần; phần mềm báo có file -> khung báo số giao dịch.
LOG = []
PAGES = {
    "/login": "<h3>Đăng nhập</h3><input id=u placeholder='Tên đăng nhập'><input id=pw type=password><button>Đăng nhập</button>",
    "/home": "<nav><a href='/tong'>Tổng quan</a> <a href='/sk'>Sao kê tài khoản</a> <a href='/ck'>Chuyển tiền</a></nav><p>Xin chào</p>",
    "/sk": """<h3>Sao kê tài khoản</h3><select id=tk><option>0071001234567</option></select>
<div class=row><label>Từ ngày</label><input id=a placeholder='dd/mm/yyyy' value='01/11/2026'></div>
<div class=row><label>Đến ngày</label><input id=b placeholder='dd/mm/yyyy' value='12/11/2026'></div>
<button id=tim onclick="fetch('/log/tim');setTimeout(()=>{document.getElementById('kq').innerHTML='<table><tr><td>02/09/2026</td><td>1.000</td></tr></table><button id=xuat onclick=&quot;fetch(\\'/log/xuat\\');localStorage.xuat=1&quot;>Xuất Excel</button>'},800)">Tra cứu</button>
<div id=kq></div>"""}


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        p = urllib.parse.urlparse(self.path).path
        LOG.append(p)
        b = ("<meta charset=utf-8><body>" + PAGES.get(p, "ok")).encode("utf-8")
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(b)

    def log_message(self, *a):
        pass


srv = HTTPServer(("127.0.0.1", 0), H); cong = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
STUB = r"""
(() => { const K = '__kho';
  const get = () => { try { return JSON.parse(localStorage.getItem(K) || '{}') } catch (e) { return {} } };
  window.chrome = { runtime: { lastError: null, sendMessage: (m, cb) => { setTimeout(() => cb(m.loai === 'nh-file-moi' && localStorage.xuat ? { co: true, so_gd: 3, ten: 'SaoKe.xlsx', so_tk: '0071001234567', canh_bao: [] } : { co: false }), 10) } },
    storage: { local: { get: (k, cb) => { const o = get(); setTimeout(() => cb({ [k]: o[k] }), 0) }, set: (o, cb) => { const x = get(); Object.assign(x, o); localStorage.setItem(K, JSON.stringify(x)); setTimeout(() => cb && cb(), 0) } } } };
})();
"""
RUN = r"""
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: process.env.CHROME || undefined });
  const ctx = await b.newContext(); await ctx.addInitScript(process.env.STUB);
  const pg = await ctx.newPage(); const U = 'http://127.0.0.1:' + process.env.PORT;
  const chay = async () => { await pg.addScriptTag({ content: process.env.JS }) };
  const tt = async () => (await pg.textContent('#__ketoanNhTt').catch(() => '')) || '';
  const cho = async (re, ms) => { const t0 = Date.now(); while (Date.now() - t0 < ms) { const t = await tt(); if (re.test(t)) return t; await pg.waitForTimeout(300) } return 'HẾT GIỜ: ' + await tt() };
  const kq = {};
  await pg.goto(U + '/login#ketoan-saoke=vcb_2026-09-01_2026-09-30&j=abc&p=8686'); await chay();
  kq.login = await cho(/tự đăng nhập/, 8000); kq.pw = await pg.inputValue('#pw');
  await pg.goto(U + '/home'); await chay();                     // người dùng đăng nhập xong -> trang chủ (mất dấu #) -> tiện ích nhớ việc, tự bấm menu
  await pg.waitForURL(/\/sk$/, { timeout: 15000 }).catch(() => {}); kq.url = pg.url();
  await chay();
  kq.xong = await cho(/Đã lấy 3 giao dịch/, 30000);
  kq.a = await pg.inputValue('#a'); kq.b = await pg.inputValue('#b');
  await pg.waitForTimeout(6000);                                 // không bấm Xuất lần 2
  console.log('@@' + JSON.stringify(kq)); await b.close();
})();
"""
f = os.path.join(tempfile.mkdtemp(), "t.js"); open(f, "w", encoding="utf-8").write(RUN)
js = open(os.path.join(_REPO_ROOT, "tien_ich_chrome", "xuat_don_tmdt", "ngan_hang.js"), encoding="utf-8").read()
env = dict(os.environ, NODE_PATH="/opt/node22/lib/node_modules", JS=js, STUB=STUB, PORT=str(cong))
if os.path.exists("/opt/pw-browsers/chromium"):
    env["CHROME"] = "/opt/pw-browsers/chromium"
p = subprocess.run(["node", f], capture_output=True, text=True, env=env, timeout=200)
dong = [x for x in p.stdout.splitlines() if x.startswith("@@")]
assert dong, p.stdout + p.stderr
r = json.loads(dong[0][2:])
print(r)
assert "tự đăng nhập" in r["login"] and r["pw"] == "", r
assert r["url"].endswith("/sk"), r
assert "Đã lấy 3 giao dịch" in r["xong"] and r["a"] == "01/09/2026" and r["b"] == "30/09/2026", r
assert LOG.count("/log/tim") == 1 and LOG.count("/log/xuat") == 1, LOG
print("PASS: nhắc tự đăng nhập (không đụng mật khẩu) -> tự mở Sao kê -> điền ngày, Tra cứu, Xuất Excel 1 lần -> báo đã lấy giao dịch.")
print("\nALL DONE")
