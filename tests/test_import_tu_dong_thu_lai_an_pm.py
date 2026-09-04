import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: "🚀 Import tự động toàn bộ vào MISA" (_misa_import_tu_dong,
mặc định ghi_de=False — đúng thiết kế, tránh xóa nhầm dữ liệu THẬT khi chạy
hàng loạt không giám sát) phải TỰ chạy lại bước Mua hàng với ghi_de=True ÉP
BẬT (chỉ cho retry này, không đổi mặc định) khi bước 4 phát hiện chứng từ
khớp PUInvoice nhưng ẨN khỏi màn Mua hàng MISA, ĐÃ XÁC NHẬN đúng nguồn gốc
do chính phần mềm tạo (xem _hd_da_co_hien_ro) — không cần người dùng tự bấm
"Ghi đè" tay sau khi chạy "Import tự động toàn bộ".

Đúng ca thật người dùng báo cáo (2 lần liên tiếp): hóa đơn "biến mất" khỏi
MISA vì bản ghi lỗi/ẩn không được tự dọn khi chạy hàng loạt (ghi_de=False
mặc định) — "hãy chỉnh lại import tự động toàn bộ vào misa fix lỗi trên
để ko bị import thiếu nữa"."""
import sys
sys.path.insert(0, _REPO_ROOT)
import server


goi_mua_hang_nk = []   # ghi lại (ghi_de) của mỗi lần gọi cho loai='nk'


def fake_ghi_mua_hang(cid, database, loai, preview=True, ghi_de=False):
    if loai == "nk":
        goi_mua_hang_nk.append(ghi_de)
        if len(goi_mua_hang_nk) == 1:
            # LẦN ĐẦU (ghi_de=False, mặc định "Import tự động toàn bộ"): 2
            # chứng từ khớp PUInvoice nhưng ẨN, đã xác nhận đúng của phần
            # mềm nhưng KHÔNG được tự dọn vì ghi_de đang tắt.
            return {"so_chungtu": 1, "so_dong": 5, "so_trung": 3,
                    "so_bo_qua_ncc": 0, "so_bo_qua_mahang": 0, "so_bo_qua_an_pm": 2,
                    "danh_sach": []}
        # LẦN 2 (retry ép ghi_de=True): đã tự dọn xong, ghi lại thành công.
        return {"so_chungtu": 3, "so_dong": 10, "so_trung": 3,
                "so_bo_qua_ncc": 0, "so_bo_qua_mahang": 0, "so_bo_qua_an_pm": 0,
                "danh_sach": []}
    return {"so_chungtu": 0, "so_dong": 0, "so_trung": 0,
            "so_bo_qua_ncc": 0, "so_bo_qua_mahang": 0, "so_bo_qua_an_pm": 0, "danh_sach": []}


def fake_ghi_mua_hang_dv(cid, database, preview=True, ghi_de=False):
    return {"so_chungtu": 0, "so_dong": 0, "so_trung": 0,
            "so_bo_qua_ncc": 0, "so_bo_qua_mahang": 0, "danh_sach": []}


def fake_ok(*a, **kw):
    return {"ok": True}


def fake_nhap_lieu_get(cid, loai):
    return {"header": ["Nợ", "Tên hàng hóa/dịch vụ", "ĐVT"], "rows": [["1561", "Sản phẩm A", "Cái"]]}


def fake_gen_danh_muc(cid, loai, header, rows):
    if loai not in ("hh", "nvl"):
        raise server.HTTPException(400, "Không có mã nào thuộc danh mục này trong Bảng kê Đầu vào.")
    return ([["HH00001-8", "Sản phẩm A", "Cái", "8", "SảnphẩmACái", 1, 100000, 100000, "1", "01/06/2026", "HH"]], 1)


originals = {}
for name, fn in [
    ("_misa_ghi_khncc", fake_ok),
    ("_misa_ghi_ban_hang", fake_ok),
    ("nhap_lieu_get", fake_nhap_lieu_get),
    ("_gen_danh_muc", fake_gen_danh_muc),
    ("_luu_danh_muc", lambda *a, **kw: None),
    ("_misa_ghi_hang_hoa", fake_ok),
    ("_misa_ghi_mua_hang", fake_ghi_mua_hang),
    ("_misa_ghi_mua_hang_dv", fake_ghi_mua_hang_dv),
    ("_misa_ghi_tang_ccdc", fake_ok),
    ("_misa_ghi_tang_tscd", fake_ok),
    ("_misa_phan_bo_ccdc", fake_ok),
    ("_misa_khau_hao_tscd", fake_ok),
    ("_misa_tao_to_khai_khau_tru_gtgt", fake_ok),
    ("_misa_doi_chieu_import_toan_bo",
     lambda cid, database: {"ban_hang": {"khop": 0, "tong_hd_nguon": 0, "thieu": [], "lech": []},
                            "mua_hang": {"khop": 0, "tong_hd_nguon": 0, "thieu": [], "lech": []}}),
]:
    originals[name] = getattr(server, name)
    setattr(server, name, fn)

try:
    # ghi_de=False — ĐÚNG mặc định thật của nút "🚀 Import tự động toàn bộ".
    kq = server._misa_import_tu_dong(1, "TESTDB", preview=False, ghi_de=False)
finally:
    for name, fn in originals.items():
        setattr(server, name, fn)

ten_buoc = [b["ten"] for b in kq["cac_buoc"]]
print("Các bước đã chạy:", ten_buoc)
print("ghi_de mỗi lần gọi _misa_ghi_mua_hang('nk'):", goi_mua_hang_nk)

assert goi_mua_hang_nk == [False, True], (
    f"_misa_ghi_mua_hang('nk') phải được gọi ĐÚNG 2 LẦN: lần đầu ghi_de=False (đúng mặc định gốc), "
    f"lần 2 (thử lại tự dọn bản ẩn) PHẢI ép ghi_de=True — được {goi_mua_hang_nk}")
assert "4a (tự dọn bản ẩn). Nhập kho vào MISA" in ten_buoc, (
    f"Phải có bước 'tự dọn bản ẩn' sau khi phát hiện so_bo_qua_an_pm > 0 ở bước 4a — được {ten_buoc}")
buoc_retry = next(b for b in kq["cac_buoc"] if b["ten"] == "4a (tự dọn bản ẩn). Nhập kho vào MISA")
assert buoc_retry["ket_qua"]["so_bo_qua_an_pm"] == 0 and buoc_retry["ket_qua"]["so_chungtu"] == 3, (
    f"Sau khi tự dọn, chứng từ phải ghi lại thành công — được {buoc_retry}")
print("PASS: Import tự động toàn bộ (mặc định ghi_de=False) TỰ chạy lại Mua hàng với ghi_de=True ÉP "
      "BẬT (chỉ cho lượt thử lại này) khi phát hiện chứng từ ẩn đã xác nhận đúng nguồn gốc phần mềm — "
      "không còn cần người dùng tự bấm 'Ghi đè' tay sau khi chạy tự động.")

print("\nTẤT CẢ TEST PASS")
