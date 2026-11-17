import json, os, subprocess, sys, tempfile
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Màn Soạn hồ sơ CN (chi nhánh/VPĐD/ĐĐKD) có mục "3. Điền tự động lên trang Sở" với nút Copy dữ liệu điền; khối người đứng đầu điền theo ĐĐKD, không xoá dòng của người đại diện công ty mẹ.
JS = r"""
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: process.env.CHROME || undefined });
  const pg = await b.newPage({ viewport: { width: 1500, height: 1000 } });
  const loi = []; pg.on('pageerror', e => loi.push(String(e)));
  await pg.goto('file://' + process.env.INDEX);
  await pg.evaluate(() => {
    current = 7; gpkdCid = 7; gpkdKhoi = []; gpkdNap = async () => {};
    api = async (p) => { if (p.startsWith('/api/gpkd-soan/nganh')) return { nganh: [], nguon: '' }; if (p.startsWith('/api/gpkd-soan/mau')) return { bien: {}, mau_rieng: [] }; return {}; };
    for (const id of ['nhapLieuHome', 'nhapLieuContent', 'nhapLieuBody']) if (!document.getElementById(id)) { const d = document.createElement('div'); d.id = id; document.body.appendChild(d); }
  });
  await pg.evaluate('moSoanCn()');
  await pg.waitForSelector('#ssL_dai_dien', { state: 'attached' });
  const r = await pg.evaluate(() => {
    const o = {}; o.nut = !!document.querySelector('button[onclick*="ssCopyDuLieuDien"]'); o.ghi = !!document.getElementById('ssDienGhi');
    document.getElementById('ssL_dai_dien').checked = true; scnHienCacMuc();
    ssHienTrang = { dai_dien: [{ ho_ten: 'TRẦN MINH KHẢI' }] };
    const set = (id, v) => { const e = document.getElementById(id); if (e) e.value = v; };
    set('ss_dai_dien_ho_ten', 'LÊ THỊ THANH NHANH'); set('ss_dai_dien_cccd', '086174001010'); set('ss_dai_dien_ngay_sinh', '09/02/1974'); set('ss_dai_dien_gioi_tinh', 'Nữ');
    set('ss_hien_tai_dd_ho_ten', 'TRẦN MINH KHẢI');
    const dl = ssTaoDuLieuDien(); ssVeChonKhoiDien();
    o.nhom = dl.nhom.map(g => ({ ten: g.ten, vao: g.vao_khoi, tao_moi: g.tao_moi, xoa_cu: g.xoa_cu || null, truong: g.truong.map(t => t.ten + '=' + t.gia_tri) }));
    o.chon = document.getElementById('ssDienKhoi').innerText;
    return o;
  });
  r.loi = loi; console.log('@@' + JSON.stringify(r)); await b.close();
})();
"""
f = os.path.join(tempfile.mkdtemp(), "t.js"); open(f, "w", encoding="utf-8").write(JS)
env = dict(os.environ, NODE_PATH="/opt/node22/lib/node_modules", INDEX=os.path.join(_REPO_ROOT, "static", "index.html"))
if os.path.exists("/opt/pw-browsers/chromium"):
    env["CHROME"] = "/opt/pw-browsers/chromium"
p = subprocess.run(["node", f], capture_output=True, text=True, env=env, timeout=200)
d = [x for x in p.stdout.splitlines() if x.startswith("@@")]
assert d, p.stdout + p.stderr
r = json.loads(d[0][2:])
assert r["nut"] and r["ghi"], r
g = r["nhom"][0]
assert "Người đứng đầu" in g["vao"] and g["ten"] == "Người đứng đầu" and g["tao_moi"] is True, g
assert not any("TRẦN MINH KHẢI" in x["ten"] for x in (g["xoa_cu"] or [])), g      # không xoá dòng người đại diện công ty mẹ
assert any(t.startswith("Họ tên người đại diện=LÊ THỊ THANH NHANH") for t in g["truong"]) and any("086174001010" in t for t in g["truong"]), g
assert "Người đứng đầu" in r["chon"] and not [e for e in r["loi"] if "fetch" not in e.lower()], r
print("PASS: màn CN có nút Copy dữ liệu điền; khối 'Người đứng đầu' điền họ tên/CCCD…, không xoá dòng người đại diện công ty mẹ.")
print("\nALL DONE")
