import os, sys, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Tra cứu hàng loạt / kết xuất: "Thư mục lưu file kết xuất" dán bằng "Copy as path" của Windows có dấu ngoặc kép bao ngoài -> trước đây không tạo được
# thư mục, file lặng lẽ rơi ra Desktop. Nay bỏ ngoặc kép / khoảng trắng; nhật ký hàng loạt nêu rõ nơi lưu hoặc lý do ra Desktop.
goc = tempfile.mkdtemp()
try:
    for dang in (f'"{goc}"', f"  {goc}  ", f"“{goc}”", f"'{goc}'"):
        d = server._thu_muc_ket_xuat_ky(dang, "01/07/2026", "30/09/2026")
        assert d == os.path.join(goc, "2026", "QUY 3") and os.path.isdir(d), (dang, d)
    assert server._thu_muc_ket_xuat_ky('""', "01/07/2026", "30/09/2026") is None
    assert server._chuan_duong_dan('"D:\\Ke toan"') == "D:\\Ke toan"
finally:
    shutil.rmtree(goc, ignore_errors=True)
src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py"), encoding="utf-8").read()
assert "✓ Đã kết xuất Excel vào: " in src and "CHƯA đặt 'Thư mục lưu file kết xuất'" in src and "XML GTGT KHÔNG lưu được" in src and "XML TNCN KHÔNG lưu được" in src
assert src.count("_chuan_duong_dan(data.get(\"export_dir\"))") == 2, "lưu công ty: chuẩn hoá đường dẫn"
print("PASS")
