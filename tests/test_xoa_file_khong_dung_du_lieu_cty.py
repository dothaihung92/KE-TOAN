import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys, sqlite3, tempfile
sys.path.insert(0, _REPO_ROOT)
import server

# ── Regression test cho cảnh báo thật của người dùng: "lưu ý mục xoá file
# đã tải không được xoá file DU LIEU CTY" — kể từ khi dữ liệu công ty
# (hạch toán, danh mục...) chuyển vào thư mục con "DU LIEU CTY" NGAY TRONG
# "Thư mục lưu file XML/PDF" (save_dir, xem _thu_muc_du_lieu_rieng_cu),
# nút "🧹 Xóa file đã tải (nhẹ máy)" (clear_downloads — xoá MỌI file .xml/
# .pdf/.zip/.html/.xlsx/.json bên trong save_dir của từng công ty) có nguy
# cơ XOÁ NHẦM LUÔN file dữ liệu công ty thật DuLieu_<MST>.json (đuôi .json
# cũng nằm trong danh sách bị xoá) — vì hàm này TRƯỚC ĐÂY chỉ loại trừ
# data_dir RIÊNG khai báo tay (đã bỏ khỏi giao diện), không biết gì về thư
# mục con tự động mới này.
_db_path = tempfile.mktemp(suffix=".sqlite3")


def db_factory():
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    return conn


orig_db = server.db
server.db = db_factory
try:
    conn0 = db_factory()
    conn0.execute("""CREATE TABLE companies (id INTEGER PRIMARY KEY, mst TEXT,
        save_dir TEXT, data_dir TEXT)""")
    conn0.commit()
    conn0.close()

    # Công ty A: KHÔNG có data_dir riêng (đúng hiện trạng đa số — dùng mặc định
    # tự động "DU LIEU CTY" ngay trong save_dir).
    save_dir_a = tempfile.mkdtemp(prefix="ketoan_savedir_A_")
    data_dir_a = os.path.join(save_dir_a, "DU LIEU CTY")
    os.makedirs(data_dir_a, exist_ok=True)
    file_xml = os.path.join(save_dir_a, "hoadon_mua_vao_001.xml")
    file_xlsx_rac = os.path.join(save_dir_a, "bao_cao_cu.xlsx")
    file_du_lieu = os.path.join(data_dir_a, "DuLieu_0319103095.json")
    with open(file_xml, "w", encoding="utf-8") as f:
        f.write("<invoice>rac tai xuong, xoa duoc</invoice>")
    with open(file_xlsx_rac, "w", encoding="utf-8") as f:
        f.write("rac excel cu")
    with open(file_du_lieu, "w", encoding="utf-8") as f:
        f.write('{"hach_toan": ["du lieu that, KHONG duoc xoa"]}')

    # Công ty B: CÓ data_dir riêng khai báo tay (bản cũ, hiếm gặp) — vẫn phải
    # được bảo vệ như hành vi cũ.
    save_dir_b = tempfile.mkdtemp(prefix="ketoan_savedir_B_")
    data_dir_b = tempfile.mkdtemp(prefix="ketoan_datadir_B_rieng_")
    file_xml_b = os.path.join(save_dir_b, "hoadon_ban_ra_002.xml")
    file_du_lieu_b = os.path.join(data_dir_b, "DuLieu_0301111222.json")
    with open(file_xml_b, "w", encoding="utf-8") as f:
        f.write("<invoice>rac tai xuong B, xoa duoc</invoice>")
    with open(file_du_lieu_b, "w", encoding="utf-8") as f:
        f.write('{"hach_toan": ["du lieu that B, KHONG duoc xoa"]}')

    conn = db_factory()
    conn.execute("INSERT INTO companies (id, mst, save_dir, data_dir) VALUES (1,?,?,?)",
                 ("0319103095", save_dir_a, ""))
    conn.execute("INSERT INTO companies (id, mst, save_dir, data_dir) VALUES (2,?,?,?)",
                 ("0301111222", save_dir_b, data_dir_b))
    conn.commit()
    conn.close()

    ket_qua = server.clear_downloads(scope="all")

    assert not os.path.isfile(file_xml), "File .xml rác trong save_dir (công ty A) phải bị xoá như cũ"
    assert not os.path.isfile(file_xlsx_rac), "File .xlsx rác trong save_dir (công ty A) phải bị xoá như cũ"
    assert not os.path.isfile(file_xml_b), "File .xml rác trong save_dir (công ty B) phải bị xoá như cũ"
    print("PASS 1: file rác (.xml/.xlsx) trong Thư mục lưu file XML/PDF vẫn bị xoá đúng như hành vi cũ.")

    assert os.path.isfile(file_du_lieu), (
        "File dữ liệu công ty THẬT (DuLieu_<MST>.json trong thư mục con 'DU LIEU CTY' TỰ ĐỘNG, công ty "
        "KHÔNG có data_dir riêng) TUYỆT ĐỐI KHÔNG được xoá — đúng cảnh báo người dùng đã báo trước")
    with open(file_du_lieu, encoding="utf-8") as f:
        assert "KHONG duoc xoa" in f.read(), "Nội dung file dữ liệu công ty A phải còn nguyên vẹn"
    print("PASS 2: file dữ liệu công ty (DuLieu_<MST>.json) trong thư mục con 'DU LIEU CTY' TỰ ĐỘNG (không "
          "có data_dir riêng) KHÔNG bị xoá — đúng yêu cầu 'mục xoá file đã tải không được xoá file DU LIEU CTY'.")

    assert os.path.isfile(file_du_lieu_b), (
        "File dữ liệu công ty B (data_dir riêng khai báo tay, bản cũ) cũng TUYỆT ĐỐI KHÔNG được xoá")
    print("PASS 3: file dữ liệu công ty có data_dir riêng khai báo tay (bản cũ) vẫn được bảo vệ như trước.")

    assert ket_qua["so_file"] == 3, f"Phải xoá đúng 3 file rác (.xml x2 + .xlsx), không hơn không kém — got {ket_qua}"
    print(f"PASS 4: tổng số file đã xoá đúng = {ket_qua['so_file']} (chỉ file rác, không đụng dữ liệu công ty).")
finally:
    server.db = orig_db

print("\nALL DONE")
