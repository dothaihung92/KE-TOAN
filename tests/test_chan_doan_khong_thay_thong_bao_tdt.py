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

# ===== Test 1 (QUAN TRỌNG — đúng ca thật): vòng lặp đọc idTbao trong
# _dvc_browser_thongbao() phải thử LẠI NHIỀU LẦN HƠN (>=4) trước khi kết
# luận "không thấy idTbao" — 2 lần/1.5s có thể chưa đủ cho trang render
# xong khung SPA (cùng nguyên nhân với lỗi jQuery chậm ở bước tải). =====
khoi_doc_id = than_thongbao[:than_thongbao.index('ids = _dvc_parse_id_tbao(html)')]
m_loop = re.search(r'for\s+\w+\s+in\s+range\((\d+)\)', khoi_doc_id)
assert m_loop and int(m_loop.group(1)) >= 4, (
    f"Vòng lặp đọc idTbao trong _dvc_browser_thongbao() phải thử lại ÍT NHẤT 4 lần (tăng từ 2) — "
    f"trang có thể chưa kịp render xong khung SPA ở vài lượt điều hướng, giống nguyên nhân khiến "
    f"jQuery nạp chậm ở bước tải file.")
print(f"PASS 1: vòng lặp đọc idTbao thử lại {m_loop.group(1)} lần (tăng từ 2).")

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
