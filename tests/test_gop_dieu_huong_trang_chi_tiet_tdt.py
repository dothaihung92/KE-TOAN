import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test (nguồn) — người dùng báo log thật LẦN 2 (sau khi build
# .291 đã thêm thử lại 2 lần + báo lỗi rõ ràng): VẪN 8/8 hồ sơ nguồn
# "thuế điện tử" lỗi y hệt "không nạp được jQuery sau 2 lần thử". Nhìn
# lại luồng gọi (_dvc_run_batch): với MỖI hồ sơ, phần mềm điều hướng tới
# ĐÚNG 1 trang chi tiết 2 LẦN RIÊNG BIỆT — 1 lần trong
# _dvc_browser_thongbao() (tải Thông báo), 1 lần NGAY SAU ĐÓ trong
# _dvc_browser_download_tdt() (tải file) — gần như không nghỉ giữa 2
# lần. Với nhiều hồ sơ x 2 lần điều hướng x tối đa 2 lần thử lại = rất
# nhiều lượt tải trang dồn dập trong thời gian ngắn, rất có thể là
# nguyên nhân thật khiến cổng không kịp nạp/chặn — không phải "mạng
# chậm ngẫu nhiên" như thông báo lỗi cũ suy đoán.
#
# Sửa: _dvc_browser_download_tdt() giờ TÁI SỬ DỤNG trang ĐANG MỞ SẴN nếu
# đúng là trang chi tiết của CHÍNH mã hồ sơ đang cần (do
# _dvc_browser_thongbao() vừa mở ngay trước đó) — giảm còn 1 lần điều
# hướng cho mỗi hồ sơ thay vì 2.


def _lay_than_ham(ten_ham):
    idx = src.index('def ' + ten_ham + '(')
    idx_ke = src.index('\ndef ', idx + 10)
    return src[idx:idx_ke]


than_download_tdt = _lay_than_ham('_dvc_browser_download_tdt')

# ===== Test 1 (QUAN TRỌNG — đúng ca thật người dùng báo lần 2):
# _dvc_browser_download_tdt() phải kiểm tra drv.current_url TRƯỚC khi
# quyết định có điều hướng lại hay không — nếu ĐANG SẴN đúng trang chi
# tiết của mã hồ sơ đang cần thì DÙNG LUÔN, không điều hướng thêm lần
# nữa. =====
assert "drv.current_url" in than_download_tdt, (
    "_dvc_browser_download_tdt() phải kiểm tra drv.current_url để biết có đang sẵn ở đúng trang chi "
    "tiết hồ sơ hay không, trước khi quyết định điều hướng lại — nếu không, MỖI hồ sơ luôn tốn ĐỦ 2 lần "
    "điều hướng (1 lần từ _dvc_browser_thongbao + 1 lần từ hàm này) dù có thể đã đang sẵn đúng trang từ "
    "bước trước, gây dồn dập yêu cầu không cần thiết lên cổng.")
print("PASS 1: _dvc_browser_download_tdt() kiểm tra drv.current_url để tái sử dụng trang đã mở sẵn, "
      "giảm bớt điều hướng dư thừa — đúng nguyên nhân người dùng báo lần 2 (8/8 hồ sơ vẫn lỗi dù đã có "
      "thử lại 2 lần).")

# ===== Test 2 (không hồi quy — an toàn): vẫn còn nhánh điều hướng lại
# (thử lại tới 2 lần) khi KHÔNG đang sẵn đúng trang — không được xóa mất
# khả năng phục hồi khi thật sự cần điều hướng (vd hồ sơ đầu tiên, hoặc
# khi tai_tb=False nên _dvc_browser_thongbao() không được gọi trước). =====
assert "range(2)" in than_download_tdt, (
    "_dvc_browser_download_tdt() vẫn phải giữ khả năng điều hướng lại (thử tới 2 lần) khi KHÔNG đang sẵn "
    "đúng trang chi tiết — vd khi 'Tải kèm thông báo' đang TẮT nên _dvc_browser_thongbao() không được "
    "gọi trước, hàm này vẫn phải tự điều hướng được.")
print("PASS 2: vẫn giữ khả năng tự điều hướng + thử lại khi cần (không phải lúc nào cũng có trang mở "
      "sẵn từ trước, vd khi tắt tùy chọn tải kèm thông báo).")

print("\nALL DONE")
