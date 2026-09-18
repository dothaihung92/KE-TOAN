import os
import re

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test (nguồn) — người dùng test thêm sau khi có bản thử lại
# jQuery (tối đa 3 lần): tra/tải 1 THÁNG lẻ luôn tải được, nhưng chạy LIÊN
# TỤC 12 tháng (đúng kịch bản chia đoạn theo tháng) vẫn báo lỗi "$ is not
# defined" hàng loạt ở bước tải file — dù đã thử lại nhiều lần. Kết luận:
# phiên trình duyệt CÀNG CHẠY LÂU (nhiều lượt tra cứu liên tiếp trước đó)
# CÀNG DỄ gặp lỗi nạp jQuery chậm ở bước tải, khác hẳn 1 lượt tra cứu đơn
# lẻ.
#
# 2 thay đổi: (1) tăng độ kiên nhẫn thử lại (3->5 lần, 10s->15s/lần) ở cả
# _dvc_browser_download_tdt và _dvc_browser_thongbao; (2) nghỉ 3s TRƯỚC
# KHI bắt đầu bước tải file, CHỈ khi vừa tra cứu NHIỀU đoạn liên tiếp
# (chia theo tháng) — cho trình duyệt "hạ nhiệt" trước bước tải nặng hơn.


def _lay_than_ham(ten_ham):
    idx = src.index('def ' + ten_ham + '(')
    idx_ke = src.index('\ndef ', idx + 10)
    return src[idx:idx_ke]


than_download_tdt = _lay_than_ham('_dvc_browser_download_tdt')
than_thongbao = _lay_than_ham('_dvc_browser_thongbao')
than_batch = _lay_than_ham('_dvc_run_batch')

# ===== Test 1 (QUAN TRỌNG — đúng ca thật): độ kiên nhẫn thử lại jQuery
# PHẢI tăng lên (>= 5 lần thử, >= 15s/lần) ở cả 2 hàm tải — 3 lần/10s
# (bản trước) không đủ cho phiên trình duyệt đã chạy lâu (nhiều tháng liên
# tiếp). =====
khoi_jq_thongbao = than_thongbao[than_thongbao.index('_dvc_wait_jquery'):]
for ten, than in (('_dvc_browser_download_tdt', than_download_tdt), ('_dvc_browser_thongbao', khoi_jq_thongbao)):
    m_loop = re.search(r'for\s+\w+\s+in\s+range\((\d+)\)', than)
    assert m_loop and int(m_loop.group(1)) >= 4, (
        f"{ten}() phải thử lại jQuery ÍT NHẤT 5 lần tổng cộng (vòng lặp range >= 4, cộng 1 lần thử "
        f"ban đầu trước vòng lặp) — phiên trình duyệt chạy lâu (nhiều tháng liên tiếp) cần kiên nhẫn "
        f"hơn 1 lượt tra cứu đơn lẻ.")
    gs = [int(x) for x in re.findall(r'_dvc_wait_jquery\(drv,\s*(\d+)\)', than)]
    assert gs and min(gs) >= 15, (
        f"{ten}(): thời gian đợi mỗi lần _dvc_wait_jquery() phải >= 15 giây (tăng từ 10s), hiện thấy "
        f"{gs}.")
print("PASS 1: cả 2 hàm tải đều tăng độ kiên nhẫn thử lại jQuery (>=5 lần, >=15s/lần).")

# ===== Test 2 (QUAN TRỌNG — đúng ca thật): _dvc_run_batch() PHẢI nghỉ 1
# chút TRƯỚC KHI bắt đầu bước tải file, CHỈ khi vừa tra cứu NHIỀU đoạn
# liên tiếp (len(cac_doan) > 1, tức nguồn 'thuedientu' chia theo tháng) —
# không áp dụng khi chỉ có 1 đoạn (nguồn 'dvc' hoặc khoảng ngày hẹp). =====
idx_tai_file = than_batch.index('if tai_file and ma_list:')
doan_truoc = than_batch[max(0, idx_tai_file - 700):idx_tai_file]
assert 'len(cac_doan) > 1' in doan_truoc and 'time.sleep(' in doan_truoc, (
    "_dvc_run_batch() phải nghỉ 1 chút (time.sleep) TRƯỚC bước tải file, chỉ khi vừa tra cứu NHIỀU "
    "đoạn liên tiếp (len(cac_doan) > 1) — cho trình duyệt 'hạ nhiệt' trước bước tải nặng hơn, đúng "
    "nguyên nhân người dùng xác nhận (phiên chạy lâu dễ lỗi hơn 1 lượt lẻ).")
print("PASS 2: _dvc_run_batch() nghỉ trước bước tải file khi vừa tra cứu nhiều đoạn liên tiếp.")

print("\nALL DONE")
