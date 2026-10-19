import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Lỗi thật (file TraCuuToKhai_20261019): công ty AZS đã nộp 05/KK-TNCN Q3/2026 ("Đã chấp nhận") và 01/GTGT Q3/2026 ("Chờ chấp nhận") nhưng danh sách
# "Tra cứu tờ khai thuế / tải tờ khai hàng loạt" KHÔNG hiện tick xanh/chờ xử lý. Nguyên nhân: _dvc_kiem_tra_da_nop_mot_loai so
# _loai_tk_tu_ten_day_du(...) (trả MÃ CHÍNH THỨC '01GTGT'/'05KK-TNCN') với 'GTGT'/'TNCN' -> không bao giờ khớp -> luôn "chưa tìm thấy".
TNCN = "05/KK-TNCN - Tờ khai thuế thu nhập cá nhân (TT80/2021)"
GTGT = "01/GTGT - TỜ KHAI THUẾ GIÁ TRỊ GIA TĂNG Mẫu số 01/GTGT (TT80/2021)"
QTT = "05/QTT-TNCN - Tờ khai quyết toán thuế thu nhập cá nhân (TT80/2021)"
assert server._la_to_khai_loai(GTGT, "GTGT") and not server._la_to_khai_loai(GTGT, "TNCN")
assert server._la_to_khai_loai(TNCN, "TNCN") and not server._la_to_khai_loai(TNCN, "GTGT")
assert not server._la_to_khai_loai(QTT, "TNCN"), "quyết toán năm không phải TNCN quý"
assert server._la_to_khai_loai("Tờ khai thuế giá trị gia tăng", "GTGT")      # tên không kèm mã (tab Thuế điện tử)
print("PASS 1: nhận đúng loại GTGT/TNCN từ tên đầy đủ (mã chính thức), loại trừ quyết toán năm.")

rows = [
    {"mst": "1101964108", "to_khai": TNCN, "ky": "Q3/2026", "loai": "Chính thức", "ngay_nop": "19/10/2026 00:26", "trang_thai": "Đã chấp nhận"},
    {"mst": "1101964108", "to_khai": GTGT, "ky": "Q3/2026", "loai": "Chính thức", "ngay_nop": "19/10/2026 00:26", "trang_thai": "Chờ chấp nhận"},
    {"mst": "1101964108", "to_khai": GTGT, "ky": "Q2/2026", "loai": "Chính thức", "ngay_nop": "10/07/2026", "trang_thai": "Đã chấp nhận"},   # kỳ khác
]
server._nguon_tra_cuu_theo_ky = lambda tu, den: ["tdt"]
server._dvc_browser_tracuu_tdt = lambda drv, tu, den: (rows, None, None, None)
server._dvc_browser_tracuu = lambda drv, tu, den: (rows, None, None, None)
tu, den = server._tu_den_cua_quy(2026, 3)
xn, tt, ct = server._dvc_kiem_tra_da_nop_mot_loai(None, "TNCN", tu, den)
assert xn is True and tt == "Đã chấp nhận" and server._phan_loai_trang_thai_cqt(tt) == "da_chap_nhan", (xn, tt, ct)
xn, tt, ct = server._dvc_kiem_tra_da_nop_mot_loai(None, "GTGT", tu, den)
assert xn is False and tt == "Chờ chấp nhận" and server._phan_loai_trang_thai_cqt(tt) == "cho", (xn, tt, ct)
print("PASS 2: TNCN Q3/2026 'Đã chấp nhận' -> xanh ✓; GTGT Q3/2026 'Chờ chấp nhận' -> vàng ⏳ (không lẫn với GTGT Q2 đã chấp nhận của kỳ khác).")

rows[:] = [rows[2]]
xn, tt, ct = server._dvc_kiem_tra_da_nop_mot_loai(None, "GTGT", tu, den)
assert xn is False and tt == "" and "KỲ KHÁC" in ct
print("PASS 3: chỉ có tờ khai kỳ khác -> vẫn báo chưa nộp kỳ này (không nhận nhầm).")
print("ALL DONE")
