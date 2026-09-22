import os
import re

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test cho phần dựng sheet "Chi tiết BÁN RA" (nested trong
# export_excel(), server.py), nhánh xử lý hóa đơn KHÔNG lấy được chi tiết dòng
# hàng nhưng ĐÃ đăng nhập thành công + có số tiền thật (thường là hóa đơn bán
# hàng của hộ/cá nhân kinh doanh — TCT không trả chi tiết dòng hàng cho loại
# này, ghi cả hóa đơn thành 1 dòng "(Cả hóa đơn — không tách dòng hàng)").
#
# Người dùng gửi file Excel export thật (công ty MST 0318712827) có sheet
# "Đối chiếu" báo hóa đơn BÁN RA C26MHH-1491 bị LỆCH: "Chi tiết BÁN RA" ghi
# Thuế suất="KCT", Tiền thuế GTGT=0đ, nhưng "BK Bán ra" ghi Thuế GTGT=357.467đ
# cho ĐÚNG hóa đơn đó (Doanh số 4.468.328đ khớp nhau ở cả 2 sheet, chỉ tiền
# thuế lệch). Nguyên nhân: bản CŨ gán CỨNG "KCT"+0đ cho MỌI hóa đơn rơi vào
# nhánh "không tách dòng hàng", giả định TẤT CẢ hóa đơn hộ kinh doanh loại
# này đều không chịu thuế — SAI với hóa đơn C26MHH-1491 (có tiền thuế thật
# 357.467đ, r["tgtthue"] khác 0) — trong khi "BK Bán ra" có nhánh dự phòng
# RIÊNG dùng đúng r["tgtthue"] thật, khiến 2 sheet tính khác nhau cho CÙNG 1
# hóa đơn.


def extract_nested_fn(name):
    """Trích xuất hàm NESTED bên trong export_excel() — dò theo ĐÚNG mức thụt lề
    của chính dòng 'def name(' (không phải cột 0) — cách làm sẵn có, dùng chung
    với tests/test_prefetch_trang_thai_mst_song_song.py."""
    idx = src.index('def ' + name + '(')
    line_start = src.rfind('\n', 0, idx) + 1
    def_indent = idx - line_start
    i = src.index(':', idx)
    lines = src[i + 1:].split('\n')
    body = []
    started = False
    for ln in lines:
        if ln.strip() == '':
            body.append(ln)
            continue
        indent = len(ln) - len(ln.lstrip(' '))
        if indent <= def_indent and started:
            break
        started = True
        body.append(ln)
    return src[idx:i + 1] + '\n'.join(body)


# ===== Test 1 (QUAN TRỌNG — đúng bug thật): nhánh "(Cả hóa đơn — không tách
# dòng hàng)" PHẢI dùng đúng tiền thuế THẬT của hóa đơn (r["tgtthue"]), KHÔNG
# được gán cứng 0 — chỉ hiện nhãn "KCT" khi số tiền thuế thật đó THẬT SỰ bằng
# 0. =====
vt_khong_tach_dong = src.index('"(Cả hóa đơn — không tách dòng hàng)", "",')
doan = src[vt_khong_tach_dong - 400:vt_khong_tach_dong + 400]
assert 'thue_hd_that = _to_num(r["tgtthue"]) or 0' in doan, (
    "Nhánh '(Cả hóa đơn — không tách dòng hàng)' phải tính tiền thuế THẬT từ r['tgtthue'] của chính hóa "
    "đơn, không được gán cứng 0 cho mọi hóa đơn rơi vào nhánh này — hóa đơn C26MHH-1491 (ca thật người "
    "dùng báo) có tiền thuế thật 357.467đ dù không tách được chi tiết dòng hàng.")
assert 'ts_hien_hd = "KCT" if not thue_hd_that else ""' in doan, (
    "Nhãn 'KCT' (không chịu thuế) chỉ được hiện khi tiền thuế thật SỰ bằng 0 — không phải gán cứng cho "
    "MỌI hóa đơn không tách được dòng hàng (giả định sai, có hóa đơn loại này vẫn có tiền thuế thật).")
assert 'tong_tien_hd, "KCT", 0, tt, kq])' not in doan, (
    "KHÔNG được còn dòng append_row gán cứng '\"KCT\", 0' cho Thuế suất/Tiền thuế — đây chính là bug cũ "
    "đã gây lệch với 'BK Bán ra' (vốn dùng đúng r['tgtthue'] thật qua nhánh dự phòng riêng của nó).")
print("PASS 1: nhánh '(Cả hóa đơn — không tách dòng hàng)' dùng đúng tiền thuế thật từ r['tgtthue'], "
      "chỉ hiện 'KCT' khi thật sự bằng 0 — không còn gán cứng 0đ cho mọi hóa đơn loại này.")

# ===== Test 2 (không hồi quy — QUAN TRỌNG): ct_totals[loai][ikey]['thue'] cũng
# phải được cộng dồn đúng tiền thuế thật này — trước đây CHỈ cộng 'ds', hoàn
# toàn bỏ qua 'thue' cho nhánh này (ct_totals dùng ở nhiều nơi khác trong hàm,
# vd đối chiếu tổng — bỏ sót thue khiến các phép đối chiếu KHÁC dựa trên
# ct_totals cũng bị lệch âm thầm, không chỉ riêng cột hiển thị). =====
assert 'cur["thue"] += thue_hd_that' in doan, (
    "ct_totals[loai][ikey]['thue'] phải được cộng dồn đúng tiền thuế thật (thue_hd_that) cho nhánh này "
    "— bản cũ chỉ cộng 'ds', bỏ sót 'thue' hoàn toàn, khiến các phép đối chiếu KHÁC trong export_excel() "
    "dựa trên ct_totals (không chỉ riêng cột hiển thị của dòng này) cũng bị lệch âm thầm.")
print("PASS 2: ct_totals[loai][ikey]['thue'] được cộng dồn đúng tiền thuế thật, không còn bỏ sót như "
      "bản cũ (chỉ cộng 'ds').")

print("\nALL DONE")
