import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Yêu cầu: bảng kê thô từ hệ thống Thuế là NGUỒN DUY NHẤT để đối chiếu/xử lý; KHÔNG dò đi dò lại nhiều lần (mất thời gian).
# Lấy 1 lần -> kiểm tra đủ/chính xác -> chỉ tải đúng phần thiếu/lệch so với file đã tải.
src = open(os.path.join(os.path.dirname(server.__file__), "server.py"), encoding="utf-8").read()

for ten in ("_query_one_range_on_dinh", "_ban_sao_phien_moi", "_xac_minh_hoa_don_bi_sot", "_doi_soat_bang_ke_tho", "MTT_SO_LAN_DO"):
    assert ten not in src, f"{ten} phải bỏ (không dò/đối soát nhiều lần)"
qi = src[src.index("    def query_invoices("):src.index("    def _toan_ky_rong(")]
assert qi.count("self._query_one_range(") == 2
print("PASS 1: bỏ dò nhiều lần/phiên mới/xác minh từng HĐ/đối soát vòng 2; mỗi tháng chỉ lấy 1 lần.")


def hd(so, ngay="2026-09-10T00:00:00", mst="0318808536"):
    return {"khhdon": "C26MCF", "shdon": so, "nbmst": mst, "tdlap": ngay}


ok, mt = server._kiem_tra_bang_ke_tho([hd(str(n)) for n in range(1, 24)], "01/09/2026", "30/09/2026", 23)
assert ok and "23 HĐ" in mt and "đúng tổng Thuế báo" in mt
ok, mt = server._kiem_tra_bang_ke_tho([hd(str(n)) for n in range(1, 19)], "01/09/2026", "30/09/2026", 23)
assert not ok and "thiếu 5" in mt
ok, mt = server._kiem_tra_bang_ke_tho([hd("1"), hd("01")], "01/09/2026", "30/09/2026", 2)
assert not ok and "trùng khoá" in mt
ok, mt = server._kiem_tra_bang_ke_tho([hd("1", ngay="2026-10-02T00:00:00"), dict(hd("2"), nbmst="")], "01/09/2026", "30/09/2026", 2)
assert not ok and "ngoài kỳ" in mt and "thiếu trường" in mt
print("PASS 2: kiểm tra bảng kê thô: đủ so với tổng Thuế báo, không trùng khoá, đủ trường, trong kỳ.")

i_kt = src.index("_ok_bk, _mt_bk = _kiem_tra_bang_ke_tho(")
assert src.index("# CHỈ xóa dữ liệu CŨ của đúng loại này NGAY TRƯỚC KHI lưu") > i_kt
assert "đối chiếu bảng kê thô với file đã tải" in src and "chỉ tải đúng phần thiếu/lệch" in src
print("PASS 3: kiểm tra bảng kê thô chạy trước khi lưu; có dòng tổng kết đối chiếu với file đã tải (chỉ tải phần thiếu/lệch).")
print("ALL DONE")
