import os, sys, asyncio, sqlite3, datetime, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server, van_ban_lao_dong as v

# Thử việc theo HỢP ĐỒNG THỬ VIỆC RIÊNG (người thử việc THẬT): cột "Thử việc từ/đến" ở Danh Sách NV -> Bảng Lương không đóng BHXH trong thời gian thử việc
# (dưới 3 tháng: khấu trừ 10% thuế TNCN -> phụ lục 05-2; từ 3 tháng: tính lũy tiến), BHXH bắt đầu từ NGÀY SAU khi hết thử việc; mẫu hợp đồng thử việc + cảnh báo Điều 25/26.
H = server.NV_HEADERS
def R(**k):
    r = [''] * len(H)
    for a, b in k.items():
        r[H.index(a)] = b
    return r
D = datetime.date
assert server._luong_thu_viec_khoang('01/03/2026', '31/03/2026') == (D(2026, 3, 1), D(2026, 3, 31))
assert server._luong_thu_viec_khoang('03/2026', '04/2026') == (D(2026, 3, 1), D(2026, 4, 30)), "chỉ ghi tháng: từ = ngày 1, đến = ngày cuối tháng"
assert server._luong_thu_viec_khoang('01/03/2026', '') == (None, None), "chưa có ngày kết thúc thì không áp dụng"

def mo(tu, den, nam=2026, thang=3, tick='x', vao='03/2026'):
    rows = [R(**{'Mã NV': '1', 'Họ và tên': 'A', 'Đóng BHXH': tick, 'Tháng/Năm vào làm': vao, 'Thử việc từ': tu, 'Thử việc đến': den, 'Lương Cơ bản': 6000000, 'Chức vụ': 'Nhân viên'})]
    return server._luong_dong_tu_nhan_vien(H, rows, 0, nam, thang)[0]
# thử việc 01/03 - 31/03 (dưới 3 tháng): T3 thử việc (không BHXH), T4 đóng BHXH
a3, a4 = mo('01/03/2026', '31/03/2026', thang=3), mo('01/03/2026', '31/03/2026', thang=4)
assert (a3["dong_bh"], a3["thu_viec"]) == (0, 1) and (a4["dong_bh"], a4["thu_viec"]) == (1, 0)
# thử việc 15/03 - 14/04: BHXH bắt đầu 15/04 (còn 16 ngày trong tháng >= 14) -> T4 đóng
b3, b4 = mo('15/03/2026', '14/04/2026', thang=3), mo('15/03/2026', '14/04/2026', thang=4)
assert (b3["dong_bh"], b3["thu_viec"]) == (0, 1) and (b4["dong_bh"], b4["thu_viec"]) == (1, 0)
# hết thử việc ngày 20/04: ngày sau là 21/04 (còn < 14 ngày) -> BHXH từ tháng 5; T4 vẫn là thử việc
c4, c5 = mo('01/03/2026', '20/04/2026', thang=4), mo('01/03/2026', '20/04/2026', thang=5)
assert (c4["dong_bh"], c4["thu_viec"]) == (0, 1) and (c5["dong_bh"], c5["thu_viec"]) == (1, 0)
# thử việc từ 3 tháng trở lên (thu_viec = 2)
d3 = mo('01/03/2026', '30/06/2026', thang=5)
assert (d3["dong_bh"], d3["thu_viec"]) == (0, 2)
# người không tick BHXH và không thử việc: không bị đánh dấu thử việc; người chưa nhập cột: như trước
assert mo('', '', thang=3)["thu_viec"] == 0 and mo('', '', thang=3)["dong_bh"] == 1

# ví dụ người dùng: thử việc 01/2024 - 01/2024, vào làm (bắt đầu đóng BHXH) 02/2024 -> chưa lên bảng lương trước 01/2024; T1 thử việc; từ T2 đóng BHXH
def thang(nam, th, tu='01/2024', den='01/2024', vao='02/2024'):
    r = server._luong_dong_tu_nhan_vien(H, [R(**{'Mã NV': '9', 'Họ và tên': 'Z', 'Đóng BHXH': 'x', 'Tháng/Năm vào làm': vao, 'Thử việc từ': tu, 'Thử việc đến': den, 'Lương Cơ bản': 5310000})], 0, nam, th)
    return (r[0]["dong_bh"], r[0]["thu_viec"]) if r else None
assert thang(2023, 12) is None, "trước tháng thử việc: không có trong bảng lương"
assert thang(2024, 1) == (0, 1) and thang(2024, 2) == (1, 0) and thang(2024, 12) == (1, 0)
assert thang(2024, 1, vao='') == (0, 1) and thang(2024, 2, vao='') == (1, 0), "không ghi tháng vào làm: BHXH từ ngày sau khi hết thử việc"
assert thang(2023, 12, tu='', den='', vao='01/2024') is None and thang(2024, 1, tu='', den='', vao='01/2024') == (1, 0), "không thử việc: lên bảng lương từ tháng vào làm"

TS = server._luong_chuan_tham_so(None, 2026)
tinh = lambda d: server._luong_tinh_dong(dict(d, ngay_lam=26), TS, "03")
t1, t2 = tinh(a3), tinh(d3)
assert t1["thoi_vu"] is True and t1["canh_bao_bh"] is False and t1["bhxh_nld"] == 0 and t1["giam_tru_ban_than"] == 0
assert t1["thue_tncn"] == server._luong_lam_tron(t1["tn_chiu_thue"] * 0.1) and t1["thue_tncn"] > 0, "dưới 3 tháng: khấu trừ 10%"
assert t2["thoi_vu"] is False and t2["canh_bao_bh"] is False and t2["bhxh_nld"] == 0 and t2["giam_tru_ban_than"] > 0, "từ 3 tháng: lũy tiến có giảm trừ, vẫn không BHXH"
# quyết toán TNCN: người thử việc dưới 3 tháng nằm trong phụ lục 05-2
tt = {"03": [t1]}
tong = server._luong_qt_tong_hop(TS, tt, ["Mã NV", "Họ và tên", "CCCD"], [["1", "A", "079090000123"]], None, 2026)
assert any(p["ma"] == "1" for p in tong["g2"]) and not tong["g1"], "thử việc dưới 3 tháng (khấu trừ 10%) -> 05-2"

# cảnh báo thử việc
W = lambda ngay, chuc_vu='Nhân viên kế toán', **k: dict({"ten": "A", "chuc_vu": chuc_vu, "thu_viec_tu": "01/03/2026", "thu_viec_den": (D(2026, 3, 1) + datetime.timedelta(days=ngay - 1)).strftime("%d/%m/%Y")}, **k)
kt = lambda nv, **tc: v.kiem_tra_thu_viec([nv], tc)
assert kt(W(30)) == [] and kt(W(6, 'Bảo vệ')) == []
assert any("06 ngày làm việc" in c["nd"] for c in kt(W(31, 'Bảo vệ'))) and any("06 ngày làm việc" in c["nd"] for c in kt(W(7, 'Lao công')))
assert any(c["muc"] == "canh_bao" and "cao đẳng" in c["nd"] for c in kt(W(45)))
assert any(c["muc"] == "canh_bao" and "người quản lý doanh nghiệp" in c["nd"] for c in kt(W(90)))
assert any(c["muc"] == "loi" and "180 ngày" in c["nd"] for c in kt(W(181)))
assert any(c["muc"] == "loi" and "85%" in c["nd"] for c in kt(W(30), tv_phan_tram=80)) and kt(W(30), tv_phan_tram=85) == []
assert any(c["muc"] == "loi" and "chưa có ngày" in c["nd"] for c in kt({"ten": "B", "chuc_vu": "X"}))
assert kt({"ten": "B", "chuc_vu": "X"}, tv_tu="01/03/2026", tv_den="30/03/2026") == [], "ngày trên form dùng cho người chưa có ngày ở Danh sách"

# mẫu hợp đồng thử việc
CTY = {"ten": "CÔNG TY TNHH THỬ", "mst": "0300000001", "dia_chi": "1 Lê Lợi, Quận 1, Thành phố Hồ Chí Minh", "nguoi_ky": "Hồ Thị Cẩm Vân"}
nv = {"ten": "Lê Văn A", "ma": "5", "chuc_vu": "Nhân viên kế toán", "luong_cb": 6_000_000, "ngay_sinh": "01/01/1990", "dia_chi": "Q1", "cccd": "079090000123", "ngay_cap": "01/01/2021",
      "gioi_tinh": "Nam", "thu_viec_tu": "01/03/2026", "thu_viec_den": "30/03/2026"}
h = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", v.dung_hop_dong_thu_viec(nv, CTY, {"ong_ba_ky": "Bà"}, 0)).replace("&nbsp;", " "))
assert "HỢP ĐỒNG THỬ VIỆC" in h and "Số: 01/HĐTV-2026" in h and "Điều 24 đến Điều 27" in h
assert "30 ngày, từ ngày 01 tháng 03 năm 2026 đến hết ngày 30 tháng 03 năm 2026" in h
assert "5.100.000 đồng/tháng" in h and "Năm triệu một trăm nghìn đồng" in h and "bằng 85% mức lương chính thức" in h and "(6.000.000 đồng/tháng)" in h
assert "không thuộc đối tượng tham gia bảo hiểm xã hội bắt buộc" in h and "Điều 27" in h and "Ông: LÊ VĂN A" in h and "Bà: HỒ THỊ CẨM VÂN" in h
assert "5.400.000 đồng/tháng" in re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", v.dung_hop_dong_thu_viec(nv, CTY, {"tv_phan_tram": 90}, 0)))
assert v.dung_hop_dong_thu_viec_nhieu([nv, nv], CTY, {}).count('<section class="vb-trang">') == 2

# API: loại 'tv' lấy ngày từ Danh Sách NV
conn = sqlite3.connect(":memory:", check_same_thread=False); conn.row_factory = sqlite3.Row
conn.execute("CREATE TABLE companies (id INTEGER, ten TEXT, mst TEXT, dia_chi TEXT, nguoi_ky TEXT)")
conn.execute("INSERT INTO companies VALUES (7, 'CÔNG TY TNHH THỬ', '0300000001', '1 Lê Lợi', 'Hồ Thị Cẩm Vân')")
class K:
    def execute(self, *a): return conn.execute(*a)
    def commit(self): conn.commit()
    def close(self): pass
server.db = lambda: K()
ROWS = [R(**{'Mã NV': 'N1', 'Họ và tên': 'Nguyễn A', 'Chức vụ': 'Nhân viên kế toán', 'CCCD': '079090000123', 'Lương Cơ bản': 7000000, 'Thử việc từ': '01/04/2026', 'Thử việc đến': '30/04/2026'}),
        R(**{'Mã NV': 'N2', 'Họ và tên': 'Trần B', 'Chức vụ': 'Bảo vệ', 'Lương Cơ bản': 5000000, 'Thử việc từ': '01/04/2026', 'Thử việc đến': '30/04/2026'}),
        R(**{'Mã NV': 'N3', 'Họ và tên': 'Lê C', 'Chức vụ': 'Nhân viên', 'Lương Cơ bản': 5000000})]
server.nhap_lieu_get = lambda cid, loai="in": {"header": H, "rows": ROWS} if loai == "nv" else {"header": [], "rows": []}
server._luong_doc_nam = lambda cid, nam: (server._luong_chuan_tham_so(None, nam), {}, "", [nam])
class Req:
    def __init__(self, b): self.b = b
    async def json(self): return self.b
r = asyncio.run(server.van_ban_xem_truoc(7, Req({"loai": "tv", "nam": 2026, "tu": 1, "den": 3})))
assert r["html"].count('<section class="vb-trang">') == 3 and "HỢP ĐỒNG THỬ VIỆC" in r["html"] and "5.950.000 đồng/tháng" in r["html"]
nd = " | ".join(c["nd"] for c in r["canh_bao"])
assert "Trần B (Bảo vệ)" in nd and "06 ngày làm việc" in nd, "bảo vệ thử việc 30 ngày -> cảnh báo"
assert "Lê C: chưa có ngày" in nd, "người chưa có ngày thử việc"
r2 = asyncio.run(server.van_ban_xem_truoc(7, Req({"loai": "tv", "nam": 2026, "tu": 3, "den": 3, "tuy_chon": {"tv_tu": "05/05/2026", "tv_den": "20/05/2026", "tv_phan_tram": "90"}})))
assert "16 ngày, từ ngày 05 tháng 05 năm 2026 đến hết ngày 20 tháng 05 năm 2026" in re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r2["html"])) and "4.500.000 đồng/tháng" in r2["html"]
print("PASS")
