import os, sys, threading, time
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Máy tính tiền (sco-query): tra cứu danh sách TỪNG ĐỢT 1 LUỒNG — xong đoạn 10 ngày này mới sang đoạn kế (kể cả mua vào + bán ra cùng lúc), tránh 429.
# Hóa đơn thường (query): giữ song song như cũ.
def do(ht, goi_dong_thoi=1):
    c = server.GDTClient.__new__(server.GDTClient)
    c._toan_ky_rong = lambda *a, **k: False
    hien, toi_da, thu_tu, kh = [0], [0], [], threading.Lock()
    def fake(tu, den, loai, page_size, he_thong, progress=None, ttxly_can_do=None, cancel_check=None):
        with kh:
            hien[0] += 1; toi_da[0] = max(toi_da[0], hien[0]); thu_tu.append(tu)
        time.sleep(0.05)
        with kh:
            hien[0] -= 1
        return ([], 0, [], [])
    c._query_one_range_on_dinh = fake
    ts = [threading.Thread(target=lambda l=l: c.query_invoices("01/01/2026", "31/03/2026", loai=l, he_thong=ht)) for l in ("purchase", "sold")[:goi_dong_thoi]]
    [t.start() for t in ts]; [t.join() for t in ts]
    return toi_da[0], len(thu_tu)

m, n = do("sco-query", 2)
assert m == 1 and n == 18, (m, n)          # mua vào + bán ra, mỗi bên 9 đoạn, nhưng không bao giờ 2 đoạn cùng lúc
m2, _ = do("query", 1)
assert m2 > 1, m2                          # hóa đơn thường vẫn song song
print("PASS: máy tính tiền chạy từng đoạn 10 ngày 1 luồng (cả mua vào + bán ra), hóa đơn thường vẫn song song.")
