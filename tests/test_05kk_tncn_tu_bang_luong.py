import os, sys, json, sqlite3, tempfile, datetime
import xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Yêu cầu: kết xuất 05/KK-TNCN tự lấy số liệu từ Bảng Lương đã lưu; kỳ không có lương -> không phát sinh (0).
# Có khoảng ngày tra cứu hoá đơn (tu/den) -> luôn kê khai TRỌN QUÝ chứa ngày bắt đầu (cả nút kết xuất và tra cứu hàng loạt).
NS = {"t": "http://kekhaithue.gdt.gov.vn/TKhaiThue"}
tmp = tempfile.mkdtemp()
server.DOWNLOAD_DIR = tmp
server._get_desktop_dir = lambda: ""
server._open_file_local = lambda p: None
conn = sqlite3.connect(":memory:", check_same_thread=False); conn.row_factory = sqlite3.Row
conn.execute("CREATE TABLE companies (id INTEGER, ten TEXT, mst TEXT, dia_chi TEXT, ma_cqt_noi_nop TEXT, ten_cqt_noi_nop TEXT, nguoi_ky TEXT, export_dir TEXT, save_dir TEXT)")
conn.execute("INSERT INTO companies VALUES (5,'CTY THỬ','0318712827','1 Đường A','70123','Thuế cơ sở 12 TP.HCM','NGUYỄN A','','')")
class KhongDong:
    def __init__(self, c): self.c = c
    def execute(self, *a): return self.c.execute(*a)
    def commit(self): self.c.commit()
    def close(self): pass
server.db = lambda: KhongDong(conn)
server._luong_dam_bao_bang(conn)

base = {"chuc_vu": "KD", "tien_com": 0, "muc_xang": 0, "muc_dt": 0, "trang_phuc": 0}
a = dict(base, ma="1", ten="Hồ Thị A", luong_cb=40_000_000, so_npt=0, dong_bh=1)     # bị khấu trừ lũy tiến
b = dict(base, ma="2", ten="Trần Thị B", luong_cb=8_000_000, so_npt=0, dong_bh=1)     # dưới mức giảm trừ
pt = dict(base, ma="3", ten="Part C", part_time=1, luong_gio=30_000, gio_lam=40)        # part-time khấu trừ 10%
thang = {"07": [a, b], "08": [a, b, pt], "09": [a, b]}                                  # chỉ có quý 3
conn.execute("INSERT INTO bang_luong (company_id, nam, tham_so_json, thang_json, updated_at) VALUES (5, 2026, '{}', ?, '')", (json.dumps(thang),))

# 1) tổng hợp chỉ tiêu
ts, nhap, _c, _n = server._luong_doc_nam(5, 2026)
dong = [r for t in ("07", "08", "09") for r in server._luong_tinh_thang(nhap[t], ts, t, 2026)]
ct = server._tncn_05kk_tong_hop(dong)
tn = round(sum(r["tn_chiu_thue"] for r in dong))
thue = round(sum(r["thue_tru_luong"] for r in dong))
tn_kt = round(sum(r["tn_chiu_thue"] for r in dong if r["thue_tru_luong"] > 0))
assert thue > 0 and ct["ct16"] == 3 and ct["ct17"] == 2, ct
assert ct["ct18"] == ct["ct19"] == 2 and ct["ct20"] == 0, "A và part-time C bị khấu trừ; B thì không"
assert ct["ct21"] == ct["ct22"] == tn and ct["ct23"] == 0
assert ct["ct26"] == ct["ct27"] == tn_kt < tn and ct["ct28"] == 0
assert ct["ct29"] == ct["ct30"] == thue and ct["ct31"] == 0
assert server._tncn_05kk_tong_hop([]) is None
print("PASS 1: chỉ tiêu 05/KK tổng hợp đúng từ Bảng Lương (người LĐ, HĐLĐ, đã khấu trừ, TNCT, thuế).")

def doc(res):
    root = ET.parse(res["path"]).getroot()
    v = lambda tag: root.find(".//t:" + tag, NS).text
    return v

# 2) chọn tra cứu 1 tháng giữa quý (05/08 -> 20/08) -> tờ khai QUÝ 3 với số liệu cả quý
res = server._export_htkk_tncn_impl(5, ky="08/2026", tu="05/08/2026", den="20/08/2026", mo_file=0)
v = doc(res)
assert v("kieuKy") == "Q" and v("kyKKhai") == "3/2026", (v("kieuKy"), v("kyKKhai"))
assert v("kyKKhaiTuNgay") == "01/07/2026" and v("kyKKhaiDenNgay") == "30/09/2026"
assert "Q32026" in res["fname"] and res["phat_sinh"] is True
for k, val in ct.items():
    assert int(v(k)) == val, (k, v(k), val)
assert int(v("ct24")) == int(v("ct32")) == int(v("ct25_1")) == 0
assert "Bảng Lương" in res["canh_bao"] and "⚠" not in res["canh_bao"]
print("PASS 2: khoảng tra cứu 05/08–20/08 -> kê khai quý 3/2026, số liệu cả quý từ Bảng Lương.")

# 3) quý không có lương -> không phát sinh (mọi chỉ tiêu 0); ngày dạng ISO cũng nhận
res = server._export_htkk_tncn_impl(5, tu="2026-10-01", den="2026-10-31", mo_file=0)
v = doc(res)
assert v("kyKKhai") == "4/2026" and res["phat_sinh"] is False
assert all(int(v(k)) == 0 for k in ("ct16", "ct17", "ct18", "ct21", "ct26", "ct29"))
assert "KHÔNG PHÁT SINH" in res["canh_bao"]
print("PASS 3: quý không có lương -> tờ khai không phát sinh (0).")

# 4) khoảng ngày trải 2 quý -> lấy quý của ngày bắt đầu + cảnh báo
res = server._export_htkk_tncn_impl(5, tu="15/09/2026", den="15/10/2026", mo_file=0)
assert doc(res)("kyKKhai") == "3/2026" and "nhiều quý" in res["canh_bao"]
print("PASS 4: khoảng ngày trải 2 quý -> quý của ngày bắt đầu, có cảnh báo.")

# 5) tra cứu hàng loạt gọi cùng hàm với tu/den của khoảng tra cứu
src = open(os.path.join(os.path.dirname(server.__file__), "server.py"), encoding="utf-8").read()
assert 'export_htkk_tncn(cid, Response(), tu=(tu or ""), den=(den or "")' in src
print("PASS 5: tra cứu hàng loạt kết xuất 05/KK theo cùng khoảng tra cứu (cùng quy tắc theo quý).")
print("ALL DONE")
