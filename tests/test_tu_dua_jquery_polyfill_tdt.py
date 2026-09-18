import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test (nguồn) — chẩn đoán qua Performance API (build .306) xác
# nhận DỨT KHOÁT: trang chi tiết hồ sơ (.../files/detail/{ma}?loai=...) vào
# THẲNG bằng drv.get() KHÔNG HỀ có thẻ <script> nào tải jQuery
# (the_script:[], tai_nguyen:[], co_jquery:False cho CẢ 12/12 hồ sơ test) —
# không phải chờ chưa đủ lâu (đã tăng 3->5 lần/10->15s không cải thiện,
# người dùng xác nhận "không phải do thời gian chờ") mà ĐƠN GIẢN LÀ KHÔNG
# CÓ YÊU CẦU TẢI jQuery khi vào thẳng link.
#
# Sửa đúng gốc: TỰ ĐƯA vào trang 1 bản $.ajax() tối giản (không cần
# internet/CDN ngoài) thay vì tiếp tục chờ/thử lại trang tự tải jQuery.


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


khoi_polyfill = _lay_khoi_js('_JS_DAM_BAO_JQUERY')
than_dam_bao = _lay_than_ham('_dvc_dam_bao_jquery')
than_download_tdt = _lay_than_ham('_dvc_browser_download_tdt')
than_thongbao = _lay_than_ham('_dvc_browser_thongbao')

# ===== Test 1 (QUAN TRỌNG — đúng ca thật): _JS_DAM_BAO_JQUERY phải tự cài
# đặt window.$.ajax (không phụ thuộc trang web nguồn có tải jQuery hay
# không), và PHẢI tự gắn header 'X-Requested-With' (đúng hành vi mặc định
# thật của jQuery — khác fetch() không tự gắn, đã gây 403 Forbidden ở các
# vòng sửa trước). =====
assert 'window.$' in khoi_polyfill and 'ajax' in khoi_polyfill, (
    "_JS_DAM_BAO_JQUERY phải tự cài đặt window.$.ajax() tối giản.")
assert 'X-Requested-With' in khoi_polyfill, (
    "_JS_DAM_BAO_JQUERY phải tự gắn header 'X-Requested-With: XMLHttpRequest' — đúng hành vi mặc định "
    "thật của jQuery $.ajax(), thiếu header này từng gây 403 Forbidden ở bản fetch() trước đây.")
assert 'X-XSRF-TOKEN' not in khoi_polyfill, (
    "_JS_DAM_BAO_JQUERY KHÔNG được tự gắn header X-XSRF-TOKEN — đã xác nhận qua nhiều lần đối chiếu "
    "request thật rằng tự đoán giá trị này (từ cookie hay thẻ meta) đều sai.")
print("PASS 1: _JS_DAM_BAO_JQUERY tự cài $.ajax() tối giản, tự gắn X-Requested-With, không tự đoán CSRF.")

# ===== Test 2 (QUAN TRỌNG — đúng ca thật): cả _dvc_browser_download_tdt()
# và _dvc_browser_thongbao() PHẢI gọi _dvc_dam_bao_jquery(drv) trước khi
# gọi $.ajax() — KHÔNG còn chờ/thử lại jQuery thật nữa (đã xác nhận vô
# ích: "the_script":[] nghĩa là trang không hề có yêu cầu tải, chờ bao
# lâu cũng vậy). =====
for ten, than in (('_dvc_browser_download_tdt', than_download_tdt), ('_dvc_browser_thongbao', than_thongbao)):
    assert '_dvc_dam_bao_jquery(drv)' in than, (
        f"{ten}() phải gọi _dvc_dam_bao_jquery(drv) trước khi gọi $.ajax() — trang không hề tự tải "
        f"jQuery khi vào thẳng link, phải tự đưa vào thay vì chờ/thử lại (đã xác nhận vô ích).")
print("PASS 2: cả 2 hàm tải đều gọi _dvc_dam_bao_jquery(drv) trước khi dùng $.ajax().")

# ===== Test 3 (không hồi quy): _dvc_browser_download_tdt() KHÔNG còn vòng
# lặp thử lại điều hướng nhiều lần vô ích (chờ jQuery thật) nữa — đơn giản
# hoá về đúng 1 lần điều hướng + tự đưa jQuery. =====
khoi_than_ma = than_download_tdt[than_download_tdt.index('import time as _t'):]
assert khoi_than_ma.count('drv.get(') == 1, (
    "_dvc_browser_download_tdt() chỉ cần điều hướng 1 LẦN (không cần vòng lặp thử lại nữa, vì không "
    "còn phụ thuộc trang tự tải jQuery) — nếu vẫn thấy nhiều drv.get(), có thể sót lại vòng lặp thử "
    "lại cũ chưa dọn.")
print("PASS 3: _dvc_browser_download_tdt() đã đơn giản hoá, không còn vòng lặp thử lại vô ích.")

print("\nALL DONE")
