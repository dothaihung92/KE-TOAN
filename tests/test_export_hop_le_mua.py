import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: bộ lọc _hop_le_mua trong export_excel (server.py) trước
đây ÂM THẦM loại hóa đơn Mua vào có MST người mua khác MST công ty, không ghi
lại/báo gì cả — khiến hóa đơn "biến mất" khỏi Bảng kê Đầu vào mà người dùng
không biết vì sao (đúng ca thật: hóa đơn MST 0317743519/Số HĐ 3381 có trong
dữ liệu tra cứu nhưng không có trong Bảng kê Đầu vào lẫn MISA). Test verify:
1. Logic lọc GIỮ NGUYÊN hành vi cũ (hóa đơn khớp MST/MST khác/rỗng vẫn qua).
2. Hóa đơn bị loại giờ được GHI LẠI vào hd_loai_mst_mua với đủ thông tin
   (Số HĐ, MST trên hóa đơn, ngày) để người dùng tự tra cứu/đối chiếu.

Extract ĐÚNG đoạn code thật trong server.py (regex theo mốc dòng
'mst_cty_goc = _chuan_mst(comp["mst"])[:10]' -> 'loai_rows = [r for r in
loai_rows if _hop_le_mua(r)]') thay vì chép tay lại, để chắc chắn test chạy
đúng logic ĐANG có trong file, không lệch bản."""
import sys, re, textwrap
sys.path.insert(0, _REPO_ROOT)
import server


def extract_block():
    src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()
    start_marker = 'mst_cty_goc = _chuan_mst(comp["mst"])[:10]'
    end_marker = "loai_rows = [r for r in loai_rows if _hop_le_mua(r)]"
    i0 = src.index(start_marker)
    i0 = src.rfind("\n", 0, i0) + 1   # lùi về ĐẦU DÒNG để giữ đủ khoảng trắng đầu dòng 1
    i1 = src.index(end_marker, i0) + len(end_marker)
    block = src[i0:i1]
    return textwrap.dedent(block)


def chay(comp, loai_rows_vao):
    ns = {"_chuan_mst": server._chuan_mst, "_ds_mst_khac": server._ds_mst_khac,
          "comp": comp, "loai_rows": loai_rows_vao, "hd_loai_mst_mua": []}
    exec(compile(extract_block(), "<hop_le_mua>", "exec"), ns)
    return ns["loai_rows"], ns["hd_loai_mst_mua"]


class FakeComp(dict):
    def keys(self):
        return dict.keys(self)


class FakeRow(dict):
    def __getitem__(self, k):
        return dict.get(self, k)


comp = FakeComp({"mst": "0100000000", "mst_khac": ""})
rows_vao = [
    FakeRow({"nmmst": "0100000000", "shdon": "1", "tdlap": "2026-08-10T00:00:00"}),   # đúng MST cty -> giữ
    FakeRow({"nmmst": "", "shdon": "2", "tdlap": "2026-08-11T00:00:00"}),              # rỗng -> giữ
    FakeRow({"nmmst": "0100000000-001", "shdon": "3", "tdlap": "2026-08-12T00:00:00"}),  # 13 số cùng gốc -> giữ
    FakeRow({"nmmst": "0999999999", "shdon": "3381", "tdlap": "2026-08-13T00:00:00"}),   # KHÁC hẳn -> loại + ghi lại
]

loai_rows_ra, hd_loai_mst_mua = chay(comp, rows_vao)

assert len(loai_rows_ra) == 3, f"Phải giữ đúng 3 hóa đơn hợp lệ (rỗng/khớp/13 số cùng gốc), được {len(loai_rows_ra)}"
assert all(r["shdon"] != "3381" for r in loai_rows_ra), "Hóa đơn 3381 (MST khác hẳn) phải bị loại khỏi Excel như cũ"
print("PASS: hành vi lọc GIỮ NGUYÊN như cũ (giữ đúng 3, loại đúng 1).")

assert len(hd_loai_mst_mua) == 1, f"Phải ghi lại ĐÚNG 1 hóa đơn bị loại, được {len(hd_loai_mst_mua)}"
ghi = hd_loai_mst_mua[0]
assert ghi["so_hd"] == "3381" and ghi["mst_tren_hd"] == "0999999999" and ghi["ngay"] == "2026-08-13", (
    f"Thông tin ghi lại sai: {ghi}")
print("PASS: hóa đơn bị loại được GHI LẠI đúng (Số HĐ, MST trên hóa đơn, ngày) — "
      "không còn 'biến mất' âm thầm như trước.")

# Test 2: có khai báo "MST khác" -> hóa đơn khớp MST KHÁC vẫn được giữ, KHÔNG
# bị ghi vào danh sách loại (đúng mục đích của MST khác).
comp2 = FakeComp({"mst": "0100000000", "mst_khac": "0999999999"})
loai_rows_ra2, hd_loai_mst_mua2 = chay(comp2, rows_vao)
assert len(loai_rows_ra2) == 4, f"Có MST khác khớp -> phải giữ đủ cả 4, được {len(loai_rows_ra2)}"
assert not hd_loai_mst_mua2, f"Có MST khác khớp -> không được ghi vào danh sách loại, được {hd_loai_mst_mua2}"
print("PASS: đã khai báo đúng 'MST khác' -> hóa đơn được giữ lại, không bị báo loại nữa.")

print("\nTẤT CẢ TEST PASS")
