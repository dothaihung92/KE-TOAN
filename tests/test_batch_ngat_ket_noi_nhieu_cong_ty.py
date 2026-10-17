import os, sys, threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Ca thật: tra cứu hàng loạt ~10 công ty ổn, ~50 công ty liên tục thì trang Thuế ngắt kết nối
# ("Connection aborted / RemoteDisconnected"). Nay: nghỉ giữa các nhóm công ty, tạm dừng cả đợt khi bị ngắt (chờ tăng dần),
# giải phóng kết nối cũ sau mỗi công ty, và TỰ THỬ LẠI các công ty bị ngắt kết nối ở cuối đợt (không đổi IP/không tránh né).
LOI = "('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))"
assert server._la_loi_ket_noi(Exception(LOI)) and server._la_loi_ket_noi(LOI)
assert not server._la_loi_ket_noi("Sai mã captcha")

# 1) bộ theo dõi sức khỏe kết nối
sk = server._SucKhoeKetNoi()
assert sk.loi() == server.BATCH_COOLDOWN_GOC and sk.loi() == 2 * server.BATCH_COOLDOWN_GOC
for _ in range(10): sk.loi()
assert sk.loi() == server.BATCH_COOLDOWN_TOI_DA
giay, ly = sk.nghi_truoc_khi_bat_dau()
assert giay > 0 and "ngắt kết nối" in ly
server._COOLDOWN_TOAN_CUC["den"] = 0.0                 # cooldown dùng chung do sk.loi() ở trên đặt -> xoá để kiểm riêng phần nghỉ giữa nhóm
sk2 = server._SucKhoeKetNoi()
dem = [sk2.nghi_truoc_khi_bat_dau()[0] for _ in range(25)]
assert [i + 1 for i, g in enumerate(dem) if g] == [11, 21] and set(dem) == {0, server.BATCH_NGHI_GIUA_NHOM}
sk2.loi(); sk2.tot(); assert sk2.lien_tiep == 0
print("PASS 1: nghỉ 20s sau mỗi nhóm 10 công ty; ngắt kết nối -> tạm dừng 30s, 60s... (tối đa 300s); thành công thì reset.")

# 2) mô phỏng đợt 25 công ty: 2 công ty bị ngắt kết nối ở lần đầu -> tự thử lại ở cuối đợt, kết quả cuối: tất cả xong
nghi = []
server.time.sleep = lambda s: None
dong_ho = [1000.0]
server.time.time = lambda: dong_ho[0]                                           # đồng hồ giả: chỉ chạy tới khi "nghỉ"
def _nghi_gia(giay, cancel_check=None):
    nghi.append(giay); dong_ho[0] += giay                                      # ghi số giây định nghỉ, không nghỉ thật
server._ngu_ktra_huy = _nghi_gia
server._xoa_loi_tra_cuu = lambda cid: None
server._luu_loi_tra_cuu = lambda cid, t: None
server._batch_luu_db = lambda *a, **k: None
server._mo_trinh_duyet_captcha = lambda: None
server._dong_trinh_duyet_captcha = lambda d: None


class FakeClient:
    def __init__(self): self.token = "T"; self.moi = 0
    def _dung_lai_session(self, ep_http11=False): self.moi += 1


clients = {}
server.get_client = lambda cid: clients.setdefault(cid, FakeClient())
server.CLIENTS = clients
server._new_fetch_job = lambda: {"messages": [], "last": None, "running": True, "cancel": False, "limiter": server.DynamicLimiter(1)}
lan_chay = {}
khoa = threading.Lock()


def chay(loi_mai):
    def fake(cid, body):
        with khoa:
            lan_chay[cid] = lan_chay.get(cid, 0) + 1
            n = lan_chay[cid]
        if cid in loi_mai or (cid in (3, 7) and n == 1):
            raise Exception(LOI)
        server.FETCH_JOBS[cid]["last"] = {"stage": "done", "text": "Hoàn tất", "total_saved": 3}
    return fake


def dung_batch(bid, n):
    items = {c: server._batch_item_moi(c, f"CT{c}") for c in range(1, n + 1)}
    server.BATCH_JOBS[bid] = {"items": items, "total": n, "done": 0, "running": True, "cancel": False,
                              "limiter": server.DynamicLimiter(3), "trang_thai": "dang_chay"}
    return server.BATCH_JOBS[bid]


server._run_fetch_job = chay(set())
b = dung_batch(901, 25)
server._run_batch(901, list(range(1, 26)), {"so_luong": 3})
assert all(it["status"] == "done" for it in b["items"].values()), {c: (i["status"], i["note"]) for c, i in b["items"].items() if i["status"] != "done"}
assert b["done"] == 25 and lan_chay[3] == 2 and lan_chay[7] == 2 and lan_chay[1] == 1
assert not b.get("thu_lai")
assert server.BATCH_NGHI_GIUA_NHOM in nghi, "có nghỉ giữa các nhóm"
assert any(x >= server.BATCH_COOLDOWN_GOC for x in nghi), "có chờ sau khi bị ngắt kết nối"
assert all(c.moi >= 1 for c in clients.values()), "mọi công ty đều được giải phóng kết nối cũ sau khi xong"
print("PASS 2: 2 công ty bị ngắt kết nối lần đầu -> tự thử lại cuối đợt; cả 25 công ty xong; đợt có nghỉ nhóm + cooldown.")

# 3) ngắt kết nối mãi: thử lại tối đa BATCH_THU_LAI_TOI_DA vòng rồi báo lỗi rõ (không lặp vô tận)
lan_chay.clear(); clients.clear(); nghi.clear()
server._run_fetch_job = chay({5})
b = dung_batch(902, 8)
server._run_batch(902, list(range(1, 9)), {"so_luong": 2})
assert lan_chay[5] == 1 + server.BATCH_THU_LAI_TOI_DA
assert b["items"][5]["status"] == "error" and "ngắt kết nối" in b["items"][5]["note"]
assert all(b["items"][c]["status"] == "done" for c in range(1, 9) if c != 5)
assert b["done"] == 8
print("PASS 3: ngắt kết nối dai dẳng -> thử lại tối đa", server.BATCH_THU_LAI_TOI_DA, "vòng rồi báo lỗi; công ty khác không bị ảnh hưởng.")

# 4) lỗi KHÔNG phải kết nối (vd sai dữ liệu) -> không thử lại
lan_chay.clear(); clients.clear()
def fake_loi_khac(cid, body):
    lan_chay[cid] = lan_chay.get(cid, 0) + 1
    if cid == 2: raise ValueError("loi du lieu")
    server.FETCH_JOBS[cid]["last"] = {"stage": "done", "text": "ok", "total_saved": 1}
server._run_fetch_job = fake_loi_khac
b = dung_batch(903, 4)
server._run_batch(903, [1, 2, 3, 4], {"so_luong": 2})
assert lan_chay[2] == 1 and b["items"][2]["status"] == "error"
print("PASS 4: lỗi không phải ngắt kết nối thì không tự thử lại.")

# 5) công ty bị canh gác đánh dấu TREO (tự dừng) -> báo lỗi rồi tự thử lại ở cuối đợt, lần sau xong
lan_chay.clear(); clients.clear()
def fake_treo(cid, body):
    lan_chay[cid] = lan_chay.get(cid, 0) + 1
    if cid == 3 and lan_chay[cid] == 1:
        server.FETCH_JOBS[cid]["treo"] = True                      # như luồng canh gác đã tự dừng
        server.FETCH_JOBS[cid]["last"] = {"stage": "warn", "text": "⏹ đã dừng"}
        return
    server.FETCH_JOBS[cid]["last"] = {"stage": "done", "text": "ok", "total_saved": 1}
server._run_fetch_job = fake_treo
b = dung_batch(904, 4)
server._run_batch(904, [1, 2, 3, 4], {"so_luong": 2})
assert lan_chay[3] == 2 and b["items"][3]["status"] == "done", (lan_chay, b["items"][3])
print("PASS 5: công ty bị treo (canh gác tự dừng) -> tự thử lại ở cuối đợt và xong.")
print("ALL DONE")
