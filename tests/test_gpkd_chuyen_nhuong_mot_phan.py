import io, json, os, subprocess, sys, tempfile, zipfile
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import gpkd_soan as g

# Chuyển nhượng MỘT PHẦN vốn: LÊ QUANG CHUNG (2.250.000.000) chuyển 2.000.000.000 cho PHẠM THANH QUYÊN (2.750.000.000) — Chung vẫn là thành viên.
TV = {"ht": [{"ho_ten": "PHẠM THANH QUYÊN", "cccd": "082186000121", "von": "2.750.000.000"},
             {"ho_ten": "LÊ QUANG CHUNG", "cccd": "037081000763", "von": "2.250.000.000", "cn": [{"den": "h0", "tien": "2.000.000.000", "gia": ""}]}], "moi": []}
sau, tong = g.tinh_thanh_vien_sau(TV)
kq = {x["ho_ten"]: (x["von"], x["ty_le"]) for x in sau}
assert kq == {"PHẠM THANH QUYÊN": (4750000000, "95%"), "LÊ QUANG CHUNG": (250000000, "5%")} and tong == 5000000000, kq
print("PASS 1: chuyển 2 tỷ từ Chung sang Quyên -> Quyên 4,75 tỷ (95%), Chung còn 250 triệu (5%), tổng vốn không đổi.")

# số chuyển vượt phần vốn đang có -> bỏ qua; người nhận bị gạch -> bỏ qua; chuyển cho người MỚI -> vốn người mới = phần nhận
tv2 = json.loads(json.dumps(TV)); tv2["ht"][1]["cn"] = [{"den": "h0", "tien": "9.000.000.000"}]
assert g.tinh_thanh_vien_sau(tv2)[0][1]["von"] == 2250000000
tv3 = json.loads(json.dumps(TV)); tv3["moi"] = [{"ho_ten": "NGƯỜI MỚI", "von": "999"}]; tv3["ht"][1]["cn"] = [{"den": "m0", "tien": "1.000.000.000"}]
s3 = {x["ho_ten"]: x["von"] for x in g.tinh_thanh_vien_sau(tv3)[0]}
assert s3["NGƯỜI MỚI"] == 1000000000 and s3["LÊ QUANG CHUNG"] == 1250000000, s3
print("PASS 2: số chuyển vượt phần đang có bị bỏ qua; chuyển cho người mới thì vốn người mới = phần nhận.")

cap = g._cac_cap_chuyen_nhuong(TV)
assert len(cap) == 1 and cap[0][0]["ho_ten"] == "LÊ QUANG CHUNG" and cap[0][0]["von"] == 2000000000 and cap[0][1]["ho_ten"] == "PHẠM THANH QUYÊN", cap
d = g.soan_hop_dong_chuyen_nhuong({"dn": {"ten": "Cty A", "ma_so": "1"}, "hien_tai": {}, "thanh_vien": TV}, cap[0][0], cap[0][1])
t = "\n".join(p.text for p in d.paragraphs)
assert "2.000.000.000 đồng chiếm 40%" in t and "LÊ QUANG CHUNG" in t and "PHẠM THANH QUYÊN" in t, t
print("PASS 3: Hợp đồng chuyển nhượng ghi đúng phần chuyển 2.000.000.000 đồng chiếm 40% vốn điều lệ (không phải toàn bộ phần của Chung).")

du = {"loai": ["chu_so_huu"], "dn": {"ten": "Cty A", "ma_so": "0300000001", "loai_hinh": "Công ty trách nhiệm hữu hạn hai thành viên trở lên"}, "hien_tai": {}, "thanh_vien": TV}
zb, ten_zip, cb = g.tao_ho_so(du, {})
ten = zipfile.ZipFile(io.BytesIO(zb)).namelist()
assert any(n.startswith("Hop_dong_chuyen_nhuong_phan_von_gop_1_") for n in ten) and any(n.startswith("PhuLuc_I-6") for n in ten), ten
print("PASS 4: hồ sơ có Hợp đồng chuyển nhượng + Phụ lục I-6 (Chung 5%, Quyên 95%).")

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
  await pg.evaluate("document.getElementById('ssL_chu_so_huu').checked=true;ssHienCacMuc();ssTv={ht:window.__tv.ht.map(x=>({...x,cn:undefined})),moi:[],chu_tich:''};ssVeNguoi('tv')");
  await pg.evaluate("ssCnThem(1)");
  await pg.evaluate("(()=>{let e=document.getElementById('ssNguoiBox_tv');while(e&&e!==document.body){if(getComputedStyle(e).display==='none')e.style.display='block';e=e.parentElement}})()");
  await pg.selectOption('#ssNguoiBox_tv select[onchange^="ssCnDen(1,0"]', 'h0');
  await pg.fill('#ssNguoiBox_tv input[placeholder^="vd 2.000"]', '2.000.000.000');
  const r = { sauVon: [await pg.innerText('#ssSauVon_0'), await pg.innerText('#ssSauVon_1')], pt: await pg.innerText('#ssCnPt_1_0'), tong: await pg.innerText('#ssNguoiTong_tv'), cn: await pg.evaluate('ssTv.ht[1].cn'), du: await pg.evaluate('ssThuThap().thanh_vien.ht[1].cn'), loi };
  console.log('@@' + JSON.stringify(r));
  await b.close();
})();
"""
tmp = tempfile.mkdtemp(); f = os.path.join(tmp, "t.js"); open(f, "w", encoding="utf-8").write(JS)
env = dict(os.environ, NODE_PATH="/opt/node22/lib/node_modules", INDEX=os.path.join(_REPO_ROOT, "static", "index.html"), TV=json.dumps({"ht": [dict(x) for x in TV["ht"]]}))
for x in json.loads(env["TV"])["ht"]:
    pass
if os.path.exists("/opt/pw-browsers/chromium"):
    env["CHROME"] = "/opt/pw-browsers/chromium"
p = subprocess.run(["node", f], capture_output=True, text=True, env=env, timeout=120)
d = [x for x in p.stdout.splitlines() if x.startswith("@@")]
assert d, p.stdout + p.stderr
r = json.loads(d[0][2:])
assert r["pt"].startswith("40% vốn điều lệ"), r
assert "PHẠM THANH QUYÊN 4.750.000.000 (95%)" in r["tong"] and "LÊ QUANG CHUNG 250.000.000 (5%)" in r["tong"], r["tong"]
assert r["cn"] == [{"den": "h0", "tien": "2.000.000.000", "gia": ""}] and r["du"] == r["cn"], r
assert "4.750.000.000 VNĐ (95%)" in r["sauVon"][0] and "nhận thêm +2.000.000.000" in r["sauVon"][0], r["sauVon"]       # thẻ thành viên cập nhật theo chuyển nhượng
assert "250.000.000 VNĐ (5%)" in r["sauVon"][1] and "chuyển đi −2.000.000.000" in r["sauVon"][1], r["sauVon"]
assert not [e for e in r["loi"] if "Failed to fetch" not in e], r["loi"]
print("PASS 5: giao diện: nút '↔ Chuyển một phần vốn' -> chọn người nhận + số vốn -> hiện 40% vốn điều lệ và tổng sau thay đổi 95%/5%; dữ liệu đi vào hồ sơ.")
print("ALL DONE")
