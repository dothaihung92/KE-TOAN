import os
import time
import datetime
import itertools

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test cho tim_to_hop() (bên trong _misa_khop_1_2, server.py) — người dùng báo (kèm ảnh
# chụp): công ty nhiều hóa đơn, bấm "Chạy đối chiếu" (Đối chiếu công nợ 3 tầng) hơn 5 phút vẫn chưa
# xong ("Đang đối chiếu 3 tầng (có thể mất chút thời gian nếu nhiều hóa đơn)...").
#
# Nguyên nhân: tim_to_hop() duyệt BRUTE-FORCE mọi tổ hợp con bằng itertools.combinations(ung_vien, k)
# cho từng k từ 2..max_to_hop (mặc định 8) — dù đã giới hạn cỡ nhóm ứng viên (2..20 phần tử, xem nơi
# gọi trong _misa_khop_1_2), C(20,8) ≈ 126.000 tổ hợp MỖI LẦN GỌI — mà hàm này được gọi LẶP LẠI cho
# MỖI khoản thanh toán CHƯA khớp × MỖI hướng (Tầng 2 thuận "nhiều hóa đơn -> 1 khoản" + Tầng 2c ngược
# "1 hóa đơn -> nhiều khoản") × MỖI đối tượng công nợ (khách hàng/NCC) trong cả kỳ đối chiếu — cộng
# dồn dễ lên tới hàng trăm triệu phép tính với công ty nhiều hóa đơn/nhiều đối tượng công nợ.
#
# Fix: số tiền hóa đơn/thanh toán luôn DƯƠNG (bản chất nghiệp vụ) -> sắp xếp tăng dần rồi duyệt quay
# lui (backtracking) có CẮT TỈA — dừng nhánh ngay khi tổng riêng phần đã vượt ngưỡng cho phép, không
# cần duyệt tiếp (mọi phần tử sau, do đã sắp tăng dần, chỉ làm tổng lớn hơn). Vẫn tìm ra ĐÚNG những
# tổ hợp brute-force sẽ tìm ra (chỉ khác thứ tự duyệt) — dự phòng rơi về brute-force cũ nếu lỡ gặp
# giá trị <=0 (an toàn tuyệt đối cho tính đúng đắn ở ca hiếm/bất thường đó).


def extract_fn(name):
    """Trích xuất hàm TOP-LEVEL — cách làm sẵn có, dùng chung nhiều test khác trong repo."""
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


ns = {'datetime': datetime, 'itertools': itertools}
for fn in ('_misa_ngay_str', '_hd_so_trong_mo_ta', '_misa_khop_1_2'):
    exec(extract_fn(fn), ns)
_misa_khop_1_2 = ns['_misa_khop_1_2']

D0 = datetime.datetime(2026, 3, 1)


def hd(inv_no, so_tien, ngay=D0):
    return {"inv_no": inv_no, "inv_date": ngay, "so_tien": so_tien, "gt": 0.0, "vat": 0.0}


def tt(so_tien, ngay=D0, mo_ta=""):
    return {"date": ngay, "so_tien": so_tien, "mo_ta": mo_ta}


# ===== Test 1 (không hồi quy — QUAN TRỌNG): tổ hợp 2 hóa đơn khớp ĐÚNG 1 khoản thanh toán (Tầng 2a)
# vẫn phải khớp đúng như trước — không có hóa đơn nào khớp 1-1 riêng lẻ (buộc phải qua Tầng 2). =====
doi_tuong_hd = {"obj1": {"ma": "0101", "ten": "Công ty A", "hoa_don": [
    hd("HD001", 1_234_567), hd("HD002", 2_345_678), hd("HD003", 3_456_789),
    hd("HD004", 4_567_890), hd("HD005", 5_678_901),
]}}
# HD002 + HD004 = 2.345.678 + 4.567.890 = 6.913.568 — tổng DUY NHẤT khớp CHÍNH XÁC (đã kiểm tra thủ
# công: không tổ hợp 2/3 hóa đơn nào khác trong nhóm này cộng ra đúng số này trong sai số 1đ).
doi_tuong_tt = {"obj1": [tt(6_913_568)]}
tang1, tang2, khong_ro, tam_ung = _misa_khop_1_2(doi_tuong_hd, doi_tuong_tt)
assert len(tang2) == 1, f"Phải khớp được đúng 1 tổ hợp Tầng 2 — got tang2={tang2}"
so_hd_khop = {h["inv_no"] for h in tang2[0]["hoa_don"]}
assert so_hd_khop == {"HD002", "HD004"}, f"Phải khớp ĐÚNG HD002+HD004 — got {so_hd_khop}"
assert tang2[0]["lech"] == 0
print("PASS 1: tổ hợp 2 hóa đơn khớp 1 khoản thanh toán (Tầng 2a) vẫn khớp đúng sau khi đổi thuật "
      "toán tim_to_hop (backtracking có cắt tỉa thay vì itertools.combinations vét cạn).")

# ===== Test 2 (không hồi quy — QUAN TRỌNG): KHÔNG có tổ hợp nào khớp -> hóa đơn vẫn "treo" (không
# bị khớp bừa/khớp nhầm do thuật toán mới cắt tỉa sai). =====
doi_tuong_hd2 = {"obj1": {"ma": "0101", "ten": "Công ty A", "hoa_don": [
    hd("HD001", 1_111_111), hd("HD002", 2_222_222), hd("HD003", 3_333_333),
]}}
doi_tuong_tt2 = {"obj1": [tt(9_999_999)]}   # không tổ hợp nào (kể cả cả 3 = 6.666.666) khớp số này
tang1b, tang2b, khong_rob, _ = _misa_khop_1_2(doi_tuong_hd2, doi_tuong_tt2)
assert not tang2b, f"Không có tổ hợp nào khớp thật -> tang2 phải rỗng — got {tang2b}"
print("PASS 2: không có tổ hợp nào khớp thật -> vẫn đúng không khớp bừa (không hồi quy sau khi đổi "
      "thuật toán).")

# ===== Test 3 (không hồi quy — QUAN TRỌNG): NHIỀU tổ hợp cùng khớp -> phải báo "không rõ", KHÔNG
# được tự chọn bừa 1 tổ hợp (thuật toán mới dừng sớm khi thấy >1 tổ hợp, phải giữ đúng hành vi này). =====
doi_tuong_hd3 = {"obj1": {"ma": "0101", "ten": "Công ty A", "hoa_don": [
    hd("HD001", 1_000_000), hd("HD002", 2_000_000), hd("HD003", 3_000_000), hd("HD004", 3_000_000),
]}}
# 2 tổ hợp cùng khớp 4.000.000: (HD001+HD003) và (HD001+HD004) — cùng giá trị HD003/HD004.
doi_tuong_tt3 = {"obj1": [tt(4_000_000)]}
tang1c, tang2c, khong_roc, _ = _misa_khop_1_2(doi_tuong_hd3, doi_tuong_tt3)
assert not tang2c, "Nhiều tổ hợp cùng khớp -> KHÔNG được tự chọn bừa 1 cái, tang2 phải rỗng"
assert any(x.get("loai_vuong") == "Nhiều tổ hợp hóa đơn cùng khớp" for x in khong_roc), (
    f"Phải báo rõ 'Nhiều tổ hợp hóa đơn cùng khớp' — got {khong_roc}")
print("PASS 3: nhiều tổ hợp cùng khớp -> vẫn đúng báo 'không rõ', không tự chọn bừa.")

# ===== Test 4 (không hồi quy — QUAN TRỌNG, dự phòng an toàn): dữ liệu có giá trị <=0 (ca hiếm/bất
# thường, VD hàng trả lại/điều chỉnh âm) -> vẫn phải rơi về đúng brute-force cũ, KHÔNG được bỏ sót
# tổ hợp khớp thật chỉ vì tối ưu cắt tỉa (cắt tỉa chỉ AN TOÀN khi mọi giá trị dương). =====
doi_tuong_hd4 = {"obj1": {"ma": "0101", "ten": "Công ty A", "hoa_don": [
    hd("HD001", 5_000_000), hd("HD002", -1_000_000), hd("HD003", 2_000_000),
]}}
# HD001 + HD002 = 5.000.000 - 1.000.000 = 4.000.000 — CHỈ tìm được nếu KHÔNG cắt tỉa sai (giá trị âm
# khiến brute-force vẫn đúng, nhưng cắt tỉa "tổng vượt ngưỡng thì dừng" sẽ SAI nếu không tự nhận diện
# và rơi về brute-force).
doi_tuong_tt4 = {"obj1": [tt(4_000_000)]}
tang1d, tang2d, khong_rod, _ = _misa_khop_1_2(doi_tuong_hd4, doi_tuong_tt4)
assert len(tang2d) == 1, (
    f"Có giá trị <=0 trong dữ liệu -> PHẢI tự rơi về brute-force cũ (an toàn tuyệt đối), vẫn phải tìm "
    f"đúng tổ hợp HD001+HD002=4.000.000 — got tang2={tang2d}")
so_hd_khop4 = {h["inv_no"] for h in tang2d[0]["hoa_don"]}
assert so_hd_khop4 == {"HD001", "HD002"}, f"got {so_hd_khop4}"
print("PASS 4: dữ liệu có giá trị <=0 (ca hiếm) -> tự rơi về brute-force cũ, vẫn tìm đúng tổ hợp, "
      "không bỏ sót do cắt tỉa sai.")

# ===== Test 5 (QUAN TRỌNG — đúng bug thật, kiểm tra tốc độ): nhóm ứng viên LỚN (20 hóa đơn, chạm
# đúng giới hạn cho phép ở nơi gọi) mà KHÔNG có tổ hợp nào khớp (ca PHỔ BIẾN NHẤT trong thực tế, cũng
# là ca brute-force cũ CHẬM NHẤT vì phải duyệt HẾT C(20,8)≈126.000 tổ hợp mới kết luận "không có") —
# phải hoàn thành NHANH (dưới vài giây), không còn "hơn 5 phút chưa xong" như báo cáo thật. =====
hoa_don_lon = [hd("HD%03d" % i, 1_000_000 + i * 37_000) for i in range(1, 21)]  # 20 hóa đơn, giá trị lệch nhau
doi_tuong_hd5 = {"obj1": {"ma": "0101", "ten": "Công ty Nhiều Hóa Đơn", "hoa_don": hoa_don_lon}}
# Số tiền thanh toán CỐ TÌNH không khớp bất kỳ tổ hợp 2..8 phần tử nào (số lẻ bất thường).
doi_tuong_tt5 = {"obj1": [tt(123_456_789)]}
bat_dau = time.time()
tang1e, tang2e, khong_roe, _ = _misa_khop_1_2(doi_tuong_hd5, doi_tuong_tt5)
thoi_gian = time.time() - bat_dau
assert thoi_gian < 5.0, (
    f"Nhóm 20 hóa đơn không có tổ hợp nào khớp (ca chậm nhất của brute-force cũ) phải chạy XONG "
    f"trong vài giây — got {thoi_gian:.2f}s (đúng bug thật: 'chạy đối chiếu hơn 5 phút chưa xong')")
print(f"PASS 5: nhóm 20 hóa đơn không có tổ hợp nào khớp (ca chậm nhất) chạy xong trong {thoi_gian:.3f}s "
      f"— không còn treo hàng phút như báo cáo thật.")

print("\nALL DONE")
