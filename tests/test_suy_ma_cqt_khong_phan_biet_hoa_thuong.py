import os, sys
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Ca thật: LÊ TUYÊN (MST 0202364592): Tên CQT "Thuế cơ sở 5 thành phố Hải Phòng" (chữ "thành phố" thường) không khớp danh mục "Thành phố"
# -> Mã CQT nơi nộp bị bỏ trống; HTKK ghi Cơ quan thuế quản lý 10315. Tên trùng 2 mã (10307, 10315) -> chọn theo xã trong địa chỉ.
dia_chi = "Số 9 Nam Sơn 1, Xã An Hưng, TP Hải Phòng"
assert server._suy_ma_cqt("Thuế cơ sở 5 thành phố Hải Phòng", dia_chi) == "10315"
assert server._suy_ma_cqt("Thuế cơ sở 5 Thành phố Hải Phòng", dia_chi) == "10315"
assert server._suy_ma_cqt("Thuế cơ sở 5 thành phố Hải Phòng", "") == ""          # tên trùng mã mà không có địa chỉ -> không đoán
assert server._suy_ma_cqt("", dia_chi) == "" and server._suy_ma_cqt("Cơ quan không tồn tại", dia_chi) == ""
print("PASS: suy Mã CQT từ Tên CQT không phân biệt hoa/thường, gỡ trùng theo địa chỉ (10315); không chắc thì để trống.")
