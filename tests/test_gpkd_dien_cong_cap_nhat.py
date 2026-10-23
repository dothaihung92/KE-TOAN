import json, os, subprocess, tempfile
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Chế độ CẬP NHẬT: nút điền phải có nhóm cho địa chỉ, người đại diện (Giám đốc) và thành viên, bấm "Sửa đổi" đúng dòng (không Tạo mới).
JS = r"""
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: process.env.CHROME || undefined });
  const pg = await b.newPage({ viewport: { width: 1500, height: 1000 } });
  const loi = []; pg.on('pageerror', e => loi.push(String(e)));
  await pg.goto('file://' + process.env.INDEX);
  await pg.evaluate(() => {
    current = 7; gpkdCid = 7; gpkdKkhoi = []; gpkdNap = async () => {};
    api = async (p) => { if (p.startsWith('/api/gpkd-soan/nganh')) return { nganh: [], nguon: '' }; if (p.startsWith('/api/gpkd-soan/mau')) return { bien: {}, mau_rieng: [] }; return {}; };
    for (const id of ['nhapLieuHome', 'nhapLieuContent', 'nhapLieuBody']) if (!document.getElementById(id)) { const d = document.createElement('div'); d.id = id; document.body.appendChild(d); }
  });
  await pg.evaluate('moSoanGpkd()');
  await pg.waitForSelector('#ssL_cap_nhat', { state: 'attached' });
  await pg.evaluate(() => {
    document.getElementById('ssL_cap_nhat').checked = true;
    ssHienTrang = { dai_dien: [{ ho_ten: 'PHAM THỊ THÚY HẰNG', chuc_danh: 'Giám đốc', cccd: '027181000304' }],
      thanh_vien: [{ ho_ten: 'NGUYÊN THÀNH TRUNG', cccd: '001079024521', von: '1000000000' }, { ho_ten: 'PHAM THỊ THÚY HẰNG', cccd: '027181000304', ngay_sinh: '01/01/1981', von: '1000000000' }] };
    ssTv.ht = []; ssCnLayNguoiHt(); ssCn.dia_chi = { so_nha: '12 Lê Lợi', xa: 'Phường Bến Nghé', tinh: 'Thành phố Hồ Chí Minh' };
  });
  const dl = await pg.evaluate('ssTaoDuLieuDien()');
  console.log('@@' + JSON.stringify({ dl, loi }));
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
r = json.loads(d[0][2:]); assert not [e for e in r["loi"] if "Failed to fetch" not in e], r["loi"]
nh = {g["ten"]: g for g in r["dl"]["nhom"]}
assert "Cập nhật địa chỉ trụ sở chính" in nh and not nh["Cập nhật địa chỉ trụ sở chính"].get("tao_moi")
dd = nh["Cập nhật người đại diện theo pháp luật (Tạo mới): PHAM THỊ THÚY HẰNG"]
assert dd["vao_khoi"] == "Người đại diện theo pháp luật" and dd["tao_moi"] and not dd.get("sua_dong") and not dd.get("bo_qua_neu_co")
assert any(t["gia_tri"] == "Giám đốc" for t in dd["truong"])
tv = [g for k, g in nh.items() if k.startswith("Cập nhật thành viên")]
assert len(tv) == 2 and all(g["vao_khoi"] == "Thông tin về thành viên" and g["tao_moi"] and not g.get("sua_dong") and not g.get("bo_qua_neu_co") for g in tv), tv
for g in tv:
    ten = {t["ten"]: t["gia_tri"] for t in g["truong"]}
    assert ten["Phần vốn góp"] == "1.000.000.000" and ten["Sở hữu vốn (%)"] == "50", ten
    assert any(t.get("bang") for t in g["truong"])
print("PASS: chế độ cập nhật bấm Tạo mới (không Sửa đổi) cho người đại diện và thành viên, kèm vốn góp 1 tỷ/50%.")
