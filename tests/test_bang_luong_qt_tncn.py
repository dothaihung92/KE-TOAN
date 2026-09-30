import os
import sys
import json
import sqlite3
import tempfile
import asyncio
import datetime
import xml.etree.ElementTree as ET

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server
from fastapi import HTTPException

# Yêu cầu: kết xuất XML quyết toán TNCN năm (05/QTT-TNCN, TT80/2021) cho HTKK, lập từ Bảng Lương + Danh Sách Nhân Viên; mã số thuế cá nhân = số CCCD;
# mặc định tất cả cá nhân ỦY QUYỀN quyết toán thay. Cấu trúc/chỉ tiêu đối chiếu theo file XML HTKK thật của người dùng.
NS = {"t": "http://kekhaithue.gdt.gov.vn/TKhaiThue"}
TS = server._luong_chuan_tham_so(None, 2025)

# ===== 1: thuế cả năm theo biểu lũy tiến (mức tháng x 12) — đúng 2 số thật trong file HTKK mẫu của người dùng =====
assert round(server._luong_qt_thue_nam(156_840_000, TS)) == 14_526_000      # 60tr x5% + 60tr x10% + 36,84tr x15%
assert round(server._luong_qt_thue_nam(63_739_800, TS)) == 3_373_980
assert server._luong_qt_thue_nam(0, TS) == 0 and server._luong_qt_thue_nam(-5, TS) == 0
print("PASS 1: thuế TNCN cả năm khớp số thật trong file HTKK mẫu (14.526.000 / 3.373.980).")

# ===== 2: tổng hợp bảng lương cả năm theo từng người =====
base = {"chuc_vu": "KD", "tien_com": 730_000, "muc_xang": 0, "muc_dt": 0, "trang_phuc": 0}
nv_hd = ["Mã NV", "Họ và tên", "CCCD"]
nv_rows = [["1", "Hồ Thị A", "001175007514"], ["2", "Trần Thị B", "079187022032"], ["3", "Làm thời vụ", "079072040223"]]


def nam_luong(d, thang=range(1, 13)):
    return {"%02d" % t: [d] for t in thang}


rows_nhap = {}
a = dict(base, ma="1", ten="Hồ Thị A", luong_cb=30_000_000, so_npt=2, dong_bh=1, thuong_bh=0)
b = dict(base, ma="2", ten="Trần Thị B", luong_cb=8_000_000, so_npt=0, dong_bh=1)
tv = dict(base, ma="3", ten="Làm thời vụ", luong_cb=20_000_000, dong_bh=0, ngay_lam=10)
for t in range(1, 13):
    k = "%02d" % t
    rows_nhap[k] = [a, b] + ([tv] if t in (3, 4) else [])
thang_tinh = {t: server._luong_tinh_thang(r, TS, t, 2025) for t, r in rows_nhap.items()}
tong = server._luong_qt_tong_hop(TS, thang_tinh, nv_hd, nv_rows)
g1 = {p["ten"]: p for p in tong["g1"]}
assert set(g1) == {"Hồ Thị A", "Trần Thị B"}, "Người làm thời vụ chỉ vào 05-2, không vào 05-1"
pa = g1["Hồ Thị A"]
tn_a = sum(thang_tinh[t][0]["tn_chiu_thue"] for t in thang_tinh)
assert pa["ct12"] == round(tn_a) and pa["cccd"] == "001175007514" and pa["ct16"] == 2
assert pa["ct17"] == 12 * (11_000_000 + 2 * 4_400_000) == 237_600_000, "Giảm trừ = 12 tháng x (bản thân + 2 người phụ thuộc)"
assert pa["ct18"] == round(sum(thang_tinh[t][0]["bh_duoc_tru"] for t in thang_tinh))
assert pa["ct21"] == max(0, pa["ct12"] - pa["ct17"] - pa["ct18"])
assert pa["ct24"] == round(server._luong_qt_thue_nam(pa["ct21"], TS)) > 0
assert pa["ct25"] == round(sum(thang_tinh[t][0]["thue_tru_luong"] for t in thang_tinh))
assert pa["ct26"] == max(0, pa["ct24"] - pa["ct25"]) and pa["ct27"] == max(0, pa["ct25"] - pa["ct24"])
pb = g1["Trần Thị B"]
assert pb["ct24"] == 0 and pb["ct26"] == 0 and pb["ct17"] == 132_000_000 and pb["ct16"] == 0, "Lương thấp dưới mức giảm trừ -> không thuế"
assert len(tong["g2"]) == 1 and tong["g2"][0]["ten"] == "Làm thời vụ" and tong["g2"][0]["ct15"] > 0
assert tong["g2"][0]["ct11"] == round(sum(thang_tinh[t][2]["tn_chiu_thue"] for t in ("03", "04")))
assert len(tong["npt"]) == 2 and tong["npt"][0]["tu"] == "01" and tong["npt"][0]["den"] == "12"
assert any("người phụ thuộc" in c for c in tong["canh_bao"]) and tong["so_nguoi"] == 3
print("PASS 2: tổng hợp cả năm: 05-1 (thu nhập, giảm trừ, BH, thuế lũy tiến năm, đã khấu trừ, còn nộp/nộp thừa), 05-2 (khấu trừ 10%), người phụ thuộc.")

# ===== 3: thiếu CCCD -> cảnh báo; khớp theo họ tên không dấu khi Mã NV khác =====
tong2 = server._luong_qt_tong_hop(TS, thang_tinh, nv_hd, [["9", "Ho Thi A", "001175007514"], ["2", "Trần Thị B", ""]])
assert {p["ten"]: p["cccd"] for p in tong2["g1"]} == {"Hồ Thị A": "001175007514", "Trần Thị B": ""}
assert any("Chưa có số CCCD" in c and "Trần Thị B" in c for c in tong2["canh_bao"])
print("PASS 3: CCCD khớp theo Mã NV hoặc họ tên không dấu; thiếu thì cảnh báo.")

# ===== 4: XML: đúng cấu trúc thẻ như file HTKK thật, chỉ tiêu tờ khai chính = tổng các bảng kê =====
class Comp(dict):
    pass
comp = {"ten": "CÔNG TY TNHH THỬ", "mst": "0318712827", "dia_chi": "1 Đường A", "ma_cqt_noi_nop": "70123", "ten_cqt_noi_nop": "Thuế cơ sở 12 TP.HCM", "nguoi_ky": "NGUYỄN A"}
class Row(dict):
    def keys(self): return list(super().keys())
comp = Row(comp)
tong["so_nguoi_khai"] = 3
xml, chinh, thay = server._luong_qt_xml(comp, 2025, tong, "NGUYỄN A", datetime.date(2026, 4, 1))
root = ET.fromstring(xml.encode("utf-8"))
q = lambda path: root.find(path, NS)
assert q(".//t:maTKhai").text == "953" and q(".//t:loaiTKhai").text == "C" and q(".//t:soLan").text == "0" and q(".//t:kieuKy").text == "Y" and q(".//t:kyKKhai").text == "2025"
assert q(".//t:kyKKhaiTuThang").text == "01/2025" and q(".//t:kyKKhaiDenThang").text == "12/2025" and q(".//t:NNT/t:mst").text == "0318712827" and q(".//t:mst_cu").text == "0318712827"
ten_the = lambda el: [c.tag.split("}")[1] for c in el]
ct = q(".//t:CTieuTKhaiChinh")
assert ten_the(ct.find("t:NVuKhauTruThue", NS)) == ["ct%d" % i for i in range(16, 35)] and ten_the(ct.find("t:NVuQToanThay", NS)) == ["ct%d" % i for i in range(35, 42)]
# thứ tự thẻ của 1 cá nhân trong 05-1 / 05-2 / 05-3 đúng như file HTKK thật
ch1 = ["coDieuChinhSoLieu", "ct07", "ct08", "nguoiVNSongNN_NguoiNN", "ct09a_ma", "ct09a_ten", "ct09", "ct10", "ct11", "ct12", "ct13", "ct14", "ct15", "ct15.1"] + ["ct%d" % i for i in range(16, 28)]
ch2 = ["coDieuChinhSoLieu", "ct07", "ct08", "nguoiVNSongNN_NguoiNN", "ct09a_ma", "ct09a_ten", "ct09", "ct10", "ct11", "ct12", "ct13", "ct14", "ct14.1", "ct15", "ct16"]
ch3 = ["ct07", "ct08", "ct09", "ct10", "ct11", "nguoiVNSongNN_NguoiNN", "ct12_ma", "ct12_ten", "ct13", "ct14_ma", "ct14_ten", "ct15", "ct16"]
p1, p2, p3 = (q(".//t:PLuc_05_1_BK_QTT"), q(".//t:PLuc_05_2_BK_QTT"), q(".//t:PLuc_05_3_BK_QTT"))
assert all(ten_the(x) == ch1 for x in p1.findall("t:BKeCTietCNhan", NS)) and all(ten_the(x) == ch2 for x in p2.findall("t:BKeCTietCNhan", NS)) and all(ten_the(x) == ch3 for x in p3.findall("t:BKeTTinNPT", NS))
assert [c.tag.split("}")[1] for c in p1 if not c.tag.endswith("BKeCTietCNhan")] == ["ct28", "ct29", "ct30", "ct31", "ct31.1", "ct32", "ct33", "ct34", "ct35", "ct36", "ct37", "ct38", "ct39", "ct40", "ct41", "ct42", "ct43"]
assert [c.tag.split("}")[1] for c in p2 if not c.tag.endswith("BKeCTietCNhan")] == ["ct17", "ct18", "ct19", "ct20", "ct20.1", "ct21", "ct22"]
v = lambda el, tag: el.find("t:" + tag, NS).text
ca = p1.findall("t:BKeCTietCNhan", NS)[0]
assert v(ca, "ct07") == "Hồ Thị A" and v(ca, "ct08") == "001175007514" == v(ca, "ct09") and v(ca, "ct10") == "1" and v(ca, "ct09a_ten") == "Thẻ CCCD/Số định danh cá nhân", "MST = CCCD; ủy quyền = 1"
assert all(v(x, "ct10") == "1" for x in p1.findall("t:BKeCTietCNhan", NS)), "Mọi cá nhân mặc định ỦY QUYỀN quyết toán thay"
# tổng của PLuc = tổng các dòng
for nguon, tong_the in (("ct12", "ct28"), ("ct17", "ct33"), ("ct18", "ct34"), ("ct21", "ct37"), ("ct24", "ct40"), ("ct25", "ct41"), ("ct26", "ct42"), ("ct27", "ct43")):
    assert int(v(p1, tong_the)) == sum(int(v(x, nguon)) for x in p1.findall("t:BKeCTietCNhan", NS)), (nguon, tong_the)
# tờ khai chính = tổng hợp bảng kê (cùng quan hệ như file HTKK thật)
assert chinh["ct16"] == 3 and chinh["ct17"] == 2 and chinh["ct22"] == int(v(p1, "ct32")) == 2
assert chinh["ct23"] == int(v(p1, "ct28")) + int(v(p2, "ct17")) and chinh["ct24"] == chinh["ct23"]
assert chinh["ct28"] == int(v(p2, "ct17")) + sum(int(v(x, "ct12")) for x in p1.findall("t:BKeCTietCNhan", NS) if int(v(x, "ct25")) > 0)
assert chinh["ct31"] == chinh["ct32"] == int(v(p2, "ct21")) + int(v(p1, "ct41")) and chinh["ct18"] == 1 + sum(1 for x in p1.findall("t:BKeCTietCNhan", NS) if int(v(x, "ct25")) > 0)
assert thay == {"ct35": 2, "ct36": 0, "ct37": 0, "ct38": int(v(p1, "ct40")), "ct39": int(v(p1, "ct41")), "ct40": int(v(p1, "ct42")), "ct41": int(v(p1, "ct43"))}
assert len(p3.findall("t:BKeTTinNPT", NS)) == 2 and v(p3.findall("t:BKeTTinNPT", NS)[0], "ct15") == "01/2025"
print("PASS 4: XML đúng cấu trúc thẻ HTKK, MST = CCCD, tất cả ủy quyền, tổng bảng kê ↔ tờ khai chính khớp.")

# ===== 5: không có người thời vụ/phụ thuộc -> bỏ phụ lục 05-2/05-3 =====
tong5 = server._luong_qt_tong_hop(TS, {t: v_ for t, v_ in thang_tinh.items()}, nv_hd, nv_rows)
tong5["g2"], tong5["npt"], tong5["so_nguoi_khai"] = [], [], 2
xml5, _c, _t = server._luong_qt_xml(comp, 2025, tong5, "", datetime.date(2026, 4, 1))
r5 = ET.fromstring(xml5.encode("utf-8"))
assert r5.find(".//t:PLuc_05_2_BK_QTT", NS) is None and r5.find(".//t:PLuc_05_3_BK_QTT", NS) is None and r5.find(".//t:PLuc_05_1_BK_QTT", NS) is not None
print("PASS 5: không có 05-2/05-3 thì bỏ phụ lục tương ứng.")

# ===== 6: API: lấy bảng lương đã lưu + Danh Sách Nhân Viên + thông tin công ty; trả file XML =====
_duong = tempfile.mktemp(suffix=".db")
def _db_tam():
    c = sqlite3.connect(_duong)
    c.row_factory = sqlite3.Row
    return c
_goc_db, _goc_dl = server.db, server.DOWNLOAD_DIR
server.db = _db_tam
server.DOWNLOAD_DIR = tempfile.mkdtemp()
try:
    c0 = _db_tam()
    c0.execute("CREATE TABLE companies (id INTEGER PRIMARY KEY, ten TEXT, mst TEXT, dia_chi TEXT, ma_cqt_noi_nop TEXT, ten_cqt_noi_nop TEXT, nguoi_ky TEXT)")
    c0.execute("INSERT INTO companies VALUES (1,'CÔNG TY TNHH THỬ','0318712827','1 Đường A','70123','Thuế cơ sở 12','')")
    c0.execute("CREATE TABLE nhap_lieu (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, loai TEXT, header_json TEXT, rows_json TEXT, updated_at TEXT, UNIQUE(company_id, loai))")
    c0.execute("INSERT INTO nhap_lieu (company_id, loai, header_json, rows_json) VALUES (1,'nv',?,?)", (json.dumps(nv_hd), json.dumps(nv_rows)))
    c0.commit(); c0.close()
    server._luong_doc_nam = lambda cid, nam: (TS, rows_nhap if nam == 2025 else {}, "", [2025])

    class Req:
        def __init__(self, b): self._b = b
        async def json(self): return self._b
    resp = asyncio.run(server.bang_luong_ket_xuat_qt_tncn(1, Req({"nam": 2025, "nguoi_ky": "NGUYỄN NGỌC PHƯƠNG THẢO"})))
    assert os.path.basename(resp.path) == "0318712827000-05_QTT_TNCN_TT80-Y2025-L00.xml"
    raw = open(resp.path, encoding="utf-8").read()
    assert raw.startswith("﻿<?xml") and "<nguoiKy>NGUYỄN NGỌC PHƯƠNG THẢO</nguoiKy>" in raw and "<maCQTNoiNop>70123</maCQTNoiNop>" in raw
    r6 = ET.fromstring(raw.lstrip("﻿").encode("utf-8"))
    assert r6.find(".//t:NNT/t:tenNNT", NS).text == "CÔNG TY TNHH THỬ" and len(r6.findall(".//t:PLuc_05_1_BK_QTT/t:BKeCTietCNhan", NS)) == 2
    from urllib.parse import unquote
    assert "người phụ thuộc" in unquote(resp.headers["x-canh-bao"]) and resp.headers["x-so-nguoi"] == "3"
    # người ký được lưu cho lần sau
    assert _db_tam().execute("SELECT nguoi_ky FROM companies WHERE id=1").fetchone()[0] == "NGUYỄN NGỌC PHƯƠNG THẢO"
    resp2 = asyncio.run(server.bang_luong_ket_xuat_qt_tncn(1, Req({"nam": 2025})))
    raw2 = open(resp2.path, encoding="utf-8").read()
    assert "<nguoiKy>NGUYỄN NGỌC PHƯƠNG THẢO</nguoiKy>" in raw2
    # Không truyền gì: người ký + CQT + địa chỉ lấy hết theo thông tin công ty đã nhập ban đầu
    assert "<tenCQTNoiNop>Thuế cơ sở 12</tenCQTNoiNop>" in raw2 and "<maCQTNoiNop>70123</maCQTNoiNop>" in raw2 and "<dchiNNT>1 Đường A</dchiNNT>" in raw2
    assert "chưa khai báo" not in __import__("urllib.parse", fromlist=["unquote"]).unquote(resp2.headers["x-canh-bao"])
    # công ty đã nhập sẵn người ký từ đầu -> dùng luôn, không cần truyền
    _c = _db_tam(); _c.execute("UPDATE companies SET nguoi_ky='HỒ THỊ CẨM VÂN' WHERE id=1"); _c.commit(); _c.close()
    assert "<nguoiKy>HỒ THỊ CẨM VÂN</nguoiKy>" in open(asyncio.run(server.bang_luong_ket_xuat_qt_tncn(1, Req({"nam": 2025}))).path, encoding="utf-8").read()
    for loi_nam in (2024,):
        try:
            asyncio.run(server.bang_luong_ket_xuat_qt_tncn(1, Req({"nam": loi_nam})))
            raise SystemExit("phải báo lỗi: năm chưa có bảng lương")
        except HTTPException as e:
            assert e.status_code == 404
finally:
    server.db, server.DOWNLOAD_DIR = _goc_db, _goc_dl
print("PASS 6: API kết xuất: file XML đúng tên (MST+000-05_QTT_TNCN_TT80-Y2025-L00), người ký nhớ cho lần sau, năm chưa có lương báo lỗi.")
print("\nALL DONE")
