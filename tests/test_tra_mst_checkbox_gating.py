import os
import textwrap

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test cho tham số tra_mst trong export_excel() (server.py) —
# người dùng yêu cầu: "thêm nút tick tra cứu tình trạng mst khi nào tick
# vào thì mới cho chạy tra cứu này còn không tíck thì không cần chạy" —
# thêm checkbox "🔍 Tra cứu tình trạng MST" (mặc định TẮT, nhớ riêng theo
# từng công ty qua companies.tra_mst_mac_dinh) ở màn hình Tra cứu & tải hóa
# đơn; export_excel() nhận query param tra_mst (mặc định 0) để BẬT/TẮT hẳn
# việc gọi mạng ra ngoài (api.vietqr.io/masothue.com/XInvoice) dò tình trạng MST.
#
# export_excel() quá lớn để extract nguyên hàm (như đã làm với các hàm nhỏ
# khác trong file này) -> trích xuất ĐÚNG 2 đoạn code thật quyết định việc
# CÓ gọi mạng dò MST hay không, verify trực tiếp bằng exec() với stub, để
# chắc chắn test chạy đúng logic ĐANG có trong file, không lệch bản.


def _extract_from_to(start_marker, end_marker, end_inclusive=True):
    i0 = src.index(start_marker)
    i0 = src.rfind("\n", 0, i0) + 1
    i1 = src.index(end_marker, i0)
    if end_inclusive:
        i1 += len(end_marker)
    return textwrap.dedent(src[i0:i1])


# ----- Đoạn 1: gọi _prefetch_trang_thai_mst() SONG SONG cho cả sheet "BK Mua
# vào" -- CHỈ khi tra_mst truthy. -----
block1 = _extract_from_to(
    "if tra_mst:",
    '"BK Mua vào", (r["nbmst"] for r in rows_mua_vao if _hd_dung_cty(r, "purchase")))')
assert "if tra_mst:" in block1 and "_prefetch_trang_thai_mst" in block1, (
    "Không trích xuất đúng đoạn gọi _prefetch_trang_thai_mst có điều kiện tra_mst")

_goi_prefetch = []


def _fake_prefetch(nhan, danh_sach_mst):
    _goi_prefetch.append((nhan, list(danh_sach_mst)))


def _fake_hd_dung_cty(r, loai):
    return True


rows_mua_vao_gia = [{"nbmst": "0311111111"}, {"nbmst": "0322222222"}]

# tra_mst=0 (mặc định, CHƯA tick) -> KHÔNG được gọi _prefetch_trang_thai_mst.
_goi_prefetch.clear()
ns0 = {"tra_mst": 0, "rows_mua_vao": rows_mua_vao_gia,
      "_hd_dung_cty": _fake_hd_dung_cty, "_prefetch_trang_thai_mst": _fake_prefetch}
exec(compile(block1, "<block1>", "exec"), ns0)
assert len(_goi_prefetch) == 0, (
    f"tra_mst=0 (chưa tick checkbox) -> TUYỆT ĐỐI KHÔNG được gọi _prefetch_trang_thai_mst (không gọi "
    f"mạng dò MST) — got {_goi_prefetch}")
print("PASS 1: tra_mst=0 (checkbox chưa tick) -> KHÔNG gọi _prefetch_trang_thai_mst, không dò MST.")

# tra_mst=1 (ĐÃ tick) -> PHẢI gọi _prefetch_trang_thai_mst đúng như trước.
_goi_prefetch.clear()
ns1 = {"tra_mst": 1, "rows_mua_vao": rows_mua_vao_gia,
      "_hd_dung_cty": _fake_hd_dung_cty, "_prefetch_trang_thai_mst": _fake_prefetch}
exec(compile(block1, "<block1>", "exec"), ns1)
assert len(_goi_prefetch) == 1 and _goi_prefetch[0][0] == "BK Mua vào", (
    f"tra_mst=1 (đã tick checkbox) -> PHẢI gọi _prefetch_trang_thai_mst cho sheet BK Mua vào như bình "
    f"thường — got {_goi_prefetch}")
assert len(_goi_prefetch[0][1]) == 2, f"Phải truyền đủ danh sách MST — got {_goi_prefetch[0][1]}"
print("PASS 2: tra_mst=1 (checkbox đã tick) -> gọi _prefetch_trang_thai_mst bình thường như trước khi "
      "có checkbox.")

# ----- Đoạn 2: đọc kết quả tình trạng MST cho TỪNG dòng (mst_info_ncc) — khi
# tra_mst=0 phải trả thẳng dict rỗng, KHÔNG gọi _lay_trang_thai_mst_cached
# (tránh dò từng dòng riêng lẻ dù đã tắt prefetch, vẫn có thể lỡ gọi mạng). -----
block2 = _extract_from_to(
    'mst_info_ncc = (_lay_trang_thai_mst_cached(r["nbmst"]) if tra_mst',
    'else {"trang_thai": "", "canh_bao": None})')
assert "tra_mst" in block2 and "_lay_trang_thai_mst_cached" in block2, (
    "Không trích xuất đúng đoạn đọc mst_info_ncc có điều kiện tra_mst")

_goi_cached = []


def _fake_cached(mst):
    _goi_cached.append(mst)
    return {"trang_thai": "Đang hoạt động", "canh_bao": False}


r_gia = {"nbmst": "0311111111"}

_goi_cached.clear()
ns2a = {"tra_mst": 0, "r": r_gia, "_lay_trang_thai_mst_cached": _fake_cached}
exec(compile(block2, "<block2>", "exec"), ns2a)
assert len(_goi_cached) == 0, (
    f"tra_mst=0 -> KHÔNG được gọi _lay_trang_thai_mst_cached cho TỪNG dòng (dù đã tắt prefetch, lỡ gọi "
    f"riêng lẻ vẫn là gọi mạng dò MST ngoài ý muốn) — got {_goi_cached} lượt gọi")
assert ns2a["mst_info_ncc"] == {"trang_thai": "", "canh_bao": None}, (
    f"tra_mst=0 -> mst_info_ncc phải là dict rỗng an toàn — got {ns2a['mst_info_ncc']}")
print("PASS 3: tra_mst=0 -> mst_info_ncc trả thẳng dict rỗng cho từng dòng, KHÔNG gọi "
      "_lay_trang_thai_mst_cached (không lỡ dò mạng dù đã tắt checkbox).")

_goi_cached.clear()
ns2b = {"tra_mst": 1, "r": r_gia, "_lay_trang_thai_mst_cached": _fake_cached}
exec(compile(block2, "<block2>", "exec"), ns2b)
assert _goi_cached == ["0311111111"], f"tra_mst=1 -> phải gọi _lay_trang_thai_mst_cached — got {_goi_cached}"
assert ns2b["mst_info_ncc"]["canh_bao"] is False
print("PASS 4: tra_mst=1 -> vẫn gọi _lay_trang_thai_mst_cached cho từng dòng như bình thường.")

# ----- Đoạn 3: endpoint export_excel có tham số tra_mst mặc định 0 (TẮT). -----
assert "tra_mst: int = 0" in src, (
    "export_excel() phải có tham số tra_mst mặc định 0 (TẮT) — chỉ BẬT khi người dùng chủ ý tick "
    "checkbox, đúng yêu cầu người dùng")
print("PASS 5: export_excel() có tham số tra_mst mặc định TẮT (0).")

print("\nALL DONE")
