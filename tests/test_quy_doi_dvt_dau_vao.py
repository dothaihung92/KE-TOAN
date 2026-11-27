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
assert '"Nợ", "Có"] + QUY_DOI_COT' in src and "[\"\"] * len(QUY_DOI_COT)" in src
print("PASS 5: Bảng kê Chi tiết MUA VÀO có 3 cột quy đổi ở cuối (V, W, X).")

# 8) lưới Nhập liệu tự thêm 3 cột cho đầu vào
html = open(os.path.join(_REPO_ROOT, "static", "index.html"), encoding="utf-8").read()
assert "'ĐVT quy đổi','Số lượng quy đổi','Đơn giá quy đổi'" in html and "nhapLieuLoaiHienTai==='in'" in html
print("PASS 6: lưới Nhập liệu Đầu vào tự thêm 3 cột quy đổi.")

# ===== TỰ QUY ĐỔI theo mô tả tờ khai =====
f = server._quy_doi_tu_mo_ta_tokhai
assert f("Dầu gội BEARING 300ml, 12pcs/carton, mã CAS: 61789-40-0", "UNK", 35, 9396147) == ("Chai", 420, round(9396147 / 420, 2))
assert f("Xịt khử mùi 600ml, 12pcs/carton", "UNK", 37, 18026681)[:2] == ("Chai", 444)
assert f("Hộp 24 bottles per carton", "CTN", 10, 2400000)[:2] == ("Chai", 240)
assert f("Carton of 6 pcs - giá đỡ", "UNK", 5, 300000)[:2] == ("Cái", 30)          # không có ml/lít -> Cái
assert f("Sản phẩm không có thông tin quy đổi", "UNK", 35, 100) is None
assert f("12pcs/carton", "PCE", 35, 100) is None and f("12pcs/carton", "KGM", 35, 100) is None   # ĐVT tờ khai đã là cái/kg -> không nhân
assert f("12pcs/carton", "UNK", 0, 100) is None
print("PASS 7: nhận '12pcs/carton', '24 bottles per carton', 'carton of 6 pcs'...; chỉ quy đổi khi ĐVT tờ khai là thùng/UNK.")

# Nhập liệu: file Bảng kê cũ (chưa có cột quy đổi) -> dòng TKNK tự điền, dòng hoá đơn thường không đổi, ô đã điền tay không bị đè
H2 = H[:14]
hd = [list(r) for r in (dong()[:14], ["C26TAA", "1", "06/01/2026", "NCC", "0311111111", "Hàng thường 12pcs/carton", "UNK", 5, 100, 500, "8%", 40, "1561", "331"])]
hd = [r[:] for r in hd]
n = server._tu_quy_doi_dong_tokhai(H2, hd)
assert n == 1 and H2[-3:] == QD, (n, H2)
assert hd[0][-3:] == ["Chai", 420, round(9396147 / 420, 2)], hd[0]
assert hd[1][-3:] == ["", "", ""], hd[1]                                            # hoá đơn thường (không phải TKNK) không tự quy đổi
dien = [dong(100, 90000, "Lốc")]
assert server._tu_quy_doi_dong_tokhai(H, dien) == 0 and dien[0][-3:] == ["Lốc", 100, 90000]     # đã điền tay -> giữ nguyên
print("PASS 8: Nhập liệu tự điền quy đổi cho dòng TKNK (không đè ô đã điền, không đụng hoá đơn thường).")

src = open(os.path.join(_REPO_ROOT, "server.py"), encoding="utf-8").read()
assert "_quy_doi_tu_mo_ta_tokhai(it.get(\"ten\", \"\"), it.get(\"dvt\", \"\"), sl_tk, round(ds_tk))" in src
print("PASS 9: Bảng kê xuất Excel tự điền quy đổi cho dòng tờ khai.")

# ===== Bảng ĐÃ LƯU từ trước (đã có 3 cột trống): mở lại / đọc lại phải tự điền cho dòng TKNK =====
import json
conn = db_factory()
conn.execute("CREATE TABLE IF NOT EXISTS nhap_lieu (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, loai TEXT, header_json TEXT, rows_json TEXT, updated_at TEXT, UNIQUE(company_id, loai))")
conn.execute("INSERT INTO nhap_lieu (company_id, loai, header_json, rows_json, updated_at) VALUES (1,'in',?,?,'')",
             (json.dumps(H), json.dumps([dong(), dong("", "", "")])))
conn.commit(); conn.close()
d = server.nhap_lieu_get(1, "in")
assert d["rows"][0][-3:] == ["Chai", 420, round(9396147 / 420, 2)], d["rows"][0]
h2, r2 = server._doc_nhap_lieu(1, "in")
assert r2[0][-3:][0] == "Chai"
print("PASS 10: bảng Nhập liệu đã lưu (cột quy đổi đang trống) mở lại là tự điền quy đổi cho dòng tờ khai.")

# ===== Dòng TKNK để trống Nợ phải được điền TK hàng hoá (trước đây bị bỏ qua -> tờ khai không vào MISA) =====
H3 = H[:14]
tk = dong()[:14]; tk[12] = ""; tk[13] = ""
hd = ["C26TAA", "1", "06/01/2026", "NCC", "0311111111", "Hàng thường", "Cái", 2, 100, 200, "8%", 16, "", ""]
moi, ds = server._dien_tk_no_bang_ke_dau_vao(1, H3, [tk, hd])
assert moi[0][12] == "1561" and moi[0][13] == "331", moi[0]
assert any(x[0] == "107853592600" for x in ds), ds
print("PASS 11: dòng TKNK trống Nợ tự điền 1561/331 (không còn bị Import bỏ qua).")

# ===== NCC nước ngoài (tờ khai NK): MST bán = TÊN; MISA lưu mã/tên lệch dấu chấm cuối hoặc mã tự sinh NCC00001 =====
A, B = ("id-A", "KING STELLA GROUP CO., LTD", "KING STELLA GROUP CO., LTD"), ("id-B", "KING STELLA GROUP CO., LTD.", "NCC00001")
ten = {x[1].lower(): x for x in (B, A)}
ten_chuan = {server._chuan_ten_ncc(x[1]): x for x in (B, A)}
ma_chuan = {server._chuan_ten_ncc(x[2]): x for x in (A, B)}
assert server._misa_tra_ncc_theo_ten(ten, ten_chuan, ma_chuan, "KING STELLA GROUP CO., LTD.") == B          # trùng TÊN y hệt (có dấu chấm cuối)
assert server._misa_tra_ncc_theo_ten({}, ten_chuan, ma_chuan, "King Stella Group Co Ltd") is not None          # lệch dấu câu/hoa thường
assert server._misa_tra_ncc_theo_ten({}, {}, ma_chuan, "KING STELLA GROUP CO., LTD.") == A                     # chỉ khớp MÃ (mất dấu chấm cuối)
assert server._misa_tra_ncc_theo_ten(ten, ten_chuan, ma_chuan, "NCC KHÁC") is None
print("PASS 12: NCC tờ khai NK (MST bán = tên) tra được theo tên/mã MISA dù lệch dấu chấm cuối hoặc mã tự sinh.")

# ===== CCDC nhập KHO: Nợ 1531 (kho CCDC) được Mua hàng NK ghi =====
H4 = H[:14]
ke = ["TKNK", "108544302530", "20/08/2026", "KING STELLA GROUP CO., LTD.", "KING STELLA GROUP CO., LTD.", "Kệ 2 tầng bày sản phẩm, 1pcs/carton, Hàng FOC",
      "UNK", 3, 1764620, 5293860, "8%", 423509, "1531", "331"]
hh = ["TKNK", "108544302530", "20/08/2026", "KING STELLA GROUP CO., LTD.", "KING STELLA GROUP CO., LTD.", "Dầu gội 300ml", "UNK", 35, 268461, 9396147,
      "8%", 751692, "1561", "331"]
nk = server._gen_mua_hang_nk(1, H4, [hh, ke])
hd = server.MUA_NK_HEADERS
assert len(nk) == 2, nk
r_ke = [r for r in nk if str(r[hd.index("Tên hàng")]).startswith("Kệ")][0]
assert r_ke[hd.index("Kho")] == "CCDC" and str(r_ke[hd.index("TK kho (*)")]) == "1531", r_ke
assert str(r_ke[hd.index("Mã hàng (*)")]).startswith("CC") and r_ke[hd.index("Thành tiền")] == 5293860 and r_ke[hd.index("Tiền thuế GTGT")] == 423509
assert r_ke[hd.index("Số phiếu nhập (*)")] == [r for r in nk if r is not r_ke][0][hd.index("Số phiếu nhập (*)")]      # cùng tờ khai -> cùng 1 phiếu nhập
r_hh = [r for r in nk if r is not r_ke][0]
assert r_hh[hd.index("Kho")] == "HH" and str(r_hh[hd.index("TK kho (*)")]) == "1561"
ma1 = r_ke[hd.index("Mã hàng (*)")]
assert server._gen_mua_hang_nk(1, H4, [ke])[0][hd.index("Mã hàng (*)")] == ma1          # mã ổn định giữa các lần chạy
assert server._misa_loai_dm_theo_tk("1531") == "ccdc"
ke2 = ke[:]; ke2[12] = "242"
assert len(server._gen_mua_hang_nk(1, H4, [ke2])) == 0 and len(server._gen_mua_hang_kqk(1, H4, [ke2])) == 1       # 242 vẫn là không qua kho
print("PASS 13: Nợ 1531 (kho CCDC) vào Mua hàng NK: kho CCDC, TK kho 1531, mã CCxxxxxx ổn định, cùng phiếu nhập với hàng hoá của tờ khai.")

# ===== Import tự động toàn bộ: chứng từ do phần mềm tạo mà khác Bảng kê thì TỰ cập nhật (không cần bấm Ghi đè tay) =====
class _Cur:
    def __init__(self, row, loi=False): self.row, self.loi = row, loi
    def execute(self, *a, **k):
        if self.loi: raise RuntimeError("x")
        return self
    def fetchone(self): return self.row
cfg = server._MUA_COT["nk"]
dong_ct = lambda tt: [""] * 29 if False else (lambda r: (r.__setitem__(28, tt) or r))([""] * 45)
l15 = [dong_ct(100.0) for _ in range(15)]
assert server._vc_pm_khac_bang_ke(_Cur((14, 1400.0)), "r", l15, cfg) is True        # MISA 14 dòng, Bảng kê 15 dòng
assert server._vc_pm_khac_bang_ke(_Cur((15, 1500.0)), "r", l15, cfg) is False       # khớp -> bỏ qua như cũ
assert server._vc_pm_khac_bang_ke(_Cur((15, 1400.0)), "r", l15, cfg) is True        # đủ dòng nhưng tổng tiền lệch
assert server._vc_pm_khac_bang_ke(_Cur(None, loi=True), "r", l15, cfg) is False     # không đọc được -> không tự gỡ gì
assert "_vc_pm_khac_bang_ke(cur, pu_refid_an, lines, cfg)" in open(os.path.join(_REPO_ROOT, "server.py"), encoding="utf-8").read()
print("PASS 14: Import tự động toàn bộ tự cập nhật chứng từ do phần mềm tạo khi số dòng/tổng tiền khác Bảng kê; khớp hoặc không chắc thì không đụng.")

# ===== Tờ khai NK -> loại chứng từ 'Mua hàng nhập khẩu nhập kho' (không phải 'Mua hàng trong nước nhập kho') =====
class CurRT:
    def __init__(self, names): self.names = names
    def execute(self, sql, *a): return self
    def fetchall(self): return [(i + 1, n) for i, n in enumerate(self.names)]
    def fetchone(self): return None
NAMES = ["Mua hàng trong nước nhập kho - Chưa thanh toán", "Mua hàng nhập khẩu nhập kho - Chưa thanh toán", "Mua hàng trong nước nhập kho - Tiền mặt",
         "Mua hàng nhập khẩu nhập kho - Tiền mặt", "Mua hàng trong nước không qua kho - Chưa thanh toán", "Mua hàng nhập khẩu không qua kho - Chưa thanh toán"]
c = CurRT(NAMES)
assert server._misa_reftype_mua(c, "nk", True, "331") == (2, NAMES[1])
assert server._misa_reftype_mua(c, "nk", False, "331") == (1, NAMES[0])
assert server._misa_reftype_mua(c, "nk", True, "1111") == (4, NAMES[3])
assert server._misa_reftype_mua(c, "kqk", True, "331") == (6, NAMES[5]) and server._misa_reftype_mua(c, "kqk", False, "331") == (5, NAMES[4])
assert server._misa_reftype_mua(CurRT(NAMES[0:1] + NAMES[4:5]), "nk", True, "331")[1] == NAMES[0]      # MISA không có loại nhập khẩu -> lùi về loại thường
assert server._la_nk_ct([0, 1]) is True and server._la_nk_ct([0, 0]) is False and server._la_nk_ct([]) is False
class CurRT2(CurRT):
    def __init__(self, names, rt): super().__init__(names); self.rt, self.q = rt, ""
    def execute(self, sql, *a): self.q = sql; return self
    def fetchone(self): return (self.rt,)
    def fetchall(self): return CurRT.fetchall(self)
first = [0, 1] + [""] * 30
cfgx = {"co": 24}
assert server._vc_pm_sai_reftype(CurRT2(NAMES, 1), "r", "nk", first, cfgx) is True       # đang là 'trong nước' (1) nhưng tờ khai NK cần loại 2
assert server._vc_pm_sai_reftype(CurRT2(NAMES, 2), "r", "nk", first, cfgx) is False
print("PASS 15: tờ khai NK dùng loại chứng từ 'Mua hàng nhập khẩu nhập kho/không qua kho'; chứng từ cũ sai loại sẽ được Import tự động cập nhật.")

# ===== MST người mua: chỉ MST/CCCD thật; tên đăng nhập sàn (kichi2906...) -> trống =====
for ok in ("0317489936", "0317489936-001", "0317489936001", "079301031317", "0 3174 89936"):
    assert server._la_mst_that(ok), ok
for bad in ("kichi2906", "loanh339", "ifz769ztuu", "KL", "", "Khách lẻ", "12345", "0317489936x", "Kháchkhôngcungcấpthôngtinxuấthoáđơn"):
    assert not server._la_mst_that(bad), bad
hd_out = ["Ký hiệu mẫu", "Ký hiệu HĐ", "Số hóa đơn", "Ngày lập", "Tên người mua", "MST người mua", "Mặt hàng", "Doanh số bán chưa thuế", "Thuế GTGT"]
rs, tk = server._gan_mst_theo_ten_doi_tuong_rows(hd_out, [["1", "C26TSG", "659", "21/04/2026", "kichi2906", "kichi2906", "Nước rửa chén", 100, 8],
                                                          ["1", "C26TSG", "660", "21/04/2026", "Cty A", "0312345678", "Nước rửa chén", 100, 8],
                                                          ["1", "C26TSG", "661", "21/04/2026", "tiendmc", "", "Nước rửa chén", 100, 8]], "out", {})
assert [r[5] for r in rs] == ["", "0312345678", ""], rs
assert server._khoa_mst_bk("kichi2906") == "kl" and server._khoa_mst_bk("0312345678") == "0312345678"
print("PASS 16: MST người mua chỉ nhận MST/CCCD thật; tên đăng nhập sàn có chữ số cũng bị bỏ trống (import MISA -> KL).")
