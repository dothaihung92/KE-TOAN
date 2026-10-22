import io, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Ca thật: file ToKhaiHQ7X_QDTQ_….xls (TỜ KHAI XUẤT KHẨU, sheet TKX) bị nhập vào nút "Import tờ khai nhập khẩu" -> báo "0 tờ khai, 1 file lỗi" không rõ lý do.
# Nay: mở được cả .xls (xlrd); nhận ra tờ khai xuất khẩu và báo rõ phải dùng nút Import tờ khai xuất khẩu; số nguyên không thành "123.0".
import xlrd
class Sh:
    def __init__(self, rows): self.rows = rows; self.nrows = len(rows)
    def row_values(self, r): return self.rows[r]
sh = _X = server._XlsSheetNhuOpenpyxl(Sh([["Tờ khai hàng hóa xuất khẩu (thông quan)", ""], ["Số tờ khai", 308754245130.0, 1.5]]))
rows = list(sh.iter_rows(values_only=True))
assert rows[1] == ("Số tờ khai", 308754245130, 1.5) and rows[0][1] is None, rows
print("PASS 1: sheet .xls đọc như openpyxl: số nguyên giữ đúng dạng, ô trống = None.")

class Wb:
    def __init__(self, names, rows): self.sheetnames = names; self._r = rows
    def __getitem__(self, n): return type("S", (), {"iter_rows": lambda s, values_only=True: iter(self._r)})()
assert server._la_to_khai_xuat_khau(Wb(["TKX", "HANG"], []))
assert server._la_to_khai_xuat_khau(Wb(["Sheet1"], [("Tờ khai hàng hóa xuất khẩu (thông quan)",)]))
assert not server._la_to_khai_xuat_khau(Wb(["TKN"], [("Tờ khai hàng hóa nhập khẩu (thông quan)",)]))
assert not server._la_to_khai_xuat_khau("không phải workbook")
print("PASS 2: nhận ra tờ khai xuất khẩu (sheet TKX/tiêu đề), không nhầm tờ khai nhập khẩu.")

f = "/root/.claude/uploads/2b881f0b-f588-5583-b98c-f1a7b9c7cf12/7d11be7b-ToKhaiHQ7X_QDTQ_308754245130.xls"
if os.path.isfile(f):
    wb = server._mo_file_to_khai(open(f, "rb").read())
    assert wb.sheetnames[0] == "TKX" and server._la_to_khai_xuat_khau(wb)
    print("PASS 3: file .xls thật của người dùng được nhận ra là tờ khai xuất khẩu.")
print("ALL DONE")
