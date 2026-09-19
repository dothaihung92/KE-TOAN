import datetime
import os
import re

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test (nguồn + hành vi) — người dùng báo "từ sau T7/2025 (mục
# tra cứu hồ sơ đã nộp trên DVC) phần mềm chưa tải được". File Excel xuất
# ra cho thấy đây KHÔNG phải lỗi tải mà là lỗi TRA CỨU: nguồn DVC trả về
# đúng 1 dòng đánh dấu "(Chưa tìm thấy tờ khai trong kỳ — nguồn DVC)" /
# "CHƯA NỘP TỜ KHAI" cho cả khoảng 01/01/2024-31/12/2025, tức không ra
# dòng nào, trong khi công ty có nộp tờ khai sau 01/07/2025.
#
# 2 nguyên nhân: (1) nguồn DVC bị tra NGUYÊN khoảng 2 năm trong 1 lần —
# đúng kiểu giới hạn khoảng ngày RỘNG đã gặp ở nguồn "thuedientu" (chia
# theo tháng mới ra đủ); (2) khoảng tra còn gồm cả phần TRƯỚC mốc chuyển
# hệ thống 01/07/2025, trong khi nguồn DVC chỉ có dữ liệu từ mốc đó trở
# đi — vừa vô ích vừa kéo dài thời gian chạy.


def _lay_than_ham(ten_ham):
    idx = src.index('def ' + ten_ham + '(')
    idx_ke = src.index('\ndef ', idx + 10)
    return src[idx:idx_ke]


ns = {'datetime': datetime}
for _ten in ('_ngay_dmy_nho_hon', '_chia_khoang_ngay_thanh_doan'):
    exec(compile(_lay_than_ham(_ten), '<test>', 'exec'), ns, ns)

# ===== Test 1 (HÀNH VI): _ngay_dmy_nho_hon so sánh đúng ngày dd/mm/yyyy,
# kể cả khi chuỗi hỏng (không được ném lỗi làm chết cả lượt chạy). =====
assert ns['_ngay_dmy_nho_hon']('01/01/2024', '01/07/2025') is True
assert ns['_ngay_dmy_nho_hon']('01/07/2025', '01/07/2025') is False
assert ns['_ngay_dmy_nho_hon']('31/12/2025', '01/07/2025') is False
assert ns['_ngay_dmy_nho_hon']('', '01/07/2025') is False
assert ns['_ngay_dmy_nho_hon']('linh tinh', '01/07/2025') is False
print("PASS 1: _ngay_dmy_nho_hon so sánh đúng, chuỗi hỏng trả False (không ném lỗi).")

# ===== Test 2 (QUAN TRỌNG — đúng ca thật): nguồn "dvc" PHẢI được chia
# theo từng tháng như nguồn "thuedientu", KHÔNG còn nhánh tra nguyên
# khoảng trong 1 lần. =====
than_batch = _lay_than_ham('_dvc_run_batch')
assert not re.search(r'cac_doan = \[\(tu_tim, den_tim\)\]', than_batch), (
    "Không được còn nhánh tra cứu NGUYÊN khoảng trong 1 lần cho nguồn 'dvc' — tra cả 01/01/2024-"
    "31/12/2025 một lần đã trả về KHÔNG DÒNG NÀO (báo cáo thật), phải chia theo tháng như nguồn "
    "'thuedientu'.")
assert re.search(r'cac_doan = _chia_khoang_ngay_thanh_doan\([^)]*so_thang_moi_doan=1\)', than_batch), (
    "Cả 2 nguồn phải dùng _chia_khoang_ngay_thanh_doan(..., so_thang_moi_doan=1) — chia theo từng "
    "tháng (đúng yêu cầu người dùng và đúng cách đã giúp nguồn 'thuedientu' ra đủ dòng).")
print("PASS 2: nguồn DVC cũng được chia tra cứu theo từng tháng.")

# ===== Test 3 (QUAN TRỌNG — đúng ca thật): với nguồn "dvc", ngày bắt đầu
# tra cứu PHẢI được cắt về mốc chuyển hệ thống (01/07/2025) nếu người dùng
# chọn khoảng bắt đầu sớm hơn. =====
assert re.search(r'if ngu == "dvc":', than_batch), (
    "Phải có nhánh xử lý riêng cho nguồn 'dvc' để cắt ngày bắt đầu về mốc chuyển hệ thống.")
khoi_dvc = than_batch[than_batch.index('if ngu == "dvc":'):]
khoi_dvc = khoi_dvc[:khoi_dvc.index('cac_doan =')]
assert '_DVC_MOC_CHUYEN_HE_THONG' in khoi_dvc and '_ngay_dmy_nho_hon' in khoi_dvc, (
    "Nguồn 'dvc' phải cắt ngày bắt đầu về _DVC_MOC_CHUYEN_HE_THONG (01/07/2025) khi người dùng chọn "
    "khoảng bắt đầu sớm hơn — nguồn này không có dữ liệu trước mốc đó.")
print("PASS 3: nguồn DVC cắt ngày bắt đầu về mốc 01/07/2025.")

# ===== Test 4 (HÀNH VI — kết quả cuối): khoảng 01/01/2024-31/12/2025 với
# nguồn DVC phải ra đúng 6 đoạn tháng 07..12/2025, không còn 1 đoạn 2 năm.
# =====
moc = datetime.date(2025, 7, 1).strftime('%d/%m/%Y')
tu = '01/01/2024'
tu_ng = moc if ns['_ngay_dmy_nho_hon'](tu, moc) else tu
doan = ns['_chia_khoang_ngay_thanh_doan'](tu_ng, '31/12/2025', so_thang_moi_doan=1)
assert len(doan) == 6, f"Phải ra 6 đoạn tháng (07..12/2025), nhận được {len(doan)}: {doan}"
assert doan[0] == ('01/07/2025', '31/07/2025'), f"Đoạn đầu phải bắt đầu từ mốc 01/07/2025: {doan[0]}"
assert doan[-1] == ('01/12/2025', '31/12/2025'), f"Đoạn cuối phải là tháng 12/2025: {doan[-1]}"
print("PASS 4: khoảng 2 năm -> đúng 6 đoạn tháng 07..12/2025 cho nguồn DVC.")

print("\nALL DONE")
