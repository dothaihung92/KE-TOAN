import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import datetime, itertools
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

"""Regression test: người dùng phản hồi thêm sau ca SATORI/HĐ 5947 — "miễn có
thanh toán đủ và số dư trong kỳ không còn nợ. nợ do đầu kỳ thì không cần kỳ
thì phần mềm không cần làm điều chỉnh. vì không phải nội dung thanh toán nào
cũng có ghi rõ số hoá đơn" — nghĩa là cách sửa TRƯỚC (_hd_so_trong_mo_ta, chỉ
khớp khi nội dung CK ghi RÕ số hóa đơn) là CHƯA ĐỦ TỔNG QUÁT, vì không phải
lúc nào nội dung chuyển khoản cũng ghi số hóa đơn.

Fix TỔNG QUÁT hơn: tính SỐ DƯ CUỐI KỲ TỔNG THỂ của cả đối tượng (tổng hóa
đơn - tổng đã thu/chi, không phụ thuộc khớp được CHÍNH XÁC khoản nào cho hóa
đơn nào) — nếu đối tượng đã hết nợ/dư về TỔNG THỂ thì KHÔNG tạo "Điều chỉnh
công nợ treo" cho bất kỳ hóa đơn còn lại nào của đối tượng đó nữa, dù thuật
toán khớp chi tiết (Tầng 1/2, kể cả theo nội dung mô tả) không xác định được
khoản thanh toán nào ứng với hóa đơn nào. Ngược lại, đối tượng THẬT SỰ còn
nợ về tổng thể vẫn phải vào Tầng 3 như cũ (không được bỏ sót nợ thật)."""


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


NOW = datetime.datetime.now()
NGAY_HD1 = NOW - datetime.timedelta(days=900)   # quá hạn (> 10 tháng mặc định)
NGAY_HD2 = NOW - datetime.timedelta(days=400)   # quá hạn

AOID_HET_NO = "ncc-het-no-tong-the"    # đối tượng ĐÃ hết nợ về TỔNG THỂ
AOID_CON_NO = "ncc-con-no-that"        # đối tượng THẬT SỰ còn nợ về tổng thể

# HĐ1 (mỗi đối tượng): khớp bình thường Tầng 1 (thanh toán trong cửa sổ ngày).
# HĐ2: thanh toán (nếu có) đến NGOÀI cửa sổ ngày mặc định (~3 tháng) VÀ nội
# dung KHÔNG hề nhắc số hóa đơn (khác hẳn ca SATORI trước) — mô phỏng đúng
# lời người dùng "không phải nội dung thanh toán nào cũng có ghi rõ số hóa
# đơn" — chỉ số dư TỔNG THỂ mới cứu được HĐ2 khỏi bị treo oan.
NGAY_TT1 = NGAY_HD1 + datetime.timedelta(days=20)     # trong cửa sổ của HĐ1
NGAY_TT2_MUON = NOW - datetime.timedelta(days=50)     # NGOÀI cửa sổ của HĐ2


class FakeCursor:
    def execute(self, sql, *params):
        if "ISNULL(CorrespondingAccountNumber,'') LIKE '111%'" in sql:
            self._result = []
        elif "FROM AccountObjectLedger WHERE AccountNumber LIKE ?" in sql:
            self._result = [
                (AOID_HET_NO, "HN01", "", "CÔNG TY TNHH ĐÃ HẾT NỢ", "hn-hd1",
                 "HN-HD1", NGAY_HD1, NGAY_HD1, 300000, ""),
                (AOID_HET_NO, "HN01", "", "CÔNG TY TNHH ĐÃ HẾT NỢ", "hn-hd2",
                 "HN-HD2", NGAY_HD2, NGAY_HD2, 300000, ""),
                (AOID_CON_NO, "CN01", "", "CÔNG TY TNHH CÒN NỢ THẬT", "cn-hd1",
                 "CN-HD1", NGAY_HD1, NGAY_HD1, 300000, ""),
                (AOID_CON_NO, "CN01", "", "CÔNG TY TNHH CÒN NỢ THẬT", "cn-hd2",
                 "CN-HD2", NGAY_HD2, NGAY_HD2, 300000, ""),
            ]
        elif "FROM AccountObjectLedger WHERE AccountObjectID = ?" in sql:
            # _misa_chi_tiet_cong_no cho AOID_HET_NO
            self._result = [
                ("hn-hd1", NGAY_HD1, NGAY_HD1, "HN-HD1", "HN-HD1", "", "", "331",
                 0, 300000, "HN01", "CÔNG TY TNHH ĐÃ HẾT NỢ"),
                ("hn-hd2", NGAY_HD2, NGAY_HD2, "HN-HD2", "HN-HD2", "", "", "331",
                 0, 300000, "HN01", "CÔNG TY TNHH ĐÃ HẾT NỢ"),
            ]
        elif "FROM BAWithDraw" in sql or "BAWithDrawDetail" in sql:
            self._result = [
                # AOID_HET_NO: HĐ1 khớp đúng Tầng 1; HĐ2 có thanh toán THẬT
                # (305.000đ, chỉ lệch 5.000đ do phí NH) nhưng đến NGOÀI cửa sổ
                # ngày và nội dung KHÔNG ghi số hóa đơn -> Tầng 1/2/Tầng 0 đều
                # KHÔNG khớp được — CHỈ số dư tổng thể mới cứu HĐ2 khỏi treo oan.
                (AOID_HET_NO, NGAY_TT1, 300000, "hn-tt1", "CHUYEN KHOAN THANH TOAN HANG HOA", "", "UNC-HN1"),
                (AOID_HET_NO, NGAY_TT2_MUON, 305000, "hn-tt2", "CHUYEN KHOAN THANH TOAN HANG HOA", "", "UNC-HN2"),
                # AOID_CON_NO: CHỈ có thanh toán cho HĐ1, HĐ2 THẬT SỰ chưa ai
                # trả đồng nào -> số dư tổng thể vẫn còn nợ thật 300.000đ.
                (AOID_CON_NO, NGAY_TT1, 300000, "cn-tt1", "CHUYEN KHOAN THANH TOAN HANG HOA", "", "UNC-CN1"),
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
           "_misa_doi_tuong_thanh_toan", "_misa_doi_tuong_dieu_chinh_tien_mat", "_hd_so_trong_mo_ta",
           "_misa_khop_1_2", "_misa_doi_chieu_3_tang", "_misa_chi_tiet_cong_no"):
    exec(extract_fn(fn), ns)
ns['_MISA_TU_DEM_TEN_CTY'] = {
    "CONG", "TY", "TNHH", "CO", "PHAN", "MTV", "MOT", "THANH", "VIEN", "TRACH",
    "NHIEM", "HUU", "HAN", "DOANH", "NGHIEP", "TU", "NHAN", "XNK", "XUAT", "NHAP",
    "KHAU", "SAN", "THUONG", "MAI", "DAU", "TAP", "DOAN", "GROUP",
}
_misa_doi_chieu_3_tang = ns['_misa_doi_chieu_3_tang']
_misa_chi_tiet_cong_no = ns['_misa_chi_tiet_cong_no']

cur = FakeCursor()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur)

# ----- Test 1 (_misa_doi_chieu_3_tang): đối tượng ĐÃ hết nợ về TỔNG THỂ
# không còn bị tạo "Điều chỉnh công nợ treo" cho HĐ2 (chưa khớp CHI TIẾT
# được), dù nội dung chuyển khoản KHÔNG hề ghi số hóa đơn. -----
r = _misa_doi_chieu_3_tang(1, "TESTDB", loai="ncc")
so_hd_tang3 = {x["inv_no"] for x in r["tang3"]}
assert "HN-HD2" not in so_hd_tang3, (
    f"HĐ 'HN-HD2' của đối tượng ĐÃ HẾT NỢ (tổng thanh toán 605.000đ >= tổng hóa đơn 600.000đ) KHÔNG "
    f"được vào Tầng 3 dù chưa khớp CHI TIẾT được khoản nào (nội dung CK không ghi số hóa đơn) — số dư "
    f"TỔNG THỂ đã đủ/thừa là bằng chứng đủ mạnh, không cần khớp đúng từng khoản mới kết luận đã trả — "
    f"got tang3={r['tang3']}")
print("PASS 1: đối tượng đã hết nợ về TỔNG THỂ (dù nội dung CK không ghi số hóa đơn) -> KHÔNG bị tạo "
      "điều chỉnh công nợ treo oan cho hóa đơn chưa khớp CHI TIẾT được.")

# ----- Test 2 (không hồi quy — quan trọng): đối tượng THẬT SỰ còn nợ về
# tổng thể vẫn phải vào Tầng 3 như cũ — không được bỏ sót nợ thật. -----
assert "CN-HD2" in so_hd_tang3, (
    f"HĐ 'CN-HD2' của đối tượng THẬT SỰ còn nợ (chỉ mới trả HĐ1, HĐ2 chưa ai trả đồng nào, số dư tổng "
    f"thể còn nợ thật 300.000đ) PHẢI vẫn vào Tầng 3 như bình thường — không được bỏ sót nợ thật chỉ vì "
    f"có thêm điều kiện chặn theo số dư tổng thể — got tang3={r['tang3']}")
print("PASS 2: đối tượng THẬT SỰ còn nợ về tổng thể vẫn được đưa vào Tầng 3 bình thường, không bị bỏ "
      "sót nợ thật.")

# ----- Test 3 (_misa_chi_tiet_cong_no): dòng chi tiết của HĐ2 (đối tượng đã
# hết nợ tổng thể) KHÔNG được tô đỏ (treo=False), đồng bộ với Tầng 3. -----
rc = _misa_chi_tiet_cong_no(1, "TESTDB", "ncc", AOID_HET_NO)
dong_hd2 = [d for d in rc["dong"] if d["so_hoa_don"] == "HN-HD2"]
assert len(dong_hd2) == 1
assert dong_hd2[0]["treo"] is False, (
    f"Dòng chi tiết HĐ2 (đối tượng đã hết nợ tổng thể) KHÔNG được tô đỏ 'treo' — got {dong_hd2}")
assert rc["so_treo"] == 0, f"Đối tượng đã hết nợ tổng thể -> so_treo phải = 0 — got {rc['so_treo']}"
print("PASS 3: màn Chi tiết công nợ đồng bộ với Tầng 3 — không tô đỏ hóa đơn nào khi đối tượng đã hết "
      "nợ về tổng thể.")

print("\nALL DONE")
