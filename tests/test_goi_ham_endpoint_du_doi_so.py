import ast, os
# Hàm endpoint có tham số bắt buộc kiểu Response/Request (FastAPI tự truyền khi gọi qua HTTP) nếu được GỌI TRỰC TIẾP trong code (vd Tra cứu hóa đơn hàng loạt
# tự kết xuất XML GTGT/TNCN, tạm tính thuế VAT) thì PHẢI truyền đủ đối số — thiếu là lỗi "missing 1 required positional argument: 'response'" và không xuất được XML.
src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py"), encoding="utf-8").read()
t = ast.parse(src)
can = {}
for n in ast.walk(t):
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
        bb = len(n.args.args) - len(n.args.defaults)
        for i, a in enumerate(n.args.args[:bb]):
            if a.annotation is not None and ast.unparse(a.annotation) in ("Response", "Request"):
                can[n.name] = (i, a.arg)
loi = []
for n in ast.walk(t):
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in can:
        i, ten = can[n.func.id]
        if len(n.args) <= i and ten not in [k.arg for k in n.keywords] and not any(isinstance(x, ast.Starred) for x in n.args):
            loi.append(f"dòng {n.lineno}: {n.func.id}() thiếu '{ten}'")
assert not loi, loi
assert {"export_htkk", "export_htkk_tncn", "vat_tam_tinh"} <= set(can)
print("PASS")
