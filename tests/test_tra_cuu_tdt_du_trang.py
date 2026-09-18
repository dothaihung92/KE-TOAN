import os
import re

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test cho _JS_SEARCH_TDT (nguồn "thuedientu" — dùng cho MỌI tờ
# khai nộp TRƯỚC 01/07/2025, xem _nguon_tra_cuu_theo_ky) — người dùng báo
# thật: tra cứu "Tùy chọn ngày" 01/01/2024-31/12/2025 cho công ty đã hoạt
# động liên tục từ TRƯỚC 2024, đối chiếu file Excel "TraCuuToKhai_..." xuất
# ra chỉ thấy 15 dòng, THIẾU HẲN tờ khai Quý 1-2/2024 (GTGT/TNCN chỉ thấy
# từ Quý 3-4/2024 trở đi) dù công ty xác nhận có nộp đầy đủ.
#
# Nguyên nhân: _JS_SEARCH_TDT gửi page/size RỖNG ('') thay vì số thật, khác
# hẳn _JS_SEARCH (nguồn "dvc") đã cẩn thận truyền page:0, size:200 để chắc
# lấy đủ 1 trang lớn — page/size rỗng khiến cổng dùng cỡ trang MẶC ĐỊNH nhỏ
# (không có vòng lặp lấy thêm trang sau), làm rớt mất các hồ sơ CŨ NHẤT khi
# công ty có nhiều hồ sơ hơn cỡ trang mặc định trong khoảng ngày tìm — đúng
# khớp hiện tượng: tờ khai CŨ (Quý 1-2/2024) mất, tờ khai MỚI hơn (Quý
# 3/2024 trở đi) vẫn thấy đủ.


def _lay_khoi_js(ten_bien):
    mo_dau = ten_bien + ' = r"""'
    idx = src.index(mo_dau)
    i = idx + len(mo_dau)
    j = src.index('"""', i)
    return src[i:j]


khoi_tdt = _lay_khoi_js('_JS_SEARCH_TDT')
khoi_dvc = _lay_khoi_js('_JS_SEARCH')

# ===== Test 1 (QUAN TRỌNG — đúng ca thật người dùng báo): _JS_SEARCH_TDT
# KHÔNG được để page/size rỗng — phải truyền số thật (page:0, size lớn) như
# _JS_SEARCH đã làm, để không bị cổng áp cỡ trang mặc định nhỏ làm rớt mất
# hồ sơ cũ. =====
assert "page:''" not in khoi_tdt and 'page: ""' not in khoi_tdt, (
    "_JS_SEARCH_TDT (nguồn 'thuedientu', chứa tờ khai TRƯỚC 01/07/2025 — đúng giai đoạn Quý 1-2/2024 "
    "bị thiếu trong ca thật người dùng báo) KHÔNG được để 'page' rỗng — phải truyền số thật (vd page:0) "
    "để tránh cổng áp phân trang mặc định làm rớt mất hồ sơ cũ.")
assert "size:''" not in khoi_tdt and 'size: ""' not in khoi_tdt, (
    "_JS_SEARCH_TDT KHÔNG được để 'size' rỗng — phải truyền số thật đủ lớn (vd size:200, giống hệt "
    "_JS_SEARCH) để lấy đủ 1 trang lớn, không bị cắt bớt hồ sơ cũ nhất khi công ty có nhiều hồ sơ hơn cỡ "
    "trang mặc định của cổng trong khoảng ngày tìm.")
m = re.search(r"size\s*:\s*(\d+)", khoi_tdt)
assert m, f"_JS_SEARCH_TDT phải truyền 'size' là 1 SỐ thật — khối JS: {khoi_tdt}"
assert int(m.group(1)) >= 200, (
    f"'size' của _JS_SEARCH_TDT nên đủ lớn (>=200, giống hệt _JS_SEARCH) để chắc lấy đủ mọi hồ sơ trong "
    f"khoảng ngày tìm, không chỉ vừa đủ để hết lỗi cú pháp — got size={m.group(1)}")
print("PASS 1: _JS_SEARCH_TDT truyền page/size là SỐ THẬT (không rỗng), đủ lớn để không bị cổng áp phân "
      "trang mặc định làm rớt mất hồ sơ cũ (Quý 1-2/2024) — đúng ca thật người dùng báo.")

# ===== Test 2 (không hồi quy — nhất quán): _JS_SEARCH (nguồn "dvc") vẫn
# giữ nguyên page:0, size:200 như trước — không bị ảnh hưởng bởi sửa đổi
# trên. =====
assert "page:0" in khoi_dvc and "size:200" in khoi_dvc, (
    f"_JS_SEARCH (nguồn 'dvc') phải vẫn giữ nguyên page:0, size:200 như trước — khối JS: {khoi_dvc}")
print("PASS 2: _JS_SEARCH (nguồn 'dvc') không bị ảnh hưởng, vẫn giữ page:0, size:200 như trước.")

print("\nALL DONE")
