import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import datetime, sqlite3, json
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


ns = {'datetime': datetime, 'HTTPException': FakeHTTPException, 'json': __import__('json')}
for fn in ("_misa_cot_bang_that", "_misa_chon_cot", "_misa_khncc_chuan_mst",
           "_mo_ta_trang_thai", "_mo_ta_ket_qua", "_snum", "_to_num",
           "_ky_hieu_chac_chan_khac", "_misa_doi_chieu_import_toan_bo"):
    exec(extract_fn(fn), ns)
ns['TTHAI_DESC'] = {
    "1": "Hóa đơn mới", "2": "Hóa đơn thay thế", "3": "Hóa đơn điều chỉnh",
    "4": "Hóa đơn đã bị thay thế", "5": "Hóa đơn đã bị điều chỉnh", "6": "Hóa đơn hủy",
}
ns['TTXLY_DESC'] = {"4": "Hóa đơn không đủ điều kiện cấp mã", "5": "Đã cấp mã hóa đơn"}
# _mo_ta_trang_thai/_mo_ta_ket_qua đọc TTHAI_DESC/TTXLY_DESC từ module-level
# scope của CHÍNH chúng (đã exec riêng ở trên) -> gán lại đúng namespace đó.
exec("TTHAI_DESC=" + repr(ns['TTHAI_DESC']), ns)
exec("TTXLY_DESC=" + repr(ns['TTXLY_DESC']), ns)
_misa_doi_chieu_import_toan_bo = ns['_misa_doi_chieu_import_toan_bo']


def _sqlite_voi(rows_seed):
    """Dựng CSDL SQLite in-memory mô phỏng bảng 'invoices' của phần mềm
    (dữ liệu GỐC tra cứu từ Tổng cục Thuế) từ danh sách rows_seed."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
    CREATE TABLE invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, loai TEXT,
        nbmst TEXT, nbten TEXT, nmmst TEXT, khhdon TEXT, shdon TEXT, tdlap TEXT,
        tgtcthue REAL, tgtthue REAL, tthai TEXT, raw TEXT
    );
    """)
    for loai, nbmst, nmmst, khhdon, shdon, tdlap, ds, thue, tthai in rows_seed:
        conn.execute(
            "INSERT INTO invoices (company_id, loai, nbmst, nmmst, khhdon, shdon, tdlap, tgtcthue, "
            "tgtthue, tthai, raw) VALUES (1,?,?,?,?,?,?,?,?,?,?)",
            (loai, nbmst, nmmst, khhdon, shdon, tdlap, ds, thue, tthai, json.dumps({"ttxly": "5"})))
    conn.commit()
    return conn


class FakeCursorMisa:
    def __init__(self, sav_rows, pui_rows, psd_rows):
        self._sav_rows = sav_rows
        self._pui_rows = pui_rows
        self._psd_rows = psd_rows

    def execute(self, sql, params=()):
        p = params if isinstance(params, (tuple, list)) else (params,) if params != () else ()
        if "sys.columns c" in sql and "sys.types ty" in sql:
            table = p[0]
            cols = {
                "SAVoucher": [("AccountObjectTaxCode", "nvarchar"), ("InvNo", "nvarchar"),
                             ("InvSeries", "nvarchar"), ("TotalAmount", "money"),
                             ("TotalVATAmount", "money")],
                "PUInvoice": [("AccountObjectTaxCode", "nvarchar"), ("InvNo", "nvarchar"),
                             ("TotalTurnoverAmount", "money"), ("TotalVATAmount", "money")],
                "PUServiceDetail": [("TaxAccountObjectTaxCode", "nvarchar"), ("InvNo", "nvarchar"),
                                   ("Amount", "money"), ("VATAmount", "money")],
            }
            self._result = cols.get(table, [])
        elif "FROM SAVoucher WHERE ISNULL" in sql:
            self._result = self._sav_rows
        elif "FROM PUInvoice WHERE ISNULL" in sql:
            self._result = self._pui_rows
        elif "FROM PUServiceDetail WHERE ISNULL" in sql:
            self._result = self._psd_rows
        else:
            self._result = []
        return self

    def fetchone(self):
        return self._result[0] if self._result else None

    def fetchall(self):
        return self._result


class FakeConnMisa:
    def __init__(self, cur):
        self._cur = cur
    def cursor(self):
        return self._cur
    def close(self):
        pass


def chay(rows_seed, sav_rows, pui_rows=(), psd_rows=()):
    conn = _sqlite_voi(rows_seed)
    ns['db'] = lambda: conn
    ns['_misa_sql_connect'] = lambda cid, database=None: FakeConnMisa(
        FakeCursorMisa(list(sav_rows), list(pui_rows), list(psd_rows)))
    r = _misa_doi_chieu_import_toan_bo(1, "TESTDB")
    conn.close()
    return r


CTY_MST = "0312320573"
MAC_MST = "0314263169"

# ══════════════════════════════════════════════════════════════════════
# TEST 1 — TỔNG KHÔNG khớp (thiếu thật 1 hóa đơn) -> phải drill-down tìm
# ĐÚNG hóa đơn gây lệch, và KHÔNG được kéo theo báo sai các hóa đơn khác
# chỉ vì khóa ghép (Ký hiệu HĐ/số 0 đầu Số hóa đơn) lệch định dạng.
# Bối cảnh: HĐ 28/29/30 (bán hàng) cùng ngày 19/11/2025, HĐ 29 bị "sót"
# khi ghi vào MISA; KH "MAC MARKETING" (MST 0314263169) có 2 hóa đơn KHÁC
# NHAU HOÀN TOÀN (khác ngày, khác tiền) nhưng CÙNG Số HĐ=29 vì khác Ký
# hiệu (1C25TKK 19/11/2025 và 1C26TKK 12/02/2026) — MISA CHỈ có 1C26TKK,
# THIẾU thật 1C25TKK. Đồng thời trộn thêm 3 hóa đơn ĐÃ CÓ trong MISA
# nhưng khóa ghép lệch định dạng (12: Ký hiệu MISA rỗng; 42: Ký hiệu MISA
# "C25TKK" khác "1C25TKK" ở nguồn; 17: Số HĐ nguồn "0000017" có số 0 đầu
# khác MISA "17") để xác nhận khi TỔNG đã lệch thật, bước drill-down vẫn
# phải nhận diện đúng các hóa đơn ĐÃ khớp này là khớp, không báo nhầm.
# ══════════════════════════════════════════════════════════════════════
rows_1 = [
    ("sold", CTY_MST, "0111111111", "1C25TKK", "28", "2025-11-19T00:00:00", 2000000, 100000, "1"),
    ("sold", CTY_MST, "0333333333", "1C25TKK", "30", "2025-11-19T00:00:00", 1000000, 50000, "1"),
    # HĐ đã bị thay thế (tthai=4) -> KHÔNG được tính là "thiếu" dù không có trong MISA
    ("sold", CTY_MST, "0444444444", "1C25TKK", "17", "2025-10-20T00:00:00", 500000, 25000, "4"),
    # Đúng kịch bản thật: KH MAC MARKETING, 2 hóa đơn KHÁC NHAU cùng Số
    # HĐ=29, khác Ký hiệu — MISA CHỈ có 1C26TKK (ghi đúng), THIẾU 1C25TKK.
    ("sold", CTY_MST, MAC_MST, "1C25TKK", "29", "2025-11-19T00:00:00", 12000000, 960000, "1"),
    ("sold", CTY_MST, MAC_MST, "1C26TKK", "29", "2026-02-12T00:00:00", 21600000, 1728000, "1"),
    # HĐ 12: ĐÃ CÓ trong MISA nhưng InvSeries đọc ra RỖNG (dữ liệu cũ)
    ("sold", CTY_MST, "0888888888", "1C25TKK", "12", "2025-11-05T00:00:00", 3000000, 300000, "1"),
    # HĐ 42: khách lẻ (MST rỗng), Ký hiệu HĐ ghi nhận LỆCH ĐỊNH DẠNG
    ("sold", CTY_MST, "", "1C25TKK", "42", "2025-12-09T00:00:00", 720000, 36000, "1"),
    # HĐ 17b: Số hóa đơn nguồn có số 0 đầu, MISA không có
    ("sold", CTY_MST, "", "1C25TKK", "0000017", "2025-10-25T00:00:00", 575000, 28750, "1"),
    # Mua hàng nhập kho -> khớp đúng qua PUInvoice
    ("purchase", "0555555555", CTY_MST, "1C25ABC", "77", "2025-11-10T00:00:00", 4000000, 400000, "1"),
    # Mua hàng dịch vụ, 1 hóa đơn NHƯNG 2 dòng TK chi phí khác nhau trong MISA -> cộng dồn khớp
    ("purchase", "0666666666", CTY_MST, "1C25ABC", "88", "2025-11-12T00:00:00", 1200000, 120000, "1"),
    # Mua hàng LỆCH số tiền (sửa tay 1 bên)
    ("purchase", "0777777777", CTY_MST, "1C25ABC", "99", "2025-11-14T00:00:00", 2500000, 250000, "1"),
]
sav_1 = [
    ("0111111111", "28", "1C25TKK", 2100000, 100000),
    ("0333333333", "30", "1C25TKK", 1050000, 50000),
    # ĐÚNG kịch bản thật: chỉ ghi được 1C26TKK/29, 1C25TKK/29 THIẾU thật
    (MAC_MST, "29", "1C26TKK", 23328000, 1728000),
    ("0888888888", "12", "", 3300000, 300000),
    ("", "42", "C25TKK", 756000, 36000),
    ("", "17", "1C25TKK", 603750, 28750),
]
pui_1 = [("0555555555", "77", 4000000, 400000)]
psd_1 = [
    ("0666666666", "88", 700000, 70000),
    ("0666666666", "88", 500000, 50000),
    ("0777777777", "99", 2000000, 200000),
]
r1 = chay(rows_1, sav_1, pui_1, psd_1)

bh1 = r1["ban_hang"]
assert bh1["tong_khop"] is False, (
    f"Tổng doanh số/thuế Bán hàng THẬT SỰ lệch (thiếu 12.000.000/960.000 của HĐ 29/1C25TKK) -> "
    f"tong_khop phải là False để kích hoạt drill-down — got {bh1}")
assert bh1["tong_hd_nguon"] == 7 and bh1["khop"] == 6, (
    f"7 HĐ bán hàng hợp lệ, 6 khớp (chỉ 29/1C25TKK thiếu thật) — got {bh1}")
assert len(bh1["thieu"]) == 1 and bh1["thieu"][0]["so_hd"] == "29", (
    f"Drill-down phải phát hiện ĐÚNG HĐ 29/1C25TKK (19/11/2025) THIẾU trong MISA — KHÔNG được gộp "
    f"nhầm với 29/1C26TKK (đã có) — và KHÔNG được kéo theo báo sai 12/42/17 chỉ vì khóa lệch định "
    f"dạng — got {bh1['thieu']}")
assert bh1["thieu"][0]["doanh_so_nguon"] == 12000000 and bh1["thieu"][0]["thue_nguon"] == 960000
assert len(bh1["lech"]) == 0, f"Không hóa đơn nào bị LỆCH số tiền trong kịch bản này — got {bh1['lech']}"
print("PASS: Test 1 — Tổng Bán hàng lệch THẬT (thiếu 12.000.000/960.000) -> tong_khop=False, "
      "drill-down tìm ĐÚNG hóa đơn 29/1C25TKK thiếu, không báo nhầm 12/42/17 (khóa lệch định dạng "
      "Ký hiệu HĐ/số 0 đầu Số hóa đơn nhưng đã có thật trong MISA).")

mh1 = r1["mua_hang"]
assert mh1["tong_khop"] is False, f"Mua hàng lệch thật (HĐ 99 lệch 500.000/50.000) — got {mh1}"
assert mh1["tong_hd_nguon"] == 3 and mh1["khop"] == 2
assert len(mh1["lech"]) == 1 and mh1["lech"][0]["so_hd"] == "99"
assert mh1["lech"][0]["doanh_so_misa"] == 2000000 and mh1["lech"][0]["thue_misa"] == 200000
print("PASS: Test 1 — Mua hàng: HĐ 77 (PUInvoice) + HĐ 88 (PUServiceDetail 2 dòng cộng dồn) khớp; "
      "tổng lệch thật do HĐ 99 -> drill-down tìm đúng HĐ 99 bị lệch số tiền.")

assert r1["doc_duoc"]["ban_hang"] and r1["doc_duoc"]["mua_hang_nk_kqk"] and r1["doc_duoc"]["mua_hang_dv"]
print("PASS: Test 1 — dò đủ cột cả 3 bảng MISA (SAVoucher/PUInvoice/PUServiceDetail).")


# ══════════════════════════════════════════════════════════════════════
# TEST 2 — TỔNG khớp đúng (theo yêu cầu người dùng: "chỉ cần kiểm tra
# tổng giá trị nếu khớp thì không cần hiện"). Cố tình dựng 1 hóa đơn MISA
# có khóa (MST, Số hóa đơn) HOÀN TOÀN không thể ghép được với nguồn (InvNo
# ghi hẳn 1 chuỗi khác chứ không chỉ lệch định dạng nhẹ) NHƯNG số tiền
# đúng nên TỔNG 2 bên vẫn khớp — phải xác nhận: khi tổng đã khớp, bảng
# đối chiếu KHÔNG chạy drill-down (nên KHÔNG hiện thieu/lech), dù nếu có
# chạy drill-down cũng sẽ báo sai "thiếu" do khóa không ghép được.
# ══════════════════════════════════════════════════════════════════════
rows_2 = [
    ("sold", CTY_MST, "0999999999", "1C25XXX", "50", "2026-01-10T00:00:00", 1000000, 100000, "1"),
    ("purchase", "0888800000", CTY_MST, "1C25YYY", "60", "2026-01-12T00:00:00", 2000000, 200000, "1"),
]
sav_2 = [
    # InvNo ghi trong MISA KHÔNG PHẢI "50" mà là 1 chuỗi hoàn toàn khác
    # (mô phỏng lỗi ghi/đọc cột InvNo không thể khắc phục bằng chuẩn hóa
    # định dạng) — nhưng SỐ TIỀN đúng nên khi cộng vào TỔNG vẫn khớp.
    ("0999999999", "MACH-KHAC-50", "1C25ZZZ", 1100000, 100000),
]
pui_2 = [
    ("0888800000", "MACH-KHAC-60", 2000000, 200000),
]
r2 = chay(rows_2, sav_2, pui_2, [])

bh2 = r2["ban_hang"]
assert bh2["tong_khop"] is True, (
    f"Tổng doanh số/thuế Bán hàng ĐÃ khớp (1.000.000/100.000 cả 2 bên) dù khóa InvNo hoàn toàn khác "
    f"nhau ('50' vs 'MACH-KHAC-50') -> tong_khop phải True — got {bh2}")
assert bh2["thieu"] == [] and bh2["lech"] == [], (
    f"Theo đúng yêu cầu: khi TỔNG đã khớp thì KHÔNG hiện thieu/lech, dù nếu chạy drill-down theo "
    f"khóa (MST, Số HĐ) sẽ báo sai '50' là THIẾU (vì InvNo MISA ghi khác hẳn) — got {bh2}")
assert bh2["khop"] == bh2["tong_hd_nguon"] == 1
print("PASS: Test 2 — Bán hàng: tổng khớp (1.000.000/100.000) dù khóa InvNo hoàn toàn không ghép "
      "được ('50' vs 'MACH-KHAC-50') -> KHÔNG chạy drill-down, KHÔNG hiện gì cho người dùng — đúng "
      "yêu cầu 'chỉ cần kiểm tra tổng giá trị, nếu khớp thì không cần hiện'.")

mh2 = r2["mua_hang"]
assert mh2["tong_khop"] is True and mh2["thieu"] == [] and mh2["lech"] == []
print("PASS: Test 2 — Mua hàng: tổng khớp (2.000.000/200.000) dù khóa InvNo khác hẳn -> không hiện gì.")

print("\nALL DONE")
