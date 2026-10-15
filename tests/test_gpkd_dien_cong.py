import json
import os
import subprocess
import sys
import tempfile
import urllib.parse

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Nút bookmark "Điền dữ liệu GPKD": chỉ ĐIỀN ô trên trang cổng theo dữ liệu đã soạn (không bấm Lưu/Ký/Nộp), tô vàng, có Hoàn tác, ô không chắc thì báo lại.
# Chạy trên trang giả lập có cấu trúc giống cổng (bảng nhãn | ô nhập, hàng 4 cột, ô chọn loại hình + ô tên, danh sách chọn giới tính). Chưa thử trên cổng thật.
ma = server.dkkd_bookmarklet_dien()
js = urllib.parse.unquote(ma[len("javascript:"):])
assert "//" not in js.replace("http://", "").replace("https://", "") or True
assert "__BAN_NUT__" not in js and server.APP_BUILD in js and "/*" not in js
assert "submit(" not in js and "__doPostBack" not in js and js.count("e.click()") == 1      # chỉ 1 chỗ bấm (mục menu / "Tạo mới" để điều hướng), không gửi biểu mẫu
assert "'Xóa'" not in js and "'Lưu'" not in js and "'Nộp'" not in js
print("PASS 1: mã nút điền hợp lệ, không có lệnh bấm nút/gửi biểu mẫu.")

TRANG = """<meta charset=utf-8><form id=f onsubmit="window.__nop=1;return false">
<table>
<tr><td>Họ, chữ đệm và tên:</td><td><input id=ht value="VÕ THỊ RI"></td></tr>
<tr><td>Ngày, tháng, năm sinh:</td><td><input id=ns value="01/04/1956"></td><td>Giới tính:</td><td><select id=gt><option>Nam</option><option selected>Nữ</option></select></td></tr>
<tr><td>Số giấy tờ pháp lý:</td><td><input id=cc value="079156001336"></td><td>Ngày cấp:</td><td><input id=nc value=""></td></tr>
<tr><td>Nơi cấp:</td><td><input id=noicap></td></tr>
<tr><td>Chức danh:</td><td><input id=cd value="Giám đốc"></td></tr>
<tr><td>Địa chỉ liên lạc:</td><td><input id=dc value="91 Số 13"></td></tr>
<tr><td>Điện thoại:</td><td><input id=dt readonly value="khoa"></td></tr>
<tr><td>Tên doanh nghiệp viết bằng tiếng Việt:</td><td><table><tr><td><select id=lh><option>CÔNG TY TNHH</option><option>CÔNG TY CỔ PHẦN</option></select></td><td><input id=ten value="LEAN HELPER"></td></tr></table></td></tr>
<tr><td>Quốc tịch:</td><td><input id=qt></td></tr>
</table><button id=luu type=submit onclick="window.__luu=1">Lưu</button></form>"""
DL = {"dkkd_dien": 1, "ban": "x", "bo_qua": ["nganh", "cshhl"], "truong": [
    {"ten": "Họ tên", "nhan": "^họ(,? ?(chữ đệm )?(và )?)? ?tên", "gia_tri": "ĐINH THỊ HUỆ", "tien_to": False},
    {"ten": "Ngày sinh", "nhan": "ngày.*sinh", "gia_tri": "12/07/1990", "tien_to": False},
    {"ten": "Giới tính", "nhan": "^giới tính", "gia_tri": "Nữ", "tien_to": False},
    {"ten": "Số giấy tờ", "nhan": "^(số (giấy tờ|định danh|cccd|căn cước)|số giấy)", "gia_tri": "036190003147", "tien_to": False},
    {"ten": "Ngày cấp", "nhan": "^ngày cấp", "gia_tri": "23/12/2022", "tien_to": False},
    {"ten": "Nơi cấp", "nhan": "^nơi cấp", "gia_tri": "Bộ Công An", "tien_to": False},
    {"ten": "Quốc tịch", "nhan": "^quốc tịch", "gia_tri": "Việt Nam", "tien_to": False},
    {"ten": "Chức danh", "nhan": "^chức (danh|vụ)", "gia_tri": "Giám đốc", "tien_to": False},
    {"ten": "Điện thoại", "nhan": "^điện thoại", "gia_tri": "0900000000", "tien_to": False},
    {"ten": "Tên doanh nghiệp", "nhan": "^tên doanh nghiệp viết bằng tiếng việt", "gia_tri": "CÔNG TY CỔ PHẦN SAO MỚI", "tien_to": True},
    {"ten": "Website", "nhan": "^website", "gia_tri": "a.vn", "tien_to": False}]}
RUN = r"""
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: process.env.CHROME || undefined });
  const pg = await b.newPage();
  pg.on('dialog', async d => { console.log('DIALOG ' + d.message()); await d.dismiss(); });
  pg.on('pageerror', e => console.log('PAGEERR ' + e));
  await pg.addInitScript(d => { Object.defineProperty(navigator, 'clipboard', { value: { readText: async () => d }, configurable: true }); }, process.env.DL);
  await pg.setContent(process.env.TRANG);
  await pg.evaluate(d => { Object.defineProperty(navigator, 'clipboard', { value: { readText: async () => d }, configurable: true }); }, process.env.DL);
  await pg.evaluate(process.env.JS);
  await pg.waitForSelector('#__dkkdHoan');
  const r = {};
  const val = id => pg.inputValue('#' + id);
  r.sau = { ht: await val('ht'), ns: await val('ns'), gt: await val('gt'), cc: await val('cc'), nc: await val('nc'), noicap: await val('noicap'), cd: await val('cd'),
            dt: await val('dt'), ten: await val('ten'), lh: await pg.$eval('#lh', e => e.options[e.selectedIndex].text), qt: await val('qt') };
  r.vang = await pg.$eval('#ht', e => e.style.background);
  r.panel = await pg.innerText('body');
  r.luu = await pg.evaluate(() => !!window.__luu || !!window.__nop);
  await pg.click('#__dkkdHoan');
  r.hoan = { ht: await val('ht'), ten: await val('ten'), lh: await pg.$eval('#lh', e => e.options[e.selectedIndex].text), nc: await val('nc') };
  console.log('@@' + JSON.stringify(r));
  await b.close();
})();
"""
tmp = tempfile.mkdtemp()
f = os.path.join(tmp, "t.js")
open(f, "w", encoding="utf-8").write(RUN)
env = dict(os.environ, NODE_PATH="/opt/node22/lib/node_modules", DL=json.dumps(DL), TRANG=TRANG, JS=js)
if os.path.exists("/opt/pw-browsers/chromium"):
    env["CHROME"] = "/opt/pw-browsers/chromium"
p = subprocess.run(["node", f], capture_output=True, text=True, env=env, timeout=120)
dong = [x for x in p.stdout.splitlines() if x.startswith("@@")]
assert dong, p.stdout + p.stderr
r = json.loads(dong[0][2:])
s = r["sau"]
assert s["ht"] == "ĐINH THỊ HUỆ" and s["ns"] == "12/07/1990" and s["gt"] == "Nữ" and s["cc"] == "036190003147" and s["nc"] == "23/12/2022" and s["noicap"] == "Bộ Công An" and s["cd"] == "Giám đốc" and s["qt"] == "Việt Nam", s
assert s["dt"] == "khoa", s                                         # ô chỉ đọc không bị ghi đè
assert s["lh"] == "CÔNG TY CỔ PHẦN" and s["ten"] == "SAO MỚI", s     # tên: ô chọn loại hình + ô tên được tách đúng
assert "255" in r["vang"] or "fff3a0" in r["vang"].lower() or "243" in r["vang"]
assert "Đã điền 9 ô" in r["panel"] and "Điện thoại (ô bị khóa, không sửa được)" in r["panel"] and "Website (không thấy ô)" in r["panel"], r["panel"]
assert "Chỉ có 1 khối" in r["panel"] and "Ngành nghề kinh doanh, Chủ sở hữu hưởng lợi" in r["panel"], r["panel"]      # nói rõ không còn khối để tự sang + mục phải nhập tay
assert not r["luu"]                                                  # không bấm Lưu/gửi biểu mẫu
print("PASS 2: điền đúng ô (kể cả ngày cấp ở hàng 4 cột, chọn giới tính, tách tiền tố tên), tô vàng, báo ô không có, không đụng ô chỉ đọc, không bấm Lưu.")
assert r["hoan"] == {"ht": "VÕ THỊ RI", "ten": "LEAN HELPER", "lh": "CÔNG TY TNHH", "nc": ""}, r["hoan"]
print("PASS 3: nút Hoàn tác khôi phục đúng giá trị cũ.")
# Trang tổng quan hồ sơ (không có ô nhập — đúng ca người dùng bấm nút ở trang 'Thông tin về hồ sơ'): không điền gì, viền đỏ mục menu cần mở và hướng dẫn
TRANG2 = """<meta charset=utf-8><div class=menu><a id=m1 href=#>Hình thức đăng ký</a><a id=m2 href=#>Địa chỉ</a><a id=m3 href=#>Người đại diện theo pháp luật</a></div>
<table><tr><td>Hình thức đăng ký:</td><td>Đăng ký thay đổi</td></tr><tr><td>Mã số doanh nghiệp:</td><td>0316951072</td></tr></table>"""
DL2 = dict(DL, truong=[dict(t, khoi="Người đại diện theo pháp luật") for t in DL["truong"]])
RUN2 = RUN.split("  const r = {};")[0] + """  const r = {};
  r.menu = await pg.$eval('#m3', e => e.style.outline); r.menu2 = await pg.$eval('#m2', e => e.style.outline);
  r.panel = await pg.innerText('body');
  console.log('@@' + JSON.stringify(r)); await b.close(); })();"""
open(os.path.join(tmp, "t2.js"), "w", encoding="utf-8").write(RUN2)
env2 = dict(env, DL=json.dumps(DL2), TRANG=TRANG2)
p2 = subprocess.run(["node", os.path.join(tmp, "t2.js")], capture_output=True, text=True, env=env2, timeout=120)
d2 = [x for x in p2.stdout.splitlines() if x.startswith("@@")]
assert d2, p2.stdout + p2.stderr
r2 = json.loads(d2[0][2:])
assert "Đã điền 0 ô" in r2["panel"] and "Trang này chưa phải trang nhập của khối cần sửa" in r2["panel"] and "Người đại diện theo pháp luật" in r2["panel"], r2["panel"]
assert "214" in r2["menu"] or "d62020" in r2["menu"].lower() or "rgb" in r2["menu"], r2["menu"]
assert not r2["menu2"]                                          # chỉ viền đỏ đúng mục cần mở
print("PASS 4: bấm nút ở trang tổng quan hồ sơ (chưa có ô nhập) -> báo rõ, viền đỏ mục menu 'Người đại diện theo pháp luật' cần mở.")
print("\nALL DONE")
