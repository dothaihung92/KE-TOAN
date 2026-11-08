import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Yêu cầu: hàng NHẬP có tên giống hàng đã có trong kho thì LẤY MÃ ĐÓ (kho còn tồn mã nào thì lấy mã đó),
KHÔNG tạo mã mới. Ca thật (TONG_HOP_TON_KHO 7–12/2026): phần mềm vẫn sinh HH00045-8 'Topper Poly 160 * 200 * 7'
dù MH27 còn tồn; HH00031-8 'Ga 1.8mx2m' (hoá đơn ĐVT 'Cái') dù MH78 (kho ĐVT 'PCS') còn tồn 9 —
vì chỉ dò theo Tên+ĐVT trong bản đồ đã học, không tra Tồn kho."""
import sys, sqlite3, tempfile
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

H = ["Ký hiệu", "Số HĐ", "Ngày", "Người bán", "MST bán", "Tên hàng hóa/dịch vụ", "ĐVT", "Số lượng", "Đơn giá",
     "Thành tiền", "Thuế suất", "Tiền thuế GTGT", "Nợ", "Có"]


def dong(ten, dvt, tt=1_000_000, so="0000101"):
    return ["C26TAA", so, "05/10/2026", "NCC A", "0311111111", ten, dvt, 1, tt, tt, 8, tt * 0.08, "1561", "331"]


def ton(ma, ten, dvt, sl):
    return {"ma": ma, "ten": ten, "dvt": dvt, "ton": sl, "gia": 100000, "gia_tri": sl * 100000, "kho": "HH",
            "kho_ro": True, "ton_kho_min": sl, "dau_ky": sl, "dau_ky_kho_min": sl}


data = server._doc_du_lieu_cty(1)
data["xk_ton"] = [
    ton("MH27", "Topper Poly 160 * 200 * 7", "Chiếc", 3),
    ton("MH78", "Ga 1.8mx2m", "PCS", 9),
    ton("HH00031-8", "Ga 1.8mx2m", "Cái", 2),                 # 2 mã cùng tên, cả 2 còn tồn -> lấy mã có sẵn từ trước
    ton("MH112", "Topper Poly 120 * 200 * 7", "Chiếc", 0),    # hết tồn nhưng vẫn là mã trong kho -> vẫn dùng lại
    ton("HH00077-8", "GỐI DUN DL WHT CLOUD POLY PL 900G 74X48", "PCS", 117),
    ton("MH01", "GỐI DUN DL WHT CLOUD POLY PL 900G 74X48", "PCS", 0),   # mã cũ HẾT tồn -> lấy mã CÒN tồn
]
# bản đồ đã học: 'Topper Poly 160' từng tự sinh HH00045 (đúng ca thật)
data["dm_hh"] = {"map": {server._dm_ky_tu("Topper Poly 160 * 200 * 7", "Chiếc"): "HH00045"}, "next": 90, "rows": []}
server._ghi_du_lieu_cty(1, data)

rows = [dong("Topper Poly 160 * 200 * 7", "Chiếc", so="1"), dong("Ga 1.8mx2m", "Cái", so="2"),
        dong("TOPPER POLY 120*200*7", "Chiếc", so="3"), dong("Gối dun DL WHT Cloud Poly PL 900g 74x48", "Cái", so="4"),
        dong("Nệm hoàn toàn mới 999", "Tấm", so="5")]

# ===== 1: Danh mục Hàng hóa =====
dm, so_moi = server._gen_danh_muc(1, "hh", H, rows)
ma = {r[1]: r[0] for r in dm}
assert ma["Topper Poly 160 * 200 * 7"] == "MH27", ma
assert ma["Ga 1.8mx2m"] == "MH78", ma
assert ma["TOPPER POLY 120*200*7"] == "MH112", ma
assert ma["Gối dun DL WHT Cloud Poly PL 900g 74x48"] == "HH00077-8", ma
assert ma["Nệm hoàn toàn mới 999"] == "HH00090-8", "Tên chưa có trong kho/MISA -> mới sinh mã mới"
print("PASS 1: Danh mục: tên trùng hàng trong kho -> lấy mã trong kho (ưu tiên mã còn tồn, mã có sẵn), ĐVT lệch vẫn nhận ra.")

# ===== 2: Mua hàng nhập kho + Danh mục VTHH dùng đúng mã đó; ĐVT ghi theo kho =====
nk = server._gen_mua_hang_nk(1, H, rows)
mi, di = server.MUA_NK_HEADERS.index("Mã hàng (*)"), server.MUA_NK_HEADERS.index("ĐVT")
assert [r[mi] for r in nk] == ["MH27", "MH78", "MH112", "HH00077-8", "HH00090-8"], [r[mi] for r in nk]
assert nk[1][di] == "PCS" and nk[3][di] == "PCS" and nk[4][di] == "Tấm", [r[di] for r in nk]
vt = {r[0] for r in server._gen_vthh_from_grid(1, H, rows)}
assert {"MH27", "MH78", "MH112", "HH00077-8", "HH00090-8"} <= vt, vt
print("PASS 2: Mua hàng NK / Danh mục VTHH dùng mã có sẵn trong kho, ĐVT theo kho.")

# ===== 3: lưu danh mục giữ nguyên mã có sẵn dạng 'MH1084-0' (không cắt còn 'MH1084') =====
server._luu_danh_muc(1, "hh", [["MH1084-0", "Nekko cá ngừ", "Thùng", 8, "", 1, 1, 1, "", "", "HH"]])
assert server._doc_du_lieu_cty(1)["dm_hh"]["map"][server._dm_ky_tu("Nekko cá ngừ", "Thùng")] == "MH1084-0"
data = server._doc_du_lieu_cty(1); data["xk_ton"] = []; server._ghi_du_lieu_cty(1, data)
dm, _ = server._gen_danh_muc(1, "hh", H, [dong("Nekko cá ngừ", "Thùng")])
assert dm[0][0] == "MH1084-0", dm[0]
print("PASS 3: lưu danh mục giữ nguyên mã có sẵn có dấu '-' (MH1084-0).")

# ===== 4: chưa nạp tồn kho nhưng đã đồng bộ MISA (map_ten): ĐVT lệch vẫn lấy mã MISA =====
data = server._doc_du_lieu_cty(1); data["dm_hh"]["map_ten"] = {server._dm_khoa_ten("Vỏ chăn 2.2mx2m"): "MH90"}
server._ghi_du_lieu_cty(1, data)
dm, _ = server._gen_danh_muc(1, "hh", H, [dong("Vỏ chăn 2.2mx2m", "Cái", so="9")])
assert dm[0][0] == "MH90", dm[0]
server._luu_danh_muc(1, "hh", dm)
assert server._doc_du_lieu_cty(1)["dm_hh"].get("map_ten"), "Lưu danh mục không được xoá bản đồ tên -> mã MISA"
print("PASS 4: mã MISA cùng tên (khác ĐVT) được dùng lại; lưu danh mục giữ bản đồ.")

# ===== 5: ĐVT Cái = PCS; tên chỉ khác hậu tố CM/MM/VN sau kích thước, dấu x/* => CÙNG 1 mặt hàng =====
K = server._dm_khoa_ten
assert K("NỆM DUN NB AUDREY PRE 200X180X25CMVN") == K("NỆM DUN NB AUDREY PRE 200X180X25") == K("Nệm dun NB Audrey Pre 200 x 180 x 25 cm")
assert K("Topper Poly 160 * 200 * 7") == K("TOPPER POLY 160X200X7") == K("Topper Poly 160x200x7MM")
assert K("Ga 1.8mx2m") != K("Ga 1.6mx2m") and K("Topper Poly 160 * 200 * 7") != K("Topper Poly 180 * 200 * 7"), "Kích thước khác vẫn là hàng khác"
assert K("Vỏ gối ôm") != K("Vỏ gối")
data = server._doc_du_lieu_cty(1)
data["xk_ton"] = [ton("MH555", "NỆM DUN NB AUDREY PRE 200X180X25CMVN", "PCS", 4)]
data["dm_hh"] = {"map": {}, "next": 200, "rows": []}
server._ghi_du_lieu_cty(1, data)
hd = [dong("NỆM DUN NB AUDREY PRE 200X180X25", "Cái", so="21"), dong("Nệm dun NB Audrey Pre 200x180x25", "Chiếc", so="22")]
dm, _ = server._gen_danh_muc(1, "hh", H, hd)
assert [r[0] for r in dm] == ["MH555", "MH555"], [r[0] for r in dm]
nk = server._gen_mua_hang_nk(1, H, hd)
assert [r[mi] for r in nk] == ["MH555", "MH555"] and nk[0][di] == "PCS", [(r[mi], r[di]) for r in nk]
print("PASS 5: Cái = PCS, ...25CMVN = ...25, 'x' = '*' => cùng 1 mã trong kho.")

# ===== 6: chưa có trong kho: 2 tên tương đương trong CÙNG lượt/giữa các lượt dùng chung 1 mã mới =====
data = server._doc_du_lieu_cty(1); data["xk_ton"] = []
data["dm_hh"] = {"map": {}, "next": 300, "rows": []}
server._ghi_du_lieu_cty(1, data)
hd = [dong("NỆM DUN NB NEWBIE 200X180X25CMVN", "Cái", so="31"), dong("NỆM DUN NB NEWBIE 200X180X25", "PCS", so="32")]
dm, _ = server._gen_danh_muc(1, "hh", H, hd)
assert [r[0] for r in dm if r[2] in ("Cái", "PCS")] == ["HH00300-8", "HH00300-8"], [r[0] for r in dm]
nk = server._gen_mua_hang_nk(1, H, hd)
assert [r[mi] for r in nk] == ["HH00300-8", "HH00300-8"], [r[mi] for r in nk]
server._luu_danh_muc(1, "hh", dm)                      # lượt sau: tên tương đương (ĐVT khác) lấy lại mã đã cấp, không sinh mới
dm2, so_moi = server._gen_danh_muc(1, "hh", H, [dong("NỆM DUN NB NEWBIE 200X180X25", "Chiếc", so="33")])
assert dm2[0][0] == "HH00300-8" and not any(r[0] == "HH00301-8" for r in dm2), [r[0] for r in dm2]
print("PASS 6: tên tương đương chưa có trong kho cũng dùng chung 1 mã (cùng lượt và giữa các lượt).")
print("\nALL DONE")
