import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Đã BỎ chức năng "Import dữ liệu đã kiểm tra" (theo yêu cầu): không còn nút, endpoint, banner; số liệu lấy từ bảng kê/hóa đơn tra cứu.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html = open(os.path.join(ROOT, "static", "index.html"), encoding="utf-8").read()
src = open(os.path.join(ROOT, "server.py"), encoding="utf-8").read()
for ten in ("Import dữ liệu đã kiểm tra</button>", 'id="importFile"', "function importExcel", "boImport", "/api/imported/", "impBanner", "/api/import-excel"):
    assert ten not in html, ten
for ten in ('"/api/import-excel/{cid}"', "async def import_excel", '"/api/imported/{cid}"'):
    assert ten not in src, ten
assert server._get_imported(1, "Q3/2026") is None and server._get_imported(1) is None
paths = {getattr(r, "path", "") for r in server.app.routes}
assert "/api/import-excel/{cid}" not in paths and "/api/imported/{cid}" not in paths
# các nút còn lại vẫn có
for giu in ("Xuất Excel tổng hợp", "Import tờ khai nhập khẩu", "Xem/Xoá TK nhập khẩu đã import", "Tạm tính thuế VAT"):
    assert giu in html, giu
print("PASS: bỏ nút/endpoint/banner Import dữ liệu đã kiểm tra; _get_imported luôn None; các nút khác giữ nguyên.")
