import json, os, subprocess, sys, tempfile, threading, urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Tiện ích thống kê trên trang GIẢ LẬP theo ảnh Phiếu 01/DN-ĐP (chưa thử trên gtsphcm.cosis.vn thật): trang đăng nhập -> điền MST/mật khẩu + bấm Đăng nhập;
# trang phiếu -> điền số lao động, số ngày, tình hình, người ghi phiếu...; KHÔNG bấm Lưu tạm/Hoàn tất; ô có sẵn không bị dùng nhầm.
LOG = []
LOGIN = "<h3>Đăng nhập</h3><input id=u placeholder='Tài khoản'><input id=p type=password><button id=dn onclick=\"fetch('/log/dn');location.href='/Phieu1CN_DN'\">Đăng nhập</button>"
PHIEU = """<h2>PHIẾU THU THẬP</h2><table>
<tr><td>5. Số lao động:</td><td>- 5.1 Thời điểm cuối tháng trước:</td><td><input id=ld1> (Người)</td><td>Trong đó: lao động tại phường xã: <input id=ld1x></td></tr>
<tr><td></td><td>- 5.2 Dự kiến thời điểm cuối tháng báo cáo:</td><td><input id=ld2> (Người)</td></tr>
<tr><td colspan=2>8. Số ngày hoạt động trong tháng trước tháng báo cáo của doanh nghiệp:</td><td><input id=ngay> Ngày</td></tr></table>
<div>9. Tình hình sản xuất trong tháng (ghi tóm tắt những khó khăn, thuận lợi chính):</div><textarea id=th></textarea>
<table><tr><td>Người ghi phiếu:</td><td><input id=ng></td><td>Ngày ghi phiếu:</td><td><select id=ngay_gp><option></option></select></td></tr>
<tr><td>Chức vụ:</td><td><input id=cv></td><td>Điện thoại ghi phiếu:</td><td><input id=dt></td></tr></table>
<div>3. Ngành hoạt động chính: <input id=nganh value="Chế biến"> - Mã ngành hoạt động chính <input id=manganh value="10209"></div>
<div id=m6><div>6. Sản xuất, tiêu thụ, tồn kho sản phẩm:</div><table id=t6><tr><th>Tên sản phẩm</th><th>Tra cứu</th><th>Mã</th></tr></table><button onclick="them6()">Thêm</button></div>
<div id=m7><div>7. Doanh thu thuần của hoạt động sản xuất công nghiệp:</div><table id=t7><tr><th>Tên ngành</th><th>Mã</th><th>Thực hiện tháng trước</th></tr></table><button onclick="them7()">Thêm</button></div>
<div id=pop style="display:none"><div>TRA CỨU MÃ SẢN PHẨM CÔNG NGHIỆP</div><div>Mô tả: <input type=text id=mota> <button onclick="mo()">Mở danh sách</button></div><table id=kq></table></div>
<script>
let hang6=null;
function them7(){const r=document.getElementById('t7').insertRow();r.innerHTML="<td><select id=s7><option></option><option value=05>05 Khai thác than</option><option value=10>10 Sản xuất chế biến thực phẩm</option><option value=32>32 Công nghiệp chế biến, chế tạo khác</option></select></td><td></td><td><input id=v7></td>";LOGJS('them7')}
function them6(){const r=document.getElementById('t6').insertRow();r.innerHTML="<td></td><td><button onclick='hop(this)'>Mã SP</button></td><td>"+[1,2,3,4,5,6,7].map(i=>"<input class=c"+i+" style='width:40px'>").join('')+"</td>";}
function hop(b){hang6=b.closest('tr');document.getElementById('pop').style.display='block'}
function mo(){const t=document.getElementById('kq');t.innerHTML=[["10209110","Thủy hải sản đã được chế biến","Tấn"],["10209121","Sản phẩm từ cá tra phi lê","Tấn"],["10209210","Dịch vụ chuẩn bị","Triệu đồng"]].map(x=>"<tr><td><a href='#' onclick='chon(this);return false'>✎</a></td><td>"+x[0]+"</td><td>"+x[1]+"</td><td>"+x[2]+"</td></tr>").join('')}
function chon(a){const tds=a.closest('tr').querySelectorAll('td');hang6.cells[0].textContent=tds[2].textContent+' ['+tds[1].textContent+']';document.getElementById('pop').style.display='none'}
function LOGJS(x){fetch('/log/'+x)}
</script>
<button id=luu onclick="fetch('/log/luu')">Lưu tạm</button><button id=ht onclick="fetch('/log/hoantat')">Hoàn tất phiếu</button>"""
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        p = urllib.parse.urlparse(self.path).path; LOG.append(p)
        b = ("<meta charset=utf-8><body>" + {"/login": LOGIN, "/Phieu1CN_DN": PHIEU}.get(p, "ok")).encode("utf-8")
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(b)
    def log_message(self, *a): pass
srv = HTTPServer(("127.0.0.1", 0), H); cong = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
DATA = {"user": "0315502878", "pass": "mk-123", "phieu": {"nguoi_ghi": "Nguyễn A", "chuc_vu": "Kế toán", "dien_thoai": "0909123456", "lao_dong_cuoi_thang_truoc": "3", "lao_dong_du_kien": "3", "so_ngay_hoat_dong": "22", "tinh_hinh": "Ổn định"},
        "so_lieu": {"thang_so_lieu": 10, "nam_so_lieu": 2026, "so_hd": 2, "doanh_thu_trieu": 15.5, "sp": [{"ten": "Cá tra phi lê", "dvt": "Kg", "sl": 150, "gia_tri_trieu": 10}], "thieu_chi_tiet": 0}, "sp_map": {"Cá tra phi lê": "10209121"}}
STUB = r"""
(() => { const P = 'tkstate';
  window.chrome = { runtime: { lastError: null, sendMessage: (m, cb) => { setTimeout(() => {
    if (m.loai === 'tk-lay') { if (m.kt === 'MA1') { localStorage[P] = JSON.stringify(window.__DATA); cb(window.__DATA) } else cb({ loi: 'mã hết hạn' }) }
    else if (m.loai === 'tk-giu') { localStorage[P] = JSON.stringify(m.d); cb({}) }
    else if (m.loai === 'tk-cho') cb(localStorage[P] ? JSON.parse(localStorage[P]) : {});
    else if (m.loai === 'tk-xoa') { delete localStorage[P]; cb({}) } else cb({}) }, 5) } } };
})();
"""
RUN = r"""
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: process.env.CHROME || undefined });
  const ctx = await b.newContext(); await ctx.addInitScript('window.__DATA=' + process.env.DATA + ';' + process.env.STUB);
  const pg = await ctx.newPage(); const U = 'http://127.0.0.1:' + process.env.PORT; const kq = {};
  await pg.goto(U + '/login#ketoan-thongke&kt=MA1&p=8686'); await pg.addScriptTag({ content: process.env.JS });
  await pg.waitForURL(/Phieu1CN_DN$/, { timeout: 15000 }).catch(() => {}); kq.url = pg.url();
  await pg.addScriptTag({ content: process.env.JS });                      // trang phiếu nạp lại: tiện ích chạy lại với dữ liệu trong bộ nhớ phiên
  await pg.waitForSelector('#__ketoanTk', { timeout: 15000 }).catch(() => {}); await pg.waitForTimeout(4000);
  await pg.click('#__ketoanTkBang'); await pg.waitForFunction(() => /Xong/.test(document.getElementById('__ketoanTkLog').innerText), null, { timeout: 40000 }).catch(() => {});
  kq.log = await pg.textContent('#__ketoanTkLog'); kq.b7 = await pg.inputValue('#s7').catch(() => ''); kq.v7 = await pg.inputValue('#v7').catch(() => ''); kq.t6 = await pg.textContent('#t6'); kq.c3 = await pg.inputValue('.c3').catch(() => ''); kq.c4 = await pg.inputValue('.c4').catch(() => '');
  const v = id => pg.inputValue('#' + id);
  kq.v = { ld1: await v('ld1'), ld1x: await v('ld1x'), ld2: await v('ld2'), ngay: await v('ngay'), th: await v('th'), ng: await v('ng'), cv: await v('cv'), dt: await v('dt') };
  kq.khung = await pg.textContent('#__ketoanTk').catch(() => '');
  console.log('@@' + JSON.stringify(kq)); await b.close();
})();
"""
f = os.path.join(tempfile.mkdtemp(), "t.js"); open(f, "w", encoding="utf-8").write(RUN)
js = open(os.path.join(_REPO_ROOT, "tien_ich_chrome", "xuat_don_tmdt", "thong_ke.js"), encoding="utf-8").read()
env = dict(os.environ, NODE_PATH="/opt/node22/lib/node_modules", JS=js, STUB=STUB, DATA=json.dumps(DATA), PORT=str(cong))
if os.path.exists("/opt/pw-browsers/chromium"): env["CHROME"] = "/opt/pw-browsers/chromium"
p = subprocess.run(["node", f], capture_output=True, text=True, env=env, timeout=200)
d = [x for x in p.stdout.splitlines() if x.startswith("@@")]
assert d, p.stdout + p.stderr
r = json.loads(d[0][2:]); print(r)
assert "/log/dn" in LOG, "phải tự bấm Đăng nhập (không có ô mã xác nhận)"
assert r["url"].endswith("/Phieu1CN_DN"), r
assert r["v"] == {"ld1": "3", "ld1x": "", "ld2": "3", "ngay": "22", "th": "Ổn định", "ng": "Nguyễn A", "cv": "Kế toán", "dt": "0909123456"}, r["v"]
assert "Cá tra phi lê" in r["khung"] and "15,5" in r["khung"].replace(".", ",") and "Lưu tạm" in r["khung"]
assert r["b7"] == "10" and r["v7"] == "15,5", (r["b7"], r["v7"], r["log"])          # mục 7: 2 số đầu của mã ngành chính 10209, doanh thu triệu đồng
assert "Sản phẩm từ cá tra phi lê [10209121]" in r["t6"] and r["c3"] == "150" and r["c4"] == "10", (r["t6"], r["c3"], r["c4"], r["log"])      # mục 6: chọn đúng mã SP đã gán, số lượng ở cột 3, giá trị cột 4
assert "/log/luu" not in LOG and "/log/hoantat" not in LOG, LOG
print("PASS: tự đăng nhập + điền bảng mục 6 (chọn mã SP trong hộp tra cứu) và mục 7 (chọn mã ngành cấp 2) — đúng công ty -> điền phiếu (không điền nhầm ô 'lao động tại phường xã') -> hiện số liệu sản phẩm/doanh thu; không bấm Lưu tạm/Hoàn tất.")
print("\nALL DONE")
