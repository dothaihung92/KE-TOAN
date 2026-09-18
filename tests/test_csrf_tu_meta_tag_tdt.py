import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test (nguồn) — vòng thứ 8 sửa lỗi tải file/Thông báo nguồn
# "thuế điện tử". Sau khi thêm header X-Requested-With (vòng 7), người
# dùng báo VẪN lỗi y hệt: 403 Forbidden.
#
# Soi kỹ lại chính request thật đã bắt trước đó (không cần bắt lại) mới
# nhận ra: giá trị header 'x-xsrf-token' trong request thật
# ('-iG1P7A_o8BEHdw9dyE26Oc4Q2UaWbpiRckiwkq23Wmi2VwPyxCNXdRbxvFpe7oKQAwCi'
# 'YYIbgR4O4tPdK8R9S_X7FmQ6G5t') KHÁC HẲN giá trị cookie 'XSRF-TOKEN'
# ('118bdde1-ff77-4aa0-abb1-1f37ea10212b') trong CÙNG request đó — 2
# chuỗi hoàn toàn khác nhau, không phải cùng 1 giá trị copy qua. Vậy
# token gửi trong header KHÔNG đọc từ cookie (khác hẳn giả định ban đầu,
# dựa theo mẫu _JS_SEARCH_TDT — endpoint tìm kiếm khác, có thể dùng cơ
# chế CSRF khác). Đây là mẫu CSRF rất phổ biến ở ứng dụng Spring+
# Thymeleaf: token được máy chủ nhúng SẴN vào chính trang HTML lúc render
# (thẻ <meta name="_csrf">), JS chỉ việc ĐỌC LẠI từ trang, không tự tạo/
# đọc cookie.


def _lay_khoi_js(ten_bien):
    mo_dau = ten_bien + ' = r"""'
    idx = src.index(mo_dau)
    i = idx + len(mo_dau)
    j = src.index('"""', i)
    return src[i:j]


khoi_download_tdt = _lay_khoi_js('_JS_DOWNLOAD_TDT')
khoi_download_tb = _lay_khoi_js('_JS_DOWNLOAD_TB')

# ===== Test 1 (QUAN TRỌNG — đúng ca thật, vòng thứ 8): _JS_DOWNLOAD_TDT
# và _JS_DOWNLOAD_TB đều PHẢI ưu tiên đọc token CSRF từ thẻ
# <meta name="_csrf"> của trang TRƯỚC, chỉ dự phòng đọc cookie XSRF-TOKEN
# nếu trang không có thẻ meta này — KHÔNG được chỉ đọc từ cookie như
# trước (giá trị cookie khác hẳn giá trị header thật cần gửi). =====
for ten, khoi in (('_JS_DOWNLOAD_TDT', khoi_download_tdt), ('_JS_DOWNLOAD_TB', khoi_download_tb)):
    assert 'meta[name="_csrf"]' in khoi, (
        f"{ten} phải đọc token CSRF từ thẻ <meta name=\"_csrf\"> của trang — request thật xác nhận giá "
        f"trị header 'x-xsrf-token' KHÁC HẲN giá trị cookie 'XSRF-TOKEN' trong CÙNG 1 request, nghĩa là "
        f"token không đọc từ cookie mà từ nơi khác (mẫu Spring+Thymeleaf phổ biến: nhúng sẵn vào thẻ "
        f"meta của trang HTML).")
    idx_meta = khoi.find('meta[name="_csrf"]')
    idx_cookie_fallback = khoi.find("getCookie('XSRF-TOKEN')")
    assert idx_cookie_fallback != -1, (
        f"{ten} vẫn nên giữ phương án dự phòng đọc cookie XSRF-TOKEN nếu trang không có thẻ meta "
        f"(phòng trường hợp đoán vẫn chưa đúng hẳn, còn cơ hội hoạt động một phần).")
    assert idx_meta < idx_cookie_fallback, (
        f"{ten} phải ưu tiên đọc thẻ meta TRƯỚC, chỉ dùng cookie làm dự phòng SAU — không được làm "
        f"ngược lại.")
print("PASS 1: cả _JS_DOWNLOAD_TDT và _JS_DOWNLOAD_TB đều ưu tiên đọc token CSRF từ thẻ "
      "<meta name=\"_csrf\"> của trang trước, dự phòng đọc cookie XSRF-TOKEN sau — đúng theo phát hiện "
      "từ request thật (2 giá trị khác nhau hoàn toàn trong cùng 1 request).")

print("\nALL DONE")
