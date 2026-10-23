import os, sys, json, sqlite3
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Ca thật: hệ thống MÁY TÍNH TIỀN (sco-query) của trang Thuế trả danh sách KHÁC NHAU giữa các lần tra cứu
# cùng 1 kỳ, 'total' cũng khớp số thiếu. Build .230 dò lại trên CÙNG phiên -> vẫn ra đúng kết quả thiếu
# (4 bảng kê người dùng gửi: mỗi lần thiếu 1 nhóm khác nhau). Nay:
#  (1) máy tính tiền: lần 2, 3... dò bằng PHIÊN HTTP MỚI (cùng token), gộp các lần, tối thiểu 3 lần;
#  (2) hóa đơn lần trước có mà lần này thiếu -> xác minh từng hóa đơn qua API chi tiết của trang Thuế,
#      trang Thuế còn trả thì GIỮ, không trả thì bỏ.
server.time.sleep = lambda s: None


def hd(so, kh="C26MCF"):
    return {"khmshdon": 1, "khhdon": kh, "shdon": so, "nbmst": "0318808536", "tdlap": "2026-09-10T00:00:00", "tthai": 1}


DU = [hd(n) for n in range(172, 195)]
THIEU = [x for x in DU if x["shdon"] not in (178, 180, 181, 186, 189)]


def tao(phien_cu, phien_moi):
    """phien_cu: kết quả trên phiên đang dùng; phien_moi: list kết quả lần lượt cho các phiên mới."""
    c = server.GDTClient.__new__(server.GDTClient)
    c.token = "T"
    goi = []

    def fake_cu(tu, den, loai="purchase", page_size=50, he_thong="query", progress=None, ttxly_can_do=None, cancel_check=None):
        goi.append("cu")
        return list(phien_cu[0]), phien_cu[1], list(phien_cu[2]), list(phien_cu[3])
    c._query_one_range = fake_cu
    goc = server.GDTClient._ban_sao_phien_moi

    def ban_sao(self):
        phu = goc(self)
        i = sum(1 for g in goi if g != "cu")
        kq = phien_moi[min(i, len(phien_moi) - 1)]

        def fake_moi(*a, **k):
            goi.append("moi")
            if isinstance(kq, Exception):
                raise kq
            return list(kq[0]), kq[1], list(kq[2]), list(kq[3])
        phu._query_one_range = fake_moi
        assert phu.session is not getattr(self, "session", None) and phu.session.headers.get("Authorization") == "Bearer T"
        assert not list(phu.session.cookies), "phiên mới không mang cookie cũ"
        return phu
    c._ban_sao_phien_moi = ban_sao.__get__(c)
    return c, goi


# 1) phiên cũ thiếu 5 HĐ (total cũng báo thiếu), phiên mới đủ -> gộp đủ 23
c, goi = tao((THIEU, 18, [], []), [(DU, 23, [], [])])
res, total, loi, tb = c._query_one_range_on_dinh("01/09/2026", "30/09/2026", "sold", he_thong="sco-query")
assert sorted(x["shdon"] for x in res) == list(range(172, 195)) and total == 23 and not loi and not tb
assert goi[0] == "cu" and goi[1:] == ["moi", "moi"], goi
print("PASS 1: lần 2+ dò bằng phiên mới (không cookie cũ, cùng token) -> gộp đủ 23 HĐ.")

# 2) cả 3 lần giống nhau -> dừng sau 3 lần; phiên mới lỗi hẳn -> bỏ qua lần đó, giữ kết quả
c, goi = tao((DU, 23, [], []), [(DU, 23, [], [])])
res, *_ = c._query_one_range_on_dinh("01/09/2026", "30/09/2026", "sold", he_thong="sco-query")
assert len(res) == 23 and len(goi) == 3
c, goi = tao((DU, 23, [], []), [RuntimeError("ket noi moi loi")])
res, total, loi, tb = c._query_one_range_on_dinh("01/09/2026", "30/09/2026", "sold", he_thong="sco-query")
assert len(res) == 23 and not tb and not loi
print("PASS 2: tối thiểu 3 lần; phiên mới lỗi không làm mất/lỗi kết quả.")

# 3) lỗi trạng thái ở phiên cũ nhưng phiên mới lấy được -> không báo lỗi; lỗi ở mọi lần -> báo lỗi
c, goi = tao((THIEU, 18, ["ttxly=6: 502"], [6]), [(DU, 23, [], [])])
res, total, loi, tb = c._query_one_range_on_dinh("01/09/2026", "30/09/2026", "purchase", he_thong="sco-query")
assert len(res) == 23 and not tb and not loi
c, goi = tao((THIEU, 18, ["ttxly=6: 502"], [6]), [(THIEU, 18, ["ttxly=6: 502"], [6])])
res, total, loi, tb = c._query_one_range_on_dinh("01/09/2026", "30/09/2026", "purchase", he_thong="sco-query")
assert tb == [6] and loi
print("PASS 3: lỗi chỉ tính khi trạng thái đó lỗi ở mọi lần dò.")

# 4) hóa đơn điện tử thường: 1 lần như cũ
c, goi = tao((DU, 23, [], []), [(DU, 23, [], [])])
c._query_one_range_on_dinh("01/09/2026", "30/09/2026", "sold", he_thong="query")
assert goi == ["cu"]
print("PASS 4: hóa đơn điện tử thường vẫn dò 1 lần.")

# 5) xác minh hóa đơn lần trước có mà lần này thiếu
conn = sqlite3.connect(":memory:"); conn.row_factory = sqlite3.Row
conn.execute("CREATE TABLE invoices (company_id, loai, he_thong, raw, tdlap)")
for x in DU + [dict(hd(999), tdlap="2026-06-01T00:00:00")]:
    conn.execute("INSERT INTO invoices VALUES (7,'sold','sco-query',?,?)", (json.dumps(x), x["tdlap"]))
con_ton_tai = {178, 180, 181, 186}           # 189: trang Thuế không trả chi tiết -> vẫn GIỮ dữ liệu lần trước (hóa đơn đã cấp không biến mất)


class FakeClient:
    def __init__(self): self.hoi = []
    def get_detail(self, nbmst, khhdon, khmshdon, shdon, he_thong="query", max_retry=None, loai=None, **k):
        self.hoi.append(shdon)
        return {"khhdon": khhdon, "shdon": shdon, "tthai": 3} if shdon in con_ton_tai else None


fc, tb_ = FakeClient(), []
giu = server._xac_minh_hoa_don_bi_sot(fc, conn, 7, "sold", "sco-query", "01/09/2026", "30/09/2026", THIEU,
                                      progress=tb_.append)
assert sorted(fc.hoi) == [178, 180, 181, 186, 189], "chỉ hỏi đúng HĐ thiếu trong kỳ (không hỏi HĐ ngoài kỳ 999)"
assert sorted(x["shdon"] for x in giu) == [178, 180, 181, 186, 189]
assert all(x["tthai"] == 3 for x in giu if x["shdon"] != 189), "HĐ xác minh được: cập nhật trạng thái mới"
assert [x for x in giu if x["shdon"] == 189][0].get("tthai") != 3, "HĐ không lấy được chi tiết: giữ nguyên dữ liệu lần trước"
assert any("189" in t for t in tb_)
assert server._xac_minh_hoa_don_bi_sot(fc, conn, 7, "sold", "sco-query", "01/09/2026", "30/09/2026", DU) == []
print("PASS 5: HĐ thiếu so với lần trước -> xác minh từng HĐ trên trang Thuế; còn thì giữ (trạng thái mới); không lấy được chi tiết thì vẫn giữ dữ liệu cũ (không làm mất hóa đơn đã Import MISA).")

# 6) nối vào luồng tra cứu: query_invoices dùng bản ổn định; xác minh chạy TRƯỚC khi xóa dữ liệu cũ
src = open(os.path.join(os.path.dirname(server.__file__), "server.py"), encoding="utf-8").read()
qi = src[src.index("    def query_invoices("):src.index("    def _toan_ky_rong(")]
assert qi.count("self._query_one_range_on_dinh(") == 2 and "self._query_one_range(" not in qi
i_xm = src.index("invs = invs + _xac_minh_hoa_don_bi_sot(")
i_del = src.index('"DELETE FROM invoices WHERE company_id=? AND loai=? AND he_thong=?"', i_xm)
assert i_del - i_xm < 1500
print("PASS 6: luồng tra cứu dùng dò ổn định + xác minh trước khi xóa dữ liệu cũ.")

# 7) Tra cứu hóa đơn HÀNG LOẠT dùng CHUNG _run_fetch_job (cùng 2 lớp trên) cho từng công ty, mặc định có máy tính tiền
i_batch = src.index("_run_fetch_job(cid, body)   # chạy đồng bộ trong thread riêng của công ty này")
assert src.count("_run_fetch_job(cid, body)") >= 2 and i_batch > src.index("def _run_fetch_job(")
assert 'body.get("he_thong_list", ["query", "sco-query"])' in src
print("PASS 7: tra cứu hàng loạt dùng chung luồng tra cứu (dò phiên mới + xác minh HĐ bị sót).")
print("ALL DONE")
