import ast
import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DUONG_DAN = os.path.join(_REPO_ROOT, 'server.py')
cay = ast.parse(open(_DUONG_DAN, encoding='utf-8').read())

# Regression test (nguồn) — người dùng xác nhận bằng thực nghiệm: tra/tải 1
# THÁNG lẻ thì TẢI ĐƯỢC, nhưng chọn cả năm (chia 12-24 đoạn tháng) thì báo
# "$ is not defined" hàng loạt ở bước tải file.
#
# Log thật chỉ ra chỗ khác biệt: bước TRA CỨU vẫn chạy tốt tới đoạn cuối
# (24/24) — mà tra cứu bắt buộc phải nạp được jQuery trên trang /tchs mới
# chạy được — nên trình duyệt và phiên đăng nhập VẪN KHOẺ, chỉ riêng TRANG
# CHI TIẾT hồ sơ là không nạp được script sau quá nhiều lượt điều hướng
# liên tiếp. Bản .284 (người dùng xác nhận tải được) chỉ tra 1 lượt rồi
# tải ngay nên luôn ở điều kiện "vừa tra xong đã tải".
#
# Vì vậy: TẢI NGAY sau mỗi đoạn vừa tra cứu xong, KHÔNG gom hết mọi đoạn
# rồi mới tải ở cuối.


def _tim_ham(ten):
    for nut in ast.walk(cay):
        if isinstance(nut, (ast.FunctionDef, ast.AsyncFunctionDef)) and nut.name == ten:
            return nut
    return None


def _tim_vong_lap_doan(goc):
    """Vòng lặp chạy qua từng đoạn ngày (for _idx_doan, (tu_doan, den_doan) ...)."""
    for nut in ast.walk(goc):
        if isinstance(nut, ast.For) and any(
                isinstance(t, ast.Name) and t.id == '_idx_doan' for t in ast.walk(nut.target)):
            return nut
    return None


def _cac_lenh_goi(goc, ten_ham):
    return [n for n in ast.walk(goc)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == ten_ham]


ham_batch = _tim_ham('_dvc_run_batch')
assert ham_batch is not None, "Không tìm thấy _dvc_run_batch trong server.py"
vong_doan = _tim_vong_lap_doan(ham_batch)
assert vong_doan is not None, (
    "Không tìm thấy vòng lặp chạy qua từng đoạn ngày (for _idx_doan ...) trong _dvc_run_batch.")

# ===== Test 1 (QUAN TRỌNG — đúng ca thật): lệnh TẢI FILE phải nằm BÊN
# TRONG vòng lặp từng đoạn, tức tra cứu xong đoạn nào là tải luôn đoạn đó.
# Nếu nằm ngoài vòng lặp (gom hết rồi mới tải) thì tới lượt tải, trang chi
# tiết hồ sơ đã qua quá nhiều lượt điều hướng và không nạp được script ->
# "$ is not defined" hàng loạt. =====
goi_trong_vong = _cac_lenh_goi(vong_doan, '_tai_ho_so_1_doan')
assert goi_trong_vong, (
    "Lệnh tải file (_tai_ho_so_1_doan) PHẢI nằm BÊN TRONG vòng lặp từng đoạn ngày — tra cứu xong "
    "đoạn nào tải luôn đoạn đó. Gom hết mọi đoạn rồi mới tải ở cuối đã gây lỗi '$ is not defined' "
    "hàng loạt (người dùng xác nhận: 1 tháng lẻ tải được, cả năm thì không).")
print("PASS 1: tải file được gọi ngay bên trong vòng lặp từng đoạn ngày.")

# ===== Test 2 (không hồi quy): không được còn lệnh tải nào nằm NGOÀI vòng
# lặp (gom lại tải cuối) — chỉ đúng 1 chỗ gọi, và chỗ đó ở trong vòng lặp.
# =====
goi_toan_ham = _cac_lenh_goi(ham_batch, '_tai_ho_so_1_doan')
assert len(goi_toan_ham) == len(goi_trong_vong) == 1, (
    f"Chỉ được gọi _tai_ho_so_1_doan ĐÚNG 1 lần và phải ở trong vòng lặp từng đoạn — hiện có "
    f"{len(goi_toan_ham)} chỗ gọi, trong đó {len(goi_trong_vong)} chỗ nằm trong vòng lặp.")
print("PASS 2: chỉ có đúng 1 chỗ gọi tải file và nằm trong vòng lặp (không gom lại tải ở cuối).")

# ===== Test 3 (không hồi quy): mã hồ sơ đã tải ở đoạn trước không được tải
# lại ở đoạn sau — seen_ma phải khởi tạo NGOÀI vòng lặp (dùng chung mọi
# đoạn), nếu khởi tạo lại trong mỗi đoạn sẽ tải trùng. =====
def _gan_seen_ma(goc):
    ra = []
    for nut in ast.walk(goc):
        if isinstance(nut, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == 'seen_ma' for t in nut.targets):
            ra.append(nut)
    return ra

assert not _gan_seen_ma(vong_doan), (
    "seen_ma KHÔNG được khởi tạo lại bên trong vòng lặp từng đoạn — phải dùng chung cho mọi đoạn, "
    "nếu không hồ sơ đã tải ở đoạn trước sẽ bị tải lại ở đoạn sau.")
assert _gan_seen_ma(ham_batch), "Phải có khởi tạo seen_ma (ngoài vòng lặp từng đoạn)."
print("PASS 3: seen_ma dùng chung mọi đoạn — không tải trùng hồ sơ giữa các đoạn.")

print("\nALL DONE")
