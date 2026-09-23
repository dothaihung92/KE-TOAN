import os
import re

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()
html = open(os.path.join(_REPO_ROOT, 'static', 'doi_chieu_ngan_hang.html'), encoding='utf-8').read()

# Regression test cho lỗi ghi UNT/UNC (Ủy nhiệm thu/chi) vào MISA — người dùng báo (kèm ảnh
# chụp màn hình): ghi 1993 chứng từ thu tiền (UNT) từ màn Đối Chiếu Ngân Hàng, lỗi ngay:
#   "Lỗi ghi UNT: ('23000', ... The INSERT statement conflicted with the FOREIGN KEY constraint
#   "FK_BADepositDetail_Account_CreditAccount". ... table "dbo.Account", column 'AccountNumber' ...")
# KHÔNG chứng từ nào được ghi, dù tuyệt đại đa số hợp lệ.
#
# Nguyên nhân: _misa_ghi_thu_chi() (server.py) ghi thẳng mã hạch toán người dùng chọn (hach, từ
# gd["tk_doi_ung"]) vào cột CreditAccount (UNT)/DebitAccount (UNC) của BADepositDetail/
# BAWithDrawDetail — cột này có FOREIGN KEY sang Account.AccountNumber trong CSDL MISA của công
# ty đó. Không hề kiểm tra mã đó có THẬT SỰ tồn tại trong danh mục tài khoản (Account) của công
# ty hay không trước khi ghi (VD tiểu khoản công ty chưa mở, hoặc gõ nhầm) — trong khi conn chỉ
# commit 1 LẦN DUY NHẤT cho CẢ LƯỢT ghi (không commit từng dòng), nên hễ 1 chứng từ dính lỗi FK
# là ROLLBACK MẤT SẠCH toàn bộ các chứng từ khác đã xử lý xong trong cùng lượt, dù bản thân chúng
# hợp lệ 100%.
#
# Fix: dùng lại CHÍNH XÁC pattern đã có sẵn cho Mua hàng/Bán hàng (tk_set + _misa_tk_fallback,
# xem docstring _misa_tk_fallback) — nạp danh mục Account.AccountNumber thật 1 lần, mỗi giao dịch
# validate hach qua _misa_tk_fallback trước khi ghi: rút về TK cha gần nhất đang tồn tại nếu tiểu
# khoản chưa mở, hoặc BỎ QUA RIÊNG chứng từ đó (báo rõ lý do trong "danh_sach") nếu không rút được
# gì cả — không còn để 1 chứng từ lỗi kéo sập cả lượt ghi.


def extract_fn(name):
    """Trích xuất hàm TOP-LEVEL (không nested) — cách làm sẵn có, dùng chung nhiều test khác
    trong repo (VD tests/test_misa_ban_hang_tien_do.py)."""
    idx = src.index('def ' + name + '(')
    i = src.index(':', idx)
    lines = src[i + 1:].split('\n')
    body = []
    started = False
    for ln in lines:
        if ln.strip() == '' and not started:
            body.append(ln)
            continue
        if ln and not ln[0].isspace() and started:
            break
        if ln.strip():
            started = True
        body.append(ln)
    return src[idx:i + 1] + '\n'.join(body)


than = extract_fn('_misa_ghi_thu_chi')

# ===== Test 1 (QUAN TRỌNG): phải nạp danh mục TK thật của MISA (tk_set, từ Account.AccountNumber)
# NGAY ĐẦU hàm — TRƯỚC vòng lặp ghi từng giao dịch — dùng chung 1 lần cho cả lượt, không truy vấn
# lại DB cho mỗi giao dịch (chậm với hàng nghìn dòng). =====
vt_tk_set = than.find('tk_set = set()')
assert vt_tk_set >= 0, (
    "_misa_ghi_thu_chi() phải nạp tk_set (danh mục Account.AccountNumber thật của MISA) — dùng để "
    "validate mã hạch toán trước khi ghi, tránh lỗi FK 'FK_BADepositDetail_Account_CreditAccount'/"
    "'FK_BAWithDrawDetail_Account_DebitAccount' đã báo thật.")
vt_vong_lap_gd = than.find('for gd in (giao_dich or [])')
assert vt_vong_lap_gd >= 0, "Không tìm thấy vòng lặp chính 'for gd in (giao_dich or [])'."
assert vt_tk_set < vt_vong_lap_gd, (
    "tk_set phải nạp TRƯỚC vòng lặp chính (1 lần cho cả lượt ghi), không phải nạp lại bên trong "
    "vòng lặp cho từng giao dịch.")
doan_tk_set = than[vt_tk_set:vt_tk_set + 300]
assert 'SELECT AccountNumber FROM Account' in doan_tk_set, (
    "Phải nạp tk_set từ đúng bảng Account.AccountNumber (bảng có FK từ CreditAccount/DebitAccount "
    "trỏ tới) — cùng cách Mua hàng/Bán hàng đã dùng.")
print("PASS 1: _misa_ghi_thu_chi() nạp tk_set (danh mục Account.AccountNumber thật) 1 lần TRƯỚC vòng lặp ghi.")

# ===== Test 2 (QUAN TRỌNG — đúng bug thật): trong vòng lặp, PHẢI validate hach (mã hạch toán,
# gd["tk_doi_ung"]) qua _misa_tk_fallback(hach, tk_set) NGAY SAU khi tính hach, TRƯỚC bước tìm đối
# tượng (dt = doi_tuong.get(...)) — không rút được TK nào (kể cả TK cha) thì BỎ QUA RIÊNG chứng từ
# đó (continue), KHÔNG ĐƯỢC để lỗi văng ra ngoài làm rollback cả lượt ghi. =====
vt_hach = than.find('hach = str(gd.get("tk_doi_ung")')
assert vt_hach >= 0, "Không tìm thấy dòng gán hach = str(gd.get(\"tk_doi_ung\")...)."
vt_dt = than.find('dt = doi_tuong.get(mst.lower())', vt_hach)
assert vt_dt >= 0, "Không tìm thấy bước tìm đối tượng (dt = doi_tuong.get(...)) sau khi tính hach."
doan_giua = than[vt_hach:vt_dt]
assert '_misa_tk_fallback(hach, tk_set)' in doan_giua, (
    "Phải gọi _misa_tk_fallback(hach, tk_set) để validate/rút TK về TK cha đang tồn tại, đặt GIỮA lúc "
    "tính hach và lúc tìm đối tượng (dt) — đảm bảo bước kiểm tra '131'/'331' bên dưới dùng đúng mã ĐÃ "
    "được validate, không phải mã thô ban đầu.")
assert re.search(r'if\s+not\s+hach_dung\s*:', doan_giua), (
    "Không rút được TK nào (kể cả TK cha, _misa_tk_fallback trả None/rỗng) phải được PHÁT HIỆN rõ "
    "ràng (if not hach_dung) để bỏ qua riêng chứng từ đó.")
vt_if_not_hach_dung = doan_giua.find('if not hach_dung')
doan_bo_qua = doan_giua[vt_if_not_hach_dung:vt_if_not_hach_dung + 350]
assert 'bo_qua_tk += 1' in doan_bo_qua, (
    "Phải tăng biến đếm bo_qua_tk khi bỏ qua 1 chứng từ vì TK không có trong danh mục MISA — để báo "
    "lại đúng số lượng cho người dùng (giống so_bo_qua_kh đã có sẵn cho lỗi thiếu MST).")
assert 'continue' in doan_bo_qua, (
    "Phải continue để CHỈ bỏ qua RIÊNG chứng từ này — KHÔNG được để lỗi văng ra ngoài (raise) làm "
    "rollback mất hết các chứng từ khác trong cùng lượt ghi (đúng bug thật: rollback toàn bộ 1993 "
    "chứng từ chỉ vì 1 chứng từ có TK không tồn tại).")
assert ('không có trong danh mục' in doan_bo_qua or 'không có trong' in doan_bo_qua), (
    "Thông báo bỏ qua phải nói rõ lý do (TK không có trong danh mục tài khoản MISA) để người dùng biết "
    "cần sửa gì, không chỉ báo chung chung.")
print("PASS 2: mỗi giao dịch được validate TK hạch toán qua _misa_tk_fallback TRƯỚC bước tìm đối "
      "tượng; TK không rút được thì bỏ qua RIÊNG chứng từ đó (continue), không làm rollback cả lượt.")

# ===== Test 3 (QUAN TRỌNG — không hồi quy): TK rút được về TK CHA (hach_dung khác hach gốc, VD "2421"
# -> "242") phải THAY THẾ hach bằng giá trị đã validate trước khi ghi vào d_row[tk_cot] — không được
# tiếp tục dùng mã gốc (chưa validate) đi ghi, nếu không vẫn dính đúng lỗi FK cũ dù đã "rút" được. =====
vt_gan_hach = than.find('_misa_gan(d_row, cols_d, hach, tk_cot)')
assert vt_gan_hach >= 0, "Không tìm thấy dòng ghi hach vào d_row[tk_cot] (_misa_gan(d_row, cols_d, hach, tk_cot))."
assert vt_gan_hach > vt_if_not_hach_dung + vt_hach, (
    "Dòng ghi hach vào d_row[tk_cot] phải nằm SAU bước validate/rút TK cha — nếu không, giá trị ghi "
    "vào cột có FK vẫn là mã THÔ chưa qua kiểm tra.")
assert 'hach = hach_dung' in doan_giua, (
    "Sau khi rút được TK cha hợp lệ (hach_dung), phải GÁN LẠI hach = hach_dung để mọi chỗ dùng hach "
    "sau đó (bao gồm dòng ghi vào d_row[tk_cot] có FK) đều dùng đúng giá trị ĐÃ validate.")
assert 'tk_thay.add(' in doan_giua, (
    "Phải ghi nhận lại các trường hợp TK đã tự rút về TK cha (tk_thay) — cùng cách Mua hàng/Bán hàng "
    "đã làm — để báo cho người dùng biết (không âm thầm đổi mã mà không nói gì).")
print("PASS 3: TK rút được về TK cha thì hach được GÁN LẠI đúng giá trị đã validate trước khi ghi vào "
      "cột có FK, và được ghi nhận lại (tk_thay) để báo cho người dùng.")

# ===== Test 4 (không hồi quy): kết quả trả về phải có so_bo_qua_tk/tk_thay — cùng quy ước đặt tên đã
# dùng cho Mua hàng/Bán hàng (so_bo_qua_tk/tk_thay) — để frontend đọc được và hiện cho người dùng. =====
assert '"so_bo_qua_tk": bo_qua_tk, "tk_thay": sorted(tk_thay)' in than, (
    "Kết quả trả về của _misa_ghi_thu_chi() phải có so_bo_qua_tk/tk_thay, đúng tên đã dùng cho Mua "
    "hàng/Bán hàng (server.py có nhiều chỗ dùng \"so_bo_qua_tk\": bo_tk, \"tk_thay\": sorted(tk_thay)) "
    "để frontend xử lý đồng nhất.")
print("PASS 4: kết quả trả về có so_bo_qua_tk/tk_thay, đúng quy ước đặt tên đã dùng cho Mua hàng/Bán hàng.")

# ===== Test 5 (frontend — QUAN TRỌNG): ImportMisaModal (static/doi_chieu_ngan_hang.html) phải hiện
# RIÊNG danh sách chứng từ bị bỏ qua vì lỗi TK (khác nhóm lỗi thiếu MST đã có sẵn) — để người dùng biết
# cần sửa mã hạch toán/tạo tiểu khoản đó trong MISA rồi ghi lại, không chỉ thấy "so_them" thấp hơn kỳ
# vọng mà không rõ lý do. =====
assert 'const loiRowsTk = (pv.danh_sach || []).filter(x => (x.trang_thai || "").includes("không có trong danh mục tài khoản MISA"));' in html, (
    "ImportMisaModal phải lọc riêng loiRowsTk từ pv.danh_sach theo đúng câu thông báo bỏ qua vì lỗi TK "
    "mà backend trả về.")
assert 'loiRowsTk.length + " giao dịch lỗi' in html, (
    "Phải hiện banner riêng cho số giao dịch lỗi TK (loiRowsTk.length) — không gộp lẫn với banner lỗi "
    "thiếu MST (loiRows) đã có sẵn, 2 lý do bỏ qua khác nhau cần người dùng xử lý khác nhau.")
assert 'pv.tk_thay && pv.tk_thay.length > 0' in html, (
    "Phải hiện thông tin các TK đã tự rút về TK cha (pv.tk_thay) — không âm thầm đổi mã mà không báo "
    "cho người dùng biết.")
print("PASS 5: ImportMisaModal hiện riêng banner lỗi TK (loiRowsTk) và thông tin TK đã tự rút về TK cha (tk_thay).")

print("\nALL DONE")
