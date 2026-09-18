import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test (nguồn) cho việc hiện tiến độ khi tra cứu "thuế điện
# tử" bị chia nhỏ theo TỪNG THÁNG (_chia_khoang_ngay_theo_thang, xem
# test_chia_khoang_ngay_theo_thang.py) — người dùng báo: khoảng ngày rộng
# giờ tốn nhiều lượt tra cứu (mỗi lượt 1 captcha riêng) nên CHẬM hẳn, mà
# khung tiến độ vẫn chỉ hiện "đang xử lý" đứng yên suốt cả quá trình ->
# "phần mềm nãy giờ cứ treo không biết đã xong chưa". Phải cập nhật
# trang_thái LIÊN TỤC theo từng đoạn (tháng) đang tra, để người dùng thấy
# rõ vẫn đang chạy, không phải bị treo.

idx_ham = src.index('def _dvc_run_batch(')
idx_ham_ke = src.index('\ndef ', idx_ham + 10)
than_ham = src[idx_ham:idx_ham_ke]

# ===== Test 1 (QUAN TRỌNG — đúng phản ánh thật người dùng): vòng lặp qua
# từng đoạn (tháng) phải cập nhật item['trang_thai'] cho biết đang tra
# đoạn nào/tổng bao nhiêu đoạn — không được để đứng yên "đang xử lý" suốt
# cả quá trình chia nhỏ nhiều lượt tra cứu. =====
assert 'item["trang_thai"] = (' in than_ham and "_idx_doan" in than_ham and "len(cac_doan)" in than_ham, (
    "_dvc_run_batch() phải cập nhật item['trang_thai'] theo TỪNG đoạn (tháng) đang tra cứu khi khoảng "
    "ngày bị chia nhỏ nhiều lượt — nếu không, khung tiến độ sẽ đứng yên 'đang xử lý' suốt cả quá trình "
    "(có thể rất lâu với khoảng ngày rộng nhiều tháng), khiến người dùng tưởng phần mềm bị treo.")
print("PASS 1: _dvc_run_batch() cập nhật trang_thái theo từng đoạn (tháng) đang tra cứu, không đứng yên "
      "'đang xử lý' suốt cả quá trình chia nhỏ nhiều lượt.")

# ===== Test 2 (không hồi quy — an toàn): kết quả cuối cùng vẫn phải được
# ghi đè lại thành 'xong' (hoặc trạng thái lỗi) sau khi xử lý xong công ty
# — không được để lại thông báo tạm "đang tra cứu tháng X/Y" khi đã xong
# thật sự. =====
assert than_ham.count('item["trang_thai"] = "xong"') >= 1, (
    "Sau khi xử lý XONG công ty, item['trang_thai'] phải được ghi đè lại thành 'xong' — không được để "
    "lại thông báo tạm 'đang tra cứu tháng X/Y' của lượt tra cứu cuối cùng.")
print("PASS 2: kết quả cuối cùng vẫn ghi đè đúng thành 'xong', không để sót thông báo tạm giữa chừng.")

print("\nALL DONE")
