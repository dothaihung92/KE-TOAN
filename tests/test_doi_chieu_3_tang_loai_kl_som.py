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

NOW = datetime.datetime.now()
NGAY_GAN = NOW - datetime.timedelta(days=5)

AOID_KL = "aoid-kl"
AOID_THUONG = "aoid-abc"


class FakeCursor:
    def execute(self, sql, params=()):
        if "ISNULL(CorrespondingAccountNumber,'') LIKE '111%'" in sql:
            self._result = []   # không có điều chỉnh tiền mặt nào
        elif "FROM AccountObjectLedger WHERE AccountNumber LIKE ?" in sql:
            # _misa_doi_tuong_hoa_don (kh, TK 131) — nhiều hóa đơn KHÁC NHAU cùng gắn 1 mã "KL"
            # (nhiều khách lẻ thật khác nhau) + 1 khách hàng BÌNH THƯỜNG để đối chứng.
            self._result = [
                (AOID_KL, "KL", "", "Khách Lẻ", "hd-kl-1", "909", NGAY_GAN, NGAY_GAN, 660000, "5111"),
                (AOID_KL, "KL", "", "Khách Lẻ", "hd-kl-2", "1038", NGAY_GAN, NGAY_GAN, 450000, "5111"),
                (AOID_THUONG, "KH001", "", "CÔNG TY TNHH ABC", "hd-abc-1", "BH100",
                 NGAY_GAN, NGAY_GAN, 300000, "5111"),
            ]
        elif "FROM BADepositDetail bd JOIN BADeposit b" in sql:
            # Khoản thanh toán ngân hàng khớp CHÍNH XÁC cả HĐ KL lẫn HĐ khách thường (nếu KHÔNG bị
            # loại sớm, KL vẫn sẽ "khớp" được ở Tầng 1 — chứng minh nó THỰC SỰ đi vào _misa_khop_1_2
            # nếu không lọc, chứ không phải chỉ đơn giản không có dữ liệu để khớp).
            self._result = [
                (AOID_KL, NGAY_GAN, 660000, "bd-kl-1", "", "", "UNT-KL-1"),
                (AOID_THUONG, NGAY_GAN, 300000, "bd-abc-1", "", "", "UNT-ABC-1"),
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
           "_misa_doi_chieu_3_tang", "_hd_so_trong_mo_ta"):
    exec(extract_fn(fn), ns)
ns['_MISA_TU_DEM_TEN_CTY'] = {
    "CONG", "TY", "TNHH", "CO", "PHAN", "MTV", "MOT", "THANH", "VIEN", "TRACH",
    "NHIEM", "HUU", "HAN", "DOANH", "NGHIEP", "TU", "NHAN", "XNK", "XUAT", "NHAP",
    "KHAU", "SAN", "THUONG", "MAI", "DAU", "TAP", "DOAN", "GROUP",
}
_misa_doi_chieu_3_tang = ns['_misa_doi_chieu_3_tang']

# ===== Test 1 (QUAN TRỌNG — đúng bug thật): "KL" phải bị loại khỏi TẤT CẢ kết quả khớp
# (tang1/tang2/khong_ro/tam_ung), không chỉ tang3 — dù có khoản thanh toán khớp CHÍNH XÁC với hóa
# đơn KL (chứng minh nếu không lọc sớm, KL vẫn sẽ lọt vào và bị xử lý trong _misa_khop_1_2). =====
cur = FakeCursor()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur)
progress_calls = []
r = _misa_doi_chieu_3_tang(1, "TESTDB", loai="kh",
                           on_progress=lambda i, n, ten: progress_calls.append((i, n, ten)))

for nhan, ds in (("tang1", r["tang1"]), ("tang2", r["tang2"]), ("khong_ro", r["khong_ro"]),
                 ("tam_ung", r.get("tam_ung") or [])):
    for it in ds:
        assert it.get("ma") != "KL", (
            f"Mã 'KL' (Khách lẻ, gộp chung hàng nghìn khách khác nhau) KHÔNG được xuất hiện trong "
            f"kết quả '{nhan}' — phải bị loại khỏi đầu vào _misa_khop_1_2() từ sớm (không chỉ Tầng "
            f"3) — got {it}")
print("PASS 1: mã 'KL' không xuất hiện trong BẤT KỲ kết quả khớp nào (tang1/tang2/khong_ro/tam_ung), "
      "kể cả khi có khoản thanh toán khớp chính xác hóa đơn KL — xác nhận đã bị loại khỏi đầu vào "
      "_misa_khop_1_2() từ sớm, không chỉ ở Tầng 3 như trước.")

# ===== Test 2 (QUAN TRỌNG — đúng bug thật): tổng số đối tượng công nợ báo qua on_progress (tham số
# thứ 2, "n") KHÔNG được tính "KL" vào — nếu không, thanh tiến độ vẫn hiện "đang xử lý: KL" và tốn
# thời gian xử lý dù kết quả bị vứt bỏ sau đó (đúng lỗi thật: thanh tiến độ đứng yên ở "đang xử lý:
# KL" suốt hơn 3 phút). =====
assert progress_calls, "on_progress phải được gọi ít nhất 1 lần (có 1 đối tượng công nợ hợp lệ: KH001)."
ten_da_bao = {ten for _i, _n, ten in progress_calls}
assert "KL" not in ten_da_bao, (
    f"on_progress KHÔNG được báo 'đang xử lý: KL' — KL phải bị loại TRƯỚC khi đưa vào vòng lặp chính "
    f"của _misa_khop_1_2 (nơi gọi on_progress), không chỉ bị loại ở kết quả cuối — got {ten_da_bao}")
tong_bao = progress_calls[0][1]
assert tong_bao == 1, (
    f"Tổng số đối tượng công nợ báo qua tiến độ phải = 1 (chỉ còn KH001, đã loại KL) — got {tong_bao}")
print("PASS 2: thanh tiến độ KHÔNG còn báo 'đang xử lý: KL' và không tính KL vào tổng số đối tượng — "
      "khớp đúng nguyên nhân 'kẹt' người dùng thấy trên thanh tiến độ.")

# ===== Test 3 (không hồi quy — QUAN TRỌNG): khách hàng BÌNH THƯỜNG (mã riêng, không dùng chung) vẫn
# được đối chiếu và khớp đúng như cũ, không bị ảnh hưởng bởi việc loại KL sớm. =====
tang1_abc = [it for it in r["tang1"] if it.get("ma") == "KH001"]
assert len(tang1_abc) == 1 and tang1_abc[0]["inv_no"] == "BH100", (
    f"Khách hàng bình thường (KH001) vẫn phải khớp đúng Tầng 1 như cũ — got tang1={r['tang1']}")
print("PASS 3: khách hàng có mã riêng (không dùng chung KL) vẫn đối chiếu/khớp đúng bình thường, "
      "không bị ảnh hưởng bởi việc loại KL sớm.")

# ===== Test 4 (không hồi quy): Tầng 3 vẫn KHÔNG có "KL" (giữ đúng hành vi cũ đã có sẵn từ trước —
# tests/test_tang3_bo_qua_khach_le.py) — chỉ đảm bảo việc loại sớm không vô tình phá vỡ điều này. =====
assert "KL" not in [it["mst"] for it in r["tang3"]], "Tầng 3 vẫn phải không có KL như hành vi cũ."
print("PASS 4: Tầng 3 vẫn không có KL, giữ đúng hành vi cũ.")

print("\nALL DONE")
