import os, sys, io, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server, openpyxl

# Import Danh Sách Nhân Viên từ Excel: giữ NGUYÊN thứ tự dòng của file và không bỏ sót người đầu tiên (file chỉ có 1 dòng tiêu đề)
def chay(wb):
    b = io.BytesIO(); wb.save(b)
    class Up:
        filename = 'a.xlsx'
        async def read(self): return b.getvalue()
    class Form:
        def getlist(self, k): return [Up()]
        def get(self, k): return None
    class Req:
        async def form(self): return Form()
    r = asyncio.run(server.nhap_lieu_import_nhan_vien(7, Req()))
    return [x[server.NV_HEADERS.index('Họ và tên')] for x in r['rows']], r
H1 = ["STT", "Mã NV", "Họ và tên", "Ngày sinh", "Địa chỉ", "CCCD", "Ngày cấp", "Tháng/Năm vào làm", "Đóng BHXH"]
wb = openpyxl.Workbook(); ws = wb.active; ws.append(H1)
ten = ["Zeta", "Alpha", "Mike", "Beta", "Alpha2", "Hạ", "An"]
for i, t in enumerate(ten, 1):
    ws.append([i, "M%d" % (10 - i), t, "01/01/1990", "dc", "07900000%04d" % i, "01/01/2020", "01/2025", "x"])
ds, r = chay(wb)
assert ds == ten, ds                      # đủ người, đúng thứ tự (kể cả người đầu tiên)
# file có 2 dòng tiêu đề (dòng phụ tên cột con của "Phụ cấp"): vẫn bỏ dòng phụ, không mất người
wb2 = openpyxl.Workbook(); w2 = wb2.active
w2.append(["STT", "Mã NV", "Họ và tên", "Ngày sinh", "Địa chỉ", "CCCD", "Ngày cấp", "Tháng/Năm vào làm", "Đóng BHXH", "Phụ cấp", None])
w2.append([None, None, None, None, None, None, None, None, None, "Tiền cơm", "Xăng xe"])
w2.merge_cells("J1:K1")
for i, t in enumerate(ten[:3], 1):
    w2.append([i, "M%d" % i, t, "01/01/1990", "dc", "07900000%04d" % i, "01/01/2020", "01/2025", "x", 700000, 500000])
ds2, r2 = chay(wb2)
assert ds2 == ten[:3], ds2
assert r2["rows"][0][server.NV_HEADERS.index("PC Tiền cơm")] == 700000 and r2["rows"][0][server.NV_HEADERS.index("PC Xăng xe")] == 500000
print("PASS")
