import os, sys, datetime
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Trang Thuế: "Khoảng thời gian tìm kiếm không được lớn hơn 10 ngày" -> tra cứu phải tự chia đoạn ≤ 10 ngày, liên tiếp tới hết khoảng người dùng chọn.
D = lambda s: datetime.datetime.strptime(s, "%d/%m/%Y").date()
assert server._chia_doan_toi_da_ngay(D("01/09/2026"), D("30/09/2026")) == [
    ("01/09/2026", "10/09/2026"), ("11/09/2026", "20/09/2026"), ("21/09/2026", "30/09/2026")]
assert server._chia_doan_toi_da_ngay(D("05/09/2026"), D("05/09/2026")) == [("05/09/2026", "05/09/2026")]
print("PASS 1: chia 01/09→30/09 thành 3 đoạn 10 ngày liên tiếp; 1 ngày -> 1 đoạn.")

for loai, ht in (("purchase", "query"), ("sold", "query"), ("purchase", "sco-query")):
    c = server.GDTClient.__new__(server.GDTClient)
    goi, dem = [], []
    c._toan_ky_rong = lambda *a, **k: dem.append(a) or False
    def fake(tu, den, loai, page_size, he_thong, progress=None, ttxly_can_do=None, cancel_check=None):
        goi.append((tu, den))
        return ([{"khmshdon": "1", "khhdon": "K", "shdon": tu, "nbmst": "1"}], 1, [], [])
    c._query_one_range_on_dinh = fake
    nhan = []
    res, total, loi, doan_loi = c.query_invoices("25/12/2025", "31/03/2026", loai=loai, he_thong=ht, progress=nhan.append)
    goi.sort(key=lambda x: D(x[0]))
    assert all((D(b) - D(a)).days <= 9 for a, b in goi), goi
    assert D(goi[0][0]) == D("25/12/2025") and D(goi[-1][1]) == D("31/03/2026")
    assert all(D(goi[i + 1][0]) == D(goi[i][1]) + datetime.timedelta(days=1) for i in range(len(goi) - 1)), "liên tiếp, không hở/chồng"
    assert len(res) == len(goi) == total and not dem, "khoảng > 10 ngày không gọi đếm nhanh 1 lần cho cả kỳ"
    assert any("[ĐOẠN 25/12/2025→03/01/2026]" in t for t in nhan)
print("PASS 2: query_invoices 25/12/2025→31/03/2026 gọi trang Thuế theo từng đoạn ≤ 10 ngày liên tiếp tới hết (mua vào/bán ra/máy tính tiền), gộp đủ kết quả.")

c = server.GDTClient.__new__(server.GDTClient)
dem = []
c._toan_ky_rong = lambda *a, **k: dem.append(a) or True
c._query_one_range_on_dinh = lambda *a, **k: ([], 0, [], [])
assert c.query_invoices("01/09/2026", "10/09/2026", loai="sold")[0] == [] and dem
print("PASS 3: khoảng ≤ 10 ngày vẫn dùng đếm nhanh để bỏ qua kỳ trống.")

# Tra cứu HÀNG LOẠT: /api/fetch-batch -> _run_batch -> _run_fetch_job(cid, body có batch=True) -> client.query_invoices(..., mtt_limiter=...)
# -> cũng chia đoạn ≤ 10 ngày (kể cả khi đi qua limiter dùng chung của batch). Không còn chỗ nào khác gọi API danh sách hóa đơn.
class Lim:
    def __init__(self): self.n = 0
    def acquire(self): self.n += 1
    def release(self): pass
c = server.GDTClient.__new__(server.GDTClient)
goi = []
c._toan_ky_rong = lambda *a, **k: False
c._query_one_range_on_dinh = lambda tu, den, *a, **k: goi.append((tu, den)) or ([], 0, [], [])
lim = Lim()
c.query_invoices("01/01/2026", "31/12/2026", loai="purchase", he_thong="query", mtt_limiter=lim)
assert len(goi) == 37 and lim.n == 37 and all((D(b) - D(a)).days <= 9 for a, b in goi), (len(goi), lim.n)
src = open(os.path.join(_REPO_ROOT, "server.py"), encoding="utf-8").read()
rb = src[src.index("def _run_batch("):src.index("def _run_batch(") + 30000]
assert "_run_fetch_job(cid, body)" in rb
rf = src[src.index("def _run_fetch_job("):src.index("def _run_batch(")]
assert "client.query_invoices(" in rf and "mtt_limiter=(mtt_limiter_query" in rf and 'body.get("batch")' in rf
import re
assert len(re.findall(r"/invoices/(purchase|sold)", src)) == 4, "API danh sách hóa đơn chỉ được gọi trong _toan_ky_rong/_query_one_range"
print("PASS 4: tra cứu hàng loạt (cả năm 2026, qua limiter của batch) cũng dò 37 đoạn ≤ 10 ngày; batch đi đúng luồng query_invoices.")
print("ALL DONE")
