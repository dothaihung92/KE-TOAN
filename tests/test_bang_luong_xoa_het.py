import os, sys, json, sqlite3, subprocess, tempfile, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Nút "🗑 Xoá hết dữ liệu" ở Bảng Lương: xoá toàn bộ dữ liệu các tháng của năm đang chọn (đã lưu), giữ Tham số năm.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
conn = sqlite3.connect(":memory:", check_same_thread=False); conn.row_factory = sqlite3.Row
class KhongDong:
    def __init__(self, c): self.c = c
    def execute(self, *a): return self.c.execute(*a)
    def commit(self): self.c.commit()
    def close(self): pass
server.db = lambda: KhongDong(conn)
server._luong_dam_bao_bang(conn)
base = {"chuc_vu": "KD", "ma": "1", "ten": "A", "luong_cb": 8_000_000, "dong_bh": 1}
ts = dict(server._luong_chuan_tham_so(None, 2026), nguong_part_time=2_530_000)
for nam in (2025, 2026):
    conn.execute("INSERT INTO bang_luong (company_id, nam, tham_so_json, thang_json, updated_at) VALUES (5, ?, ?, ?, '')",
                 (nam, json.dumps(ts), json.dumps({"%02d" % t: [base] for t in range(1, 13)})))
conn.commit()
assert len(server._luong_doc_nam(5, 2026)[1]) == 12

kq = server.bang_luong_xoa_nam(5, 2026)
assert not kq["thang"] and kq["nam"] == 2026
assert server._luong_doc_nam(5, 2026)[1] == {}
assert len(server._luong_doc_nam(5, 2025)[1]) == 12, "năm khác không bị đụng"
assert server._luong_doc_nam(5, 2026)[0].get("nguong_part_time") == 2_530_000, "giữ Tham số năm"
assert server.bang_luong_xoa_nam(6, 2026)["thang"] == {}                    # công ty/năm chưa có dữ liệu: không lỗi
print("PASS 1: xoá hết các tháng của năm chọn; giữ Tham số năm; không đụng năm khác/công ty khác.")

html = open(os.path.join(ROOT, "static", "index.html"), encoding="utf-8").read()
assert 'onclick="blXoaHetDuLieu()"' in html and "Xoá hết dữ liệu" in html
fn = re.search(r"async function blXoaHetDuLieu\(\)\{.*?\n\}\n", html, re.S).group(0)
js = """
const BL_THANG=Array.from({length:12},(_,i)=>String(i+1).padStart(2,'0'));
let blNam=2026,blThang='03',blTS={},blDL={'01':[{}, {}],'03':[{}]},blCacNam=[2026],blBan=true,current=5,hoi=[],goi=[],toasts=[];
const blVeChonNam=()=>{},blVeTabs=()=>{},blVeBang=()=>{},blVeInfo=()=>{};
const toast=(m,k)=>toasts.push(m);
let dongY=false;const confirm=m=>{hoi.push(m);return dongY};
const api=async(u,o)=>{goi.push([u,o&&o.method]);return {tham_so:{x:1},thang:{},cac_nam:[2026]}};
""" + fn + """
(async()=>{
  await blXoaHetDuLieu();                       // không đồng ý -> không gọi API
  const a={goi:goi.length,hoi:hoi[0]};
  dongY=true;await blXoaHetDuLieu();
  console.log(JSON.stringify({a,goi,dl:blDL,ban:blBan,thang:blThang,toast:toasts[toasts.length-1]}));
  blDL={};toasts.length=0;await blXoaHetDuLieu();console.log(JSON.stringify({rong:toasts[0]}));
})();
"""
with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as fh:
    fh.write(js)
out = subprocess.run(["node", fh.name], capture_output=True, text=True, timeout=60)
assert out.returncode == 0, out.stderr
l1, l2 = [json.loads(x) for x in out.stdout.strip().splitlines()[-2:]]
assert l1["a"]["goi"] == 0 and "2026" in l1["a"]["hoi"] and "2 tháng, 3 dòng" in l1["a"]["hoi"].replace("• ", "") or "3 dòng" in l1["a"]["hoi"]
assert l1["goi"] == [["/api/bang-luong/5?nam=2026", "DELETE"]] and l1["dl"] == {} and l1["ban"] is False and l1["thang"] == "03"
assert "chưa có dữ liệu" in l2["rong"]
print("PASS 2: nút hỏi xác nhận (không đồng ý -> không xoá); đồng ý -> gọi DELETE, xoá sạch dữ liệu trên màn hình, giữ tab đang xem; năm trống -> báo không có gì để xoá.")
print("ALL DONE")
