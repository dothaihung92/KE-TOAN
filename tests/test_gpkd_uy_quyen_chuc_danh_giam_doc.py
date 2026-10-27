import io, os, sys, zipfile
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import docx
import gpkd_soan as g

# Giấy ủy quyền: hồ sơ KHÔNG đổi người đại diện -> Bên A là GIÁM ĐỐC hiện tại (cả công ty 1 thành viên lẫn 2 thành viên). Đổi người đại diện: Chủ tịch HĐTV
# (từ 2 thành viên) / Chủ sở hữu công ty (1 thành viên). Ca thật SOL AGENCY: hồ sơ cập nhật thành viên nhưng giấy ủy quyền ghi "CHỦ TỊCH CÔNG TY".
UQ = {"ho_ten": "ĐỖ THÁI HƯNG", "ngay_sinh": "04/01/1992", "so_giay_to": "083092014700"}
def bena(loai_hinh, loai, chu_tich_moi=""):
    du = {"loai": loai, "dn": {"ten": "CÔNG TY TNHH SOL AGENCY", "ma_so": "0318807606", "loai_hinh": loai_hinh},
          "hien_tai": {"dd_ho_ten": "NGUYỄN THỊ ÁNH NGUYỆT", "dd_chuc_danh": "Giám đốc", "chu_so_huu": "NGUYỄN THỊ ÁNH NGUYỆT", "dia_chi": "34 Bùi Thế Mỹ"},
          "uy_quyen": UQ, "tao_uy_quyen": True, "dai_dien": [{"ho_ten": "NGƯỜI MỚI", "chuc_danh": "Giám đốc"}],
          "thanh_vien": {"ht": [{"ho_ten": "NGUYỄN THỊ ÁNH NGUYỆT"}, {"ho_ten": "B"}], "moi": []}, "chu_tich_moi": chu_tich_moi}
    t = [p.text for p in g.soan_giay_uy_quyen(du, {}).paragraphs]
    return next(x for x in t if x.startswith("Chức danh:"))
MOT, HAI = "Công ty trách nhiệm hữu hạn một thành viên", "Công ty trách nhiệm hữu hạn hai thành viên trở lên"
assert bena(MOT, ["cap_nhat"]) == "Chức danh: GIÁM ĐỐC của CÔNG TY TNHH SOL AGENCY", bena(MOT, ["cap_nhat"])
assert bena(HAI, ["cap_nhat"]) == "Chức danh: GIÁM ĐỐC của CÔNG TY TNHH SOL AGENCY"
assert bena(HAI, ["chu_so_huu"]).startswith("Chức danh: GIÁM ĐỐC")
assert bena(MOT, ["ten", "cshhl"]).startswith("Chức danh: GIÁM ĐỐC")
print("PASS 1: hồ sơ không đổi người đại diện (cập nhật thành viên/chuyển vốn/đổi tên...) -> chức danh Bên A = GIÁM ĐỐC, cả công ty 1 thành viên lẫn 2 thành viên.")
assert bena(HAI, ["dai_dien"]).startswith("Chức danh: CHỦ TỊCH HỘI ĐỒNG THÀNH VIÊN"), bena(HAI, ["dai_dien"])
assert bena(MOT, ["dai_dien"]).startswith("Chức danh: CHỦ SỞ HỮU CÔNG TY"), bena(MOT, ["dai_dien"])
print("PASS 2: ĐỔI người đại diện -> công ty từ 2 thành viên: CHỦ TỊCH HỘI ĐỒNG THÀNH VIÊN; công ty 1 thành viên: CHỦ SỞ HỮU CÔNG TY.")
print("ALL DONE")
