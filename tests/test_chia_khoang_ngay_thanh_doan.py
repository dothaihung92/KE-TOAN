import os
import datetime

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test cho _chia_khoang_ngay_thanh_doan() — vòng thứ 4 chẩn
# đoán "Tra cứu tờ khai thuế / tải tờ khai hàng loạt" thiếu tờ khai cũ.
# Người dùng tự xác nhận qua chính phần mềm: tra "Tùy chọn ngày"
# 01/01/2024-31/12/2025 (2 năm) luôn thiếu Quý 1-2/2024, nhưng thu hẹp
# lại 01/01/2024-30/06/2024 (6 tháng) thì LẤY ĐỦ (kể cả Quý 4/2023 nộp
# trong khoảng đó — đối chiếu Excel "TraCuuToKhai_...160535.xlsx" xuất
# ra: có đủ GTGT/TNCN Quý 1/2024, Quý 4/2023, và các báo cáo năm 2023).
#
# Từng thử chia theo TỪNG THÁNG ở build .286-287 nhưng ĐỒNG THỜI đổi
# luôn page/size sang số (page:0, size:200) — gây thất bại HOÀN TOÀN;
# xác nhận riêng ở build .289 (chỉ đổi page/size sang số, KHÔNG chia
# nhỏ) cũng thất bại y hệt (8/8 lần "chưa ra bảng") -> lỗi THẬT SỰ là do
# tham số số bị cổng từ chối, KHÔNG phải do việc chia nhỏ/gọi lặp lại.
# Lần này chia theo đoạn 6 THÁNG (đúng độ rộng đã xác nhận chạy được)
# và GIỮ NGUYÊN page/size rỗng.


def extract_fn(name):
    try:
        idx = src.index('async def ' + name + '(')
    except ValueError:
        idx = src.index('def ' + name + '(')
    i = src.index(':', idx)
    lines = src[i + 1:].split('\n')
    body = []
    started = False
    for ln in lines:
        if ln.strip() == '' and not started:
            body.append(ln)
            continue
        if ln and not ln[0].isspace() and started:
            break
        if ln.strip():
            started = True
        body.append(ln)
    return src[idx:i + 1] + '\n'.join(body)


ns = {'datetime': datetime}
exec(extract_fn('_chia_khoang_ngay_thanh_doan'), ns)
_chia_khoang_ngay_thanh_doan = ns['_chia_khoang_ngay_thanh_doan']


def _tong_so_ngay(doan):
    tong = 0
    for tu_s, den_s in doan:
        d1, m1, y1 = (int(x) for x in tu_s.split("/"))
        d2, m2, y2 = (int(x) for x in den_s.split("/"))
        tong += (datetime.date(y2, m2, d2) - datetime.date(y1, m1, d1)).days + 1
    return tong


# ===== Test 1 (QUAN TRỌNG — đúng ca thật người dùng báo): khoảng RỘNG 2
# năm (01/01/2024-31/12/2025) -> chia thành 4 đoạn 6-THÁNG. =====
doan1 = _chia_khoang_ngay_thanh_doan("01/01/2024", "31/12/2025")
assert doan1 == [
    ("01/01/2024", "30/06/2024"),
    ("01/07/2024", "31/12/2024"),
    ("01/01/2025", "30/06/2025"),
    ("01/07/2025", "31/12/2025"),
], f"got {doan1}"
print("PASS 1: khoảng 2 năm chia đúng 4 đoạn 6-tháng, đúng độ rộng người dùng đã tự xác nhận chạy được "
      "(01/01/2024-30/06/2024).")

# ===== Test 2 (QUAN TRỌNG — đúng NGUYÊN VĂN khoảng người dùng vừa test
# thành công thật): khoảng ĐÚNG 6 tháng -> giữ NGUYÊN 1 đoạn duy nhất
# (không chia vụn thêm không cần thiết, khớp đúng cách người dùng vừa
# thử tay và xác nhận lấy đủ dữ liệu). =====
doan2 = _chia_khoang_ngay_thanh_doan("01/01/2024", "30/06/2024")
assert doan2 == [("01/01/2024", "30/06/2024")], f"got {doan2}"
print("PASS 2: khoảng đúng 6 tháng (đúng khoảng người dùng vừa tự tay thử thành công) giữ nguyên 1 "
      "đoạn duy nhất.")

# ===== Test 3 (không hồi quy — an toàn): tổng số ngày các đoạn PHẢI BẰNG
# đúng tổng số ngày khoảng gốc — không thiếu/trùng ngày nào. =====
tu_g = datetime.date(2024, 1, 1); den_g = datetime.date(2025, 12, 31)
so_ngay_goc = (den_g - tu_g).days + 1
assert _tong_so_ngay(doan1) == so_ngay_goc, (
    f"tổng số ngày các đoạn ({_tong_so_ngay(doan1)}) phải bằng đúng khoảng gốc ({so_ngay_goc})")
print("PASS 3: tổng số ngày các đoạn khớp đúng khoảng gốc — không thiếu/trùng ngày nào.")

# ===== Test 4 (không hồi quy — an toàn): khoảng lệch giữa (bắt đầu KHÔNG
# đúng đầu tháng) -> mỗi đoạn tính từ ngày bắt đầu THẬT + 6 tháng, đoạn
# cuối cắt đúng ngày kết thúc thật (không lấn ra ngoài khoảng gốc). =====
doan4 = _chia_khoang_ngay_thanh_doan("15/03/2024", "10/10/2024")
assert doan4 == [
    ("15/03/2024", "31/08/2024"),
    ("01/09/2024", "10/10/2024"),
], f"got {doan4}"
print("PASS 4: khoảng lệch giữa chia đúng từng đoạn (mỗi đoạn tính từ ngày bắt đầu thật + 6 tháng), "
      "đoạn cuối cắt đúng ngày kết thúc thật, không lấn ra ngoài khoảng gốc.")

# ===== Test 5 (không hồi quy — an toàn): tu > den (đảo ngược) -> tự đảo
# lại đúng thứ tự, không lỗi/crash. =====
doan5 = _chia_khoang_ngay_thanh_doan("31/12/2025", "01/01/2024")
assert doan5 == doan1, "tu > den phải tự đảo lại đúng thứ tự, cho kết quả giống hệt tu < den"
print("PASS 5: tu > den (đảo ngược) tự đảo lại đúng, không lỗi.")

# ===== Test 6 (không hồi quy — an toàn): ngày không đọc được -> trả rỗng
# an toàn, không lỗi/crash. =====
doan6 = _chia_khoang_ngay_thanh_doan("", "31/12/2025")
assert doan6 == [], f"got {doan6}"
print("PASS 6: ngày không hợp lệ -> trả rỗng an toàn, không lỗi.")

print("\nALL DONE")
