import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: "🚀 Import tự động toàn bộ vào MISA" (_misa_import_tu_dong)
phải TỰ THỬ LẠI đúng 1 lần khi bước "Nhập/Không qua kho/Dịch vụ vào MISA"
(bước 4) còn bỏ qua chứng từ vì THIẾU MÃ HÀNG trong MISA — chạy lại Danh mục
Hàng hóa/NVL rồi ghi lại Mua hàng, để những hóa đơn CHỈ TOÀN sản phẩm MỚI
(chưa kịp có mã trong MISA lúc bước 4 chạy) vẫn được ghi nốt, KHÔNG cần
người dùng tự phát hiện rồi bấm lại từng nút.

Đúng ca thật người dùng báo cáo + yêu cầu: "hãy chỉnh lại import toàn bộ
vào misa phần mềm sẽ xử lý các hoá đơn thiếu đó luôn" — 4/7 hóa đơn cùng 1
NCC (đã có sẵn trong MISA) bị bỏ qua HOÀN TOÀN vì toàn sản phẩm mới chưa
có mã hàng trong MISA."""
import sys
sys.path.insert(0, _REPO_ROOT)
import server


goi_mua_hang_nk = {"lan": 0}


def fake_ghi_mua_hang(cid, database, loai, preview=True, ghi_de=False):
    if loai == "nk":
        goi_mua_hang_nk["lan"] += 1
        if goi_mua_hang_nk["lan"] == 1:
            # LẦN ĐẦU: 2 chứng từ bị bỏ qua vì thiếu mã hàng (sản phẩm mới).
            return {"so_chungtu": 3, "so_dong": 10, "so_trung": 0,
                    "so_bo_qua_ncc": 0, "so_bo_qua_mahang": 2, "danh_sach": []}
        # LẦN 2 (SAU KHI đã "thử lại" chạy lại Danh mục Hàng hóa): thành công hết.
        return {"so_chungtu": 2, "so_dong": 8, "so_trung": 3,
                "so_bo_qua_ncc": 0, "so_bo_qua_mahang": 0, "danh_sach": []}
    return {"so_chungtu": 0, "so_dong": 0, "so_trung": 0,
            "so_bo_qua_ncc": 0, "so_bo_qua_mahang": 0, "danh_sach": []}


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
    kq = server._misa_import_tu_dong(1, "TESTDB", preview=False, ghi_de=False)
finally:
    for name, fn in originals.items():
        setattr(server, name, fn)

ten_buoc = [b["ten"] for b in kq["cac_buoc"]]
print("Các bước đã chạy:", ten_buoc)

assert goi_mua_hang_nk["lan"] == 2, (
    f"_misa_ghi_mua_hang('nk') phải được gọi ĐÚNG 2 LẦN (lần đầu bỏ qua vì thiếu mã hàng, lần 2 "
    f"'thử lại' sau khi Danh mục đã bổ sung) — được gọi {goi_mua_hang_nk['lan']} lần")
assert "4a (thử lại). Nhập kho vào MISA" in ten_buoc, (
    f"Phải có bước 'thử lại' Nhập kho vào MISA sau khi phát hiện thiếu mã hàng ở bước 4a — được {ten_buoc}")
assert "3a (thử lại). Danh mục Hàng hóa" in ten_buoc, (
    f"Phải chạy lại Danh mục Hàng hóa TRƯỚC khi thử ghi lại Mua hàng — được {ten_buoc}")
i_3a2 = ten_buoc.index("3a (thử lại). Danh mục Hàng hóa")
i_4a2 = ten_buoc.index("4a (thử lại). Nhập kho vào MISA")
assert i_3a2 < i_4a2, "Bước Danh mục 'thử lại' phải chạy TRƯỚC bước Nhập kho 'thử lại'"
buoc_4a2 = next(b for b in kq["cac_buoc"] if b["ten"] == "4a (thử lại). Nhập kho vào MISA")
assert buoc_4a2["ket_qua"]["so_bo_qua_mahang"] == 0, (
    f"Sau khi thử lại, không còn chứng từ nào bị bỏ qua vì thiếu mã hàng — được {buoc_4a2}")
print("PASS: Import tự động toàn bộ TỰ THỬ LẠI đúng 1 lần (chạy lại Danh mục Hàng hóa/NVL rồi ghi "
      "lại Mua hàng) khi phát hiện chứng từ bị bỏ qua vì thiếu mã hàng — không cần người dùng tự "
      "phát hiện rồi bấm lại từng nút.")

print("\nTẤT CẢ TEST PASS")
