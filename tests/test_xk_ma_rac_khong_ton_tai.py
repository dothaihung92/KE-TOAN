import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: _xk_gan_ma_truc_tiep (nút "🔍 Dò mã hàng tự động" khi
GIATHANH đã có dữ liệu) PHẢI TỰ SỬA LẠI dòng có "Mã hàng kho" (ma) là 1
chuỗi RÁC không khớp mã nào trong Tồn kho hiện có (vd chính TÊN hàng bị
gán nhầm vào ô Mã hàng kho từ 1 lỗi rất cũ, hoặc mã đã đổi/xoá trong MISA)
— KHÔNG được giữ nguyên mãi mãi chỉ vì dòng đó "đã có mã" (chuỗi không
rỗng).

Đúng ca thật người dùng báo cáo — gửi kèm 3 file: "TONG_HOP_TON_KHO.xlsx"
(Tồn kho thật, có mã "HH00087-8" tên "Gạch men 600x1200 mm" tồn 79,2),
"KetXuatGiaThanh_...xlsx" (file Giá thành phần mềm đã xuất, cột "Mã hàng
kho" của dòng "GẠCH ỐP LÁT 600*1200MM" lại là chuỗi "Gạch men 600x1200 mm"
— CHÍNH LÀ TÊN HÀNG, không phải mã thật), và "KetQua.xls" (log lỗi MISA từ
chối ghi sổ Xuất kho): "Không thể xuất vật tư, hàng hóa <Gạch men 600x1200
mm - Gạch men 600x1200 mm> quá số lượng tồn trong kho <HH - HH>. Số lượng
tồn trong kho <HH - HH> là: 0,00." — vì MISA không tìm thấy mã hàng nào
tên là "Gạch men 600x1200 mm" (không tồn tại, khác hẳn mã thật "HH00087-8"
đang còn tồn 79,2) nên coi như tồn = 0. Người dùng: "kiểm tra lại mã tồn
kho phần mềm đang lấy mã hàng tồn bị sai nên xuất misa bị báo lỗi".

Nguyên nhân: bước phát hiện "dòng đáng ngờ" (dong_ngo) của
_xk_gan_ma_truc_tiep CHỈ kiểm tra mã hiện tại có KHỚP CHẮC CHẮN theo
_ma_ngoac_khop_xk (mã-trong-ngoặc) hay không — hoàn toàn BỎ QUA trường hợp
mã hiện tại KHÔNG map được tới BẤT KỲ mặt hàng nào trong Tồn kho hiện có
(ton_by_ma.get(ma) trả None) — dòng đó bị "continue" ngay, không bao giờ
được đưa vào dong_ngo, nên bị hàm giữ NGUYÊN vĩnh viễn dù "Mã hàng kho" là
rác hoàn toàn, bấm "Dò mã hàng tự động" bao nhiêu lần cũng không tự sửa."""
import sys
sys.path.insert(0, _REPO_ROOT)
import server

ton_rows = [{"ma": "HH00087-8", "ten": "Gạch men 600x1200 mm", "dvt": "M2", "ton": 79.2, "gia": 140878}]
giathanh_cu = [{
    "sohd": "3", "ngay": "07/05/2024", "ten_sp": "Gạch men 600x1200 mm", "dvt": "M2",
    "sl": 61.92, "dgia": 288000, "tt": 17832960,
    # "Mã hàng kho" đang là RÁC — chính TÊN hàng, không phải mã thật "HH00087-8".
    "ma": "Gạch men 600x1200 mm", "ten_xk": "Gạch men 600x1200 mm", "dvt_xk": "Cái",
    "sl_kho": 61.92, "gia_xk": 140878,
}]

out = server._xk_gan_ma_truc_tiep(ton_rows, giathanh_cu, {})
print("Kết quả:", [{k: r.get(k) for k in ("ma", "ten_xk", "sl", "sl_kho", "tt")} for r in out])

assert len(out) == 1, f"Không được tách dòng (tồn 79,2 đủ cho 61,92) — được {len(out)} dòng: {out}"
dong = out[0]
assert dong["ma"] == "HH00087-8", (
    f"Bấm 'Dò mã hàng tự động' PHẢI TỰ SỬA mã rác 'Gạch men 600x1200 mm' (chính TÊN hàng, MISA từ chối vì "
    f"không tìm thấy mã này, coi tồn=0) thành mã THẬT 'HH00087-8' (đang còn tồn 79,2) — được ma={dong['ma']}")
assert dong["ten_xk"] == "Gạch men 600x1200 mm"
assert dong["sl_kho"] == 61.92 and dong["sl"] == 61.92, (
    f"Số lượng/SL kho không được đổi khi chỉ sửa lại mã (không tách dòng, tồn vẫn đủ) — được {dong}")
assert dong["tt"] == 17832960

print("\nPASS: _xk_gan_ma_truc_tiep giờ TỰ SỬA được 'Mã hàng kho' là chuỗi RÁC không khớp mã nào trong Tồn "
      "kho (không chỉ riêng trường hợp mã-trong-ngoặc sai màu như trước) — MISA sẽ không còn từ chối ghi sổ "
      "vì 'Số lượng tồn... là: 0,00' do mã không tồn tại nữa.")
print("\nTẤT CẢ TEST PASS")
