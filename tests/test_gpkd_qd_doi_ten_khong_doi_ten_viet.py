import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gpkd_soan as g

# Quyết định: thay đổi tên mà KHÔNG đổi tên tiếng Việt (ô Tên mới tiếng Việt để trống) -> không ghi "Thay đổi tên công ty từ ... thành ……",
# chỉ ghi tên tiếng nước ngoài / tên viết tắt thay đổi; hồ sơ không báo thiếu tên tiếng Việt.
base = {"loai": ["ten", "dia_chi"], "dn": {"ten": "CÔNG TY TNHH DỊCH VỤ FXC", "ma_so": "0316627693", "co_quan": "Phòng Đăng ký kinh doanh",
                                         "loai_hinh": "Công ty trách nhiệm hữu hạn một thành viên"},
        "hien_tai": {"chu": "TRẦN ĐỨC HOÀNG", "dd_ho_ten": "TRẦN ĐỨC HOÀNG", "dia_chi": "78/5 Bình Lợi, Phường Bình Lợi Trung, Hồ Chí Minh", "ngay_dieu_le": "08/12/2020"},
        "dia_chi": {"so_nha": "78/3 Bình Lợi", "xa": "Phường Bình Lợi Trung", "tinh": "TP Hồ Chí Minh"}}
chu = lambda t: "\n".join(p.text for p in g.soan_quyet_dinh(dict(base, ten=t), {}).paragraphs)
t1 = chu({"viet": "", "nuoc_ngoai": "FXC SERVICES COMPANY LIMITED", "viet_tat": "CTY TNHH DV FXC"})
assert "Thay đổi tên công ty từ" not in t1 and "……" not in t1.split("Điều 1")[1].split("2. Thay đổi địa chỉ")[0], t1
assert "1. Thay đổi tên công ty viết bằng tiếng nước ngoài thành FXC SERVICES COMPANY LIMITED; tên viết tắt của công ty thành CTY TNHH DV FXC." in t1, t1
assert "2. Thay đổi địa chỉ trụ sở chính công ty từ 78/5 Bình Lợi" in t1
t2 = chu({"viet": "", "nuoc_ngoai": "", "viet_tat": "CTY TNHH DV FXC"})
assert "1. Thay đổi tên viết tắt của công ty thành CTY TNHH DV FXC." in t2 and "tiếng nước ngoài" not in t2
t3 = chu({"viet": "Công ty TNHH ABC", "nuoc_ngoai": "ABC CO", "viet_tat": ""})
assert "1. Thay đổi tên công ty từ CÔNG TY TNHH DỊCH VỤ FXC thành CÔNG TY TNHH ABC; tên viết bằng tiếng nước ngoài: ABC CO." in t3
print("PASS 1: Quyết định — không đổi tên tiếng Việt thì chỉ ghi tên tiếng nước ngoài / viết tắt thay đổi.")

th = g._kiem_thieu(dict(base, ten={"viet": "", "nuoc_ngoai": "FXC SERVICES COMPANY LIMITED", "viet_tat": ""}))
assert not any("Tên doanh nghiệp mới" in x for x in th), th
th = g._kiem_thieu(dict(base, ten={"viet": "", "nuoc_ngoai": "", "viet_tat": ""}))
assert any("Tên doanh nghiệp mới" in x for x in th), th
print("PASS 2: kiểm thiếu — chỉ báo thiếu khi không có tên mới nào.")
