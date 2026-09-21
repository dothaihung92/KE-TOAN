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
# QUAN TRỌNG (đổi ý nghĩa lớn — ĐANG Ở CHẾ ĐỘ KIỂM TRA RIÊNG
# tracuunnt.gdt.gov.vn, tạm thời): trải qua nhiều vòng chỉnh sửa nguồn tra
# MST (XInvoice -> +masothue.com -> +tracuunnt.gdt.gov.vn -> bỏ 2 nguồn đó
# -> +api.vietqr.io -> +escodata.net -> đổi escodata.net thành masothue.com
# ...), người dùng yêu cầu: "hãy tạm ngưng dùng
# VietQR/masothue.com/XInvoice mà tập trung xử lý test chạy kiểm tra qua
# tracuunnt.gdt.gov.vn" — nên _tra_cuu_trang_thai_mst() giờ CHỈ gọi
# _tra_cuu_mst_qua_tracuunnt(), KHÔNG còn gọi VietQR/masothue.com/XInvoice
# (dù 3 hàm đó vẫn còn nguyên trong server.py, sẵn sàng khôi phục). File
# test này CHỈ kiểm tra phần orchestration CHUNG (validate MST, circuit
# breaker, ngân sách thời gian, gộp tiền tố lỗi) qua 1 stub đơn giản cho
# _tra_cuu_mst_qua_tracuunnt — hành vi THẬT của hàm đó (session/captcha/HTML)
# có test riêng ở test_tra_mst_qua_tracuunnt.py. Cũng KHÔNG còn cache dài hạn
# (bảng mst_status_cache) — LUÔN tra cứu thật sự qua mạng mỗi lần gọi (trừ
# dedup trong bộ nhớ CHỈ trong CÙNG 1 lượt xuất Excel — xem _mst_status_local
# ở export_excel, không có trong phạm vi test file này).


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
exec(extract_fn('_tra_cuu_trang_thai_mst'), ns)
_phan_loai_trang_thai_mst = ns['_phan_loai_trang_thai_mst']
_tra_cuu_trang_thai_mst = ns['_tra_cuu_trang_thai_mst']

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
_fake_tracuunnt.calls = 0
r7a = _tra_cuu_trang_thai_mst("", timeout=1)
r7b = _tra_cuu_trang_thai_mst("KL", timeout=1)
r7c = _tra_cuu_trang_thai_mst("123", timeout=1)
assert r7a["canh_bao"] is None and r7b["canh_bao"] is None and r7c["canh_bao"] is None
assert _fake_tracuunnt.calls == 0, (
    f"MST rỗng/'KL'/quá ngắn KHÔNG được gọi mạng (tránh tra cứu vô nghĩa cho khách lẻ dùng chung mã) "
    f"— got {_fake_tracuunnt.calls} lượt gọi")
assert "ly_do_loi" not in r7a and "ly_do_loi" not in r7b, (
    f"MST rỗng/'KL' là CHỦ Ý bỏ qua (khách lẻ dùng chung mã), KHÔNG phải lỗi -> không kèm ly_do_loi "
    f"— got r7a={r7a}, r7b={r7b}")
assert "không hợp lệ" in (r7c.get("ly_do_loi") or ""), (
    f"MST '123' (không đủ 9-10 chữ số) -> PHẢI kèm ly_do_loi ghi rõ 'không hợp lệ' — got {r7c}")
print("PASS 7: MST rỗng/'KL' (khách lẻ dùng chung mã) -> bỏ qua hẳn, không gọi mạng, không kèm "
      "ly_do_loi (chủ ý, không phải lỗi); MST quá ngắn/sai định dạng -> vẫn bỏ qua nhưng kèm ly_do_loi "
      "rõ ràng để chẩn đoán.")

# ===== Test 8 (đúng ca thật — MST hợp lệ, tracuunnt.gdt.gov.vn thành công):
# phải gọi ĐÚNG 1 lần, lấy đúng trang_thai/canh_bao từ kết quả trả về. =====
_fake_tracuunnt.calls = 0
_fake_tracuunnt.ket_qua = (True, "NNT đang hoạt động", False, None)
r8 = _tra_cuu_trang_thai_mst("0315696199", timeout=1)
assert r8["canh_bao"] is False and r8["trang_thai"] == "NNT đang hoạt động", f"got {r8}"
assert _fake_tracuunnt.calls == 1, f"Phải gọi tracuunnt.gdt.gov.vn đúng 1 lần — got {_fake_tracuunnt.calls}"
assert "ly_do_loi" not in r8, f"Tra thành công thì không được kèm ly_do_loi — got {r8}"
print("PASS 8: MST hợp lệ, tracuunnt.gdt.gov.vn thành công -> gọi đúng 1 lần, lấy đúng tình trạng.")

# ===== Test 9 (không hồi quy — gộp tiền tố nguồn ĐÚNG 1 LẦN, không lặp):
# tracuunnt.gdt.gov.vn thất bại -> canh_bao=None, ly_do_loi phải được gắn
# tiền tố "tracuunnt.gdt.gov.vn: " đúng 1 LẦN (không lặp 2 lần kiểu bug đã
# gặp ở escodata.net/VietQR trước đây: "escodata.net: escodata.net: ..."). =====
_fake_tracuunnt.calls = 0
_fake_tracuunnt.ket_qua = (False, "", None, "không giải được captcha (OCR không đọc ra)")
r9 = _tra_cuu_trang_thai_mst("0315696200", timeout=1)
assert r9["canh_bao"] is None
assert _fake_tracuunnt.calls == 1
assert r9.get("ly_do_loi") == "tracuunnt.gdt.gov.vn: không giải được captcha (OCR không đọc ra)", (
    f"Phải gắn tiền tố 'tracuunnt.gdt.gov.vn: ' đúng 1 lần — got {r9.get('ly_do_loi')!r}")
print("PASS 9: tracuunnt.gdt.gov.vn thất bại -> canh_bao=None an toàn, ly_do_loi gắn tiền tố nguồn "
      "ĐÚNG 1 lần (không lặp 2 lần).")

# ===== Test 10 (bug THẬT đã sửa trước đây — KHÔNG còn cache dài hạn): gọi
# lại CÙNG 1 MST ngay sau đó vẫn PHẢI tra cứu THẬT SỰ lại (không có cache
# nào để trả thẳng kết quả cũ), đúng yêu cầu người dùng "không cần lưu cứ dò
# ở thời điểm hiện tại". =====
_fake_tracuunnt.calls = 0
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
# (vd captcha sai liên tục/mất mạng) -> KHÔNG được crash, trả canh_bao=None,
# và bộ đếm lỗi liên tiếp phải hoạt động: sau 5 lỗi liên tiếp trong CÙNG 1
# lượt xuất Excel, DỪNG gọi mạng cho các MST còn lại (tránh treo lâu). =====
_fake_tracuunnt.calls = 0
_fake_tracuunnt.ket_qua = (False, "", None, "lỗi kết nối: timeout")
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
print("PASS 11: lỗi liên tiếp không làm crash (canh_bao=None, an toàn), dừng hẳn việc gọi mạng sau 5 "
      "lỗi liên tiếp trong cùng 1 lượt xuất Excel, và mỗi lượt lỗi đều kèm ly_do_loi cụ thể để chẩn đoán.")

# ===== Test 12 (đúng ca thật người dùng báo "chạy lâu quá" với bảng kê
# nhiều trăm hóa đơn): chi_dung_cache=True (đã hết ngân sách thời gian dành
# cho việc tra MST trong lượt xuất Excel này) -> TUYỆT ĐỐI không gọi mạng
# thêm, để trống an toàn (canh_bao=None), kèm ly_do_loi ghi rõ nguyên nhân. =====
_fake_tracuunnt.calls = 0
_fake_tracuunnt.ket_qua = (True, "NNT đang hoạt động", False, None)
r12 = _tra_cuu_trang_thai_mst("0316888888", timeout=1, chi_dung_cache=True)
assert r12["canh_bao"] is None
assert _fake_tracuunnt.calls == 0, (
    f"chi_dung_cache=True (đã hết ngân sách thời gian) -> TUYỆT ĐỐI không được gọi mạng "
    f"— got {_fake_tracuunnt.calls} lượt gọi")
assert "ngân sách thời gian" in (r12.get("ly_do_loi") or ""), (
    f"PHẢI kèm ly_do_loi ghi rõ nguyên nhân 'hết ngân sách thời gian' — got {r12}")
print("PASS 12: hết ngân sách thời gian (chi_dung_cache=True) -> để trống, không gọi mạng thêm (không "
      "làm treo lâu cả lượt xuất Excel), kèm ly_do_loi ghi rõ nguyên nhân.")

# ===== Test 13 (không hồi quy — bộ đếm lỗi liên tiếp reset đúng khi thành
# công): sau vài lỗi (chưa tới ngưỡng 5), 1 lượt THÀNH CÔNG phải reset bộ
# đếm về 0 — không được cộng dồn lỗi từ những MST không liên quan trước đó
# khiến MST sau bị dừng oan dù nguồn đang hoạt động bình thường trở lại. =====
_fake_tracuunnt.calls = 0
dem_loi13 = [0]
_fake_tracuunnt.ket_qua = (False, "", None, "lỗi kết nối: timeout")
_tra_cuu_trang_thai_mst("0317111111", timeout=1, so_lan_that_bai_lien_tiep=dem_loi13)
_tra_cuu_trang_thai_mst("0317222222", timeout=1, so_lan_that_bai_lien_tiep=dem_loi13)
assert dem_loi13[0] == 2
_fake_tracuunnt.ket_qua = (True, "NNT đang hoạt động", False, None)
r13 = _tra_cuu_trang_thai_mst("0317333333", timeout=1, so_lan_that_bai_lien_tiep=dem_loi13)
assert r13["canh_bao"] is False
assert dem_loi13[0] == 0, f"1 lượt THÀNH CÔNG phải reset bộ đếm lỗi liên tiếp về 0 — got {dem_loi13[0]}"
print("PASS 13: bộ đếm lỗi liên tiếp reset về 0 khi có 1 lượt tra THÀNH CÔNG, không cộng dồn oan cho "
      "các MST sau khi nguồn đã hoạt động bình thường trở lại.")

print("\nALL DONE")
