import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test theo yêu cầu người dùng: "hãy chỉnh lại file xuất kho luôn
để cuối ngày hẹn giờ xuất là 23:59:00" (kèm ảnh chụp MISA "Nhập, xuất kho" cho
thấy phiếu "XK T12/2025" ngày 31/12/2025 nằm cùng ngày với nhiều phiếu Nhập
kho "NK..." cũng ngày 31/12/2025).

Nguyên nhân/bối cảnh: _gen_xuat_kho_rows (dùng bởi endpoint /api/xk/export -
file Excel "Xuất kho" người dùng tự import tay vào MISA) trước đây chỉ ghi
"dd/mm/yyyy" (KHÔNG có giờ) vào cột "Ngày hạch toán (*)"/"Ngày chứng từ (*)".
Cùng lý do đã fix ở đường ghi thẳng SQL (_misa_gio_xuat_co_dinh, build .200,
đặt cố định 23:00): thiếu giờ có thể khiến MISA hiểu ngầm là 00:00:00, đứng
TRƯỚC các phiếu Nhập kho CÙNG NGÀY về mặt thời gian trong ngày, khiến MISA từ
chối ghi sổ vì "quá số lượng tồn trong kho" dù tổng cả tháng vẫn đủ hàng.

Fix: _gen_xuat_kho_rows giờ ghi "dd/mm/yyyy 23:59:00" (cố định cuối ngày,
theo đúng yêu cầu người dùng) vào cả 2 cột "Ngày hạch toán (*)"/"Ngày chứng
từ (*)"."""
import sys
sys.path.insert(0, _REPO_ROOT)
import server


def test_ngay_hach_toan_va_ngay_chung_tu_co_gio_23_59_00():
    giathanh_rows = [
        {"ma": "MH1-0", "ten_xk": "Hàng A", "dvt_xk": "Cái", "sl": 1, "sl_kho": 1,
         "ngay": "31/12/2025"},
        {"ma": "MH2-0", "ten_xk": "Hàng B", "dvt_xk": "Cái", "sl": 2, "sl_kho": 2,
         "ngay": "15/12/2025"},
    ]
    ton_rows = [
        {"ma": "MH1-0", "kho": "HH"},
        {"ma": "MH2-0", "kho": "HH"},
    ]
    out, so_ct = server._gen_xuat_kho_rows(giathanh_rows, ton_rows, None)
    assert len(out) == 2, f"Phải có đúng 2 dòng — got {out}"
    for row in out:
        assert row[2] == "31/12/2025 23:59:00", (
            f"Cột 'Ngày hạch toán (*)' (index 2) PHẢI kèm giờ cố định cuối ngày "
            f"'23:59:00' — được {row[2]!r}, cả dòng: {row}")
        assert row[3] == "31/12/2025 23:59:00", (
            f"Cột 'Ngày chứng từ (*)' (index 3) PHẢI kèm giờ cố định cuối ngày "
            f"'23:59:00' — được {row[3]!r}, cả dòng: {row}")
    assert so_ct == "XK T12/2025", f"Số chứng từ vẫn phải đúng như cũ (không đổi) — got {so_ct!r}"
    print("PASS: 'Ngày hạch toán (*)'/'Ngày chứng từ (*)' của file Excel Xuất kho giờ kèm giờ cố định "
          "cuối ngày '23:59:00' — tránh MISA hiểu ngầm 00:00:00 đứng TRƯỚC phiếu Nhập kho cùng ngày.")


def test_khong_co_dong_thi_khong_loi():
    out, so_ct = server._gen_xuat_kho_rows([], [], None)
    assert out == [] and so_ct == "", f"Không có dòng hợp lệ nào -> phải trả về rỗng, không lỗi — got {out!r}, {so_ct!r}"
    print("PASS: không có dòng hợp lệ -> trả về rỗng an toàn, không crash khi ghép chuỗi giờ.")


test_ngay_hach_toan_va_ngay_chung_tu_co_gio_23_59_00()
test_khong_co_dong_thi_khong_loi()

print("\nTẤT CẢ TEST PASS")
