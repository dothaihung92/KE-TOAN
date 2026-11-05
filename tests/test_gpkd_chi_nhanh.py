import io, os, sys, zipfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import docx
import gpkd_soan as g
import server

# Hồ sơ thay đổi hoạt động CHI NHÁNH / VPĐD (Mẫu 19). Dữ liệu giả.
DU = {"la_chi_nhanh": True, "loai": ["ten", "dia_chi", "nganh", "dai_dien"],
      "dn": {"ten": "CÔNG TY TNHH GIẢ", "ma_so": "0300000001", "co_quan": "Phòng ĐKKD", "so_vb": "01", "ngay_lap": "05/11/2026"},
      "hien_tai": {"dd_ho_ten": "NGUYỄN AAA"}, "cn": {"kieu": "chi_nhanh", "ten": "CHI NHÁNH GIẢ", "ma_so": "0300000001-001"},
      "ten": {"viet": "CHI NHÁNH MỚI"}, "dia_chi": {"so_nha": "1 Đường A", "xa": "Phường B", "tinh": "TP C"},
      "nganh": {"ds": [{"ma": "4610", "ten": "Đại lý", "chinh": True}], "noi_dung": "Giao dịch"},
      "dai_dien": [{"ho_ten": "Trần BBB", "ngay_sinh": "01/02/1985", "gioi_tinh": "Nữ", "cccd": "079000000009", "dia_chi": "2 Đường B, Phường C, TP D"}]}

def van_ban(d):
    t = [p.text for p in d.paragraphs]
    for b in d.tables:
        for r in b.rows:
            t += [c.text for c in r.cells]
    return "\n".join(t)

def tao(du):
    z, ten, cb = g.tao_ho_so(du, None, False)
    zf = zipfile.ZipFile(io.BytesIO(z))
    return {n: docx.Document(io.BytesIO(zf.read(n))) for n in zf.namelist() if n.endswith(".docx")}, ten, cb

f, ten, cb = tao(DU)
assert ten.startswith("Ho_so_chi_nhanh_") and any(n.startswith("Mau19_") for n in f) and "00_Danh_muc_ho_so_chi_nhanh.docx" in f
t = van_ban(next(v for k, v in f.items() if k.startswith("Mau19_")))
for x in ("CÔNG TY TNHH GIẢ", "0300000001-001", "CHI NHÁNH GIẢ", "CHI NHÁNH MỚI", "1 Đường A", "TRẦN BBB", "079000000009", "4610", "NGUYỄN AAA"):
    assert x in t, x
assert "chi nhánh/văn phòng đại diện" not in t.lower().replace("\n", " ").replace("  ", " ") or "ĐĂNG KÝ THAY ĐỔI NỘI DUNG ĐĂNG KÝ HOẠT ĐỘNG CHI NHÁNH" in t
assert "Nội dung hoạt động sau khi thay đổi" not in t            # chi nhánh: không có phần nội dung hoạt động (chỉ VPĐD)
print("PASS 1: Mẫu 19 chi nhánh điền đủ tên/mã/địa chỉ/ngành/người đứng đầu.")

du = dict(DU, cn=dict(DU["cn"], kieu="vpdd"))
f, ten, cb = tao(du)
t = van_ban(next(v for k, v in f.items() if k.startswith("Mau19_")))
assert "văn phòng đại diện" in t and "Giao dịch" in t and "Đại lý" not in t     # VPĐD: nội dung hoạt động, không có bảng ngành
print("PASS 2: văn phòng đại diện: ghi nội dung hoạt động, không bảng ngành.")

du = dict(DU, loai=["bo_sung"], bo_sung={"noi_dung": "Cập nhật số điện thoại"})
f, ten, cb = tao(du)
t = van_ban(next(v for k, v in f.items() if k.startswith("Mau19_")))
assert "Cập nhật số điện thoại" in t and "CHI NHÁNH MỚI" not in t
du = dict(DU, cn={}, loai=["ten"])
f, ten, cb = tao(du)
assert any("Còn thiếu" in c and "Tên chi nhánh" in c for c in cb)
print("PASS 3: mục B và cảnh báo thiếu thông tin.")

# lưu dữ liệu gom RIÊNG cho chi nhánh, không lẫn với công ty
store = {}
server._get_setting = lambda k, d="": store.get(k, d)
server._set_setting = lambda k, v: store.__setitem__(k, v)
server.gpkd_du_lieu_luu(5, {"khoi": [{"khoi": "CTY"}]})
server.gpkd_du_lieu_luu(5, {"khoi": [{"khoi": "CN1"}, {"khoi": "CN2"}]}, loai="cn")
assert [k["khoi"] for k in server.gpkd_du_lieu_doc(5)["khoi"]] == ["CTY"] and len(server.gpkd_du_lieu_doc(5, loai="cn")["khoi"]) == 2
html = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "index.html"), encoding="utf-8").read()
for k in ("3. Lấy thông tin GPKD CN", "4. Soạn hồ sơ CN", "moSoanCn()", "?loai=cn"):
    assert k in html, k
print("PASS 4: dữ liệu gom chi nhánh lưu riêng; giao diện có 2 tab mới.")

# Hình thức hạch toán: chọn gì thì đánh dấu X đúng ô đó (Mẫu 19 dùng ô ☐)
def tick_hach(hach):
    f, _t, _c = tao(dict(DU, loai=["thue"], thue={"hach_toan": hach}))
    d = next(v for k, v in f.items() if k.startswith("Mau19_"))
    t = "".join(x.text or "" for x in d.element.body.iter(docx.oxml.ns.qn("w:t")))
    i = t.find("Hình thức hạch toán")
    return t[i:i + 500]
t1, t2 = tick_hach("Phụ thuộc"), tick_hach("Độc lập")
assert "Hạch toán phụ thuộc☒" in t1 and "Hạch toán độc lập☐" in t1
assert "Hạch toán độc lập☒" in t2 and "Hạch toán phụ thuộc☐" in t2
print("PASS 5: hạch toán phụ thuộc/độc lập đánh X đúng ô trong Mẫu 19.")

# người ký mặc định = giám đốc/người đại diện công ty mẹ khi chưa nhập
import sqlite3
conn = sqlite3.connect(":memory:", check_same_thread=False); conn.row_factory = sqlite3.Row
conn.execute("CREATE TABLE companies (id INTEGER, nguoi_ky TEXT)"); conn.execute("INSERT INTO companies VALUES (9, 'Lê Giám Đốc')")
class K:
    def execute(self, *a): return conn.execute(*a)
    def commit(self): pass
    def close(self): pass
server.db = lambda: K()
import tempfile
server._get_desktop_dir = lambda: tempfile.mkdtemp()
r = server.gpkd_soan_tao({"cid": 9, "du_lieu": dict(DU, hien_tai={})})
zf = zipfile.ZipFile(io.BytesIO(r.body))
mau = docx.Document(io.BytesIO(zf.read(next(n for n in zf.namelist() if n.startswith("Mau19_")))))
assert "LÊ GIÁM ĐỐC" in van_ban(mau)
print("PASS 6: người ký hồ sơ chi nhánh mặc định là người ký của công ty mẹ.")
