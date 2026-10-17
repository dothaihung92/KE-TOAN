import os
# Sheet "Đối chiếu" của Export Excel KHÔNG còn mục "TK NỢ MUA VÀO TỰ ĐOÁN" (người dùng yêu cầu bỏ); các mục đối chiếu khác giữ nguyên.
src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py"), encoding="utf-8").read()
assert "TK NỢ MUA VÀO TỰ ĐOÁN" not in src and "Không có dòng nào phải tự đoán TK Nợ" not in src and '"TK Nợ đã điền"' not in src
for giu in ("KẾT LUẬN ĐỐI CHIẾU", "CHI TIẾT HÓA ĐƠN LỆCH - BÁN RA", "CHI TIẾT HÓA ĐƠN LỆCH - MUA VÀO"):
    assert giu in src, giu
# 2 mục "DÒNG THUẾ SUẤT KHÔNG KHỚP TIỀN THUẾ - BÁN RA/MUA VÀO" đã bỏ khỏi sheet Đối chiếu (theo yêu cầu người dùng)
assert "DÒNG THUẾ SUẤT KHÔNG KHỚP TIỀN THUẾ - BÁN RA (" not in src and "DÒNG THUẾ SUẤT KHÔNG KHỚP TIỀN THUẾ - MUA VÀO (" not in src
assert "def them_ds_lech_thue_suat" not in src
print("PASS")
