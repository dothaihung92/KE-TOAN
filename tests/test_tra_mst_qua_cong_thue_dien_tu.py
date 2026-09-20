import os
import re

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test (nguồn + hành vi) — người dùng báo: tra tình trạng MST khi
# xuất Excel bảng kê BẾ TẮC vì API XInvoice hết hạn mức gói free tier ở CẢ 2
# key đã cấu hình (HTTP 429 "Exceeded free tier limit"), kéo theo dự phòng
# masothue.com cũng 429 (vì cả lượt ~44 MST dồn sang cùng lúc, 3 luồng song
# song) -> "hãy xem còn cách nào khác để dò kiểm tra mst không vì api XInvoice
# hạn chế quá".
#
# Cách đã chọn: dùng CHÍNH cổng Thuế điện tử (hoadondientu.gdt.gov.vn) mà phần
# mềm VỐN ĐÃ đăng nhập để tải hóa đơn — nguồn CHÍNH THỨC của Tổng cục Thuế,
# miễn phí, KHÔNG hạn mức gói bên thứ 3.


def _than_ham(ten):
    i = src.index('def ' + ten + '(')
    j = src.index('\ndef ', i + 10)
    return src[i:j]


# ===== Test 1 (QUAN TRỌNG — đúng yêu cầu): nguồn cổng Thuế điện tử phải được
# thử TRƯỚC XInvoice, không phải sau. Đặt sau thì mỗi MST vẫn "đốt" 1 lượt gọi
# XInvoice trước khi tới lượt nguồn miễn phí — tức KHÔNG giải quyết được đúng
# vấn đề hết hạn mức mà người dùng đang gặp. =====
than_chinh = _than_ham('_tra_cuu_trang_thai_mst')
vt_tct = than_chinh.find('_tra_cuu_mst_qua_tct(')
vt_xinvoice = than_chinh.find('_goi_1_lan_xinvoice(')
vt_masothue = than_chinh.find('_tra_cuu_masothue(')
assert vt_tct > 0, "_tra_cuu_trang_thai_mst() phải gọi _tra_cuu_mst_qua_tct() (nguồn cổng Thuế điện tử)."
assert vt_tct < vt_xinvoice, (
    "Phải thử cổng Thuế điện tử TRƯỚC XInvoice — tra được ở nguồn chính thức miễn phí thì KHÔNG tốn "
    "lượt gọi nào của gói XInvoice, giữ nguyên hạn mức cho lúc thật sự cần (đúng vấn đề người dùng "
    "báo: cả 2 key XInvoice đều HTTP 429 hết hạn mức).")
assert vt_xinvoice < vt_masothue, "Thứ tự dự phòng còn lại phải giữ nguyên: XInvoice rồi mới masothue.com."
print("PASS 1: cổng Thuế điện tử được thử TRƯỚC XInvoice, masothue.com vẫn là chốt chặn cuối.")

# ===== Test 2 (BẪY DỄ SAI — tốn thời gian hàng loạt): 1 lượt xuất Excel có thể
# phải tra HÀNG TRĂM MST. Nếu cổng Thuế đổi đường dẫn/không đăng nhập được mà
# cứ thử lại cho TỪNG MST thì cả lượt xuất Excel sẽ ì ạch vô ích -> phải có
# ngưỡng TẮT sau vài lần lỗi liên tiếp, và tuyệt đối KHÔNG giải captcha lại cho
# từng MST. =====
than_tct = _than_ham('_tra_cuu_mst_qua_tct')
assert '_TCT_MST_NGUONG_TAT' in src and '_tct_danh_dau(' in than_tct, (
    "Phải có bộ đếm lỗi liên tiếp + ngưỡng TẮT nguồn cổng Thuế điện tử cho công ty đó, tránh thử lại "
    "vô ích cho hàng trăm MST còn lại trong cùng lượt xuất Excel.")
assert 'da_thu_login' in than_tct, (
    "Phải ghi nhớ ĐÃ THỬ tự đăng nhập — giải captcha rất tốn thời gian, không được giải lại cho từng MST.")
assert than_tct.count('_tu_dong_dang_nhap(') >= 1 and 'so_lan=5' in than_tct, (
    "Khi chưa có phiên thì tự đăng nhập, giới hạn số lần thử (không lặp vô hạn) để không treo lượt xuất Excel.")
assert '_mo_trinh_duyet_captcha()' in than_tct and '_dong_trinh_duyet_captcha(' in than_tct, (
    "Đăng nhập phải dùng trình duyệt ẩn vẽ captcha CHÍNH XÁC (giống /api/auto-login, xuất Excel) thay "
    "vì rớt về svglib kém chính xác — đây là điều kiện tiên quyết để cả nguồn tra MST này chạy được, "
    "đăng nhập thất bại thì mọi MST trong lượt đều rơi xuống XInvoice/masothue.")
print("PASS 2: có ngưỡng tắt khi lỗi liên tiếp, chỉ tự đăng nhập 1 lần (dùng trình duyệt ẩn vẽ captcha chính xác), không giải captcha lại cho từng MST.")

# ===== Test 3 (AN TOÀN — không được suy đoán): có dữ liệu trả về nhưng KHÔNG
# dò ra cụm mô tả tình trạng thì phải coi là THẤT BẠI (để rơi xuống XInvoice/
# masothue), tuyệt đối không mặc định "đang hoạt động" — đoán sai kiểu đó sẽ
# BỎ SÓT đúng những MST cần tô đỏ cảnh báo. =====
assert re.search(r'if canh_bao is None:\s*\n(?:\s*#.*\n)*\s*_tct_danh_dau\(cid, False\)', than_tct), (
    "Khi không dò được tình trạng trong dữ liệu trả về thì phải trả THẤT BẠI (rơi xuống nguồn khác), "
    "không được coi là thành công/suy đoán 'đang hoạt động'.")
assert 'return True, trang_thai_goc, canh_bao, None' in than_tct, (
    "Khi dò được tình trạng thì trả về đúng bộ 4 giá trị giống _tra_cuu_masothue() để ghép vào chuỗi dự phòng.")
print("PASS 3: không dò được tình trạng thì coi là thất bại, không suy đoán 'đang hoạt động'.")

# ===== Test 4 (đúng ca thật 401 hết phiên): phiên cổng Thuế hết hạn giữa
# chừng phải tự đăng nhập lại rồi THỬ LẠI, không được coi luôn là MST không tra
# được (đây là lỗi phiên, không phải lỗi dữ liệu MST). =====
assert 'if http == 401:' in than_tct, "Phải xử lý riêng HTTP 401 (hết phiên) thay vì coi là tra thất bại."
assert than_tct.count('client.tra_cuu_nnt(') >= 2, (
    "Sau khi đăng nhập lại do 401 thì phải GỌI LẠI tra_cuu_nnt — chỉ đăng nhập lại mà không thử lại "
    "thì MST đó vẫn mất trắng dù phiên đã hợp lệ trở lại.")
print("PASS 4: hết phiên (401) thì tự đăng nhập lại rồi tra lại, không bỏ sót MST.")

# ===== Test 5 (chẩn đoán được khi đường dẫn sai): cổng Thuế KHÔNG công bố tài
# liệu API nên đường dẫn tra NNT phải dò nhiều mẫu; phải có endpoint chẩn đoán
# hiện RÕ từng đường dẫn đã thử + HTTP + nội dung thật, nếu không người dùng chỉ
# thấy "không tra được" mà không ai biết sửa gì. =====
assert 'NNT_ENDPOINTS' in src, "GDTClient phải có danh sách đường dẫn tra NNT để dò."
than_nnt = _than_ham('    def tra_cuu_nnt'.strip().replace('def ', '')) if False else src[
    src.index('def tra_cuu_nnt('):src.index('# --- Tra cứu hóa đơn (tự chia nhỏ theo tháng) ---')]
assert 'ensure_ascii=False' in than_nnt, (
    "Phải bung unicode khi đọc JSON — nếu máy chủ trả '\\u0110ang ho\\u1ea1t...' mà giữ nguyên chuỗi "
    "escape thì dò từ khoá tiếng Việt sẽ TRƯỢT HẾT dù dữ liệu trả về vẫn đúng.")
assert 'chan_doan_mst_tct' in src and '/api/chan-doan-mst-tct/' in src, (
    "Phải có endpoint chẩn đoán /api/chan-doan-mst-tct/{cid} để biết đường dẫn nào đúng/sai ngay.")
than_cd = _than_ham('chan_doan_mst_tct')
assert '"da_thu": chi_tiet' in than_cd and 'ket_luan' in than_cd, (
    "Chẩn đoán phải trả về CHI TIẾT từng đường dẫn đã thử kèm kết luận đọc được ngay, không chỉ ok/không ok.")
assert 'so_lan=5' in than_cd and '_mo_trinh_duyet_captcha()' in than_cd, (
    "Endpoint chẩn đoán cũng phải tự đăng nhập bằng trình duyệt ẩn vẽ captcha chính xác (giống thật) — "
    "nếu dùng OCR thô yếu hơn thì kết quả chẩn đoán không phản ánh đúng khả năng chạy thật của tính năng.")
print("PASS 5: có endpoint chẩn đoán hiện rõ từng đường dẫn đã thử + kết luận; JSON bung đúng unicode tiếng Việt; đăng nhập bằng trình duyệt ẩn vẽ captcha chính xác.")

# ===== Test 6 (không hồi quy — phải nối dây tới nơi gọi thật): export Excel
# phải TRUYỀN cid xuống, nếu không thì hàm tra cứu không biết mượn phiên đăng
# nhập của công ty nào -> nguồn mới không bao giờ chạy. =====
assert re.search(r'_tra_cuu_trang_thai_mst\(mst,[^)]*cid=cid', src, re.S), (
    "Nơi gọi trong export Excel phải truyền cid=cid — thiếu thì nguồn cổng Thuế điện tử không bao giờ "
    "được dùng (im lặng quay về đúng tình trạng cũ: chỉ XInvoice + masothue).")
assert 'def _tra_cuu_trang_thai_mst(mst, timeout=8, so_lan_that_bai_lien_tiep=None, chi_dung_cache=False,\n                            cid=None)' in src, (
    "cid phải là tham số TÙY CHỌN (mặc định None) — các nơi gọi khác (nếu có) không truyền vẫn chạy "
    "bình thường như cũ, không vỡ.")
print("PASS 6: export Excel đã truyền cid; cid là tham số tùy chọn nên không vỡ nơi gọi cũ.")

# ===== Test 7 (chẩn đoán đầy đủ): khi CẢ 3 nguồn đều hỏng, thông báo lỗi phải
# gộp lý do của cả 3 — người dùng đang đọc đúng dòng log này để biết mắc ở đâu
# (log thật họ gửi chỉ có 2 nguồn vì lúc đó chưa có nguồn cổng Thuế). =====
assert 'ly_do_loi_tct' in than_chinh and 'Cổng Thuế điện tử:' in than_chinh, (
    "Thông báo lỗi cuối cùng phải kèm cả lý do của nguồn cổng Thuế điện tử, nếu không người dùng "
    "không biết nguồn mới có được thử hay không.")
print("PASS 7: lỗi cuối cùng gộp đủ lý do của cả 3 nguồn (cổng Thuế điện tử + XInvoice + masothue.com).")

print("\nALL DONE")
