import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Regression test cho GDTClient._fetch_paginated() (server.py) — người dùng
# báo lỗi thật: đăng nhập được rồi (đã sửa xong ở bản trước), nhưng khi TRA
# CỨU hóa đơn (mua vào/bán ra, đặc biệt máy tính tiền) vẫn gặp "HTTP Error
# 403" cho MỘT PHẦN các lượt gọi (vd 3/9 lượt cho các trạng thái ttxly=5/6/8
# của tháng 08/2026), dù đã tự tra cứu lại 6 lượt vẫn còn lỗi ở đúng các
# đoạn đó.
#
# Nguyên nhân cùng họ với lỗi 403 ở bước đăng nhập đã sửa trước đó (thiếu
# header "request-id" — trang thật (Angular) tự sinh UUID mới cho MỌI
# request, không riêng gì đăng nhập) — nhưng KHÁC ở chỗ: trước đây 403 ở
# bước tra cứu hóa đơn hoàn toàn KHÔNG được retry (rơi thẳng xuống
# raise_for_status(), khác hẳn cách xử lý 429/5xx đã có sẵn ở ngay bên
# cạnh) — 1 lượt 403 thoáng qua (có thể do tải dồn dập 3 luồng ttxly cùng
# lúc) là mất hẳn đoạn đó, phải người dùng tự bấm tra cứu lại.
#
# Sửa 2 việc: (1) thêm header "request-id" (UUID mới mỗi lượt gọi, đúng như
# trang thật) vào MỌI lượt gọi trong _fetch_paginated(); (2) 403 giờ được
# RETRY có chờ (giống hệt cách đã xử lý 429), GIỚI HẠN số lần liên tiếp
# (retry_max) — khác 429/5xx vốn thử vô hạn, vì 403 cũng có thể là lỗi thật
# sự không tự hết.


class _FakeResp:
    def __init__(self, status_code, data=None):
        self.status_code = status_code
        self._data = data if data is not None else {}
        self.headers = {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP Error {self.status_code}: ")

    def json(self):
        return self._data


class _FakeSession:
    def __init__(self):
        self.calls = []
        self.headers = {}
        self.next_responses = []   # queue [(status, data), ...]

    def get(self, url, headers=None, timeout=None, params=None):
        self.calls.append({"url": url, "headers": dict(headers or {})})
        status, data = self.next_responses.pop(0)
        return _FakeResp(status, data)


def _patch_sleep():
    """Thay time.sleep THẬT bằng bản ghi lại (không chờ thật) trong lúc test
    — _ngu_ktra_huy() gọi thẳng time.sleep() của module server.py."""
    calls = []
    orig = server.time.sleep
    server.time.sleep = lambda s: calls.append(s)
    return calls, orig


def _unpatch_sleep(orig):
    server.time.sleep = orig


def _new_client():
    c = server.GDTClient()
    fs = _FakeSession()
    c.session = fs
    return c, fs


DATA_THANH_CONG = {"datas": [{"khhdon": "1", "khhdon": "K1", "shdon": "1", "nbmst": "0300000000"}],
                   "total": 1, "state": None}

# ===== Test 1 (QUAN TRỌNG — đúng ca thật người dùng gặp): 3 lượt 403 LIÊN
# TIẾP (thoáng qua) rồi lượt thứ 4 thành công -> PHẢI tự động thử lại (có
# chờ, giống hệt cách xử lý 429), KHÔNG được bỏ cuộc ngay ở lượt 403 đầu
# tiên — lấy được kết quả thật, mỗi lượt gọi có request-id KHÁC NHAU. =====
sleeps, orig_sleep = _patch_sleep()
c1, fs1 = _new_client()
fs1.next_responses = [(403, None), (403, None), (403, None), (200, DATA_THANH_CONG)]
try:
    results, total = c1._fetch_paginated(
        "https://hoadondientu.gdt.gov.vn/api/query/invoices/purchase",
        "tdlap=ge=2026-08-01T00:00:00", "Tìm kiếm (hóa đơn mua vào)", want_total=True)
finally:
    _unpatch_sleep(orig_sleep)
assert len(results) == 1 and total == 1, f"Phải lấy được kết quả thật sau khi thử lại qua 403 — got {results}, {total}"
assert len(fs1.calls) == 4, f"Phải thử ĐÚNG 4 lượt gọi (3 lượt 403 rồi lượt 4 thành công) — got {len(fs1.calls)}"
rids = [c["headers"].get("request-id") for c in fs1.calls]
assert all(rids) and len(set(rids)) == 4, (
    f"Mỗi lượt gọi phải có request-id KHÁC NHAU (UUID mới mỗi lần, đúng như trang thật) — got {rids}")
assert len(sleeps) == 3, f"Phải có ĐÚNG 3 lượt chờ (trước mỗi lần thử lại sau 403) — got {sleeps}"
print("PASS 1: 403 thoáng qua (3 lượt liên tiếp) -> tự động thử lại có chờ (giống 429), KHÔNG bỏ cuộc "
      "ngay, lấy được kết quả thật sau khi thử lại — mỗi lượt gọi có request-id khác nhau.")

# ===== Test 2 (không hồi quy — QUAN TRỌNG): 403 liên tục VƯỢT QUÁ số lần
# thử lại cho phép (retry_max, mặc định 8 ở tốc độ "fast") -> PHẢI dừng lại
# và báo lỗi rõ ràng (KHÔNG lặp vô hạn như 429/5xx). =====
sleeps2, orig_sleep2 = _patch_sleep()
c2, fs2 = _new_client()
retry_max = server.SP()["retry_max"]
fs2.next_responses = [(403, None)] * (retry_max + 2)   # nhiều hơn hẳn ngưỡng cho phép
loi = None
try:
    try:
        c2._fetch_paginated(
            "https://hoadondientu.gdt.gov.vn/api/query/invoices/purchase",
            "tdlap=ge=2026-08-01T00:00:00", "Tìm kiếm (hóa đơn mua vào)", want_total=True)
    except Exception as e:
        loi = e
finally:
    _unpatch_sleep(orig_sleep2)
assert loi is not None and "403" in str(loi), f"403 liên tục vượt ngưỡng thử lại -> phải báo lỗi rõ ràng — got {loi}"
assert len(fs2.calls) == retry_max + 1, (
    f"Phải dừng lại ĐÚNG sau retry_max+1 lượt gọi (không lặp vô hạn như 429/5xx) — got "
    f"{len(fs2.calls)} lượt, kỳ vọng {retry_max + 1}")
print(f"PASS 2: 403 liên tục vượt quá ngưỡng thử lại ({retry_max} lần) -> dừng lại, báo lỗi rõ ràng, "
      f"KHÔNG lặp vô hạn.")

print("\nALL DONE")
