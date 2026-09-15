import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test cho phan_bo_chiet_khau() (nested trong export_excel(), server.py) —
# người dùng gửi kèm HĐ C25MHY-1387 (CÔNG TY TNHH PHÂN PHỐI HÀNG TIÊU DÙNG HOÀNG YẾN,
# bán cho NGUYỄN KIỀU THANH TRÚC MST 0307293740) và báo: "hoá đơn 1387 này có chiết
# khấu thương mại nhưng phần chi tiết phần mềm không tính chung vào đơn giá làm cho
# đối chiếu bị lệch với bảng kê đầu vào".
#
# Dữ liệu THẬT từ file XML hóa đơn: 3 dòng hàng (Mì Gấu Đỏ, cùng thuế suất 8%,
# SLuong/DGia đầy đủ) + 1 dòng "Chiết khấu hàng bán" (SLuong=0, DGia=0,
# ThTien=1734815) — NHƯNG dòng chiết khấu này ghi TChat=2 (đúng chuẩn hóa đơn điện
# tử TChat=2 là "Khuyến mại", TChat=3 mới là "Chiết khấu thương mại" — nhà cung cấp
# hóa đơn này ghi SAI/không đúng chuẩn). TgTCThue (Tổng tiền chưa thuế CHÍNH THỨC
# của hóa đơn) = 25.185.185đ = (6.730.000 + 10.095.000 + 10.095.000) - 1.734.815 —
# xác nhận dòng "Chiết khấu hàng bán" PHẢI được TRỪ, không phải cộng dương.
#
# TRƯỚC KHI SỬA: phan_bo_chiet_khau() CHỈ nhận diện "dòng chiết khấu thương mại
# riêng" qua đúng TChat=="3" — dòng TChat=2 này lọt qua như 1 dòng hàng BÌNH
# THƯỜNG, bị CỘNG DƯƠNG vào tổng thay vì trừ, khiến tổng "Chi tiết" hóa đơn phần
# mềm tính ra (28.654.815đ) lệch hẳn với TgTCThue chính thức (25.185.185đ) VÀ lệch
# với Bảng kê đầu vào (vốn ghi đúng theo số chính thức của hóa đơn).


def extract_fn(name):
    """Trích xuất hàm TOP-LEVEL (không nested) — dò tới dòng đầu tiên thụt lề về
    cột 0 (cách làm sẵn có, dùng chung nhiều test khác trong repo)."""
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


def extract_nested_fn(name):
    """Trích xuất hàm NESTED bên trong 1 hàm khác (như phan_bo_chiet_khau bên
    trong export_excel) — dò theo ĐÚNG mức thụt lề của chính dòng 'def name(' (chứ
    không phải cột 0, vì hàm này không nằm ở cột 0) — dừng ở dòng đầu tiên thụt lề
    <= mức đó, đúng ranh giới thật của hàm nested (extract_fn kiểu cũ sẽ 'ăn' luôn
    toàn bộ phần còn lại của hàm export_excel bao ngoài, gây lỗi cú pháp thụt lề)."""
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


ns = {}
exec(extract_fn('_to_num'), ns)
exec(extract_fn('_parse_thue_suat'), ns)
exec(extract_nested_fn('phan_bo_chiet_khau'), ns)
_to_num = ns['_to_num']
phan_bo_chiet_khau = ns['phan_bo_chiet_khau']


def item(tchat, ten, sl, dg, tt, tsuat="8%", ck=0):
    return {"tchat": tchat, "ten_hang": ten, "sluong": sl, "dgia": dg,
            "thtien": tt, "tsuat": tsuat, "stckhau": ck}


# ----- Test 1 (ca thật HĐ C25MHY-1387): dòng "Chiết khấu hàng bán" ghi TChat=2
# (sai chuẩn) vẫn PHẢI được nhận diện là chiết khấu thương mại riêng và TRỪ vào
# thành tiền các dòng hàng, để tổng "Chi tiết" khớp ĐÚNG TgTCThue chính thức. -----
items_1387 = [
    item("1", "900000172 -  Mì Gấu Đỏ 30 gói Chay RN", 100, 67300, 6730000),
    item("1", "900000173 -  Mì Gấu Đỏ 30 gói Gà SP", 150, 67300, 10095000),
    item("1", "900000175 -  Mì Gấu Đỏ 30 gói Tôm Gà", 150, 67300, 10095000),
    item("2", "Chiết khấu hàng bán", 0, 0, 1734815),   # TChat=2 (sai chuẩn), không phải 3
]
out = phan_bo_chiet_khau(items_1387, tgtcthue_hd=25185185)
assert len(out) == 3, (
    f"Dòng 'Chiết khấu hàng bán' (TChat=2) PHẢI bị loại khỏi danh sách dòng hàng hiển thị (đã gộp "
    f"trừ vào các dòng khác), KHÔNG được hiện như 1 dòng hàng riêng — got {len(out)} dòng: {out}")
assert not any("chiết khấu" in str(o.get("ten_hang", "")).lower() for o in out), (
    f"Không được còn dòng nào tên 'Chiết khấu...' trong kết quả — dòng CK phải được PHÂN BỔ TRỪ, "
    f"không giữ lại riêng — got {out}")
tong_thtien = sum(_to_num(o.get("thtien")) or 0 for o in out)
assert abs(tong_thtien - 25185185) <= 1, (
    f"Tổng thành tiền các dòng SAU KHI trừ chiết khấu PHẢI khớp ĐÚNG TgTCThue chính thức của hóa đơn "
    f"(25.185.185đ) — nếu dòng CK bị cộng dương nhầm thì tổng sẽ ra 28.654.815đ (lệch nguyên "
    f"2 x 1.734.815đ) — got {tong_thtien}")
print("PASS 1: dòng 'Chiết khấu hàng bán' ghi TChat=2 (sai chuẩn, không phải TChat=3) VẪN được nhận "
      "diện đúng là chiết khấu thương mại riêng, trừ đúng vào thành tiền — khớp TgTCThue chính thức, "
      "không còn lệch với Bảng kê đầu vào như người dùng báo.")

# ----- Test 2 (không hồi quy — quan trọng): dòng chiết khấu ĐÚNG CHUẨN TChat=3
# (không cần dò theo tên) vẫn phải hoạt động y hệt như trước — không bị ảnh hưởng
# bởi thay đổi thêm điều kiện nhận diện theo tên. -----
items_tchat3 = [
    item("1", "Sản phẩm A", 10, 100000, 1000000),
    item("1", "Sản phẩm B", 5, 100000, 500000),
    item("3", "CK 10%", 0, 0, 150000),   # TChat=3 đúng chuẩn, tên KHÔNG có chữ "chiết khấu"
]
out2 = phan_bo_chiet_khau(items_tchat3, tgtcthue_hd=1350000)
assert len(out2) == 2, f"TChat=3 (đúng chuẩn) vẫn phải nhận diện như cũ, không hồi quy — got {out2}"
tong2 = sum(_to_num(o.get("thtien")) or 0 for o in out2)
assert abs(tong2 - 1350000) <= 1, f"TChat=3 vẫn phải trừ đúng như hành vi cũ — got {tong2}"
print("PASS 2: dòng chiết khấu ĐÚNG CHUẨN TChat=3 (không cần dò theo tên) vẫn hoạt động y hệt trước "
      "đây — không hồi quy.")

# ----- Test 3 (an toàn/không hồi quy — QUAN TRỌNG): 1 dòng hàng THẬT (TChat=1, có
# đủ SLuong/DGia) mà tên SẢN PHẨM tình cờ chứa chữ "chiết khấu" KHÔNG được coi
# nhầm là dòng chiết khấu riêng (phải giữ nguyên là hàng hóa bình thường) — vì có
# SLuong/DGia thật (khác hẳn dòng CK chỉ có tiền, không SL/đơn giá). -----
items_ten_trung = [
    item("1", "Bột giặt Chiết Khấu Xanh 3kg", 10, 50000, 500000),
    item("1", "Sản phẩm khác", 5, 20000, 100000),
]
out3 = phan_bo_chiet_khau(items_ten_trung, tgtcthue_hd=600000)
assert len(out3) == 2, (
    f"Dòng hàng THẬT có SL/đơn giá dù tên trùng chữ 'chiết khấu' KHÔNG được loại bỏ nhầm — got {out3}")
assert any("Bột giặt Chiết Khấu Xanh" in str(o.get("ten_hang", "")) for o in out3), (
    f"Dòng 'Bột giặt Chiết Khấu Xanh 3kg' (hàng thật, có SL/đơn giá) phải GIỮ NGUYÊN, không bị coi "
    f"nhầm là dòng chiết khấu riêng chỉ vì tên có chữ 'chiết khấu' — got {out3}")
print("PASS 3: hàng hóa THẬT có SL/đơn giá dù tên sản phẩm trùng chữ 'chiết khấu' KHÔNG bị nhận nhầm "
      "thành dòng chiết khấu riêng (chỉ áp dụng khi KHÔNG có SL/đơn giá, đúng đặc trưng dòng chiết "
      "khấu gộp).")

print("\nALL DONE")
