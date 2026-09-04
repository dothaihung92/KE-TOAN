import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: "Mua hàng NK" (_gen_mua_hang_nk, dùng bởi 4a "Nhập kho
vào MISA") và "Danh mục VTHH" (_gen_vthh_from_grid) PHẢI tra bản đồ mã hàng
(dm_hh/dm_nvl.map) đúng CÙNG công thức Ký tự (_dm_ky_tu, không phân biệt
hoa/thường) và PHẢI dùng NGUYÊN VẸN mã CÓ SẴN thật trong MISA (không thêm
hậu tố '-thuế suất') giống hệt _gen_danh_muc — nếu không sẽ tính RA MỘT MÃ
HÀNG KHÁC với mã đã lưu/đồng bộ, khiến _misa_ghi_mua_hang không dò được
InventoryItem tương ứng trong MISA (tra theo hang[ma.lower()]) và ÂM THẦM
BỎ QUA toàn bộ dòng hoá đơn -> "0 chứng từ, 0 dòng" dù Danh mục Hàng hóa đã
đúng và Bảng kê Đầu vào đã Lưu đầy đủ.

Đúng ca thật người dùng báo cáo (CÔNG TY TNHH ỐC GẠO FAMILY): bước 3a
"Danh mục Hàng hóa" tìm đúng 31 mã có sẵn, nhưng bước 4a/4b/4c "Import tự
động toàn bộ" đều ghi "Sẽ ghi: 0 chứng từ, 0 dòng" dù đã Import & Lưu Bảng
kê Đầu vào đầy đủ."""
import sys, sqlite3, os, tempfile
sys.path.insert(0, _REPO_ROOT)
import server

_db_path = tempfile.mktemp(suffix=".sqlite3")
_data_dir = tempfile.mkdtemp()


def db_factory():
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    return conn


orig_db, orig_data_dir = server.db, server.DATA_DIR
server.db = db_factory
server.DATA_DIR = _data_dir

NK_HEADER = ["Ký hiệu", "Số HĐ", "Ngày", "Người bán", "MST bán", "Tên hàng hóa/dịch vụ",
             "ĐVT", "Số lượng", "Đơn giá", "Thành tiền", "Thuế suất", "Tiền thuế GTGT",
             "Nợ", "Có"]

try:
    conn = db_factory()
    conn.execute("""CREATE TABLE companies (id INTEGER PRIMARY KEY, mst TEXT,
        save_dir TEXT, data_dir TEXT)""")
    conn.execute("INSERT INTO companies VALUES (1,'3700149145','','')")
    conn.commit()
    conn.close()

    # ===== Danh mục Hàng hóa ĐÃ ĐỒNG BỘ mã thật MISA cho sản phẩm, dùng
    # đúng Ký tự (_dm_ky_tu) làm khoá bản đồ — giống trạng thái sau khi
    # "🔄 Đồng bộ mã có sẵn trong MISA" chạy tự động. =====
    ten_sp = "Bia Tiger Bạc thùng 24 lon x 330ml"
    dvt = "Thùng"
    ky = server._dm_ky_tu(ten_sp, dvt)
    data = server._doc_du_lieu_cty(1)
    data["dm_hh"] = {"map": {ky: "MH225"}, "next": 1, "rows": []}
    server._ghi_du_lieu_cty(1, data)

    # Dòng hoá đơn thật: Tên hàng đúng y hệt (trường hợp đơn giản nhất, đủ
    # để lộ lỗi công thức Ký tự khác nhau và lỗi luôn nối hậu tố).
    row = ["", "0001234", "05/08/2026", "Cty TNHH Bia Sài Gòn", "3700149145",
           ten_sp, dvt, 10, 350000, 3500000, 10, 350000, "1561", "331"]

    out_vthh = server._gen_vthh_from_grid(1, NK_HEADER, [row])
    print("VTHH out:", out_vthh)
    ma_vthh = next((r[0] for r in out_vthh if r[1] == ten_sp), None)
    assert ma_vthh == "MH225", (
        f"'Danh mục VTHH' phải dùng ĐÚNG mã đã đồng bộ 'MH225' (nguyên vẹn, không thêm hậu tố "
        f"'-thuế suất') — được {ma_vthh!r}")

    out_nk = server._gen_mua_hang_nk(1, NK_HEADER, [row])
    print("Mua hang NK out:", out_nk)
    assert len(out_nk) == 1, f"Phải sinh đúng 1 dòng Mua hàng NK — được {len(out_nk)}"
    ma_nk = out_nk[0][19]     # cột 'Mã hàng (*)'
    assert ma_nk == "MH225", (
        f"'Mua hàng NK' (dùng để ghi vào MISA, bước 4a) PHẢI dùng ĐÚNG mã đã đồng bộ 'MH225' "
        f"(nguyên vẹn — KHÔNG tự bịa ra mã khác/thêm hậu tố), nếu không MISA sẽ không dò được "
        f"InventoryItem tương ứng và ÂM THẦM BỎ QUA cả dòng hoá đơn (đúng lỗi thật: '0 chứng từ, "
        f"0 dòng' dù Danh mục đã đúng) — được {ma_nk!r}")
    print("PASS: _gen_vthh_from_grid và _gen_mua_hang_nk dùng đúng mã đã đồng bộ, không tự bịa mã khác.")

    # ===== Ca 2: chưa đồng bộ (mã tự sinh dạng HH00001) -> vẫn phải nối
    # đúng hậu tố '-thuế suất' như cũ (không phá hành vi bình thường). =====
    data2 = server._doc_du_lieu_cty(1)
    ten_sp2 = "Bia Heineken lon 330ml"
    ky2 = server._dm_ky_tu(ten_sp2, dvt)
    data2["dm_hh"] = {"map": {ky2: "HH00007"}, "next": 8, "rows": []}
    server._ghi_du_lieu_cty(1, data2)
    row2 = ["", "0005678", "07/08/2026", "Cty TNHH Bia Sài Gòn", "3700149145",
            ten_sp2, dvt, 5, 400000, 2000000, 10, 200000, "1561", "331"]
    out_nk2 = server._gen_mua_hang_nk(1, NK_HEADER, [row2])
    ma_nk2 = out_nk2[0][19]
    assert ma_nk2 == "HH00007-10", f"Mã TỰ SINH vẫn phải nối hậu tố thuế suất như cũ — được {ma_nk2!r}"
    print("PASS: mã tự sinh (chưa đồng bộ) vẫn nối đúng hậu tố '-thuế suất' như trước.")

    # ===== Ca 3: khác HOA/thường giữa Tên hàng trong bảng kê và Tên đã
    # đồng bộ (đúng lỗi thật: MISA lưu tên không nhất quán hoa/thường giữa
    # các mã) -> vẫn phải khớp đúng mã đã đồng bộ, không tạo mã mới. =====
    ten_sp3_dongbo = "CHẬU POLYSTONE WILV24 - MTWT"
    ten_sp3_bangke = "Chậu Polystone WILV24 - MTWT"
    ky3 = server._dm_ky_tu(ten_sp3_dongbo, "Cái")
    data3 = server._doc_du_lieu_cty(1)
    data3["dm_hh"]["map"][ky3] = "MH553"
    server._ghi_du_lieu_cty(1, data3)
    row3 = ["", "0009999", "10/08/2026", "Cty TNHH ABC", "3700149145",
            ten_sp3_bangke, "Cái", 2, 500000, 1000000, 8, 80000, "1561", "331"]
    out_nk3 = server._gen_mua_hang_nk(1, NK_HEADER, [row3])
    ma_nk3 = out_nk3[0][19]
    assert ma_nk3 == "MH553", (
        f"Tên hàng khác HOA/thường với tên đã đồng bộ vẫn phải khớp đúng mã 'MH553' (Ký tự không "
        f"phân biệt hoa/thường) — được {ma_nk3!r}")
    print("PASS: khác hoa/thường vẫn khớp đúng mã đã đồng bộ trong Mua hàng NK.")

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
