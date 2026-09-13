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

# ── Regression test cho yêu cầu người dùng: dữ liệu công ty (hạch toán,
# danh mục...) đang lưu RẢI RÁC mỗi công ty 1 thư mục riêng, khó quản lý.
# Theo phản hồi tiếp theo của người dùng ("tôi không thấy đường dẫn lưu
# file DỮ LIỆU công ty? hãy để chung với đường dẫn Thư mục lưu file XML/
# PDF và tự tạo folder là DU LIEU CTY"): KHÔNG cần ô nhập riêng nào nữa —
# mặc định dữ liệu công ty TỰ ĐỘNG nằm trong thư mục con "DU LIEU CTY"
# ngay bên trong "Thư mục lưu file XML/PDF" (save_dir) đã có sẵn của công
# ty đó. Vẫn giữ tuỳ chọn "Thư mục dữ liệu chung" (global_data_dir) cho ai
# muốn gộp MỌI công ty vào đúng 1 thư mục khác duy nhất — ưu tiên cao hơn
# mặc định tự động ở trên khi đã cấu hình, và tự động gom dữ liệu cũ về
# khi đặt đường dẫn mới. File dữ liệu công ty cũng có thêm thông tin công
# ty đã điền vào phần mềm ("_cty_info").
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
CREATE TABLE app_settings (key TEXT PRIMARY KEY, value TEXT);
""")
conn0.commit()
conn0.close()

def db():
    c = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    c.row_factory = sqlite3.Row
    return c

ns = {'os': os, 'json': json, 'db': db, 'DATA_DIR': DATA_DIR}
for fn in ('_chuan_mst', '_get_setting', '_set_setting', '_thu_muc_du_lieu_rieng_cu',
           '_du_lieu_cty_path', '_gom_du_lieu_cty_ve_thu_muc_chung',
           '_doc_du_lieu_cty', '_ghi_du_lieu_cty'):
    exec(extract_fn(fn), ns)
_get_setting = ns['_get_setting']
_set_setting = ns['_set_setting']
_du_lieu_cty_path = ns['_du_lieu_cty_path']
_gom_du_lieu_cty_ve_thu_muc_chung = ns['_gom_du_lieu_cty_ve_thu_muc_chung']
_doc_du_lieu_cty = ns['_doc_du_lieu_cty']
_ghi_du_lieu_cty = ns['_ghi_du_lieu_cty']

# ── Dựng 2 công ty với dữ liệu CŨ rải rác (đúng hiện trạng người dùng báo):
# công ty A dùng data_dir riêng (bản cũ, hiếm — ô này đã bỏ khỏi giao
# diện); công ty B chỉ có "Thư mục lưu file XML/PDF" (save_dir), KHÔNG có
# data_dir -> theo đúng yêu cầu người dùng "để chung với đường dẫn Thư mục
# lưu file XML/PDF và tự tạo folder là DU LIEU CTY", dữ liệu công ty B phải
# tự động nằm ở save_dir/"DU LIEU CTY"/.
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

# ── Test 1: CHƯA cấu hình thư mục chung -> vẫn lùi về đúng thư mục RIÊNG
# kiểu cũ của từng công ty (không phá vỡ cài đặt hiện có). ──
assert _du_lieu_cty_path(1) == os.path.join(tmpA, "DuLieu_0301111222.json"), (
    f"Chưa có thư mục chung -> công ty A phải dùng đúng data_dir riêng cũ — got {_du_lieu_cty_path(1)}")
assert _du_lieu_cty_path(2) == os.path.join(tmpB_data, "DuLieu_0302222333.json"), (
    f"Chưa có thư mục chung -> công ty B (không có data_dir) phải TỰ ĐỘNG dùng thư mục con "
    f"'DU LIEU CTY' ngay trong Thư mục lưu file XML/PDF (save_dir) — got {_du_lieu_cty_path(2)}")
print("PASS 1: chưa cấu hình thư mục chung -> công ty A dùng đúng data_dir riêng cũ; công ty B (không có "
      "data_dir) tự động dùng thư mục con 'DU LIEU CTY' ngay trong Thư mục lưu file XML/PDF — không cần "
      "gõ thêm đường dẫn nào.")

# ── Test 1b (đúng câu hỏi người dùng "những cty đã lưu trước đó có cần
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
print("PASS 1b: công ty ĐÃ DÙNG PHẦN MỀM TỪ TRƯỚC (dữ liệu nằm thẳng trong Thư mục lưu file XML/PDF, chưa "
      "có thư mục con DU LIEU CTY) được TỰ ĐỘNG sao chép dữ liệu sang đúng vị trí mới ngay lần đọc/ghi "
      "đầu tiên sau khi nâng cấp — người dùng KHÔNG cần tự chỉnh lại đường dẫn, không mất dữ liệu cũ.")

# ── Test 2: đặt thư mục CHUNG -> _du_lieu_cty_path của MỌI công ty đổi
# sang đúng thư mục chung đó (mỗi công ty vẫn 1 file riêng theo MST). ──
tmp_shared = os.path.join(tmp_root, "thu_muc_chung")
_set_setting("global_data_dir", tmp_shared)
assert _du_lieu_cty_path(1) == os.path.join(tmp_shared, "DuLieu_0301111222.json"), (
    f"Đã đặt thư mục chung -> công ty A PHẢI dùng thư mục chung, không còn data_dir riêng — got {_du_lieu_cty_path(1)}")
assert _du_lieu_cty_path(2) == os.path.join(tmp_shared, "DuLieu_0302222333.json"), (
    f"Đã đặt thư mục chung -> công ty B PHẢI dùng thư mục chung, không còn save_dir riêng — got {_du_lieu_cty_path(2)}")
print("PASS 2: đặt thư mục dữ liệu CHUNG -> TẤT CẢ công ty cùng lưu vào 1 thư mục (mỗi công ty vẫn 1 file riêng theo MST).")

# ── Test 3 (đúng yêu cầu "tự động gộm khi đặt đường dẫn mới"): gom dữ liệu
# CŨ đang rải rác về thư mục chung — KHÔNG xoá bản gốc, giữ nguyên nội
# dung. ──
so_gom = _gom_du_lieu_cty_ve_thu_muc_chung(tmp_shared)
assert so_gom == 3, f"Phải gom được đúng 3 công ty (A + B + C) — got {so_gom}"
with open(os.path.join(tmp_shared, "DuLieu_0301111222.json"), encoding="utf-8") as f:
    assert json.load(f) == {"note": "A-old"}, "Nội dung file gom về của công ty A phải khớp bản gốc"
with open(os.path.join(tmp_shared, "DuLieu_0302222333.json"), encoding="utf-8") as f:
    assert json.load(f) == {"note": "B-old"}, "Nội dung file gom về của công ty B phải khớp bản gốc"
with open(os.path.join(tmp_shared, "DuLieu_0303333444.json"), encoding="utf-8") as f:
    assert json.load(f).get("hach_toan") == ["da co san"], "Nội dung file gom về của công ty C phải khớp bản gốc (đã tự sao chép ở Test 1b)"
assert os.path.isfile(os.path.join(tmpA, "DuLieu_0301111222.json")), (
    "File GỐC của công ty A KHÔNG được xoá sau khi gom (chỉ sao chép, an toàn)")
assert os.path.isfile(os.path.join(tmpB_data, "DuLieu_0302222333.json")), (
    "File GỐC của công ty B KHÔNG được xoá sau khi gom (chỉ sao chép, an toàn)")
print("PASS 3: tự động gom đúng 3 file dữ liệu cũ (A, B, C) về thư mục chung, giữ nguyên nội dung, KHÔNG xoá bản gốc.")

# ── Test 4: gọi gom LẦN 2 (mô phỏng lỡ bấm lưu lại) -> KHÔNG ghi đè dữ
# liệu đã có sẵn ở thư mục chung (đề phòng thư mục chung đã có dữ liệu MỚI
# hơn từ máy khác). ──
with open(os.path.join(tmp_shared, "DuLieu_0301111222.json"), "w", encoding="utf-8") as f:
    json.dump({"note": "A-shared-NEWER"}, f)
so_gom_2 = _gom_du_lieu_cty_ve_thu_muc_chung(tmp_shared)
assert so_gom_2 == 0, f"File đích đã có sẵn -> KHÔNG được gom/ghi đè lại — got so_gom={so_gom_2}"
with open(os.path.join(tmp_shared, "DuLieu_0301111222.json"), encoding="utf-8") as f:
    assert json.load(f) == {"note": "A-shared-NEWER"}, "Dữ liệu MỚI HƠN đã có ở thư mục chung KHÔNG được ghi đè lại bởi bản gom cũ"
print("PASS 4: gọi gom lại lần 2 KHÔNG ghi đè dữ liệu đã có sẵn ở thư mục chung (an toàn khi bấm lưu nhiều lần).")

# ── Test 5 (đúng yêu cầu "file này lưu tất cả thông tin cty đã điền"):
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
print("PASS 5: file dữ liệu công ty (DuLieu_<MST>.json) giờ LUÔN kèm sẵn thông tin công ty đã điền vào phần mềm "
      "(tên, MST, mật khẩu, thư mục...) qua khoá \"_cty_info\", không sửa dict gốc của nơi gọi.")

_shutil_std.rmtree(tmp_root, ignore_errors=True)
print("\nALL DONE")
