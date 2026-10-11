import io
import os
import sys
import urllib.parse

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import openpyxl
import server

# Hỗ trợ thay đổi GPKD: đăng nhập cổng qua VNeID không chạy trong trình duyệt bị điều khiển -> người dùng
# dùng Chrome bình thường; dữ liệu vào phần mềm qua nút bookmark (copy JSON) hoặc file trang đã lưu (Ctrl+S).

# 1) đọc file trang đã lưu: bảng 2/4 cột, input/select/textarea, label for, dt/dd, link gốc trong "saved from url"
html = """<!-- saved from url=(70)https://dangkyquamang.dkkd.gov.vn/Forms/DW_DOCUMENTEdit.aspx?h=720 -->
<html><head><title>Hồ sơ</title></head><body><h2>Thông tin chung</h2><table>
<tr><td>Tên doanh nghiệp:</td><td><input value="CÔNG TY TNHH ABC"></td></tr>
<tr><td>Mã số DN</td><td>0316267842</td><td>Ngày cấp</td><td>01/02/2020</td></tr>
<tr><td>Loại hình</td><td><select><option>Cổ phần</option><option selected>TNHH 1TV</option></select></td></tr>
<tr><td>Vốn điều lệ *</td><td><input type="text" value="1.000.000.000"><input type="hidden" value="x"></td></tr>
<tr><td>Mật khẩu</td><td><input type="password" value="bi-mat"></td></tr>
<tr><td colspan="2">Tiêu đề gộp</td></tr></table>
<label for="g">Ghi chú</label><textarea id="g">abc</textarea>
<dl><dt>Người đại diện</dt><dd>Nguyễn Văn A</dd></dl></body></html>"""
k = server.dkkd_doc_html(html)
assert k["url"].endswith("DW_DOCUMENTEdit.aspx?h=720") and k["khoi"] == "Thông tin chung"
assert k["cap"] == [["Tên doanh nghiệp", "CÔNG TY TNHH ABC"], ["Mã số DN", "0316267842"], ["Ngày cấp", "01/02/2020"],
                    ["Loại hình", "TNHH 1TV"], ["Vốn điều lệ", "1.000.000.000"], ["Ghi chú", "abc"],
                    ["Người đại diện", "Nguyễn Văn A"]], k["cap"]
print("PASS 1: đọc file trang đã lưu đúng các cặp Tiêu đề : Giá trị (bỏ ô mật khẩu/ẩn).")

# 2) endpoint đọc nhiều file: file không có dữ liệu -> báo lỗi riêng
r = server.dkkd_doc_file({"files": [{"ten": "a.html", "noi_dung": html}, {"ten": "rong.html", "noi_dung": "<p>x</p>"}]})
assert len(r["khoi"]) == 1 and r["khoi"][0]["ten_file"] == "a.html" and "rong.html" in r["loi"][0]
print("PASS 2: đọc nhiều file, file rỗng báo riêng.")

# 3) gom theo hồ sơ (tham số h) -> Excel 2 sheet
U = "https://dangkyquamang.dkkd.gov.vn/Forms/"
khoi = [k,
        {"url": U + "DW_Address.aspx?h=720", "khoi": "Địa chỉ", "cap": [["Địa chỉ trụ sở", "1 Lê Lợi"]]},
        {"url": U + "DW_DOCUMENTEdit.aspx?h=800", "khoi": "Thông tin chung", "cap": [["Mã số DN", "0300000001"]]}]
wb = openpyxl.load_workbook(io.BytesIO(server.dkkd_xuat_excel(khoi)))
ct = [[c.value for c in r] for r in wb["Chi tiết"].iter_rows()]
assert ct[0] == ["Hồ sơ", "Khối", "Trường", "Giá trị", "Link"] and len(ct) == 1 + 7 + 1 + 1
th = [[c.value for c in r] for r in wb["Tổng hợp"].iter_rows()]
assert th[0][:3] == ["Hồ sơ", "Tên doanh nghiệp", "Mã số DN"] and "Địa chỉ trụ sở" in th[0]
assert [r[0] for r in th[1:]] == ["h=720", "h=800"]
assert th[1][th[0].index("Địa chỉ trụ sở")] == "1 Lê Lợi" and th[2][th[0].index("Mã số DN")] == "0300000001"
try:
    server.dkkd_xuat_excel_api({"khoi": []})
    raise AssertionError("phải báo lỗi")
except server.HTTPException as e:
    assert e.status_code == 400
print("PASS 3: gom các khối theo mã hồ sơ, xuất Chi tiết + Tổng hợp.")

# 4) bookmarklet: javascript: hợp lệ, chứa đúng đoạn đọc trang, chỉ copy vào clipboard (không gửi mạng)
bm = server.dkkd_bookmarklet()
assert bm.startswith("javascript:") and " " not in bm
than = urllib.parse.unquote(bm[len("javascript:"):])
assert "navigator.clipboard" in than and "querySelectorAll('tr')" in than
assert "fetch(" not in than and "XMLHttpRequest" not in than and ".submit(" not in than and ".click()" not in than
print("PASS 4: mã bookmark chỉ đọc trang và copy, không gửi/bấm gì.")

# 5) giao diện: bỏ TMĐT + bỏ Chrome tự động; có 2 cách nhập
html_ui = open(os.path.join(_REPO_ROOT, "static", "index.html"), encoding="utf-8").read()
src = open(os.path.join(_REPO_ROOT, "server.py"), encoding="utf-8").read()
assert "moTmdt" not in html_ui and "/api/tmdt/" not in src
assert 'onclick="moGpkd()"' in html_ui and "/api/dkkd/doc-file" in html_ui and "gpkdThemDan" in html_ui
assert "KHÔNG dán mã vào thanh địa chỉ" in html_ui and "Thêm trang..." in html_ui   # Chrome bỏ 'javascript:' khi dán vào thanh địa chỉ
assert "/api/dkkd/mo-trinh-duyet" not in src and "chrome_dkkd" not in src
print("PASS 5: giao diện mới (bookmark + file đã lưu), không còn mở Chrome tự động.")

print("\nALL DONE")
