import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: đồng bộ mã hàng ĐÃ CÓ SẴN trong MISA (InventoryItem —
kể cả mã tạo TRƯỚC khi dùng phần mềm này, vd 'MH316'/'MH613') để lần "Sinh
Danh mục" (_gen_danh_muc) SAU không tự sinh mã 'HH0000X' MỚI trùng lặp cho
tên hàng đã có mã sẵn trong MISA.

Đúng ca thật người dùng báo cáo: ảnh chụp MISA "Tổng hợp tồn kho" cho thấy
3 mã KHÁC NHAU cho CÙNG tên "Chậu Polystone D35xH45 cm - Matte Black"
(HH00063-8 do phần mềm tự sinh, MH316/MH613 có sẵn từ trước trong MISA) —
"xem lại phần gộp mã hàng tôi có thiết lập nếu giống tên hàng sẽ gôm về 1
mã hàng mà" — phần mềm chỉ gộp trùng tên trong PHẠM VI CỦA CHÍNH NÓ (bản đồ
tên->mã tự học từ trước tới giờ), không hề biết MH316/MH613 đã tồn tại sẵn
trong MISA nên vẫn tự sinh thêm HH00063-8 mới.

CŨNG xác nhận: KHÔNG còn lọc theo TK kho (InventoryAccount) nữa — ảnh chụp
MISA thật (màn "Vật tư hàng hóa") cho thấy mã CÓ SẴN tạo TRƯỚC khi dùng
phần mềm ('MH225'/'MH553' cho CÙNG tên 'Chậu Polystone ASH30 - MTWT')
thường CHƯA từng gán 'Tài khoản kho' (InventoryAccount để TRỐNG) dù đúng
Tính chất 'Vật tư hàng hóa' — lọc theo TK (bản trước) loại mất đúng những
mã này, khiến "tên giống mà vẫn tạo mã mới"."""
import sys, sqlite3, os, tempfile
sys.path.insert(0, _REPO_ROOT)
import server

_db_path = tempfile.mktemp(suffix=".sqlite3")
_data_dir = tempfile.mkdtemp()


def db_factory():
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    return conn


orig_db, orig_data_dir, orig_connect = server.db, server.DATA_DIR, server._misa_sql_connect
server.db = db_factory
server.DATA_DIR = _data_dir

HANG_HOA_HEADER = ["Nợ", "Tên hàng hóa/dịch vụ", "ĐVT", "Thuế suất", "Số lượng",
                   "Đơn giá", "Thành tiền", "Số HĐ", "Ngày"]


class FakeCursor:
    def execute(self, sql, params=()):
        self.last_sql = sql
        return self

    def fetchall(self):
        if "FROM Unit" in self.last_sql:
            return [("U1", "Cái")]
        if "FROM InventoryItem" in self.last_sql:
            return [
                # Đã có sẵn trong MISA TỪ TRƯỚC (mã KHÔNG theo khuôn tự sinh
                # 'HH00000') cho ĐÚNG 2 tên hàng bị báo cáo gán trùng. Cột thứ
                # 4 (InventoryItemType) = 1 "Vật tư, hàng hóa" — tính chất
                # ĐÚNG cho cả 3 mã ở đây (xem test_dong_bo_danh_muc_uu_tien_vthh.py
                # cho ca ưu tiên tính chất khi có mã Thành phẩm trùng tên).
                ("MH613", "Chậu Polystone D35xH45 cm - Matte Black", "U1", 1),
                ("MH607", "Chậu Polystone D34xH30 cm - Matte White", "U1", 1),
                # Mã cũ TỪNG rất phổ biến trong dữ liệu thật: KHÔNG có
                # InventoryAccount (nay hàm KHÔNG còn lọc theo TK nên vẫn
                # PHẢI đọc được — xem _misa_doc_toan_bo_danh_muc/
                # _misa_dong_bo_danh_muc_tu_misa, đã bỏ cột InventoryAccount
                # khỏi câu SELECT, đây chỉ còn (code, name, unit_id, item_type)
                # 4 cột).
                ("MH225", "Chậu Polystone ASH30 - MTWT", "U1", 1),
            ]
        return []


class FakeConn:
    def cursor(self):
        return FakeCursor()

    def close(self):
        pass


server._misa_sql_connect = lambda cid, database=None: FakeConn()

try:
    conn = db_factory()
    conn.execute("""CREATE TABLE companies (id INTEGER PRIMARY KEY, mst TEXT,
        save_dir TEXT, data_dir TEXT)""")
    conn.execute("INSERT INTO companies VALUES (1,'0317743519','','')")
    conn.commit()
    conn.close()

    # ===== Trước khi đồng bộ: _gen_danh_muc tự sinh mã HH0000X MỚI cho tên
    # hàng CHƯA từng gặp, dù MISA đã có mã MH613/MH607 sẵn cho đúng tên đó
    # (đúng lỗi thật đang bị báo cáo). =====
    rows_truoc = [
        ["1561", "Chậu Polystone D35xH45 cm - Matte Black", "Cái", 8, 50, 370000, 18500000, "41", "18/05/2026"],
    ]
    all_rows, so_moi = server._gen_danh_muc(1, "hh", HANG_HOA_HEADER, rows_truoc)
    ma_truoc = all_rows[0][0]
    print("Mã TRƯỚC khi đồng bộ:", ma_truoc)
    assert ma_truoc.startswith("HH0") and ma_truoc.endswith("-8"), (
        f"Trước khi đồng bộ, chưa biết MH613 nên phải tự sinh mã HH0000X-8 kiểu cũ (để tái hiện đúng lỗi "
        f"thật trước khi fix) — được {ma_truoc}")
    # _gen_danh_muc chỉ TÍNH TOÁN (không tự lưu) — mô phỏng đúng luồng thật:
    # người dùng bấm "💾 Lưu" ở lưới Danh mục sau khi Sinh Danh mục, mã tự
    # sinh mới CHỐT lại trong bản đồ (_luu_danh_muc) rồi mới đồng bộ MISA.
    server._luu_danh_muc(1, "hh", all_rows)

    # ===== ĐÚNG LỖI THẬT người dùng gặp SAU khi có nút Đồng bộ (round 1 của
    # fix): công ty đã Sinh Danh mục cho GẦN NHƯ MỌI mặt hàng từ trước (bản
    # đồ đã có sẵn mã TỰ SINH 'HH00001-8' ở bước trên, y hệt thực tế 541 mã
    # MISA nhưng "học 0 mã mới") — vì quy tắc "chỉ thêm, không ghi đè" (bản
    # ĐẦU TIÊN của _misa_dong_bo_danh_muc_tu_misa) chặn đứng chính trường hợp
    # CẦN sửa nhất: tên hàng ĐÃ có mã tự sinh (placeholder) vẫn phải được
    # THAY bằng mã THẬT trong MISA khi tìm thấy. =====
    kq_dongbo_ghide = server._misa_dong_bo_danh_muc_tu_misa(1, "TESTDB", "hh")
    print("Kết quả đồng bộ (đang có sẵn mã TỰ SINH từ trước):", kq_dongbo_ghide)
    assert kq_dongbo_ghide["so_thay_the"] == 1, (
        f"Phải THAY THẾ đúng 1 mã (D35xH45 Matte Black đang trỏ mã tự sinh '{ma_truoc}' -> phải đổi thành "
        f"'MH613' có sẵn thật trong MISA) — KHÔNG được báo 'học 0 mã mới' như lỗi thật đã gặp (bản đồ đã "
        f"có mã tự sinh cho gần hết mặt hàng nên round đầu của fix không sửa được gì) — được {kq_dongbo_ghide}")
    data1 = server._doc_du_lieu_cty(1)
    assert data1["dm_hh"]["map"][server._dm_ky_tu("Chậu Polystone D35xH45 cm - Matte Black", "Cái")] == "MH613", (
        "Mã tự sinh (placeholder) PHẢI được thay bằng mã MISA thật khi tìm thấy — không được giữ nguyên "
        "mã tự sinh mãi mãi chỉ vì đã 'có' trong bản đồ")
    print("PASS: mã TỰ SINH (placeholder) được tự động THAY bằng mã MISA thật khi đồng bộ — không còn kẹt "
          "ở tình trạng 'học 0 mã mới' dù MISA có sẵn hàng trăm mã, đúng lỗi thật đã gặp.")

    # Reset lại dữ liệu công ty để test riêng luồng "thêm mới hoàn toàn" (chưa
    # có gì trong bản đồ) — độc lập với ca thay thế placeholder ở trên.
    data1 = server._doc_du_lieu_cty(1)
    data1["dm_hh"] = {}
    server._ghi_du_lieu_cty(1, data1)

    # ===== Đồng bộ mã có sẵn trong MISA (bản đồ RỖNG, thêm mới hoàn toàn) —
    # xác nhận đọc được CẢ 3 mã kể cả 'MH225' (mã cũ không có TK kho, đúng
    # tình huống thật vừa xác nhận qua ảnh chụp "Vật tư hàng hóa" MISA). =====
    kq_dongbo = server._misa_dong_bo_danh_muc_tu_misa(1, "TESTDB", "hh")
    print("Kết quả đồng bộ:", kq_dongbo)
    assert kq_dongbo["so_ma_misa"] == 3, (
        f"Phải đọc đúng CẢ 3 mã (không còn lọc theo TK kho — mã cũ 'MH225' không có TK vẫn phải đọc "
        f"được) — được {kq_dongbo}")
    assert kq_dongbo["so_them_moi"] == 3

    data1 = server._doc_du_lieu_cty(1)
    keymap = data1["dm_hh"]["map"]
    assert keymap.get(server._dm_ky_tu("Chậu Polystone D35xH45 cm - Matte Black", "Cái")) == "MH613"
    assert keymap.get(server._dm_ky_tu("Chậu Polystone D34xH30 cm - Matte White", "Cái")) == "MH607"
    assert keymap.get(server._dm_ky_tu("Chậu Polystone ASH30 - MTWT", "Cái")) == "MH225", (
        f"Mã 'MH225' (không có TK kho, đúng ca thật ảnh chụp MISA gửi) PHẢI vẫn được đồng bộ — được {keymap}")
    print("PASS: đồng bộ đọc được CẢ mã KHÔNG có TK kho (không còn lọc theo TK, đúng ca thật MH225/MH553).")

    # ===== Sau khi đồng bộ: _gen_danh_muc cho ĐÚNG tên hàng đó PHẢI dùng
    # NGUYÊN VẸN mã MH613 có sẵn trong MISA, KHÔNG tự sinh HH0000X mới, và
    # KHÔNG thêm hậu tố '-thuế suất' (mã MISA đã hoàn chỉnh). =====
    all_rows2, so_moi2 = server._gen_danh_muc(1, "hh", HANG_HOA_HEADER, rows_truoc)
    ma_sau = all_rows2[0][0]
    print("Mã SAU khi đồng bộ:", ma_sau)
    assert ma_sau == "MH613", (
        f"Sau khi đồng bộ, PHẢI dùng NGUYÊN VẸN mã có sẵn 'MH613' trong MISA cho 'Chậu Polystone D35xH45 "
        f"cm - Matte Black', KHÔNG được tự sinh mã HH0000X mới trùng lặp nữa — được {ma_sau}")

    # ===== Đối chứng: đồng bộ LẦN 2 KHÔNG được ghi đè mã ĐÃ HỌC (kể cả nếu
    # nó là mã tự sinh trước đó của phần mềm, để không làm lệch chứng từ cũ
    # đã ghi sổ theo mã đó) — chỉ thêm cho tên hàng THẬT SỰ MỚI. =====
    data1 = server._doc_du_lieu_cty(1)
    data1["dm_hh"]["map"]["ChậuPolystoneD31xH40cm-MatteBlackCái"] = "HH-DA-HOC-TRUOC"
    server._ghi_du_lieu_cty(1, data1)
    kq_dongbo2 = server._misa_dong_bo_danh_muc_tu_misa(1, "TESTDB", "hh")
    assert kq_dongbo2["so_them_moi"] == 0, (
        f"Lần đồng bộ THỨ 2 không có tên hàng mới nào (3 mã đã học từ trước) -> so_them_moi phải = 0 — "
        f"được {kq_dongbo2}")
    data1 = server._doc_du_lieu_cty(1)
    assert data1["dm_hh"]["map"]["ChậuPolystoneD31xH40cm-MatteBlackCái"] == "HH-DA-HOC-TRUOC", (
        "Đồng bộ KHÔNG được ghi đè mã đã học từ trước (dù không liên quan gì tới MISA) — mất dữ liệu đã học")
    print("PASS: đồng bộ lần 2 không ghi đè/không thêm trùng, giữ nguyên mã đã học trước đó.")

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
