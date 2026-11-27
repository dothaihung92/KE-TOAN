import os, sys, re
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""(1) Ghi đè chứng từ Mua hàng phải gỡ cả SỔ (sổ cái, công nợ, kho...) — tránh MISA báo 'Chứng từ không tồn tại do đã bị xoá, vui lòng bảo trì';
dọn sổ MỒ CÔI cũ. (2) Tờ khai XNK: NCC nước ngoài không ghi Mã số thuế. (3) Gộp KH/NCC trùng tên chỉ khác dấu chấm."""
sys.path.insert(0, _REPO_ROOT)
import server


class Cur:
    def __init__(self, ket=None):
        self.sql, self.ket, self._last = [], ket or {}, None
    def execute(self, sql, *a):
        self.sql.append((sql, a)); self._last = (sql, a); return self
    def fetchone(self):
        for k, v in self.ket.items():
            if k in self._last[0]:
                return v(self._last) if callable(v) else v
        return (0,)
    def fetchall(self):
        for k, v in self.ket.items():
            if k in self._last[0]:
                return v(self._last) if callable(v) else v
        return []


# 1) gỡ sổ theo RefID
c = Cur(); server._misa_go_so_cua_ct(c, ["r1", None, "inv1"])
xoa = [(q, a) for q, a in c.sql if q.startswith("DELETE")]
assert {q.split()[2] for q, _ in xoa} >= {"GeneralLedger", "AccountObjectLedger", "InventoryLedger", "PurchaseLedger", "CustomFieldLedger"}
assert {a[0] for _, a in xoa} == {"r1", "inv1"}
src = open(os.path.join(_REPO_ROOT, "server.py"), encoding="utf-8").read()
i = src.index("def _misa_ghi_mua_hang(cid, database, loai"); j = src.index("\ndef ", i + 10)
f = src[i:j]
assert f.count("_misa_go_so_cua_ct(cur,") == 2 and "_misa_don_so_mo_coi(cur, preview=preview)" in f
print("PASS 1: ghi đè chứng từ Mua hàng gỡ cả sổ cái/công nợ/kho/mua hàng của bản cũ.")

# 2) dọn sổ mồ côi: chỉ RefType của chứng từ mua/bán, RefID không còn trong bảng chứng từ
c = Cur({"FROM SYSRefType": lambda l: [(302,), (303,)] if l[1][0] == "PUVoucher" else [],
         "SELECT COUNT(*) FROM GeneralLedger": (5,), "SELECT COUNT(*) FROM AccountObjectLedger": (3,)})
server._misa_cot_bang_that = lambda cur, b: {"RefID": 1, "RefType": 1}
kq = server._misa_don_so_mo_coi(c, preview=True)
assert kq == {"GeneralLedger": 5, "AccountObjectLedger": 3}, kq
assert not [q for q, _ in c.sql if q.startswith("DELETE")]
c2 = Cur(c.ket); server._misa_don_so_mo_coi(c2, preview=False)
dl = [q for q, _ in c2.sql if q.startswith("DELETE")]
assert len(dl) == 2 and all("RefType IN (302,303) AND RefID NOT IN (SELECT RefID FROM PUVoucher)" in q for q in dl), dl
print("PASS 2: dọn sổ mồ côi — chỉ dòng sổ loại Mua/Bán hàng có RefID không còn chứng từ; xem trước không xoá.")

# 3) khoá MST đối chiếu / tờ khai XNK không ghi MST
assert server._kmst_dc("KING STELLA GROUP CO., LTD.") == "" and server._kmst_dc("079301031317") == "" and server._kmst_dc("") == ""
assert server._kmst_dc("0312345678") == "0312345678" and server._kmst_dc("0312345678-001") == "0312345678001"
assert '"AccountObjectTaxCode": mst_thue[:50] or None' in f and 'mst_thue = mst if _la_mst_that(mst) else ""' in f
assert "k0 = (_kmst_dc(hd_mst), k[1])" in f
print("PASS 3: tờ khai XNK — NCC nước ngoài ghi Mã số thuế TRỐNG; chống trùng/đối chiếu dùng khoá '' (khớp cả bản cũ lưu tên).")

# 4) nhóm trùng tên
rows = [("a1", "KING STELLA GROUP CO., LTD", "KING STELLA GROUP CO., LTD", None, 0),
        ("a2", "NCC00001", "KING STELLA GROUP CO., LTD.", None, 0),
        ("b1", "0300000001", "CTY ABC", "0300000001", 0), ("b2", "0300000002", "CÔNG TY ABC", "0300000002", 0),
        ("c1", "X1", "Cty XYZ", "0311111111", 0), ("c2", "X2", "CTY XYZ.", "0322222222", 0)]
c = Cur({"FROM AccountObjectLedger": lambda l: ((947,) if l[1][0] == "a2" else (1,)), "FROM AccountObject": rows})
nh = server._misa_doi_tuong_trung_ten(c)
assert len(nh) == 1 and {x["ma"] for x in nh[0]["doi_tuong"]} == {"KING STELLA GROUP CO., LTD", "NCC00001"}, nh      # XYZ: 2 MST khác nhau -> không gộp
assert {x["id"]: x["so_dong_cong_no"] for x in nh[0]["doi_tuong"]} == {"a1": 1, "a2": 947}
print("PASS 4: liệt kê nhóm KH/NCC trùng tên (chỉ khác dấu); bỏ nhóm có 2 MST thật khác nhau.")

# 5) gộp
dt = [("a1", "KING STELLA GROUP CO., LTD", "KING STELLA GROUP CO., LTD"), ("a2", "NCC00001", "KING STELLA GROUP CO., LTD.")]
ket = {"FROM AccountObject WHERE AccountObjectID IN": dt, "INFORMATION_SCHEMA": [("PUVoucher",), ("AccountObjectLedger",), ("GeneralLedger",)],
       "COUNT(*) FROM [PUVoucher]": (16,), "COUNT(*) FROM [AccountObjectLedger]": (947,), "COUNT(*) FROM [GeneralLedger]": (0,)}
server._misa_cot_bang_that = lambda cur, b: {"AccountObjectID": 1, "AccountObjectName": 1} if b == "PUVoucher" else {"AccountObjectID": 1}
c = Cur(ket); kq = server._misa_gop_doi_tuong(c, "a1", ["a2"], preview=True)
assert kq == {"AccountObjectLedger": 947, "PUVoucher": 16} and not [q for q, _ in c.sql if q.startswith("UPDATE")]
c = Cur(ket); server._misa_gop_doi_tuong(c, "a1", ["a2"], preview=False)
up = [(q, a) for q, a in c.sql if q.startswith("UPDATE")]
assert ("UPDATE [PUVoucher] SET AccountObjectID=?, AccountObjectName=? WHERE AccountObjectID IN (?)", ("a1", "KING STELLA GROUP CO., LTD", "a2")) in up, up
assert any(q.startswith("UPDATE AccountObject SET Inactive=1") and a == ("a2",) for q, a in up)
c = Cur({"FROM AccountObject WHERE AccountObjectID IN": [("a1", "A", "CTY A"), ("b1", "B", "CTY B")]})
try:
    server._misa_gop_doi_tuong(c, "a1", ["b1"], preview=True); assert False
except server.HTTPException as e:
    assert "CÙNG TÊN" in e.detail
print("PASS 5: gộp — chuyển mọi bảng có AccountObjectID sang mã giữ lại, mã bị gộp ngừng theo dõi; chỉ gộp mã cùng tên.")

# 6) Danh mục KH/NCC không tạo mã thứ 2 chỉ khác dấu chấm
assert "existing_ten.setdefault(_k_ten, ten_misa)" in src and "không tạo mã thứ 2" in src
html = open(os.path.join(_REPO_ROOT, "static", "index.html"), encoding="utf-8").read()
assert "misaGopDtMo()" in html and "/api/misa-sql/gop-doi-tuong/" in html
print("PASS 6: Danh mục KH/NCC không tạo mã trùng tên; có nút 'Gộp NCC/KH trùng tên'.")
