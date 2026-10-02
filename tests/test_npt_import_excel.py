import os, sys, io, asyncio, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server, openpyxl
from fastapi import HTTPException

# Import Excel Người Phụ Thuộc: tự dò dòng tiêu đề, ghép cột theo từ khóa, chuẩn hóa ngày sinh dd/mm/yyyy và Từ/Đến tháng mm/yyyy, bỏ dòng thiếu họ tên NPT.
grid = [["DANH SÁCH NGƯỜI PHỤ THUỘC"], [],
        ["STT", "Mã NV", "Họ và tên người lao động", "Họ và tên người phụ thuộc", "Ngày sinh", "CCCD/Số định danh", "Quan hệ", "Từ tháng", "Đến tháng"],
        [1, "2", "Trần Minh Hùng", "Trần Bảo An", datetime.datetime(2015, 3, 2), "079 215 000 111", "Con", datetime.datetime(2025, 1, 1), None],
        [2, None, "Nguyễn Giang Nam", "Nguyễn Thị Lan", "05/06/1960", None, "Cha/mẹ", "1/2025", "12-2025"],
        [3, "9", "Phạm Ngọc Khánh", None, None, None, None, None, None]]
rows, cb = server._npt_doc_excel(grid)
assert len(rows) == 2 and any("bỏ qua" in c for c in cb), (rows, cb)
assert rows[0] == ["", "2", "Trần Minh Hùng", "Trần Bảo An", "02/03/2015", "079215000111", "Con", "01/2025", ""], rows[0]
assert rows[1] == ["", "", "Nguyễn Giang Nam", "Nguyễn Thị Lan", "05/06/1960", "", "Cha/mẹ", "01/2025", "12/2025"], rows[1]
# tiêu đề khác tên / không có Mã NV
g2 = [["Tên nhân viên", "Tên người phụ thuộc", "Ngày sinh", "Mã số thuế", "Quan hệ"], ["A", "B", None, "0123", "Con"]]
r2, c2 = server._npt_doc_excel([["Họ tên nhân viên", "Họ tên người phụ thuộc", "Quan hệ"], ["A", "B", "Con"]])
assert r2 == [["", "", "A", "B", "", "", "Con", "", ""]] and not c2
r3, c3 = server._npt_doc_excel([["Họ tên người phụ thuộc", "Quan hệ"], ["B", "Con"]])
assert r3 == [["", "", "", "B", "", "", "Con", "", ""]] and any("Mã NV" in c for c in c3)
# không có cột người phụ thuộc -> báo lỗi rõ
try:
    server._npt_doc_excel([["Mã NV", "Họ tên"], ["1", "A"]]); raise SystemExit("phải lỗi")
except HTTPException as e:
    assert e.status_code == 400 and "người phụ thuộc" in e.detail
# API
wb = openpyxl.Workbook(); ws = wb.active
for r in grid:
    ws.append(r)
b = io.BytesIO(); wb.save(b)
class Up:
    filename = "npt.xlsx"
    async def read(self): return b.getvalue()
class Form:
    def getlist(self, k): return [Up()] if k == "files" else []
    def get(self, k): return None
class Req:
    async def form(self): return Form()
kq = asyncio.run(server.nhap_lieu_import_npt(1, Req()))
assert kq["header"] == server._NPT_HEADERS_IMPORT and len(kq["rows"]) == 2 and kq["rows"][0][4] == "02/03/2015" and kq["loi"]
print("PASS: import Excel Người Phụ Thuộc (tự dò tiêu đề, chuẩn hóa ngày/tháng, bỏ dòng thiếu tên, API).")
print("\nALL DONE")
