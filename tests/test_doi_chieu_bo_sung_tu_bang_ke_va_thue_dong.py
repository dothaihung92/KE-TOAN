import os, sys, sqlite3, datetime, json
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# ===== 1) Thuế từng dòng (TongTien_Thue người bán ghi) cộng lại lệch TgTThue -> tính lại theo thuế suất (ca thật Universe C26TUN 6357) =====
def dong(ds, ts, th, **k):
    return {"ds": ds, "ts_hien": ts, "tien_thue": th, "phan_bo": False, "it": dict(k)}
d6357 = [dong(529200, "8%", 42336), dong(1800000, "8%", 144000), dong(298469, "8%", 23878),
         dong(793800, "8%", 63504), dong(596938, "8%", 47755), dong(1591834, "8%", 271347)]
assert server._khop_thue_dong_voi_tong_hd(d6357, 448820)
assert sum(d["tien_thue"] for d in d6357) == 448820 and d6357[5]["tien_thue"] == 127347 and d6357[1]["tien_thue"] == 144000, [d["tien_thue"] for d in d6357]
d8052 = [dong(654250, "8%", 52340), dong(523400, "8%", 193872), dong(1900000, "8%", 152000)]
assert server._khop_thue_dong_voi_tong_hd(d8052, 246212) and [d["tien_thue"] for d in d8052] == [52340, 41872, 152000]
print("PASS 1: HĐ 6357/8052 — thuế dòng cộng 592.820/398.212 khác TgTThue 448.820/246.212 -> tính lại đúng (dòng xếp hàng 127.347, đại lý 41.872).")

# không đụng: tổng đã khớp; TgTThue = 0 mà dòng có thuế (API trả thiếu); thuế suất KHAC lẻ; tính lại cũng không khớp; dòng 0%/KCT
ok = [dong(100000, "8%", 8000), dong(50000, "KCT", 0)]
assert not server._khop_thue_dong_voi_tong_hd(ok, 8000)
z = [dong(100000, "8%", 8000)]
assert not server._khop_thue_dong_voi_tong_hd(z, 0) and z[0]["tien_thue"] == 8000
kh = [dong(100000, "KHAC:5.26%", 5260)]
assert not server._khop_thue_dong_voi_tong_hd(kh, 9000) and kh[0]["tien_thue"] == 5260
lech = [dong(100000, "8%", 8000), dong(100000, "10%", 10000)]
assert not server._khop_thue_dong_voi_tong_hd(lech, 30000) and [d["tien_thue"] for d in lech] == [8000, 10000]
hon = [dong(1000000, "8%", 100000), dong(37148, "0%", 0)]
assert server._khop_thue_dong_voi_tong_hd(hon, 80000) and [d["tien_thue"] for d in hon] == [80000, 0]
print("PASS 2: không tự sửa khi tổng đã khớp / TgTThue=0 / thuế suất lẻ / tính lại vẫn lệch; dòng 0% giữ 0.")

src = open(os.path.join(_REPO_ROOT, "server.py"), encoding="utf-8").read()
i = src.index("_khop_thue_dong_voi_tong_hd(dong_list, _tong_thue_hd_tu_file(items, r[\"tgtthue\"]))")
assert src.index("# --- Phân bổ tiền thuế cho dòng thuế suất KHAC") < i < src.index("# --- Pass 2: ghi ra sheet ---")
print("PASS 3: Bảng kê áp dụng kiểm tra thuế dòng = TgTThue trước khi ghi ra sheet.")

# ===== 2) Đối chiếu: hóa đơn có trong Bảng kê Đầu vào (đã Import MISA) nhưng mất khỏi dữ liệu tra cứu -> không báo THỪA =====
HEADER = ["Ký hiệu", "Số HĐ", "Ngày", "Người bán", "MST bán", "STT", "Mã vt", "Tên hàng hóa/dịch vụ", "ĐVT", "Số lượng", "Đơn giá",
          "Thành tiền", "Thuế suất", "Tiền thuế GTGT", "Nợ", "Có"]
BK = [["C26TUN", "6357", "10/08/2026", "UNIVERSE", "0318581564", 1, "", "Phí", "", 1, 5610241, 5610241, "8%", 448820, "6422", "331"],
      ["C26MHD", "15468879", "03/08/2026", "GSM", "0110269067", 1, "", "Cước", "", 1, 37147, 37147, "8%", 2972, "6422", "331"],
      ["C26MHD", "15468879", "03/08/2026", "GSM", "0110269067", 2, "", "Phí nền tảng", "", 1, 2668, 2668, "8%", 213, "6422", "331"],
      ["C26MHC", "71013018", "07/08/2026", "GSM CN", "0110269067-001", 1, "", "Cước", "", 1, 163889, 163889, "8%", 13111, "6422", "331"],
      ["C26MHA", "999", "05/08/2026", "Bị hủy", "0300000001", 1, "", "Hàng", "", 1, 500000, 500000, "8%", 40000, "6422", "331"],
      ["TỔNG CỘNG", "", "", "", "", "", "", "", "", "", "", 0, "", 0, "", ""]]

def db_factory():
    conn = sqlite3.connect(":memory:"); conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE invoices (company_id INTEGER, loai TEXT, nbmst TEXT, nmmst TEXT, khhdon TEXT, shdon TEXT, tdlap TEXT, tgtcthue REAL, tgtthue REAL, tthai TEXT, raw TEXT, detail_json TEXT)")
    conn.execute("CREATE TABLE companies (id INTEGER PRIMARY KEY, save_dir TEXT)"); conn.execute("INSERT INTO companies VALUES (1, '')")
    conn.execute("CREATE TABLE nhap_lieu (company_id INTEGER, loai TEXT, header_json TEXT, rows_json TEXT, updated_at TEXT, PRIMARY KEY (company_id, loai))")
    conn.execute("INSERT INTO invoices VALUES (1,'purchase','0318581564','0100000000','C26TUN','6357','2026-08-10T08:00:00',5610241,448820,'1','{}',NULL)")
    conn.execute("INSERT INTO invoices VALUES (1,'purchase','0300000001','0100000000','C26MHA','999','2026-08-05T08:00:00',500000,40000,'6','{}',NULL)")   # đã hủy: KHÔNG bổ sung lại từ Bảng kê
    conn.execute("INSERT INTO nhap_lieu VALUES (1,'in',?,?,?)", (json.dumps(HEADER), json.dumps(BK), "x"))
    conn.commit(); return conn

MISA = [("0318581564", "6357", 5610241, 448820, datetime.datetime(2026, 8, 10)),
        ("0110269067", "15468879", 39815, 3185, datetime.datetime(2026, 8, 3)),
        ("0110269067001", "71013018", 163889, 13111, datetime.datetime(2026, 8, 7)),
        ("0300000001", "999", 500000, 40000, datetime.datetime(2026, 8, 5))]

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
print(mh)
assert sorted(x["so_hd"] for x in mh["bo_sung_bang_ke"]) == ["15468879", "71013018"], mh["bo_sung_bang_ke"]
assert [x["so_hd"] for x in mh["thua"]] == ["999"], "HĐ đã hủy trên trang Thuế mà MISA vẫn có -> vẫn báo THỪA đúng"
assert not mh["thieu"] and not mh["lech"]
assert {"15468879", "71013018"}.isdisjoint(x["so_hd"] for x in mh["thua"])
print("PASS 4: 2 HĐ máy tính tiền mất khỏi dữ liệu tra cứu nhưng có trong Bảng kê -> lấy số Bảng kê làm nguồn, không báo THỪA; HĐ đã hủy vẫn báo THỪA.")

# ===== 3) LỆCH vì Bảng kê cũ ghi sai thuế dòng (như MISA) -> ghi chú cách sửa =====
BK[0] = ["C26TUN", "6357", "10/08/2026", "UNIVERSE", "0318581564", 1, "", "Phí", "", 1, 5610241, 5610241, "8%", 592820, "6422", "331"]
MISA[0] = ("0318581564", "6357", 5610241, 592820, datetime.datetime(2026, 8, 10))
server.db = db_factory; server._misa_sql_connect = lambda cid, database=None: FakeConn()
try:
    mh = server._misa_doi_chieu_import_toan_bo(1, "TESTDB")["mua_hang"]
finally:
    server.db, server._misa_sql_connect = orig_db, orig_connect
assert len(mh["lech"]) == 1 and mh["lech"][0]["thue_nguon"] == 448820 and mh["lech"][0]["thue_misa"] == 592820
assert "Xuất lại Bảng kê" in mh["lech"][0].get("ghi_chu", ""), mh["lech"]
assert server._doi_chieu_xuat_rows({"mua_hang": mh})[0][-1] == mh["lech"][0]["ghi_chu"]
print("PASS 5: HĐ 6357 LỆCH thuế 448.820/592.820 do Bảng kê cũ -> ghi chú hướng dẫn xuất lại Bảng kê và sửa chứng từ MISA (có trong file Excel).")

# ===== 4) Tự sửa Bảng kê ĐÃ LƯU (bản cũ) theo tổng thuế hóa đơn gốc trước khi ghi MISA/đối chiếu =====
import tempfile
fdb = os.path.join(tempfile.mkdtemp(), "t.db")
c = sqlite3.connect(fdb)
c.execute("CREATE TABLE invoices (company_id INTEGER, loai TEXT, nbmst TEXT, nmmst TEXT, khhdon TEXT, shdon TEXT, tdlap TEXT, tgtcthue REAL, tgtthue REAL, tthai TEXT, raw TEXT, detail_json TEXT)")
c.execute("CREATE TABLE nhap_lieu (company_id INTEGER, loai TEXT, header_json TEXT, rows_json TEXT, updated_at TEXT, PRIMARY KEY (company_id, loai))")
c.execute("INSERT INTO invoices VALUES (1,'purchase','0318581564','x','C26TUN','6357','2026-08-10',5610241,448820,'1','{}',NULL)")
c.execute("INSERT INTO invoices VALUES (1,'purchase','0110269067','x','C26MHD','15468879','2026-08-03',39815,3185,'1','{}',NULL)")
H2 = ["Ký hiệu", "Số HĐ", "Ngày", "Người bán", "MST bán", "STT", "Mã vt", "Tên hàng hóa/dịch vụ", "ĐVT", "Số lượng", "Đơn giá", "Thành tiền", "Thuế suất", "Tiền thuế GTGT", "Nợ", "Có"]
def r6357(stt, ten, tt, th): return ["C26TUN", 6357, "10/08/2026", "UNIVERSE", "0318581564", stt, "", ten, "", 1, tt, tt, "8%", th, "6422", "331"]
R2 = [r6357(1, "Phí đại lý", 529200, 42336), r6357(2, "Giao nhận", 1800000, 144000), r6357(3, "Cân bằng cont", 298469, 23878),
      r6357(4, "Chứng từ", 793800, 63504), r6357(5, "Xếp dỡ", 596938, 47755), r6357(6, "Xếp hàng vào kho", 1591834, 271347),
      ["C26MHD", 15468879, "03/08/2026", "GSM", "0110269067", 1, "", "Cước", "", 1, 37147, 37147, "8%", 2972, "6422", "331"],
      ["C26MHD", 15468879, "03/08/2026", "GSM", "0110269067", 2, "", "Phí", "", 1, 2668, 2668, "8%", 213, "6422", "331"],
      ["TỔNG CỘNG", "", "", "", "", "", "", "", "", "", "", 5650056, "", 596005, "", ""]]
c.execute("INSERT INTO nhap_lieu VALUES (1,'in',?,?,'x')", (json.dumps(H2), json.dumps(R2)))
c.commit(); c.close()
def db_file():
    k = sqlite3.connect(fdb); k.row_factory = sqlite3.Row; return k
server.db = db_file
try:
    sua = server._sua_thue_dong_bang_ke_da_luu(1)
    sua2 = server._sua_thue_dong_bang_ke_da_luu(1)
    _, rr = server._doc_nhap_lieu(1, "in")
finally:
    server.db = orig_db
assert sua == [("in", "C26TUN", "6357", 592820, 448820)], sua
assert sua2 == [], "chạy lại không sửa gì thêm"
assert [x[13] for x in rr[:6]] == [42336, 144000, 23878, 63504, 47755, 127347] and rr[6][13] == 2972 and rr[7][13] == 213
assert rr[8][13] == 448820 + 3185, rr[8]
print("PASS 6: Bảng kê đã lưu tự sửa HĐ 6357 (592.820 -> 448.820, dòng xếp hàng 127.347), dòng TỔNG CỘNG cập nhật; HĐ đúng không đổi; chạy lại không đổi gì.")
src = open(os.path.join(_REPO_ROOT, "server.py"), encoding="utf-8").read()
tu_dong = src[src.index("def _misa_import_tu_dong("):]
assert tu_dong.index("_sua_thue_dong_bang_ke_da_luu(cid)") < tu_dong.index("_misa_ghi_mua_hang_dv(")
for ten in ("def misa_sql_doi_chieu_import(", "def misa_sql_doi_chieu_import_xuat("):
    f = src[src.index(ten):]
    assert f.index("_sua_thue_dong_bang_ke_da_luu(cid)") < f.index("_misa_doi_chieu_import_toan_bo(cid, database)")
print("PASS 7: Import tự động / Đối chiếu / Xuất đối chiếu đều tự sửa Bảng kê đã lưu trước.")

# Bảng kê đã đúng (đã tự sửa) nhưng MISA còn số cũ -> ghi chú hướng dẫn chạy lại Import tự động
BK[0] = ["C26TUN", "6357", "10/08/2026", "UNIVERSE", "0318581564", 1, "", "Phí", "", 1, 5610241, 5610241, "8%", 448820, "6422", "331"]
server.db = db_factory; server._misa_sql_connect = lambda cid, database=None: FakeConn()
try:
    mh = server._misa_doi_chieu_import_toan_bo(1, "TESTDB")["mua_hang"]
finally:
    server.db, server._misa_sql_connect = orig_db, orig_connect
assert "Import tự động toàn bộ" in mh["lech"][0].get("ghi_chu", "") and "Bảng kê đã đúng" in mh["lech"][0]["ghi_chu"], mh["lech"]
print("PASS 8: Bảng kê đúng, MISA còn số cũ -> ghi chú chạy lại Import tự động toàn bộ.")
print("ALL DONE")
