import os
import re

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test (nguồn + hành vi) — tải Thông báo cho hồ sơ nguồn "thuế
# điện tử" (trước 01/07/2025).
#
# Báo cáo thật cho thấy trang chi tiết KHÔNG có idTbao nào: thứ duy nhất
# khớp chữ "thông báo" trong HTML là LINK MENU /tthc/tra-cuu-thongbao-cqt.
# Sở dĩ trước đó chỉ thấy link menu là vì mẫu dò cũ (a) viết "hong báo"
# KHÔNG DẤU MŨ nên không khớp chữ "thông báo" thật, và (b) chỉ lấy lần
# khớp ĐẦU TIÊN nên luôn trúng link menu nằm ở đầu trang.
#
# 2 thay đổi: (1) thử tải Thông báo theo MÃ HỒ SƠ qua endpoint đúng quy
# ước của chính API này (tờ khai ETAX dùng /downloadhoso-tdt?loaiTraCuu=
# ETAX và đã tải được -> Thông báo thử /downloadthongbao-tdt?loaiTraCuu=
# ETAX), ghi lại nguyên phản hồi máy chủ để biết đúng/sai; (2) sửa đoạn
# gợi ý để trỏ đúng mục "Danh sách thông báo" thay vì link menu.


def _lay_than_ham(ten_ham):
    idx = src.index('def ' + ten_ham + '(')
    idx_ke = src.index('\ndef ', idx + 10)
    return src[idx:idx_ke]


def _lay_khoi_js(ten_bien):
    mo_dau = ten_bien + ' = r"""'
    i = src.index(mo_dau) + len(mo_dau)
    return src[i:src.index('"""', i)]


than_thongbao = _lay_than_ham('_dvc_browser_thongbao')

# ===== Test 1 (đúng ca thật): phải có khối JS tải Thông báo cho nguồn
# ETAX theo đúng quy ước endpoint của tờ khai ETAX (đã xác nhận tải
# được) — cùng dùng $.ajax của trang, không fetch(), không tự đoán CSRF.
# =====
khoi_tb_tdt = _lay_khoi_js('_JS_DOWNLOAD_TB_TDT')
assert 'downloadthongbao-tdt' in khoi_tb_tdt and 'loaiTraCuu=ETAX' in khoi_tb_tdt, (
    "_JS_DOWNLOAD_TB_TDT phải gọi /tthc/tchs/downloadthongbao-tdt?loaiTraCuu=ETAX — đúng quy ước mà "
    "API này dùng cho tờ khai nguồn ETAX (/downloadhoso-tdt?loaiTraCuu=ETAX, đã xác nhận tải được).")
assert '$.ajax(' in khoi_tb_tdt and 'fetch(' not in khoi_tb_tdt, (
    "_JS_DOWNLOAD_TB_TDT phải dùng $.ajax của trang (fetch() từng gây 403 Forbidden).")
assert 'X-XSRF-TOKEN' not in khoi_tb_tdt, (
    "_JS_DOWNLOAD_TB_TDT không được tự đoán/set header CSRF — để script của trang tự gắn.")
print("PASS 1: có khối JS tải Thông báo nguồn ETAX đúng quy ước endpoint, dùng $.ajax của trang.")

# ===== Test 2 (đúng ca thật): _dvc_browser_thongbao() phải thử cách tải
# theo MÃ HỒ SƠ khi không dò được idTbao và hồ sơ thuộc nguồn ETAX. =====
assert '_JS_DOWNLOAD_TB_TDT' in than_thongbao, (
    "_dvc_browser_thongbao() phải thử _JS_DOWNLOAD_TB_TDT khi không dò được idTbao cho hồ sơ nguồn "
    "ETAX — trang chi tiết không hề có idTbao nên chỉ dò HTML thì không bao giờ tải được Thông báo.")
assert re.search(r'if not ids and str\(loai\)\.upper\(\) == "ETAX"', than_thongbao), (
    "Chỉ thử cách theo mã hồ sơ khi KHÔNG dò được idTbao VÀ đúng nguồn ETAX — không được áp dụng "
    "cho nguồn DVC (nguồn đó vẫn dùng idTbao như cũ).")
assert 'maHoSo' in than_thongbao, "Phải gửi tham số maHoSo khi tải Thông báo theo mã hồ sơ."
print("PASS 2: khi không có idTbao và đúng nguồn ETAX thì thử tải Thông báo theo mã hồ sơ.")

# ===== Test 3 (không hồi quy): nguồn DVC vẫn tải Thông báo theo idTbao
# qua endpoint cũ — không bị đổi lây. =====
khoi_tb = _lay_khoi_js('_JS_DOWNLOAD_TB')
assert "url:'/tthc/tchs/downloadthongbao'" in khoi_tb, (
    "_JS_DOWNLOAD_TB (dùng cho idTbao, gồm cả nguồn DVC) phải giữ nguyên endpoint cũ.")
assert 'idTbao' in than_thongbao, "Vẫn phải giữ đường tải theo idTbao cho các hồ sơ dò được."
print("PASS 3: đường tải Thông báo theo idTbao (nguồn DVC) giữ nguyên.")

# ===== Test 4 (HÀNH VI): đoạn gợi ý khi không thấy idTbao phải trỏ đúng
# mục "Danh sách thông báo", KHÔNG trúng link menu tra-cuu-thongbao-cqt
# nằm đầu trang (đúng lỗi của mẫu dò cũ). =====
assert 'finditer' in than_thongbao and 'Danh sách' in than_thongbao, (
    "Phải duyệt MỌI chỗ nhắc 'thông báo' và ưu tiên chỗ gần 'Danh sách'/'Tải' — mẫu cũ chỉ lấy lần "
    "khớp đầu tiên nên luôn trúng link menu ở đầu trang.")

html_mau = ('<a style="align-items: center;" href="/tthc/tra-cuu-thongbao-cqt">Tra cuu</a>'
            + 'x' * 400
            + '<div><label>Danh sách thông báo</label>'
              '<a onclick="taiTB(\'99880011223344\')">Tải xuống</a></div>')
ung_vien = [m for m in re.finditer(r'[Tt]h[ôo]ng\s*b[áa]o', html_mau)]
chon = None
for m in ung_vien:
    quanh = html_mau[max(0, m.start() - 120):m.start() + 200]
    if 'Danh sách' in quanh or 'Tải' in quanh or 'ownload' in quanh:
        chon = m
        break
assert chon is not None, "Phải chọn được chỗ nhắc 'thông báo' nằm trong mục Danh sách thông báo."
goi_y = html_mau[max(0, chon.start() - 110):chon.start() + 190]
assert 'Danh sách thông báo' in goi_y and 'tra-cuu-thongbao-cqt' not in goi_y, (
    f"Đoạn gợi ý phải là mục 'Danh sách thông báo' thật, không phải link menu. Nhận được: {goi_y[:120]}")
print("PASS 4: đoạn gợi ý trỏ đúng mục 'Danh sách thông báo', không trúng link menu.")

print("\nALL DONE")
