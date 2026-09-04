"""Regression test: TỰ ĐỘNG gắn MST người mua/MST bán trên Bảng kê Đầu ra/
Đầu vào NGAY LÚC IMPORT — người dùng gửi ảnh chụp lưới Nhập Liệu: hóa đơn
xuất khẩu cho khách nước ngoài có TÊN riêng biệt (JUST ADD PLANTS,
FlowerVine, Urban Pots Australia PTY LTD...) nhưng KHÔNG có MST (đúng thực
tế hóa đơn xuất khẩu), trước đây MỌI dòng thiếu MST đều bị dồn CHUNG vào 1
mã 'KL' — mất khả năng phân biệt từng khách thật.

Yêu cầu (2 vòng góp ý người dùng):
  1) Tên chứa 'khách lẻ'/'người tiêu dùng' -> vẫn gắn 'KL'; tên khác -> tra
     Danh mục Đối tượng MISA theo TÊN, khớp thì lấy mã đối tượng, không
     khớp thì lấy chính TÊN làm mã (tối đa 50 ký tự).
  2) "không cần nút này phần mềm sẽ tự động gắn luôn khi import nhập liệu
     bảng kê" — KHÔNG cần bấm nút riêng, phải chạy NGAY khi import (cả 2
     luồng import: nhap_lieu_import và nhap_lieu_import_bang_ke)."""
import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys
sys.path.insert(0, _REPO_ROOT)
import server
import asyncio


class FakeCursor:
    def __init__(self, doi_tuong_rows):
        self._rows = doi_tuong_rows

    def execute(self, sql, *params):
        self.last_sql = sql
        return self

    def fetchall(self):
        if "FROM AccountObject" in self.last_sql:
            return self._rows
        return []


class FakeConn:
    def __init__(self, cur):
        self._cur = cur

    def cursor(self):
        return self._cur

    def close(self):
        pass


class FakeUploadFile:
    """Giả UploadFile của FastAPI — đủ để nhap_lieu_import*/openpyxl đọc."""
    def __init__(self, filename, content):
        self.filename = filename
        self._content = content

    async def read(self):
        return self._content


def _xlsx_bytes_out():
    """Dựng 1 file .xlsx tối thiểu có sheet 'Đầu ra' — đúng định dạng
    nhap_lieu_import_bang_ke đọc thẳng (dòng 1 = tiêu đề)."""
    import openpyxl, io
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Đầu ra"
    ws.append(["Ký hiệu mẫu", "Ký hiệu HĐ", "Số hóa đơn", "Ngày lập",
               "Tên người mua", "MST người mua", "Mặt hàng",
               "Doanh số bán chưa thuế", "Thuế GTGT"])
    ws.append(["1", "C26TUE", "13", "27/06/2026", "JUST ADD PLANTS", "KL", "Chậu...", 527363867, 0])
    ws.append(["1", "C26TUE", "9", "06/05/2026", "Khách lẻ", "KL", "Chậu...", 407218282, 0])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


orig_connect = server._misa_sql_connect
orig_cfg = server._misa_sql_cfg

try:
    # ===== Ca 1: hàm THUẦN _gan_mst_theo_ten_doi_tuong_rows — đúng dữ liệu
    # thật người dùng gửi (Bảng kê Đầu ra). =====
    header_out = ["Ký hiệu mẫu", "Ký hiệu HĐ", "Số hóa đơn", "Ngày lập",
                  "Tên người mua", "MST người mua", "Mặt hàng",
                  "Doanh số bán chưa thuế", "Thuế GTGT"]
    rows_out = [
        ["1", "C26TUE", "13", "27/06/2026", "JUST ADD PLANTS", "KL", "Chậu...", 527363867, 0],
        ["1", "C26TUE", "11", "20/05/2026", "FlowerVine", "KL", "Chậu...", 670275086, 0],
        ["1", "C26TUE", "10", "12/05/2026", "Urban Pots Australia PTY LTD", "KL", "Chậu...", 122702364, 0],
        ["1", "C26TUE", "9", "06/05/2026", "Khách lẻ", "KL", "Chậu...", 407218282, 0],
        ["1", "C26TUE", "8", "20/04/2026", "Người tiêu dùng", "", "Chậu...", 564720213, 0],
        ["1", "C26TUE", "7", "27/03/2026", "CÔNG TY TNHH ABC", "0300111222", "Chậu...", 250884486, 20070759],
    ]
    doi_tuong_map = {"just add plants": "JUST ADD PLANTS", "flowervine": "FV001",
                      "công ty tnhh abc": "0300111222"}
    rows_moi, tk = server._gan_mst_theo_ten_doi_tuong_rows(header_out, rows_out, "out", doi_tuong_map)
    mst_ket_qua = {r[4]: r[5] for r in rows_moi}
    assert mst_ket_qua["JUST ADD PLANTS"] == "JUST ADD PLANTS"
    assert mst_ket_qua["FlowerVine"] == "FV001"
    assert mst_ket_qua["Urban Pots Australia PTY LTD"] == "Urban Pots Australia PTY LTD"
    assert mst_ket_qua["Khách lẻ"] == "KL" and mst_ket_qua["Người tiêu dùng"] == "KL"
    assert mst_ket_qua["CÔNG TY TNHH ABC"] == "0300111222"
    assert tk == {"so_giu_nguyen": 1, "so_gan_kl": 2, "so_gan_tu_danh_muc_misa": 2, "so_gan_theo_ten": 1}
    print("PASS ca 1: _gan_mst_theo_ten_doi_tuong_rows gắn đúng MST theo tên/Danh mục/KL/giữ nguyên.")

    # ===== Ca 2: doi_tuong_map RỖNG (MISA chưa kết nối được lúc import) —
    # vẫn phải áp dụng nhánh 'khách lẻ'->KL / còn lại->tự lấy tên làm mã,
    # KHÔNG được để trống/lỗi. =====
    rows_moi2, tk2 = server._gan_mst_theo_ten_doi_tuong_rows(header_out, rows_out, "out", {})
    mst2 = {r[4]: r[5] for r in rows_moi2}
    assert mst2["JUST ADD PLANTS"] == "JUST ADD PLANTS" and mst2["FlowerVine"] == "FlowerVine"
    assert mst2["Khách lẻ"] == "KL"
    print("PASS ca 2: doi_tuong_map rỗng (MISA chưa kết nối) vẫn tự lấy tên làm mã, không lỗi/không trống.")

    # ===== Ca 3: tên dài hơn 50 ký tự -> cắt đúng 50 ký tự. =====
    ten_dai = "CÔNG TY TNHH THƯƠNG MẠI DỊCH VỤ XUẤT NHẬP KHẨU RẤT LÀ DÀI VƯỢT QUÁ NĂM MƯƠI KÝ TỰ"
    assert len(ten_dai) > 50
    rows_dai = [["1", "C26TUE", "1", "01/01/2026", ten_dai, "", "Chậu...", 100000, 0]]
    rows_moi3, _ = server._gan_mst_theo_ten_doi_tuong_rows(header_out, rows_dai, "out", {})
    assert len(rows_moi3[0][5]) == 50 and rows_moi3[0][5] == ten_dai[:50]
    print("PASS ca 3: tên dài hơn 50 ký tự được cắt đúng giới hạn cột AccountObjectCode.")

    # ===== Ca 4: Bảng kê Đầu vào (loai='in'), tờ khai nhập khẩu — NCC nước
    # ngoài chưa có trong Danh mục MISA -> tự lấy tên làm mã. =====
    header_in = ["Ký hiệu", "Số HĐ", "Ngày", "Người bán", "MST bán", "Mã vt",
                 "Tên hàng hóa/dịch vụ", "ĐVT", "Số lượng", "Đơn giá", "Thành tiền",
                 "Thuế suất", "Tiền thuế GTGT", "Nợ", "Có"]
    rows_in = [
        ["TKNK", "10230145670001", "15/03/2026", "SHENZHEN TRADING CO LTD", "", "HH001",
         "Hàng nhập khẩu", "Cái", 100, 50000, 5000000, "8%", 400000, "1561", "331"],
    ]
    rows_moi4, tk4 = server._gan_mst_theo_ten_doi_tuong_rows(header_in, rows_in, "in", {})
    assert rows_moi4[0][4] == "SHENZHEN TRADING CO LTD"
    print("PASS ca 4: Bảng kê Đầu vào (tờ khai nhập khẩu) — NCC nước ngoài được gắn mã = tên.")

    # ===== Ca 5: _misa_lay_doi_tuong_map — đọc đúng Danh mục Đối tượng MISA,
    # trả {} an toàn khi kết nối lỗi (KHÔNG được raise). =====
    cur5 = FakeCursor([("FV001", "FlowerVine"), ("JUST ADD PLANTS", "JUST ADD PLANTS")])
    server._misa_sql_connect = lambda cid, database=None: FakeConn(cur5)
    m5 = server._misa_lay_doi_tuong_map(1, "TESTDB")
    assert m5 == {"flowervine": "FV001", "just add plants": "JUST ADD PLANTS"}
    print("PASS ca 5a: _misa_lay_doi_tuong_map đọc đúng Danh mục Đối tượng MISA.")

    def _connect_loi(cid, database=None):
        raise Exception("không kết nối được MISA")
    server._misa_sql_connect = _connect_loi
    m5b = server._misa_lay_doi_tuong_map(1, "TESTDB")
    assert m5b == {}, "Kết nối MISA lỗi -> PHẢI trả {} an toàn, không được raise/chặn import"
    m5c = server._misa_lay_doi_tuong_map(1, "")
    assert m5c == {}, "Chưa cấu hình database -> PHẢI trả {} an toàn"
    print("PASS ca 5b: _misa_lay_doi_tuong_map trả {} an toàn khi MISA chưa kết nối được (không chặn import).")

    # ===== Ca 6 (ĐÚNG yêu cầu người dùng: "không cần nút này phần mềm sẽ tự
    # động gắn luôn khi import nhập liệu bảng kê") — gọi THẲNG endpoint
    # nhap_lieu_import_bang_ke (Import Excel trong màn Nhập Liệu) với file
    # Excel có sẵn 'KL' cho JUST ADD PLANTS -> PHẢI TỰ ĐỘNG sửa lại thành mã
    # đúng theo Danh mục MISA, KHÔNG cần gọi thêm hành động nào khác. =====
    server._misa_sql_connect = lambda cid, database=None: FakeConn(
        FakeCursor([("JUST ADD PLANTS", "JUST ADD PLANTS")]))
    server._misa_sql_cfg = lambda cid: {"database": "TESTDB"}
    up = FakeUploadFile("BangKe.xlsx", _xlsx_bytes_out())

    class FakeForm:
        def getlist(self, k):
            return [up] if k == "files" else []

        def get(self, k):
            return None

    class FakeRequest:
        async def form(self):
            return FakeForm()

    kq6 = asyncio.run(server.nhap_lieu_import_bang_ke(1, FakeRequest(), loai="out"))
    mst6 = {r[4]: r[5] for r in kq6["rows"]}
    print("Ca 6 (import-bang-ke, tự động, không nút):", mst6)
    assert mst6["JUST ADD PLANTS"] == "JUST ADD PLANTS", (
        f"Import Excel (không bấm nút gì thêm) PHẢI tự động gắn đúng mã theo Danh mục MISA — được {mst6}")
    assert mst6["Khách lẻ"] == "KL"
    print("PASS ca 6: nhap_lieu_import_bang_ke (Import Excel màn Nhập Liệu) TỰ ĐỘNG gắn MST khi import, "
          "đúng yêu cầu 'không cần nút này'.")

    print("\nTẤT CẢ TEST PASS")
finally:
    server._misa_sql_connect = orig_connect
    server._misa_sql_cfg = orig_cfg
