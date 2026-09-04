import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import datetime
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


COLUMNS = {
    "BADeposit": [("RefID", "uniqueidentifier"), ("AccountObjectID", "uniqueidentifier"),
                  ("AccountObjectName", "nvarchar")],
    "BADepositDetail": [("RefDetailID", "uniqueidentifier"), ("RefID", "uniqueidentifier"),
                        ("AccountObjectID", "uniqueidentifier")],
    # GeneralLedger THẬT không có cột DebitAccount/CreditAccount — mỗi dòng
    # chỉ ghi TK của CHÍNH dòng đó qua AccountNumber (TK đối ứng ở
    # CorrespondingAccountNumber) — khác hẳn AccountObjectLedger/
    # BADepositDetail/GLVoucherDetail (đều dùng DebitAccount/CreditAccount).
    "GeneralLedger": [("RefID", "uniqueidentifier"), ("AccountNumber", "nvarchar"),
                      ("CorrespondingAccountNumber", "nvarchar"), ("AccountObjectID", "uniqueidentifier"),
                      ("AccountObjectName", "nvarchar"), ("AccountObjectNameDI", "nvarchar"),
                      ("AccountObjectCode", "nvarchar")],
    "AccountObjectLedger": [("RefID", "uniqueidentifier"), ("AccountObjectID", "uniqueidentifier"),
                            ("AccountObjectCode", "nvarchar"), ("AccountObjectName", "nvarchar"),
                            ("AccountObjectNameDI", "nvarchar")],
    # BADepositWithdrawList KHÔNG có cột AccountObjectName (mô phỏng bản MISA
    # cũ hơn/thiếu cột) -> phải tự bỏ qua phần tên, chỉ sửa ID, KHÔNG lỗi cả lượt.
    "BADepositWithdrawList": [("RefID", "uniqueidentifier"), ("AccountObjectID", "uniqueidentifier")],
}

NEW_OBJ_ID = "obj-oxygen-new"


class FakeCursor:
    def __init__(self):
        self.updates = []   # (sql, params)

    def execute(self, sql, params=()):
        p = params if isinstance(params, (tuple, list)) else (params,) if params != () else ()
        if sql.startswith("UPDATE"):
            self.updates.append((sql, p))
            self._result = []
            return self
        if "sys.columns c" in sql and "sys.types ty" in sql:
            table = p[0]
            self._result = COLUMNS.get(table, [])
        elif "AccountObjectCode, ISNULL(AccountObjectName" in sql or (
                "SELECT ISNULL(AccountObjectCode,''), ISNULL(AccountObjectName,'')" in sql):
            self._result = [("OX01", "CÔNG TY TNHH OXYGEN RETAIL")]
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
    def commit(self):
        pass
    def rollback(self):
        pass
    def close(self):
        pass


ns = {'datetime': datetime, 'HTTPException': FakeHTTPException}
for fn in ("_misa_cot_bang_that", "_misa_chon_cot", "_misa_gan", "_misa_gia_tri_mac_dinh",
           "_misa_sua_doi_tuong_giao_dich"):
    exec(extract_fn(fn), ns)
_misa_sua_doi_tuong_giao_dich = ns['_misa_sua_doi_tuong_giao_dich']

cur = FakeCursor()
ns['_misa_sql_connect'] = lambda cid, database=None: FakeConn(cur)

r = _misa_sua_doi_tuong_giao_dich(1, "TESTDB", "kh", "unt-1709", NEW_OBJ_ID, preview=False)

assert r["so_bang_sua"] == 5, f"Phải sửa đủ 5 bảng — got {r['so_bang_sua']}"
assert r["ma_moi"] == "OX01" and r["ten_moi"] == "CÔNG TY TNHH OXYGEN RETAIL"

by_table = {}
for sql, params in cur.updates:
    table = sql.split("UPDATE ")[1].split(" SET")[0]
    by_table.setdefault(table, []).append((sql, params))

assert "BADeposit" in by_table and NEW_OBJ_ID in by_table["BADeposit"][0][1]
assert "BADepositDetail" in by_table and NEW_OBJ_ID in by_table["BADepositDetail"][0][1]
assert "AccountObjectLedger" in by_table and NEW_OBJ_ID in by_table["AccountObjectLedger"][0][1]
assert "BADepositWithdrawList" in by_table and NEW_OBJ_ID in by_table["BADepositWithdrawList"][0][1]
gl_sql, gl_params = by_table["GeneralLedger"][0]
assert "131%" in gl_params, f"GeneralLedger phải lọc ĐÚNG dòng 131 (không đụng dòng 1121 ngân hàng) — {gl_params}"
assert "[AccountNumber] LIKE ?" in gl_sql, (
    f"Phải dùng ĐÚNG cột thật AccountNumber (GeneralLedger KHÔNG có DebitAccount/CreditAccount, "
    f"đúng lỗi SQL Server người dùng báo: 'Invalid column name DebitAccount') — got {gl_sql}")
assert "DebitAccount" not in gl_sql and "CreditAccount" not in gl_sql

# Bảng BADepositWithdrawList THIẾU cột AccountObjectName (mô phỏng bản MISA
# khác) -> câu UPDATE chỉ có 1 tham số (ID) + RefID, KHÔNG lỗi cả lượt.
bdwl_sql, bdwl_params = by_table["BADepositWithdrawList"][0]
assert "AccountObjectName" not in bdwl_sql, "Không có cột AccountObjectName -> không được đưa vào câu UPDATE"
assert len(bdwl_params) == 2, f"Chỉ AccountObjectID + RefID (2 tham số) — got {bdwl_params}"

print("PASS: sửa đối tượng giao dịch ghi ĐÚNG cả 5 bảng (BADeposit, BADepositDetail, GeneralLedger "
      "[chỉ dòng 131, không đụng dòng ngân hàng 1121], AccountObjectLedger, BADepositWithdrawList) — "
      "đúng bài học 'MISA denormalize ra nhiều bảng, sửa thiếu 1 bảng là không đủ'. Bảng thiếu cột "
      "tên (BADepositWithdrawList) tự bỏ qua phần tên, không lỗi cả lượt.")

print("\nALL DONE")
