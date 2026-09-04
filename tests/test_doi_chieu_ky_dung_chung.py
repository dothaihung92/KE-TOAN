import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: khi 1 trong 2 loại (Bán hàng/Mua hàng) KHÔNG xác định
được "kỳ đang làm việc" riêng (chưa Import & Lưu đúng Bảng kê của loại đó
TRONG PHẦN MỀM — dù đã có hóa đơn thật trong MISA rồi, khác với việc lưu
Bảng kê ở màn Nhập Liệu), nhưng loại KIA lại CÓ kỳ rõ ràng (đã lưu Bảng kê),
phải DÙNG CHUNG kỳ đó cho cả 2 loại — thay vì loại thiếu Bảng kê rơi về so
TOÀN BỘ invoices (lộ lại dữ liệu tra cứu CŨ không liên quan).

Đúng ca thật người dùng báo cáo: "đã import rồi phần mềm đang check khác
thời điểm quý 2/2026. hãy chỉnh lại chỉnh kiểm tra theo dữ liệu import
thôi" — công ty CÓ Bảng kê Đầu vào Q2/2026 đã lưu (Mua hàng lọc đúng), MISA
Bán hàng CÓ 6 hóa đơn thật Q2/2026 (chụp màn hình MISA xác nhận), nhưng
Bảng kê Đầu ra CHƯA lưu trong phần mềm nên "Bán hàng" vẫn báo lệch với 9
hóa đơn NGUỒN CŨ (2025-07 đến 2025-09, tổng chỉ 105.757đ — rõ ràng dữ liệu
thử/tồn đọng, không phải kỳ đang làm việc)."""
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
    # Mua hàng: 1 hóa đơn Q2/2026, khớp đúng MISA.
    conn.execute("INSERT INTO invoices VALUES (1,'purchase','0317743519','0100000000','','9001',"
                 "'2026-05-15T08:00:00',1000000,80000,'1','{}',NULL)")
    # Bán hàng: 9 hóa đơn NGUỒN CŨ (2025, không liên quan) + 1 hóa đơn Q2/2026 THẬT.
    for i, ngay in enumerate(["2025-07-12", "2025-07-14", "2025-08-01"], start=16):
        conn.execute("INSERT INTO invoices VALUES (1,'sold','0100000000',?,'','%d',"
                     "'%sT08:00:00',6377,0,'1','{}',NULL)" % (i, ngay), ("020000000%d" % i,))
    conn.execute("INSERT INTO invoices VALUES (1,'sold','0100000000','0200000099','C1','5001',"
                 "'2026-05-20T08:00:00',500000000,40000000,'1','{}',NULL)")
    # Bảng kê Đầu vào (Mua hàng) ĐÃ LƯU, trải rộng CẢ QUÝ 2/2026 (04/2026 -
    # 06/2026, như thực tế 534 dòng thật) -> ky_lam_viec['purchase'] xác
    # định được khung ngày ĐỦ RỘNG để dùng chung cho cả Bán hàng.
    header_in = ["Ký hiệu", "Số HĐ", "Ngày", "Người bán", "MST bán", "Nợ", "Có"]
    rows_in = [["", "9000", "10/04/2026", "NCC A", "0317743519", "1561", "331"],
               ["", "9001", "15/05/2026", "NCC A", "0317743519", "1561", "331"],
               ["", "9002", "25/06/2026", "NCC A", "0317743519", "1561", "331"]]
    conn.execute("INSERT INTO nhap_lieu VALUES (1,'in',?,?,?)",
                 (json.dumps(header_in), json.dumps(rows_in), "2026-06-30T21:00:00"))
    # Bảng kê Đầu ra (Bán hàng) CHƯA LƯU (không có dòng nào trong nhap_lieu 'out').
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
            if self.last_params[0] == "SAVoucher":
                return [("AccountObjectTaxCode", "nvarchar"), ("InvNo", "nvarchar"),
                        ("InvSeries", "nvarchar"), ("TotalAmount", "money"),
                        ("TotalVATAmount", "money"), ("RefDate", "datetime")]
            if self.last_params[0] == "PUInvoice":
                return [("AccountObjectTaxCode", "nvarchar"), ("InvNo", "nvarchar"),
                        ("TotalTurnoverAmount", "money"), ("TotalVATAmount", "money"),
                        ("RefDate", "datetime")]
            return []
        if "FROM SAVoucher" in sql:
            rows = [
                # khớp đúng hóa đơn Q2/2026 thật (5001).
                ("0200000099", "5001", "C1", 540000000, 40000000, datetime.datetime(2026, 5, 20)),
                # Hóa đơn CŨ (2025) — CHỈ trả về nếu KHÔNG bị lọc theo tham số
                # ngày (mô phỏng đúng hành vi SQL Server thật khi có ?/?).
                ("0100000016", "16", "C1", 6377, 0, datetime.datetime(2025, 7, 12)),
            ]
            if self.last_params:
                lo, hi = self.last_params[0], self.last_params[1]
                return [r[:6] for r in rows if lo <= r[5] <= hi]
            return [r[:6] for r in rows]
        if "FROM PUInvoice" in sql:
            rows = [("0317743519", "9001", 1000000, 80000, datetime.datetime(2026, 5, 15))]
            if self.last_params:
                lo, hi = self.last_params[0], self.last_params[1]
                return [r[:5] for r in rows if lo <= r[4] <= hi]
            return [r[:5] for r in rows]
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

bh, mh = kq["ban_hang"], kq["mua_hang"]
print("Bán hàng:", bh)
print("Mua hàng:", mh)

assert mh["tong_khop"] is True, f"Mua hàng (đã có Bảng kê Đầu vào Q2/2026) phải khớp đúng — được {mh}"

so_hd_bh = [x["so_hd"] for x in bh["thieu"] + bh["lech"] + bh["thua"]]
for so_hd_cu in ("16", "17", "18"):
    assert so_hd_cu not in so_hd_bh, (
        f"Hóa đơn NGUỒN CŨ ({so_hd_cu}, 2025, không liên quan tới kỳ Q2/2026 đang làm việc) PHẢI bị "
        f"loại khỏi đối chiếu Bán hàng dù Bảng kê Đầu ra CHƯA lưu riêng — phải dùng chung kỳ với Mua "
        f"hàng (đã xác định đúng Q2/2026) — được {bh}")
assert bh["tong_khop"] is True and not bh["thieu"] and not bh["lech"] and not bh["thua"], (
    f"Hóa đơn Q2/2026 thật (5001) phải khớp đúng với MISA, không còn hóa đơn cũ nào lẫn vào — được {bh}")
print("PASS: Bán hàng (chưa lưu Bảng kê Đầu ra riêng) DÙNG CHUNG kỳ Q2/2026 đã xác định từ Bảng kê "
      "Đầu vào (Mua hàng) — không còn lộ lại 3 hóa đơn nguồn CŨ (2025) không liên quan tới kỳ đang "
      "làm việc, đúng yêu cầu 'kiểm tra theo dữ liệu import thôi'.")

print("\nTẤT CẢ TEST PASS")
