import os, sys, types
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
# Ca thật: sổ MISA theo TT133 (không có TK 521, không có tiểu khoản 1561) -> "2. Bảng kê Đầu ra" lỗi FK_SAVoucherDetail_Account_DiscountAccount
# và "3a. Danh mục Hàng hóa" lỗi FK_InventoryItem_Account_InventoryAccount (phần mềm ghi cứng 5211 / 1561). Phải dùng TK có thật trong sổ.
g = {"__file__": os.path.join(_REPO_ROOT, "tests", "test_ban_hang_ghi_so.py")}
src = open(g["__file__"], encoding="utf-8").read()
exec(src[:src.index("r = _misa_ghi_ban_hang(1")], g)

TK133 = [("131",), ("156",), ("632",), ("5111",), ("3331",), ("33311",), ("511",)]


class Cur133(g["FakeCursor"]):
    def __init__(self, ck_hoc=None):
        super().__init__(); self.ck_hoc = ck_hoc

    def fetchall(self):
        sql = self._last_sql
        if sql.startswith("SELECT AccountNumber FROM Account"):
            return TK133
        if "DiscountAccount FROM SAVoucherDetail" in sql:
            return [(self.ck_hoc,)] if self.ck_hoc else []
        return super().fetchall()


def chay(cur, thue=80000):
    g["ns"]['_misa_sql_connect'] = lambda cid, database=None: g["FakeConn"](cur)
    g["ns"]['nhap_lieu_get'] = lambda cid, loai: {"header": g["header"], "rows": [
        ["31/03/2026", "22", "0100109106", "CÔNG TY TNHH KHÁCH HÀNG A", "Bán Hàng", 1000000, thue, "", ""]]}
    exec(g["extract_fn"]('_misa_ghi_ban_hang'), g["ns"])
    return g["ns"]['_misa_ghi_ban_hang'](1, "TESTDB", preview=False, ghi_de=False)


c = Cur133()
chay(c)
d = c.inserted["SAVoucherDetail"][0]
assert d["DiscountAccount"] in {a for (a,) in TK133}, d["DiscountAccount"]
assert d["DiscountAccount"] == "5111" and d["VATAccount"] == "33311", d
print("PASS 1: sổ TT133 không có 521 -> TK chiết khấu = TK doanh thu của dòng (5111), không còn ghi 5211.")
c = Cur133(ck_hoc="511")
chay(c)
assert c.inserted["SAVoucherDetail"][0]["DiscountAccount"] == "511"
print("PASS 2: có chứng từ bán hàng thật trong sổ -> dùng đúng TK chiết khấu sổ đang dùng.")
c = Cur133(ck_hoc="5211")        # TK học được nhưng không còn trong danh mục -> không dùng
chay(c)
assert c.inserted["SAVoucherDetail"][0]["DiscountAccount"] == "5111"
print("PASS 3: TK chiết khấu học được nhưng không có trong danh mục -> bỏ.")

# 3a Danh mục Hàng hóa: TK kho 1561 -> 156 khi sổ không có 1561
import server
ghi = []


class CurDm:
    def execute(self, sql, *p):
        self.sql = sql
        if sql.startswith("INSERT INTO InventoryItem"):
            ghi.append(p)
        return self

    def fetchall(self):
        if self.sql.startswith("SELECT AccountNumber FROM Account"):
            return TK133
        return []

    def fetchone(self):
        return None


class ConnDm:
    autocommit = True
    def cursor(self): return CurDm()
    def commit(self): pass
    def rollback(self): pass
    def close(self): pass


server._misa_sql_connect = lambda cid, database=None: ConnDm()
r = server._misa_ghi_hang_hoa(1, "TESTDB", [["HH01", "Nệm DUN", "Cái", None]], preview=False, loai="hh")
assert ghi, r
cols = ["InventoryItemID", "InventoryItemCode", "InventoryItemName", "InventoryItemType", "UnitID", "InventoryAccount", "COGSAccount", "SaleAccount"]
v = dict(zip(cols, ghi[0][:8]))
assert (v["InventoryAccount"], v["COGSAccount"], v["SaleAccount"]) == ("156", "632", "5111"), v
print("PASS 4: Danh mục Hàng hóa — sổ không có 1561 thì TK kho = 156 (TK cha có thật).")
print("\nALL DONE")
