import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test (nguồn) — người dùng xác nhận: đã tăng độ kiên nhẫn thử
# lại (5 lần/15s, build .305) nhưng chạy 12 tháng liên tục VẪN không tải
# được, và nói rõ "không phải do thời gian chờ". Vậy đây KHÔNG phải race
# condition (chờ chưa đủ lâu) mà lỗi THẬT SỰ không nạp được jQuery, bất kể
# chờ bao lâu — tiếp tục tăng thời gian chờ sẽ không giải quyết được gì.
#
# Đổi hướng: thay vì đoán tiếp thời gian chờ, THÊM CHẨN ĐOÁN bằng
# Performance API để biết CHÍNH XÁC vì sao — có thẻ <script> nào tham
# chiếu jquery trên trang không, request tải nó có thật sự xảy ra không,
# kết quả thế nào (transferSize=0 dù duration>0 thường là dấu hiệu bị
# chặn/lỗi mạng, khác hẳn tải chậm đơn thuần).


def _lay_than_ham(ten_ham):
    idx = src.index('def ' + ten_ham + '(')
    idx_ke = src.index('\ndef ', idx + 10)
    return src[idx:idx_ke]


than_chan_doan = _lay_than_ham('_dvc_chan_doan_jquery')
than_download_tdt = _lay_than_ham('_dvc_browser_download_tdt')

# ===== Test 1 (QUAN TRỌNG — đúng ca thật): PHẢI có hàm chẩn đoán
# _dvc_chan_doan_jquery() đọc Performance API (resource timing) để biết
# request tải jquery.js có xảy ra không và kết quả ra sao — không tiếp
# tục đoán mù thời gian chờ (đã xác nhận không phải nguyên nhân). =====
assert '_JS_CHAN_DOAN_JQUERY' in src, "Phải có khối JS chẩn đoán _JS_CHAN_DOAN_JQUERY đọc Performance API."
assert 'getEntriesByType' in src and "'resource'" in src.replace('"resource"', "'resource'"), (
    "Khối chẩn đoán phải dùng performance.getEntriesByType('resource') để biết request tải jquery.js "
    "có thật sự xảy ra và kết quả ra sao (transferSize/duration).")
assert than_chan_doan, "_dvc_chan_doan_jquery() phải tồn tại."
print("PASS 1: có hàm/khối JS chẩn đoán jQuery qua Performance API.")

# ===== Test 2 (QUAN TRỌNG — đúng ca thật): _dvc_browser_download_tdt()
# PHẢI gọi _dvc_chan_doan_jquery() và đính kèm kết quả vào lỗi ném ra khi
# jQuery không nạp được sau khi thử lại hết — để lần chạy tới TỰ cho biết
# nguyên nhân thật, không cần người dùng tự bắt DevTools. =====
assert '_dvc_chan_doan_jquery(drv)' in than_download_tdt, (
    "_dvc_browser_download_tdt() phải gọi _dvc_chan_doan_jquery(drv) và đính kèm kết quả vào lỗi ném "
    "ra khi jQuery không nạp được sau khi đã thử lại hết — người dùng xác nhận tăng thời gian chờ "
    "không giải quyết được, cần dữ liệu chẩn đoán thật để biết nguyên nhân, không đoán mù tiếp.")
print("PASS 2: _dvc_browser_download_tdt() đính kèm chẩn đoán jQuery vào lỗi khi thất bại.")

print("\nALL DONE")
