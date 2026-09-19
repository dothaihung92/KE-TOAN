import os
import re

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test (nguồn) — người dùng nghi ngờ ĐÚNG: "tải nhiều tháng
# phần mềm báo ko tìm thấy thông báo thuế là sẽ ko tải được file" — cả 2
# cùng 1 gốc: ĐỌC/GỌI KHI SCRIPT CỦA TRANG CHƯA CHẠY XONG. Mục "Danh sách
# thông báo" do chính script của trang render ra SAU khi HTML tải xong,
# nên phải đợi rồi mới đọc page_source; không hẳn là CQT chưa phát hành.
#
# Test này khoá 2 điểm: (1) đợi script của trang chạy xong rồi mới đọc
# trang để dò idTbao (đúng trình tự bản .284 — bản người dùng xác nhận
# chạy được); (2) _dvc_run_batch() phải thực sự HIỂN THỊ diag trả về từ
# _dvc_browser_thongbao() (trước đó vứt bỏ vào biến "_", nên hàm có trả
# về gợi ý gì cũng không ai thấy).


def _lay_than_ham(ten_ham):
    idx = src.index('def ' + ten_ham + '(')
    idx_ke = src.index('\ndef ', idx + 10)
    return src[idx:idx_ke]


than_thongbao = _lay_than_ham('_dvc_browser_thongbao')
than_batch = _lay_than_ham('_dvc_run_batch')

# ===== Test 1 (QUAN TRỌNG — đúng ca thật): PHẢI đợi jQuery thật nạp xong
# RỒI MỚI đọc page_source để dò idTbao — mục "Danh sách thông báo" do
# chính script của trang render ra SAU khi HTML tải xong, đọc sớm sẽ thấy
# rỗng và kết luận nhầm "CQT chưa phát hành thông báo". Bản gỡ bước đợi
# này đi (thay bằng sleep cứng + thử lại nhiều lần) đã báo "không tìm
# thấy Thông báo" hàng loạt; bản .284 có bước đợi thì dò được bình
# thường. =====
khoi_doc_id = than_thongbao[:re.search(r'ids = _dvc_parse_id_tbao\(', than_thongbao).start()]
assert '_dvc_wait_jquery(' in khoi_doc_id, (
    "_dvc_browser_thongbao() phải gọi _dvc_wait_jquery() TRƯỚC khi đọc page_source để dò idTbao — "
    "đọc khi script của trang chưa chạy xong sẽ thấy trang rỗng và báo nhầm 'không tìm thấy Thông "
    "báo' hàng loạt (đúng lỗi đã xảy ra khi gỡ bước đợi này).")
assert khoi_doc_id.index('_dvc_wait_jquery(') < khoi_doc_id.index('drv.page_source'), (
    "Phải ĐỢI jQuery TRƯỚC rồi mới đọc drv.page_source, không được làm ngược lại.")
print("PASS 1: đợi jQuery thật nạp xong rồi mới đọc trang để dò idTbao.")

# (Đã bỏ phần kiểm tra "ghi kèm trạng thái jQuery vào thông điệp không
# thấy idTbao": chẩn đoán đó GÂY HIỂU NHẦM — nó báo "jQuery lúc đó:
# KHÔNG" cho mọi hồ sơ vì _dvc_wait_jquery đòi cả window.jQuery, trong
# khi trang thật sự vẫn có $ dùng được và bản .284 vẫn tải được bình
# thường. Tin vào chẩn đoán đó đã dẫn tới bản sửa sai gây 403 hàng loạt.)

# ===== Test 2 (QUAN TRỌNG — đúng ca thật, không hồi quy): _dvc_run_batch()
# PHẢI thực sự LẤY và HIỂN THỊ giá trị diag trả về từ _dvc_browser_thongbao()
# vào khong_co_tb_mau — trước đó bị vứt bỏ (gán vào biến "_"), khiến chẩn
# đoán dù có thêm cũng không ai thấy được. =====
assert 'tb_files, tb_diag = _dvc_browser_thongbao(' in than_batch, (
    "_dvc_run_batch() phải lấy giá trị diag trả về từ _dvc_browser_thongbao() (không được vứt bỏ vào "
    "biến '_') để hiển thị chẩn đoán jQuery ra cho người dùng thấy.")
assert 'tb_diag' in than_batch[than_batch.index('tb_files, tb_diag ='):than_batch.index('tb_files, tb_diag =') + 800], (
    "_dvc_run_batch() phải dùng biến tb_diag (vd đưa vào khong_co_tb_mau) chứ không chỉ lấy ra rồi bỏ "
    "không dùng.")
print("PASS 2: _dvc_run_batch() lấy và hiển thị chẩn đoán diag từ _dvc_browser_thongbao().")

print("\nALL DONE")
