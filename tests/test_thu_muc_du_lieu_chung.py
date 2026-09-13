import os, sys, json, sqlite3, tempfile, shutil as _shutil_std
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

def extract_fn(name):
    idx = src.index('def ' + name + '(')
    i = src.index(':', idx)
    lines = src[i+1:].split('\n')
    body = []
    started = False
    for ln in lines:
        if ln.strip() == '' and not started:
            body.append(ln); continue
        if ln and not ln[0].isspace() and started:
            break
        if ln.strip():
            started = True
        body.append(ln)
    return src[idx:i+1] + '\n'.join(body)

# ── Regression test cho yêu cầu người dùng: "tôi không thấy đường dẫn lưu
# file DỮ LIỆU công ty? hãy để chung với đường dẫn Thư mục lưu file XML/PDF
# và tự tạo folder là DU LIEU CTY" — KHÔNG cần ô nhập riêng nào (đã thử 1
# "Thư mục dữ liệu chung" toàn app ở bản trước, nhưng người dùng báo
# "không cần dùng tới nữa" nên đã bỏ hẳn): mặc định dữ liệu công ty TỰ ĐỘNG
# nằm trong thư mục con "DU LIEU CTY" ngay bên trong "Thư mục lưu file
# XML/PDF" (save_dir) đã có sẵn của công ty đó — không cấu hình gì thêm.
# File dữ liệu công ty cũng có thêm thông tin công ty đã điền vào phần mềm
# ("_cty_info").
tmp_root = tempfile.mkdtemp(prefix="ketoan_test_")
DB_PATH = os.path.join(tmp_root, "app.db")
DATA_DIR = os.path.join(tmp_root, "data_dir_default")
os.makedirs(DATA_DIR, exist_ok=True)

conn0 = sqlite3.connect(DB_PATH)
conn0.executescript("""
CREATE TABLE companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ten TEXT, mst TEXT, username TEXT, password TEXT, ghichu TEXT,
    save_dir TEXT, data_dir TEXT, export_dir TEXT,
    dvc_password TEXT, dvc_password2 TEXT, mst_khac TEXT, dia_chi TEXT,
    ma_cqt_noi_nop TEXT, ten_cqt_noi_nop TEXT, nguoi_ky TEXT, no_mac_dinh TEXT,
    created_at TEXT
);
""")
conn0.commit()
conn0.close()

def db():
    c = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    c.row_factory = sqlite3.Row
    return c

ns = {'os': os, 'json': json, 'db': db, 'DATA_DIR': DATA_DIR}
for fn in ('_chuan_mst', '_thu_muc_du_lieu_rieng_cu', '_du_lieu_cty_path',
           '_doc_du_lieu_cty', '_ghi_du_lieu_cty'):
    exec(extract_fn(fn), ns)
_du_lieu_cty_path = ns['_du_lieu_cty_path']
_doc_du_lieu_cty = ns['_doc_du_lieu_cty']
_ghi_du_lieu_cty = ns['_ghi_du_lieu_cty']

# ── Dựng 2 công ty: A dùng data_dir riêng (bản cũ, hiếm — ô này đã bỏ khỏi
# giao diện); B chỉ có "Thư mục lưu file XML/PDF" (save_dir), KHÔNG có
# data_dir -> theo đúng yêu cầu người dùng, dữ liệu công ty B phải tự động
# nằm ở save_dir/"DU LIEU CTY"/.
tmpA = os.path.join(tmp_root, "cty_A_datadir")
tmpB_save = os.path.join(tmp_root, "cty_B_savedir")
tmpB_data = os.path.join(tmpB_save, "DU LIEU CTY")
os.makedirs(tmpA, exist_ok=True)
os.makedirs(tmpB_data, exist_ok=True)

conn = db()
conn.execute("INSERT INTO companies (id, ten, mst, save_dir, data_dir) VALUES (1,?,?,?,?)",
             ("CONG TY A", "0301111222", "", tmpA))
conn.execute("INSERT INTO companies (id, ten, mst, save_dir, data_dir) VALUES (2,?,?,?,?)",
             ("CONG TY B", "0302222333", tmpB_save, ""))
conn.commit()
conn.close()

with open(os.path.join(tmpA, "DuLieu_0301111222.json"), "w", encoding="utf-8") as f:
    json.dump({"note": "A-old"}, f)
with open(os.path.join(tmpB_data, "DuLieu_0302222333.json"), "w", encoding="utf-8") as f:
    json.dump({"note": "B-old"}, f)

# ── Công ty C: đúng ca ĐÃ DÙNG PHẦN MỀM TỪ TRƯỚC bản vá "DU LIEU CTY" —
# dữ liệu đang nằm THẲNG trong save_dir (KHÔNG có thư mục con "DU LIEU
# CTY" nào cả, chưa hề tồn tại) — mô phỏng đúng câu hỏi người dùng đặt ra:
# "những cty đã lưu trước đó có cần phải chỉnh lại đường dẫn lưu không?"
tmpC_save = os.path.join(tmp_root, "cty_C_savedir_cu")
os.makedirs(tmpC_save, exist_ok=True)
conn = db()
conn.execute("INSERT INTO companies (id, ten, mst, save_dir, data_dir) VALUES (3,?,?,?,?)",
             ("CONG TY C", "0303333444", tmpC_save, ""))
conn.commit()
conn.close()
with open(os.path.join(tmpC_save, "DuLieu_0303333444.json"), "w", encoding="utf-8") as f:
    json.dump({"note": "C-old-bare-savedir", "hach_toan": ["da co san"]}, f)

# ── Test 1: công ty A (data_dir riêng, bản cũ) dùng đúng data_dir; công ty
# B (không có data_dir) tự động dùng thư mục con "DU LIEU CTY" ngay trong
# Thư mục lưu file XML/PDF — không cần gõ thêm đường dẫn nào. ──
assert _du_lieu_cty_path(1) == os.path.join(tmpA, "DuLieu_0301111222.json"), (
    f"Công ty A phải dùng đúng data_dir riêng cũ — got {_du_lieu_cty_path(1)}")
assert _du_lieu_cty_path(2) == os.path.join(tmpB_data, "DuLieu_0302222333.json"), (
    f"Công ty B (không có data_dir) phải TỰ ĐỘNG dùng thư mục con 'DU LIEU CTY' ngay trong Thư mục "
    f"lưu file XML/PDF (save_dir) — got {_du_lieu_cty_path(2)}")
print("PASS 1: công ty A dùng đúng data_dir riêng cũ; công ty B (không có data_dir) tự động dùng thư mục "
      "con 'DU LIEU CTY' ngay trong Thư mục lưu file XML/PDF — không cần gõ thêm đường dẫn nào.")

# ── Test 2 (đúng câu hỏi người dùng "những cty đã lưu trước đó có cần
# chỉnh lại đường dẫn không?"): công ty C đã có dữ liệu THẬT nằm thẳng
# trong save_dir (kiểu CŨ, trước khi có thư mục con "DU LIEU CTY") ->
# _du_lieu_cty_path PHẢI tự động sao chép dữ liệu đó vào đúng vị trí MỚI
# (không cần người dùng tự làm gì, không mất dữ liệu), và đọc lại đúng nội
# dung cũ ở vị trí mới. ──
duong_dan_c = _du_lieu_cty_path(3)
assert duong_dan_c == os.path.join(tmpC_save, "DU LIEU CTY", "DuLieu_0303333444.json"), (
    f"Công ty C phải dùng đúng thư mục con DU LIEU CTY mới — got {duong_dan_c}")
assert os.path.isfile(duong_dan_c), (
    "Dữ liệu CŨ (nằm thẳng trong save_dir, trước khi có thư mục con) PHẢI được TỰ ĐỘNG sao chép sang vị "
    "trí mới — người dùng KHÔNG cần tự chỉnh lại đường dẫn cho công ty đã dùng phần mềm từ trước")
du_lieu_c = _doc_du_lieu_cty(3)
assert du_lieu_c.get("hach_toan") == ["da co san"], (
    f"Đọc lại đúng nội dung dữ liệu CŨ ở vị trí MỚI, không bị mất/trống — got {du_lieu_c}")
assert os.path.isfile(os.path.join(tmpC_save, "DuLieu_0303333444.json")), (
    "File GỐC (kiểu cũ, nằm thẳng trong save_dir) KHÔNG được xoá sau khi tự động sao chép — an toàn, "
    "giữ lại làm bản dự phòng")
print("PASS 2: công ty ĐÃ DÙNG PHẦN MỀM TỪ TRƯỚC (dữ liệu nằm thẳng trong Thư mục lưu file XML/PDF, chưa "
      "có thư mục con DU LIEU CTY) được TỰ ĐỘNG sao chép dữ liệu sang đúng vị trí mới ngay lần đọc/ghi "
      "đầu tiên sau khi nâng cấp — người dùng KHÔNG cần tự chỉnh lại đường dẫn, không mất dữ liệu cũ.")

# ── Test 3 (đúng yêu cầu "file này lưu tất cả thông tin cty đã điền"):
# _ghi_du_lieu_cty phải LUÔN kèm snapshot thông tin công ty ("_cty_info")
# — không đụng/mất dict gốc do caller truyền vào. ──
data_goc = {"hach_toan": ["dong1", "dong2"]}
_ghi_du_lieu_cty(1, data_goc)
assert "_cty_info" not in data_goc, "_ghi_du_lieu_cty KHÔNG được sửa/thêm khoá vào dict gốc của caller"
da_luu = _doc_du_lieu_cty(1)
assert da_luu.get("hach_toan") == ["dong1", "dong2"], f"Dữ liệu hạch toán gốc phải được giữ nguyên — got {da_luu}"
assert da_luu.get("_cty_info", {}).get("ten") == "CONG TY A", (
    f"File dữ liệu công ty PHẢI kèm thông tin công ty (_cty_info) — got {da_luu.get('_cty_info')}")
assert da_luu.get("_cty_info", {}).get("mst") == "0301111222"
print("PASS 3: file dữ liệu công ty (DuLieu_<MST>.json) giờ LUÔN kèm sẵn thông tin công ty đã điền vào phần mềm "
      "(tên, MST, mật khẩu, thư mục...) qua khoá \"_cty_info\", không sửa dict gốc của nơi gọi.")

_shutil_std.rmtree(tmp_root, ignore_errors=True)
print("\nALL DONE")
