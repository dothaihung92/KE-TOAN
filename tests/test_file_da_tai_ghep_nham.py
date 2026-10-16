import os, sys, sqlite3, tempfile, zipfile, io
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Ca thật: máy có NHIỀU file hoá đơn đã tải -> mỗi lần tra cứu ra số hoá đơn khác nhau; xoá hết file đã tải rồi
# tải lại thì hết lỗi. Nguyên nhân: file đã tải được ghép với hoá đơn CHỈ theo TÊN FILE (ký hiệu + số, MST cắt 10
# số, hoặc tên file cũ không có MST) -> ghép NHẦM file của hoá đơn khác -> "tự sửa ngày lập" theo file sai đẩy
# hoá đơn ra ngoài kỳ (mất khỏi bảng kê) và đọc nhầm dòng hàng. Nay chỉ dùng file khi NỘI DUNG file đúng
# (ký hiệu + số + MST người bán).


def xml(kh, so, mst, ngay):
    return (f"<HDon><DLHDon><TTChung><KHMSHDon>1</KHMSHDon><KHHDon>{kh}</KHHDon><SHDon>{so}</SHDon>"
            f"<NLap>{ngay}</NLap></TTChung><NDHDon><NBan><Ten>A</Ten><MST>{mst}</MST></NBan>"
            f"<DSHHDVu><HHDVu><STT>1</STT><THHDVu>Hàng</THHDVu><ThTien>100</ThTien></HHDVu></DSHHDVu>"
            f"</NDHDon></DLHDon></HDon>").encode()


d = tempfile.mkdtemp()
# file tên KIỂU CŨ (không MST) "C26MCV_2244.xml" nhưng là hoá đơn của NGƯỜI BÁN KHÁC, ngày 15/12/2026
sai = os.path.join(d, "C26MCV_2244.xml"); open(sai, "wb").write(xml("C26MCV", "2244", "0311111111", "2026-12-15"))
# file đúng (zip) của hoá đơn 3400738220
dung = os.path.join(d, "C26MCV_2244_3400738220.zip")
b = io.BytesIO(); zipfile.ZipFile(b, "w").writestr("invoice.xml", xml("C26MCV", "00002244", "3400738220", "2026-08-11")); open(dung, "wb").write(b.getvalue())
# chi nhánh: MST cắt 10 số trùng công ty mẹ
cn = os.path.join(d, "K26TAA_5_0302391670-031.xml"); open(cn, "wb").write(xml("K26TAA", "5", "0302391670-031", "2026-07-01"))

assert server._file_khop_hoa_don(dung, "C26MCV", "2244", "3400738220")
assert not server._file_khop_hoa_don(sai, "C26MCV", "2244", "3400738220"), "file của người bán khác"
assert not server._file_khop_hoa_don(sai, "C26MCV", "2245", "0311111111"), "khác số hoá đơn"
assert server._file_khop_hoa_don(cn, "K26TAA", "5", "0302391670-031")
assert not server._file_khop_hoa_don(cn, "K26TAA", "5", "0302391670"), "công ty mẹ khác chi nhánh"
assert not server._file_khop_hoa_don(os.path.join(d, "khong_co.xml"), "C26MCV", "2244", "3400738220")
print("PASS 1: chỉ nhận file khi nội dung đúng ký hiệu + số + MST người bán (không tin tên file).")

# 2) tự sửa ngày lập: file của hoá đơn khác -> KHÔNG sửa; file đúng -> vẫn sửa như cũ
conn = sqlite3.connect(":memory:", check_same_thread=False); conn.row_factory = sqlite3.Row
conn.execute("CREATE TABLE invoices (id INTEGER PRIMARY KEY, company_id, khmshdon, khhdon, shdon, loai, he_thong, tdlap, nbmst)")
conn.execute("INSERT INTO invoices VALUES (1, 5, '1', 'C26MCV', '2244', 'purchase', 'sco-query', '2026-08-11T00:00:00', '3400738220')")
class KhongDong:
    def __init__(self, c): self.c = c
    def execute(self, *a): return self.c.execute(*a)
    def commit(self): self.c.commit()
    def close(self): pass
server.db = lambda: KhongDong(conn)
inv = {"khmshdon": "1", "khhdon": "C26MCV", "shdon": "2244", "nbmst": "3400738220", "tdlap": "2026-08-11T00:00:00"}
server._sua_ngay_lap_tu_xml(5, inv, "purchase", "sco-query", open(sai, "rb").read())
assert conn.execute("SELECT tdlap FROM invoices").fetchone()[0] == "2026-08-11T00:00:00", "không được dời ngày theo file sai"
server._sua_ngay_lap_tu_xml(5, inv, "purchase", "sco-query", xml("C26MCV", "2244", "3400738220", "2026-08-12"))
assert conn.execute("SELECT tdlap FROM invoices").fetchone()[0].startswith("2026-08-12")
print("PASS 2: 'tự sửa ngày lập' bỏ qua file của hoá đơn khác; file đúng vẫn sửa như cũ.")

# 3) mọi chỗ ghép file theo tên đều qua bước kiểm tra nội dung
src = open(os.path.join(os.path.dirname(server.__file__), "server.py"), encoding="utf-8").read()
assert "fp if fp and _file_khop_hoa_don(fp, r[\"khhdon\"], r[\"shdon\"], r[\"nbmst\"]) else None" in src
assert "co_file = find_invoice_file(r) is not None" in src
assert "if fpath and not _file_khop_hoa_don(fpath, khhdon, shdon, nbmst):" in src
assert src.count("_file_index.get((khh, sho, mst)) or _file_index_2.get((khh, sho))") == 1, "chỉ còn trong find_invoice_file"
print("PASS 3: tra cứu (bỏ qua file đã có) và xuất Excel (đọc file/sửa ngày) đều kiểm tra nội dung file.")
print("ALL DONE")
