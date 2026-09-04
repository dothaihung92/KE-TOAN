"""Regression test: tự động gắn MST người mua/MST bán trên Bảng kê Đầu ra/
Đầu vào — người dùng gửi ảnh chụp lưới Nhập Liệu: hóa đơn xuất khẩu cho
khách nước ngoài có TÊN riêng biệt (JUST ADD PLANTS, FlowerVine, Urban Pots
Australia PTY LTD...) nhưng KHÔNG có MST (đúng thực tế hóa đơn xuất khẩu),
trước đây MỌI dòng thiếu MST đều bị dồn CHUNG vào 1 mã 'KL' — mất khả năng
phân biệt từng khách thật. Yêu cầu: tên chứa 'khách lẻ'/'người tiêu dùng'
thì vẫn gắn 'KL'; tên khác thì tra Danh mục Đối tượng MISA theo TÊN, khớp
thì lấy mã đối tượng, không khớp thì lấy chính TÊN làm mã (tối đa 50 ký
tự) — áp dụng cho cả Bảng kê Đầu ra (MST người mua) và Đầu vào (MST bán)."""
import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys
sys.path.insert(0, _REPO_ROOT)
import server


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


orig_connect = server._misa_sql_connect
orig_get = server.nhap_lieu_get

try:
    # ===== Ca 1: Bảng kê Đầu ra (loai='out') — đúng dữ liệu thật người dùng
    # gửi (Ký hiệu mẫu, Ký hiệu HĐ, Số hóa đơn, Ngày lập, Tên người mua, MST
    # người mua, Mặt hàng, Doanh số, Thuế GTGT). =====
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
    server.nhap_lieu_get = lambda cid, loai: {"header": header_out, "rows": rows_out}
    # Danh mục Đối tượng MISA: có sẵn "JUST ADD PLANTS" (mã JUST ADD PLANTS)
    # và "FlowerVine" (mã FV001) — "Urban Pots Australia PTY LTD" CHƯA có.
    doi_tuong_rows = [
        ("JUST ADD PLANTS", "JUST ADD PLANTS"),
        ("FV001", "FlowerVine"),
        ("0300111222", "CÔNG TY TNHH ABC"),
    ]
    server._misa_sql_connect = lambda cid, database=None: FakeConn(FakeCursor(doi_tuong_rows))

    r1 = server._misa_gan_mst_theo_ten_doi_tuong(1, "TESTDB", "out")
    print("Ca 1 (Đầu ra):", r1)
    mst_ket_qua = {r[4]: r[5] for r in r1["rows"]}   # tên -> mst mới
    assert mst_ket_qua["JUST ADD PLANTS"] == "JUST ADD PLANTS", (
        f"Phải khớp đúng theo tên trong Danh mục MISA — được {mst_ket_qua}")
    assert mst_ket_qua["FlowerVine"] == "FV001", f"Phải lấy đúng mã đối tượng FV001 — được {mst_ket_qua}"
    assert mst_ket_qua["Urban Pots Australia PTY LTD"] == "Urban Pots Australia PTY LTD"[:50], (
        f"KHÔNG có trong Danh mục MISA -> phải tự lấy TÊN làm mã — được {mst_ket_qua}")
    assert mst_ket_qua["Khách lẻ"] == "KL", "Tên chứa 'khách lẻ' -> vẫn phải gắn 'KL'"
    assert mst_ket_qua["Người tiêu dùng"] == "KL", "Tên chứa 'người tiêu dùng' -> vẫn phải gắn 'KL'"
    assert mst_ket_qua["CÔNG TY TNHH ABC"] == "0300111222", (
        f"Dòng ĐÃ CÓ MST thật (0300111222) phải GIỮ NGUYÊN, không đụng tới — được {mst_ket_qua}")
    assert r1["so_giu_nguyen"] == 1 and r1["so_gan_kl"] == 2 and r1["so_gan_tu_danh_muc_misa"] == 2 \
        and r1["so_gan_theo_ten"] == 1, f"Thống kê phải đúng — được {r1}"
    print("PASS ca 1: Bảng kê Đầu ra — gắn đúng MST theo tên khớp Danh mục MISA/KL/giữ nguyên.")

    # ===== Ca 2: Bảng kê Đầu vào (loai='in') — tờ khai nhập khẩu, người bán
    # nước ngoài KHÔNG có trong Danh mục NCC MISA -> tự lấy tên làm mã. =====
    header_in = ["Ký hiệu", "Số HĐ", "Ngày", "Người bán", "MST bán", "Mã vt",
                 "Tên hàng hóa/dịch vụ", "ĐVT", "Số lượng", "Đơn giá", "Thành tiền",
                 "Thuế suất", "Tiền thuế GTGT", "Nợ", "Có"]
    rows_in = [
        ["TKNK", "10230145670001", "15/03/2026", "SHENZHEN TRADING CO LTD", "", "HH001",
         "Hàng nhập khẩu", "Cái", 100, 50000, 5000000, "8%", 400000, "1561", "331"],
        ["C26ABC", "445", "20/03/2026", "CÔNG TY TNHH XYZ", "0301234567", "MHDV",
         "Dịch vụ", "", 1, 1000000, 1000000, "8%", 80000, "6427", "331"],
    ]
    server.nhap_lieu_get = lambda cid, loai: {"header": header_in, "rows": rows_in}
    doi_tuong_rows_in = [("0301234567", "CÔNG TY TNHH XYZ")]   # KHÔNG có SHENZHEN TRADING
    server._misa_sql_connect = lambda cid, database=None: FakeConn(FakeCursor(doi_tuong_rows_in))

    r2 = server._misa_gan_mst_theo_ten_doi_tuong(1, "TESTDB", "in")
    print("Ca 2 (Đầu vào):", r2)
    mst_ket_qua2 = {r[3]: r[4] for r in r2["rows"]}
    assert mst_ket_qua2["SHENZHEN TRADING CO LTD"] == "SHENZHEN TRADING CO LTD", (
        f"Tờ khai NK, NCC CHƯA có trong Danh mục MISA -> phải tự lấy TÊN làm mã — được {mst_ket_qua2}")
    assert mst_ket_qua2["CÔNG TY TNHH XYZ"] == "0301234567", "Dòng đã có MST thật phải giữ nguyên"
    print("PASS ca 2: Bảng kê Đầu vào (tờ khai nhập khẩu) — NCC chưa có trong MISA được gắn mã = tên.")

    # ===== Ca 3: tên dài hơn 50 ký tự -> phải cắt đúng 50 ký tự (giới hạn cột
    # AccountObjectCode). =====
    ten_dai = "CÔNG TY TNHH THƯƠNG MẠI DỊCH VỤ XUẤT NHẬP KHẨU RẤT LÀ DÀI VƯỢT QUÁ NĂM MƯƠI KÝ TỰ"
    assert len(ten_dai) > 50
    rows_dai = [["1", "C26TUE", "1", "01/01/2026", ten_dai, "", "Chậu...", 100000, 0]]
    server.nhap_lieu_get = lambda cid, loai: {"header": header_out, "rows": rows_dai}
    server._misa_sql_connect = lambda cid, database=None: FakeConn(FakeCursor([]))
    r3 = server._misa_gan_mst_theo_ten_doi_tuong(1, "TESTDB", "out")
    mst3 = r3["rows"][0][5]
    assert len(mst3) == 50 and mst3 == ten_dai[:50], f"Phải cắt đúng 50 ký tự — được len={len(mst3)}, {mst3!r}"
    print("PASS ca 3: tên dài hơn 50 ký tự được cắt đúng giới hạn cột AccountObjectCode.")

    print("\nTẤT CẢ TEST PASS")
finally:
    server._misa_sql_connect = orig_connect
    server.nhap_lieu_get = orig_get
