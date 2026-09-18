import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()
html_src = open(os.path.join(_REPO_ROOT, 'static', 'index.html'), encoding='utf-8').read()

# Regression test (nguồn) cho việc thêm chẩn đoán "LỆCH" khi cổng báo
# "Tổng số bản ghi" khác với số dòng thật đọc được trong tra cứu tờ khai
# hàng loạt — người dùng báo qua nhiều vòng: tra cứu "Tùy chọn ngày"
# 01/01/2024-31/12/2025 bị THIẾU tờ khai Quý 1-2/2024 dù search vẫn coi
# là "thành công". Đã thử 2 cách sửa (page/size build .285, chia nhỏ
# theo tháng build .286-287) đều KHÔNG giải quyết được — cách chia nhỏ
# theo tháng còn làm TỆ HƠN (15 dòng -> 5 dòng, người dùng báo lại) nên
# đã REVERT. Thay vì đoán tiếp, thêm chẩn đoán THẬT: đối chiếu "Tổng số
# bản ghi" cổng tự báo với số dòng đọc được, và hiện ra khung tiến độ
# (item.loi_tra_cuu) để có dữ liệu thật cho lần chẩn đoán tiếp theo.


def _lay_than_ham(ten_ham):
    idx = src.index('def ' + ten_ham + '(')
    idx_ke = src.index('\ndef ', idx + 10)
    return src[idx:idx_ke]


than_tracuu = _lay_than_ham('_dvc_browser_tracuu')
than_tracuu_tdt = _lay_than_ham('_dvc_browser_tracuu_tdt')
than_run_batch = _lay_than_ham('_dvc_run_batch')

# ===== Test 1: cả 2 hàm tra cứu (DVC + Thuế điện tử) phải đối chiếu
# "Tổng số bản ghi" cổng báo với số dòng thật đọc được, và đánh dấu LỆCH
# khi khác nhau. =====
for ten, than in (('_dvc_browser_tracuu', than_tracuu), ('_dvc_browser_tracuu_tdt', than_tracuu_tdt)):
    assert "tổng số bản ghi" in than.lower(), f"{ten} phải đọc 'Tổng số bản ghi' cổng tự báo — thiếu"
    assert "LỆCH" in than, (
        f"{ten} phải đánh dấu rõ 'LỆCH' khi 'Tổng số bản ghi' cổng báo khác số dòng thật đọc được — "
        f"để chẩn đoán được có đang bị cổng âm thầm cắt bớt kết quả hay không.")
print("PASS 1: cả 2 hàm tra cứu (DVC + Thuế điện tử) đều đối chiếu 'Tổng số bản ghi' và đánh dấu LỆCH "
      "khi phát hiện khác biệt.")

# ===== Test 2 (QUAN TRỌNG): _dvc_run_batch() phải bắt được thông báo LỆCH
# này và ghi vào item['loi_tra_cuu'] NGAY CẢ KHI search có rows (thành
# công) — trước đây item['loi_tra_cuu'] CHỈ được ghi khi search thất bại
# HOÀN TOÀN (not rows), nên chẩn đoán LỆCH (search "thành công" nhưng
# thiếu dữ liệu) sẽ bị bỏ sót nếu không xử lý riêng. =====
assert '"LỆCH" in _d' in than_run_batch or "'LỆCH' in _d" in than_run_batch, (
    "_dvc_run_batch() phải kiểm tra riêng thông báo LỆCH trong sdiag và ghi vào item['loi_tra_cuu'] — "
    "nếu không, chẩn đoán LỆCH sẽ bị bỏ sót vì nhánh loi_tra_cuu cũ chỉ chạy khi search thất bại hoàn "
    "toàn (not rows), trong khi ca LỆCH vẫn có rows (search coi là 'thành công').")
print("PASS 2: _dvc_run_batch() bắt riêng thông báo LỆCH và ghi vào item['loi_tra_cuu'] dù search có "
      "rows (không bị bỏ sót như nhánh loi_tra_cuu cũ).")

# ===== Test 3 (không hồi quy): hàm chia nhỏ theo TỪNG THÁNG (bản lỗi cũ,
# build .286-287 — kết hợp NHẦM với việc đổi page/size sang số, gây thất
# bại hoàn toàn) phải đã bị gỡ bỏ hẳn — không được để sót code chết. Việc
# chia nhỏ theo khoảng RỘNG HƠN (6 tháng, xem
# _chia_khoang_ngay_thanh_doan + test_chia_khoang_ngay_thanh_doan.py) là
# tính năng KHÁC, được thêm lại SAU khi xác nhận nguyên nhân thật sự là
# do tham số số (không phải do chia nhỏ/gọi lặp lại) — không mâu thuẫn
# với test này. =====
assert "_chia_khoang_ngay_theo_thang" not in src, (
    "_chia_khoang_ngay_theo_thang() (bản chia theo TỪNG THÁNG, lỗi cũ) phải đã được gỡ bỏ hoàn toàn — "
    "không được để sót lại code chết. Việc chia nhỏ theo 6 tháng (_chia_khoang_ngay_thanh_doan) là tính "
    "năng khác, không phải hàm này.")
print("PASS 3: đã gỡ bỏ hoàn toàn hàm chia theo TỪNG THÁNG (bản lỗi cũ), không còn code chết sót lại.")

# ===== Test 4: khung tiến độ (frontend) phải HIỂN THỊ item.loi_tra_cuu —
# trước đây trường này ĐÃ được ghi ở backend nhưng KHÔNG hiện ra đâu cả,
# không cách nào biết để chẩn đoán. =====
assert "it.loi_tra_cuu" in html_src, (
    "Khung tiến độ (static/index.html, dvcbPoll) phải hiển thị item.loi_tra_cuu — trước đây trường này "
    "được backend ghi lại nhưng không hiện ra UI, không cách nào biết lý do 1 nguồn tra cứu bị thiếu dữ "
    "liệu để chẩn đoán tiếp.")
print("PASS 4: khung tiến độ đã hiển thị item.loi_tra_cuu (trước đây có ghi nhưng không hiện ra UI).")

print("\nALL DONE")
