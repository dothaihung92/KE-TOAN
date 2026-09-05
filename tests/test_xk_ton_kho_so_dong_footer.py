import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: đúng ca thật người dùng gửi (file TONG_HOP_TON_KHO.xlsx,
công ty CÔNG TY TNHH THƯƠNG MẠI PHẨM LỢI, 5/9/2026) — báo cáo 'Tổng hợp tồn
kho' MISA có dòng TỔNG CỘNG CUỐI FILE dạng "Số dòng = 1543" ghi THẲNG vào
cột "Mã hàng" (khác dòng 'Tên kho : ...' luôn để trống cột Mã hàng) — dòng
này mang đúng SL/GT TỔNG CỦA CẢ FILE (Cuối kỳ 118.303,2 / 5.874.257.303đ).

_doc_file_ton_kho TRƯỚC ĐÂY chỉ loại 2 chuỗi "Tổng cộng"/"Tổng số" khỏi cột
Mã hàng — KHÔNG nhận diện "Số dòng = N" — nên dòng này bị coi là 1 "mã hàng"
THẬT, cộng thẳng nguyên TỔNG CẢ FILE vào tổng chung -> tổng tồn cuối kỳ báo
ra gần GẤP ĐÔI số thật (xác nhận đúng qua file thật: khối kho cuối cùng
("Kho Quần Áo", đúng khối chứa dòng "Số dòng = 1543" ở cuối) tính ra
7.362.538.709đ thay vì đúng 1.488.281.406đ — chênh ĐÚNG bằng 5.874.257.303đ,
= TỔNG CẢ FILE bị cộng lẫn vào)."""
import sys
sys.path.insert(0, _REPO_ROOT)
import server


def test_bo_qua_dong_so_dong_footer():
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
    # Khối kho 1: HH — 1 mã, cuối kỳ 100 SL / 1.000.000đ.
    ws.append(["Tên kho : HH (1 )", None, None, None, 0, 0, 100, 1000000, 0, 0, 100, 1000000])
    ws.append([None, "HH001", "Hàng A", "Cái", 0, 0, 100, 1000000, 0, 0, 100, 1000000])
    # Khối kho 2: Kho Quần Áo — 1 mã, cuối kỳ 48 SL / 3.288.048đ — Y HỆT tỉ lệ
    # ca thật (chỉ rút gọn số dòng cho test).
    ws.append(["Tên kho : Kho Quần Áo (1 )", None, None, None, 0, 0, 48, 3288048, 0, 0, 48, 3288048])
    ws.append([None, "HH1524-KQA", "Áo lá nữ", "Cái", 0, 0, 48, 3288048, 0, 0, 48, 3288048])
    # Dòng TỔNG CỘNG CUỐI FILE — ĐÚNG format thật MISA xuất ra: "Số dòng = N"
    # nằm ở CỘT B, ĐÚNG cột "Mã hàng" (khác dòng 'Tên kho :...' luôn nằm ở
    # CỘT A) — TỔNG CẢ FILE = 100+48=148 SL / 1.000.000+3.288.048=4.288.048đ.
    ws.append([None, "Số dòng = 2", None, None, 0, 0, 148, 4288048, 0, 0, 148, 4288048])

    rows, danh_sach_kho = server._doc_file_ton_kho(wb)
    by_ma = {r["ma"]: r for r in rows}

    assert "so dong = 2" not in [str(r.get("ma", "")).lower() for r in rows], (
        f"Dòng 'Số dòng = 2' KHÔNG được lọt vào danh sách mã hàng — được {rows}")
    assert len(rows) == 2, f"Chỉ đúng 2 mã hàng thật (HH001, HH1524-KQA) — được {len(rows)} dòng: {rows}"
    assert by_ma["HH1524-KQA"]["ton"] == 48 and by_ma["HH1524-KQA"]["gia"] == round(3288048 / 48), (
        f"Mã trong khối kho CÓ dòng 'Số dòng =...' theo sau KHÔNG được cộng lẫn tổng cả file vào — "
        f"được {by_ma.get('HH1524-KQA')}")

    tong_gt = sum(r["gia"] * r["ton"] for r in rows)
    assert tong_gt == 1000000 + 3288048, (
        f"TỔNG giá trị tồn cuối kỳ (cộng dồn từ các mã hàng đọc được) phải đúng bằng 4.288.048đ, KHÔNG "
        f"được gần gấp đôi (8.576.096đ) do cộng lẫn dòng tổng cộng cuối file — được {tong_gt}")
    print("PASS: dòng 'Số dòng = N' (tổng cộng cuối file báo cáo MISA) bị loại đúng, không còn bị coi "
          "là 1 mã hàng giả cộng dồn thêm nguyên tổng cả file vào tổng tồn kho.")


test_bo_qua_dong_so_dong_footer()

print("\nTẤT CẢ TEST PASS")
