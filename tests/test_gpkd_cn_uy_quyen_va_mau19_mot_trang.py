import os, sys, io, zipfile, shutil, subprocess, tempfile
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, R)
import docx
import gpkd_chi_nhanh as c
import gpkd_soan as g

DU = {"la_chi_nhanh": True, "loai": ["bo_sung"], "tao_uy_quyen": True,
      "dn": {"ten": "CÔNG TY TNHH THÀNH LỢI", "ma_so": "0301899694", "co_quan": "Phòng đăng ký kinh doanh Thành phố Hồ Chí Minh", "dia_danh": "TP. Hồ Chí Minh",
             "ngay_lap": "25/11/2026", "loai_hinh": "Công ty TNHH một thành viên"},
      "cn": {"kieu": "chi_nhanh", "ten": "CHI NHÁNH CÔNG TY TNHH THÀNH LỢI", "ma_so": "0301899694-001",
             "dia_chi": {"so_nha": "12 Nguyễn Huệ", "xa": "Phường Bến Nghé", "tinh": "TP. Hồ Chí Minh"}, "dau": {"ho_ten": "Nguyễn Văn An"}},
      "hien_tai": {"dd_ho_ten": "HÀ NHỰT THÀNH", "dia_chi": "Địa chỉ công ty mẹ"},
      "uy_quyen": {"ho_ten": "ĐỖ THÁI HƯNG"}, "bo_sung": {"noi_dung": "Số điện thoại: 0903660274"}}

d = g.soan_giay_uy_quyen(DU, {})
t = "\n".join(p.text for p in d.paragraphs)
assert "NGUYỄN VĂN AN" in t and "Chức danh: Giám đốc chi nhánh" in t, t
assert "Địa chỉ chi nhánh: 12 Nguyễn Huệ, Phường Bến Nghé, TP. Hồ Chí Minh" in t and "Mã số chi nhánh (mã số thuế): 0301899694-001" in t, t
assert "CHI NHÁNH CÔNG TY TNHH THÀNH LỢI" in t and "Địa chỉ công ty mẹ" not in t, t
print("PASS 1: giấy ủy quyền chi nhánh — Bên A là người đứng đầu CN (Giám đốc chi nhánh), địa chỉ + MST chi nhánh.")

du2 = dict(DU, cn=dict(DU["cn"], dau={}))
t2 = "\n".join(p.text for p in g.soan_giay_uy_quyen(du2, {}).paragraphs)
assert "HÀ NHỰT THÀNH" in t2 and "Giám đốc chi nhánh" in t2
du3 = {k: v for k, v in DU.items() if k not in ("la_chi_nhanh",)}
t3 = "\n".join(p.text for p in g.soan_giay_uy_quyen(du3, {}).paragraphs)
assert "Địa chỉ trụ sở chính" in t3 and "Giám đốc chi nhánh" not in t3
print("PASS 2: thiếu người đứng đầu CN -> dùng người ký công ty; hồ sơ công ty thường giữ nguyên mẫu cũ.")

m = c.soan_mau19(DU, {}); g._bo_dong_trong_thua(m)
x = m.element.xml
assert 'w:type="page"' not in x, "Mẫu 19 còn dấu ngắt trang cứng"
if shutil.which("soffice") and shutil.which("pdfinfo"):
    tmp = tempfile.mkdtemp(); f = os.path.join(tmp, "m.docx"); open(f, "wb").write(g._luu_bytes(m))
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", tmp, f], capture_output=True, timeout=180)
    n = [l for l in subprocess.run(["pdfinfo", os.path.join(tmp, "m.pdf")], capture_output=True, text=True).stdout.splitlines() if l.startswith("Pages")][0]
    assert n.split()[-1] == "1", n
print("PASS 3: Mẫu 19 ngắn (chỉ mục B) gọn trong 1 trang, không còn ngắt trang cứng.")
