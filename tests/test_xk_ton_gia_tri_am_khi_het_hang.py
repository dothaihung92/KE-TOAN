import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: đúng ca thật người dùng gửi (file TONG_HOP_TON_KHO.xlsx)
— 15/449 mã có Cuối kỳ Số lượng = 0 (hết sạch hàng trong kỳ) nhưng Cuối kỳ
Giá trị lại ÂM vài đồng đến vài trăm đồng (vd 'HH00008-10' SL=0, Giá trị=-2;
'MH451' SL=0, Giá trị=-461) — người dùng báo "file xuất kho có khá nhiều
dòng xuất hàng bị - giá trị".

Nguyên nhân: MISA tự làm tròn "Giá trị" ở TỪNG dòng Xuất kho riêng lẻ (giá
vốn bình quân gia quyền) trước khi cộng dồn vào báo cáo — khi 1 mã bị xuất
HẾT trong kỳ (Cuối kỳ SL đúng 0), phần dư làm tròn cộng dồn qua nhiều lần
xuất khiến "Giá trị Cuối kỳ" (= Đầu kỳ GT + Nhập kho GT - Xuất kho GT) lệch
ÂM một chút dù về bản chất không còn hàng thì không thể còn "giá trị âm".
_doc_file_ton_kho/_misa_lay_ton_kho trước đây giữ NGUYÊN số âm nhỏ đó vào
field "gia_tri" (dùng để cộng badge "Tổng giá trị tồn cuối kỳ", xem
test_xk_ton_gia_tri_chinh_xac.py) — khiến badge bị trừ nhầm và mã đó hiện
"-2đ"/"-461đ" dù thực chất tồn = 0.

Fix: ép "gia_tri" về ĐÚNG 0 khi tồn (Số lượng Cuối kỳ) = 0 — bất kể "Giá
trị" gốc trong file dương/âm bao nhiêu, tồn 0 thì giá trị PHẢI 0."""
import sys
sys.path.insert(0, _REPO_ROOT)
import server


def test_gia_tri_am_khi_het_hang_bi_ep_ve_0():
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Báo cáo"
    ws.append(["TỔNG HỢP TỒN KHO"])
    ws.append(["Kho: HH; Năm 2025"])
    ws.append([None, "Mã hàng", "Tên hàng", "ĐVT", "Đầu kỳ", None, "Nhập kho", None,
               "Xuất kho", None, "Cuối kỳ", None])
    ws.append([None, None, None, None, "Số lượng", "Giá trị", "Số lượng", "Giá trị",
               "Số lượng", "Giá trị", "Số lượng", "Giá trị"])
    ws.append(["Tên kho : HH (2 )", None, None, None, 8, 2105974, 0, 0, 8, 2105976, 0, -2])
    # Đúng dữ liệu THẬT từ file người dùng gửi: Đầu kỳ 8/2.105.974đ, Xuất hết
    # cả 8 nhưng MISA làm tròn Giá trị Xuất kho dôi lên 2.105.976đ (2đ) ->
    # Cuối kỳ SL=0 nhưng Giá trị=-2 (ÂM dù không còn hàng).
    ws.append([None, "HH00008-10", "CHẤT CHỐNG THẤM CO GIÃN KOVA CT14", "Kg", 8, 2105974, 0, 0, 8, 2105976, 0, -2])
    # Mã còn tồn thật (SL>0, Giá trị dương bình thường) — PHẢI giữ nguyên,
    # không bị đụng tới bởi fix này.
    ws.append([None, "MH-CON-TON", "Hàng còn tồn", "Cái", 0, 0, 5, 500000, 0, 0, 5, 500000])
    ws.append(["Số dòng = 2", None, None, None, 8, 2105974, 5, 500000, 8, 2105976, 5, 499998])

    rows, danh_sach_kho = server._doc_file_ton_kho(wb)
    by_ma = {r["ma"]: r for r in rows}

    het = by_ma["HH00008-10"]
    assert het["ton"] == 0, f"Cuối kỳ Số lượng phải đúng 0 (hết sạch hàng) — được {het['ton']}"
    assert het["gia_tri"] == 0, (
        f"'gia_tri' PHẢI bị ép về 0 khi tồn=0 — tồn=0 thì không thể còn 'giá trị âm' dù file gốc ghi -2đ "
        f"(lỗi làm tròn cộng dồn của MISA) — được {het['gia_tri']}")
    assert het["gia"] == 0, f"'gia' (đơn giá bình quân) khi tồn=0 vẫn phải là 0 như cũ — được {het['gia']}"

    con = by_ma["MH-CON-TON"]
    assert con["gia_tri"] == 500000, f"Mã còn tồn thật (SL>0) KHÔNG được đụng tới — got {con['gia_tri']}"
    assert con["gia"] == 100000

    tong_gia_tri = sum(r["gia_tri"] for r in rows)
    assert tong_gia_tri == 500000, (
        f"Tổng 'gia_tri' (dùng cho badge 'Tổng giá trị tồn cuối kỳ') phải đúng 500.000đ (chỉ còn mã "
        f"MH-CON-TON, mã đã hết hàng không còn đóng góp -2đ rác nữa) — được {tong_gia_tri}")
    print("PASS: mã hết sạch hàng (Cuối kỳ SL=0) có Giá trị ÂM do làm tròn cộng dồn của MISA (đúng ca "
          "thật 'HH00008-10' Giá trị=-2đ) được ép về ĐÚNG 0, không còn làm sai badge tổng giá trị tồn "
          "kho hay hiện '-2đ' gây hiểu lầm; mã còn tồn thật không bị đụng tới.")


test_gia_tri_am_khi_het_hang_bi_ep_ve_0()

print("\nTẤT CẢ TEST PASS")
