import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: "Chi tiết BÁN RA" (ctbr — nguồn cho Xuất Kho, xem
_xk_gop_them_ban_hang) phải TÍCH LŨY qua NHIỀU lần Import & Lưu ở màn Nhập
Liệu (vd import file Quý 1/2026 rồi sau đó import thêm file Quý 2/2026),
KHÔNG được để lần Lưu SAU thay thế mất dữ liệu ctbr của lần Lưu TRƯỚC.

Đúng ca thật người dùng báo cáo: "tôi import dữ liệu từ tháng 1/2026 -
tháng 6/2026 để xử lý kho nhưng phần mềm chỉ lấy dữ liệu từ quý 2/2026
thôi... nếu import như thế nào thì sẽ xử lý những dữ liệu import chứ
không phải theo kỳ nhập liệu" — vì trước đây JS (luuCaHaiBangKe) lưu ctbr
qua /api/nhap-lieu/save?loai=ctbr (THAY THẾ toàn bộ, giống 'in'/'out'),
trong khi ctbr phải GỘP THÊM (dùng _xk_gop_them_ban_hang, hàm ĐÃ CÓ SẴN
cho nút '➕ Import thêm dữ liệu' ở Xuất Kho) — sửa bằng cách thêm endpoint
mới /api/nhap-lieu/save-ctbr-gop dùng lại đúng hàm gộp này, và đổi JS gọi
endpoint mới thay vì endpoint thay thế cũ."""
import sys, sqlite3, os, tempfile
sys.path.insert(0, _REPO_ROOT)
import server


# Mô phỏng đúng thật: mỗi request thật server.db() mở connection MỚI nhưng
# trỏ vào CÙNG 1 file sqlite trên đĩa (dữ liệu persist qua nhiều lần gọi,
# kể cả sau conn.close()) — ":memory:" không persist qua connection mới
# nên phải dùng file thật cho test có NHIỀU lần gọi db() nối tiếp này.
_db_path = tempfile.mktemp(suffix=".sqlite3")


def db_factory():
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    return conn


_data_dir = tempfile.mkdtemp()
orig_db, orig_data_dir = server.db, server.DATA_DIR
server.db = db_factory
server.DATA_DIR = _data_dir
try:
    conn0 = db_factory()
    conn0.execute("""CREATE TABLE companies (id INTEGER PRIMARY KEY, mst TEXT,
        save_dir TEXT, data_dir TEXT)""")
    conn0.execute("INSERT INTO companies VALUES (1,'0317743519','','')")
    conn0.commit()
    conn0.close()

    header = ["Ký hiệu", "Số HĐ", "Ngày", "Tên hàng hóa, dịch vụ", "ĐVT", "Số lượng",
              "Đơn giá", "Thành tiền"]
    # Đợt 1: file Quý 1/2026 (tháng 1-3), 3 dòng bán hàng.
    rows_q1 = [
        ["C1", "101", "15/01/2026", "Chậu Polystone ASH60 - MTBK", "Cái", 5, 100000, 500000],
        ["C1", "102", "20/02/2026", "Chậu Polystone D210xH62 cm - MTWT", "Cái", 2, 200000, 400000],
        ["C1", "103", "10/03/2026", "Chậu Polystone D180xH50 cm - MTBK", "Cái", 3, 150000, 450000],
    ]
    so_them1, so_trung1, tong1 = server._xk_gop_them_ban_hang(1, header, rows_q1)
    assert so_them1 == 3 and tong1 == 3, f"Đợt 1 (Quý 1/2026) phải lưu đủ 3 dòng — được so_them={so_them1}, tong={tong1}"

    # Đợt 2: file Quý 2/2026 (tháng 4-6), 2 dòng bán hàng KHÁC (giống hệt
    # tình huống người dùng: import thêm 1 đợt mới sau đợt trước).
    rows_q2 = [
        ["C1", "201", "06/05/2026", "Chậu Polystone ASH60 - CT", "Cái", 20, 2364242.4, 47284848],
        ["C1", "202", "12/05/2026", "Chậu Polystone D210xH62 cm - MTWT", "cái", 2, 7885546.56, 15771093.12],
    ]
    so_them2, so_trung2, tong2 = server._xk_gop_them_ban_hang(1, header, rows_q2)
    print(f"Đợt 2 (Quý 2/2026): so_them={so_them2}, so_trung={so_trung2}, tong={tong2}")

    ket_qua = server.nhap_lieu_get(1, "ctbr")
    so_hd_con = [r[1] for r in ket_qua["rows"]]  # cột "Số HĐ" ở vị trí 1
    print("Số HĐ còn trong ctbr sau 2 đợt import:", so_hd_con)

    assert so_them2 == 2 and tong2 == 5, (
        f"Đợt 2 phải GỘP THÊM vào 3 dòng của đợt 1 (Quý 1/2026), tổng phải là 5 dòng — "
        f"được so_them={so_them2}, tong={tong2} (nếu tong=2 nghĩa là đợt 2 đã XOÁ MẤT dữ liệu "
        f"đợt 1, đúng lỗi người dùng báo cáo)")
    for so_hd_q1 in ("101", "102", "103"):
        assert so_hd_q1 in so_hd_con, (
            f"Hóa đơn {so_hd_q1} (Quý 1/2026, đợt import TRƯỚC) phải CÒN NGUYÊN trong dữ liệu Xuất "
            f"Kho sau khi import thêm đợt Quý 2/2026 — bị mất mất rồi, được {so_hd_con}")
    for so_hd_q2 in ("201", "202"):
        assert so_hd_q2 in so_hd_con, f"Hóa đơn {so_hd_q2} (Quý 2/2026, đợt mới) phải có trong dữ liệu — được {so_hd_con}"

    print("PASS: ctbr (nguồn Xuất Kho) tích luỹ đúng qua nhiều đợt Import & Lưu (Quý 1 rồi Quý "
          "2/2026) — không còn bị đợt sau xoá mất dữ liệu đợt trước.")
finally:
    server.db = orig_db
    server.DATA_DIR = orig_data_dir
    try:
        os.remove(_db_path)
    except OSError:
        pass
    import shutil
    shutil.rmtree(_data_dir, ignore_errors=True)

print("\nTẤT CẢ TEST PASS")
