import json
import os
import subprocess
import sys
import tempfile

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Soạn hồ sơ GPKD: thay đổi chủ sở hữu/thành viên và chủ sở hữu hưởng lợi — hiện danh sách người đang tham gia (lấy từ hồ sơ đã gom),
# nút gạch bỏ, chuyển vốn, thêm người mới; địa chỉ liên lạc người đại diện chỉ 1 ô. Chạy trang thật bằng Playwright (file://, api giả lập).
KHOI = [
    {"khoi": "Thông tin về thành viên", "cap": [["Số hồ sơ", "X"],
        ["Danh sách thành viên #1 - Tên", "HÀ NHẬT QUANG"], ["Danh sách thành viên #1 - Số giấy tờ pháp lý", "079086016995"],
        ["Danh sách thành viên #2 - Tên", "HÀ THỊ TRÚC MAI"], ["Danh sách thành viên #2 - Số giấy tờ pháp lý", "079188029565"]]},
    {"khoi": "Thông tin về thành viên (2)", "cap": [["Họ tên", "HÀ NHẬT QUANG"], ["Ngày sinh", "22/07/1986"], ["Giới tính", "Nam"], ["Số giấy tờ pháp lý", "079086016995"],
        ["Nơi cấp", "Bộ Công An"], ["Địa chỉ liên lạc", "481 Hòa Hảo, Phường Diên Hồng, TP Hồ Chí Minh, Việt Nam"], ["Giá trị vốn góp (VNĐ)", "4.500.000.000,000"]]},
    {"khoi": "Thông tin về thành viên (3)", "cap": [["Họ tên", "HÀ THỊ TRÚC MAI"], ["Ngày sinh", "28/11/1988"], ["Giới tính", "Nữ"], ["Số giấy tờ pháp lý", "079188029565"],
        ["Giá trị vốn góp (VNĐ)", "4.500.000.000"]]},
    {"khoi": "Thông tin về chủ sở hữu hưởng lợi", "cap": [["Họ tên", "HÀ NHẬT QUANG"], ["Số giấy tờ pháp lý", "079086016995"], ["Tỷ lệ sở hữu vốn điều lệ trực tiếp", "50"]]},
]
JS = r"""
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: process.env.CHROME || undefined });
  const pg = await b.newPage({ viewport: { width: 1500, height: 1000 } });
  const loi = []; pg.on('pageerror', e => loi.push(String(e)));
  await pg.goto('file://' + process.env.INDEX);
  await pg.evaluate((k) => {
    current = 7; gpkdCid = 7; gpkdKhoi = k; gpkdNap = async () => {};
    api = async (p) => { if (p.startsWith('/api/gpkd-soan/nganh')) return { nganh: [], nguon: '' }; if (p.startsWith('/api/gpkd-soan/mau')) return { bien: {}, mau_rieng: [] }; return {}; };
    for (const id of ['nhapLieuHome', 'nhapLieuContent', 'nhapLieuBody']) if (!document.getElementById(id)) { const d = document.createElement('div'); d.id = id; document.body.appendChild(d); }
  }, JSON.parse(process.env.KHOI));
  await pg.evaluate('moSoanGpkd()');
  await pg.waitForSelector('#ssL_chu_so_huu', { state: 'attached' });
  await pg.evaluate("document.getElementById('ssL_chu_so_huu').checked=true;document.getElementById('ssL_cshhl').checked=true;document.getElementById('ssL_dai_dien').checked=true;ssHienCacMuc()");
  const r = {};
  r.gom = await pg.evaluate('({tv:ssTv.ht,cs:ssCs.ht})');
  await pg.evaluate("ssNguoiBo('tv',0);ssNguoiThem('tv');ssNguoiSet('tv','moi',0,'ho_ten','NGUYỄN VĂN C');ssNguoiSet('tv','moi',0,'von','1.000.000.000');ssNguoiChuyen('tv',0,'m0')");
  r.chonChuyen = await pg.evaluate("[...document.querySelectorAll('#ssNguoiBox_tv select[data-chon^=chuyen] option')].map(o=>o.textContent)");
  r.chonChuTich = await pg.evaluate("[...document.querySelectorAll('#ssNguoiBox_tv select[data-chon^=chutich] option')].map(o=>o.textContent)");
  await pg.evaluate("ssNguoiSet('tv','ht',0,'gia','4.000.000.000')");
  r.vonMoi = await pg.inputValue('#ssng_tv_moi_0_von');
  r.sauGia = await pg.evaluate('ssTvSau().sau.map(x=>[x.ho_ten,x._v])');
  await pg.evaluate("ssNguoiSet('tv','ht',0,'gia','')");
  r.tong = await pg.innerText('#ssNguoiTong_tv');
  r.sau = await pg.evaluate('ssTvSau().sau.map(x=>[x.ho_ten,x._v])');
  r.gach = await pg.evaluate("!!document.querySelector('#ssNguoiBox_tv b[style*=line-through]')");
  r.du = await pg.evaluate('(()=>{const d=ssThuThap();return {tv:d.thanh_vien,csm:d.chu_so_huu_moi}})()');
  await pg.evaluate("ssNguoiBo('cs',0);ssNguoiThem('cs');ssNguoiSet('cs','moi',0,'ho_ten','NGUYỄN VĂN C');ssNguoiSet('cs','moi',0,'truc_tiep','55')");
  r.tongCs = await pg.innerText('#ssNguoiTong_cs');
  r.nutKy = await pg.evaluate("document.querySelectorAll('#ssNguoiBox_tv input[type=file]').length");
  r.dien = await pg.evaluate("(()=>{document.getElementById('ss_dai_dien_ho_ten').value='đinh thị huệ';document.getElementById('ss_dai_dien_cccd').value='036190003147';document.getElementById('ss_dai_dien_dia_chi').value='Số nhà 91, Đường 13, Phường Bình Trưng, Thành phố Hồ Chí Minh';document.getElementById('ssL_chu_so_huu').checked=true;return ssTaoDuLieuDien()})()");
  r.diaChi1 = await pg.evaluate("!!document.getElementById('ss_dai_dien_dia_chi')");
  r.diaChiCu = await pg.evaluate("['so_nha','xa','tinh','quoc_gia'].filter(k=>document.getElementById('ss_dai_dien_'+k))");
  try {
    await pg.evaluate("(()=>{let e=document.getElementById('nhapLieuBody');while(e&&e!==document.body){if(getComputedStyle(e).display==='none')e.style.display='block';e=e.parentElement}})()");
    await (await pg.$('#ssNguoiBox_tv')).screenshot({ path: process.env.ANH });
  } catch (e) {}
  r.loi = loi;
  console.log('@@' + JSON.stringify(r));
  await b.close();
})();
"""
tmp = tempfile.mkdtemp()
jsf = os.path.join(tmp, "t.js")
open(jsf, "w", encoding="utf-8").write(JS)
env = dict(os.environ, NODE_PATH="/opt/node22/lib/node_modules", INDEX=os.path.join(_REPO_ROOT, "static", "index.html"), KHOI=json.dumps(KHOI),
           ANH=os.environ.get("ANH_UI") or os.path.join(tmp, "ui.png"), CHROME="/opt/pw-browsers/chromium" if os.path.exists("/opt/pw-browsers/chromium") else "")
if not env["CHROME"]:
    env.pop("CHROME")
p = subprocess.run(["node", jsf], capture_output=True, text=True, env=env, timeout=120)
dong = [x for x in p.stdout.splitlines() if x.startswith("@@")]
assert dong, p.stdout + p.stderr
r = json.loads(dong[0][2:])
assert not [e for e in r["loi"] if "Failed to fetch" not in e], r["loi"]      # file:// không có máy chủ nên các lệnh gọi khi mở trang báo Failed to fetch — bỏ qua
tv = r["gom"]["tv"]
assert [x["ho_ten"] for x in tv] == ["HÀ NHẬT QUANG", "HÀ THỊ TRÚC MAI"], tv
q = tv[0]
assert q["ngay_sinh"] == "22/07/1986" and q["von"] == "4.500.000.000"      # cổng ghi "4.500.000.000,000" -> không bị nhân 1000 and q["dia_chi"].startswith("481 Hòa Hảo") and q["noi_cap"] == "Bộ Công An", q
assert [x["ho_ten"] for x in r["gom"]["cs"]] == ["HÀ NHẬT QUANG"] and r["gom"]["cs"][0]["truc_tiep"] == "50", r["gom"]["cs"]
print("PASS 1: danh sách thành viên + chủ sở hữu hưởng lợi hiện tại lấy từ hồ sơ đã gom (gộp bảng danh sách và khối chi tiết, không trùng người).")
assert r["sau"] == [["HÀ THỊ TRÚC MAI", 4500000000], ["NGUYỄN VĂN C", 4500000000]]    # người MỚI nhận chuyển nhượng: vốn = phần nhận (số 1 tỷ đã nhập không cộng thêm) -> 2 người, mỗi người 4,5 tỷ, r["sau"]
assert "2 thành viên" in r["tong"] and "NGUYỄN VĂN C" in r["tong"] and r["gach"], r["tong"]
assert r["du"]["tv"]["ht"][0]["bo"] is True and r["du"]["tv"]["ht"][0]["chuyen_cho"] == "m0" and r["du"]["csm"]["ho_ten"] == "NGUYỄN VĂN C"
assert "1 người" in r["tongCs"], r["tongCs"]
assert "NGUYỄN VĂN C" in r["chonChuyen"] and "NGUYỄN VĂN C" in r["chonChuTich"] and "HÀ THỊ TRÚC MAI" in r["chonChuTich"] and "HÀ NHẬT QUANG" not in r["chonChuTich"], (r["chonChuyen"], r["chonChuTich"])
assert r["vonMoi"] == "4.000.000.000" and r["sauGia"][-1][1] == 4000000000, (r["vonMoi"], r["sauGia"])      # nhập giá chuyển nhượng -> ô phần vốn góp của người mới nhảy theo
print("PASS 2: gạch bỏ (có gạch ngang), chuyển vốn sang người khác, thêm người mới; tổng sau thay đổi đúng.")
assert r["diaChi1"] and r["diaChiCu"] == []
assert r["nutKy"] == 3, r["nutKy"]      # mỗi thành viên (2 hiện tại + 1 mới) có nút tải chữ ký
dd = {x["ten"]: x["gia_tri"] for x in r["dien"]["truong"]}
assert dd["Họ tên người đại diện"] == "ĐINH THỊ HUỆ" and dd["Số giấy tờ pháp lý"] == "036190003147" and "chu_so_huu" in r["dien"]["bo_qua"], r["dien"]
ch = {x["ten"]: x for x in r["dien"]["truong"]}
assert ch["Tỉnh/Thành phố"]["gia_tri"] == "Thành phố Hồ Chí Minh" and ch["Xã/Phường/Đặc khu"]["gia_tri"] == "Phường Bình Trưng" and ch["Tỉnh/Thành phố"]["chuoi"] and ch["Xã/Phường/Đặc khu"]["chuoi"], ch
assert ch["Số nhà/đường/phố…"]["gia_tri"] == "Số nhà 91, Đường 13", ch      # địa chỉ 1 ô được tách: số nhà / xã / tỉnh
print("PASS 3c: địa chỉ 1 ô tách thành Số nhà, Tỉnh/Thành, Xã/Phường (2 ô chọn nối tiếp) trong dữ liệu điền.")
print("PASS 3b: dữ liệu điền lên cổng lấy từ ô đã nhập (họ tên IN HOA, số giấy tờ), mục chưa hỗ trợ được báo.")
print("PASS 3: địa chỉ liên lạc người đại diện chỉ còn 1 ô.")
print("\nALL DONE")
