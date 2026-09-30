import os
import sys
import json
import sqlite3
import tempfile
import asyncio
import datetime
import random
import xml.etree.ElementTree as ET

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Yêu cầu: thêm bảng kê chi tiết người phụ thuộc (nhập trong phần mềm); Bảng Lương tự tính giảm trừ người phụ thuộc theo danh sách; kết xuất QT TNCN dùng
# danh sách này lập bảng kê 05-3/BK-QTT-TNCN.
NS = {"t": "http://kekhaithue.gdt.gov.vn/TKhaiThue"}
TS = server._luong_chuan_tham_so(None, 2025)
HD = server.NPT_HEADERS
assert HD == ["STT", "Mã NV", "Họ và tên người lao động", "Họ và tên người phụ thuộc", "Ngày sinh", "CCCD/Số định danh", "Quan hệ", "Từ tháng", "Đến tháng"]
NPT = {"header": HD, "rows": [
    [1, "1", "Hồ Thị A", "Hồ Quang Khải", "10/03/1948", "034048001696", "Cha/mẹ", "01/2025", ""],
    [2, "1", "Hồ Thị A", "Hồ Con Một", "02/03/2015", "", "Con", "04/2025", "09/2025"],
    [3, "", "Trần Thị B", "Trần Con Hai", "25/11/2016", "079206010409", "Vợ/chồng", "", "06/2025"],
    [4, "9", "", "Thiếu thông tin", "", "", "Con", "", ""],              # không xác định được người lao động bằng Mã NV hợp lệ? (có Mã NV 9 -> vẫn là bản ghi của mã 9)
    [5, "1", "Hồ Thị A", "", "", "", "Con", "", ""],                   # thiếu tên người phụ thuộc -> bỏ qua
]}

# ===== 1: đọc danh sách + đếm số người phụ thuộc theo tháng =====
ds = server._luong_npt_doc(NPT)
assert [r["ten"] for r in ds] == ["Hồ Quang Khải", "Hồ Con Một", "Trần Con Hai", "Thiếu thông tin"], "Dòng thiếu tên người phụ thuộc bị bỏ qua"
assert ds[0]["tu"] == (2025, 1) and ds[0]["den"] is None and ds[1]["den"] == (2025, 9) and ds[2]["tu"] is None and ds[2]["den"] == (2025, 6)
n = lambda ma, ten, t, nam=2025: server._luong_so_npt_thang(ds, ma, ten, nam, t)
assert [n("1", "Hồ Thị A", t) for t in range(1, 13)] == [1, 1, 1, 2, 2, 2, 2, 2, 2, 1, 1, 1], "Cha/mẹ từ T1; con T4–T9"
assert [n("", "tran thi b", t) for t in (1, 6, 7)] == [1, 1, 0], "Khớp theo họ tên không dấu khi không có Mã NV; Đến tháng 06/2025"
assert n("1", "Hồ Thị A", 12, 2024) == 0 and n("1", "Hồ Thị A", 1, 2026) == 1, "Từ tháng 01/2025: năm trước chưa có; Đến tháng trống: còn mãi"
assert n("2", "Người khác", 5) == 0
print("PASS 1: danh sách người phụ thuộc: đọc, bỏ dòng thiếu tên, đếm đúng theo từ tháng/đến tháng.")

# ===== 2: Bảng Lương tự giảm trừ người phụ thuộc theo danh sách (kể cả khi người dùng nhập tay số khác) =====
_duong = tempfile.mktemp(suffix=".db")
def _db_tam():
    c = sqlite3.connect(_duong)
    c.row_factory = sqlite3.Row
    return c
_goc = server.db
server.db = _db_tam
try:
    c0 = _db_tam()
    c0.execute("CREATE TABLE nhap_lieu (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, loai TEXT, header_json TEXT, rows_json TEXT, updated_at TEXT, UNIQUE(company_id, loai))")
    c0.execute("CREATE TABLE bang_luong (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, nam INTEGER, tham_so_json TEXT, thang_json TEXT, updated_at TEXT, UNIQUE(company_id, nam))")
    hd_nv = ["STT", "Mã NV", "Họ và tên", "CCCD", "Đóng BHXH", "Chức vụ", "Lương Cơ bản"]
    rows_nv = [[1, "1", "Hồ Thị A", "001175007514", "x", "KD", 30_000_000], [2, "", "Trần Thị B", "079187022032", "x", "KD", 30_000_000]]
    c0.execute("INSERT INTO nhap_lieu (company_id, loai, header_json, rows_json) VALUES (1,'nv',?,?)", (json.dumps(hd_nv), json.dumps(rows_nv)))
    a_nhap = {"ma": "1", "ten": "Hồ Thị A", "luong_cb": 30_000_000, "dong_bh": 1, "so_npt": 5}         # nhập tay 5 (sai) — danh sách là nguồn chuẩn
    b_nhap = {"ma": "", "ten": "Trần Thị B", "luong_cb": 30_000_000, "dong_bh": 1, "so_npt": 0}
    thang_json = {"%02d" % t: [a_nhap, b_nhap] for t in range(1, 13)}
    c0.execute("INSERT INTO bang_luong (company_id, nam, tham_so_json, thang_json) VALUES (1, 2025, '{}', ?)", (json.dumps(thang_json),))
    c0.commit(); c0.close()

    # chưa có danh sách: giữ số nhập tay
    kq0 = server.bang_luong_get(1, 2025)
    assert kq0["thang"]["05"][0]["so_npt"] == 5 and kq0["thang"]["05"][0]["tien_giam_tru_npt"] == 5 * 4_400_000
    c1 = _db_tam()
    c1.execute("INSERT INTO nhap_lieu (company_id, loai, header_json, rows_json) VALUES (1,'npt',?,?)", (json.dumps(HD), json.dumps(NPT["rows"])))
    c1.commit(); c1.close()
    kq = server.bang_luong_get(1, 2025)
    a5, b5, a2, a7 = kq["thang"]["05"][0], kq["thang"]["05"][1], kq["thang"]["02"][0], kq["thang"]["07"][1]
    assert a5["so_npt"] == 2 and a5["tien_giam_tru_npt"] == 2 * 4_400_000, "T5: cha/mẹ + con = 2 người phụ thuộc"
    assert a2["so_npt"] == 1 and kq["thang"]["12"][0]["so_npt"] == 1
    assert b5["so_npt"] == 1 and a7["so_npt"] == 0, "Trần Thị B: hết giảm trừ sau 06/2025"
    # thuế giảm đúng theo giảm trừ: 2 NPT ít hơn 1 NPT một khoản 4,4tr x thuế suất biên
    so_sanh = server._luong_tinh_dong(dict(a_nhap, so_npt=0), TS, "05")
    assert a5["tn_tinh_thue"] == so_sanh["tn_tinh_thue"] - 2 * 4_400_000 and a5["thue_tncn"] < so_sanh["thue_tncn"]
    # nạp từ Danh Sách Nhân Viên: dòng dựng sẵn có số NPT theo tháng + cờ npt_co_ds
    server.nhap_lieu_get.__globals__  # noqa (dùng hàm thật đọc DB tạm)
    r = server.bang_luong_tu_nhan_vien(1, 2025, 5)
    assert r["npt_co_ds"] is True and {x["ten"]: x["so_npt"] for x in r["rows"]} == {"Hồ Thị A": 2.0, "Trần Thị B": 1.0}
    r7 = server.bang_luong_tu_nhan_vien(1, 2025, 7)
    assert {x["ten"]: x["so_npt"] for x in r7["rows"]} == {"Hồ Thị A": 2.0, "Trần Thị B": 0.0}
    # lưu lại bảng lương -> dữ liệu trả về vẫn theo danh sách
    class Req:
        def __init__(self, b): self._b = b
        async def json(self): return self._b
    out = asyncio.run(server.bang_luong_luu(1, Req({"tham_so": {}, "thang": {"05": [dict(a_nhap, so_npt=9)]}}), 2025))
    assert out["thang"]["05"][0]["so_npt"] == 2
    # kế hoạch chi phí cả năm: pool đã có số NPT theo tháng
    hd_kh = hd_nv + []
    pool = lambda t: server._luong_dong_tu_nhan_vien(hd_nv, rows_nv, 0, 2025, int(t), ds)
    assert [x["so_npt"] for x in pool("05")] == [2.0, 1.0] and [x["so_npt"] for x in pool("10")] == [1.0, 0.0]
    print("PASS 2: Bảng Lương tự tính giảm trừ người phụ thuộc theo danh sách (ghi đè số nhập tay; chưa có danh sách thì giữ số nhập tay); nạp + kế hoạch theo tháng.")

    # ===== 3: kết xuất QT TNCN dùng danh sách để lập 05-3 =====
    class Row(dict):
        def keys(self): return list(super().keys())
    thang_tinh = {t: server._luong_tinh_thang(rs, TS, t, 2025) for t, rs in
                  {"%02d" % t: [dict(a_nhap, so_npt=server._luong_so_npt_thang(ds, "1", "Hồ Thị A", 2025, t)), dict(b_nhap, so_npt=server._luong_so_npt_thang(ds, "", "Trần Thị B", 2025, t))] for t in range(1, 13)}.items()}
    tong = server._luong_qt_tong_hop(TS, thang_tinh, hd_nv, rows_nv, ds, 2025)
    g = {p["ten"]: p for p in tong["g1"]}
    assert g["Hồ Thị A"]["ct16"] == 2 and g["Trần Thị B"]["ct16"] == 1
    assert g["Hồ Thị A"]["ct17"] == 12 * 11_000_000 + (12 + 6) * 4_400_000, "Giảm trừ: bản thân 12 tháng + cha/mẹ 12 tháng + con 6 tháng"
    assert g["Trần Thị B"]["ct17"] == 12 * 11_000_000 + 6 * 4_400_000
    e = {(x["ten"], x["npt_ten"]): x for x in tong["npt"]}
    assert set(e) == {("Hồ Thị A", "Hồ Quang Khải"), ("Hồ Thị A", "Hồ Con Một"), ("Trần Thị B", "Trần Con Hai")}
    assert (e[("Hồ Thị A", "Hồ Quang Khải")]["tu"], e[("Hồ Thị A", "Hồ Quang Khải")]["den"]) == ("01", "12") and (e[("Hồ Thị A", "Hồ Con Một")]["tu"], e[("Hồ Thị A", "Hồ Con Một")]["den"]) == ("04", "09")
    assert (e[("Trần Thị B", "Trần Con Hai")]["tu"], e[("Trần Thị B", "Trần Con Hai")]["den"]) == ("01", "06")
    assert any("CCCD/số định danh" in c and "Hồ Con Một" in c for c in tong["canh_bao"]) and any("Vợ/chồng" in c for c in tong["canh_bao"]), "Cảnh báo thiếu CCCD NPT + quan hệ chưa có mã HTKK"
    assert not any("dòng tạm" in c for c in tong["canh_bao"])
    tong["so_nguoi_khai"] = 2
    comp = Row({"ten": "CÔNG TY THỬ", "mst": "0318712827", "dia_chi": "x", "ma_cqt_noi_nop": "70123", "ten_cqt_noi_nop": "CQT", "nguoi_ky": "K"})
    xml, chinh, thay = server._luong_qt_xml(comp, 2025, tong, "K", datetime.date(2026, 4, 1))
    root = ET.fromstring(xml.encode("utf-8"))
    ds53 = root.findall(".//t:PLuc_05_3_BK_QTT/t:BKeTTinNPT", NS)
    v = lambda el, tag: el.find("t:" + tag, NS)
    assert len(ds53) == 3
    cha = next(x for x in ds53 if v(x, "ct09").text == "Hồ Quang Khải")
    assert v(cha, "ct07").text == "Hồ Thị A" and v(cha, "ct08").text == "001175007514" and v(cha, "ct10").text == "1948-03-10" and v(cha, "ct11").text == "034048001696" == v(cha, "ct13").text
    assert v(cha, "ct14_ma").text == "03" and v(cha, "ct14_ten").text == "Cha/mẹ" and v(cha, "ct15").text == "01/2025" and v(cha, "ct16").text == "12/2025"
    con = next(x for x in ds53 if v(x, "ct09").text == "Hồ Con Một")
    assert v(con, "ct14_ma").text == "01" and v(con, "ct14_ten").text == "Con" and v(con, "ct15").text == "04/2025" and v(con, "ct16").text == "09/2025"
    assert v(con, "ct11").attrib.get("{http://www.w3.org/2001/XMLSchema-instance}nil") == "true", "Chưa có CCCD -> nil như mẫu HTKK"
    vc = next(x for x in ds53 if v(x, "ct09").text == "Trần Con Hai")
    assert v(vc, "ct14_ma").text is None and v(vc, "ct14_ten").text == "Vợ/chồng", "Quan hệ chưa có mã HTKK đã xác nhận -> để trống mã"
    assert chinh["ct22"] == 3 and len(ds53) == chinh["ct22"]
    print("PASS 3: kết xuất QT TNCN dùng danh sách người phụ thuộc lập 05-3 (họ tên, ngày sinh, CCCD, quan hệ, từ/đến tháng theo các tháng có lương); giảm trừ khớp.")

    # ===== 4: người phụ thuộc chỉ tính các tháng người lao động có trên bảng lương =====
    thang_ngan = {"%02d" % t: thang_tinh["%02d" % t][:1] for t in range(3, 8)}          # A chỉ làm T3–T7
    tong4 = server._luong_qt_tong_hop(TS, thang_ngan, hd_nv, rows_nv, ds, 2025)
    e4 = {x["npt_ten"]: x for x in tong4["npt"]}
    assert (e4["Hồ Quang Khải"]["tu"], e4["Hồ Quang Khải"]["den"]) == ("03", "07") and (e4["Hồ Con Một"]["tu"], e4["Hồ Con Một"]["den"]) == ("04", "07")
    print("PASS 4: bảng kê 05-3 cắt khoảng tháng theo các tháng người lao động có lương.")
finally:
    server.db = _goc
print("\nALL DONE")
