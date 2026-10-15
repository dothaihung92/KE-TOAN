import os, sys, re, json, subprocess, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Khung quảng cáo (ANTS...): trang quảng cáo trên website riêng (https) nạp trong iframe sandbox KHÔNG có
# allow-same-origin -> mã quảng cáo không đọc được dữ liệu phần mềm. URL trống / không https -> không hiện.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cai = {}
server._get_setting = lambda k, d="": cai.get(k, d)

server.QUANG_CAO_URL = ""
assert server.get_quang_cao()["url"] == ""
server.QUANG_CAO_URL = "http://khong-an-toan.vn/qc.html"
assert server.get_quang_cao()["url"] == "", "chỉ nhận https"
server.QUANG_CAO_URL = "https://vi-du.vn/qc.html"
assert server.get_quang_cao() == {"url": "https://vi-du.vn/qc.html", "cao": server.QUANG_CAO_CAO}
cai["quang_cao_url"] = "https://rieng-may.vn/qc.html"
assert server.get_quang_cao()["url"] == "https://rieng-may.vn/qc.html"
print("PASS 1: /api/quang-cao chỉ trả URL https; trống = không quảng cáo; app_settings ghi đè được.")

html = open(os.path.join(ROOT, "static", "index.html"), encoding="utf-8").read()
m = re.search(r"async function qcNap\(\)\{.*?\n\}\n", html, re.S)
assert m, "thiếu qcNap"
assert "allow-same-origin" not in m.group(0)
assert os.path.exists(os.path.join(ROOT, "templates", "quang_cao", "khung_ants.html"))

js = r"""
const {chromium}=require('playwright');
(async()=>{
  const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium'});
  const kq={};
  for(const url of ['', 'https://vi-du.vn/qc.html']){
    const p=await b.newPage();
    await p.route('**/*',r=>{const u=r.request().url();
      if(u.endsWith('/api/quang-cao'))return r.fulfill({contentType:'application/json',body:JSON.stringify({url,cao:90})});
      if(u.startsWith('https://vi-du.vn/'))return r.fulfill({contentType:'text/html',body:'<script>try{parent.document.title="LOT"}catch(e){document.title="CHAN"}</script>'});
      if(u==='http://app.local/')return r.fulfill({contentType:'text/html',body:'<title>APP</title><body><script>'+QC+'</script></body>'});
      r.abort()});
    await p.goto('http://app.local/');await p.evaluate(()=>qcNap());await p.waitForTimeout(800);
    const f=await p.$('#qcKhung iframe');
    kq[url||'trong']={co:!!f,sandbox:f?await f.getAttribute('sandbox'):null,title:await p.title(),pad:await p.evaluate(()=>document.body.style.paddingBottom)};
    if(f){await p.click('#qcKhung button');kq[url].sauAn=!!(await p.$('#qcKhung'))}
    await p.close();
  }
  console.log(JSON.stringify(kq));await b.close();
})();
"""
qc = m.group(0)
with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as fh:
    fh.write("const QC=" + json.dumps(qc) + ";\n" + js)
out = subprocess.run(["node", fh.name], capture_output=True, text=True, timeout=120,
                     env=dict(os.environ, NODE_PATH="/opt/node22/lib/node_modules"))
assert out.returncode == 0, out.stderr
kq = json.loads(out.stdout.strip().splitlines()[-1])
assert kq["trong"]["co"] is False and kq["trong"]["pad"] == ""
c = kq["https://vi-du.vn/qc.html"]
assert c["co"] and "allow-scripts" in c["sandbox"] and "allow-same-origin" not in c["sandbox"]
assert c["title"] == "APP", "mã quảng cáo KHÔNG được chạm vào trang phần mềm"
assert c["pad"] == "90px" and c["sauAn"] is False
print("PASS 2: có URL -> khung iframe sandbox hiện ở đáy; mã quảng cáo không truy cập được trang phần mềm; nút × ẩn được.")
print("ALL DONE")
