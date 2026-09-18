import os
import datetime
import calendar

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test cho _chia_khoang_ngay_theo_thang() — người dùng tự tay
# thử tra cứu trực tiếp trên cổng (tab "Tra cứu hồ sơ đã nộp trên thuế
# điện tử") với khoảng rộng 01/01/2024-31/12/2025: "hệ thống thuế chỉ cho
# tra cứu 1 tháng không cho hiện từ 01/01/2024, Đến ngày=31/12/2025" — xác
# nhận CỔNG THẬT giới hạn tối đa 1 tháng/lần tra cứu. Trước đó
# _dvc_browser_tracuu_tdt() gọi thẳng cả khoảng rộng trong 1 lần AJAX, nên
# công ty MST 0312253694 (hoạt động liên tục từ trước 2024) bị THIẾU HẲN
# tờ khai Quý 1-2/2024 khỏi kết quả — sửa page/size (build .285) không
# giải quyết được vì đây không phải lỗi phân trang.
#
# _chia_khoang_ngay_theo_thang() chia khoảng ngày rộng thành nhiều đoạn,
# MỖI đoạn nằm TRỌN trong 1 tháng dương lịch, để gọi tra cứu riêng từng
# đoạn rồi gộp kết quả lại — không đoạn nào vượt quá giới hạn cổng.


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


ns = {'datetime': datetime, 'calendar': calendar}
exec(extract_fn('_chia_khoang_ngay_theo_thang'), ns)
_chia_khoang_ngay_theo_thang = ns['_chia_khoang_ngay_theo_thang']


def _tong_so_ngay(doan):
    tong = 0
    for tu_s, den_s in doan:
        d1, m1, y1 = (int(x) for x in tu_s.split("/"))
        d2, m2, y2 = (int(x) for x in den_s.split("/"))
        tong += (datetime.date(y2, m2, d2) - datetime.date(y1, m1, d1)).days + 1
    return tong


# ===== Test 1 (QUAN TRỌNG — đúng ca thật người dùng báo): khoảng RỘNG 2
# năm (01/01/2024-31/12/2025, đúng khoảng người dùng đã chọn) -> chia
# thành 24 đoạn, MỖI đoạn nằm TRỌN trong 1 tháng (không đoạn nào vượt quá
# 31 ngày — trong giới hạn "1 tháng" cổng cho phép). =====
doan1 = _chia_khoang_ngay_theo_thang("01/01/2024", "31/12/2025")
assert len(doan1) == 24, f"01/01/2024-31/12/2025 phải chia đủ 24 tháng — got {len(doan1)}: {doan1}"
assert doan1[0] == ("01/01/2024", "31/01/2024"), f"got {doan1[0]}"
assert doan1[-1] == ("01/12/2025", "31/12/2025"), f"got {doan1[-1]}"
for tu_s, den_s in doan1:
    d1, m1, y1 = (int(x) for x in tu_s.split("/"))
    d2, m2, y2 = (int(x) for x in den_s.split("/"))
    assert (y1, m1) == (y2, m2), f"đoạn {tu_s}-{den_s} phải nằm TRỌN trong 1 tháng dương lịch"
    so_ngay = (datetime.date(y2, m2, d2) - datetime.date(y1, m1, d1)).days + 1
    assert so_ngay <= 31, f"đoạn {tu_s}-{den_s} có {so_ngay} ngày, vượt quá giới hạn 1 tháng của cổng"
print(f"PASS 1: khoảng rộng 2 năm (đúng ca thật người dùng báo) chia đúng 24 đoạn, MỖI đoạn nằm trọn "
      f"trong 1 tháng dương lịch, không đoạn nào vượt giới hạn cổng.")

# ===== Test 2 (không hồi quy — an toàn): tổng số ngày của các đoạn PHẢI
# BẰNG đúng tổng số ngày của khoảng gốc (không thiếu/không trùng ngày nào
# — mọi ngày trong khoảng gốc phải được 1 và chỉ 1 đoạn bao phủ). =====
tu_g = datetime.date(2024, 1, 1); den_g = datetime.date(2025, 12, 31)
so_ngay_goc = (den_g - tu_g).days + 1
assert _tong_so_ngay(doan1) == so_ngay_goc, (
    f"tổng số ngày các đoạn ({_tong_so_ngay(doan1)}) phải bằng đúng tổng số ngày khoảng gốc "
    f"({so_ngay_goc}) — không được thiếu/trùng ngày nào")
print("PASS 2: tổng số ngày các đoạn khớp đúng khoảng gốc — không thiếu/trùng ngày nào.")

# ===== Test 3 (không hồi quy — an toàn): khoảng NẰM TRỌN trong 1 tháng
# (vd tra cứu theo Tháng, chế độ hiện tại) -> chỉ 1 đoạn, giữ NGUYÊN
# khoảng gốc (không chia vụn thêm không cần thiết). =====
doan3 = _chia_khoang_ngay_theo_thang("01/07/2024", "31/07/2024")
assert doan3 == [("01/07/2024", "31/07/2024")], f"got {doan3}"
print("PASS 3: khoảng đã nằm trọn trong 1 tháng -> giữ nguyên 1 đoạn, không chia vụn thừa.")

# ===== Test 4 (không hồi quy — an toàn): khoảng lệch giữa tháng (vd Quý,
# 3 tháng không tròn) -> chia đúng số đoạn, đoạn đầu/cuối cắt đúng ngày
# bắt đầu/kết thúc thật (không lấn ra ngoài khoảng gốc). =====
doan4 = _chia_khoang_ngay_theo_thang("15/03/2024", "10/05/2024")
assert doan4 == [
    ("15/03/2024", "31/03/2024"),
    ("01/04/2024", "30/04/2024"),
    ("01/05/2024", "10/05/2024"),
], f"got {doan4}"
print("PASS 4: khoảng lệch giữa tháng chia đúng từng đoạn, đoạn đầu/cuối cắt đúng ngày thật, không lấn "
      "ra ngoài khoảng gốc.")

# ===== Test 5 (không hồi quy — an toàn): tu > den (đảo ngược) -> tự đảo "
# lại đúng thứ tự, không lỗi/crash. =====
doan5 = _chia_khoang_ngay_theo_thang("31/12/2025", "01/01/2024")
assert doan5 == doan1, "tu > den phải tự đảo lại đúng thứ tự, cho kết quả giống hệt tu < den"
print("PASS 5: tu > den (đảo ngược) tự đảo lại đúng, không lỗi.")

# ===== Test 6 (không hồi quy — an toàn): ngày không đọc được -> trả rỗng
# an toàn, không lỗi/crash. =====
doan6 = _chia_khoang_ngay_theo_thang("", "31/12/2025")
assert doan6 == [], f"got {doan6}"
print("PASS 6: ngày không hợp lệ -> trả rỗng an toàn, không lỗi.")

print("\nALL DONE")
