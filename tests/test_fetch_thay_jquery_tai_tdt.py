import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test (nguồn) — vòng thứ 6 sửa lỗi tải file/Thông báo nguồn
# "thuế điện tử". Sau khi thêm header X-XSRF-TOKEN còn thiếu (vòng 5),
# vẫn quay lại đúng lỗi "trang chi tiết hồ sơ không nạp được jQuery sau
# 3 lần thử" — xác nhận CHẮC CHẮN (qua nhiều vòng chẩn đoán khác nhau,
# luôn cùng 1 kết quả) trang chi tiết .../files/detail/{ma}?loai=ETAX
# KHÔNG BAO GIỜ tự nạp xong thư viện jQuery qua drv.get(), bất kể thêm
# token/tăng số lần thử/tăng thời gian chờ.
#
# Nhận ra: bước tải file/Thông báo chỉ cần gọi 1 API POST thuần — không
# hề cần jQuery. fetch() là API GỐC của mọi trình duyệt hiện đại, LUÔN
# sẵn có ngay khi trang load xong HTML, không phụ thuộc việc jQuery (hay
# bất kỳ thư viện ngoài nào) có tải được hay không — né hẳn vấn đề chờ
# jQuery đã bế tắc suốt nhiều vòng sửa trước. _JS_DOWNLOAD_TDT và
# _JS_DOWNLOAD_TB đổi từ $.ajax() sang fetch(); _dvc_browser_download_tdt
# và _dvc_browser_thongbao() không còn gọi/kiểm tra _dvc_wait_jquery()
# nữa (chỉ cần điều hướng đúng trang + đợi trang render, không liên quan
# gì đến việc jQuery tải được hay không).


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
than_thongbao = _lay_than_ham('_dvc_browser_thongbao')

# ===== Test 1 (QUAN TRỌNG — đúng ca thật, vòng thứ 6): _JS_DOWNLOAD_TDT
# và _JS_DOWNLOAD_TB PHẢI dùng fetch() thay vì $.ajax() (jQuery) — đã xác
# nhận chắc chắn qua nhiều vòng chẩn đoán: trang chi tiết hồ sơ không bao
# giờ tự nạp xong jQuery, nhưng bước tải chỉ cần 1 API POST thuần, không
# cần jQuery. =====
for ten, khoi in (('_JS_DOWNLOAD_TDT', khoi_download_tdt), ('_JS_DOWNLOAD_TB', khoi_download_tb)):
    assert "fetch(" in khoi, (
        f"{ten} phải dùng fetch() (API gốc mọi trình duyệt, luôn sẵn có) thay vì $.ajax() (jQuery) — "
        f"đã xác nhận chắc chắn qua nhiều vòng chẩn đoán trang chi tiết hồ sơ KHÔNG BAO GIỜ tự nạp xong "
        f"jQuery, dù đã thử kiểm tra/thử lại/tăng thời gian chờ nhiều lần.")
    assert "$.ajax(" not in khoi, f"{ten} không được còn dùng $.ajax() (jQuery) nữa."
print("PASS 1: _JS_DOWNLOAD_TDT và _JS_DOWNLOAD_TB đều đã đổi sang fetch() (không phụ thuộc jQuery).")

# ===== Test 2 (QUAN TRỌNG — không hồi quy): _dvc_browser_download_tdt()
# và _dvc_browser_thongbao() KHÔNG được còn gọi _dvc_wait_jquery() nữa —
# bước tải file/Thông báo không cần jQuery, chờ/kiểm tra jQuery chỉ gây
# thất bại giả (đã xác nhận thất bại 100% qua nhiều vòng dù trang thật
# sự vẫn hoạt động — dùng fetch() vẫn tải được bình thường). =====
for ten, than in (('_dvc_browser_download_tdt', than_download_tdt), ('_dvc_browser_thongbao', than_thongbao)):
    assert "_dvc_wait_jquery" not in than, (
        f"{ten} KHÔNG được còn gọi _dvc_wait_jquery() — bước này giờ dùng fetch() (không cần jQuery), "
        f"chờ/kiểm tra jQuery chỉ gây thất bại giả không cần thiết (đã xác nhận trang chi tiết hồ sơ "
        f"không bao giờ tự nạp xong jQuery, nhưng vẫn tải file được bình thường bằng fetch()).")
print("PASS 2: cả 2 hàm không còn phụ thuộc/kiểm tra jQuery nữa — đúng hướng sửa fetch().")

print("\nALL DONE")
