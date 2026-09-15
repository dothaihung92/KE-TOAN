import os
import re
import sqlite3
import tempfile
import datetime

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test cho tính năng MỚI "dò tình trạng hoạt động MST khi xuất Excel"
# (_phan_loai_trang_thai_mst / _tra_cuu_trang_thai_mst trong server.py) — người dùng
# yêu cầu: "hãy thêm chức năng dò mst còn đang hoạt động hay không hoặc công ty cần
# xác minh địa chỉ kinh doanh khi kết xuất ra excel thêm 1 cột trạng thái mst ở
# cuối công ty nào bị khoá mst hoặc báo chờ xác minh tình trạng hoạt động tại địa
# chỉ thì trong file excel tô đỏ dòng đó" — nguồn tra cứu do người dùng chỉ định:
# "https://masothue.com/ hãy dùng trang này để tự động dò mst".


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


class _FakeResp:
    def __init__(self, text):
        self.text = text


class _FakeRequests:
    """Thay cho module requests thật — kiểm soát được nội dung trả về/lỗi mạng
    để test KHÔNG cần gọi mạng thật (không thể test trực tiếp masothue.com từ
    môi trường sandbox hiện tại — bị chặn egress proxy)."""
    def __init__(self):
        self.calls = []
        self.next_text = None
        self.next_exc = None

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append({"url": url, "params": dict(params or {})})
        if self.next_exc is not None:
            raise self.next_exc
        return _FakeResp(self.next_text or "")


ns = {'datetime': datetime}
exec(extract_fn('_khong_dau'), ns)
exec(extract_fn('_chuan_mst'), ns)
exec(extract_fn('_phan_loai_trang_thai_mst'), ns)
m = re.search(r'^_MST_CACHE_NGAY\s*=\s*\d+', src, re.M)
exec(m.group(0), ns)

_fake_requests = _FakeRequests()
ns['requests'] = _fake_requests

_tmp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
_tmp_db.close()


def _fresh_db():
    conn = sqlite3.connect(_tmp_db.name, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS mst_status_cache (
        mst TEXT PRIMARY KEY, trang_thai_goc TEXT, canh_bao INTEGER, checked_at TEXT
    )""")
    return conn


ns['db'] = _fresh_db
exec(extract_fn('_tra_cuu_trang_thai_mst'), ns)
_phan_loai_trang_thai_mst = ns['_phan_loai_trang_thai_mst']
_tra_cuu_trang_thai_mst = ns['_tra_cuu_trang_thai_mst']

_conn0 = _fresh_db()
_conn0.execute("DELETE FROM mst_status_cache")
_conn0.commit()
_conn0.close()

# ===== Test 1-6: _phan_loai_trang_thai_mst() — phân loại theo nội dung trang, các
# ca thường gặp trên masothue.com (mô phỏng đoạn HTML chứa đúng cụm mô tả chính
# thức của Tổng cục Thuế). =====
_, cb = _phan_loai_trang_thai_mst("<div>Tình trạng: Người nộp thuế đang hoạt động (đã cấp GCN ĐKT)</div>")
assert cb is False, f"'đang hoạt động' PHẢI được coi là bình thường (canh_bao=False) — got {cb}"
print("PASS 1: 'đang hoạt động' -> canh_bao=False (bình thường, không tô đỏ).")

nhan, cb = _phan_loai_trang_thai_mst(
    "<span>NNT đang trong quá trình chờ xác minh tình trạng hoạt động tại địa chỉ đã đăng ký</span>")
assert cb is True, f"'chờ xác minh tình trạng hoạt động tại địa chỉ' PHẢI cảnh báo (canh_bao=True) — got {cb}"
assert "xác minh" in nhan.lower()
print("PASS 2: 'chờ xác minh tình trạng hoạt động tại địa chỉ' -> canh_bao=True (đúng yêu cầu người dùng).")

_, cb = _phan_loai_trang_thai_mst("<td>Người nộp thuế đã bị khóa mã số thuế</td>")
assert cb is True, f"'đã bị khóa mã số thuế' PHẢI cảnh báo — got {cb}"
print("PASS 3: 'đã bị khóa mã số thuế' -> canh_bao=True.")

_, cb = _phan_loai_trang_thai_mst("<td>NNT ngừng hoạt động nhưng chưa hoàn thành thủ tục đóng mã số thuế</td>")
assert cb is True, f"'ngừng hoạt động' PHẢI cảnh báo — got {cb}"
print("PASS 4: 'ngừng hoạt động nhưng chưa hoàn thành thủ tục đóng MST' -> canh_bao=True.")

_, cb = _phan_loai_trang_thai_mst("<td>Không hoạt động tại địa chỉ đã đăng ký</td>")
assert cb is True, f"'không hoạt động tại địa chỉ đã đăng ký' PHẢI cảnh báo — got {cb}"
print("PASS 5: 'không hoạt động tại địa chỉ đã đăng ký' -> canh_bao=True.")

_, cb = _phan_loai_trang_thai_mst("<html><body>Không tìm thấy kết quả nào phù hợp</body></html>")
assert cb is None, f"Trang KHÔNG có dữ liệu tình trạng -> canh_bao=None (KHÔNG suy đoán/không tô đỏ) — got {cb}"
print("PASS 6: trang không có dữ liệu (không tìm thấy MST) -> canh_bao=None, không suy đoán bừa.")

# ===== Test 7-11: _tra_cuu_trang_thai_mst() — luồng cache + gọi mạng (mock). =====

# Test 7: MST rỗng/"KL" (khách lẻ)/quá ngắn -> KHÔNG gọi mạng, trả canh_bao=None.
_fake_requests.calls.clear()
r7a = _tra_cuu_trang_thai_mst("", timeout=1)
r7b = _tra_cuu_trang_thai_mst("KL", timeout=1)
r7c = _tra_cuu_trang_thai_mst("123", timeout=1)
assert r7a["canh_bao"] is None and r7b["canh_bao"] is None and r7c["canh_bao"] is None
assert len(_fake_requests.calls) == 0, (
    f"MST rỗng/'KL'/quá ngắn KHÔNG được gọi mạng (tránh tra cứu vô nghĩa cho khách lẻ dùng chung mã) "
    f"— got {len(_fake_requests.calls)} lượt gọi")
print("PASS 7: MST rỗng/'KL' (khách lẻ dùng chung mã)/quá ngắn -> bỏ qua hẳn, không gọi mạng.")

# Test 8: cache MISS -> gọi mạng đúng 1 lần, phân loại đúng, LƯU vào cache.
_fake_requests.calls.clear()
_fake_requests.next_text = "<div>Người nộp thuế đã bị khóa mã số thuế</div>"
r8 = _tra_cuu_trang_thai_mst("0315696133", timeout=1)
assert r8["canh_bao"] is True, f"Phải phân loại đúng từ nội dung trả về — got {r8}"
assert len(_fake_requests.calls) == 1, f"Cache MISS phải gọi mạng đúng 1 lần — got {len(_fake_requests.calls)}"
assert _fake_requests.calls[0]["params"].get("q") == "0315696133"
print("PASS 8: cache MISS -> gọi mạng đúng 1 lần, phân loại đúng từ nội dung trang.")

# Test 9: cache HIT (vừa tra ở Test 8) -> KHÔNG gọi mạng lại, trả đúng kết quả đã lưu.
_fake_requests.calls.clear()
r9 = _tra_cuu_trang_thai_mst("0315696133", timeout=1)
assert r9["canh_bao"] is True
assert len(_fake_requests.calls) == 0, (
    f"MST đã tra cứu gần đây (còn trong hạn cache _MST_CACHE_NGAY ngày) KHÔNG được gọi mạng lại "
    f"— got {len(_fake_requests.calls)} lượt gọi")
print("PASS 9: cache HIT (MST vừa tra) -> không gọi mạng lại, dùng lại kết quả đã lưu (giảm tải "
      "masothue.com).")

# Test 10: cache đã QUÁ HẠN (checked_at cũ hơn _MST_CACHE_NGAY ngày) -> tra lại THẬT SỰ.
conn10 = _fresh_db()
qua_han = (datetime.datetime.now() - datetime.timedelta(days=ns['_MST_CACHE_NGAY'] + 1)).isoformat()
conn10.execute("UPDATE mst_status_cache SET checked_at=? WHERE mst=?", (qua_han, "0315696133"))
conn10.commit()
conn10.close()
_fake_requests.calls.clear()
_fake_requests.next_text = "<div>Người nộp thuế đang hoạt động (đã cấp GCN ĐKT)</div>"
r10 = _tra_cuu_trang_thai_mst("0315696133", timeout=1)
assert r10["canh_bao"] is False, f"Sau khi tra lại, tình trạng đã đổi thành 'đang hoạt động' — got {r10}"
assert len(_fake_requests.calls) == 1, "Cache quá hạn PHẢI tra lại thật sự (gọi mạng lại)"
print("PASS 10: cache đã quá hạn (_MST_CACHE_NGAY ngày) -> tự động tra lại thật sự, cập nhật kết quả "
      "mới.")

# Test 11 (an toàn/không hồi quy — QUAN TRỌNG): lỗi mạng (mất kết nối/timeout) -> KHÔNG
# được crash, trả canh_bao=None (không suy đoán khi không tra cứu được), và bộ đếm lỗi
# liên tiếp phải hoạt động: sau nhiều lỗi liên tiếp trong CÙNG 1 lượt xuất Excel, DỪNG
# gọi mạng cho các MST còn lại (tránh treo lâu vì hàng loạt MST timeout liên tục).
conn11 = _fresh_db()
conn11.execute("DELETE FROM mst_status_cache")
conn11.commit()
conn11.close()
_fake_requests.calls.clear()
_fake_requests.next_text = None
_fake_requests.next_exc = Exception("mạng lỗi giả lập")
dem_loi = [0]
ket_qua_11 = []
for i in range(8):
    mst_gia = f"031569613{i % 10}"  # nhiều MST khác nhau -> không trùng cache
    ket_qua_11.append(_tra_cuu_trang_thai_mst(mst_gia + "0", timeout=1, so_lan_that_bai_lien_tiep=dem_loi))
assert all(kq["canh_bao"] is None for kq in ket_qua_11), (
    "Lỗi mạng KHÔNG được crash và KHÔNG được suy đoán canh_bao — phải luôn là None")
assert len(_fake_requests.calls) == 5, (
    f"Sau ĐÚNG 5 lỗi liên tiếp phải NGỪNG gọi mạng cho các MST còn lại trong lượt này (tránh treo lâu "
    f"vì hàng loạt timeout) — got {len(_fake_requests.calls)} lượt gọi thật (kỳ vọng đúng 5)")
print("PASS 11: lỗi mạng không làm crash (canh_bao=None, an toàn), và dừng hẳn việc gọi mạng sau 5 lỗi "
      "liên tiếp trong cùng 1 lượt xuất Excel — không treo lâu vô ích.")

os.unlink(_tmp_db.name)
print("\nALL DONE")
