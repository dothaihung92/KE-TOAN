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
def par(kk):
    return [c[:2] for c in kk["cap"]]


k = server.dkkd_doc_html(html)
assert k["url"].endswith("DW_DOCUMENTEdit.aspx?h=720") and k["khoi"] == "Thông tin chung"
assert par(k) == [["Tên doanh nghiệp", "CÔNG TY TNHH ABC"], ["Mã số DN", "0316267842"], ["Ngày cấp", "01/02/2020"],
                    ["Loại hình", "TNHH 1TV"], ["Vốn điều lệ", "1.000.000.000"], ["Ghi chú", "abc"],
                    ["Người đại diện", "Nguyễn Văn A"]], k["cap"]
assert [c[2] for c in k["cap"]][:5] == ["Thông tin chung"] * 5      # tiêu đề mục đứng trước bảng
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
assert ["Quốc gia", "Việt Nam"] in par(k2) and ["Số nhà/đường/phố/tổ/xóm/ấp/thôn", "28 đường số 3 KDC Khang An"] in par(k2)
assert ["Số hồ sơ", "OD-0780566/26"] in par(k2)
T = "Danh sách ngành nghề kinh doanh"
for c in ([f"{T} #1 - Mã số ngành nghề kinh doanh", "6202"], [f"{T} #1 - Tên ngành nghề kinh doanh", "Tư vấn máy vi tính"],
          [f"{T} #2 - Có phải là ngành chính?", "Có"], [f"{T} #2 - Mã số ngành nghề kinh doanh", "6201"]):
    assert c in par(k2), (c, k2["cap"])
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
assert ct[0] == ["Hồ sơ", "Khối", "Mục", "Trường", "Giá trị", "Link"] and len(ct) == 1 + 7 + 1 + 1
th = [[c.value for c in r] for r in wb["Tổng hợp"].iter_rows()]
assert th[0][0] == "Hồ sơ" and "Thông tin chung - Tên doanh nghiệp" in th[0] and "Địa chỉ - Địa chỉ trụ sở" in th[0]
assert [r[0] for r in th[1:]] == ["h=720", "h=800"]
assert th[1][th[0].index("Địa chỉ - Địa chỉ trụ sở")] == "1 Lê Lợi" and th[2][th[0].index("Thông tin chung - Mã số DN")] == "0300000001"
try:
    server.dkkd_xuat_excel_api({"khoi": []})
    raise AssertionError("phải báo lỗi")
except server.HTTPException as e:
    assert e.status_code == 400
print("PASS 3: gom các khối theo mã hồ sơ, xuất Chi tiết + Tổng hợp.")

# 3b) phần "Thông tin về hồ sơ" lặp ở MỌI khối chỉ ghi 1 lần; field trùng chữ giữa các khối KHÁC NHAU thì giữ nguyên
HS = [["Số hồ sơ", "OD-0780566/26"], ["Trạng thái hồ sơ", "Đã gửi đi"]]
cs = {"url": U + "Owner.aspx", "khoi": "Thông tin về chủ sở hữu", "cap": HS + [["Họ và tên", "NGUYỄN VĂN A"], ["Số giấy tờ", "079"]]}
dd = {"url": U + "Rep.aspx", "khoi": "Người đại diện theo pháp luật", "cap": HS + [["Họ và tên", "NGUYỄN VĂN A"], ["Số giấy tờ", "079"]]}
dc = {"url": U + "Addr.aspx", "khoi": "Địa chỉ", "cap": HS + [["Quốc gia", "Việt Nam"]]}
wb2 = openpyxl.load_workbook(io.BytesIO(server.dkkd_xuat_excel([dc, cs, dd])))
ct2 = [[c.value for c in r] for r in wb2["Chi tiết"].iter_rows(min_row=2)]
assert {r[0] for r in ct2} == {"OD-0780566/26"}
assert sum(1 for r in ct2 if r[3] == "Số hồ sơ") == 1 and [r[1] for r in ct2 if r[3] == "Số hồ sơ"] == ["Thông tin về hồ sơ"]
assert [(r[1], r[4]) for r in ct2 if r[3] == "Họ và tên"] == [("Thông tin về chủ sở hữu", "NGUYỄN VĂN A"),
                                                              ("Người đại diện theo pháp luật", "NGUYỄN VĂN A")]
th2 = [[c.value for c in r] for r in wb2["Tổng hợp"].iter_rows()]
assert len(th2) == 2 and th2[0].count("Thông tin về chủ sở hữu - Họ và tên") == 1 and "Người đại diện theo pháp luật - Họ và tên" in th2[0]
print("PASS 3b: thông tin chung chỉ ghi 1 lần; họ tên trùng giữa chủ sở hữu và người đại diện vẫn giữ ở cả 2 khối.")

# 4) bookmarklet: javascript: hợp lệ, chứa đúng đoạn đọc trang, chỉ copy vào clipboard (không gửi mạng)
bm = server.dkkd_bookmarklet()
assert bm.startswith("javascript:") and " " not in bm
than = urllib.parse.unquote(bm[len("javascript:"):])
assert "navigator.clipboard" in than and "querySelectorAll('tr')" in than
assert "contentDocument" in than and "chan_doan" in than    # đọc cả khung con (iframe) cùng nguồn + báo chẩn đoán
# mở khối nút bấm như điều hướng thật (target của form = khung ẩn), kiểm tra trang trả về ĐÚNG khối, dự phòng POST
# cổng chặn nhúng khung (X-Frame-Options) -> mở khối trong 1 CỬA SỔ PHỤ (mở ngay lúc bấm nút), bấm đúng link của mục menu
assert "it.a.click()" in than and "fm.target = '__gpkdCuaSo'" in than and "window.open('about:blank', '__gpkdCuaSo'" in than
# tên khối trên trang có thể khác tên menu ("Thông tin vốn" / "Thông tin về vốn"): chỉ loại trang tổng / trang trùng; trang DANH SÁCH thì
# bấm "Xem" từng dòng để lấy chi tiết (mở lại danh sách rồi bấm dòng kế tiếp)
assert "/^(xem|sửa đổi|sửa)$/i.test(sachT(a.textContent))" in than and "laTrangTong(r)" in than and "dsXem(" in than and "xem chi tiết dòng" in than and "tenDongXem(" in than
assert "khopTen" not in than
# tên mục (tiêu đề/ dòng 1 ô trước bảng) + ô giới tính dạng chữ đậm (không phải <input>)
assert "chonTrongNhom(" in than and "mucHienTai" in than and "mucCua(" in than
assert "// " not in than, "mã bookmark nằm trên 1 dòng: dòng chú thích '//' sẽ nuốt mất phần mã phía sau"
# tự đọc mọi khối trong menu "KHỐI DỮ LIỆU" (dừng ở "VĂN BẢN ĐÍNH KÈM") CHỈ bằng GET trong phiên của người dùng
assert "khối dữ liệu" in than and "văn bản đính kèm" in than and "cacTrang(document)" in than and "chan_doan_menu" in than and "credentials: 'same-origin'" in than
assert "XMLHttpRequest" not in than and than.count("method: 'POST'") == 1
assert ".submit(" not in than and than.count(".click()") == 3 and "it.a.click()" in than and "lien.click()" in than
# chỉ bấm: link của mục menu KHỐI DỮ LIỆU và link "Xem" (chữ đúng là "xem") trong các dòng danh sách
# menu dạng nút bấm (postback ASP.NET): CHỈ gọi __doPostBack của đúng mục trong menu KHỐI DỮ LIỆU (đã lọc chữ xoá/nộp/gửi...),
# trong KHUNG ẨN; không tự gọi postback nào khác
# cách chính: POST form ASP.NET của chính trang (đúng lệnh mục menu, phiên người dùng); dự phòng: khung ẩn. Lỗi ghi vào dữ liệu.
assert "method: 'POST'" in than and "duLieuForm(it.doc, it.nut, it.doi)" in than
assert than.count("__doPostBack(") == 0 and "win.__doPostBack(" not in than
assert "chanDoanMenu.loi = loi" in than and 'name="__VIEWSTATE"' in than
assert "if (!cam(t) && !daCo['pb:' + t])" in than and "\"__gpkdHop\"" not in than
assert "javascript:" in than and "cam(t)" in than                       # bỏ link javascript:/postback và link xoá/nộp/gửi...
print("PASS 4: mã bookmark chỉ đọc trang và copy, không gửi/bấm gì.")

# 5) giao diện: bỏ TMĐT + bỏ Chrome tự động; có 2 cách nhập
html_ui = open(os.path.join(_REPO_ROOT, "static", "index.html"), encoding="utf-8").read()
src = open(os.path.join(_REPO_ROOT, "server.py"), encoding="utf-8").read()
assert "moTmdt" not in html_ui and "/api/tmdt/" not in src
assert 'onclick="moGpkd()"' in html_ui and "/api/dkkd/doc-file" in html_ui and "gpkdThemDan" in html_ui
assert "KHÔNG dán mã vào thanh địa chỉ" in html_ui and "Thêm trang..." in html_ui   # Chrome bỏ 'javascript:' khi dán vào thanh địa chỉ
assert "/api/dkkd/mo-trinh-duyet" not in src and "chrome_dkkd" not in src
# 6) màn hình xem trong phần mềm: menu khối, thông tin hồ sơ, mục, bảng danh sách có màu dòng
for kw in ("gpkdVeXem", "gpkdHtmlKhoi", "KHỐI DỮ LIỆU", "Thông tin về hồ sơ", "gpkdBang", "GPKD_THU_TU"):
    assert kw in html_ui, kw
# 7) trường cùng tên ở 2 mục khác nhau (2 địa chỉ) không bị lẫn khi xuất Excel: giữ cả 2 và thêm (2) nếu cùng mục
m1 = {"url": U + "Owner.aspx", "khoi": "Chủ sở hữu", "cap": [["Số nhà", "618", "Địa chỉ thường trú"], ["Số nhà", "194", "Địa chỉ liên lạc"]]}
wb3 = openpyxl.load_workbook(io.BytesIO(server.dkkd_xuat_excel([m1])))
ct3 = [[c.value for c in r] for r in wb3["Chi tiết"].iter_rows(min_row=2)]
assert [(r[2], r[4]) for r in ct3] == [("Địa chỉ thường trú", "618"), ("Địa chỉ liên lạc", "194")]
th3 = [[c.value for c in r] for r in wb3["Tổng hợp"].iter_rows()]
assert "Chủ sở hữu - Địa chỉ thường trú - Số nhà" in th3[0] and "Chủ sở hữu - Địa chỉ liên lạc - Số nhà" in th3[0]
print("PASS 6-7: màn hình xem + xuất Excel giữ tên mục.")

# 8) màu dòng ngành nghề: đọc cả màu đặt ở ô (không chỉ ở dòng); màn hình xem tô đỏ/xanh đúng màu cổng
assert "[r].concat([].slice.call(r.children))" in server._JS_DKKD_QUET
assert "'đỏ':'#e8372c'" in html_ui and "'xanh lá':'#7dff4f'" in html_ui
print("PASS 8: màu dòng ngành nghề đúng như cổng.")
print("PASS 5: giao diện mới (bookmark + file đã lưu), không còn mở Chrome tự động.")

# Chạy bookmarklet từ trang một KHỐI (vd Địa chỉ): nút menu ở đó chỉ đưa về trang tổng "Khối dữ liệu"
# (DW_DOCUMENTEdit) nên phải mở trang tổng trong cửa sổ phụ rồi bấm mục ở đó (đã kiểm bằng trang giả lập).
_js = server._JS_DKKD_TAT_CA
assert "moTuTrangTong" in _js and "dangODangTong" in _js and "if (!dangODangTong && urlTong) return await moTuTrangTong" in _js
print("PASS: chạy từ trang một khối vẫn mở được các khối khác qua trang tổng.")

# Danh sách (người đại diện, chủ sở hữu hưởng lợi...): bấm "Sửa đổi" (hoặc "Xem") để vào chi tiết, KHÔNG bấm "Xóa";
# không lấy 2 khối "Hình thức đăng ký" và "Khối dữ liệu" (đã kiểm bằng trang giả lập).
assert "(xem|sửa đổi|sửa)" in _js and "xóa|xoá" in _js
assert "chuan('Hình thức đăng ký')" in _js and "!/DW_DOCUMENTEdit" in _js
_h2 = open(os.path.join(_REPO_ROOT, "static", "index.html"), encoding="utf-8").read()
assert "GPKD_BO_QUA=['hình thức đăng ký','khối dữ liệu']" in _h2
print("PASS: bấm Sửa đổi để lấy chi tiết; bỏ qua Hình thức đăng ký và Khối dữ liệu.")

# Khối "Tên doanh nghiệp" (ô nhập trong bảng lồng nhau + câu cảnh báo trùng tên), danh sách thành viên (tên dòng theo cột Tên, không theo số giấy tờ),
# đối chiếu trang với đường dẫn "Danh sách thành viên"... (đã kiểm bằng trang giả lập có bảng lồng nhau)
_js_q = server._JS_DKKD_QUET + _js
assert "2b) Ô nhập nằm trong bảng LỒNG NHAU" in _js_q and "Có\\s+\\d+\\s+doanh nghiệp" in _js_q
assert "tenCot" in _js and "function trangDung" in _js and "cổng mở nhầm trang" in _js and "trang chủ\\s*>" in _js_q
print("PASS: khối Tên doanh nghiệp đọc được; danh sách thành viên đặt tên theo cột Tên; chống mở nhầm trang danh sách.")

# Lỗi "chỉ tô màu các dòng lẻ": CSS chung `tbody tr:nth-child(even) td{background:...}` đè lên nền của <tr> -> phải đặt nền màu ngay trên từng <td> (đã kiểm bằng trình duyệt: 8 dòng đúng đỏ,đỏ,xanh,xanh,xanh,đỏ,trắng,trắng)
assert "tbody tr:nth-child(even) td{background:#faf9f3}" in html_ui
assert 'padding:6px 8px;background:${bg}">${gpkdEsc(r[c]' in html_ui and "const bg=nen[r['Màu dòng']]" in html_ui
# mục "Thông tin về đại diện của tổ chức" trống: không báo lỗi, không lấy nhầm danh sách thành viên
assert "mucTrong" in _js and "đại diện của tổ chức" in _js
print("PASS: tô màu ngành nghề đúng cả dòng chẵn; mục đại diện của tổ chức trống không bị lấy nhầm.")

print("\nALL DONE")
