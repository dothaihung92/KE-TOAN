import os, sys, json, threading, time, subprocess, tempfile
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Người dùng làm việc khác trong lúc tra cứu: khi cần mã captcha, phần mềm kêu "ting" và đưa cửa sổ phần mềm lên trên cùng (1 lần mỗi
# lượt hỏi; "Mã khác" không kêu lại; nhiều công ty cùng chờ trong 3 giây chỉ kêu 1 lần).
goi = []
server._keu_ting = lambda: goi.append("ting") or True
server._dua_cua_so_len_truoc = lambda tieu_de=server.TIEU_DE_CUA_SO_APP: goi.append(("len", tieu_de)) or 1
server._solve_captcha = lambda content, drv=None: "ABC123"

class R:
    status_code = 200
    def json(self): return {"key": "K", "content": "<svg xmlns='http://www.w3.org/2000/svg'></svg>"}
class C:
    def get_captcha(self): return R().json()

def mo_hop(cid):
    kq = {}
    t = threading.Thread(target=lambda: kq.update(r=server._cho_nguoi_dung_xac_nhan_captcha(cid, C(), "CTY")))
    t.start()
    for _ in range(200):
        ds = [x for x in server.tra_cuu_captcha_dang_cho()["ds"] if x["cid"] == cid]
        if ds:
            return t, kq, ds[0]
        time.sleep(0.02)
    raise AssertionError("không hiện hộp")

server._GOI_NGUOI_DUNG["luc"] = 0
t, kq, h = mo_hop(1)
assert goi == ["ting", ("len", "Quản lý Hóa đơn điện tử")] and h["da_keu"] is True, goi
server.tra_cuu_captcha_tra_loi(1, {"id": h["id"], "lam_moi": 1})
for _ in range(100):
    ds = [x for x in server.tra_cuu_captcha_dang_cho()["ds"] if x["cid"] == 1]
    if ds and ds[0]["id"] != h["id"]: break
    time.sleep(0.02)
assert len(goi) == 2, "Mã khác: không kêu lại"
server.tra_cuu_captcha_tra_loi(1, {"id": ds[0]["id"], "cvalue": "ABC123"}); t.join(5)
t2, kq2, h2 = mo_hop(2)                       # công ty khác hỏi ngay sau (< 3 giây) -> không kêu chồng
assert len(goi) == 2
server.tra_cuu_captcha_tra_loi(2, {"id": h2["id"], "cvalue": "X"}); t2.join(5)
server._GOI_NGUOI_DUNG["luc"] = 0
t3, kq3, h3 = mo_hop(3)
assert goi[2:] == ["ting", ("len", "Quản lý Hóa đơn điện tử")]
server.tra_cuu_captcha_tra_loi(3, {"id": h3["id"], "cvalue": "X"}); t3.join(5)
print("PASS 1: hộp captcha mới -> kêu 'ting' + đưa cửa sổ lên trước; 'Mã khác' không kêu lại; nhiều công ty trong 3 giây chỉ kêu 1 lần.")

src = open(os.path.join(_REPO_ROOT, "server.py"), encoding="utf-8").read()
html = open(os.path.join(_REPO_ROOT, "static", "index.html"), encoding="utf-8").read()
assert "<title>Quản lý Hóa đơn điện tử — Đa công ty</title>" in html and server.TIEU_DE_CUA_SO_APP in "Quản lý Hóa đơn điện tử — Đa công ty"
assert '"--disable-background-timer-throttling"' in src and '"--autoplay-policy=no-user-gesture-required"' in src
import importlib
if os.name != "nt":
    assert importlib.reload(server)._dua_cua_so_len_truoc() == 0 and server._keu_ting() is False, "máy không phải Windows: không lỗi"
print("PASS 2: tiêu đề cửa sổ khớp <title>; cửa sổ app không bị làm chậm khi thu nhỏ, cho phát âm thanh; máy không phải Windows không lỗi.")

JS = r"""
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: process.env.CHROME || undefined });
  const pg = await b.newPage(); const loi = []; pg.on('pageerror', e => loi.push(String(e)));
  await pg.goto('file://' + process.env.INDEX);
  const r = await pg.evaluate(async () => {
    window.__ting = 0; tcCapTing = () => window.__ting++;
    let lan = 0;
    api = async (p, o) => { if (p === '/api/tra-cuu-captcha') { lan++; return {ds: lan <= 3 ? [{cid: 7, id: 'a' + Math.min(lan, 2), ten: 'A', anh: 'data:image/svg+xml;base64,PHN2Zy8+', goi_y: 'X', da_keu: window.__daKeu}] : []}; } return {ok: true}; };
    window.__daKeu = false;
    await tcCapKiemTra(); const t1 = window.__ting;
    await tcCapGui(true); await tcCapKiemTra(); const t2 = window.__ting;      // Mã khác -> không kêu lại
    return {t1, t2};
  });
  console.log(JSON.stringify({r, loi}));
  await b.close();
})();
"""
f = os.path.join(tempfile.mkdtemp(), "t.js"); open(f, "w", encoding="utf-8").write(JS)
env = dict(os.environ, NODE_PATH="/opt/node22/lib/node_modules", INDEX=os.path.join(_REPO_ROOT, "static", "index.html"))
if os.path.exists("/opt/pw-browsers/chromium"):
    env["CHROME"] = "/opt/pw-browsers/chromium"
out = subprocess.run(["node", f], capture_output=True, text=True, env=env, timeout=120)
d = json.loads(out.stdout.strip().splitlines()[-1])
assert d["r"] == {"t1": 1, "t2": 1} and not [e for e in d["loi"] if "fetch" not in e.lower()], d
print("PASS 3: giao diện — máy không kêu được tiếng Windows thì kêu bằng trình duyệt 1 lần; 'Mã khác' không kêu lại.")
print("ALL DONE")
