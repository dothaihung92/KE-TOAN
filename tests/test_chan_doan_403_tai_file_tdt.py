import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test (nguồn) — vòng thứ 9 sửa lỗi tải file/Thông báo nguồn
# "thuế điện tử". Sau khi đổi CSRF sang đọc từ thẻ <meta name="_csrf">
# (vòng 8), người dùng báo VẪN lỗi 403 Forbidden Y HỆT, không đổi gì —
# nghĩa là 8 vòng đoán liên tiếp qua từng header (X-XSRF-TOKEN nguồn
# cookie, X-Requested-With, rồi nguồn meta tag) ĐỀU KHÔNG giải quyết
# được, luôn ra CÙNG 1 lỗi 403 bất kể header gửi đi thế nào.
#
# Đổi chiến thuật: thay vì tiếp tục đoán mù header tiếp theo, THÊM THÔNG
# TIN CHẨN ĐOÁN ngay vào chính phản hồi lỗi (cb) để lần chạy tới TỰ cho
# biết: token CSRF thực tế lấy được từ đâu (meta hay cookie), độ dài/vài
# ký tự đầu của nó (không lộ toàn bộ giá trị bí mật), và trình duyệt có
# bị lộ cờ navigator.webdriver hay không (dấu hiệu bot phổ biến — đã có
# tiền lệ masothue.com chủ động phát hiện tự động hoá). Nhờ vậy vòng sửa
# tiếp theo có DỮ LIỆU THẬT để biết đi tiếp hướng nào, không cần người
# dùng tự bắt DevTools thêm 1 lần nữa.


def _lay_khoi_js(ten_bien):
    mo_dau = ten_bien + ' = r"""'
    idx = src.index(mo_dau)
    i = idx + len(mo_dau)
    j = src.index('"""', i)
    return src[i:j]


khoi_download_tdt = _lay_khoi_js('_JS_DOWNLOAD_TDT')
khoi_download_tb = _lay_khoi_js('_JS_DOWNLOAD_TB')

# ===== Test 1 (QUAN TRỌNG — đúng ca thật, vòng thứ 9): cả _JS_DOWNLOAD_TDT
# và _JS_DOWNLOAD_TB đều PHẢI đính kèm thông tin chẩn đoán (csrfSrc,
# csrfLen, hasWebdriver) trong phản hồi lỗi — để biết chắc token đọc từ
# đâu và trình duyệt có bị lộ dấu hiệu tự động hoá hay không, thay vì tiếp
# tục đoán mù từng header một như 8 vòng trước. =====
for ten, khoi in (('_JS_DOWNLOAD_TDT', khoi_download_tdt), ('_JS_DOWNLOAD_TB', khoi_download_tb)):
    for truong in ('csrfSrc', 'csrfLen', 'csrfPre', 'hasWebdriver'):
        assert truong in khoi, (
            f"{ten} phải đính kèm trường chẩn đoán '{truong}' trong phản hồi lỗi — sau 8 vòng đoán mù "
            f"từng header (đều ra cùng lỗi 403 y hệt), cần dữ liệu thật để biết token CSRF thực tế lấy "
            f"từ đâu và trình duyệt có lộ dấu hiệu tự động hoá (navigator.webdriver) hay không.")
print("PASS 1: cả _JS_DOWNLOAD_TDT và _JS_DOWNLOAD_TB đều đính kèm thông tin chẩn đoán "
      "(csrfSrc/csrfLen/csrfPre/hasWebdriver) trong phản hồi lỗi.")

# ===== Test 2 (không hồi quy): _dvc_ghi_loi_tai() phải giữ đủ chỗ (>=300
# ký tự) cho chuỗi lỗi — nếu vẫn cắt ở 200 ký tự như trước, các trường
# chẩn đoán MỚI thêm (đứng sau 'resp' cũ, dài) sẽ bị cắt mất, không hiện
# ra được cho người dùng đọc. =====
idx_ham = src.index('def _dvc_ghi_loi_tai(')
idx_ke = src.index('\ndef ', idx_ham + 10)
than_ham = src[idx_ham:idx_ke]
import re
m = re.search(r"""loi or (?:""|'')\)\[:(\d+)\]""", than_ham)
assert m, "_dvc_ghi_loi_tai() phải có giới hạn cắt chuỗi lỗi dạng str(loi or '')[:N]"
gioi_han = int(m.group(1))
assert gioi_han >= 300, (
    f"_dvc_ghi_loi_tai() đang cắt chuỗi lỗi ở {gioi_han} ký tự — quá ngắn để chứa đủ các trường chẩn "
    f"đoán mới (csrfSrc/csrfLen/csrfPre/hasWebdriver) cộng với 'resp' gốc, cần >= 300 ký tự.")
print(f"PASS 2: _dvc_ghi_loi_tai() giữ đủ chỗ ({gioi_han} ký tự) cho các trường chẩn đoán mới.")

print("\nALL DONE")
