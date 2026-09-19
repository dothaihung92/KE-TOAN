import os
import re

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test (nguồn) — mục "Danh sách thông báo" CÓ TỒN TẠI trên
# trang chi tiết hồ sơ (ảnh chụp trang thật của người dùng xác nhận), và
# bản code cũ từng tải được cả Thông báo cho 2024-2025. Nhưng phần mềm
# đọc trang lại không dò ra mã thông báo nào.
#
# Nguyên nhân: mục đó do chính script của trang gọi thêm rồi mới vẽ ra,
# XONG SAU cả lúc jQuery đã sẵn sàng. _dvc_wait_jquery() trả về ngay khi
# jQuery vừa có (thường 1-2 giây), đọc page_source ngay lúc đó thì mục
# thông báo chưa kịp hiện -> kết luận nhầm "CQT chưa phát hành".
#
# Sửa: đọc lại trang nhiều lần cho tới khi dò được mã thông báo (tối đa
# ~8 giây) rồi mới chịu thua.


def _than_ma(ten_ham):
    i = src.index('def ' + ten_ham + '(')
    j = src.index('\ndef ', i + 10)
    than = src[i:j]
    return than[than.index('"""', than.index('"""') + 3) + 3:]


than = _than_ma('_dvc_browser_thongbao')
truoc_ids = than[:re.search(r'^    ids = _dvc_parse_id_tbao\(', than, re.M).start()]

# ===== Test 1 (QUAN TRỌNG — đúng ca thật): phải ĐỌC LẠI trang nhiều lần
# chờ mục thông báo hiện ra, không được đọc page_source đúng 1 lần rồi
# kết luận luôn. =====
so_lan_doc = len(re.findall(r'drv\.page_source', truoc_ids))
assert so_lan_doc >= 2, (
    f"_dvc_browser_thongbao() phải đọc lại trang nhiều lần trong lúc chờ mục 'Danh sách thông báo' "
    f"hiện ra — hiện chỉ đọc {so_lan_doc} lần. Mục này do script của trang vẽ ra SAU khi jQuery đã "
    f"sẵn sàng, đọc đúng 1 lần ngay lúc đó sẽ luôn thấy rỗng và báo nhầm 'CQT chưa phát hành'.")
assert re.search(r'for\s+\w+\s+in\s+range\(\d+\)', truoc_ids), (
    "Phải có vòng lặp chờ/đọc lại trang trước khi kết luận không có thông báo.")
print(f"PASS 1: có vòng lặp đọc lại trang ({so_lan_doc} chỗ đọc page_source) trong lúc chờ.")

# ===== Test 2 (đúng ca thật): điều kiện dừng chờ phải là ĐÃ DÒ RA mã
# thông báo, không phải chỉ chờ hết thời gian cố định. =====
m_vong = re.search(r'for\s+\w+\s+in\s+range\(\d+\):(?:.|\n){0,400}', truoc_ids)
assert m_vong and '_dvc_parse_id_tbao(' in m_vong.group(0) and 'break' in m_vong.group(0), (
    "Vòng lặp chờ phải dừng NGAY khi dò được mã thông báo (_dvc_parse_id_tbao ... break) — chờ đủ "
    "thời gian cố định sẽ làm chậm mọi hồ sơ thật sự không có thông báo.")
print("PASS 2: dừng chờ ngay khi dò được mã thông báo (không chờ cứng đủ thời gian).")

# ===== Test 3 (không hồi quy): vẫn phải đợi script của trang chạy xong
# (_dvc_wait_jquery) trước khi đọc — phần đã xác nhận đúng ở bản .284. =====
assert '_dvc_wait_jquery(' in truoc_ids, (
    "Vẫn phải gọi _dvc_wait_jquery() trước khi đọc trang (trình tự đúng của bản .284).")
assert truoc_ids.index('_dvc_wait_jquery(') < truoc_ids.index('drv.page_source'), (
    "Phải đợi script của trang TRƯỚC rồi mới đọc trang.")
print("PASS 3: vẫn giữ bước đợi script của trang trước khi đọc (đúng bản .284).")

print("\nALL DONE")
