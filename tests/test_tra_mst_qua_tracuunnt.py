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
    j = src.index('\ndef ', i + 10)
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

# ===== Test 5 (QUAN TRỌNG — đúng yêu cầu người dùng hiện tại: "hãy tạm ngưng
# dùng VietQR/masothue.com/XInvoice mà tập trung xử lý test chạy kiểm tra qua
# tracuunnt.gdt.gov.vn"): _tra_cuu_trang_thai_mst() giờ CHỈ được gọi
# _tra_cuu_mst_qua_tracuunnt(), KHÔNG còn gọi 3 nguồn kia nữa trong lượt kiểm
# tra này (dù 3 hàm đó vẫn còn nguyên trong file để khôi phục sau). =====
than_chinh = _than_ham('_tra_cuu_trang_thai_mst')
assert '_tra_cuu_mst_qua_tracuunnt(' in than_chinh, (
    "_tra_cuu_trang_thai_mst() phải gọi _tra_cuu_mst_qua_tracuunnt().")
assert '_tra_cuu_mst_qua_vietqr(' not in than_chinh, (
    "TẠM NGƯNG api.vietqr.io theo yêu cầu người dùng — _tra_cuu_trang_thai_mst() KHÔNG được gọi "
    "_tra_cuu_mst_qua_vietqr() trong lượt kiểm tra riêng tracuunnt.gdt.gov.vn này.")
assert '_tra_cuu_mst_qua_masothue(' not in than_chinh, (
    "TẠM NGƯNG masothue.com theo yêu cầu người dùng — _tra_cuu_trang_thai_mst() KHÔNG được gọi "
    "_tra_cuu_mst_qua_masothue() trong lượt kiểm tra riêng tracuunnt.gdt.gov.vn này.")
assert '_goi_1_lan_xinvoice(' not in than_chinh, (
    "TẠM NGƯNG XInvoice theo yêu cầu người dùng — _tra_cuu_trang_thai_mst() KHÔNG được gọi "
    "_goi_1_lan_xinvoice() trong lượt kiểm tra riêng tracuunnt.gdt.gov.vn này.")
# Nhưng 3 hàm đó vẫn phải còn NGUYÊN trong file (chưa xoá hẳn) để khôi phục
# nhanh chuỗi đầy đủ khi người dùng xác nhận xong đợt kiểm tra.
assert 'def _tra_cuu_mst_qua_vietqr(' in src and 'def _tra_cuu_mst_qua_masothue(' in src and 'def _goi_1_lan_xinvoice(' in src, (
    "3 hàm tra MST kia (VietQR/masothue.com/XInvoice) phải vẫn còn NGUYÊN trong file (chỉ tạm ngưng GỌI, "
    "không xoá) để khôi phục lại chuỗi đầy đủ khi cần, không phải viết lại từ đầu.")
print("PASS 5: _tra_cuu_trang_thai_mst() hiện CHỈ gọi tracuunnt.gdt.gov.vn (tạm ngưng VietQR/masothue.com/"
      "XInvoice theo yêu cầu người dùng), 3 hàm kia vẫn còn nguyên trong file để khôi phục sau.")

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

print("\nALL DONE")
