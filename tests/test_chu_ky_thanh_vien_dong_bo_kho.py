import asyncio, os, sqlite3, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Chữ ký thành viên GPKD đồng bộ với Kho chữ ký (bảng lương/giám đốc/công ty khác): thành viên chưa có chữ ký theo CCCD nhưng trong kho đã có chữ ký
# ĐÃ XÁC NHẬN của người CÙNG HỌ TÊN -> sao chép sang khoá CCCD (nguồn giữ nguyên). Không có / chưa xác nhận -> không làm gì.
conn = sqlite3.connect(":memory:", check_same_thread=False); conn.row_factory = sqlite3.Row
server._ck_dam_bao_bang(conn)
IMG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="


class KhongDong:
    def __init__(self, c): self.c = c
    def execute(self, *a): return self.c.execute(*a)
    def commit(self): self.c.commit()
    def close(self): pass


server.db = lambda: KhongDong(conn)
server._ck_chuan_hoa_anh = lambda a: a
conn.execute("INSERT INTO chu_ky_chung (khoa, ten, anh, xac_nhan, updated_at) VALUES ('ten:pham thanh quyen', 'Phạm Thanh Quyên', ?, 1, '2026-01-01')", (IMG,))
conn.execute("INSERT INTO chu_ky_chung (khoa, ten, anh, xac_nhan, updated_at) VALUES ('ten:le quang chung', 'Lê Quang Chung', ?, 0, '2026-01-01')", (IMG,))
conn.commit()


class Rq:
    def __init__(self, b): self.b = b
    async def json(self): return self.b


def goi(khoa, ten):
    return asyncio.run(server.chu_ky_dong_bo(7, Rq({"khoa": khoa, "ten": ten})))


r = goi("cccd:082186000121", "PHẠM THANH QUYÊN")
assert r["ok"] and r["anh"] == IMG, r
dong = conn.execute("SELECT xac_nhan, anh FROM chu_ky_chung WHERE khoa='cccd:082186000121'").fetchone()
assert dong and dong["xac_nhan"] == 1 and dong["anh"] == IMG
assert conn.execute("SELECT COUNT(*) FROM chu_ky_chung WHERE khoa='ten:pham thanh quyen'").fetchone()[0] == 1      # nguồn giữ nguyên
print("PASS 1: thành viên cùng họ tên với người đã có chữ ký (đã xác nhận) trong kho -> sao chép sang khoá CCCD.")
assert goi("cccd:037081000763", "LÊ QUANG CHUNG") == {"ok": False}          # chữ ký trong kho CHƯA xác nhận đồng ý -> không dùng
assert goi("cccd:000000000001", "NGƯỜI LẠ") == {"ok": False}
assert not conn.execute("SELECT 1 FROM chu_ky_chung WHERE khoa IN ('cccd:037081000763','cccd:000000000001')").fetchone()
print("PASS 2: chữ ký chưa xác nhận đồng ý hoặc người lạ -> không đồng bộ.")
assert goi("cccd:082186000121", "PHẠM THANH QUYÊN")["nguon"] == "đã có"
src = open(os.path.join(os.path.dirname(server.__file__), "static", "index.html"), encoding="utf-8").read()
assert src.count("/dong-bo`") == 2           # thẻ thành viên + bên nhận ủy quyền đều đồng bộ với kho
print("PASS 3: đã có chữ ký theo CCCD thì giữ; giao diện thành viên và bên nhận ủy quyền gọi đồng bộ kho.")
print("ALL DONE")
