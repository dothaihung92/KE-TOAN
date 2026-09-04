import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: hóa đơn NGOẠI TỆ (USD...) tra cứu từ Thuế phải được quy
đổi ra VNĐ (nhân tỷ giá) TRƯỚC khi lưu vào bảng invoices/dùng để đối chiếu —
người dùng báo cáo (@Ban_hang.xlsx, @Mua_hang_hoa__dich_vu.xlsx): "Đối chiếu
tổng giá trị & VAT" báo "Bán hàng TỔNG LỆCH (13/13 hóa đơn thiếu/lệch)" với
mẫu hình RẤT ĐẶC TRƯNG — "nguồn" (tra cứu Thuế) hiện số RẤT NHỎ (vd 6.837,
14.616đ) trong khi MISA (đã ghi ĐÚNG) hiện số RẤT LỚN cho ĐÚNG hóa đơn đó
(176.323.651, 376.952.056đ) — tỷ lệ luôn quanh 25.800-26.100 lần, đúng tỷ
giá USD/VNĐ thật theo từng ngày (xác nhận qua trả lời trực tiếp: hóa đơn
Bán hàng này xuất bằng USD). Nguyên nhân: bảng invoices lưu tgtcthue/
tgtthue/tgtttbso THEO NGUYÊN TỆ GỐC (chưa nhân tỷ giá) cho hóa đơn ngoại tệ,
trong khi MISA đã ghi đúng số VNĐ đã quy đổi từ trước — Đối chiếu so trực
tiếp 2 đơn vị khác nhau nên báo nhầm hàng loạt "thiếu"/"lệch"."""
import sys, sqlite3, os, tempfile, json
sys.path.insert(0, _REPO_ROOT)
import server

_db_path = tempfile.mktemp(suffix=".sqlite3")


def db_factory():
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    return conn


orig_db = server.db
server.db = db_factory

try:
    # ===== Phần 1: _quy_doi_ngoai_te_tu_inv — hàm thuần, quy đổi đúng khi
    # có dvtte/tgia (ngoại tệ), giữ nguyên khi là VNĐ/thiếu tỷ giá. =====
    inv_usd = {"dvtte": "USD", "tgia": "25791.99", "tgtcthue": "6837", "tgtthue": "0", "tgtttbso": "6837"}
    tc, tt, tb = server._quy_doi_ngoai_te_tu_inv(inv_usd)
    print("Quy đổi USD:", tc, tt, tb)
    assert abs(tc - 6837 * 25791.99) < 1, f"tgtcthue phải quy đổi đúng tỷ giá — được {tc}"
    assert abs(tb - 6837 * 25791.99) < 1, f"tgtttbso phải quy đổi đúng tỷ giá — được {tb}"
    assert tt == 0, f"tgtthue=0 (không VAT) vẫn phải ra 0 sau quy đổi — được {tt}"

    inv_vnd = {"dvtte": "VND", "tgia": "", "tgtcthue": "5000000", "tgtthue": "500000", "tgtttbso": "5500000"}
    tc2, tt2, tb2 = server._quy_doi_ngoai_te_tu_inv(inv_vnd)
    assert (tc2, tt2, tb2) == ("5000000", "500000", "5500000"), (
        f"Hóa đơn VNĐ (dvtte=VND) phải GIỮ NGUYÊN giá trị gốc, không quy đổi gì — được {(tc2, tt2, tb2)}")

    inv_no_dvtte = {"tgtcthue": "5000000", "tgtthue": "500000", "tgtttbso": "5500000"}
    tc3, tt3, tb3 = server._quy_doi_ngoai_te_tu_inv(inv_no_dvtte)
    assert (tc3, tt3, tb3) == ("5000000", "500000", "5500000"), (
        f"Hóa đơn KHÔNG có field dvtte (VNĐ mặc định) phải GIỮ NGUYÊN — được {(tc3, tt3, tb3)}")
    print("PASS: _quy_doi_ngoai_te_tu_inv quy đổi đúng ngoại tệ, giữ nguyên VNĐ.")

    # ===== Phần 2: _sua_hoa_don_ngoai_te_da_luu — backfill hóa đơn ngoại tệ
    # ĐÃ LƯU SAI (nguyên tệ gốc, từ trước khi có fix) về đúng VNĐ. =====
    conn = db_factory()
    conn.execute("""CREATE TABLE invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, loai TEXT, he_thong TEXT,
        nbmst TEXT, nbten TEXT, nmmst TEXT, khmshdon TEXT, khhdon TEXT, shdon TEXT,
        tdlap TEXT, tgtcthue REAL, tgtthue REAL, tgtttbso REAL, tthai TEXT, raw TEXT, detail_json TEXT,
        UNIQUE(company_id, nbmst, khmshdon, khhdon, shdon, loai, he_thong))""")

    conn.execute("""CREATE TABLE companies (
        id INTEGER PRIMARY KEY, save_dir TEXT)""")
    conn.execute("INSERT INTO companies VALUES (1, '')")
    # Hóa đơn USD ĐÃ LƯU SAI: tgtcthue/tgtttbso vẫn là 6.837/6.837 (nguyên tệ
    # gốc, CHƯA quy đổi) dù raw có đủ dvtte/tgia — đúng hiện trạng dữ liệu cũ
    # trước khi có fix này.
    raw_usd = json.dumps({"dvtte": "USD", "tgia": "25791.99", "tgtcthue": "6837",
                          "tgtthue": "0", "tgtttbso": "6837", "shdon": "3", "khhdon": "C26TUE"},
                         ensure_ascii=False)
    conn.execute("INSERT INTO invoices (company_id, loai, he_thong, nbmst, khhdon, shdon, "
                 "tgtcthue, tgtthue, tgtttbso, raw) VALUES (1,'sold','query','X','C26TUE','3',6837,0,6837,?)",
                 (raw_usd,))
    # Hóa đơn VNĐ bình thường — KHÔNG được đụng vào.
    raw_vnd = json.dumps({"dvtte": "VND", "tgtcthue": "5000000", "tgtthue": "500000",
                          "tgtttbso": "5500000", "shdon": "99"}, ensure_ascii=False)
    conn.execute("INSERT INTO invoices (company_id, loai, he_thong, nbmst, khhdon, shdon, "
                 "tgtcthue, tgtthue, tgtttbso, raw) VALUES (1,'sold','query','X','C26TUE','99',5000000,500000,5500000,?)",
                 (raw_vnd,))
    conn.commit()
    conn.close()

    kq1 = server._sua_hoa_don_ngoai_te_da_luu(1)
    print("Kết quả sửa lần 1:", kq1)
    assert kq1["so_sua"] == 1, f"Chỉ đúng 1 hóa đơn USD cần sửa, hóa đơn VNĐ không đụng tới — được {kq1}"

    conn = db_factory()
    r_usd = conn.execute("SELECT tgtcthue, tgtthue, tgtttbso FROM invoices WHERE shdon='3'").fetchone()
    r_vnd = conn.execute("SELECT tgtcthue, tgtthue, tgtttbso FROM invoices WHERE shdon='99'").fetchone()
    conn.close()
    print("Sau khi sửa — USD:", dict(r_usd), "VNĐ:", dict(r_vnd))
    assert abs(r_usd["tgtcthue"] - 6837 * 25791.99) < 1, (
        f"tgtcthue hóa đơn USD phải được SỬA LẠI đúng số VNĐ đã quy đổi — được {r_usd['tgtcthue']}")
    assert abs(r_usd["tgtttbso"] - 6837 * 25791.99) < 1
    assert r_vnd["tgtcthue"] == 5000000 and r_vnd["tgtthue"] == 500000 and r_vnd["tgtttbso"] == 5500000, (
        f"Hóa đơn VNĐ PHẢI GIỮ NGUYÊN, không bị đụng vào — được {dict(r_vnd)}")
    print("PASS: backfill sửa đúng hóa đơn USD, không đụng hóa đơn VNĐ.")

    # ===== Chạy lại lần 2 (idempotent) — KHÔNG được nhân tỷ giá thêm lần
    # nữa (vì tính lại từ 'raw' gốc, không phải từ giá trị đã sửa). =====
    kq2 = server._sua_hoa_don_ngoai_te_da_luu(1)
    print("Kết quả sửa lần 2 (chạy lại):", kq2)
    assert kq2["so_sua"] == 0, (
        f"Chạy lại lần 2 KHÔNG được sửa gì nữa (đã đúng từ lần 1, tính lại từ 'raw' gốc phải ra CÙNG kết "
        f"quả, không nhân tỷ giá chồng lần nữa) — được {kq2}")
    print("PASS: backfill an toàn khi chạy lại nhiều lần (idempotent), không nhân tỷ giá 2 lần.")

    print("\nTẤT CẢ TEST PASS")
finally:
    server.db = orig_db
    try:
        os.remove(_db_path)
    except OSError:
        pass
