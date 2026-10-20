import json, os, subprocess, tempfile
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Ca thật: người dùng đã cập nhật phần mềm (2026-10-19.260) nhưng trên cổng vẫn chạy nút bookmark CŨ (khung kết quả ghi
# "bản 2026-10-15.226") -> mở thêm tab thứ 2. Nay phần mềm có nút xanh KÉO THẢ thẳng lên thanh dấu trang (mã nút mới nhất)
# và hướng dẫn xóa nút cũ, kèm cách nhận biết nút cũ/mới qua chữ "bản …".
JS = r"""
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: process.env.CHROME || undefined });
  const pg = await b.newPage({ viewport: { width: 1500, height: 1000 } });
  await pg.goto('file://' + process.env.INDEX);
  await pg.evaluate(() => {
    current = 7; window.__appBuild = '2026-10-19.261';
    api = async (p) => { if (p.startsWith('/api/dkkd/bookmarklet-dien')) return { ma: 'javascript:alert(1)', ma_nut: 'abc1234567' }; if (p.startsWith('/api/gpkd-soan/nganh')) return { nganh: [], nguon: '' }; if (p.startsWith('/api/gpkd-soan/mau')) return { bien: {}, mau_rieng: [] }; return {}; };
    for (const id of ['nhapLieuHome', 'nhapLieuContent', 'nhapLieuBody']) if (!document.getElementById(id)) { const d = document.createElement('div'); d.id = id; document.body.appendChild(d); }
  });
  await pg.evaluate('moSoanGpkd()');
  await pg.waitForSelector('#ssNutDienKeo', { state: 'attached' });
  await pg.evaluate("ssNapNutKeo(document.getElementById('ssNutDienKeo'))");
  await pg.waitForFunction(() => document.getElementById('ssNutDienKeo').getAttribute('href').startsWith('javascript:'));
  const r = { href: await pg.getAttribute('#ssNutDienKeo', 'href'), keo: await pg.getAttribute('#ssNutDienKeo', 'draggable'), ban: await pg.textContent('#ssBanNut'),
    ls: await pg.evaluate("localStorage.getItem('dkkdMaNutDien')"), hd: await pg.evaluate("document.getElementById('ssNutDienKeo').parentElement.innerText") };
  console.log('@@' + JSON.stringify(r));
  await b.close();
})();
"""
tmp = tempfile.mkdtemp(); f = os.path.join(tmp, "t.js"); open(f, "w", encoding="utf-8").write(JS)
env = dict(os.environ, NODE_PATH="/opt/node22/lib/node_modules", INDEX=os.path.join(_REPO_ROOT, "static", "index.html"))
if os.path.exists("/opt/pw-browsers/chromium"):
    env["CHROME"] = "/opt/pw-browsers/chromium"
p = subprocess.run(["node", f], capture_output=True, text=True, env=env, timeout=120)
d = [x for x in p.stdout.splitlines() if x.startswith("@@")]
assert d, p.stdout + p.stderr
r = json.loads(d[0][2:])
assert r["href"] == "javascript:alert(1)" and r["keo"] == "true" and r["ban"] == "2026-10-19.261" and r["ls"] == "abc1234567", r
assert "XÓA nút" in r["hd"] and "KÉO THẢ" in r["hd"] and "2026-10-15.226" in r["hd"], r["hd"]
print("PASS: nút xanh kéo thả lên thanh dấu trang mang mã nút mới nhất; hướng dẫn xóa nút cũ và cách nhận biết nút cũ qua chữ 'bản …'.")
print("ALL DONE")
