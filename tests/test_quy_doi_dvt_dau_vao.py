import os, sys, sqlite3, tempfile
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Yêu cầu: Bảng kê / Nhập liệu ĐẦU VÀO có 3 cột QUY ĐỔI (ĐVT, Số lượng, Đơn giá) — tờ khai nhập theo THÙNG, nhập kho/bán theo CHAI.
Khi người dùng điền, các bước tạo chứng từ (Mua hàng, Danh mục hàng hoá) dùng thông tin QUY ĐỔI thay cho ĐVT/SL/Đơn giá trên hoá đơn/tờ khai."""
sys.path.insert(0, _REPO_ROOT)
import server

_db_path = tempfile.mktemp(suffix=".sqlite3")
server.DATA_DIR = tempfile.mkdtemp()


def db_factory():
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    return conn


server.db = db_factory
conn = db_factory()
conn.execute("CREATE TABLE companies (id INTEGER PRIMARY KEY, mst TEXT, save_dir TEXT, data_dir TEXT)")
conn.execute("INSERT INTO companies VALUES (1,'0300000001','','')")
conn.commit(); conn.close()

QD = server.QUY_DOI_COT
assert QD == ["ĐVT quy đổi", "Số lượng quy đổi", "Đơn giá quy đổi"]
H = ["Ký hiệu", "Số HĐ", "Ngày", "Người bán", "MST bán", "Tên hàng hóa/dịch vụ", "ĐVT", "Số lượng", "Đơn giá",
     "Thành tiền", "Thuế suất", "Tiền thuế GTGT", "Nợ", "Có"] + QD
TEN = "Dầu gội trị ve Tick & Flea Dog Shampoo 300ml, 12pcs/carton"


def dong(sl_qd="", dg_qd="", dvt_qd=""):
    return ["TKNK", "107853592600", "06/01/2026", "KING STELLA", "KING STELLA", TEN, "UNK", 35, 268461, 9396147, "8%", 751692,
            "1561", "331", dvt_qd, sl_qd, dg_qd]


# 1) không điền quy đổi -> giữ nguyên (cùng đối tượng, không sao chép)
rows0 = [dong()]
assert server._ap_quy_doi_nhap_lieu(H, rows0) is rows0
# header không có cột quy đổi -> giữ nguyên
assert server._ap_quy_doi_nhap_lieu(H[:14], [r[:14] for r in rows0]) is not None
print("PASS 1: chưa điền quy đổi thì dữ liệu giữ nguyên.")

# 2) điền đủ 3 ô
r = server._ap_quy_doi_nhap_lieu(H, [dong(420, 22371.75, "Chai")])[0]
assert (r[6], r[7], r[8], r[9]) == ("Chai", 420, 22371.75, 9396147), r       # Thành tiền KHÔNG đổi
# 3) chỉ điền ĐVT + Số lượng -> Đơn giá = Thành tiền / SL quy đổi
r = server._ap_quy_doi_nhap_lieu(H, [dong(420, "", "Chai")])[0]
assert r[6] == "Chai" and r[7] == 420 and abs(r[8] * 420 - 9396147) < 1, r
# 4) chỉ điền ĐVT -> SL/ĐG gốc
r = server._ap_quy_doi_nhap_lieu(H, [dong("", "", "Chai")])[0]
assert (r[6], r[7], r[8]) == ("Chai", 35, 268461), r
print("PASS 2: điền đủ/thiếu từng ô đều lấy đúng (Đơn giá tự = Thành tiền / SL quy đổi; Thành tiền giữ nguyên).")

# 5) Mua hàng NK dùng ĐVT/SL/ĐG quy đổi (không dùng 'UNK', 35, 268.461)
flat = server._gen_mua_hang_nk(1, H, [dong(420, "", "Chai")])
hd = server.MUA_NK_HEADERS
assert flat, "không sinh dòng Mua hàng"
f = flat[0]
assert f[hd.index("ĐVT")] == "Chai" and float(f[hd.index("Số lượng")]) == 420, (f[hd.index("ĐVT")], f[hd.index("Số lượng")])
assert abs(float(f[hd.index("Đơn giá")]) * 420 - 9396147) < 2, f[hd.index("Đơn giá")]
assert float(f[hd.index("Thành tiền")]) == 9396147
flat0 = server._gen_mua_hang_nk(1, H, [dong()])
assert flat0[0][hd.index("ĐVT")] == "UNK" and float(flat0[0][hd.index("Số lượng")]) == 35
print("PASS 3: Mua hàng NK lấy ĐVT/Số lượng/Đơn giá QUY ĐỔI; không điền thì như cũ.")

# 6) Danh mục hàng hoá/VTHH dùng ĐVT quy đổi
dm, _ = server._gen_danh_muc(1, "hh", H, [dong(420, "", "Chai")])
assert any("Chai" in [str(x) for x in r] for r in dm) and not any("UNK" in [str(x) for x in r] for r in dm), dm
vt = server._gen_vthh_from_grid(1, H, [dong(420, "", "Chai")])
assert all(v[3] == "Chai" for v in vt) and vt, vt
print("PASS 4: danh mục hàng hoá/VTHH lấy ĐVT quy đổi.")

# 7) Bảng kê xuất Excel: 3 cột quy đổi nằm CUỐI (sau Nợ/Có, không làm lệch cột T/U), dòng pad đủ
src = open(os.path.join(_REPO_ROOT, "server.py"), encoding="utf-8").read()
assert '"Nợ", "Có"] + QUY_DOI_COT' in src and "vals.extend([\"\"] * len(QUY_DOI_COT))" in src
print("PASS 5: Bảng kê Chi tiết MUA VÀO có 3 cột quy đổi ở cuối (V, W, X).")

# 8) lưới Nhập liệu tự thêm 3 cột cho đầu vào
html = open(os.path.join(_REPO_ROOT, "static", "index.html"), encoding="utf-8").read()
assert "'ĐVT quy đổi','Số lượng quy đổi','Đơn giá quy đổi'" in html and "nhapLieuLoaiHienTai==='in'" in html
print("PASS 6: lưới Nhập liệu Đầu vào tự thêm 3 cột quy đổi.")
