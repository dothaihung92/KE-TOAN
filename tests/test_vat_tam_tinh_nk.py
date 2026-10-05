import os, sys, sqlite3, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server
from fastapi import Response

# Tạm tính thuế VAT: VAT đầu vào = hóa đơn mua trong kỳ + thuế GTGT tờ khai NHẬP KHẨU đăng ký trong kỳ; tờ khai NK sát NGOÀI kỳ được nêu rõ (không âm thầm bỏ).
conn = sqlite3.connect(":memory:", check_same_thread=False); conn.row_factory = sqlite3.Row
conn.execute("CREATE TABLE companies (id INTEGER, ten TEXT, mst TEXT)")
conn.execute("INSERT INTO companies VALUES (7, 'CT', '0315253276')")
conn.execute("CREATE TABLE invoices (id INTEGER, company_id INTEGER, loai TEXT, he_thong TEXT, khhdon TEXT, shdon TEXT, nbmst TEXT, tdlap TEXT, tgtthue REAL, tthai TEXT, raw TEXT, nmmst TEXT, tgtcthue REAL)")
conn.execute("CREATE TABLE tokhai_nhap (company_id INTEGER, so_tk TEXT, ngay_dk TEXT, nguoi_xk TEXT, items_json TEXT, updated_at TEXT)")
conn.execute("CREATE TABLE vat_balance (company_id INTEGER, ky TEXT, du_dau_ky REAL, du_cuoi_ky REAL, updated_at TEXT)")
def hd(i, loai, ngay, thue): conn.execute("INSERT INTO invoices VALUES (?,7,?, 'query','K','%d','1',?,?,'1','{}','',0)" % i, (i, loai, ngay, thue))
hd(1, "purchase", "2026-07-10T00:00:00", 28_132_741); hd(2, "purchase", "2026-08-10T00:00:00", 38_175_387); hd(3, "purchase", "2026-09-10T00:00:00", 25_631_223)
hd(4, "sold", "2026-08-01T00:00:00", 162_824_055)
hd(5, "purchase", "2026-06-05T00:00:00", 9_999_999)       # ngoài kỳ: không tính
def nk(so, ngay, thue): conn.execute("INSERT INTO tokhai_nhap VALUES (7,?,?,'PIMEX',?,'')", (so, ngay, json.dumps([{"tri_gia_gtgt": 654_378_215, "tien_thue_gtgt": thue}])))
class KhongDong:
    def __init__(self, c): self.c = c
    def execute(self, *a): return self.c.execute(*a)
    def commit(self): self.c.commit()
    def close(self): pass
server.db = lambda: KhongDong(conn)
server._get_imported = lambda cid, ky: None
tinh = lambda: server.vat_tam_tinh(7, Response(), ky="Q3/2026", du_dau_ky=0)

# tờ khai NK đăng ký 26/06/2026 (Q2): KHÔNG tính vào Q3 nhưng phải được nêu trong cảnh báo
nk("108379094830", "2026-06-26", 52_350_257)
r = tinh()
assert r["vat_mua"] == 91_939_351 and r["vat_mua_nk"] == 0 and r["vat_ban"] == 162_824_055 and r["phai_nop"] == 70_884_704, r
assert "108379094830" in r["canh_bao_nk"] and "26/06/2026" in r["canh_bao_nk"] and "52,350,257" in r["canh_bao_nk"] and "NGOÀI kỳ" in r["canh_bao_nk"], r["canh_bao_nk"]
# cùng tờ khai đăng ký trong Q3: tính vào VAT đầu vào -> khớp tờ khai XML (mua 144.289.608, phải nộp 18.534.447)
conn.execute("DELETE FROM tokhai_nhap"); nk("108379094830", "2026-07-02", 52_350_257)
r = tinh()
assert r["vat_mua"] == 144_289_608 and r["vat_mua_nk"] == 52_350_257 and r["phai_nop"] == 18_534_447 and not r["canh_bao_nk"], r
# ngày dạng dd/mm/yyyy hoặc kèm giờ vẫn được nhận
for nd in ("02/07/2026", "2026-07-02T00:00:00", "2026-07-02 00:00:00"):
    conn.execute("DELETE FROM tokhai_nhap"); nk("1", nd, 52_350_257)
    assert tinh()["vat_mua_nk"] == 52_350_257, nd
# tờ khai NK xa kỳ (> 45 ngày) không nhắc
conn.execute("DELETE FROM tokhai_nhap"); nk("2", "2026-03-01", 1_000_000)
r = tinh(); assert r["vat_mua_nk"] == 0 and not r["canh_bao_nk"]
print("PASS")
