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
  r.thue = await pg.evaluate("(()=>{document.getElementById('ssL_thue').checked=true;ssHienCacMuc();document.getElementById('ss_thue_kt_ho_ten').value='Nguyễn Thị Kế';document.getElementById('ss_thue_lao_dong').value='12';const d=ssThuThap();return {loai:d.loai,thue:d.thue}})()");
  r.dien2 = await pg.evaluate('ssTaoDuLieuDien()');
  r.cungDc = await pg.evaluate("(()=>{ssHienTrang.dia_chi={so_nha:'91 đường Số 13',xa:'Phường Bình Trưng',tinh:'Hồ Chí Minh'};const c=document.getElementById('ss_thue_cung_dia_chi');c.checked=true;ssDongBoDiaChiThue();const d=ssThuThap();return {sn:document.getElementById('ss_thue_tt_so_nha').value,xa:document.getElementById('ss_thue_tt_xa').value,tinh:document.getElementById('ss_thue_tt_tinh').value,ro:document.getElementById('ss_thue_tt_xa').readOnly,du:d.thue.cung_dia_chi,gh:document.getElementById('ssThueDiaChiHt').textContent}})()");
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
assert dd["Họ tên người đại diện"] == "ĐINH THỊ HUỆ" and dd["Số giấy tờ pháp lý"] == "036190003147" and not r["dien"]["bo_qua"], r["dien"]
nh = {g["ten"]: g for g in r["dien"]["nhom"]}
g_tv = nh["Thành viên mới: NGUYỄN VĂN C"]
assert g_tv["vao_khoi"] == "Thông tin về thành viên" and g_tv["tao_moi"], g_tv
gt = {x["ten"]: x["gia_tri"] for x in g_tv["truong"]}
assert gt["Họ tên"] == "NGUYỄN VĂN C" and gt["Phần vốn góp"] == "4.500.000.000" and gt["Sở hữu vốn (%)"] == "50", gt       # vốn = phần nhận chuyển nhượng
bg = {x["ten"]: x for x in g_tv["truong"] if x.get("bang")}
assert bg["Loại tài sản — tỷ lệ (%)"]["bang"] == "^đồng việt nam" and bg["Loại tài sản — tỷ lệ (%)"]["gia_tri"] == "100" and bg["Loại tài sản — giá trị (VNĐ)"]["o_thu"] == 1 and bg["Loại tài sản — giá trị (VNĐ)"]["gia_tri"] == "4.500.000.000", bg
assert not any(k.startswith("Thành viên — sửa vốn") for k in nh), "HÀ THỊ TRÚC MAI vốn/tỷ lệ không đổi -> không sửa"
g_cs = nh["Chủ sở hữu hưởng lợi mới: NGUYỄN VĂN C"]
assert g_cs["vao_khoi"] == "Thông tin về chủ sở hữu hưởng lợi" and g_cs["tao_moi"] and {x["ten"]: x["gia_tri"] for x in g_cs["truong"]}["Tỷ lệ sở hữu trực tiếp"] == "55", g_cs
assert any("HÀ NHẬT QUANG" in x and "tự bấm Xóa" in x for x in r["dien"]["nhac"]), r["dien"]["nhac"]      # người rời đi: nhắc tự xóa, phần mềm không xóa
print("PASS 3a: tự điền khối thành viên (Tạo mới người mới, vốn = phần nhận) và chủ sở hữu hưởng lợi; người rời đi -> nhắc tự xóa.")
ch = {x["ten"]: x for x in r["dien"]["truong"]}
assert ch["Tỉnh/Thành phố"]["gia_tri"] == "Thành phố Hồ Chí Minh" and ch["Xã/Phường/Đặc khu"]["gia_tri"] == "Phường Bình Trưng" and ch["Tỉnh/Thành phố"]["chuoi"] and ch["Xã/Phường/Đặc khu"]["chuoi"], ch
assert ch["Số nhà/đường/phố…"]["gia_tri"] == "Số nhà 91, Đường 13", ch      # địa chỉ 1 ô được tách: số nhà / xã / tỉnh
kh = [g["ten"] for g in r["dien2"]["nhom"]]
assert kh == ["Người đại diện theo pháp luật", "Thuế — Kế toán trưởng/Phụ trách kế toán", "Thuế — địa chỉ nhận thông báo & thông tin khác",
              "Thành viên mới: NGUYỄN VĂN C", "Chủ sở hữu hưởng lợi mới: NGUYỄN VĂN C"], kh      # các khối thuế đi sau người đại diện
g_kt = next(g for g in r["dien2"]["nhom"] if g["ten"].startswith("Thuế — Kế toán"))
g_kh = next(g for g in r["dien2"]["nhom"] if g["ten"].startswith("Thuế — địa chỉ"))
assert g_kt["tao_moi"] and g_kt["muc_tao_moi"] == "Kế toán trưởng/ Phụ trách kế toán" and g_kt["vao_khoi"] == "Thông tin về thuế" and g_kt["truong"][0]["gia_tri"] == "NGUYỄN THỊ KẾ", g_kt
assert any(x["ten"] == "Tổng số lao động" and x["gia_tri"] == "12" for x in g_kh["truong"]) and not g_kh["tao_moi"], g_kh
print("PASS 3c2: khối 'Thông tin về thuế' tách thành các mục (Giám đốc, Kế toán trưởng: bấm 'Tạo mới' trong đúng mục; địa chỉ & thông tin khác) đi sau người đại diện.")
print("PASS 3c: địa chỉ 1 ô tách thành Số nhà, Tỉnh/Thành, Xã/Phường (2 ô chọn nối tiếp) trong dữ liệu điền.")
print("PASS 3b: dữ liệu điền lên cổng lấy từ ô đã nhập (họ tên IN HOA, số giấy tờ), mục chưa hỗ trợ được báo.")
assert "thue" in r["thue"]["loai"] and r["thue"]["thue"]["kt_ho_ten"] == "Nguyễn Thị Kế" and r["thue"]["thue"]["lao_dong"] == "12", r["thue"]
assert r["cungDc"]["sn"] == "91 đường Số 13" and r["cungDc"]["xa"] == "Phường Bình Trưng" and r["cungDc"]["tinh"] == "Hồ Chí Minh" and r["cungDc"]["ro"] and r["cungDc"]["du"] is True and "Hồ Chí Minh" in r["cungDc"]["gh"], r["cungDc"]
print("PASS 3e: tick 'địa chỉ nhận thông báo thuế trùng địa chỉ công ty' tự điền và hiện địa chỉ công ty.")
print("PASS 3d: có mục tick 'Thay đổi thông tin đăng ký thuế' với các ô nhập, dữ liệu đưa vào hồ sơ.")
print("PASS 3: địa chỉ liên lạc người đại diện chỉ còn 1 ô.")
print("\nALL DONE")
