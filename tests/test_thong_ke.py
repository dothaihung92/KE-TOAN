import json, os, sqlite3, sys, tempfile
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server, thong_ke
from fastapi import HTTPException
# Báo cáo thống kê (Phiếu 01/DN-ĐP): số liệu tháng trước từ hoá đơn bán ra; tài khoản riêng từng công ty; mã dùng 1 lần cho tiện ích. DỮ LIỆU GIẢ.
server.DATA_DIR = tempfile.mkdtemp()
conn = sqlite3.connect(":memory:", check_same_thread=False); conn.row_factory = sqlite3.Row
conn.execute("CREATE TABLE companies (id INTEGER, ten TEXT, mst TEXT)")
conn.execute("INSERT INTO companies VALUES (1,'CTY A','0315502878'), (2,'CTY B','0100000002')")
conn.execute("CREATE TABLE invoices (company_id INTEGER, loai TEXT, tdlap TEXT, shdon TEXT, tgtcthue REAL, tthai TEXT, raw TEXT, detail_json TEXT)")
def hd(cid, ngay, so, ct, dong):
    conn.execute("INSERT INTO invoices VALUES (?,?,?,?,?,?,?,?)", (cid, "sold", ngay, so, ct, "1", "{}", json.dumps({"hdhhdvu": dong})))
hd(1, "2026-10-05T00:00:00", "1", 10_000_000, [{"ten": "Cá tra phi lê", "dvtinh": "Kg", "sl": "100", "thtien": "6000000"}, {"ten": "Cá  tra phi lê", "dvtinh": "kg", "sl": "50", "thtien": "4000000"}])
hd(1, "2026-10-20T00:00:00", "2", 5_500_000, [{"ten": "Tôm khô", "dvtinh": "Kg", "sl": "10", "thtien": "5500000"}])
hd(1, "2026-11-02T00:00:00", "3", 99_000_000, [{"ten": "Khác tháng", "dvtinh": "Kg", "sl": "1", "thtien": "99000000"}])
hd(2, "2026-10-05T00:00:00", "9", 7_000_000, [{"ten": "Của công ty B", "dvtinh": "c", "sl": "1", "thtien": "7000000"}])
conn.execute("INSERT INTO invoices VALUES (1,'purchase','2026-10-06T00:00:00','8',3000000,'1','{}','{}')")
class K:
    def execute(self, *a): return conn.execute(*a)
    def commit(self): conn.commit()
    def close(self): pass
server.db = lambda: K()
assert thong_ke.thang_truoc(1, 2027) == (12, 2026) and thong_ke.thang_truoc(11, 2026) == (10, 2026)
r = server.tk_so_lieu(1, 11, 2026)      # phiếu tháng 11 -> số liệu tháng 10
assert r["thang_so_lieu"] == 10 and r["so_hd"] == 2 and r["doanh_thu_trieu"] == 15.5, r
sp = {x["ten"]: x for x in r["sp"]}
assert sp["Cá tra phi lê"]["sl"] == 150 and sp["Cá tra phi lê"]["gia_tri_trieu"] == 10.0 and sp["Tôm khô"]["gia_tri_trieu"] == 5.5 and len(r["sp"]) == 2, r
assert server.tk_so_lieu(2, 11, 2026)["doanh_thu_trieu"] == 7.0
print("PASS 1: số liệu tháng trước từ HĐ bán ra, gộp sản phẩm cùng tên+ĐVT, đúng từng công ty, bỏ HĐ mua/tháng khác.")
c1 = server.tk_cau_hinh(1)
assert c1["user"] == "0315502878" and c1["mac_dinh_mk"] is True
server.tk_luu_cau_hinh(1, {"pass": "MatKhau@1", "phieu": {"nguoi_ghi": "Nguyễn A", "chuc_vu": "Kế toán", "dien_thoai": "0909", "lao_dong_cuoi_thang_truoc": "3", "x_la": "bo"}})
c1 = server.tk_cau_hinh(1)
assert c1["co_mat_khau"] and "pass" not in c1 and c1["phieu"] == {"nguoi_ghi": "Nguyễn A", "chuc_vu": "Kế toán", "dien_thoai": "0909", "lao_dong_cuoi_thang_truoc": "3"}, c1
assert server.tk_cau_hinh(2)["co_mat_khau"] is False                 # công ty khác không dùng chung tài khoản
print("PASS 2: tài khoản/ô nhập lưu riêng từng công ty, không trả mật khẩu, bỏ khoá lạ.")
server.webbrowser.open = lambda url, new=2: MO.append(url) or True
server._san_chrome = lambda: (None, None)
MO = []
r = server.tk_mo(1, {"thang": 11, "nam": 2026, "phieu": {"so_ngay_hoat_dong": "22"}})
ma = MO[-1].split("kt=")[1].split("&")[0]
assert "MatKhau" not in MO[-1] and MO[-1].startswith("https://gtsphcm.cosis.vn/Phieu1CN_DN#ketoan-thongke")
p = server.tk_mot_lan(ma)
assert p["user"] == "0315502878" and p["pass"] == "MatKhau@1" and p["phieu"]["so_ngay_hoat_dong"] == "22" and p["phieu"]["nguoi_ghi"] == "Nguyễn A" and p["so_lieu"]["doanh_thu_trieu"] == 15.5, p
try: server.tk_mot_lan(ma); raise SystemExit("mã chỉ dùng 1 lần")
except HTTPException as e: assert e.status_code == 404
server.tk_mo(2, {"thang": 11, "nam": 2026}); p2 = server.tk_mot_lan(MO[-1].split("kt=")[1].split("&")[0])
assert p2["user"] == "0100000002" and p2["pass"] == "0100000002", p2         # chưa lưu mật khẩu -> mặc định = MST (theo hướng dẫn của hệ thống)
print("PASS 3: mở trang bằng mã dùng 1 lần (không lộ mật khẩu trên địa chỉ); mặc định tài khoản/mật khẩu = MST.")
print("\nALL DONE")

# --- không có hoá đơn: điền số ước tính hợp lý, ổn định, khớp tổng ---
r = thong_ke.lap_so_lieu({"doanh_thu_trieu": 0, "sp": []}, ["Cá tra phi lê", "Tôm"], 7, 5, 2026)
assert r["gia_lap"] and 80 <= r["doanh_thu_trieu"] <= 400, r
assert len(r["sp"]) == 2 and abs(sum(x["gia_tri_trieu"] for x in r["sp"]) - r["doanh_thu_trieu"]) < 0.01 and all(x["sl"] > 0 for x in r["sp"]), r
assert r == thong_ke.lap_so_lieu({"doanh_thu_trieu": 0, "sp": []}, ["Cá tra phi lê", "Tôm"], 7, 5, 2026)
thật = {"doanh_thu_trieu": 12.5, "sp": [{"ten": "A", "sl": 3, "gia_tri_trieu": 12.5}]}
assert "gia_lap" not in thong_ke.lap_so_lieu(thật, ["A"], 7, 5, 2026)
print("PASS lập số liệu ước tính")
