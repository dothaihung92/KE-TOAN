import io, os, re, sys, zipfile
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import docx
import gpkd_soan as g

# Phòng Đăng ký kinh doanh yêu cầu sửa hồ sơ chuyển đổi loại hình: (1) kê khai đầy đủ Vốn điều lệ BẰNG CHỮ (Mẫu 3 có chữ 'ằ' gõ kiểu tổ hợp nên trước đây không tìm thấy dòng),
# (2) lý do chuyển đổi chính xác, (3) thời điểm góp vốn từng thành viên ở Điều 9 Điều lệ, (4) dùng đúng "Mẫu số 6", (5) Quyết định không thuộc thành phần hồ sơ (không xuất PDF để đính kèm). DỮ LIỆU GIẢ.
def ng(ten, von, cc, gt="Nam", th=""):
    return {"ho_ten": ten, "von": von, "cccd": cc, "ngay_sinh": "01/02/1980", "gioi_tinh": gt, "quoc_tich": "Việt Nam", "dan_toc": "Kinh", "dia_chi": "1 Đường A, Phường B, TP C",
            "noi_cap": "Cục X", "ngay_cap": "01/01/2021", "thoi_han": th}
DU = {"loai": ["chuyen_doi"], "dn": {"ten": "CÔNG TY TNHH GIẢ", "ma_so": "0300000001", "loai_hinh": "Công ty TNHH một thành viên", "co_quan": "Phòng ĐKKD", "so_vb": "01", "ngay_lap": "17/11/2026"},
      "hien_tai": {"dd_ho_ten": "NGUYỄN AAA", "dd_chuc_danh": "Giám đốc", "ngay_cap_gcn": "20/03/2026"}, "ht_nganh": [{"ma": "4610", "ten": "Đại lý"}], "ht_von": "700000000",
      "ht_dia_chi": {"so_nha": "1 Đường A", "xa": "Phường B", "tinh": "TP C"}, "chuyen_doi": {"den": "2tv", "nganh_chinh": "4610"},
      "thanh_vien": {"ht": [dict(ng("NGUYỄN AAA", "700000000", "079000000001", th="30/04/2026"), cn=[{"den": "m0", "tien": "50000000"}])], "moi": [ng("TRẦN BBB", "", "079000000002", "Nữ", th="11/11/2026")]}}
def vb(d):
    t = [p.text for p in d.paragraphs]
    for b in d.tables:
        for r in b.rows:
            t += [c.text for c in r.cells]
    import unicodedata
    return unicodedata.normalize("NFC", "\n".join(t))
zb, ten, cb = g.tao_ho_so(DU, None, False)
zf = zipfile.ZipFile(io.BytesIO(zb)); ds = zf.namelist()
doc = lambda pre: docx.Document(io.BytesIO(zf.read([x for x in ds if x.startswith(pre)][0])))
gd = vb(doc("1_"))
assert "Vốn điều lệ (bằng số; VNĐ): 700.000.000 VNĐ" in gd and "Vốn điều lệ (bằng chữ; VNĐ): Bảy trăm triệu đồng" in gd, gd[gd.find("Vốn điều lệ"):][:300]
print("PASS 1: Giấy đề nghị mục 5 ghi đủ Vốn điều lệ bằng số VÀ bằng chữ.")
ly = re.search(r"Lý do chuyển đổi loại hình doanh nghiệp:([^\n]*)", gd).group(1)
assert "từ công ty trách nhiệm hữu hạn một thành viên sang công ty trách nhiệm hữu hạn hai thành viên trở lên" in ly and "số 01 ngày 17/11/2026" in ly and "CÔNG TY TNHH GIẢ" in ly, ly
du2 = dict(DU, chuyen_doi=dict(DU["chuyen_doi"], ly_do="Lý do do người dùng nhập"))
z2 = zipfile.ZipFile(io.BytesIO(g.tao_ho_so(du2, None, False)[0]))
assert "Lý do do người dùng nhập" in vb(docx.Document(io.BytesIO(z2.read([x for x in z2.namelist() if x.startswith("1_")][0]))))
print("PASS 2: lý do chuyển đổi nêu loại hình trước → sau + số/ngày quyết định; người dùng nhập tay thì dùng đúng văn bản đó.")
dl = "\n".join(p.text for p in doc("2_").paragraphs)
i = dl.find("Điều 9")
d9 = dl[i:i + 900]
assert "thời điểm góp vốn: ngày 30/04/2026" in d9 and "thời điểm góp vốn: ngày 11/11/2026" in d9, d9
print("PASS 3: Điều 9 Điều lệ nêu rõ thời điểm góp vốn từng thành viên.")
m6 = [x for x in ds if x.startswith("6_Mau6_")]
assert m6 and "Mẫu số 6" in vb(doc("6_Mau6_")) and "Phụ lục I-6" not in vb(doc("6_Mau6_")), ds
print("PASS 4: danh sách thành viên đề là 'Mẫu số 6' (không còn 'Phụ lục I-6').")
dm = vb(doc("00_"))
assert "KHÔNG đính kèm Quyết định" in dm and "ĐÚNG biểu mẫu “Mẫu số 6”" in dm
zp, _, cb = g.tao_ho_so(DU, None, True)      # xuất PDF (nếu máy có Word/LibreOffice): Quyết định (5_) không có bản PDF scan để đính kèm
tp = zipfile.ZipFile(io.BytesIO(zp)).namelist()
assert not any(x.startswith("PDF/5_") for x in tp), tp
print("PASS 5: danh mục có lưu ý của Sở; Quyết định giữ nội bộ, không xuất PDF scan để đính kèm.")
# thiếu ngày góp vốn -> cảnh báo
du3 = dict(DU, thanh_vien={"ht": [ng("NGUYỄN AAA", "700000000", "079000000001")], "moi": [ng("TRẦN BBB", "", "079000000002", "Nữ")]})
assert any("thời điểm (ngày) góp vốn" in x for x in g.tao_ho_so(du3, None, False)[2]), "phải cảnh báo thiếu ngày góp vốn"
print("PASS 6: thiếu ngày góp vốn -> cảnh báo.")
print("\nALL DONE")
