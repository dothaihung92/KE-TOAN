import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys, datetime
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

names = ['_misa_cot_bang_that', '_misa_gia_tri_mac_dinh', '_misa_chon_cot', '_misa_gan',
         '_misa_mau_dong_that', '_misa_khncc_chuan_mst', '_misa_branch_id', '_misa_doc_ngay',
         '_snum', '_to_num', '_misa_bank_account_du_phong', '_misa_reason_type_du_phong',
         '_misa_reason_type_hop_le', '_misa_sua_ghi_so_unt_unc_cu']

class FakeHTTPException(Exception):
    def __init__(self, code, msg):
        self.code = code; self.msg = msg
        super().__init__(f"{code}: {msg}")

ns = {'datetime': datetime, 'HTTPException': FakeHTTPException, '_PM_MARK': 'HDDT-AUTO'}
for n in names:
    exec(extract_fn(n), ns)

cols_badeposit = [("RefID","uniqueidentifier"),("BranchID","uniqueidentifier"),("RefDate","datetime"),
    ("PostedDate","datetime"),("RefNoFinance","nvarchar"),("RefNoManagement","nvarchar"),
    ("AccountObjectID","uniqueidentifier"),("AccountObjectName","nvarchar"),("JournalMemo","nvarchar"),
    ("RefOrder","int"),("TotalAmountOC","money"),("TotalAmount","money"),
    ("IsPostedFinance","bit"),("IsPostedManagement","bit"),("CreatedDate","datetime"),
    ("ModifiedDate","datetime"),("CustomField10","nvarchar"),
    ("BankAccountID","uniqueidentifier"),("BankName","nvarchar"),("ReasonTypeID","int")]
cols_badepositdetail = [("BADepositDetailID","uniqueidentifier"),("RefID","uniqueidentifier"),
    ("AccountObjectID","uniqueidentifier"),("Description","nvarchar"),("CreditAccount","nvarchar"),
    ("Amount","money"),("AmountOC","money")]
cols_generalledger = [("GeneralLedgerID","int"),("RefID","uniqueidentifier"),("RefDetailID","uniqueidentifier"),
    ("RefNo","nvarchar"),("RefNo1","nvarchar"),("RefNo2","nvarchar"),("RefDate","datetime"),("RefDate1","datetime"),
    ("PostedDate","datetime"),("AccountNumber","nvarchar"),("CorrespondingAccountNumber","nvarchar"),
    ("DebitAmountOC","money"),("DebitAmount","money"),("CreditAmountOC","money"),("CreditAmount","money"),
    ("JournalMemo","nvarchar"),("Description","nvarchar"),("AccountObjectID","uniqueidentifier"),
    ("AccountObjectName","nvarchar"),("AccountObjectNameDI","nvarchar"),("AccountObjectCode","nvarchar"),
    ("AccountObjectTaxCode","nvarchar"),("BranchID","uniqueidentifier"),("RefOrder","int"),("EntryType","int"),
    ("RefType","int")]
cols_accountobjectledger = [("AccountObjectLedgerID","int"),("RefID","uniqueidentifier"),
    ("RefDetailID","uniqueidentifier"),("AccountNumber","nvarchar"),("DebitAmountOC","money"),
    ("DebitAmount","money"),("CreditAmountOC","money"),("CreditAmount","money"),("JournalMemo","nvarchar"),
    ("Description","nvarchar"),("AccountObjectID","uniqueidentifier"),("AccountObjectCode","nvarchar"),
    ("AccountObjectName","nvarchar"),("AccountObjectNameDI","nvarchar"),("AccountObjectTaxCode","nvarchar"),
    ("BranchID","uniqueidentifier"),("RefOrder","int"),("PayKeyID","nvarchar"),("DebtKeyID","nvarchar"),
    ("EntryType","int"),("RefType","int")]
cols_bdwl = [("RefID","uniqueidentifier"),("PostedDate","datetime"),("RefDate","datetime"),
    ("RefNoFinance","nvarchar"),("RefNoManagement","nvarchar"),("IsPostedFinance","bit"),
    ("IsPostedManagement","bit"),("AccountObjectID","uniqueidentifier"),("AccountObjectName","nvarchar"),
    ("BranchID","uniqueidentifier"),("JournalMemo","nvarchar"),("TotalAmountOC","money"),
    ("TotalAmount","money"),("RefOrder","int"),("CreatedDate","datetime"),("ModifiedDate","datetime"),
    ("CustomField10","nvarchar"),("BAType","int"),("ListTableName","nvarchar"),
    ("BankAccountID","uniqueidentifier"),("BankName","nvarchar"),("ReasonTypeID","int"),("RefType","int")]
cols_cfl = [("CustomFieldLegerID","uniqueidentifier"),("RefDetailID","uniqueidentifier"),
    ("RefID","uniqueidentifier"),("IsPostToManagementBook","bit"),("BranchID","uniqueidentifier"),
    ("PostedDate","datetime"),("IsUpdateRedundant","bit")]

def fake_cot_bang_that(cur, table):
    m = {"BADeposit": cols_badeposit, "BADepositDetail": cols_badepositdetail,
         "GeneralLedger": cols_generalledger, "AccountObjectLedger": cols_accountobjectledger,
         "BADepositWithdrawList": cols_bdwl, "CustomFieldLedger": cols_cfl}
    return {c.lower(): (c, t) for c, t in m.get(table, [])}

REAL_ID = "REAL-REFID"
BROKEN1_ID = "BROKEN-1"   # missing GL/AOL entirely
BROKEN2_ID = "BROKEN-2"   # already has 2 GL rows -> should be skipped
BROKEN3_ID = "BROKEN-3"   # đủ cả GL/AOL/BDWL/CFL nhưng BankName Master=null (lỗi DBNull->String thật)
BROKEN4_ID = "BROKEN-4"   # Master BankName đã đúng, nhưng BADepositWithdrawList.BankName=null (đợt 5)
BROKEN5_ID = "BROKEN-5"   # BankName đúng cả 2 bảng, nhưng Master.ReasonTypeID=null (đợt 6)
BROKEN6_ID = "BROKEN-6"   # Master thiếu CẢ HAI BankAccountID+BankName (đợt 9 — gap cũ: chỉ sửa
                          # được khi BankAccountID đã có sẵn, nhân bản từ 1 chứng từ THẬT tự nó
                          # cũng thiếu cả hai thì không bao giờ được sửa)

def fake_mau_dong_that(cur, table, where, params=()):
    if table == "BADepositDetail":
        return {"BADepositDetailID": "real-d", "RefID": REAL_ID, "AccountObjectID": "real-aid",
                "Description": "real", "CreditAccount": "131", "Amount": 999, "AmountOC": 999}
    return {}

class FakeCursor:
    def __init__(self):
        self.master_rows = {
            BROKEN1_ID: {"RefID": BROKEN1_ID, "BranchID": "b1", "RefDate": datetime.datetime(2025,1,1),
                         "PostedDate": datetime.datetime(2025,1,1), "RefNoFinance": "UNT-B1",
                         "RefNoManagement": "UNT-B1", "AccountObjectID": "aid-1", "AccountObjectName": "CTY 1",
                         "JournalMemo": "memo1", "RefOrder": 10, "TotalAmountOC": 100000, "TotalAmount": 100000,
                         "IsPostedFinance": True, "IsPostedManagement": False, "CreatedDate": None,
                         "ModifiedDate": None, "CustomField10": "HDDT-AUTO",
                         "BankAccountID": "bank-1", "BankName": "Ngân hàng ABC", "ReasonTypeID": 34},
            BROKEN2_ID: {"RefID": BROKEN2_ID, "BranchID": "b1", "RefDate": datetime.datetime(2025,1,2),
                         "PostedDate": datetime.datetime(2025,1,2), "RefNoFinance": "UNT-B2",
                         "RefNoManagement": "UNT-B2", "AccountObjectID": "aid-2", "AccountObjectName": "CTY 2",
                         "JournalMemo": "memo2", "RefOrder": 11, "TotalAmountOC": 200000, "TotalAmount": 200000,
                         "IsPostedFinance": True, "IsPostedManagement": False, "CreatedDate": None,
                         "ModifiedDate": None, "CustomField10": "HDDT-AUTO",
                         "BankAccountID": "bank-1", "BankName": "Ngân hàng ABC", "ReasonTypeID": 34},
            BROKEN3_ID: {"RefID": BROKEN3_ID, "BranchID": "b1", "RefDate": datetime.datetime(2025,1,3),
                         "PostedDate": datetime.datetime(2025,1,3), "RefNoFinance": "UNT-B3",
                         "RefNoManagement": "UNT-B3", "AccountObjectID": "aid-3", "AccountObjectName": "CTY 3",
                         "JournalMemo": "memo3", "RefOrder": 12, "TotalAmountOC": 300000, "TotalAmount": 300000,
                         "IsPostedFinance": True, "IsPostedManagement": False, "CreatedDate": None,
                         "ModifiedDate": None, "CustomField10": "HDDT-AUTO",
                         "BankAccountID": "bank-3", "BankName": None, "ReasonTypeID": 34},
            BROKEN4_ID: {"RefID": BROKEN4_ID, "BranchID": "b1", "RefDate": datetime.datetime(2025,1,4),
                         "PostedDate": datetime.datetime(2025,1,4), "RefNoFinance": "UNT-B4",
                         "RefNoManagement": "UNT-B4", "AccountObjectID": "aid-4", "AccountObjectName": "CTY 4",
                         "JournalMemo": "memo4", "RefOrder": 13, "TotalAmountOC": 400000, "TotalAmount": 400000,
                         "IsPostedFinance": True, "IsPostedManagement": False, "CreatedDate": None,
                         "ModifiedDate": None, "CustomField10": "HDDT-AUTO",
                         "BankAccountID": "bank-1", "BankName": "Ngân hàng ABC", "ReasonTypeID": 34},
            BROKEN5_ID: {"RefID": BROKEN5_ID, "BranchID": "b1", "RefDate": datetime.datetime(2025,1,5),
                         "PostedDate": datetime.datetime(2025,1,5), "RefNoFinance": "UNT-B5",
                         "RefNoManagement": "UNT-B5", "AccountObjectID": "aid-5", "AccountObjectName": "CTY 5",
                         "JournalMemo": "memo5", "RefOrder": 14, "TotalAmountOC": 500000, "TotalAmount": 500000,
                         "IsPostedFinance": True, "IsPostedManagement": False, "CreatedDate": None,
                         "ModifiedDate": None, "CustomField10": "HDDT-AUTO",
                         "BankAccountID": "bank-1", "BankName": "Ngân hàng ABC", "ReasonTypeID": None},
            BROKEN6_ID: {"RefID": BROKEN6_ID, "BranchID": "b1", "RefDate": datetime.datetime(2025,1,6),
                         "PostedDate": datetime.datetime(2025,1,6), "RefNoFinance": "UNT-B6",
                         "RefNoManagement": "UNT-B6", "AccountObjectID": "aid-6", "AccountObjectName": "CTY 6",
                         "JournalMemo": "memo6", "RefOrder": 15, "TotalAmountOC": 600000, "TotalAmount": 600000,
                         "IsPostedFinance": True, "IsPostedManagement": False, "CreatedDate": None,
                         "ModifiedDate": None, "CustomField10": "HDDT-AUTO",
                         "BankAccountID": None, "BankName": None, "ReasonTypeID": 34},
        }
        self.detail_rows = {
            BROKEN1_ID: {"BADepositDetailID": "d-1", "RefID": BROKEN1_ID, "AccountObjectID": "aid-1",
                         "Description": "memo1", "CreditAccount": "131", "Amount": 100000, "AmountOC": 100000},
            BROKEN2_ID: {"BADepositDetailID": "d-2", "RefID": BROKEN2_ID, "AccountObjectID": "aid-2",
                         "Description": "memo2", "CreditAccount": "131", "Amount": 200000, "AmountOC": 200000},
            BROKEN3_ID: {"BADepositDetailID": "d-3", "RefID": BROKEN3_ID, "AccountObjectID": "aid-3",
                         "Description": "memo3", "CreditAccount": "131", "Amount": 300000, "AmountOC": 300000},
            BROKEN4_ID: {"BADepositDetailID": "d-4", "RefID": BROKEN4_ID, "AccountObjectID": "aid-4",
                         "Description": "memo4", "CreditAccount": "131", "Amount": 400000, "AmountOC": 400000},
            BROKEN6_ID: {"BADepositDetailID": "d-6", "RefID": BROKEN6_ID, "AccountObjectID": "aid-6",
                         "Description": "memo6", "CreditAccount": "131", "Amount": 600000, "AmountOC": 600000},
            BROKEN5_ID: {"BADepositDetailID": "d-5", "RefID": BROKEN5_ID, "AccountObjectID": "aid-5",
                         "Description": "memo5", "CreditAccount": "131", "Amount": 500000, "AmountOC": 500000},
        }
        # BROKEN4: Master.BankName đã đúng nhưng dòng BADepositWithdrawList ĐÃ CÓ SẴN (da_co_bdwl=1)
        # lại bị để trống BankName riêng (lỗi thật đợt 5 — bảng này mới CHÍNH LÀ bảng màn XEM đọc).
        self.bdwl_row_bank = {BROKEN4_ID: (None, "bank-1")}
        self.gl_by_refid = {
            REAL_ID: [
                {"GeneralLedgerID": 1, "RefID": REAL_ID, "RefDetailID": "real-d", "RefNo": "R1",
                 "RefNo1": "R1", "RefNo2": "R1", "RefDate": datetime.datetime(2025,1,1),
                 "RefDate1": datetime.datetime(2025,1,1), "PostedDate": datetime.datetime(2025,1,1),
                 "AccountNumber": "1121", "CorrespondingAccountNumber": "131",
                 "DebitAmountOC": 999, "DebitAmount": 999, "CreditAmountOC": 0, "CreditAmount": 0,
                 "JournalMemo": "m", "Description": "m", "AccountObjectID": "real-aid",
                 "AccountObjectName": "R", "AccountObjectNameDI": "R", "AccountObjectCode": "RC",
                 "AccountObjectTaxCode": "RT", "BranchID": "b1", "RefOrder": 1, "EntryType": 1},
                {"GeneralLedgerID": 2, "RefID": REAL_ID, "RefDetailID": "real-d", "RefNo": "R1",
                 "RefNo1": "R1", "RefNo2": "R1", "RefDate": datetime.datetime(2025,1,1),
                 "RefDate1": datetime.datetime(2025,1,1), "PostedDate": datetime.datetime(2025,1,1),
                 "AccountNumber": "131", "CorrespondingAccountNumber": "1121",
                 "DebitAmountOC": 0, "DebitAmount": 0, "CreditAmountOC": 999, "CreditAmount": 999,
                 "JournalMemo": "m", "Description": "m", "AccountObjectID": "real-aid",
                 "AccountObjectName": "R", "AccountObjectNameDI": "R", "AccountObjectCode": "RC",
                 "AccountObjectTaxCode": "RT", "BranchID": "b1", "RefOrder": 1, "EntryType": 2},
            ],
            BROKEN2_ID: [  # already has 2 -> should be SKIPPED
                {"GeneralLedgerID": 3, "RefID": BROKEN2_ID}, {"GeneralLedgerID": 4, "RefID": BROKEN2_ID},
            ],
            BROKEN3_ID: [  # đủ 2 GL rồi -> chỉ còn thiếu BankName Master
                {"GeneralLedgerID": 5, "RefID": BROKEN3_ID}, {"GeneralLedgerID": 6, "RefID": BROKEN3_ID},
            ],
            BROKEN4_ID: [  # đủ 2 GL rồi -> chỉ còn thiếu BankName của chính dòng BDWL
                {"GeneralLedgerID": 7, "RefID": BROKEN4_ID}, {"GeneralLedgerID": 8, "RefID": BROKEN4_ID},
            ],
            BROKEN5_ID: [  # đủ 2 GL rồi -> chỉ còn thiếu ReasonTypeID của Master
                {"GeneralLedgerID": 9, "RefID": BROKEN5_ID}, {"GeneralLedgerID": 10, "RefID": BROKEN5_ID},
            ],
            BROKEN6_ID: [  # đủ 2 GL rồi -> chỉ còn thiếu BankAccountID+BankName của Master
                {"GeneralLedgerID": 11, "RefID": BROKEN6_ID}, {"GeneralLedgerID": 12, "RefID": BROKEN6_ID},
            ],
        }
        self.aol_by_refid = {
            REAL_ID: {"AccountObjectLedgerID": 1, "RefID": REAL_ID, "RefDetailID": "real-d",
                      "AccountNumber": "131", "DebitAmountOC": 0, "DebitAmount": 0,
                      "CreditAmountOC": 999, "CreditAmount": 999, "JournalMemo": "m", "Description": "m",
                      "AccountObjectID": "real-aid", "AccountObjectCode": "RC", "AccountObjectName": "R",
                      "AccountObjectNameDI": "R", "AccountObjectTaxCode": "RT", "BranchID": "b1",
                      "RefOrder": 1, "PayKeyID": "x", "DebtKeyID": "y", "EntryType": 2},
        }
        self.bdwl_by_refid = {
            REAL_ID: {"RefID": REAL_ID, "PostedDate": datetime.datetime(2025,1,1),
                      "RefDate": datetime.datetime(2025,1,1), "RefNoFinance": "R1",
                      "RefNoManagement": None, "IsPostedFinance": True, "IsPostedManagement": False,
                      "AccountObjectID": "real-aid", "AccountObjectName": "R", "BranchID": "b1",
                      "JournalMemo": "m", "TotalAmountOC": 999, "TotalAmount": 999, "RefOrder": 1,
                      "CreatedDate": datetime.datetime(2025,1,1), "ModifiedDate": datetime.datetime(2025,1,1),
                      "CustomField10": None, "BAType": 0, "ListTableName": "BADeposit"},
        }
        self.cfl_by_refid = {
            REAL_ID: {"CustomFieldLegerID": "real-cfl", "RefDetailID": "real-d", "RefID": REAL_ID,
                      "IsPostToManagementBook": False, "BranchID": "b1",
                      "PostedDate": datetime.datetime(2025,1,1), "IsUpdateRedundant": True},
        }
        # BROKEN2 đã có đủ GeneralLedger/AccountObjectLedger (sửa từ đợt 2) nhưng CHƯA có
        # BADepositWithdrawList/CustomFieldLedger (đợt 3 mới phát hiện) -> vẫn phải sửa bổ sung
        # riêng 2 bảng này, không được bỏ qua toàn bộ chỉ vì GeneralLedger đã đủ.
        self.bdwl_count = {BROKEN3_ID: 1, BROKEN4_ID: 1, BROKEN5_ID: 1, BROKEN6_ID: 1}
        self.cfl_count = {BROKEN3_ID: 1, BROKEN4_ID: 1, BROKEN5_ID: 1, BROKEN6_ID: 1}
        # Đợt 7: bug ẩn từ đầu — GeneralLedger/AccountObjectLedger/BADepositWithdrawList đã ghi
        # từ trước có RefType=0 (đúng phải là 1500/1510), không bao giờ được sửa vì logic cũ chỉ
        # THÊM dòng còn thiếu, không sửa dòng đã có. Giả lập: 3 dòng GL + 1 dòng AOL + 2 dòng BDWL
        # đang sai RefType trên toàn bộ các chứng từ phần mềm ghi.
        self.reftype_wrong_count = {"GeneralLedger": 3, "AccountObjectLedger": 1, "BADepositWithdrawList": 2}
        # BROKEN5: BankName đúng cả 2 bảng (không mượn qua bdwl_row_bank) nhưng ReasonTypeID=null.
        self.bdwl_row_bank.setdefault(BROKEN5_ID, ("Ngân hàng ABC", "bank-1"))
        # BROKEN6: BDWL của nó đã hợp lệ sẵn (bank + reason) — cô lập lỗi chỉ ở Master (thiếu CẢ
        # HAI BankAccountID/BankName), không để can_sua_bank_bdwl/can_sua_reason_bdwl ăn theo.
        self.bdwl_row_bank.setdefault(BROKEN6_ID, ("Ngân hàng ABC", "bank-1"))
        self.bdwl_row_reason = {BROKEN5_ID: (34,), BROKEN6_ID: (34,)}  # BDWL của BROKEN5/6 đã đúng, chỉ Master thiếu
        self.inserted = {"GeneralLedger": [], "AccountObjectLedger": [],
                         "BADepositWithdrawList": [], "CustomFieldLedger": []}
        self.updates = []

    def execute(self, sql, *params):
        params = params[0] if len(params) == 1 and isinstance(params[0], (tuple, list)) else params
        self._last_sql = sql
        self._last_params = params
        if sql.startswith("UPDATE"):
            self.updates.append((sql, params))
        elif sql.startswith("INSERT INTO"):
            table = sql.split(" ")[2]
            self.inserted.setdefault(table, []).append(params)
        return self

    def fetchall(self):
        sql = self._last_sql
        if sql.startswith("SELECT [") and "FROM BADeposit WHERE" in sql:
            return [tuple(self.master_rows[BROKEN1_ID].values()),
                    tuple(self.master_rows[BROKEN2_ID].values()),
                    tuple(self.master_rows[BROKEN3_ID].values()),
                    tuple(self.master_rows[BROKEN4_ID].values()),
                    tuple(self.master_rows[BROKEN5_ID].values()),
                    tuple(self.master_rows[BROKEN6_ID].values())]
        if "FROM GeneralLedger WHERE RefID=?" in sql:
            refid = self._last_params[0]
            return [tuple(row.values()) for row in self.gl_by_refid.get(refid, [])]
        return []

    def fetchone(self):
        sql = self._last_sql
        if sql.startswith("SELECT COUNT(*) FROM SYSVoucherTemplate"):
            # Gia lap: chi 34 la VoucherType hop le cho RefType=1500 (mo phong SYSVoucherTemplate
            # that cua MISA, xem chan_doan_1ct_unt).
            reftype_p, voucher_p = self._last_params
            return (1,) if (reftype_p == 1500 and voucher_p == 34) else (0,)
        if "JOIN" in sql and "RefType" in sql:
            return self.fetchone_reftype_count(sql)
        if sql.startswith("SELECT COUNT(*) FROM GeneralLedger"):
            refid = self._last_params[0]
            return (len(self.gl_by_refid.get(refid, [])),)
        if sql.startswith("SELECT COUNT(*) FROM BADepositWithdrawList"):
            refid = self._last_params[0]
            return (self.bdwl_count.get(refid, 0),)
        if sql.startswith("SELECT COUNT(*) FROM CustomFieldLedger"):
            refid = self._last_params[0]
            return (self.cfl_count.get(refid, 0),)
        if sql.startswith("SELECT [") and "FROM BADepositDetail WHERE RefID=?" in sql:
            refid = self._last_params[0]
            d = self.detail_rows.get(refid)
            return tuple(d.values()) if d else None
        if "FROM AccountObjectLedger WHERE RefID=?" in sql:
            refid = self._last_params[0]
            row = self.aol_by_refid.get(refid)
            return tuple(row.values()) if row else None
        if sql.startswith("SELECT BankName, BankAccountID FROM BADepositWithdrawList"):
            refid = self._last_params[0]
            return self.bdwl_row_bank.get(refid)
        if sql.startswith("SELECT ReasonTypeID FROM BADepositWithdrawList"):
            refid = self._last_params[0]
            return self.bdwl_row_reason.get(refid)
        if "FROM BADepositWithdrawList WHERE RefID=?" in sql:
            refid = self._last_params[0]
            row = self.bdwl_by_refid.get(refid)
            return tuple(row.values()) if row else None
        if "FROM CustomFieldLedger WHERE RefID=?" in sql:
            refid = self._last_params[0]
            row = self.cfl_by_refid.get(refid)
            return tuple(row.values()) if row else None
        if sql.startswith("SELECT AccountObjectCode"):
            return ("ACC1", "0311111111")
        if "MAX(RefOrder" in sql:
            return (11,)
        if "FROM BADeposit WHERE BankAccountID IS NOT NULL AND BankName IS NOT NULL" in sql:
            return ("bank-1", "Ngân hàng ABC")
        if sql.startswith("SELECT TOP 1 ReasonTypeID FROM BADeposit WHERE ReasonTypeID IS NOT NULL AND ReasonTypeID<>0"):
            return (34,)
        return None

    def fetchone_reftype_count(self, sql):
        # Đợt 7: giả lập đếm số dòng RefType sai (=0) qua JOIN — mô phỏng đơn giản, không thực sự
        # chạy JOIN, chỉ trả về số đếm CỐ ĐỊNH đã set sẵn theo tên bảng để kiểm chứng logic gọi
        # đúng SQL COUNT rồi UPDATE, không kiểm chứng cú pháp T-SQL (không thể mô phỏng JOIN thật
        # trong mock Python đơn giản này).
        for ten_bang, dem in self.reftype_wrong_count.items():
            if f"FROM {ten_bang} t JOIN" in sql:
                return (dem,)
        return None

class FakeConn:
    def __init__(self, cur): self._cur = cur; self.autocommit = True
    def cursor(self): return self._cur
    def commit(self): self.committed = True
    def rollback(self): self.rolled_back = True
    def close(self): pass

cur = FakeCursor()
def fake_sql_connect(cid, database=None):
    return FakeConn(cur)

ns['_misa_cot_bang_that'] = fake_cot_bang_that
ns['_misa_mau_dong_that'] = fake_mau_dong_that
ns['_misa_sql_connect'] = fake_sql_connect
exec(extract_fn('_misa_sua_ghi_so_unt_unc_cu'), ns)
_misa_sua_ghi_so_unt_unc_cu = ns['_misa_sua_ghi_so_unt_unc_cu']

r = _misa_sua_ghi_so_unt_unc_cu(1, "TESTDB", "unt", preview=False)
print("Result:", r)
# BROKEN1 (thiếu tất cả) + BROKEN2 (thiếu BDWL/CFL) + BROKEN3 (Master.BankName=null) + BROKEN4
# (BADepositWithdrawList.BankName=null, đợt 5) + BROKEN5 (Master.ReasonTypeID=null, đợt 6 — cột
# INT bị bỏ sót vì công cụ chẩn đoán chỉ soát nvarchar) + BROKEN6 (Master thiếu CẢ HAI
# BankAccountID+BankName, đợt 9 — gap cũ: chỉ sửa được khi BankAccountID đã có sẵn) đều phải sửa.
assert r["so_se_sua"] == 6, f"expected 6 fixed (BROKEN1..6), got {r['so_se_sua']}"
assert len(cur.inserted["GeneralLedger"]) == 2, f"expected 2 GL inserts (chỉ BROKEN1), got {len(cur.inserted['GeneralLedger'])}"
assert len(cur.inserted["AccountObjectLedger"]) == 1, "chỉ BROKEN1 (BROKEN2 đã có AOL từ trước)"
assert len(cur.inserted["BADepositWithdrawList"]) == 2, "cả BROKEN1 và BROKEN2 đều thiếu BDWL"
assert len(cur.inserted["CustomFieldLedger"]) == 2, "cả BROKEN1 và BROKEN2 đều thiếu CFL"
print("PASS: BROKEN1 được sửa đủ 4 bảng, BROKEN2 chỉ được bổ sung BADepositWithdrawList/CustomFieldLedger (không tạo trùng GL/AOL)")

bdwl_cols = list(cur.bdwl_by_refid[REAL_ID].keys())
bdwl_refids = {dict(zip(bdwl_cols, p))["RefID"] for p in cur.inserted["BADepositWithdrawList"]}
assert bdwl_refids == {BROKEN1_ID, BROKEN2_ID}
print("PASS: BADepositWithdrawList ghi đúng cho cả 2 chứng từ còn thiếu")

gl_cols = list(cur.gl_by_refid[REAL_ID][0].keys())
by_acc = {}
for p in cur.inserted["GeneralLedger"]:
    d = dict(zip(gl_cols, p))
    by_acc[d["AccountNumber"]] = d
assert by_acc["1121"]["DebitAmountOC"] == 100000 and by_acc["1121"]["CreditAmountOC"] == 0
assert by_acc["131"]["CreditAmountOC"] == 100000 and by_acc["131"]["DebitAmountOC"] == 0
assert by_acc["1121"]["RefID"] == BROKEN1_ID
print("PASS: correct amounts assigned to correct account sides, RefID correctly points to broken row")

bankname_updates_master = [u for u in cur.updates if u[0].startswith(f"UPDATE BADeposit SET BankName=?")]
bankname_updates_bdwl = [u for u in cur.updates if u[0].startswith("UPDATE BADepositWithdrawList SET BankName=?")]
bankaccountid_updates_master = [u for u in cur.updates if u[0].startswith("UPDATE BADeposit SET BankAccountID=?")]
assert len(bankname_updates_master) == 2, f"expected exactly 2 Master BankName UPDATE (BROKEN3+BROKEN6), got {len(bankname_updates_master)}"
bankname_master_refids = {p[1] for _, p in bankname_updates_master}
assert bankname_master_refids == {BROKEN3_ID, BROKEN6_ID}
assert len(bankname_updates_bdwl) == 1, f"expected exactly 1 BDWL BankName UPDATE (chỉ BROKEN4), got {len(bankname_updates_bdwl)}"
assert bankname_updates_bdwl[0][1] == ("Ngân hàng ABC", BROKEN4_ID)
bankaccountid_master_refids = {p[1] for _, p in bankaccountid_updates_master}
assert bankaccountid_master_refids == {BROKEN3_ID, BROKEN6_ID}, (
    f"expected Master BankAccountID UPDATE cho cả BROKEN3 (mã ngân hàng cũ 'bank-3' vẫn bị ghi đè "
    f"đồng bộ theo BankName mượn được, vì code hiện ghi đè cả 2 cột 1 lần khi 1 trong 2 thiếu) và "
    f"BROKEN6 (đợt 9), got {bankaccountid_master_refids}")
for _, p in bankaccountid_updates_master:
    assert p[0] == "bank-1"
gl_inserted_refids = {dict(zip(gl_cols, p))["RefID"] for p in cur.inserted["GeneralLedger"]}
assert BROKEN3_ID not in gl_inserted_refids and BROKEN4_ID not in gl_inserted_refids and BROKEN6_ID not in gl_inserted_refids, \
    "BROKEN3/BROKEN4/BROKEN6 đã có đủ GL rồi, không được ghi trùng"
bdwl_inserted_refids = {dict(zip(bdwl_cols, p))["RefID"] for p in cur.inserted["BADepositWithdrawList"]}
assert BROKEN3_ID not in bdwl_inserted_refids and BROKEN4_ID not in bdwl_inserted_refids and BROKEN6_ID not in bdwl_inserted_refids, \
    "BROKEN3/BROKEN4/BROKEN6 đã có đủ BDWL rồi, không được ghi trùng (chỉ UPDATE cột BankName/BankAccountID, không INSERT thêm dòng)"
print("PASS: BROKEN3 sửa đúng Master.BankName, BROKEN4 sửa đúng BADepositWithdrawList.BankName, "
      "BROKEN6 sửa đúng CẢ HAI Master.BankAccountID+BankName — không ghi trùng GL/BDWL nào")

reason_updates_master = [u for u in cur.updates if u[0].startswith("UPDATE BADeposit SET ReasonTypeID=?")]
reason_updates_bdwl = [u for u in cur.updates if u[0].startswith("UPDATE BADepositWithdrawList SET ReasonTypeID=?")]
assert len(reason_updates_master) == 1, f"expected exactly 1 Master ReasonTypeID UPDATE (chỉ BROKEN5), got {len(reason_updates_master)}"
assert reason_updates_master[0][1] == (34, BROKEN5_ID)
assert len(reason_updates_bdwl) == 0, "BDWL của BROKEN5 đã đúng ReasonTypeID rồi, không được UPDATE thừa"
assert BROKEN5_ID not in gl_inserted_refids and BROKEN5_ID not in bdwl_inserted_refids, \
    "BROKEN5 đã có đủ GL/BDWL rồi, không được ghi trùng"
print("PASS: BROKEN5 (chỉ thiếu Master.ReasonTypeID) được sửa ĐÚNG 1 cột, không đụng BDWL/GL")

assert BROKEN6_ID not in {p[1] for _, p in reason_updates_master} and \
    BROKEN6_ID not in {p[1] for _, p in reason_updates_bdwl}, \
    "BROKEN6 đã có ReasonTypeID=34 hợp lệ sẵn (Master lẫn BDWL) — không được UPDATE ReasonTypeID thừa, chỉ sửa Bank*"
print("PASS: BROKEN6 chỉ bị sửa Bank*, không đụng ReasonTypeID vốn đã hợp lệ")

# --- Đợt 7: bulk-sửa RefType sai (=0) trên GL/AOL/BDWL đã ghi từ trước — không phụ thuộc vào
# per-row loop (chạy 1 lần, độc lập, luôn tính vào kết quả trả về để frontend không bỏ qua nhầm
# như đã từng xảy ra với BankName/ReasonTypeID).
assert r["so_sua_reftype"] == 3 + 1 + 2, f"expected tong 6 dong RefType sai duoc dem, got {r['so_sua_reftype']}"
reftype_updates_by_table = [u for u in cur.updates if u[0].startswith("UPDATE t SET t.RefType=?")]
assert len(reftype_updates_by_table) == 3, f"expected 3 UPDATE statements (1 moi bang GL/AOL/BDWL), got {len(reftype_updates_by_table)}"
bang_da_update = set()
for sql, params in reftype_updates_by_table:
    assert params == (1500, "HDDT-AUTO", 1500), f"tham so UPDATE RefType sai: {params}"
    for ten_bang in ("GeneralLedger", "AccountObjectLedger", "BADepositWithdrawList"):
        if f"FROM {ten_bang} t JOIN" in sql:
            bang_da_update.add(ten_bang)
            break
    else:
        raise AssertionError(f"khong nhan dien duoc bang trong SQL: {sql}")
assert bang_da_update == {"GeneralLedger", "AccountObjectLedger", "BADepositWithdrawList"}
print("PASS: bulk-sua RefType sai dem dung 6 dong (3 GL + 1 AOL + 2 BDWL) va UPDATE dung tham so cho ca 3 bang")

print("\nALL DONE")
