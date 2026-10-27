import json, os, subprocess, sys, tempfile, threading, urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Công ty TNHH 1 thành viên: khối "Thông tin về chủ sở hữu" hiện sẵn chủ cũ + nút "Xóa", KHÔNG có nút "Tạo mới".
# Phần mềm chỉ bấm "Xóa" khi trang đang hiện đúng người cũ (cccd/họ tên), rồi điền vào form trống. Không bấm Lưu. Cổng GIẢ LẬP, chưa thử cổng thật.
MENU = '<div id=menu><a href="/ov">Hình thức đăng ký</a> <a href="/cs">Thông tin về chủ sở hữu</a></div>'
FORM = '<form onsubmit="return false"><table><tr><td>Họ tên:</td><td><input id=ht value="%s"></td></tr><tr><td>Số Giấy tờ pháp lý của cá nhân:</td><td><input id=cc value="%s"></td></tr></table><input type=button id=luu value="Lưu"></form>'
PAGES = {
    "/ov": MENU + "<p>Đăng ký thay đổi</p>",
    "/cs": MENU + FORM % ("NGUYỄN VĂN CŨ", "001099000111") + '<input type=button id=xoa value="Xóa" onclick="location=\'/trong\'">',
    "/cs2": MENU + FORM % ("TRẦN NGƯỜI KHÁC", "001099000222") + '<input type=button id=xoa value="Xóa" onclick="location=\'/trong\'">',
    "/trong": MENU + FORM % ("", ""),
}
LOG = []


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        LOG.append(self.path.split("?")[0])
        body = ("<meta charset=utf-8>" + PAGES.get(self.path.split("?")[0], "404")).encode("utf-8")
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(body)

    def log_message(self, *a):
        pass


srv = HTTPServer(("127.0.0.1", 0), H)
cong = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
T = [{"ten": "Họ tên", "nhan": "^họ(,? ?(chữ đệm )?(và )?)? ?tên", "gia_tri": "LÊ THỊ MỚI", "tien_to": False, "khoi": "Thông tin về chủ sở hữu"},
     {"ten": "Số giấy tờ", "nhan": "^(số (giấy tờ|định danh|cccd|căn cước)|số giấy)", "gia_tri": "036190003147", "tien_to": False, "khoi": "Thông tin về chủ sở hữu"}]


def dl(ten, cccd):
    g = {"ten": "Chủ sở hữu", "vao_khoi": "Thông tin về chủ sở hữu", "tao_moi": True, "xoa_roi_tao": {"ten": ten, "cccd": cccd}, "truong": T}
    return {"dkkd_dien": 1, "ban": "x", "nhom": [g], "truong": T, "bo_qua": []}


js = urllib.parse.unquote(server.dkkd_bookmarklet_dien()[len("javascript:"):])
RUN = r"""
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: process.env.CHROME || undefined });
  const pg = await (await b.newContext()).newPage();
  const ds = []; pg.on('dialog', async d => { ds.push(d.message()); await d.dismiss(); });
  await pg.goto('http://127.0.0.1:' + process.env.PORT + '/ov');
  await pg.evaluate(d => { Object.defineProperty(navigator, 'clipboard', { value: { readText: async () => d }, configurable: true }); }, process.env.DL);
  await pg.evaluate(process.env.JS);
  const r = {};
  const het = Date.now() + 30000; let w = null;
  while (Date.now() < het && !w) {            // cổng giả có thể chạy trong khung hoặc tab phụ
    await new Promise(ok => setTimeout(ok, 500));
    const hk = await pg.$('#__dkkdKhung iframe'); if (hk) { w = await hk.contentFrame(); continue; }
    for (const q of pg.context().pages()) if (q !== pg) w = q;
  }
  if (w) try {
    await w.waitForSelector('#__dkkdHoan', { timeout: 20000 });
    r.ht = await w.inputValue('#ht'); r.cc = await w.inputValue('#cc');
  } catch (e) { r.loi = 1; }
  if (!r.ht) await new Promise(ok => setTimeout(ok, 3000));
  r.ds = ds; r.url = w ? w.url().split('?')[0] : '';
  console.log('@@' + JSON.stringify(r));
  await b.close();
})();
"""
tmp = tempfile.mkdtemp(); f = os.path.join(tmp, "t.js"); open(f, "w", encoding="utf-8").write(RUN)


def chay(du_lieu, trang):
    PAGES["/ov"] = MENU + "<p>x</p>"
    LOG.clear()
    env = dict(os.environ, NODE_PATH="/opt/node22/lib/node_modules", DL=json.dumps(du_lieu), JS=js, PORT=str(cong))
    if os.path.exists("/opt/pw-browsers/chromium"):
        env["CHROME"] = "/opt/pw-browsers/chromium"
    # đổi trang "chủ sở hữu" mà menu dẫn tới
    PAGES["/cs"] = PAGES[trang]
    p = subprocess.run(["node", f], capture_output=True, text=True, env=env, timeout=180)
    d = [x for x in p.stdout.splitlines() if x.startswith("@@")]
    assert d, p.stdout + p.stderr
    return json.loads(d[0][2:])


GOC = PAGES["/cs"]
PAGES["/cs_cu"] = GOC
# 1) đúng người cũ -> bấm Xóa rồi điền form trống
r = chay(dl("NGUYỄN VĂN CŨ", "001099000111"), "/cs_cu")
assert "/trong" in LOG and r.get("ht") == "LÊ THỊ MỚI" and r.get("cc") == "036190003147", (r, LOG)
# 2) trang đang hiện người KHÁC -> không bấm Xóa, báo người dùng
PAGES["/cs_kh"] = PAGES["/cs2"]
r2 = chay(dl("NGUYỄN VĂN CŨ", "001099000111"), "/cs_kh")
assert "/trong" not in LOG and r2.get("loi") and any("không tự bấm" in m for m in r2["ds"]), (r2, LOG)
# 3) không bao giờ bấm Lưu
assert "/luu" not in LOG
print("PASS: công ty 1 thành viên: chỉ bấm 'Xóa' khi trang hiện đúng chủ cũ rồi điền form trống; người khác thì dừng và báo; không bấm Lưu.")
