import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import datetime, itertools
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

def extract_fn(name):
    idx = src.index('def ' + name + '(')
    i = src.index(':', idx)
    lines = src[i+1:].split('\n')
    body = []
    started = False
    for ln in lines:
        if ln.strip() == '' and not started:
            body.append(ln); continue
        if ln and not ln[0].isspace() and started:
            break
        if ln.strip():
            started = True
        body.append(ln)
    return src[idx:i+1] + '\n'.join(body)


class FakeHTTPException(Exception):
    def __init__(self, code, msg):
        self.code = code; self.detail = msg
        super().__init__(f"{code}: {msg}")


# Regression test cho _misa_doi_chieu_3_tang() — người dùng báo (kèm ảnh chụp thanh tiến độ vừa
# thêm): "Chạy đối chiếu" kẹt hơn 3 phút, thanh tiến độ đứng yên ở "140/742 đối tượng công nợ (19%)
# — đang xử lý: KL" không nhúc nhích.
#
# Nguyên nhân: mã "KL" (Khách lẻ) dùng CHUNG cho HÀNG NGHÌN khách hàng THẬT KHÁC NHAU không có MST
# (xem _misa_ghi_ban_hang) — CSDL thật có hàng nghìn hóa đơn/khoản thanh toán khác nhau đều gắn
# chung mã "KL", bị _misa_doi_chieu_3_tang() coi là 1 "đối tượng công nợ" DUY NHẤT. Trước đây "KL"
# CHỈ bị loại khỏi Tầng 3 (xem tests/test_tang3_bo_qua_khach_le.py) và khỏi "Ghi bù trừ treo"
# (_misa_ghi_bu_tru_treo) — nhưng KHÔNG bị loại khỏi chính _misa_khop_1_2() (Tầng 1/2/2c)! Với hàng
# nghìn hóa đơn/thanh toán gộp vào 1 "đối tượng" KL, các vòng lặp O(số hóa đơn × số thanh toán) của
# Tầng 1/2c (lặp lại tới 30 vòng ổn định hóa MỖI đối tượng) phải xử lý khối lượng khổng lồ CHỈ CHO
# đúng "đối tượng" KL này — đúng điểm nghẽn "kẹt" người dùng thấy trên thanh tiến độ.
#
# Fix: loại bỏ HẲN "KL" khỏi doi_tuong_hd/doi_tuong_tt NGAY SAU khi nạp dữ liệu — TRƯỚC khi đưa vào
# _misa_khop_1_2() — không chỉ ở Tầng 3 như trước. Kết quả khớp cho "KL" cũng vốn dĩ VÔ NGHĨA (gộp
# nhiều khách khác nhau làm 1), nên loại sớm vừa đúng vừa nhanh hơn nhiều.


# Ca thật (báo cáo "Tổng hợp công nợ phải thu" năm 2025): khách hàng có SỐ DƯ ĐẦU KỲ Nợ (vd HKD DR Nguyên Optic 195.000.001, Nguyễn Văn Thắng 50.000.000),
# KHÔNG phát sinh gì suốt năm, dư cuối kỳ y nguyên. Yêu cầu: số dư đầu kỳ còn treo đến cuối kỳ mà đối tượng không có giao dịch nào -> phần mềm đề xuất
# XỬ LÝ VỀ 0đ luôn (Tầng 3, du_dau_ky=True) — kể cả khoản LỚN (vượt ngưỡng 5.000.000) và không chờ quá hạn.
D = datetime.datetime
DAU_KY = D(2024, 12, 31)
TRONG_KY = D(2025, 6, 15)


class FakeCursor:
    def execute(self, sql, params=()):
        if "/*SO_DU_DAU_KY*/" in sql:
            # sổ chi tiết công nợ (aoid, mã, tên, refid, ngày, Nợ, Có) — để tính SỐ DƯ ĐẦU KỲ RÒNG từng đối tượng
            self._result = [
                ("a1", "DR", "HKD DR NGUYÊN OPTIC", "dk-1", DAU_KY, 195000001, 0),
                ("a2", "TV", "NGUYỄN VĂN THẮNG", "dk-2", DAU_KY, 50000000, 0),
                ("a3", "QM", "BỆNH VIỆN QM", "dk-3", DAU_KY, 36000000, 0),
                ("a3", "QM", "BỆNH VIỆN QM", "bd-3", D(2025, 3, 10), 0, 15000000),                  # a3 có thanh toán TRONG kỳ
                ("a4", "NEW", "KHÁCH MỚI", "hd-4", TRONG_KY, 90000000, 0),                           # phát sinh trong kỳ
                # SH: 3 khoản cũ NHƯNG đã trả bớt trước kỳ -> số dư đầu kỳ RÒNG chỉ 274.556 (không phải 6.5tr tổng các hóa đơn)
                ("a8", "SH", "SHAANXI", "o-1", D(2019, 12, 31), 41400, 0),
                ("a8", "SH", "SHAANXI", "o-2", D(2019, 12, 31), 6233156, 0),
                ("a8", "SH", "SHAANXI", "o-3", D(2020, 6, 1), 0, 6000000),
            ]
        elif "ISNULL(CorrespondingAccountNumber,'') LIKE '111%'" in sql:
            self._result = []
        elif "FROM AccountObjectLedger WHERE AccountNumber LIKE ?" in sql:
            self._result = [
                ("a1", "DR", "", "HKD DR NGUYÊN OPTIC", "dk-1", "SDDK", DAU_KY, DAU_KY, 195000001, "9999"),         # dư đầu kỳ, cả năm không động
                ("a2", "TV", "", "NGUYỄN VĂN THẮNG", "dk-2", "SDDK", DAU_KY, DAU_KY, 50000000, "9999"),             # dư đầu kỳ, cả năm không động
                ("a3", "QM", "", "BỆNH VIỆN QM", "dk-3", "SDDK", DAU_KY, DAU_KY, 36000000, "9999"),                 # dư đầu kỳ NHƯNG có thanh toán trong kỳ
                ("a4", "NEW", "", "KHÁCH MỚI", "hd-4", "BH1", TRONG_KY, TRONG_KY, 90000000, "5111"),                # phát sinh TRONG kỳ, lớn -> không phải dư đầu kỳ
                ("a8", "SH", "", "SHAANXI", "o-1", "SD", D(2019, 12, 31), D(2019, 12, 31), 41400, "9999"),
                ("a8", "SH", "", "SHAANXI", "o-2", "SD", D(2019, 12, 31), D(2019, 12, 31), 6233156, "9999"),
            ]
        elif "FROM BADepositDetail bd JOIN BADeposit b" in sql:
            self._result = [("a3", D(2025, 3, 10), 15000000, "bd-3", "", "", "UNT-3")]       # a3 trả 15tr trong kỳ (1 phần)
        else:
            self._result = []
        return self

    def fetchone(self):
        return self._result[0] if self._result else None

    def fetchall(self):
        return self._result


class FakeConn:
    def __init__(self, cur):
        self._cur = cur
    def cursor(self):
        return self._cur
    def close(self):
        pass


ns = {'datetime': datetime, 'itertools': itertools, 'HTTPException': FakeHTTPException}
for fn in ("_misa_ngay_str", "_misa_la_dong_thue", "_misa_doc_ngay", "_misa_bo_dau",
           "_misa_ten_khop_mo_ta", "_misa_doi_tuong_hoa_don",
           "_misa_doi_tuong_thanh_toan", "_misa_doi_tuong_dieu_chinh_tien_mat", "_misa_khop_1_2",
           "_misa_doi_chieu_3_tang", "_hd_so_trong_mo_ta", "_xl_dau_ky_tham_so", "_misa_so_du_dau_ky_doi_dien"):
    exec(extract_fn(fn), ns)
ns['_MISA_TU_DEM_TEN_CTY'] = {
    "CONG", "TY", "TNHH", "CO", "PHAN", "MTV", "MOT", "THANH", "VIEN", "TRACH",
    "NHIEM", "HUU", "HAN", "DOANH", "NGHIEP", "TU", "NHAN", "XNK", "XUAT", "NHAP",
    "KHAU", "SAN", "THUONG", "MAI", "DAU", "TAP", "DOAN", "GROUP",
}
_misa_doi_chieu_3_tang = ns['_misa_doi_chieu_3_tang']

cur = FakeCursor()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur)
r = _misa_doi_chieu_3_tang(1, "TESTDB", loai="kh", tu_ngay="01/01/2025", den_ngay="31/12/2025", nguong=5_000_000)
dd = {x["mst"]: x for x in r["tang3"] if x.get("du_dau_ky")}
assert set(dd) == {"DR", "TV", "SH"}, [(x["mst"], x.get("du_dau_ky")) for x in r["tang3"]]
assert dd["DR"]["so_tien"] == 195000001 and dd["TV"]["so_tien"] == 50000000 and dd["DR"]["ref_id"] == "dk-1", dd
# Shaanxi: chỉ xử lý ĐÚNG số dư đầu kỳ ròng (274.556), 1 dòng — không liệt kê/xử lý lại từng hóa đơn cũ (41.400 + 6.233.156 …)
sh = [x for x in r["tang3"] if x["mst"] == "SH"]
assert len(sh) == 1 and sh[0]["so_tien"] == 274556 and sh[0]["so_du_loai"] == "no", sh
print("PASS 1b: số dư đầu kỳ RÒNG (đã trừ khoản trả trước kỳ) -> 1 dòng đúng 274.556, không xử lý lại từng hóa đơn.")
print("PASS 1: dư đầu kỳ còn treo, cả năm không giao dịch -> đề xuất xử lý về 0đ (195.000.001 và 50.000.000 — vượt ngưỡng 5tr vẫn có).")
assert "QM" not in dd and "NEW" not in dd, dd
print("PASS 2: đối tượng có thanh toán trong kỳ, hoặc hóa đơn phát sinh trong kỳ -> không phải 'dư đầu kỳ treo'.")
r2 = _misa_doi_chieu_3_tang(1, "TESTDB", loai="kh", den_ngay="31/12/2025", nguong=5_000_000)       # không nhập Từ ngày -> không có khái niệm đầu kỳ
assert not [x for x in r2["tang3"] if x.get("du_dau_ky")]
print("PASS 3: không nhập 'Từ ngày' thì không có khái niệm số dư đầu kỳ -> không đề xuất.")
src_html = open(os.path.join(_REPO_ROOT, "static", "index.html"), encoding="utf-8").read()
assert "it.du_dau_ky" in src_html and "số dư ĐẦU KỲ còn treo đến cuối kỳ" in src_html
print("PASS 4: giao diện đánh dấu các dòng 'Dư đầu kỳ' (nền xanh dương) kèm giải thích.")

# ===== Dư CÓ đầu kỳ (KH trả trước / dư bên ngược) =====
KH_TT = D(2024, 12, 31)


class FakeCursor2(FakeCursor):
    def execute(self, sql, params=()):
        if "/*SO_DU_DAU_KY*/" in sql:
            # (aoid, mã, tên, refid, refdate, Nợ, Có)
            self._result = [
                ("c1", "TT1", "KHÁCH TRẢ TRƯỚC 1", "dk-c1", KH_TT, 0, 30000000),                       # dư Có đầu kỳ 30tr, cả năm không động
                ("c2", "TT2", "KHÁCH 2", "dk-c2", KH_TT, 0, 20000000),                                  # dư Có đầu kỳ NHƯNG có phát sinh trong kỳ
                ("c2", "TT2", "KHÁCH 2", "hd-c2", D(2025, 5, 1), 5000000, 0),
                ("c3", "TT3", "KHÁCH 3", "x-c3", KH_TT, 10000000, 0),                                   # dư NỢ đầu kỳ (bên thường) -> không thuộc nhóm này
            ]
            return self
        return super().execute(sql, params)


cur2 = FakeCursor2()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur2)
r3 = _misa_doi_chieu_3_tang(1, "TESTDB", loai="kh", tu_ngay="01/01/2025", den_ngay="31/12/2025", nguong=5_000_000)
co = {x["mst"]: x for x in r3["tang3"] if x.get("du_dau_ky") and x.get("so_du_loai") == "co"}
assert set(co) == {"TT1"} and co["TT1"]["so_tien"] == 30000000 and co["TT1"]["ref_id"] == "dk-c1", r3["tang3"]
no = {x["mst"] for x in r3["tang3"] if x.get("du_dau_ky") and x.get("so_du_loai") == "no"}
assert no == {"TT3"}, no                                           # dư Nợ đầu kỳ cũng 1 dòng (so_du_loai="no")
print("PASS 5: dư CÓ đầu kỳ (KH trả trước 30tr) cả kỳ không giao dịch -> đề xuất xử lý; khách có phát sinh trong kỳ không bị đưa vào; dư Nợ (TT3) -> dòng XLNDK.")
assert ns["_xl_dau_ky_tham_so"]("kh", {"du_dau_ky": True, "so_du_loai": "no"}) == ("XLNDK", "1111", "131")
assert ns["_xl_dau_ky_tham_so"]("kh", {"du_dau_ky": True, "so_du_loai": "co"}) == ("XLCDK", "131", "1111")
assert ns["_xl_dau_ky_tham_so"]("ncc", {"du_dau_ky": True, "so_du_loai": "co"}) == ("XLCDK", "331", "1111")
assert ns["_xl_dau_ky_tham_so"]("ncc", {"du_dau_ky": True, "so_du_loai": "no"}) == ("XLNDK", "1111", "331")
assert ns["_xl_dau_ky_tham_so"]("kh", {"du_dau_ky": False}) is None
print("PASS 6: tiền tố/tài khoản: dư Nợ -> XLNDK (Nợ 1111/Có TK), dư Có -> XLCDK (Nợ TK/Có 1111), cho cả KH (131) và NCC (331).")

# Excel "Nghiệp vụ khác": số chứng từ XLNDK…/XLCDK… đánh số riêng, đúng TK Nợ/Có và cột đối tượng
import sys, tempfile
sys.path.insert(0, _REPO_ROOT)
import server, openpyxl
server.DOWNLOAD_DIR = tempfile.mkdtemp()
server._get_desktop_dir = lambda: None
ds = [dict(x) for x in r3["tang3"] if x.get("du_dau_ky")] + [{"account_object_id": "z", "mst": "KH9", "ten": "KH THƯỜNG", "inv_no": "HD9", "inv_date": "2025-03-05", "so_tien": 1000000}]
path, n = server._xuat_excel_dieu_chinh_cong_no(1, "kh", ds, den_ngay="31/12/2025")
ws = openpyxl.load_workbook(path).active
hdr = [c.value for c in ws[1]]
rows = [[c.value for c in r] for r in ws.iter_rows(min_row=2)]
assert n == len(rows) == 3, (n, rows)
theo_ma = {(r[13] or r[14]): r for r in rows}
cs, nd, thg = theo_ma["TT1"], theo_ma["TT3"], theo_ma["KH9"]
assert cs[3].startswith("XLCDK001/T12/2025") and cs[9] == "131" and cs[10] == "1111" and cs[13] == "TT1" and cs[11] == 30000000, cs
assert nd[3].startswith("XLNDK001/T12/2025") and nd[9] == "1111" and nd[10] == "131" and nd[14] == "TT3" and nd[11] == 10000000, nd
assert thg[3].startswith("DCTH001") and thg[9] == "1111" and thg[10] == "131" and thg[14] == "KH9", thg
print("PASS 7: Excel: XLNDK001 (Nợ 1111/Có 131), XLCDK001 (Nợ 131/Có 1111, đối tượng ở cột Nợ), HĐ thường vẫn DCTH…")
print("ALL DONE")
