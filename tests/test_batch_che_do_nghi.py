import os, sys, re, json, subprocess, tempfile, threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Chế độ nghỉ (tra cứu hàng loạt): xong 1 công ty thì nghỉ ngẫu nhiên 3–5 phút (tuỳ chọn) rồi mới xử lý công ty khác.
nghi = []
dong_ho = [1000.0]
server.time.time = lambda: dong_ho[0]
server.time.sleep = lambda s: None
def _ngu(giay, cancel_check=None):
    nghi.append(giay); dong_ho[0] += giay
server._ngu_ktra_huy = _ngu
server._xoa_loi_tra_cuu = lambda cid: None
server._luu_loi_tra_cuu = lambda cid, t: None
server._batch_luu_db = lambda *a, **k: None
server._mo_trinh_duyet_captcha = lambda: None
server._dong_trinh_duyet_captcha = lambda d: None
server._lam_moi_toan_bo_ket_noi = lambda ly_do="": (0, 0)
server._lam_moi_ket_noi_tu_dong = lambda ly_do: None
server._canh_gac_treo = lambda *a, **k: None
class FakeClient:
    token = "T"
    def _dung_lai_session(self, ep_http11=False): pass
server.get_client = lambda cid: FakeClient()
server._new_fetch_job = lambda: {"messages": [], "last": None, "running": True, "cancel": False, "limiter": server.DynamicLimiter(1)}
thu_tu = []
def fake_run(cid, body):
    thu_tu.append(("chay", cid, len(nghi)))
    server.FETCH_JOBS[cid]["last"] = {"stage": "done", "text": "ok", "total_saved": 1}
server._run_fetch_job = fake_run

def dung(bid, n):
    items = {c: server._batch_item_moi(c, f"CT{c}") for c in range(1, n + 1)}
    server.BATCH_JOBS[bid] = {"items": items, "total": n, "done": 0, "running": True, "cancel": False,
                              "limiter": server.DynamicLimiter(1), "trang_thai": "dang_chay"}
    return server.BATCH_JOBS[bid]

# 1) bật nghỉ 3–5 phút, 1 luồng: 4 công ty -> nghỉ 3 lần (công ty cuối không nghỉ), mỗi lần 180..300s, công ty sau chạy SAU khi nghỉ
b = dung(1, 4)
server._run_batch(1, [1, 2, 3, 4], {"so_luong": 1, "nghi_giua_tu_phut": 3, "nghi_giua_den_phut": 5})
nghi_cong_ty = [g for g in nghi if 180 <= g <= 300]
assert len(nghi_cong_ty) == 3, nghi
assert [t[2] for t in thu_tu] == [0, 1, 2, 3], thu_tu        # công ty thứ k bắt đầu sau đúng k-1 lần nghỉ
assert all(it["status"] == "done" for it in b["items"].values()) and not b["nghi_ds"]
print("PASS 1: xong mỗi công ty nghỉ 3–5 phút rồi mới sang công ty tiếp; công ty cuối không nghỉ.")

# 2) tắt chế độ nghỉ -> không nghỉ
nghi.clear(); thu_tu.clear()
dung(2, 3)
server._run_batch(2, [1, 2, 3], {"so_luong": 1})
assert not [g for g in nghi if g >= 60], nghi
print("PASS 2: không bật chế độ nghỉ thì chạy liền như cũ.")

# 3) công ty chưa lưu mật khẩu (không tra cứu qua mạng) -> không nghỉ sau nó
nghi.clear(); thu_tu.clear()
server._tu_dong_lay_so_du_dau_ky_va_tinh_vat = lambda cid, tu, den: ("", "")
server._tu_dong_ket_xuat_bao_cao = lambda *a, **k: None
class ChuaDangNhap(FakeClient):
    token = None
server.get_client = lambda cid: ChuaDangNhap() if cid == 1 else FakeClient()
server._tu_dong_dang_nhap = lambda cid, **k: (False, "Công ty chưa lưu mật khẩu — không thể tự đăng nhập", 0, [])
b = dung(3, 3)
server._run_batch(3, [1, 2, 3], {"so_luong": 1, "nghi_giua_tu_phut": 3, "nghi_giua_den_phut": 5})
assert b["items"][1]["status"] == "done" and b["items"][1].get("khong_goi_thue")
assert len([g for g in nghi if 180 <= g <= 300]) == 1, nghi        # chỉ nghỉ sau công ty 2 (công ty 3 là cuối)
print("PASS 3: công ty chưa lưu mật khẩu không tra cứu qua mạng -> không nghỉ sau nó.")

# 4) giá trị nhập sai được kẹp 0..60, đến < từ thì lấy bằng từ
server.get_client = lambda cid: FakeClient()
nghi.clear()
dung(4, 2)
server._run_batch(4, [1, 2], {"so_luong": 1, "nghi_giua_tu_phut": 90, "nghi_giua_den_phut": "abc"})
assert [g for g in nghi if g >= 60] == [3600.0], nghi
print("PASS 4: giới hạn 0..60 phút; giá trị không hợp lệ không làm lỗi.")

# 5) giao diện: ô chọn + gửi đúng tham số + nhớ lựa chọn
html = open(os.path.join(os.path.dirname(server.__file__), "static", "index.html"), encoding="utf-8").read()
assert 'id="bCheDoNghi"' in html and 'id="bNghiTu"' in html and 'id="bNghiDen"' in html and "...bCheDoNghiGiaTri()" in html
fn = re.search(r"function bCheDoNghiGiaTri\(\)\{.*?\n\}\n", html, re.S).group(0)
js = """const el={bCheDoNghi:{checked:true},bNghiTu:{value:'3'},bNghiDen:{value:'5'}};
const document={getElementById:id=>el[id]};""" + fn + """
const a=bCheDoNghiGiaTri(); el.bNghiDen.value='2'; const b=bCheDoNghiGiaTri(); el.bCheDoNghi.checked=false; const c=bCheDoNghiGiaTri();
console.log(JSON.stringify([a,b,c]));"""
with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as fh:
    fh.write(js)
out = subprocess.run(["node", fh.name], capture_output=True, text=True, timeout=30)
a, b2, c = json.loads(out.stdout.strip())
assert a == {"nghi_giua_tu_phut": 3, "nghi_giua_den_phut": 5} and b2 == {"nghi_giua_tu_phut": 3, "nghi_giua_den_phut": 3}
assert c == {"nghi_giua_tu_phut": 0, "nghi_giua_den_phut": 0}
print("PASS 5: giao diện gửi đúng khoảng phút nghỉ (tắt = 0), lựa chọn được nhớ.")
print("ALL DONE")
