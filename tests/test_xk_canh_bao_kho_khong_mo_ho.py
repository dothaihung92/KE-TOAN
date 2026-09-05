import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: người dùng báo lại đúng ca thật — file tồn kho gồm 5
kho (HH, Kho Chó Mèo Có VAT, Kho Chó Mèo KO VAT, Kho Quần Áo, Kho Chăn Ga)
nhưng KHÔNG còn mã hàng nào thật sự rải rác ở nhiều kho (mọi mã đều
kho_ro=True, đã được sửa về đúng 1 kho nhất quán qua các fix "kho gần
nhất") — _xk_canh_bao_kho_ton VẪN hiện banner cảnh báo màu đỏ CHUNG CHUNG
("File tồn kho gồm 5 KHO khác nhau... Mã hàng chỉ thuộc đúng 1 kho đã tự
động xuất ĐÚNG kho đó.") dù không có gì cần chú ý — đúng câu người dùng
báo: "nếu mã chỉ về 1 kho rồi thì không cần hiện thông báo này nữa".

Fix: khi KHÔNG còn mã nào "kho_ro"=False (mọi mã đều CHỈ thuộc đúng 1
kho), _xk_canh_bao_kho_ton phải trả None (không hiện banner) — banner chỉ
còn cần thiết khi CÓ ÍT NHẤT 1 mã thật sự mơ hồ (rải rác nhiều kho, không
xác định được kho đúng để xuất)."""
import sys
sys.path.insert(0, _REPO_ROOT)
import server


def test_khong_hien_banner_khi_khong_con_ma_mo_ho():
    danh_sach_kho = ["HH", "Kho Chó Mèo Có VAT", "Kho Chó Mèo KO VAT", "Kho Quần Áo", "Kho Chăn Ga"]
    ton_rows = [
        {"ma": "MH1269-0", "ten": "Súp thưởng INABA CIAO", "kho_ro": True, "kho": "HH"},
        {"ma": "MH1561-8", "ten": "Cát đậu phụ cho mèo", "kho_ro": True, "kho": "KHODOKOVAT"},
        {"ma": "MH100-0", "ten": "Áo thun", "kho_ro": True, "kho": "KHOQUANAO"},
    ]
    kq = server._xk_canh_bao_kho_ton(danh_sach_kho, ton_rows)
    assert kq is None, (
        f"KHÔNG còn mã nào rải rác nhiều kho (mọi mã đều kho_ro=True) -> KHÔNG được hiện banner cảnh báo "
        f"nữa dù file vẫn gồm nhiều kho — được {kq!r}")
    print("PASS: không còn mã mơ hồ -> _xk_canh_bao_kho_ton trả None, không hiện banner nữa.")


def test_van_hien_banner_khi_con_ma_mo_ho():
    danh_sach_kho = ["HH", "Kho Chó Mèo Có VAT", "Kho Chó Mèo KO VAT"]
    ton_rows = [
        {"ma": "MH1269-0", "ten": "Súp thưởng INABA CIAO", "kho_ro": True, "kho": "HH"},
        {"ma": "HH4610-0", "ten": "Hàng rải rác", "kho_ro": False, "kho": None},
    ]
    kq = server._xk_canh_bao_kho_ton(danh_sach_kho, ton_rows)
    assert kq is not None and "HH4610-0" in kq, (
        f"VẪN CÒN mã 'HH4610-0' rải rác nhiều kho (kho_ro=False) -> PHẢI vẫn hiện banner nêu rõ mã đó — "
        f"được {kq!r}")
    print("PASS: còn mã mơ hồ -> _xk_canh_bao_kho_ton vẫn hiện banner nêu đúng tên mã cần chú ý.")


test_khong_hien_banner_khi_khong_con_ma_mo_ho()
test_van_hien_banner_khi_con_ma_mo_ho()

print("\nTẤT CẢ TEST PASS")
