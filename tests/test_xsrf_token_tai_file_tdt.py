import os
import re

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test (nguồn) — vòng thứ 5 (VÀ LÀ VÒNG TÌM RA ĐÚNG NGUYÊN
# NHÂN THẬT) sửa lỗi tải file nguồn "thuế điện tử". Diễn biến 4 vòng sửa
# trước (đều KHÔNG giải quyết được, cùng lỗi hoặc lỗi khác nhưng vẫn
# thất bại 100%):
#   1-2) Kiểm tra kết quả chờ jQuery + gộp bớt điều hướng -> KHÔNG hết.
#   3) Bỏ hẳn điều hướng sang trang chi tiết, gọi thẳng từ trang hiện tại
#      (nghĩ là /tchs, nhưng thực ra luôn là trang chi tiết do
#      _dvc_browser_thongbao() đã điều hướng trước) -> vẫn lỗi y hệt.
#   4) Sửa lại điều hướng VỀ ĐÚNG /tchs khi thất bại (thay vì quay lại
#      trang chi tiết) -> lỗi ĐỔI HẲN: không còn "$ is not defined" (lỗi
#      client-side, thiếu jQuery) nữa, mà thành lỗi SERVER-SIDE rõ ràng:
#      {'status': 500, 'resp': '{"error":"Tải hồ sơ thất bại"}'} — tức
#      ĐÃ vượt qua được bước nạp trang, server nhận được request nhưng
#      TỪ CHỐI vì thiếu gì đó.
#   5) (bản này) Người dùng tự bắt request THẬT lúc tải thành công qua
#      DevTools (Copy Request Headers) — phát hiện 2 điều: (a) request
#      thật CÓ header 'x-xsrf-token' (đọc từ cookie XSRF-TOKEN) mà
#      _JS_DOWNLOAD_TDT/_JS_DOWNLOAD_TB TRƯỚC GIỜ CHƯA BAO GIỜ gửi — đã
#      thêm vào; (b) 'referer' của request thật ĐÚNG LÀ trang chi tiết
#      hồ sơ (trình duyệt tự gắn theo trang đang đứng, không giả được từ
#      script khác trang) -> PHẢI điều hướng tới đúng trang chi tiết
#      trước khi gọi (khôi phục lại, không gọi thẳng từ /tchs như vòng 4
#      nữa).


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
than_ham_download_tdt = _lay_than_ham('_dvc_browser_download_tdt')

# ===== Test 1 (QUAN TRỌNG — đúng ca thật, phát hiện qua request THẬT
# người dùng tự bắt): _JS_DOWNLOAD_TDT và _JS_DOWNLOAD_TB đều PHẢI gửi
# header 'X-XSRF-TOKEN' (đọc từ cookie XSRF-TOKEN) — trước đây HOÀN TOÀN
# KHÔNG gửi, khiến server từ chối với lỗi 500 "Tải hồ sơ thất bại". =====
for ten, khoi in (('_JS_DOWNLOAD_TDT', khoi_download_tdt), ('_JS_DOWNLOAD_TB', khoi_download_tb)):
    assert "getCookie('XSRF-TOKEN')" in khoi, (
        f"{ten} phải đọc cookie XSRF-TOKEN — request tải file THẬT (bắt qua DevTools lúc tải thành "
        f"công) có header 'x-xsrf-token' mà code cũ hoàn toàn không gửi, khiến server từ chối 500 "
        f"'Tải hồ sơ thất bại'.")
    assert re.search(r"['\"]X-XSRF-TOKEN['\"]\s*:\s*csrf", khoi), (
        f"{ten} phải gửi header 'X-XSRF-TOKEN' (giá trị đọc từ cookie XSRF-TOKEN) trong request tải "
        f"file — đúng như request thật đã xác nhận.")
print("PASS 1: cả _JS_DOWNLOAD_TDT và _JS_DOWNLOAD_TB đều gửi header X-XSRF-TOKEN (đọc từ cookie) — "
      "đúng request thật người dùng tự bắt qua DevTools lúc tải file thành công.")

# ===== Test 2 (QUAN TRỌNG — đúng ca thật, referer PHẢI đúng trang chi
# tiết): _dvc_browser_download_tdt() PHẢI điều hướng tới đúng trang chi
# tiết hồ sơ trước khi gọi tải — KHÔNG được gọi thẳng từ trang khác (vd
# /tchs) như vòng sửa liền trước, vì Referer của request thật xác nhận
# đúng là trang chi tiết (trình duyệt tự gắn theo trang đang đứng, không
# giả được từ script). =====
assert 'drv.get(url_muon)' in than_ham_download_tdt and 'files/detail/{ma}?loai=ETAX' in than_ham_download_tdt, (
    "_dvc_browser_download_tdt() phải điều hướng tới ĐÚNG trang chi tiết hồ sơ (.../files/detail/{ma}"
    "?loai=ETAX) trước khi gọi tải file — Referer của request thật (bắt qua DevTools) xác nhận đúng là "
    "trang này, không thể gọi thẳng từ trang khác (vd /tchs) vì Referer sẽ sai.")
print("PASS 2: _dvc_browser_download_tdt() điều hướng tới đúng trang chi tiết hồ sơ trước khi gọi tải "
      "— đúng Referer của request thật, không còn gọi thẳng từ /tchs như vòng sửa liền trước.")

print("\nALL DONE")
