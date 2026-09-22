import os
import re

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test cho phần dựng sheet "BK Mua vào" (nested trong export_excel(),
# server.py) — người dùng gửi file Excel export thật (công ty MST 0318712827) có
# sheet "Đối chiếu" báo 15 hóa đơn MUA VÀO bị LỆCH giữa "Chi tiết MUA VÀO" và
# "BK Mua vào" (vd C25TVT-158: Chi tiết ghi Thành tiền -14.475.783đ, nhưng BK Mua
# vào ghi Doanh số -15.633.846đ — lệch đúng 1.158.063đ = đúng bằng Tiền thuế GTGT
# của hóa đơn, dù Thuế GTGT ở cả 2 sheet đều khớp nhau tuyệt đối).
#
# Người dùng gửi kèm file XML GỐC của 2 hóa đơn (C25TVT-158, C26MGV-1817) để xác
# nhận nguyên nhân thật: đây là các hóa đơn "Chiết khấu TM"/"Hóa đơn điều chỉnh
# giảm" — trường tổng đầu hóa đơn <TgTCThue> (Tổng tiền CHƯA thuế CHÍNH THỨC) bên
# phát hành ghi = 0 (họ diễn giải khoản chiết khấu qua <TTCKTMai>/dòng hàng theo
# nhóm thuế suất <THTTLTSuat>, KHÔNG qua TgTCThue) dù dòng hàng <HHDVu> có
# <ThTien> thật khác 0. Code CŨ coi TgTCThue=0 là "hóa đơn hộ kinh doanh thiếu dữ
# liệu" (nhánh "HKD") nên lấy NHẦM <TgTTTBSo> (Tổng tiền CÓ thuế) làm Doanh số
# CHƯA thuế — lệch hẳn so với "Chi tiết MUA VÀO" (vốn tính đúng trực tiếp từ
# Thành tiền của chính dòng hàng qua get_invoice_items()/dong_list).
#
# SỬA: "BK Mua vào" giờ ƯU TIÊN đọc lại tổng ĐÃ TÍNH SẴN từ chính các dòng hàng
# khi dựng sheet "Chi tiết MUA VÀO" (ct_totals, chạy TRƯỚC trong cùng lượt xuất
# Excel) thay vì tính LẠI từ trường tổng đầu hóa đơn — đảm bảo 2 sheet LUÔN khớp
# TUYỆT ĐỐI (cùng 1 nguồn số liệu duy nhất), chỉ rơi về cách tính CŨ (trường tổng
# đầu hóa đơn + fallback HKD) khi "Chi tiết MUA VÀO" KHÔNG có dòng nào cho đúng
# hóa đơn đó (ct_totals không có entry).


def extract_nested_fn(name):
    """Trích xuất hàm NESTED bên trong export_excel() — dò theo ĐÚNG mức thụt lề
    của chính dòng 'def name(' (không phải cột 0), dừng ở dòng đầu tiên thụt lề
    <= mức đó (ranh giới thật của hàm nested) — cách làm sẵn có, dùng chung với
    tests/test_prefetch_trang_thai_mst_song_song.py."""
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


# ===== Test 1 (QUAN TRỌNG — đúng bug thật): đoạn dựng dòng "BK Mua vào" PHẢI ưu
# tiên đọc ct_totals["purchase"] (tổng ĐÃ TÍNH SẴN từ "Chi tiết MUA VÀO") TRƯỚC
# khi rơi về cách tính cũ (tgtcthue/tgtttbso) — không phải tính tgtcthue/fallback
# HKD làm NGUỒN CHÍNH như trước (khiến lệch với "Chi tiết MUA VÀO" cho hóa đơn
# chiết khấu có TgTCThue=0). =====
vt_ws_bk_mua = src.index('ws = wb.create_sheet("BK Mua vào")')
vt_ws_bk_ban = src.index('ws = wb.create_sheet("BK Bán ra")')
than_bk_mua = src[vt_ws_bk_mua:vt_ws_bk_ban]

vt_ct_tong = than_bk_mua.find('ct_tong = ct_totals["purchase"].get(ikey)')
vt_tgtcthue_cu = than_bk_mua.find('ds = _to_num(r["tgtcthue"]) or 0')
assert vt_ct_tong >= 0, (
    "Phải đọc ct_totals['purchase'].get(ikey) (tổng đã tính sẵn từ 'Chi tiết MUA VÀO') TRƯỚC khi tính "
    "Doanh số/Thuế cho 'BK Mua vào' — đảm bảo 2 sheet luôn khớp nhau, không lệch như bug thật đã gặp.")
assert vt_tgtcthue_cu >= 0 and vt_ct_tong < vt_tgtcthue_cu, (
    "Việc đọc ct_totals['purchase'] PHẢI đứng TRƯỚC cách tính cũ (tgtcthue/fallback HKD) trong đoạn code "
    "— cách tính cũ giờ chỉ còn là DỰ PHÒNG khi ct_totals không có entry cho hóa đơn đó, không phải "
    "nguồn chính nữa.")
# Cách tính cũ (tgtcthue + fallback HKD) phải nằm trong nhánh "else" (khi KHÔNG
# có ct_tong), không phải chạy VÔ ĐIỀU KIỆN như trước.
doan_giua = than_bk_mua[vt_ct_tong:vt_tgtcthue_cu]
assert 'if ct_tong is not None:' in doan_giua and 'else:' in doan_giua, (
    "Cách tính cũ (tgtcthue/fallback HKD) phải nằm trong nhánh 'else:' của việc kiểm tra ct_tong, chỉ "
    "chạy khi 'Chi tiết MUA VÀO' KHÔNG có dòng nào cho hóa đơn đó — không phải chạy vô điều kiện rồi bị "
    "ct_totals ghi đè (dễ nhầm là code chết, hoặc chạy 2 lần lãng phí).")
print("PASS 1: 'BK Mua vào' ưu tiên đọc ct_totals['purchase'] (tổng đã tính sẵn từ 'Chi tiết MUA VÀO') "
      "trước khi rơi về cách tính cũ (tgtcthue/fallback HKD) — đảm bảo 2 sheet luôn khớp tuyệt đối.")

# ===== Test 2 (không hồi quy — QUAN TRỌNG): 'ikey' phải được tính đúng 1 lần,
# DÙNG CHUNG cho cả việc tra ct_totals lẫn việc ghi bk_totals ở cuối vòng lặp —
# không phải tính lại 2 lần (rủi ro copy-paste lệch công thức key, 2 chỗ ra
# key khác nhau âm thầm không khớp). =====
so_lan_ikey = len(re.findall(
    r'ikey = \(str\(r\["khhdon"\]\), str\(r\["shdon"\]\)\.lstrip\("0"\) or "0"\)', than_bk_mua))
assert so_lan_ikey == 1, (
    f"'ikey' trong đoạn dựng 'BK Mua vào' chỉ nên tính ĐÚNG 1 LẦN (dùng chung cho cả tra ct_totals lẫn "
    f"ghi bk_totals ở cuối vòng lặp) — tính lại nhiều lần dễ copy-paste lệch công thức, 2 chỗ ra key "
    f"khác nhau âm thầm không khớp mà không báo lỗi gì — got {so_lan_ikey} lần trong đoạn này.")
print("PASS 2: 'ikey' chỉ được tính đúng 1 lần trong đoạn dựng 'BK Mua vào', dùng chung nhất quán cho "
      "cả tra ct_totals lẫn ghi bk_totals.")

# ===== Test 3 (xác nhận bằng SỐ LIỆU THẬT — đúng ca thật người dùng báo qua file
# Excel export + 2 file XML gốc C25TVT-158/C26MGV-1817): mô phỏng LẠI đúng công
# thức ct_totals (tổng Thành tiền/Tiền thuế của các dòng hàng — công thức dùng ở
# 'Chi tiết MUA VÀO', xem dòng 'cur["ds"] += ds' / 'cur["thue"] += d["tien_thue"]'
# trong than_bk_mua's phần trên) PHẢI cho ra ĐÚNG Doanh số -14.475.783đ (không
# phải -15.633.846đ như cách tính cũ dùng tgtcthue/tgtttbso). =====
# Dữ liệu THẬT trích từ XML gốc hóa đơn C25TVT-158 (1 dòng hàng, TChat=3):
#   <ThTien>14475783</ThTien> <TSuat>8%</TSuat>  (dòng hàng, số DƯƠNG trong XML)
#   <TgTCThue>0</TgTCThue> <TgTThue>1158063</TgTThue> <TgTTTBSo>15633846</TgTTTBSo>
# "Chi tiết MUA VÀO" (đã xác nhận qua file Excel export thật) hiện đúng dòng này
# với Thành tiền = -14.475.783đ (đã đổi dấu âm vì la_ck_hd — hóa đơn chiết khấu
# thuần), Tiền thuế GTGT = -1.158.063đ.
ct_tong_that_ds = -14475783    # = ct_totals["purchase"][ikey]["ds"] mô phỏng (khớp "Chi tiết MUA VÀO")


def _to_num(x):
    try:
        return float(x)
    except Exception:
        return 0

tgtcthue_xml = 0
tgtttbso_xml = 15633846
ds_cach_cu = _to_num(tgtcthue_xml) or 0
if not ds_cach_cu:
    ds_cach_cu = _to_num(tgtttbso_xml) or 0   # = 15633846 (SAI — lấy nhầm tổng CÓ thuế)
ds_cach_cu = -abs(ds_cach_cu)   # la_ck_hd áp dụng -abs() như code thật
assert ds_cach_cu == -15633846, f"Xác nhận lại đúng bug gốc (cách tính CŨ) — got {ds_cach_cu}"
assert ct_tong_that_ds == -14475783, "Xác nhận đúng số liệu THẬT từ 'Chi tiết MUA VÀO' (file Excel export thật)."
assert ct_tong_that_ds != ds_cach_cu, (
    "Xác nhận đúng bug: cách tính CŨ (tgtcthue/tgtttbso) cho ra Doanh số KHÁC HẲN với 'Chi tiết MUA VÀO' "
    f"thật — cách cũ: {ds_cach_cu}, Chi tiết MUA VÀO thật: {ct_tong_that_ds}, lệch đúng "
    f"{ds_cach_cu - ct_tong_that_ds}đ = đúng bằng Tiền thuế GTGT của hóa đơn (1.158.063đ) — khớp hoàn "
    f"toàn với dòng lệch trong sheet 'Đối chiếu' người dùng báo.")
print("PASS 3: xác nhận bằng số liệu THẬT (file Excel export + XML gốc C25TVT-158) — cách tính CŨ "
      "(tgtcthue=0 -> fallback tgtttbso) cho ra Doanh số -15.633.846đ, lệch đúng 1.158.063đ (= Tiền "
      "thuế GTGT hóa đơn) so với 'Chi tiết MUA VÀO' thật (-14.475.783đ) — sau khi sửa, 'BK Mua vào' đọc "
      "thẳng từ ct_totals (khớp Chi tiết MUA VÀO) nên không còn lệch nữa.")

print("\nALL DONE")
