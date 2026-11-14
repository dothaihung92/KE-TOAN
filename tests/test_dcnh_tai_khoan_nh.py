import json, os, sys, tempfile
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server
from fastapi import HTTPException
# Lấy sao kê tự động chỉ hiện tài khoản NH đã lưu trong thông tin công ty; thêm mới ở Đối Chiếu NH đồng bộ vào đúng chỗ đó (bank_accounts).
server.DATA_DIR = tempfile.mkdtemp(); server.DB_PATH = os.path.join(server.DATA_DIR, "t.db")
try:
    server.init_db()
except Exception:
    pass
c = server.db()
c.execute("INSERT INTO companies (ten, mst, username, password, created_at) VALUES ('A','0313829148','u','p','2026-01-01')"); c.commit()
cid = c.execute("SELECT id FROM companies").fetchone()["id"]; c.close()
assert server.dcnh_tai_khoan_nh("0313829148")["ds"] == []
r = server.dcnh_them_tai_khoan_nh({"mst": "0313829148", "bank": "tcb", "stk": "1903 1234-567", "user": "ib1", "pass": "mk"})
assert r["them_moi"] is True
r = server.dcnh_them_tai_khoan_nh({"mst": "0313-829-148", "bank": "vcb", "stk": "0071001234567"})
d = server.dcnh_tai_khoan_nh("0313829148")["ds"]
assert [(x["bank"], x["stk"], x["user"]) for x in d] == [("tcb", "19031234567", "ib1"), ("vcb", "0071001234567", "")], d
# đồng bộ với hộp "Tài khoản Ngân hàng" ở màn sửa công ty: cùng dữ liệu, mã lưu theo kiểu cũ (techcombank), có mật khẩu
goc = server.get_bank_accounts(cid)["ds"]
assert goc[0] == {"bank": "techcombank", "stk": "19031234567", "user": "ib1", "pass": "mk"}, goc
# thêm trùng: không nhân đôi, mật khẩu để trống thì giữ cũ
r = server.dcnh_them_tai_khoan_nh({"mst": "0313829148", "bank": "techcombank", "stk": "19031234567", "user": "ib2"})
assert r["them_moi"] is False and len(server.get_bank_accounts(cid)["ds"]) == 2
g = server.get_bank_accounts(cid)["ds"][0]; assert g["user"] == "ib2" and g["pass"] == "mk", g
for sai in ({"mst": "0313829148", "bank": "", "stk": "1"}, {"mst": "0313829148", "bank": "acb", "stk": ""}):
    try: server.dcnh_them_tai_khoan_nh(sai); raise SystemExit("phải lỗi")
    except HTTPException as e: assert e.status_code == 400
try: server.dcnh_tai_khoan_nh("0999999999"); raise SystemExit("phải lỗi")
except HTTPException as e: assert e.status_code == 404
# GET không lộ mật khẩu
assert all("pass" not in x for x in server.dcnh_tai_khoan_nh("0313829148")["ds"])
print("PASS: đọc/thêm tài khoản NH theo MST, đồng bộ với thông tin công ty, không nhân đôi, không trả mật khẩu.")
print("\nALL DONE")
