import os
import re

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test (nguồn + hành vi) — sau khi tờ khai nguồn "thuế điện tử"
# đã tải được (22 dòng/22 file), còn 2 việc người dùng nêu:
#
# 1) Thông báo vẫn chưa tải được. Log mới cho thấy KHÔNG còn "không thấy
#    idTbao" nữa mà là máy chủ trả 500 "Tải file thất bại." — và idTbao
#    gửi đi (11320240228940064) CHÍNH LÀ mã hồ sơ. Tức bộ dò bắt nhầm mã
#    hồ sơ (17 chữ số, nằm đầy trên trang) làm mã thông báo. Trước đây
#    không lộ vì trang chưa nạp được nên không khớp gì cả.
#
# 2) "Tờ khai từ sau 07/2025 nằm ở mục tra cứu hồ sơ đã nộp trên DVC phần
#    mềm chưa tải được": _dvc_browser_download (nhánh DVC) KHÔNG tự mở
#    trang chi tiết mà gọi $.ajax thẳng trên trang hiện tại — trang đó là
#    trang chi tiết do _dvc_browser_thongbao vừa mở, chưa chắc nạp xong
#    script -> "$ is not defined". Nhánh thuế điện tử tự mở trang + đợi
#    nên đã chạy được; nhánh DVC phải làm y hệt.


def _lay_than_ham(ten_ham):
    idx = src.index('def ' + ten_ham + '(')
    idx_ke = src.index('\ndef ', idx + 10)
    return src[idx:idx_ke]


# ===== Test 1 (HÀNH VI — đúng ca thật): _dvc_parse_id_tbao() KHÔNG được
# trả về mã hồ sơ của chính trang đang đọc. =====
ns = {}
exec(compile(_lay_than_ham('_dvc_parse_id_tbao'), '<test>', 'exec'), {}, ns)
parse = ns['_dvc_parse_id_tbao']

MA_HO_SO = '11320240228940064'
ID_TBAO_THAT = '99880011223344'
html_mau = (
    f'<div data-id="{MA_HO_SO}">Mã hồ sơ: {MA_HO_SO}</div>'
    f'<a onclick="downloadThongBao(\'{ID_TBAO_THAT}\')">Tải xuống</a>'
)
ket = parse(html_mau, MA_HO_SO)
assert MA_HO_SO not in ket, (
    f"_dvc_parse_id_tbao() KHÔNG được coi mã hồ sơ ({MA_HO_SO}) là idTbao — gửi nó lên máy chủ gây "
    f"lỗi 500 'Tải file thất bại.' (đúng lỗi thật đã gặp). Kết quả nhận được: {ket}")
assert ID_TBAO_THAT in ket, (
    f"_dvc_parse_id_tbao() vẫn phải nhận ra idTbao THẬT trong trang. Kết quả nhận được: {ket}")
print("PASS 1: bộ dò idTbao loại đúng mã hồ sơ, vẫn nhận ra mã thông báo thật.")

# ===== Test 2 (không hồi quy): nơi gọi phải TRUYỀN mã hồ sơ vào bộ dò,
# nếu không thì việc loại trừ ở Test 1 vô tác dụng. =====
than_thongbao = _lay_than_ham('_dvc_browser_thongbao')
assert re.search(r'_dvc_parse_id_tbao\(\s*html\s*,\s*ma\s*\)', than_thongbao), (
    "_dvc_browser_thongbao() phải gọi _dvc_parse_id_tbao(html, ma) — truyền mã hồ sơ vào để loại "
    "trừ, nếu chỉ gọi _dvc_parse_id_tbao(html) thì vẫn bắt nhầm mã hồ sơ như cũ.")
print("PASS 2: nơi gọi có truyền mã hồ sơ vào bộ dò idTbao.")

# ===== Test 3 (đúng ca thật — tờ khai sau 07/2025): _dvc_browser_download()
# (nhánh DVC) phải TỰ MỞ trang chi tiết hồ sơ và đợi script của trang chạy
# xong trước khi gọi $.ajax — y hệt nhánh thuế điện tử đã chạy được. =====
than_dvc = _lay_than_ham('_dvc_browser_download')
than_dvc_ma = than_dvc[than_dvc.index('"""', than_dvc.index('"""') + 3) + 3:]
assert 'drv.get(' in than_dvc_ma and 'files/detail/' in than_dvc_ma, (
    "_dvc_browser_download() phải tự mở đúng trang chi tiết hồ sơ trước khi tải — gọi $.ajax thẳng "
    "trên trang hiện tại (do _dvc_browser_thongbao để lại) gây '$ is not defined', đúng lỗi 'tờ khai "
    "từ sau 07/2025 chưa tải được'.")
assert '_dvc_wait_jquery(' in than_dvc_ma, (
    "_dvc_browser_download() phải đợi script của trang chạy xong (_dvc_wait_jquery) sau khi mở trang, "
    "y hệt _dvc_browser_download_tdt (cách đã xác nhận tải được).")
assert than_dvc_ma.index('drv.get(') < than_dvc_ma.index('execute_async_script'), (
    "Phải mở trang TRƯỚC rồi mới gọi tải, không được làm ngược lại.")
print("PASS 3: nhánh DVC tự mở trang chi tiết + đợi script trước khi tải, như nhánh thuế điện tử.")

# ===== Test 4 (không hồi quy — người dùng yêu cầu GIỮ NGUYÊN phần đã chạy
# được): _dvc_browser_download_tdt() vẫn giữ đúng trình tự mở trang chi
# tiết ?loai=ETAX + đợi + $.ajax, không bị sửa lây. =====
than_tdt = _lay_than_ham('_dvc_browser_download_tdt')
than_tdt_ma = than_tdt[than_tdt.index('"""', than_tdt.index('"""') + 3) + 3:]
assert 'files/detail/{ma}?loai=ETAX' in than_tdt_ma, (
    "_dvc_browser_download_tdt() phải giữ nguyên việc mở trang chi tiết ?loai=ETAX (phần đã chạy "
    "được, người dùng yêu cầu giữ nguyên).")
assert '_dvc_wait_jquery(drv, 10)' in than_tdt_ma, (
    "_dvc_browser_download_tdt() phải giữ nguyên bước đợi script của trang.")
assert '_dvc_dam_bao_jquery' not in than_tdt_ma, (
    "_dvc_browser_download_tdt() không được quay lại cơ chế tự cài $.ajax (đã gây 403 hàng loạt).")
print("PASS 4: hàm tải tờ khai thuế điện tử (đang chạy được) giữ nguyên, không bị sửa lây.")

print("\nALL DONE")
