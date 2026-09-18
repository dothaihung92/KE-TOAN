import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test (nguồn) — vòng thứ 4 sửa lỗi "$ is not defined"/"không
# có jQuery" khi tải file nguồn "thuế điện tử". Diễn biến:
#   vòng 1: thêm kiểm tra kết quả _dvc_wait_jquery() + thử lại 1 lần ->
#     KHÔNG hết (8/8 hồ sơ vẫn lỗi y hệt).
#   vòng 2: gộp bớt điều hướng (dùng lại trang đã mở từ
#     _dvc_browser_thongbao()) -> VẪN KHÔNG hết, 8/8 lỗi y hệt.
#   vòng 3: đổi sang kiểm tra jQuery ở "trang hiện tại" trước, chỉ điều
#     hướng LẠI TRANG CHI TIẾT làm dự phòng -> VẪN KHÔNG hết, 8/8 lỗi y
#     hệt — vì luồng gọi thật (_dvc_run_batch) LUÔN gọi
#     _dvc_browser_thongbao() TRƯỚC hàm này cho CÙNG mã hồ sơ, mà
#     thongbao() tự nó VẪN điều hướng sang trang chi tiết (cần đọc HTML
#     để dò idTbao) -> "trang hiện tại" lúc hàm NÀY chạy LUÔN LÀ trang
#     chi tiết (đã xác nhận không tự nạp jQuery) — phần "kiểm tra trang
#     hiện tại" ở vòng 3 vì vậy VÔ NGHĨA, và dự phòng quay LẠI đúng
#     trang chi tiết (đã hỏng) càng vô ích.
#   vòng 4 (bản này): khi trang hiện tại không có jQuery, điều hướng VỀ
#     THẲNG /tchs (trang tìm kiếm — nơi XÁC NHẬN CHẮC CHẮN có jQuery, vì
#     tra cứu luôn thành công), KHÔNG quay lại trang chi tiết (đã xác
#     nhận hỏng) như 3 vòng sửa trước.


def _lay_than_ham(ten_ham):
    idx = src.index('def ' + ten_ham + '(')
    idx_ke = src.index('\ndef ', idx + 10)
    return src[idx:idx_ke]


than_download_tdt = _lay_than_ham('_dvc_browser_download_tdt')

# ===== Test 1 (QUAN TRỌNG — đúng ca thật người dùng báo lần 4): khi
# trang hiện tại không có jQuery, PHẢI điều hướng về /tchs (trang tìm
# kiếm, đã xác nhận luôn có jQuery) — TUYỆT ĐỐI KHÔNG được quay lại
# trang .../files/detail/{ma}?loai=ETAX (đã xác nhận qua 3 vòng sửa liên
# tiếp là KHÔNG BAO GIỜ tự nạp jQuery). =====
assert 'drv.get(f"{DVC_BASE}/tchs")' in than_download_tdt, (
    "_dvc_browser_download_tdt() phải điều hướng VỀ THẲNG /tchs (không phải trang chi tiết hồ sơ) khi "
    "trang hiện tại không có jQuery — đã xác nhận qua 3 vòng sửa liên tiếp (kiểm tra kết quả chờ, gộp "
    "bớt điều hướng, kiểm tra trang hiện tại trước) đều KHÔNG giải quyết được vì trang chi tiết hồ sơ "
    "KHÔNG BAO GIỜ tự nạp jQuery qua drv.get() — 'trang hiện tại' lúc hàm này chạy luôn LÀ trang chi "
    "tiết đó (do _dvc_browser_thongbao() gọi trước luôn điều hướng tới đó), nên quay lại đúng trang đó "
    "làm dự phòng là vô ích, phải điều hướng sang trang KHÁC (đã xác nhận hoạt động: /tchs).")
assert 'drv.get(f"{DVC_BASE}/tchs/files/detail' not in than_download_tdt, (
    "_dvc_browser_download_tdt() KHÔNG được còn CODE điều hướng tới trang .../files/detail/{ma}?loai="
    "ETAX nữa dưới bất kỳ hình thức nào (chỉ nhắc tới trong docstring lịch sử sửa lỗi là được) — đã xác "
    "nhận chắc chắn trang này không bao giờ tự nạp jQuery qua drv.get(), điều hướng lại đó chỉ lặp lại "
    "đúng lỗi cũ.")
print("PASS 1: khi trang hiện tại không có jQuery, điều hướng VỀ THẲNG /tchs (trang tìm kiếm, đã xác "
      "nhận luôn có jQuery) — không còn quay lại trang chi tiết hồ sơ (đã xác nhận hỏng qua nhiều vòng "
      "sửa liên tiếp).")

# ===== Test 2 (không hồi quy — an toàn): vẫn giữ được thông báo lỗi RÕ
# RÀNG khi cả trang hiện tại lẫn /tchs đều không có jQuery — không được
# để lỗi mù mờ "$ is not defined" lọt ra ngoài lại. =====
assert "raise Exception(" in than_download_tdt and "jQuery" in than_download_tdt, (
    "_dvc_browser_download_tdt() vẫn phải báo lỗi rõ ràng có nhắc tới jQuery khi thật sự thất bại — "
    "không được để lỗi mù mờ 'ReferenceError: $ is not defined' lọt ra ngoài như trước.")
print("PASS 2: vẫn giữ thông báo lỗi rõ ràng khi thất bại thật sự, không để lỗi mù mờ lọt ra.")

print("\nALL DONE")
