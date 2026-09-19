import os
import re

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test (nguồn) — người dùng nghi ngờ: "tải nhiều tháng phần
# mềm báo ko tìm thấy thông báo thuế là sẽ ko tải được file" — tức "không
# thấy idTbao" và lỗi "$ is not defined" ở bước tải file CÙNG hồ sơ có thể
# CÙNG 1 nguyên nhân (trang chưa kịp khởi động xong khung SPA ở lượt điều
# hướng đó), không hẳn là CQT chưa phát hành thông báo như vẫn ghi chú.
#
# 2 thay đổi: (1) tăng số lần/thời gian thử lại đọc idTbao (2 lần/1.5s ->
# 4 lần/2.5s), giống mức tăng đã áp dụng cho bước tải file; (2) đính kèm
# trạng thái jQuery lúc không tìm thấy idTbao vào chẩn đoán, và THỰC SỰ
# hiện ra cho người dùng (trước đó _dvc_run_batch() gọi
# _dvc_browser_thongbao() nhưng VỨT BỎ giá trị diag trả về — dù hàm có
# trả về gợi ý gì cũng không ai thấy được) để xác nhận/bác bỏ nghi ngờ.


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
khoi_doc_id = than_thongbao[:than_thongbao.index('ids = _dvc_parse_id_tbao(html)')]
assert '_dvc_wait_jquery(' in khoi_doc_id, (
    "_dvc_browser_thongbao() phải gọi _dvc_wait_jquery() TRƯỚC khi đọc page_source để dò idTbao — "
    "đọc khi script của trang chưa chạy xong sẽ thấy trang rỗng và báo nhầm 'không tìm thấy Thông "
    "báo' hàng loạt (đúng lỗi đã xảy ra khi gỡ bước đợi này).")
assert khoi_doc_id.index('_dvc_wait_jquery(') < khoi_doc_id.index('drv.page_source'), (
    "Phải ĐỢI jQuery TRƯỚC rồi mới đọc drv.page_source, không được làm ngược lại.")
print("PASS 1: đợi jQuery thật nạp xong rồi mới đọc trang để dò idTbao.")

# ===== Test 2 (QUAN TRỌNG — đúng ca thật): khi không thấy idTbao, PHẢI
# ghi kèm trạng thái jQuery lúc đó vào thông điệp diag trả về — để biết
# có đúng cùng nguyên nhân với lỗi tải file hay không. =====
idx_khong_thay = than_thongbao.index("không thấy idTbao")
doan_quanh = than_thongbao[max(0, idx_khong_thay - 400):idx_khong_thay + 100]
assert 'jquery' in doan_quanh.lower(), (
    "Thông điệp 'không thấy idTbao' phải kèm trạng thái jQuery lúc đó (có/không) để xác nhận/bác bỏ "
    "nghi ngờ của người dùng rằng 2 lỗi cùng 1 nguyên nhân.")
print("PASS 2: thông điệp 'không thấy idTbao' kèm trạng thái jQuery lúc đó.")

# ===== Test 3 (QUAN TRỌNG — đúng ca thật, không hồi quy): _dvc_run_batch()
# PHẢI thực sự LẤY và HIỂN THỊ giá trị diag trả về từ _dvc_browser_thongbao()
# vào khong_co_tb_mau — trước đó bị vứt bỏ (gán vào biến "_"), khiến chẩn
# đoán dù có thêm cũng không ai thấy được. =====
assert 'tb_files, tb_diag = _dvc_browser_thongbao(' in than_batch, (
    "_dvc_run_batch() phải lấy giá trị diag trả về từ _dvc_browser_thongbao() (không được vứt bỏ vào "
    "biến '_') để hiển thị chẩn đoán jQuery ra cho người dùng thấy.")
assert 'tb_diag' in than_batch[than_batch.index('tb_files, tb_diag ='):than_batch.index('tb_files, tb_diag =') + 800], (
    "_dvc_run_batch() phải dùng biến tb_diag (vd đưa vào khong_co_tb_mau) chứ không chỉ lấy ra rồi bỏ "
    "không dùng.")
print("PASS 3: _dvc_run_batch() lấy và hiển thị chẩn đoán diag từ _dvc_browser_thongbao().")

print("\nALL DONE")
