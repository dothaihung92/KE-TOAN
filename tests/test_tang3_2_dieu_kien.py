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


# ── Theo đúng yêu cầu người dùng: "chỉnh lại tầng 3 là phải phù hợp vs 2
# điều kiện luôn chứ không phải dựa vào 1 điều kiện" — Tầng 3 phải LUÔN áp
# dụng CẢ 2 điều kiện (giá trị dưới ngưỡng + quá hạn hơn N tháng), kể cả
# khi đã nhập khung Từ ngày/Đến ngày (trước đây khung ngày làm điều kiện
# quá hạn bị BỎ HẲN, coi 2 điều kiện là loại trừ nhau).
AOID_A = "kh-a"
HOM_NAY = datetime.datetime.now()
# HĐ CÒN MỚI (chỉ ~30 ngày trước hôm nay) -> KHÔNG đủ điều kiện quá hạn
# (mặc định thang_qua_han=10 tháng ~300 ngày) dù nằm trong khung ngày rộng
# và giá trị dưới ngưỡng.
NGAY_MOI = HOM_NAY - datetime.timedelta(days=30)
# HĐ THẬT SỰ quá hạn (~400 ngày trước, quá 300 ngày mặc định).
NGAY_QUA_HAN = HOM_NAY - datetime.timedelta(days=400)


class FakeCursor:
    def execute(self, sql, params=()):
        if "ISNULL(CorrespondingAccountNumber,'') LIKE '111%'" in sql:
            self._result = []
        elif "FROM AccountObjectLedger WHERE AccountNumber LIKE ?" in sql:
            self._result = [
                (AOID_A, "KA01", "", "CÔNG TY TNHH A", "inv-moi",
                 "1", NGAY_MOI, NGAY_MOI, 1000000, ""),
                (AOID_A, "KA01", "", "CÔNG TY TNHH A", "inv-cu",
                 "2", NGAY_QUA_HAN, NGAY_QUA_HAN, 1000000, ""),
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

# Nhập khung ngày RỘNG (bao trùm cả 2 hóa đơn) — mô phỏng đúng ảnh chụp
# người dùng gửi (01/01/2025 - 31/12/2025) — cùng thang_qua_han=10 (mặc
# định) và nguong=5.000.000 (mặc định, cả 2 HĐ đều dưới ngưỡng).
tu_ngay = (HOM_NAY - datetime.timedelta(days=800)).strftime("%Y-%m-%d")
den_ngay = (HOM_NAY + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
r = _misa_doi_chieu_3_tang(1, "TESTDB", loai="kh", tu_ngay=tu_ngay, den_ngay=den_ngay)

so_hd_trong_tang3 = {x["inv_no"] for x in r["tang3"]}
assert "1" not in so_hd_trong_tang3, (
    f"HĐ 1 (chỉ ~30 ngày trước, CHƯA quá hạn 10 tháng) KHÔNG được vào Tầng 3 dù nằm trong khung "
    f"ngày rộng và giá trị dưới ngưỡng — Tầng 3 phải đòi CẢ 2 điều kiện (giá trị + quá hạn), không "
    f"phải chỉ 1-trong-2 — got tang3={r['tang3']}")
assert "2" in so_hd_trong_tang3, (
    f"HĐ 2 (~400 ngày trước, ĐÃ quá hạn 10 tháng) PHẢI vào Tầng 3 (thỏa cả 2 điều kiện) — "
    f"got tang3={r['tang3']}")
print("PASS: Tầng 3 giờ đòi ĐỦ CẢ 2 điều kiện (giá trị dưới ngưỡng VÀ quá hạn hơn N tháng tính từ "
      "hôm nay) CÙNG LÚC, kể cả khi đã nhập khung Từ ngày/Đến ngày — HĐ còn mới (chưa quá hạn) "
      "không còn lọt vào Tầng 3 chỉ vì nằm trong khung ngày rộng; HĐ thật sự quá hạn vẫn đúng vào "
      "Tầng 3 — đúng yêu cầu người dùng 'phải phù hợp với 2 điều kiện luôn chứ không phải dựa vào "
      "1 điều kiện'.")


# ── Phần 2 (MỚI): đúng phản hồi thật người dùng — chọn khung 01/01/2025-
# 31/12/2025, "quá hạn hơn 3 tháng", "giá trị dưới 20tr" nhưng phần mềm
# vẫn hiện điều chỉnh hóa đơn tháng 11-12/2025. Nguyên nhân: MỐC tính quá
# hạn trước đây LUÔN là "hôm nay" (lúc thật sự chạy, 2026-08-30 — GẦN 1
# NĂM sau kỳ báo cáo) nên MỌI hóa đơn 2025 nghiễm nhiên "quá hạn hơn 3
# tháng" theo mốc đó — sai bản chất khi người dùng đang xem công nợ TÍNH
# ĐẾN 31/12/2025. Mốc ĐÚNG phải là chính "Đến ngày" (31/12/2025).
AOID_B = "kh-b"
DEN_NGAY_BAO_CAO = datetime.datetime(2025, 12, 31, 23, 59, 59)
# 09/2025 -> cách 31/12/2025 hơn 3 tháng (>90 ngày) -> ĐÚNG quá hạn.
HD_THANG_9 = datetime.datetime(2025, 9, 11)
# 11/2025 và 12/2025 -> cách 31/12/2025 CHƯA tới 3 tháng -> KHÔNG quá hạn
# (dù đã cách "hôm nay" 2026-08-30 rất xa) — đúng 2 hóa đơn người dùng
# thắc mắc trong ảnh chụp (mã 0319166112 số HĐ 22 ngày 2025-11-05, mã
# 0402196345 số HĐ 23 ngày 2025-11-05, mã 0107429031-001 số HĐ 46 ngày
# 2025-12-13).
HD_THANG_11 = datetime.datetime(2025, 11, 5)
HD_THANG_12 = datetime.datetime(2025, 12, 13)


class FakeCursorB:
    def execute(self, sql, params=()):
        if "ISNULL(CorrespondingAccountNumber,'') LIKE '111%'" in sql:
            self._result = []
        elif "FROM AccountObjectLedger WHERE AccountNumber LIKE ?" in sql:
            self._result = [
                (AOID_B, "KB01", "", "CÔNG TY TNHH B", "inv-t9",
                 "1", HD_THANG_9, HD_THANG_9, 1000000, ""),
                (AOID_B, "KB01", "", "CÔNG TY TNHH B", "inv-t11",
                 "22", HD_THANG_11, HD_THANG_11, 2394000, ""),
                (AOID_B, "KB01", "", "CÔNG TY TNHH B", "inv-t12",
                 "46", HD_THANG_12, HD_THANG_12, 4410000, ""),
            ]
        elif "FROM BADeposit" in sql or "BADepositDetail" in sql:
            self._result = []
        else:
            self._result = []
        return self

    def fetchone(self):
        return self._result[0] if self._result else None

    def fetchall(self):
        return self._result


curB = FakeCursorB()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(curB)
rB = _misa_doi_chieu_3_tang(1, "TESTDB", loai="kh", thang_qua_han=3, nguong=20_000_000,
                            tu_ngay="2025-01-01", den_ngay="2025-12-31")

so_hd_tang3_B = {x["inv_no"] for x in rB["tang3"]}
assert "1" in so_hd_tang3_B, (
    f"HĐ tháng 9/2025 cách 'Đến ngày' 31/12/2025 hơn 3 tháng -> PHẢI vào Tầng 3 — got {rB['tang3']}")
assert "22" not in so_hd_tang3_B and "46" not in so_hd_tang3_B, (
    f"HĐ tháng 11 và 12/2025 CHƯA cách 'Đến ngày' 31/12/2025 đủ 3 tháng -> KHÔNG được vào Tầng 3, dù "
    f"đã cách 'hôm nay' (lúc chạy báo cáo) rất xa — mốc tính quá hạn phải là 'Đến ngày' đang xem, "
    f"không phải lúc nào cũng là hôm nay — đúng bug người dùng vừa báo lại — got {rB['tang3']}")
print("PASS: Phần 2 — mốc tính 'quá hạn hơn N tháng' giờ là 'Đến ngày' (31/12/2025) khi có nhập, "
      "KHÔNG còn luôn luôn là 'hôm nay' (lúc thật sự chạy báo cáo, có thể rất lâu sau kỳ đang xem) — "
      "HĐ tháng 11-12/2025 (chưa quá hạn TÍNH ĐẾN cuối kỳ 2025) không còn bị đề xuất điều chỉnh oan; "
      "HĐ tháng 9/2025 (thật sự quá hạn hơn 3 tháng tính đến cuối kỳ) vẫn đúng vào Tầng 3.")

print("\nALL DONE")
