import io, json, os, subprocess, sys, tempfile, zipfile
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import gpkd_soan as g

# Chỉ CẬP NHẬT thông tin (địa chỉ ghi lại theo đơn vị hành chính mới sau sáp nhập + thông tin người đại diện pháp luật/thành viên):
# Mẫu 12 chỉ giữ mục B (Bổ sung, cập nhật thông tin) theo đúng bộ hồ sơ thực tế (PACI), KHÔNG soạn Quyết định.
DU = {"loai": ["cap_nhat"], "dn": {"ten": "CÔNG TY TNHH CÔNG NGHỆ PACI", "ma_so": "0316485079", "co_quan": "Phòng đăng ký kinh doanh Thành phố Hồ Chí Minh",
      "loai_hinh": "Công ty trách nhiệm hữu hạn hai thành viên trở lên"}, "hien_tai": {"dd_ho_ten": "NGUYỄN QUỐC ĐẠT", "ngay_cap_gcn": "01/01/2020"},
      "cap_nhat": {"dia_chi": {"so_nha": "18/02 Trần Thị Do", "xa": "Phường Tân Thới Hiệp", "tinh": "Thành phố Hồ Chí Minh"},
                   "nguoi": [{"ho_ten": "Nguyễn Quốc Đạt", "gioi_tinh": "Nam", "ngay_sinh": "1986-04-12", "cccd": "066086014123", "ngay_cap": "26/08/2024",
                              "noi_cap": "Cục Cảnh Sát Quản Lý Hành Chính Về Trật Tự Xã Hội", "dia_chi": "18/02 Trần Thị Do, Phường Tân Thới Hiệp, TP Hồ Chí Minh, Việt Nam"},
                             {"ho_ten": "Võ Thị Huỳnh Như", "gioi_tinh": "Nữ", "ngay_sinh": "02/09/1986", "cccd": "083186013788", "ngay_cap": "21/08/2022", "noi_cap": "Cục Cảnh Sát QLHC Về TTXH"},
                             {"ho_ten": "  ", "cccd": "x"}]}}
d = g.soan_mau12(DU, {})
t = [p.text for p in d.paragraphs if p.text.strip()]
i = t.index("1. Cập nhật địa chỉ trụ sở chính công ty:")
assert t[i - 1].startswith("B. BỔ SUNG, CẬP NHẬT THÔNG TIN ĐĂNG KÝ DOANH NGHIỆP"), t[i - 1]
assert t[i + 1:i + 4] == ["Số nhà/phòng, ngách/hẻm, ngõ/kiệt, đường/phố/đại lộ, tổ/xóm/ấp/thôn: 18/02 Trần Thị Do", "Xã/Phường/Đặc khu: Phường Tân Thới Hiệp",
                          "Tỉnh/Thành phố trực thuộc trung ương: Thành phố Hồ Chí Minh"], t[i:i + 5]
assert t[i + 4] == "2. Cập nhật thông tin đại diện pháp luật và thành viên:" and t[i + 5] == "1/ Họ và tên: NGUYỄN QUỐC ĐẠT", t[i + 4:i + 7]
assert t[i + 6:i + 14] == ["Giới tính: Nam", "Sinh ngày: 12/04/1986", "Dân tộc: Kinh", "Quốc tịch: Việt Nam", "Số giấy tờ pháp lý của cá nhân: 066086014123", "Ngày cấp: 26/08/2024",
                           "Nơi cấp: Cục Cảnh Sát Quản Lý Hành Chính Về Trật Tự Xã Hội", "Địa chỉ thường trú: 18/02 Trần Thị Do, Phường Tân Thới Hiệp, TP Hồ Chí Minh, Việt Nam"], t[i + 6:i + 14]
assert "2/ Họ và tên: VÕ THỊ HUỲNH NHƯ" in t and "Giới tính: Nữ" in t and not any(x.startswith("3/ ") for x in t), t
assert not any(re.fullmatch(r"[…\.\s]+", x) for x in t for re in [__import__("re")]), "đoạn chấm của mục B đã được thay"
for muc in ("ĐĂNG KÝ THAY ĐỔI TÊN", "ĐĂNG KÝ THAY ĐỔI ĐỊA CHỈ", "ĐĂNG KÝ THAY ĐỔI THÀNH VIÊN", "ĐĂNG KÝ THAY ĐỔI VỐN", "THÔNG BÁO THAY ĐỔI NGÀNH", "C. ĐỀ NGHỊ HIỆU ĐÍNH"):
    assert not any(x.startswith(muc) for x in t), muc
print("PASS 1: Mẫu 12 chỉ giữ mục B: '1. Cập nhật địa chỉ…' (3 dòng) + '2. Cập nhật thông tin đại diện pháp luật và thành viên' kèm từng người (đúng bộ hồ sơ mẫu).")

# chỉ cập nhật địa chỉ / chỉ người
du2 = json.loads(json.dumps(DU)); du2["cap_nhat"]["nguoi"] = []
t2 = [p.text for p in g.soan_mau12(du2, {}).paragraphs if p.text.strip()]
assert "1. Cập nhật địa chỉ trụ sở chính công ty:" in t2 and not any(x.startswith("2. Cập nhật thông tin đại diện") for x in t2)
du3 = json.loads(json.dumps(DU)); du3["cap_nhat"]["dia_chi"] = {}
t3 = [p.text for p in g.soan_mau12(du3, {}).paragraphs if p.text.strip()]
assert "1. Cập nhật thông tin đại diện pháp luật và thành viên:" in t3 and not any("Cập nhật địa chỉ trụ sở" in x for x in t3)
print("PASS 2: chỉ địa chỉ / chỉ người -> đánh số mục 1 đúng, không ghi phần để trống.")

# cùng 'Bổ sung' tự do: vẫn điền các dòng chấm còn lại
du4 = json.loads(json.dumps(DU)); du4["loai"] = ["cap_nhat", "bo_sung"]; du4["bo_sung"] = {"noi_dung": "Cập nhật email liên hệ; Cập nhật số điện thoại"}
t4 = [p.text for p in g.soan_mau12(du4, {}).paragraphs if p.text.strip()]
assert "Cập nhật email liên hệ" in t4 and "Cập nhật số điện thoại" in t4 and "1. Cập nhật địa chỉ trụ sở chính công ty:" in t4
print("PASS 3: kết hợp 'Bổ sung, cập nhật' tự do: các ý tự do vẫn ghi sau phần cập nhật có cấu trúc.")

# gói hồ sơ: có Mẫu 12, KHÔNG có Quyết định/Mẫu 15/I-6/hợp đồng
zb, ten_zip, cb = g.tao_ho_so(DU, {})
ten = zipfile.ZipFile(io.BytesIO(zb)).namelist()
assert any(n.startswith("Mau12_") for n in ten) and not any(n.startswith(("Quyet_dinh", "Mau15", "PhuLuc_I-6", "Hop_dong")) for n in ten), ten
print("PASS 4: gói hồ sơ chỉ có Mẫu 12 (mục B) + danh mục, không soạn Quyết định.", sorted(ten))

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
  await pg.evaluate('moSoanGpkd()');
  await pg.waitForSelector('#ssL_cap_nhat', { state: 'attached' });
  await pg.evaluate(() => {
    ssHienTrang = { dia_chi: { so_nha: '18/02 Trần Thị Do', xa: 'Phường Tân Thới Hiệp', tinh: 'Thành phố Hồ Chí Minh' }, dai_dien: [{ ho_ten: 'NGUYỄN QUỐC ĐẠT', cccd: '066086014123', chuc_danh: 'Giám đốc' }],
      thanh_vien: [{ ho_ten: 'NGUYỄN QUỐC ĐẠT', cccd: '066086014123', gioi_tinh: 'Nam', ngay_sinh: '12/04/1986', ngay_cap: '26/08/2024', noi_cap: 'Cục CSQLHC', dia_chi: '18/02 Trần Thị Do', von: '1' },
                   { ho_ten: 'VÕ THỊ HUỲNH NHƯ', cccd: '083186013788', gioi_tinh: 'Nữ', ngay_sinh: '02/09/1986', von: '1' }] };
    ssTv = { ht: ssHienTrang.thanh_vien.map(x => ({ ...x })), moi: [] };
    document.getElementById('ssL_cap_nhat').checked = true; ssHienCacMuc();
  });
  const r = await pg.evaluate(() => { const d = ssThuThap(); return { loai: d.loai, cn: d.cap_nhat, dc: document.getElementById('ssCnDc_xa').value, n: document.querySelectorAll('#ssCapNhatBox input[id^=ssCnN_]').length }; });
  await pg.evaluate("(()=>{let e=document.getElementById('ssCapNhatBox');while(e&&e!==document.body){if(getComputedStyle(e).display==='none')e.style.display='block';e=e.parentElement}})()");
  await pg.fill('#ssCnDc_xa', 'Phường Mới');
  r.sau = await pg.evaluate(() => ssThuThap().cap_nhat.dia_chi.xa);
  r.loi = loi;
  console.log('@@' + JSON.stringify(r));
  await b.close();
})();
"""
tmp = tempfile.mkdtemp(); f = os.path.join(tmp, "t.js"); open(f, "w", encoding="utf-8").write(JS)
env = dict(os.environ, NODE_PATH="/opt/node22/lib/node_modules", INDEX=os.path.join(_REPO_ROOT, "static", "index.html"))
if os.path.exists("/opt/pw-browsers/chromium"):
    env["CHROME"] = "/opt/pw-browsers/chromium"
p = subprocess.run(["node", f], capture_output=True, text=True, env=env, timeout=120)
dd = [x for x in p.stdout.splitlines() if x.startswith("@@")]
assert dd, p.stdout + p.stderr
r = json.loads(dd[0][2:])
assert r["loai"] == ["cap_nhat"] and r["dc"] == "Phường Tân Thới Hiệp" and r["n"] == 18, r          # 2 người x 9 ô (người đại diện trùng thành viên đã gộp)
assert [x["ho_ten"] for x in r["cn"]["nguoi"]] == ["NGUYỄN QUỐC ĐẠT", "VÕ THỊ HUỲNH NHƯ"] and r["cn"]["nguoi"][0]["ngay_sinh"] == "12/04/1986" and r["sau"] == "Phường Mới", r
assert not [e for e in r["loi"] if "Failed to fetch" not in e], r["loi"]
print("PASS 5: giao diện: tick 'Chỉ CẬP NHẬT thông tin' -> tự điền địa chỉ + người đại diện/thành viên hiện tại (gộp trùng), sửa được từng ô, dữ liệu đi vào hồ sơ.")
print("ALL DONE")
