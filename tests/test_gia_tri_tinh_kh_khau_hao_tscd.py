import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test (nguồn) — người dùng gửi 2 file Excel "Sổ tài sản cố định"
# xuất từ MISA: 1 file do PHẦN MỀM tự động Ghi tăng + Tính khấu hao (SAI:
# "Giá trị tính KH"=0, "Giá trị còn lại"=ÂM), 1 file do người dùng tự tay
# nhập + tự trích khấu hao trên MISA (ĐÚNG: "Giá trị tính KH"=Nguyên giá,
# "Giá trị còn lại"=Nguyên giá - Hao mòn luỹ kế, dương).
#
# Đối chiếu số liệu: "Giá trị còn lại" trong file SAI ĐÚNG BẰNG ÂM "Hao mòn
# luỹ kế" (vd TSCD003: L=-4.151.212, K=4.151.212) — chỉ có thể xảy ra nếu
# "Giá trị tính KH" (cơ sở tính L = GiaTriKH - K) đang bị đọc là 0.
#
# Root cause: MISA đọc "Giá trị tính KH" từ dòng MỚI NHẤT trong bảng
# FixedAssetLedger (giống bài học "Sổ theo dõi TSCĐ đọc SỐNG dòng mới nhất"
# đã ghi trong comment _misa_khau_hao_tscd). _misa_ghi_tang_tscd() ghi ĐÚNG
# cột DepreciationAmount cho dòng "Ghi tăng" ban đầu, nhưng mỗi lần
# _misa_khau_hao_tscd() chạy (Tính khấu hao hàng tháng) lại ghi THÊM 1 dòng
# MỚI vào FixedAssetLedger mà QUÊN set cột DepreciationAmount (cột NOT
# NULL, tự về 0 theo _misa_gia_tri_mac_dinh) — dòng mới nhất này ghi đè
# "Giá trị tính KH" trên báo cáo về 0, dù dòng Ghi tăng ban đầu đã đúng.


def _lay_than_ham(ten_ham):
    idx = src.index('def ' + ten_ham + '(')
    idx_ke = src.index('\ndef ', idx + 10)
    return src[idx:idx_ke]


than_khau_hao = _lay_than_ham('_misa_khau_hao_tscd')
than_ghi_tang = _lay_than_ham('_misa_ghi_tang_tscd')

# ===== Test 1 (QUAN TRỌNG — đúng ca thật): trong vòng lặp ghi dòng sổ cái
# (FixedAssetLedger) mỗi kỳ khấu hao, PHẢI có set cột "DepreciationAmount"
# — nếu thiếu, cột NOT NULL này tự về 0, ghi đè "Giá trị tính KH" trên báo
# cáo Sổ tài sản cố định (đọc dòng MỚI NHẤT) về 0 sau mỗi lần chạy khấu
# hao. =====
idx_led_block = than_khau_hao.index('if cols_led:')
idx_ket_block = than_khau_hao.index('dep_row = {real:', idx_led_block)
khoi_led = than_khau_hao[idx_led_block:idx_ket_block]
assert '"DepreciationAmount"' in khoi_led, (
    "_misa_khau_hao_tscd(): dòng FixedAssetLedger ghi mỗi kỳ khấu hao PHẢI set cột "
    "'DepreciationAmount' (cột NOT NULL) — thiếu sẽ tự về 0, ghi đè 'Giá trị tính KH' trên báo cáo Sổ "
    "tài sản cố định về 0 sau khi chạy Tính khấu hao (xác nhận qua dữ liệu thật: Giá trị còn lại = ÂM "
    "Hao mòn luỹ kế, chỉ xảy ra khi Giá trị tính KH bị đọc là 0).")

# ===== Test 2 (không hồi quy): giá trị gán cho "DepreciationAmount" phải
# CÙNG giá trị với "OriginDepreciationAmount" (đều là st["tong_tien"] —
# nguyên giá/cơ sở tính khấu hao gốc của tài sản, KHÔNG phải số tiền khấu
# hao riêng kỳ này). =====
idx_dep = khoi_led.index('"DepreciationAmount"')
idx_dep_line_start = khoi_led.rfind('\n', 0, idx_dep)
dong_dep = khoi_led[idx_dep_line_start:idx_dep + 40]
assert 'st["tong_tien"]' in dong_dep, (
    "'DepreciationAmount' phải được set = st['tong_tien'] (nguyên giá tài sản) — giống hệt cách "
    "'OriginDepreciationAmount' đang được set, KHÔNG phải số tiền khấu hao riêng kỳ này (tien_ky_thuc).")
print("PASS 1+2: _misa_khau_hao_tscd() set đúng cột DepreciationAmount = nguyên giá cho mỗi dòng sổ "
      "cái khấu hao hàng kỳ — không còn bị ghi đè 'Giá trị tính KH' về 0.")

# ===== Test 3 (đối chiếu _misa_ghi_tang_tscd — đảm bảo 2 hàm nhất quán):
# _misa_ghi_tang_tscd() (dòng Ghi tăng ban đầu) vẫn phải set đúng
# DepreciationAmount như trước (không bị ảnh hưởng bởi sửa đổi này). =====
assert '"DepreciationAmount"' in than_ghi_tang, (
    "_misa_ghi_tang_tscd() vẫn phải set cột DepreciationAmount cho dòng Ghi tăng ban đầu (không được "
    "vô tình xoá mất khi sửa _misa_khau_hao_tscd).")
print("PASS 3: _misa_ghi_tang_tscd() vẫn set đúng DepreciationAmount cho dòng Ghi tăng ban đầu.")

print("\nALL DONE")
