import io
import os
import sys
import zipfile

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import docx
import gpkd_soan as g

# 1) địa chỉ liên lạc 1 ô -> tự tách cho Mẫu 13/15
t = g._tach_dia_chi("481 Hòa Hảo, Phường Diên Hồng, TP Hồ Chí Minh, Việt Nam")
assert t == {"so_nha": "481 Hòa Hảo", "xa": "Phường Diên Hồng", "tinh": "TP Hồ Chí Minh", "quoc_gia": "Việt Nam"}, t
assert g._tach_dia_chi("12 Lê Lợi, Hà Nội")["tinh"] == "Hà Nội" and g._tach_dia_chi("")["so_nha"] == ""
assert g.so_nguyen("4.500.000.000,000") == 4_500_000_000 and g.so_nguyen("1,000,000") == 1_000_000 and g.so_nguyen("1.000.000 đồng") == 1_000_000 and g.so_nguyen("2.500,5") == 2500
print("PASS 1: tách địa chỉ 1 ô; đọc số tiền có phần thập phân của cổng.")

# 2) chuyển vốn: Quang rời đi, chuyển 4,5 tỷ cho người mới C
tv = {"ht": [{"ho_ten": "A", "von": "4.500.000.000", "bo": True, "chuyen_cho": "m0"}, {"ho_ten": "B", "von": "4.500.000.000"}], "moi": [{"ho_ten": "C", "von": "1.000.000.000"}, {"ho_ten": ""}]}
sau, tong = g.tinh_thanh_vien_sau(tv)
assert tong == 9_000_000_000 and [(x["ho_ten"], x["von"], x["ty_le"]) for x in sau] == [("B", 4_500_000_000, "50%"), ("C", 4_500_000_000, "50%")], sau      # người mới nhận chuyển nhượng: không tính 2 lần số vốn đã nhập
assert g.tinh_thanh_vien_sau({"ht": [{"ho_ten": "A", "von": "1", "bo": True, "chuyen_cho": "h0"}]})[0] == []      # không chuyển cho chính người bị gạch
sau_g, tong_g = g.tinh_thanh_vien_sau({"ht": [{"ho_ten": "A", "von": "4.500.000.000", "bo": True, "chuyen_cho": "m0", "gia": "4.000.000.000"}, {"ho_ten": "B", "von": "4.000.000.000"}], "moi": [{"ho_ten": "C", "von": "9"}]})
assert [(x["ho_ten"], x["von"], x["ty_le"]) for x in sau_g] == [("B", 4_000_000_000, "50%"), ("C", 4_000_000_000, "50%")]      # có giá chuyển nhượng: phần vốn chuyển theo giá
print("PASS 2: tính vốn/tỷ lệ sau chuyển vốn (kể cả khi nhập giá chuyển nhượng).")

DU = {"loai": ["chu_so_huu", "cshhl", "dai_dien", "nganh"],
      "dn": {"ten": "Công ty TNHH ABC", "ma_so": "0313030299", "co_quan": "Sở Tài chính TP. Hồ Chí Minh", "loai_hinh": "Công ty trách nhiệm hữu hạn hai thành viên trở lên",
             "ngay_lap": "02/10/2026", "dia_danh": "TP. Hồ Chí Minh"},
      "hien_tai": {"dd_ho_ten": "Hà Thị Trúc Mai", "dd_chuc_danh": "Tổng giám đốc", "chu_so_huu": "Hà Thị Trúc Mai", "ngay_cap_gcn": "20/08/2019"},
      "thanh_vien": {"ht": [{"ho_ten": "Hà Nhật Quang", "ngay_sinh": "22/07/1986", "gioi_tinh": "Nam", "cccd": "079086016995", "noi_cap": "Bộ Công An",
                             "dia_chi": "481 Hòa Hảo, Phường Diên Hồng, TP Hồ Chí Minh, Việt Nam", "von": "4.500.000.000", "bo": True, "chuyen_cho": "h1"},
                            {"ho_ten": "Hà Thị Trúc Mai", "ngay_sinh": "28/11/1988", "gioi_tinh": "Nữ", "cccd": "079188029565", "noi_cap": "Bộ Công An",
                             "dia_chi": "481 Hòa Hảo, Phường Diên Hồng, TP Hồ Chí Minh, Việt Nam", "von": "4.500.000.000", "thoi_han": "02/10/2026"}],
                     "moi": [{"ho_ten": "Nguyễn Văn C", "ngay_sinh": "01/01/1990", "gioi_tinh": "Nam", "cccd": "079090000001", "dia_chi": "1 Lê Lợi, Quận 1, TP Hồ Chí Minh", "von": "500.000.000"}]},
      "cshhl_ds": {"ht": [{"ho_ten": "Hà Nhật Quang", "bo": True}, {"ho_ten": "Hà Thị Trúc Mai", "ngay_sinh": "28/11/1988", "gioi_tinh": "Nữ", "cccd": "079188029565", "noi_cap": "Bộ Công An",
                           "dia_chi": "481 Hòa Hảo, Phường Diên Hồng, TP Hồ Chí Minh, Việt Nam", "truc_tiep": "90"}],
                   "moi": [{"ho_ten": "Nguyễn Văn C", "cccd": "079090000001", "truc_tiep": "10"}]},
      "dai_dien": [{"ho_ten": "Nguyễn Văn C", "ngay_sinh": "01/01/1990", "gioi_tinh": "Nam", "cccd": "079090000001", "chuc_danh": "Giám đốc",
                    "dia_chi": "1 Lê Lợi, Phường Bến Nghé, TP Hồ Chí Minh, Việt Nam"}],
      "nganh": {"them": [{"ma": "5820", "ten": "Xuất bản phần mềm", "chinh": True, "chi_tiet": "Phát triển phần mềm kế toán"}, {"ma": "4651", "ten": "Bán buôn máy vi tính"}]}}
zb, _ten, cb = g.tao_ho_so(DU)
zz = zipfile.ZipFile(io.BytesIO(zb))
ten = zz.namelist()
i6 = next(n for n in ten if n.startswith("PhuLuc_I-6"))
m10 = next(n for n in ten if n.startswith("Mau10"))
qd = next(n for n in ten if n.startswith("Quyet_dinh"))
m13 = next(n for n in ten if n.startswith("Mau13"))
assert not any(n.startswith("Mau15") for n in ten)                    # công ty từ 2 thành viên: Phụ lục I-6, không dùng Mẫu 15

def tat_ca(d):
    return "\n".join([p.text for p in d.paragraphs] + [c.text for t in d.tables for r in t.rows for c in r.cells])
d6 = docx.Document(io.BytesIO(zz.read(i6)))
t6 = tat_ca(d6)
assert "Phụ lục I-6" in t6 and "DANH SÁCH THÀNH VIÊN CÔNG TY TRÁCH NHIỆM HỮU HẠN HAI THÀNH VIÊN TRỞ LÊN" in t6
assert "HÀ NHẬT QUANG" not in t6 and "HÀ THỊ TRÚC MAI" in t6 and "NGUYỄN VĂN C" in t6, t6               # người bị gạch không còn trong danh sách
assert "9.000.000.000 VNĐ" in t6 and "94,74%" in t6 and "500.000.000 VNĐ" in t6 and "5,26%" in t6 and "079188029565" in t6 and "Bộ Công An" in t6 and "TP Hồ Chí Minh, Việt Nam" in t6
assert len(d6.tables[0].rows) == 2 + 2 and d6.sections[0].page_width > d6.sections[0].page_height      # 2 hàng tiêu đề + 2 thành viên; trang ngang
print("PASS 3: Phụ lục I-6 theo danh sách sau thay đổi (người bị gạch bỏ, vốn chuyển, tỷ lệ).")
d10 = docx.Document(io.BytesIO(zz.read(m10)))
t10 = tat_ca(d10)
assert "HÀ NHẬT QUANG" not in t10 and "HÀ THỊ TRÚC MAI" in t10 and "NGUYỄN VĂN C" in t10 and "90" in t10 and "TP. Hồ Chí Minh, ngày 2 tháng 10 năm 2026" in t10
assert "NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT/CHỦ TỊCH CÔNG TY" in t10
print("PASS 4: Mẫu 10 điền danh sách chủ sở hữu hưởng lợi (trừ người bị gạch, thêm người mới), có ngày và khối ký.")
dq = tat_ca(docx.Document(io.BytesIO(zz.read(qd))))
assert "Bổ sung ngành, nghề kinh doanh:" in dq and "- 5820 — Xuất bản phần mềm" in dq and "Chi tiết: Phát triển phần mềm kế toán" in dq and "- 4651 — Bán buôn máy vi tính" in dq, dq
assert "Thay đổi thành viên/chủ sở hữu công ty" in dq and "HÀ NHẬT QUANG chuyển nhượng" in dq and "tiếp nhận thành viên/chủ sở hữu mới" in dq and "tỷ lệ 94,74%" in dq, dq
dq_doan = [p for p in docx.Document(io.BytesIO(zz.read(qd))).paragraphs if p.text.startswith("Chi tiết:")]
assert dq_doan and dq_doan[0].runs[0].italic
print("PASS 5: Quyết định in ngành kèm dòng 'Chi tiết:' nghiêng ở hàng dưới + nội dung thay đổi thành viên.")
t13 = tat_ca(docx.Document(io.BytesIO(zz.read(m13))))
assert "1 Lê Lợi" in t13 and "Phường Bến Nghé" in t13 and "TP Hồ Chí Minh" in t13, t13       # địa chỉ 1 ô đã được tách vào các ô của Mẫu 13
print("PASS 6: địa chỉ 1 ô tự điền vào các ô số nhà/xã/tỉnh của Mẫu 13.")

# 7) công ty 1 thành viên đổi chủ -> Mẫu 15 (không có Phụ lục I-6)
du1 = {"loai": ["chu_so_huu"], "dn": {"ten": "Công ty TNHH Một TV", "ma_so": "0101", "loai_hinh": "Công ty trách nhiệm hữu hạn một thành viên"},
       "thanh_vien": {"ht": [{"ho_ten": "Cũ", "von": "1.000.000.000", "bo": True}], "moi": [{"ho_ten": "Mới", "ngay_sinh": "01/01/1990", "gioi_tinh": "Nam", "cccd": "0790", "dia_chi": "2 Hai Bà Trưng, Phường Bến Nghé, TP Hồ Chí Minh"}]}}
z1 = zipfile.ZipFile(io.BytesIO(g.tao_ho_so(du1)[0])).namelist()
assert any(n.startswith("Mau15") for n in z1) and not any(n.startswith("PhuLuc_I-6") for n in z1), z1
print("PASS 7: công ty 1 thành viên đổi chủ: Mẫu 15 với chủ mới = người đầu tiên trong danh sách mới.")
# 8) bộ hồ sơ đổi chủ + đổi giám đốc của công ty 2TV: hợp đồng chuyển nhượng, Quyết định bầu Chủ tịch HĐTV, Mẫu 12 (thành viên + thuế)
import copy
du8 = copy.deepcopy(DU)
du8["loai"] = ["chu_so_huu", "dai_dien"]
DC = "481 Hòa Hảo, Phường Diên Hồng, TP Hồ Chí Minh, Việt Nam"
du8["thanh_vien"] = {"ht": [{"ho_ten": "Bùi Thị Thanh Phụng", "ngay_sinh": "06/07/1979", "gioi_tinh": "Nữ", "cccd": "080179017183", "ngay_cap": "09/03/2022", "noi_cap": "Cục cảnh sát QLHC về TTXH",
                             "dia_chi": DC, "von": "4.500.000.000", "bo": True, "chuyen_cho": "m0", "gia": "4.500.000.000"},
                            {"ho_ten": "Hà Nhật Quang", "ngay_sinh": "22/07/1986", "gioi_tinh": "Nam", "cccd": "079086016995", "noi_cap": "Bộ Công An", "dia_chi": DC, "von": "4.500.000.000"}],
                     "moi": [{"ho_ten": "Hà Thị Trúc Mai", "ngay_sinh": "28/11/1988", "gioi_tinh": "Nữ", "cccd": "079188029565", "ngay_cap": "01/03/2023", "noi_cap": "Bộ Công An", "dan_toc": "Kinh", "dia_chi": DC}]}
du8["hien_tai"]["chu_so_huu"] = "Bùi Thị Thanh Phụng"
du8["chu_tich_moi"] = "m0"
du8["dai_dien"] = [{"ho_ten": "Hà Thị Trúc Mai", "ngay_sinh": "28/11/1988", "gioi_tinh": "Nữ", "cccd": "079188029565", "chuc_danh": "Tổng giám đốc", "dien_thoai": "0900000001"}]
z8 = zipfile.ZipFile(io.BytesIO(g.tao_ho_so(du8)[0]))
n8 = z8.namelist()
hd = next(n for n in n8 if n.startswith("Hop_dong_chuyen_nhuong"))
assert len([n for n in n8 if n.startswith("Hop_dong_chuyen_nhuong")]) == 1 and any(n.startswith("PhuLuc_I-6") for n in n8) and any(n.startswith("Mau12") for n in n8) and any(n.startswith("Mau13") for n in n8)
th = tat_ca(docx.Document(io.BytesIO(z8.read(hd))))
assert "HỢP ĐỒNG CHUYỂN NHƯỢNG PHẦN VỐN GÓP" in th and "Bên chuyển nhượng (Bên bán):" in th and "BÙI THỊ THANH PHỤNG" in th and "09/03/2022" in th, th
assert "4.500.000.000 đồng chiếm 50% vốn điều lệ" in th and "là 4.500.000.000 đồng" in th and "ngày 2 tháng 10 năm 2026" in th.lower().replace("Ngày", "ngày") and "Ông/bà: HÀ THỊ TRÚC MAI (Bên mua) giữ 01 bản" in th, th
q8 = tat_ca(docx.Document(io.BytesIO(z8.read(next(n for n in n8 if n.startswith("Quyet_dinh"))))))
assert "Bầu bà HÀ THỊ TRÚC MAI giữ chức vụ Chủ tịch Hội đồng thành viên Công ty kể từ ngày 02/10/2026" in q8 and "Số giấy tờ chứng thực cá nhân: 079188029565" in q8 and "Ngày cấp: 01/03/2023" in q8, q8
assert "Bà BÙI THỊ THANH PHỤNG thôi giữ chức vụ Chủ tịch Hội đồng thành viên" in q8 and "do đã chuyển nhượng toàn bộ phần vốn góp" in q8
t12 = tat_ca(docx.Document(io.BytesIO(z8.read(next(n for n in n8 if n.startswith("Mau12"))))))
assert "ĐĂNG KÝ THAY ĐỔI THÀNH VIÊN CÔNG TY TNHH" in t12 and "Gửi kèm" in t12 and "Giám đốc/Tổng giám đốc:HÀ THỊ TRÚC MAI" in t12 and "Giới tính: Nữ" in t12 and "28/11/1988" in t12, t12[:3000]
print("PASS 8: bộ hồ sơ đổi chủ + đổi giám đốc 2TV: hợp đồng chuyển nhượng, Quyết định bầu Chủ tịch HĐTV, Mẫu 12 (thành viên + thuế), Phụ lục I-6, Mẫu 13.")
# 9) khớp bộ hồ sơ thực tế: Quyết định bầu Chủ tịch HĐTV, Mẫu 12/13 gọn + người ký là Chủ tịch HĐTV
du9 = copy.deepcopy(du8)
du9["hien_tai"].update({"dd_ho_ten": "Bùi Thị Thanh Phụng", "dd_chuc_danh": "Tổng Giám đốc"})
du9["tao_uy_quyen"] = True
du9["uy_quyen"] = {"ho_ten": "Đỗ Thái Hưng"}
z9 = zipfile.ZipFile(io.BytesIO(g.tao_ho_so(du9)[0]))
n9 = z9.namelist()
q9 = tat_ca(docx.Document(io.BytesIO(z9.read(next(n for n in n9 if n.startswith("Quyet_dinh"))))))
assert "Về việc bầu Chủ tịch Hội đồng thành viên" in q9 and "(Điều 55, Điều 56)" in q9 and "Căn cứ Điều lệ" not in q9
assert "Điều 1: Bầu Chủ tịch Hội đồng thành viên" in q9 and "☒ Căn cước công dân" in q9 and "☐ Chứng minh nhân dân" in q9 and "Ngày hết hạn (nếu có):" in q9
assert "Điều 2: Bà BÙI THỊ THANH PHỤNG thôi giữ chức vụ Chủ tịch Hội đồng thành viên Công ty kể từ ngày 02/10/2026 do đã chuyển nhượng toàn bộ phần vốn góp tại Công ty." in q9, q9
assert "Điều 3: Thay đổi người đại diện theo pháp luật của Công ty: bà BÙI THỊ THANH PHỤNG (chức danh Tổng Giám đốc) thôi làm người đại diện theo pháp luật; bà HÀ THỊ TRÚC MAI, chức danh Tổng giám đốc, là người đại diện theo pháp luật mới" in q9, q9
assert "Điều 4: Giao cho bà HÀ THỊ TRÚC MAI (Chủ tịch Hội đồng thành viên, người đại diện theo pháp luật)" in q9 and "Như Điều 5 (để thực hiện)" in q9 and "Điều 6: Quyết định này có hiệu lực" in q9
t12_9 = tat_ca(docx.Document(io.BytesIO(z9.read(next(n for n in n9 if n.startswith("Mau12"))))))
assert "Mẫu số 12" not in t12_9 and "(Dùng trong trường hợp" not in t12_9 and "Kê khai trong trường hợp có nhà đầu tư nước ngoài" not in t12_9 and "(Cơ quan đăng ký kinh doanh cấp tỉnh)" not in t12_9
assert t12_9.rstrip().endswith("HÀ THỊ TRÚC MAI") and "NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT/\nCHỦ TỊCH CÔNG TY/CHỦ TỊCH HỘI ĐỒNG THÀNH VIÊN CỦA CÔNG TY\n(Ký, ghi họ tên)" in t12_9, t12_9[-300:]
t13_9 = tat_ca(docx.Document(io.BytesIO(z9.read(next(n for n in n9 if n.startswith("Mau13"))))))
assert t13_9.rstrip().endswith("HÀ THỊ TRÚC MAI") and "NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT/\nCHỦ TỊCH CÔNG TY/CHỦ TỊCH HỘI ĐỒNG THÀNH VIÊN CỦA CÔNG TY\n(Ký, ghi họ tên)" in t13_9 and "Mẫu số 13" not in t13_9, t13_9[-300:]
assert "ủy quyền thực hiện thủ tục đăng ký doanh nghiệp): 079188029565" in t13_9.replace("\t", ""), t13_9[:900]
du9b = copy.deepcopy(du9)
du9b["loai"] = ["chu_so_huu", "dai_dien", "cshhl"]          # tick thêm chủ sở hữu hưởng lợi: vẫn là Quyết định bầu Chủ tịch HĐTV
z9b = zipfile.ZipFile(io.BytesIO(g.tao_ho_so(du9b)[0]))
q9b = tat_ca(docx.Document(io.BytesIO(z9b.read(next(n for n in z9b.namelist() if n.startswith("Quyet_dinh"))))))
assert "Về việc bầu Chủ tịch Hội đồng thành viên" in q9b and "Điều 1: Bầu Chủ tịch Hội đồng thành viên" in q9b
t12b = tat_ca(docx.Document(io.BytesIO(z9b.read(next(n for n in z9b.namelist() if n.startswith("Mau12"))))))
assert "ĐĂNG KÝ THAY ĐỔI THÀNH VIÊN CÔNG TY TNHH" in t12b and "THÀNH VIÊN HỢP DANH CÔNG TY HỢP DANH" not in t12b, t12b[:1500]
print("PASS 9: Quyết định bầu Chủ tịch HĐTV, Mẫu 12 và Mẫu 13 gọn như bộ hồ sơ thực tế; người ký là Chủ tịch HĐTV có hiện họ tên.")
# 10) TNHH 1TV chỉ đổi giám đốc (hồ sơ Lean Helper): không Mẫu 10, ủy quyền bởi Chủ tịch công ty, Quyết định theo mẫu thực tế
du10 = {"loai": ["dai_dien"], "tao_uy_quyen": True,
        "dn": {"ten": "Công ty TNHH Lean Helper", "ma_so": "0316951072", "loai_hinh": "Công ty trách nhiệm hữu hạn một thành viên", "ngay_lap": "24/07/2026",
               "dia_danh": "TP. Hồ Chí Minh", "co_quan": "Phòng Đăng ký kinh doanh Thành phố Hồ Chí Minh", "so_vb": "01"},
        "hien_tai": {"dd_ho_ten": "Võ Thị Ri", "dd_chuc_danh": "Giám đốc", "chu_so_huu": "Võ Thị Ri", "chu_so_huu_cccd": "079156001336", "ngay_cap_gcn": "12/08/2021", "dia_chi": "91 đường Số 13, Phường Bình Trưng"},
        "dai_dien": [{"ho_ten": "Đinh Thị Huệ", "ngay_sinh": "12/07/1990", "gioi_tinh": "Nữ", "cccd": "036190003147", "ngay_cap": "23/12/2022", "noi_cap": "Bộ Công An", "chuc_danh": "Giám đốc",
                      "dia_chi": "Số nhà 91, Đường 13, Phường Bình Trưng, Thành phố Hồ Chí Minh"}],
        "uy_quyen": {"ho_ten": "Đỗ Thái Hưng", "so_giay_to": "083092014700"}}
z10 = zipfile.ZipFile(io.BytesIO(g.tao_ho_so(du10)[0]))
n10 = z10.namelist()
assert not any(n.startswith("Mau10") for n in n10), n10                  # chỉ đổi giám đốc: không có Mẫu 10
uq10 = tat_ca(docx.Document(io.BytesIO(z10.read(next(n for n in n10 if n.startswith("Giay_uy_quyen"))))))
assert "Ông (Bà): VÕ THỊ RI" in uq10 and "Chức danh: CHỦ TỊCH CÔNG TY của CÔNG TY TNHH LEAN HELPER" in uq10 and "Là người đại diện theo pháp luật của" not in uq10, uq10[:500]
m13_10 = tat_ca(docx.Document(io.BytesIO(z10.read(next(n for n in n10 if n.startswith("Mau13"))))))
assert "ủy quyền thực hiện thủ tục đăng ký doanh nghiệp): 079156001336" in m13_10.replace("\t", "") and "NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT/\nCHỦ TỊCH CÔNG TY/CHỦ TỊCH HỘI ĐỒNG THÀNH VIÊN CỦA CÔNG TY\n(Ký, ghi họ tên)" in m13_10 and m13_10.rstrip().endswith("VÕ THỊ RI"), m13_10[-400:]
qd10 = tat_ca(docx.Document(io.BytesIO(z10.read(next(n for n in n10 if n.startswith("Quyet_dinh"))))))
assert "Thay đổi Ông/Bà VÕ THỊ RI chức danh Giám đốc chuyển sang đại diện pháp luật mới là Ông/Bà ĐINH THỊ HUỆ - chức danh Giám đốc." in qd10
assert "☒ Căn cước công dân" in qd10 and "Nơi đăng ký hộ khẩu thường trú: Số nhà 91" in qd10 and "Chức vụ: Giám đốc" in qd10 and "Giao cho Ông/Bà VÕ THỊ RI" in qd10 and "Điều 4: Quyết định này có hiệu lực" in qd10, qd10
assert "1. Thay đổi người đại diện" not in qd10
# tick thêm chủ sở hữu hưởng lợi thì mới có Mẫu 10
du10b = dict(du10, loai=["dai_dien", "cshhl"])
assert any(n.startswith("Mau10") for n in zipfile.ZipFile(io.BytesIO(g.tao_ho_so(du10b)[0])).namelist())
print("PASS 10: TNHH 1TV chỉ đổi giám đốc: không Mẫu 10 (chỉ khi tick CSHHL), ủy quyền bởi Chủ tịch công ty, Mẫu 13 ký Chủ tịch công ty + số định danh, Quyết định theo mẫu thực tế.")
# 11) Mẫu 12 — mục THÔNG BÁO THAY ĐỔI THÔNG TIN ĐĂNG KÝ THUẾ (tick riêng "Thay đổi thông tin đăng ký thuế")
du11 = {"loai": ["thue"], "dn": {"ten": "Cty A", "ma_so": "0101", "loai_hinh": "Công ty trách nhiệm hữu hạn một thành viên", "ngay_lap": "14/10/2026"},
        "thue": {"kt_ho_ten": "Nguyễn Thị Kế", "kt_ngay_sinh": "01/02/1985", "kt_gioi_tinh": "Nữ", "kt_cccd": "079185000001", "kt_dien_thoai": "0900000009",
                 "gd_ho_ten": "Đinh Thị Huệ", "gd_cccd": "036190003147", "tt_so_nha": "1 Lê Lợi", "tt_xa": "Phường Bến Nghé", "tt_tinh": "TP. Hồ Chí Minh", "tt_email": "a@b.vn",
                 "ngay_bat_dau": "2019-08-20", "hach_toan": "Độc lập", "nam_tu": "01/01", "nam_den": "31/12", "lao_dong": "12", "pp_gtgt": "Khấu trừ"}}
z11 = zipfile.ZipFile(io.BytesIO(g.tao_ho_so(du11)[0]))
d11 = docx.Document(io.BytesIO(z11.read(next(n for n in z11.namelist() if n.startswith("Mau12")))))
ban = tat_ca(d11)
for kv in ("Họ, chữ đệm và tên Giám đốc/Tổng giám đốc:ĐINH THỊ HUỆ", "Họ, chữ đệm và tên Kế toán trưởng/Phụ trách kế toán:NGUYỄN THỊ KẾ", "Số định danh cá nhân: 079185000001",
           "Xã/Phường/Đặc khu: Phường Bến Nghé", "Thư điện tử (nếu có): a@b.vn", "Ngày bắt đầu hoạt động: 20/08/2019", "Áp dụng từ ngày 01/01 đến ngày 31/12", "Tổng số lao động: 12"):
    assert kv.replace(": ", ":") in ban.replace(": ", ":"), kv
# ô tick: hạch toán độc lập + khấu trừ (nằm trong bảng lồng nhau)
cells = ["".join(x.text or "" for x in tc.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")) for tc in d11.element.body.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc")]
def tick_sau(nhan):
    i = cells.index(nhan)
    return cells[i + 1].strip()
assert tick_sau("Hạch toán độc lập") == "☒" and tick_sau("Hạch toán phụ thuộc") == "□" and tick_sau("Khấu trừ") == "☒" and tick_sau("Trực tiếp trên GTGT") == "□", (tick_sau("Hạch toán độc lập"), tick_sau("Khấu trừ"))
assert "Kê khai trong trường hợp" not in ban and "Trường hợp doanh nghiệp kê khai hình thức hạch toán" not in ban     # chú thích đã bỏ như các mẫu khác
assert "ĐĂNG KÝ THAY ĐỔI THÀNH VIÊN" not in ban                                                                      # chỉ có mục thuế, không kéo theo mục thành viên
print("PASS 11: tick 'Thay đổi thông tin đăng ký thuế': Mẫu 12 có mục thuế điền Giám đốc, Kế toán trưởng, địa chỉ nhận thông báo thuế, ngày bắt đầu, hạch toán độc lập (tick), năm tài chính, lao động, phương pháp GTGT (tick).")
# 12) mục thuế: tick 'địa chỉ nhận thông báo thuế = địa chỉ công ty'; không điền trùng lặp Giám đốc (đổi người đại diện + mục thuế)
du12 = {"loai": ["thue", "dai_dien"], "dn": {"ten": "Cty A", "ma_so": "0101", "loai_hinh": "Công ty trách nhiệm hữu hạn một thành viên", "ngay_lap": "14/10/2026"},
        "hien_tai": {"dia_chi": "91 đường Số 13, Phường Bình Trưng, Hồ Chí Minh", "dd_ho_ten": "Võ Thị Ri", "chu_so_huu": "Võ Thị Ri"},
        "dai_dien": [{"ho_ten": "Võ Thị Ri", "ngay_sinh": "01/04/1956", "gioi_tinh": "Nữ", "cccd": "079156001336"}],
        "thue": {"cung_dia_chi": True, "gd_ho_ten": "Võ Thị Ri", "gd_ngay_sinh": "01/04/1956", "gd_gioi_tinh": "Nữ", "gd_cccd": "079156001336"}}
d12 = docx.Document(io.BytesIO(zipfile.ZipFile(io.BytesIO(g.tao_ho_so(du12)[0])).read(next(n for n in zipfile.ZipFile(io.BytesIO(g.tao_ho_so(du12)[0])).namelist() if n.startswith("Mau12")))))
b12 = tat_ca(d12)
assert "Họ, chữ đệm và tên Giám đốc/Tổng giám đốc:VÕ THỊ RI\n" in b12 + "\n" and "VÕ THỊ RI VÕ THỊ RI" not in b12 and "Nữ Nữ" not in b12 and "01/04/1956 01/04/1956" not in b12, b12[:1500]
assert "Số nhà/phòng, ngách/hẻm, ngõ/kiệt, đường/phố/đại lộ, tổ/xóm/ấp/thôn: 91 đường Số 13" in b12 and "Xã/Phường/Đặc khu: Phường Bình Trưng" in b12 and "Tỉnh/Thành phố trực thuộc trung ương: Hồ Chí Minh" in b12, b12[:2500]
print("PASS 12: mục thuế: địa chỉ nhận thông báo thuế lấy theo địa chỉ công ty khi tick; Giám đốc không bị điền trùng (VÕ THỊ RI / Nữ / ngày sinh chỉ 1 lần).")

# 13) chữ ký đặt lệch nhẹ mỗi lần (xoay ±6°, vị trí quanh giữa), vẫn nằm sau chữ
import base64 as _b64
import re as _re
from PIL import Image as _Im
_bio = io.BytesIO(); _Im.new("RGBA", (300, 120), (0, 0, 120, 255)).save(_bio, "PNG")
_uri = "data:image/png;base64," + _b64.b64encode(_bio.getvalue()).decode()
_rot, _pos = set(), set()
for _ in range(12):
    dk = g._van_ban_moi()
    tb = dk.add_table(rows=1, cols=1)
    c = tb.rows[0].cells[0]
    c._tc.get_or_add_tcPr()
    g._dong_trong_ky(c)                                   # ô ký có khoảng chừa phía trên họ tên -> ảnh nổi sau chữ
    pk = c.add_paragraph("HỌ TÊN")
    assert g._gan_chu_ky(pk, _uri)
    x = c._tc.xml
    assert 'behindDoc="1"' in x and "<wp:anchor" in x
    _r = int(_re.search(r'<a:xfrm rot="(-?\d+)"', x).group(1)); assert -6 * 60000 <= _r <= 6 * 60000; _rot.add(_r)
    _pos.add(_re.search(r"positionV.*?posOffset>\s*(-?\d+)", x, _re.S).group(1))
assert len(_rot) > 6 and len(_pos) > 6, (len(_rot), len(_pos))      # mỗi lần lệch khác nhau, không cố định 1 chỗ
print("PASS 13: chữ ký xoay nhẹ và lệch vị trí ngẫu nhiên quanh tên người ký, vẫn behind text.")
print("\nALL DONE")
