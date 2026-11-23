# Rà các chức năng ghi MISA khác: Bán hàng (thuế đầu ra 0đ trên Sổ cái), Khấu hao TSCĐ/Phân bổ CCDC (đã ghi sổ mà thiếu
# Sổ cái), Nghiệp vụ khác (đã ghi sổ mà thiếu Sổ cái), TK tiểu khoản/Sổ công nợ ở Mua/Bán hàng. Giả lập CSDL bằng sqlite.
import os, sys, sqlite3, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server
SV = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py"), encoding="utf8").read()

class Cur:   # SQL Server -> SQLite: ISNULL(a,b)=IFNULL(a,b), TOP 1 không dùng ở đây
    def __init__(self, c): self.c = c
    def execute(self, sql, params=()): return self.c.execute(sql.replace("ISNULL(", "IFNULL("), params)
    def executescript(self, s): return self.c.executescript(s)
    def executemany(self, sql, rows): return self.c.executemany(sql, rows)
db = sqlite3.connect(":memory:")
c = Cur(db.cursor())
c.executescript("""
CREATE TABLE GeneralLedger(RefID TEXT, RefDetailID TEXT, RefType INT, RefNo TEXT, RefDate TEXT, PostedDate TEXT, AccountNumber TEXT,
  CorrespondingAccountNumber TEXT, DebitAmount REAL, DebitAmountOC REAL, CreditAmount REAL, CreditAmountOC REAL, JournalMemo TEXT,
  Description TEXT, BranchID TEXT, EntryType INT, OrganizationUnitID TEXT, SortOrder INT);
CREATE TABLE SAVoucher(RefID TEXT, CustomField10 TEXT, TotalVATAmount REAL);
CREATE TABLE FADepreciation(RefID TEXT, RefType INT, RefNo TEXT, RefDate TEXT, PostedDate TEXT, JournalMemo TEXT, BranchID TEXT, IsPostedFinance INT);
CREATE TABLE FADepreciationDetailPost(RefDetailID TEXT, RefID TEXT, DebitAccount TEXT, CreditAccount TEXT, Amount REAL, Description TEXT, OrganizationUnitID TEXT, SortOrder INT);
CREATE TABLE SUAllocation(RefID TEXT, RefType INT, RefNo TEXT, RefDate TEXT, PostedDate TEXT, JournalMemo TEXT, BranchID TEXT, IsPostedFinance INT);
CREATE TABLE SUAllocationDetailPost(RefDetailID TEXT, RefID TEXT, DebitAccount TEXT, CreditAccount TEXT, Amount REAL, Description TEXT, OrganizationUnitID TEXT, SortOrder INT);
CREATE TABLE GLVoucher(RefID TEXT, IsPostedFinance INT, CustomField10 TEXT, TotalAmount REAL);
CREATE TABLE SYSRefType(RefType INT, RefTypeName TEXT);
""")
TYPES = {"GeneralLedger": "nvarchar", "FADepreciationDetailPost": "nvarchar", "SUAllocationDetailPost": "nvarchar"}
def cot(cur, bang):   # thay _misa_cot_bang_that (đọc INFORMATION_SCHEMA của SQL Server)
    rows = db.execute("PRAGMA table_info(%s)" % bang).fetchall()
    return {r[1].lower(): (r[1], "decimal" if r[2] == "REAL" else ("int" if r[2] == "INT" else "nvarchar")) for r in rows}
server._misa_cot_bang_that = cot
M = server._PM_MARK

# 1) Bán hàng: cặp thuế 0đ của chứng từ phần mềm -> điền đúng thuế; chứng từ người dùng không đụng
c.executemany("INSERT INTO SAVoucher VALUES (?,?,?)", [("s1", M, 100000), ("s2", None, 50000)])
c.executemany("INSERT INTO GeneralLedger(RefID,AccountNumber,CorrespondingAccountNumber,DebitAmount,CreditAmount) VALUES (?,?,?,?,?)", [
    ("s1", "131", "5111", 1000000, 0), ("s1", "5111", "131", 0, 1000000), ("s1", "33311", "131", 0, 0), ("s1", "131", "33311", 0, 0),
    ("s2", "33311", "131", 0, 0)])
assert server._misa_sua_thue_ban_hang_so_cai(c, preview=True) == 1
assert server._misa_sua_thue_ban_hang_so_cai(c, preview=False) == 1
assert c.execute("SELECT CreditAmount FROM GeneralLedger WHERE RefID='s1' AND AccountNumber='33311'").fetchone()[0] == 100000
assert c.execute("SELECT DebitAmount FROM GeneralLedger WHERE RefID='s1' AND CorrespondingAccountNumber='33311'").fetchone()[0] == 100000
assert c.execute("SELECT CreditAmount FROM GeneralLedger WHERE RefID='s2'").fetchone()[0] == 0          # chứng từ người dùng giữ nguyên
assert server._misa_sua_thue_ban_hang_so_cai(c, preview=False) == 0
assert "_gl(tk_vat_ra, tk_no_dc, 0, thue, 2, 3, desc_vat)" in SV and "_gl(tk_no_dc, tk_vat_ra, thue, 0, 1, 3, desc_vat)" in SV
assert "_gl(tk_vat_ra, tk_no_dc, 0, 0," not in SV

# 2) Khấu hao / Phân bổ: đã ghi sổ mà không có Sổ cái -> sinh Sổ cái từ dòng hạch toán
c.execute("INSERT INTO SYSRefType VALUES (?,?)", (254, "Khấu hao TSCĐ"))
c.executemany("INSERT INTO FADepreciation VALUES (?,?,?,?,?,?,?,?)", [
    ("k1", 254, "KH00001", "2026-01-31", "2026-01-31", "Khấu hao TSCĐ tháng 1", "B", 1),
    ("k2", 254, "KH00002", "2026-02-28", "2026-02-28", "chưa ghi sổ", "B", 0)])
c.executemany("INSERT INTO FADepreciationDetailPost VALUES (?,?,?,?,?,?,?,?)", [
    ("p1", "k1", "6424", "2141", 3000000, "KH", None, 0), ("p2", "k2", "6424", "2141", 3000000, "KH", None, 0)])
c.executemany("INSERT INTO SUAllocation VALUES (?,?,?,?,?,?,?,?)", [("a1", 431, "PBCC00001", "2026-01-31", "2026-01-31", "Phân bổ CCDC", "B", 1)])
c.executemany("INSERT INTO SUAllocationDetailPost VALUES (?,?,?,?,?,?,?,?)", [("q1", "a1", "6423", "242", 500000, "PB", None, 0)])
kq = server._misa_sua_so_cai_khau_hao_phan_bo(c, preview=True)
assert kq == {"khau_hao": 1, "phan_bo": 1}, kq
server._misa_sua_so_cai_khau_hao_phan_bo(c, preview=False)
r = c.execute("SELECT AccountNumber, CorrespondingAccountNumber, DebitAmount, CreditAmount, RefNo FROM GeneralLedger WHERE RefID='k1' ORDER BY EntryType").fetchall()
assert r == [("6424", "2141", 3000000, 0, "KH00001"), ("2141", "6424", 0, 3000000, "KH00001")], r
assert c.execute("SELECT COUNT(*) FROM GeneralLedger WHERE RefID='k2'").fetchone()[0] == 0     # chưa ghi sổ: không đụng
assert c.execute("SELECT AccountNumber, DebitAmount FROM GeneralLedger WHERE RefID='a1' AND EntryType=1").fetchone() == ("6423", 500000)
assert server._misa_sua_so_cai_khau_hao_phan_bo(c, preview=False) == {"khau_hao": 0, "phan_bo": 0}
assert SV.count("_misa_ghi_so_cai_tu_bang_hach_toan(cur, \"SUAllocation\"") == 1 and SV.count("_misa_ghi_so_cai_tu_bang_hach_toan(cur, \"FADepreciation\"") == 1

# 3) Nghiệp vụ khác của phần mềm: đã ghi sổ mà thiếu Sổ cái -> chuyển về chưa ghi sổ (bấm Ghi sổ trong MISA)
c.executemany("INSERT INTO GLVoucher VALUES (?,?,?,?)", [("g1", 1, M, 5000), ("g2", 1, None, 5000), ("g3", 1, M, 7000)])
c.execute("INSERT INTO GeneralLedger(RefID,AccountNumber,DebitAmount,CreditAmount) VALUES ('g3','131',7000,0)")
assert server._misa_sua_glvoucher_ghi_so_thieu_so_cai(c, preview=False) == 1
assert [r[0] for r in c.execute("SELECT IsPostedFinance FROM GLVoucher ORDER BY RefID").fetchall()] == [0, 1, 1]
assert 'bool(co_mau_so_cai), "IsPostedFinance"' in SV
a = SV.index("def _misa_chuyen_cong_no_sai_doi_tuong("); b = SV.index("\ndef ", a + 10)
assert '_misa_gan(glv_row, cols_glv, False, "IsPostedFinance")' in SV[a:b] and "_PM_MARK, \"CustomField10\"" in SV[a:b]
a = SV.index("def _misa_dao_dieu_chinh_cong_no("); b = SV.index("\ndef ", a + 10)
assert '_misa_gan(glv_row, cols_glv, False, "IsPostedFinance")' in SV[a:b]

# 4) Mua/Bán hàng: TK tiểu khoản + Sổ công nợ chỉ cho TK công nợ
assert SV.count('_misa_tk_chi_tiet(cur, t2, tk_set, tra_tk.__dict__.setdefault("cache", {}))') == 3
assert SV.count('if _misa_tk_co_cong_no(m["co_acc"]):') == 4
assert '"/api/misa-sql/sua-so-cai/{cid}"' in SV
ix = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "index.html"), encoding="utf8").read()
assert "misaSqlSuaSoCai()" in ix and "/api/misa-sql/sua-so-cai/" in ix
print("PASS: rà Sổ cái các chức năng ghi MISA — thuế bán hàng, khấu hao/phân bổ, NVK ghi sổ thiếu sổ cái, TK tiểu khoản, nút sửa")
