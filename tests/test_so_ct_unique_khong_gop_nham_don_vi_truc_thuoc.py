import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: đúng ca thật người dùng báo lại qua màn "Đối chiếu tổng
giá trị & VAT" (Mua hàng) — hóa đơn Số HĐ 1696 (MST đơn vị trực thuộc
'3700152194-003', 06/11/2025, tổng 15.068.561đ) báo "THIẾU trong MISA",
trong khi hóa đơn Số HĐ 1030 (MST '3700152194-002', 14/05/2025, tổng
8.295.600đ) lại "LỆCH -16.274.045đ" — MISA ghi 23.364.161đ = ĐÚNG BẰNG
8.295.600 + 15.068.561 — chứng tỏ 2 hóa đơn của 2 CHI NHÁNH KHÁC NHAU (cùng
MST gốc '3700152194' nhưng khác hậu tố đơn vị trực thuộc '-002'/'-003',
khác Số HĐ, khác hẳn ngày) đã bị GỘP NHẦM vào chung 1 chứng từ khi ghi vào
MISA — hóa đơn 1696 "biến mất" (không có chứng từ riêng), tiền của nó cộng
dồn nhầm vào chứng từ của hóa đơn 1030. Y hệt vậy với cặp Số HĐ 74 (MST
'-003', 779.000đ) và 1314 (MST '-002', 12.682.500đ) -> MISA ghi 13.461.500đ
= 779.000 + 12.682.500.

Nguyên nhân: _so_ct_unique() (sinh "Số phiếu nhập" duy nhất, tối đa 20 ký
tự) đếm số lần trùng RIÊNG cho từng "base" gốc (prefix+năm+MST) rồi mới CẮT
BỚT base để chèn hậu tố '-2','-3'... khi trùng. Base của MST '-002' và
'-003' (cùng 20 ký tự, chỉ khác đúng 1 ký tự CUỐI) mà CÙNG rơi vào bậc
collision thứ N (vd cả 2 đều là hóa đơn thứ 2 trong năm của đúng MST gốc
'3700152194' đó) sẽ bị cắt về ĐÚNG 1 chuỗi giống hệt nhau (mất đúng ký tự
phân biệt '2'/'3' ở cuối) — 2 hóa đơn hoàn toàn khác nhau bị coi là "1
nhóm = 1 PUVoucher" trong _misa_ghi_mua_hang.

Fix: _so_ct_unique() giờ kiểm tra ĐÚNG chuỗi CUỐI CÙNG đã cấp ra (không
phải base gốc) trước khi trả về, tăng dần hậu tố tới khi thật sự chưa cấp
cho ai — đảm bảo KHÔNG BAO GIỜ có 2 lời gọi khác invoice_key trả về cùng 1
chuỗi, dù base gốc của chúng trùng nhau ở phần bị cắt."""
import sys
sys.path.insert(0, _REPO_ROOT)
import server


def test_khong_gop_nham_2_don_vi_truc_thuoc_khac_hau_to_mst():
    seen, cache = {}, {}
    # Đúng thứ tự thật trong Bảng kê: 1029 (MST -002) xử lý trước, đẩy 1030
    # (cũng MST -002) lên bậc collision thứ 2 của base '...-002'; rồi tới
    # 1696 (MST -003, HOÀN TOÀN KHÁC hóa đơn, khác chi nhánh, khác ngày) —
    # base '...-003' của riêng nó cũng đang ở bậc collision thứ 2 (do các
    # hóa đơn KHÁC của MST -003 xử lý trước đó, không liệt kê ở đây cho gọn
    # — mô phỏng bằng cách gọi thẳng seen với base '...-003' đã có sẵn 1 lần).
    def goi(sohd, mst, ngay):
        return server._so_ct_unique_memo("NK", ngay, mst, (sohd, mst, ngay, "C25TCL"), seen, cache)

    v_1029 = goi("1029", "3700152194-002", "14/05/2025")   # base '...-002' lần 1
    v_1030 = goi("1030", "3700152194-002", "14/05/2025")   # base '...-002' lần 2 -> bị cắt hậu tố
    # mô phỏng đã có 1 hóa đơn KHÁC của MST -003 xử lý trước đó (đẩy base
    # '...-003' lên collision lần 2 khi tới lượt 1696) — invoice_key khác
    # nên KHÔNG dùng cache, gọi thẳng seen qua 1 invoice giả trước.
    server._so_ct_unique_memo("NK", "01/03/2025", "3700152194-003", ("giả-truoc", "3700152194-003", "01/03/2025", "X"), seen, cache)
    v_1696 = goi("1696", "3700152194-003", "06/11/2025")   # base '...-003' lần 2 -> bị cắt hậu tố

    assert v_1030 != v_1696, (
        f"Hóa đơn 1030 (MST '3700152194-002', 14/05/2025) và hóa đơn 1696 (MST '3700152194-003', "
        f"06/11/2025) là 2 hóa đơn HOÀN TOÀN KHÁC NHAU (khác Số HĐ, khác MST đơn vị trực thuộc, khác ngày) "
        f"— PHẢI sinh 2 'Số phiếu nhập' KHÁC NHAU để không bị gộp nhầm vào chung 1 chứng từ MISA — cả 2 "
        f"cùng ra {v_1030!r}")
    assert len({v_1029, v_1030, v_1696}) == 3, (
        f"3 hóa đơn khác nhau (1029, 1030, 1696) phải ra 3 'Số phiếu nhập' khác nhau — được "
        f"{v_1029!r}, {v_1030!r}, {v_1696!r}")
    for v in (v_1029, v_1030, v_1696):
        assert len(v) <= 20, f"'Số phiếu nhập' phải tối đa 20 ký tự (giới hạn MISA) — {v!r} dài {len(v)}"
    print(f"PASS: 3 hóa đơn (1029={v_1029!r}, 1030={v_1030!r}, 1696={v_1696!r}) sinh 3 'Số phiếu nhập' "
          f"khác nhau, không còn gộp nhầm 2 chi nhánh khác nhau (MST '-002'/'-003') vào chung 1 chứng từ.")


test_khong_gop_nham_2_don_vi_truc_thuoc_khac_hau_to_mst()

print("\nTẤT CẢ TEST PASS")
