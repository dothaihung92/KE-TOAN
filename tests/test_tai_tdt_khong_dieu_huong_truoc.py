import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test (nguồn) — vòng thứ 3 sửa lỗi "$ is not defined" (jQuery
# chưa nạp) khi tải file nguồn "thuế điện tử". Diễn biến:
#   vòng 1: thêm kiểm tra kết quả _dvc_wait_jquery() + thử lại 1 lần ->
#     KHÔNG hết (8/8 hồ sơ vẫn lỗi y hệt "không nạp được jQuery sau 2
#     lần thử").
#   vòng 2: gộp bớt điều hướng (dùng lại trang đã mở từ
#     _dvc_browser_thongbao() thay vì điều hướng thêm lần nữa) -> VẪN
#     KHÔNG hết, 8/8 hồ sơ lỗi y hệt, KHÔNG đổi chút nào — chứng tỏ
#     nguyên nhân không nằm ở việc điều hướng dồn dập.
#   vòng 3 (bản này): ĐỔI HẲN cách tiếp cận — không điều hướng sang
#     trang chi tiết .../files/detail/{ma}?loai=ETAX nữa (trang này có
#     vẻ ĐƠN GIẢN LÀ KHÔNG BAO GIỜ tự nạp jQuery qua drv.get()), gọi
#     thẳng $.ajax(...) NGAY TỪ TRANG HIỆN TẠI (thường vẫn đang ở /tchs
#     — trang tìm kiếm, nơi jQuery đã XÁC NHẬN nạp tốt vì tra cứu vẫn
#     luôn thành công) — chỉ điều hướng sang trang chi tiết làm PHƯƠNG
#     ÁN DỰ PHÒNG nếu trang hiện tại thật sự không có jQuery.


def _lay_than_ham(ten_ham):
    idx = src.index('def ' + ten_ham + '(')
    idx_ke = src.index('\ndef ', idx + 10)
    return src[idx:idx_ke]


than_download_tdt = _lay_than_ham('_dvc_browser_download_tdt')

# ===== Test 1 (QUAN TRỌNG — đúng ca thật người dùng báo lần 3):
# _dvc_browser_download_tdt() phải THỬ GỌI TẢI NGAY TỪ TRANG HIỆN TẠI
# (không điều hướng) TRƯỚC — chỉ điều hướng sang trang chi tiết khi
# trang hiện tại THẬT SỰ không có jQuery. =====
idx_check_hien_tai = than_download_tdt.find("_dvc_wait_jquery(drv, 3)")
idx_dieu_huong = than_download_tdt.find("drv.get(url_muon)")
assert idx_check_hien_tai != -1, (
    "_dvc_browser_download_tdt() phải kiểm tra jQuery trên trang HIỆN TẠI trước (không điều hướng) — "
    "đã xác nhận qua 2 vòng sửa trước: thêm kiểm tra kết quả chờ + gộp bớt điều hướng ĐỀU KHÔNG giải "
    "quyết được (8/8 hồ sơ vẫn lỗi y hệt) — nghi trang chi tiết .../files/detail/{ma}?loai=ETAX đơn "
    "giản là không bao giờ tự nạp jQuery qua drv.get(), nên thử gọi thẳng từ trang tìm kiếm /tchs (nơi "
    "jQuery đã xác nhận nạp tốt) thay vì điều hướng sang đó trước.")
assert idx_dieu_huong != -1, (
    "_dvc_browser_download_tdt() vẫn phải giữ phương án dự phòng điều hướng sang trang chi tiết nếu "
    "trang hiện tại thật sự không có jQuery (vd lần gọi đầu tiên, chưa từng tra cứu gì).")
assert idx_check_hien_tai < idx_dieu_huong, (
    "Phải kiểm tra jQuery trên trang HIỆN TẠI TRƯỚC, chỉ điều hướng sang trang chi tiết làm phương án "
    "dự phòng SAU — không được làm ngược lại (điều hướng trước rồi mới kiểm tra).")
print("PASS 1: _dvc_browser_download_tdt() thử gọi tải ngay từ trang hiện tại (không điều hướng) "
      "TRƯỚC, chỉ điều hướng sang trang chi tiết làm phương án dự phòng — đúng hướng sửa mới sau khi 2 "
      "vòng sửa trước (kiểm tra kết quả chờ, gộp bớt điều hướng) đều không giải quyết được.")

# ===== Test 2 (không hồi quy — an toàn): vẫn giữ được thông báo lỗi RÕ
# RÀNG khi cả 2 cách (trang hiện tại + điều hướng dự phòng) đều thất
# bại — không được để lỗi mù mờ "$ is not defined" lọt ra ngoài lại. =====
assert "raise Exception(" in than_download_tdt and "jQuery" in than_download_tdt, (
    "_dvc_browser_download_tdt() vẫn phải báo lỗi rõ ràng có nhắc tới jQuery khi cả 2 cách đều thất bại "
    "— không được để lỗi mù mờ 'ReferenceError: $ is not defined' lọt ra ngoài như trước.")
print("PASS 2: vẫn giữ thông báo lỗi rõ ràng khi cả 2 cách đều thất bại, không để lỗi mù mờ lọt ra.")

print("\nALL DONE")
