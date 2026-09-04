import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: /api/xk/cap-nhat-ton-misa (nút "🔄 Cập nhật tồn kho" ->
"Lấy tồn kho từ MISA") khi KHÔNG chọn riêng Mã kho nào (TẤT CẢ kho) PHẢI
THAY THẾ TOÀN BỘ Sheet TON bằng đúng kết quả MISA vừa trả về cho Kỳ báo cáo
đang chọn — KHÔNG được cộng dồn mãi với lần lấy TRƯỚC (Kỳ báo cáo khác).

Đúng ca thật người dùng báo cáo: "số mã hàng Tồn kho đã tăng từ 247 lên
713 mã cái này bị lỗi khi tôi thay đổi kỳ báo cáo nhấn cập nhật lại và quay
lại kỳ báo cáo năm 2024 thì phần mềm không thay đổi 247 mà vẫn giữ 713 mã
xem lại chổ này" — lần 1 chọn Kỳ báo cáo hẹp (vd Năm 2024) -> lấy được 247
mã; lần 2 đổi Kỳ báo cáo rộng hơn -> lấy được 713 mã (đúng, thời gian rộng
hơn thấy nhiều mã hơn); lần 3 CHỌN LẠI đúng Kỳ báo cáo hẹp như lần 1 (Năm
2024, đáng lẽ phải RA LẠI ĐÚNG 247 mã) nhưng vẫn hiện 713 mã — vì trước đây
endpoint này LUÔN dùng kiểu 'cập nhật' (merge, giữ mã cũ không nhắc tới)
giống hệt xk_cap_nhat_ton (file Excel) — mỗi lần đổi Kỳ báo cáo chỉ CỘNG
THÊM, không bao giờ bớt xuống đúng số mã thật của khoảng thời gian đang
chọn.

CÓ chọn riêng Mã kho cụ thể thì VẪN merge như cũ (không xoá dữ liệu của
các kho KHÁC không nằm trong lần lấy này) — test kèm ca đối chứng."""
import sys, sqlite3, os as _os, tempfile, asyncio
sys.path.insert(0, _REPO_ROOT)
import server

_db_path = tempfile.mktemp(suffix=".sqlite3")
_data_dir = tempfile.mkdtemp()


def db_factory():
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    return conn


orig_db, orig_data_dir = server.db, server.DATA_DIR
orig_connect, orig_cfg = server._misa_sql_connect, server._misa_sql_cfg
server.db = db_factory
server.DATA_DIR = _data_dir

try:
    conn = db_factory()
    conn.execute("""CREATE TABLE companies (id INTEGER PRIMARY KEY, mst TEXT,
        save_dir TEXT, data_dir TEXT)""")
    conn.execute("INSERT INTO companies VALUES (1,'0318332127','','')")
    conn.commit()
    conn.close()

    server._misa_sql_cfg = lambda cid: {"database": "TESTDB"}

    # ===== Lần 1: Kỳ báo cáo HẸP (giả lập "Năm 2024") -> 247 mã (rút gọn còn
    # 2 mã cho gọn test, chỉ cần khác con số ở lần 2). =====
    ket_qua_hep = [
        {"ma": "HH00087-8", "ten": "Gạch men 600x1200 mm", "dvt": "m2", "ton": 79.2, "gia": 140878,
         "kho": "HH", "kho_ro": True, "ton_kho_min": 79.2, "dau_ky": 0, "dau_ky_kho_min": 0},
        {"ma": "HH00026-8", "ten": "Gạch 60x120", "dvt": "Hộp", "ton": 110, "gia": 149364,
         "kho": "HH", "kho_ro": True, "ton_kho_min": 110, "dau_ky": 0, "dau_ky_kho_min": 0},
    ]
    server._misa_lay_ton_kho = lambda cid, db, tu_ngay=None, den_ngay=None, ma_kho_list=None: (ket_qua_hep, ["HH"])
    d1 = asyncio.run(server.xk_cap_nhat_ton_misa(1, tu="", den="2024-12-31", kho=""))
    print("Lần 1 (Kỳ báo cáo hẹp, TẤT CẢ kho):", d1)
    assert d1["tong"] == 2, f"Lần đầu lấy TẤT CẢ kho phải ra đúng {len(ket_qua_hep)} mã — được {d1['tong']}"

    # ===== Lần 2: đổi Kỳ báo cáo RỘNG hơn -> 3 mã (thêm 1 mã mới, đúng vì
    # thời gian rộng hơn thấy nhiều mã hơn — hợp lý, không phải lỗi). =====
    ket_qua_rong = ket_qua_hep + [
        {"ma": "MH50", "ten": "Gạch ốp lát có tráng men, kích thước 600x1200mm", "dvt": "m2", "ton": 26.64,
         "gia": 250000, "kho": "HH", "kho_ro": True, "ton_kho_min": 26.64, "dau_ky": 0, "dau_ky_kho_min": 0},
    ]
    server._misa_lay_ton_kho = lambda cid, db, tu_ngay=None, den_ngay=None, ma_kho_list=None: (ket_qua_rong, ["HH"])
    d2 = asyncio.run(server.xk_cap_nhat_ton_misa(1, tu="", den="2026-09-04", kho=""))
    print("Lần 2 (Kỳ báo cáo rộng, TẤT CẢ kho):", d2)
    assert d2["tong"] == 3

    # ===== Lần 3: CHỌN LẠI đúng Kỳ báo cáo hẹp như lần 1 -> PHẢI VỀ LẠI
    # ĐÚNG 2 mã (KHÔNG được giữ 3 mã như lần 2 — đúng lỗi thật đã báo cáo). =====
    server._misa_lay_ton_kho = lambda cid, db, tu_ngay=None, den_ngay=None, ma_kho_list=None: (ket_qua_hep, ["HH"])
    d3 = asyncio.run(server.xk_cap_nhat_ton_misa(1, tu="", den="2024-12-31", kho=""))
    print("Lần 3 (chọn lại Kỳ báo cáo hẹp như lần 1, TẤT CẢ kho):", d3)
    assert d3["tong"] == 2, (
        f"Chọn lại ĐÚNG Kỳ báo cáo hẹp như lần 1 (TẤT CẢ kho) PHẢI THAY THẾ toàn bộ, ra lại ĐÚNG "
        f"{len(ket_qua_hep)} mã — KHÔNG được giữ 3 mã cộng dồn từ lần 2 (Kỳ báo cáo khác) — được {d3['tong']}")
    assert d3.get("so_xoa") == 1, f"Phải báo đã bỏ đúng 1 mã (MH50, không còn thuộc Kỳ báo cáo này) — được {d3}"
    ma_con_lai = {t["ma"] for t in server._doc_du_lieu_cty(1)["xk_ton"]}
    assert ma_con_lai == {"HH00087-8", "HH00026-8"}, f"Danh sách mã còn lại phải đúng — được {ma_con_lai}"
    print("PASS: TẤT CẢ kho -> THAY THẾ đúng, không còn cộng dồn qua các lần đổi Kỳ báo cáo.")

    # ===== Đối chứng: CÓ chọn riêng 1 Mã kho cụ thể -> vẫn MERGE (không xoá
    # mã của kho KHÁC không nằm trong lần lấy này). =====
    server._doc_du_lieu_cty(1)["xk_ton"]  # (đang có 2 mã kho "HH" từ lần 3)
    ket_qua_kho_khac = [
        {"ma": "NVL001", "ten": "Xi măng", "dvt": "Bao", "ton": 5, "gia": 90000,
         "kho": "NVL", "kho_ro": True, "ton_kho_min": 5, "dau_ky": 0, "dau_ky_kho_min": 0},
    ]
    server._misa_lay_ton_kho = lambda cid, db, tu_ngay=None, den_ngay=None, ma_kho_list=None: (
        ket_qua_kho_khac, ["NVL"])
    d4 = asyncio.run(server.xk_cap_nhat_ton_misa(1, tu="", den="2026-09-04", kho="NVL"))
    print("Lần 4 (chọn riêng kho NVL):", d4)
    ma_sau4 = {t["ma"] for t in server._doc_du_lieu_cty(1)["xk_ton"]}
    assert ma_sau4 == {"HH00087-8", "HH00026-8", "NVL001"}, (
        f"CÓ chọn riêng 1 kho (NVL) -> PHẢI merge, GIỮ NGUYÊN 2 mã kho HH cũ (không nằm trong lần lấy NVL "
        f"này) + thêm mã NVL001 mới — được {ma_sau4}")
    assert d4.get("so_xoa", 0) == 0, "Có chọn riêng kho -> KHÔNG được xoá gì (merge, không phải thay thế)"
    print("PASS: có chọn riêng Mã kho -> vẫn merge, không xoá dữ liệu kho khác.")

    print("\nTẤT CẢ TEST PASS")
finally:
    server.db = orig_db
    server.DATA_DIR = orig_data_dir
    server._misa_sql_connect = orig_connect
    server._misa_sql_cfg = orig_cfg
    try:
        _os.remove(_db_path)
    except OSError:
        pass
    import shutil
    shutil.rmtree(_data_dir, ignore_errors=True)
