import os, sys
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

# Ca thật: lấy ĐỦ hóa đơn (82/82 mua, 207/207 bán) nhưng 247 file XML (hóa đơn máy tính tiền) chưa tải được -> khung đỏ
# "Lỗi/cảnh báo lần tra cứu gần nhất" vẫn hiện dù không có sai sót gì với dữ liệu hóa đơn. Nay khung CHỈ giữ lại khi:
# lỗi tra cứu / thiếu so với trang Thuế / hóa đơn không lấy được chi tiết lẫn file / lỗi tải file. Chỉ thiếu file XML -> không hiện khung.
src = open(os.path.join(_REPO_ROOT, "server.py"), encoding="utf-8").read()
html = open(os.path.join(_REPO_ROOT, "static", "index.html"), encoding="utf-8").read()
msg = src[src.index("        stage = kw.get(\"stage\")\n        if stage == \"error\":"):][:900]
assert 'if kw.get("canh_bao_nang"):' in msg and "file_thieu" not in msg, msg
assert "canh_bao_nang=bool(thieu or thieu_chi_tiet or loi_tai_file_ngoai_le)" in src
assert "renderFetchErrorBanner(m.canh_bao_nang" in html and "renderFetchErrorBanner(m.file_thieu" not in html
# lỗi tra cứu (stage=error) vẫn lưu + hiện khung như cũ
assert 'if stage == "error":\n            _luu_loi_tra_cuu(cid, kw.get("text") or "")' in src
assert "renderFetchErrorBanner({last_fetch_error:m.text" in html
print("PASS: khung cảnh báo tra cứu chỉ hiện khi lỗi/thiếu hóa đơn thật sự; lấy đủ mà chỉ thiếu file XML thì không hiện.")
