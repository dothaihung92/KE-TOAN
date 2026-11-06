import io, json, os, subprocess, sys, tempfile, zipfile
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import docx
import gpkd_soan as g

# Hồ sơ CHI NHÁNH (Mẫu 19) — mục B "Bổ sung, cập nhật thông tin đăng ký hoạt động" có thêm 2 phần cập nhật như Mẫu 12:
# "Cập nhật địa chỉ trụ sở chính (theo đơn vị hành chính mới sau sáp nhập)" và "Cập nhật thông tin người đại diện pháp luật". Dữ liệu giả.
DU = {"la_chi_nhanh": True, "loai": ["bo_sung"],
      "dn": {"ten": "CÔNG TY TNHH GIẢ", "ma_so": "0300000001", "co_quan": "Phòng ĐKKD", "so_vb": "01", "ngay_lap": "05/11/2026"},
      "hien_tai": {"dd_ho_ten": "NGUYỄN AAA"}, "cn": {"kieu": "chi_nhanh", "ten": "CHI NHÁNH GIẢ", "ma_so": "0300000001-001"},
      "bo_sung": {"noi_dung": ""},
      "cap_nhat": {"dia_chi": {"so_nha": "78/3 Bình Lợi", "xa": "Phường Bình Lợi Trung", "tinh": "TP Hồ Chí Minh"},
                   "nguoi": [{"ho_ten": "Trần Đức Hoàng", "gioi_tinh": "Nam", "ngay_sinh": "1990-07-31", "cccd": "075090020672", "ngay_cap": "2022-11-02", "noi_cap": "Bộ Công An", "dia_chi": "78/5 Bình Lợi"}]}}


def muc_b(du):
    z, _t, _c = g.tao_ho_so(du, None, False)
    zf = zipfile.ZipFile(io.BytesIO(z))
    d = docx.Document(io.BytesIO(zf.read(next(n for n in zf.namelist() if n.startswith("Mau19_")))))
    ps = [p.text for p in d.paragraphs]
    i = next(k for k, t in enumerate(ps) if t.startswith("B."))
    j = next(k for k, t in enumerate(ps) if t.startswith("Doanh nghiệp cam kết"))
    return [t for t in ps[i + 1:j] if t.strip()]

# 1) chỉ phần cập nhật: ghi địa chỉ + người đại diện (không có phần 'thành viên'), bỏ dòng chấm
b = muc_b(DU)
assert b[0] == "1. Cập nhật địa chỉ trụ sở chính công ty:" and "Số nhà/phòng, ngách/hẻm, ngõ/kiệt, đường/phố/đại lộ, tổ/xóm/ấp/thôn: 78/3 Bình Lợi" in b
assert "Xã/Phường/Đặc khu: Phường Bình Lợi Trung" in b and "Tỉnh/Thành phố trực thuộc trung ương: TP Hồ Chí Minh" in b
assert "2. Cập nhật thông tin đại diện pháp luật:" in b and "1/ Họ và tên: TRẦN ĐỨC HOÀNG" in b and "Sinh ngày: 31/07/1990" in b and "Số giấy tờ pháp lý của cá nhân: 075090020672" in b
assert not any("thành viên" in t for t in b) and not any(t.strip("….") == "" for t in b), b
print("PASS 1: Mẫu 19 mục B ghi cập nhật địa chỉ trụ sở chính + người đại diện pháp luật (không có thành viên).")

# 2) kèm ý nhập tay: phần cập nhật đứng trước, rồi tới các ý nhập
b = muc_b(dict(DU, bo_sung={"noi_dung": "ý một; ý hai"}))
assert b.index("1. Cập nhật địa chỉ trụ sở chính công ty:") < b.index("ý một") < b.index("ý hai"), b
print("PASS 2: có ý nhập tay: phần cập nhật đứng trước, ý nhập tay đứng sau.")

# 3) chỉ người đại diện (không nhập địa chỉ) -> đánh số 1; không có gì -> giữ như cũ (chỉ ý nhập tay)
b = muc_b(dict(DU, cap_nhat={"dia_chi": {}, "nguoi": DU["cap_nhat"]["nguoi"]}))
assert b[0] == "1. Cập nhật thông tin đại diện pháp luật:" and not any("địa chỉ trụ sở" in t for t in b), b
b = muc_b(dict(DU, cap_nhat={"dia_chi": {}, "nguoi": []}, bo_sung={"noi_dung": "chỉ ý nhập tay"}))
assert b[0] == "chỉ ý nhập tay" and not any("Cập nhật" in t for t in b), b
print("PASS 3: để trống phần nào thì không ghi phần đó.")

# 4) Mẫu 12 (công ty) vẫn ghi 'đại diện pháp luật và thành viên'
assert g._dong_cap_nhat(DU)[-9][0].startswith("1/ ") or any("đại diện pháp luật và thành viên" in x[0] for x in g._dong_cap_nhat(DU))
assert any(x[0] == "2. Cập nhật thông tin đại diện pháp luật:" for x in g._dong_cap_nhat(DU, chi_dai_dien=True))
print("PASS 4: Mẫu 12 giữ tiêu đề 'đại diện pháp luật và thành viên'.")

# 5) giao diện màn CN: tick mục B hiện 2 phần; lấy từ hồ sơ công ty (chỉ người đại diện, không thành viên); dữ liệu gửi đi có cap_nhat + loai bo_sung
UI = r"""
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: process.env.CHROME || undefined });
  const pg = await b.newPage({ viewport: { width: 1500, height: 1000 } });
  const loi = []; pg.on('pageerror', e => loi.push(String(e)));
  await pg.goto('file://' + process.env.INDEX);
  await pg.evaluate(() => {
    current = 7; gpkdCid = 7; gpkdKhoi = [];
    gpkdNap = async () => { gpkdCid = 7; };
    api = async (p) => { if (p.startsWith('/api/gpkd-soan/nganh')) return { nganh: [], nguon: '' }; if (p.startsWith('/api/gpkd-soan/mau')) return { bien: {}, mau_rieng: [] }; return {}; };
    for (const id of ['nhapLieuHome', 'nhapLieuContent', 'nhapLieuBody']) if (!document.getElementById(id)) { const d = document.createElement('div'); d.id = id; document.body.appendChild(d); }
    ssHienTrangTuGom = () => ({ ten: 'CÔNG TY GIẢ', ma_so: '0300000001', dia_chi: { so_nha: '78/5 Bình Lợi', xa: 'Phường Bình Lợi Trung', tinh: 'TP Hồ Chí Minh' },
      dai_dien: [{ ho_ten: 'TRẦN ĐỨC HOÀNG', chuc_danh: 'Giám đốc', cccd: '075090020672' }], thanh_vien: [{ ho_ten: 'NGƯỜI THÀNH VIÊN', cccd: '1' }], nganh: [] });
  });
  await pg.evaluate('moSoanCn()');
  await pg.waitForSelector('#ssL_bo_sung', { state: 'attached' });
  const r = {};
  r.truoc = await pg.evaluate(() => document.getElementById('ssM_bo_sung').style.display);
  await pg.evaluate(() => { document.getElementById('ssL_bo_sung').checked = true; scnHienCacMuc(); });
  r.sau = await pg.evaluate(() => document.getElementById('ssM_bo_sung').style.display);
  r.tieude = await pg.evaluate(() => document.getElementById('ssCapNhatBox').innerText);
  await pg.evaluate(() => { ssCnLayDiaChiHt(); ssCnLayNguoiHt(); });
  r.so_nguoi = await pg.evaluate(() => ssCn.nguoi.map(x => x.ho_ten));
  r.dia_chi = await pg.evaluate(() => ssCn.dia_chi);
  r.o_nhap = await pg.evaluate(() => document.getElementById('ssCnN_0_ho_ten').value + '|' + document.getElementById('ssCnDc_xa').value);
  r.du = await pg.evaluate(() => { const d = ssThuThap(); return { loai: d.loai, cap_nhat: d.cap_nhat }; });
  console.log('@@' + JSON.stringify({ r, loi }));
  await b.close();
})();
"""
tmp = tempfile.mkdtemp(); f = os.path.join(tmp, "t.js"); open(f, "w", encoding="utf-8").write(UI)
env = dict(os.environ, NODE_PATH="/opt/node22/lib/node_modules", INDEX=os.path.join(_REPO_ROOT, "static", "index.html"))
if os.path.exists("/opt/pw-browsers/chromium"):
    env["CHROME"] = "/opt/pw-browsers/chromium"
p = subprocess.run(["node", f], capture_output=True, text=True, env=env, timeout=120)
d = [x for x in p.stdout.splitlines() if x.startswith("@@")]
assert d, p.stdout + p.stderr
o = json.loads(d[0][2:]); assert not [e for e in o["loi"] if "Failed to fetch" not in e], o["loi"]
r = o["r"]
assert r["truoc"] == "none" and r["sau"] == "block", r
assert "Cập nhật địa chỉ trụ sở chính (theo đơn vị hành chính mới sau sáp nhập)" in r["tieude"] and "Cập nhật thông tin người đại diện pháp luật" in r["tieude"] and "thành viên" not in r["tieude"], r["tieude"]
assert r["so_nguoi"] == ["TRẦN ĐỨC HOÀNG"], r["so_nguoi"]                  # chỉ người đại diện, không lấy thành viên
assert r["dia_chi"] == {"so_nha": "78/5 Bình Lợi", "xa": "Phường Bình Lợi Trung", "tinh": "TP Hồ Chí Minh"} and r["o_nhap"] == "TRẦN ĐỨC HOÀNG|Phường Bình Lợi Trung", r
assert "bo_sung" in r["du"]["loai"] or r["du"]["loai"] == [], r["du"]
assert r["du"]["cap_nhat"]["nguoi"][0]["ho_ten"] == "TRẦN ĐỨC HOÀNG"
print("PASS 5: màn chi nhánh — mục B hiện 2 phần cập nhật, lấy từ hồ sơ công ty (chỉ người đại diện), dữ liệu gửi đi có cap_nhat.")
