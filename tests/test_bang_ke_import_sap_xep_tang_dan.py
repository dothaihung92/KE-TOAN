import os, sys, datetime, subprocess, shutil, re, json
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Import Bảng kê Đầu vào/Đầu ra: sắp xếp TĂNG DẦN theo Ngày lập, Ký hiệu HĐ, Số hóa đơn (so theo SỐ). File gốc đang xếp GIẢM dần.
H_OUT = ["STT", "Ký hiệu mẫu", "Ký hiệu HĐ", "Số hóa đơn", "Ngày lập", "Tên người mua", "MST người mua", "Mặt hàng", "Doanh số bán chưa thuế", "Thuế GTGT"]
R_OUT = [[1, "1", "C26MCF", "00000206", "15/10/2026", "A", "KL", "x", 100, 8],
         [2, "1", "C26MCF", "00000205", "15/10/2026", "B", "KL", "x", 100, 8],
         [3, "1", "C26TCF", "00000059", "13/10/2026", "C", "0300000001", "x", 100, 8],
         [4, "1", "C26MCF", "00000202", "09/10/2026", "D", "KL", "x", 100, 8],
         [5, "1", "C26MCF", "00000200", datetime.datetime(2026, 9, 30), "E", "KL", "x", 100, 8],
         [6, "1", "C26MCF", "00000010", "2026-10-09", "F", "KL", "x", 100, 8],
         [7, "1", "C26MCF", "000009", "09/10/2026", "G", "KL", "x", 100, 8]]
rows, ok = server._sap_xep_bang_ke_tang_dan(H_OUT, [r[:] for r in R_OUT])
assert ok
assert [r[5] for r in rows] == ["E", "G", "F", "D", "C", "B", "A"], [r[5] for r in rows]      # 30/09; 09/10: số 9 < 10 < 202; 13/10; 15/10: 205 < 206
assert [r[0] for r in rows] == [1, 2, 3, 4, 5, 6, 7], "Đầu ra: STT đánh lại theo thứ tự mới"
print("PASS 1: Bảng kê Đầu ra xếp tăng dần theo ngày rồi ký hiệu rồi SỐ hóa đơn (9 < 10 < 202), STT đánh lại; ngày dạng chuỗi/datetime/ISO đều đọc được.")

H_IN = ["Ký hiệu", "Số HĐ", "Ngày", "Người bán", "MST bán", "STT", "Mã vt", "Tên hàng hóa/dịch vụ", "Thành tiền"]
R_IN = [["C26TA", "20", "05/10/2026", "X", "1", 1, "a", "hàng 1", 10], ["C26TA", "20", "05/10/2026", "X", "1", 2, "b", "hàng 2", 20],
        ["C26TA", "9", "05/10/2026", "Y", "2", 1, "c", "hàng 3", 30], ["C26TA", "3", "01/10/2026", "Z", "3", 1, "d", "hàng 4", 40]]
rows_in, ok = server._sap_xep_bang_ke_tang_dan(H_IN, [r[:] for r in R_IN])
assert [(r[1], r[5]) for r in rows_in] == [("3", 1), ("9", 1), ("20", 1), ("20", 2)], rows_in           # các dòng cùng hóa đơn giữ thứ tự; STT dòng KHÔNG đánh lại
print("PASS 2: Bảng kê Đầu vào (dòng chi tiết): xếp theo hóa đơn, các dòng cùng hóa đơn giữ nguyên thứ tự và STT dòng.")

# không đủ cột / rỗng -> giữ nguyên
r0 = [[1, 2], [3, 4]]
assert server._sap_xep_bang_ke_tang_dan(["a", "b"], r0) == (r0, False) and server._sap_xep_bang_ke_tang_dan(H_OUT, []) == ([], False)
# dòng không có ngày xếp cuối; ổn định
rr, _ = server._sap_xep_bang_ke_tang_dan(["Ký hiệu HĐ", "Số hóa đơn", "Ngày lập"], [["K", "5", ""], ["K", "2", "01/01/2026"], ["K", "1", "01/01/2026"]])
assert [r[1] for r in rr] == ["1", "2", "5"]
print("PASS 3: thiếu cột -> giữ nguyên; dòng không có ngày xếp cuối.")

src = open(os.path.join(_REPO_ROOT, "server.py"), encoding="utf-8").read()
a = src[src.index("async def nhap_lieu_import("):src.index("async def nhap_lieu_import_bang_ke(")]
assert "_sap_xep_bang_ke_tang_dan(header_in, rows_in)" in a and "_sap_xep_bang_ke_tang_dan(header_out, rows_out)" in a
assert a.index("_sap_xep_bang_ke_tang_dan(header_in") < a.index("_gan_mst_theo_ten_doi_tuong_rows(header_out")
b = src[src.index("async def nhap_lieu_import_bang_ke("):src.index("NV_HEADERS = [")]
assert "_sap_xep_bang_ke_tang_dan(header, rows)" in b
print("PASS 4: cả 'Import & tách dữ liệu' (gộp nhiều file) lẫn 'Import' vào từng bảng kê đều sắp xếp tăng dần.")

# phía giao diện: sau khi nối dòng mới vào bảng đang xem, sắp xếp lại CẢ bảng; bảng có công thức thì không sắp xếp
html = open(os.path.join(_REPO_ROOT, "static", "index.html"), encoding="utf-8").read()
m = re.search(r"function nlSapXepTangDan\(\)\{.*?\n\}\n", html, re.S)
assert m and "const kqSapXep=nlSapXepTangDan();" in html
node = shutil.which("node")
if node:
    R_JS = [r if not isinstance(r[4], datetime.datetime) else r[:4] + ["30/09/2026"] + r[5:] for r in R_OUT[:6]]
    js = """
let nlHeader=%s, nlRows=%s, nlFormulas={};
%s
const r1=nlSapXepTangDan();
const kq1=nlRows.map(r=>r[5]);
nlRows=%s; nlFormulas={'0_8':'=K5/J5'}; const r2=nlSapXepTangDan(); const kq2=nlRows.map(r=>r[5]);
console.log(JSON.stringify([r1,kq1,r2,kq2]));""" % (json.dumps(H_OUT[1:]), json.dumps([r[1:] for r in R_JS]), m.group(0), json.dumps([r[1:] for r in R_JS]))
    # bỏ cột STT cho khớp giao diện (Đầu ra không hiện STT): cột Tên người mua nằm ở chỉ số 4
    js = js.replace("r=>r[5]", "r=>r[4]")
    out = json.loads(subprocess.run([node, "-e", js], capture_output=True, text=True, check=True).stdout)
    assert out[0] is True and out[1] == ["E", "F", "D", "C", "B", "A"], out
    assert out[2] == "cong_thuc" and out[3] == ["A", "B", "C", "D", "E", "F"], out
    print("PASS 5: giao diện sắp xếp cả bảng tăng dần sau import; bảng có công thức thì giữ nguyên thứ tự.")
else:
    print("SKIP 5: không có node")
