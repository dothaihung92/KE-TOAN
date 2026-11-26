import os, sys, io, zipfile, tempfile
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Đối chiếu tờ khai 01/GTGT: file đã tải từ Thuế (zip/xml HTKK) <-> tờ khai trong MISA (TADeclaration*), từng kỳ."""
sys.path.insert(0, _REPO_ROOT)
import server


def xml(kieu, ky, so_lan, ct):
    thes = "".join(f"<{k}>{v}</{k}>" for k, v in ct.items())
    return (f'<?xml version="1.0" encoding="UTF-8"?><HSoKhaiThue xmlns="http://kekhaithue.gdt.gov.vn/TKhaiThue"><TTinChung><TTinTKhaiThue>'
            f'<TKhaiThue><maTKhai>842</maTKhai><kieuKy>{kieu}</kieuKy><kyKKhai>{ky}</kyKKhai><soLan>{so_lan}</soLan></TKhaiThue></TTinTKhaiThue></TTinChung>'
            f'<CTieuTKhaiChinh>{thes}</CTieuTKhaiChinh></HSoKhaiThue>').encode("utf-8")


CT1 = {"ct22": 0, "ct23": 1000000000, "ct24": 80000000, "ct25": 80000000, "ct40": 5000000, "ct43": 0}
d = tempfile.mkdtemp()
with zipfile.ZipFile(os.path.join(d, "01GTGT_QUY1.2026-0317489936.zip"), "w") as z:
    z.writestr("tkhai.xml", xml("Q", "1/2026", 0, CT1))
    z.writestr("ghichu.txt", "x")
open(os.path.join(d, "01GTGT_QUY2.2026-0317489936.xml"), "wb").write(xml("Q", "2/2026", 0, dict(CT1, ct23=2000000000)))
# bổ sung lần 1 của quý 2 (số lần cao hơn) phải được ưu tiên
open(os.path.join(d, "01GTGT_QUY2.2026-0317489936_L1.xml"), "wb").write(xml("Q", "2/2026", 1, dict(CT1, ct23=2100000000)))
open(os.path.join(d, "01GTGT_QUY2.2026-0317489936_ThongBao.xml"), "wb").write(b"<x>thong bao</x>")          # thông báo -> bỏ qua
open(os.path.join(d, "khac.xml"), "wb").write(b"<a><ct99>1</ct99></a>")                                      # không phải tờ khai GTGT
thue, so_doc, loi = server._tk_vat_doc_thu_muc(d)
assert so_doc == 3, so_doc
assert set(thue) == {("Q", 2026, 1), ("Q", 2026, 2)}, thue.keys()
assert thue[("Q", 2026, 2)]["so_lan"] == 1 and thue[("Q", 2026, 2)]["ct"]["ct23"] == 2100000000      # lấy bản bổ sung mới nhất
assert thue[("Q", 2026, 1)]["ct"]["ct40"] == 5000000
print("PASS 1: đọc tờ khai 01/GTGT đã tải (zip/xml, có namespace), chọn lần bổ sung cao nhất, bỏ thông báo/file không phải tờ khai.")

assert server._tk_vat_ky_tu_chuoi("Quý 2 năm 2025") == ("Q", 2025, 2)
assert server._tk_vat_ky_tu_chuoi("Tháng 3/2026") == ("M", 2026, 3) and server._tk_vat_ky_tu_chuoi("QUY1.2026") == ("Q", 2026, 1)
assert server._tk_vat_ky_tu_chuoi("???") is None
# kỳ tháng trong XML
r = server._tk_vat_doc_xml(xml("M", "03/2026", 0, CT1), "")
assert r["ky"] == ("M", 2026, 3)
print("PASS 2: nhận diện kỳ quý/tháng từ XML và từ chuỗi MISA/tên file.")

lech = server._tk_vat_so_sanh(CT1, dict(CT1, ct23=999999000, ct25=80000001, ct40=4000000))
assert [x[0] for x in lech] == ["ct23", "ct40"], lech            # ct25 chênh 1đ -> bỏ qua làm tròn
assert lech[0][3] == -1000 and lech[1][3] == -1000000
assert server._tk_vat_so_sanh(CT1, dict(CT1)) == []
assert [x[0] for x in server._tk_vat_so_sanh({"ct23": 5}, {})] == ["ct23"]                      # thiếu phía MISA = 0
print("PASS 3: so sánh chỉ tiêu: lệch > 1đ mới báo, thiếu 1 phía coi là 0.")


class Cur:
    def __init__(self, hdr, det): self.hdr, self.det, self.q = hdr, det, None
    def execute(self, sql, *a):
        self.q = (sql, a); return self
    def fetchall(self):
        sql, a = self.q
        return self.hdr if "FROM TADeclaration " in sql else self.det[a[0]]


cur = Cur([("r1", "Quý 1 năm 2026", 1), ("r2", "Quý 2 năm 2026", 2), ("r3", "Quý 3 năm 2026", 3)],
          {"r1": [("Item22", 0), ("Item23", 1000000000), ("Item24", 80000000), ("Item25", 80000000), ("Item40", 5000000), ("Item43", 0)],
           "r2": [("Item23", 1500000000), ("Item24", 80000000), ("Item25", 80000000), ("Item22", 0), ("Item40", 5000000)],
           "r3": [("Item23", 7)]})
misa = server._tk_vat_doc_misa(cur)
assert misa[("Q", 2026, 1)]["ct"]["ct40"] == 5000000 and ("Q", 2026, 3) in misa
print("PASS 4: đọc tờ khai MISA (TADeclaration/TADeclarationDetail) theo kỳ.")

# tổng hợp theo kỳ qua hàm chính (giả lập thư mục + MISA)
server._dvc_save_folder = lambda cid: d
server._misa_sql_connect = lambda cid, database=None, **k: type("C", (), {"cursor": lambda self: cur, "close": lambda self: None})()
kq = server._tk_vat_doi_chieu(1, "db")
tt = {t["ky"]: t["trang_thai"] for t in kq["to_khai"]}
assert tt == {"Quý 1/2026": "KHỚP", "Quý 2/2026": "LỆCH", "Quý 3/2026": "CHƯA CÓ FILE TỜ KHAI TẢI TỪ THUẾ"}, tt
q2 = [t for t in kq["to_khai"] if t["ky"] == "Quý 2/2026"][0]
assert q2["lech"][0]["ct"] == "ct23" and q2["lech"][0]["chenh"] == 1500000000 - 2100000000 and q2["so_lan"] == 1
print("PASS 5: kết quả từng kỳ: khớp / lệch (kèm chênh) / thiếu file tải về.")
html = open(os.path.join(_REPO_ROOT, "static", "index.html"), encoding="utf-8").read()
assert "misaDoiChieuToKhaiVat()" in html and "Đối chiếu tờ khai VAT (MISA ↔ Thuế)" in html
print("PASS 6: có nút 'Đối chiếu tờ khai VAT' ở hộp Import tự động.")
