import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: đúng ca thật người dùng báo cáo (công ty TNHH THƯƠNG MẠI
PHẨM LỢI, 5/9/2026, kèm ảnh chụp MISA "Vật tư hàng hóa") — "kiểm tra lại
phần mềm tự tạo mã hàng mặc dù tên hàng giống. ví dụ MH1084-0 là mã đã có
nhưng phần mềm không lấy và tự tạo mã MH1084".

Đúng hiện trạng MISA: CÙNG 1 tên "Nekko cá ngừ thanh cua kèm nước sốt 70g
(gói)" có 2 mã KHÁC NHAU — "MH1084" (Tính chất "Thành phẩm" — hàng công ty
TỰ SẢN XUẤT/đóng gói, KHÔNG phải hàng đi MUA) và "MH1084-0" (Tính chất "Vật
tư, hàng hóa" — ĐÚNG loại dùng cho Mua hàng, xem _misa_ghi_hang_hoa luôn
tạo InventoryItemType=1). _misa_dong_bo_danh_muc_tu_misa (đồng bộ mã có sẵn
trong MISA vào bản đồ tên->mã của phần mềm, _gen_danh_muc dùng bản đồ này
để gán "Mã hàng" cho Bảng kê Đầu vào) TRƯỚC ĐÂY chỉ giữ "mã XUẤT HIỆN TRƯỚC
trong kết quả SQL" (SELECT InventoryItem KHÔNG có ORDER BY -> thứ tự trả về
của SQL Server KHÔNG đảm bảo) — nếu tình cờ "MH1084" (Thành phẩm) trả về
trước "MH1084-0" (Vật tư hàng hóa), bản đồ học nhầm "MH1084" -> mọi hóa đơn
MUA sau này bị gán/tự tạo nhầm mã "Thành phẩm" thay vì đúng "Vật tư hàng
hóa" có sẵn.

Fix: khi CÙNG 1 tên (Ký tự) có NHIỀU mã KHÁC tính chất, ưu tiên GIỮ/ĐỔI
SANG mã InventoryItemType=1 ("Vật tư, hàng hóa") — bất kể thứ tự SQL trả
về."""
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
    def __init__(self, thu_tu):
        self._thu_tu = thu_tu   # "thanh_pham_truoc" hoặc "vthh_truoc"

    def execute(self, sql, params=()):
        self.last_sql = sql
        return self

    def fetchall(self):
        if "FROM Unit" in self.last_sql:
            return [("U1", "Thùng")]
        if "FROM InventoryItem" in self.last_sql:
            vthh = ("MH1084-0", "Nekko cá ngừ thanh cua kèm nước sốt 70g (gói)", "U1", 1)
            tp = ("MH1084", "Nekko cá ngừ thanh cua kèm nước sốt 70g (gói)", "U1", 3)
            return [tp, vthh] if self._thu_tu == "thanh_pham_truoc" else [vthh, tp]
        return []


class FakeConn:
    def __init__(self, cur):
        self._cur = cur

    def cursor(self):
        return self._cur

    def close(self):
        pass


orig_db, orig_data_dir, orig_connect = server.db, server.DATA_DIR, server._misa_sql_connect
server.db = db_factory
server.DATA_DIR = _data_dir
try:
    for thu_tu in ("thanh_pham_truoc", "vthh_truoc"):
        conn = db_factory()
        conn.execute("DROP TABLE IF EXISTS companies")
        conn.execute("""CREATE TABLE companies (id INTEGER PRIMARY KEY, mst TEXT,
            save_dir TEXT, data_dir TEXT)""")
        conn.execute("INSERT INTO companies VALUES (1,'0317009837','','')")
        conn.commit()
        conn.close()

        cur = FakeCursor(thu_tu)
        server._misa_sql_connect = lambda cid, database=None, _c=cur: FakeConn(_c)
        kq = server._misa_dong_bo_danh_muc_tu_misa(1, "TESTDB", "hh")
        print(f"[{thu_tu}] Kết quả đồng bộ:", kq)
        data = server._doc_du_lieu_cty(1)
        ky_tu = server._dm_ky_tu("Nekko cá ngừ thanh cua kèm nước sốt 70g (gói)", "Thùng")
        ma_hoc = data["dm_hh"]["map"].get(ky_tu)
        assert ma_hoc == "MH1084-0", (
            f"[{thu_tu}] Dù thứ tự SQL trả về thế nào, bản đồ PHẢI học đúng mã 'MH1084-0' (Tính chất "
            f"'Vật tư, hàng hóa' — ĐÚNG loại dùng cho Mua hàng), KHÔNG được lấy nhầm 'MH1084' (Tính chất "
            f"'Thành phẩm' — hàng tự sản xuất, không phải hàng mua) — được {ma_hoc}")
        print(f"PASS [{thu_tu}]: đồng bộ ưu tiên đúng mã 'MH1084-0' (Vật tư hàng hóa), không lấy nhầm "
              f"'MH1084' (Thành phẩm) dù thứ tự SQL trả về khác nhau.")

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
