import json, os, subprocess, sys, tempfile, threading, urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Khối "Người đại diện theo pháp luật" / "Thông tin về thành viên": có nhập dữ liệu mới thì nút điền TỰ XÓA các dòng CŨ của đúng những người được thay
# (khớp họ tên / số giấy tờ; cổng hỏi xác nhận thì tự đồng ý), rồi mới "Tạo mới" và điền. Người khác trong danh sách giữ nguyên. Không bấm Lưu. Cổng GIẢ LẬP (có danh sách + nút Xóa từng dòng).
ST = {}
LOG = []
MENU = '<div id=menu><a href="/khoi?k=dd">Người đại diện theo pháp luật</a> <a href="/khoi?k=tv">Thông tin về thành viên</a></div>'
KHOI = {"dd": "Người đại diện theo pháp luật", "tv": "Thông tin về thành viên"}


def danh_sach(k):
    if k not in ST:
        return MENU + "<p>Trang khác</p>"
    hang = "".join(f'<tr><td>{x[0]}</td><td>{x[1]}</td><td>01/01/2020</td><td>Giám đốc</td><td><a href="/sua?k={k}&i={i}">Sửa đổi</a></td>'
                   f'<td><a href="/xoa?k={k}&i={i}" onclick="return confirm(\'Bạn có chắc chắn muốn xóa?\')">Xóa</a></td></tr>' for i, x in enumerate(ST[k]))
    return (MENU + f"<h3>{KHOI[k]}</h3><table><tr><th>Họ và tên</th><th>Số Giấy tờ pháp lý của cá nhân</th><th>Ngày cấp</th><th>Chức vụ</th><th></th><th></th></tr>{hang}</table>"
            f'<p>Danh sách của khối, đủ dài hơn tám mươi ký tự để nút điền nhận ra trang đã tải xong.</p><input type=button value="Tạo mới" onclick="location=\'/tao?k={k}\'">')


FORM = ('<table><tr><td>Họ tên:</td><td><input id=ht></td></tr><tr><td>Số Giấy tờ pháp lý của cá nhân:</td><td><input id=cc></td></tr></table>'
        '<p>Trang nhập, đủ dài hơn tám mươi ký tự để nút điền nhận ra trang đã tải xong.</p><input type=button id=luu value="Lưu">')


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        k = (q.get("k") or [""])[0]
        LOG.append(u.path + ("?" + u.query if u.path in ("/xoa", "/luu") else ""))
        if u.path == "/xoa" and not ST.get("tu_choi"):
            del ST[k][int(q["i"][0])]
        body = {"/home": MENU + "<p>Trang chính hồ sơ, đủ dài hơn tám mươi ký tự để nút điền nhận ra trang đã tải xong.</p>", "/tao": MENU + FORM}.get(u.path) or danh_sach(k)
        b = ("<meta charset=utf-8>" + body).encode("utf-8")
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(b)

    def log_message(self, *a):
        pass


srv = HTTPServer(("127.0.0.1", 0), H)
cong = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()


def tr(khoi, ten, so):
    return [{"ten": "Họ tên", "nhan": "^họ(,? ?(chữ đệm )?(và )?)? ?tên", "gia_tri": ten, "tien_to": False, "khoi": khoi},
            {"ten": "Số giấy tờ", "nhan": "^(số (giấy tờ|định danh|cccd|căn cước)|số giấy)", "gia_tri": so, "tien_to": False, "khoi": khoi}]


js = urllib.parse.unquote(server.dkkd_bookmarklet_dien()[len("javascript:"):])
RUN = r"""
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: process.env.CHROME || undefined });
  const pg = await (await b.newContext()).newPage();
  const ds = []; pg.on('dialog', async d => { ds.push(d.message().slice(0, 50)); await d.dismiss(); });
  await pg.goto('http://127.0.0.1:' + process.env.PORT + '/home');
  await pg.evaluate(d => { Object.defineProperty(navigator, 'clipboard', { value: { readText: async () => d }, configurable: true }); }, process.env.DL);
  await pg.evaluate(process.env.JS);
  const r = {};
  const het = Date.now() + 40000; let w = null;
  while (Date.now() < het && !w) {
    await new Promise(ok => setTimeout(ok, 500));
    const hk = await pg.$('#__dkkdKhung iframe'); if (hk) { w = await hk.contentFrame(); continue; }
    for (const q of pg.context().pages()) if (q !== pg) w = q;
  }
  if (w) try {
    await w.waitForSelector('#__dkkdHoan', { timeout: 30000 });
    r.ht = await w.inputValue('#ht'); r.cc = await w.inputValue('#cc');
  } catch (e) { r.loi = 1; }
  if (!r.ht) await new Promise(ok => setTimeout(ok, 4000));
  r.ds = ds;
  console.log('@@' + JSON.stringify(r));
  await b.close();
})();
"""
tmp = tempfile.mkdtemp(); f = os.path.join(tmp, "t.js"); open(f, "w", encoding="utf-8").write(RUN)


def chay(nhom, ds_dau, k, tu_choi=False):
    ST.clear(); ST.update(ds_dau); ST["tu_choi"] = tu_choi; LOG.clear()
    du_lieu = {"dkkd_dien": 1, "ban": "x", "nhom": nhom, "truong": [t for g in nhom for t in g["truong"]], "bo_qua": []}
    env = dict(os.environ, NODE_PATH="/opt/node22/lib/node_modules", DL=json.dumps(du_lieu), JS=js, PORT=str(cong))
    if os.path.exists("/opt/pw-browsers/chromium"):
        env["CHROME"] = "/opt/pw-browsers/chromium"
    p = subprocess.run(["node", f], capture_output=True, text=True, env=env, timeout=240)
    d = [x for x in p.stdout.splitlines() if x.startswith("@@")]
    assert d, p.stdout + p.stderr
    return json.loads(d[0][2:])


# 1) Người đại diện: danh sách có 2 dòng của cùng 1 người (CCCD cũ + CCCD mới) và 1 người khác -> xóa 2 dòng của người đó, giữ người khác, rồi Tạo mới và điền
dd = {"ten": "Người đại diện", "vao_khoi": KHOI["dd"], "tao_moi": True, "xoa_cu": [{"ten": "TRẦN ĐỨC HOÀNG", "cccd": "075090020672"}], "truong": tr(KHOI["dd"], "TRẦN ĐỨC HOÀNG", "075090020672")}
r = chay([dd], {"dd": [["TRẦN ĐỨC HOÀNG", "312635811"], ["TRẦN ĐỨC HOÀNG", "075090020672"], ["LÊ VĂN KHÁC", "111222333444"]]}, "dd")
assert ST["dd"] == [["LÊ VĂN KHÁC", "111222333444"]], ST["dd"]
assert sum(1 for x in LOG if x.startswith("/xoa")) == 2 and "/tao" in LOG[-3:] and not any(x.startswith("/luu") for x in LOG), LOG
assert r.get("ht") == "TRẦN ĐỨC HOÀNG" and r.get("cc") == "075090020672" and r["ds"] == [], r          # không hiện hộp xác nhận (tự đồng ý), điền đúng form trống
print("PASS 1: Người đại diện — tự xóa 2 dòng cũ của người được thay, giữ người khác, rồi Tạo mới và điền; không bấm Lưu.")

# 2) Thành viên: nhóm CHỈ XÓA người rời công ty (không có ô điền) tự sang nhóm Tạo mới thành viên mới
tv_xoa = {"ten": "Xóa dòng cũ của thành viên rời công ty", "vao_khoi": KHOI["tv"], "tao_moi": False, "xoa_cu": [{"ten": "NGUYỄN THỊ RỜI", "cccd": "079111111111"}], "truong": []}
tv_moi = {"ten": "Thành viên mới", "vao_khoi": KHOI["tv"], "tao_moi": True, "truong": tr(KHOI["tv"], "TRẦN VĂN MỚI", "079333333333")}
r = chay([tv_xoa, tv_moi], {"tv": [["NGUYỄN THỊ RỜI", "079111111111"], ["PHẠM VĂN Ở LẠI", "079222222222"]]}, "tv")
assert ST["tv"] == [["PHẠM VĂN Ở LẠI", "079222222222"]], ST["tv"]
assert r.get("ht") == "TRẦN VĂN MỚI" and r.get("cc") == "079333333333" and r["ds"] == [], (r, LOG)
print("PASS 2: Thành viên — xóa dòng cũ của người rời công ty (giữ thành viên ở lại), tự sang nhóm thêm thành viên mới.")

# 3) Cổng không cho xóa: thử lại tối đa 2 lần rồi báo, KHÔNG Tạo mới (không để trùng)
r = chay([dd], {"dd": [["TRẦN ĐỨC HOÀNG", "312635811"]]}, "dd", tu_choi=True)
assert any("Chưa xóa được dòng cũ" in x for x in r["ds"]) and "/tao" not in LOG and sum(1 for x in LOG if x.startswith("/xoa")) <= 3, (r, LOG)
print("PASS 3: cổng không xóa được -> báo người dùng tự xóa, không Tạo mới (không để trùng).")

# 4) Nhóm KHÔNG có xoa_cu (hành vi cũ): không bấm Xóa dòng nào
dd2 = dict(dd); dd2.pop("xoa_cu")
r = chay([dd2], {"dd": [["TRẦN ĐỨC HOÀNG", "312635811"]]}, "dd")
assert ST["dd"] == [["TRẦN ĐỨC HOÀNG", "312635811"]] and not any(x.startswith("/xoa") for x in LOG), (ST, LOG)
print("PASS 4: nhóm không yêu cầu xóa thì không bấm Xóa dòng nào.")

# 5) Dữ liệu sinh ra từ phần mềm: đổi người đại diện / chế độ cập nhật / thành viên rời & nhập lại vốn (công ty 2 thành viên) đều có danh sách xoa_cu
GEN = r"""
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
  const kq = {};
  // a) chế độ cập nhật, công ty từ 2 thành viên: người đại diện + thành viên nhập lại
  await pg.evaluate(() => {
    document.getElementById('ssL_cap_nhat').checked = true;
    ssHienTrang = { dai_dien: [{ ho_ten: 'PHAM THỊ THÚY HẰNG', chuc_danh: 'Giám đốc', cccd: '027181000304' }],
      thanh_vien: [{ ho_ten: 'NGUYÊN THÀNH TRUNG', cccd: '001079024521', von: '1000000000' }, { ho_ten: 'PHAM THỊ THÚY HẰNG', cccd: '027181000304', ngay_sinh: '01/01/1981', von: '1000000000' }] };
    ssTv.ht = []; ssCnLayNguoiHt(); ssCn.dia_chi = { so_nha: '12 Lê Lợi', xa: 'Phường Bến Nghé', tinh: 'Thành phố Hồ Chí Minh' };
  });
  kq.capnhat = await pg.evaluate('ssTaoDuLieuDien().nhom.map(g => ({ ten: g.ten, xoa_cu: g.xoa_cu || null }))');
  console.log('@@' + JSON.stringify({ kq, loi }));
  await b.close();
})();
"""
f2 = os.path.join(tmp, "g.js"); open(f2, "w", encoding="utf-8").write(GEN)
env = dict(os.environ, NODE_PATH="/opt/node22/lib/node_modules", INDEX=os.path.join(_REPO_ROOT, "static", "index.html"))
if os.path.exists("/opt/pw-browsers/chromium"):
    env["CHROME"] = "/opt/pw-browsers/chromium"
p = subprocess.run(["node", f2], capture_output=True, text=True, env=env, timeout=120)
d = [x for x in p.stdout.splitlines() if x.startswith("@@")]
assert d, p.stdout + p.stderr
g = json.loads(d[0][2:]); assert not [e for e in g["loi"] if "Failed to fetch" not in e], g["loi"]
nh = {x["ten"]: x["xoa_cu"] for x in g["kq"]["capnhat"]}
assert nh["Cập nhật người đại diện theo pháp luật (Tạo mới): PHAM THỊ THÚY HẰNG"] == [{"ten": "PHAM THỊ THÚY HẰNG", "cccd": "027181000304"}], nh
tvs = {k: v for k, v in nh.items() if k.startswith("Cập nhật thành viên")}
assert len(tvs) == 2 and all(v and v[0]["ten"] and v[0]["cccd"] for v in tvs.values()), tvs
assert nh["Cập nhật địa chỉ trụ sở chính"] is None
print("PASS 5: dữ liệu điền sinh từ phần mềm có xoa_cu cho người đại diện + thành viên (cập nhật); khối địa chỉ không xóa gì.")
