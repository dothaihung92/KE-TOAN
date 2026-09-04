import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: _xk_gan_ma_truc_tiep (nút "🔍 Dò mã hàng tự động" khi
GIATHANH đã có dữ liệu) PHẢI đồng bộ lại "ĐVT kho" (dvt_xk) theo ĐÚNG ĐVT
đang có trong Tồn kho (nguồn lấy trực tiếp/gián tiếp từ MISA) — KHÔNG chỉ
với dòng vừa được TỰ SỬA mã (dong_ngo), mà kể cả dòng mã ĐANG ĐÚNG (không
bị nghi ngờ) nhưng "ĐVT kho" đã lưu từ trước lỡ SAI/CŨ (vd Tồn kho được
"Cập nhật tồn kho" lại sau đó với ĐVT khác) — ĐVT là thuộc tính CỐ ĐỊNH
của 1 mã hàng trong Danh mục MISA, không có lý do gì để lệch giữa dòng bán
và Tồn kho khi mã đã đúng.

Người dùng: "đơn vị tính cũng phải lấy đúng trong misa hãy kiểm tra lại"
(gửi ngay sau khi phần mềm đã tự sửa được lỗi 'Mã hàng kho' là chuỗi rác,
xem test_xk_ma_rac_khong_ton_tai.py) — yêu cầu kiểm tra thêm phần Đơn vị
tính cũng phải khớp đúng theo MISA.

Đồng thời PHẢI AN TOÀN: nếu bản thân Tồn kho đang lưu ĐVT RỖNG (dữ liệu
MISA/thiếu cột) thì KHÔNG được xoá mất "ĐVT kho" đang có sẵn của dòng bán
— chỉ ghi đè khi Tồn kho có ĐVT rõ ràng."""
import sys
sys.path.insert(0, _REPO_ROOT)
import server


# ===== Ca 1: mã ĐÚNG (không bị nghi ngờ, không tách dòng) nhưng "ĐVT kho"
# đã lưu từ TRƯỚC bị SAI/CŨ so với Tồn kho hiện có -> PHẢI tự đồng bộ lại. =====
ton_rows1 = [{"ma": "HH00087-8", "ten": "Gạch men 600x1200 mm", "dvt": "M2", "ton": 79.2, "gia": 140878}]
giathanh_cu1 = [{
    "sohd": "3", "ngay": "07/05/2024", "ten_sp": "Gạch men 600x1200 mm", "dvt": "M2",
    "sl": 61.92, "dgia": 288000, "tt": 17832960,
    "ma": "HH00087-8", "ten_xk": "Gạch men 600x1200 mm", "dvt_xk": "Cái (SAI CŨ)",
    "sl_kho": 61.92, "gia_xk": 140878,
}]
out1 = server._xk_gan_ma_truc_tiep(ton_rows1, giathanh_cu1, {})
assert len(out1) == 1
assert out1[0]["dvt_xk"] == "M2", (
    f"Mã ĐÚNG nhưng 'ĐVT kho' cũ SAI ('Cái (SAI CŨ)') PHẢI được đồng bộ lại đúng theo Tồn kho ('M2') — "
    f"được dvt_xk={out1[0]['dvt_xk']!r}")
assert out1[0]["ma"] == "HH00087-8" and out1[0]["sl_kho"] == 61.92, "Không được đụng gì khác ngoài dvt_xk"
print("PASS ca 1: mã đúng nhưng ĐVT kho cũ sai -> tự đồng bộ lại đúng theo Tồn kho.")

# ===== Ca 2: Tồn kho đang lưu ĐVT RỖNG (dữ liệu thiếu) -> KHÔNG được xoá
# mất 'ĐVT kho' đang có sẵn của dòng bán (an toàn, không mất dữ liệu tốt). =====
ton_rows2 = [{"ma": "HH00099", "ten": "ABC", "dvt": "", "ton": 10, "gia": 1000}]
giathanh_cu2 = [{"sohd": "1", "ten_sp": "ABC", "sl": 5, "tt": 5000,
                 "ma": "HH00099", "ten_xk": "ABC", "dvt_xk": "Cái", "sl_kho": 5, "gia_xk": 1000}]
out2 = server._xk_gan_ma_truc_tiep(ton_rows2, giathanh_cu2, {})
assert out2[0]["dvt_xk"] == "Cái", (
    f"Tồn kho ĐVT rỗng -> KHÔNG được xoá 'ĐVT kho' đang có sẵn — được dvt_xk={out2[0]['dvt_xk']!r}")
print("PASS ca 2: Tồn kho ĐVT rỗng -> giữ nguyên ĐVT kho đang có, không xoá mất dữ liệu tốt.")

# ===== Ca 3: mã ĐÃ ĐÚNG SẴN 'ĐVT kho' (khớp Tồn kho) -> không đổi gì (đối
# chứng, tránh ghi đè không cần thiết mọi dòng). =====
ton_rows3 = [{"ma": "HH00087-8", "ten": "Gạch men 600x1200 mm", "dvt": "M2", "ton": 79.2, "gia": 140878}]
giathanh_cu3 = [{"sohd": "3", "ten_sp": "Gạch men 600x1200 mm", "sl": 10, "tt": 100000,
                 "ma": "HH00087-8", "ten_xk": "Gạch men 600x1200 mm", "dvt_xk": "M2",
                 "sl_kho": 10, "gia_xk": 140878}]
out3 = server._xk_gan_ma_truc_tiep(ton_rows3, giathanh_cu3, {})
assert out3[0]["dvt_xk"] == "M2"
print("PASS ca 3: ĐVT kho đã đúng sẵn -> không đổi gì thêm.")

print("\nTẤT CẢ TEST PASS")
