import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: khoá so khớp Tên hàng+ĐVT (_dm_ky_tu, dùng cho Danh mục
Hàng hóa/NVL) PHẢI KHÔNG phân biệt chữ HOA/thường — trước đây so khớp phân
biệt hoa/thường khiến 44/255 mặt hàng ĐÃ CÓ mã trong MISA vẫn bị tự sinh
thêm mã HH0000X mới trùng lặp.

Đúng 2 ca thật từ file DanhMuc_DMHH người dùng gửi (đối chiếu qua "👁 Xem
danh mục MISA"):
- MISA mã 'TPVT00174' lưu tên TOÀN CHỮ HOA 'CHẬU POLYSTONE WILV24 - MTWT',
  trong khi bảng kê ghi 'Chậu Polystone WILV24 - MTWT' (Title Case) -> vẫn
  bị tự sinh 'HH00017-8' MỚI dù MISA đã có mã.
- MISA mã 'VT00230' lưu tên 'Chậu Polystone Auc60L' (chỉ viết hoa chữ đầu,
  kể cả hậu tố '60L'), trong khi bảng kê ghi 'Chậu Polystone AUC60L' (viết
  hoa toàn bộ hậu tố) -> vẫn bị tự sinh 'HH00009-8' MỚI."""
import sys
sys.path.insert(0, _REPO_ROOT)
import server

# ===== Ca 1: _dm_ky_tu tự nó phải không phân biệt hoa/thường =====
ky1a = server._dm_ky_tu("Chậu Polystone WILV24 - MTWT", "Cái")
ky1b = server._dm_ky_tu("CHẬU POLYSTONE WILV24 - MTWT", "Cái")
assert ky1a == ky1b, f"_dm_ky_tu phải KHÔNG phân biệt hoa/thường — được {ky1a!r} != {ky1b!r}"

ky2a = server._dm_ky_tu("Chậu Polystone AUC60L", "Cái")
ky2b = server._dm_ky_tu("Chậu Polystone Auc60L", "Cái")
assert ky2a == ky2b, f"_dm_ky_tu phải KHÔNG phân biệt hoa/thường — được {ky2a!r} != {ky2b!r}"
print("PASS: _dm_ky_tu không phân biệt chữ hoa/thường (kể cả ký tự có dấu tiếng Việt).")

# ===== Ca 2: mô phỏng đúng thật — bản đồ ĐÃ HỌC (giả lập đồng bộ MISA
# thành công trước đó, lưu ky_tu theo TÊN VIẾT HOA của MISA) rồi Sinh Danh
# mục cho bảng kê ghi TÊN KHÁC KIỂU CHỮ (Title Case) -> PHẢI tái sử dụng
# đúng mã MISA, KHÔNG tự sinh mã mới trùng lặp. =====
import sqlite3, os, tempfile
_db_path = tempfile.mktemp(suffix=".sqlite3")
_data_dir = tempfile.mkdtemp()


def db_factory():
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    return conn


orig_db, orig_data_dir = server.db, server.DATA_DIR
server.db = db_factory
server.DATA_DIR = _data_dir

HANG_HOA_HEADER = ["Nợ", "Tên hàng hóa/dịch vụ", "ĐVT", "Thuế suất", "Số lượng",
                   "Đơn giá", "Thành tiền", "Số HĐ", "Ngày"]

try:
    conn = db_factory()
    conn.execute("""CREATE TABLE companies (id INTEGER PRIMARY KEY, mst TEXT,
        save_dir TEXT, data_dir TEXT)""")
    conn.execute("INSERT INTO companies VALUES (1,'0315673577','','')")
    conn.commit()
    conn.close()

    # Bản đồ đã học mã MISA THẬT (giả lập đồng bộ trước đó thành công) —
    # dùng ĐÚNG công thức _dm_ky_tu (viết hoa) làm khoá, y hệt cách
    # _misa_dong_bo_danh_muc_tu_misa lưu.
    data1 = server._doc_du_lieu_cty(1)
    data1["dm_hh"] = {"map": {
        server._dm_ky_tu("CHẬU POLYSTONE WILV24 - MTWT", "Cái"): "TPVT00174",
        server._dm_ky_tu("Chậu Polystone Auc60L", "Cái"): "VT00230",
    }, "next": 1, "rows": []}
    server._ghi_du_lieu_cty(1, data1)

    rows = [
        ["1561", "Chậu Polystone WILV24 - MTWT", "Cái", 8, 10, 700000, 7000000, "1", "07/01/2026"],
        ["1561", "Chậu Polystone AUC60L", "Cái", 8, 5, 2250000, 11250000, "1", "07/01/2026"],
    ]
    all_rows, so_moi = server._gen_danh_muc(1, "hh", HANG_HOA_HEADER, rows)
    print("Kết quả Sinh Danh mục:", all_rows)
    ma_map = {r[1]: r[0] for r in all_rows}
    assert ma_map["Chậu Polystone WILV24 - MTWT"] == "TPVT00174", (
        f"Phải tái sử dụng ĐÚNG mã MISA 'TPVT00174' (khác chữ hoa/thường với tên đã học) — được "
        f"{ma_map['Chậu Polystone WILV24 - MTWT']}")
    assert ma_map["Chậu Polystone AUC60L"] == "VT00230", (
        f"Phải tái sử dụng ĐÚNG mã MISA 'VT00230' (khác chữ hoa/thường với tên đã học) — được "
        f"{ma_map['Chậu Polystone AUC60L']}")
    print("PASS: Sinh Danh mục tái sử dụng đúng mã MISA đã học dù tên trong bảng kê khác kiểu chữ "
          "hoa/thường — không còn tự sinh mã HH0000X trùng lặp nữa.")

    print("\nTẤT CẢ TEST PASS")
finally:
    server.db = orig_db
    server.DATA_DIR = orig_data_dir
    try:
        os.remove(_db_path)
    except OSError:
        pass
    import shutil
    shutil.rmtree(_data_dir, ignore_errors=True)
