import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test (nguồn) — sau khi quay lại $.ajax() (bản gốc) cho bước
# tải file/Thông báo nguồn "thuế điện tử", người dùng test 2 lần liên
# tiếp: lần 1 tải được 3/3 file, lần 2 (đổi sang chia đoạn từng tháng) lại
# lỗi "$ is not defined" cho CẢ 12/12 hồ sơ. Kết luận: việc jQuery có nạp
# xong hay không là FLAKY (lúc được lúc không), không phải lỗi cố định
# như từng nghĩ trước đây — nhưng code trước đó chỉ ĐỢI 1 lần rồi cứ thế
# gọi $.ajax() bừa dù jQuery chưa chắc đã nạp xong.
#
# Sửa: THỬ LẠI (tải lại đúng trang, không đổi cách gọi API) khi jQuery
# chưa nạp xong, thay vì chỉ đợi 1 lần — cả _dvc_browser_download_tdt (tải
# file tờ khai) và _dvc_browser_thongbao (tải file Thông báo, cũng dùng
# $.ajax() qua _JS_DOWNLOAD_TB sau khi quay lại bản gốc).


def _lay_than_ham(ten_ham):
    idx = src.index('def ' + ten_ham + '(')
    idx_ke = src.index('\ndef ', idx + 10)
    return src[idx:idx_ke]


than_download_tdt = _lay_than_ham('_dvc_browser_download_tdt')
than_thongbao = _lay_than_ham('_dvc_browser_thongbao')

# ===== Test 1 (QUAN TRỌNG — đúng ca thật): _dvc_browser_download_tdt()
# PHẢI thử lại (gọi lại drv.get() + _dvc_wait_jquery) nếu jQuery chưa nạp
# xong ở lần đầu, KHÔNG được chỉ đợi 1 lần rồi bỏ qua kết quả như trước
# (nguyên nhân gây lỗi "$ is not defined" hàng loạt khi jQuery nạp chậm/
# flaky). =====
import re as _re
m_loop = _re.search(r'for\s+\w+\s+in\s+range\((\d+)\)', than_download_tdt)
assert m_loop, (
    "_dvc_browser_download_tdt() phải bọc drv.get()+_dvc_wait_jquery() trong 1 VÒNG LẶP thử lại — "
    "không được chỉ gọi 1 lần duy nhất như bản gốc, gây lỗi '$ is not defined' hàng loạt khi jQuery "
    "nạp chậm/flaky.")
assert int(m_loop.group(1)) >= 2, (
    f"Vòng lặp thử lại trong _dvc_browser_download_tdt() phải thử ít nhất 2 lần, hiện chỉ "
    f"{m_loop.group(1)} lần.")
assert 'if _dvc_wait_jquery(' in than_download_tdt or 'if not _dvc_wait_jquery(' in than_download_tdt, (
    "_dvc_browser_download_tdt() phải KIỂM TRA kết quả _dvc_wait_jquery() (không được gọi rồi bỏ qua "
    "kết quả) để quyết định có cần thử lại hay không.")
print("PASS 1: _dvc_browser_download_tdt() thử lại điều hướng khi jQuery chưa nạp xong.")

# ===== Test 2 (không hồi quy — cùng vấn đề áp dụng cho tải Thông báo):
# _dvc_browser_thongbao() cũng PHẢI đợi/thử lại jQuery trước khi gọi
# _JS_DOWNLOAD_TB (đã quay lại $.ajax(), cần jQuery) khi có idTbao cần
# tải. =====
assert '_dvc_wait_jquery' in than_thongbao, (
    "_dvc_browser_thongbao() phải gọi _dvc_wait_jquery() trước khi tải file Thông báo — "
    "_JS_DOWNLOAD_TB đã quay lại dùng $.ajax() (cần jQuery), không còn là fetch() (không cần jQuery) "
    "như trước nữa.")
print("PASS 2: _dvc_browser_thongbao() đợi/thử lại jQuery trước khi gọi _JS_DOWNLOAD_TB.")

print("\nALL DONE")
