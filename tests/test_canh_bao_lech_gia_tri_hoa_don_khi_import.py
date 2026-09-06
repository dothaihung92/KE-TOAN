import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: đúng ca thật người dùng báo lại — hóa đơn Số HĐ 22619
(MST 0108705693-008) trong Bảng kê Đầu vào bị SỬA TAY sai (cộng dồn phí
"Phí kéo lầu bồn" 111.111đ vào Thành tiền dòng "Bồn Inox" rồi quên xóa
dòng phí gốc) khiến tổng Bảng kê (5.648.148đ) lệch so với hóa đơn GỐC đã
tra cứu (invoices.tgtcthue = 5.537.037đ). Yêu cầu người dùng: "hãy thêm
thông báo khi tôi import excel lại vào trong bảng kê nhập liệu nếu phát
hiện có sự thay đổi giá trị hoá đơn giống trường hợp này thì phần mềm sẽ
hiện thông báo... nhấn vào sẽ hiện đúng hoá đơn này để xử lý".

_canh_bao_lech_gia_tri_hoa_don_in() phải phát hiện ĐÚNG hóa đơn này (chỉ ra
đúng các dòng liên quan trong Bảng kê để nhảy tới), và KHÔNG báo nhầm hóa
đơn khớp đúng."""
import sys, sqlite3, json as _json
sys.path.insert(0, _REPO_ROOT)
import server

HEADER = ['Ký hiệu', 'Số HĐ', 'Ngày', 'Người bán', 'MST bán', 'STT', 'Mã vt',
          'Tên hàng hóa/dịch vụ', 'ĐVT', 'Số lượng', 'Đơn giá', 'Thành tiền',
          'Thuế suất', 'Tiền thuế GTGT', 'Trị giá tính thuế NK', 'Thuế suất NK',
          'Tiền thuế NK', 'Nợ', 'Có']


def db_factory():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE invoices (
        company_id INTEGER, loai TEXT, nbmst TEXT, nmmst TEXT, khhdon TEXT, shdon TEXT,
        tdlap TEXT, tgtcthue REAL, tgtthue REAL, tthai TEXT, raw TEXT, detail_json TEXT)""")
    # Hóa đơn 22619: đúng ca thật, tgtcthue GỐC = 5.537.037 (đã gồm cả 2 dòng
    # hàng hóa thật của hóa đơn — xem ca thật XML gốc).
    conn.execute(
        "INSERT INTO invoices VALUES (1,'purchase','0108705693-008','0318332127','C26THM','22619',"
        "'2026-08-29T10:00:00',5537037,442963,'1','{}',NULL)")
    # Hóa đơn khác (khớp đúng, không có gì bất thường) — để xác nhận KHÔNG bị
    # báo nhầm.
    conn.execute(
        "INSERT INTO invoices VALUES (1,'purchase','0313093362','0318332127','C26X','999',"
        "'2026-01-01T10:00:00',1000000,80000,'1','{}',NULL)")
    conn.commit()
    return conn


def test_phat_hien_dung_hoa_don_bi_sua_tay_lech_gia_tri():
    orig_db = server.db
    server.db = db_factory
    try:
        rows_in = [
            ['C26THM', '22619', '29/08/2026', 'CHI NHÁNH', '0108705693-008', '1',
             '9011315011020012', 'Bồn Inox Đại Thành 1.500N ĐK1170', 'Bộ', 1, 5537037, 5537037,
             '8%', 442963, None, None, None, '1561', '331'],
            ['C26THM', '22619', '29/08/2026', 'CHI NHÁNH', '0108705693-008', '2',
             '8300000000000043', 'Phí kéo lầu bồn Inox dưới 7 tầng - 1.500L', 'Gói', 1, 111111, 111111,
             '8%', 8889, None, None, None, '1561', '331'],
            # hóa đơn KHÁC, khớp đúng -> KHÔNG được báo
            ['C26X', '999', '01/01/2026', 'NCC X', '0313093362', '1', 'M1', 'Hàng A', 'Cái', 1,
             1000000, 1000000, '8%', 80000, None, None, None, '1561', '331'],
        ]
        kq = server._canh_bao_lech_gia_tri_hoa_don_in(1, HEADER, rows_in)
    finally:
        server.db = orig_db

    print("Cảnh báo:", kq)
    assert len(kq) == 1, f"Chỉ đúng 1 hóa đơn (22619) bị lệch — got {kq}"
    cb = kq[0]
    assert cb["so_hd"] == "22619", f"Phải đúng Số HĐ 22619 — got {cb}"
    assert cb["chenh_lech"] == 111111, f"Chênh lệch phải đúng 111.111đ (5.648.148 - 5.537.037) — got {cb}"
    assert sorted(cb["dong"]) == [0, 1], f"Phải chỉ đúng 2 dòng (chỉ số 0,1) của hóa đơn 22619 để nhảy tới — got {cb['dong']}"
    print("PASS: phát hiện đúng hóa đơn 22619 bị sửa tay lệch giá trị, chỉ đúng dòng cần xử lý, không báo "
          "nhầm hóa đơn khớp đúng khác.")


test_phat_hien_dung_hoa_don_bi_sua_tay_lech_gia_tri()

print("\nTẤT CẢ TEST PASS")
