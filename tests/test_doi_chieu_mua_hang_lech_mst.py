import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: "Đối chiếu tổng giá trị & VAT" (Mua hàng) không được
báo 1 hóa đơn ĐÃ CÓ ĐỦ ở cả 2 bên là VỪA "THIẾU" (theo nguồn) VỪA "THỪA"
(theo MISA) cùng lúc — đúng lỗi thật xác nhận qua file Excel người dùng
xuất (DoiChieu_GiaTriVAT_0315673577.xlsx): CÙNG 1 NCC (MST 038303003080)
có 11 hóa đơn (Số HĐ 367, 1297, 2508... ) xuất hiện Y HỆT ở CẢ "thiếu"
LẪN "thừa" — ĐÚNG cùng Số HĐ, ĐÚNG cùng số tiền tuyệt đối — vì khóa ghép
(MST, Số HĐ) không khớp (MST lệch định dạng giữa nguồn/tra cứu Thuế và
MISA cho ĐÚNG NCC này, vd MISA lưu thiếu số 0 ở đầu), dù hóa đơn ĐÃ CÓ
ĐỦ ở cả 2 bên. Fix: cứu vãn (salvage) ghép lại theo Số hóa đơn ĐƠN THUẦN
(bỏ MST) khi CHỈ CÓ ĐÚNG 1 ứng viên thiếu và 1 ứng viên thừa cùng Số HĐ đó
(không mơ hồ)."""
import sys, sqlite3, os, tempfile, datetime, json
sys.path.insert(0, _REPO_ROOT)
import server

_db_path = tempfile.mktemp(suffix=".sqlite3")


def db_factory():
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    return conn


class FakeCursor:
    def execute(self, sql, params=()):
        self.last_sql = sql
        self.last_params = params
        return self

    def fetchone(self):
        return None

    def fetchall(self):
        sql = self.last_sql
        if "sys.columns" in sql:
            table = self.last_params if isinstance(self.last_params, str) else (
                self.last_params[0] if self.last_params else "")
            if table == "PUServiceDetail":
                return [("TaxAccountObjectTaxCode", "nvarchar"), ("InvNo", "nvarchar"),
                        ("Amount", "money"), ("VATAmount", "money"), ("InvDate", "datetime")]
            return []   # SAVoucher/PUInvoice/... không dò được cột -> bỏ qua, không ảnh hưởng test này
        if "FROM PUServiceDetail" in sql:
            return [
                # Hóa đơn A: MST MISA lưu THIẾU số 0 đầu ("38303003080", 11 số)
                # so với nguồn ("038303003080", 12 số) — ĐÚNG hiện trạng lỗi
                # thật (cùng NCC, số tiền/Số HĐ khớp tuyệt đối).
                ("38303003080", "367", 590444, 0, datetime.datetime(2026, 1, 10)),
                # Hóa đơn C: chỉ có trong MISA, KHÔNG có trong nguồn -> "thừa" thật.
                ("0399999999", "888", 500000, 0, datetime.datetime(2026, 1, 15)),
            ]
        return []


class FakeConn:
    def cursor(self):
        return FakeCursor()

    def close(self):
        pass


orig_db, orig_connect = server.db, server._misa_sql_connect
server.db = db_factory
server._misa_sql_connect = lambda cid, database=None: FakeConn()

try:
    conn = db_factory()
    conn.execute("""CREATE TABLE invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, loai TEXT, he_thong TEXT,
        nbmst TEXT, nbten TEXT, nmmst TEXT, khmshdon TEXT, khhdon TEXT, shdon TEXT,
        tdlap TEXT, tgtcthue REAL, tgtthue REAL, tgtttbso REAL, tthai TEXT, raw TEXT, detail_json TEXT)""")
    conn.execute("""CREATE TABLE companies (
        id INTEGER PRIMARY KEY, save_dir TEXT)""")
    conn.execute("INSERT INTO companies VALUES (1, '')")
    # Hóa đơn A (nguồn): MST ĐỦ số 0 đầu — sẽ "thiếu" nếu ghép cứng (MST,Số HĐ).
    conn.execute("INSERT INTO invoices (company_id, loai, he_thong, nbmst, khhdon, shdon, tdlap, "
                 "tgtcthue, tgtthue, tgtttbso, tthai, raw) VALUES "
                 "(1,'purchase','query','038303003080','','367','2026-01-10T00:00:00',590444,0,590444,'1','{}')")
    # Hóa đơn B (nguồn): hoàn toàn KHÔNG có bên MISA -> "thiếu" THẬT, không được cứu vãn.
    conn.execute("INSERT INTO invoices (company_id, loai, he_thong, nbmst, khhdon, shdon, tdlap, "
                 "tgtcthue, tgtthue, tgtttbso, tthai, raw) VALUES "
                 "(1,'purchase','query','0316491058','','999','2026-01-20T00:00:00',1000000,80000,1080000,'1','{}')")
    conn.commit()
    conn.close()

    dc = server._misa_doi_chieu_import_toan_bo(1, "TESTDB")
    mh = dc["mua_hang"]
    print("Kết quả đối chiếu Mua hàng:", json.dumps(mh, ensure_ascii=False, indent=1))

    so_hd_thieu = {x["so_hd"] for x in mh["thieu"]}
    so_hd_thua = {x["so_hd"] for x in mh["thua"]}
    assert "367" not in so_hd_thieu, (
        f"Hóa đơn 367 (MST lệch định dạng nhưng ĐÃ CÓ đủ ở cả 2 bên, cùng Số HĐ + cùng số tiền) "
        f"KHÔNG được báo 'THIẾU' — được thieu={so_hd_thieu}")
    assert "367" not in so_hd_thua, (
        f"Hóa đơn 367 KHÔNG được báo 'THỪA' (đã cứu vãn ghép đúng, không phải hóa đơn thừa thật) — "
        f"được thua={so_hd_thua}")
    assert "999" in so_hd_thieu, (
        f"Hóa đơn 999 (thật sự không có bên MISA) VẪN PHẢI báo đúng 'THIẾU', không bị cứu vãn nhầm — "
        f"được thieu={so_hd_thieu}")
    assert "888" in so_hd_thua, (
        f"Hóa đơn 888 (thật sự chỉ có bên MISA) VẪN PHẢI báo đúng 'THỪA' — được thua={so_hd_thua}")
    assert mh["khop"] == 1, f"Hóa đơn 367 phải được tính là 1 hóa đơn KHỚP (qua cứu vãn) — khop={mh['khop']}"
    print("PASS: hóa đơn MST lệch định dạng (cùng Số HĐ + cùng số tiền) được cứu vãn đúng, không còn "
          "báo nhầm vừa 'thiếu' vừa 'thừa'; hóa đơn thiếu/thừa THẬT vẫn báo đúng, không bị cứu vãn nhầm.")

    print("\nTẤT CẢ TEST PASS")
finally:
    server.db = orig_db
    server._misa_sql_connect = orig_connect
    try:
        os.remove(_db_path)
    except OSError:
        pass
