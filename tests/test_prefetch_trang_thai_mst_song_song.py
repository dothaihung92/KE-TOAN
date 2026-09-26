import os
import re
import time
import threading

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test cho _prefetch_trang_thai_mst() (nested trong export_excel(),
# server.py) — người dùng yêu cầu sau khi thấy xuất Excel bị chậm/treo lâu với
# công ty có nhiều nhà cung cấp/khách hàng khác nhau: "có thể kiểm tra nhiều
# luồn được đẩy 3 luồn kiểm tra luôn phiên" — tra tình trạng nhiều MST SONG
# SONG (ban đầu mặc định 3 luồng, tăng lên 8 khi tracuunnt.gdt.gov.vn trở
# thành nguồn ưu tiên 1 — chậm hơn hẳn XInvoice — rồi GIẢM DẦN 8 -> 5 -> lại
# 3 sau 2 lần log thật liên tiếp cho thấy CÀNG NHIỀU luồng CÀNG tệ, nghi bị
# WAF chặn — xem Test 6) thay vì tuần tự từng cái, để tận dụng đầy đủ ngân
# sách thời gian
# (_MST_NGAN_SACH_GIAY) dò được nhiều MST hơn trong cùng thời gian.


def extract_nested_fn(name):
    """Trích xuất hàm NESTED bên trong export_excel() — dò theo ĐÚNG mức thụt
    lề của chính dòng 'def name(' (không phải cột 0), dừng ở dòng đầu tiên
    thụt lề <= mức đó (ranh giới thật của hàm nested)."""
    idx = src.index('def ' + name + '(')
    line_start = src.rfind('\n', 0, idx) + 1
    def_indent = idx - line_start
    i = src.index(':', idx)
    lines = src[i + 1:].split('\n')
    body = []
    started = False
    for ln in lines:
        if ln.strip() == '':
            body.append(ln)
            continue
        indent = len(ln) - len(ln.lstrip(' '))
        if indent <= def_indent and started:
            break
        started = True
        body.append(ln)
    return src[idx:i + 1] + '\n'.join(body)


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


ns = {'time': time}
exec(extract_fn('_chuan_mst'), ns)
m = re.search(r'^_MST_NGAN_SACH_GIAY\s*=\s*(None|[\d.]+)', src, re.M)
exec(m.group(0), ns)
ns['_MST_TIEN_DO'] = {}
ns['_TRACUUNNT_TD'] = {"mst_dang_tra": ""}
ns['cid'] = 1

# Mô phỏng _tra_cuu_trang_thai_mst() thật — mỗi lượt gọi "chậm" NGANG NHAU (mô
# phỏng độ trễ mạng thật khi gọi API XInvoice), ghi lại thời điểm bắt
# đầu/kết thúc từng lượt để kiểm chứng có THẬT SỰ chạy song song hay không
# (nếu chạy song song, nhiều lượt sẽ CHỒNG LẤN thời gian nhau; nếu tuần tự,
# các lượt sẽ nối đuôi nhau không chồng lấn).
DO_TRE_GIAY = 0.12
_calls_lock = threading.Lock()
_call_intervals = []
_call_count = {"n": 0}


def _fake_tra_cuu(mst, so_lan_that_bai_lien_tiep=None, chi_dung_cache=False):
    t0 = time.time()
    with _calls_lock:
        _call_count["n"] += 1
    time.sleep(DO_TRE_GIAY)
    t1 = time.time()
    with _calls_lock:
        _call_intervals.append((t0, t1))
    return {"trang_thai": "Đang hoạt động", "canh_bao": False}


_tlog_msgs = []
ns['_tra_cuu_trang_thai_mst'] = _fake_tra_cuu
ns['_mst_status_local'] = {}
ns['_mst_fail_counter'] = [0]
ns['_mst_bat_dau'] = time.time()
ns['_tlog'] = lambda m: _tlog_msgs.append(m)
ns['_tracuunnt_dat_lai_dem_loi'] = lambda: None

exec(extract_nested_fn('_lay_trang_thai_mst_cached'), ns)
exec(extract_nested_fn('_prefetch_trang_thai_mst'), ns)
_prefetch_trang_thai_mst = ns['_prefetch_trang_thai_mst']
_mst_status_local = ns['_mst_status_local']


def _chong_lan(intervals):
    """True nếu có ÍT NHẤT 2 khoảng thời gian trong danh sách CHỒNG LẤN nhau
    — bằng chứng trực tiếp cho thấy các lượt gọi THẬT SỰ chạy song song
    (khác hẳn chạy tuần tự, nơi mỗi lượt luôn bắt đầu SAU khi lượt trước đã
    kết thúc, không bao giờ chồng lấn)."""
    for i in range(len(intervals)):
        for j in range(i + 1, len(intervals)):
            a0, a1 = intervals[i]
            b0, b1 = intervals[j]
            if a0 < b1 and b0 < a1:
                return True
    return False


# ----- Test 1 (QUAN TRỌNG — đúng yêu cầu người dùng): 9 MST khác nhau, mỗi lượt
# tra "chậm" 0.12s -> nếu chạy SONG SONG 3 luồng, phải xong NHANH HƠN HẲN so với
# chạy tuần tự (9 x 0.12s = 1.08s) VÀ phải có ít nhất 2 lượt CHỒNG LẤN thời gian
# nhau (bằng chứng trực tiếp là đa luồng thật, không phải giả vờ). -----
_call_intervals.clear()
_call_count["n"] = 0
_tlog_msgs.clear()
ds_mst = [f"03{i:08d}" for i in range(9)]
t_bd = time.time()
_prefetch_trang_thai_mst("BK Test", ds_mst, so_luong_song_song=3)
t_kt = time.time()
thoi_gian_thuc_te = t_kt - t_bd
thoi_gian_tuan_tu = len(ds_mst) * DO_TRE_GIAY
assert _call_count["n"] == 9, f"Phải tra ĐỦ cả 9 MST khác nhau — got {_call_count['n']}"
assert thoi_gian_thuc_te < thoi_gian_tuan_tu * 0.7, (
    f"Chạy SONG SONG 3 luồng phải NHANH HƠN HẲN tuần tự — tuần tự sẽ mất ~{thoi_gian_tuan_tu:.2f}s, "
    f"song song đo được {thoi_gian_thuc_te:.2f}s (kỳ vọng < {thoi_gian_tuan_tu*0.7:.2f}s)")
assert _chong_lan(_call_intervals), (
    "Phải có ÍT NHẤT 2 lượt gọi CHỒNG LẤN thời gian nhau — bằng chứng trực tiếp chạy đa luồng thật, "
    "không phải giả vờ nhanh nhờ nguyên nhân khác")
for mst in ds_mst:
    key = ns['_chuan_mst'](mst)[:10]
    assert _mst_status_local.get(key, {}).get("canh_bao") is False, f"Kết quả phải được đổ vào _mst_status_local cho MST {mst}"
print(f"PASS 1: 9 MST khác nhau tra SONG SONG (3 luồng) mất {thoi_gian_thuc_te:.2f}s, "
      f"nhanh hơn hẳn tuần tự (~{thoi_gian_tuan_tu:.2f}s), có lượt chồng lấn thời gian thật — "
      "đúng yêu cầu người dùng.")

# ----- Test 1b (đúng yêu cầu người dùng "hãy hiện thông tin quá trình đối chiếu
# và còn bao nhiêu để người dùng biết"): phải có log báo tiến độ dạng "đã
# xong/tổng" ở lúc bắt đầu (0/9) và lúc kết thúc (9/9), kèm tên nhãn để phân
# biệt đang ở bước nào (BK Mua vào/BK Bán ra). -----
assert any("0/9" in m and "BK Test" in m for m in _tlog_msgs), (
    f"Phải có log báo bắt đầu '0/9' kèm tên bước — got {_tlog_msgs}")
assert any("9/9" in m and "BK Test" in m for m in _tlog_msgs), (
    f"Phải có log báo hoàn tất '9/9' kèm tên bước — got {_tlog_msgs}")
print("PASS 1b: có log báo tiến độ dạng 'đã xong/tổng' (0/9 lúc bắt đầu, 9/9 lúc xong) kèm tên bước, "
      "đúng yêu cầu người dùng 'hiện thông tin quá trình và còn bao nhiêu để người dùng biết'.")

# ----- Test 2 (không hồi quy — quan trọng): DANH SÁCH có MST TRÙNG NHAU nhiều
# lần (đúng thực tế 1 nhà cung cấp xuất hóa đơn nhiều lần) -> chỉ tra ĐÚNG 1 LẦN
# cho mỗi MST duy nhất, không tra trùng lặp dù đưa vào danh sách nhiều lần. -----
_call_intervals.clear()
_call_count["n"] = 0
ns['_mst_status_local'].clear()
ds_trung = ["0311112222"] * 5 + ["0322223333"] * 3
_prefetch_trang_thai_mst("BK Test", ds_trung, so_luong_song_song=3)
assert _call_count["n"] == 2, f"Chỉ được tra ĐÚNG 1 lần cho mỗi MST duy nhất (2 MST khác nhau) — got {_call_count['n']}"
print("PASS 2: MST trùng lặp nhiều lần trong danh sách (1 NCC xuất nhiều hóa đơn) -> chỉ tra đúng 1 "
      "lần cho mỗi MST duy nhất, không lãng phí lượt gọi.")

# ----- Test 3 (không hồi quy): MST ĐÃ CÓ SẴN trong _mst_status_local (đã tra
# từ trước, vd 1 lượt prefetch trước đó hoặc tra inline) -> KHÔNG tra lại. -----
_call_intervals.clear()
_call_count["n"] = 0
ns['_mst_status_local'].clear()
ns['_mst_status_local']["0333334444"] = {"trang_thai": "Đang hoạt động", "canh_bao": False}
_prefetch_trang_thai_mst("BK Test", ["0333334444", "0344445555"], so_luong_song_song=3)
assert _call_count["n"] == 1, f"MST đã có sẵn trong cache cục bộ KHÔNG được tra lại — got {_call_count['n']}"
print("PASS 3: MST đã có sẵn trong cache cục bộ (_mst_status_local) -> không tra lại, chỉ tra MST mới.")

# ----- Test 4 (an toàn): danh sách rỗng -> không tạo thread pool, không lỗi. -----
_call_count["n"] = 0
_prefetch_trang_thai_mst("BK Test", [], so_luong_song_song=3)
assert _call_count["n"] == 0
print("PASS 4: danh sách rỗng -> không làm gì, không lỗi.")

# ----- Test 5 (MỚI — đúng câu hỏi người dùng hỏi đi hỏi lại "sao vẫn còn?"/
# "thực tế dò chỉ còn 4 mst thôi?" khi thấy log báo N MST chưa dò được mà
# không rõ MST nào đang bị lỗi gì): log tổng kết PHẢI liệt kê ĐẦY ĐỦ TỪNG
# MST chưa lấy được tình trạng KÈM lý do cụ thể của CHÍNH MST đó — khác hẳn
# trước đây chỉ in 1 "VÍ DỤ LỖI GẶP PHẢI" DUY NHẤT (không đủ để biết CÁC MST
# còn lại có cùng nguyên nhân hay không, hay mỗi MST bị 1 lỗi khác nhau). -----
def _fake_tra_cuu_hon_hop(mst, so_lan_that_bai_lien_tiep=None, chi_dung_cache=False):
    if mst.endswith("1"):
        return {"trang_thai": "Đang hoạt động", "canh_bao": False}
    if mst.endswith("2"):
        return {"trang_thai": "", "canh_bao": None, "ly_do_loi": f"LY DO RIENG CUA {mst}"}
    return {"trang_thai": "", "canh_bao": None}   # không có ly_do_loi cụ thể


ns['_tra_cuu_trang_thai_mst'] = _fake_tra_cuu_hon_hop   # late-binding qua ns (globals của hàm đã exec)
ns['_mst_status_local'].clear()
_tlog_msgs.clear()
ds_hon_hop = ["0300000001", "0300000002", "0300000003"]
_prefetch_trang_thai_mst("BK Hon Hop", ds_hon_hop, so_luong_song_song=3)
dong_ket = next((m for m in _tlog_msgs if "CHI TIẾT TỪNG MST" in m), None)
assert dong_ket is not None, f"Phải có dòng log liệt kê CHI TIẾT TỪNG MST chưa dò được — got {_tlog_msgs}"
assert "0300000002" in dong_ket and "LY DO RIENG CUA 0300000002" in dong_ket, (
    f"Phải liệt kê MST 0300000002 KÈM đúng lý do riêng của chính MST đó — got {dong_ket}")
assert "0300000003" in dong_ket and "không rõ lý do" in dong_ket, (
    f"MST không có ly_do_loi cụ thể vẫn phải liệt kê, kèm 'không rõ lý do' — got {dong_ket}")
assert "0300000001" not in dong_ket, (
    f"MST đã tra THÀNH CÔNG (có trạng thái) KHÔNG được liệt kê vào danh sách chưa dò được — got {dong_ket}")
print("PASS 5: log tổng kết liệt kê ĐẦY ĐỦ từng MST chưa lấy được tình trạng KÈM lý do cụ thể của "
      "chính MST đó, thay vì chỉ 1 ví dụ lỗi duy nhất — giúp chẩn đoán rõ ràng khi người dùng hỏi lại "
      "'sao vẫn còn?'.")

# ===== Test 6 (QUAN TRỌNG — đúng lựa chọn người dùng đã xác nhận, ĐÃ ĐIỀU
# CHỈNH LẠI 2 LẦN theo log thật): mặc định PHẢI là 3 luồng (quay về giá trị
# GỐC) — lịch sử: 3 (gốc) -> tăng 8 khi tracuunnt.gdt.gov.vn thành nguồn ưu
# tiên 1 -> log thật TỆ HƠN HẲN (chỉ 4/77 tra được, kèm "Connection
# aborted") -> giảm xuống 5 -> log thật VẪN còn tệ (15/77, dù đỡ hơn 8) —
# CÙNG điều kiện (XInvoice tạm dừng) ở cả 2 lần đo, xu hướng RÕ: càng ít
# luồng càng tra được nhiều hơn, dấu hiệu chắc chắn bị WAF của
# tracuunnt.gdt.gov.vn giới hạn theo số phiên đồng thời -> GIẢM TIẾP về lại
# 3 (mức cao nhất từng đo tỷ lệ thành công tốt). Lệnh gọi THẬT trong
# export_excel() (không truyền so_luong_song_song, dùng mặc định của hàm)
# phải dùng đúng số luồng mới này. =====
than_nested = extract_nested_fn('_prefetch_trang_thai_mst')
m6 = re.search(r'def _prefetch_trang_thai_mst\([^)]*so_luong_song_song\s*=\s*(\d+)', than_nested)
assert m6 is not None and m6.group(1) == '3', (
    f"Mặc định so_luong_song_song PHẢI là 3 (giảm từ 5 rồi từ 8, đúng lựa chọn người dùng đã xác nhận "
    f"sau khi log thật 2 lần liên tiếp cho thấy CÀNG NHIỀU luồng CÀNG tệ — nghi bị WAF của "
    f"tracuunnt.gdt.gov.vn giới hạn theo số phiên đồng thời) — got {m6.group(1) if m6 else None}")
loi_goi_that = re.search(r'_prefetch_trang_thai_mst\(\s*"BK Mua vào"[^)]*\)', src)
assert loi_goi_that is not None and 'so_luong_song_song' not in loi_goi_that.group(0), (
    "Lệnh gọi thật trong export_excel() (sheet BK Mua vào) phải KHÔNG truyền so_luong_song_song riêng, "
    "để dùng đúng mặc định mới của hàm — nếu test này fail nghĩa là có ai đó đã ghi đè giá trị khác ở "
    "đây, cần xem lại cho khớp.")
print("PASS 6: mặc định so_luong_song_song=3 (quay về giá trị gốc sau 2 lần điều chỉnh giảm dần theo "
      "log thật, nghi bị WAF chặn), lệnh gọi thật trong export_excel() dùng đúng mặc định này.")

print("\nALL DONE")
