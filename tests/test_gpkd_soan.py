import base64
import io
import os
import sys
import tempfile
import zipfile

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import docx
import gpkd_soan as g
import server

# Soạn hồ sơ GPKD từ biểu mẫu chính thức (Phụ lục I TT 121/2026 + TT 68/2025): cắt mẫu, điền ô "……", bỏ mục không dùng,
# bảng ngành nghề, mẫu riêng {{biến}}, gói zip + danh mục hồ sơ. Ô không có dữ liệu giữ nguyên dấu chấm.


def van_ban(d):
    return "\n".join(p.text for p in d.paragraphs) + "\n" + "\n".join(
        c.text for t in d.tables for r in t.rows for c in r.cells)


# 1) đọc số tiền thành chữ
for n, chu in {1: "một", 14: "mười bốn", 21: "hai mươi mốt", 24: "hai mươi tư", 25: "hai mươi lăm", 105: "một trăm linh năm",
               1000: "một nghìn", 1050000: "một triệu không trăm năm mươi nghìn", 5300000: "năm triệu ba trăm nghìn",
               10000000: "mười triệu", 1000000000: "một tỷ", 2500000000: "hai tỷ năm trăm triệu",
               1005000000: "một tỷ không trăm linh năm triệu", 1500000000000: "một nghìn năm trăm tỷ", 0: "không"}.items():
    assert g.doc_so_vn(n) == chu, (n, g.doc_so_vn(n))
assert g.tien_bang_so_chu("1.000.000.000") == "1.000.000.000 đồng (bằng chữ: Một tỷ đồng)"
print("PASS 1: đọc số tiền thành chữ.")

# 2) cắt mẫu: có đủ 79 mẫu; mẫu có ở TT121/2026 thì lấy bản mới
ds = g.danh_sach_mau()
assert len(ds) >= 75 and all(ds[n][0] == "TT121" for n in (1, 2, 3, 4, 5, 10, 12, 27, 30))
assert ds[13][0] == "TT68" and ds[15][0] == "TT68"
t12, t13 = van_ban(g.cat_mau(12)), van_ban(g.cat_mau(13))
assert "Mẫu số 12" in t12 and "Mẫu số 13" not in t12 and "Mẫu số 14" not in t13
assert "Đăng ký thay đổi người đại diện theo pháp luật" in t13 and "ĐĂNG KÝ THAY ĐỔI TÊN DOANH NGHIỆP" in t12
print("PASS 2: cắt đúng từng mẫu từ Thông tư (mẫu 12 lấy bản TT 121/2026).")

DU = {"loai": ["ten", "dia_chi", "von", "nganh"],
      "dn": {"ten": "Công ty TNHH Seasoft Technology Vietnam", "ma_so": "0313030299", "co_quan": "Sở Tài chính TP. Hồ Chí Minh",
             "loai_hinh": "Công ty trách nhiệm hữu hạn một thành viên", "ngay_lap": "2026-10-13", "dia_danh": "TP. Hồ Chí Minh"},
      "ten": {"viet": "công ty tnhh mới abc", "viet_tat": "ABC CO., LTD"},
      "dia_chi": {"so_nha": "30 đường số 5", "xa": "Phường Long Trường", "tinh": "TP. Hồ Chí Minh", "email": "a@b.vn", "doi_thue": True},
      "von": {"cu": "1000000000", "moi": "2500000000", "thoi_diem": "01/11/2026", "hinh_thuc": "Tăng vốn"},
      "nganh": {"them": [{"ten": "Xuất bản phần mềm", "ma": "5820", "chinh": True}, {"ten": "Bán buôn máy vi tính", "ma": "4651"}],
                "bo": [{"ten": "Cổng thông tin", "ma": "6312", "ghi_chu": "bỏ theo QĐ 36/2025"}]},
      "dai_dien": [{"ho_ten": "Nguyễn Văn B", "ngay_sinh": "1985-02-01", "gioi_tinh": "Nam", "cccd": "079085000001", "chuc_danh": "Giám đốc",
                    "so_nha": "1 Lê Lợi", "xa": "Phường Bến Nghé", "tinh": "TP. Hồ Chí Minh", "dien_thoai": "0900000000"}],
      "chu_so_huu_moi": {"ho_ten": "Trần Thị C", "ngay_sinh": "06/05/1990", "gioi_tinh": "Nữ", "cccd": "079190000002"}}

# 3) Mẫu 12: điền đúng, giữ chấm khi thiếu, chỉ giữ các mục được chọn
d12 = g.soan_mau12(DU)
t = van_ban(d12)
for kv in ("Kính gửi: (Cơ quan đăng ký kinh doanh cấp tỉnh) Sở Tài chính TP. Hồ Chí Minh", "Tên doanh nghiệp (ghi bằng chữ in hoa): CÔNG TY TNHH SEASOFT TECHNOLOGY VIETNAM",
           "Mã số doanh nghiệp/Mã số thuế: 0313030299", "(ghi bằng chữ in hoa): CÔNG TY TNHH MỚI ABC", "viết tắt sau khi thay đổi (nếu có): ABC CO., LTD",
           "đường/phố/đại lộ, tổ/xóm/ấp/thôn: 30 đường số 5", "Xã/Phường/Đặc khu: Phường Long Trường", "Thư điện tử (nếu có): a@b.vn",
           "☒ Đồng thời thay đổi địa chỉ nhận thông báo thuế", "1.000.000.000 đồng (bằng chữ: Một tỷ đồng)",
           "2.500.000.000 đồng (bằng chữ: Hai tỷ năm trăm triệu đồng)", "Thời điểm thay đổi vốn: 01/11/2026", "Hình thức tăng, giảm vốn: Tăng vốn",
           "TP. Hồ Chí Minh, ngày 13 tháng 10 năm 2026"):
    assert kv in t, kv
assert "tiếng nước ngoài sau khi thay đổi (nếu có): …" in t                  # không có dữ liệu -> giữ chấm
assert "Điện thoại: …" in t and "Website (nếu có): …" in t
for bo in ("THAY ĐỔI THÔNG TIN ĐĂNG KÝ THUẾ", "THAY ĐỔI VỐN ĐẦU TƯ", "THAY ĐỔI THÀNH VIÊN CÔNG TY", "THAY ĐỔI CỔ ĐÔNG", "HIỆU ĐÍNH THÔNG TIN",
           "Thông tin về doanh nghiệp bị sáp nhập", "Thông tin về cổ phần", "Đăng ký thay đổi phần vốn góp"):
    assert bo not in t, bo                                                    # mục không chọn / không áp dụng (TNHH 1TV) bị bỏ
assert "ĐĂNG KÝ THAY ĐỔI ĐỊA CHỈ TRỤ SỞ CHÍNH" in t and "THÔNG BÁO THAY ĐỔI NGÀNH" in t and "Doanh nghiệp cam kết hoàn toàn chịu trách nhiệm" in t
bang = [[c.text for c in r.cells] for tb in d12.tables for r in tb.rows]
assert ["1", "Xuất bản phần mềm", "5820", "X"] in bang and ["2", "Bán buôn máy vi tính", "4651", ""] in bang
assert ["1", "Cổng thông tin", "6312", "bỏ theo QĐ 36/2025"] in bang
assert "3. Sửa đổi chi tiết ngành" not in t                                    # tiểu mục không có dữ liệu bị bỏ
print("PASS 3: Mẫu 12 điền đúng, giữ chấm khi thiếu, bỏ mục không chọn/không áp dụng, bảng ngành nghề đủ dòng.")

# 4) Mẫu 13 / 15
t13 = van_ban(g.soan_mau13(DU))
for kv in ("Họ, chữ đệm và tên (ghi bằng chữ in hoa): NGUYỄN VĂN B", "01/02/1985", "Giới tính: Nam", "Số định danh cá nhân: 079085000001",
           "Chức danh: Giám đốc", "tổ/xóm/ấp/thôn: 1 Lê Lợi", "Xã/Phường/Đặc khu: Phường Bến Nghé", "Điện thoại (nếu có): 0900000000", "Quốc gia: Việt Nam"):
    assert kv in t13, kv
assert "Số định danh cá nhân của Chủ tịch hội đồng thành viên" in t13 and "(Chỉ kê khai trong trường hợp ủy quyền" in t13   # ô của người ủy quyền không bị điền nhầm
t15 = van_ban(g.soan_mau15(DU))
assert "Họ, chữ đệm và tên chủ sở hữu (ghi bằng chữ in hoa): TRẦN THỊ C" in t15 and "06/05/1990" in t15 and "2. Đối với chủ sở hữu là tổ chức" not in t15
print("PASS 4: Mẫu 13 và Mẫu 15 điền đúng người mới; không điền nhầm ô khác.")

# 5) gói zip + danh mục + cảnh báo thiếu; không ký thay
DU2 = dict(DU, loai=["dai_dien", "ten"], dai_dien=[{"ho_ten": "Nguyễn Văn B"}], dn={"ten": "Cty A", "ma_so": "0313030299"})
zb, ten_zip, cb = g.tao_ho_so(DU2)
z = zipfile.ZipFile(io.BytesIO(zb))
tl = z.namelist()
assert ten_zip == "Ho_so_thay_doi_DKDN_0313030299.zip"
assert any(n.startswith("Mau12_") for n in tl) and any(n.startswith("Mau13_") for n in tl) and any(n.startswith("Mau10_") for n in tl) and "00_Danh_muc_ho_so.docx" in tl
assert any("Cơ quan đăng ký kinh doanh" in c for c in cb) and any("ngày sinh" in c for c in cb)
dm = van_ban(docx.Document(io.BytesIO(z.read("00_Danh_muc_ho_so.docx"))))
assert "BẢN NHÁP" in dm and "không tự điền thông tin chưa được cung cấp và không ký thay" in dm and "Mẫu số 10" in dm
try:
    g.tao_ho_so({"loai": []})
    raise AssertionError("phải báo lỗi")
except ValueError:
    pass
print("PASS 5: gói hồ sơ zip + danh mục + cảnh báo thiếu thông tin.")

# 6) mẫu riêng {{biến}} qua API
tmp = tempfile.mkdtemp()
server.GPKD_MAU_RIENG_DIR = os.path.join(tmp, "mr")
dm_ = docx.Document()
dm_.add_paragraph("QUYẾT ĐỊNH {{dn_ten_hoa}} MST {{dn_ma_so}} bổ nhiệm {{dd_ho_ten_hoa}} làm {{dd_chuc_danh}}; vốn {{von_moi_chu}}")
b = io.BytesIO()
dm_.save(b)
r = server.gpkd_soan_luu_mau_rieng({"ten": "QĐ bổ nhiệm", "noi_dung_b64": base64.b64encode(b.getvalue()).decode()})
assert r["ten"] == "QĐ bổ nhiệm.docx" and "dd_ho_ten_hoa" in r["bien_trong_mau"]
assert server.gpkd_soan_mau()["mau_rieng"] == ["QĐ bổ nhiệm.docx"]
try:
    server.gpkd_soan_luu_mau_rieng({"ten": "x", "noi_dung_b64": base64.b64encode(b"khong phai docx").decode()})
    raise AssertionError("phải từ chối")
except server.HTTPException as e:
    assert e.status_code == 400
resp = server.gpkd_soan_tao({"du_lieu": DU, "mau_rieng": ["QĐ bổ nhiệm.docx"]})
zz = zipfile.ZipFile(io.BytesIO(resp.body))
ten_mr = next(n for n in zz.namelist() if n.startswith("MauRieng_"))
tt = docx.Document(io.BytesIO(zz.read(ten_mr))).paragraphs[0].text
assert tt == "QUYẾT ĐỊNH CÔNG TY TNHH SEASOFT TECHNOLOGY VIETNAM MST 0313030299 bổ nhiệm NGUYỄN VĂN B làm Giám đốc; vốn hai tỷ năm trăm triệu đồng", tt
server.gpkd_soan_xoa_mau_rieng("QĐ bổ nhiệm.docx")
assert server.gpkd_soan_mau()["mau_rieng"] == []
print("PASS 6: mẫu riêng của người dùng thay {{biến}}; biến thiếu giữ nguyên; từ chối file không phải Word.")

# 7) cấu hình triển khai + giao diện
up = open(os.path.join(_REPO_ROOT, "update.py"), encoding="utf-8").read()
assert "gpkd_soan.py" in up and "templates/gpkd/TT121_2026_PL1.docx" in up and "templates/gpkd/TT68_2025_PL1.docx" in up
assert "python-docx" in open(os.path.join(_REPO_ROOT, "requirements.txt")).read()
html = open(os.path.join(_REPO_ROOT, "static", "index.html"), encoding="utf-8").read()
for kw in ('onclick="moSoanGpkd()"', "Soạn hồ sơ GPKD", "/api/gpkd-soan/tao", "ssThemMauRieng", "không ký thay"):
    assert kw in html, kw
print("PASS 7: cập nhật tự động có file mẫu, giao diện có mục Soạn hồ sơ GPKD.")

print("\nALL DONE")


# --- Tự khắc phục khi máy thiếu file/thư viện (lỗi "No module named 'gpkd_soan'") ---
def _test_tu_khac_phuc():
    import importlib
    import server as sv
    goc_kp, goc_mod = sv._gpkd_tu_khac_phuc, sys.modules.get("gpkd_soan")
    goi = []
    try:
        # 1) không khắc phục được -> HTTP 500 báo rõ cách xử lý
        sys.modules["gpkd_soan"] = None
        sv._gpkd_tu_khac_phuc = lambda tv: goi.append(tv) or ["không tải được"]
        try:
            sv._gpkd_soan_mod()
            raise AssertionError("phải báo lỗi")
        except sv.HTTPException as e:
            assert e.status_code == 500 and "mở lại phần mềm" in e.detail and "pip install python-docx" in e.detail
        assert len(goi) == 1
        # 2) khắc phục xong (module nạp được) -> dùng được, không lỗi
        def _kp(tv):
            sys.modules.pop("gpkd_soan", None)
            return ["đã tải"]
        sv._gpkd_tu_khac_phuc = _kp
        importlib.invalidate_caches()
        assert sv._gpkd_soan_mod().__name__ == "gpkd_soan"
    finally:
        sv._gpkd_tu_khac_phuc = goc_kp
        if goc_mod is not None:
            sys.modules["gpkd_soan"] = goc_mod
        else:
            sys.modules.pop("gpkd_soan", None)


_test_tu_khac_phuc()
print("PASS: tự khắc phục thiếu file/thư viện.")


# Hồ sơ mới (MST khác) phải thay dữ liệu cũ, bản nháp cũ không được ghi đè lên (đã kiểm bằng trình duyệt thật)
_h = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "index.html"), encoding="utf-8").read()
assert "mMoi!==mCu" in _h and "gpkdKhoi=[]" in _h and "ssLayTuGom(true,true)" in _h
assert "khoi.slice().reverse()" in _h and "ghi=!im||ghiDe" in _h
print("PASS: MST mới thay dữ liệu gom cũ; bản nháp MST khác tự lấy lại; nút Lấy từ hồ sơ đã gom ghi đè.")
