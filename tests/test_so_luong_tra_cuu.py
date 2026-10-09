import os
import sys
import threading
import time

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Yêu cầu: tra cứu hóa đơn HÀNG LOẠT mặc định 1 luồng, người dùng chỉnh 2 hoặc 3, TỐI ĐA 3 (lưu ở
# app_settings 'so_luong_tra_cuu'). Tra cứu TỪNG công ty giữ NGUYÊN như cũ (thanh trượt 0-32 theo tốc độ).

_kho = {}
server._get_setting = lambda k, d="": _kho.get(k, d)
server._set_setting = lambda k, v: _kho.__setitem__(k, v)

# 1) Mặc định 1, kẹp 1..3
assert server._so_luong_tra_cuu() == 1
for vao, ra in [(0, 1), (-2, 1), (1, 1), (2, 2), (3, 3), (4, 3), (32, 3), ("abc", 1), (None, 1), ("2", 2)]:
    assert server._kep_so_luong_tra_cuu(vao) == ra, (vao, server._kep_so_luong_tra_cuu(vao))
assert server.set_so_luong_tra_cuu({"n": 9})["n"] == 3
assert server.get_so_luong_tra_cuu()["n"] == 3
print("PASS 1: số luồng hàng loạt mặc định 1, kẹp 1..3, lưu được.")

# 2) Tra cứu TỪNG công ty: như cũ — limiter theo tốc độ, endpoint 0-32, không lưu lựa chọn
_kho.clear()
assert server._new_fetch_job()["limiter"].get_limit() == server.SP().get("song_song", 4)
server.FETCH_JOBS[777] = server._new_fetch_job()
assert server.fetch_set_song_song(777, {"n": 20})["n"] == 20
assert server.FETCH_JOBS[777]["limiter"].get_limit() == 20
assert server.fetch_set_song_song(777, {"n": 0})["n"] == 0
assert "so_luong_tra_cuu" not in _kho
del server.FETCH_JOBS[777]
try:
    server.fetch_set_song_song(778, {"n": 3})
    raise AssertionError("không có job phải báo 404 như cũ")
except server.HTTPException as e:
    assert e.status_code == 404
print("PASS 2: tra cứu từng công ty giữ nguyên như cũ.")


# 3) query_invoices: có limiter -> không vượt giới hạn (cả HĐ thường lẫn máy tính tiền);
#    không limiter (1 công ty HĐ thường) -> như cũ 4 luồng
def _do_dong_thoi(lim, he_thong):
    c = server.GDTClient()
    dang = [0]
    max_dang = [0]
    khoa = threading.Lock()

    def _gia(*a, **k):
        with khoa:
            dang[0] += 1
            max_dang[0] = max(max_dang[0], dang[0])
        time.sleep(0.05)
        with khoa:
            dang[0] -= 1
        return [], 0, [], []
    c._query_one_range = _gia
    c._toan_ky_rong = lambda *a, **k: False
    c.query_invoices("01/01/2026", "31/12/2026", "sale", he_thong=he_thong,
                     mtt_limiter=(server.DynamicLimiter(lim) if lim else None))
    return max_dang[0]


for ht in ("query", "sco-query"):
    assert _do_dong_thoi(1, ht) == 1, ht
    m3 = _do_dong_thoi(3, ht)
    assert 1 < m3 <= 3, (ht, m3)
assert _do_dong_thoi(None, "query") == 4
print("PASS 3: có limiter -> không vượt giới hạn; HĐ thường không limiter -> 4 luồng như cũ.")

# 4) Giao diện: màn hình 1 công ty như cũ; khung hàng loạt có ô chọn 1-3
html = open(os.path.join(_REPO_ROOT, "static", "index.html"), encoding="utf-8").read()
assert 'id="songSongSlider" min="0" max="32" value="8"' in html
assert "SPEED_SONG_SONG={fast:16,balanced:8,safe:1}" in html
assert 'id="soLuongSel"' not in html
print("PASS 4: giao diện tra cứu từng công ty giữ như cũ.")

# 5) Tra cứu hàng loạt: số luồng = số công ty chạy cùng lúc (mặc định 1, tối đa 3), mỗi công ty 1 luồng
class _Cl:
    token = "x"


def _chay_batch(body):
    dang = [0]
    max_dang = [0]
    lim_cty = []
    khoa = threading.Lock()

    def _gia_fetch(cid, b):
        lim_cty.append(server.FETCH_JOBS[cid]["limiter"].get_limit())
        with khoa:
            dang[0] += 1
            max_dang[0] = max(max_dang[0], dang[0])
        time.sleep(0.05)
        with khoa:
            dang[0] -= 1
    goc = (server._run_fetch_job, server.get_client, server._batch_luu_db, server._xoa_loi_tra_cuu)
    server._run_fetch_job = _gia_fetch
    server.get_client = lambda cid: _Cl()
    server._batch_luu_db = lambda *a, **k: None
    server._xoa_loi_tra_cuu = lambda *a, **k: None
    cids = list(range(9001, 9007))
    bid = 424242
    server.BATCH_JOBS[bid] = {"running": True, "cancel": False, "total": len(cids), "done": 0,
                              "current_list": [], "started": time.time(), "order": cids,
                              "items": {c: {"status": "pending"} for c in cids}}
    try:
        server._run_batch(bid, cids, body)
    finally:
        (server._run_fetch_job, server.get_client, server._batch_luu_db, server._xoa_loi_tra_cuu) = goc
        server.BATCH_JOBS.pop(bid, None)
        for c in cids:
            server.FETCH_JOBS.pop(c, None)
    return max_dang[0], lim_cty


_kho["so_luong_tra_cuu"] = "1"
m, lc = _chay_batch({})
assert m == 1 and set(lc) == {1}, (m, lc)
m, lc = _chay_batch({"so_luong": 3})
assert 1 < m <= 3 and set(lc) == {1}, (m, lc)
m, lc = _chay_batch({"so_luong": 9})
assert m <= 3, m
assert server.fetch_batch_set_song_song(1, {"n": 5})["n"] == 3
assert 'id="bSoLuong"' in html and "/api/fetch-batch-song-song/" in html and "so_luong:kepSoLuongTraCuu" in html
print("PASS 5: hàng loạt mặc định 1 công ty/lần, chọn tối đa 3; mỗi công ty 1 luồng.")

# 6) Trong job tra cứu: hàng loạt (body["batch"]) -> HĐ thường cũng qua limiter; 1 công ty -> chỉ MTT
src = open(os.path.join(_REPO_ROOT, "server.py"), encoding="utf-8").read()
assert 'if (he_thong == "sco-query" or body.get("batch")) else None' in src
print("PASS 6: limiter cho HĐ thường chỉ bật khi tra cứu hàng loạt.")

print("\nALL DONE")
