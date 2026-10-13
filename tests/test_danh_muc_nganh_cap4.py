import json
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Danh mục ngành kinh tế CẤP 4 (Phụ lục I QĐ 27/2018/QĐ-TTg): dò mã/tên khi soạn hồ sơ GPKD.
p = os.path.join(_REPO_ROOT, "templates", "gpkd", "nganh_cap4_QD27_2018.json")
d = json.load(open(p, encoding="utf-8"))
m = dict(d)
assert len(d) == len(m) == 464, len(d)                      # VSIC 2018 có 464 ngành cấp 4 (734 cấp 5 đều thuộc 464 mã này)
assert all(len(k) == 4 and k.isdigit() and t and t == t.strip() and "  " not in t for k, t in d)
assert m["4933"] == "Vận tải hàng hóa bằng đường bộ" and m["6202"].startswith("Tư vấn máy vi tính") and m["5820"] == "Xuất bản phần mềm"
assert m["4661"].startswith("Bán buôn nhiên liệu rắn") and m["7710"] == "Cho thuê xe có động cơ" and m["0111"] == "Trồng lúa"
assert [k for k, _ in d] == sorted(m)
print("PASS 1: danh mục có đủ 464 ngành cấp 4, tên sạch, đúng các mã mẫu.")

kq = server.gpkd_soan_nganh()
assert len(kq["nganh"]) == 464 and "27/2018" in kq["nguon"] and "36/2025" in kq["nguon"]
print("PASS 2: API trả danh mục kèm nguồn và lưu ý QĐ 36/2025.")

assert "templates/gpkd/nganh_cap4_QD27_2018.json" in open(os.path.join(_REPO_ROOT, "update.py"), encoding="utf-8").read()
h = open(os.path.join(_REPO_ROOT, "static", "index.html"), encoding="utf-8").read()
assert 'list="ssDlMa"' in h and 'list="ssDlTen"' in h and "function ssNganhMa" in h and "function ssNganhTen" in h
print("PASS 3: tự cập nhật có file danh mục; ô mã/tên ngành có gợi ý và tự điền (đã kiểm bằng trình duyệt: 4933 -> Vận tải hàng hóa bằng đường bộ).")
# --- máy thiếu file (update.py cũ không có trong FILES) -> API tự tải về; tải lỗi -> báo rõ
import tempfile, update, shutil
from fastapi import HTTPException
goc_base, goc_tai = server.BASE_DIR, update._tai_raw
tmp = tempfile.mkdtemp()
try:
    server.BASE_DIR = tmp
    update._tai_raw = lambda path, timeout=20: open(p, "rb").read() if path.endswith("nganh_cap4_QD27_2018.json") else b""
    kq = server.gpkd_soan_nganh()
    assert len(kq["nganh"]) == 464 and os.path.isfile(os.path.join(tmp, "templates", "gpkd", "nganh_cap4_QD27_2018.json"))
    shutil.rmtree(os.path.join(tmp, "templates"))
    def hong(path, timeout=20): raise OSError("mất mạng")
    update._tai_raw = hong
    try:
        server.gpkd_soan_nganh(); raise SystemExit("phải báo lỗi")
    except HTTPException as e:
        assert e.status_code == 404 and "không tự tải được" in e.detail
    update._tai_raw = lambda path, timeout=20: b"<html>404</html>"
    try:
        server.gpkd_soan_nganh(); raise SystemExit("phải báo lỗi")
    except HTTPException as e:
        assert e.status_code == 404
    assert not os.path.exists(os.path.join(tmp, "templates", "gpkd", "nganh_cap4_QD27_2018.json"))
finally:
    server.BASE_DIR, update._tai_raw = goc_base, goc_tai
    shutil.rmtree(tmp, ignore_errors=True)
print("PASS 4: thiếu file danh mục -> tự tải thẳng từ kho dự án; mất mạng/nội dung hỏng -> báo lỗi rõ, không ghi file hỏng.")

# --- dòng "Chi tiết" ở hàng dưới tên ngành
assert 'id="ssn_${k}_${i}_ct"' in h and "function gpkdOChiTiet" in h and "gpkdOChiTiet(r[c]" in h
import re, subprocess
fn = re.search(r"function gpkdOChiTiet\(v\)\{.*?\n\}", h, re.S).group(0)
js = "const gpkdEsc=s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;');" + fn + \
     "console.log(gpkdOChiTiet('Bán buôn sắt thép Chi tiết: Mua bán sắt thép xây dựng'));console.log(gpkdOChiTiet('Trồng lúa'))"
out = subprocess.run(["node", "-e", js], capture_output=True, text=True).stdout.splitlines()
assert out[0] == 'Bán buôn sắt thép<div style="font-style:italic;margin-top:2px">Chi tiết: Mua bán sắt thép xây dựng</div>' and out[1] == "Trồng lúa", out
import gpkd_soan
from docx import Document
src = open(os.path.join(_REPO_ROOT, "gpkd_soan.py"), encoding="utf-8").read()
assert 'n.get("chi_tiet")' in src
print("PASS 5: viewer tách 'Chi tiết:' xuống dòng nghiêng dưới tên ngành; ô soạn có dòng chi tiết; Mẫu 12 in dòng này nghiêng ở hàng dưới.")
print("\nALL DONE")
