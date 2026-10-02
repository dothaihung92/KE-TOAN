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
assert pa["ct19"] == round(sum(thang_tinh[t][0]["bh_duoc_tru"] for t in thang_tinh)) and pa["ct18"] == 0, "Bảo hiểm ở ct19 (đối chiếu HTKK); ct18 = từ thiện"
assert pa["ct21"] == max(0, pa["ct12"] - pa["ct17"] - pa["ct19"])
assert pa["ct24"] == round(server._luong_qt_thue_nam(pa["ct21"], TS)) > 0
# [22] đã khấu trừ; [24] phải nộp; [25] nộp thừa = [22]-[24]; [26] còn phải nộp = [24]-[22]; [27] miễn (còn phải nộp 1..50.000đ)
assert pa["ct22"] == pa["khau_tru"] == round(sum(thang_tinh[t][0]["thue_tru_luong"] for t in thang_tinh)) and pa["ct23"] == 0
assert pa["ct26"] == max(0, pa["ct24"] - pa["ct22"]) and pa["ct25"] == max(0, pa["ct22"] - pa["ct24"]) and pa["ct27"] == (1 if 0 < pa["ct26"] <= 50000 else 0)
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
for nguon, tong_the in (("ct12", "ct28"), ("ct17", "ct33"), ("ct18", "ct34"), ("ct19", "ct35"), ("ct21", "ct37"), ("ct22", "ct38"), ("ct24", "ct40"), ("ct25", "ct41"), ("ct26", "ct42"), ("ct27", "ct43")):
    assert int(v(p1, tong_the)) == sum(int(v(x, nguon)) for x in p1.findall("t:BKeCTietCNhan", NS)), (nguon, tong_the)
# tờ khai chính = tổng hợp bảng kê (cùng quan hệ như file HTKK thật)
assert chinh["ct16"] == 3 and chinh["ct17"] == 2 and chinh["ct22"] == int(v(p1, "ct32")) == 2
assert chinh["ct23"] == int(v(p1, "ct28")) + int(v(p2, "ct17")) and chinh["ct24"] == chinh["ct23"]
assert chinh["ct28"] == int(v(p2, "ct17")) + sum(int(v(x, "ct12")) for x in p1.findall("t:BKeCTietCNhan", NS) if int(v(x, "ct22")) > 0)
assert chinh["ct31"] == chinh["ct32"] == int(v(p2, "ct21")) + int(v(p1, "ct38")) and chinh["ct18"] == 1 + sum(1 for x in p1.findall("t:BKeCTietCNhan", NS) if int(v(x, "ct22")) > 0)
assert thay == {"ct35": 2, "ct36": int(v(p1, "ct38")), "ct37": int(v(p1, "ct39")), "ct38": int(v(p1, "ct40")), "ct39": int(v(p1, "ct41")), "ct40": int(v(p1, "ct42")), "ct41": int(v(p1, "ct43"))}
assert len(p3.findall("t:BKeTTinNPT", NS)) == 2 and v(p3.findall("t:BKeTTinNPT", NS)[0], "ct15") == "01/2025"
print("PASS 4: XML đúng cấu trúc thẻ HTKK, MST = CCCD, tất cả ủy quyền, tổng bảng kê ↔ tờ khai chính khớp.")

# ===== 5: KHÔNG phát sinh 05-2/05-3 -> KHÔNG xuất 2 phụ lục đó (HTKK tự xuất như vậy, kể cả khi tab vẫn hiện; dòng rỗng bị HTKK báo "Cấu trúc tờ khai xml nhập vào không hợp lệ") =====
tong5 = server._luong_qt_tong_hop(TS, {t: v_ for t, v_ in thang_tinh.items()}, nv_hd, nv_rows)
tong5["g2"], tong5["npt"], tong5["so_nguoi_khai"] = [], [], 2
xml5, chinh5, thay5 = server._luong_qt_xml(comp, 2025, tong5, "", datetime.date(2026, 4, 1))
r5 = ET.fromstring(xml5.encode("utf-8"))
assert [c.tag.split("}")[1] for c in r5.find(".//t:PLuc", NS)] == ["PLuc_05_1_BK_QTT"], "Chỉ có 05-1 như file HTKK tự xuất"
assert "PLuc_05_2_BK_QTT" not in xml5 and "PLuc_05_3_BK_QTT" not in xml5 and "BKeTTinNPT" not in xml5
assert chinh5["ct16"] == 2 and chinh5["ct23"] == int(r5.find(".//t:PLuc_05_1_BK_QTT/t:ct28", NS).text), "Tờ khai chính không lệch"
tong5b = {"g1": [], "g2": [], "npt": [], "canh_bao": [], "so_nguoi": 0, "so_nguoi_khai": 0}
x5b, c5b, t5b = server._luong_qt_xml(comp, 2025, tong5b, "", datetime.date(2026, 4, 1))
r5b = ET.fromstring(x5b.encode("utf-8"))
assert [c.tag.split("}")[1] for c in r5b.find(".//t:PLuc", NS)] == ["PLuc_05_1_BK_QTT"] and all(int(v_) == 0 for v_ in c5b.values())
# chỉ có 05-3 (có NPT nhưng không có người nào bị khấu trừ 10%) -> 05-1 + 05-3, không có 05-2
tong5c = dict(tong5, npt=tong["npt"])
r5c = ET.fromstring(server._luong_qt_xml(comp, 2025, tong5c, "", datetime.date(2026, 4, 1))[0].encode("utf-8"))
assert [c.tag.split("}")[1] for c in r5c.find(".//t:PLuc", NS)] == ["PLuc_05_1_BK_QTT", "PLuc_05_3_BK_QTT"]
print("PASS 5: không phát sinh -> không xuất 05-2/05-3 (như HTKK), có dữ liệu mới xuất phụ lục tương ứng, tờ khai chính không lệch.")

# ===== 5b: SO KHỚP file HTKK thật (đã ẩn danh: tests/fixtures/htkk_05qtt_tncn_1nguoi_mau.xml): cùng dữ liệu -> XML giống HỆT từng thẻ/giá trị (trừ ttinNhaCCapDVu) =====
ref = ET.parse(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "htkk_05qtt_tncn_1nguoi_mau.xml")).getroot()
def phang(root):
    kq = []
    def duyet(e, duong):
        p_ = duong + "/" + e.tag.split("}")[-1]
        if len(e) == 0:
            kq.append((p_, (e.text or "").strip()))
        for c_ in e:
            duyet(c_, p_)
    duyet(root, "")
    return kq
comp_m = Row({"ten": "CÔNG TY TNHH MẪU", "mst": "0300000001", "dia_chi": "1 Đường Mẫu", "ma_cqt_noi_nop": "70123", "ten_cqt_noi_nop": "Thuế cơ sở 12 Thành phố Hồ Chí Minh", "nguoi_ky": "NGUYỄN VĂN KÝ"})
nnt_m = {"ten_xa": "Phường An Phú Đông", "ma_xa": "70123098", "ten_tinh": "Thành phố Hồ Chí Minh", "ma_tinh": "701"}
nguoi = {"ma": "2", "ten": "Nguyễn Văn A", "cccd": "000000000001", "ct12": 63_720_000, "ct16": 0, "ct17": 132_000_000, "ct18": 0, "ct19": 6_690_600, "ct21": 0, "ct22": 0, "ct24": 0, "ct25": 0, "ct26": 0, "ct27": 0, "khau_tru": 0}
xml_m, ch_m, th_m = server._luong_qt_xml(comp_m, 2025, {"g1": [nguoi], "g2": [], "npt": [], "canh_bao": [], "so_nguoi": 1, "so_nguoi_khai": 1}, "NGUYỄN VĂN KÝ", datetime.date(2026, 10, 1))
a_, b_ = phang(ref), phang(ET.fromstring(xml_m.encode("utf-8")))
assert len(a_) == len(b_) == 110, "Mọi thẻ khớp file HTKK (HTKK không xuất phụ lục trống)"
khac = [(x, y) for x, y in zip(a_, b_) if x != y and not x[0].endswith("ttinNhaCCapDVu")]
# Khác duy nhất ngoài ttinNhaCCapDVu: phường/xã — HTKK ghi mã/tên PHƯỜNG của người dùng chọn; phần mềm dùng mã/tên cơ quan thuế đã khai báo ở "Sửa công ty"
assert [x[0].split("/")[-1] for x, y in khac] == ["tenXaNNT", "maXaNNT"], khac
assert dict((x[0].split("/")[-1], y[1]) for x, y in khac) == {"tenXaNNT": "Thuế cơ sở 12 Thành phố Hồ Chí Minh", "maXaNNT": "70123"}
print("PASS 5b: cùng dữ liệu -> XML giống file HTKK thật từng thẻ/giá trị (BH ở ct19, ct09a_ma=03, tỉnh) ; chỉ khác phường/xã (lấy theo CQT đã khai báo).")

# ===== 5c: NNT lấy theo thông tin công ty đã nhập: tỉnh/thành suy từ mã + tên CQT =====
assert server._luong_tinh_tu_ten_cqt("Thuế cơ sở 12 Thành phố Hồ Chí Minh") == "Thành phố Hồ Chí Minh" and server._luong_tinh_tu_ten_cqt("Thuế cơ sở 10 tỉnh Lâm Đồng") == "Tỉnh Lâm Đồng" and server._luong_tinh_tu_ten_cqt("") == ""
rdp = ET.fromstring(xml_m.encode("utf-8"))
assert rdp.find(".//t:NNT/t:tenTinhNNT", NS).text == "Thành phố Hồ Chí Minh" and rdp.find(".//t:NNT/t:maTinhNNT", NS).text == "701"
assert rdp.find(".//t:NNT/t:dchiNNT", NS).text == "1 Đường Mẫu" and rdp.find(".//t:NNT/t:maXaNNT", NS).text == "70123"
print("PASS 5c: NNT theo thông tin công ty đã nhập (địa chỉ, mã/tên CQT); tỉnh/thành suy từ CQT.")

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
    from urllib.parse import unquote as _uq
    assert "phường/xã" not in _uq(resp.headers["x-canh-bao"]), "Không còn yêu cầu nạp phường/xã"
    cb = _uq(resp.headers["x-canh-bao"])
    assert "Không có phụ lục 05-2" in cb or "người phụ thuộc" in cb
    assert os.path.basename(resp.path) == "0318712827000-05_QTT_TNCN_TT80-Y2025-L00.xml"
    assert _uq(resp.headers["x-ten-file"]) == "0318712827000-05_QTT_TNCN_TT80-Y2025-L00.xml"
    assert all(x.startswith("ℹ") for x in _uq(resp.headers["x-canh-bao"]).split(" | ") if "hụ lục 05-" in x), "Ghi chú phụ lục trống chỉ là thông tin (ℹ), không phải cảnh báo"
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

# ===== 7: cột thuế 05-1 đúng thứ tự: [22] đã khấu trừ, [24] phải nộp, [25] nộp thừa, [26] còn phải nộp, [27] miễn (còn phải nộp <= 50.000đ); tổng sang tờ khai chính =====
def dong_t(ma, thue_thang):
    return {"ma": ma, "ten": "NV " + ma, "tn_chiu_thue": 20_000_000, "bh_duoc_tru": 1_000_000, "giam_tru_ban_than": 15_500_000, "tien_giam_tru_npt": 0, "thue_tru_luong": thue_thang, "so_npt": 0}
ts7 = server._luong_chuan_tham_so(None, 2026)
tt7 = {t: [dong_t("A", 100_000), dong_t("B", 300_000), dong_t("C", 0)] for t in server._LUONG_THANG}
nv_h = ["Mã NV", "Họ và tên", "CCCD"]
nv_r = [["A", "NV A", "000000000001"], ["B", "NV B", "000000000002"], ["C", "NV C", "000000000003"]]
tg = server._luong_qt_tong_hop(ts7, tt7, nv_h, nv_r, None, 2026)
by = {p["ma"]: p for p in tg["g1"]}
ct24 = by["A"]["ct24"]
assert ct24 > 0 and by["A"]["ct21"] == 20_000_000 * 12 - 15_500_000 * 12 - 1_000_000 * 12
a, b, c = by["A"], by["B"], by["C"]
assert a["ct22"] == 1_200_000 and a["ct24"] == ct24 and a["ct25"] == max(0, 1_200_000 - ct24) and a["ct26"] == max(0, ct24 - 1_200_000)
assert b["ct22"] == 3_600_000 and b["ct25"] == 3_600_000 - ct24 and b["ct26"] == 0 and b["ct27"] == 0, "khấu trừ nhiều hơn phải nộp -> NỘP THỪA ở [25], không phải còn phải nộp"
assert c["ct22"] == 0 and c["ct26"] == ct24 and c["ct25"] == 0
tong7 = dict(tg, so_nguoi_khai=3)
comp7 = Row({"ten": "CT", "mst": "0300000001", "dia_chi": "x", "ma_cqt_noi_nop": "70123", "ten_cqt_noi_nop": "Thuế cơ sở 12", "nguoi_ky": "K"})
x7, ch7, th7 = server._luong_qt_xml(comp7, 2026, tong7, "K", datetime.date(2026, 10, 2))
assert th7["ct36"] == 1_200_000 + 3_600_000 and th7["ct38"] == 3 * ct24 and th7["ct39"] == b["ct25"] and th7["ct40"] == a["ct26"] + c["ct26"], th7
r7 = ET.fromstring(x7.encode("utf-8"))
nb = {x.find("t:ct07", NS).text: x for x in r7.findall(".//t:PLuc_05_1_BK_QTT/t:BKeCTietCNhan", NS)}
assert nb["NV B"].find("t:ct22", NS).text == "3600000" and nb["NV B"].find("t:ct25", NS).text == str(3_600_000 - ct24)
# người còn phải nộp nhỏ (<= 50.000đ) được đánh dấu miễn [27]=1
tt8 = {t: [dong_t("A", 0)] for t in server._LUONG_THANG}
for t in tt8:
    tt8[t][0]["tn_chiu_thue"] = 16_550_000          # tính ra thuế năm rất nhỏ
g8 = server._luong_qt_tong_hop(ts7, tt8, nv_h, nv_r, None, 2026)["g1"][0]
assert 0 < g8["ct26"] <= 50000 and g8["ct27"] == 1 and g8["ct25"] == 0, g8
print("PASS 7: 05-1: [22] đã khấu trừ, [24] phải nộp, [25] nộp thừa, [26] còn phải nộp, [27] miễn; tờ khai chính ct36..ct41 khớp tổng.")
print("\nALL DONE")
