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
    document.querySelector('#tcCapBox img').click();
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
print("PASS 5: giao diện — hộp captcha hiện mã đọc sẵn, chạm vào ảnh/bất kỳ đâu trên hộp gửi đúng mã và đóng hộp.")

# Ca thật: trang Thuế trả 429 liên tục (lần 16/30) cho lượt tra cứu chưa kèm captcha, không có chữ "captcha" -> hộp không hiện.
class S429(S):
    def get(self, url, headers=None, timeout=None):
        self.urls.append(url)
        if "cvalue=QFWFNF" in url:
            return R(200, {"datas": [{"shdon": 1, "khhdon": "C26MPL", "khmshdon": 1, "nbmst": "1"}], "total": 1, "state": None})
        return R(429, {})
c5 = server.GDTClient.__new__(server.GDTClient); c5.session = S429(); c5.token = "T"
hoi5 = []
c5.captcha_cb = lambda cancel_check=None: hoi5.append(1) or ("k", "QFWFNF")
r5 = c5._fetch_paginated("https://x/api/sco-query/invoices/purchase", "s", "x")
assert len(r5) == 1 and len(hoi5) == 1 and sum(1 for u in c5.session.urls if "ckey" not in u) == 2, c5.session.urls
assert server._la_loi_captcha_tra_cuu(R(400, {"message": "Mã xác thực không đúng"}))
print("PASS 6: 429 lặp lại 2 lần khi chưa có mã captcha -> hiện hộp captcha (ca thật 'lần 30' không hiện hộp); nhận cả thông báo 'mã xác thực'.")

# Ca thật 26/10/2026: hộp captcha hiện 1 lần rồi không hiện nữa — trang Thuế trả 429 "Too Many Requests" mỗi khi mã thiếu/hết hạn.
# Nay: 429 lặp lại 2 lần -> hỏi mã MỚI mỗi lần, và vẫn tiếp tục tra tới khi lấy được.
class STM(S):
    def __init__(self): super().__init__(); self.da_dung = set()
    def get(self, url, headers=None, timeout=None):
        self.urls.append(url)
        import re as _re
        m = _re.search(r"cvalue=([A-Z0-9]+)", url)
        if m and m.group(1) not in self.da_dung:          # mã chỉ dùng được 1 lượt
            self.da_dung.add(m.group(1))
            return R(200, {"datas": [{"shdon": len(self.urls), "khhdon": "K", "khmshdon": 1, "nbmst": "1"}], "total": 1, "state": None})
        return R(429, {"error": "Too Many Requests"})
c6 = server.GDTClient.__new__(server.GDTClient); c6.session = STM(); c6.token = "T"
hoi6 = []
c6.captcha_cb = lambda cancel_check=None: hoi6.append(1) or ("k", "M%d" % len(hoi6))
cho = []
_goc = server._bao_ngat_ket_noi
server._bao_ngat_ket_noi = lambda g: cho.append(g)
try:
    for k in range(3):
        assert len(c6._fetch_paginated("https://x/api/sco-query/invoices/sold", "s%d" % k, "x")) == 1
finally:
    server._bao_ngat_ket_noi = _goc
assert len(hoi6) == 3, hoi6
assert server.TRA_CUU_DS_DONG_THOI == 2 and server._cho_429(1) == 2 and server._cho_429(9) == 2 and server._cho_429(3, 60) == 2
print("PASS 7: mỗi lần mã hết hạn (429 lặp lại) đều hiện hộp captcha hỏi mã MỚI (3 lượt tra -> 3 lần hỏi), tra tiếp tới khi được; 429 chỉ nghỉ 2s.")

# Ca thật: hộp hiện ô TRỐNG, bấm Enter báo "chưa có mã" — bộ đọc nhanh không đọc được SVG nét vẽ. Nay: đọc lại bằng trình duyệt ẩn, vẫn
# không ra thì lấy captcha khác (tối đa 3); ô trống thì Enter = lấy mã khác.
goi = []
server._solve_captcha = lambda content, drv=None: goi.append(drv) or ("ABC123" if drv == "DRV" and len(goi) >= 4 else "")
server._TD_DOC_CAPTCHA.update(drv="DRV", da_thu=True)
c7 = server.GDTClient.__new__(server.GDTClient); c7.session = S(); c7.token = "T"
kq7 = {}
t7 = threading.Thread(target=lambda: kq7.update(r=server._cho_nguoi_dung_xac_nhan_captcha(8, c7, "B")))
t7.start()
for _ in range(200):
    ds = [x for x in server.tra_cuu_captcha_dang_cho()["ds"] if x["cid"] == 8]
    if ds: break
    time.sleep(0.02)
assert ds[0]["goi_y"] == "ABC123" and goi == [None, "DRV", None, "DRV"], goi
server.tra_cuu_captcha_tra_loi(8, {"id": ds[0]["id"], "cvalue": "ABC123"}); t7.join(5)
html = open(os.path.join(_REPO_ROOT, "static", "index.html"), encoding="utf-8").read()
assert "if(!lamMoi&&!v)lamMoi=true;" in html
print("PASS 8: chưa đọc được mã -> đọc lại bằng trình duyệt ẩn, lấy captcha khác; ô trống thì Enter = lấy mã khác (không báo 'chưa có mã').")

# Ca thật (MTT): log lặp "Token hết hạn giữa chừng — đã đăng nhập lại thành công" mãi, dữ liệu không lấy tiếp: trang Thuế trả 401 cho lượt gọi
# kèm mã captcha cũ/hết hạn -> bản trước coi là token hết hạn, đăng nhập lại xong lại gửi đúng mã cũ. Nay: 401 kèm mã = mã sai -> xin mã mới.
class S401(S):
    def __init__(self): super().__init__(); self.moi = set()
    def get(self, url, headers=None, timeout=None):
        self.urls.append(url)
        import re as _re
        m = _re.search(r"cvalue=([A-Z0-9]+)", url)
        if m and m.group(1).startswith("OK") and m.group(1) not in self.moi:
            self.moi.add(m.group(1))
            return R(200, {"datas": [{"shdon": 5, "khhdon": "K", "khmshdon": 1, "nbmst": "1"}], "total": 1, "state": None})
        if m:
            return R(401, {"message": "Unauthorized"})
        return R(429, {})
c8 = server.GDTClient.__new__(server.GDTClient); c8.session = S401(); c8.token = "T"
c8._trang_thai_captcha().update(ckey="old", cvalue="OLD1", the_he=1)
hoi8 = []
c8.captcha_cb = lambda cancel_check=None: hoi8.append(1) or ("k", "OK%d" % len(hoi8))
r8 = c8._fetch_paginated("https://x/api/sco-query/invoices/sold", "s", "x")
assert [x["shdon"] for x in r8] == [5] and hoi8 == [1], (r8, hoi8)
print("PASS 9: 401 khi đã kèm mã captcha cũ -> xin mã MỚI và lấy tiếp được (không báo 'token hết hạn' rồi đăng nhập lại lặp mãi).")

# MTT: đã dùng captcha thì chỉ dò 1 lần/đoạn (không bắt nhập mã 4 lần cho cùng 1 đoạn)
c9 = server.GDTClient.__new__(server.GDTClient); c9.session = S(); c9.token = "T"
lan9 = []
def fake_q(tu, den, loai, page_size, he_thong, progress=None, ttxly_can_do=None, cancel_check=None):
    lan9.append(1); return ([{"khmshdon": "1", "khhdon": "K", "shdon": len(lan9), "nbmst": "1"}], 1, [], [])
c9._query_one_range = fake_q
c9._trang_thai_captcha().update(the_he=2)
c9._query_one_range_on_dinh("01/09/2026", "10/09/2026", "sold", 50, "sco-query")
assert len(lan9) == 1, lan9
c10 = server.GDTClient.__new__(server.GDTClient); lan9.clear()
c10._query_one_range = fake_q; c10._ban_sao_phien_moi = lambda: c10; c10.session = type("S", (), {"close": staticmethod(lambda: None)})()
c10._query_one_range_on_dinh("01/09/2026", "10/09/2026", "sold", 50, "sco-query")
assert len(lan9) >= 3, "chưa dùng captcha: vẫn dò nhiều lần như cũ"
print("PASS 10: MTT đã dùng captcha -> dò 1 lần/đoạn; chưa dùng captcha vẫn dò nhiều lần như cũ.")

# Tải file XML (export-xml) và lấy chi tiết (detail) cũng bị đòi captcha (ảnh thật: hộp captcha hiện sau khi bấm nút xuất file): trước đây
# 2 hàm này không gửi mã, bị từ chối thì lặng lẽ trả None -> "không tải hóa đơn về, không dò chi tiết". Nay kèm ckey/cvalue và hỏi mã khi bị đòi.
class PH:
    def __init__(self, dung): self.dung = dung; self.urls = []
    def get(self, url, params=None, headers=None, timeout=None):
        self.urls.append(dict(params or {}))
        if (params or {}).get("cvalue") == self.dung:
            body = b"PK\x03\x04zipdata"
            r = R(200, {"ok": 1}); r.content = body
            return r
        r = R(429, {"message": "Too Many Requests"}); r.content = b'{"mes'
        return r
    def close(self): pass
for ham in ("download_xml", "get_detail"):
    cx = server.GDTClient.__new__(server.GDTClient); cx.token = "T"
    ph = PH("ZZ9"); cx._phien_mot_lan = lambda ph=ph: ph
    cx._ghi_loi_chi_tiet = lambda *a: None
    cx._trang_thai_captcha().update(the_he=1)
    hoi = []
    cx.captcha_cb = lambda cancel_check=None, hoi=hoi: hoi.append(1) or ("kk", "ZZ9")
    server.time.sleep = lambda s_: None
    kq = getattr(cx, ham)("0317009837", "C26MPL", 1, 8749, "sold", "sco-query") if ham == "download_xml" else cx.get_detail("0317009837", "C26MPL", 1, 8749, he_thong="sco-query", loai="sold", cho_khi_429=False)
    assert kq and len(hoi) == 1, (ham, kq, hoi)
    assert ph.urls[-1].get("ckey") == "kk" and ph.urls[-1].get("cvalue") == "ZZ9", ph.urls
print("PASS 11: tải XML và lấy chi tiết bị đòi captcha (429 khi phiên đã dùng mã) -> hỏi mã, gọi lại kèm ckey/cvalue và tải được (trước đây lặng lẽ trả None).")
print("ALL DONE")
