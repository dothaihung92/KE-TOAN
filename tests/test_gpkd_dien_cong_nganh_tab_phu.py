import json, os, subprocess, sys, tempfile, threading, urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# BIẾN THỂ TAB PHỤ: cổng cấm hiện trong khung (X-Frame-Options) -> phần mềm mở tab phụ; Lưu ở lại CÙNG trang và khoá nút Lưu như cổng thật.
# Lỗi đã gặp: khối Ngành nghề không nhớ tab phụ nên báo ngay "chưa thấy bạn Lưu xong" và không tự sang khối kế tiếp.
# Nút "Điền dữ liệu GPKD" — KHỐI NGÀNH NGHỀ (trước đây "chưa hỗ trợ điền tự động", người dùng phải tự gõ từng mã ngành):
# Xóa ngành bỏ -> gõ mã + bấm "Thêm ngành nghề bằng mã số" (cổng gửi lại trang, thêm dòng) -> điền ô chi tiết dưới tên ngành -> chọn ngành chính + "Cập nhật chính".
# Không bấm Lưu. Cổng GIẢ LẬP theo ảnh người dùng gửi (khối "Ngành nghề theo Hệ thống ngành kinh tế Việt Nam"); chưa thử trên cổng thật.
TEN = {"7821": "Cung ứng lao động tạm thời", "7822": "Cung ứng nguồn nhân lực khác", "4101": "Xây dựng nhà để ở", "4102": "Xây dựng nhà không để ở",
       "4222": "Xây dựng công trình cấp, thoát nước", "4299": "Xây dựng công trình kỹ thuật dân dụng khác"}
ST = {"ds": ["7821", "7822"], "chinh": "7821"}
LOG = []
MENU = '<div id=menu><a href="/ov">Hình thức đăng ký</a> <a href="/nganh">Ngành, nghề kinh doanh</a></div>'


def trang_nganh():
    dong = "".join(f'<tr><td>{i+1}</td><td><input type=checkbox></td><td><input type=radio name=chinh value={m}{" checked" if m == ST["chinh"] else ""}></td>'
                   f'<td>{m}</td><td>{TEN.get(m, "?")}<br><textarea id=ct{m}></textarea></td><td><a href="/nganh?del={m}">Xóa</a></td></tr>' for i, m in enumerate(ST["ds"]))
    return f"""<div>Ngành nghề theo Hệ thống ngành kinh tế Việt Nam</div><div>Thêm ngành nghề</div>
<form id=f action="/nganh"><div>Mã số ngành nghề kinh doanh theo Hệ thống ngành kinh tế Việt Nam</div><input id=ma name=add>
<input type=button value="Chọn"><input type=submit value="Thêm ngành nghề bằng mã số"> <input type=button value="Thêm/xóa ngành nghề trong danh sách"></form>
<div>Danh sách ngành nghề kinh doanh</div><table id=ds><tr><th>STT.</th><th></th><th>Có phải là ngành chính?</th><th>Mã số ngành nghề kinh doanh</th><th>Tên ngành nghề kinh doanh</th><th></th></tr>{dong}</table>
<input type=button value="Xóa"><input type=button id=cnc value="Cập nhật chính" onclick="location.href='/nganh?chinh='+document.querySelector('input[name=chinh]:checked').value">
<div>Ngành nghề kinh doanh không liệt kê trong Hệ thống ngành kinh tế Việt Nam</div><textarea id=khac></textarea><input type=button value="Trở về" onclick="location.href='/ov'"><input type=button id=luu value="Lưu"{" disabled" if ST.get("daluu") else ""} onclick="location.href='/nganh?luu=1'">"""


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        LOG.append(self.path)
        pr = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(pr.query)
        if pr.path == "/nganh":
            for m in q.get("add", []):
                m = m.strip()
                if m in TEN and m not in ST["ds"]:
                    ST["ds"].append(m)
            for m in q.get("del", []):
                if m in ST["ds"]:
                    ST["ds"].remove(m)
            if q.get("luu"):
                ST["daluu"] = True
            if q.get("chinh"):
                ST["chinh"] = q["chinh"][0]
            html = trang_nganh()
        else:
            html = MENU + "<table><tr><td>Hình thức đăng ký:</td><td>Đăng ký thay đổi</td></tr></table>" + "x" * 100
        b = ("<meta charset=utf-8>" + html).encode("utf-8")
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("X-Frame-Options", "DENY"); self.end_headers(); self.wfile.write(b)

    def log_message(self, *a):
        pass


srv = HTTPServer(("127.0.0.1", 0), H); cong = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
NG = {"them": [{"ma": "4101", "ten": "Xây dựng nhà để ở", "chi_tiet": "", "chinh": False}, {"ma": "4102", "ten": "", "chi_tiet": "Xây dựng nhà xưởng", "chinh": True},
               {"ma": "4222", "ten": "", "chi_tiet": "", "chinh": False}, {"ma": "4299", "ten": "", "chi_tiet": "", "chinh": False}],
      "bo": [{"ma": "7822", "ten": ""}], "sua": [{"ma": "7821", "ten": "", "chi_tiet": "Trừ cho thuê lại lao động", "chinh": False}]}
DL = {"dkkd_dien": 1, "ban": "x", "truong": [], "nhac": [], "bo_qua": [],
      "nhom": [{"ten": "Ngành nghề kinh doanh", "vao_khoi": "Ngành nghề kinh doanh || Ngành, nghề kinh doanh || Ngành nghề", "tao_moi": False, "truong": [], "nganh": NG},
               {"ten": "Khối kế tiếp", "vao_khoi": "Ngành, nghề kinh doanh", "tao_moi": False, "truong": [], "nganh": {"them": [{"ma": "4101", "ten": "", "chi_tiet": "", "chinh": False}], "bo": [], "sua": []}}]}
js = urllib.parse.unquote(server.dkkd_bookmarklet_dien()[len("javascript:"):])
RUN = r"""
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: process.env.CHROME || undefined });
  const ctx = await b.newContext(); const pg = await ctx.newPage(); const pops = []; ctx.on('page', p => pops.push(p));
  const dlg = []; pg.on('dialog', async d => { dlg.push(d.message()); await d.dismiss(); });
  await pg.goto('http://127.0.0.1:' + process.env.PORT + '/ov');
  await pg.evaluate(d => { Object.defineProperty(navigator, 'clipboard', { value: { readText: async () => d }, configurable: true }); }, process.env.DL);
  await pg.evaluate(process.env.JS);
  await pg.waitForFunction(() => /Kiểm tra rồi bấm Lưu/.test(((document.getElementById('__dkkdTrangThai') || {}).innerText || '') + ((document.getElementById('__dkkdBang') || {}).innerText || '')), null, { timeout: 120000 });
  await pg.waitForTimeout(500); const w = pops[0];
  const truoc = { ct4102: await w.inputValue('#ct4102'), ct7821: await w.inputValue('#ct7821'), khac: await w.inputValue('#khac') };
  await w.click('#luu');                       // người dùng bấm Lưu -> cổng chuyển sang trang "Hình thức đăng ký": phần mềm tự sang khối kế tiếp
  try { await pg.waitForFunction(() => /đã Lưu ✓/.test((document.getElementById('__dkkdBang') || {}).innerText || ''), null, { timeout: 40000 }); } catch (e) { console.log('@@' + JSON.stringify({kt: 'KHONG_TU_SANG', bang: await pg.evaluate(() => (document.getElementById('__dkkdBang') || {}).innerText)})); await b.close(); return }
  await pops[0].waitForTimeout(16000); const w2 = pops[0];            // khối kế tiếp đã mở lại trang Ngành nghề
  const r = { bang: await pg.evaluate(() => ((document.getElementById('__dkkdTrangThai') || {}).innerText || '') + ((document.getElementById('__dkkdBang') || {}).innerText || '')), dlg, ...truoc };
  console.log('@@' + JSON.stringify(r));
  await b.close();
})();
"""
f = os.path.join(tempfile.mkdtemp(), "t.js"); open(f, "w", encoding="utf-8").write(RUN)
env = dict(os.environ, NODE_PATH="/opt/node22/lib/node_modules", DL=json.dumps(DL), JS=js, PORT=str(cong))
if os.path.exists("/opt/pw-browsers/chromium"):
    env["CHROME"] = "/opt/pw-browsers/chromium"
p = subprocess.run(["node", f], capture_output=True, text=True, env=env, timeout=240)
dong = [x for x in p.stdout.splitlines() if x.startswith("@@")]
assert dong, p.stdout + p.stderr
r = json.loads(dong[0][2:])
assert ST["ds"] == ["7821", "4101", "4102", "4222", "4299"], (ST, r)                       # bỏ 7822, thêm đủ 4 mã theo thứ tự
assert ST["chinh"] == "4102", ST                                                          # ngành chính + "Cập nhật chính"
assert r["ct4102"] == "Xây dựng nhà xưởng" and r["ct7821"] == "Trừ cho thuê lại lao động", r     # chi tiết dưới tên ngành
assert r["khac"] == "", r                                                                  # không đụng ô "ngành nghề không liệt kê"
assert not r["dlg"], r["dlg"]                                                              # không có lỗi cần xử lý tay
assert "CẦN XỬ LÝ TAY" not in r["bang"], r["bang"]
assert any(x.startswith("/nganh?luu=1") for x in LOG) and LOG[-3:].count("/ov") + LOG.count("/ov") >= 4, LOG            # chỉ người dùng bấm Lưu (1 lần); phần mềm tự sang khối kế tiếp                                              # không bấm Lưu
print("PASS: khối Ngành nghề — điền xong, người dùng bấm Lưu (cổng chuyển sang trang khác) thì phần mềm TỰ sang khối kế tiếp.")
print("\nALL DONE")
