import os
import re

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test (nguồn) — vòng thứ 10 sửa lỗi tải file nguồn "thuế điện
# tử". 2 vòng liền trước (9: đọc CSRF từ thẻ meta; 10 chẩn đoán: thêm
# csrfSrc/csrfLen/hasWebdriver vào log lỗi) đều đi sai hướng — người dùng
# chỉ ra: hồ sơ ĐẦU TIÊN trong 1 lượt chạy vẫn tải THÀNH CÔNG (log cũ "✓
# Lấy được: 1") bằng đúng cơ chế cookie/token cũ, chỉ các hồ sơ SAU ĐÓ
# trong CÙNG lượt chạy mới bị 403 liên tục — chứng tỏ cơ chế lấy token
# không sai, mà nhiều khả năng do gọi tải liên tiếp quá nhanh (trước đây
# chỉ nghỉ 0.3s/hồ sơ) bị cổng tạm chặn.
#
# Sửa: tăng thời gian nghỉ giữa các lượt tải liên tiếp CHỈ cho nguồn "thuế
# điện tử" (nguồn DVC vẫn tải bình thường, giữ nguyên 0.3s, không đổi để
# tránh làm chậm không cần thiết phần đang hoạt động tốt).


def _lay_than_ham(ten_ham):
    idx = src.index('def ' + ten_ham + '(')
    idx_ke = src.index('\ndef ', idx + 10)
    return src[idx:idx_ke]


than_batch = _lay_than_ham('_dvc_run_batch')

# ===== Test 1 (QUAN TRỌNG — đúng ca thật, vòng thứ 10): nhánh nguồn
# "thuedientu" PHẢI đặt thời gian nghỉ giữa các lượt tải (_nghi_giua_tai)
# LỚN HƠN nhánh nguồn "dvc" — log thật cho thấy tải liên tiếp quá nhanh
# là nguyên nhân khả dĩ nhất gây 403 hàng loạt sau hồ sơ đầu tiên. =====
assert '_nghi_giua_tai' in than_batch, (
    "_dvc_run_batch() phải có biến nghỉ giữa các lượt tải (_nghi_giua_tai) tách riêng theo từng nguồn.")
idx_thuedientu = than_batch.index('if ngu == "thuedientu"')
idx_else = than_batch.index('\n                else:', idx_thuedientu)
khoi_thuedientu = than_batch[idx_thuedientu:idx_else]
# Khối else (nguồn dvc) — lấy 800 ký tự sau đó là đủ để chứa dòng gán biến.
khoi_dvc = than_batch[idx_else:idx_else + 800]

m_tdt = re.search(r'_nghi_giua_tai\s*=\s*([\d.]+)', khoi_thuedientu)
m_dvc = re.search(r'_nghi_giua_tai\s*=\s*([\d.]+)', khoi_dvc)
assert m_tdt, "Nhánh nguồn 'thuedientu' phải gán _nghi_giua_tai."
assert m_dvc, "Nhánh nguồn 'dvc' (else) phải gán _nghi_giua_tai."
gia_tri_tdt = float(m_tdt.group(1))
gia_tri_dvc = float(m_dvc.group(1))
assert gia_tri_tdt > gia_tri_dvc, (
    f"Nguồn 'thuedientu' (_nghi_giua_tai={gia_tri_tdt}) phải nghỉ LÂU HƠN nguồn 'dvc' "
    f"(_nghi_giua_tai={gia_tri_dvc}) — log thật cho thấy tải liên tiếp quá nhanh khả năng cao gây 403 "
    f"hàng loạt sau hồ sơ đầu tiên, trong khi nguồn DVC vẫn tải bình thường ở tốc độ cũ nên không đổi.")
assert gia_tri_tdt >= 2.0, (
    f"_nghi_giua_tai cho nguồn 'thuedientu' ({gia_tri_tdt}s) có vẻ vẫn còn quá ngắn để tránh bị chặn.")
print(f"PASS 1: nguồn 'thuedientu' nghỉ {gia_tri_tdt}s/hồ sơ (dài hơn hẳn nguồn 'dvc' {gia_tri_dvc}s).")

# ===== Test 2 (không hồi quy): cả 2 vòng lặp tải file (theo rows và theo
# ma_list dự phòng) đều PHẢI dùng biến _nghi_giua_tai thay vì số cứng
# 0.3 như trước — nếu còn số cứng, nguồn thuedientu sẽ KHÔNG được hưởng
# thời gian nghỉ dài hơn vừa thêm. =====
so_lan_dung_bien = than_batch.count('time.sleep(_nghi_giua_tai)')
assert so_lan_dung_bien >= 2, (
    f"Cả 2 vòng lặp tải file (theo rows và theo ma_list dự phòng) đều phải dùng "
    f"time.sleep(_nghi_giua_tai) — hiện chỉ thấy {so_lan_dung_bien} chỗ dùng, có thể còn sót số cứng "
    f"0.3 khiến nguồn thuedientu vẫn tải nhanh như cũ.")
print(f"PASS 2: cả 2 vòng lặp tải file đều dùng time.sleep(_nghi_giua_tai) ({so_lan_dung_bien} chỗ).")

print("\nALL DONE")
