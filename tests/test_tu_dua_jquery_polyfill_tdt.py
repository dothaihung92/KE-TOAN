import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test (nguồn) — KHOÁ CHẶT đúng lỗi đã xảy ra thật: có bản đã
# GỠ BỎ bước đợi jQuery THẬT của trang (_dvc_wait_jquery) ở bước tải file,
# thay bằng tự cài ngay bản $.ajax() tối giản (_dvc_dam_bao_jquery) —
# hậu quả: KHÔNG TẢI ĐƯỢC TỜ NÀO (người dùng đối chiếu: "build
# 2026-09-17.284 chức năng tải tờ khai vẫn được dù bị thiếu vài tờ khai,
# giờ up bảng mới lại ko tải được tờ nào").
#
# Nguyên nhân: jQuery THẬT đi kèm chính các script của trang, trong đó có
# phần tự gắn token CSRF cho mọi request AJAX. Bản tối giản KHÔNG có phần
# đó nên server từ chối hết. Phải đợi jQuery thật; bản tối giản CHỈ là
# phương án cuối khi đợi hết giờ (lúc đó bản .284 cũng sẽ lỗi "$ is not
# defined" nên thử vẫn hơn là chắc chắn hỏng).
#
# Quyết định gỡ sai dựa trên chẩn đoán Performance API lọc script có chữ
# "jquery" trong đường dẫn, thấy rỗng rồi kết luận nhầm "trang không hề
# tải jQuery" — thực ra trang gói jQuery trong bundle mang tên khác
# (app/vendor/main...). Rỗng chỉ nghĩa là "không đường dẫn nào chứa chữ
# jquery", KHÔNG nghĩa là "không có jQuery".


def _lay_khoi_js(ten_bien):
    mo_dau = ten_bien + ' = r"""'
    idx = src.index(mo_dau)
    i = idx + len(mo_dau)
    j = src.index('"""', i)
    return src[i:j]


def _lay_than_ham(ten_ham):
    idx = src.index('def ' + ten_ham + '(')
    idx_ke = src.index('\ndef ', idx + 10)
    than = src[idx:idx_ke]
    # chỉ lấy phần MÃ THỰC THI (bỏ docstring) — docstring có nhắc tên hàm
    # để giải thích lịch sử, dễ gây khớp nhầm khi kiểm tra thứ tự gọi.
    k = than.index('"""', than.index('"""') + 3) + 3
    return than[k:]


than_download_tdt = _lay_than_ham('_dvc_browser_download_tdt')
than_thongbao = _lay_than_ham('_dvc_browser_thongbao')

# ===== Test 1 (QUAN TRỌNG NHẤT — đúng lỗi thật): cả 2 hàm tải PHẢI đợi
# jQuery THẬT (_dvc_wait_jquery) TRƯỚC, và chỉ dùng bản tối giản
# (_dvc_dam_bao_jquery) khi đợi THẤT BẠI — không được tự cài bản tối giản
# vô điều kiện (đã gây không tải được tờ nào). =====
for ten, than in (('_dvc_browser_download_tdt', than_download_tdt),
                  ('_dvc_browser_thongbao', than_thongbao)):
    assert '_dvc_wait_jquery(' in than, (
        f"{ten}() PHẢI đợi jQuery THẬT của trang (_dvc_wait_jquery) trước khi gọi $.ajax() — chính "
        f"script của trang mới tự gắn đúng token CSRF. Bản gỡ bước đợi này đi đã khiến KHÔNG TẢI "
        f"ĐƯỢC TỜ NÀO (build .284 có bước đợi thì tải được).")
    assert 'if not _dvc_wait_jquery(' in than, (
        f"{ten}(): bản $.ajax() tối giản (_dvc_dam_bao_jquery) chỉ được dùng khi ĐỢI THẤT BẠI — phải "
        f"đặt trong nhánh 'if not _dvc_wait_jquery(...)', không được gọi vô điều kiện.")
    i_doi = than.index('_dvc_wait_jquery(')
    i_toi_gian = than.index('_dvc_dam_bao_jquery(')
    assert i_doi < i_toi_gian, (
        f"{ten}(): phải ĐỢI jQuery thật TRƯỚC rồi mới tới bản tối giản, không được làm ngược lại.")
print("PASS 1: cả 2 hàm tải đều đợi jQuery THẬT trước, chỉ dùng bản tối giản khi đợi thất bại.")

# ===== Test 2 (không hồi quy): bản $.ajax() tối giản vẫn phải giữ đúng
# hành vi mặc định của jQuery thật cho đúng ca đang dùng — tự gắn
# 'X-Requested-With' (fetch() không tự gắn, từng gây 403) và KHÔNG tự
# đoán token X-XSRF-TOKEN (mọi lần tự đoán đều sai). =====
khoi_polyfill = _lay_khoi_js('_JS_DAM_BAO_JQUERY')
assert 'window.$' in khoi_polyfill and 'ajax' in khoi_polyfill, (
    "_JS_DAM_BAO_JQUERY phải tự cài đặt window.$.ajax() tối giản (phương án cuối).")
assert 'X-Requested-With' in khoi_polyfill, (
    "_JS_DAM_BAO_JQUERY phải tự gắn header 'X-Requested-With: XMLHttpRequest' — đúng hành vi mặc "
    "định thật của jQuery $.ajax(), thiếu header này từng gây 403 Forbidden ở bản fetch().")
assert 'X-XSRF-TOKEN' not in khoi_polyfill, (
    "_JS_DAM_BAO_JQUERY KHÔNG được tự đoán/gắn header X-XSRF-TOKEN — đã xác nhận qua nhiều lần đối "
    "chiếu request thật rằng tự đoán giá trị này (từ cookie hay thẻ meta) đều sai.")
assert 'typeof window.$' in khoi_polyfill, (
    "_JS_DAM_BAO_JQUERY phải kiểm tra window.$ chưa tồn tại mới cài — không được đè lên jQuery THẬT "
    "của trang (đè lên sẽ mất phần tự gắn token CSRF của trang).")
print("PASS 2: bản tối giản giữ đúng hành vi jQuery, không đè lên jQuery thật, không tự đoán CSRF.")

print("\nALL DONE")
