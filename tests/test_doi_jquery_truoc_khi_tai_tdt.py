import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test (nguồn) — người dùng báo log thật: sau khi tra cứu
# "thuế điện tử" được sửa tìm ra ĐỦ dữ liệu hơn hẳn (29 dòng, đủ cả Quý
# 1-2/2024), bước TẢI FILE lại lỗi 22/22 hồ sơ y hệt nhau:
#   {'err': 'ReferenceError: $ is not defined', 'ok': False}
# Nguyên nhân: _dvc_browser_download_tdt()/_dvc_browser_thongbao() gọi
# _dvc_wait_jquery() (chờ jQuery nạp xong ở trang chi tiết hồ sơ) NHƯNG
# KHÔNG kiểm tra kết quả chờ — nếu jQuery chưa kịp nạp (hết giờ chờ) vẫn
# cứ chạy tiếp execute_async_script() dùng $.ajax(...), gây lỗi mù mờ
# "$ is not defined" thay vì thông báo rõ nguyên nhân.


def _lay_than_ham(ten_ham):
    idx = src.index('def ' + ten_ham + '(')
    idx_ke = src.index('\ndef ', idx + 10)
    return src[idx:idx_ke]


than_download_tdt = _lay_than_ham('_dvc_browser_download_tdt')
than_thongbao = _lay_than_ham('_dvc_browser_thongbao')

# ===== Test 1 (QUAN TRỌNG — đúng ca thật người dùng báo): cả 2 hàm gọi
# trang chi tiết hồ sơ nguồn "thuế điện tử" phải KIỂM TRA kết quả
# _dvc_wait_jquery() — không được gọi rồi bỏ qua kết quả trả về. =====
for ten, than in (('_dvc_browser_download_tdt', than_download_tdt), ('_dvc_browser_thongbao', than_thongbao)):
    assert "_dvc_wait_jquery(drv, 10)" in than, f"{ten} phải gọi _dvc_wait_jquery(drv, 10)"
    # Không được để dòng gọi đứng riêng lẻ (không gán/không kiểm tra) — phải
    # gán vào 1 biến để sau đó CÓ kiểm tra (vd "if not da_co_jquery:").
    assert "da_co_jquery = _dvc_wait_jquery(drv, 10)" in than, (
        f"{ten} phải GÁN kết quả _dvc_wait_jquery() vào biến rồi kiểm tra — trước đây gọi xong bỏ qua "
        f"luôn kết quả, nếu jQuery chưa kịp nạp vẫn chạy tiếp gây lỗi mù mờ 'ReferenceError: $ is not "
        f"defined' (đúng log thật người dùng báo: 22/22 hồ sơ lỗi y hệt nhau).")
    assert "da_co_jquery" in than and ("if not da_co_jquery" in than or "if da_co_jquery" in than), (
        f"{ten} phải THỰC SỰ dùng kết quả _dvc_wait_jquery() để quyết định thử lại/báo lỗi rõ ràng.")
print("PASS 1: cả _dvc_browser_download_tdt() và _dvc_browser_thongbao() đều kiểm tra kết quả chờ "
      "jQuery, không còn gọi xong bỏ qua như trước — đúng nguyên nhân lỗi 'ReferenceError: $ is not "
      "defined' người dùng báo qua log thật.")

# ===== Test 2 (QUAN TRỌNG): _dvc_browser_download_tdt() phải THỬ LẠI (tải
# lại trang chi tiết) nếu lần đầu jQuery chưa kịp nạp, và báo lỗi RÕ RÀNG
# (không phải "$ is not defined" mù mờ) nếu vẫn không được sau khi thử
# lại — không được để lỗi mù mờ lọt ra ngoài như trước. =====
assert "range(2)" in than_download_tdt, (
    "_dvc_browser_download_tdt() phải thử tải lại trang chi tiết ít nhất 1 lần nữa nếu jQuery chưa kịp "
    "nạp lần đầu, trước khi báo lỗi hẳn — tránh thất bại ngay chỉ vì 1 lần chờ không đủ lâu.")
assert "nạp được jQuery" in than_download_tdt, (
    "_dvc_browser_download_tdt() phải báo lỗi RÕ RÀNG ('không nạp được jQuery...') khi thật sự thất bại "
    "sau khi đã thử lại — không được để lỗi mù mờ 'ReferenceError: $ is not defined' lọt ra ngoài, "
    "người dùng không biết nguyên nhân thật là gì.")
print("PASS 2: _dvc_browser_download_tdt() thử lại 1 lần khi jQuery chưa kịp nạp, và báo lỗi rõ ràng "
      "(không mù mờ) nếu vẫn thất bại sau khi thử lại.")

print("\nALL DONE")
