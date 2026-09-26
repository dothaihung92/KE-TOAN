import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Regression test: "Cấu hình API tra cứu tình trạng MST (XInvoice)" — theo yêu cầu người dùng "hãy
# chỉnh lại sao cho chỉ có phần mềm của admin mới thấy phần mềm của người dùng bình thường sẽ không
# thấy mục này và vẫn có thể dùng api mà admin đã lưu mà không cần hiện ra" — 2 endpoint GET/POST
# /api/settings/xinvoice-mst-api (xem/sửa cặp client-id/api-key) chỉ máy admin (có sẵn
# admin_private_key.pem cục bộ — cap_phep_admin.la_may_admin()) mới gọi được, máy người dùng thường
# bị từ chối (403). NHƯNG _lay_danh_sach_xinvoice_keys() — hàm _tra_cuu_trang_thai_mst() dùng để đọc
# key khi xuất Excel — KHÔNG được qua kiểm tra này, để máy người dùng thường vẫn tự động dùng được
# key admin đã cấu hình sẵn (cùng chung cơ sở dữ liệu app_settings).

_cai_dat = {}
_goc_get, _goc_set = server._get_setting, server._set_setting
server._get_setting = lambda key, default="": _cai_dat.get(key, default)
server._set_setting = lambda key, value: _cai_dat.__setitem__(key, value)

_goc_la_admin = server.cap_phep_admin.la_may_admin
try:
    # ===== 1: máy KHÔNG phải admin -> cả GET lẫn POST đều bị từ chối (403), không xem/sửa được. =====
    server.cap_phep_admin.la_may_admin = lambda: False
    loi = None
    try:
        server.get_xinvoice_mst_api()
    except server.HTTPException as e:
        loi = e
    assert loi is not None and loi.status_code == 403, f"got {loi!r}"

    loi = None
    try:
        server.set_xinvoice_mst_api({"keys": [{"client_id": "c1", "api_key": "k1"}]})
    except server.HTTPException as e:
        loi = e
    assert loi is not None and loi.status_code == 403, f"got {loi!r}"
    print("PASS 1: máy KHÔNG phải admin -> GET/POST cấu hình XInvoice đều bị từ chối (403).")

    # ===== 2: máy LÀ admin -> xem/sửa được bình thường. =====
    server.cap_phep_admin.la_may_admin = lambda: True
    kq = server.set_xinvoice_mst_api({"keys": [{"client_id": "cA", "api_key": "kA"},
                                               {"client_id": "cB", "api_key": "kB"}]})
    assert kq["ok"] is True and len(kq["keys"]) == 2, kq
    kq2 = server.get_xinvoice_mst_api()
    assert kq2["keys"] == kq["keys"], kq2
    print("PASS 2: máy admin xem/sửa cấu hình XInvoice bình thường.")

    # ===== 3 (QUAN TRỌNG — đúng ý người dùng "vẫn có thể dùng api mà admin đã lưu"): sau khi ADMIN
    # đã lưu key ở bước 2, chuyển máy về KHÔNG PHẢI admin -> _lay_danh_sach_xinvoice_keys() (hàm nội
    # bộ _tra_cuu_trang_thai_mst() dùng khi xuất Excel) VẪN đọc được đủ 2 key đó, KHÔNG bị chặn bởi
    # kiểm tra la_may_admin(). =====
    server.cap_phep_admin.la_may_admin = lambda: False
    ds = server._lay_danh_sach_xinvoice_keys()
    assert len(ds) == 2 and ds[0]["client_id"] == "cA" and ds[1]["client_id"] == "cB", ds
    print("PASS 3: máy người dùng thường (không phải admin) vẫn tự động dùng được key admin đã lưu "
          "khi xuất Excel — chỉ không xem/sửa được qua giao diện.")
finally:
    server.cap_phep_admin.la_may_admin = _goc_la_admin
    server._get_setting, server._set_setting = _goc_get, _goc_set

# ===== 4: giao diện — nút "Cấu hình API tra cứu tình trạng MST (XInvoice)" ẩn mặc định (chỉ hiện khi
# JS xác nhận la_admin qua adminKiemTraQuyen(), giống nút "Quản lý user" đã có sẵn); tính năng "Soạn
# nháp hoá đơn nhanh" đã bị xoá hẳn (nút, modal, các hàm hdn*). =====
html = open(os.path.join(_REPO_ROOT, "static", "index.html"), encoding="utf-8").read()
assert 'id="btnXInvoiceCauHinh"' in html, "Phải còn nút cấu hình XInvoice (chỉ ẩn mặc định, không xoá hẳn)."
i_btn = html.index('id="btnXInvoiceCauHinh"')
dong_nut = html[html.rindex("<button", 0, i_btn):html.index(">", i_btn) + 1]
assert "display:none" in dong_nut, f"Nút cấu hình XInvoice phải ẩn mặc định — got {dong_nut!r}"

assert "btnXInvoiceCauHinh" in html[html.index("async function adminKiemTraQuyen("):
                                     html.index("}", html.index("async function adminKiemTraQuyen(")) + 400], (
    "adminKiemTraQuyen() phải hiện/ẩn nút cấu hình XInvoice theo đúng quyền admin, giống nút "
    "'Quản lý user' đã có sẵn.")

for tu_khoa in ("hdnModal", "moHDNModal", "hdnXuatExcel", "hdnPhanTichPaste", "Soạn nháp hoá đơn"):
    assert tu_khoa not in html, f"Tính năng 'Soạn nháp hoá đơn nhanh' phải đã xoá hẳn — vẫn còn {tu_khoa!r}"

src = open(os.path.join(_REPO_ROOT, "server.py"), encoding="utf-8").read()
for tu_khoa in ("/api/hoa-don-nhanh/doc-excel", "/api/hoa-don-nhanh/xuat-excel", "_doc_hoa_don_nhanh_tu_excel"):
    assert tu_khoa not in src, f"Backend 'Soạn nháp hoá đơn nhanh' phải đã xoá hẳn — vẫn còn {tu_khoa!r}"
print("PASS 4: nút cấu hình XInvoice ẩn mặc định (JS bật lại đúng khi là máy admin); tính năng "
      "'Soạn nháp hoá đơn nhanh' đã xoá hẳn cả giao diện lẫn backend.")

print("\nALL DONE")
