# UNT/UNC ghi thẳng MISA: dòng Sổ cái phải mang ĐÚNG TK hạch toán của chi tiết (3383, 3341, 1111…), không giữ 131/331
# của chứng từ mẫu — nếu không, báo cáo MISA không thấy hạch toán này cho tới khi chạy "Bảo trì dữ liệu".
import os, sys, sqlite3
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server
cols = {k.lower(): (k, "nvarchar") for k in ("AccountNumber", "CorrespondingAccountNumber", "DebitAmount", "CreditAmount")}
# UNC (chi): Nợ hạch toán / Có ngân hàng
g = {"AccountNumber": "331", "CorrespondingAccountNumber": "1121"}
server._misa_gl_dat_tk_unt_unc(g, cols, "unc", True, "3383", "1121-STB")
assert g == {"AccountNumber": "3383", "CorrespondingAccountNumber": "1121-STB"}, g
g = {"AccountNumber": "1121", "CorrespondingAccountNumber": "331"}
server._misa_gl_dat_tk_unt_unc(g, cols, "unc", False, "3383", "1121-STB")
assert g == {"AccountNumber": "1121-STB", "CorrespondingAccountNumber": "3383"}, g
# UNT (thu): Nợ ngân hàng / Có hạch toán
g = {"AccountNumber": "1121", "CorrespondingAccountNumber": "131"}
server._misa_gl_dat_tk_unt_unc(g, cols, "unt", True, "515", "1121")
assert g == {"AccountNumber": "1121", "CorrespondingAccountNumber": "515"}, g
g = {"AccountNumber": "131", "CorrespondingAccountNumber": "1121"}
server._misa_gl_dat_tk_unt_unc(g, cols, "unt", False, "515", "1121")
assert g == {"AccountNumber": "515", "CorrespondingAccountNumber": "1121"}, g
assert server._misa_tk_co_cong_no("331") and server._misa_tk_co_cong_no("1311") and not server._misa_tk_co_cong_no("3383") and not server._misa_tk_co_cong_no("3341")

# Sửa chứng từ CŨ đã ghi sai (giả lập CSDL bằng sqlite + hàm ISNULL)
db = sqlite3.connect(":memory:")
class Cur:   # SQL Server ISNULL(a,b) == SQLite IFNULL(a,b)
    def __init__(self, c): self.c = c
    def execute(self, sql, params=()): return self.c.execute(sql.replace("ISNULL(", "IFNULL("), params)
    def executescript(self, s): return self.c.executescript(s)
    def executemany(self, sql, rows): return self.c.executemany(sql, rows)
c = Cur(db.cursor())
c.executescript("""
CREATE TABLE BAWithDraw(RefID TEXT, CustomField10 TEXT);
CREATE TABLE BAWithDrawDetail(RefID TEXT, DebitAccount TEXT, CreditAccount TEXT);
CREATE TABLE GeneralLedger(RefID TEXT, AccountNumber TEXT, CorrespondingAccountNumber TEXT, DebitAmount REAL, CreditAmount REAL);
CREATE TABLE AccountObjectLedger(RefID TEXT, AccountNumber TEXT, CorrespondingAccountNumber TEXT);
""")
M = server._PM_MARK
# r1: BHXH 3383 ghi sai thành 331 + có sổ công nợ thừa; r2: 331 đúng; r3: chứng từ THẬT của người dùng (không đánh dấu) -> không đụng
c.executemany("INSERT INTO BAWithDraw VALUES (?,?)", [("r1", M), ("r2", M), ("r3", None)])
c.executemany("INSERT INTO BAWithDrawDetail VALUES (?,?,?)", [("r1", "3383", "1121"), ("r2", "331", "1121"), ("r3", "3383", "1121")])
c.executemany("INSERT INTO GeneralLedger VALUES (?,?,?,?,?)", [
    ("r1", "331", "1121", 5482500, 0), ("r1", "1121", "331", 0, 5482500),
    ("r2", "331", "1121", 100, 0), ("r2", "1121", "331", 0, 100),
    ("r3", "331", "1121", 7, 0), ("r3", "1121", "331", 0, 7)])
c.executemany("INSERT INTO AccountObjectLedger VALUES (?,?,?)", [("r1", "331", "1121"), ("r2", "331", "1121")])
assert server._misa_sua_tk_so_cai_unt_unc(c, "unc", preview=True) == 1
assert c.execute("SELECT AccountNumber FROM GeneralLedger WHERE RefID='r1' AND DebitAmount>0").fetchone()[0] == "331"  # xem trước không ghi
assert server._misa_sua_tk_so_cai_unt_unc(c, "unc", preview=False) == 1
assert c.execute("SELECT AccountNumber, CorrespondingAccountNumber FROM GeneralLedger WHERE RefID='r1' AND DebitAmount>0").fetchone() == ("3383", "1121")
assert c.execute("SELECT AccountNumber, CorrespondingAccountNumber FROM GeneralLedger WHERE RefID='r1' AND CreditAmount>0").fetchone() == ("1121", "3383")
assert c.execute("SELECT COUNT(*) FROM AccountObjectLedger WHERE RefID='r1'").fetchone()[0] == 0     # 3383 không phải công nợ
assert c.execute("SELECT COUNT(*) FROM AccountObjectLedger WHERE RefID='r2'").fetchone()[0] == 1     # 331 giữ nguyên
assert c.execute("SELECT AccountNumber FROM GeneralLedger WHERE RefID='r3' AND DebitAmount>0").fetchone()[0] == "331"  # không đụng chứng từ thật
assert server._misa_sua_tk_so_cai_unt_unc(c, "unc", preview=False) == 0   # chạy lại: không còn gì để sửa
sv = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py"), encoding="utf8").read()
assert sv.count("    _misa_gl_dat_tk_unt_unc(g, cols_gl, loai, _snum(mgl.get") == 2 and sv.count("_misa_sua_tk_so_cai_unt_unc(cur, loai, preview=preview)") == 2
assert "if mau_aol is not None and aid and _misa_tk_co_cong_no(hach):" in sv
print("PASS: UNT/UNC — Sổ cái mang đúng TK hạch toán (3383/3341/515…), không giữ 131/331 của mẫu; tự sửa chứng từ cũ do phần mềm ghi")
