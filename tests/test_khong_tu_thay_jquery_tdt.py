import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test (nguồn) — KHOÁ CHẶT 2 sai lầm đã trả giá thật ở bước tải
# file/Thông báo. Mốc đối chiếu: build 2026-09-17.284 người dùng xác nhận
# TẢI ĐƯỢC (chỉ thiếu vài tờ khai do lỗi tra cứu khác).
#
# Sai lầm 1 — tự cài bản $.ajax() thay thế jQuery của trang: đổi lỗi từ
# "$ is not defined" thành 403 Forbidden cho 22/22 hồ sơ, VÀ hỏng luôn
# nhánh DVC (từ 01/07/2025) vốn chạy tốt. Lý do: (a) request do bản tự
# cài gửi thiếu token CSRF mà chính script của trang tự gắn; (b) bản tự
# cài còn "đầu độc" các lần gọi SAU trên cùng trang — _dvc_browser_download
# (nhánh DVC) gọi $.ajax NGAY TRÊN trang mà _dvc_browser_thongbao vừa mở.
#
# Sai lầm 2 — XÉT kết quả trả về của _dvc_wait_jquery để rẽ nhánh: hàm đó
# đòi CẢ window.jQuery lẫn typeof window.$ === 'function' nên trả False
# ngay cả khi trang đã có $ dùng được (log thật: "jQuery lúc đó: KHÔNG"
# cho mọi hồ sơ, trong khi bản .284 trên đúng trang đó vẫn $.ajax() tải
# được). Chỉ được GỌI để ĐỢI, không được dùng kết quả để đổi cách gọi.


def _lay_than_ham(ten_ham):
    idx = src.index('def ' + ten_ham + '(')
    idx_ke = src.index('\ndef ', idx + 10)
    than = src[idx:idx_ke]
    # bỏ docstring (chỗ ghi lại bài học có nhắc tên hàm, dễ khớp nhầm)
    return than[than.index('"""', than.index('"""') + 3) + 3:]


def _lay_khoi_js(ten_bien):
    mo_dau = ten_bien + ' = r"""'
    i = src.index(mo_dau) + len(mo_dau)
    return src[i:src.index('"""', i)]


than_download_tdt = _lay_than_ham('_dvc_browser_download_tdt')
than_thongbao = _lay_than_ham('_dvc_browser_thongbao')

# ===== Test 1 (sai lầm 1): TUYỆT ĐỐI không còn cơ chế tự cài $.ajax()
# thay thế jQuery của trang ở bất kỳ đâu trong server.py. =====
for ten_cam in ('_dvc_dam_bao_jquery', '_JS_DAM_BAO_JQUERY'):
    assert ten_cam not in src.replace('# ', ''), (
        f"Không được có lại cơ chế tự cài $.ajax() thay thế ({ten_cam}) — đã thử và hỏng nặng hơn: "
        f"403 Forbidden 22/22 hồ sơ, hỏng luôn nhánh DVC (từ 01/07/2025) vì bản tự cài 'đầu độc' "
        f"trang mà _dvc_browser_download dùng chung.")
print("PASS 1: không còn cơ chế tự cài $.ajax() thay thế jQuery của trang.")

# ===== Test 2 (sai lầm 2): 2 hàm tải PHẢI gọi _dvc_wait_jquery để ĐỢI,
# nhưng KHÔNG được dùng kết quả trả về để rẽ nhánh. =====
for ten, than in (('_dvc_browser_download_tdt', than_download_tdt),
                  ('_dvc_browser_thongbao', than_thongbao)):
    assert '_dvc_wait_jquery(' in than, (
        f"{ten}() phải gọi _dvc_wait_jquery() để ĐỢI script của trang chạy xong — đúng trình tự bản "
        f".284 (bản người dùng xác nhận tải được).")
    assert 'if _dvc_wait_jquery(' not in than and 'if not _dvc_wait_jquery(' not in than, (
        f"{ten}(): KHÔNG được rẽ nhánh theo kết quả _dvc_wait_jquery() — hàm đó trả False cả khi "
        f"trang đã có $ dùng được (đòi thêm window.jQuery), tin vào nó sẽ đi sai đường như bản vừa "
        f"gây lỗi 403 hàng loạt. Chỉ gọi để đợi, rồi cứ gọi $.ajax() như .284.")
print("PASS 2: 2 hàm tải chỉ GỌI _dvc_wait_jquery để đợi, không rẽ nhánh theo kết quả.")

# ===== Test 3 (không hồi quy): cả 3 khối JS tải file vẫn dùng $.ajax()
# của trang (không fetch(), không tự set header CSRF) — đúng bản .284. =====
for ten in ('_JS_DOWNLOAD', '_JS_DOWNLOAD_TDT', '_JS_DOWNLOAD_TB'):
    khoi = _lay_khoi_js(ten)
    assert '$.ajax(' in khoi and 'fetch(' not in khoi, (
        f"{ten} phải dùng $.ajax() của trang (bản fetch() từng gây 403 Forbidden).")
    assert 'X-XSRF-TOKEN' not in khoi, (
        f"{ten} không được tự đoán/set header X-XSRF-TOKEN — để script của trang tự gắn.")
print("PASS 3: cả 3 khối JS tải file đều dùng $.ajax() của trang, không tự set CSRF.")

print("\nALL DONE")
