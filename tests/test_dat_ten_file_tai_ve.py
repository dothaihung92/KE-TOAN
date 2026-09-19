import io
import os
import re
import unicodedata
import zipfile

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test (hành vi + nguồn) — 2 yêu cầu về đặt tên file tải về:
#
# 1) Đồng bộ tên tờ khai giữa 2 nguồn. Trước đây cùng một loại tờ khai mà
#    ra 2 kiểu tên khác nhau: nguồn DVC lấy thẳng MÃ từ cột "Tờ khai" ->
#    01GTGT_QUY2.2026-..., còn nguồn thuế điện tử chỉ suy được nhãn ngắn
#    -> GTGT_QUY1.2025-... Người dùng chọn thống nhất theo MÃ CHÍNH THỨC.
#
# 2) Tên file Thông báo phải nói rõ là loại gì: tiếp nhận / đã chấp nhận /
#    bị từ chối, thay vì đánh số _ThongBao1/_ThongBao2 vô nghĩa.


def _nap(*ten_ham):
    ns = {'re': re, 'unicodedata': unicodedata}
    for ten in ten_ham:
        i = src.index('def ' + ten + '(')
        j = src.index('\ndef ', i + 10)
        exec(compile(src[i:j], '<test>', 'exec'), ns, ns)
    return ns


def _nap_hang(ns, ten_bien, ket_thuc):
    i = src.index(ten_bien)
    exec(compile(src[i:src.index(ket_thuc, i)], '<test>', 'exec'), ns, ns)


# ---------- 1) Tên tờ khai ----------
ns = _nap('_khong_dau', '_ma_to_khai_tu_ten', '_loai_tk_tu_ten_day_du')
_nap_hang(ns, '_TEN_TO_KHAI_MAP', '\ndef ')
_nap_hang(ns, '_TDT_LOAI_TU_KHOA = [', '_TDT_TU_BO_QUA')
_nap_hang(ns, '_TDT_TU_BO_QUA', '\n\n')
loai = ns['_loai_tk_tu_ten_day_du']

# ===== Test 1 (QUAN TRỌNG — đúng yêu cầu): tên đầy đủ ở tab Thuế điện tử
# phải ra ĐÚNG MÃ CHÍNH THỨC, khớp với tên mà nguồn DVC sinh ra. =====
mong_doi = {
    "TỜ KHAI THUẾ GIÁ TRỊ GIA TĂNG (TT80/2021)(00-Hoạt động sản xuất kinh doanh thông thường)": "01GTGT",
    "Tờ khai khấu trừ thuế thu nhập cá nhân (TT80)": "05KK-TNCN",
    "TỜ KHAI QUYẾT TOÁN THUẾ THU NHẬP CÁ NHÂN (TT80/2021)": "QTTNCN",
    "Tờ khai quyết toán thuế TNDN (TT80/2021)": "QTTNDN",
    "Bộ báo cáo tài chính": "BCTC",
}
for ten_day_du, ma_mong in mong_doi.items():
    thuc_te = loai(ten_day_du)
    assert thuc_te == ma_mong, (
        f"'{ten_day_du[:55]}' phải ra mã '{ma_mong}' (mã chính thức, khớp tên nguồn DVC) "
        f"— hiện ra '{thuc_te}'.")
print("PASS 1: tờ khai nguồn thuế điện tử đặt tên theo đúng mã chính thức (khớp nguồn DVC).")

# ===== Test 2 (không hồi quy): tên có sẵn mã "01/GTGT - ..." (kiểu cột
# Tờ khai của tab DVC) vẫn phải ra đúng mã đó. =====
assert loai("01/GTGT - Tờ khai thuế giá trị gia tăng") == "01GTGT"
assert loai("05/KK-TNCN - Tờ khai khấu trừ thuế TNCN") == "05KK-TNCN"
print("PASS 2: tên có sẵn mã tờ khai vẫn cho ra đúng mã đó.")

# ===== Test 3 (không hồi quy): tờ khai QUYẾT TOÁN không được rơi xuống
# mã chung (QTTNDN khác hẳn TNDN là tờ khai tạm tính). =====
assert loai("Tờ khai quyết toán thuế TNDN (TT80/2021)") != "TNDN", (
    "Tờ khai QUYẾT TOÁN TNDN không được đặt tên trùng nhóm với tờ khai TNDN thường.")
assert loai("TỜ KHAI QUYẾT TOÁN THUẾ THU NHẬP CÁ NHÂN (TT80/2021)") != "TNCN"
print("PASS 3: tờ khai quyết toán không bị gộp nhầm vào mã chung.")

# ---------- 2) Tên file Thông báo ----------
ns2 = _nap('_khong_dau', '_giai_ma_chu', '_doc_chu_trong_file_tai_ve', '_hau_to_ten_thong_bao')
hau_to = ns2['_hau_to_ten_thong_bao']

# ===== Test 4 (QUAN TRỌNG — đúng yêu cầu): đặt tên theo đúng loại thông
# báo đọc từ NỘI DUNG file. =====
def _xml(tieu_de):
    return f'<?xml version="1.0"?><TBao><tieuDe>{tieu_de}</tieuDe></TBao>'.encode('utf-8')

assert hau_to(_xml("Thông báo về việc tiếp nhận hồ sơ khai thuế điện tử")) == "_TB_TIEPNHAN"
assert hau_to(_xml("Thông báo V/v chấp nhận hồ sơ khai thuế điện tử")) == "_TB_CHAPNHAN"
assert hau_to(_xml("Thông báo về việc KHÔNG chấp nhận hồ sơ khai thuế điện tử")) == "_TB_TUCHOI"
print("PASS 4: đặt tên đúng loại tiếp nhận / chấp nhận / từ chối theo nội dung file.")

# ===== Test 5 (BẪY DỄ SAI): "không chấp nhận" phải ra TỪ CHỐI, tuyệt đối
# không được khớp nhầm thành "chấp nhận" (chỉ vì chuỗi con). =====
assert hau_to(_xml("Cơ quan thuế không chấp nhận hồ sơ")) == "_TB_TUCHOI", (
    "'không chấp nhận' phải ra _TB_TUCHOI — xét 'chấp nhận' trước sẽ đặt nhầm thành chấp nhận, "
    "người dùng tưởng nộp thành công trong khi thực tế bị từ chối.")
assert hau_to(_xml("Hồ sơ bị từ chối")) == "_TB_TUCHOI"
print("PASS 5: 'không chấp nhận'/'từ chối' luôn ra _TB_TUCHOI, không khớp nhầm thành chấp nhận.")

# ===== Test 6 (không hồi quy): đọc được cả khi nội dung nằm trong file
# nén, và không nhận ra thì trả rỗng để nơi gọi dùng tên chung như cũ. =====
buf = io.BytesIO()
with zipfile.ZipFile(buf, 'w') as z:
    z.writestr('tb.xml', _xml("Thông báo về việc chấp nhận hồ sơ khai thuế điện tử").decode('utf-8'))
assert hau_to(buf.getvalue()) == "_TB_CHAPNHAN", "Phải đọc được nội dung nằm trong file nén."
assert hau_to(_xml("Giấy nộp tiền")) == "", "Không nhận ra loại thì phải trả rỗng (dùng tên chung)."
assert hau_to(b"") == "", "Nội dung rỗng không được làm chết lượt tải."
print("PASS 6: đọc được file nén; không nhận ra thì trả rỗng, không ném lỗi.")

# ===== Test 6b (ĐÚNG CA THẬT người dùng báo): thông báo THỨ HAI (chấp
# nhận/từ chối) vẫn rơi về tên chung _ThongBao2. 3 nguyên nhân đã tái
# hiện được, phải xử lý hết: =====
# (a) chữ bị CẮT NGANG bởi thẻ XML -> phải bỏ thẻ rồi mới dò
assert hau_to('<tieuDe>TB về việc <b>chấp</b> <b>nhận</b> hồ sơ khai thuế điện tử</tieuDe>'
              .encode('utf-8')) == "_TB_CHAPNHAN", (
    "Chữ bị cắt ngang bởi thẻ XML ('<b>chấp</b> <b>nhận</b>') vẫn phải nhận ra — giữ nguyên thẻ thì "
    "cụm 'chấp nhận' không bao giờ khớp, đúng lỗi thông báo thứ 2 luôn về tên chung.")
# (b) file KHÔNG phải UTF-8 (gặp cả UTF-16) -> ép UTF-8 sẽ ra chuỗi rác
assert hau_to('<tieuDe>Thông báo về việc chấp nhận hồ sơ khai thuế</tieuDe>'
              .encode('utf-16')) == "_TB_CHAPNHAN", (
    "File mã hoá UTF-16 vẫn phải đọc được — ép UTF-8 cho file UTF-16 ra chuỗi rác, dò gì cũng trượt.")
# (c) BẪY NGUY HIỂM: tiêu đề mẫu ghi GỘP "chấp nhận/không chấp nhận";
#     kết quả thật nằm ở phần nội dung. Gắn nhầm nhãn TỪ CHỐI cho hồ sơ
#     ĐÃ ĐƯỢC CHẤP NHẬN là sai nghiêm trọng.
tieu_de_gop = '<tieuDe>TB về việc chấp nhận/không chấp nhận hồ sơ khai thuế điện tử</tieuDe>'
assert hau_to((tieu_de_gop + '<noiDung>Hồ sơ khai thuế điện tử của quý đơn vị đã được chấp nhận'
               '</noiDung>').encode('utf-8')) == "_TB_CHAPNHAN", (
    "Tiêu đề mẫu ghi gộp 'chấp nhận/không chấp nhận' nhưng nội dung ghi ĐÃ ĐƯỢC CHẤP NHẬN thì phải "
    "ra _TB_CHAPNHAN — chỉ dò tiêu đề sẽ gắn nhầm thành từ chối.")
assert hau_to((tieu_de_gop + '<noiDung>Hồ sơ không được chấp nhận. Lý do không chấp nhận: sai mẫu'
               '</noiDung>').encode('utf-8')) == "_TB_TUCHOI", (
    "Cùng tiêu đề gộp đó nhưng nội dung ghi KHÔNG ĐƯỢC CHẤP NHẬN thì phải ra _TB_TUCHOI.")
print("PASS 6b: xử lý đúng cả 3 ca thật — chữ bị cắt bởi thẻ, file UTF-16, và tiêu đề ghi gộp.")

# ===== Test 7 (nguồn): nơi lưu file Thông báo phải dùng hậu tố này. =====
i = src.index('def _dvc_run_batch(')
than_batch = src[i:src.index('\ndef ', i + 10)]
assert '_hau_to_ten_thong_bao(raw)' in than_batch, (
    "Chỗ lưu file Thông báo phải gọi _hau_to_ten_thong_bao(raw) để đặt tên theo loại thông báo.")
print("PASS 7: chỗ lưu file Thông báo có dùng hậu tố theo loại.")

print("\nALL DONE")
