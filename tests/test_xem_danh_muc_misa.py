import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: "👁 Xem danh mục MISA" — đọc TOÀN BỘ mã hàng đang có
sẵn trong MISA (không chỉ mã có trong bảng kê đang xử lý) để hiển thị lên
lưới Danh mục, đúng yêu cầu người dùng: "ý tôi vậy còn dữ liệu danh mục
trên misa sao không hiện lên? ... xem toàn bộ 541 mã trong MISA ngay trên
lưới này".

KHÔNG lọc theo TK kho (InventoryAccount) nữa — ảnh chụp MISA thật (màn
"Vật tư hàng hóa") cho thấy mã CÓ SẴN tạo TRƯỚC khi dùng phần mềm (vd
'MH225') thường CHƯA từng gán TK kho dù đúng Tính chất 'Vật tư hàng hóa',
lọc theo TK sẽ loại mất chính mã cần xem/đối chiếu nhất."""
import sys
sys.path.insert(0, _REPO_ROOT)
import server


class FakeCursor:
    def execute(self, sql, params=()):
        self.last_sql = sql
        return self

    def fetchall(self):
        if "FROM Unit" in self.last_sql:
            return [("U1", "Cái")]
        if "FROM InventoryItem" in self.last_sql:
            return [
                ("MH613", "Chậu Polystone D35xH45 cm - Matte Black", "U1", 8),
                ("HH00001-8", "Chậu Polystone ASH50 - WT", "U1", 8),
                # Mã cũ KHÔNG có TK kho (đúng ca thật MH225/MH553) -> vẫn
                # phải đọc được, không còn bị loại vì thiếu TK nữa.
                ("MH225", "Chậu Polystone ASH30 - MTWT", "U1", 8),
            ]
        return []


class FakeConn:
    def cursor(self):
        return FakeCursor()

    def close(self):
        pass


orig_connect = server._misa_sql_connect
server._misa_sql_connect = lambda cid, database=None: FakeConn()

try:
    rows = server._misa_doc_toan_bo_danh_muc(1, "TESTDB", "hh")
    print("Danh mục MISA (hh):", rows)
    assert len(rows) == 3, f"Phải đọc đúng cả 3 mã, kể cả mã không có TK kho — được {len(rows)}: {rows}"
    ma_list = [r[0] for r in rows]
    assert "MH613" in ma_list and "HH00001-8" in ma_list and "MH225" in ma_list, (
        f"Mã 'MH225' (không có TK kho, đúng ca thật) PHẢI có trong kết quả — được {ma_list}")

    dong_mh613 = next(r for r in rows if r[0] == "MH613")
    assert len(dong_mh613) == 11, f"Mỗi dòng phải đủ 11 cột khớp _dm_headers (Mã/Mặt hàng/ĐVT/Thuế suất/Ký "
    f"tự/SL/Đơn giá/Thành tiền/Hoá đơn/Ngày/Kho) — được {len(dong_mh613)} cột: {dong_mh613}"
    assert dong_mh613[1] == "Chậu Polystone D35xH45 cm - Matte Black"
    assert dong_mh613[2] == "Cái"
    assert dong_mh613[3] == 8, f"Thuế suất phải lấy đúng từ InventoryItem.TaxRate — được {dong_mh613[3]}"
    assert dong_mh613[4] == server._dm_ky_tu("Chậu Polystone D35xH45 cm - Matte Black", "Cái"), f"Ký tự phải khớp đúng khoá dùng ở _gen_danh_muc — được {dong_mh613[4]}"
    assert dong_mh613[5] == "" and dong_mh613[8] == "", (
        f"SL/Hoá đơn PHẢI để trống (dữ liệu Danh mục THUẦN từ MISA, không gắn với hoá đơn cụ thể nào) — "
        f"được sl={dong_mh613[5]!r}, hoadon={dong_mh613[8]!r}")
    print("PASS: đọc đúng toàn bộ mã trong MISA (kể cả mã không có TK kho), đủ 11 cột, SL/Hoá đơn để trống.")

    print("\nTẤT CẢ TEST PASS")
finally:
    server._misa_sql_connect = orig_connect
