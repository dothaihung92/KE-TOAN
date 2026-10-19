import os, re, json, subprocess, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html = open(os.path.join(ROOT, "static", "index.html"), encoding="utf-8").read()

# Yêu cầu: tick/màu GTGT + TNCN hiện NGAY khi xử lý xong từng công ty, không đợi cả đợt chạy hết.
fn = re.search(r"let dvcbKhoaCapNhat='', dvcbDangCapNhat=false;\nasync function dvcbCapNhatTrangThaiKhiDangChay\(j\)\{.*?\n\}\n", html, re.S).group(0)
assert "dvcbCapNhatTrangThaiKhiDangChay(j);" in html and "dvcbKhoaCapNhat='';" in html
js = fn + """
const box={scrollTop:0};
const document={getElementById:id=>id==='dvcbCoList'?box:null};
let taiLai=0,ve=0;
async function dvcbTaiTrangThaiCqt(){taiLai++;}
function dvcbRenderCoList(giu){ve++;if(giu!==true)throw new Error('phải giữ lựa chọn');box.scrollTop=0;}   // vẽ lại làm mất vị trí cuộn
(async()=>{
  const kq=[];
  const it=(t)=>({trang_thai:t});
  box.scrollTop=240;
  await dvcbCapNhatTrangThaiKhiDangChay({done:0,items:[it('đang xử lý')]});                  kq.push([taiLai,ve,box.scrollTop]);   // chưa công ty nào xong
  await dvcbCapNhatTrangThaiKhiDangChay({done:1,items:[it('xong'),it('đang xử lý')]});          kq.push([taiLai,ve,box.scrollTop]);   // xong 1 -> cập nhật, giữ vị trí cuộn
  await dvcbCapNhatTrangThaiKhiDangChay({done:1,items:[it('xong'),it('đang tải file DVC: 1/3')]}); kq.push([taiLai,ve]);          // không đổi -> không tải lại
  await dvcbCapNhatTrangThaiKhiDangChay({done:2,items:[it('xong'),it('sai mật khẩu / lỗi đăng nhập')]}); kq.push([taiLai,ve]);   // thêm 1 công ty (lỗi) -> cập nhật
  console.log(JSON.stringify(kq));
})();
"""
with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as fh:
    fh.write(js)
out = subprocess.run(["node", fh.name], capture_output=True, text=True, timeout=30)
assert out.returncode == 0, out.stderr
kq = json.loads(out.stdout.strip())
assert kq[0] == [1, 1, 240], kq        # lần đầu: đồng bộ 1 lần (chưa công ty nào xong)
assert kq[1] == [2, 2, 240], kq        # xong 1 công ty -> cập nhật tick, giữ vị trí cuộn
assert kq[2] == [2, 2], kq             # không đổi -> không tải lại
assert kq[3] == [3, 3], kq             # thêm 1 công ty (lỗi đăng nhập) -> cập nhật
print("PASS: tick/màu cập nhật ngay khi xong từng công ty (giữ lựa chọn + vị trí cuộn); không đổi thì không tải lại.")
