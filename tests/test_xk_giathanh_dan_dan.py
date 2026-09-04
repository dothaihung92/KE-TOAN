import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: hành vi MỚI của Xuất Kho (Sheet GIATHANH) theo đúng 3
yêu cầu người dùng:

1) Không import gì thêm -> vẫn xử lý đúng dữ liệu đã có sẵn từ đầu (bootstrap
   1 lần từ 'Chi tiết BÁN RA' (ctbr) khi bảng Xuất Kho đang RỖNG).
2) Đã Xoá dữ liệu Xuất Kho rồi import dữ liệu mới (vd '📥 Import giá thành')
   -> 'Dò mã hàng tự động' CHỈ xử lý đúng dữ liệu mới đó, KHÔNG tự động lôi
   lại dữ liệu cũ đã import từ Nhập Liệu (ctbr) về.
3) Thêm dữ liệu (không xoá) -> dữ liệu mới được thêm vào CUỐI bảng Xuất Kho
   (đã tự gán mã ngay lúc import, xem _xk_gop_them_ban_hang/_xk_gan_ma_lo_moi),
   'Dò mã hàng tự động' xử lý đúng dữ liệu ĐANG CÓ trong bảng (không rebuild
   lại từ ctbr).

Đồng thời xác nhận TÁCH DÒNG (1 hoá đơn cần nhiều mã mới đủ tồn, xem
_xk_gan_1_muc — logic dùng chung sau khi refactor _gen_xk_giathanh) vẫn hoạt
động đúng, và tồn kho được trừ ĐÚNG LIÊN TỤC qua nhiều lô import kế tiếp
(không double-allocate / không âm tồn ngầm)."""
import sys, sqlite3, os, tempfile
sys.path.insert(0, _REPO_ROOT)
import server

_db_path = tempfile.mktemp(suffix=".sqlite3")
_data_dir = tempfile.mkdtemp()


def db_factory():
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    return conn


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
    conn.execute("INSERT INTO companies VALUES (2,'0300000002','','')")
    conn.commit()
    conn.close()

    # ---- Chuẩn bị Sheet TON cho công ty 1: 2 mã CÙNG tên "Chau ABC", MA1
    # đứng trước (tồn 3), MA2 đứng sau (tồn 4) — KHÔNG mã đơn nào đủ 5 cả
    # (3<5 và 4<5) nên PHẢI tách dòng (dùng hết MA1 rồi mới bù MA2, đúng
    # thứ tự xuất hiện trong file tồn kho).
    data1 = server._doc_du_lieu_cty(1)
    data1["xk_ton"] = [
        {"ma": "MA1", "ten": "Chau ABC", "dvt": "Cai", "ton": 3, "gia": 100000},
        {"ma": "MA2", "ten": "Chau ABC", "dvt": "Cai", "ton": 4, "gia": 100000},
    ]
    server._ghi_du_lieu_cty(1, data1)

    # ===== Lô 1: hoá đơn H1 cần 5 Chau ABC -> TÁCH DÒNG (3 từ MA1 + 2 từ MA2) =====
    rows_l1 = [["", "H1", "10/05/2026", "Chau ABC", "Cai", 5, 100000, 500000]]
    so_them1, so_trung1, tong1 = server._xk_gop_them_ban_hang(1, CTBR_HEADER, rows_l1)
    assert so_them1 == 1 and tong1 == 1, f"Lô 1: phải gộp đúng 1 dòng ctbr — được {so_them1}, {tong1}"

    gt1 = server._doc_du_lieu_cty(1).get("xk_giathanh") or []
    print("Sau lô 1 (H1, cần 5, MA1 chỉ có 3):", gt1)
    assert len(gt1) == 2, f"H1 (SL=5) phải bị TÁCH thành 2 dòng (MA1 hết 3, MA2 bù 2) — được {len(gt1)} dòng: {gt1}"
    ma1_dong = next(r for r in gt1 if r["ma"] == "MA1")
    ma2_dong = next(r for r in gt1 if r["ma"] == "MA2")
    assert ma1_dong["sl"] == 3 and ma2_dong["sl"] == 2, (
        f"Tách dòng phải đúng 3 (MA1, hết tồn) + 2 (MA2, bù phần thiếu) — được MA1={ma1_dong['sl']}, MA2={ma2_dong['sl']}")
    assert all(r["sohd"] == "H1" for r in gt1), f"Cả 2 dòng tách đều phải giữ đúng Số HĐ H1 — được {gt1}"

    # ===== Lô 2 (yêu cầu 3 — THÊM dữ liệu, KHÔNG xoá): hoá đơn H2 cần đúng 2
    # Chau ABC (= đúng phần MA2 còn lại 4-2=2 sau lô 1) -> MA1 đã HẾT tồn
    # (dùng hết ở lô 1) nên phải lấy ĐÚNG từ MA2, KHÔNG được gán lại MA1 (sẽ
    # âm tồn) — xác nhận tồn kho trừ LIÊN TỤC qua nhiều lô, và dữ liệu lô 1
    # (H1) không bị đụng tới. =====
    rows_l2 = [["", "H2", "12/05/2026", "Chau ABC", "Cai", 2, 100000, 200000]]
    so_them2, so_trung2, tong2 = server._xk_gop_them_ban_hang(1, CTBR_HEADER, rows_l2)
    assert so_them2 == 1 and tong2 == 2, f"Lô 2: phải gộp thêm đúng 1 dòng ctbr (tổng 2) — được {so_them2}, {tong2}"

    gt2 = server._doc_du_lieu_cty(1).get("xk_giathanh") or []
    print("Sau lô 2 (H2, cần 2, MA1 đã hết):", gt2)
    assert len(gt2) == 3, f"Phải có ĐỦ 3 dòng (2 dòng H1 GIỮ NGUYÊN + 1 dòng H2 mới) — được {len(gt2)} dòng: {gt2}"
    # 2 dòng đầu (H1) phải giữ NGUYÊN như lô 1 (không bị rebuild lại).
    assert gt2[0] == ma1_dong and gt2[1] == ma2_dong, "Dữ liệu H1 (lô 1) phải GIỮ NGUYÊN, không bị đụng tới khi gộp lô 2"
    h2_dong = gt2[2]
    assert h2_dong["sohd"] == "H2" and h2_dong["sl"] == 2, f"H2 phải là dòng MỚI thêm ở CUỐI bảng — được {h2_dong}"
    assert h2_dong["ma"] == "MA2", (
        f"H2 (2 cái) phải được gán MA2 (MA1 đã dùng hết ở lô 1, không được gán lại gây âm tồn) — được ma={h2_dong['ma']}")

    # ===== Yêu cầu 2: Xoá dữ liệu Xuất Kho rồi import dữ liệu mới (mô phỏng
    # '📥 Import giá thành' — THAY THẾ toàn bộ GIATHANH bằng 1 hoá đơn KHÁC,
    # KHÔNG liên quan gì tới ctbr đang có sẵn 2 hoá đơn H1/H2) -> bấm "Dò mã
    # hàng tự động" (xk_tao_giathanh) KHÔNG được tự động lôi lại H1/H2 (dữ
    # liệu cũ từ Nhập Liệu) về, CHỈ xử lý đúng dữ liệu mới. =====
    data1 = server._doc_du_lieu_cty(1)
    data1["xk_giathanh"] = [{
        "khhdon": "", "sohd": "999", "ngay": "01/06/2026", "ten_sp": "Chau XYZ khac han",
        "dvt": "Cai", "sl": 1, "dgia": 200000, "tt": 200000,
        "ma": "MA2", "ten_xk": "Chau ABC", "dvt_xk": "Cai", "gia_xk": 100000,
        "goi_y": [], "mo_ho": False, "thieu_ton": False,
    }]
    server._ghi_du_lieu_cty(1, data1)

    kq = server.xk_tao_giathanh(1)
    print("Sau Xoá + Import dữ liệu mới rồi Dò mã hàng tự động:", kq["rows"])
    so_hd_con = [r["sohd"] for r in kq["rows"]]
    assert so_hd_con == ["999"], (
        f"Sau khi Xoá dữ liệu Xuất Kho + import dữ liệu MỚI, 'Dò mã hàng tự động' phải CHỈ xử lý đúng "
        f"dữ liệu mới (hoá đơn 999), KHÔNG được tự động lôi lại H1/H2 (dữ liệu cũ từ Nhập Liệu ctbr) về "
        f"— được {so_hd_con}")

    # ===== Yêu cầu 1 (công ty KHÁC, mô phỏng bảng Xuất Kho CHƯA từng dùng —
    # bootstrap lần đầu): 'Chi tiết BÁN RA' (ctbr) đã có sẵn dữ liệu (Import
    # & Lưu Bảng kê Đầu ra trước đây), Xuất Kho hoàn toàn RỖNG (chưa import/
    # bấm gì) -> 'Dò mã hàng tự động' phải LẤY dữ liệu ctbr TỪ ĐẦU, xử lý
    # đúng như trước giờ. =====
    data2 = server._doc_du_lieu_cty(2)
    data2["xk_ton"] = [{"ma": "MB1", "ten": "San pham Z", "dvt": "Cai", "ton": 20, "gia": 50000}]
    server._ghi_du_lieu_cty(2, data2)
    conn = server.db()
    conn.execute("""CREATE TABLE IF NOT EXISTS nhap_lieu (
        id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, loai TEXT,
        header_json TEXT, rows_json TEXT, updated_at TEXT, UNIQUE(company_id, loai))""")
    import json as _json
    conn.execute("""INSERT INTO nhap_lieu (company_id, loai, header_json, rows_json, updated_at)
        VALUES (2,'ctbr',?,?,'')""",
        (_json.dumps(CTBR_HEADER, ensure_ascii=False),
         _json.dumps([["", "B1", "05/05/2026", "San pham Z", "Cai", 6, 50000, 300000]], ensure_ascii=False)))
    conn.commit()
    conn.close()

    kq2 = server.xk_tao_giathanh(2)
    print("Bootstrap công ty 2 (Xuất Kho chưa từng dùng, ctbr có sẵn):", kq2["rows"])
    assert len(kq2["rows"]) == 1 and kq2["rows"][0]["ma"] == "MB1" and kq2["rows"][0]["sl"] == 6, (
        f"Chưa import gì thêm ở Xuất Kho (bảng đang rỗng) thì phải lấy TOÀN BỘ dữ liệu ctbr đã có sẵn từ "
        f"đầu để xử lý, y hệt trước giờ — được {kq2['rows']}")

    print("\nPASS: Xuất Kho hoạt động đúng cả 3 yêu cầu (bootstrap mặc định / không lôi lại dữ liệu cũ "
          "sau khi Xoá+Import mới / thêm dữ liệu vào cuối bảng và trừ tồn liên tục đúng qua nhiều lô, "
          "kể cả khi cần TÁCH DÒNG).")
finally:
    server.db = orig_db
    server.DATA_DIR = orig_data_dir
    try:
        os.remove(_db_path)
    except OSError:
        pass
    import shutil
    shutil.rmtree(_data_dir, ignore_errors=True)

print("\nTẤT CẢ TEST PASS")
