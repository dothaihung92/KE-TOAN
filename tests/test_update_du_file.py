import ast, os, re, sys
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
# Mọi module .py của phần mềm (ở thư mục gốc) mà server/gpkd... import phải nằm trong danh sách tự cập nhật của update.py
# (lần trước quên gpkd_giai_the.py -> máy người dùng cập nhật xong bị lỗi khi soạn hồ sơ giải thể). Tiện ích Chrome cũng vậy.
up = open(os.path.join(_REPO_ROOT, "update.py"), encoding="utf-8").read()
files = set(re.findall(r'"([^"]+)"', up[up.index("FILES = ["):up.index("]", up.index("FILES = ["))]))
goc = {f[:-3] for f in os.listdir(_REPO_ROOT) if f.endswith(".py") and not f.startswith("test")}
thieu = []
for f in files | {"server.py"}:
    if not f.endswith(".py") or not os.path.isfile(os.path.join(_REPO_ROOT, f)):
        continue
    for n in ast.walk(ast.parse(open(os.path.join(_REPO_ROOT, f), encoding="utf-8").read())):
        ten = [a.name.split(".")[0] for a in n.names] if isinstance(n, ast.Import) else ([n.module.split(".")[0]] if isinstance(n, ast.ImportFrom) and n.module and not n.level else [])
        thieu += [f"{t}.py (import trong {f})" for t in ten if t in goc and f"{t}.py" not in files]
assert not thieu, thieu
ti = "tien_ich_chrome/xuat_don_tmdt"
thieu_ti = [f for f in os.listdir(os.path.join(_REPO_ROOT, ti)) if f.endswith((".js", ".json")) and f"{ti}/{f}" not in files]
assert not thieu_ti, thieu_ti
print("PASS: update.py có đủ các module .py được import và đủ file tiện ích Chrome.")
print("\nALL DONE")
