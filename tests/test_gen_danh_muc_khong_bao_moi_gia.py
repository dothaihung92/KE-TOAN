import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: sau khi "🔄 Đồng bộ mã có sẵn trong MISA" THAY mã tự
sinh (placeholder) bằng mã thật trong MISA cho 1 ky_tu, các dòng ĐÃ LƯU
trước đó (giữ nguyên mã CŨ, không bị đụng vào — đúng thiết kế) KHÔNG được
báo lại là "mới" nữa — trước đây khoá dò trùng (rk) dùng CHÍNH mã hàng làm
1 phần khoá, nên mã đổi (do đồng bộ) khiến MỌI dòng đã lưu trước đó không
còn khớp lại được, bị hiểu nhầm là dòng MỚI toàn bộ.

Đúng ca thật người dùng báo cáo: ảnh chụp "Tổng 141 mặt hàng — 141 mới"
(TẤT CẢ đều "mới") ngay sau khi bấm Đồng bộ, dù bảng kê không hề đổi gì —
trước đó (trước khi đồng bộ) đã đúng "0 mới" (khớp hết, không có gì mới)."""
import sys, sqlite3, os, tempfile
sys.path.insert(0, _REPO_ROOT)
import server

_db_path = tempfile.mktemp(suffix=".sqlite3")
_data_dir = tempfile.mkdtemp()


def db_factory():
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    return conn


class FakeCursor:
    def execute(self, sql, params=()):
        self.last_sql = sql
        return self

    def fetchall(self):
        if "FROM Unit" in self.last_sql:
            return [("U1", "Cái")]
        if "FROM InventoryItem" in self.last_sql:
            return [("MH613", "Chậu Polystone D35xH45 cm - Matte Black", "U1")]
        return []


class FakeConn:
    def cursor(self):
        return FakeCursor()

    def close(self):
        pass


orig_db, orig_data_dir, orig_connect = server.db, server.DATA_DIR, server._misa_sql_connect
server.db = db_factory
server.DATA_DIR = _data_dir
server._misa_sql_connect = lambda cid, database=None: FakeConn()

HANG_HOA_HEADER = ["Nợ", "Tên hàng hóa/dịch vụ", "ĐVT", "Thuế suất", "Số lượng",
                   "Đơn giá", "Thành tiền", "Số HĐ", "Ngày"]

try:
    conn = db_factory()
    conn.execute("""CREATE TABLE companies (id INTEGER PRIMARY KEY, mst TEXT,
        save_dir TEXT, data_dir TEXT)""")
    conn.execute("INSERT INTO companies VALUES (1,'0317743519','','')")
    conn.commit()
    conn.close()

    # ===== Bước 1: Sinh + Lưu Danh mục cho 3 hóa đơn (2 hóa đơn CÙNG sản
    # phẩm "Matte Black" bị đồng bộ sau này, 1 hóa đơn KHÁC sản phẩm để đối
    # chứng không bị ảnh hưởng) — giống hệt trạng thái "0 mới" ban đầu. =====
    rows_v1 = [
        ["1561", "Chậu Polystone D35xH45 cm - Matte Black", "Cái", 8, 50, 370000, 18500000, "41", "18/05/2026"],
        ["1561", "Chậu Polystone D31xH40 cm - Gloss Olive", "Cái", 8, 50, 321000, 16050000, "41", "18/05/2026"],
    ]
    all_rows_v1, so_moi_v1 = server._gen_danh_muc(1, "hh", HANG_HOA_HEADER, rows_v1)
    assert so_moi_v1 == 2, f"Lần đầu, cả 2 dòng phải là mới — được {so_moi_v1}"
    server._luu_danh_muc(1, "hh", all_rows_v1)
    ma_matte_black_cu = next(r[0] for r in all_rows_v1 if "Matte Black" in r[1])
    print("Mã 'Matte Black' TRƯỚC khi đồng bộ (đã Lưu):", ma_matte_black_cu)
    assert ma_matte_black_cu.startswith("HH0")

    # Chạy lại NGAY (chưa đồng bộ gì) với ĐÚNG bảng kê cũ -> phải "0 mới"
    # (đối chứng hành vi bình thường, chưa có gì thay đổi).
    all_rows_v1b, so_moi_v1b = server._gen_danh_muc(1, "hh", HANG_HOA_HEADER, rows_v1)
    assert so_moi_v1b == 0, f"Chạy lại với bảng kê y hệt (chưa đồng bộ gì) phải '0 mới' — được {so_moi_v1b}"

    # ===== Bước 2: Đồng bộ mã có sẵn trong MISA — THAY mã tự sinh của
    # 'Matte Black' bằng 'MH613' (đúng ky_tu, MISA có sẵn). =====
    kq_dongbo = server._misa_dong_bo_danh_muc_tu_misa(1, "TESTDB", "hh")
    print("Kết quả đồng bộ:", kq_dongbo)
    assert kq_dongbo["so_thay_the"] == 1

    # ===== Bước 3: Chạy lại Sinh Danh mục với ĐÚNG bảng kê CŨ (không đổi gì
    # cả, người dùng chỉ mở lại màn Danh mục) -> KHÔNG được báo "2 mới" hay
    # "1 mới" — phải VẪN LÀ "0 mới" như trước khi đồng bộ (dòng đã lưu vẫn
    # được nhận diện đúng là đã có, dù mã trong bản đồ vừa đổi). =====
    all_rows_v2, so_moi_v2 = server._gen_danh_muc(1, "hh", HANG_HOA_HEADER, rows_v1)
    print(f"Sau khi đồng bộ, chạy lại với bảng kê CŨ y hệt: so_moi={so_moi_v2}, tổng={len(all_rows_v2)}")
    assert so_moi_v2 == 0, (
        f"Đồng bộ chỉ đổi BẢN ĐỒ tên->mã cho hoá đơn MỚI sau này, KHÔNG được làm các dòng ĐÃ LƯU trước đó "
        f"bị hiểu nhầm là 'mới' lại — đúng lỗi thật đã gặp ('141 mới' dù bảng kê không đổi gì) — được "
        f"so_moi={so_moi_v2}")
    assert len(all_rows_v2) == 2, f"Tổng số dòng KHÔNG được tăng lên (không bị nhân đôi do dò trùng sai) — được {len(all_rows_v2)} dòng: {all_rows_v2}"
    ma_matte_black_sau = next(r[0] for r in all_rows_v2 if "Matte Black" in r[1])
    assert ma_matte_black_sau == ma_matte_black_cu, (
        f"Dòng ĐÃ LƯU trước đó phải GIỮ NGUYÊN mã cũ '{ma_matte_black_cu}' (không tự đổi ngược ra 'MH613' "
        f"— đồng bộ CHỈ áp dụng cho hoá đơn MỚI, không đụng dữ liệu đã lưu) — được {ma_matte_black_sau}")
    print("PASS: dòng đã lưu trước đó KHÔNG bị báo 'mới' lại sau khi đồng bộ đổi bản đồ, vẫn giữ đúng mã cũ.")

    # ===== Bước 4: hoá đơn MỚI THẬT SỰ (khác Số HĐ) cho ĐÚNG sản phẩm
    # 'Matte Black' đó -> PHẢI dùng mã MISA MỚI 'MH613' (chứng minh việc
    # đồng bộ vẫn có tác dụng cho dữ liệu thật sự mới, không bị fix quá tay
    # làm mất luôn lợi ích của tính năng đồng bộ). =====
    rows_v3 = rows_v1 + [
        ["1561", "Chậu Polystone D35xH45 cm - Matte Black", "Cái", 8, 20, 370000, 7400000, "99", "20/06/2026"],
    ]
    all_rows_v3, so_moi_v3 = server._gen_danh_muc(1, "hh", HANG_HOA_HEADER, rows_v3)
    print(f"Thêm hoá đơn MỚI (Số HĐ 99, cùng Matte Black): so_moi={so_moi_v3}")
    assert so_moi_v3 == 1, f"CHỈ hoá đơn 99 (thật sự mới) phải được báo mới, 2 hoá đơn cũ vẫn '0 mới' — được {so_moi_v3}"
    dong_hd99 = next(r for r in all_rows_v3 if r[8] == "99")
    assert dong_hd99[0] == "MH613", (
        f"Hoá đơn MỚI (Số HĐ 99, chưa từng lưu) cho cùng sản phẩm 'Matte Black' PHẢI dùng mã MISA thật "
        f"'MH613' đã học từ đồng bộ — được {dong_hd99[0]}")
    print("PASS: hoá đơn thật sự mới vẫn đúng dùng mã MISA đã đồng bộ — fix dò trùng không làm mất tác "
          "dụng của tính năng đồng bộ.")

    print("\nTẤT CẢ TEST PASS")
finally:
    server.db = orig_db
    server.DATA_DIR = orig_data_dir
    server._misa_sql_connect = orig_connect
    try:
        os.remove(_db_path)
    except OSError:
        pass
    import shutil
    shutil.rmtree(_data_dir, ignore_errors=True)
