import os, sys, datetime
_HERE = os.path.dirname(os.path.abspath(__file__))
_t = open(os.path.join(_HERE, "test_ban_hang_ghi_so.py"), encoding="utf-8").read()
exec(_t[:_t.index('header = ["Ngày lập"')], globals())   # harness MISA giả (ns, FakeCursor, FakeConn...)

# Yêu cầu: khách bán hàng KHÔNG có MST nhưng có tên (khách nước ngoài, MST ghi 'KL') PHẢI lấy ĐÚNG mã khách trong Danh mục Đối tượng
# MISA (vd 'JUSTADDPLANTS'), chưa có thì tạo mã riêng (BARON LTD -> 'BARONLTD'); mã chung 'KL' chỉ cho khách bán cho người tiêu dùng.
# Ca thật: HĐ 22 (BARON LTD) bị bỏ qua 'thiếu KH', HĐ 21 (JUST ADD PLANTS) trước đây dồn vào KL.

class Cur(FakeCursor):
    def fetchall(self):
        if self._last_sql.startswith("SELECT AccountObjectID, CompanyTaxCode, AccountObjectCode, AccountObjectName"):
            return [("aid-kl", None, "KL", "Khách lẻ"), ("aid-jap", None, "JUSTADDPLANTS", "JUST ADD PLANTS"),
                    ("aid-urban", None, "URBAN-AU", "URBAN POTS AUSTRALIA PTY LTD")]
        return super().fetchall()

header = ["Ngày lập", "Số hóa đơn", "MST người mua", "Tên người mua", "Mặt hàng", "Doanh số bán chưa thuế", "Thuế GTGT", "Ký hiệu HĐ", "Ký hiệu mẫu"]
rows = [["19/09/2026", "21", "KL", "JUST ADD PLANTS", "Chậu", 576369754, 0, "C26TUE", "1"],
        ["25/09/2026", "22", "KL", "BARON LTD", "Chậu gốm", 307883584, 0, "C26TUE", "1"],
        ["26/09/2026", "23", "KL", "Urban Pots Australia PTY LTD", "Chậu", 1000000, 0, "C26TUE", "1"],
        ["27/09/2026", "24", "", "Bán cho người tiêu dùng", "Hàng lẻ", 500000, 0, "C26TUE", "1"],
        ["28/09/2026", "25", "KL", "", "Hàng lẻ", 600000, 0, "C26TUE", "1"]]
cur = Cur()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur)
ns['nhap_lieu_get'] = lambda cid, loai: {"header": header, "rows": rows}
exec(extract_fn('_misa_ghi_ban_hang'), ns)
r = ns['_misa_ghi_ban_hang'](1, "TESTDB", preview=False, ghi_de=False)
sv = {v["InvNo"]: v for v in cur.inserted["SAVoucher"]}
assert r["so_chungtu"] == 5, r
assert sv["21"]["AccountObjectID"] == "aid-jap", "Khách đã có trong Danh mục Đối tượng (mã JUSTADDPLANTS) -> gắn đúng, không dồn vào KL"
assert sv["23"]["AccountObjectID"] == "aid-urban", "Khớp theo TÊN khi mã khác quy ước"
moi = [x for x in cur.inserted.get("AccountObject", []) if x.get("AccountObjectCode") == "BARONLTD"]
assert len(moi) == 1 and moi[0]["AccountObjectName"] == "BARON LTD", cur.inserted.get("AccountObject")
assert sv["22"]["AccountObjectID"] == moi[0]["AccountObjectID"] and sv["22"]["AccountObjectName"] == "BARON LTD", sv["22"]
assert sv["24"]["AccountObjectID"] == "aid-kl" and sv["25"]["AccountObjectID"] == "aid-kl", "Người tiêu dùng / không tên -> KL"
print("PASS: khách không MST lấy mã theo tên trong Danh mục Đối tượng; chưa có thì tạo; KL chỉ cho người tiêu dùng.")
print("\nALL DONE")


# ===== Chống ghi TRÙNG: chứng từ đã ghi trước đó dù lưu MST kiểu nào ('KL', tên khách, trống) vẫn khớp với hoá đơn khách không MST =====
# Ca thật: sau khi sửa mã khách, import lại ghi THÊM 8 chứng từ trùng (doanh số MISA gấp đôi) vì khoá MST đổi.
class Cur2(Cur):
    pm_rows = []
    def fetchall(self):
        if self._last_sql.startswith("SELECT RefID, RefNoManagement, ISNULL(AccountObjectTaxCode") and "CustomField10" in self._last_sql:
            return self.pm_rows
        return super().fetchall()

for luu in ("KL", "JUST ADD PLANTS", ""):
    cur2 = Cur2(); cur2.pm_rows = [("old-ref", "BH003/T9/2026", luu, "21", "C26TUE", 1, 0, 576369754, 0)]
    ns['_misa_sql_connect'] = lambda cid, database=None, c=cur2: FakeConn(c)
    r2 = ns['_misa_ghi_ban_hang'](1, "TESTDB", preview=False, ghi_de=False, ) if False else None
    ns['nhap_lieu_get'] = lambda cid, loai: {"header": header, "rows": [rows[0]]}
    r2 = ns['_misa_ghi_ban_hang'](1, "TESTDB", preview=False, ghi_de=False)
    assert r2["so_chungtu"] == 0 and not cur2.inserted["SAVoucher"], (luu, r2)
print("PASS 2: hoá đơn khách không MST đã ghi trước đó (MST lưu 'KL'/tên/trống) -> bỏ qua, không ghi trùng.")
