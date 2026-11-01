import os, sys, sqlite3, datetime, json
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Ca thật (Ajinomoto C26TDN 213437, dữ liệu GIẢ ở đây): hóa đơn chiết khấu thương mại mà MỌI dòng ÂM (-164.543.635, thuế -13.163.491) nhưng tổng hóa
# đơn trên trang Thuế (tgtcthue/tgtthue/tgtttbso) ghi DƯƠNG. Bảng kê ghi ÂM theo dòng và MISA nhận ÂM (đúng), nhưng đối chiếu lấy tổng DƯƠNG làm nguồn
# -> báo "TỔNG LỆCH" (lệch đúng 2 × (doanh số + thuế)) dù Excel không lệch. Nay nguồn đổi dấu theo cùng quy ước Bảng kê.
dong_ck = {"tchat": "1", "ten_hang": "Chiết khấu thương mại theo bảng kê số 197 (Chiết khấu TM - ghi âm)", "thtien": -100000000, "stckhau": 0}
assert server._la_dong_chiet_khau_thuan(dong_ck)
assert server._la_hd_chiet_khau_thuan([dong_ck])
assert server._la_hd_chiet_khau_thuan([{"tchat": "3", "ten_hang": "CK", "thtien": 5000000}, {"tchat": "4", "ten_hang": "ghi chú", "thtien": 0}])
assert not server._la_hd_chiet_khau_thuan([])
assert not server._la_hd_chiet_khau_thuan([{"tchat": "1", "ten_hang": "Hàng", "thtien": 100000}, dong_ck])           # có dòng hàng dương -> không phải CK thuần
assert not server._la_hd_chiet_khau_thuan([{"tchat": "3", "ten_hang": "Hàng giảm giá", "thtien": 90000, "stckhau": 10000}])   # CK dòng -> hàng net dương
print("PASS 1: nhận diện hóa đơn chiết khấu thuần (mọi dòng âm / TChat=3), không nhầm hàng có chiết khấu dòng.")

HEADER = ["Ký hiệu", "Số HĐ", "Ngày", "Người bán", "MST bán", "STT", "Mã vt", "Tên hàng hóa/dịch vụ", "ĐVT", "Số lượng", "Đơn giá",
          "Thành tiền", "Thuế suất", "Tiền thuế GTGT", "Nợ", "Có"]
BK = [["C26TZZ", "9001", "30/10/2026", "NCC GIẢ", "0300000099", 1, "MHDV", "Chiết khấu", "Kỳ", 1, -100000000, -100000000, "8%", -8000000, "6427", "331"],
      ["C26TZZ", "9002", "30/10/2026", "NCC GIẢ", "0300000099", 1, "H1", "Hàng", "Cái", 1, 50000000, 50000000, "8%", 4000000, "1561", "331"],
      ["TỔNG CỘNG", "", "", "", "", "", "", "", "", "", "", 0, "", 0, "", ""]]
detail_ck = json.dumps({"hdhhdvu": [{"stt": 1, "tchat": 1, "ten": dong_ck["ten_hang"], "thtien": -100000000, "sluong": 1, "dgia": -100000000,
                                    "tsuat": 0.08, "tthue": -8000000, "dvtinh": "Kỳ"}], "tgtcthue": 100000000, "tgtthue": 8000000})

def db_factory():
    conn = sqlite3.connect(":memory:"); conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE invoices (company_id INTEGER, loai TEXT, nbmst TEXT, nmmst TEXT, khhdon TEXT, shdon TEXT, tdlap TEXT, tgtcthue REAL, tgtthue REAL, tthai TEXT, raw TEXT, detail_json TEXT)")
    conn.execute("CREATE TABLE companies (id INTEGER PRIMARY KEY, save_dir TEXT)"); conn.execute("INSERT INTO companies VALUES (1, '')")
    conn.execute("CREATE TABLE nhap_lieu (company_id INTEGER, loai TEXT, header_json TEXT, rows_json TEXT, updated_at TEXT, PRIMARY KEY (company_id, loai))")
    # tổng trên trang Thuế: DƯƠNG dù các dòng đều ÂM
    conn.execute("INSERT INTO invoices VALUES (1,'purchase','0300000099','0100000000','C26TZZ','9001','2026-10-30T08:00:00',100000000,8000000,'1','{}',?)", (detail_ck,))
    conn.execute("INSERT INTO invoices VALUES (1,'purchase','0300000099','0100000000','C26TZZ','9002','2026-10-30T08:00:00',50000000,4000000,'1','{}',NULL)")
    conn.execute("INSERT INTO nhap_lieu VALUES (1,'in',?,?,?)", (json.dumps(HEADER), json.dumps(BK), "x"))
    conn.commit(); return conn

MISA = [("0300000099", "9001", -100000000, -8000000, datetime.datetime(2026, 10, 30)),
        ("0300000099", "9002", 50000000, 4000000, datetime.datetime(2026, 10, 30))]

class FakeCursor:
    def execute(self, sql, params=()):
        self.sql, self.p = sql, tuple(params) if isinstance(params, (tuple, list)) else (params,); return self
    def fetchall(self):
        if "FROM sys.columns" in self.sql:
            return [("AccountObjectTaxCode", "nvarchar"), ("InvNo", "nvarchar"), ("TotalTurnoverAmount", "money"), ("TotalVATAmount", "money"), ("RefDate", "datetime")] if self.p[0] == "PUInvoice" else []
        if "FROM PUInvoice" in self.sql:
            return [r for r in MISA if self.p[0] <= r[4] <= self.p[1]]
        return []
    def fetchone(self): return None

class FakeConn:
    def __init__(self): self.c = FakeCursor()
    def cursor(self): return self.c
    def close(self): pass

orig_db, orig_connect = server.db, server._misa_sql_connect
server.db = db_factory; server._misa_sql_connect = lambda cid, database=None: FakeConn()
try:
    mh = server._misa_doi_chieu_import_toan_bo(1, "TESTDB")["mua_hang"]
finally:
    server.db, server._misa_sql_connect = orig_db, orig_connect
assert mh["tong_khop"] is True and not mh["lech"] and not mh["thieu"] and not mh["thua"], mh
assert mh["tong_ds_nguon"] == -50000000 and mh["tong_thue_nguon"] == -4000000, mh
print("PASS 2: HĐ chiết khấu ghi âm (tổng trang Thuế dương, dòng âm) khớp MISA âm — không còn báo TỔNG LỆCH.")

# Không đụng hóa đơn thường: chỉ đổi dấu khi MỌI dòng là chiết khấu
src = open(os.path.join(_REPO_ROOT, "server.py"), encoding="utf-8").read()
assert "la_ck_hd = _la_hd_chiet_khau_thuan(_items_hh)" in src and "_la_hd_ck_thuan_nguon(r)" in src
print("PASS 3: Bảng kê và đối chiếu dùng CHUNG một quy ước nhận diện hóa đơn chiết khấu thuần.")
