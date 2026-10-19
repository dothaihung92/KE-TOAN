import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Công ty đã nộp ĐỦ 2 tờ khai (GTGT + TNCN) nhưng danh sách chỉ hiện 1 loại (loại kia '–'). Nguyên nhân: trạng thái từng loại được tra cứu RIÊNG
# (2 lượt tra cứu cổng/captcha); lượt nào lỗi/không ra bảng thì bị coi là "chưa nộp" và còn GHI ĐÈ trạng thái cũ bằng rỗng.
# Nay: 1 lần tra cứu cho cả 2 loại; thử lại khi không ra bảng; lỗi tra cứu thì KHÔNG kết luận "chưa nộp" và KHÔNG ghi đè trạng thái cũ.
TNCN = "05/KK-TNCN - Tờ khai thuế thu nhập cá nhân (TT80/2021)"
GTGT = "01/GTGT - TỜ KHAI THUẾ GIÁ TRỊ GIA TĂNG Mẫu số 01/GTGT (TT80/2021)"
ROWS = [{"to_khai": TNCN, "ky": "Q3/2026", "trang_thai": "Đã chấp nhận"}, {"to_khai": GTGT, "ky": "Q3/2026", "trang_thai": "Đã chấp nhận"}]
goi = []
server._nguon_tra_cuu_theo_ky = lambda tu, den: ["dvc"]

# 1) 1 lần tra cứu, phân tích cho cả 2 loại
server._dvc_browser_tracuu = lambda drv, tu, den: (goi.append(1) or ROWS, [], "<table>", [])
tu, den = server._tu_den_cua_quy(2026, 3)
rows, loi, tt, dt = server._dvc_lay_ho_so_theo_ky(None, tu, den)
assert len(goi) == 1 and not loi and len(rows) == 2
for loai in ("GTGT", "TNCN"):
    xn, t, ct = server._dvc_phan_tich_da_nop(rows, loai, tu, den, tt, dt)
    assert xn is True and t == "Đã chấp nhận", (loai, xn, t)
print("PASS 1: 1 lần tra cứu cho cả GTGT + TNCN -> cả 2 đều 'Đã chấp nhận'.")

# 2) lần 1 không ra bảng (captcha/cổng lỗi) -> thử lại, lần 2 ra -> đủ 2 loại
goi.clear()
def chap_chon(drv, tu, den):
    goi.append(1)
    return ([], [], "", ["captcha sai"]) if len(goi) == 1 else (ROWS, [], "<table>", [])
server._dvc_browser_tracuu = chap_chon
rows, loi, tt, dt = server._dvc_lay_ho_so_theo_ky(None, tu, den)
assert len(goi) == 2 and not loi and len(rows) == 2
print("PASS 2: lần 1 không ra bảng -> tự thử lại, lần 2 lấy đủ.")

# 3) lỗi dai dẳng -> báo LỖI TRA CỨU, KHÔNG kết luận chưa nộp
server._dvc_browser_tracuu = lambda drv, tu, den: ([], [], "", ["captcha sai", "captcha sai"])
xn, t, ct = server._dvc_kiem_tra_da_nop_mot_loai(None, "GTGT", tu, den)
assert xn is False and ct.startswith(server._DVC_TIEN_TO_LOI_TRA_CUU), ct
# nhưng "tra cứu được, không có hồ sơ" thì vẫn là chưa nộp
server._dvc_browser_tracuu = lambda drv, tu, den: ([], [], "<table></table>", [])
xn, t, ct = server._dvc_kiem_tra_da_nop_mot_loai(None, "GTGT", tu, den)
assert xn is False and not ct.startswith(server._DVC_TIEN_TO_LOI_TRA_CUU) and "Chưa tìm thấy" in ct
print("PASS 3: lỗi tra cứu khác hẳn 'chưa có hồ sơ': lỗi thì không kết luận chưa nộp.")

# 4) đồng bộ batch: lỗi tra cứu thì không ghi đè trạng thái cũ
src = open(os.path.join(os.path.dirname(server.__file__), "server.py"), encoding="utf-8").read()
assert "GIỮ NGUYÊN trạng thái cũ, không kết luận chưa nộp" in src and "_dvc_lay_ho_so_theo_ky(drv, tu_ky_db, den_ky_db)" in src
assert "if not str(chi_tiet).startswith(_DVC_TIEN_TO_LOI_TRA_CUU):" in src
print("PASS 4: đồng bộ batch và API kiểm tra lại không ghi đè trạng thái cũ khi lỗi tra cứu.")
print("ALL DONE")
