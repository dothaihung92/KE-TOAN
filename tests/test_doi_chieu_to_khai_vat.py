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

# ===== Khoảng quý + tự tải khi thiếu =====
assert server._tk_vat_ds_quy(2026, 1, 2026, 3) == [(2026, 1), (2026, 2), (2026, 3)]
assert server._tk_vat_ds_quy(2025, 4, 2026, 2) == [(2025, 4), (2026, 1), (2026, 2)]
assert server._tk_vat_ds_quy(2026, 3, 2026, 1) == [] and server._tk_vat_ds_quy(2026, 0, 2026, 1) == []
assert server._tk_vat_ngay_quy(2026, 3) == ("01/07/2026", "30/09/2026") and server._tk_vat_ngay_quy(2026, 1) == ("01/01/2026", "31/03/2026")
th = server.misa_sql_to_khai_vat_thieu(1, tu_quy=1, tu_nam=2026, den_quy=4, den_nam=2026)        # thư mục giả lập có Quý 1, 2
assert th["co"] == ["Quý 1/2026", "Quý 2/2026"] and th["thieu"] == ["Quý 3/2026", "Quý 4/2026"], th
assert th["tu_ngay_tai"] == "01/07/2026" and th["den_ngay_tai"] == "31/12/2026" and th["ky_label"] == "Quý 3/2026 - Quý 4/2026", th
assert "thieu" in server.misa_sql_to_khai_vat_thieu(1, 3, 2026, 3, 2026) and server.misa_sql_to_khai_vat_thieu(1, 1, 2026, 1, 2026)["thieu"] == []
try:
    server.misa_sql_to_khai_vat_thieu(1, tu_quy=3, tu_nam=2026, den_quy=1, den_nam=2026); assert False
except server.HTTPException:
    pass
print("PASS 7: dò thư mục theo khoảng quý, liệt kê quý thiếu + khoảng ngày để tự tải.")

# đối chiếu chỉ trong khoảng + quý không có ở cả 2 phía vẫn được liệt kê
kq = server._tk_vat_doi_chieu(1, "db", [(2026, 1), (2026, 2), (2026, 4)])
tt = {t["ky"]: t["trang_thai"] for t in kq["to_khai"]}
assert tt == {"Quý 1/2026": "KHỚP", "Quý 2/2026": "LỆCH", "Quý 4/2026": "CHƯA CÓ TỜ KHAI (MISA lẫn file tải về)"}, tt       # Quý 3 (ngoài khoảng) không hiện
print("PASS 8: chỉ hiện các quý trong khoảng chọn.")
html = open(os.path.join(_REPO_ROOT, "static", "index.html"), encoding="utf-8").read()
assert "async function misaTkVatChay()" in html and "/api/dvc/batch'" in html and "to-khai-vat-thieu" in html and "tu_ngay:th.tu_ngay_tai" in html
print("PASS 9: giao diện: chọn khoảng quý -> dò thư mục -> tự tải (dvc/batch) -> đối chiếu.")

# ===== Tờ khai TNCN/TNDN cũng có ct22..ct43 -> không được đọc nhầm thành 01/GTGT (ca thật: 05KK-TNCN_QUY1.2026-*.zip) =====
def xml_ten(ten, ma, ky, ct):
    return xml("Q", ky, 0, ct).replace(b"<maTKhai>842</maTKhai>", f"<maTKhai>{ma}</maTKhai><tenTKhai>{ten}</tenTKhai>".encode("utf-8"))
assert server._tk_vat_doc_xml(xml_ten("TỜ KHAI KHẤU TRỪ THUẾ THU NHẬP CÁ NHÂN (Mẫu số 05/KK-TNCN)", "864", "1/2026", CT1), "x.xml") is None
assert server._tk_vat_doc_xml(xml_ten("TỜ KHAI THUẾ GIÁ TRỊ GIA TĂNG (TT80/2021)", "842", "1/2026", CT1), "x.xml")["ky"] == ("Q", 2026, 1)
assert server._tk_vat_doc_xml(xml("Q", "1/2026", 0, CT1).replace(b"842", b"864"), "x.xml") is None            # không có tên, mã khác 842
d2 = tempfile.mkdtemp()
with zipfile.ZipFile(os.path.join(d2, "05KK-TNCN_QUY1.2026-0313358428_2.zip"), "w") as z:
    z.writestr("a.xml", xml("Q", "1/2026", 0, CT1))                                    # tên file là TNCN -> bỏ qua dù XML trông như GTGT
with zipfile.ZipFile(os.path.join(d2, "01GTGT_QUY1.2026-0313358428_2.zip"), "w") as z:
    z.writestr("tk.xml", xml_ten("TỜ KHAI THUẾ GIÁ TRỊ GIA TĂNG (TT80/2021)", "842", "1/2026", dict(CT1, ct23=123456)))
open(os.path.join(d2, "01GTGT_QUY1.2026-0313358428_TB_TIEPNHAN.xml"), "wb").write(b"<TBao><ct22>1</ct22></TBao>")
th2, n2, _ = server._tk_vat_doc_thu_muc(d2)
assert n2 == 1 and list(th2) == [("Q", 2026, 1)] and th2[("Q", 2026, 1)]["ct"]["ct23"] == 123456 and "01GTGT" in th2[("Q", 2026, 1)]["file"], th2
print("PASS 10: tờ khai TNCN/TNDN và thông báo tiếp nhận không bị đọc nhầm thành 01/GTGT.")
