import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server
f = server._misa_tk_chi_tiet
class Cur:
    def __init__(self, dem): self.dem = dem
    def execute(self, sql, params=()):
        self.rows = [(a, self.dem[a]) for a in params if a in self.dem]
        return self
    def fetchall(self): return self.rows
tk = {"111", "1111", "131", "331", "334", "3341", "3348", "3383", "3384", "1121", "6427"}
# công ty dùng 3341 nhiều nhất -> 334 phải thành 3341
assert f(Cur({"3341": 120, "3348": 3}), "334", tk) == "3341"
# công ty dùng chủ yếu 3348 -> theo dữ liệu thật của công ty
assert f(Cur({"3341": 1, "3348": 50}), "334", tk) == "3348"
# chưa có dữ liệu sổ cái -> ưu tiên tiểu khoản kết thúc bằng 1
assert f(Cur({}), "334", tk) == "3341"
# TK không có tiểu khoản -> giữ nguyên
for t in ("131", "331", "6427", "1121", "3383"):
    assert f(Cur({}), t, tk) == t, t
# TK có sẵn tiểu khoản 111 -> 1111 (TK cha 111 có 1111)
assert f(Cur({}), "111", tk) == "1111"
# danh mục rỗng/không biết -> giữ nguyên, không lỗi
assert f(Cur({}), "334", set()) == "334"
# lỗi SQL ở bước đếm không làm hỏng
class Loi(Cur):
    def execute(self, *a, **k): raise RuntimeError("x")
assert f(Loi({}), "334", tk) == "3341"
c = {}; f(Cur({"3341": 5}), "334", tk, c); assert c == {"334": "3341"}
sv = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py"), encoding="utf8").read()
assert "_misa_tk_chi_tiet(cur, hach, tk_set, tk_ct_cache)" in sv
print("PASS: TK cha có tiểu khoản (334 -> 3341) chọn theo dữ liệu thật của công ty trên MISA")
