import os, sys, threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Yêu cầu: TỰ ĐỘNG "Làm mới kết nối" khi bị trang Thuế ngắt kết nối và khi tra cứu bị treo (không cần tắt/mở phần mềm).
dong_ho = [10_000.0]
server.time.time = lambda: dong_ho[0]
server.time.sleep = lambda s: None

# 1) tự làm mới khi ngắt kết nối: tối đa 1 lần / LAM_MOI_TU_DONG_GIAN_CACH giây; luồng khác đang làm mới thì bỏ qua
server.CLIENTS.clear()
server._LAM_MOI_TT.update(luc=0.0, text="", so_lan=0)
assert server._lam_moi_ket_noi_tu_dong("Trang Thuế ngắt kết nối khi tải danh sách hóa đơn") is not None
assert "ngắt kết nối" in server._LAM_MOI_TT["text"] and server._LAM_MOI_TT["so_lan"] == 1
assert server._lam_moi_ket_noi_tu_dong("lại lỗi") is None, "chưa đủ giãn cách -> không làm mới dồn dập"
dong_ho[0] += server.LAM_MOI_TU_DONG_GIAN_CACH + 1
server._KHOA_LAM_MOI_KET_NOI.acquire()
try:
    assert server._lam_moi_ket_noi_tu_dong("x") is None, "luồng khác đang làm mới -> bỏ qua, không chờ"
finally:
    server._KHOA_LAM_MOI_KET_NOI.release()
assert server._lam_moi_ket_noi_tu_dong("lần 2") is not None and server._LAM_MOI_TT["so_lan"] == 2
print("PASS 1: bị ngắt kết nối -> tự làm mới toàn bộ kết nối, giãn cách", server.LAM_MOI_TU_DONG_GIAN_CACH, "s, không làm trùng.")

src = open(os.path.join(os.path.dirname(server.__file__), "server.py"), encoding="utf-8").read()
for ly_do in ("khi tải danh sách hóa đơn", "khi kiểm tra kỳ có hóa đơn", "khi tải file hóa đơn", "khi lấy captcha đăng nhập", "Trang Thuế ngắt kết nối khi đăng nhập"):
    assert f'_lam_moi_ket_noi_tu_dong("Trang Thuế ngắt kết nối {ly_do}' in src or f'_lam_moi_ket_noi_tu_dong("{ly_do}' in src, ly_do
print("PASS 2: gắn tự làm mới ở mọi chỗ bị ngắt: tải danh sách, đếm nhanh, tải file, lấy captcha, đăng nhập.")

# 3) luồng canh gác treo
lam_moi = []
server._lam_moi_ket_noi_tu_dong = lambda ly_do: lam_moi.append(ly_do)
def _ngu(giay, cancel_check=None): dong_ho[0] += giay
server._ngu_ktra_huy = _ngu
def chay_canh_gac(so_vong, cids, cho_phep_huy=True):
    dem = [0]; ghi = []
    def con_chay():
        dem[0] += 1
        return dem[0] <= so_vong
    server._canh_gac_treo(con_chay, lambda: cids, cho_phep_huy, lambda cid, t: ghi.append((cid, t)), chu_ky=15)
    return ghi

server.FETCH_JOBS[1] = {"messages": [{"stage": "query", "text": "x"}], "last": {"stage": "query"}}
ghi = chay_canh_gac(50, [1])            # 50 vòng x 15s = 750s đứng yên
assert lam_moi and "đứng yên" in lam_moi[0], lam_moi
assert server.FETCH_JOBS[1].get("treo") and server.FETCH_JOBS[1].get("cancel")
assert any("treo" in t for _, t in ghi) and any("làm mới" in t for _, t in ghi)
print("PASS 3: đứng yên >=", server.BATCH_TREO_LAM_MOI, "s -> tự làm mới kết nối; >=", server.BATCH_TREO_HUY, "s ở bước tra cứu -> tự dừng công ty (thử lại cuối đợt).")

lam_moi.clear()
server.FETCH_JOBS[2] = {"messages": [], "last": {"stage": "query"}}
class TangDan(list):
    pass
def chay_co_tien_do():
    dem = [0]
    def con_chay():
        dem[0] += 1
        server.FETCH_JOBS[2]["messages"].append({"stage": "download"})     # mỗi vòng có tiến độ mới
        return dem[0] <= 60
    server._canh_gac_treo(con_chay, lambda: [2], True, None, chu_ky=15)
chay_co_tien_do()
assert not lam_moi and not server.FETCH_JOBS[2].get("treo")
print("PASS 4: có tiến độ đều -> không làm mới, không dừng.")

server.FETCH_JOBS[3] = {"messages": [{"stage": "info"}], "last": {"stage": "info", "text": "Đang tự động kết xuất Excel"}}
chay_canh_gac(60, [3])
assert not server.FETCH_JOBS[3].get("treo"), "bước kết xuất Excel/XML không bị dừng"
server.FETCH_JOBS[4] = {"messages": [{"stage": "query"}], "last": {"stage": "query"}}
chay_canh_gac(60, [4], cho_phep_huy=False)
assert not server.FETCH_JOBS[4].get("treo"), "tra cứu 1 công ty: chỉ làm mới, không tự dừng"
print("PASS 5: không dừng ở bước kết xuất; tra cứu 1 công ty chỉ tự làm mới kết nối (không tự dừng).")

assert 'if (FETCH_JOBS.get(cid) or {}).get("treo"):' in src and "threading.Thread(target=_canh_gac_treo" in src
assert src.count("threading.Thread(target=_canh_gac_treo") == 2
print("PASS 6: canh gác chạy cho cả tra cứu hàng loạt (tự dừng + thử lại) và tra cứu 1 công ty (tự làm mới).")
print("ALL DONE")
