import json, base64, io, os, sys, tempfile, time
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import openpyxl
import server
from fastapi import HTTPException

# API lấy sao kê tự động: mở ngân hàng (không mở trình duyệt thật trong test) -> chờ file mới trong Downloads -> đọc -> trả văn bản TAB.
dl, dt = tempfile.mkdtemp(), tempfile.mkdtemp()
server._san_thu_muc_downloads = lambda: dl
server._get_desktop_dir = lambda: dt
server._san_chrome = lambda: (None, None)
MO = []
server.webbrowser.open = lambda url, new=2: MO.append(url) or True
server.DATA_DIR = tempfile.mkdtemp(); server.DB_PATH = os.path.join(server.DATA_DIR, 't.db')
try:
    server.init_db()
except Exception:
    pass


class _R:
    def __init__(self, f, *a, **k):
        try:
            self._j, self.status_code = f(*a, **k), 200
        except HTTPException as e:
            self._j, self.status_code = {"detail": e.detail}, e.status_code

    def json(self):
        return self._j


class c:
    @staticmethod
    def get(path, params=None):
        return _R({"/api/ngan-hang/danh-sach": lambda: server.nh_danh_sach(), "/api/ngan-hang/file-moi": lambda: server.nh_file_moi(**params)}[path])

    @staticmethod
    def post(path, json=None):
        return _R({"/api/ngan-hang/mo": lambda: server.nh_mo(json), "/api/ngan-hang/doc-file": lambda: server.nh_doc_file(json)}[path])

ds = c.get("/api/ngan-hang/danh-sach").json()
assert [x["ma"] for x in ds["ngan_hang"]] == ["vcb", "acb", "vtb", "tcb"], ds
assert c.post("/api/ngan-hang/mo", json={"ngan_hang": "vcb", "tu": "2026-09-30", "den": "2026-09-01"}).status_code == 400
assert c.post("/api/ngan-hang/mo", json={"ngan_hang": "vcb", "tu": "2026-09-01", "den": "2026-09-30", "url": "http://x"}).status_code == 400

open(os.path.join(dl, "cu.xlsx"), "wb").write(b"PK")                 # file CŨ có sẵn trước khi mở ngân hàng: bỏ qua
os.utime(os.path.join(dl, "cu.xlsx"), (time.time() - 3600, time.time() - 3600))
r = c.post("/api/ngan-hang/mo", json={"ngan_hang": "vcb", "tu": "2026-09-01", "den": "2026-09-30", "mst": "0314948317", "acc": "main"}).json()
j = r["j"]
assert MO and "#ketoan-saoke=vcb_2026-09-01_2026-09-30&j=" + j in MO[-1] and MO[-1].startswith("https://vcbdigibiz.vietcombank.com.vn/"), MO
assert c.get("/api/ngan-hang/file-moi", params={"j": j}).json()["co"] is False

open(os.path.join(dl, "SaoKe.xlsx.crdownload"), "wb").write(b"x")
assert c.get("/api/ngan-hang/file-moi", params={"j": j}).json()["dang_tai"] is True
os.remove(os.path.join(dl, "SaoKe.xlsx.crdownload"))
open(os.path.join(dl, "hinh.xlsx"), "wb").write(b"PK\x03\x04rac")       # file mới nhưng không phải sao kê: báo lỗi, không lặp lại
k = c.get("/api/ngan-hang/file-moi", params={"j": j}).json()
assert k["co"] is False and k["loi"], k
assert not c.get("/api/ngan-hang/file-moi", params={"j": j}).json()["loi"]

wb = openpyxl.Workbook(); ws = wb.active
for row in [["VIETCOMBANK"], ["Số tài khoản: 0071001234567"], ["Ngày giao dịch", "Số tham chiếu", "Ghi nợ", "Ghi có", "Số dư", "Mô tả"],
            ["02/09/2026", "R1", "15,053,400", None, "1", "THANH TOAN HD 1749"], ["05/10/2026", "R2", None, "100", "2", "LAI"]]:
    ws.append(row)
wb.save(os.path.join(dl, "SaoKe_VCB.xlsx"))
k = c.get("/api/ngan-hang/file-moi", params={"j": j}).json()
assert k["co"] and k["so_gd"] == 2 and k["so_tk"] == "0071001234567" and k["acc"] == "main", k
assert "02/09/2026\tTHANH TOAN HD 1749\t15053400\t" in k["tsv"] and any("ngoài khoảng" in x for x in k["canh_bao"]), k
assert os.listdir(os.path.join(server.DATA_DIR, "sao_ke_nh", "0314948317")), "lưu bản sao file sao kê"
assert c.get("/api/ngan-hang/file-moi", params={"j": j}).json()["so_gd"] == 2       # hỏi lại vẫn trả kết quả
assert c.get("/api/ngan-hang/file-moi", params={"j": "khong-co"}).status_code == 404
print("PASS 1: mở ngân hàng có dấu #ketoan-saoke; bỏ file cũ/đang tải/không phải sao kê; đọc file mới; cảnh báo ngoài khoảng ngày.")

b = open(os.path.join(dl, "SaoKe_VCB.xlsx"), "rb").read()
k = c.post("/api/ngan-hang/doc-file", json={"ten": "a.xlsx", "du_lieu": base64.b64encode(b).decode()}).json()
assert k["so_gd"] == 2 and k["ngan_hang"] == "Vietcombank", k
assert c.post("/api/ngan-hang/doc-file", json={"ten": "a.xlsx", "du_lieu": base64.b64encode(b"abc").decode()}).status_code == 400
print("PASS 2: đọc file sao kê người dùng tự chọn.")

# mã dùng 1 lần lấy tài khoản internet banking đã lưu trong thông tin công ty (để tiện ích tự điền ô đăng nhập)
cn = server.db()
cn.execute("INSERT INTO companies (ten, mst, username, password, bank_accounts, created_at) VALUES ('A','0314948317','u','p',?, '2026-01-01')",
           (json.dumps([{"bank": "acb", "stk": "123456789", "user": "ib_user", "pass": "ib_pass"}, {"bank": "vcb", "stk": "999", "user": "", "pass": ""}]),))
cn.commit(); cn.close()
r = c.post("/api/ngan-hang/mo", json={"ngan_hang": "acb", "tu": "2026-10-01", "den": "2026-10-31", "mst": "0314948317", "stk": "123 456 789"}).json()
ma = MO[-1].split("&kt=")[1]
assert ma and "ib_pass" not in MO[-1] and "ib_user" not in MO[-1]
assert server.nh_tk_mot_lan(ma) == {"user": "ib_user", "pass": "ib_pass"}
try: server.nh_tk_mot_lan(ma); raise SystemExit("mã chỉ dùng 1 lần")
except HTTPException as e: assert e.status_code == 404
c.post("/api/ngan-hang/mo", json={"ngan_hang": "vcb", "tu": "2026-10-01", "den": "2026-10-31", "mst": "0314948317", "stk": "999"})
assert "&kt=" not in MO[-1], "tài khoản chưa có tên đăng nhập/mật khẩu -> không tạo mã"
print("PASS 3: mã dùng 1 lần cho tài khoản NH đã lưu; không lộ mật khẩu trên địa chỉ; dùng xong hết hiệu lực.")
print("\nALL DONE")
