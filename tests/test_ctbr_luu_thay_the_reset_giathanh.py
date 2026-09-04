import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: '💾 Lưu' BÌNH THƯỜNG ở màn Nhập Liệu (nhap_lieu_save,
loai='ctbr') phải THAY THẾ hoàn toàn ctbr (giống 'in'/'out'), KHÔNG gộp —
và phải RESET xk_giathanh để 'Dò mã hàng tự động' lần sau dựng lại TỪ ĐẦU
đúng dữ liệu MỚI, không còn sót dữ liệu kỳ TRƯỚC.

Đúng ca thật người dùng báo cáo (CÔNG TY TNHH ỐC GẠO FAMILY): "tôi đang xử
lý tháng 8 và dữ liệu chỉ có tháng 8 đầu ra thôi sao phần mềm vẫn nhớ tháng
7 vậy hãy chỉnh lại. nếu không import thêm thì chỉ lấy dữ liệu nhập liệu từ
đầu thôi" — ảnh chụp cho thấy bảng Xuất Kho (GIATHANH) vẫn còn nguyên các
dòng Ngày 20/07, 24/07/2026 dù chỉ vừa Import & Lưu bảng kê Đầu ra CHỈ có
dữ liệu tháng 8 (KHÔNG dùng nút '➕ Import thêm dữ liệu').

Ngược lại, nút RIÊNG '➕ Import thêm dữ liệu' (save-ctbr-gop/
_xk_gop_them_ban_hang, xem test_ctbr_gop_nhieu_dot.py) vẫn phải GIỮ NGUYÊN
hành vi tích luỹ như cũ — đây là ca test cho '💾 Lưu' bình thường, không
đụng tới nút đó."""
import sys, sqlite3, os, tempfile, asyncio
sys.path.insert(0, _REPO_ROOT)
import server

_db_path = tempfile.mktemp(suffix=".sqlite3")
_data_dir = tempfile.mkdtemp()


def db_factory():
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    return conn


class FakeRequest:
    def __init__(self, payload):
        self._payload = payload

    async def json(self):
        return self._payload


orig_db, orig_data_dir = server.db, server.DATA_DIR
server.db = db_factory
server.DATA_DIR = _data_dir

CTBR_HEADER = ["Ký hiệu", "Số HĐ", "Ngày", "Tên hàng hóa/dịch vụ", "ĐVT",
               "Số lượng", "Đơn giá", "Thành tiền"]

try:
    conn = db_factory()
    conn.execute("""CREATE TABLE companies (id INTEGER PRIMARY KEY, mst TEXT,
        save_dir TEXT, data_dir TEXT)""")
    conn.execute("INSERT INTO companies VALUES (1,'0317743519','','')")
    conn.commit()
    conn.close()

    # Giả lập trạng thái đã có sẵn: xk_giathanh đã dựng từ ctbr THÁNG 7 (kỳ
    # trước, còn 1 dòng ĐÃ được gán mã tay/qua Import giá thành trước đó).
    data = server._doc_du_lieu_cty(1)
    data["xk_giathanh"] = [
        {"khhdon": "C1", "sohd": "514", "ngay": "20/07/2026", "ten_sp": "Bia Heineken Silver 250x24c Ctn",
         "dvt": "Thùng", "sl": 30, "ma": "HH00006-10", "ten_xk": "Bia Heineken Silver 250x24c Ctn"},
    ]
    server._ghi_du_lieu_cty(1, data)

    rows_t7 = [["C1", "514", "20/07/2026", "Bia Heineken Silver 250x24c Ctn", "Thùng", 30, 331818, 9954545]]
    conn2 = db_factory()
    conn2.execute("""CREATE TABLE IF NOT EXISTS nhap_lieu (
        id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, loai TEXT,
        header_json TEXT, rows_json TEXT, updated_at TEXT,
        UNIQUE(company_id, loai))""")
    import json as _json
    conn2.execute("INSERT INTO nhap_lieu (company_id, loai, header_json, rows_json, updated_at) VALUES (?,?,?,?,?)",
                  (1, "ctbr", _json.dumps(CTBR_HEADER, ensure_ascii=False),
                   _json.dumps(rows_t7, ensure_ascii=False), "2026-07-20T00:00:00"))
    conn2.commit()
    conn2.close()

    # ===== Import & Lưu BÌNH THƯỜNG (nhap_lieu_save, loai='ctbr') với file
    # CHỈ có dữ liệu THÁNG 8 -> phải THAY THẾ hoàn toàn, và reset giathanh. =====
    rows_t8 = [["C2", "556", "26/08/2026", "Bia Tiger Bạc thùng 24 lon x 330ml", "Thùng", 10, 350000, 3500000]]
    req = FakeRequest({"header": CTBR_HEADER, "rows": rows_t8})
    asyncio.run(server.nhap_lieu_save(1, req, loai="ctbr"))

    cur_ctbr = server.nhap_lieu_get(1, "ctbr")
    print("ctbr sau khi Lưu (chỉ tháng 8):", cur_ctbr)
    so_hd_con_lai = {r[1] for r in cur_ctbr["rows"]}
    assert so_hd_con_lai == {"556"}, (
        f"'💾 Lưu' bình thường (KHÔNG dùng 'Import thêm dữ liệu') phải THAY THẾ hoàn toàn ctbr — chỉ còn "
        f"đúng hóa đơn 556 (tháng 8), KHÔNG còn hóa đơn 514 (tháng 7 cũ) — được {so_hd_con_lai}")

    data_sau = server._doc_du_lieu_cty(1)
    giathanh_sau = data_sau.get("xk_giathanh") or []
    print("xk_giathanh sau khi Lưu ctbr mới:", giathanh_sau)
    assert giathanh_sau == [], (
        f"xk_giathanh (bảng Xuất Kho) PHẢI được reset về rỗng khi ctbr bị thay thế bằng dữ liệu kỳ mới, để "
        f"lần 'Dò mã hàng tự động' kế tiếp tự dựng lại TỪ ĐẦU đúng dữ liệu tháng 8 — KHÔNG được còn sót dòng "
        f"'514' (Số HĐ) / '20/07/2026' của tháng 7 cũ — đúng lỗi thật đã báo cáo (ảnh Xuất Kho còn Ngày "
        f"20/07, 24/07/2026 dù chỉ Import dữ liệu tháng 8) — được {giathanh_sau}")
    print("PASS: '💾 Lưu' ctbr thay thế hoàn toàn + reset xk_giathanh, không còn sót dữ liệu kỳ cũ.")

    print("\nTẤT CẢ TEST PASS")
finally:
    server.db = orig_db
    server.DATA_DIR = orig_data_dir
    try:
        os.remove(_db_path)
    except OSError:
        pass
    import shutil
    shutil.rmtree(_data_dir, ignore_errors=True)
