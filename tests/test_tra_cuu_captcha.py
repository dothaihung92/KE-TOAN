import os, sys, json, threading, time
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server
server.time.sleep = (lambda f: (lambda s: f(min(s, 0.05))))(time.sleep)

# Trang Thuế (10/2026) yêu cầu captcha khi tra cứu: GET /api/captcha -> {key, content}; tra cứu gửi kèm &ckey=...&cvalue=... trên URL
# (ca thật: .../sco-query/invoices/sold?sort=tdlap:desc&size=15&search=...&ckey=6ade...&cvalue=QFWFNF). Thiếu/sai mã -> bị từ chối.
class R:
    def __init__(self, code, body): self.status_code, self._b, self.headers = code, body, {}
    @property
    def text(self): return json.dumps(self._b, ensure_ascii=False)
    def json(self): return self._b
    def raise_for_status(self):
        if self.status_code >= 400: raise Exception(self.status_code)

class S:
    def __init__(self): self.urls = []; self.headers = {}
    def get(self, url, headers=None, timeout=None):
        self.urls.append(url)
        if url.endswith("/captcha"):
            return R(200, {"key": "K%d" % len(self.urls), "content": "<svg xmlns='http://www.w3.org/2000/svg'></svg>"})
        if "cvalue=QFWFNF" in url:
            return R(200, {"datas": [{"shdon": 9216, "khhdon": "C26MPL", "khmshdon": 1, "nbmst": "0317009837"}], "total": 1, "state": None})
        return R(400, {"message": "Mã captcha không hợp lệ"})

c = server.GDTClient.__new__(server.GDTClient)
c.session = S(); c.token = "T"
hoi = []
c.captcha_cb = lambda cancel_check=None: hoi.append(1) or ("6ade3361b86cb105bb030380", "QFWFNF")
res = c._fetch_paginated("https://hoadondientu.gdt.gov.vn/api/sco-query/invoices/sold", "tdlap=ge=19/10/2026T00:00:00;tdlap=le=25/10/2026T23:59:59", "x")
assert [x["shdon"] for x in res] == [9216] and len(hoi) == 1, (res, hoi)
assert c.session.urls[-1].endswith("&ckey=6ade3361b86cb105bb030380&cvalue=QFWFNF"), c.session.urls[-1]
res2 = c._fetch_paginated("https://hoadondientu.gdt.gov.vn/api/sco-query/invoices/sold", "tdlap=ge=01/10/2026T00:00:00;tdlap=le=10/10/2026T23:59:59", "x")
assert len(res2) == 1 and len(hoi) == 1, "mã còn dùng được -> không hỏi lại"
print("PASS 1: bị đòi captcha -> hỏi người dùng 1 lần, gọi lại kèm &ckey=&cvalue= đúng định dạng trang Thuế; lượt sau dùng lại mã.")

c2 = server.GDTClient.__new__(server.GDTClient)
c2.session = S(); c2.token = "T"
try:
    c2._fetch_paginated("https://x/api/query/invoices/sold", "s", "x"); assert False
except Exception as e:
    assert "captcha" in str(e).lower()
print("PASS 2: không có hộp captcha (gọi ngoài màn hình tra cứu) -> báo rõ cần nhập captcha, không treo.")

# hộp captcha: phần mềm đọc sẵn mã (gợi ý), NGƯỜI DÙNG xác nhận qua endpoint; 'Mã khác' lấy captcha mới
server._solve_captcha = lambda content, drv=None: "QFWFNX"
c3 = server.GDTClient.__new__(server.GDTClient); c3.session = S(); c3.token = "T"
kq = {}
t = threading.Thread(target=lambda: kq.update(r=server._cho_nguoi_dung_xac_nhan_captcha(7, c3, "CTY A")))
t.start()
for _ in range(100):
    ds = server.tra_cuu_captcha_dang_cho()["ds"]
    if ds: break
    time.sleep(0.02)
assert ds[0]["cid"] == 7 and ds[0]["goi_y"] == "QFWFNX" and ds[0]["anh"].startswith("data:image/svg+xml;base64,") and ds[0]["ten"] == "CTY A"
id1 = ds[0]["id"]
server.tra_cuu_captcha_tra_loi(7, {"id": id1, "lam_moi": 1})
for _ in range(100):
    ds = server.tra_cuu_captcha_dang_cho()["ds"]
    if ds and ds[0]["id"] != id1: break
    time.sleep(0.02)
assert ds[0]["id"] != id1
try:
    server.tra_cuu_captcha_tra_loi(7, {"id": id1, "cvalue": "ABC"}); assert False
except server.HTTPException as e:
    assert e.status_code == 409
server.tra_cuu_captcha_tra_loi(7, {"id": ds[0]["id"], "cvalue": "QFWFNF"})
t.join(5)
assert kq["r"][1] == "QFWFNF" and kq["r"][0].startswith("K") and 7 not in server.CAPTCHA_TRA_CUU
print("PASS 3: hộp captcha hiện ảnh + mã đọc sẵn; 'Mã khác' đổi captcha; chỉ gửi mã người dùng xác nhận.")

src = open(os.path.join(_REPO_ROOT, "server.py"), encoding="utf-8").read()
rf = src[src.index("def _run_fetch_job("):]
assert rf.index("client.captcha_cb = ") < rf.index("client.query_invoices(")
html = open(os.path.join(_REPO_ROOT, "static", "index.html"), encoding="utf-8").read()
assert "setInterval(tcCapKiemTra,1500)" in html and "ev.key==='Enter'" in html
print("PASS 4: tra cứu (1 công ty + hàng loạt) gắn hộp captcha; giao diện tự hiện hộp, Enter để xác nhận.")

import subprocess, tempfile
JS = r"""const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: process.env.CHROME || undefined });
  const pg = await b.newPage();
  const loi=[]; pg.on('pageerror', e => loi.push(String(e)));
  await pg.goto('file://' + process.env.INDEX);
  const r = await pg.evaluate(async () => {
    window.__goi=[];
    api = async (p,o) => { window.__goi.push([p,o&&o.body]); if(p==='/api/tra-cuu-captcha') return {ds: window.__da?[]:[{cid:7,id:'a1',ten:'CTY A',anh:'data:image/svg+xml;base64,PHN2Zy8+',goi_y:'QFWFNF'}]}; window.__da=1; return {ok:true}; };
    await tcCapKiemTra();
    const o=document.getElementById('tcCapO'); const v=o.value, f=document.activeElement===o;
    o.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter'}));
    await new Promise(r=>setTimeout(r,200));
    return {v, f, goi: window.__goi, con: !!document.getElementById('tcCapBox')};
  });
  console.log(JSON.stringify({r, loi: loi.filter(x=>!/fetch/i.test(x))}));
  await b.close();
})();
"""
f = os.path.join(tempfile.mkdtemp(), "t.js"); open(f, "w", encoding="utf-8").write(JS)
env = dict(os.environ, NODE_PATH="/opt/node22/lib/node_modules", INDEX=os.path.join(_REPO_ROOT, "static", "index.html"))
if os.path.exists("/opt/pw-browsers/chromium"):
    env["CHROME"] = "/opt/pw-browsers/chromium"
out = subprocess.run(["node", f], capture_output=True, text=True, env=env, timeout=120).stdout.strip().splitlines()
d = json.loads(out[-1])
assert d["r"]["v"] == "QFWFNF" and d["r"]["goi"][-1] == ["/api/tra-cuu-captcha/7", json.dumps({"id": "a1", "cvalue": "QFWFNF"}, separators=(",", ":"))] and not d["r"]["con"] and not d["loi"], d
print("PASS 5: giao diện — hộp captcha hiện mã đọc sẵn, bấm Enter gửi đúng mã và đóng hộp.")

# Ca thật: trang Thuế trả 429 liên tục (lần 16/30) cho lượt tra cứu chưa kèm captcha, không có chữ "captcha" -> hộp không hiện.
class S429(S):
    def get(self, url, headers=None, timeout=None):
        self.urls.append(url)
        if "cvalue=QFWFNF" in url:
            return R(200, {"datas": [{"shdon": 1, "khhdon": "C26MPL", "khmshdon": 1, "nbmst": "1"}], "total": 1, "state": None})
        return R(429, {"message": "Too many requests"})
c5 = server.GDTClient.__new__(server.GDTClient); c5.session = S429(); c5.token = "T"
hoi5 = []
c5.captcha_cb = lambda cancel_check=None: hoi5.append(1) or ("k", "QFWFNF")
r5 = c5._fetch_paginated("https://x/api/sco-query/invoices/purchase", "s", "x")
assert len(r5) == 1 and len(hoi5) == 1 and sum(1 for u in c5.session.urls if "ckey" not in u) == 3, c5.session.urls
assert server._la_loi_captcha_tra_cuu(R(400, {"message": "Mã xác thực không đúng"}))
print("PASS 6: 429 lặp lại 3 lần khi chưa có mã captcha -> hiện hộp captcha (ca thật 'lần 30' không hiện hộp); nhận cả thông báo 'mã xác thực'.")
print("ALL DONE")
