import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: đúng lỗi THẬT người dùng vừa báo (3/9/2026, hóa đơn
Traveloka Số HĐ 6470, NCC 0313581779) — Đối chiếu tổng giá trị & VAT báo
"LỆCH -150.000đ" dù người dùng xác nhận (kèm ảnh chụp Bảng kê Đầu vào VÀ
MISA) tổng ĐÚNG là 3.252.315đ ở cả 2 nơi, có 2 dòng: vé máy bay 3.102.315đ
(8% VAT) + "Tổng tiền phí" 150.000đ (KCT, không chịu VAT — phí sân bay/thu
hộ nằm RIÊNG ngoài DSHHDVu trên hóa đơn điện tử thật).

Nguyên nhân: "invoices.tgtcthue" (lấy từ API DANH SÁCH hóa đơn của Thuế,
_run_fetch_job) chỉ có 3.102.315đ — thiếu khoản "Tổng tiền phí" 150.000đ,
trong khi Bảng kê Đầu vào/MISA đều dùng dữ liệu CHI TIẾT (detail_json, qua
_parse_xml_invoice/_parse_detail_json) nên có ĐỦ. _misa_doi_chieu_import_toan_bo
phải cộng thêm "Tổng tiền phí" (đọc từ chính detail_json ĐÃ LƯU của hóa đơn
đó, qua _lay_tong_tien_phi_json) vào doanh số nguồn để khớp đúng."""
import sys, sqlite3, json
sys.path.insert(0, _REPO_ROOT)
import server
import datetime


def db_factory():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE invoices (
        company_id INTEGER, loai TEXT, nbmst TEXT, nmmst TEXT, khhdon TEXT, shdon TEXT,
        tdlap TEXT, tgtcthue REAL, tgtthue REAL, tthai TEXT, raw TEXT, detail_json TEXT)""")
    conn.execute("""CREATE TABLE companies (
        id INTEGER PRIMARY KEY, save_dir TEXT)""")
    conn.execute("INSERT INTO companies VALUES (1, '')")
    # detail_json THẬT (rút gọn) — cấu trúc dslphi/tphi đúng như hóa đơn
    # Traveloka thật, xem _lay_tong_tien_phi_json.
    detail_json = json.dumps({"dslphi": [{"tlphi": "Phí thu hộ", "tphi": 150000}]})
    conn.execute(
        "INSERT INTO invoices VALUES (1,'purchase','0313581779','0100000000','C26TTL','6470',"
        "'2026-02-25T10:00:00',3102315,248185,'1','{}',?)", (detail_json,))
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
            table = self.last_params[0]
            if table == "PUInvoice":
                return []
            if table == "PUServiceDetail":
                return [("TaxAccountObjectTaxCode", "nvarchar"), ("InvNo", "nvarchar"),
                        ("Amount", "money"), ("VATAmount", "money"), ("InvDate", "datetime")]
            return []
        if "FROM PUServiceDetail" in sql:
            # ĐÚNG như MISA thật (ảnh chụp người dùng): 2 dòng chi tiết cùng
            # hóa đơn — 3.102.315 (vé) + 150.000 (phí) = 3.252.315 tổng.
            rows = [
                ("0313581779", "6470", 3102315, 248185, datetime.datetime(2026, 2, 25)),
                ("0313581779", "6470", 150000, 0, datetime.datetime(2026, 2, 25)),
            ]
            return rows
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
print("Mua hàng:", mh)

assert not mh["thieu"], f"Hóa đơn 6470 KHÔNG được báo thiếu — được thieu={mh.get('thieu')}"
assert not mh["lech"], (
    f"Hóa đơn 6470 KHÔNG được báo LỆCH — 'Tổng tiền phí' 150.000đ (KCT) phải được cộng vào doanh số "
    f"nguồn (3.102.315+150.000=3.252.315, khớp đúng MISA) — được lech={mh.get('lech')}")
print("PASS: hóa đơn 6470 (NCC 0313581779) không còn báo LỆCH sai — 'Tổng tiền phí' 150.000đ đọc từ "
      "detail_json đã được cộng vào doanh số nguồn, khớp đúng 3.252.315đ với MISA.")

print("\nALL DONE (test 1: detail_json)")

# ===== Test 2: ĐA SỐ hóa đơn thật KHÔNG có detail_json (chỉ hóa đơn "không
# mã"/lỗi tải file mới có — xem _dam_bao_du_chi_tiet_hoa_don) mà có FILE
# XML đã tải trên máy — đây mới là đường THẬT giải quyết đa số ca thật
# giống hóa đơn Traveloka 6470. Dựng file XML tối thiểu (đúng cấu trúc
# TToan/DSLPhi/LPhi/TPhi mà _lay_tong_tien_phi_xml dò) trong 1 thư mục
# tạm, gán làm "save_dir" của công ty, detail_json để TRỐNG.
import tempfile, os as _os

def db_factory2():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE invoices (
        company_id INTEGER, loai TEXT, nbmst TEXT, nmmst TEXT, khhdon TEXT, shdon TEXT,
        tdlap TEXT, tgtcthue REAL, tgtthue REAL, tthai TEXT, raw TEXT, detail_json TEXT)""")
    conn.execute("""CREATE TABLE companies (
        id INTEGER PRIMARY KEY, save_dir TEXT)""")
    conn.execute("INSERT INTO companies VALUES (1, ?)", (tmp_dir,))
    conn.execute(
        "INSERT INTO invoices VALUES (1,'purchase','0313581779','0100000000','C26TTL','6470',"
        "'2026-02-25T10:00:00',3102315,248185,'1','{}',NULL)")   # detail_json = NULL (đa số hóa đơn thật)
    conn.commit()
    return conn


tmp_dir = tempfile.mkdtemp(prefix="ke_toan_test_hd_")
try:
    xml_noi_dung = (
        "<HDon><DLHDon><NDHDon>"
        "<NBan><MST>0313581779</MST></NBan>"
        "<TToan><DSLPhi><LPhi><TLPhi>Phi thu ho</TLPhi><TPhi>150000</TPhi></LPhi></DSLPhi></TToan>"
        "</NDHDon></DLHDon></HDon>")
    with open(_os.path.join(tmp_dir, "C26TTL_6470_0313581779.xml"), "w", encoding="utf-8") as f:
        f.write(xml_noi_dung)

    server.db = db_factory2
    server._misa_sql_connect = lambda cid, database=None: FakeConn()
    try:
        kq2 = server._misa_doi_chieu_import_toan_bo(1, "TESTDB")
    finally:
        server.db = orig_db
        server._misa_sql_connect = orig_connect

    mh2 = kq2["mua_hang"]
    print("Mua hàng (test 2, file XML, không detail_json):", mh2)
    assert not mh2["thieu"], f"Hóa đơn 6470 KHÔNG được báo thiếu — được thieu={mh2.get('thieu')}"
    assert not mh2["lech"], (
        f"Hóa đơn 6470 (KHÔNG có detail_json, chỉ có file XML trên máy) KHÔNG được báo LỆCH — phải tự "
        f"dò file XML đã tải (theo save_dir công ty) để lấy 'Tổng tiền phí' — được lech={mh2.get('lech')}")
    print("PASS: hóa đơn 6470 KHÔNG có detail_json (đúng đa số ca thật) vẫn không báo LỆCH sai — đã tự "
          "dò đúng file XML đã tải trên máy (save_dir công ty) để lấy 'Tổng tiền phí' 150.000đ.")
finally:
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)

print("\nTẤT CẢ TEST PASS")
