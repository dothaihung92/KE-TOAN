import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: _xk_gan_1_muc (Xuất Kho — 'Dò mã hàng tự động') PHẢI ưu
tiên mã hàng ĐÃ CÓ SẴN/ĐANG DÙNG trong MISA (còn tồn Đầu kỳ) hơn 1 mã khác
TRÙNG TÊN nhưng KHÔNG có Đầu kỳ (mã mới/trùng lặp để lại trong MISA), thay vì
lặng lẽ chọn đại theo thứ tự trong file khi tên đã chuẩn hoá giống hệt nhau.

Đúng ca thật người dùng báo cáo kèm 2 ảnh chụp báo cáo MISA "Tổng hợp tồn
kho": sản phẩm "CHẬU POLYSTONE WILV50 - MTBK" bị TÁCH tồn kho ra 3 mã —
'MH451' (Đầu kỳ 20, Xuất 15 — mã công ty ĐANG DÙNG THẬT) và 'MH51' (Đầu kỳ
13, Xuất 0 — cũng mã đang dùng, chưa hề được xuất tới dù vẫn còn tồn) đều bị
"mồ côi", trong khi mã 'TPVT00176' (Đầu kỳ 0, Nhập 50, Xuất 40 — mã mới/
trùng lặp KHÔNG có Đầu kỳ) lại hứng trọn toàn bộ số bán ra đáng lẽ phải đi
vào 2 mã cũ trước — "kiểm tra lại phần đặt mã hàng phần mềm vẫn chưa gộp
đúng mã đã có trong misa trước có trước. tồn đầu kỳ còn mà phần mềm lấy mã
cũ".

Nguyên nhân: _chuan_ten_hang_xk chuẩn hoá tên "CHẬU POLYSTONE WILV50 -
MTBK" của cả 3 mã về HỆT NHAU (không phân biệt được bằng kích thước/mã
trong ngoặc/điểm giống tên) -> sort ỔN ĐỊNH rơi về đúng thứ tự trong file
Tồn kho (ngẫu nhiên, không phản ánh mã nào công ty THẬT SỰ đang dùng) —
nếu mã KHÔNG có Đầu kỳ (mới/trùng) tình cờ đứng trước hoặc còn nhiều tồn
hơn, nó sẽ hút hết các giao dịch bán mới, còn mã cũ còn Đầu kỳ thì bị bỏ
quên dù vẫn còn tồn thật.

Fix: thêm tiêu chí sắp xếp PHỤ (sau bracket-match + điểm giống tên, trước
khi rơi về thứ tự file) — ưu tiên mã có Đầu kỳ (dau_ky, cột "Đầu kỳ - Số
lượng" trong Tồn kho) CAO HƠN, vì đó là bằng chứng khách quan mã đó đã
được dùng liên tục từ trước."""
import sys
sys.path.insert(0, _REPO_ROOT)
import server


def _ton_list(items):
    return [dict(it, con_lai=it["ton"], ten_chuan=server._chuan_ten_hang_xk(it["ten"]))
            for it in items]


# ===== Test 1 (QUAN TRỌNG — đúng ca thật): mã KHÔNG Đầu kỳ đứng TRƯỚC trong file + còn NHIỀU tồn
# hơn (TPVT00176: dau_ky=0, con_lai=50) vs 2 mã CŨ có Đầu kỳ (MH451: dau_ky=20, con_lai=20; MH51:
# dau_ky=13, con_lai=13) — 1 dòng bán số lượng nhỏ (5, đủ cho bất kỳ mã nào) PHẢI ưu tiên mã có
# Đầu kỳ CAO NHẤT (MH451), KHÔNG được chọn TPVT00176 dù nó đứng trước file/còn nhiều tồn hơn. =====
ton1 = _ton_list([
    {"ma": "TPVT00176", "ten": "CHAU POLYSTONE WILV50 - MTBK", "dvt": "Cai", "ton": 50,
     "gia": 200000, "dau_ky": 0},
    {"ma": "MH451", "ten": "CHAU POLYSTONE WILV50 - MTBK", "dvt": "Cai", "ton": 20,
     "gia": 200000, "dau_ky": 20},
    {"ma": "MH51", "ten": "CHAU POLYSTONE WILV50 - MTBK", "dvt": "Cai", "ton": 13,
     "gia": 200000, "dau_ky": 13},
])
it1 = {"ten_sp": "Chậu Polystone WILV50 - MTBK", "sl": 5, "tt": 1000000}
ket1 = server._xk_gan_1_muc(it1, ton1, {})
print("Test 1 (ưu tiên mã còn Đầu kỳ cao nhất):", [(r["ma"], r.get("sl")) for r in ket1])
assert len(ket1) == 1 and ket1[0]["ma"] == "MH451", (
    f"Phải ưu tiên mã 'MH451' (Đầu kỳ 20, cao nhất — mã công ty đang dùng thật) thay vì "
    f"'TPVT00176' (Đầu kỳ 0, dù đứng trước file/còn nhiều tồn hơn) — được {ket1}")

# ===== Test 2 (QUAN TRỌNG — đúng ca thật, NHIỀU dòng bán liên tiếp như thực tế 1 kỳ báo cáo): mỗi
# dòng bán riêng lẻ đủ nhỏ để 1 mã đơn lẻ tự đáp ứng được (không phải TÁCH DÒNG — đúng thực tế: 1
# kỳ có NHIỀU hoá đơn nhỏ chứ không phải 1 hoá đơn khổng lồ) -> vẫn phải DÙNG HẾT MH451 (Đầu kỳ cao
# nhất) trước, rồi mới sang MH51 (Đầu kỳ nhì), CHỈ chạm tới TPVT00176 (Đầu kỳ 0) khi cả 2 mã cũ đã
# cạn — đúng hành vi 'gộp đúng mã đã có trong MISA trước' người dùng yêu cầu, khác hẳn lỗi thật đã
# báo (MH51 Đầu kỳ 13 nhưng Xuất=0 suốt cả kỳ, mọi giao dịch đều dồn vào TPVT00176). =====
ton2 = _ton_list([
    {"ma": "TPVT00176", "ten": "CHAU POLYSTONE WILV50 - MTBK", "dvt": "Cai", "ton": 50,
     "gia": 200000, "dau_ky": 0},
    {"ma": "MH451", "ten": "CHAU POLYSTONE WILV50 - MTBK", "dvt": "Cai", "ton": 20,
     "gia": 200000, "dau_ky": 20},
    {"ma": "MH51", "ten": "CHAU POLYSTONE WILV50 - MTBK", "dvt": "Cai", "ton": 10,
     "gia": 200000, "dau_ky": 10},
])
ma_da_gan = []
for _ in range(4):                                    # 4 dòng bán, mỗi dòng 10 cái = 40 tổng
    it_dong = {"ten_sp": "Chậu Polystone WILV50 - MTBK", "sl": 10, "tt": 2000000}
    ket_dong = server._xk_gan_1_muc(it_dong, ton2, {})
    assert len(ket_dong) == 1, f"Mỗi dòng 10 cái phải đủ 1 mã đơn lẻ đáp ứng — được {ket_dong}"
    ma_da_gan.append(ket_dong[0]["ma"])
print("Test 2 (nhiều dòng bán liên tiếp, đúng thứ tự ưu tiên Đầu kỳ):", ma_da_gan)
assert ma_da_gan == ["MH451", "MH451", "MH51", "TPVT00176"], (
    f"Phải dùng HẾT MH451 (Đầu kỳ 20 -> đủ 2 dòng x10) trước, rồi MH51 (Đầu kỳ 10 -> đủ đúng 1 "
    f"dòng x10 tiếp), CHỈ chạm tới TPVT00176 (Đầu kỳ 0) ở dòng thứ 4 khi cả 2 mã cũ đã cạn — được "
    f"{ma_da_gan}")

# ===== Test 3 (không hồi quy — QUAN TRỌNG): không có dữ liệu Đầu kỳ (dau_ky thiếu/bằng nhau, VD
# ton_list KHÔNG lấy từ báo cáo Tồn kho) -> vẫn rơi về đúng thứ tự trong file như thiết kế gốc
# (test_xk_gan_ma_dung_mau.py 'Đối chứng'), không đổi hành vi cũ khi không có tín hiệu Đầu kỳ. =====
ton3 = [dict(it, con_lai=it["ton"], ten_chuan=server._chuan_ten_hang_xk(it["ten"])) for it in [
    {"ma": "HH00001-8", "ten": "Chậu Polystone D40xH50 cm", "dvt": "Cái", "ton": 50, "gia": 100000},
    {"ma": "MH215-0", "ten": "Chậu Polystone D40xH50 cm", "dvt": "Cái", "ton": 50, "gia": 100000},
]]
it3 = {"ten_sp": "Chậu nhựa-Polystone planter (Kích thước:D40xH50 cm), hàng mới 100%, xuất xứ "
                 "Việt Nam#&VN", "sl": 5, "tt": 500000}
ket3 = server._xk_gan_1_muc(it3, ton3, {})
print("Test 3 (không có dữ liệu Đầu kỳ -> giữ nguyên thứ tự file):",
      [(r["ma"], r.get("sl")) for r in ket3])
assert len(ket3) == 1 and ket3[0]["ma"] == "HH00001-8", (
    f"Khi KHÔNG có dữ liệu Đầu kỳ (thiếu key dau_ky) vẫn phải giữ đúng hành vi cũ (ưu tiên mã "
    f"đứng trước file) — được {ket3}")

print("\nTẤT CẢ TEST PASS")
