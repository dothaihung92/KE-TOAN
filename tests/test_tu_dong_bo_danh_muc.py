import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: mỗi lần Sinh Danh mục Hàng hóa/NVL (mở màn Danh mục từ
bảng kê, hoặc "🚀 Import tự động toàn bộ") phải TỰ ĐỘNG đồng bộ mã hàng có
sẵn trong MISA TRƯỚC khi sinh (nếu công ty đã cấu hình kết nối MISA SQL),
KHÔNG cần người dùng tự bấm nút riêng — đúng yêu cầu người dùng: "khi nhập
liệu bảng kê đầu vào phần mềm đã tạo ra danh mục hàng hoá rồi và tôi muốn
lấy theo danh mục hàng hoá đã tạo... những lần import dữ liệu mới sẽ dò
trong danh mục hàng hoá nếu có tên hàng giống mã hàng đã tạo trước đó thì
lấy mã đó còn nếu không có sẽ tạo mã mới" — "danh mục đã tạo" ở đây PHẢI
hiểu là gồm CẢ mã có sẵn trong MISA (kể cả tạo trước khi dùng phần mềm),
không chỉ mã phần mềm tự sinh trước đó."""
import sys, sqlite3, os, tempfile
sys.path.insert(0, _REPO_ROOT)
import server

_db_path = tempfile.mktemp(suffix=".sqlite3")
_data_dir = tempfile.mkdtemp()


def db_factory():
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    return conn


class FakeCursor:
    def execute(self, sql, params=()):
        self.last_sql = sql
        return self

    def fetchall(self):
        if "FROM Unit" in self.last_sql:
            return [("U1", "Cái")]
        if "FROM InventoryItem" in self.last_sql:
            return [("MH613", "Chậu Polystone D35xH45 cm - Matte Black", "U1", 1)]
        return []


class FakeConn:
    def cursor(self):
        return FakeCursor()

    def close(self):
        pass


so_lan_ket_noi = []


def fake_connect_ok(cid, database=None):
    so_lan_ket_noi.append(database)
    return FakeConn()


def fake_connect_loi(cid, database=None):
    raise server.HTTPException(400, "Không kết nối được MISA (mô phỏng lỗi mạng)")


orig_db, orig_data_dir, orig_connect = server.db, server.DATA_DIR, server._misa_sql_connect
server.db = db_factory
server.DATA_DIR = _data_dir

try:
    conn = db_factory()
    conn.execute("""CREATE TABLE companies (id INTEGER PRIMARY KEY, mst TEXT,
        save_dir TEXT, data_dir TEXT)""")
    conn.execute("INSERT INTO companies VALUES (1,'0317743519','','')")
    conn.execute("INSERT INTO companies VALUES (2,'0300000002','','')")
    conn.commit()
    conn.close()

    # ===== Ca 1: công ty 1 CHƯA cấu hình kết nối MISA SQL -> tự đồng bộ
    # phải BỎ QUA LẶNG LẼ, không lỗi, không đụng gì tới dữ liệu. =====
    server._misa_sql_connect = fake_connect_ok
    server._tu_dong_bo_danh_muc_misa(1, "hh")
    data1 = server._doc_du_lieu_cty(1)
    assert not data1.get("dm_hh"), f"Chưa cấu hình MISA SQL thì KHÔNG được tự đồng bộ gì cả — được {data1.get('dm_hh')}"
    assert not so_lan_ket_noi, "Chưa cấu hình MISA SQL thì KHÔNG được thử kết nối"
    print("PASS ca 1: chưa cấu hình MISA SQL -> bỏ qua lặng lẽ, không lỗi.")

    # ===== Ca 2: công ty 2 ĐÃ cấu hình kết nối MISA SQL -> mở màn Danh mục
    # (Sinh Danh mục) phải TỰ ĐỘNG đồng bộ, không cần bấm nút riêng. =====
    data2 = server._doc_du_lieu_cty(2)
    data2["misa_sql"] = {"server": ".\\MISASME2023", "database": "TESTDB", "trusted": True}
    server._ghi_du_lieu_cty(2, data2)
    server._tu_dong_bo_danh_muc_misa(2, "hh")
    data2 = server._doc_du_lieu_cty(2)
    keymap2 = data2.get("dm_hh", {}).get("map", {})
    assert keymap2.get(server._dm_ky_tu("Chậu Polystone D35xH45 cm - Matte Black", "Cái")) == "MH613", (
        f"Đã cấu hình MISA SQL -> Sinh Danh mục phải TỰ ĐỘNG học mã MH613 có sẵn trong MISA, không cần "
        f"bấm nút Đồng bộ riêng — được {keymap2}")
    assert so_lan_ket_noi == ["TESTDB"], f"Phải tự kết nối đúng CSDL đã cấu hình — được {so_lan_ket_noi}"
    print("PASS ca 2: đã cấu hình MISA SQL -> Sinh Danh mục tự động đồng bộ, không cần bấm nút riêng.")

    # ===== Ca 3: loai='tscd' -> KHÔNG áp dụng (dùng cơ chế sinh mã riêng),
    # phải bỏ qua dù đã cấu hình MISA SQL. =====
    so_lan_ket_noi.clear()
    server._tu_dong_bo_danh_muc_misa(2, "tscd")
    assert not so_lan_ket_noi, "loai='tscd' không thuộc phạm vi đồng bộ này, không được thử kết nối MISA"
    print("PASS ca 3: loai='tscd' bỏ qua đúng như thiết kế (chỉ áp dụng hh/nvl).")

    # ===== Ca 4: kết nối MISA lỗi (mạng, sai cấu hình...) -> PHẢI bỏ qua
    # lặng lẽ, KHÔNG được làm hỏng luồng Sinh Danh mục bình thường. =====
    server._misa_sql_connect = fake_connect_loi
    try:
        server._tu_dong_bo_danh_muc_misa(2, "hh")
        loi_khong_lam_vo = True
    except Exception as e:
        loi_khong_lam_vo = False
        print("LỖI:", e)
    assert loi_khong_lam_vo, "Kết nối MISA lỗi lúc tự đồng bộ KHÔNG được làm vỡ luồng Sinh Danh mục bình thường"
    print("PASS ca 4: kết nối MISA lỗi lúc tự đồng bộ được bỏ qua lặng lẽ, không làm gián đoạn Sinh Danh mục.")

    print("\nTẤT CẢ TEST PASS")
finally:
    server.db = orig_db
    server.DATA_DIR = orig_data_dir
    server._misa_sql_connect = orig_connect
    try:
        os.remove(_db_path)
    except OSError:
        pass
    import shutil
    shutil.rmtree(_data_dir, ignore_errors=True)
