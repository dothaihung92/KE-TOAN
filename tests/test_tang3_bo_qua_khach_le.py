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


# ── Đúng lỗi thật người dùng báo kèm 2 file Excel thật (Chi tiết công nợ
# phải thu TK 131 KL, và danh sách ~3.600 chứng từ NVK "DCTH.../T8/2026 —
# Điều chỉnh công nợ treo HĐ ... - Khách Lẻ" ĐÃ GHI SỔ THẬT trong MISA):
# mã "KL" (Khách lẻ) DÙNG CHUNG cho HÀNG NGHÌN khách hàng THẬT KHÁC NHAU
# không có MST (xem _misa_ghi_ban_hang) — nhưng Tầng 3 coi CẢ "KL" là 1 đối
# tượng công nợ DUY NHẤT, nên hàng loạt hóa đơn của NHIỀU khách lẻ khác
# nhau (chỉ trùng mã KL) bị coi là "công nợ treo" của "cùng 1 người", sinh
# ra hàng nghìn gợi ý ảo -> "Ghi bù trừ treo" tạo hàng nghìn chứng từ sai,
# làm lệch hẳn số dư công nợ của KL trên MISA.
NOW = datetime.datetime.now()
NGAY_CU = NOW - datetime.timedelta(days=400)   # quá hạn > 10 tháng (mặc định)

AOID_KL = "aoid-kl"
AOID_THUONG = "aoid-abc"


class FakeCursor:
    def execute(self, sql, params=()):
        if "ISNULL(CorrespondingAccountNumber,'') LIKE '111%'" in sql:
            self._result = []   # không có điều chỉnh tiền mặt nào
        elif "FROM AccountObjectLedger WHERE AccountNumber LIKE ?" in sql:
            # _misa_doi_tuong_hoa_don (kh, TK 131) — nhiều hóa đơn KHÁC NHAU
            # cùng gắn 1 mã "KL" (nhiều khách lẻ thật khác nhau, không phân
            # biệt được qua AccountObjectID vì dùng CHUNG 1 đối tượng MISA)
            # + 1 khách hàng BÌNH THƯỜNG (có mã riêng) để đối chứng.
            self._result = [
                (AOID_KL, "KL", "", "Khách Lẻ", "hd-kl-1", "909", NGAY_CU, NGAY_CU, 660000, "5111"),
                (AOID_KL, "KL", "", "Khách Lẻ", "hd-kl-2", "1038", NGAY_CU, NGAY_CU, 450000, "5111"),
                (AOID_KL, "KL", "", "Khách Lẻ", "hd-kl-3", "908", NGAY_CU, NGAY_CU, 451000, "5111"),
                (AOID_THUONG, "KH001", "", "CÔNG TY TNHH ABC", "hd-abc-1", "BH100",
                 NGAY_CU, NGAY_CU, 300000, "5111"),
            ]
        elif "FROM BADepositDetail bd JOIN BADeposit b" in sql:
            self._result = []   # không có khoản thanh toán ngân hàng nào khớp -> mọi HĐ đều "treo"
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
r = _misa_doi_chieu_3_tang(1, "TESTDB", loai="kh")

tang3_ma = [it["mst"] for it in r["tang3"]]
assert "KL" not in tang3_ma, (
    f"Mã 'KL' (Khách lẻ, dùng chung cho hàng nghìn khách khác nhau) KHÔNG được vào Tầng 3 — đối chiếu "
    f"treo theo AccountObjectID chỉ có ý nghĩa với 1 đối tượng công nợ THẬT, gộp chung 'KL' sinh ra "
    f"gợi ý ảo (đúng lỗi thật đã báo: ~3.600 chứng từ 'Điều chỉnh công nợ treo ... - Khách Lẻ' ghi sai "
    f"vào MISA) — got {r['tang3']}")
assert len(r["tang3"]) == 1 and r["tang3"][0]["mst"] == "KH001", (
    f"Khách hàng BÌNH THƯỜNG (mã riêng, không dùng chung) vẫn PHẢI vào Tầng 3 như cũ, không bị ảnh "
    f"hưởng bởi việc loại KL — got {r['tang3']}")
print("PASS: mã 'KL' (Khách Lẻ, dùng chung cho nhiều khách khác nhau) bị loại hẳn khỏi Tầng 3 — không "
      "còn sinh ra gợi ý 'công nợ treo' ảo giữa các khách lẻ không liên quan; khách hàng có mã RIÊNG "
      "vẫn được đối chiếu Tầng 3 bình thường.")

print("\nALL DONE")
