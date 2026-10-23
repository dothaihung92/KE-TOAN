import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Ca thật (bán ra máy tính tiền, 1 đoạn 01/09→10/09/2026 có 2320 HĐ — trang Thuế giới hạn 10 ngày/lần): thiếu 5 HĐ -> mỗi lượt dò lại ĐOẠN thiếu, màn hình báo
# "trang Thuế báo 2320 → 4640 → 6960..." (tăng đúng 1 tháng mỗi lượt) và luôn coi là còn thiếu dù đã lấy đủ 2320.
# Nguyên nhân: tổng "Thuế báo" của lượt dò lại bị CỘNG CHỒNG vào tổng lượt trước. Nay THAY phần cũ bằng phần mới.
server.time.sleep = lambda s: None


def hd(n):
    return {"khmshdon": 1, "khhdon": "C26MCF", "shdon": n, "nbmst": "0318808536"}


DU = [hd(n) for n in range(2320)]


class C(server.GDTClient):
    def __init__(self, cac_lan):
        self.cac_lan = cac_lan; self.goi = []; self.token = "T"
        self.session = type("S", (), {"close": staticmethod(lambda: None)})()
    def _ban_sao_phien_moi(self):                       # không mở kết nối thật trong test
        return self
    def _query_one_range(self, tu, den, loai="purchase", page_size=50, he_thong="query", progress=None, ttxly_can_do=None, cancel_check=None):
        kq = self.cac_lan[min(len(self.goi), len(self.cac_lan) - 1)]
        self.goi.append((tu, den, ttxly_can_do))
        return kq


# lượt 1: lấy 2315/2320; lượt dò lại đoạn: lấy đủ 2320/2320
c = C([(DU[:2315], 2320, [], [])] * 3 + [(DU, 2320, [], [])])   # 3 lần dò đầu (máy tính tiền) cùng thiếu, lượt dò lại đoạn đủ
moi, tong1, loi, doan = c.query_invoices("01/09/2026", "10/09/2026", loai="sold", he_thong="sco-query")
assert len(moi) == 2315 and tong1 == 2320
assert doan == [{"tu": "01/09/2026", "den": "10/09/2026", "ttxly": None, "total": 2320}], doan
exp = tong1                                                    # như _run_fetch_job: lượt đầu thay hoàn toàn
moi2, tong2, loi2, doan2 = c.query_invoices("01/09/2026", "10/09/2026", loai="sold", he_thong="sco-query", chi_cac_doan=doan)
exp = max(0, exp - sum(int(d.get("total") or 0) for d in doan)) + tong2       # đúng công thức ở _run_fetch_job
assert exp == 2320 and not doan2, (exp, doan2)
assert len(moi2) == 2320
print("PASS 1: dò lại đoạn thiếu -> tổng Thuế báo vẫn 2320 (không còn 4640/6960), đủ 2320/2320 là xong.")

# đoạn LỖI HẲN (chưa cộng total nào) -> total=0 -> lượt dò lại cộng total mới, không trừ nhầm
c = C([([], 0, ["boom"], [None])] * 4 + [(DU, 2320, [], [])])
moi, tong1, loi, doan = c.query_invoices("01/09/2026", "10/09/2026", loai="sold", he_thong="sco-query")
assert tong1 == 0 and doan == [{"tu": "01/09/2026", "den": "10/09/2026", "ttxly": None, "total": 0}]
moi2, tong2, _l, _d = c.query_invoices("01/09/2026", "10/09/2026", loai="sold", he_thong="sco-query", chi_cac_doan=doan)
assert max(0, tong1 - 0) + tong2 == 2320
print("PASS 2: đoạn lỗi hẳn (total=0) dò lại -> tổng đúng 2320.")

# công thức nằm đúng ở nhánh dò lại theo đoạn của _run_fetch_job
src = open(os.path.join(os.path.dirname(server.__file__), "server.py"), encoding="utf-8").read()
assert "exp0_gop = max(0, exp0_gop - sum(int(d.get(\"total\") or 0) for d in (doan_dung_de_goi or []))) + (moi_total or 0)" in src
assert "exp0_gop += moi_total or 0" not in src
print("PASS 3: _run_fetch_job thay (không cộng chồng) tổng kỳ vọng của đoạn dò lại.")
print("ALL DONE")
