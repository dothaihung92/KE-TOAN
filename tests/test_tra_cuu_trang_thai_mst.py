import os
import re
import json
import threading

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test cho tính năng "dò tình trạng hoạt động MST khi xuất Excel"
# (_phan_loai_trang_thai_mst / _tra_cuu_trang_thai_mst trong server.py) —
# người dùng yêu cầu ban đầu: "hãy thêm chức năng dò mst còn đang hoạt động
# hay không hoặc công ty cần xác minh địa chỉ kinh doanh khi kết xuất ra
# excel thêm 1 cột trạng thái mst ở cuối công ty nào bị khoá mst hoặc báo
# chờ xác minh tình trạng hoạt động tại địa chỉ thì trong file excel tô đỏ
# dòng đó".
#
# CHUỖI NGUỒN TRA MST ĐÃ CHỐT (đúng yêu cầu người dùng: "GIữ
# tracuunnt.gdt.gov.vn + XInvoice, BỊ VietQR/masothue.com"): NGUỒN ƯU TIÊN 1
# là tracuunnt.gdt.gov.vn (cổng công khai chính thức của Tổng cục Thuế, miễn
# phí, không hạn mức gói) — _goi_1_lan_xinvoice (API trả phí, cần client-id/
# api-key) là NGUỒN DỰ PHÒNG, CHỈ gọi khi tracuunnt.gdt.gov.vn không tra
# được VÀ chưa bị tạm dừng. VietQR (api.vietqr.io) và masothue.com đã BỎ HẲN
# khỏi server.py. XInvoice hiện ĐANG TẠM DỪNG (_XINVOICE_TAM_DUNG=True,
# code vẫn còn nguyên) — log thật cho thấy cả 2 key đã cấu hình đều hết hạn
# mức gói (HTTP 429)/timeout, gọi dự phòng chỉ tốn thêm thời gian vô ích —
# xem Test 15. Các test 8-14 CHỦ ĐỘNG mở cờ này ra (_XINVOICE_TAM_DUNG=False
# trong ns) để kiểm tra riêng LOGIC chuỗi dự phòng (thứ tự ưu tiên, luân
# phiên key XInvoice, gộp tiền tố lỗi), không phụ thuộc giá trị THẬT đang
# cấu hình lúc này. File test này CHỈ kiểm tra phần orchestration CHUNG
# (validate MST, circuit breaker, ngân sách thời gian) qua 2 stub đơn giản
# cho _tra_cuu_mst_qua_tracuunnt/_goi_1_lan_xinvoice — hành vi THẬT của
# tracuunnt.gdt.gov.vn (session/captcha/HTML) có test riêng ở
# test_tra_mst_qua_tracuunnt.py. Cũng KHÔNG có cache dài hạn (bảng
# mst_status_cache) — LUÔN tra cứu thật sự qua mạng mỗi lần gọi (trừ dedup
# trong bộ nhớ CHỈ trong CÙNG 1 lượt xuất Excel — xem _mst_status_local ở
# export_excel, không có trong phạm vi test file này).


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


class _FakeTime:
    """Thay cho module time thật — ghi lại các lượt sleep() thay vì chờ
    thật (_tra_cuu_trang_thai_mst nghỉ 1 chút trước mỗi lượt gọi API thật)."""
    def __init__(self):
        self.sleeps = []

    def sleep(self, s):
        self.sleeps.append(s)


class _FakeTracuunnt:
    """Thay cho _tra_cuu_mst_qua_tracuunnt() thật — kiểm soát được kết quả
    trả về qua .ket_qua, đếm số lượt gọi qua .calls, KHÔNG mô phỏng lại
    request/session/captcha thật (đã kiểm tra riêng ở
    test_tra_mst_qua_tracuunnt.py) vì file này chỉ quan tâm hành vi
    orchestration CHUNG của _tra_cuu_trang_thai_mst."""
    def __init__(self):
        self.calls = 0
        self.ket_qua = (True, "NNT đang hoạt động", False, None)

    def __call__(self, mst_c, timeout):
        self.calls += 1
        return self.ket_qua


class _FakeXInvoice:
    """Thay cho _goi_1_lan_xinvoice() thật — kiểm soát được kết quả trả về
    THEO TỪNG KEY (client_id) qua .ket_qua_theo_key (dict client_id -> tuple
    5 phần tử), đếm số lượt gọi (.calls) và ghi lại đúng client_id nào đã
    được gọi (.client_ids_da_goi) để test được đúng thứ tự luân phiên key.
    KHÔNG mô phỏng lại request HTTP thật (đó là việc của 1 file test riêng
    cho XInvoice nếu cần sau này) — file này chỉ quan tâm orchestration
    CHUNG của _tra_cuu_trang_thai_mst (khi nào gọi XInvoice, luân phiên key
    ra sao)."""
    def __init__(self):
        self.calls = 0
        self.client_ids_da_goi = []
        # mặc định: bất kỳ key nào cũng thành công ngay
        self.ket_qua_theo_key = {}
        self.ket_qua_mac_dinh = (True, "NNT đang hoạt động", False, None, False)

    def __call__(self, mst_c, client_id, api_key, timeout):
        self.calls += 1
        self.client_ids_da_goi.append(client_id)
        return self.ket_qua_theo_key.get(client_id, self.ket_qua_mac_dinh)


ns = {'json': json, 'threading': threading}
exec(extract_fn('_khong_dau'), ns)
exec(extract_fn('_chuan_mst'), ns)
exec(extract_fn('_phan_loai_trang_thai_mst'), ns)
m2 = re.search(r'^_MST_API_NGHI_GIUA_LUOT\s*=\s*[\d.]+', src, re.M)
exec(m2.group(0), ns)

_fake_time = _FakeTime()
ns['time'] = _fake_time
_fake_tracuunnt = _FakeTracuunnt()
ns['_tra_cuu_mst_qua_tracuunnt'] = _fake_tracuunnt
_fake_xinvoice = _FakeXInvoice()
ns['_goi_1_lan_xinvoice'] = _fake_xinvoice
_danh_sach_keys_gia = [{"client_id": "key1", "api_key": "sec1"}]
ns['_lay_danh_sach_xinvoice_keys'] = lambda: _danh_sach_keys_gia
ns['_XINVOICE_KEY_STATE'] = {"idx": 0, "lock": threading.Lock()}
# CÁC TEST TỪ 8 TRỞ ĐI (trừ Test 15) kiểm tra ĐÚNG LOGIC chuỗi dự phòng
# tracuunnt.gdt.gov.vn -> XInvoice — nên CHỦ ĐỘNG mở cờ này (False = KHÔNG
# tạm dừng) để test được logic đó, KHÔNG PHỤ THUỘC giá trị THẬT
# (_XINVOICE_TAM_DUNG=True) đang cấu hình trong server.py lúc này (log thật
# cho thấy cả 2 key XInvoice đều hết hạn mức gói/timeout, người dùng xác
# nhận tạm dừng gọi XInvoice — xem Test 15 kiểm tra ĐÚNG hành vi khi cờ THẬT
# đang bật).
ns['_XINVOICE_TAM_DUNG'] = False
exec(extract_fn('_tra_cuu_trang_thai_mst'), ns)
_phan_loai_trang_thai_mst = ns['_phan_loai_trang_thai_mst']
_tra_cuu_trang_thai_mst = ns['_tra_cuu_trang_thai_mst']


def _reset():
    _fake_tracuunnt.calls = 0
    _fake_tracuunnt.ket_qua = (True, "NNT đang hoạt động", False, None)
    _fake_xinvoice.calls = 0
    _fake_xinvoice.client_ids_da_goi = []
    _fake_xinvoice.ket_qua_theo_key = {}
    _fake_xinvoice.ket_qua_mac_dinh = (True, "NNT đang hoạt động", False, None, False)
    _danh_sach_keys_gia[:] = [{"client_id": "key1", "api_key": "sec1"}]
    ns['_XINVOICE_KEY_STATE']["idx"] = 0
    ns['_XINVOICE_TAM_DUNG'] = False


# ===== Test 1-6: _phan_loai_trang_thai_mst() — phân loại theo nội dung trường
# "status" trả về từ API, các ca thường gặp (đúng cụm mô tả chính thức của Tổng
# cục Thuế). =====
_, cb = _phan_loai_trang_thai_mst("Người nộp thuế đang hoạt động (đã cấp GCN ĐKT)")
assert cb is False, f"'đang hoạt động' PHẢI được coi là bình thường (canh_bao=False) — got {cb}"
print("PASS 1: 'đang hoạt động' -> canh_bao=False (bình thường, không tô đỏ).")

nhan, cb = _phan_loai_trang_thai_mst(
    "NNT đang trong quá trình chờ xác minh tình trạng hoạt động tại địa chỉ đã đăng ký")
assert cb is True, f"'chờ xác minh tình trạng hoạt động tại địa chỉ' PHẢI cảnh báo (canh_bao=True) — got {cb}"
assert "xác minh" in nhan.lower()
print("PASS 2: 'chờ xác minh tình trạng hoạt động tại địa chỉ' -> canh_bao=True (đúng yêu cầu người dùng).")

_, cb = _phan_loai_trang_thai_mst("Người nộp thuế đã bị khóa mã số thuế")
assert cb is True, f"'đã bị khóa mã số thuế' PHẢI cảnh báo — got {cb}"
print("PASS 3: 'đã bị khóa mã số thuế' -> canh_bao=True.")

_, cb = _phan_loai_trang_thai_mst("NNT ngừng hoạt động nhưng chưa hoàn thành thủ tục đóng mã số thuế")
assert cb is True, f"'ngừng hoạt động' PHẢI cảnh báo — got {cb}"
print("PASS 4: 'ngừng hoạt động nhưng chưa hoàn thành thủ tục đóng MST' -> canh_bao=True.")

_, cb = _phan_loai_trang_thai_mst("Không hoạt động tại địa chỉ đã đăng ký")
assert cb is True, f"'không hoạt động tại địa chỉ đã đăng ký' PHẢI cảnh báo — got {cb}"
print("PASS 5: 'không hoạt động tại địa chỉ đã đăng ký' -> canh_bao=True.")

_, cb = _phan_loai_trang_thai_mst("")
assert cb is None, f"KHÔNG có dữ liệu tình trạng -> canh_bao=None (KHÔNG suy đoán/không tô đỏ) — got {cb}"
print("PASS 6: không có dữ liệu tình trạng -> canh_bao=None, không suy đoán bừa.")

# ===== Test 6b (bug THẬT người dùng vừa báo qua log xuất Excel — "kiểm tra
# lại sao phần mềm không kiểm tra đủ thông tin"): nhiều MST thật (vd
# 0106869738-005, 0315482212, 0316642412) trả về tình trạng VIẾT TẮT "NNT
# ngừng HĐ nhưng chưa hoàn thành thủ tục chấm dứt hiệu lực MST" ("HĐ" =
# "hoạt động", "MST" = "mã số thuế") — các cụm từ khoá ĐẦY ĐỦ ở Test 4 KHÔNG
# khớp được cụm viết tắt này, trước đây rơi vào "tình trạng lạ chưa nhận
# diện được" (canh_bao=None, coi là THẤT BẠI) dù MST thật sự đang ở tình
# trạng xấu này -> PHẢI nhận diện được cả biến thể viết tắt. =====
nhan6b, cb6b = _phan_loai_trang_thai_mst(
    "NNT ngừng HĐ nhưng chưa hoàn thành thủ tục chấm dứt hiệu lực MST")
assert cb6b is True, (
    f"Biến thể VIẾT TẮT 'ngừng HĐ...chấm dứt hiệu lực MST' PHẢI được nhận diện là CẢNH BÁO (canh_bao=True) "
    f"giống hệt cụm đầy đủ 'ngừng hoạt động...đóng mã số thuế' — got {cb6b}")
assert "ngừng hoạt động" in nhan6b.lower(), f"got {nhan6b}"
print("PASS 6b: biến thể viết tắt 'ngừng HĐ...chấm dứt hiệu lực MST' -> canh_bao=True (khớp đúng như "
      "cụm đầy đủ), sửa đúng bug thật khiến các MST như 0106869738-005/0315482212/0316642412 không "
      "được nhận diện đúng tình trạng.")

# ===== Test 7 (QUAN TRỌNG — chẩn đoán "sao vẫn còn?"): MST rỗng/"KL" (khách
# lẻ)/quá ngắn -> KHÔNG gọi mạng, trả canh_bao=None. "" và "KL" là CHỦ Ý bỏ
# qua (không phải lỗi) nên KHÔNG kèm ly_do_loi; còn "123" (có chữ nhưng
# KHÔNG đủ 9-10 chữ số — dấu hiệu dữ liệu MST trên hóa đơn gốc bị lỗi/thiếu/
# sai định dạng) PHẢI kèm ly_do_loi để _prefetch_trang_thai_mst() còn hiện
# được trong "VÍ DỤ LỖI GẶP PHẢI". =====
_reset()
r7a = _tra_cuu_trang_thai_mst("", timeout=1)
r7b = _tra_cuu_trang_thai_mst("KL", timeout=1)
r7c = _tra_cuu_trang_thai_mst("123", timeout=1)
assert r7a["canh_bao"] is None and r7b["canh_bao"] is None and r7c["canh_bao"] is None
assert _fake_tracuunnt.calls == 0 and _fake_xinvoice.calls == 0, (
    f"MST rỗng/'KL'/quá ngắn KHÔNG được gọi mạng (tránh tra cứu vô nghĩa cho khách lẻ dùng chung mã) "
    f"— got tracuunnt={_fake_tracuunnt.calls}, xinvoice={_fake_xinvoice.calls}")
assert "ly_do_loi" not in r7a and "ly_do_loi" not in r7b, (
    f"MST rỗng/'KL' là CHỦ Ý bỏ qua (khách lẻ dùng chung mã), KHÔNG phải lỗi -> không kèm ly_do_loi "
    f"— got r7a={r7a}, r7b={r7b}")
assert "không hợp lệ" in (r7c.get("ly_do_loi") or ""), (
    f"MST '123' (không đủ 9-10 chữ số) -> PHẢI kèm ly_do_loi ghi rõ 'không hợp lệ' — got {r7c}")
print("PASS 7: MST rỗng/'KL' (khách lẻ dùng chung mã) -> bỏ qua hẳn, không gọi mạng, không kèm "
      "ly_do_loi (chủ ý, không phải lỗi); MST quá ngắn/sai định dạng -> vẫn bỏ qua nhưng kèm ly_do_loi "
      "rõ ràng để chẩn đoán.")

# ===== Test 8 (đúng ca thật — MST hợp lệ, tracuunnt.gdt.gov.vn thành công
# NGAY LẦN ĐẦU): phải gọi tracuunnt ĐÚNG 1 lần, KHÔNG được gọi XInvoice
# (giữ hạn mức gói XInvoice cho lúc thật sự cần). =====
_reset()
r8 = _tra_cuu_trang_thai_mst("0315696199", timeout=1)
assert r8["canh_bao"] is False and r8["trang_thai"] == "NNT đang hoạt động", f"got {r8}"
assert _fake_tracuunnt.calls == 1, f"Phải gọi tracuunnt.gdt.gov.vn đúng 1 lần — got {_fake_tracuunnt.calls}"
assert _fake_xinvoice.calls == 0, (
    f"tracuunnt.gdt.gov.vn đã thành công -> KHÔNG được gọi XInvoice (giữ hạn mức gói) "
    f"— got {_fake_xinvoice.calls}")
assert "ly_do_loi" not in r8, f"Tra thành công thì không được kèm ly_do_loi — got {r8}"
print("PASS 8: MST hợp lệ, tracuunnt.gdt.gov.vn thành công -> gọi đúng 1 lần, KHÔNG gọi XInvoice, "
      "lấy đúng tình trạng.")

# ===== Test 9 (QUAN TRỌNG — chuỗi dự phòng): tracuunnt.gdt.gov.vn thất bại ->
# PHẢI tự động thử XInvoice (dự phòng), và nếu XInvoice thành công thì
# ly_do_loi được XOÁ (không còn báo lỗi dù tracuunnt lỗi, vì cuối cùng vẫn
# tra được). =====
_reset()
_fake_tracuunnt.ket_qua = (False, "", None, "không giải được captcha (OCR không đọc ra)")
_fake_xinvoice.ket_qua_mac_dinh = (True, "NNT đang hoạt động", False, None, False)
r9 = _tra_cuu_trang_thai_mst("0315696200", timeout=1)
assert r9["canh_bao"] is False and r9["trang_thai"] == "NNT đang hoạt động", f"got {r9}"
assert _fake_tracuunnt.calls == 1 and _fake_xinvoice.calls == 1, (
    f"tracuunnt lỗi -> PHẢI thử XInvoice dự phòng đúng 1 lần "
    f"— got tracuunnt={_fake_tracuunnt.calls}, xinvoice={_fake_xinvoice.calls}")
assert "ly_do_loi" not in r9, (
    f"XInvoice dự phòng cuối cùng THÀNH CÔNG -> không được kèm ly_do_loi (đã tra được) — got {r9}")
print("PASS 9: tracuunnt.gdt.gov.vn thất bại -> tự động thử XInvoice dự phòng, XInvoice thành công thì "
      "kết quả cuối cùng KHÔNG kèm ly_do_loi.")

# ===== Test 9b (không hồi quy — gộp lý do lỗi CẢ 2 nguồn, không lặp): cả
# tracuunnt.gdt.gov.vn LẪN XInvoice đều thất bại -> ly_do_loi phải gộp ĐỦ lý
# do của CẢ 2 nguồn, mỗi nguồn xuất hiện ĐÚNG 1 lần (không lặp kiểu bug đã
# gặp trước đây: "escodata.net: escodata.net: ..."). =====
_reset()
_fake_tracuunnt.ket_qua = (False, "", None, "không giải được captcha (OCR không đọc ra)")
_fake_xinvoice.ket_qua_mac_dinh = (False, "", None, "Lỗi kết nối: timeout", False)
r9b = _tra_cuu_trang_thai_mst("0315696201", timeout=1)
assert r9b["canh_bao"] is None
assert _fake_tracuunnt.calls == 1 and _fake_xinvoice.calls == 1
ly_do_9b = r9b.get("ly_do_loi") or ""
assert ly_do_9b.count("tracuunnt.gdt.gov.vn:") == 1 and ly_do_9b.count("XInvoice:") == 1, (
    f"Phải gộp lý do của CẢ 2 nguồn, mỗi nguồn ĐÚNG 1 lần (không lặp) — got {ly_do_9b!r}")
assert "không giải được captcha" in ly_do_9b and "Lỗi kết nối" in ly_do_9b, f"got {ly_do_9b!r}"
print("PASS 9b: cả 2 nguồn đều thất bại -> ly_do_loi gộp ĐỦ lý do của cả tracuunnt.gdt.gov.vn LẪN "
      "XInvoice, mỗi nguồn đúng 1 lần (không lặp).")

# ===== Test 9c (đúng yêu cầu người dùng — nhiều key XInvoice luân phiên):
# tracuunnt.gdt.gov.vn lỗi, key XInvoice ĐẦU TIÊN báo lỗi DO CHÍNH KEY đó
# (401/429 hết hạn mức riêng key) -> PHẢI tự động chuyển sang key KẾ TIẾP thử
# lại NGAY trong CÙNG lượt gọi này (không phải đợi lượt sau), và nếu key thứ
# 2 thành công thì kết quả cuối cùng KHÔNG kèm ly_do_loi. =====
_reset()
_danh_sach_keys_gia[:] = [{"client_id": "key1", "api_key": "sec1"},
                          {"client_id": "key2", "api_key": "sec2"}]
_fake_tracuunnt.ket_qua = (False, "", None, "lỗi kết nối")
_fake_xinvoice.ket_qua_theo_key = {
    "key1": (False, "", None, "HTTP 429: Exceeded free tier limit", True),
    "key2": (True, "NNT đang hoạt động", False, None, False),
}
r9c = _tra_cuu_trang_thai_mst("0315696202", timeout=1)
assert r9c["canh_bao"] is False and r9c["trang_thai"] == "NNT đang hoạt động", f"got {r9c}"
assert _fake_xinvoice.client_ids_da_goi == ["key1", "key2"], (
    f"Phải thử key1 trước, lỗi DO KEY -> chuyển ngay sang key2 trong CÙNG lượt gọi "
    f"— got {_fake_xinvoice.client_ids_da_goi}")
assert "ly_do_loi" not in r9c, f"key2 THÀNH CÔNG -> không được kèm ly_do_loi — got {r9c}"
print("PASS 9c: key XInvoice đầu tiên lỗi DO CHÍNH KEY đó -> tự động chuyển sang key kế tiếp thử lại "
      "NGAY trong cùng lượt gọi, đúng yêu cầu người dùng 'hết key này có thể chạy qua key khác'.")

# ===== Test 10 (bug THẬT đã sửa trước đây — KHÔNG còn cache dài hạn): gọi
# lại CÙNG 1 MST ngay sau đó vẫn PHẢI tra cứu THẬT SỰ lại (không có cache
# nào để trả thẳng kết quả cũ), đúng yêu cầu người dùng "không cần lưu cứ dò
# ở thời điểm hiện tại". =====
_reset()
_fake_tracuunnt.ket_qua = (True, "NNT ngừng hoạt động nhưng chưa hoàn thành thủ tục đóng mã số thuế", True, None)
r10a = _tra_cuu_trang_thai_mst("0313415034", timeout=1)
assert r10a["canh_bao"] is True
_fake_tracuunnt.ket_qua = (True, "NNT đang hoạt động", False, None)
r10b = _tra_cuu_trang_thai_mst("0313415034", timeout=1)
assert r10b["canh_bao"] is False, (
    f"KHÔNG được cache lại kết quả cũ — gọi lại PHẢI LUÔN tra cứu THẬT SỰ và lấy đúng tình trạng MỚI "
    f"NHẤT — got {r10b}")
assert _fake_tracuunnt.calls == 2, f"Phải gọi mạng lại THẬT SỰ cả 2 lần (không cache) — got {_fake_tracuunnt.calls}"
print("PASS 10: KHÔNG còn cache dài hạn — gọi lại CÙNG 1 MST luôn tra cứu THẬT SỰ, lấy đúng tình trạng "
      "mới nhất.")

# ===== Test 11 (an toàn/không hồi quy — QUAN TRỌNG): lỗi liên tiếp nhiều lần
# (vd captcha sai liên tục/mất mạng, cả tracuunnt lẫn XInvoice dự phòng đều
# lỗi) -> KHÔNG được crash, trả canh_bao=None, và bộ đếm lỗi liên tiếp phải
# hoạt động: sau 5 lỗi liên tiếp trong CÙNG 1 lượt xuất Excel, DỪNG gọi mạng
# cho các MST còn lại (tránh treo lâu). =====
_reset()
_fake_tracuunnt.ket_qua = (False, "", None, "lỗi kết nối: timeout")
_fake_xinvoice.ket_qua_mac_dinh = (False, "", None, "lỗi kết nối: timeout", False)
dem_loi = [0]
ket_qua_11 = []
for i in range(8):
    mst_gia = f"031569613{i % 10}0"
    ket_qua_11.append(_tra_cuu_trang_thai_mst(mst_gia, timeout=1, so_lan_that_bai_lien_tiep=dem_loi))
assert all(kq["canh_bao"] is None for kq in ket_qua_11), (
    "Lỗi liên tiếp KHÔNG được crash và KHÔNG được suy đoán canh_bao — phải luôn là None")
assert _fake_tracuunnt.calls == 5, (
    f"Sau ĐÚNG 5 lượt lỗi liên tiếp phải NGỪNG gọi mạng cho các MST còn lại trong lượt này (tránh treo "
    f"lâu) — got {_fake_tracuunnt.calls} lượt gọi thật (kỳ vọng đúng 5)")
assert all("lỗi kết nối" in (kq.get("ly_do_loi") or "").lower() for kq in ket_qua_11[:5]), (
    f"Mỗi lượt lỗi THẬT SỰ (5 lượt đầu) phải kèm ly_do_loi cụ thể — got {ket_qua_11[:5]}")
assert "5 lỗi liên tiếp" in (ket_qua_11[5].get("ly_do_loi") or ""), (
    f"3 lượt cuối (sau khi bộ đếm đạt ngưỡng) phải kèm ly_do_loi ghi rõ đã dừng do 5 lỗi liên tiếp, để "
    f"người dùng biết đúng nguyên nhân khi thấy MST còn trống — got {ket_qua_11[5]}")
print("PASS 11: lỗi liên tiếp (cả tracuunnt.gdt.gov.vn lẫn XInvoice dự phòng) không làm crash "
      "(canh_bao=None, an toàn), dừng hẳn việc gọi mạng sau 5 lỗi liên tiếp trong cùng 1 lượt xuất "
      "Excel, và mỗi lượt lỗi đều kèm ly_do_loi cụ thể để chẩn đoán.")

# ===== Test 12 (đúng ca thật người dùng báo "chạy lâu quá" với bảng kê
# nhiều trăm hóa đơn): chi_dung_cache=True (đã hết ngân sách thời gian dành
# cho việc tra MST trong lượt xuất Excel này) -> TUYỆT ĐỐI không gọi mạng
# thêm (cả tracuunnt lẫn XInvoice), để trống an toàn (canh_bao=None), kèm
# ly_do_loi ghi rõ nguyên nhân. =====
_reset()
r12 = _tra_cuu_trang_thai_mst("0316888888", timeout=1, chi_dung_cache=True)
assert r12["canh_bao"] is None
assert _fake_tracuunnt.calls == 0 and _fake_xinvoice.calls == 0, (
    f"chi_dung_cache=True (đã hết ngân sách thời gian) -> TUYỆT ĐỐI không được gọi mạng "
    f"— got tracuunnt={_fake_tracuunnt.calls}, xinvoice={_fake_xinvoice.calls}")
assert "ngân sách thời gian" in (r12.get("ly_do_loi") or ""), (
    f"PHẢI kèm ly_do_loi ghi rõ nguyên nhân 'hết ngân sách thời gian' — got {r12}")
print("PASS 12: hết ngân sách thời gian (chi_dung_cache=True) -> để trống, không gọi mạng thêm (không "
      "làm treo lâu cả lượt xuất Excel), kèm ly_do_loi ghi rõ nguyên nhân.")

# ===== Test 13 (không hồi quy — bộ đếm lỗi liên tiếp reset đúng khi thành
# công): sau vài lỗi (chưa tới ngưỡng 5), 1 lượt THÀNH CÔNG phải reset bộ
# đếm về 0 — không được cộng dồn lỗi từ những MST không liên quan trước đó
# khiến MST sau bị dừng oan dù nguồn đang hoạt động bình thường trở lại. =====
_reset()
dem_loi13 = [0]
_fake_tracuunnt.ket_qua = (False, "", None, "lỗi kết nối: timeout")
_fake_xinvoice.ket_qua_mac_dinh = (False, "", None, "lỗi kết nối: timeout", False)
_tra_cuu_trang_thai_mst("0317111111", timeout=1, so_lan_that_bai_lien_tiep=dem_loi13)
_tra_cuu_trang_thai_mst("0317222222", timeout=1, so_lan_that_bai_lien_tiep=dem_loi13)
assert dem_loi13[0] == 2
_fake_tracuunnt.ket_qua = (True, "NNT đang hoạt động", False, None)
r13 = _tra_cuu_trang_thai_mst("0317333333", timeout=1, so_lan_that_bai_lien_tiep=dem_loi13)
assert r13["canh_bao"] is False
assert dem_loi13[0] == 0, f"1 lượt THÀNH CÔNG phải reset bộ đếm lỗi liên tiếp về 0 — got {dem_loi13[0]}"
print("PASS 13: bộ đếm lỗi liên tiếp reset về 0 khi có 1 lượt tra THÀNH CÔNG, không cộng dồn oan cho "
      "các MST sau khi nguồn đã hoạt động bình thường trở lại.")

# ===== Test 14 (không hồi quy — chưa cấu hình key XInvoice nào): danh sách
# key rỗng (so_key=0) -> vòng lặp XInvoice KHÔNG được chạy lần nào (tránh
# IndexError/ZeroDivisionError khi chia % 0), chỉ dựa vào tracuunnt.gdt.gov.vn. =====
_reset()
_danh_sach_keys_gia[:] = []
_fake_tracuunnt.ket_qua = (False, "", None, "lỗi kết nối: timeout")
r14 = _tra_cuu_trang_thai_mst("0318444444", timeout=1)
assert r14["canh_bao"] is None
assert _fake_xinvoice.calls == 0, (
    f"Chưa cấu hình key XInvoice nào -> KHÔNG được gọi (tránh lỗi chia cho 0) — got {_fake_xinvoice.calls}")
assert "tracuunnt.gdt.gov.vn:" in (r14.get("ly_do_loi") or ""), f"got {r14}"
print("PASS 14: chưa cấu hình key XInvoice nào -> không gọi XInvoice, không crash, chỉ dựa vào "
      "tracuunnt.gdt.gov.vn.")

# ===== Test 15 (QUAN TRỌNG — đúng yêu cầu người dùng: "hãy tạm dừng
# xinvoice.vn chỉ dùng tracuunnt.gdt.gov.vn để tra cứu" sau khi log thật cho
# thấy CẢ 2 key XInvoice đều HTTP 429 "Exceeded free tier limit"/timeout):
# khi cờ _XINVOICE_TAM_DUNG=True (giá trị THẬT đang cấu hình trong
# server.py, KHÁC các Test 8-14 ở trên chủ động mở cờ này ra để test riêng
# logic dự phòng), _tra_cuu_trang_thai_mst() PHẢI KHÔNG gọi XInvoice dù
# tracuunnt.gdt.gov.vn thất bại — kể cả khi ĐÃ cấu hình sẵn key. =====
_reset()
ns['_XINVOICE_TAM_DUNG'] = True
_fake_tracuunnt.ket_qua = (False, "", None, "không giải được captcha (OCR không đọc ra)")
r15 = _tra_cuu_trang_thai_mst("0319555555", timeout=1)
assert r15["canh_bao"] is None
assert _fake_tracuunnt.calls == 1, f"vẫn phải gọi tracuunnt.gdt.gov.vn — got {_fake_tracuunnt.calls}"
assert _fake_xinvoice.calls == 0, (
    f"_XINVOICE_TAM_DUNG=True -> TUYỆT ĐỐI không được gọi XInvoice dù tracuunnt.gdt.gov.vn thất bại và "
    f"ĐÃ có cấu hình key — got {_fake_xinvoice.calls} lượt gọi")
assert r15.get("ly_do_loi") == "tracuunnt.gdt.gov.vn: không giải được captcha (OCR không đọc ra)", (
    f"ly_do_loi chỉ được nhắc tới tracuunnt.gdt.gov.vn (XInvoice đang tạm dừng, không tham gia) "
    f"— got {r15.get('ly_do_loi')!r}")
ns['_XINVOICE_TAM_DUNG'] = False   # trả lại mặc định cho các test khác nếu file được import lại
print("PASS 15: XInvoice đang TẠM DỪNG (_XINVOICE_TAM_DUNG=True, giá trị THẬT trong server.py) -> "
      "KHÔNG gọi XInvoice dù tracuunnt.gdt.gov.vn thất bại và đã có cấu hình key — chỉ dựa vào "
      "tracuunnt.gdt.gov.vn, đúng yêu cầu người dùng sau khi cả 2 key XInvoice đều hết hạn mức gói.")

print("\nALL DONE")
