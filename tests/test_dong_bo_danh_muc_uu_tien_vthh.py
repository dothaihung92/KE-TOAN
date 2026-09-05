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
về.

Test 2 (da_hoc_sai_tu_truoc): đúng NGUYÊN VĂN phản hồi người dùng SAU round
1 của fix — "vẫn còn hiện và đã thử xoá hết import tự động lại vẫn còn":
công ty này đã CHẠY "Đồng bộ" TỪ TRƯỚC (khi CHƯA có ưu tiên tính chất),
bản đồ (keymap) ĐÃ LỠ học "MH1084" (Thành phẩm) rồi — round 1 chỉ sửa cách
CHỌN mã mới (misa_map) nhưng vòng ghi đè bản đồ CŨ chỉ chịu thay khi mã
đang giữ là mã TỰ SINH placeholder ('HH00000'), KHÔNG áp dụng cho mã ĐÃ LÀ
mã thật (dù sai tính chất) -> đồng bộ lại báo "học 0 mã mới, thay 0 mã",
Sinh Danh mục lại vẫn ra "MH1084" y hệt. Fix thêm: ghi đè cả khi mã đang
giữ là mã thật nhưng SAI tính chất (không phải Vật tư hàng hóa)."""
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

    # ===== Test 2: bản đồ ĐÃ LỠ học "MH1084" (Thành phẩm) TỪ TRƯỚC (lần đồng
    # bộ CŨ, trước khi có ưu tiên tính chất) — đồng bộ LẠI phải TỰ SỬA, không
    # còn báo "học 0 mã mới, thay 0 mã" như phản hồi thật của người dùng. =====
    conn = db_factory()
    conn.execute("DROP TABLE IF EXISTS companies")
    conn.execute("""CREATE TABLE companies (id INTEGER PRIMARY KEY, mst TEXT,
        save_dir TEXT, data_dir TEXT)""")
    conn.execute("INSERT INTO companies VALUES (1,'0317009837','','')")
    conn.commit()
    conn.close()
    ky_tu = server._dm_ky_tu("Nekko cá ngừ thanh cua kèm nước sốt 70g (gói)", "Thùng")
    data = server._doc_du_lieu_cty(1)
    data["dm_hh"] = {"map": {ky_tu: "MH1084"}}   # bản đồ CŨ, đã lỡ học sai
    server._ghi_du_lieu_cty(1, data)

    cur2 = FakeCursor("thanh_pham_truoc")
    server._misa_sql_connect = lambda cid, database=None, _c=cur2: FakeConn(_c)
    kq2 = server._misa_dong_bo_danh_muc_tu_misa(1, "TESTDB", "hh")
    print("[da_hoc_sai_tu_truoc] Kết quả đồng bộ:", kq2)
    assert kq2["so_thay_the"] == 1, (
        f"Bản đồ ĐÃ học sai 'MH1084' (Thành phẩm) từ trước PHẢI được đồng bộ SỬA LẠI thành 'MH1084-0' "
        f"(Vật tư hàng hóa) — KHÔNG được báo 'thay 0 mã' như phản hồi thật của người dùng ('vẫn còn hiện "
        f"và đã thử xoá hết import tự động lại vẫn còn') — được {kq2}")
    data2 = server._doc_du_lieu_cty(1)
    assert data2["dm_hh"]["map"].get(ky_tu) == "MH1084-0", (
        f"Bản đồ sau đồng bộ phải đúng 'MH1084-0' — được {data2['dm_hh']['map'].get(ky_tu)}")
    print("PASS [da_hoc_sai_tu_truoc]: bản đồ đã lỡ học sai mã 'Thành phẩm' từ TRƯỚC round 1 của fix nay "
          "được đồng bộ tự sửa lại đúng, không còn kẹt mãi ở mã sai dù xoá/import lại nhiều lần.")

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
