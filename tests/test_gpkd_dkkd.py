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

# 1b) trang thật (ảnh người dùng gửi, bản .154 chỉ lấy được khung "Thông tin về hồ sơ"): dòng "Quốc gia: [ô chọn] [biểu
#     tượng ?]" (giá trị KHÔNG ở ô cuối), bảng danh sách Ngành nghề nhiều cột, tên khối lấy từ dòng "Trang chủ > ... > Khối"
that = """<div>Trang chủ &gt; DANH SÁCH HỒ SƠ ĐĂNG KÝ &gt; Khối dữ liệu &gt; Ngành nghề kinh doanh</div>
<table><tr><td><div>Thông tin về hồ sơ</div><table>
 <tr><td>Dừng thực hiện thủ tục đăng ký doanh nghiệp:</td><td><input type="checkbox" disabled></td></tr>
 <tr><td>Số hồ sơ:</td><td>OD-0780566/26</td></tr></table></td></tr></table>
<table>
 <tr><td>Quốc gia:</td><td><select disabled><option>Chọn</option><option selected>Việt Nam</option></select></td><td><img src="h.png"></td></tr>
 <tr><td>Số nhà/đường/phố/tổ/xóm/ấp/thôn:</td><td><input value="28 đường số 3 KDC Khang An"></td><td><img src="h.png"></td></tr>
</table>
<div>Danh sách ngành nghề kinh doanh</div>
<div>Lưu ý: Ngành, nghề kinh doanh bị thay đổi<br>Màu đỏ: bị xóa</div>
<table>
 <tr><th><input type="checkbox"></th><th>Có phải là ngành chính?</th><th>Mã số ngành nghề kinh doanh</th><th>Tên ngành nghề kinh doanh</th></tr>
 <tr><td><input type="checkbox"></td><td><input type="radio" name="c"></td><td>6202</td><td>Tư vấn máy vi tính</td></tr>
 <tr><td><input type="checkbox"></td><td><input type="radio" name="c" checked></td><td>6201</td><td>Lập trình máy vi tính</td></tr>
</table>"""
k2 = server.dkkd_doc_html(that)
assert k2["khoi"] == "Ngành nghề kinh doanh", k2["khoi"]
assert ["Quốc gia", "Việt Nam"] in k2["cap"] and ["Số nhà/đường/phố/tổ/xóm/ấp/thôn", "28 đường số 3 KDC Khang An"] in k2["cap"]
assert ["Số hồ sơ", "OD-0780566/26"] in k2["cap"]
T = "Danh sách ngành nghề kinh doanh"
for c in ([f"{T} #1 - Mã số ngành nghề kinh doanh", "6202"], [f"{T} #1 - Tên ngành nghề kinh doanh", "Tư vấn máy vi tính"],
          [f"{T} #2 - Có phải là ngành chính?", "Có"], [f"{T} #2 - Mã số ngành nghề kinh doanh", "6201"]):
    assert c in k2["cap"], (c, k2["cap"])
assert not any(x[0].startswith(f"{T} #1 - Có phải") for x in k2["cap"])          # radio không chọn -> bỏ
assert not any("6202" == x[0] for x in k2["cap"])                                 # dòng bảng không bị đọc thành cặp
print("PASS 1b: trang thật — ô chọn Địa chỉ (bỏ biểu tượng), bảng Ngành nghề từng dòng, tên khối từ 'Trang chủ > ...'.")

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

# 3b) gom theo "Số hồ sơ" (trang thật không có tham số h) + bỏ phần "Thông tin về hồ sơ" lặp lại ở mỗi khối
dc = {"url": U + "DW_REORGANIZATIONEdit.aspx", "khoi": "Địa chỉ",
      "cap": [["Số hồ sơ", "OD-0780566/26"], ["Quốc gia", "Việt Nam"]]}
wb2 = openpyxl.load_workbook(io.BytesIO(server.dkkd_xuat_excel([dc, k2])))
ct2 = [[c.value for c in r] for r in wb2["Chi tiết"].iter_rows(min_row=2)]
assert {r[0] for r in ct2} == {"OD-0780566/26"}
assert sum(1 for r in ct2 if r[2] == "Số hồ sơ") == 1 and sum(1 for r in ct2 if r[2] == "Quốc gia") == 1
assert len(list(wb2["Tổng hợp"].iter_rows())) == 2
print("PASS 3b: gom theo Số hồ sơ, không lặp lại phần thông tin chung.")

# 4) bookmarklet: javascript: hợp lệ, chứa đúng đoạn đọc trang, chỉ copy vào clipboard (không gửi mạng)
bm = server.dkkd_bookmarklet()
assert bm.startswith("javascript:") and " " not in bm
than = urllib.parse.unquote(bm[len("javascript:"):])
assert "navigator.clipboard" in than and "querySelectorAll('tr')" in than
assert "contentDocument" in than and "chan_doan" in than    # đọc cả khung con (iframe) cùng nguồn + báo chẩn đoán
assert "// " not in than, "mã bookmark nằm trên 1 dòng: dòng chú thích '//' sẽ nuốt mất phần mã phía sau"
# tự đọc mọi khối trong menu "KHỐI DỮ LIỆU" (dừng ở "VĂN BẢN ĐÍNH KÈM") CHỈ bằng GET trong phiên của người dùng
assert "khối dữ liệu" in than and "văn bản đính kèm" in than and "cacTrang(document)" in than and "chan_doan_menu" in than and "credentials: 'same-origin'" in than
assert "method" not in than and "POST" not in than and "XMLHttpRequest" not in than
assert ".submit(" not in than and ".click()" not in than and "__doPostBack(" not in than
assert "javascript:" in than and "cam(t)" in than                       # bỏ link javascript:/postback và link xoá/nộp/gửi...
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
