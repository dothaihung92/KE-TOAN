import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test (nguồn) — vòng thứ 11: QUAY LẠI đúng code GỐC cho bước
# tải file/Thông báo nguồn "thuế điện tử". 5 vòng sửa liên tiếp trước đó
# (đổi $.ajax()->fetch(), thêm X-XSRF-TOKEN từ cookie, thêm
# X-Requested-With, đổi nguồn token sang thẻ <meta>, tăng thời gian nghỉ
# giữa các lượt tải) ĐỀU KHÔNG giải quyết được 403 Forbidden — mỗi vòng
# đều dựa trên dữ liệu thật (log lỗi/DevTools người dùng cung cấp) nhưng
# vẫn bế tắc.
#
# Người dùng chỉ ra: code GỐC (trước khi có bất kỳ sửa đổi CSRF/fetch nào
# ở trên) đã từng tải được "gần như tất cả" hồ sơ thật. Bản gốc dùng
# $.ajax() (jQuery) thuần, đợi jQuery nạp xong, KHÔNG tự set bất kỳ header
# CSRF nào — giả thuyết: khi jQuery nạp được, chính trang web tự gắn đúng
# header cần thiết qua cơ chế nội bộ (site tự cấu hình), không cần (và
# không nên) tự đoán/set tay vì giá trị thật không nằm ở cookie hay thẻ
# meta nào tìm được (đã xác nhận nhiều lần qua request thật). Quay lại
# đúng cách làm gốc, bỏ hết các lớp CSRF tự thêm.


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


khoi_download_tdt = _lay_khoi_js('_JS_DOWNLOAD_TDT')
khoi_download_tb = _lay_khoi_js('_JS_DOWNLOAD_TB')
than_download_tdt = _lay_than_ham('_dvc_browser_download_tdt')

# ===== Test 1 (QUAN TRỌNG — đúng ca thật, vòng thứ 11): _JS_DOWNLOAD_TDT
# và _JS_DOWNLOAD_TB PHẢI dùng $.ajax() (jQuery) như bản gốc, KHÔNG còn
# dùng fetch() — và KHÔNG tự set bất kỳ header CSRF/X-Requested-With nào
# (để trang web tự gắn đúng qua cơ chế nội bộ của nó khi jQuery nạp được,
# thay vì tự đoán sai giá trị như 4 vòng sửa trước). =====
for ten, khoi in (('_JS_DOWNLOAD_TDT', khoi_download_tdt), ('_JS_DOWNLOAD_TB', khoi_download_tb)):
    assert '$.ajax(' in khoi, (
        f"{ten} phải quay lại dùng $.ajax() (jQuery) như code gốc — bản fetch() (5 vòng sửa gần đây) "
        f"không giải quyết được 403 Forbidden dù đã thử nhiều cách gắn CSRF khác nhau.")
    assert 'fetch(' not in khoi, f"{ten} không được còn dùng fetch() nữa (đã quay lại $.ajax())."
    assert 'X-XSRF-TOKEN' not in khoi, (
        f"{ten} không được tự set header X-XSRF-TOKEN thủ công — giá trị thật không nằm ở cookie hay "
        f"thẻ <meta> nào tìm được (đã xác nhận qua nhiều lần đối chiếu request thật); để jQuery/trang "
        f"web tự gắn đúng qua cơ chế nội bộ của nó như code gốc.")
    assert 'X-Requested-With' not in khoi, f"{ten} không được tự set header X-Requested-With (bản gốc không có)."
print("PASS 1: cả _JS_DOWNLOAD_TDT và _JS_DOWNLOAD_TB đều quay lại $.ajax() thuần, không tự set header CSRF.")

# ===== Test 2 (không hồi quy): _dvc_browser_download_tdt() phải gọi lại
# _dvc_wait_jquery() trước khi gọi tải — đúng bản gốc (chờ jQuery nạp,
# dùng $.ajax() cần jQuery). =====
assert '_dvc_wait_jquery' in than_download_tdt, (
    "_dvc_browser_download_tdt() phải gọi _dvc_wait_jquery() trước khi tải — bản $.ajax() cần jQuery "
    "đã nạp xong, khác bản fetch() (không cần) vừa bỏ.")
print("PASS 2: _dvc_browser_download_tdt() gọi _dvc_wait_jquery() trước khi tải — đúng bản gốc.")

print("\nALL DONE")
