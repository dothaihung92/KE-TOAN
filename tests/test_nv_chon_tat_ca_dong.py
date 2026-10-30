import os, sys, subprocess, tempfile, threading, time, shutil
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server, uvicorn

# Danh Sách Nhân Viên: chọn TẤT CẢ dòng (nút "☑ Chọn tất cả" / ô tick ở tiêu đề — theo bộ lọc đang hiện), tick từng dòng,
# "🗑 Xóa dòng đã chọn" xóa MỌI dòng đã tick một lần (trước chỉ xóa được 1 dòng đang bấm).
td = tempfile.mkdtemp()
server.DB_PATH = os.path.join(td, "t.db"); server.DATA_DIR = td; server.init_db()
c = server.db(); c.execute("INSERT INTO companies (id, ten, mst) VALUES (1,'CTY A','0300000001')"); c.commit(); c.close()
server._trang_thai_giay_phep = lambda: (True, None, "")
PORT = 8797
cfg = uvicorn.Config(server.app, host="127.0.0.1", port=PORT, log_level="error")
sv = uvicorn.Server(cfg)
threading.Thread(target=sv.run, daemon=True).start()
for _ in range(100):
    if sv.started: break
    time.sleep(0.1)

JS = r"""
const { chromium } = require('playwright');
(async()=>{
 const b=await chromium.launch(); const p=await b.newPage({viewport:{width:1400,height:800}});
 const loi=[]; p.on('pageerror',e=>loi.push(e.message)); p.on('dialog',d=>d.accept());
 await p.goto('http://127.0.0.1:PORT/'); await p.waitForTimeout(1200);
 await p.evaluate(async()=>{current=1;let d=document.getElementById('nhapLieuBody');document.body.appendChild(d);
   d.style.cssText='display:block;position:fixed;inset:0;z-index:8000;background:#fff;overflow:auto';
   moDanhSachNhanVien(); await nvTaiPromise;
   nvHeader=['STT','Mã NV','Họ và tên','CCCD'];
   nvRows=[[1,'1','Nguyễn A','1'],[2,'2','Trần B','2'],[3,'3','Nguyễn C','3'],[4,'4','Lê D','4']]; veGridNhanVien();});
 const kq={};
 await p.click('#nvNutChonTatCa');
 kq.tatCa=await p.evaluate(()=>[nvTick.size,document.getElementById('nvTickAll').checked,document.querySelectorAll('tr[data-nvtick]').length]);
 await p.click('#nvNutChonTatCa');
 kq.boChon=await p.evaluate(()=>nvTick.size);
 await p.evaluate(()=>{nvFilters={2:'nguyen'};veGridNhanVien()});
 await p.check('#nvTickAll');
 kq.theoLoc=await p.evaluate(()=>[...nvTick].map(r=>r[2]));
 await p.evaluate(()=>{nvFilters={};veGridNhanVien()});
 await p.locator('#nvTableWrap tbody tr').nth(3).locator('input[type=checkbox]').first().check();
 await p.click('text=Xóa dòng đã chọn'); await p.waitForTimeout(300);
 kq.conLai=await p.evaluate(()=>nvRows.map(r=>[r[0],r[2]]));
 kq.loi=loi;
 console.log(JSON.stringify(kq)); await b.close();
})();
""".replace("PORT", str(PORT))
node = shutil.which("node")
if not node:
    print("SKIP: không có node"); sys.exit(0)
env = dict(os.environ)
try:
    env["NODE_PATH"] = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
except Exception:
    pass
r = subprocess.run([node, "-e", JS], capture_output=True, text=True, timeout=120, env=env)
if "Cannot find module 'playwright'" in r.stderr:
    print("SKIP: không có playwright"); sys.exit(0)
import json
kq = json.loads(r.stdout.strip().splitlines()[-1])
assert kq["tatCa"] == [4, True, 4], kq
assert kq["boChon"] == 0, kq
assert kq["theoLoc"] == ["Nguyễn A", "Nguyễn C"], kq
assert kq["conLai"] == [[1, "Trần B"]], kq
assert not kq["loi"], kq
print("PASS: chọn tất cả dòng nhân viên (cả theo bộ lọc), bỏ chọn, tick từng dòng, xóa nhiều dòng đã chọn một lần.")
