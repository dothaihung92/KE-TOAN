import io, json, os, subprocess, sys, tempfile, zipfile
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import gpkd_soan as g

# Chuyển nhượng MỘT PHẦN vốn: LÊ QUANG CHUNG (2.250.000.000) chuyển 2.000.000.000 cho PHẠM THANH QUYÊN (2.750.000.000) — Chung vẫn là thành viên.
TV = {"ht": [{"ho_ten": "PHẠM THANH QUYÊN", "cccd": "082186000121", "ngay_sinh": "16/06/1986", "von": "2.750.000.000"},
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
  const dien = await pg.evaluate('ssTaoDuLieuDien()');
  const cs = await pg.evaluate("(()=>{document.getElementById('ssL_cshhl').checked=true;ssCs={ht:[{ho_ten:'PHẠM THANH QUYÊN',cccd:'082186000121',truc_tiep:'55'},{ho_ten:'LÊ QUANG CHUNG',cccd:'037081000763',truc_tiep:'45'}],moi:[]};return ssTaoDuLieuDien()})()");
  const r = { cs, dien, sauVon: [await pg.innerText('#ssSauVon_0'), await pg.innerText('#ssSauVon_1')], pt: await pg.innerText('#ssCnPt_1_0'), tong: await pg.innerText('#ssNguoiTong_tv'), cn: await pg.evaluate('ssTv.ht[1].cn'), du: await pg.evaluate('ssThuThap().thanh_vien.ht[1].cn'), loi };
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
nh = {x["ten"]: x for x in r["dien"]["nhom"]}
gq, gc = nh["Thành viên — nhập vốn mới: PHẠM THANH QUYÊN"], nh["Thành viên — nhập vốn mới: LÊ QUANG CHUNG"]
assert gq["tao_moi"] and not gq.get("sua_dong") and gq["vao_khoi"] == "Thông tin về thành viên", gq            # bấm 'Tạo mới' (không dùng 'Sửa đổi')
tq = {x["ten"]: x["gia_tri"] for x in gq["truong"]}
assert tq["Họ tên"] == "PHẠM THANH QUYÊN" and tq["Số giấy tờ pháp lý"] == "082186000121" and tq["Phần vốn góp"] == "4.750.000.000" and tq["Sở hữu vốn (%)"] == "95", tq
assert {x["ten"]: x["gia_tri"] for x in gc["truong"]}["Phần vốn góp"] == "250.000.000"
assert sum("tự bấm Xóa dòng CŨ" in x for x in r["dien"]["nhac"]) == 2, r["dien"]["nhac"]
gcs = [g for g in r["cs"]["nhom"] if g["vao_khoi"] == "Thông tin về chủ sở hữu hưởng lợi"]
assert [g["ten"] for g in gcs] == ["Chủ sở hữu hưởng lợi: PHẠM THANH QUYÊN"], [g["ten"] for g in gcs]      # danh sách trên cổng trống -> nhập cả người còn giữ
tcs = {x["ten"]: x["gia_tri"] for x in gcs[0]["truong"]}
assert tcs["Tỷ lệ sở hữu trực tiếp"] == "95" and tcs["Ngày sinh"] == "16/06/1986" and gcs[0]["bo_qua_neu_co"]["cccd"] == "082186000121", tcs      # tỷ lệ sau chuyển nhượng; thông tin lấy từ thẻ thành viên
assert any("LÊ QUANG CHUNG" in x and "dưới 25%" in x for x in r["cs"]["nhac"]), r["cs"]["nhac"]          # còn 5% -> không kê khai, có nhắc
assert not [e for e in r["loi"] if "Failed to fetch" not in e], r["loi"]
print("PASS 5: giao diện: nút '↔ Chuyển một phần vốn' -> chọn người nhận + số vốn -> hiện 40% vốn điều lệ và tổng sau thay đổi 95%/5%; dữ liệu đi vào hồ sơ.")

# Quyết định: chỉ chuyển nhượng vốn giữa các thành viên hiện tại -> KHÔNG ghi "Thay đổi thành viên/chủ sở hữu công ty"
TV2 = {"ht": [dict(TV["ht"][0]), dict(TV["ht"][1], cn=[{"den": "h0", "tien": "1.750.000.000"}])], "moi": []}
dq = g.soan_quyet_dinh({"loai": ["chu_so_huu"], "dn": {"ten": "Cty", "loai_hinh": "Công ty TNHH hai thành viên trở lên"}, "hien_tai": {"dd_ho_ten": "PHẠM THANH QUYÊN"}, "thanh_vien": TV2}, {})
tq = "\n".join(p.text for p in dq.paragraphs)
assert "Chuyển nhượng phần vốn góp giữa các thành viên công ty: Ông/Bà LÊ QUANG CHUNG chuyển nhượng cho Ông/Bà PHẠM THANH QUYÊN phần vốn góp trị giá 1.750.000.000 đồng, tương ứng tỷ lệ 35% vốn điều lệ" in tq, tq
assert "Thay đổi thành viên/chủ sở hữu" not in tq and "Phần vốn góp sau khi chuyển nhượng: Ông/Bà PHẠM THANH QUYÊN góp 4.500.000.000 đồng, tỷ lệ 90%" in tq, tq
tv3 = {"ht": [dict(TV["ht"][0], bo=True, chuyen_cho="h1"), dict(TV["ht"][1])], "moi": []}
t3 = "\n".join(p.text for p in g.soan_quyet_dinh({"loai": ["chu_so_huu"], "dn": {"ten": "Cty", "loai_hinh": "Công ty TNHH hai thành viên trở lên"}, "hien_tai": {}, "thanh_vien": tv3}, {}).paragraphs)
assert "Thay đổi thành viên/chủ sở hữu công ty" in t3            # có người rời/người mới vẫn là thay đổi thành viên
print("PASS 6: chỉ chuyển nhượng vốn -> Quyết định ghi 'Chuyển nhượng phần vốn góp…' (không phải thay đổi thành viên/chủ sở hữu); có người rời/mới thì giữ như cũ.")

# Mẫu 12: chỉ chuyển nhượng vốn -> mục "ĐĂNG KÝ THAY ĐỔI VỐN ĐIỀU LỆ, PHẦN VỐN GÓP, TỶ LỆ PHẦN VỐN GÓP" (chỉ mục 2), KHÔNG phải mục thành viên
du12 = {"loai": ["chu_so_huu"], "dn": {"ten": "Cty", "loai_hinh": "Công ty trách nhiệm hữu hạn hai thành viên trở lên"}, "hien_tai": {"dd_ho_ten": "PHẠM THANH QUYÊN"}, "thanh_vien": TV2}
t12 = "\n".join(p.text for p in g.soan_mau12(du12, {}).paragraphs)
assert "ĐĂNG KÝ THAY ĐỔI VỐN ĐIỀU LỆ, PHẦN VỐN GÓP" in t12 and "2. Đăng ký thay đổi phần vốn góp, tỷ lệ phần vốn góp công ty TNHH" in t12, t12
assert "ĐĂNG KÝ THAY ĐỔI THÀNH VIÊN" not in t12 and "1. Đăng ký thay đổi vốn điều lệ" not in t12 and "cam kết bảo đảm thanh toán" not in t12, t12
tv_roi = {"ht": [dict(TV["ht"][0]), dict(TV["ht"][1], bo=True, chuyen_cho="m0")], "moi": [{"ho_ten": "NGƯỜI MỚI", "cccd": "123456789012"}]}
t12b = "\n".join(p.text for p in g.soan_mau12(dict(du12, thanh_vien=tv_roi), {}).paragraphs)
assert "ĐĂNG KÝ THAY ĐỔI THÀNH VIÊN CÔNG TY TNHH" in t12b           # có người rời -> vẫn là thay đổi thành viên
print("PASS 7: Mẫu 12 khi chỉ chuyển nhượng vốn: mục THAY ĐỔI VỐN ĐIỀU LỆ, PHẦN VỐN GÓP, TỶ LỆ (chỉ mục 2); không mục thành viên, không mục 1 vốn điều lệ, không cam kết giảm vốn.")
print("ALL DONE")
