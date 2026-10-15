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
for kv in ("Kính gửi: - Sở Tài chính TP. Hồ Chí Minh", "Tên doanh nghiệp (ghi bằng chữ in hoa): CÔNG TY TNHH SEASOFT TECHNOLOGY VIETNAM",
           "Mã số doanh nghiệp/Mã số thuế: 0313030299", "(ghi bằng chữ in hoa): CÔNG TY TNHH MỚI ABC", "viết tắt sau khi thay đổi (nếu có): ABC CO., LTD",
           "đường/phố/đại lộ, tổ/xóm/ấp/thôn: 30 đường số 5", "Xã/Phường/Đặc khu: Phường Long Trường", "Thư điện tử (nếu có): a@b.vn",
           "☒ Đồng thời thay đổi địa chỉ nhận thông báo thuế", "1.000.000.000 đồng (bằng chữ: Một tỷ đồng)",
           "2.500.000.000 đồng (bằng chữ: Hai tỷ năm trăm triệu đồng)", "Thời điểm thay đổi vốn: 01/11/2026", "Hình thức tăng, giảm vốn: Tăng vốn",
           "TP. Hồ Chí Minh, ngày 13 tháng 10 năm 2026"):
    assert kv in t, kv
assert "tiếng nước ngoài sau khi thay đổi (nếu có): …" in t                  # không có dữ liệu -> giữ chấm
assert "Điện thoại: …" in t and "Website (nếu có): …" in t
assert "THAY ĐỔI THÔNG TIN ĐĂNG KÝ THUẾ" in t                              # đổi địa chỉ nhận thông báo thuế -> có phần Thông báo thay đổi thông tin đăng ký thuế
for bo in ("THAY ĐỔI VỐN ĐẦU TƯ", "THAY ĐỔI THÀNH VIÊN CÔNG TY", "THAY ĐỔI CỔ ĐÔNG", "HIỆU ĐÍNH THÔNG TIN",
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
assert any(n.startswith("Mau12_") for n in tl) and any(n.startswith("Mau13_") for n in tl) and not any(n.startswith("Mau10_") for n in tl) and "00_Danh_muc_ho_so.docx" in tl      # chỉ đổi người đại diện: KHÔNG có Mẫu 10 (chỉ khi tick chủ sở hữu hưởng lợi)
assert any("Cơ quan đăng ký kinh doanh" in c for c in cb) and any("ngày sinh" in c for c in cb)
dm = van_ban(docx.Document(io.BytesIO(z.read("00_Danh_muc_ho_so.docx"))))
assert "BẢN NHÁP" in dm and "không tự điền thông tin chưa được cung cấp và không ký thay" in dm and "Mẫu số 10" in dm
try:
    g.tao_ho_so({"loai": []})
    raise AssertionError("phải báo lỗi")
except ValueError:
    pass
print("PASS 5: gói hồ sơ zip + danh mục + cảnh báo thiếu thông tin.")

# 6) đã bỏ hẳn "mẫu riêng" (không còn API, biến, thư mục): tạo hồ sơ vẫn đủ và không có file MauRieng
resp = server.gpkd_soan_tao({"du_lieu": DU})
zz = zipfile.ZipFile(io.BytesIO(resp.body))
assert not any(n.startswith("MauRieng_") for n in zz.namelist()) and any(n.startswith("Mau12_") for n in zz.namelist())
assert not hasattr(server, "gpkd_soan_luu_mau_rieng") and not hasattr(server, "GPKD_MAU_RIENG_DIR") and not hasattr(g, "dien_mau_rieng") and not hasattr(g, "CAC_BIEN")
assert set(server.gpkd_soan_mau()) == {"loai", "mau_chinh_thuc"}
print("PASS 6: đã bỏ hẳn mẫu riêng khỏi phần mềm; tạo hồ sơ vẫn đủ các biểu mẫu chính thức.")

# 7) cấu hình triển khai + giao diện
up = open(os.path.join(_REPO_ROOT, "update.py"), encoding="utf-8").read()
assert "gpkd_soan.py" in up and "templates/gpkd/TT121_2026_PL1.docx" in up and "templates/gpkd/TT68_2025_PL1.docx" in up
assert "python-docx" in open(os.path.join(_REPO_ROOT, "requirements.txt")).read()
html = open(os.path.join(_REPO_ROOT, "static", "index.html"), encoding="utf-8").read()
for kw in ("moSoanGpkd()", "Cập nhật GPKD", "1. Lấy thông tin GPKD", "2. Soạn hồ sơ", "/api/gpkd-soan/tao", "không ký thay"):
    assert kw in html, kw
assert "Mẫu riêng của bạn" not in html and 'id="ssMauRieng"' not in html          # mục "3. Mẫu riêng của bạn" đã bỏ khỏi giao diện
print("PASS 7: cập nhật tự động có file mẫu, giao diện gộp 1 mục Cập nhật GPKD (2 tab: Lấy thông tin GPKD / Soạn hồ sơ).")

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


# Dữ liệu GPKD lưu RIÊNG từng công ty (API) và giao diện nạp/lưu theo công ty đang chọn
import tempfile
_kho = {}
server._get_setting = lambda k, d="": _kho.get(k, d)
server._set_setting = lambda k, v: _kho.__setitem__(k, v)
assert server.gpkd_du_lieu_doc(1)["khoi"] == []
server.gpkd_du_lieu_luu(1, {"khoi": [{"khoi": "A", "cap": [["x", "1"]]}]})
server.gpkd_du_lieu_luu(2, {"khoi": [{"khoi": "B", "cap": [["x", "2"]]}, {"khoi": "C", "cap": []}]})
assert [k["khoi"] for k in server.gpkd_du_lieu_doc(1)["khoi"]] == ["A"]
assert len(server.gpkd_du_lieu_doc(2)["khoi"]) == 2 and server.gpkd_du_lieu_doc(2)["luc"]
try:
    server.gpkd_du_lieu_luu(3, {"khoi": "sai"})
    raise AssertionError
except server.HTTPException as e:
    assert e.status_code == 400
assert "gpkdNap()" in _h and "💾 Lưu dữ liệu" in _h and "localStorage.getItem('gpkdKhoi')" not in _h
print("PASS: dữ liệu GPKD lưu riêng từng công ty; Soạn hồ sơ chỉ dùng dữ liệu của công ty đang chọn.")


# --- Hồ sơ đổi địa chỉ trụ sở (theo bộ hồ sơ mẫu của người dùng): Mẫu 12 (TT121/2026) + thông báo thuế + Quyết định + Giấy ủy quyền ---
import io as _io
import zipfile as _zf
import datetime as _dt
import docx as _docx
import gpkd_soan as _g

_du = {"loai": ["dia_chi"], "tao_uy_quyen": True, "de_nghi_xac_nhan": True,
       "dn": {"ten": "Công ty TNHH K2 Onigiri", "ma_so": "0319239547", "loai_hinh": "Công ty trách nhiệm hữu hạn một thành viên",
              "dia_danh": "TP.HCM", "co_quan": "Phòng Đăng ký kinh doanh Thành phố Hồ Chí Minh"},
       "dia_chi": {"so_nha": "28 đường số 3 KDC Khang An", "xa": "Phường Long Trường", "tinh": "Thành phố Hồ Chí Minh", "doi_thue": True},
       "hien_tai": {"dd_ho_ten": "Đỗ Thị Ánh Tuyết", "dd_chuc_danh": "Giám đốc", "dia_chi": "194 Đường D, Phường Bình Trưng, Thành phố Hồ Chí Minh"},
       "uy_quyen": {"ho_ten": "Nguyễn Văn B", "cong_viec_tai": "Sở Tài chính TP.HCM"}}
_b, _ten, _cb = _g.tao_ho_so(_du)
_z = _zf.ZipFile(_io.BytesIO(_b))
_ds = _z.namelist()
assert any(n.startswith("Mau12") for n in _ds) and any(n.startswith("Quyet_dinh") for n in _ds) and any(n.startswith("Giay_uy_quyen") for n in _ds), _ds
_hom_nay = _dt.date.today()
_chuoi_ngay = f"ngày {_hom_nay.day} tháng {_hom_nay.month} năm {_hom_nay.year}"


def _toan_van(n):
    d = _docx.Document(_io.BytesIO(_z.read(n)))
    return "\n".join([p.text for p in d.paragraphs] + [c.text for t in d.tables for r in t.rows for c in r.cells])


_m12 = _toan_van([n for n in _ds if n.startswith("Mau12")][0])
assert "CÔNG TY TNHH K2 ONIGIRI" in _m12 and _chuoi_ngay in _m12, "Mẫu 12: tên ở tiêu đề + ngày lập mặc định = hôm nay"
assert "THÔNG BÁO THAY ĐỔI THÔNG TIN ĐĂNG KÝ THUẾ" in _m12 and "Địa chỉ nhận thông báo thuế:" in _m12 and _m12.count("28 đường số 3 KDC Khang An") >= 2
assert "☒ Đề nghị Quý Cơ quan cấp Giấy xác nhận" in _m12 and "☒ Đồng thời thay đổi địa chỉ nhận thông báo thuế" in _m12
_qd = _toan_van([n for n in _ds if n.startswith("Quyet_dinh")][0])
assert "QUYẾT ĐỊNH" in _qd and "CHỦ SỞ HỮU" in _qd and "từ 194 Đường D" in _qd and "đến địa chỉ 28 đường số 3 KDC Khang An" in _qd and _chuoi_ngay in _qd
assert "ĐỖ THỊ ÁNH TUYẾT" in _qd
_uq = _toan_van([n for n in _ds if n.startswith("Giay_uy_quyen")][0])
assert "GIẤY ỦY QUYỀN" in _uq and "NGUYỄN VĂN B" in _uq and "0319239547" in _uq and "194 Đường D" in _uq and "Sở Tài chính TP.HCM" in _uq
assert "Nộp hồ sơ và nhận kết quả đăng ký doanh nghiệp tại Phòng Đăng ký kinh doanh" in _uq and "Ngày" in _uq
assert any("thiếu ngày sinh" in c for c in _cb)
# không đổi địa chỉ thuế -> không có phần thông báo thuế; không ủy quyền -> không có giấy ủy quyền
_du2 = dict(_du, tao_uy_quyen=False, dia_chi=dict(_du["dia_chi"], doi_thue=False))
_z2 = _zf.ZipFile(_io.BytesIO(_g.tao_ho_so(_du2)[0]))
assert not any(n.startswith("Giay_uy_quyen") for n in _z2.namelist())
_m12b = "\n".join(p.text for p in _docx.Document(_io.BytesIO(_z2.read([n for n in _z2.namelist() if n.startswith("Mau12")][0]))).paragraphs)
assert "THÔNG BÁO THAY ĐỔI THÔNG TIN ĐĂNG KÝ THUẾ" not in _m12b
print("PASS: hồ sơ đổi địa chỉ — Mẫu 12 + thông báo thuế + Quyết định + Giấy ủy quyền, ngày lập mặc định hôm nay.")


# Quyết định tự soạn khi có thay đổi cần quyết định; chỉ bổ sung/cập nhật thì KHÔNG soạn (không còn ô tick)
def _ten_tep(loai, **kw):
    du = {"loai": loai, "dn": {"ten": "Cty A", "ma_so": "0300000001", "loai_hinh": "Công ty trách nhiệm hữu hạn một thành viên"}, **kw}
    return _zf.ZipFile(_io.BytesIO(_g.tao_ho_so(du)[0])).namelist()


for _l, _co in (("ten", True), ("dia_chi", True), ("von", True), ("nganh", True), ("dai_dien", True), ("chu_so_huu", True), ("bo_sung", False)):
    _n = _ten_tep([_l], bo_sung={"noi_dung": "Cập nhật số điện thoại; Cập nhật email"})
    assert any(x.startswith("Quyet_dinh") for x in _n) == _co, (_l, _n)
_nbs = _ten_tep(["bo_sung"], bo_sung={"noi_dung": "Cập nhật số điện thoại: 0900000000; Cập nhật email: a@b.vn"})
_m12bs = _g.soan_mau12({"loai": ["bo_sung"], "dn": {"ten": "Cty A"}, "bo_sung": {"noi_dung": "Cập nhật số điện thoại: 0900000000; Cập nhật email: a@b.vn"}})
_tx = "\n".join(p.text for p in _m12bs.paragraphs)
assert "B. BỔ SUNG, CẬP NHẬT THÔNG TIN ĐĂNG KÝ DOANH NGHIỆP" in _tx and "Cập nhật số điện thoại: 0900000000" in _tx and "Cập nhật email: a@b.vn" in _tx
assert "ĐĂNG KÝ THAY ĐỔI ĐỊA CHỈ TRỤ SỞ" not in _tx
assert 'id="ss_tao_quyet_dinh"' not in _h and "tự soạn" in _h
print("PASS: Quyết định tự soạn khi đổi tên/địa chỉ/vốn/ngành/người đại diện/chủ sở hữu; chỉ bổ sung thì không.")


# Số văn bản tự điền; tên người ký lấy từ dữ liệu GPKD (người đại diện / chủ sở hữu); bỏ lựa chọn "chỉ bổ sung" khỏi giao diện
_du3 = {"loai": ["dia_chi"], "dn": {"ten": "Cty A", "ma_so": "1", "so_vb": "07", "ngay_lap": "11/10/2026", "loai_hinh": "Công ty trách nhiệm hữu hạn một thành viên"},
        "dia_chi": {"so_nha": "x"}, "hien_tai": {"dd_ho_ten": "Đỗ Thị Ánh Tuyết", "chu_so_huu": "Đỗ Thị Ánh Tuyết"}}
_z3 = _zf.ZipFile(_io.BytesIO(_g.tao_ho_so(_du3)[0]))
_t12 = _docx.Document(_io.BytesIO(_z3.read([n for n in _z3.namelist() if n.startswith("Mau12")][0])))
assert "Số: 07" in _t12.tables[0].rows[1].cells[0].text
assert "NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT/\nCHỦ TỊCH CÔNG TY/CHỦ TỊCH HỘI ĐỒNG THÀNH VIÊN CỦA CÔNG TY\n(Ký, ghi họ tên)" in _t12.tables[-1].rows[-1].cells[-1].text and "ĐỖ THỊ ÁNH TUYẾT" in _t12.tables[-1].rows[-1].cells[-1].text      # công ty 1TV: Chủ tịch công ty (chủ sở hữu) ký
_qd3 = _docx.Document(_io.BytesIO(_z3.read([n for n in _z3.namelist() if n.startswith("Quyet_dinh")][0])))
assert "Số: 07" in _qd3.tables[0].rows[0].cells[0].text and "ĐỖ THỊ ÁNH TUYẾT" in _qd3.tables[1].rows[0].cells[1].text
assert "'bo_sung','Chỉ bổ sung" not in _h and "ssSoKeTiep" in _h and "chu_so_huu:''" in _h
print("PASS: số văn bản tự điền; tên ký lấy từ dữ liệu GPKD.")


# Mục chủ sở hữu hưởng lợi chỉ có khi tick; Giấy ủy quyền/Quyết định: nơi cấp mặc định + ngày Điều lệ = ngày cấp GCN
def _m12_text(loai):
    z = _zf.ZipFile(_io.BytesIO(_g.tao_ho_so({"loai": loai, "dn": {"ten": "A", "ma_so": "1"}, "dia_chi": {"so_nha": "x"}})[0]))
    d = _docx.Document(_io.BytesIO(z.read([n for n in z.namelist() if n.startswith("Mau12")][0])))
    import unicodedata
    return unicodedata.normalize("NFC", "\n".join(p.text for p in d.paragraphs)), z.namelist()


_t1, _n1 = _m12_text(["dia_chi"])
assert "CHỦ SỞ HỮU HƯỞNG LỢI" not in _t1 and "Mẫu số 10" not in _t1 and not any(x.startswith("Mau10") for x in _n1)
_t2, _n2 = _m12_text(["dia_chi", "cshhl"])
assert "THÔNG BÁO THAY ĐỔI THÔNG TIN VỀ CHỦ SỞ HỮU HƯỞNG LỢI" in _t2 and any(x.startswith("Mau10") for x in _n2)
_du4 = dict(_du, hien_tai=dict(_du["hien_tai"], ngay_cap_gcn="26/11/2014"), tao_uy_quyen=True)
_z4 = _zf.ZipFile(_io.BytesIO(_g.tao_ho_so(_du4)[0]))
_uq4 = "\n".join(p.text for p in _docx.Document(_io.BytesIO(_z4.read([n for n in _z4.namelist() if n.startswith("Giay_uy_quyen")][0]))).paragraphs)
_qd4 = "\n".join(p.text for p in _docx.Document(_io.BytesIO(_z4.read([n for n in _z4.namelist() if n.startswith("Quyet_dinh")][0]))).paragraphs)
assert "do Phòng Đăng ký kinh doanh cấp ngày 26/11/2014" in _uq4, _uq4
assert "đã được thông qua ngày 26/11/2014" in _qd4, _qd4
print("PASS: mục chủ sở hữu hưởng lợi chỉ khi tick; nơi cấp mặc định + ngày Điều lệ theo ngày cấp GCN.")


# Công ty từ 2 thành viên: Quyết định của HỘI ĐỒNG THÀNH VIÊN (theo mẫu người dùng); 1 thành viên: Quyết định của CHỦ SỞ HỮU
def _qd(loai_hinh):
    du = {"loai": ["dia_chi"], "dn": {"ten": "Cty A", "ma_so": "1", "loai_hinh": loai_hinh}, "dia_chi": {"so_nha": "y"},
          "hien_tai": {"dd_ho_ten": "Hà Thị Trúc Mai", "chu_so_huu": "Hà Thị Trúc Mai", "dia_chi": "x"}}
    z = _zf.ZipFile(_io.BytesIO(_g.tao_ho_so(du)[0]))
    n = [x for x in z.namelist() if x.startswith("Quyet_dinh") or x.startswith("Nghi_quyet")][0]
    d = _docx.Document(_io.BytesIO(z.read(n)))
    return n, "\n".join([p.text for p in d.paragraphs] + [c.text for t in d.tables for r in t.rows for c in r.cells])


_n2, _t2 = _qd("Công ty trách nhiệm hữu hạn hai thành viên trở lên")
assert _n2.startswith("Quyet_dinh_cua_hoi_dong_thanh_vien") and "HỘI ĐỒNG THÀNH VIÊN" in _t2 and "QUYẾT ĐỊNH" in _t2 and "NGHỊ QUYẾT" not in _t2
assert "Căn cứ Nghị định số 168/2025/NĐ-CP" in _t2 and "TM. Hội đồng thành viên" in _t2 and "CHỦ TỊCH HỘI ĐỒNG THÀNH VIÊN" in _t2 and "HÀ THỊ TRÚC MAI" in _t2
assert "CHỦ SỞ HỮU" not in _t2
_n1, _t1 = _qd("Công ty trách nhiệm hữu hạn một thành viên")
assert _n1.startswith("Quyet_dinh_cua_chu_so_huu") and "CHỦ SỞ HỮU" in _t1 and "HỘI ĐỒNG THÀNH VIÊN" not in _t1
print("PASS: 2 thành viên trở lên -> Quyết định của Hội đồng thành viên; 1 thành viên -> Quyết định của chủ sở hữu.")

assert html.count("Hỗ trợ thay đổi GPKD") == 0 and html.count('<div style="font-size:18px;font-weight:700;color:#b5502d">Cập nhật GPKD</div>') == 1
assert 'color:#2d7a5a">Soạn hồ sơ GPKD</div>' not in html      # không còn thẻ riêng
print("PASS: chỉ còn 1 thẻ 'Cập nhật GPKD' trong Nhập Liệu.")

# dòng "Chi tiết: …" nằm ở hàng dưới tên ngành (đoạn riêng, in nghiêng) trong bảng ngành của Mẫu 12
import copy as _cp
_du_ct = _cp.deepcopy(DU)
_du_ct["nganh"]["them"][0]["chi_tiet"] = "Xuất bản phần mềm quản lý kế toán"
_d_ct = g.soan_mau12(_du_ct)
_found = False
for _tb in _d_ct.tables:
    for _row in _tb.rows:
        for _c in _row.cells:
            if _c.text.startswith("Xuất bản phần mềm") and len(_c.paragraphs) == 2:
                assert _c.paragraphs[1].text == "Chi tiết: Xuất bản phần mềm quản lý kế toán" and _c.paragraphs[1].runs[0].italic
                _found = True
assert _found
print("PASS: Mẫu 12 in 'Chi tiết: …' nghiêng ở hàng dưới tên ngành.")
