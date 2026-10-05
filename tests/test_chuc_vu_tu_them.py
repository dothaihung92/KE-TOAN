import os, sys, asyncio, sqlite3
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server
from fastapi import HTTPException

# Danh Sách NV: nút ＋ ở cột Chức vụ — người dùng tự thêm chức vụ, lưu theo công ty, không trùng chức danh thang bảng lương; xoá được chức vụ tự thêm.
conn = sqlite3.connect(":memory:", check_same_thread=False); conn.row_factory = sqlite3.Row
class KhongDong:
    def __init__(self, c): self.c = c
    def execute(self, *a): return self.c.execute(*a)
    def commit(self): self.c.commit()
    def close(self): pass
server.db = lambda: KhongDong(conn)
server._vb_doc_thang_luong = lambda cid, nam: ({}, None)
class Req:
    def __init__(self, b): self.b = b
    async def json(self): return self.b
them = lambda cid, ten: asyncio.run(server.van_ban_them_chuc_danh(cid, Req({"ten": ten, "nam": 2026})))

goc = server.van_ban_chuc_danh(7, 2026)
assert "Bảo vệ" in goc["chuc_danh"] and goc["tu_them"] == []
r = them(7, "  Tổ   trưởng bảo vệ ")
assert r["ten"] == "Tổ trưởng bảo vệ" and not r["da_co"] and r["chuc_danh"][-1] == "Tổ trưởng bảo vệ"
r = them(7, "Thủ kho"); assert r["chuc_danh"][-2:] == ["Tổ trưởng bảo vệ", "Thủ kho"], "giữ thứ tự thêm"
r = them(7, "tổ trưởng bảo vệ"); assert r["da_co"] and r["ten"] == "Tổ trưởng bảo vệ" and r["chuc_danh"].count("Tổ trưởng bảo vệ") == 1, "không trùng (hoa/thường)"
r = them(7, "BẢO VỆ"); assert r["da_co"] and r["ten"] == "Bảo vệ", "đã có trong thang bảng lương"
assert server.van_ban_chuc_danh(7, 2026)["tu_them"] == ["Tổ trưởng bảo vệ", "Thủ kho"]
assert server.van_ban_chuc_danh(8, 2026)["tu_them"] == [], "riêng từng công ty"
for xau in ("", "   ", "a|b", "x" * 61):
    try:
        them(7, xau); raise SystemExit("phải lỗi: " + repr(xau))
    except HTTPException as e:
        assert e.status_code == 400
server.van_ban_xoa_chuc_danh(7, "Thủ kho")
assert server.van_ban_chuc_danh(7, 2026)["tu_them"] == ["Tổ trưởng bảo vệ"] and "Thủ kho" not in server.van_ban_chuc_danh(7, 2026)["chuc_danh"]
try:
    server.van_ban_xoa_chuc_danh(7, "Bảo vệ"); raise SystemExit("không được xoá chức danh thang bảng lương")
except HTTPException as e:
    assert e.status_code == 404
print("PASS: chức vụ tự thêm")
