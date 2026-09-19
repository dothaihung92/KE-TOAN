import os
import re

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test (nguồn) — sau khi bước TẢI FILE nguồn "thuế điện tử" đã
# sửa xong (quay lại $.ajax() bản gốc, tải được file bình thường), người
# dùng tự test thêm ĐỘC LẬP và báo lại: tải theo khoảng 6 THÁNG/đoạn (chọn
# ban đầu để đảm bảo TRA CỨU đủ dòng) vẫn còn thiếu — chỉ khi tải theo
# TỪNG THÁNG mới tải đủ file tờ khai. Yêu cầu rõ: "lấy kỳ từ 01/01/2024
# đến 31/12/2024 thì hãy xử lý từng tháng cho đến hết vì tôi đã test thử
# lấy file từng tháng thì down được file tờ khai".
#
# Đổi _chia_khoang_ngay_thanh_doan(..., so_thang_moi_doan=6) ở
# _dvc_run_batch() (chỉ áp dụng cho nguồn "thuedientu") thành
# so_thang_moi_doan=1 (mỗi đoạn đúng 1 tháng).


def _lay_than_ham(ten_ham):
    idx = src.index('def ' + ten_ham + '(')
    idx_ke = src.index('\ndef ', idx + 10)
    return src[idx:idx_ke]


than_batch = _lay_than_ham('_dvc_run_batch')

# ===== Test 1 (QUAN TRỌNG — đúng yêu cầu mới nhất): lệnh gọi
# _chia_khoang_ngay_thanh_doan cho nguồn "thuedientu" PHẢI dùng
# so_thang_moi_doan=1 (từng tháng), KHÔNG còn 6 tháng/đoạn như trước. =====
m = re.search(r'_chia_khoang_ngay_thanh_doan\([^)]*so_thang_moi_doan=(\d+)\)', than_batch)
assert m, "_dvc_run_batch() phải gọi _chia_khoang_ngay_thanh_doan(tu_tim, den_tim, so_thang_moi_doan=N)."
so_thang = int(m.group(1))
assert so_thang == 1, (
    f"Nguồn 'thuedientu' phải chia đoạn tải theo TỪNG THÁNG (so_thang_moi_doan=1), hiện đang là "
    f"{so_thang} tháng/đoạn — người dùng tự test xác nhận chỉ khi tải theo từng tháng mới tải đủ file "
    f"tờ khai (đoạn rộng hơn vẫn thiếu).")
print(f"PASS 1: nguồn 'thuedientu' chia đoạn tải theo đúng {so_thang} tháng/đoạn (từng tháng).")

# ===== Test 2 (không hồi quy): _chia_khoang_ngay_thanh_doan() bản thân
# hàm vẫn phải hoạt động đúng khi so_thang_moi_doan=1 (mỗi đoạn tách đúng
# 1 tháng dương lịch, không lệch ngày). =====
ns = {}
exec(compile(_lay_than_ham('_chia_khoang_ngay_thanh_doan'), '<test>', 'exec'), {'datetime': __import__('datetime')}, ns)
chia = ns['_chia_khoang_ngay_thanh_doan']
doan = chia("01/01/2024", "31/03/2024", so_thang_moi_doan=1)
assert doan == [("01/01/2024", "31/01/2024"), ("01/02/2024", "29/02/2024"), ("01/03/2024", "31/03/2024")], (
    f"_chia_khoang_ngay_thanh_doan('01/01/2024','31/03/2024', so_thang_moi_doan=1) phải trả về 3 đoạn "
    f"đúng từng tháng dương lịch (kể cả tháng 2 nhuận 29 ngày), nhận được: {doan}")
print("PASS 2: _chia_khoang_ngay_thanh_doan() với so_thang_moi_doan=1 tách đúng từng tháng dương lịch.")

print("\nALL DONE")
