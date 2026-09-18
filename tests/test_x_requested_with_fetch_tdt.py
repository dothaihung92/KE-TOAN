import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test (nguồn) — vòng thứ 7 sửa lỗi tải file/Thông báo nguồn
# "thuế điện tử". Sau khi đổi sang fetch() (vòng 6, né được vấn đề jQuery
# không bao giờ nạp xong), người dùng báo lỗi MỚI, RÕ RÀNG hơn hẳn: server
# trả về 403 Forbidden — request ĐÃ gửi đi đúng (khác lỗi client-side
# trước đó), chỉ còn thiếu quyền.
#
# Đối chiếu lại đúng request thật đã bắt trước đó (Copy Request Headers)
# mới để ý sót 1 header: 'x-requested-with: XMLHttpRequest' — jQuery TỰ
# ĐỘNG thêm header này cho mọi request AJAX (đó là lý do bản $.ajax() cũ
# không cần khai báo tay), nhưng fetch() KHÔNG tự thêm — phải khai báo
# thủ công trong headers.


def _lay_khoi_js(ten_bien):
    mo_dau = ten_bien + ' = r"""'
    idx = src.index(mo_dau)
    i = idx + len(mo_dau)
    j = src.index('"""', i)
    return src[i:j]


khoi_download_tdt = _lay_khoi_js('_JS_DOWNLOAD_TDT')
khoi_download_tb = _lay_khoi_js('_JS_DOWNLOAD_TB')

# ===== Test 1 (QUAN TRỌNG — đúng ca thật, vòng thứ 7): _JS_DOWNLOAD_TDT
# và _JS_DOWNLOAD_TB đều PHẢI gửi header 'X-Requested-With: XMLHttpRequest'
# — request thật (Copy Request Headers) có header này nhưng bản fetch()
# đầu tiên (vòng 6) quên khai báo, gây lỗi 403 Forbidden. =====
for ten, khoi in (('_JS_DOWNLOAD_TDT', khoi_download_tdt), ('_JS_DOWNLOAD_TB', khoi_download_tb)):
    assert "fetch(" in khoi, f"{ten} phải dùng fetch() (đã xác nhận đúng ở vòng sửa trước)"
    assert "'X-Requested-With': 'XMLHttpRequest'" in khoi, (
        f"{ten} phải gửi header 'X-Requested-With: XMLHttpRequest' — jQuery TỰ ĐỘNG thêm header này "
        f"cho mọi request AJAX (bản $.ajax() cũ không cần khai báo tay), nhưng fetch() KHÔNG tự thêm — "
        f"thiếu header này khiến server trả về 403 Forbidden (đúng log thật người dùng báo: request đã "
        f"gửi đi đúng — khác lỗi client-side trước đó — nhưng bị từ chối vì thiếu quyền).")
print("PASS 1: cả _JS_DOWNLOAD_TDT và _JS_DOWNLOAD_TB đều gửi header X-Requested-With: XMLHttpRequest "
      "— đúng request thật, khắc phục lỗi 403 Forbidden.")

print("\nALL DONE")
