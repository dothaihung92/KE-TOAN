import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: đúng ca thật người dùng báo cáo (công ty TNHH THƯƠNG MẠI
PHẨM LỢI, file TONG_HOP_TON_KHO.xlsx 01/07/2026-31/08/2026, kèm dòng tổng
cộng "Số dòng = 1497") — phần mềm hiện "Tổng giá trị tồn cuối kỳ:
5.836.267.522 đ" trong khi TỔNG THẬT của chính file đó (dòng "Số dòng =
1497" ghi rõ) chỉ là 5.831.242.503đ — lệch ~5 triệu đồng.

Nguyên nhân: _doc_file_ton_kho/_misa_lay_ton_kho chỉ trả về "gia" (đơn giá
BÌNH QUÂN đã LÀM TRÒN = round(tổng giá trị / tổng số lượng) của từng mã) —
KHÔNG giữ lại tổng giá trị THẬT (chưa làm tròn). Badge "Tổng giá trị tồn
cuối kỳ" (xkTaiTrangThai, index.html) phải TÍNH LẠI bằng tổng(Số lượng ×
"gia" đã làm tròn) vì không có gì khác để dùng — cộng dồn sai số làm tròn
đơn giá của TỪNG mã (có thể lệch tới ±0,5đ/đơn vị) qua HÀNG NGÀN mã hàng
tồn kho, ra sai lệch tổng cỡ vài triệu đồng dù mỗi mã chỉ lệch rất nhỏ.

Fix: _doc_file_ton_kho/_misa_lay_ton_kho trả thêm "gia_tri" = TỔNG giá trị
THẬT (chưa làm tròn, cộng dồn nguyên vẹn từ cột "Giá trị" của file/SUM SQL)
cho từng mã — badge phải cộng "gia_tri" (chính xác), không tính lại bằng
Số lượng × "gia" (đơn giá đã làm tròn)."""
import sys
sys.path.insert(0, _REPO_ROOT)
import server


def test_gia_tri_giu_dung_tong_that_khong_lam_tron():
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Báo cáo"
    ws.append(["TỔNG HỢP TỒN KHO"])
    ws.append(["Từ ngày 01/7/2026 đến ngày 31/8/2026"])
    ws.append([None, "Mã hàng", "Tên hàng", "ĐVT", "Đầu kỳ", None, "Nhập kho", None,
               "Xuất kho", None, "Cuối kỳ", None])
    ws.append([None, None, None, None, "Số lượng", "Giá trị", "Số lượng", "Giá trị",
               "Số lượng", "Giá trị", "Số lượng", "Giá trị"])
    ws.append(["Tên kho : HH (2 )", None, None, None, 0, 0, 6, 20, 0, 0, 6, 20])
    # 2 mã, MỖI mã: Cuối kỳ SL=3, GT=10 -> đơn giá bình quân = 10/3 = 3.33 ->
    # round() = 3 -> 3x3=9 (LỆCH 1đ so với 10 thật, THIẾU chứ không dư — round()
    # làm tròn XUỐNG ở đây) -> cộng dồn 2 mã: tính theo SL×giá làm tròn ra
    # 9+9=18, trong khi TỔNG THẬT (cộng "Giá trị" gốc) là 10+10=20 — lệch 2đ,
    # đúng bản chất lỗi thật (nhân với hàng ngàn mã ra lệch tới hàng triệu).
    ws.append([None, "MH-A", "Hàng A", "Cái", 0, 0, 3, 10, 0, 0, 3, 10])
    ws.append([None, "MH-B", "Hàng B", "Cái", 0, 0, 3, 10, 0, 0, 3, 10])
    ws.append(["Số dòng = 2", None, None, None, 0, 0, 6, 20, 0, 0, 6, 20])

    rows, danh_sach_kho = server._doc_file_ton_kho(wb)
    by_ma = {r["ma"]: r for r in rows}

    for ma in ("MH-A", "MH-B"):
        assert "gia_tri" in by_ma[ma], f"Thiếu field 'gia_tri' (tổng giá trị THẬT, chưa làm tròn) — {by_ma[ma]}"
        assert by_ma[ma]["gia_tri"] == 10, (
            f"'gia_tri' của {ma} phải đúng bằng 10 (tổng giá trị gốc từ file, KHÔNG làm tròn) — "
            f"được {by_ma[ma]['gia_tri']}")
        assert by_ma[ma]["gia"] == 3, (
            f"'gia' (đơn giá bình quân làm tròn) của {ma} vẫn phải là 3 (round(10/3)) như cũ, chỉ "
            f"KHÔNG dùng để tính tổng nữa — được {by_ma[ma]['gia']}")

    tong_gia_tri_dung = sum(r["gia_tri"] for r in rows)
    tong_tinh_sai_kieu_cu = sum(r["ton"] * r["gia"] for r in rows)
    assert tong_gia_tri_dung == 20, f"Tổng 'gia_tri' phải đúng 20 (10+10, khớp dòng 'Số dòng = 2' của file) — được {tong_gia_tri_dung}"
    assert tong_tinh_sai_kieu_cu == 18, (
        f"(Đối chứng) cách tính CŨ (Số lượng × đơn giá làm tròn) phải ra 18 (SAI, thiếu 2đ) — nếu "
        f"assertion này fail nghĩa là dữ liệu test không còn tái hiện đúng lỗi làm tròn nữa — "
        f"được {tong_tinh_sai_kieu_cu}")
    print("PASS: _doc_file_ton_kho trả đúng 'gia_tri' = tổng giá trị THẬT (20), khác với cách tính SAI "
          "cũ (Số lượng × đơn giá làm tròn = 18) — badge tổng tồn kho phải dùng 'gia_tri', không tính "
          "lại bằng ton×gia nữa.")


test_gia_tri_giu_dung_tong_that_khong_lam_tron()

print("\nTẤT CẢ TEST PASS")
