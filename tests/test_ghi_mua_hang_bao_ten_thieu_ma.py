import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: khi 1 chứng từ Mua hàng bị bỏ qua HOÀN TOÀN vì TẤT CẢ
dòng đều thiếu mã hàng trong MISA, thông báo phải nêu CỤ THỂ tên hàng nào
đang thiếu (thay vì chỉ nói chung chung "thiếu mã hàng"), để người dùng biết
CHÍNH XÁC sản phẩm nào cần bổ sung/Import lại Danh mục Hàng hóa vào MISA.

Đúng ca thật người dùng báo cáo: Bảng kê Đầu vào Q2/2026 (534 dòng, ~96 hóa
đơn) đối chiếu với Mua_hang_hoa__dich_vu.xlsx (MISA, 91 dòng) phát hiện 5
hóa đơn THẬT SỰ thiếu (không liên quan gì tới lỗi kỳ cũ) — cùng NCC (MST
3603289732, "CÔNG TY TNHH TUẤN TRƯỜNG THỊNH") có NHIỀU hóa đơn khác (32,37,
38) đã ghi ĐÚNG vào MISA, chỉ riêng 4 hóa đơn (33,41,43,46) toàn sản phẩm
MỚI ("Chậu Polystone..." nhiều biến thể) bị bỏ qua HOÀN TOÀN — nhà cung cấp
rõ ràng ĐÃ có trong MISA (hóa đơn khác cùng NCC vẫn ghi được), nên nguyên
nhân CHỈ có thể là các mã hàng MỚI (tự sinh theo tên ở _gen_mua_hang_nk)
chưa từng được Import Danh mục Hàng hóa vào MISA."""
import sys, textwrap
sys.path.insert(0, _REPO_ROOT)
import server


def extract(start_marker, end_marker):
    src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()
    i0 = src.index(start_marker)
    i0 = src.rfind("\n", 0, i0) + 1
    i1 = src.index(end_marker, i0)
    return textwrap.dedent(src[i0:i1])


block = extract(
    '            acc_obj_id, ten_ncc_misa, ma_dt_misa = ncc[mst_k]\n            valid_lines = []\n'
    '            # Ghi lại TÊN HÀNG',
    '            # TK Nợ/Có phải tồn tại trong danh mục Account MISA (FK) — TK')
# Bọc trong 1 vòng lặp giả để "continue" (vốn continue vòng "for doc in
# order" ngoài cùng ở code thật) vẫn hợp lệ khi exec() đoạn cắt rời.
block = "for __once in [0]:\n" + textwrap.indent(block, "    ")

# NCC ĐÃ có trong MISA (mst_k khớp) — mô phỏng đúng ca thật: chứng từ khác
# cùng NCC ghi được bình thường, chỉ riêng chứng từ NÀY toàn sản phẩm MỚI.
ns = {
    "ncc": {"3603289732": ("aid-1", "CÔNG TY TNHH TUẤN TRƯỜNG THỊNH", "NCC01")},
    "hang": {},   # Danh mục MISA CHƯA có mã nào của lô hàng mới này
    "mst_k": "3603289732",
    "lines": [
        {19: "HH00301-8", 20: "Chậu Polystone WIL50 - MTWT"},
        {19: "HH00302-8", 20: "Chậu Polystone WIL50 - WT"},
        {19: "HH00303-8", 20: "Chậu Polystone WIL65 - WT"},
    ],
    "cfg": {"ma": 19, "ten": 20},
    "bo_mahang": 0,
    "doc": "NK202636032897-43",
    "ket": [],
}
exec(compile(block, "<ghi_mua_hang_bao_ten_thieu_ma>", "exec"), ns)

assert len(ns["ket"]) == 1, f"Phải có đúng 1 kết quả (bỏ qua) — được {ns['ket']}"
tt = ns["ket"][0]["trang_thai"]
print("Trạng thái:", tt)
assert "bỏ qua — tất cả dòng đều thiếu mã hàng trong MISA" in tt
assert "Chậu Polystone WIL50 - MTWT" in tt, (
    f"Thông báo PHẢI nêu cụ thể tên hàng thiếu mã (vd 'Chậu Polystone WIL50 - MTWT') để người dùng "
    f"biết chính xác sản phẩm nào cần bổ sung Danh mục — được: {tt}")
assert ns["bo_mahang"] == 3, f"Phải đếm đúng 3 dòng bỏ qua — được {ns['bo_mahang']}"
print("PASS: thông báo 'thiếu mã hàng' giờ nêu cụ thể tên hàng (ví dụ), giúp người dùng tự biết "
      "chính xác sản phẩm nào cần bổ sung/Import lại Danh mục Hàng hóa vào MISA.")

print("\nTẤT CẢ TEST PASS")
