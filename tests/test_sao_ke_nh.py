import io, os, sys, datetime
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import openpyxl
import sao_ke_nh as s

# File sao kê MÔ PHỎNG theo bố cục thường gặp (chưa có file thật của người dùng): tiêu đề nhiều dòng, tiêu đề 2 tầng, song ngữ, số kiểu 1.234.567 / 1,234,567.
def xlsx(rows):
    wb = openpyxl.Workbook(); ws = wb.active
    for r in rows:
        ws.append(r)
    b = io.BytesIO(); wb.save(b); return b.getvalue()

# 1. Kiểu Vietcombank: tiêu đề 2 tầng (Số tiền -> Ghi nợ | Ghi có), số TK ở đầu, dòng Tổng cuối
vcb = xlsx([["NGÂN HÀNG TMCP NGOẠI THƯƠNG VIỆT NAM"], ["SAO KÊ TÀI KHOẢN / ACCOUNT STATEMENT"], ["Số tài khoản/Account No:", "0071001234567"],
            ["Từ ngày 01/09/2026 đến ngày 30/09/2026"], [],
            ["Ngày giao dịch/Transaction Date", "Số tham chiếu/Reference No", "Số tiền/Amount", None, "Số dư/Balance", "Mô tả/Description"],
            [None, None, "Ghi nợ/Debit", "Ghi có/Credit", None, None],
            ["02/09/2026 10:15:00", "5221.12345", "15,053,400", None, "84,946,600", "THANH TOAN CTY ANH DUNG HD SO 1749"],
            [datetime.datetime(2026, 9, 3, 9, 0), "5221.12346", None, 30240000, 115186600, "NICESTAR THANH TOAN TIEN HANG"],
            ["Tổng số/Total", None, "15,053,400", "30,240,000", None, None]])
r = s.doc_sao_ke(vcb, "SaoKe_VCB.xlsx")
assert r["ngan_hang"] == "vcb" and r["so_tk"] == "0071001234567", r
assert [(g["ngay"], g["tien_ra"], g["tien_vao"]) for g in r["giao_dich"]] == [("02/09/2026", 15053400, 0), ("03/09/2026", 0, 30240000)], r["giao_dich"]
assert r["tsv"].splitlines()[1] == "02/09/2026\tTHANH TOAN CTY ANH DUNG HD SO 1749\t15053400\t", r["tsv"]
assert "5221" not in r["tsv"], "không nối số tham chiếu vào nội dung"
print("PASS 1: kiểu Vietcombank (tiêu đề 2 tầng, song ngữ, dòng Tổng cuối).")

# 2. Kiểu ACB: file .xls thực chất là HTML; Rút ra | Gửi vào; nhiều cột ngày (ưu tiên ngày giao dịch); số 1.234.567
acb = ("<html><body><table><tr><td colspan=6>NGÂN HÀNG TMCP Á CHÂU (ACB)</td></tr><tr><td>Số tài khoản: 123456789</td></tr>"
       "<tr><th>Ngày hiệu lực</th><th>Ngày giao dịch</th><th>Số GD</th><th>Rút ra</th><th>Gửi vào</th><th>Số dư</th><th>Mô tả</th></tr>"
       "<tr><td>06/09/2026</td><td>05/09/2026</td><td>FT1</td><td>1.000.000</td><td></td><td>9.000.000</td><td>PHI DICH VU &amp; VAT</td></tr>"
       "<tr><td>07/09/2026</td><td>07/09/2026</td><td>FT2</td><td></td><td>2.500.000</td><td>11.500.000</td><td>CTY B<br>TRA TIEN HD 22</td></tr>"
       "</table></body></html>").encode("utf-8")
r = s.doc_sao_ke(acb, "statement.xls")
assert r["ngan_hang"] == "acb" and r["so_tk"] == "123456789", r
assert [(g["ngay"], g["noi_dung"], g["tien_ra"], g["tien_vao"]) for g in r["giao_dich"]] == [
    ("05/09/2026", "PHI DICH VU & VAT", 1000000, 0), ("07/09/2026", "CTY B TRA TIEN HD 22", 0, 2500000)], r["giao_dich"]
print("PASS 2: kiểu ACB (.xls dạng HTML, Rút ra/Gửi vào, ưu tiên ngày giao dịch).")

# 3. Kiểu VietinBank: CSV ; Nợ | Có; nội dung xuống dòng sang dòng sau
vtb = ("NGAN HANG TMCP CONG THUONG VIET NAM;;;;\nTai khoan: 1180 0012 3456;;;;\nSTT;Ngày giao dịch;Diễn giải;Nợ;Có;Số dư\n"
       "1;10/09/2026;CHUYEN TIEN LUONG T8;20.000.000;;5.000.000\n;;CHO NHAN VIEN;;;\n2;11/09/2026;LAI TIEN GUI;;1.234;5.001.234\n").encode("utf-8")
r = s.doc_sao_ke(vtb, "efast.csv")
assert r["ngan_hang"] == "vtb" and r["so_tk"] == "118000123456", r
assert r["giao_dich"][0]["noi_dung"] == "CHUYEN TIEN LUONG T8 CHO NHAN VIEN" and r["giao_dich"][1]["tien_vao"] == 1234, r["giao_dich"]
print("PASS 3: kiểu VietinBank (CSV ;, Nợ/Có, nội dung 2 dòng gộp lại).")

# 4. Kiểu Techcombank: 1 cột Số tiền + cột loại D/C; và biến thể số tiền có dấu âm
tcb = xlsx([["TECHCOMBANK"], ["Account number: 19031234567890"], [],
            ["Date", "Description", "Transaction No", "Amount", "D/C", "Balance"],
            ["2026-09-12", "PAY INV 0000123 CONG TY C", "TT1", "3,300,000.00", "D", "1,000,000.00"],
            ["2026-09-13", "CONG TY D CK", "TT2", "4,400,000.00", "C", "5,400,000.00"]])
r = s.doc_sao_ke(tcb, "tcb.xlsx")
assert r["ngan_hang"] == "tcb" and r["so_tk"] == "19031234567890", r
assert [(g["tien_ra"], g["tien_vao"]) for g in r["giao_dich"]] == [(3300000, 0), (0, 4400000)], r["giao_dich"]
tcb2 = xlsx([["Ngày", "Nội dung", "Số tiền", "Số dư"], ["12/09/2026", "A", "-3.300.000", "1"], ["13/09/2026", "B", "4.400.000", "2"]])
r = s.doc_sao_ke(tcb2, "x.xlsx")
assert [(g["tien_ra"], g["tien_vao"]) for g in r["giao_dich"]] == [(3300000, 0), (0, 4400000)], r["giao_dich"]
print("PASS 4: kiểu Techcombank (Amount + D/C) và cột Số tiền có dấu âm.")

# 5. File không phải sao kê -> báo lỗi rõ
try:
    s.doc_sao_ke(xlsx([["Mã hàng", "Tên hàng"], ["A", "B"]]), "kho.xlsx"); raise SystemExit("phải báo lỗi")
except ValueError as e:
    assert "Không nhận ra bảng giao dịch" in str(e)
print("PASS 5: file không phải sao kê -> báo lỗi rõ ràng.")
print("\nALL DONE")
