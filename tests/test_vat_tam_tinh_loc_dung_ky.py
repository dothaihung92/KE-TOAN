import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: vat_tam_tinh() ("Tạm tính thuế GTGT trong kỳ") — khi
KHÔNG có dữ liệu đã import (dùng dữ liệu tra cứu trực tiếp từ bảng
invoices), PHẢI chỉ cộng hóa đơn NẰM TRONG đúng kỳ (ky) đang tính, KHÔNG
được cộng lẫn hóa đơn của kỳ khác còn sót lại trong bảng invoices.

Đúng ca thật người dùng báo cáo (kèm ảnh chụp + file Excel bảng kê thật):
công ty MST 0313829148, kỳ Q3/2026 — phần mềm báo VAT mua vào 50.010.855đ/
VAT bán ra 130.987.776đ, trong khi bảng kê hóa đơn THẬT của đúng Q3/2026
(kết xuất trực tiếp từ trang Thuế, 74 hóa đơn mua + 202 hóa đơn bán) chỉ có
VAT mua 26.899.508đ/VAT bán 61.378.697đ — gần gấp đôi số thật.

Nguyên nhân: bảng invoices chỉ XOÁ/GHI ĐÈ theo (company_id, loai, he_thong)
mỗi lần tra cứu (xem "DELETE FROM invoices WHERE company_id=? AND loai=?
AND he_thong=?" ở luồng tra cứu), KHÔNG theo kỳ — nếu "HĐ điện tử thường"
(he_thong='query') và "HĐ máy tính tiền" (he_thong='sco-query') từng được
tra cứu ở 2 khoảng ngày KHÁC nhau (vd 1 bên đã tra cứu lại đúng kỳ đang
xem, bên kia còn sót dữ liệu của lần tra cứu TRƯỚC với khoảng ngày rộng
hơn/khác kỳ), bảng invoices sẽ lẫn lộn NHIỀU kỳ cùng lúc. vat_tam_tinh()
(nhánh "tra cứu", không có import) trước đây cộng THẲNG toàn bộ hóa đơn
trong bảng company_id đó, không lọc theo ky -> ra số cao hơn hẳn số thật
của đúng kỳ, không cảnh báo gì cho người dùng biết.

Fix: lọc rows theo tdlap (ngày lập) nằm trong khoảng ngày của đúng ky
(_khoang_ngay_ky) TRƯỚC khi cộng dồn vat_mua/vat_ban, y hệt cách luồng
xuất Excel đã lọc đúng kỳ trước khi xử lý (xem _ngay_hoa_don ở luồng đó)."""
import sys, sqlite3, tempfile, json
sys.path.insert(0, _REPO_ROOT)
import server


_db_path = tempfile.mktemp(suffix=".sqlite3")


def db_factory():
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    return conn


orig_db = server.db
server.db = db_factory

conn0 = db_factory()
conn0.execute("""CREATE TABLE companies (id INTEGER PRIMARY KEY, mst TEXT)""")
conn0.execute("""CREATE TABLE invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, loai TEXT, he_thong TEXT,
    nbmst TEXT, nbten TEXT, nmmst TEXT, khmshdon TEXT, khhdon TEXT, shdon TEXT,
    tdlap TEXT, tgtcthue REAL, tgtthue REAL, tgtttbso REAL, tthai TEXT, raw TEXT)""")
conn0.execute("""CREATE TABLE imported_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, ky TEXT,
    mua_ds REAL, mua_thue REAL, ban_ds_0 REAL, ban_ds_5 REAL, ban_thue_5 REAL,
    ban_ds_8 REAL, ban_thue_8 REAL, ban_ds_10 REAL, ban_thue_10 REAL,
    ban_ds_kct REAL, updated_at TEXT)""")
conn0.execute("""CREATE TABLE vat_balance (
    id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, ky TEXT,
    du_dau_ky REAL, vat_mua REAL, vat_ban REAL, phai_nop REAL, du_cuoi_ky REAL,
    updated_at TEXT)""")
conn0.execute("""CREATE TABLE tokhai_nhap (
    id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, so_tk TEXT,
    ngay_dk TEXT, nguoi_xk TEXT, items_json TEXT)""")
conn0.execute("INSERT INTO companies (id, mst) VALUES (1, '0313829148')")


def them_hd(loai, he_thong, shdon, ngay, tgtthue, tthai="1"):
    conn0.execute(
        "INSERT INTO invoices (company_id, loai, he_thong, nbmst, nbten, nmmst, khmshdon, "
        "khhdon, shdon, tdlap, tgtcthue, tgtthue, tgtttbso, tthai, raw) VALUES "
        "(1, ?, ?, 'MST-NB', 'Ten NB', 'MST-NM', '1', 'K1', ?, ?, ?, ?, ?, ?, ?)",
        (loai, he_thong, shdon, ngay, tgtthue * 10, tgtthue, tgtthue * 11, tthai,
         json.dumps({"tthai": tthai})))


# ===== Test 1 (QUAN TRỌNG — đúng ca thật): "HĐ điện tử thường" (query) đã tra cứu ĐÚNG kỳ Q3/2026,
# nhưng "HĐ máy tính tiền" (sco-query) còn sót dữ liệu của kỳ Q2/2026 (tra cứu trước đó, chưa tra
# cứu lại) -> vat_tam_tinh(ky='Q3/2026') PHẢI CHỈ cộng đúng hóa đơn Q3/2026, KHÔNG được cộng lẫn hóa
# đơn Q2/2026 còn sót của MTT. =====
them_hd("purchase", "query", "HD-Q3-MUA-1", "01/07/2026", 3_000_000)
them_hd("purchase", "query", "HD-Q3-MUA-2", "15/09/2026", 2_000_000)
them_hd("sold", "query", "HD-Q3-BAN-1", "10/08/2026", 5_000_000)
# dữ liệu MTT còn sót của Q2/2026 (04-06/2026) — KHÔNG thuộc kỳ đang tính Q3/2026
them_hd("sold", "sco-query", "HD-Q2-MTT-1", "10/04/2026", 9_000_000)
them_hd("sold", "sco-query", "HD-Q2-MTT-2", "20/05/2026", 4_000_000)
conn0.commit()

resp = server.Response()
ket1 = server.vat_tam_tinh(1, resp, ky="Q3/2026", du_dau_ky=0)
print("Test 1 (lọc đúng kỳ, bỏ dữ liệu kỳ khác còn sót):", ket1)
assert ket1["vat_mua"] == 5_000_000, (
    f"VAT mua vào phải CHỈ tính 2 hóa đơn Q3/2026 (3tr+2tr=5tr), không tính hóa đơn kỳ khác — "
    f"được {ket1['vat_mua']}")
assert ket1["vat_ban"] == 5_000_000, (
    f"VAT bán ra phải CHỈ tính đúng 1 hóa đơn Q3/2026 (5tr) — KHÔNG được cộng lẫn 2 hóa đơn MTT còn "
    f"sót của Q2/2026 (9tr+4tr) — được {ket1['vat_ban']} (nếu ra 18tr = cộng lẫn cả kỳ khác, đúng lỗi "
    f"thật đã báo)")

# ===== Test 2 (không hồi quy): hóa đơn Q2/2026 (MTT) khi tính đúng kỳ Q2/2026 vẫn được cộng đủ —
# xác nhận việc lọc không xóa nhầm dữ liệu của CHÍNH kỳ đó. =====
ket2 = server.vat_tam_tinh(1, resp, ky="Q2/2026", du_dau_ky=0)
print("Test 2 (không hồi quy, tính đúng kỳ có dữ liệu):", ket2)
assert ket2["vat_ban"] == 13_000_000, (
    f"Khi tính ĐÚNG kỳ Q2/2026 (kỳ của chính 2 hóa đơn MTT đó) vẫn phải cộng đủ (9tr+4tr=13tr) — "
    f"được {ket2['vat_ban']}")
assert ket2["vat_mua"] == 0, f"Q2/2026 không có hóa đơn mua nào — phải = 0, được {ket2['vat_mua']}"

# ===== Test 3 (không hồi quy — QUAN TRỌNG): ky rỗng/không hợp lệ (không parse được) -> GIỮ NGUYÊN
# hành vi cũ (cộng toàn bộ, không lọc) — không đổi hành vi các luồng gọi không truyền ky. =====
ket3 = server.vat_tam_tinh(1, resp, ky="", du_dau_ky=0)
print("Test 3 (ky rỗng -> không lọc, giữ hành vi cũ):", ket3)
assert ket3["vat_mua"] == 5_000_000 and ket3["vat_ban"] == 18_000_000, (
    f"ky rỗng phải cộng TOÀN BỘ hóa đơn trong bảng (hành vi cũ, không lọc theo kỳ) — được {ket3}")

server.db = orig_db
print("\nTẤT CẢ TEST PASS")
