import os
import sys
import sqlite3
import datetime
import tempfile

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Regression test cho việc LƯU KẾT QUẢ TRA MST TRONG NGÀY (_mst_cache_doc_trong_ngay/_mst_cache_ghi,
# dùng trong _tra_cuu_trang_thai_mst) — người dùng đồng ý: mỗi lượt xuất Excel chỉ có ngân sách
# thời gian giới hạn để tra MST, trước đây KHÔNG lưu gì nên lượt sau lại tra lại đúng những MST đầu
# danh sách, các MST sau không bao giờ tới lượt (câu "sẽ tự bổ sung ở lần xuất Excel sau" trong log
# vì vậy không đúng). Giờ: kết quả tra ĐƯỢC lưu lại và dùng lại TRONG CÙNG NGÀY; sang ngày mới tra lại
# (vẫn đúng ý "dò ở thời điểm hiện tại"); không tra được thì KHÔNG lưu.

_duong_db = tempfile.mktemp(suffix=".sqlite3")


def _db_tam():
    c = sqlite3.connect(_duong_db)
    c.row_factory = sqlite3.Row
    return c


c0 = _db_tam()
c0.execute("""CREATE TABLE mst_status_cache (mst TEXT PRIMARY KEY, trang_thai_goc TEXT,
              canh_bao INTEGER, checked_at TEXT)""")
c0.commit()
c0.close()

_goc = {k: getattr(server, k) for k in (
    "db", "_tra_cuu_mst_qua_masothue_trinh_duyet", "_tra_cuu_mst_qua_tracuunnt",
    "_lay_danh_sach_xinvoice_keys", "_MST_API_NGHI_GIUA_LUOT")}
server.db = _db_tam
server._MST_API_NGHI_GIUA_LUOT = 0
server._lay_danh_sach_xinvoice_keys = lambda: []
try:
    # ===== 1: ghi rồi đọc lại trong ngày -> có; lưu từ HÔM QUA -> không dùng; dòng không tra được
    # (canh_bao NULL) -> không dùng. =====
    server._mst_cache_ghi("0311941289", "Đang hoạt động", False)
    assert server._mst_cache_doc_trong_ngay("0311941289") == {"trang_thai": "Đang hoạt động", "canh_bao": False}
    server._mst_cache_ghi("0311941289", "Ngừng hoạt động", True)   # ghi đè kết quả mới hơn
    assert server._mst_cache_doc_trong_ngay("0311941289") == {"trang_thai": "Ngừng hoạt động", "canh_bao": True}
    hom_qua = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat(timespec="seconds")
    c = _db_tam()
    c.execute("INSERT INTO mst_status_cache VALUES ('0300000001', 'Đang hoạt động', 0, ?)", (hom_qua,))
    c.execute("INSERT INTO mst_status_cache VALUES ('0300000002', '', NULL, ?)",
              (datetime.datetime.now().isoformat(timespec="seconds"),))
    c.commit()
    c.close()
    assert server._mst_cache_doc_trong_ngay("0300000001") is None, "Lưu từ hôm qua -> phải tra lại."
    assert server._mst_cache_doc_trong_ngay("0300000002") is None, "Không tra được (NULL) -> không dùng."
    assert server._mst_cache_doc_trong_ngay("0399999999") is None
    print("PASS 1: chỉ dùng lại kết quả tra ĐƯỢC trong CÙNG NGÀY; hôm trước/không tra được thì tra lại.")

    # ===== 2: _tra_cuu_trang_thai_mst: lần đầu tra qua nguồn + lưu; lần sau trong ngày KHÔNG gọi
    # nguồn nào; kể cả khi đã hết ngân sách thời gian (chi_dung_cache) vẫn trả kết quả đã lưu. =====
    goi = []
    server._tra_cuu_mst_qua_masothue_trinh_duyet = lambda m, t: (
        goi.append(m), (True, "Đang hoạt động (đã được cấp GCN ĐKT)", False, None))[1]
    server._tra_cuu_mst_qua_tracuunnt = lambda m, t: (goi.append("tracuunnt"), (False, "", None, "lỗi"))[1]
    kq1 = server._tra_cuu_trang_thai_mst("0312345678")
    kq2 = server._tra_cuu_trang_thai_mst("0312345678")
    kq3 = server._tra_cuu_trang_thai_mst("0312345678", chi_dung_cache=True)
    mong_doi = {"trang_thai": "Đang hoạt động (đã được cấp GCN ĐKT)", "canh_bao": False}
    assert kq1 == kq2 == kq3 == mong_doi, f"got {kq1!r} {kq2!r} {kq3!r}"
    assert goi == ["0312345678"], f"Chỉ được tra qua mạng ĐÚNG 1 lần trong ngày — got {goi}"
    print("PASS 2: MST đã tra được trong ngày -> các lượt sau (kể cả khi hết ngân sách thời gian) dùng "
          "lại, không gọi mạng.")

    # ===== 3: không tra được -> KHÔNG lưu, lượt sau vẫn tra lại qua mạng. =====
    goi.clear()
    server._tra_cuu_mst_qua_masothue_trinh_duyet = lambda m, t: (goi.append(m), (False, "", None, "lỗi"))[1]
    kq = server._tra_cuu_trang_thai_mst("0319876543")
    assert kq["canh_bao"] is None and kq.get("ly_do_loi")
    server._tra_cuu_trang_thai_mst("0319876543")
    assert goi == ["0319876543", "tracuunnt", "0319876543", "tracuunnt"], (
        f"Không tra được thì lượt sau phải tra lại (masothue.com rồi tracuunnt) — got {goi}")
    assert server._mst_cache_doc_trong_ngay("0319876543") is None
    print("PASS 3: không tra được thì không lưu, lượt sau tra lại.")

    # (Giới hạn thời gian tra MST mỗi lượt đã BỎ theo yêu cầu người dùng — xem
    # test_tra_mst_tien_do_khong_gioi_han.py.)
finally:
    for k, v in _goc.items():
        setattr(server, k, v)
    try:
        os.remove(_duong_db)
    except Exception:
        pass

print("\nALL DONE")
