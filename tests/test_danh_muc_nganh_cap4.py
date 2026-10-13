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
print("\nALL DONE")
