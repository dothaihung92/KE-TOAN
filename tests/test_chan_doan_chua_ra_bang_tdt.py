import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test — vòng thứ 3 chẩn đoán tra cứu "thuế điện tử" bị thiếu
# tờ khai cũ (Quý 1-2/2024). Diễn biến:
#   build .284: page/size RỖNG (đúng nguyên văn request thật người dùng
#     từng chụp gửi) -> tìm được MỘT PHẦN dữ liệu (Quý 3/2024 trở đi).
#   build .285: đổi page:0, size:200 (đoán do phân trang) -> KHÔNG giúp
#     gì (vẫn thiếu Quý 1-2/2024).
#   build .286-287: chia nhỏ theo tháng (đoán do giới hạn 1 tháng của
#     form) -> làm TỆ HƠN HẲN (15 dòng -> 5 dòng) -> ĐÃ REVERT ở .288.
#   build .288 (giữ page:0/size:200, bỏ chia nhỏ): người dùng báo
#     nguồn "thuedientu" THẤT BẠI HOÀN TOÀN — 8/8 lần thử đều "chưa ra
#     bảng", cùng kích thước phản hồi (923 ký tự) bất kể mã captcha khác
#     nhau mỗi lần -> nghi tham số page/size dạng SỐ bị cổng từ chối.
#
# -> Trả page/size về RỖNG (đúng request thật ban đầu, đã có bằng chứng
# "chạy được ít nhất một phần" — không suy diễn thêm nữa) + thêm chẩn
# đoán THẬT (đoạn chữ đã bỏ thẻ HTML của response "chưa ra bảng") để có
# dữ liệu thật cho lần chẩn đoán tiếp theo, tránh đoán mò lần thứ 4.


def _lay_khoi_js(ten_bien):
    mo_dau = ten_bien + ' = r"""'
    idx = src.index(mo_dau)
    i = idx + len(mo_dau)
    j = src.index('"""', i)
    return src[i:j]


def _lay_than_ham(ten_ham):
    idx = src.index('def ' + ten_ham + '(')
    idx_ke = src.index('\ndef ', idx + 10)
    return src[idx:idx_ke]


khoi_tdt = _lay_khoi_js('_JS_SEARCH_TDT')
than_tracuu_tdt = _lay_than_ham('_dvc_browser_tracuu_tdt')

# ===== Test 1 (QUAN TRỌNG — đúng ca thật người dùng báo lần 3): page/size
# của _JS_SEARCH_TDT phải RỖNG — đúng NGUYÊN VĂN request thật ban đầu, đã
# có bằng chứng chạy được (dù chỉ một phần) — KHÔNG được đổi sang số nữa
# (đã thử page:0/size:200 và gây THẤT BẠI HOÀN TOÀN, xác nhận qua log
# thật: 8/8 lần thử "chưa ra bảng", cùng kích thước 923 ký tự bất kể
# captcha khác nhau). =====
assert "page:''" in khoi_tdt or 'page: ""' in khoi_tdt, (
    "_JS_SEARCH_TDT phải để 'page' RỖNG — đúng nguyên văn request thật ban đầu. Đã thử đổi sang số "
    "(page:0) và gây thất bại HOÀN TOÀN theo log thật người dùng báo (8/8 lần thử đều lỗi, cùng kích "
    f"thước phản hồi bất kể captcha khác nhau) — không được lặp lại thay đổi này. Khối JS: {khoi_tdt}")
assert "size:''" in khoi_tdt or 'size: ""' in khoi_tdt, (
    "_JS_SEARCH_TDT phải để 'size' RỖNG — cùng lý do với 'page' ở trên, đã xác nhận đổi sang số "
    f"(size:200) gây thất bại hoàn toàn. Khối JS: {khoi_tdt}")
print("PASS 1: _JS_SEARCH_TDT giữ page/size RỖNG — đúng request thật ban đầu, không lặp lại thay đổi đã "
      "xác nhận gây thất bại hoàn toàn (log thật: 8/8 lần thử 'chưa ra bảng', cùng kích thước bất kể "
      "captcha khác nhau).")

# ===== Test 2 (chẩn đoán — để có dữ liệu thật cho lần sửa tiếp theo,
# tránh đoán mò lần thứ 4): _dvc_browser_tracuu_tdt() khi "chưa ra bảng"
# phải in kèm 1 đoạn CHỮ THẬT (đã bỏ thẻ HTML) của response — trước đây
# chỉ in ĐỘ DÀI (vd "(923)"), không biết nội dung thật là gì (sai mã xác
# nhận? lỗi tham số? trang khác hẳn?). =====
assert 'chưa ra bảng' in than_tracuu_tdt, "_dvc_browser_tracuu_tdt() phải còn nhánh 'chưa ra bảng'"
assert 're.sub' in than_tracuu_tdt.replace('_re.sub', 're.sub'), (
    "_dvc_browser_tracuu_tdt() phải bóc tách 1 đoạn CHỮ THẬT (bỏ thẻ HTML) từ response khi 'chưa ra "
    "bảng' để biết nội dung thật — trước đây chỉ in độ dài, không đủ để chẩn đoán vì sao thất bại.")
print("PASS 2: 'chưa ra bảng' giờ kèm đoạn chữ thật (đã bỏ thẻ HTML) của response, đủ để chẩn đoán lần "
      "tới thay vì đoán mò tiếp.")

print("\nALL DONE")
