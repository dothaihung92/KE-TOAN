import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Ca thật (batch, CÔNG TY TNHH ... MÁY LÀM MẮT KÍNH, Q3/2026): file bảng kê và XML KHỚP (mua vào 171.863.410 / 12.137.645),
# nhưng cuối batch báo "LỆCH XML" chênh 1.235.502.221đ doanh số, 65.145.943đ thuế. Nguyên nhân: bước đối chiếu cộng thêm
# TẤT CẢ tờ khai nhập khẩu của công ty (mọi kỳ) vào tổng bảng kê, trong khi bảng kê/XML chỉ có tờ khai NK TRONG kỳ
# (Excel đã lọc theo kỳ). Nay đối chiếu dùng tờ khai NK TRONG kỳ.
f = server._mua_vao_bk_de_doi_chieu
ct23, ct24 = 171_863_410, 12_137_645                       # [23]/[24] trên XML = BK (không có TKNK trong kỳ)
bk = f(171_863_410, 12_137_645, 0, 0, 0)                   # tk_ds_nk/tk_thue_nk = TRONG kỳ = 0
assert bk == (ct23, ct24), "không báo lệch giả khi chỉ có tờ khai NK ở kỳ khác"
print("PASS 1: file khớp XML, tờ khai NK chỉ ở kỳ khác -> đối chiếu khớp (không báo lệch giả 1,2 tỷ).")

# tờ khai NK TRONG kỳ nhập SAU khi xuất Excel (bảng kê chưa có dòng TKNK): XML cộng thêm, đối chiếu cũng cộng thêm -> khớp
bk = f(171_863_410, 12_137_645, 0, 50_000_000, 4_000_000)
assert bk == (ct23 + 50_000_000, ct24 + 4_000_000)
# bảng kê ĐÃ có dòng TKNK (imp_nk_ds>0): tổng bảng kê đã gồm NK, không cộng lần nữa
assert f(221_863_410, 16_137_645, 50_000_000, 50_000_000, 4_000_000) == (221_863_410, 16_137_645)
print("PASS 2: NK trong kỳ chưa có ở bảng kê -> cộng đúng 1 lần; bảng kê đã có TKNK -> không cộng trùng.")

# vẫn báo lệch thật: bảng kê có hóa đơn NGOÀI kỳ (ds_full > ds trong kỳ)
bk = f(171_863_410 + 30_000_000, 12_137_645 + 2_400_000, 0, 0, 0)
assert bk[0] - ct23 == 30_000_000 and bk[1] - ct24 == 2_400_000
print("PASS 3: hóa đơn ngoài kỳ trong bảng kê vẫn bị phát hiện là lệch.")

src = open(os.path.join(os.path.dirname(server.__file__), "server.py"), encoding="utf-8").read()
assert "tk_ds_nk_full" not in src and "tk_thue_nk_full" not in src, "không còn cộng tờ khai NK của mọi kỳ"
assert "_mua_vao_bk_de_doi_chieu(mua_ds_full, mua_thue_full, imp_nk_ds, tk_ds_nk, tk_thue_nk)" in src
print("PASS 4: đối chiếu dùng tờ khai NK trong kỳ (không còn biến cộng mọi kỳ).")
print("ALL DONE")
