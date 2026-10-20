import json, os, subprocess, sys, tempfile, threading, urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Ca thật (BIOGREEN): nút "Điền dữ liệu GPKD" chỉ điền xong khối Địa chỉ rồi dừng — khối thành viên / chủ sở hữu hưởng lợi bị bỏ qua.
# Nay: người đang có mà vốn đổi -> bấm "Sửa đổi" ĐÚNG dòng người đó (không bấm Xóa, không sửa nhầm người khác) rồi điền vốn/tỷ lệ;
# người mới -> "Tạo mới" và điền. Chạy trên cổng GIẢ LẬP (chưa thử cổng thật).
MENU = '<div><a href="/dcx">Địa chỉ</a> <a href="/tv">Thông tin về thành viên</a> <a href="/cs">Thông tin về chủ sở hữu hưởng lợi</a></div>'
PAGES = {
    "/ov": MENU + "<p>Trang tổng quan hồ sơ</p>" * 5,
    "/tv": MENU + '''<table><tr><th>Tên</th><th>Số giấy tờ</th><th></th><th></th></tr>
<tr><td>DƯƠNG NGỌC BẢO CHÂU</td><td>079197029102</td><td><a href="/sua1">Sửa đổi</a></td><td><a href="/xoa1">Xóa</a></td></tr>
<tr><td>TRẦN KHẢ VY</td><td>093199002120</td><td><a href="/sua2">Sửa đổi</a></td><td><a href="/xoa2">Xóa</a></td></tr></table>
<input type=button value="Tạo mới" onclick="location='/moi'">''',
}
FORM = MENU + '''<table><tr><td>Họ tên:</td><td><input id=ht value="{ten}"></td></tr><tr><td>Ngày sinh:</td><td><input id=ns></td></tr>
<tr><td>Giới tính:</td><td><input type=radio name=g id=gn><label for=gn>Nam</label><input type=radio name=g id=gnu><label for=gnu>Nữ</label></td></tr>
<tr><td>Số giấy tờ pháp lý:</td><td><input id=cc></td></tr><tr><td>Giá trị vốn góp (VNĐ):</td><td><input id=von></td></tr>
<tr><td>Sở hữu vốn (%):</td><td><input id=tl></td></tr>
<tr><td>Tỉnh/Thành phố:</td><td><select id=tp><option></option><option>Cần Thơ</option><option>Hồ Chí Minh</option></select></td></tr></table>
<table><tr><th>Loại tài sản</th><th>Tỷ lệ (%)</th><th>Giá trị (VNĐ)</th></tr>
<tr><td>Đồng Việt Nam</td><td><input id=ts_vn_tl value="0,000"></td><td><input id=ts_vn_gt value="0,000"></td></tr>
<tr><td>Vàng</td><td><input id=ts_v_tl value="0,000"></td><td><input id=ts_v_gt value="0,000"></td></tr>
<tr><td>Tổng số</td><td><input disabled value="0"></td><td><input disabled value="0,000"></td></tr></table>
<table><tr><td>Thời điểm góp vốn:</td><td><input id=th></td></tr></table>
<div>Thông tin liên hệ Điện thoại: Fax: Website: E-mail: Nếu bạn muốn nhận kết quả hồ sơ qua email, vui lòng nhập địa chỉ email tại đây. Nếu để trống, hệ thống sẽ không gửi kết quả qua email.</div>
<input type=button value="Lưu" id=luu onclick="location='/tv'">'''
PAGES["/sua1"] = FORM.format(ten="DƯƠNG NGỌC BẢO CHÂU")
PAGES["/sua2"] = FORM.format(ten="TRẦN KHẢ VY")
PAGES["/moi"] = FORM.format(ten="")
LOG = []
LUU = {"kieu": "tai_lai"}
PAGES["/cs"] = MENU + '<table><tr><td>HÀ NHẬT QUANG</td><td><a href="/sua_cs">Sửa đổi</a></td></tr></table><input type=button value="Tạo mới" onclick="location=\'/csmoi\'">'


def trang_cs(q):
    # cổng thật: trang Tạo mới CSHHL lúc đầu CHỈ có ô "Loại chủ sở hữu hưởng lợi"; chọn xong cổng gửi lại trang mới hiện các ô thông tin
    loai = q.get("loai", [""])[0]
    ops = "".join(f"<option{' selected' if x == loai else ''}>{x}</option>" for x in ["Loại chủ sở hữu hưởng lợi", "Cá nhân có quyền chi phối", "Cá nhân sở hữu trực tiếp hoặc gián tiếp từ 25% vốn điều lệ trở lên"])
    o = f'<form method=get action="/csmoi"><table><tr><td>Loại chủ sở hữu hưởng lợi:</td><td><select id=loai name=loai onchange="this.form.submit()">{ops}</select></td></tr>'
    if loai and loai != "Loại chủ sở hữu hưởng lợi":
        o += '<tr><td>Họ tên:</td><td><input id=ht></td></tr><tr><td>Tỷ lệ sở hữu vốn điều lệ trực tiếp (%):</td><td><input id=tt></td></tr>'
    return MENU + o + '</table><input type=button value="Lưu"></form>'


def trang_dc():
    # khối Địa chỉ của cổng thật: sau Lưu VẪN Ở LẠI cùng trang, các ô vẫn mở
    bam = {"tai_lai": "location='/dcx?da_luu=1'", "khoa": "this.disabled=true", "khong": ""}[LUU["kieu"]]
    return MENU + f'''<table><tr><td>Số nhà/đường/phố/tổ/xóm/ấp/thôn:</td><td><input id=sn></td></tr><tr><td>Điện thoại:</td><td><input id=dt></td></tr></table>
<input type=button value="Lưu" id=luu onclick="{bam}"><input type=button value="Trở về">'''


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        LOG.append(self.path)
        duong = urllib.parse.urlparse(self.path).path
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        body = ("<meta charset=utf-8>" + (trang_dc() if duong == "/dcx" else trang_cs(q) if duong == "/csmoi" else PAGES.get(duong, "404"))).encode("utf-8")
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(body)

    def log_message(self, *a):
        pass


srv = HTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
K = "Thông tin về thành viên"
T = lambda ten, nhan, v: {"ten": ten, "nhan": nhan, "gia_tri": v, "tien_to": False, "khoi": K, "chuoi": False}
VON = [T("Phần vốn góp", "(giá trị|phần) vốn góp|^vốn góp", "2.550.000.000"), T("Sở hữu vốn (%)", "^(tỷ lệ|sở hữu vốn)", "51"),
       dict(T("Loại tài sản — tỷ lệ (%)", "^đồng việt nam", "100"), bang="^đồng việt nam", o_thu=0),
       dict(T("Loại tài sản — giá trị (VNĐ)", "^đồng việt nam", "2.550.000.000"), bang="^đồng việt nam", o_thu=1)]
SUA = {"dkkd_dien": 1, "ban": "x", "nhom": [{"ten": "Thành viên — sửa vốn: TRẦN KHẢ VY", "vao_khoi": K, "tao_moi": False,
       "sua_dong": {"ten": "Trần Khả Vy", "cccd": "093199002120"}, "truong": VON}], "bo_qua": [], "nhac": ["Thành viên rời công ty: X — bạn tự bấm Xóa"]}
SUA["truong"] = SUA["nhom"][0]["truong"]
MOI = {"dkkd_dien": 1, "ban": "x", "nhom": [{"ten": "Thành viên mới: LÊ D", "vao_khoi": K, "tao_moi": True, "truong": [
       T("Họ tên", "^(họ(,? ?(chữ đệm )?(và )?)? ?tên|tên thành viên)", "LÊ D"), T("Ngày sinh", "ngày.*sinh", "01/02/1990"), T("Giới tính", "^giới tính", "Nữ"),
       T("Số giấy tờ", "^(số (giấy tờ|định danh)|số giấy)", "012345678901"), dict(T("Tỉnh", "^tỉnh\\/thành", "TP.Hồ Chí Minh"), chuoi=True)] + VON + [T("Thời hạn", "^(thời (điểm|hạn) góp vốn)", "19/10/2026")]}], "bo_qua": []}
MOI["truong"] = MOI["nhom"][0]["truong"]
js = urllib.parse.unquote(server.dkkd_bookmarklet_dien()[len("javascript:"):])
RUN = r"""
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: process.env.CHROME || undefined });
  const pg = await (await b.newContext()).newPage();
  pg.on('dialog', async d => { console.log('DIALOG ' + d.message()); await d.dismiss(); });
  await pg.goto('http://127.0.0.1:' + process.env.PORT + '/ov');
  await pg.evaluate(d => { Object.defineProperty(navigator, 'clipboard', { value: { readText: async () => d }, configurable: true }); }, process.env.DL);
  await pg.evaluate(process.env.JS);
  const w = await (await pg.waitForSelector('#__dkkdKhung iframe', { timeout: 60000 })).contentFrame();
  await w.waitForSelector('#__dkkdHoan', { timeout: 60000 });
  const v = id => w.inputValue('#' + id);
  const r = { tp: await w.$eval('#tp', e => e.value), tsTl: await v('ts_vn_tl'), tsGt: await v('ts_vn_gt'), vangTl: await v('ts_v_tl'), url: w.url(), ht: await v('ht'), ns: await v('ns'), cc: await v('cc'), von: await v('von'), tl: await v('tl'), th: await v('th'),
    nu: await w.$eval('#gnu', e => e.checked), panel: await w.innerText('#__dkkdHoan >> xpath=../..') };
  console.log('@@' + JSON.stringify(r));
  await b.close();
})();
"""
tmp = tempfile.mkdtemp(); f = os.path.join(tmp, "t.js"); open(f, "w", encoding="utf-8").write(RUN)
_bm = os.path.join(tmp, "bm.js"); open(_bm, "w", encoding="utf-8").write(js)
_ck = subprocess.run(["node", "--check", _bm], capture_output=True, text=True)
assert _ck.returncode == 0, "nút bookmark (mã gộp 1 dòng) phải hợp lệ — không dùng chú thích // cuối dòng: " + _ck.stderr[-300:]


def chay(dl):
    env = dict(os.environ, NODE_PATH="/opt/node22/lib/node_modules", DL=json.dumps(dl), JS=js, PORT=str(srv.server_address[1]))
    if os.path.exists("/opt/pw-browsers/chromium"):
        env["CHROME"] = "/opt/pw-browsers/chromium"
    p = subprocess.run(["node", f], capture_output=True, text=True, env=env, timeout=180)
    d = [x for x in p.stdout.splitlines() if x.startswith("@@")]
    assert d, p.stdout + p.stderr
    return json.loads(d[0][2:])


r = chay(SUA)
assert r["url"].endswith("/sua2") and r["ht"] == "TRẦN KHẢ VY", r                         # đúng dòng người cần sửa
assert r["von"] == "2.550.000.000" and r["tl"] == "51", r
assert not any(x.startswith("/xoa") for x in LOG) and "/sua1" not in LOG, LOG              # không bấm Xóa, không mở người khác
assert "tự bấm Xóa" in r["panel"], r["panel"]
print("PASS 1: thành viên đang có đổi vốn -> bấm 'Sửa đổi' đúng dòng (theo số giấy tờ), điền vốn/tỷ lệ; không bấm Xóa; hiện nhắc việc tự làm.")
r = chay(MOI)
assert r["url"].endswith("/moi") and r["ht"] == "LÊ D" and r["ns"] == "01/02/1990" and r["cc"] == "012345678901" and r["nu"], r
assert r["von"] == "2.550.000.000" and r["tl"] == "51" and r["th"] == "19/10/2026", r
assert r["tsTl"] == "100" and r["tsGt"] == "2.550.000.000" and r["vangTl"] == "0,000", r          # bảng loại tài sản: đúng dòng Đồng Việt Nam
assert r["tp"] == "Hồ Chí Minh", r                                                                 # "TP.Hồ Chí Minh" (không cách) khớp lựa chọn "Hồ Chí Minh"
assert "không thấy" not in r["panel"], r["panel"]
assert not any(x.startswith("/xoa") for x in LOG)
print("PASS 2: thành viên mới -> 'Tạo mới' trong khối thành viên và điền đủ họ tên, ngày sinh, giới tính, số giấy tờ, vốn, sở hữu vốn (%), bảng loại tài sản (Đồng Việt Nam: 100% / giá trị), tỉnh 'TP.Hồ Chí Minh', thời hạn.")

# Khối Địa chỉ đã Lưu nhưng cổng ở lại cùng trang (ô vẫn mở) -> vẫn phải tự sang khối kế tiếp (Thành viên mới)
G_DC = {"ten": "Địa chỉ", "vao_khoi": "Địa chỉ", "tao_moi": False, "truong": [{"ten": "Số nhà", "nhan": "^số nhà", "gia_tri": "Số 200", "tien_to": False, "khoi": "Địa chỉ", "chuoi": False}]}
HAI = {"dkkd_dien": 1, "ban": "x", "nhom": [G_DC, MOI["nhom"][0]], "truong": G_DC["truong"] + MOI["truong"], "bo_qua": []}
RUN2 = RUN.split("  await pg.evaluate(process.env.JS);")[0] + r"""
  await pg.evaluate(process.env.JS);
  const w = await (await pg.waitForSelector('#__dkkdKhung iframe', { timeout: 60000 })).contentFrame();
  await w.waitForSelector('#__dkkdHoan', { timeout: 60000 });
  const r = { sn: await w.inputValue('#sn') };
  await new Promise(ok => setTimeout(ok, 2500));
  r.truoc = w.url();
  await w.click('#luu');
  await new Promise(ok => setTimeout(ok, 5000));
  r.sau5s = w.url();
  if (process.env.EP) { await w.click('#__dkkdSang'); }
  await w.waitForURL(/\/moi$/, { timeout: 60000 });
  await w.waitForSelector('#__dkkdHoan', { timeout: 60000 });
  r.ht = await w.inputValue('#ht');
  console.log('@@' + JSON.stringify(r));
  await b.close();
})();
"""
f2 = os.path.join(tmp, "t2.js"); open(f2, "w", encoding="utf-8").write(RUN2)


def chay2(kieu, ep=False):
    LUU["kieu"] = kieu
    env = dict(os.environ, NODE_PATH="/opt/node22/lib/node_modules", DL=json.dumps(HAI), JS=js, PORT=str(srv.server_address[1]))
    if ep:
        env["EP"] = "1"
    if os.path.exists("/opt/pw-browsers/chromium"):
        env["CHROME"] = "/opt/pw-browsers/chromium"
    p = subprocess.run(["node", f2], capture_output=True, text=True, env=env, timeout=240)
    d = [x for x in p.stdout.splitlines() if x.startswith("@@")]
    assert d, p.stdout + p.stderr
    return json.loads(d[0][2:])


for kieu in ("tai_lai", "khoa"):
    r = chay2(kieu)
    assert r["sn"] == "Số 200" and r["truoc"].endswith("/dcx") and r["ht"] == "LÊ D", (kieu, r)
print("PASS 3: Lưu xong cổng ở lại trang Địa chỉ (tải lại cùng trang / nút Lưu bị khóa) -> tự sang khối Thành viên mới và điền.")
r = chay2("khong", ep=True)
assert r["sau5s"].endswith("/dcx") and r["ht"] == "LÊ D", r
print("PASS 4: bấm Lưu mà không có dấu hiệu đã lưu -> đứng yên; bấm 'Đã Lưu xong → sang khối kế tiếp' thì sang ngay.")
KC = "Thông tin về chủ sở hữu hưởng lợi"
CS = {"dkkd_dien": 1, "ban": "x", "ma_nut": "khac_ma_nut", "nhom": [{"ten": "CSHHL mới", "vao_khoi": KC, "tao_moi": True, "truong": [
      {"ten": "Loại chủ sở hữu hưởng lợi", "nhan": "^loại chủ sở hữu hưởng lợi", "gia_tri": "sở hữu trực tiếp || 25% || vốn điều lệ || cá nhân", "tien_to": False, "khoi": KC, "chuoi": True},
      {"ten": "Họ tên", "nhan": "^(họ(,? ?(chữ đệm )?(và )?)? ?tên)", "gia_tri": "LÊ D", "tien_to": False, "khoi": KC, "chuoi": False},
      {"ten": "Tỷ lệ sở hữu trực tiếp", "nhan": "^tỷ lệ.*trực tiếp", "gia_tri": "55", "tien_to": False, "khoi": KC, "chuoi": False}]}], "bo_qua": []}
CS["truong"] = CS["nhom"][0]["truong"]
RUN3 = RUN.split("  const v = id =>")[0] + r"""
  const r = { loai: await w.$eval('#loai', e => e.options[e.selectedIndex].text), ht: await w.inputValue('#ht'), tt: await w.inputValue('#tt'),
    panel: await w.innerText('#__dkkdHoan >> xpath=../..'), tabs: pg.context().pages().length };
  console.log('@@' + JSON.stringify(r));
  await b.close();
})();
"""
f3 = os.path.join(tmp, "t3.js"); open(f3, "w", encoding="utf-8").write(RUN3)
env = dict(os.environ, NODE_PATH="/opt/node22/lib/node_modules", DL=json.dumps(CS), JS=js, PORT=str(srv.server_address[1]))
if os.path.exists("/opt/pw-browsers/chromium"):
    env["CHROME"] = "/opt/pw-browsers/chromium"
p = subprocess.run(["node", f3], capture_output=True, text=True, env=env, timeout=240)
d = [x for x in p.stdout.splitlines() if x.startswith("@@")]
assert d, p.stdout + p.stderr
r = json.loads(d[0][2:])
assert r["loai"].startswith("Cá nhân sở hữu trực tiếp") and r["ht"] == "LÊ D" and r["tt"] == "55", r
assert "không thấy ô" not in r["panel"] and r["tabs"] == 1, r          # điền ngay trong tab đang mở (khung phủ), không mở thêm tab
assert "Nút bookmark này đã CŨ" in r["panel"], r["panel"]                 # dữ liệu từ phần mềm có mã nút khác -> nhắc cập nhật dấu trang
print("PASS 5: CSHHL: chọn 'Loại chủ sở hữu hưởng lợi' trước, cổng hiện ô thì điền tiếp họ tên/tỷ lệ; chỉ 1 tab; nhắc khi nút bookmark cũ.")
import re as _re
_m = server.dkkd_ma_nut_dien()
assert _re.fullmatch(r"[0-9a-f]{10}", _m) and server.dkkd_bookmarklet_dien_get()["ma_nut"] == _m
print("PASS 6: phần mềm biết mã nút hiện tại để phát hiện dấu trang cũ.")
HAI2 = {"dkkd_dien": 1, "ban": "x", "nhom": [MOI["nhom"][0], CS["nhom"][0]], "truong": MOI["truong"] + CS["truong"], "bo_qua": []}
RUN4 = RUN.split("  const v = id =>")[0] + r"""
  await new Promise(ok => setTimeout(ok, 2500));
  await w.click('#luu');
  await w.waitForURL(/\/csmoi/, { timeout: 60000 });
  await w.waitForSelector('#__dkkdHoan', { timeout: 60000 });
  console.log('@@' + JSON.stringify({ ht: await w.inputValue('#ht') }));
  await b.close();
})();
"""
f4 = os.path.join(tmp, "t4.js"); open(f4, "w", encoding="utf-8").write(RUN4)
p = subprocess.run(["node", f4], capture_output=True, text=True, env=dict(env, DL=json.dumps(HAI2)), timeout=240)
d = [x for x in p.stdout.splitlines() if x.startswith("@@")]
assert d and json.loads(d[0][2:])["ht"] == "LÊ D", p.stdout + p.stderr
print("PASS 7: lời hướng dẫn email luôn hiện trên trang thành viên không bị coi là lỗi -> Lưu xong tự sang khối chủ sở hữu hưởng lợi.")
print("ALL DONE")
