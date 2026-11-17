import io, os, sys, zipfile
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import docx
import gpkd_soan as g

# Địa điểm kinh doanh — THAY ĐỔI NGƯỜI ĐỨNG ĐẦU: Giấy đề nghị theo bố cục bộ hồ sơ thực tế (CÔNG TY KIM KHẢI HOÀN, ĐĐKD số 1, mã 00003) + Giấy ủy quyền.
DU = {"la_chi_nhanh": True, "loai": ["dai_dien"], "tao_uy_quyen": True,
      "dn": {"ten": "CÔNG TY TNHH VÀNG BẠC ĐÁ QUÝ KIM KHẢI HOÀN", "ma_so": "0315848675", "co_quan": "Phòng Đăng ký kinh doanh Thành phố Hồ Chí Minh", "ngay_lap": "17/11/2026"},
      "cn": {"kieu": "ddkd", "ten": "ĐỊA ĐIỂM KINH DOANH SỐ 1 - CÔNG TY TNHH VÀNG BẠC ĐÁ QUÝ KIM KHẢI HOÀN", "ma_so": "00003"},
      "hien_tai": {"dd_ho_ten": "TRẦN MINH KHẢI", "dd_chuc_danh": "Giám đốc", "dia_chi": "89 Phan Đình Phùng, Phường Phú Nhuận, Thành phố Hồ Chí Minh, Việt Nam", "ngay_cap_gcn": "14/08/2019"},
      "dai_dien": [{"ho_ten": "Lê Thị Thanh Nhanh", "gioi_tinh": "Nữ", "ngay_sinh": "09/02/1974", "cccd": "086174001010", "dia_chi": "89 Phan Đình Phùng, Phường Phú Nhuận, TP Hồ Chí Minh, Việt Nam"}],
      "uy_quyen": {"ho_ten": "Đỗ Thái Hưng", "ngay_sinh": "04/01/1992", "so_giay_to": "083092014700", "ngay_cap": "09/08/2021", "noi_cap": "Cục Trưởng Cục Cảnh Sát QLHC Về TTXH", "cho_o": "32/70 Lê Thị Hồng, Phường Gò Vấp, TP.HCM", "cong_viec_tai": "Sở Tài chính TP.HCM"}}
zb, ten, cb = g.tao_ho_so(DU, {})
zf = zipfile.ZipFile(io.BytesIO(zb)); ds = zf.namelist()
f = [x for x in ds if x.startswith("Giay_de_nghi_thay_doi_nguoi_dung_dau")][0]
assert any(x.startswith("Giay_uy_quyen") for x in ds) and not any(x.startswith("Mau19") for x in ds), ds
d = docx.Document(io.BytesIO(zf.read(f)))
t = [p.text for p in d.paragraphs if p.text.strip()] + [c.text for tb in d.tables for r in tb.rows for c in r.cells]
tx = "\n".join(t)
for k in ("GIẤY ĐỀ NGHỊ", "Đăng ký thay đổi nội dung đăng ký hoạt động địa điểm kinh doanh", "Phòng Đăng ký kinh doanh Thành phố Hồ Chí Minh", "CÔNG TY TNHH VÀNG BẠC ĐÁ QUÝ KIM KHẢI HOÀN", "Mã số doanh nghiệp/Mã số thuế: 0315848675",
          "ĐỊA ĐIỂM KINH DOANH SỐ 1", "Mã số địa điểm kinh doanh: 00003", "ĐĂNG KÝ THAY ĐỔI NGƯỜI ĐỨNG ĐẦU", "Người đứng đầu địa điểm kinh doanh sau khi thay đổi:",
          "LÊ THỊ THANH NHANH", "Ngày, tháng, năm sinh: 09/02/1974", "Giới tính: Nữ", "Số định danh cá nhân: 086174001010", "Địa chỉ liên lạc: 89 Phan Đình Phùng", "Ngày 17 tháng 11 năm 2026",
          "TRẦN MINH KHẢI", "NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT"):
    assert k in tx, k
assert "Dân tộc: " in tx and "Nơi thường trú:" in tx
uq = docx.Document(io.BytesIO(zf.read([x for x in ds if x.startswith("Giay_uy_quyen")][0])))
tq = "\n".join(p.text for p in uq.paragraphs)
for k in ("Ông (Bà): TRẦN MINH KHẢI", "Chức danh: Giám đốc", "Là người đại diện theo pháp luật của CÔNG TY TNHH VÀNG BẠC ĐÁ QUÝ KIM KHẢI HOÀN", "Địa chỉ trụ sở chính: 89 Phan Đình Phùng",
          "Giấy chứng nhận đăng ký doanh nghiệp số: 0315848675 do Phòng Đăng ký kinh doanh cấp ngày 14/08/2019", "Ông (Bà): ĐỖ THÁI HƯNG", "Sinh ngày: 04/01/1992 – Dân tộc: Kinh – Quốc tịch: Việt Nam",
          "Số chứng thực: 083092014700, ngày cấp: 09/08/2021", "Chỗ ở hiện tại: 32/70 Lê Thị Hồng", "hoàn thành công việc của công ty tại Sở Tài chính TP.HCM", "Ngày 17 tháng 11 năm 2026"):
    assert k in tq, k      # Giấy ủy quyền khớp file mẫu (Nơi cấp GCN mặc định Phòng Đăng ký kinh doanh; Dân tộc/Quốc tịch mặc định Kinh/Việt Nam)
print("PASS 1: ĐĐKD đổi người đứng đầu -> Giấy đề nghị đúng bố cục hồ sơ thực tế + Giấy ủy quyền, không dùng Mẫu 19.")
# đổi thêm nội dung khác (vd địa chỉ) -> vẫn dùng Mẫu 19 đầy đủ
du2 = dict(DU, loai=["dai_dien", "dia_chi"], dia_chi={"so_nha": "1 A", "xa": "P1", "tinh": "TP.HCM"})
n2 = zipfile.ZipFile(io.BytesIO(g.tao_ho_so(du2, {})[0])).namelist()
assert any(x.startswith("Mau19") for x in n2) and not any(x.startswith("Giay_de_nghi_thay_doi_nguoi_dung_dau") for x in n2), n2
# chi nhánh (không phải ĐĐKD) đổi người đứng đầu -> Mẫu 19
du3 = dict(DU, cn=dict(DU["cn"], kieu="chi_nhanh"))
n3 = zipfile.ZipFile(io.BytesIO(g.tao_ho_so(du3, {})[0])).namelist()
assert any(x.startswith("Mau19") for x in n3), n3
# người đứng đầu mới không có số định danh -> điền khung kê khai
du4 = json = None
import copy
du4 = copy.deepcopy(DU); du4["dai_dien"][0].update(cccd="", so_ho_chieu="C1234567", ngay_cap="01/02/2020", noi_cap="Cục QLXNC")
zf4 = zipfile.ZipFile(io.BytesIO(g.tao_ho_so(du4, {})[0]))
d4 = docx.Document(io.BytesIO(zf4.read([x for x in zf4.namelist() if x.startswith("Giay_de_nghi")][0])))
tx4 = "\n".join(c.text for tb in d4.tables for r in tb.rows for c in r.cells)
assert "Dân tộc: Kinh" in tx4 and "Quốc tịch: Việt Nam" in tx4 and "C1234567" in tx4 and "Ngày cấp: 01/02/2020" in tx4 and "Nơi cấp: Cục QLXNC" in tx4, tx4
print("PASS 2: đổi thêm nội dung khác / chi nhánh -> vẫn Mẫu 19; không có số định danh -> điền khung Dân tộc/Quốc tịch/Hộ chiếu/Nơi thường trú.")
print("\nALL DONE")
