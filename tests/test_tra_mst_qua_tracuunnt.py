import os
import re
import html as _html_mod

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test cho tracuunnt.gdt.gov.vn — cổng tra cứu CÔNG KHAI CHÍNH
# THỨC của Tổng cục Thuế (mstdn.jsp), KHÔNG cần đăng nhập công ty nào, xác
# nhận qua cURL thật chụp từ DevTools:
#   GET  /tcnnt/captcha.png            -> ảnh PNG
#   POST /tcnnt/mstdn.jsp (cm=cm&mst=..&captcha=..) -> bảng HTML kết quả,
#        cột cuối "Trạng thái MST" (VD "NNT đang hoạt động")
# và nội dung trang HTML kết quả thật (dán từ DevTools) cho MST có NHIỀU
# dòng (trụ sở chính + các chi nhánh "gốc-001", "gốc-002"...) trong CÙNG 1
# bảng — phải khớp ĐÚNG CHÍNH XÁC cột MST, không phải startswith.
#
# Nguồn này từng bị BỎ (captcha khó/ddddocr không nạp được trên 1 số máy),
# nhưng người dùng yêu cầu: "hãy tạm ngưng dùng VietQR/masothue.com/XInvoice
# mà tập trung xử lý test chạy kiểm tra qua tracuunnt.gdt.gov.vn" — nên đã
# thêm lại làm nguồn DUY NHẤT đang bật trong chuỗi tra MST (tạm thời, để
# đánh giá riêng độ ổn định của nguồn này).


def _than_ham(ten):
    i = src.index('def ' + ten + '(')
    j_def = src.index('\ndef ', i + 10)
    j_deco = src.find('\n@', i + 10)
    j = min(j_def, j_deco) if 0 <= j_deco < j_def else j_def
    return src[i:j]


def _nap(*ten_ham):
    ns = {}
    exec('import unicodedata, re, html as _html_mod, threading', ns)
    for t in ten_ham:
        exec(_than_ham(t), ns)
    return ns


# ===== Test 1 (QUAN TRỌNG — đúng cấu trúc trang thật): dò ĐÚNG dòng khớp
# CHÍNH XÁC cột MST trong bảng kết quả — trang trả về CẢ trụ sở chính lẫn chi
# nhánh (MST dạng "gốc-001") trong CÙNG 1 bảng, lấy nhầm dòng đầu tiên/dòng
# chứa chuỗi con MST sẽ có thể lấy nhầm tình trạng của CHI NHÁNH thay vì công
# ty cần tra. Test bằng HTML MÔ PHỎNG đúng cấu trúc trang thật (người dùng đã
# dán nội dung thật: 4 dòng — 1 trụ sở chính + 3 chi nhánh, cột cuối "Trạng
# thái MST" ghi "NNT đang hoạt động"). =====
ns = _nap('_khong_dau', '_phan_loai_trang_thai_mst', '_doc_bang_trang_thai_tracuunnt')
doc_bang = ns['_doc_bang_trang_thai_tracuunnt']

HTML_MAU = """
<table>
<tr><th>STT</th><th>MST</th><th>Tên người nộp thuế</th><th>Địa chỉ</th><th>CQT</th><th>Trạng thái MST</th></tr>
<tr><td>1</td><td>0315458241</td><td>CÔNG TY TNHH THƯƠNG MẠI DỊCH VỤ KINH DOANH PHỤ TÙNG Ô TÔ ANH KHÔI</td>
    <td>27J5 Đường DN12, Phường Đông Hưng Thuận, TP Hồ Chí Minh</td><td>Thuế cơ sở 12 Thành phố Hồ Chí Minh</td>
    <td>NNT đang hoạt động</td></tr>
<tr><td>2</td><td>0315458241-001</td><td>CHI NHÁNH CÔNG TY TNHH... ANH KHÔI</td>
    <td>678 Trường Chinh, TP Hồ Chí Minh</td><td>Thuế cơ sở 12 Thành phố Hồ Chí Minh</td>
    <td>NNT đang hoạt động</td></tr>
<tr><td>3</td><td>0315458241-003</td><td>CHI NHÁNH TÂN SƠN...</td>
    <td>377 Đường Tân Sơn, TP Hồ Chí Minh</td><td>Thuế cơ sở 16 Thành phố Hồ Chí Minh</td>
    <td>Đang xác minh tình trạng hoạt động tại địa chỉ đã đăng ký</td></tr>
</table>
"""

assert doc_bang(HTML_MAU, "0315458241") == "NNT đang hoạt động", (
    "Phải lấy đúng cột 'Trạng thái MST' của dòng có MST KHỚP CHÍNH XÁC (trụ sở chính, dòng 1) — trang "
    "thật trả về nhiều dòng chi nhánh trong CÙNG 1 bảng, lấy nhầm dòng khác là sai tình trạng công ty.")
assert doc_bang(HTML_MAU, "0315458241-003") == "Đang xác minh tình trạng hoạt động tại địa chỉ đã đăng ký", (
    "Khớp đúng dòng chi nhánh khi tra thẳng đúng mã chi nhánh đó (không lẫn sang trụ sở chính) — chi "
    "nhánh 003 có tình trạng KHÁC hẳn trụ sở chính trong ví dụ này, phải phân biệt được.")
assert doc_bang(HTML_MAU, "9999999999") == "", "MST không có trong bảng phải trả rỗng (không suy đoán/lấy nhầm)."
assert ns['_phan_loai_trang_thai_mst'](doc_bang(HTML_MAU, "0315458241")) == ("Đang hoạt động", False), (
    "'NNT đang hoạt động' (đúng nguyên văn cổng trả về, có tiền tố 'NNT') phải nhận diện đúng là KHÔNG "
    "cảnh báo — nếu chỉ dò 'đang hoạt động' không tính tiền tố 'NNT ' thì vẫn phải khớp vì kiểm tra dùng "
    "substring, không phải so khớp toàn chuỗi.")
assert ns['_phan_loai_trang_thai_mst'](doc_bang(HTML_MAU, "0315458241-003"))[1] is True, (
    "'Đang xác minh tình trạng hoạt động tại địa chỉ đã đăng ký' phải bị coi là CẢNH BÁO (tô đỏ) — đúng "
    "dấu hiệu rủi ro NCC 'ma' cần cảnh báo khi khấu trừ thuế GTGT.")
print("PASS 1: dò đúng dòng khớp CHÍNH XÁC cột MST trong bảng có nhiều dòng (trụ sở + chi nhánh), không lấy nhầm dòng khác.")

# ===== Test 2 (không hồi quy — quy trình 3 bước đúng thứ tự): phải GET trang
# trước để có JSESSIONID (sess_thu.get), rồi GET captcha.png (gắn với đúng
# session đó, sess.get), rồi POST mstdn.jsp (sess.post) — dùng CHUNG 1 session
# cho cả 3 bước, KHÔNG tạo session mới giữa chừng (nếu không captcha sẽ không
# khớp session lúc POST, tra cứu luôn thất bại). =====
than_tc = _than_ham('_tra_cuu_mst_qua_tracuunnt')
assert 'sess_thu.get(' in than_tc and than_tc.count('sess.get(') >= 1 and than_tc.count('sess.post(') >= 1, (
    "Phải dùng CHUNG 1 session cho cả bước mở trang, lấy captcha, và POST tra cứu.")
vt_mo_trang = than_tc.find('sess_thu.get(')
vt_captcha = than_tc.find('r_cap = sess.get(')
vt_post = than_tc.find('sess.post(')
assert 0 < vt_mo_trang < vt_captcha < vt_post, (
    "Thứ tự PHẢI là: mở trang lấy JSESSIONID -> lấy captcha.png (gắn với session đó) -> POST tra cứu "
    "kèm mã captcha đã giải — sai thứ tự thì captcha không khớp session lúc tra cứu.")
assert '_ocr_png(' in than_tc, "Phải dùng bộ giải captcha PNG sẵn có (_ocr_png) — captcha ở đây là ẢNH PNG, khác captcha SVG của hoadondientu."
print("PASS 2: quy trình 3 bước đúng thứ tự (mở trang -> lấy captcha -> tra cứu), dùng chung 1 session.")

# ===== Test 2b (QUAN TRỌNG — đúng ca thật người dùng báo): captcha trang này
# KHÓ, tự nhập tay còn phải thử 3-5 lần -> phải THỬ LẠI với ảnh captcha MỚI
# nhiều lần trong CÙNG 1 session trước khi chịu thua, không phải chỉ 1 lần. =====
assert '_SO_LAN_THU_CAPTCHA_TRACUUNNT' in src, "Phải có hằng số số lần thử captcha (không phải chỉ thử 1 lần)."
m_solan = re.search(r'^_SO_LAN_THU_CAPTCHA_TRACUUNNT\s*=\s*(\d+)', src, re.M)
assert m_solan and int(m_solan.group(1)) >= 3, (
    "Số lần thử captcha phải đủ nhiều (>=3) — người dùng xác nhận tự nhập tay còn phải thử 3-5 lần mới "
    "ra, thử đúng 1 lần rồi bỏ cuộc sẽ gần như luôn thất bại với captcha khó kiểu này.")
assert 'for lan in range(1, _SO_LAN_THU_CAPTCHA_TRACUUNNT' in than_tc, (
    "Phải có vòng lặp thử lại lấy captcha MỚI (không dùng lại đúng 1 ảnh captcha đã sai nhiều lần).")
print("PASS 2b: thử lại captcha nhiều lần (ảnh mới mỗi lần) trong cùng 1 session trước khi chịu thua, đúng thực tế captcha khó.")

# ===== Test 2c (QUAN TRỌNG — đúng ca thật người dùng báo lỗi SSL): lỗi
# 'unable to get local issuer certificate' của curl_cffi trên 1 số máy phải
# được xử lý bằng cách đổi sang requests thường (VẪN xác thực TLS đầy đủ,
# chỉ khác kho chứng chỉ) — TUYỆT ĐỐI không được tắt xác thực TLS (verify=False)
# để né lỗi này. =====
assert 'def _loi_ssl_chung_thuc' in src, "Phải có hàm nhận diện lỗi xác thực chứng chỉ TLS."
than_ssl_fn = _than_ham('_loi_ssl_chung_thuc')
assert 'certificate' in than_ssl_fn.lower() and 'ssl' in than_ssl_fn.lower(), (
    "Phải dò đúng các từ khoá lỗi chứng chỉ TLS (certificate/ssl/issuer).")
assert '_loi_ssl_chung_thuc(e)' in than_tc, (
    "_tra_cuu_mst_qua_tracuunnt() phải dùng _loi_ssl_chung_thuc() để phát hiện lỗi SSL và đổi cách kết nối.")
assert 'verify=False' not in than_tc and 'verify = False' not in than_tc, (
    "TUYỆT ĐỐI không được tắt xác thực TLS (verify=False) để né lỗi SSL — đây là lỗ hổng bảo mật nghiêm "
    "trọng (mất khả năng phát hiện tấn công man-in-the-middle), phải xử lý bằng cách đổi kho chứng chỉ "
    "(đổi sang requests thường) thay vì tắt xác thực.")
assert "for dung_curl_cffi in (True, False):" in than_tc, (
    "Phải thử curl_cffi (giả lập Chrome, cần cho WAF) trước, rồi mới rớt về requests thường khi gặp lỗi SSL.")
print("PASS 2c: lỗi xác thực chứng chỉ TLS (SSL) được xử lý bằng cách đổi kho chứng chỉ, không tắt xác thực TLS.")

# ===== Test 3 (AN TOÀN — không suy đoán): không dò ra tình trạng (bảng trống/
# không khớp MST/tình trạng lạ) thì PHẢI trả thất bại, tuyệt đối không mặc
# định "đang hoạt động". =====
assert 'canh_bao is None' in than_tc and 'return False, "", None' in than_tc, (
    "Không dò được tình trạng (hoặc tình trạng lạ chưa nhận diện) thì phải trả THẤT BẠI, không suy đoán.")
assert "if not trang_thai_goc:" in than_tc, (
    "Không tìm thấy đúng dòng MST trong bảng thì phải trả thất bại (không phải mặc định thành công).")
print("PASS 3: không dò được tình trạng thì coi là thất bại, không suy đoán 'đang hoạt động'.")

# ===== Test 4 (đúng ca thật — tránh lãng phí lượt gọi hàng loạt): 1 lượt xuất
# Excel có thể phải tra hàng trăm MST; nếu trang chặn/lỗi liên tục thì phải có
# ngưỡng TẮT tạm thời, không cứ thử lại vô ích cho từng MST còn lại. =====
assert '_TRACUUNNT_NGUONG_TAT' in src and '_tracuunnt_danh_dau(' in than_tc, (
    "Phải có bộ đếm lỗi liên tiếp + ngưỡng tạm tắt nguồn này trong 1 lượt xuất Excel.")
print("PASS 4: có ngưỡng tạm tắt khi lỗi liên tiếp, tránh lãng phí lượt gọi cho hàng trăm MST còn lại.")

# ===== Test 5 (QUAN TRỌNG — đúng yêu cầu người dùng đã CHỐT: "GIữ
# tracuunnt.gdt.gov.vn + XInvoice, BỊ VietQR/masothue.com"): chuỗi tra MST
# PERMANENT là tracuunnt.gdt.gov.vn (ưu tiên 1) -> XInvoice (dự phòng) —
# VietQR/masothue.com đã BỎ HẲN (xoá code, không phải tạm ngưng). =====
than_chinh = _than_ham('_tra_cuu_trang_thai_mst')
assert '_tra_cuu_mst_qua_tracuunnt(' in than_chinh, (
    "_tra_cuu_trang_thai_mst() phải gọi _tra_cuu_mst_qua_tracuunnt() (nguồn ưu tiên 1).")
assert '_goi_1_lan_xinvoice(' in than_chinh, (
    "_tra_cuu_trang_thai_mst() phải gọi _goi_1_lan_xinvoice() làm nguồn dự phòng khi "
    "tracuunnt.gdt.gov.vn không tra được.")
assert than_chinh.index('_tra_cuu_mst_qua_tracuunnt(') < than_chinh.index('_goi_1_lan_xinvoice('), (
    "tracuunnt.gdt.gov.vn phải được gọi TRƯỚC XInvoice (đúng thứ tự ưu tiên: nguồn chính thức, "
    "miễn phí, không hạn mức gói trước; XInvoice dự phòng sau, tốn hạn mức key).")
assert 'def _tra_cuu_mst_qua_vietqr(' not in src, (
    "VietQR (api.vietqr.io) phải đã BỎ HẲN khỏi file (xoá code, theo yêu cầu người dùng), "
    "không chỉ tạm ngưng gọi.")
assert 'def _tra_cuu_mst_qua_masothue(' not in src, (
    "masothue.com phải đã BỎ HẲN khỏi file (xoá code, theo yêu cầu người dùng), "
    "không chỉ tạm ngưng gọi.")
print("PASS 5: _tra_cuu_trang_thai_mst() gọi tracuunnt.gdt.gov.vn (ưu tiên 1) rồi XInvoice (dự phòng); "
      "VietQR/masothue.com đã bỏ hẳn khỏi file.")

# ===== Test 6 (không hồi quy — endpoint chẩn đoán riêng, không cần cid): phải
# có endpoint chẩn đoán đơn giản (không cần biết id công ty nào, vì nguồn này
# không cần đăng nhập) để test nhanh khi trang đổi cấu trúc. =====
assert '/api/chan-doan-mst-tracuunnt' in src and 'def chan_doan_mst_tracuunnt' in src, (
    "Phải có endpoint chẩn đoán cho tracuunnt.gdt.gov.vn.")
than_cd = _than_ham('chan_doan_mst_tracuunnt')
assert '_tra_cuu_mst_qua_tracuunnt(' in than_cd, "Endpoint chẩn đoán phải gọi đúng hàm tra cứu thật (không phải mô phỏng riêng)."
print("PASS 6: có endpoint chẩn đoán /api/chan-doan-mst-tracuunnt, không cần biết id công ty nào.")

# ===== Test 7 (QUAN TRỌNG — đúng ca thật: SSL lỗi ở CẢ curl_cffi LẪN requests
# thường trên máy người dùng, "SSL certificate problem: unable to get local
# issuer certificate" / SSLCertVerificationError): phải dùng kho chứng chỉ
# GỐC CỦA HỆ ĐIỀU HÀNH (truststore) thay cho kho chứng chỉ certifi đóng gói
# sẵn — trình duyệt tin cậy được trang .gov.vn này (dùng kho chứng chỉ hệ
# điều hành) nhưng Python (certifi) thì không. Phải bật NGAY LÚC KHỞI ĐỘNG,
# TRƯỚC MỌI request (inject_into_ssl() vá thẳng ssl.SSLContext) — không phải
# tắt xác thực TLS, chỉ đổi NGUỒN kho chứng chỉ dùng để xác thực. =====
assert 'truststore' in open(os.path.join(_REPO_ROOT, 'requirements.txt'), encoding='utf-8').read(), (
    "Phải có truststore trong requirements.txt để start.bat tự cài cho người dùng ở lần chạy sau "
    "(start.bat tự pip install lại khi requirements.txt mới hơn .installed).")
vt_import_requests = src.find('\nimport requests\n')
vt_inject = src.find('truststore.inject_into_ssl()')
vt_fastapi_import = src.find('from fastapi import FastAPI')
assert 0 < vt_import_requests < vt_inject < vt_fastapi_import, (
    "Phải gọi truststore.inject_into_ssl() NGAY SAU 'import requests' và TRƯỚC các import/code khác "
    "— gọi trễ (sau khi đã có request/session nào đó tạo trước) sẽ không vá kịp, request đó vẫn lỗi.")
khoi_inject = src[src.find('try:\n    import truststore'):vt_fastapi_import]
assert 'except Exception:' in khoi_inject and 'pass' in khoi_inject, (
    "Phải bọc try/except — máy nào chưa kịp cài truststore (vd chưa chạy lại start.bat) không được làm "
    "sập cả server, chỉ là chưa có bản vá này (rớt về hành vi cũ, vẫn còn thử curl_cffi/requests thường)."
)
assert 'verify=False' not in src and 'verify = False' not in src, (
    "TUYỆT ĐỐI không được tắt xác thực TLS ở bất kỳ đâu để né lỗi SSL — phải luôn xác thực, chỉ đổi "
    "nguồn kho chứng chỉ.")
print("PASS 7: dùng kho chứng chỉ gốc hệ điều hành (truststore) ngay lúc khởi động, không tắt xác thực TLS.")

# ===== Test 8 (QUAN TRỌNG — đúng ca thật: "không giải được captcha" LẶP LẠI
# giống hệt nhau cả 6/6 lần): captcha trang này bắt buộc OCR ảnh PNG thật sự
# (không có đường tắt đọc <text> trong SVG như hoadondientu) — nếu ddddocr
# KHÔNG NẠP ĐƯỢC (thường do thiếu VC++ Redistributable) thì CHẮC CHẮN cả 6
# lần thử lại đều thất bại y hệt nhau, lãng phí 6 lượt gọi mạng vô ích và
# không báo đúng nguyên nhân thật. Phải kiểm tra NGAY TỪ ĐẦU (trước khi gọi
# mạng lần nào) và trỏ đúng cơ chế tự khắc phục đã có sẵn (/api/fix-ocr). =====
than_tc2 = _than_ham('_tra_cuu_mst_qua_tracuunnt')
vt_check_ddddocr = than_tc2.find('_get_ddddocr() is None')
vt_vong_lap_captcha = than_tc2.find('for lan in range(1, _SO_LAN_THU_CAPTCHA_TRACUUNNT')
assert 0 < vt_check_ddddocr < vt_vong_lap_captcha, (
    "Phải kiểm tra ddddocr đã nạp được chưa NGAY TỪ ĐẦU, TRƯỚC vòng lặp thử captcha — nếu không, máy "
    "chưa nạp được ddddocr sẽ lãng phí đủ 6 lượt gọi mạng rồi mới báo lỗi, và lỗi báo ra ('OCR không "
    "đọc ra') không đúng nguyên nhân thật (ddddocr chưa nạp được, không phải OCR đọc sai).")
assert '/api/fix-ocr' in than_tc2, (
    "Thông báo lỗi phải trỏ tới đúng cơ chế tự khắc phục ddddocr đã có sẵn trong phần mềm (/api/fix-ocr) "
    "— không bắt người dùng tự mò cách sửa.")
assert '_DDDDOCR_ERR' in than_tc2, "Phải kèm chi tiết lỗi thật (_DDDDOCR_ERR) để chẩn đoán chính xác, không chỉ nói chung chung."
print("PASS 8: kiểm tra ddddocr nạp được ngay từ đầu, tránh lãng phí 6 lượt gọi mạng vô ích, trỏ đúng cách tự khắc phục.")

# ===== Test 9 (bug/ca thật người dùng vừa báo qua endpoint chẩn đoán: "không
# giải được captcha (ảnh 1184 byte, ddddocr đoán: ['', '']) (đã thử 6 lần
# captcha)" — ảnh xem trực tiếp qua /api/xem-captcha-tracuunnt cho thấy
# captcha RẤT RÕ RÀNG, dễ đọc bằng mắt thường ("n5xa3", chữ đậm, ít nhiễu) —
# ddddocr CÓ nạp được (đã qua nhánh kiểm tra sớm ở Test 8) nhưng đoán ra
# CHUỖI RỖNG dù captcha dễ, cần phân biệt RÕ RÀNG 2 khả năng: (a) model THẬT
# SỰ trả về '' (không đọc được gì), hay (b) model trả về CÓ chữ nhưng TOÀN
# ký tự bị bộ lọc [^A-Za-z0-9] xoá sạch (vd ký tự Unicode/dấu câu lạ) — 2 ca
# này có nguyên nhân và cách sửa khác hẳn nhau, nên debug list phải ghi CẢ
# chuỗi THÔ (trước lọc) LẪN chuỗi ĐÃ LỌC, không chỉ mỗi chuỗi đã lọc như
# trước (khiến ca (b) trông giống hệt ca (a), không phân biệt được). =====
ns9 = _nap('_khong_dau')
exec("import re as _re_o", ns9)


class _FakeOcr:
    """Giả lập ddddocr.DdddOcr() — trả về LẦN LƯỢT các chuỗi đã cấu hình sẵn
    cho từng lần gọi .classification(), mô phỏng đúng ca thật: đoán ra chuỗi
    RỖNG/QUÁ NGẮN/TOÀN KÝ TỰ LẠ liên tục (không phải exception, không phải
    None)."""
    def __init__(self, cac_ket_qua):
        self._ds = list(cac_ket_qua)

    def classification(self, buf):
        return self._ds.pop(0) if self._ds else ""


ns9['_get_ddddocr'] = lambda: ns9['_fake_ocr']
ns9['_preprocess_png'] = lambda b: b
ns9['_flatten_rgba_png'] = lambda b: b   # không liên quan phần đang test (bộ lọc chuỗi), bỏ qua alpha
exec(_than_ham('_ocr_png'), ns9)
ocr_png = ns9['_ocr_png']

# Lượt 1 (ảnh gốc): model trả về RỖNG THẬT SỰ ('') -> ca (a).
# Lượt 2 (ảnh đã làm sạch): model trả về CÓ chữ ('###') nhưng TOÀN ký tự bị
# bộ lọc [^A-Za-z0-9] xoá sạch -> sau lọc cũng thành '' -> ca (b), PHẢI phân
# biệt được với lượt 1 qua debug list (chuỗi thô khác nhau: '' vs '###').
ns9['_fake_ocr'] = _FakeOcr(["", "###"])
debug9 = []
r9 = ocr_png(b"\x89PNG-gia-lap-du-lieu-anh-captcha", debug9)
assert r9 == "", f"Cả 2 lần thử đều KHÔNG đạt độ dài hợp lệ (4-10 ký tự) -> phải trả rỗng — got {r9!r}"
assert debug9 == ["'' -> ''", "'###' -> ''"], (
    f"debug list phải ghi lại CẢ chuỗi THÔ (trước lọc) LẪN chuỗi ĐÃ LỌC ở mỗi lần thử, để phân biệt "
    f"được ca 'model thật sự trả về rỗng' (thô cũng rỗng) với ca 'model có trả về chữ nhưng bị bộ lọc "
    f"ký tự lạ xoá sạch' (thô KHÔNG rỗng, chỉ lọc xong mới rỗng) — 2 ca này nguyên nhân khác hẳn nhau "
    f"— got {debug9!r}")
print("PASS 9a: _ocr_png() ghi lại CẢ chuỗi thô (trước lọc) LẪN chuỗi đã lọc vào debug list, phân biệt "
      "được 'model thật sự đoán rỗng' với 'model có đoán ra chữ nhưng bị lọc ký tự lạ xoá sạch'.")

than_tc9 = _than_ham('_tra_cuu_mst_qua_tracuunnt')
assert '_ocr_png(r_cap.content, doan_debug)' in than_tc9 or ('doan_debug' in than_tc9 and '_ocr_png(r_cap.content,' in than_tc9), (
    "_tra_cuu_mst_qua_tracuunnt() phải truyền debug list vào _ocr_png() để ghi lại chuỗi thật đã đoán.")
assert 'doan_debug' in than_tc9 and 'len(r_cap.content)' in than_tc9, (
    "Thông báo lỗi khi không giải được captcha phải kèm CẢ kích cỡ ảnh nhận được (len(r_cap.content)) "
    "LẪN debug list (ddddocr thật sự đoán ra gì) — không còn chỉ 1 câu chung chung 'OCR không đọc ra' "
    "không giúp chẩn đoán được gì thêm khi captcha thất bại LẶP LẠI 6/6 lần dù ddddocr đã nạp được.")
print("PASS 9b: _tra_cuu_mst_qua_tracuunnt() kèm kích cỡ ảnh + chuỗi ddddocr thật sự đoán được vào "
      "thông báo lỗi cuối cùng, thay vì chỉ 1 câu chung chung không giúp chẩn đoán được gì thêm.")

# ===== Test 9c (TÌM RA ĐÚNG NGUYÊN NHÂN GỐC — bug THẬT vừa xác nhận qua file
# ảnh captcha THẬT người dùng gửi + test độc lập bằng ddddocr THẬT ngoài
# phần mềm): captcha.png của tracuunnt.gdt.gov.vn là ảnh RGBA NỀN TRONG SUỐT
# (đã xác nhận: pixel góc ảnh = (0,0,0,0) — đen, alpha=0). Trình duyệt tự
# composite đúng với nền trang (trắng/sáng) nên NGƯỜI DÙNG thấy chữ rõ ràng
# ("6r4yy"), nhưng PIL .convert('RGB')/('L') KHÔNG composite — chỉ CẮT BỎ
# kênh alpha, để lại phần RGB dưới vùng trong suốt vốn gần như ĐEN TRÙNG MÀU
# CHỮ luôn -> ảnh kết quả gần như toàn đen, ddddocr đoán ra RỖNG dù ảnh gốc
# rất dễ đọc. Test bằng ddddocr THẬT (không mock) trên chính file ảnh thật
# người dùng gửi, xác nhận: KHÔNG làm phẳng alpha trước -> đoán rỗng; CÓ làm
# phẳng (composite xuống nền trắng) -> đoán ĐÚNG '6r4yy'. =====
_duong_dan_fixture = os.path.join(_REPO_ROOT, 'tests', 'fixtures', 'tracuunnt_captcha_fixture_rgba.png')
try:
    import ddddocr as _ddddocr_that
    _co_ddddocr_that = True
except Exception:
    _co_ddddocr_that = False

if _co_ddddocr_that and os.path.exists(_duong_dan_fixture):
    ns9c = _nap('_khong_dau')
    exec(_than_ham('_flatten_rgba_png'), ns9c)
    exec(_than_ham('_preprocess_png'), ns9c)
    exec(_than_ham('_ocr_png'), ns9c)
    _ocr_that = _ddddocr_that.DdddOcr(show_ad=False)
    ns9c['_get_ddddocr'] = lambda: _ocr_that

    anh_that = open(_duong_dan_fixture, 'rb').read()

    from PIL import Image as _Image_t
    import io as _io_t
    im_that = _Image_t.open(_io_t.BytesIO(anh_that))
    assert im_that.mode == "RGBA", f"Fixture phải đúng ảnh RGBA thật đã xác nhận — got mode={im_that.mode}"
    assert im_that.getpixel((0, 0))[3] == 0, "Pixel góc ảnh phải TRONG SUỐT (alpha=0) — đúng ca thật đã xác nhận."

    # KHÔNG làm phẳng alpha (mô phỏng hành vi CŨ trước khi sửa) -> ddddocr
    # phải đoán RỖNG (tái hiện đúng bug thật).
    ans_chua_sua = (_ocr_that.classification(anh_that) or "").strip()
    assert ans_chua_sua == "", (
        f"Xác nhận lại đúng bug gốc: KHÔNG làm phẳng alpha trước -> ddddocr phải đoán RỖNG trên ảnh "
        f"thật này (như đã tái hiện được) — got {ans_chua_sua!r} (nếu ddddocr đã đoán ra được không cần "
        f"làm phẳng thì có thể model đã đổi, xem lại giả thiết)")

    # _ocr_png() (ĐÃ SỬA, tự làm phẳng alpha bên trong) -> phải đoán ĐÚNG.
    debug9c = []
    ket_qua_9c = ns9c['_ocr_png'](anh_that, debug9c)
    assert ket_qua_9c == "6r4yy", (
        f"_ocr_png() ĐÃ SỬA (tự làm phẳng alpha xuống nền trắng trước khi OCR) phải đọc ĐÚNG captcha "
        f"thật '6r4yy' từ file ảnh RGBA nền trong suốt — got {ket_qua_9c!r}, debug={debug9c!r}")
    print("PASS 9c: xác nhận ĐÚNG NGUYÊN NHÂN GỐC bằng ddddocr THẬT trên file ảnh captcha THẬT người "
          "dùng gửi — captcha.png là RGBA nền trong suốt, không làm phẳng alpha thì ddddocr đoán rỗng; "
          "_ocr_png() đã sửa (tự làm phẳng xuống nền trắng) đọc đúng '6r4yy'.")
else:
    print("BỎ QUA Test 9c: cần cài ddddocr thật + file tests/fixtures/tracuunnt_captcha_fixture_rgba.png "
          "để xác nhận bằng OCR thật (môi trường này thiếu 1 trong 2, các test khác vẫn đủ để xác nhận "
          "logic làm phẳng alpha qua Test 9d bên dưới, không cần ddddocr thật).")

# ===== Test 9d (không cần ddddocr thật — kiểm tra ĐÚNG logic làm phẳng alpha
# ở mức pixel, luôn chạy được dù môi trường không có ddddocr): _flatten_rgba_png()
# phải composite ĐÚNG kênh alpha xuống nền TRẮNG (không phải chỉ cắt bỏ alpha)
# — pixel trong suốt (alpha=0) trong ảnh RGBA phải thành TRẮNG (255,255,255)
# sau khi làm phẳng, không phải giữ nguyên RGB gốc (thường là đen/tối với
# ảnh captcha kiểu này). Ảnh KHÔNG có alpha (RGB thường) phải giữ NGUYÊN,
# không bị đổi gì (an toàn cho các nguồn captcha khác đã tự vẽ nền trắng). =====
if os.path.exists(_duong_dan_fixture):
    ns9d = _nap('_khong_dau')
    exec(_than_ham('_flatten_rgba_png'), ns9d)
    from PIL import Image as _Image_d
    import io as _io_d

    anh_that_d = open(_duong_dan_fixture, 'rb').read()
    da_lam_phang = ns9d['_flatten_rgba_png'](anh_that_d)
    im_sau = _Image_d.open(_io_d.BytesIO(da_lam_phang))
    assert im_sau.mode == "RGB", f"Sau khi làm phẳng phải hết kênh alpha (mode RGB) — got {im_sau.mode}"
    assert im_sau.getpixel((0, 0)) == (255, 255, 255), (
        f"Pixel TRONG SUỐT (alpha=0) trong ảnh gốc phải thành TRẮNG (255,255,255) sau khi composite "
        f"— KHÔNG được chỉ cắt bỏ alpha (sẽ giữ nguyên RGB gốc, thường đen/tối, làm mất chữ) "
        f"— got {im_sau.getpixel((0, 0))}")

    # Ảnh KHÔNG có alpha -> phải giữ NGUYÊN, không đổi.
    anh_rgb_thuong = _Image_d.new("RGB", (10, 10), (128, 64, 32))
    buf_thuong = _io_d.BytesIO()
    anh_rgb_thuong.save(buf_thuong, format="PNG")
    khong_alpha_bytes = buf_thuong.getvalue()
    ket_qua_khong_alpha = ns9d['_flatten_rgba_png'](khong_alpha_bytes)
    assert ket_qua_khong_alpha == khong_alpha_bytes, (
        "Ảnh KHÔNG có kênh alpha (RGB thường) phải trả về NGUYÊN VẸN, không bị đổi gì — an toàn cho các "
        "nguồn captcha khác (vd _svg_to_png đã tự vẽ nền trắng sẵn, không cần/không nên làm phẳng lại).")
    print("PASS 9d: _flatten_rgba_png() composite ĐÚNG kênh alpha xuống nền trắng (pixel trong suốt "
          "thành trắng, không phải giữ nguyên RGB tối gốc), và KHÔNG đổi gì với ảnh không có alpha.")
else:
    print("BỎ QUA Test 9d: thiếu file tests/fixtures/tracuunnt_captcha_fixture_rgba.png")

# ===== Test 10 (không hồi quy — endpoint xem ảnh captcha thật, ca thật vừa
# gặp: ddddocr đoán RỖNG HOÀN TOÀN 6/6 lần dù ảnh nhận được có kích cỡ hợp
# lý 1184 byte — cần xem trực tiếp ảnh để biết đây là captcha bình thường
# hay ảnh bị hỏng/không phải captcha thật): phải có endpoint trả THẲNG ảnh
# PNG thật (Content-Type image/png) để người dùng tự mắt xem trên trình
# duyệt, dùng CHUNG cơ chế mở session/fallback SSL như
# _tra_cuu_mst_qua_tracuunnt() (không phải mô phỏng riêng). =====
assert '/api/xem-captcha-tracuunnt' in src and 'def xem_captcha_tracuunnt' in src, (
    "Phải có endpoint trả ảnh captcha thật để xem trực tiếp trên trình duyệt.")
than_xem = _than_ham('xem_captcha_tracuunnt')
assert '_tao_session_tracuunnt(' in than_xem and '_loi_ssl_chung_thuc(' in than_xem, (
    "Endpoint xem ảnh phải dùng CHUNG cơ chế mở session/fallback SSL như _tra_cuu_mst_qua_tracuunnt(), "
    "không phải viết lại logic riêng (dễ lệch hành vi, khó chẩn đoán đúng).")
assert 'media_type="image/png"' in than_xem, (
    "Phải trả về đúng Content-Type image/png để trình duyệt hiển thị được ảnh trực tiếp, không phải "
    "JSON/base64 (người dùng cần xem BẰNG MẮT ngay, không cần công cụ giải mã thêm).")
assert '"https://tracuunnt.gdt.gov.vn/tcnnt/captcha.png"' in than_xem, (
    "Phải lấy đúng ảnh captcha.png thật từ tracuunnt.gdt.gov.vn, không phải ảnh mô phỏng/giả lập.")
print("PASS 10: có endpoint /api/xem-captcha-tracuunnt trả thẳng ảnh captcha thật (image/png) để xem "
      "trực tiếp trên trình duyệt, dùng chung cơ chế session/fallback SSL với hàm tra cứu thật.")

# ===== Test 11 (QUAN TRỌNG — ca thật vừa gặp: RẤT NHIỀU MST khác nhau cùng
# thất bại đủ 6/6 lần captcha trong 1 lượt xuất Excel — đáng ngờ hơn ngẫu
# nhiên đoán sai captcha 6 lần liên tiếp cho từng đó MST khác nhau, có thể
# do lý do KHÁC hẳn "đoán sai captcha" — vd trang WAF chặn tạm do gọi dồn
# dập nhiều luồng cùng lúc — mà câu thông báo cũ "có thể đã đoán sai
# captcha" không phản ánh đúng): khi không ra bảng kết quả, PHẢI trích kèm
# đoạn văn bản THẬT trang trả về (không phải chỉ đoán mù), để biết chắc lần
# sau. BẢN ĐẦU TIÊN (200 ký tự đầu trang) hoá ra VÔ ÍCH — log thật (sau khi
# triển khai) cho thấy 200 ký tự đầu LUÔN là tiêu đề/nhãn form cố định
# ("Cục Thuế - Bộ Tài Chính ... Mã số thuế * Tên tổ chức cá nhân nộp thuế
# Địa chỉ trụ sở kinh doanh Số c...") GIỐNG HỆT NHAU ở MỌI MST khác nhau —
# đã SỬA: ưu tiên đoạn văn bản QUANH từ khoá liên quan lỗi thật nếu có,
# tăng độ dài mặc định (200 -> 450) khi không tìm thấy từ khoá nào. =====
ns11 = _nap('_khong_dau')
m11 = re.search(r'^_TU_KHOA_LOI_TRACUUNNT\s*=\s*\([^)]*\)', src, re.M | re.S)
assert m11 is not None, "Phải có danh sách _TU_KHOA_LOI_TRACUUNNT (các từ khoá liên quan lỗi/chặn thật)."
exec(m11.group(0), ns11)
exec(_than_ham('_trich_doan_loi_html_tracuunnt'), ns11)
trich = ns11['_trich_doan_loi_html_tracuunnt']
r11a = trich('<html><body><script>var x=1;</script><p>Bạn đã gửi quá nhiều '
             'yêu cầu, vui lòng thử lại sau &amp; kiên nhẫn.</p></body></html>')
assert 'Bạn đã gửi quá nhiều yêu cầu' in r11a and '<' not in r11a and '&amp;' not in r11a, (
    f"Phải bỏ hết thẻ HTML/script, giải mã HTML entity, giữ lại đúng văn bản thật — got {r11a!r}")
r11b = trich('a' * 500, do_dai=50)
assert len(r11b) == 50, f"Phải giới hạn độ dài (tránh log quá dài) — got độ dài {len(r11b)}"
r11c = trich(None)
assert r11c == "", f"HTML rỗng/None không được crash, trả rỗng — got {r11c!r}"
print("PASS 11a: _trich_doan_loi_html_tracuunnt() trích đúng văn bản thật (bỏ thẻ/script, giải mã "
      "entity, giới hạn độ dài), không crash với input rỗng.")

# Đúng ca thật: đoạn tiêu đề/nhãn form cố định (giống hệt log thật) ĐỨNG
# TRƯỚC 1 thông báo lỗi thật xa hơn trong trang -> PHẢI trả về đoạn QUANH
# thông báo lỗi đó, KHÔNG PHẢI chỉ lấy phần đầu (tiêu đề cố định) như bản cũ.
m_sig11 = re.search(r'def _trich_doan_loi_html_tracuunnt\([^)]*do_dai\s*=\s*(\d+)', src)
assert m_sig11 is not None and int(m_sig11.group(1)) >= 400, (
    f"Độ dài mặc định (khi KHÔNG tìm thấy từ khoá lỗi nào) phải tăng lên đủ dài (>= 400, từ 200 cũ) để "
    f"có cơ hội vượt qua phần tiêu đề/nhãn form cố định — got {m_sig11.group(1) if m_sig11 else None}")
tieu_de_co_dinh = ('Cục Thuế - Bộ Tài Chính Trang chủ Tra cứu thông tin người nộp Thuế Thông tin về '
                   'người nộp thuế Thông tin về người nộp thuế TNCN Mã số thuế * Tên tổ chức cá nhân '
                   'nộp thuế Địa chỉ trụ sở kinh doanh Số chứng minh thư')
html_that = f'<html><body><div>{tieu_de_co_dinh}</div><div>Mã xác nhận không đúng, vui lòng nhập lại.</div></body></html>'
r11d = trich(html_that)
assert 'không đúng' in r11d.lower(), (
    f"Phải ưu tiên đoạn văn bản QUANH từ khoá lỗi thật ('không đúng'), KHÔNG PHẢI chỉ lấy phần đầu "
    f"trang (tiêu đề/nhãn form cố định, giống hệt nhau ở mọi MST, không giúp chẩn đoán được gì) — "
    f"got {r11d!r}")
print("PASS 11c: khi trang có từ khoá liên quan lỗi thật (vd 'không đúng'), trích đúng đoạn QUANH từ "
      "khoá đó thay vì chỉ lấy phần đầu trang (tiêu đề/nhãn form cố định, vô ích để chẩn đoán — đúng "
      "bug thật phát hiện qua log sau khi triển khai bản đầu tiên).")

# ===== Test 11e (QUAN TRỌNG — ca thật vừa gặp: SAU KHI đã tăng độ dài + ưu
# tiên từ khoá ở Test 11c, log thật VẪN chỉ ra đúng nhãn form tĩnh — kể cả
# đoạn "Mã xác nhận * Lưu ý:... Vui lòng nhập đúng mã xác nhận!" cũng chỉ là
# NHÃN HƯỚNG DẪN CỐ ĐỊNH cạnh ô nhập captcha, không phải thông báo lỗi ĐỘNG
# theo từng lần thử — nghĩa là trang này KHÔNG có thông báo lỗi nào trong
# phần VĂN BẢN HIỂN THỊ cả, dù captcha đúng hay sai): nhiều trang JSP cũ báo
# lỗi qua alert()/confirm() JAVASCRIPT (popup), mà bản cũ lại CỐ TÌNH bỏ hẳn
# nội dung trong <script> (coi là không phải văn bản người đọc) — PHẢI tìm
# TRƯỚC trong HTML gốc xem có alert()/confirm() với thông báo lỗi thật
# không, ưu tiên CAO NHẤT (trước cả từ khoá/đầu trang). =====
r11e = trich('<html><head><script>alert(\'Mã xác nhận không đúng, vui lòng thử lại!\');'
             'history.back();</script></head><body><div>Cục Thuế - Bộ Tài Chính ...</div></body></html>')
assert 'Mã xác nhận không đúng, vui lòng thử lại' in r11e, (
    f"Phải ưu tiên CAO NHẤT lấy thông báo lỗi thật từ alert()/confirm() JAVASCRIPT (bản cũ bỏ hẳn nội "
    f"dung <script>, bỏ sót đúng chỗ nhiều trang JSP cũ dùng để báo lỗi captcha) — got {r11e!r}")
r11f = trich('<html><body><script>var x=1; someOtherFunc("khong lien quan");</script>'
             '<div>Chỉ có tiêu đề trang bình thường thôi, không có popup nào cả.</div></body></html>')
assert '[thông báo popup của trang]' not in r11f and 'someOtherFunc' not in r11f and (
    'Chỉ có tiêu đề trang bình thường' in r11f), (
    f"KHÔNG có alert()/confirm() nào trong trang -> phải rơi về hành vi cũ (từ khoá/đầu trang văn bản "
    f"hiển thị, bỏ qua nội dung <script> không liên quan), không được báo nhầm có popup lỗi — got {r11f!r}")
print("PASS 11e: ưu tiên CAO NHẤT lấy thông báo lỗi thật từ alert()/confirm() JAVASCRIPT nếu trang có "
      "(nhiều trang JSP cũ báo lỗi captcha qua popup, không phải văn bản hiển thị thường) — không có "
      "alert nào thì rơi về hành vi cũ (từ khoá/đầu trang).")

than_tc11 = _than_ham('_tra_cuu_mst_qua_tracuunnt')
assert '_trich_doan_loi_html_tracuunnt(html)' in than_tc11 and 'doan_html' in than_tc11, (
    "_tra_cuu_mst_qua_tracuunnt() phải gọi _trich_doan_loi_html_tracuunnt() và đưa vào ly_do_loi_cuoi "
    "khi không ra bảng kết quả, thay vì chỉ 1 câu đoán mù 'có thể đã đoán sai captcha' không giúp chẩn "
    "đoán được gì thêm khi RẤT NHIỀU MST khác nhau cùng thất bại 6/6 lần trong 1 lượt.")
print("PASS 11b: _tra_cuu_mst_qua_tracuunnt() kèm đoạn văn bản THẬT trang trả về vào thông báo lỗi khi "
      "không ra bảng kết quả, thay vì chỉ đoán mù 'có thể đã đoán sai captcha'.")

# ===== Test 12 (QUAN TRỌNG — đúng yêu cầu người dùng: "hãy tạm dừng
# xinvoice.vn chỉ dùng tracuunnt.gdt.gov.vn để tra cứu" sau khi log thật cho
# thấy CẢ 2 key XInvoice đã cấu hình đều HTTP 429 "Exceeded free tier
# limit"/timeout — gọi XInvoice dự phòng chỉ tốn thêm thời gian chờ vô ích):
# _tra_cuu_trang_thai_mst() phải KHÔNG gọi _goi_1_lan_xinvoice() khi cờ
# _XINVOICE_TAM_DUNG đang True (mặc định hiện tại), NHƯNG code XInvoice vẫn
# phải CÒN NGUYÊN trong file (chỉ tạm dừng gọi qua cờ, không xoá) để khôi
# phục ngay khi hạn mức gói có lại — TẠM DỪNG khác hẳn BỎ HẲN (đã áp dụng
# đúng cho VietQR/masothue.com ở Test 5, không lẫn 2 khái niệm này). =====
assert 'def _goi_1_lan_xinvoice(' in src, (
    "_goi_1_lan_xinvoice() phải CÒN NGUYÊN trong file (TẠM dừng gọi, không xoá code) — khác VietQR/"
    "masothue.com đã BỎ HẲN.")
assert re.search(r'^_XINVOICE_TAM_DUNG\s*=\s*True', src, re.M), (
    "Phải có cờ _XINVOICE_TAM_DUNG=True (mặc định TẠM dừng gọi XInvoice) — đúng yêu cầu người dùng sau "
    "khi thấy cả 2 key XInvoice đều hết hạn mức gói/timeout, gọi dự phòng chỉ tốn thêm thời gian vô ích.")
assert '_XINVOICE_TAM_DUNG' in than_chinh, (
    "_tra_cuu_trang_thai_mst() phải kiểm tra cờ _XINVOICE_TAM_DUNG trước khi gọi _goi_1_lan_xinvoice().")
print("PASS 12: XInvoice đang TẠM dừng qua cờ _XINVOICE_TAM_DUNG=True (code vẫn còn nguyên, không xoá) "
      "— đúng yêu cầu người dùng sau khi cả 2 key đều hết hạn mức gói/timeout.")

print("\nALL DONE")
