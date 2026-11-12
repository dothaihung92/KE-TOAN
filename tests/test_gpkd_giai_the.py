import io, os, sys, zipfile
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import docx
import gpkd_soan as g

# Giải thể BƯỚC 1: Quyết định giải thể theo mẫu thực tế (9 Điều) + danh mục hồ sơ + thông tin nhập cổng. DỮ LIỆU GIẢ.
def van_ban(d):
    t = [p.text for p in d.paragraphs]
    for b in d.tables:
        for r in b.rows:
            t += [c.text for c in r.cells]
    return "\n".join(t)

def tao(du, ck=None):
    z, ten, cb = g.tao_ho_so(du, ck, False)
    zf = zipfile.ZipFile(io.BytesIO(z))
    return {n: docx.Document(io.BytesIO(zf.read(n))) for n in zf.namelist()}, cb, ten

DU = {"loai": ["giai_the"], "dn": {"ten": "CÔNG TY TNHH GIẢ ABC", "ma_so": "0300000001", "loai_hinh": "Công ty TNHH một thành viên", "dia_danh": "TP.HCM", "so_vb": "01", "ngay_lap": "24/08/2026"},
      "hien_tai": {"chu_so_huu": "NGUYỄN VĂN A", "chu_so_huu_cccd": "079000000001", "ngay_cap_gcn": "27/03/2018", "noi_cap_gcn": "Sở Kế hoạch Đầu tư thành phố Hồ Chí Minh",
                   "dia_chi": "Số 4 Phan Kế Bính, Phường Đa Kao, Quận 1, Thành phố Hồ Chí Minh, Việt Nam"},
      "giai_the": {"so_qd": "01/QĐ", "ngay_qd": "24/08/2026", "ly_do": "Không hoạt động nữa"}}
f, cb, ten = tao(DU)
assert ten == "Ho_so_giai_the_0300000001.zip", ten
assert sorted(f) == ["00_Danh_muc_ho_so_giai_the.docx", "1_Quyet_dinh_giai_the_doanh_nghiep_0300000001.docx"], sorted(f)
qd = van_ban(f["1_Quyet_dinh_giai_the_doanh_nghiep_0300000001.docx"])
for s in ("CÔNG TY TNHH GIẢ ABC", "Số: 01/QĐ", "TP.HCM, ngày 24 tháng 8 năm 2026", "Về việc giải thể doanh nghiệp", "CHỦ SỞ HỮU", "Căn cứ tình hình hoạt động của doanh nghiệp",
          "Điều 1: Giải thể doanh nghiệp: CÔNG TY TNHH GIẢ ABC", "Mã số doanh nghiệp 0300000001 ngày cấp 27/03/2018 nơi cấp Sở Kế hoạch Đầu tư thành phố Hồ Chí Minh",
          "Địa chỉ trụ sở: Số 4 Phan Kế Bính", "Điều 2: Lý do giải thể: Không hoạt động nữa", "Điều 3: Thời hạn, thủ tục thanh lý các hợp đồng đã ký kết:", "Không có hợp đồng ký kết",
          "không ký kết hợp đồng mới", "Điều 4: Thời hạn, thủ tục thanh toán các khoản nợ:", "Không có các khoản nợ phát sinh", "không huy động vốn dưới mọi hình thức",
          "Điều 5: Xử lý các nghĩa vụ phát sinh từ hợp đồng lao động:", "Doanh nghiệp sử dụng 0 lao động.", "Điều 6: Thanh lý tài sản", "Không có tài sản",
          "Điều 7: Ông/bà NGUYỄN VĂN A chủ sở hữu phải liên đới chịu trách nhiệm", "05 năm kể từ ngày nộp hồ sơ giải thể", "Điều 8: Quyết định này phải được đăng trên Cổng thông tin quốc gia",
          "Điều 9: Quyết định này có hiệu lực từ ngày ký.", "Nơi nhận:", "Như điều 8;", "(Ký, ghi rõ họ và tên)", "NGUYỄN VĂN A"):
    assert s in qd, (s, qd[:1500])
dm = van_ban(f["00_Danh_muc_ho_so_giai_the.docx"])
assert "Số quyết định: 01/QĐ" in dm and "Ngày quyết định: 24/08/2026" in dm and "Lý do giải thể: Không hoạt động nữa" in dm, dm[:800]
print("PASS 1: Quyết định giải thể (công ty 1 TV) đủ 9 Điều theo mẫu; danh mục hồ sơ ghi 3 thông tin nhập cổng.")

# tuỳ chỉnh: hợp đồng/nợ/lao động/tài sản; công ty 2 TV: Nghị quyết/Quyết định của HĐTV, ký TM. HĐTV; Giấy ủy quyền kèm theo
du2 = dict(DU, dn=dict(DU["dn"], loai_hinh="Công ty TNHH hai thành viên trở lên"), tao_uy_quyen=True,
           uy_quyen={"ho_ten": "TRẦN THỊ B", "so_giay_to": "079000000002"},
           giai_the={"so_qd": "02/QĐ-HĐTV", "ngay_qd": "25/08/2026", "ly_do": "Hết thời hạn hoạt động", "hop_dong": "Hợp đồng thuê văn phòng thanh lý trước 30/09/2026",
                     "no": "Nợ phải trả người bán 20.000.000 đồng, thanh toán trước 30/09/2026", "lao_dong": "3 người", "tai_san": "Thanh lý máy tính, chia theo tỷ lệ vốn góp"})
f2, cb2, _t = tao(du2, {"chu_so_huu": None})
assert any(n.startswith("2_Giay_uy_quyen") for n in f2), sorted(f2)
q2 = van_ban(next(v for k, v in f2.items() if k.startswith("1_")))
for s in ("Số: 02/QĐ-HĐTV", "HỘI ĐỒNG THÀNH VIÊN", "Điều 2: Lý do giải thể: Hết thời hạn hoạt động", "Hợp đồng thuê văn phòng thanh lý", "Nợ phải trả người bán 20.000.000 đồng",
          "Doanh nghiệp sử dụng 3 lao động.", "Thanh lý máy tính", "TM. HỘI ĐỒNG THÀNH VIÊN", "CHỦ TỊCH HỘI ĐỒNG THÀNH VIÊN", "các thành viên công ty phải liên đới"):
    assert s in q2, (s, q2[:2500])
assert any("Biên bản họp" in c for c in cb2) or any("2 thành viên" in c for c in cb2), cb2
print("PASS 2: công ty 2 TV: Quyết định của HĐTV, nội dung tuỳ chỉnh, ký TM. HĐTV, kèm Giấy ủy quyền, cảnh báo biên bản họp.")

# thiếu thông tin -> cảnh báo, ô trống giữ dấu chấm (không lỗi)
f3, cb3, _t = tao({"loai": ["giai_the"], "dn": {"ten": "CÔNG TY GIẢ"}})
assert any("Số quyết định" in c for c in cb3) and any("ngày cấp" in c for c in cb3), cb3
print("PASS 3: thiếu thông tin vẫn soạn được, có cảnh báo.")
print("\nALL DONE")
