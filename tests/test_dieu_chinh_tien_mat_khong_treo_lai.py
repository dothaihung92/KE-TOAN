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


ns = {'datetime': datetime, 'itertools': itertools, 'HTTPException': FakeHTTPException}
for fn in ("_misa_ngay_str", "_misa_la_dong_thue", "_misa_doc_ngay", "_misa_doi_tuong_hoa_don",
           "_misa_doi_tuong_thanh_toan", "_misa_doi_tuong_dieu_chinh_tien_mat", "_misa_khop_1_2",
           "_misa_doi_chieu_3_tang"):
    exec(extract_fn(fn), ns)
_misa_doi_chieu_3_tang = ns['_misa_doi_chieu_3_tang']

AOID = "ao-cocobete"


class FakeCursor:
    """Mô phỏng ĐÚNG kịch bản báo cáo thật: 1 NCC có
      - HĐ89 (09/09/2025, 2.940.000đ) ĐÃ được điều chỉnh xong bằng bút toán
        'Điều chỉnh công nợ treo' (Nợ 331/Có 1111) — người dùng ĐÃ Import
        Excel vào MISA đúng như công cụ hướng dẫn.
      - HĐ-BANK (01/02/2025, 3.000.000đ) đã trả THẬT qua ngân hàng (UNC,
        BAWithDraw) — dùng để xác nhận không bị đếm trùng khi gộp nguồn mới.
      - HĐ-CON-TREO (01/01/2025, 1.000.000đ) CHƯA có bất kỳ khoản nào —
        phải vẫn còn treo ở Tầng 3 (fix không được suy rộng quá tay)."""
    def execute(self, sql, params=()):
        p = params if isinstance(params, (tuple, list)) else (params,) if params != () else ()
        if "ISNULL(CorrespondingAccountNumber,'') LIKE '111%'" in sql:
            # _misa_doi_tuong_dieu_chinh_tien_mat — bút toán DCCN Nợ 331/Có 1111
            self._result = [(AOID, datetime.datetime(2025, 9, 9), 2940000, "dccn-89")]
        elif "FROM AccountObjectLedger WHERE AccountNumber LIKE ?" in sql:
            # _misa_doi_tuong_hoa_don — CreditAmount (hóa đơn NCC)
            self._result = [
                (AOID, "0317826028", "", "COCOBETE", "inv-89", "89",
                 datetime.datetime(2025, 9, 9), datetime.datetime(2025, 9, 9), 2940000, ""),
                (AOID, "0317826028", "", "COCOBETE", "inv-bank", "BANK1",
                 datetime.datetime(2025, 2, 1), datetime.datetime(2025, 2, 1), 3000000, ""),
                (AOID, "0317826028", "", "COCOBETE", "inv-treo", "TREO1",
                 datetime.datetime(2025, 1, 1), datetime.datetime(2025, 1, 1), 1000000, ""),
            ]
        elif "FROM BAWithDraw" in sql or "BAWithDrawDetail" in sql:
            self._result = [(AOID, datetime.datetime(2025, 2, 1), 3000000, "unc-bank", "", "", "UNC001")]
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


cur = FakeCursor()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur)
_misa_doi_chieu_3_tang = ns['_misa_doi_chieu_3_tang']

r = _misa_doi_chieu_3_tang(1, "TESTDB", loai="ncc")

tang3_inv = {x["inv_no"] for x in r["tang3"]}
assert "89" not in tang3_inv, (
    f"BUG: HĐ89 ĐÃ có bút toán điều chỉnh công nợ treo (Nợ 331/Có 1111) trong MISA "
    f"nhưng vẫn bị liệt vào Tầng 3 'treo' — tang3={r['tang3']}")
print("PASS: HĐ89 (đã Import Excel điều chỉnh công nợ treo vào MISA) KHÔNG còn hiện lại ở Tầng 3.")

assert "BANK1" not in tang3_inv, f"HĐ-BANK đã trả qua ngân hàng thật vẫn phải khớp Tầng 1 — tang3={r['tang3']}"
tang1_inv = {x["inv_no"] for x in r["tang1"]}
assert "BANK1" in tang1_inv, f"HĐ-BANK phải khớp Tầng 1 (ngân hàng thật) — tang1={r['tang1']}"
print("PASS: HĐ-BANK (trả qua ngân hàng thật) vẫn khớp Tầng 1 bình thường, không bị đếm trùng "
      "khi gộp thêm nguồn 'điều chỉnh tiền mặt'.")

assert "TREO1" in tang3_inv, f"HĐ-CON-TREO chưa có gì phải VẪN còn treo ở Tầng 3 — tang3={r['tang3']}"
print("PASS: hóa đơn THẬT SỰ chưa xử lý gì (không ngân hàng, không điều chỉnh) vẫn đúng ở Tầng 3, "
      "fix không suy rộng quá tay làm biến mất hóa đơn treo thật.")

print("\nALL DONE")
