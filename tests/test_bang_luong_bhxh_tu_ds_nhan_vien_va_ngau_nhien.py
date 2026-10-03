import os
import sys
import json
import random
import sqlite3
import tempfile
import datetime

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Yêu cầu người dùng (Bảng Lương):
#  1) "Trong Danh Sách Nhân Viên thêm cột tick đóng BHXH và 'Tháng/Năm vào làm' là thời gian bắt đầu đóng BHXH.
#     Phần mềm dựa vào cột này để tự động tick đóng; lao động nào không tick thì không đóng BHXH."
#  2) "thưởng bán hàng và tăng ca hãy chỉnh RANDOM nhiều mức cho từng người để nhìn tự nhiên hơn, đừng phân bổ đều".

# ===== 1a: cột mới trong NV_HEADERS + nhận diện khi import. =====
assert "Đóng BHXH" in server.NV_HEADERS and server.NV_HEADERS.index("Đóng BHXH") == server.NV_HEADERS.index("Tháng/Năm vào làm") + 1
assert server._NV_TU_KHOA[0][0] == "Đóng BHXH"
print("PASS 1a: Danh Sách Nhân Viên có cột 'Đóng BHXH' ngay sau 'Tháng/Năm vào làm'.")

# ===== 1b: ô tick; 'Tháng/Năm vào làm' -> tháng bắt đầu đóng (vào làm từ ngày 18 trở đi tính từ tháng sau). =====
tk = server._nv_co_tick
assert [tk(v) for v in ("x", "X", "1", 1, True, "có", "Có", "true", "✓")] == [True] * 9
assert [tk(v) for v in ("", None, 0, "0", False, "không", "Không", "false", "k")] == [False] * 9
bd = server._luong_bat_dau_bhxh
assert bd("10/2024") == (2024, 10) and bd("1/10/2024") == (2024, 10) and bd("01-10-2024") == (2024, 10)
assert bd("2024-10") == (2024, 10) and bd("2024-10-05") == (2024, 10) and bd(datetime.datetime(2024, 3, 5)) == (2024, 3)
assert bd("20/10/2024") == (2024, 11), "Vào làm 20/10 chỉ còn 12 ngày -> chưa đóng tháng 10"
assert bd("18/10/2024") == (2024, 10) and bd("31/12/2024") == (2025, 1)
assert bd("") is None and bd(None) is None and bd("abc") is None and bd("13/13/2024") is None
f = server._luong_dong_bh_tu_nv
assert f(True, "10/2024", 2024, 9) == 0 and f(True, "10/2024", 2024, 10) == 1 and f(True, "10/2024", 2025, 1) == 1
assert f(False, "10/2024", 2024, 12) == 0, "Không tick -> không đóng dù đã tới tháng"
assert f(True, "", 2024, 1) == 1 and f(True, "10/2024") == 1, "Không có tháng vào làm/không có tháng tính -> chỉ xét tick"
print("PASS 1b: tick + tháng bắt đầu đóng BHXH (vào làm sau ngày 18 tính từ tháng sau).")

# ===== 1c: dựng dòng lương từ Danh Sách Nhân Viên theo tháng. =====
hdr = ["STT", "Mã NV", "Họ và tên", "Tháng/Năm vào làm", "Đóng BHXH", "Chức vụ", "Lương Cơ bản", "PC Tiền cơm"]
rows = [[1, "1", "A tick, vào làm 10/2024", "10/2024", "x", "KD", "5.310.000", 700000],
        [2, "2", "B không tick", "01/2024", "", "KD", 5310000, 700000],
        [3, "3", "C tick, chưa nhập ngày", "", "1", "KD", 5310000, 700000]]
kq = {m: [x["dong_bh"] for x in server._luong_dong_tu_nhan_vien(hdr, rows, 0, 2024, m)] for m in (9, 10, 12)}
assert kq == {9: [0, 0, 1], 10: [1, 0, 1], 12: [1, 0, 1]}, kq
assert [x["dong_bh"] for x in server._luong_dong_tu_nhan_vien(hdr, rows)] == [1, 0, 1]        # không có tháng: chỉ theo tick
# danh sách cũ chưa có cột Đóng BHXH -> coi như đều đóng (giữ hành vi cũ)
cu = server._luong_dong_tu_nhan_vien([h for h in hdr if h != "Đóng BHXH"], [[r[0], r[1], r[2], r[3], r[5], r[6], r[7]] for r in rows], 0, 2024, 12)
assert [x["dong_bh"] for x in cu] == [1, 1, 1]
assert server._luong_dong_tu_nhan_vien(hdr, rows)[0]["luong_cb"] == 5_310_000, "'5.310.000' (định dạng có dấu chấm) vẫn đọc đúng"
print("PASS 1c: dòng lương lấy tick + tháng bắt đầu đóng theo từng tháng; danh sách cũ giữ nguyên; '5.310.000' đọc đúng.")

# ===== 1d: API tu-nhan-vien có tham số tháng. =====
_duong = tempfile.mktemp(suffix=".sqlite3")
def _db_tam():
    c = sqlite3.connect(_duong); c.row_factory = sqlite3.Row; return c
_goc = server.db
server.db = _db_tam
try:
    c0 = _db_tam()
    c0.execute("CREATE TABLE nhap_lieu (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, loai TEXT, "
               "header_json TEXT, rows_json TEXT, updated_at TEXT, UNIQUE(company_id, loai))")
    c0.execute("INSERT INTO nhap_lieu (company_id, loai, header_json, rows_json) VALUES (1,'nv',?,?)", (json.dumps(hdr), json.dumps(rows)))
    c0.commit(); c0.close()
    assert [x["dong_bh"] for x in server.bang_luong_tu_nhan_vien(1, nam=2024, thang=9)["rows"]] == [0, 0, 1]
    assert [x["dong_bh"] for x in server.bang_luong_tu_nhan_vien(1, nam=2024, thang=11)["rows"]] == [1, 0, 1]
    assert [x["dong_bh"] for x in server.bang_luong_tu_nhan_vien(1, nam=2024)["rows"]] == [1, 0, 1]
finally:
    server.db = _goc
print("PASS 1d: /tu-nhan-vien?thang=N trả dong_bh theo từng tháng.")

# ===== 2: kế hoạch chi phí lương: người KHÔNG được đóng BHXH chỉ làm < 14 ngày; người được đóng làm đủ công. =====
TS = server._luong_chuan_tham_so(None, 2024)
base = {"luong_cb": 5_310_000, "tien_com": 700_000, "muc_xang": 500_000, "pc_chuc_vu": 500_000, "muc_dt": 500_000, "trang_phuc": 400_000}
pool = [server._luong_chuan_dong_nhap(dict(base, ma=str(i), ten=f"NV{i}", dong_bh=1 if i <= 4 else 0)) for i in range(1, 8)]   # 4 được đóng, 3 không
th, tom = server._luong_ke_hoach(pool, 2024, 11, 12, 60_000_000, None, rng=random.Random(3))
assert sum(r["chi_phi_luong"] for rows_ in th.values() for r in rows_) == 60_000_000
for rows_ in th.values():
    for r in rows_:
        if r["dong_bh"] == 1:
            assert r["ngay_lam_hd"] == r["ngay_cong_hd"] and int(r["ma"]) <= 4, "Người đủ công phải là người được đóng BHXH"
        else:
            assert r["ngay_cong_hd"] - r["ngay_lam_hd"] >= 14, "không đóng BHXH phải không lương từ 14 ngày làm việc"
# mục tiêu nhỏ: chỉ có người không được đóng BHXH ở đầu danh sách sử dụng trước cho phần làm < 14 ngày
pool2 = [server._luong_chuan_dong_nhap(dict(base, ma=str(i), ten=f"NV{i}", dong_bh=0 if i == 3 else 1)) for i in range(1, 5)]
th2, tom2 = server._luong_ke_hoach(pool2, 2024, 12, 12, 3_000_000, None, rng=random.Random(1))
assert th2["12"][0]["ma"] == "3", "Người không được đóng BHXH được dùng làm người làm < 14 ngày trước"
assert all(r["dong_bh"] == 0 and r["ngay_cong_hd"] - r["ngay_lam_hd"] >= 14 for r in th2["12"])
# pool theo THÁNG (hàm): người vào làm 10/2024 chưa được đóng ở tháng 9
def pool_thang(t):
    return server._luong_dong_tu_nhan_vien(hdr, [[1, "1", "A", "10/2024", "x", "KD", 5310000, 700000]], 0, 2024, int(t))
th3, _ = server._luong_ke_hoach(pool_thang, 2024, 9, 10, 20_000_000, None, rng=random.Random(2))
assert th3["09"][0]["dong_bh"] == 0 and th3["09"][0]["ngay_cong_hd"] - th3["09"][0]["ngay_lam_hd"] >= 14 and th3["10"][0]["dong_bh"] == 1
print("PASS 2: người không được đóng BHXH chỉ làm < 14 ngày; người được đóng làm đủ công; tick theo từng tháng.")

# ===== 3: thưởng bán hàng + tăng ca RANDOM từng người (không chia đều), làm tròn nghìn đồng, tổng vẫn đúng từng đồng. =====
pool7 = [server._luong_chuan_dong_nhap(dict(base, ma=str(i), ten=f"NV{i}")) for i in range(2, 9)]
th, tom = server._luong_ke_hoach(pool7, 2024, 11, 12, 120_000_000, None, 60, rng=random.Random(11))
assert sum(r["chi_phi_luong"] for rows_ in th.values() for r in rows_) == 120_000_000 and tom["tong_thue"] == 0
thuong = [r["thuong_bh"] for rows_ in th.values() for r in rows_]
tc = [r["tang_ca"] for rows_ in th.values() for r in rows_]
assert len(set(thuong)) >= 10 and len(set(tc)) >= 10, "Mỗi người một mức khác nhau (không chia đều)"
assert max(thuong) > 2 * min(thuong) and max(tc) > 2 * min(tc), "Chênh lệch giữa người có mức cao / thấp"
le = [x for x in thuong + tc if x % 1000 != 0]
assert len(le) <= 2 * 1 + 2, f"Chỉ phần lẻ dồn cho khớp tổng mới không tròn nghìn — got {le}"
assert all(r["thue_tncn"] == 0 and r["tn_tinh_thue"] <= 0 for rows_ in th.values() for r in rows_), "Vẫn dưới ngưỡng nộp thuế"
assert all(r["gio_tang_ca"] <= 40 + 1e-9 for rows_ in th.values() for r in rows_)
# cùng seed -> cùng kết quả (kiểm thử/tái hiện được); khác seed -> khác; không seed -> mỗi lần tính một khác
kq = lambda seed: json.dumps([[r["thuong_bh"], r["tang_ca"]] for rows_ in server._luong_ke_hoach(pool7, 2024, 11, 12, 120_000_000, None, 60, rng=random.Random(seed))[0].values() for r in rows_])
assert kq(5) == kq(5) and kq(5) != kq(6)
a = server._luong_ke_hoach(pool7, 2024, 11, 12, 120_000_000, None, 60)[0]
b = server._luong_ke_hoach(pool7, 2024, 11, 12, 120_000_000, None, 60)[0]
assert json.dumps(a, sort_keys=True) != json.dumps(b, sort_keys=True), "Bấm Tính lần nữa ra phương án khác"
# nhiều mục tiêu: luôn khớp tổng, không âm
for muc in (20_000_000, 60_000_000, 90_000_000, 300_000_000):
    th, _ = server._luong_ke_hoach(pool7, 2024, 10, 12, muc, None, 50, rng=random.Random(muc))
    assert sum(r["chi_phi_luong"] for rows_ in th.values() for r in rows_) == muc
    assert all(r["thuong_bh"] >= 0 and r["tang_ca"] >= 0 for rows_ in th.values() for r in rows_)
print("PASS 3: thưởng/tăng ca ngẫu nhiên từng người (tròn nghìn), tổng đúng từng đồng, không thuế, tăng ca <= 40 giờ.")

# ===== 4: import file nhân viên không có cột tick -> mặc định tick (đóng). =====
src = open(os.path.join(_REPO_ROOT, "server.py"), encoding="utf-8").read()
assert 'dong_moi[NV_HEADERS.index("Đóng BHXH")] = "x"' in src
print("PASS 4: import Danh Sách Nhân Viên từ file không có cột tick -> mặc định tick.")

# ===== 5: người làm < 14 ngày: SỐ NGÀY LÀM NGẪU NHIÊN mỗi người một khác; thưởng + tăng ca chia cho NHIỀU người. =====
kb = {"luong_cb": 5_310_000, "tien_com": 700_000, "muc_xang": 500_000, "pc_chuc_vu": 500_000, "muc_dt": 500_000, "trang_phuc": 400_000}
khong = [server._luong_chuan_dong_nhap(dict(kb, ma=str(i), ten=f"NV{i}", dong_bh=0)) for i in range(2, 9)]   # 7 người, không ai được đóng BHXH
for muc, ky_vong_tuan_thu in ((24_000_000, True), (60_000_000, False), (117_000_000, False)):
    th, tom = server._luong_ke_hoach(khong, 2024, 10, 11, muc, None, 50, rng=random.Random(muc))
    assert sum(r["chi_phi_luong"] for rows_ in th.values() for r in rows_) == muc
    for rows_ in th.values():
        assert all(r["dong_bh"] == 0 and r["thoi_vu"] and 1 <= r["ngay_lam_hd"] <= 13 for r in rows_)
        nguoi_co_thuong = sum(1 for r in rows_ if r["thuong_bh"] > 0 or r["tang_ca"] > 0)
        assert nguoi_co_thuong >= len(rows_) - 1 and nguoi_co_thuong >= 2, "Thưởng/tăng ca chia cho nhiều người, không dồn 1 người"
        if muc != 117_000_000:
            assert max(r["thuong_bh"] for r in rows_) < 0.8 * sum(r["thuong_bh"] for r in rows_), "Không có ai chiếm gần hết thưởng"
    if ky_vong_tuan_thu:
        assert tom["tong_thue"] == 0, "Đủ sức chứa -> mỗi người dưới ngưỡng khấu trừ 10%"
# số ngày khác nhau giữa người với người (nhiều mức), qua nhiều lần tính
so_muc = set()
for seed in range(20):
    th, _ = server._luong_ke_hoach(khong, 2024, 10, 10, 60_000_000, None, 50, rng=random.Random(seed))
    so_muc |= {r["ngay_lam_hd"] for r in th["10"]}
    assert len({r["ngay_lam_hd"] for r in th["10"]}) >= 3, "Trong 1 tháng có nhiều mức số ngày khác nhau"
assert len(so_muc) >= 8 and min(so_muc) <= 4 and max(so_muc) >= 11, so_muc
# mục tiêu vừa phải: người làm ít ngày (dưới ngưỡng thuế) có số ngày khác nhau
th, tom = server._luong_ke_hoach(khong, 2024, 10, 11, 24_000_000, None, 50, rng=random.Random(2))
assert len({r["ngay_lam_hd"] for r in th["10"]}) >= 2 and tom["tong_thue"] == 0
print("PASS 5: số ngày làm ngẫu nhiên nhiều mức (vd 3, 7, 12 ngày); thưởng + tăng ca chia cho nhiều người; tổng đúng.")

print("\nALL DONE")
