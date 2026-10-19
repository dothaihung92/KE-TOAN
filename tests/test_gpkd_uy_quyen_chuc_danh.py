import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gpkd_soan as g

# Giấy ủy quyền (TNHH 2TV): giám đốc KHÔNG đổi -> Bên A giữ chức danh giám đốc; đổi giám đốc -> Chủ tịch HĐTV.
def du(loai, **kw):
    d = {"dn": {"ten": "CÔNG TY TNHH X", "loai_hinh": "Công ty trách nhiệm hữu hạn hai thành viên trở lên", "ma_so": "1"},
         "hien_tai": {"dd_ho_ten": "Nguyễn Văn A", "dd_chuc_danh": "Giám đốc", "chu_so_huu": "Trần Thị B"},
         "uy_quyen": {"ho_ten": "Đỗ C"}, "loai": loai}
    d.update(kw); return d

def text(d):
    return "\n".join(p.text for p in d.paragraphs)

t = text(g.soan_giay_uy_quyen(du(["ten"])))
assert "NGUYỄN VĂN A" in t and "Chức danh: GIÁM ĐỐC của CÔNG TY TNHH X" in t and "CHỦ TỊCH" not in t, t
print("PASS 1: giám đốc không đổi -> chức danh GIÁM ĐỐC.")

tv = {"ht": [{"ho_ten": "Lê D", "cccd": "012345678901"}]}
t = text(g.soan_giay_uy_quyen(du(["dai_dien"], dai_dien=[{"ho_ten": "Lê D"}], thanh_vien=tv, chu_tich_moi="Lê D")))
assert "CHỦ TỊCH HỘI ĐỒNG THÀNH VIÊN của" in t, t
print("PASS 2: đổi giám đốc -> Chủ tịch HĐTV.")
print("ALL DONE")
