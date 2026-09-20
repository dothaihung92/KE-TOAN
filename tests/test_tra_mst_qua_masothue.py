import os
import re

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test — masothue.com đã từng bị BỎ trước đó (người dùng báo
# "không đúng được": server chủ động hủy session/chặn khi phát hiện request
# tìm kiếm tự động dồn dập), nhưng người dùng tự kiểm tra lại link thật
# (https://masothue.com/Search/?q=0316956049&type=auto) xác nhận "chạy
# được" nên yêu cầu thêm lại làm nguồn DỰ PHÒNG thứ 2 (sau api.vietqr.io,
# trước XInvoice — thay cho vị trí của escodata.net vừa bị bỏ theo yêu cầu
# "hãy bỏ escodata.net đi").
#
# Khác api.vietqr.io/escodata.net (API JSON có cấu trúc), masothue.com trả
# về HTML — dò tình trạng bằng CÙNG hàm _phan_loai_trang_thai_mst() quét từ
# khoá trên TOÀN BỘ nội dung trang (không phụ thuộc cấu trúc HTML/CSS cụ
# thể, bền hơn khi trang đổi giao diện).


def _than_ham(ten):
    i = src.index('def ' + ten + '(')
    j = src.index('\ndef ', i + 10)
    return src[i:j]


class _FakeTime:
    """Thay cho module time thật — ghi lại các lượt sleep() thay vì chờ
    thật, để test chạy nhanh dù _tra_cuu_mst_qua_masothue giờ nghỉ theo
    Retry-After khi gặp 429 tạm thời trước khi thử lại."""
    def __init__(self):
        self.sleeps = []

    def sleep(self, s):
        self.sleeps.append(s)


def _nap(*ten_ham):
    ns = {'threading': __import__('threading'), 'requests': None}
    exec('import unicodedata, re, json', ns)
    for t in ten_ham:
        exec(_than_ham(t), ns)
    m = re.search(r'^_MASOTHUE_STATE\s*=\s*\{.*\}', src, re.M)
    exec(m.group(0), ns)
    m2 = re.search(r'^_MASOTHUE_NGUONG_TAT\s*=\s*\d+', src, re.M)
    exec(m2.group(0), ns)
    ns['_fake_time'] = _FakeTime()
    ns['time'] = ns['_fake_time']
    return ns


class _FakeResp:
    def __init__(self, status_code, text="", headers=None):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}


class _FakeRequests:
    """khớp chữ ký .get(url, params=None, headers=None, timeout=None) mà
    _tra_cuu_mst_qua_masothue() thật sự dùng (GET .../Search/ kèm params
    q/type, không phải URL path như api.vietqr.io/escodata.net)."""
    def __init__(self, fn):
        self._fn = fn

    def get(self, url, params=None, headers=None, timeout=None):
        return self._fn(url, params, timeout)


class _FakeRequestsQueue:
    """Trả về LẦN LƯỢT các response trong hàng đợi theo từng lượt gọi — dùng
    để mô phỏng 429 rồi 200 ở lượt thử lại."""
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append(url)
        return self.responses.pop(0)


# ===== Test 1 (đúng ca thật): phải quét đúng nội dung trang (r.text) qua
# _phan_loai_trang_thai_mst(), phân loại đúng "đang hoạt động" là KHÔNG
# cảnh báo. =====
ns = _nap('_khong_dau', '_phan_loai_trang_thai_mst', '_masothue_danh_dau', '_tra_cuu_mst_qua_masothue')
fn = ns['_tra_cuu_mst_qua_masothue']

HTML_DANG_HOAT_DONG = """<html><body>
<h1>CÔNG TY TNHH MARINE DIGITALE</h1>
<table><tr><td>Mã số thuế</td><td>0316956049</td></tr>
<tr><td>Tình trạng</td><td>Người nộp thuế đang hoạt động (đã cấp GCN ĐKT)</td></tr></table>
</body></html>"""

ns['requests'] = _FakeRequests(lambda url, params, timeout: (
    _FakeResp(200, HTML_DANG_HOAT_DONG) if url == "https://masothue.com/Search/" and params == {"q": "0316956049", "type": "auto"}
    else (_ for _ in ()).throw(AssertionError(f"URL/params sai: {url} {params}"))
))
r1 = fn("0316956049", 20)
assert r1[0] is True and r1[2] is False, f"Phải quét đúng trang, dò ra 'đang hoạt động', canh_bao=False — got {r1}"
print("PASS 1: quét đúng nội dung trang HTML thật, dò ra 'đang hoạt động' và phân loại KHÔNG cảnh báo.")

# ===== Test 2 (đúng ca thật — MST bị cảnh báo): trang có tình trạng xấu thì
# phải cảnh báo (tô đỏ), không suy đoán "bình thường". =====
HTML_DA_KHOA = HTML_DANG_HOAT_DONG.replace(
    "Người nộp thuế đang hoạt động (đã cấp GCN ĐKT)", "Người nộp thuế đã bị khóa mã số thuế")
ns['requests'] = _FakeRequests(lambda url, params, timeout: _FakeResp(200, HTML_DA_KHOA))
r2 = fn("0316956049", 20)
assert r2[0] is True and r2[2] is True, f"MST đã khoá phải ra canh_bao=True, got {r2}"
print("PASS 2: MST có tình trạng xấu (đã khoá MST) được nhận diện đúng là CẢNH BÁO.")

# ===== Test 3 (AN TOÀN — không suy đoán): HTTP lỗi, trang không có tình
# trạng khớp nào (bị chặn/không có dữ liệu MST), hoặc lỗi kết nối -> đều
# phải trả THẤT BẠI (để rơi xuống nguồn sau), tuyệt đối không suy đoán "đang
# hoạt động". =====
ns['requests'] = _FakeRequests(lambda url, params, timeout: _FakeResp(404))
assert fn("0000000000", 20)[0] is False, "HTTP khác 200 phải trả thất bại."

ns['requests'] = _FakeRequests(lambda url, params, timeout: _FakeResp(200, "<html>Không tìm thấy kết quả</html>"))
r_la = fn("0000000000", 20)
assert r_la[0] is False and r_la[2] is None, (
    f"Trang không có tình trạng khớp nào (vd bị chặn/không có dữ liệu) phải trả thất bại, canh_bao=None "
    f"(không suy đoán) — got {r_la}")

def _nem_loi(url, params, timeout):
    raise ConnectionError("mất mạng")
ns['requests'] = _FakeRequests(_nem_loi)
assert fn("0000000000", 20)[0] is False, "Lỗi kết nối phải trả thất bại, không văng exception ra ngoài."
print("PASS 3: mọi trường hợp lỗi/dữ liệu bất thường đều trả thất bại an toàn, không suy đoán 'đang hoạt động'.")

# ===== Test 3b (không hồi quy — cùng lỗi trùng lặp tiền tố đã phát hiện ở
# escodata.net/VietQR "escodata.net: escodata.net: ..."): ly_do_loi do
# _tra_cuu_mst_qua_masothue() TỰ trả về KHÔNG được tự ý kèm sẵn tiền tố
# "masothue.com: " — vì _tra_cuu_trang_thai_mst() (nơi gộp lỗi cuối cùng của
# cả 3 nguồn) ĐÃ tự thêm tiền tố "masothue.com: " rồi, kèm sẵn nữa sẽ bị LẶP
# tiền tố 2 LẦN. =====
ns3b = _nap('_khong_dau', '_phan_loai_trang_thai_mst', '_masothue_danh_dau', '_tra_cuu_mst_qua_masothue')
fn3b = ns3b['_tra_cuu_mst_qua_masothue']
ns3b['requests'] = _FakeRequests(lambda url, params, timeout: _FakeResp(404))
r3b = fn3b("0000000000", 20)
assert r3b[0] is False
assert not (r3b[3] or "").lower().startswith("masothue.com"), (
    f"ly_do_loi KHÔNG được tự kèm sẵn tiền tố 'masothue.com: ' (nơi gộp lỗi cuối cùng ở "
    f"_tra_cuu_trang_thai_mst() đã tự thêm rồi, kèm sẵn nữa sẽ bị lặp 2 lần "
    f"'masothue.com: masothue.com: ...') — got {r3b[3]!r}")
print("PASS 3b: ly_do_loi trả về KHÔNG tự kèm sẵn tiền tố 'masothue.com: ' — tránh lặp tiền tố 2 lần "
      "khi _tra_cuu_trang_thai_mst() gộp lỗi cuối cùng của cả 3 nguồn.")

# ===== Test 4 (đúng ca thật — tránh lãng phí lượt gọi hàng loạt, đúng bài
# học cũ đã gặp: masothue.com từng bị chặn khi gọi dồn dập): phải có ngưỡng
# tạm tắt khi lỗi liên tiếp, giống cơ chế đã áp dụng cho VietQR. =====
than_masothue = _than_ham('_tra_cuu_mst_qua_masothue')
assert '_MASOTHUE_NGUONG_TAT' in src and '_masothue_danh_dau(' in than_masothue, (
    "Phải có bộ đếm lỗi liên tiếp + ngưỡng tạm tắt nguồn này trong 1 lượt xuất Excel — quan trọng vì "
    "masothue.com từng bị chặn khi gọi dồn dập trước đây.")
print("PASS 4: có ngưỡng tạm tắt khi lỗi liên tiếp, tránh lãng phí lượt gọi cho hàng trăm MST còn lại "
      "(và tự bảo vệ nếu masothue.com lại chặn dồn dập như trước).")

# ===== Test 4b (không hồi quy — đề phòng nếu bị giới hạn tốc độ thoáng
# qua): 429 phải được THỬ LẠI đúng 1 lần (theo Retry-After, mặc định 2
# giây) trước khi chịu thua hẳn, giống các nguồn khác. =====
ns4b = _nap('_khong_dau', '_phan_loai_trang_thai_mst', '_masothue_danh_dau', '_tra_cuu_mst_qua_masothue')
fn4b = ns4b['_tra_cuu_mst_qua_masothue']
freq = _FakeRequestsQueue([
    _FakeResp(429, headers={"Retry-After": "3"}),
    _FakeResp(200, HTML_DANG_HOAT_DONG),
])
ns4b['requests'] = freq
r4b = fn4b("0316956049", 20)
assert r4b[0] is True and r4b[2] is False, (
    f"429 tạm thời PHẢI được thử lại đúng 1 lần rồi lấy được kết quả thật, không được bỏ cuộc ngay "
    f"— got {r4b}")
assert len(freq.calls) == 2, f"Phải gọi ĐÚNG 2 lượt (429 rồi thử lại thành công) — got {len(freq.calls)}"
assert ns4b['_fake_time'].sleeps == [3], (
    f"Phải nghỉ đúng theo Retry-After (3s) trước khi thử lại — got {ns4b['_fake_time'].sleeps}")
print("PASS 4b: gặp 429 (giới hạn tốc độ tạm thời) -> nghỉ đúng theo Retry-After rồi thử lại thành "
      "công, không bỏ cuộc ngay.")

# ===== Test 5 (QUAN TRỌNG — đúng yêu cầu thứ tự ưu tiên): masothue.com phải
# được thử SAU api.vietqr.io (chỉ khi VietQR đã thất bại) nhưng TRƯỚC
# XInvoice (dự phòng cuối, cần key/có thể hết hạn mức gói free tier). =====
than_chinh = _than_ham('_tra_cuu_trang_thai_mst')
vt_vietqr = than_chinh.find('_tra_cuu_mst_qua_vietqr(')
vt_masothue = than_chinh.find('_tra_cuu_mst_qua_masothue(')
vt_xinvoice = than_chinh.find('_goi_1_lan_xinvoice(')
assert 0 < vt_vietqr < vt_masothue < vt_xinvoice, (
    "Thứ tự ưu tiên phải là: api.vietqr.io -> masothue.com -> XInvoice (dự phòng cuối).")
assert 'if not thanh_cong:' in than_chinh[vt_masothue - 100:vt_masothue], (
    "Chỉ thử masothue.com khi VietQR đã THẤT BẠI (thanh_cong=False) — tra được ở VietQR rồi thì không "
    "cần thử thêm nguồn khác, tránh lãng phí gọi mạng vô ích.")
print("PASS 5: masothue.com được thử SAU api.vietqr.io nhưng TRƯỚC XInvoice, chỉ rơi xuống khi VietQR "
      "đã thất bại.")

# ===== Test 6 (không hồi quy — thông báo lỗi cuối gộp đủ cả 3 nguồn): thiếu
# lý do của 1 nguồn sẽ khiến người dùng chẩn đoán "cụt", không biết nguồn đó
# có được thử hay không. =====
assert 'masothue.com: {ly_do_loi_masothue}' in src, (
    "Thông báo lỗi cuối cùng (khi cả 3 nguồn đều thất bại) phải kèm lý do của masothue.com.")
print("PASS 6: thông báo lỗi cuối cùng gộp đủ lý do của cả 3 nguồn (VietQR + masothue.com + XInvoice).")

# ===== Test 7 (không hồi quy — endpoint chẩn đoán riêng): phải có endpoint
# chẩn đoán nhanh cho masothue.com, không cần biết id công ty nào (trang
# công khai). =====
assert '/api/chan-doan-mst-masothue' in src and 'def chan_doan_mst_masothue' in src, (
    "Phải có endpoint chẩn đoán riêng cho masothue.com.")
than_cd = _than_ham('chan_doan_mst_masothue')
assert '_tra_cuu_mst_qua_masothue(' in than_cd, "Endpoint chẩn đoán phải gọi đúng hàm tra cứu thật (không phải mô phỏng riêng)."
print("PASS 7: có endpoint chẩn đoán riêng /api/chan-doan-mst-masothue, không cần biết id công ty nào.")

print("\nALL DONE")
