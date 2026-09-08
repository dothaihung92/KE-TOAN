import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import datetime, itertools
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

"""Regression test: đúng ca thật người dùng báo lại kèm 2 ảnh chụp MISA
("Tổng hợp công nợ phải thu" TK 131 năm 2025 và "Chi tiết công nợ phải
thu" cùng khách hàng) — 1 khách hàng có Số dư ĐẦU KỲ Nợ 13.595.900đ,
KHÔNG phát sinh gì suốt cả năm 2025, Số dư CUỐI KỲ vẫn y hệt Đầu kỳ —
nghĩa là hóa đơn gốc phát sinh khoản nợ này nằm TRƯỚC "Từ ngày" (01/01/2025)
đang chọn nhưng vẫn còn TREO (chưa thu) tính đến "Đến ngày" (31/12/2025).
Người dùng báo: "hoá đơn đó ở tháng 12/2025 nên công nợ bị treo qua 2026
nhưng phần mềm không xử lý phần treo này" — chức năng "Đối chiếu công nợ
3 tầng" (_misa_doi_chieu_3_tang) TRƯỚC ĐÂY lọc bỏ HẲN hóa đơn trước "Từ
ngày" khỏi CẢ 3 TẦNG, khiến khoản treo từ trước kỳ hoàn toàn VÔ HÌNH
trong báo cáo đối chiếu — không hiện Tầng 1/2 (đã khớp) LẪN Tầng 3 (treo,
cần xử lý).

Fix: chỉ còn lọc hóa đơn theo "Đến ngày" (hóa đơn tính đến ngày đó) —
KHÔNG còn loại hóa đơn trước "Từ ngày" nữa. Hóa đơn cũ đã khớp thanh toán
từ lâu vẫn hiện đúng Tầng 1/2 (không hại gì thêm); hóa đơn cũ CÒN TREO
nay ĐÚNG sẽ lọt vào Tầng 3 nếu đủ điều kiện quá hạn + giá trị nhỏ."""


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


AOID_CU = "kh-cu"
# Hóa đơn gốc TRƯỚC "Từ ngày" (01/01/2025) — đúng ca thật (số dư đầu kỳ
# 2025 phát sinh từ hóa đơn cũ hơn), quá hạn hơn 10 tháng (mặc định)
# TÍNH ĐẾN "Đến ngày" (31/12/2025), giá trị dưới ngưỡng mặc định 5tr.
NGAY_HD_CU = datetime.datetime(2024, 6, 1)
DEN_NGAY_BAO_CAO = datetime.datetime(2025, 12, 31, 23, 59, 59)

AOID_MOI = "kh-moi"
# Hóa đơn BÌNH THƯỜNG trong khung (tháng 1/2025, đủ xa "Đến ngày" 31/12/2025
# hơn 10 tháng mặc định) — phải KHÔNG bị đụng tới bởi thay đổi này, hành vi
# cũ (quá hạn thật -> vào Tầng 3) vẫn giữ nguyên.
NGAY_HD_TRONG_KHUNG = datetime.datetime(2025, 1, 15)


class FakeCursor:
    def execute(self, sql, *params):
        if "ISNULL(CorrespondingAccountNumber,'') LIKE '111%'" in sql:
            self._result = []
        elif "FROM AccountObjectLedger WHERE AccountNumber LIKE ?" in sql:
            self._result = [
                (AOID_CU, "KCU01", "", "CÔNG TY TNHH DƯỢC PHẨM ANH MỸ", "inv-cu",
                 "HD-CU", NGAY_HD_CU, NGAY_HD_CU, 2000000, ""),
                (AOID_MOI, "KMOI01", "", "CÔNG TY TNHH B", "inv-trong-khung",
                 "HD-TRONG-KHUNG", NGAY_HD_TRONG_KHUNG, NGAY_HD_TRONG_KHUNG, 2000000, ""),
            ]
        elif "FROM AccountObjectLedger WHERE AccountObjectID = ?" in sql:
            # _misa_chi_tiet_cong_no: RefID, RefDate, PostedDate, RefNo, InvNo,
            # JournalMemo, Description, CorrespondingAccountNumber, DebitAmount,
            # CreditAmount, AccountObjectCode, AccountObjectName
            self._result = [
                ("inv-cu", NGAY_HD_CU, NGAY_HD_CU, "HD-CU", "HD-CU", "", "", "511",
                 2000000, 0, "KCU01", "CÔNG TY TNHH DƯỢC PHẨM ANH MỸ"),
            ]
        elif "FROM BADeposit" in sql or "BADepositDetail" in sql:
            self._result = []   # không có khoản thanh toán nào -> cả 2 HĐ đều "chưa khớp"
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
           "_misa_doi_chieu_3_tang", "_misa_chi_tiet_cong_no"):
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

# ----- Test 1 (_misa_doi_chieu_3_tang, màn "Đối chiếu công nợ 3 tầng"):
# hóa đơn TRƯỚC "Từ ngày" (01/01/2025) nhưng vẫn còn TREO tính đến "Đến
# ngày" (31/12/2025) PHẢI lọt vào Tầng 3, không còn vô hình hoàn toàn. -----
r = _misa_doi_chieu_3_tang(1, "TESTDB", loai="kh", tu_ngay="2025-01-01", den_ngay="2025-12-31")
so_hd_tang3 = {x["inv_no"] for x in r["tang3"]}
assert "HD-CU" in so_hd_tang3, (
    f"Hóa đơn 'HD-CU' (ngày 01/06/2024, TRƯỚC 'Từ ngày' 01/01/2025 nhưng vẫn còn TREO tính đến "
    f"'Đến ngày' 31/12/2025) PHẢI lọt vào Tầng 3 — trước đây bị tu_ngay loại bỏ hoàn toàn khỏi cả 3 "
    f"tầng, đúng lỗi thật đã báo 'phần mềm không xử lý phần treo này' — got tang3={r['tang3']}")
assert "HD-TRONG-KHUNG" in so_hd_tang3, (
    f"Hóa đơn bình thường TRONG khung (03/2025, cũng quá hạn+dưới ngưỡng) vẫn phải vào Tầng 3 như cũ, "
    f"không bị ảnh hưởng bởi thay đổi này — got tang3={r['tang3']}")
print("PASS 1: hóa đơn công nợ treo TỪ TRƯỚC 'Từ ngày' (đúng ca thật khách hàng có Số dư đầu kỳ vẫn "
      "còn treo nguyên suốt kỳ) nay được nhận diện đúng ở Tầng 3, không còn vô hình trong báo cáo; "
      "hóa đơn bình thường trong khung không bị ảnh hưởng.")

# ----- Test 2 (_misa_chi_tiet_cong_no, màn "Chi tiết công nợ" drill-down):
# dòng "Số dư đầu kỳ" PHẢI được tô đỏ (treo=True) khi khoản nợ đầu kỳ đó
# thật sự vẫn còn treo — trước đây LUÔN treo=False vì hóa đơn gốc bị loại
# khỏi việc tính khớp/treo trước khi tới bước này. -----
rc = _misa_chi_tiet_cong_no(1, "TESTDB", "kh", AOID_CU, tu_ngay="2025-01-01", den_ngay="2025-12-31")
dong_dau_ky = rc["dong"][0]
assert dong_dau_ky["dien_giai"] == "Số dư đầu kỳ"
assert dong_dau_ky["treo"] is True, (
    f"Dòng 'Số dư đầu kỳ' (gộp từ hóa đơn 'HD-CU' còn treo thật) PHẢI được tô đỏ (treo=True) — đúng "
    f"ca thật ảnh chụp 'Chi tiết công nợ phải thu' của khách hàng có Số dư đầu kỳ Nợ 13.595.900đ không "
    f"phát sinh gì suốt kỳ — got {dong_dau_ky}")
assert dong_dau_ky["du_no"] == 2000000
print("PASS 2: dòng 'Số dư đầu kỳ' ở màn Chi tiết công nợ được tô đỏ đúng khi khoản nợ đầu kỳ thật sự "
      "vẫn còn treo (chưa khớp thanh toán nào), không còn luôn hiện treo=False như trước.")

print("\nTẤT CẢ TEST PASS")
