import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: _xk_canh_bao_dau_ky phải phát hiện mã hàng vượt tồn ĐẦU
KỲ dù vẫn trong tồn Cuối kỳ (nên _xk_kiem_tra_vuot_ton — hard-block — không
bắt được) — đúng ca thật người dùng báo cáo: MISA từ chối ghi sổ "XK T7/2026"
với thông báo "Số lượng tồn trong kho <HH-HH> là: 122,00" cho mã HH00143-8,
dù báo cáo 'Tổng hợp tồn kho' của MISA cho thấy tồn Cuối kỳ tới 902 (122 đầu
kỳ + 780 nhập trong kỳ, có thể CHƯA được ghi sổ) — và _xk_kiem_tra_vuot_ton
(so tổng đã gán 537 với Cuối kỳ 902) không hề cảnh báo gì.

Dữ liệu số lấy ĐÚNG từ 2 file người dùng gửi:
  - TONG_HOP_TON_KHO.xlsx: HH00143-8 đầu kỳ=122, nhập=780, cuối kỳ=902.
  - XuatKho_T7.2026_...xlsx: tổng SL đã gán xuất cho HH00143-8 = 537."""
import sys
sys.path.insert(0, _REPO_ROOT)
import server


def test_doc_file_ton_kho_doc_dau_ky():
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Báo cáo"
    ws.append(["TỔNG HỢP TỒN KHO"])
    ws.append(["Kho: HH; Tháng 7 năm 2026"])
    ws.append([None, "Mã hàng", "Tên hàng", "ĐVT", "Đầu kỳ", None, "Nhập kho", None, "Xuất kho", None, "Cuối kỳ", None])
    ws.append([None, None, None, None, "Số lượng", "Giá trị", "Số lượng", "Giá trị", "Số lượng", "Giá trị", "Số lượng", "Giá trị"])
    ws.append(["Tên kho : HH (1 )"])
    ws.append([None, "HH00143-8", "Hạt nêm Heo Aji-ngon 3kgP13", "Thùng",
               122, 106361796, 780, 695714760, 0, 0, 902, 802076556])
    rows, danh_sach_kho = server._doc_file_ton_kho(wb)
    assert len(rows) == 1, f"Phải đọc được đúng 1 mã hàng — được {rows}"
    it = rows[0]
    assert it["ma"] == "HH00143-8"
    assert it["ton"] == 902, f"Tồn Cuối kỳ phải đọc đúng 902 — được {it['ton']}"
    assert it["dau_ky"] == 122, f"Tồn Đầu kỳ phải đọc đúng 122 (cột MỚI thêm) — được {it.get('dau_ky')}"
    print("PASS: _doc_file_ton_kho đọc đúng cả tồn Đầu kỳ lẫn Cuối kỳ.")
    return it


def test_canh_bao_dau_ky_khong_chan_vuot_ton():
    ton_rows = [{"ma": "HH00143-8", "ton": 902, "dau_ky": 122,
                 "kho_ro": True, "ton_kho_min": 902, "dau_ky_kho_min": 122}]
    giathanh_rows = [{"ma": "HH00143-8", "sl_kho": 537}]

    vuot = server._xk_kiem_tra_vuot_ton(ton_rows, giathanh_rows)
    assert vuot == [], (
        f"_xk_kiem_tra_vuot_ton (so Cuối kỳ) KHÔNG được chặn — 537 < 902 vẫn hợp lệ theo tổng tồn cả "
        f"kỳ — được {vuot}")

    canh_bao = server._xk_canh_bao_dau_ky(ton_rows, giathanh_rows)
    assert len(canh_bao) == 1 and canh_bao[0]["ma"] == "HH00143-8", (
        f"_xk_canh_bao_dau_ky PHẢI phát hiện HH00143-8 vượt tồn Đầu kỳ (537 > 122) — được {canh_bao}")
    assert canh_bao[0]["vuot_dau_ky"] == 537 - 122
    print("PASS: _xk_canh_bao_dau_ky cảnh báo đúng ca thật (537 > 122 đầu kỳ) mà "
          "_xk_kiem_tra_vuot_ton (so Cuối kỳ) hoàn toàn bỏ lọt.")


def test_canh_bao_dau_ky_khong_bao_trung_khi_da_vuot_ton_cuoi_ky():
    # Mã hàng ĐÃ bị _xk_kiem_tra_vuot_ton chặn cứng (vượt cả Cuối kỳ) không
    # cần cảnh báo trùng lặp ở _xk_canh_bao_dau_ky nữa.
    ton_rows = [{"ma": "MH999", "ton": 100, "dau_ky": 10,
                 "kho_ro": True, "ton_kho_min": 100, "dau_ky_kho_min": 10}]
    giathanh_rows = [{"ma": "MH999", "sl_kho": 150}]
    vuot = server._xk_kiem_tra_vuot_ton(ton_rows, giathanh_rows)
    assert len(vuot) == 1 and vuot[0]["ma"] == "MH999"
    canh_bao = server._xk_canh_bao_dau_ky(ton_rows, giathanh_rows)
    assert canh_bao == [], f"Mã đã bị chặn cứng (vượt cả Cuối kỳ) không cần cảnh báo trùng — được {canh_bao}"
    print("PASS: không cảnh báo trùng cho mã đã bị chặn cứng vượt tồn Cuối kỳ.")


def test_canh_bao_dau_ky_binh_thuong_khong_bao():
    # Số đã gán TRONG tồn Đầu kỳ -> hoàn toàn bình thường, không cảnh báo.
    ton_rows = [{"ma": "MH001", "ton": 500, "dau_ky": 400,
                 "kho_ro": True, "ton_kho_min": 500, "dau_ky_kho_min": 400}]
    giathanh_rows = [{"ma": "MH001", "sl_kho": 300}]
    canh_bao = server._xk_canh_bao_dau_ky(ton_rows, giathanh_rows)
    assert canh_bao == [], f"Số đã gán (300) < tồn Đầu kỳ (400) -> không cảnh báo — được {canh_bao}"
    print("PASS: không cảnh báo khi số đã gán vẫn trong tồn Đầu kỳ.")


it = test_doc_file_ton_kho_doc_dau_ky()
test_canh_bao_dau_ky_khong_chan_vuot_ton()
test_canh_bao_dau_ky_khong_bao_trung_khi_da_vuot_ton_cuoi_ky()
test_canh_bao_dau_ky_binh_thuong_khong_bao()

print("\nTẤT CẢ TEST PASS")
