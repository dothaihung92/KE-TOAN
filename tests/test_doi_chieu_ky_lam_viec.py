import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: _misa_doi_chieu_import_toan_bo phải CHỈ đối chiếu đúng
KỲ ĐANG LÀM VIỆC (khung ngày của Bảng kê Đầu ra/Đầu vào ĐÃ LƯU), KHÔNG được
gộp chung hóa đơn của các kỳ CŨ còn sót lại trong bảng "invoices" (bảng này
TÍCH LŨY mọi lần tra cứu, không tự xóa dữ liệu kỳ trước).

Đúng ca thật người dùng báo cáo: import dữ liệu quý 2/2026 (Bảng kê Đầu vào
lưu 534 dòng, tháng 4-6/2026) nhưng "Đối chiếu tổng giá trị & VAT" lại hiện
hàng loạt hóa đơn ngày 2025-07 đến 2025-09 — kiểm tra chéo với chính Bảng kê
Đầu vào Q2/2026 vừa lưu thì HOÀN TOÀN không có các MST/Số HĐ đó — chứng tỏ
đó là dữ liệu tra cứu CŨ (kỳ trước) còn sót lại trong bảng invoices, không
phải kỳ hiện tại đang làm việc.

Test dựng invoices table có CẢ hóa đơn kỳ CŨ (2025) lẫn kỳ MỚI (Q2/2026,
04-06/2026), và Bảng kê Đầu vào ĐÃ LƯU (nhap_lieu 'in') chỉ có dữ liệu Q2/
2026 — xác nhận đối chiếu CHỈ xét hóa đơn Q2/2026, hóa đơn 2025 KHÔNG được
tính vào "thiếu"/"thừa" gì cả (dù MISA không hề có 2 hóa đơn đó)."""
import sys, sqlite3, datetime, json
sys.path.insert(0, _REPO_ROOT)
import server


def db_factory():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE invoices (
        company_id INTEGER, loai TEXT, nbmst TEXT, nmmst TEXT, khhdon TEXT, shdon TEXT,
        tdlap TEXT, tgtcthue REAL, tgtthue REAL, tthai TEXT, raw TEXT, detail_json TEXT)""")
    conn.execute("""CREATE TABLE companies (
        id INTEGER PRIMARY KEY, save_dir TEXT)""")
    conn.execute("INSERT INTO companies VALUES (1, '')")
    conn.execute("""CREATE TABLE nhap_lieu (
        company_id INTEGER, loai TEXT, header_json TEXT, rows_json TEXT, updated_at TEXT,
        PRIMARY KEY (company_id, loai))""")
    # Hóa đơn KỲ CŨ (2025-08) -> KHÔNG nằm trong Bảng kê Đầu vào Q2/2026 đã
    # lưu, MISA cũng không hề có (đúng thực tế: kỳ trước, không liên quan).
    conn.execute("INSERT INTO invoices VALUES (1,'purchase','3603289732','0100000000','','61',"
                 "'2025-08-22T08:00:00',11360000,908800,'1','{}',NULL)")
    # Hóa đơn KỲ MỚI (Q2/2026, thật sự cần đối chiếu) -> khớp đúng với MISA.
    conn.execute("INSERT INTO invoices VALUES (1,'purchase','0317743519','0100000000','','9001',"
                 "'2026-04-15T08:00:00',1000000,80000,'1','{}',NULL)")
    # Bảng kê Đầu vào ĐÃ LƯU — CHỈ có hóa đơn Q2/2026 (04-06/2026), không có
    # gì về hóa đơn kỳ cũ 2025 nói trên.
    header = ["Ký hiệu", "Số HĐ", "Ngày", "Người bán", "MST bán", "STT", "Mã vt",
              "Tên hàng hóa/dịch vụ", "ĐVT", "Số lượng", "Đơn giá", "Thành tiền",
              "Thuế suất", "Tiền thuế GTGT", "Nợ", "Có"]
    rows = [["", "9001", "15/04/2026", "NCC A", "0317743519", "1", "", "Hàng 1",
              "Cái", 1, 1000000, 1000000, "8%", 80000, "1561", "331"]]
    conn.execute("INSERT INTO nhap_lieu VALUES (1,'in',?,?,?)",
                 (json.dumps(header), json.dumps(rows), "2026-06-30T21:00:00"))
    conn.commit()
    return conn


class FakeCursor:
    def __init__(self):
        self.last_sql = ""
        self.last_params = ()

    def execute(self, sql, params=()):
        self.last_sql = sql
        self.last_params = tuple(params) if isinstance(params, (tuple, list)) else (params,)
        return self

    def fetchall(self):
        sql = self.last_sql
        if "FROM sys.columns" in sql:
            if self.last_params[0] == "PUInvoice":
                return [("AccountObjectTaxCode", "nvarchar"), ("InvNo", "nvarchar"),
                        ("TotalTurnoverAmount", "money"), ("TotalVATAmount", "money"),
                        ("RefDate", "datetime")]
            return []
        if "FROM PUInvoice" in sql:
            # MISA CHỈ có đúng hóa đơn Q2/2026 (9001) — hóa đơn 2025 (61)
            # HOÀN TOÀN không có trong MISA (đúng thực tế: không liên quan).
            rows = [("0317743519", "9001", 1000000, 80000, datetime.datetime(2026, 4, 15))]
            lo, hi = self.last_params[0], self.last_params[1]
            return [r[:5] for r in rows if lo <= r[4] <= hi]
        return []

    def fetchone(self):
        return None


class FakeConn:
    def __init__(self):
        self._cur = FakeCursor()

    def cursor(self):
        return self._cur

    def close(self):
        pass


orig_db, orig_connect = server.db, server._misa_sql_connect
server.db = db_factory
server._misa_sql_connect = lambda cid, database=None: FakeConn()
try:
    kq = server._misa_doi_chieu_import_toan_bo(1, "TESTDB")
finally:
    server.db = orig_db
    server._misa_sql_connect = orig_connect

mh = kq["mua_hang"]
print("Kết quả Mua hàng:", mh)

assert mh["tong_hd_nguon"] == 1, (
    f"Chỉ được tính đúng 1 hóa đơn nguồn (9001, Q2/2026) — hóa đơn kỳ cũ (61, 2025) PHẢI bị loại "
    f"khỏi đối chiếu vì không thuộc kỳ Bảng kê Đầu vào đã lưu — được tong_hd_nguon={mh['tong_hd_nguon']}")
so_hd_tat_ca = [x["so_hd"] for x in mh["thieu"] + mh["lech"] + mh["thua"]]
assert "61" not in so_hd_tat_ca, (
    f"Hóa đơn kỳ CŨ (61, 2025) KHÔNG được xuất hiện ở bất kỳ đâu (thiếu/lệch/thừa) — được {mh}")
assert mh["tong_khop"] is True, f"Kỳ Q2/2026 (chỉ 1 hóa đơn, khớp đúng) phải báo tong_khop=True — được {mh}"
print("PASS: hóa đơn KỲ CŨ (61, 2025-08, không thuộc Bảng kê Đầu vào Q2/2026 đã lưu) bị LOẠI HẲN khỏi "
      "đối chiếu — chỉ còn đúng hóa đơn Q2/2026 (9001) được xét, khớp đúng với MISA.")

print("\nTẤT CẢ TEST PASS")
