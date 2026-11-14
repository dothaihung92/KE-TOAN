import json, os, sys, subprocess, tempfile
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server
# 1) Lưu (sửa) công ty không còn lỗi 500 (câu lệnh UPDATE từng thiếu dấu phẩy) và giữ tài khoản ngân hàng cũ khi form không gửi.
server.DATA_DIR = tempfile.mkdtemp(); server.DB_PATH = os.path.join(server.DATA_DIR, "t.db")
try:
    server.init_db()
except Exception:
    pass
c = server.db()
c.execute("INSERT INTO companies (ten, mst, username, password, bank, bank_user, bank_password, created_at) VALUES ('A','0100000001','u','p','VCB','nguoi_nh','mk_nh','2026-01-01')")
c.commit(); cid = c.execute("SELECT id FROM companies WHERE mst='0100000001'").fetchone()["id"]; c.close()
r = server.update_company(cid, {"ten": "A mới", "mst": "0100000001", "username": "u", "password": ""})
assert r == {"ok": True}
c = server.db(); row = c.execute("SELECT ten, password, bank_user, bank_password FROM companies WHERE id=?", (cid,)).fetchone(); c.close()
assert row["ten"] == "A mới" and row["password"] == "p" and row["bank_user"] == "nguoi_nh" and row["bank_password"] == "mk_nh", dict(row)
print("PASS 1: sửa công ty lưu được (hết lỗi Internal Server Error), giữ mật khẩu và tài khoản ngân hàng cũ.")
# 2) Phím tắt Esc/Enter
JS = r"""
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: process.env.CHROME || undefined });
  const pg = await b.newPage(); const loi = []; pg.on('pageerror', e => loi.push(String(e)));
  await pg.goto('file://' + process.env.INDEX);
  const r = await pg.evaluate(async () => {
    const o = {}; let luu = 0, luuNh = 0;
    saveCompany = async () => { luu++ }; luuBankModal = async () => { luuNh++ };
    const co = document.getElementById('coModal'), nh = document.getElementById('bankModal');
    const ph = (el, k, tg) => { (tg || document.body).dispatchEvent(new KeyboardEvent('keydown', { key: k, bubbles: true, cancelable: true })) };
    ph(0, 'Enter'); o.dong_enter = luu;                                  // hộp đóng: không làm gì
    co.classList.add('show'); const inp = document.getElementById('m_ten'); inp.focus();
    inp.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true })); o.enter_luu = luu;
    ph(0, 'Escape'); o.esc_dong = !co.classList.contains('show');
    co.classList.add('show'); nh.classList.add('show');
    ph(0, 'Enter'); o.nh_luu = [luu, luuNh];                             // hộp ngân hàng trên cùng: Enter lưu ngân hàng
    ph(0, 'Escape'); o.nh_dong = [!nh.classList.contains('show'), co.classList.contains('show')];   // Esc chỉ đóng hộp ngân hàng
    const btn = document.createElement('button'); co.appendChild(btn); btn.focus();
    btn.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true })); o.enter_nut = luu;
    return o;
  });
  console.log(JSON.stringify({ r, loi }));
  await b.close();
})();
"""
f = os.path.join(tempfile.mkdtemp(), "t.js"); open(f, "w", encoding="utf-8").write(JS)
env = dict(os.environ, NODE_PATH="/opt/node22/lib/node_modules", INDEX=os.path.join(_REPO_ROOT, "static", "index.html"))
if os.path.exists("/opt/pw-browsers/chromium"):
    env["CHROME"] = "/opt/pw-browsers/chromium"
out = subprocess.run(["node", f], capture_output=True, text=True, env=env, timeout=120)
d = json.loads(out.stdout.strip().splitlines()[-1])
assert d["r"] == {"dong_enter": 0, "enter_luu": 1, "esc_dong": True, "nh_luu": [1, 1], "nh_dong": [True, True], "enter_nut": 1} and not [e for e in d["loi"] if "fetch" not in e.lower()], d
print("PASS 2: Enter = Lưu, Esc = Hủy cho hộp công ty; hộp Ngân hàng (nằm trên) xử lý trước; Enter trên nút giữ nghĩa cũ.")
print("\nALL DONE")
