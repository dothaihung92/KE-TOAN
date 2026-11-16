import base64, io, os, sys, tempfile, json, subprocess
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import openpyxl
import server
# Chọn nhiều file: file hoá đơn/bảng kê (không phải đơn hàng sàn) báo lý do rõ; + khung tiến trình khi bấm Hỗ trợ import hoá đơn.
tmp = tempfile.mkdtemp(); server.DATA_DIR = tmp
def xl(rows):
    wb = openpyxl.Workbook(); ws = wb.active
    for r in rows: ws.append(r)
    b = io.BytesIO(); wb.save(b); return base64.b64encode(b.getvalue()).decode()
r = server.san_nhan_nhieu_file(1, {"files": [{"ten": "BangKe_HoaDon_0317256924_T102026.xlsx", "b64": xl([["Số hóa đơn", "Ngày"], [1, "2026-10-01"]])},
                                           {"ten": "linh_tinh.xlsx", "b64": xl([["a"], [1]])}]})
m = {x["ten"]: x for x in r["file"]}
assert "KHÔNG phải file đơn hàng của sàn" in m["BangKe_HoaDon_0317256924_T102026.xlsx"]["loi"], m
assert "đúng báo cáo ĐƠN HÀNG" in m["linh_tinh.xlsx"]["loi"], m
print("PASS 1: file bảng kê/hoá đơn báo rõ 'không phải file đơn hàng của sàn'; file lạ báo cần đúng báo cáo đơn hàng.")
JS = r"""
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: process.env.CHROME || undefined });
  const pg = await b.newPage(); const loi = []; pg.on('pageerror', e => loi.push(String(e)));
  await pg.goto('file://' + process.env.INDEX);
  const r = await pg.evaluate(async () => {
    document.body.insertAdjacentHTML('beforeend', '<div id="xhdKq"></div>');
    window.fetch = () => new Promise(res => setTimeout(() => res({ ok: false, json: async () => ({ detail: 'Không có đơn MỚI' }), headers: { get: () => '' } }), 1500));
    window.current = 1; window.xhdThan = () => ({ tu_ngay: '', den_ngay: '', chi_hoan_thanh: true, tuy_chon: {} });
    window.xhdGopCfg = () => ({ san: ['shopee'] }); window.xhdGopFile = k => ({ ten: 'Order.all.x.xlsx', nguon: 'dl' });
    const p = xhdXuatGop(false, null); await new Promise(r => setTimeout(r, 700));
    const dang = document.getElementById('xhdKq').innerText;
    await p; const sau = document.getElementById('xhdKq').innerText;
    return { dang, sau };
  });
  console.log(JSON.stringify({ r, loi })); await b.close();
})();
"""
f = os.path.join(tempfile.mkdtemp(), "t.js"); open(f, "w", encoding="utf-8").write(JS)
env = dict(os.environ, NODE_PATH="/opt/node22/lib/node_modules", INDEX=os.path.join(_REPO_ROOT, "static", "index.html"))
if os.path.exists("/opt/pw-browsers/chromium"): env["CHROME"] = "/opt/pw-browsers/chromium"
d = json.loads(subprocess.run(["node", f], capture_output=True, text=True, env=env, timeout=120).stdout.strip().splitlines()[-1])
assert "Đang xuất file import hoá đơn" in d["r"]["dang"] and "Shopee: Order.all.x.xlsx" in d["r"]["dang"] and "giây" in d["r"]["dang"], d
assert "Đang xuất" not in d["r"]["sau"] and "Xuất file thất bại" in d["r"]["sau"] and "Không có đơn MỚI" in d["r"]["sau"], d
assert not [e for e in d["loi"] if "fetch" not in e.lower()], d
print("PASS 2: bấm xuất -> hiện khung tiến trình (file đang xử lý + đồng hồ giây); xong/lỗi thì xoá khung và báo kết quả/lỗi ngay trong mục kết quả.")
print("\nALL DONE")
