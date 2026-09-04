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


# ── Đúng dữ liệu thật người dùng gửi (báo cáo MISA 'Chi tiết công nợ phải
# trả' — NCC 'CÔNG TY TNHH THƯƠNG MẠI S-MART'): 3 hóa đơn Nhập kho (mỗi hóa
# đơn 2 dòng Dừa + Thuế GTGT), 2 khoản UNC thanh toán khớp CHÍNH XÁC 2 hóa
# đơn PHÁT SINH SAU, chỉ hóa đơn ĐẦU TIÊN (05/11, 2.835.000đ) còn treo,
# không khoản nào khớp — người dùng muốn phần mềm TỰ NHẬN DIỆN đây là
# trường hợp "độ tin cậy cao" (rất có thể đã thanh toán, chỉ không qua
# ngân hàng) mà KHÔNG tự động ghi gì (vẫn cần xác nhận).
AOID_SMART = "ncc-smart"
NOW = datetime.datetime.now()
NGAY_HD1 = NOW - datetime.timedelta(days=800)          # 05/11 (còn treo)
NGAY_HD2 = NGAY_HD1 + datetime.timedelta(days=7)        # 12/11 (đã trả đủ)
NGAY_HD3 = NGAY_HD1 + datetime.timedelta(days=16)       # 21/11 (đã trả đủ)


class FakeCursor:
    def execute(self, sql, params=()):
        if "ISNULL(CorrespondingAccountNumber,'') LIKE '111%'" in sql:
            self._result = []   # không có điều chỉnh tiền mặt nào
        elif "FROM AccountObjectLedger WHERE AccountNumber LIKE ?" in sql:
            # _misa_doi_tuong_hoa_don (ncc, TK 331) — mỗi hóa đơn 2 dòng
            # (Dừa=gt, Thuế GTGT=vat), CÙNG RefID để gộp thành 1 hóa đơn.
            self._result = [
                (AOID_SMART, "SM01", "", "CÔNG TY TNHH THƯƠNG MẠI S-MART", "hd1",
                 "NK1", NGAY_HD1, NGAY_HD1, 2700000, "1561"),
                (AOID_SMART, "SM01", "", "CÔNG TY TNHH THƯƠNG MẠI S-MART", "hd1",
                 "NK1", NGAY_HD1, NGAY_HD1, 135000, "1331"),
                (AOID_SMART, "SM01", "", "CÔNG TY TNHH THƯƠNG MẠI S-MART", "hd2",
                 "NK1", NGAY_HD2, NGAY_HD2, 4650000, "1561"),
                (AOID_SMART, "SM01", "", "CÔNG TY TNHH THƯƠNG MẠI S-MART", "hd2",
                 "NK1", NGAY_HD2, NGAY_HD2, 232500, "1331"),
                (AOID_SMART, "SM01", "", "CÔNG TY TNHH THƯƠNG MẠI S-MART", "hd3",
                 "NK1", NGAY_HD3, NGAY_HD3, 6750000, "1561"),
                (AOID_SMART, "SM01", "", "CÔNG TY TNHH THƯƠNG MẠI S-MART", "hd3",
                 "NK1", NGAY_HD3, NGAY_HD3, 337500, "1331"),
            ]
        elif "FROM BAWithDraw" in sql or "BAWithDrawDetail" in sql:
            # _misa_doi_tuong_thanh_toan (ncc, UNC) — 2 khoản khớp ĐÚNG hóa
            # đơn 2 và 3, KHÔNG có khoản nào cho hóa đơn 1.
            self._result = [
                (AOID_SMART, NGAY_HD2, 4882500, "unc-hd2",
                 "THANH TOAN TIEN DUA-121125-13:5", "", "UNC718561211253"),
                (AOID_SMART, NGAY_HD3, 7087500, "unc-hd3",
                 "THANH TOAN HOA DON 533-211125-", "", "UNC718562111254"),
            ]
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
           "_misa_doi_chieu_3_tang"):
    exec(extract_fn(fn), ns)
ns['_MISA_TU_DEM_TEN_CTY'] = {
    "CONG", "TY", "TNHH", "CO", "PHAN", "MTV", "MOT", "THANH", "VIEN", "TRACH",
    "NHIEM", "HUU", "HAN", "DOANH", "NGHIEP", "TU", "NHAN", "XNK", "XUAT", "NHAP",
    "KHAU", "SAN", "THUONG", "MAI", "DAU", "TAP", "DOAN", "GROUP",
}
_misa_doi_chieu_3_tang = ns['_misa_doi_chieu_3_tang']

cur = FakeCursor()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur)
r = _misa_doi_chieu_3_tang(1, "TESTDB", loai="ncc")

assert len(r["tang1"]) == 2, f"HĐ2 (4.882.500) và HĐ3 (7.087.500) phải khớp Tầng 1 đúng — got {r['tang1']}"
print("PASS: HĐ2/HĐ3 (đã trả đủ qua UNC, khớp CHÍNH XÁC số tiền) khớp Tầng 1 đúng.")

assert len(r["tang3"]) == 1 and r["tang3"][0]["inv_no"] == "NK1" and r["tang3"][0]["so_tien"] == 2835000, (
    f"CHỈ HĐ1 (2.835.000đ, 05/11) còn treo, không khoản nào khớp -> phải vào Tầng 3 — got {r['tang3']}")
assert r["tang3"][0]["tin_cay_cao"] is True, (
    f"HĐ1 phải được đánh dấu 'tin_cay_cao'=True vì HĐ2/HĐ3 (phát sinh SAU, cùng NCC S-MART) đều ĐÃ "
    f"khớp thanh toán ngân hàng đủ — dấu hiệu mạnh cho thấy HĐ1 rất có thể cũng đã được thanh toán "
    f"(bằng tiền mặt/cách khác) — đúng yêu cầu người dùng — got {r['tang3'][0]}")
print("PASS: HĐ1 (2.835.000đ, còn treo, KHÔNG khoản nào khớp) vào Tầng 3 VÀ được tự nhận diện "
      "'tin_cay_cao'=True vì các hóa đơn phát sinh SAU (HĐ2/HĐ3) của cùng NCC S-MART đã khớp thanh "
      "toán ngân hàng đủ — đúng yêu cầu người dùng ('phần mềm có thể nhận biết hóa đơn này là đã "
      "thanh toán tiền mặt') — nhưng CHỈ là gợi ý, chưa tự động ghi gì (vẫn nằm trong Tầng 3, cần "
      "người dùng tự xác nhận trước khi xuất Excel/ghi SQL).")

# ── Đối chứng: hóa đơn treo KHÔNG có hóa đơn nào phát sinh SAU (vd hóa đơn
# duy nhất/mới nhất của 1 đối tượng khác) -> KHÔNG đủ dấu hiệu, tin_cay_cao
# phải là False (an toàn, không suy đoán khi thiếu bằng chứng).
AOID_DON_LE = "ncc-le"
NGAY_DON_LE = NOW - datetime.timedelta(days=800)


class FakeCursor2(FakeCursor):
    def execute(self, sql, params=()):
        if "ISNULL(CorrespondingAccountNumber,'') LIKE '111%'" in sql:
            return super().execute(sql, params)
        if "FROM AccountObjectLedger WHERE AccountNumber LIKE ?" in sql:
            self._result = [
                (AOID_DON_LE, "LE01", "", "CÔNG TY TNHH ĐƠN LẺ", "hd-le",
                 "NK9", NGAY_DON_LE, NGAY_DON_LE, 1000000, "1561"),
            ]
            return self
        return super().execute(sql, params)


cur2 = FakeCursor2()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur2)
r2 = _misa_doi_chieu_3_tang(1, "TESTDB", loai="ncc")

assert len(r2["tang3"]) == 1 and r2["tang3"][0]["tin_cay_cao"] is False, (
    f"Hóa đơn DUY NHẤT của 1 đối tượng (không có hóa đơn nào phát sinh sau để làm bằng chứng) "
    f"KHÔNG được suy đoán 'tin_cay_cao'=True — got {r2['tang3']}")
print("PASS: hóa đơn treo KHÔNG có hóa đơn nào phát sinh SAU (không đủ bằng chứng) -> "
      "tin_cay_cao=False, không suy đoán bừa khi thiếu dấu hiệu.")

# ── Phần 3 (MỚI, theo đúng yêu cầu người dùng): "Trường hợp này sẽ không
# dựa vào thời gian quá hạn để phát hiện" — hóa đơn tin_cay_cao vẫn phải
# hiện trong Tầng 3 dù CÒN RẤT MỚI (chưa quá hạn theo thời gian thông
# thường), miễn giá trị vẫn dưới ngưỡng. Đối chứng: hóa đơn MỚI tương tự
# nhưng KHÔNG có dấu hiệu tin_cay_cao thì vẫn bị loại vì chưa quá hạn
# (giữ đúng hành vi Tầng 3 gốc cho trường hợp không có dấu hiệu mạnh).
AOID_MOI = "ncc-moi"
NGAY_MOI_1 = NOW - datetime.timedelta(days=20)   # còn treo, rất mới
NGAY_MOI_2 = NGAY_MOI_1 + datetime.timedelta(days=5)   # đã trả đủ, mới hơn


class FakeCursor3(FakeCursor):
    def execute(self, sql, params=()):
        if "ISNULL(CorrespondingAccountNumber,'') LIKE '111%'" in sql:
            return super().execute(sql, params)
        if "FROM AccountObjectLedger WHERE AccountNumber LIKE ?" in sql:
            self._result = [
                (AOID_MOI, "MOI01", "", "CÔNG TY TNHH MỚI", "hd-moi-1",
                 "NKA", NGAY_MOI_1, NGAY_MOI_1, 500000, "1561"),
                (AOID_MOI, "MOI01", "", "CÔNG TY TNHH MỚI", "hd-moi-2",
                 "NKB", NGAY_MOI_2, NGAY_MOI_2, 800000, "1561"),
            ]
            return self
        if "FROM BAWithDraw" in sql or "BAWithDrawDetail" in sql:
            self._result = [
                (AOID_MOI, NGAY_MOI_2, 800000, "unc-moi-2", "THANH TOAN HD SAU", "", "UNC-MOI2"),
            ]
            return self
        return super().execute(sql, params)


cur3 = FakeCursor3()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur3)
# thang_qua_han mặc định 10 tháng -> hóa đơn ~20 ngày trước CHẮC CHẮN
# chưa quá hạn theo tiêu chí thời gian thông thường.
r3 = _misa_doi_chieu_3_tang(1, "TESTDB", loai="ncc")

hd_moi_trong_tang3 = [x for x in r3["tang3"] if x["inv_no"] == "NKA"]
assert len(hd_moi_trong_tang3) == 1 and hd_moi_trong_tang3[0]["tin_cay_cao"] is True, (
    f"HĐ 'NKA' (còn treo, mới ~20 ngày, CHƯA quá hạn) vẫn phải hiện trong Tầng 3 với tin_cay_cao=True "
    f"vì HĐ 'NKB' phát sinh SAU đã khớp thanh toán đủ — dấu hiệu này KHÔNG phụ thuộc thời gian quá "
    f"hạn theo đúng yêu cầu người dùng — got {r3['tang3']}")
print("PASS: Phần 3 — hóa đơn tin_cay_cao VẪN hiện trong Tầng 3 dù còn rất mới (chưa quá hạn theo "
      "thời gian thông thường) — dấu hiệu 'hóa đơn sau đã trả, hóa đơn này thì chưa' đủ mạnh để gợi "
      "ý ngay, không cần chờ đủ thời gian quá hạn, đúng yêu cầu người dùng.")

print("\nALL DONE")
