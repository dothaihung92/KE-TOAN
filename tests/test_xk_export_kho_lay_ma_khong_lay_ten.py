import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: đúng ca thật người dùng gửi file
XuatKho_T8.2026_0317009837.xlsx — cột "Kho (*)" của form Excel "Xuất kho"
MISA đang ghi TÊN kho đầy đủ ("Kho Chó Mèo KO VAT") thay vì MÃ kho
(StockCode, vd "KHOCHOMEOKOVAT") — người dùng báo "Cột kho là lấy mã kho
chứ không phải lấy tên Kho".

Nguyên nhân: field "kho" trong Sheet TON (_doc_file_ton_kho/_misa_lay_ton_kho)
luôn là TÊN kho (đọc từ dòng "Tên kho : ..." của báo cáo Excel MISA, hoặc ưu
tiên StockName khi lấy trực tiếp từ SQL) — _gen_xuat_kho_rows trước đây ghi
thẳng giá trị "kho" đó vào cột "Kho (*)" mà không đổi sang mã.

Fix: _gen_xuat_kho_rows nhận thêm tham số ten_sang_ma_kho ({tên kho
(lower): mã kho}) để đổi tên -> mã đúng trước khi ghi vào cột "Kho (*)"."""
import sys
sys.path.insert(0, _REPO_ROOT)
import server


def test_doi_ten_kho_sang_ma_kho_khi_co_mapping():
    giathanh_rows = [
        {"ma": "MH1625-0", "ten_xk": "Thức ăn cho mèo PetQ", "dvt_xk": "Túi", "sl": 50, "sl_kho": 50,
         "ngay": "31/08/2026"},
        {"ma": "HH6040-0", "ten_xk": "RC408310 - Mini Adult 2kg", "dvt_xk": "Bao", "sl": 2, "sl_kho": 2,
         "ngay": "31/08/2026"},
    ]
    ton_rows = [
        {"ma": "MH1625-0", "kho": "Kho Chó Mèo KO VAT"},
        {"ma": "HH6040-0", "kho": "Kho Chó Mèo KO VAT"},
    ]
    ten_sang_ma_kho = {"kho chó mèo ko vat": "KHOCHOMEOKOVAT"}
    out, so_ct = server._gen_xuat_kho_rows(giathanh_rows, ton_rows, ten_sang_ma_kho)
    assert len(out) == 2, f"Phải có đúng 2 dòng — got {out}"
    for row in out:
        assert row[30] == "KHOCHOMEOKOVAT", (
            f"Cột 'Kho (*)' (AE, index 30) PHẢI ghi ĐÚNG MÃ kho 'KHOCHOMEOKOVAT' (StockCode) — KHÔNG được "
            f"ghi tên đầy đủ 'Kho Chó Mèo KO VAT' — được {row[30]!r}, cả dòng: {row}")
    print("PASS: có mapping tên->mã kho (từ Stock thật) -> cột 'Kho (*)' ghi ĐÚNG MÃ kho, không còn ghi "
          "tên đầy đủ như ca thật người dùng báo (file XuatKho_T8.2026, cột Kho ghi 'Kho Chó Mèo KO VAT').")


def test_khong_co_mapping_van_giu_nguyen_gia_tri_cu():
    giathanh_rows = [{"ma": "MH1-0", "ten_xk": "Hàng A", "dvt_xk": "Cái", "sl": 1, "sl_kho": 1,
                       "ngay": "31/08/2026"}]
    ton_rows = [{"ma": "MH1-0", "kho": "Kho Chó Mèo KO VAT"}]
    out, so_ct = server._gen_xuat_kho_rows(giathanh_rows, ton_rows, None)
    assert out[0][30] == "Kho Chó Mèo KO VAT", (
        f"Chưa cấu hình kết nối SQL MISA (không có mapping) -> phải GIỮ NGUYÊN giá trị 'kho' cũ (tên), "
        f"KHÔNG được để trống/lỗi — được {out[0][30]!r}")
    print("PASS: không có mapping tên->mã (chưa cấu hình SQL MISA) -> vẫn xuất được, giữ nguyên như cũ.")


test_doi_ten_kho_sang_ma_kho_khi_co_mapping()
test_khong_co_mapping_van_giu_nguyen_gia_tri_cu()

print("\nTẤT CẢ TEST PASS")
