import io, json, os, subprocess, sys, tempfile, zipfile
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import docx
import gpkd_soan as g

# Ca thật (SAO MỸ): LÊ QUANG CHUNG góp 2.250.000.000 (45%) chuyển 1.750.000.000 (35%) cho PHẠM THANH QUYÊN.
TV = {"ht": [{"ho_ten": "PHẠM THANH QUYÊN", "cccd": "082186000121", "von": "2.750.000.000"},
             {"ho_ten": "LÊ QUANG CHUNG", "cccd": "037081000763", "von": "2.250.000.000", "cn": [{"den": "h0", "tien": "1.750.000.000", "gia": ""}]}], "moi": []}
du = {"loai": ["chu_so_huu"], "dn": {"ten": "Cty A", "ma_so": "0318369215", "loai_hinh": "Công ty trách nhiệm hữu hạn hai thành viên trở lên"}, "hien_tai": {}, "thanh_vien": TV}
z = zipfile.ZipFile(io.BytesIO(g.tao_ho_so(du, {})[0]))
ten = z.namelist()
hd = [n for n in ten if n.startswith("Hop_dong_chuyen_nhuong")][0]
t = "\n".join(p.text for p in docx.Document(io.BytesIO(z.read(hd))).paragraphs)
assert "có góp vốn vào CTY A với tỷ lệ giá trị phần góp vốn là 2.250.000.000 đồng chiếm 45% vốn điều lệ" in t, t
assert "giá chuyển nhượng phần góp 1.750.000.000 đồng chiếm 35% vốn điều lệ nói trên là 1.750.000.000 đồng" in t
print("PASS 1: Hợp đồng Điều 1 ghi phần vốn góp HIỆN CÓ của bên bán (2.250.000.000 — 45%); Điều 2 ghi phần chuyển nhượng (1.750.000.000 — 35%).")

assert not any(n.startswith("Quyet_dinh") or n.startswith("Nghi_quyet") for n in ten), ten
assert any(n.startswith("PhuLuc_I-6") for n in ten) and any(n.startswith("Mau12") for n in ten)
print("PASS 2: chuyển nhượng vốn giữa các thành viên (không đổi GĐ/Chủ tịch) -> KHÔNG soạn Quyết định HĐTV; vẫn có Mẫu 12 + Phụ lục I-6 + Hợp đồng.")

du2 = dict(du, chu_tich_moi="h0")
assert any(n.startswith("Quyet_dinh") for n in zipfile.ZipFile(io.BytesIO(g.tao_ho_so(du2, {})[0])).namelist()), "bầu Chủ tịch mới -> vẫn cần Quyết định"
du3 = dict(du, loai=["chu_so_huu", "dai_dien"], dai_dien=[{"ho_ten": "A", "chuc_danh": "Giám đốc"}])
assert any(n.startswith("Quyet_dinh") for n in zipfile.ZipFile(io.BytesIO(g.tao_ho_so(du3, {})[0])).namelist()), "đổi người đại diện -> vẫn cần Quyết định"
du4 = dict(du, loai=["chu_so_huu", "von"], von={"cu": "5.000.000.000", "moi": "6.000.000.000"})
assert any(n.startswith("Quyet_dinh") for n in zipfile.ZipFile(io.BytesIO(g.tao_ho_so(du4, {})[0])).namelist()), "đổi vốn điều lệ -> vẫn cần Quyết định"
print("PASS 3: vẫn soạn Quyết định khi bầu Chủ tịch mới / đổi người đại diện / đổi vốn điều lệ.")

JS = r"""
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: process.env.CHROME || undefined });
  const pg = await b.newPage({ viewport: { width: 1500, height: 1000 } });
  const loi = []; pg.on('pageerror', e => loi.push(String(e)));
  await pg.goto('file://' + process.env.INDEX);
  await pg.evaluate((tv) => {
    current = 7; gpkdCid = 7; gpkdKkhoi = []; gpkdNap = async () => {};
    api = async (p) => { if (p.startsWith('/api/gpkd-soan/nganh')) return { nganh: [], nguon: '' }; if (p.startsWith('/api/gpkd-soan/mau')) return { bien: {}, mau_rieng: [] }; return {}; };
    for (const id of ['nhapLieuHome', 'nhapLieuContent', 'nhapLieuBody']) if (!document.getElementById(id)) { const d = document.createElement('div'); d.id = id; document.body.appendChild(d); }
    window.__tv = tv;
  }, JSON.parse(process.env.TV));
  await pg.evaluate('moSoanGpkd()');
  await pg.waitForSelector('#ssL_chu_so_huu', { state: 'attached' });
  await pg.evaluate("document.getElementById('ssL_chu_so_huu').checked=true;ssHienCacMuc();ssTv={ht:window.__tv.ht.map(x=>({...x})),moi:[],chu_tich:''};ssVeNguoi('tv')");
  const r = await pg.evaluate(() => ({ nhan: document.querySelector('#ssng_tv_ht_1_von').closest('label').innerText, von: document.querySelector('#ssng_tv_ht_1_von').value,
    sau: [document.getElementById('ssVonSau_0').value, document.getElementById('ssVonSau_1').value], ro: document.getElementById('ssVonSau_1').readOnly }));
  console.log('@@' + JSON.stringify({ r, loi: loi.filter(x => !/fetch/i.test(x)) }));
  await b.close();
})();
"""
f = os.path.join(tempfile.mkdtemp(), "t.js"); open(f, "w", encoding="utf-8").write(JS)
env = dict(os.environ, NODE_PATH="/opt/node22/lib/node_modules", INDEX=os.path.join(_REPO_ROOT, "static", "index.html"), TV=json.dumps(TV))
if os.path.exists("/opt/pw-browsers/chromium"):
    env["CHROME"] = "/opt/pw-browsers/chromium"
p = subprocess.run(["node", f], capture_output=True, text=True, env=env, timeout=120)
d = json.loads([x for x in p.stdout.splitlines() if x.startswith("@@")][0][2:])
assert d["r"]["von"] == "2.250.000.000" and "hiện có" in d["r"]["nhan"] and d["r"]["ro"] and not d["loi"], d
assert d["r"]["sau"] == ["4.500.000.000", "500.000.000"], d
print("PASS 4: thẻ thành viên có ô 'Phần vốn góp SAU chuyển nhượng' (chỉ đọc) = vốn còn lại (Quyên 4.500.000.000, Chung 500.000.000); ô nhập ghi rõ 'hiện có'.")
print("ALL DONE")
