import os
import re
import sys
import time
import threading

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Regression test cho yêu cầu người dùng (sau lượt xuất Excel thật 29 MST, 4 MST cuối "Hết ngân sách
# thời gian" 180s): "nếu có 100 mst thì... bỏ giới hạn 180 giây mà hãy để trung bình kiểm tra 6–7
# giây mỗi MST giống như người dò thật đang dò mst. và làm ra hiện thông tin đang dò bao nhiêu mst và
# đang dò tới đâu rồi trên phần mềm để người dùng biết".

src = open(os.path.join(_REPO_ROOT, "server.py"), encoding="utf-8").read()

# ===== 1: KHÔNG còn giới hạn thời gian tra MST mỗi lượt xuất Excel. =====
assert server._MST_NGAN_SACH_GIAY is None, f"got {server._MST_NGAN_SACH_GIAY}"
print("PASS 1: bỏ giới hạn thời gian tra MST mỗi lượt xuất Excel (dò tới hết danh sách).")


# ===== 2: nhịp tra masothue.com NGẪU NHIÊN 6–7 giây mỗi MST (như người dò thật). =====
class _ThoiGianGia:
    def __init__(self):
        self.bay_gio = 1_000_000.0
        self.da_ngu = []

    def time(self):
        return self.bay_gio

    def sleep(self, s):
        self.da_ngu.append(s)
        self.bay_gio += s


assert server._MASOTHUE_KHOANG_CACH_GIAY == (6.0, 7.0), f"got {server._MASOTHUE_KHOANG_CACH_GIAY}"
_time_goc = server.time
tg = _ThoiGianGia()
server.time = tg
try:
    server._MASOTHUE_TD["lan_mo_cuoi"] = 0.0
    server._masothue_cho_gian_cach()                 # lần đầu: không phải chờ
    for _ in range(20):
        server._masothue_cho_gian_cach()             # các lần sau: chờ 6-7 giây kể từ lần trước
finally:
    server.time = _time_goc
    server._MASOTHUE_TD["lan_mo_cuoi"] = 0.0
assert len(tg.da_ngu) == 20 and all(6.0 <= s <= 7.0 for s in tg.da_ngu), f"got {tg.da_ngu}"
assert len({round(s, 3) for s in tg.da_ngu}) > 1, "Khoảng chờ phải NGẪU NHIÊN (như người thật), không cố định."
print("PASS 2: giữa 2 lần tìm trên masothue.com chờ ngẫu nhiên 6–7 giây.")


# ===== 3: _prefetch_trang_thai_mst (trong export_excel) cập nhật TIẾN ĐỘ: tổng số MST, đã dò, tra
# được — và KHÔNG báo "Hết ngân sách" dù đã chạy rất lâu. =====
def _than_long(ten):
    i = src.index(f"    def {ten}(")
    dong = src[i:].split("\n")
    than = [dong[0]]
    for d in dong[1:]:
        if d.strip() and not d.startswith("        "):
            break
        than.append(d)
    return "\n".join(x[4:] if x.startswith("    ") else x for x in than)


ns = {"time": time, "_chuan_mst": server._chuan_mst, "_MST_NGAN_SACH_GIAY": server._MST_NGAN_SACH_GIAY,
      "_MST_TIEN_DO": {}, "_TRACUUNNT_TD": {"mst_dang_tra": ""}, "cid": 7,
      "_mst_status_local": {}, "_mst_fail_counter": [0], "_mst_bat_dau": time.time() - 100000,
      "_tlog": lambda m: None, "_tracuunnt_dat_lai_dem_loi": lambda: None}
thay_trong_luc_chay = []


def _tra_gia(mst, so_lan_that_bai_lien_tiep=None, chi_dung_cache=False):
    td = ns["_MST_TIEN_DO"].get(7) or {}
    thay_trong_luc_chay.append((td.get("dang_chay"), td.get("tong"), chi_dung_cache))
    if mst.endswith("5"):
        return {"trang_thai": "", "canh_bao": None, "ly_do_loi": "lỗi"}
    return {"trang_thai": "Đang hoạt động", "canh_bao": False}


ns["_tra_cuu_trang_thai_mst"] = _tra_gia
exec(_than_long("_lay_trang_thai_mst_cached"), ns)
exec(_than_long("_prefetch_trang_thai_mst"), ns)
ns["_prefetch_trang_thai_mst"]("BK Mua vào", ["0300000001", "0300000002", "0300000003", "0300000004",
                                               "0300000005"])
assert thay_trong_luc_chay and all(d is True and t == 5 for d, t, _c in thay_trong_luc_chay), thay_trong_luc_chay
assert not any(c for _d, _t, c in thay_trong_luc_chay), (
    "Đã bỏ giới hạn thời gian -> không MST nào bị 'Hết ngân sách' dù lượt đã chạy rất lâu.")
td = ns["_MST_TIEN_DO"][7]
assert td["dang_chay"] is False and td["tong"] == 5 and td["da_xong"] == 5 and td["tra_duoc"] == 4, td
print("PASS 3: tiến độ ghi đúng tổng số MST / đã dò / tra được; không còn 'Hết ngân sách thời gian'.")

# ===== 4: /api/tra-mst-tien-do/{cid}: đang dò MST nào (MST Chrome ẩn ĐANG thực sự tra) và ước thời
# gian còn lại (theo tốc độ đo thực tế khi đã dò >= 3 MST, chưa đủ thì ~6,5 giây/MST). =====
_goc_td = dict(server._TRACUUNNT_TD)
try:
    server._MST_TIEN_DO[7] = {"dang_chay": True, "nhan": "BK Mua vào", "tong": 100, "da_xong": 10,
                              "tra_duoc": 9, "dang_tra": "0300000011", "bat_dau": time.time() - 70}
    server._TRACUUNNT_TD["mst_dang_tra"] = "0312345678"
    kq = server.tra_mst_tien_do(7)
    assert kq["dang_tra"] == "0312345678" and kq["tong"] == 100 and kq["da_xong"] == 10, kq
    assert 600 <= kq["con_lai_giay"] <= 640, f"90 MST x ~7s đo được -> ~630s — got {kq['con_lai_giay']}"
    server._MST_TIEN_DO[7].update(da_xong=1, bat_dau=time.time() - 2)
    assert server.tra_mst_tien_do(7)["con_lai_giay"] == round(99 * 6.5)
    kq_trong = server.tra_mst_tien_do(424242)
    assert kq_trong["dang_chay"] is False and kq_trong["tong"] == 0
finally:
    server._MST_TIEN_DO.pop(7, None)
    server._TRACUUNNT_TD.update(_goc_td)
print("PASS 4: endpoint tiến độ trả MST đang dò và ước thời gian còn lại.")

# ===== 5: MST đang dò được ghi NGAY khi Chrome ẩn bắt đầu tra (cả masothue.com lẫn tracuunnt) —
# các luồng dò song song xếp hàng dùng chung 1 Chrome. =====
for ten in ("_tra_cuu_mst_qua_masothue_trinh_duyet", "_tra_cuu_mst_qua_tracuunnt_trinh_duyet"):
    i = src.index(f"def {ten}(")
    than = src[i:src.index("\ndef ", i + 10)]
    assert 'with _TRACUUNNT_TD["lock"]:' in than and '_TRACUUNNT_TD["mst_dang_tra"] = mst_c' in than, ten
    assert than.index('with _TRACUUNNT_TD["lock"]:') < than.index('_TRACUUNNT_TD["mst_dang_tra"] = mst_c'), ten
print("PASS 5: MST đang dò được ghi đúng lúc Chrome ẩn bắt đầu tra (sau khi giữ khoá trình duyệt).")

print("\nALL DONE")
