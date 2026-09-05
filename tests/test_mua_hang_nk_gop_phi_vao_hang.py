import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: đúng ca thật người dùng báo lại qua màn "Đối chiếu tổng
giá trị & VAT" — hóa đơn Số HĐ 22619 (MST 0108705693-008, 29/08/2026) có 2
dòng: "Bồn Inox Đại Thành 1.500N ĐK1170" (5.537.037đ) và "Phí kéo lầu bồn
Inox dưới 7 tầng - 1.500L" (111.111đ) — trước đây dòng phí này tạo thành 1
MÃ HÀNG RIÊNG (mã "rác", chỉ dùng đúng 1 lần, không tái sử dụng được cho
hóa đơn khác) khiến dữ liệu "nguồn" đối chiếu (không có dòng phí tách rời
này) báo lệch dù MISA ghi đúng theo Bảng kê.

Theo yêu cầu người dùng ("xem có cách nào cộng dồn phí vào mặt hàng luôn
không vì phí này tôi cũng sẽ cộng thẳng vào tiền hàng"): người dùng tự
đánh dấu tay dòng phí bằng cách thêm cột "Là phí" vào Bảng kê Đầu vào rồi
gõ 'x' cho dòng đó — _gen_mua_hang_nk PHÂN BỔ (theo tỷ lệ Thành tiền) số
tiền phí thẳng vào TẤT CẢ dòng hàng hóa CÙNG hóa đơn rồi bỏ hẳn dòng phí,
không tạo mã hàng riêng cho nó nữa."""
import sys
sys.path.insert(0, _REPO_ROOT)
import server

HEADER = ['Ký hiệu', 'Số HĐ', 'Ngày', 'Người bán', 'MST bán', 'STT', 'Mã vt',
          'Tên hàng hóa/dịch vụ', 'ĐVT', 'Số lượng', 'Đơn giá', 'Thành tiền',
          'Thuế suất', 'Tiền thuế GTGT', 'Trị giá tính thuế NK', 'Thuế suất NK',
          'Tiền thuế NK', 'Nợ', 'Có', 'Là phí']


def test_gop_phi_vao_dung_1_dong_hang_khi_hoa_don_chi_co_1_ma():
    rows = [
        ['C26THM', '22619', '29/08/2026', 'CHI NHÁNH CÔNG TY', '0108705693-008', 1,
         '9011315011020012', 'Bồn Inox Đại Thành 1.500N ĐK1170', 'Bộ', 1, 5537037, 5537037,
         '8%', 442963, None, None, None, '1561', '331', ''],
        ['C26THM', '22619', '29/08/2026', 'CHI NHÁNH CÔNG TY', '0108705693-008', 2,
         '8300000000000043', 'Phí kéo lầu bồn Inox dưới 7 tầng - 1.500L', 'Gói', 1, 111111, 111111,
         '8%', 8889, None, None, None, '1561', '331', 'x'],
    ]
    out = server._gen_mua_hang_nk(999999, HEADER, rows)
    assert len(out) == 1, f"Dòng phí PHẢI bị gộp vào dòng hàng hóa, không còn tạo mã hàng riêng — got {len(out)} dòng: {out}"
    r = out[0]
    assert r[28] == 5648148, f"Thành tiền phải cộng cả phí (5.537.037+111.111=5.648.148) — được {r[28]}"
    assert r[35] == 451852, f"Tiền thuế GTGT phải cộng cả phí (442.963+8.889=451.852) — được {r[35]}"
    assert abs(r[27] * r[26] - r[28]) < 0.01, f"Đơn giá × Số lượng phải khớp đúng Thành tiền mới — Đơn giá={r[27]}, SL={r[26]}, Thành tiền={r[28]}"
    print("PASS: hóa đơn chỉ có 1 mã hàng — dòng phí gộp trọn vào đúng mã đó, Đơn giá tính lại khớp Thành tiền mới.")


def test_gop_phi_phan_bo_theo_ty_le_khi_nhieu_ma_hang():
    rows = [
        ['C26X', 'HD1', '01/01/2026', 'NCC X', '0100000000', 1, 'M1', 'Hàng A', 'Cái', 1, 3000000, 3000000,
         '10%', 300000, None, None, None, '1561', '331', ''],
        ['C26X', 'HD1', '01/01/2026', 'NCC X', '0100000000', 2, 'M2', 'Hàng B', 'Cái', 1, 1000000, 1000000,
         '10%', 100000, None, None, None, '1561', '331', ''],
        ['C26X', 'HD1', '01/01/2026', 'NCC X', '0100000000', 3, 'M3', 'Phí vận chuyển', 'Chuyến', 1, 400000, 400000,
         '10%', 40000, None, None, None, '1561', '331', 'x'],
    ]
    out = server._gen_mua_hang_nk(999999, HEADER, rows)
    assert len(out) == 2, f"Chỉ 2 dòng hàng hóa (bỏ dòng phí) — got {len(out)} dòng: {out}"
    by_ten = {r[20]: r for r in out}
    # Hàng A (3.000.000, tỷ lệ 75%) nhận 75% phí = 300.000 -> tổng 3.300.000
    # Hàng B (1.000.000, tỷ lệ 25%) nhận 25% phí = 100.000 -> tổng 1.100.000
    assert by_ten["Hàng A"][28] == 3300000, f"Hàng A phải nhận đúng 75% phí (300.000) -> tổng 3.300.000 — được {by_ten['Hàng A'][28]}"
    assert by_ten["Hàng B"][28] == 1100000, f"Hàng B phải nhận đúng 25% phí (100.000) -> tổng 1.100.000 — được {by_ten['Hàng B'][28]}"
    tong = sum(r[28] for r in out)
    assert tong == 3000000 + 1000000 + 400000, f"Tổng Thành tiền sau phân bổ phải KHÔNG đổi so với tổng gốc (bảo toàn tiền) — được {tong}"
    print("PASS: phí phân bổ ĐÚNG theo tỷ lệ Thành tiền cho nhiều dòng hàng hóa cùng hóa đơn, bảo toàn tổng tiền.")


def test_khong_co_cot_la_phi_thi_hanh_vi_giu_nguyen_nhu_cu():
    header_khong_co_cot = HEADER[:-1]   # bỏ cột "Là phí"
    rows = [
        ['C26THM', '22619', '29/08/2026', 'CHI NHÁNH CÔNG TY', '0108705693-008', 1,
         '9011315011020012', 'Bồn Inox Đại Thành 1.500N ĐK1170', 'Bộ', 1, 5537037, 5537037,
         '8%', 442963, None, None, None, '1561', '331'],
        ['C26THM', '22619', '29/08/2026', 'CHI NHÁNH CÔNG TY', '0108705693-008', 2,
         '8300000000000043', 'Phí kéo lầu bồn Inox dưới 7 tầng - 1.500L', 'Gói', 1, 111111, 111111,
         '8%', 8889, None, None, None, '1561', '331'],
    ]
    out = server._gen_mua_hang_nk(999999, header_khong_co_cot, rows)
    assert len(out) == 2, (
        f"Chưa thêm cột 'Là phí' -> hành vi PHẢI giữ nguyên như cũ (mỗi dòng vẫn tạo 1 mã hàng riêng, "
        f"KHÔNG tự động gộp) — got {len(out)} dòng: {out}")
    print("PASS: chưa thêm cột 'Là phí' -> hành vi giữ nguyên như cũ (không tự động gộp bất cứ dòng nào).")


test_gop_phi_vao_dung_1_dong_hang_khi_hoa_don_chi_co_1_ma()
test_gop_phi_phan_bo_theo_ty_le_khi_nhieu_ma_hang()
test_khong_co_cot_la_phi_thi_hanh_vi_giu_nguyen_nhu_cu()

print("\nTẤT CẢ TEST PASS")
