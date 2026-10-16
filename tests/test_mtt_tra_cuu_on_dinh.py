import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Ca thật: hệ thống MÁY TÍNH TIỀN (sco-query) của trang Thuế trả danh sách KHÁC NHAU giữa các lần gọi
# cùng 1 kỳ (lần 1 thiếu 5 HĐ bán ra C26MCF tháng 9; lần 2 thiếu 2 HĐ mua vào tháng 8) mà 'total' cũng
# khớp số thiếu -> tra cứu lại ra số khác. Nay: máy tính tiền dò mỗi tháng ít nhất 2 lần, GỘP các lần,
# dò tiếp tới khi 1 lần không thêm hóa đơn mới. Hóa đơn điện tử thường: giữ 1 lần như cũ.
server.time.sleep = lambda s: None


def hd(so):
    return {"khmshdon": 1, "khhdon": "C26MCF", "shdon": so, "nbmst": "0318808536"}


DU = [hd(n) for n in range(172, 195)]                      # 23 hóa đơn tháng 9 (đầy đủ)
THIEU = [x for x in DU if x["shdon"] not in (178, 180, 181, 186, 189)]


def tao(cac_lan):
    c = server.GDTClient.__new__(server.GDTClient)
    goi = []

    def fake(tu, den, loai="purchase", page_size=50, he_thong="query", progress=None, ttxly_can_do=None, cancel_check=None):
        kq = cac_lan[min(len(goi), len(cac_lan) - 1)]
        goi.append(he_thong)
        return list(kq[0]), kq[1], list(kq[2]), list(kq[3])
    c._query_one_range = fake
    return c, goi


# 1) lần 1 thiếu (total cũng báo thiếu), lần 2 đủ, lần 3 không thêm gì -> 23 hóa đơn
c, goi = tao([(THIEU, 18, [], []), (DU, 23, [], []), (DU, 23, [], [])])
res, total, loi, tb = c._query_one_range_on_dinh("01/09/2026", "30/09/2026", "sold", he_thong="sco-query")
assert sorted(x["shdon"] for x in res) == list(range(172, 195)) and total == 23 and not loi and not tb
assert len(goi) == 3
print("PASS 1: máy tính tiền lần 1 thiếu 5 HĐ -> dò lại, gộp đủ 23 HĐ.")

# 2) lần 1 đủ, lần 2 thiếu -> vẫn giữ đủ (không mất HĐ đã lấy được), dừng khi không thêm mới
c, goi = tao([(DU, 23, [], []), (THIEU, 18, [], [])])
res, total, loi, tb = c._query_one_range_on_dinh("01/09/2026", "30/09/2026", "sold", he_thong="sco-query")
assert len(res) == 23 and total == 23 and len(goi) == 2
print("PASS 2: lần sau trả thiếu không làm mất HĐ đã lấy; 2 lần khớp nhau thì dừng.")

# 3) lỗi 1 trạng thái ở lần 1 nhưng lần 2 lấy được -> không báo lỗi; lỗi ở MỌI lần -> báo lỗi
c, goi = tao([(THIEU, 18, ["ttxly=6: 502"], [6]), (DU, 23, [], []), (DU, 23, [], [])])
res, total, loi, tb = c._query_one_range_on_dinh("01/09/2026", "30/09/2026", "purchase", he_thong="sco-query")
assert len(res) == 23 and not tb and not loi
c, goi = tao([(THIEU, 18, ["ttxly=6: 502"], [6])])
res, total, loi, tb = c._query_one_range_on_dinh("01/09/2026", "30/09/2026", "purchase", he_thong="sco-query")
assert tb == [6] and loi and len(goi) == server.GDTClient.MTT_SO_LAN_DO
print("PASS 3: lỗi chỉ tính khi trạng thái đó lỗi ở mọi lần dò.")

# 4) hóa đơn điện tử thường: chỉ 1 lần như cũ
c, goi = tao([(DU, 23, [], [])])
res, total, loi, tb = c._query_one_range_on_dinh("01/09/2026", "30/09/2026", "sold", he_thong="query")
assert len(goi) == 1 and len(res) == 23
print("PASS 4: hóa đơn điện tử thường vẫn dò 1 lần.")

# 5) query_invoices (cả đường dò đoạn lỗi) đều đi qua bản ổn định
src = open(os.path.join(os.path.dirname(server.__file__), "server.py"), encoding="utf-8").read()
qi = src[src.index("    def query_invoices("):src.index("    def _toan_ky_rong(")]
assert qi.count("self._query_one_range_on_dinh(") == 2 and "self._query_one_range(" not in qi
print("PASS 5: query_invoices dùng bản dò ổn định cho cả lượt đầu và lượt dò lại đoạn lỗi.")
print("ALL DONE")
