import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test cho _thu_lai_tai_file_loi() trong server.py — người dùng báo lại
# ảnh chụp "CÒN 175 FILE CHƯA TẢI ĐƯỢC" sau khi tra cứu, rồi yêu cầu: "hãy tải đầy
# đủ file không được thiếu file nào trong quá trình tra cứu". TRƯỚC ĐÂY (_run_fetch_job)
# chỉ thử lại ĐÚNG 1 LƯỢT cho các file lỗi rồi bỏ cuộc luôn dù còn thiếu (thường chỉ
# do bị chặn tốc độ TẠM THỜI giữa chừng — chờ/thử thêm vài lượt là qua), bắt người
# dùng phải tự nhận ra rồi tự bấm tra cứu lại. Fix: tách chính sách thử lại thành
# hàm THUẦN _thu_lai_tai_file_loi(), thử lại NHIỀU LƯỢT (chờ tăng dần) cho tới khi
# hết lỗi HẲN hoặc hết số lượt thử tối đa hoặc có tín hiệu phải dừng ngay (token hết
# hạn/người dùng huỷ).


def extract_fn(name):
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


import time
ns = {'time': time}
exec(extract_fn('_thu_lai_tai_file_loi'), ns)
_thu_lai_tai_file_loi = ns['_thu_lai_tai_file_loi']

# ----- Test 1: file lỗi do bị chặn tốc độ TẠM THỜI — 3 hóa đơn lỗi ở lượt 1, chỉ
# còn 1 lỗi ở lượt 2, hết lỗi hẳn ở lượt 3 -> PHẢI thử ĐỦ 3 lượt và trả về HẾT lỗi,
# không được dừng/bỏ cuộc sau đúng 1 lượt như hành vi cũ. -----
ket_qua_theo_lan = {
    1: (2, ["hd3"], 0, 0),      # lượt 1: tải được 2/3, còn hd3 lỗi
    2: (1, [], 0, 0),           # lượt 2: hd3 tải được luôn -> hết lỗi
}
so_lan_da_goi = []


def tai_lai_fn_1(ds_loi, lan):
    so_lan_da_goi.append((lan, list(ds_loi)))
    return ket_qua_theo_lan[lan]


sleeps = []
tong_ok, loi_con, tong_bo_qua, tong_km, so_lan = _thu_lai_tai_file_loi(
    tai_lai_fn_1, ["hd1", "hd2", "hd3"], so_lan_toi_da=8, sleep_fn=lambda s: sleeps.append(s))
assert loi_con == [], f"Phải hết lỗi HẲN sau khi thử đủ số lượt cần thiết — got loi_con={loi_con}"
assert tong_ok == 3, f"Tổng số file tải thành công qua các lượt PHẢI cộng dồn đủ (2+1=3) — got {tong_ok}"
assert so_lan == 2, f"Phải dừng NGAY khi hết lỗi (2 lượt là đủ, không thử thêm lượt 3 vô ích) — got {so_lan}"
assert sleeps == [5, 10], f"Thời gian chờ PHẢI tăng dần theo từng lượt (5s, 10s...) — got {sleeps}"
print("PASS 1: file lỗi do chặn tốc độ tạm thời -> thử lại NHIỀU LƯỢT (không dừng sau đúng 1 lượt như "
      "trước) cho tới khi hết lỗi HẲN, dừng ngay khi đã đủ (không thử thừa).")

# ----- Test 2 (không hồi quy — quan trọng): lỗi THẬT SỰ dai dẳng (không bao giờ hết)
# -> PHẢI dừng lại sau ĐÚNG so_lan_toi_da lượt (không lặp vô hạn, tránh treo cả quá
# trình tra cứu), vẫn trả về đúng danh sách lỗi còn lại để báo cho người dùng. -----
def tai_lai_fn_2(ds_loi, lan):
    return 0, list(ds_loi), 0, 0   # không bao giờ tải được, lỗi mãi


tong_ok2, loi_con2, _, _, so_lan2 = _thu_lai_tai_file_loi(
    tai_lai_fn_2, ["hd-loi-mai"], so_lan_toi_da=8, sleep_fn=lambda s: None)
assert so_lan2 == 8, f"Phải DỪNG đúng sau so_lan_toi_da=8 lượt với lỗi dai dẳng, không lặp vô hạn — got {so_lan2}"
assert loi_con2 == ["hd-loi-mai"], f"Vẫn phải trả đúng danh sách lỗi CÒN LẠI để báo người dùng — got {loi_con2}"
print("PASS 2: lỗi thật sự dai dẳng (không bao giờ hết) -> dừng đúng sau số lượt tối đa, không treo vô "
      "hạn, vẫn báo đúng danh sách còn lỗi.")

# ----- Test 3: không có lỗi nào ngay từ đầu -> KHÔNG thử lại lượt nào (tránh chờ vô
# ích khi đã tải đủ hết ngay từ lượt đầu tiên, trước khi gọi hàm này). -----
so_lan_goi_3 = []
tong_ok3, loi_con3, _, _, so_lan3 = _thu_lai_tai_file_loi(
    lambda ds, lan: so_lan_goi_3.append(lan) or (0, [], 0, 0),
    [], so_lan_toi_da=8, sleep_fn=lambda s: None)
assert so_lan3 == 0 and so_lan_goi_3 == [], f"Không có lỗi ban đầu -> KHÔNG được gọi thử lại lượt nào — got so_lan={so_lan3}"
print("PASS 3: không có file lỗi ngay từ đầu -> không thử lại lượt nào, không chờ vô ích.")

# ----- Test 4: tín hiệu phải dừng NGAY (token hết hạn/người dùng huỷ) -> dừng SỚM
# giữa chừng dù còn lỗi và chưa hết số lượt tối đa (không cố thử tiếp vô ích). -----
da_goi_4 = []


def tai_lai_fn_4(ds_loi, lan):
    da_goi_4.append(lan)
    return 0, list(ds_loi), 0, 0


tong_ok4, loi_con4, _, _, so_lan4 = _thu_lai_tai_file_loi(
    tai_lai_fn_4, ["hd-x"], so_lan_toi_da=8, sleep_fn=lambda s: None,
    nen_dung_fn=lambda: True)   # báo phải dừng NGAY từ đầu (vd token đã hết hạn)
assert so_lan4 == 0 and da_goi_4 == [], (
    f"Có tín hiệu phải dừng ngay (nen_dung_fn=True) -> KHÔNG được thử lại lượt nào — got so_lan={so_lan4}")
assert loi_con4 == ["hd-x"], "Vẫn phải trả đúng danh sách lỗi (chưa xử lý được) khi dừng sớm"
print("PASS 4: có tín hiệu phải dừng ngay (token hết hạn/người dùng huỷ) -> dừng sớm ngay, không cố "
      "thử lại vô ích.")

print("\nALL DONE")
