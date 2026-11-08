import os, sys, asyncio, sqlite3, tempfile, io
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server, openpyxl

# 'Cập nhật tồn kho' bằng file GIỮ mã cũ không có trong file -> Tổng giá trị lệch MISA: phản hồi phải báo số mã + giá trị mã cũ.
_p = tempfile.mktemp(); server.DATA_DIR = tempfile.mkdtemp()
def _db():
    c = sqlite3.connect(_p); c.row_factory = sqlite3.Row; return c
server.db = _db
c = _db(); c.execute("CREATE TABLE companies (id INTEGER PRIMARY KEY, mst TEXT, save_dir TEXT, data_dir TEXT)"); c.execute("INSERT INTO companies VALUES (1,'1','','')"); c.commit()
d = server._doc_du_lieu_cty(1)
d["xk_ton"] = [{"ma": "CU1", "ten": "Hàng cũ", "dvt": "Cái", "ton": 5, "gia": 100, "gia_tri": 500}]
server._ghi_du_lieu_cty(1, d)
wb = openpyxl.Workbook(); ws = wb.active
ws.append(["TỔNG HỢP TỒN KHO"]); ws.append(["Q3"])
ws.append([None, "Mã hàng", "Tên hàng", "ĐVT", "Đầu kỳ", None, "Nhập kho", None, "Xuất kho", None, "Cuối kỳ", None])
ws.append([None, None, None, None] + ["Số lượng", "Giá trị"] * 4)
ws.append(["Tên kho : HH (1 )", None, None, None, 0, 0, 2, 2000, 0, 0, 2, 2000])
ws.append([None, "MOI1", "Hàng mới", "Cái", 0, 0, 2, 2000, 0, 0, 2, 2000])
b = io.BytesIO(); wb.save(b)
class Up:
    filename = "t.xlsx"
    async def read(self): return b.getvalue()
class Req:
    async def form(self):
        class F(dict):
            def getlist(s, k): return [Up()]
            def get(s, k, d=None): return None
        return F()
r = asyncio.run(server.xk_cap_nhat_ton(1, Req()))
assert r["so_ma_cu_ngoai_file"] == 1 and r["gt_ma_cu_ngoai_file"] == 500 and r["gt_file"] == 2000 and r["tong"] == 2, r
print("PASS: cập nhật tồn kho từ file báo mã cũ ngoài file + giá trị.")
print("\nALL DONE")
