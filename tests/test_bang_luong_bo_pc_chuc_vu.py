import os
import sys
import tempfile

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server
import openpyxl

# Yêu cầu: "bỏ cột phụ cấp chức vụ luôn" khỏi Bảng Lương (phụ cấp chức vụ có tính BHXH nên không đưa vào bảng lương này).

TS = server._luong_chuan_tham_so(None, 2025)

# 1: dòng có pc_chuc_vu (dữ liệu cũ/API) -> bị bỏ qua, không cộng vào lương/chi phí/thu nhập chịu thuế
a = server._luong_tinh_dong({"luong_cb": 6_000_000, "ngay_cong": 26, "dong_bh": 1}, TS, "05")
b = server._luong_tinh_dong({"luong_cb": 6_000_000, "ngay_cong": 26, "dong_bh": 1, "pc_chuc_vu": 500_000}, TS, "05")
assert a["chi_phi_luong"] == b["chi_phi_luong"] == 6_000_000 and a["tn_chiu_thue"] == b["tn_chiu_thue"] and a["tt_luong"] == b["tt_luong"]
assert "pc_chuc_vu" not in b and "tt_pc_chuc_vu" not in b and "pc_chuc_vu" not in server._luong_chuan_dong_nhap({"pc_chuc_vu": 5})
print("PASS 1: phụ cấp chức vụ không còn tính vào bảng lương (kể cả dữ liệu cũ có sẵn số này).")

# 2: nạp từ Danh Sách Nhân Viên: bỏ qua cột PC Chức vụ
hd = ["Mã NV", "Họ và tên", "Chức vụ", "Lương Cơ bản", "PC Tiền cơm", "PC Xăng xe", "PC Chức vụ", "PC Điện thoại", "PC Trang phục"]
rows = server._luong_dong_tu_nhan_vien(hd, [["1", "A", "KD", 5_310_000, 700_000, 500_000, 500_000, 500_000, 400_000]])
assert rows[0]["muc_xang"] == 500_000 and rows[0]["muc_dt"] == 500_000 and "pc_chuc_vu" not in rows[0]
assert server._luong_tinh_dong(rows[0], TS, "05")["chi_phi_luong"] == 5_310_000 + 700_000 + 500_000 + 500_000 + 400_000
print("PASS 2: nạp từ Danh Sách Nhân Viên không lấy PC Chức vụ.")

# 3: Excel xuất không còn cột PC Chức vụ; đọc lại file cũ có cột này không lỗi; tổng khớp
_dl = server.DOWNLOAD_DIR
server.DOWNLOAD_DIR = tempfile.mkdtemp()
try:
    assert not any(c[0] == "pc_chuc_vu" for c in server._LUONG_COT_EXCEL)
    duong, _ = server._luong_xuat_excel(2025, TS, {"05": [dict(rows[0], ngay_lam="")]})
    ws = openpyxl.load_workbook(duong).active
    tieu = " ".join(str(c.value or "") for c in ws[1]) + " " + " ".join(str(c.value or "") for c in ws[2])
    assert "PC Chức vụ" not in tieu
    t, loi = server._luong_doc_excel(openpyxl.load_workbook(duong, data_only=True), openpyxl.load_workbook(duong))
    assert loi == [] and t["05"][0]["muc_xang"] == 500_000 and "pc_chuc_vu" not in t["05"][0]
finally:
    server.DOWNLOAD_DIR = _dl
print("PASS 3: Excel không còn cột PC Chức vụ, đọc lại bình thường.")
print("\nALL DONE")
