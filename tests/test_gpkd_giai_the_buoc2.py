import io, os, sys, zipfile
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import docx
import gpkd_soan as g

# Giải thể bước 2: Thông báo về việc giải thể + Danh sách chủ nợ + Báo cáo thanh lý tài sản (theo mẫu người dùng gửi).
du = {"loai": ["giai_the2"], "dn": {"ten": "Công ty TNHH CREA CAPITAL", "ma_so": "0314948317", "loai_hinh": "Công ty trách nhiệm hữu hạn một thành viên",
                                    "ngay_lap": "19/09/2026", "dia_danh": "TP.HCM"}, "hien_tai": {"dd_ho_ten": "Jo Yeongkeun"}, "giai_the2": {}}
z, ten, cb = g.tao_ho_so(du, None, False)
zz = zipfile.ZipFile(io.BytesIO(z))
ds = zz.namelist()
assert ten == "Ho_so_giai_the_buoc2_0314948317.zip", ten
assert [x for x in ds if x.startswith(("1_Thong_bao", "2_Danh_sach_chu_no", "3_Bao_cao_thanh_ly"))].__len__() == 3 and not any("Quyet_dinh" in x for x in ds), ds
txt = lambda f: "\n".join(p.text for p in docx.Document(io.BytesIO(zz.read(f))).paragraphs) + "\n" + "\n".join(c.text for t in docx.Document(io.BytesIO(zz.read(f))).tables for r in t.rows for c in r.cells)
tb = txt([x for x in ds if x.startswith("1_")][0])
for k in ("THÔNG BÁO", "Về việc giải thể doanh nghiệp", "Số: 01.", "TP.HCM, Ngày 19 tháng 9 năm 2026", "CÔNG TY TNHH CREA CAPITAL", "0314948317", "khoản 2 Điều 207 Luật Doanh nghiệp", "JO YEONGKEUN"):
    assert k in tb, k
no = txt([x for x in ds if x.startswith("2_")][0])
for k in ("DANH SÁCH CHỦ NỢ VÀ SỐ NỢ ĐÃ THANH TOÁN", "Nợ lương", "Nợ trợ cấp thôi việc", "Nợ bảo hiểm xã hội", "Nợ thuế", "Các khoản nợ khác", "HĐLĐ", "Không có"):
    assert k in no, k
assert no.count("Không có") >= 6
ts = txt([x for x in ds if x.startswith("3_")][0])
for k in ("BÁO CÁO THANH LÝ TÀI SẢN TẠI CÔNG TY", "Nguyên giá", "Giá trị còn lại", "Hiện trạng sử dụng", "Không có"):
    assert k in ts, k
# 2 biểu mẫu bảng nằm ngang
for f in ds:
    if f.startswith(("2_", "3_")):
        s = docx.Document(io.BytesIO(zz.read(f))).sections[0]
        assert s.page_width > s.page_height, f
print("PASS 1: 3 biểu mẫu bước 2 đúng nội dung mẫu; 2 bảng khổ ngang.")
# 2: tuỳ chọn ủy quyền + giá trị người dùng nhập + thiếu dữ liệu
du2 = dict(du, tao_uy_quyen=True, giai_the2={"so_tb": "05", "ngay_tb": "2026-10-02", "noi_lap": "Hà Nội", "nguoi": "Nguyen Van A"})
du2["uy_quyen"] = {"ho_ten": "Tran B", "so_giay_to": "012345678901"}
z2, _, cb2 = g.tao_ho_so(du2, None, False)
n2 = zipfile.ZipFile(io.BytesIO(z2)).namelist()
assert any("uy_quyen" in x for x in n2), n2
t2 = "\n".join(p.text for p in docx.Document(io.BytesIO(zipfile.ZipFile(io.BytesIO(z2)).read([x for x in n2 if x.startswith("1_")][0]))).paragraphs)
assert "Số: 05." not in t2 or True
d2 = docx.Document(io.BytesIO(zipfile.ZipFile(io.BytesIO(z2)).read([x for x in n2 if x.startswith("1_")][0])))
alltxt = "\n".join(c.text for t in d2.tables for r in t.rows for c in r.cells)
assert "Số: 05." in alltxt and "Hà Nội, Ngày 2 tháng 10 năm 2026" in alltxt and "NGUYEN VAN A" in alltxt, alltxt
_, _, cb3 = g.tao_ho_so({"loai": ["giai_the2"], "dn": {}}, None, False)
assert any("tên doanh nghiệp" in c for c in cb3) and any("người đại diện" in c for c in cb3), cb3
print("PASS 2: giá trị người dùng nhập, ủy quyền kèm theo, cảnh báo khi thiếu dữ liệu.")
print("\nALL DONE")
