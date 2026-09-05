import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: nút '🔄 Cập nhật tồn kho' (Xuất Kho) chỉnh lại để LẤY
TRỰC TIẾP tồn kho từ MISA (bảng InventoryLedger — đúng Sổ Kho MISA dùng để
lên báo cáo 'Tổng hợp tồn kho') THAY VÌ bắt buộc phải import file Excel thủ
công như trước — kèm chọn khoảng thời gian (Từ/Đến) và chọn Mã kho.

Test hàm THUẦN _misa_lay_danh_sach_kho (đọc bảng Stock, dùng để hiển thị ô
chọn Mã kho) và _misa_lay_ton_kho (tính tồn kho theo InventoryLedger, TRẢ VỀ
ĐÚNG cấu trúc như _doc_file_ton_kho để dùng lại nguyên các hàm/luồng Xuất
Kho hiện có — _xk_ton_an_toan/_xk_dau_ky_an_toan/_xk_canh_bao_kho_ton...)."""
import sys
sys.path.insert(0, _REPO_ROOT)
import server


class FakeCursor:
    def __init__(self, stock_rows=None, ledger_rows=None):
        self._stock_rows = stock_rows or []
        self._ledger_rows = ledger_rows or []
        self.last_sql = None
        self.last_params = None

    def execute(self, sql, params=None):
        self.last_sql = sql
        self.last_params = params
        return self

    def fetchall(self):
        if "FROM Stock" in self.last_sql:
            return self._stock_rows
        if "FROM InventoryLedger" in self.last_sql:
            return self._ledger_rows
        return []


class FakeConn:
    def __init__(self, cur):
        self._cur = cur

    def cursor(self):
        return self._cur

    def close(self):
        pass


orig_connect = server._misa_sql_connect
try:
    # ===== _misa_lay_danh_sach_kho: đọc đúng bảng Stock, an toàn khi lỗi =====
    curA = FakeCursor(stock_rows=[("HH", "Hàng Hóa"), ("NVL", None)])
    server._misa_sql_connect = lambda cid, database=None: FakeConn(curA)
    dsA = server._misa_lay_danh_sach_kho(1, "TESTDB")
    assert dsA == [{"ma": "HH", "ten": "Hàng Hóa"}, {"ma": "NVL", "ten": "NVL"}], (
        f"_misa_lay_danh_sach_kho phải đọc đúng Mã/Tên kho từ bảng Stock (Tên trống thì lấy tạm Mã) — được {dsA}")
    print("PASS ca A: _misa_lay_danh_sach_kho đọc đúng danh sách Kho từ MISA (Stock).")

    def _connect_loi(cid, database=None):
        raise Exception("không kết nối được MISA")
    server._misa_sql_connect = _connect_loi
    assert server._misa_lay_danh_sach_kho(1, "TESTDB") == [], "Kết nối lỗi -> PHẢI trả [] an toàn, không raise"
    assert server._misa_lay_danh_sach_kho(1, "") == [], "Chưa cấu hình database -> PHẢI trả [] an toàn"
    print("PASS ca B: _misa_lay_danh_sach_kho trả [] an toàn khi MISA chưa kết nối được.")

    # ===== _misa_lay_ton_kho: TẤT CẢ kho, KHÔNG chọn Từ ngày (Đầu kỳ = 0) =====
    # HH00009-8 chỉ ở kho "HH" (kho_ro=True) — HH00099-1 rải rác 2 kho "HH"+"NVL" (kho_ro=False).
    ledger_c2 = [
        ("HH00009-8", "Chậu ABC", "Cái", "HH", "Hàng Hóa", 0, 5, 500000),
        ("HH00099-1", "Chậu XYZ", "Cái", "HH", "Hàng Hóa", 0, 3, 150000),
        ("HH00099-1", "Chậu XYZ", "Cái", "NVL", "NVL", 0, 2, 100000),
    ]
    cur2 = FakeCursor(ledger_rows=ledger_c2)
    server._misa_sql_connect = lambda cid, database=None: FakeConn(cur2)
    rows2, kho2 = server._misa_lay_ton_kho(1, "TESTDB", tu_ngay=None, den_ngay="2026-09-04", ma_kho_list=None)
    assert cur2.last_params == ["2026-09-05"], (
        f"KHÔNG chọn Từ ngày -> KHÔNG được có tham số Đầu kỳ, chỉ 1 tham số Đến ngày+1 (Cuối kỳ CỘNG DỒN "
        f"đến hết ngày đã chọn) — được {cur2.last_params}")
    by_ma2 = {r["ma"]: r for r in rows2}
    assert by_ma2["HH00009-8"]["ton"] == 5 and by_ma2["HH00009-8"]["kho_ro"] is True
    assert by_ma2["HH00009-8"]["kho"] == "Hàng Hóa" and by_ma2["HH00009-8"]["ton_kho_min"] == 5
    assert by_ma2["HH00009-8"]["gia"] == 100000
    assert by_ma2["HH00099-1"]["ton"] == 5 and by_ma2["HH00099-1"]["kho_ro"] is False, (
        "Mã rải rác 2 kho khác nhau PHẢI kho_ro=False (mơ hồ), giống hệt _doc_file_ton_kho")
    assert by_ma2["HH00099-1"]["ton_kho_min"] == 2, "ton_kho_min PHẢI lấy kho ÍT NHẤT (2), không phải tổng (5)"
    assert by_ma2["HH00099-1"]["gia"] == 50000
    assert "Hàng Hóa" in kho2 and "NVL" in kho2
    print("PASS ca 2: _misa_lay_ton_kho (TẤT CẢ kho, không chọn Từ ngày) tính đúng Cuối kỳ + kho_ro/ton_kho_min, "
          "giống hệt cấu trúc _doc_file_ton_kho.")

    # ===== Ca 2b: đúng ca thật người dùng báo cáo (mã 'HH1690-0') — SQL GROUP
    # BY theo (mã, StockCode) trả 1 DÒNG RIÊNG cho kho CŨ đã hết sạch hàng từ
    # trước (Cuối kỳ = 0 tại kho đó) dù mã THẬT SỰ chỉ còn ở ĐÚNG 1 kho hiện
    # tại — KHÔNG được báo "rải rác nhiều kho" chỉ vì còn 1 dòng lịch sử 0
    # đơn vị ở kho cũ (xác nhận đúng qua báo cáo thật: chính màn hình "Tổng
    # hợp tồn kho" của MISA lọc riêng mã 'HH1690-0' CHỈ hiện đúng 1 kho 'HH'). =====
    ledger_c2b = [
        ("HH1690-0", "Nekko cá ngừ rắc tôm và sò điệp", "Thùng", "HH", "HH", 0, 6, 3836160),
        # dòng SQL RIÊNG cho kho CŨ (StockCode khác) — đã hết sạch (Cuối kỳ = 0
        # tại kho này) do phát sinh Sổ Kho TỪ TRƯỚC đây, không còn liên quan.
        ("HH1690-0", "Nekko cá ngừ rắc tôm và sò điệp", "Thùng", "KHOCU", "Kho Chó Mèo Có VAT", 0, 0, 0),
    ]
    cur2b = FakeCursor(ledger_rows=ledger_c2b)
    server._misa_sql_connect = lambda cid, database=None: FakeConn(cur2b)
    rows2b, _ = server._misa_lay_ton_kho(1, "TESTDB", tu_ngay=None, den_ngay="2026-08-31", ma_kho_list=None)
    by_ma2b = {r["ma"]: r for r in rows2b}
    r2b = by_ma2b["HH1690-0"]
    assert r2b["kho_ro"] is True and r2b["kho"] == "HH", (
        f"Mã 'HH1690-0' CHỈ THẬT SỰ còn ở kho 'HH' (kho cũ 'Kho Chó Mèo Có VAT' đã hết sạch, Cuối kỳ=0) "
        f"-> PHẢI kho_ro=True, kho='HH' — KHÔNG được báo rải rác nhiều kho chỉ vì 1 dòng lịch sử 0 đơn vị "
        f"— được {r2b}")
    assert r2b["ton_kho_min"] == 6, f"ton_kho_min PHẢI đúng bằng 6 (kho HH), không bị kéo về 0 bởi kho cũ đã hết — được {r2b}"
    print("PASS ca 2b: _misa_lay_ton_kho không còn báo nhầm 'rải rác nhiều kho' cho mã chỉ còn 1 kho thật "
          "sự có hàng, dù SQL trả thêm dòng lịch sử 0 đơn vị ở kho cũ đã hết sạch.")

    # ===== Có chọn Từ ngày -> Đầu kỳ CỘNG DỒN đúng, tham số Đầu kỳ đi TRƯỚC tham số Cuối kỳ =====
    ledger_c3 = [("HH00009-8", "Chậu ABC", "Cái", "HH", "Hàng Hóa", 20, 5, 500000)]
    cur3 = FakeCursor(ledger_rows=ledger_c3)
    server._misa_sql_connect = lambda cid, database=None: FakeConn(cur3)
    rows3, _ = server._misa_lay_ton_kho(1, "TESTDB", tu_ngay="2026-01-01", den_ngay="2026-09-04", ma_kho_list=None)
    assert cur3.last_params == ["2026-01-01", "2026-09-05"], (
        f"Có chọn Từ ngày -> tham số PHẢI là [Từ ngày (Đầu kỳ, KHÔNG +1), Đến ngày+1 (Cuối kỳ)] — "
        f"được {cur3.last_params}")
    assert rows3[0]["dau_ky"] == 20 and rows3[0]["dau_ky_kho_min"] == 20
    print("PASS ca 3: _misa_lay_ton_kho có chọn Từ ngày tính đúng tồn Đầu kỳ, tham số SQL đúng thứ tự.")

    # ===== Lọc theo Mã kho đã chọn -> WHERE có StockCode IN (...), tham số nối đúng SAU tham số ngày =====
    ledger_c4 = [("HH00009-8", "Chậu ABC", "Cái", "HH", "Hàng Hóa", 0, 5, 500000)]
    cur4 = FakeCursor(ledger_rows=ledger_c4)
    server._misa_sql_connect = lambda cid, database=None: FakeConn(cur4)
    rows4, _ = server._misa_lay_ton_kho(1, "TESTDB", tu_ngay=None, den_ngay="2026-09-04", ma_kho_list=["HH", "NVL"])
    assert "StockCode IN" in cur4.last_sql, f"Có chọn Mã kho -> SQL PHẢI lọc WHERE StockCode IN (...) — được {cur4.last_sql}"
    assert cur4.last_params == ["2026-09-05", "HH", "NVL"], (
        f"Tham số Mã kho đã chọn PHẢI nối SAU tham số ngày, đúng thứ tự đã chọn — được {cur4.last_params}")
    print("PASS ca 4: _misa_lay_ton_kho lọc đúng theo danh sách Mã kho đã chọn.")

    # ===== Ca 4b: đúng lỗi thật người dùng báo cáo — chọn Kỳ báo cáo (vd 2
    # tháng) ra "Đã có 7427 mã hàng tồn kho" trong khi báo cáo Excel CÙNG kỳ
    # của chính MISA chỉ có 1497 dòng. Nguyên nhân: SUM SQL cộng dồn TOÀN BỘ
    # lịch sử InventoryLedger (cần để tính đúng Cuối kỳ) kể cả mã ĐÃ HẾT
    # SẠCH tồn từ lâu (Đầu kỳ=0, Cuối kỳ=0 — không có gì để dùng) — phải bị
    # loại khỏi kết quả, KHÔNG được tính là "1 mã hàng tồn kho". Mã có Đầu kỳ
    # KHÁC 0 dù Cuối kỳ = 0 (xuất hết trong kỳ) vẫn PHẢI giữ lại (còn ý nghĩa
    # báo cáo, không phải "hàng ma"). =====
    ledger_c4b = [
        ("HH00009-8", "Chậu ABC", "Cái", "HH", "Hàng Hóa", 0, 5, 500000),   # bình thường, còn tồn
        ("MA-CU-HET", "Hàng cũ đã hết từ lâu", "Cái", "HH", "Hàng Hóa", 0, 0, 0),   # "hàng ma": 0 đầu kỳ, 0 cuối kỳ
        ("MA-XUAT-HET", "Hàng có đầu kỳ, xuất hết trong kỳ", "Cái", "HH", "Hàng Hóa", 10, 0, 0),  # đầu kỳ > 0
    ]
    cur4b = FakeCursor(ledger_rows=ledger_c4b)
    server._misa_sql_connect = lambda cid, database=None: FakeConn(cur4b)
    rows4b, _ = server._misa_lay_ton_kho(1, "TESTDB", tu_ngay="2026-01-01", den_ngay="2026-09-04", ma_kho_list=None)
    ma_con_lai = {r["ma"] for r in rows4b}
    assert ma_con_lai == {"HH00009-8", "MA-XUAT-HET"}, (
        f"'MA-CU-HET' (Đầu kỳ=0 VÀ Cuối kỳ=0 — không còn gì để dùng) PHẢI bị loại khỏi kết quả; "
        f"'HH00009-8' (còn tồn) và 'MA-XUAT-HET' (có Đầu kỳ, dù Cuối kỳ=0) PHẢI vẫn giữ lại — được {ma_con_lai}")
    print("PASS ca 4b: _misa_lay_ton_kho loại đúng mã 'hàng ma' (Đầu kỳ=0 VÀ Cuối kỳ=0, không dùng được), "
          "không còn báo số mã hàng tồn kho bị thổi phồng sai so với báo cáo Excel MISA cùng kỳ.")

    # ===== An toàn khi MISA lỗi kết nối / chưa cấu hình database =====
    server._misa_sql_connect = _connect_loi
    assert server._misa_lay_ton_kho(1, "TESTDB") == ([], []), "Kết nối lỗi -> PHẢI trả ([], []) an toàn, không raise"
    assert server._misa_lay_ton_kho(1, "") == ([], []), "Chưa cấu hình database -> PHẢI trả ([], []) an toàn"
    print("PASS ca 5: _misa_lay_ton_kho trả ([], []) an toàn khi MISA chưa kết nối được.")

    print("\nTẤT CẢ TEST PASS")
finally:
    server._misa_sql_connect = orig_connect
