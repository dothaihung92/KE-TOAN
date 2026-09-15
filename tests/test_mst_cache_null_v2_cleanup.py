import os
import sqlite3
import tempfile
import textwrap

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test cho migration MỘT LẦN thứ 2 trong init_db() dọn dẹp
# mst_status_cache — bug THẬT phát hiện qua log người dùng gửi: xuất Excel
# xong, "CHI TIẾT TỪNG MST" (tính năng chẩn đoán mới thêm) báo TOÀN "không
# rõ lý do" cho đủ cả 8 MST, dù đã có log chẩn đoán chi tiết theo từng MST —
# thời gian chạy chỉ 6.0s cho 234 MST (quá nhanh so với gọi mạng thật) ->
# dấu hiệu rõ ràng là CACHE HIT, không hề thử mạng lại lần nào.
#
# Nguyên nhân gốc: _goi_1_lan_xinvoice() TRƯỚC ĐÂY coi HTTP 200 là "tra
# THÀNH CÔNG" dù trường "status" trả về KHÔNG khớp được tình trạng nào
# (canh_bao=NULL) -> LƯU CACHE kết quả rỗng đó vĩnh viễn (14 ngày), y hệt
# bug cache-khi-thất-bại đã sửa trước đây (migration thứ 1, cờ
# 'mst_cache_null_cleanup_done') nhưng qua đường "200 thành công rỗng" thay
# vì lỗi HTTP -> migration thứ 1 (đã chạy xong TRƯỚC KHI bug này bị phát
# hiện, đã tự đánh dấu xong) KHÔNG dọn được các dòng NÀY (ghi SAU khi
# migration 1 đã chạy) -> cache-hit lần sau trả thẳng {"trang_thai":"",
# "canh_bao":None} không kèm ly_do_loi -> "CHI TIẾT TỪNG MST" phải tự điền
# "không rõ lý do".
#
# Migration thứ 2 (cờ RIÊNG 'mst_cache_null_cleanup_done_v2') dọn NỐT các
# dòng canh_bao=NULL còn sót lại do bug NÀY, và code đã sửa để KHÔNG còn ghi
# thêm dòng nào như vậy nữa — bài test này xác nhận: (A) dọn đúng các dòng
# canh_bao=NULL còn sót dù migration 1 ĐÃ chạy xong từ trước; (B) CHỈ chạy
# ĐÚNG 1 LẦN (không xoá tiếp ở các lần khởi động SAU, tránh xoá luôn dữ liệu
# hợp lệ nào đó trong tương lai).

_MARK_START = "if not conn.execute(\n            \"SELECT 1 FROM app_settings WHERE key='mst_cache_null_cleanup_done'"
_MARK_END_ANCHOR = "# Migration: thêm cột he_thong nếu DB cũ chưa có"
i0_mid = src.index(_MARK_START)
i0 = src.rfind('\n', 0, i0_mid) + 1   # lùi về đầu dòng để giữ đúng thụt lề gốc
i1 = src.index(_MARK_END_ANCHOR, i0)
migration_src = textwrap.dedent(src[i0:i1])
assert "mst_cache_null_cleanup_done_v2" in migration_src, (
    "Không trích xuất được đoạn migration v2 — kiểm tra lại mốc trích xuất trong init_db()")


def _fresh_conn():
    conn = sqlite3.connect(_tmp_db.name, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS app_settings (
        key TEXT PRIMARY KEY, value TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS mst_status_cache (
        mst TEXT PRIMARY KEY, trang_thai_goc TEXT, canh_bao INTEGER, checked_at TEXT
    )""")
    return conn


def _chay_migration(conn):
    ns = {'conn': conn}
    exec(migration_src, ns)


_tmp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
_tmp_db.close()

# ----- Test A: DB HOÀN TOÀN MỚI (chưa cờ nào được đánh dấu) — vài dòng
# canh_bao=NULL (poisoned) + 1 dòng hợp lệ (canh_bao=0) -> chạy migration 1
# LẦN -> xoá hết dòng NULL, GIỮ dòng hợp lệ, cả 2 cờ được đánh dấu xong. -----
conn = _fresh_conn()
conn.execute("INSERT INTO mst_status_cache VALUES('0311111111', '', NULL, '2026-01-01T00:00:00')")
conn.execute("INSERT INTO mst_status_cache VALUES('0322222222', '', NULL, '2026-01-01T00:00:00')")
conn.execute("INSERT INTO mst_status_cache VALUES('0333333333', 'Đang hoạt động', 0, '2026-01-01T00:00:00')")
conn.commit()
_chay_migration(conn)
conn.commit()
con_lai = {r["mst"] for r in conn.execute("SELECT mst FROM mst_status_cache").fetchall()}
assert con_lai == {"0333333333"}, f"Phải xoá hết dòng canh_bao=NULL, giữ lại dòng hợp lệ — got {con_lai}"
co_1 = conn.execute("SELECT 1 FROM app_settings WHERE key='mst_cache_null_cleanup_done'").fetchone()
co_2 = conn.execute("SELECT 1 FROM app_settings WHERE key='mst_cache_null_cleanup_done_v2'").fetchone()
assert co_1 and co_2, "Cả 2 cờ migration phải được đánh dấu đã chạy xong"
conn.close()
print("PASS A: DB mới -> migration xoá hết dòng canh_bao=NULL (poisoned), giữ dòng hợp lệ, đánh dấu "
      "cả 2 cờ đã chạy xong.")

# ----- Test B (QUAN TRỌNG — đúng ca thật): mô phỏng ĐÚNG tình huống thật đã
# xảy ra — migration THỨ 1 đã chạy xong TỪ TRƯỚC (cờ đã có), NHƯNG sau đó
# bug _goi_1_lan_xinvoice() (đã sửa) vẫn tiếp tục ghi thêm dòng canh_bao=NULL
# mới (vì migration 1 chạy XONG rồi, không dọn được dòng ghi SAU đó) -> PHẢI
# dọn được NHỜ migration thứ 2 (cờ RIÊNG, độc lập với cờ thứ 1). -----
os.unlink(_tmp_db.name)
_tmp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
_tmp_db.close()
conn = _fresh_conn()
conn.execute("INSERT INTO app_settings VALUES('mst_cache_null_cleanup_done', '1')")   # migration 1: ĐÃ xong từ trước
conn.execute("INSERT INTO mst_status_cache VALUES('0106869738', '', NULL, '2026-09-14T00:00:00')")  # VNPT - bị kẹt bởi bug 200-rỗng
conn.execute("INSERT INTO mst_status_cache VALUES('0301075425', '', NULL, '2026-09-14T00:00:00')")  # Trung tâm Đăng kiểm
conn.commit()
_chay_migration(conn)
conn.commit()
con_lai_b = {r["mst"] for r in conn.execute("SELECT mst FROM mst_status_cache").fetchall()}
assert con_lai_b == set(), (
    f"Migration thứ 2 PHẢI dọn được các dòng canh_bao=NULL do bug 200-thành-công-rỗng ghi SAU khi "
    f"migration thứ 1 đã chạy xong (đúng ca thật: VNPT/Trung tâm Đăng kiểm bị 'kẹt cứng không rõ lý "
    f"do') — got còn lại {con_lai_b}")
co_2b = conn.execute("SELECT 1 FROM app_settings WHERE key='mst_cache_null_cleanup_done_v2'").fetchone()
assert co_2b, "Cờ migration thứ 2 phải được đánh dấu đã chạy xong"
conn.close()
print("PASS B: migration thứ 1 đã chạy xong từ trước (cờ có sẵn) nhưng vẫn còn dòng canh_bao=NULL mới "
      "do bug 200-thành-công-rỗng ghi SAU đó -> migration thứ 2 (cờ riêng) vẫn dọn sạch được, đúng ca "
      "thật người dùng báo (VNPT/Trung tâm Đăng kiểm bị kẹt 'không rõ lý do').")

# ----- Test C (không hồi quy): CHỈ chạy ĐÚNG 1 LẦN — sau khi cả 2 cờ đã
# đánh dấu xong, thêm 1 dòng canh_bao=NULL MỚI rồi chạy lại migration ->
# KHÔNG được xoá (để tránh xoá nhầm dữ liệu ở các lần khởi động SAU). -----
conn = _fresh_conn()
conn.execute("INSERT INTO mst_status_cache VALUES('0344444444', '', NULL, '2026-09-15T00:00:00')")
conn.commit()
_chay_migration(conn)
conn.commit()
row_c = conn.execute("SELECT mst FROM mst_status_cache WHERE mst='0344444444'").fetchone()
assert row_c is not None, (
    "Sau khi cả 2 cờ đã đánh dấu xong, migration KHÔNG được chạy lại (dòng canh_bao=NULL mới phải "
    "được GIỮ NGUYÊN, không tự xoá tiếp ở các lần khởi động sau)")
conn.close()
print("PASS C: cả 2 migration CHỈ chạy đúng 1 lần — dòng canh_bao=NULL mới ở lần khởi động SAU không "
      "bị xoá tiếp (an toàn, tránh xoá nhầm dữ liệu tương lai).")

os.unlink(_tmp_db.name)
print("\nALL DONE")
