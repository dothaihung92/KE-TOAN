import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: _misa_ghi_mua_hang (nk/kqk) và _misa_ghi_mua_hang_dv đối
chiếu THEO NỘI DUNG (MST NCC, Số HĐ) THẬT, và khi đối chiếu được thì PHẢI TIN
HẲN kết quả đó — KHÔNG được để "Số chứng từ" (k_doc, tự đặt theo thứ tự xử
lý, dễ trùng nhầm giữa các lần tạo Bảng kê Đầu vào khác nhau) chặn lại 1 hóa
đơn mà đối chiếu nội dung đã xác nhận là MỚI.

Đúng ca thật người dùng báo cáo: hóa đơn 3381 (MST 0317743519) ĐÃ có trong
Bảng kê Đầu vào (xác nhận qua ảnh chụp + đã bấm Lưu, 197 dòng) và XÁC NHẬN
THẬT SỰ CHƯA có trong MISA (đối chiếu qua file Excel Mua hàng thật, chỉ thấy
3306/3307/3397/3398/3434-3436/3449-3452/3460 của cùng NCC, KHÔNG có 3381) —
nhưng "Xem trước" vẫn báo "Sẽ ghi: 0" TUYỆT ĐỐI KHÔNG ĐỔI qua nhiều lần chạy
lại, kể cả sau khi thêm bước đối chiếu theo nội dung (PR trước) — vì PR đó
chỉ THÊM 1 điều kiện "trùng" mới, chưa VÔ HIỆU HOÁ điều kiện "trùng" CŨ (theo
k_doc/"Số chứng từ") — nếu "Số chứng từ" tính ra cho hóa đơn 3381 tình cờ
trùng với 1 "Số chứng từ" đã có trong MISA (của 1 hóa đơn KHÁC, do đổi thứ tự
xử lý giữa các lần tạo Bảng kê), điều kiện CŨ vẫn chặn nó lại y hệt như trước,
dù điều kiện MỚI đã xác nhận đúng đây là hóa đơn CHƯA CÓ."""
import sys, textwrap, datetime
sys.path.insert(0, _REPO_ROOT)
import server


def extract(start_marker, end_marker):
    src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()
    i0 = src.index(start_marker)
    i0 = src.rfind("\n", 0, i0) + 1
    i1 = src.index(end_marker, i0)
    return textwrap.dedent(src[i0:i1])


class FakeCursor:
    """rows: dòng PUInvoice (2-tuple (mst,inv), tự thêm RefID; hoặc PUServiceDetail
    tùy hàm gọi). Mô phỏng LUÔN PUVoucher liên kết HIỆN RÕ (PostedDate có, đúng
    chi nhánh 'BR1', DisplayOnBook=0) — test này không nhắm vào tính năng kiểm
    tra 'hiện rõ trên MISA' (xem test_ghi_mua_hang_hd_an_view.py riêng), nên giữ
    dữ liệu PUVoucher 'bình thường, hợp lệ' để không đổi kết quả gốc của test."""
    def __init__(self, rows):
        self._rows = [(f"inv-{i}",) + tuple(r) for i, r in enumerate(rows)]

    def execute(self, sql, *a):
        self._sql = sql
        self._params = a
        return self

    def fetchall(self):
        # sys.columns (dò cột NGÀY qua _misa_cot_bang_that) -> KHÔNG phải dữ
        # liệu PUInvoice thật, trả RỖNG (giống CSDL không dò được cột ngày —
        # test này không nhắm vào tính năng lọc theo ngày, xem
        # test_mua_hang_nk_ghi_so.py cho ca đó).
        if "sys.columns" in self._sql:
            return []
        return self._rows

    def fetchone(self):
        if "PUVoucherRefID FROM PUInvoiceDetail" in self._sql:
            return ("pu-fake",)
        if "FROM PUVoucher WHERE RefID" in self._sql:
            import datetime as _dt
            return (_dt.datetime(2026, 1, 1), "BR1", 0, "", "chung-tu-khac-khong-lien-quan")
        return None


def chay_nk(pu_invoice_rows, mst_dg, sohd_dg, k_doc_gia_lap, posted_refno=None, unposted_docs=None, ghi_de=False):
    block = extract(
        '        # ĐỐI CHIẾU THEO NỘI DUNG HÓA ĐƠN (MST NCC + Số HĐ), KHÔNG CHỈ THEO',
        '            if mst_k not in ncc:')
    ns = {
        "_misa_khncc_chuan_mst": server._misa_khncc_chuan_mst,
        "_chuan_shd": server._chuan_shd,
        "_misa_chon_cot": server._misa_chon_cot,
        "_misa_cot_bang_that": server._misa_cot_bang_that,
        "datetime": datetime,
        "_PM_MARK": server._PM_MARK,
        "branch_id": "BR1",
        "preview": False,
        "cur": FakeCursor(pu_invoice_rows),
        "loai": "nk",
        # "doc" tính sao cho k_doc.strip().lower() == k_doc_gia_lap — dùng
        # ĐÚNG giá trị giả lập tình huống "Số chứng từ" trùng nhầm với 1 hóa
        # đơn KHÁC (không liên quan gì tới nội dung hóa đơn 3381 đang xét).
        "order": [k_doc_gia_lap],
        "groups": {k_doc_gia_lap: [{"mst": mst_dg, "sohd": sohd_dg}]},
        "cfg": {"mst": "mst", "sohd": "sohd"},
        "posted_refno": posted_refno if posted_refno is not None else set(),
        "unposted_docs": unposted_docs if unposted_docs is not None else {},
        "ghi_de": ghi_de,
        "trung": 0,
        "ket": [],
    }
    exec(compile(block, "<ghi_mua_hang_nk>", "exec"), ns)
    return ns["trung"], ns["ket"], ns.get("doi_chieu_duoc")


# ====== Ca đúng thật người dùng báo cáo ======
# PUInvoice trong MISA CHỈ có các hóa đơn KHÁC (3306, 3307...) của CÙNG NCC —
# KHÔNG có 3381. "Số chứng từ" tính cho 3381 TÌNH CỜ trùng với 1 bản ghi
# unposted_docs CÓ SẴN (mô phỏng đúng lỗi đổi thứ tự xử lý khiến hậu tố bị
# gán lại) — điều kiện CŨ (k_doc) sẽ chặn nếu vẫn chạy song song.
pu_invoice_hien_co = [("0317743519", "3306"), ("0317743519", "3307"), ("0317743519", "3460")]
trung, ket, doi_chieu_duoc = chay_nk(
    pu_invoice_hien_co, "0317743519", "3381",
    k_doc_gia_lap="nk20260317743519-99",
    unposted_docs={"nk20260317743519-99": {"refids": ["fake-rid"], "reftype_ten": "Mua hàng NK"}})

assert doi_chieu_duoc is True, "Phải đối chiếu được theo nội dung (có PUInvoice + có Số HĐ)"
assert trung == 0, (
    f"Hóa đơn 3381 THẬT SỰ CHƯA CÓ trong MISA (không khớp PUInvoice) -> KHÔNG được bị 'Số chứng từ' "
    f"trùng nhầm với hóa đơn KHÁC chặn lại — được trung={trung}, ket={ket}")
assert not ket, f"Không được có kết quả 'đã có/trùng' nào cho hóa đơn 3381 — được {ket}"
print("PASS: hóa đơn 3381 (thật sự chưa có trong MISA) KHÔNG còn bị 'Số chứng từ' trùng nhầm chặn lại "
      "— đúng sửa lỗi cho ca thật người dùng báo cáo.")

# Đối chứng: hóa đơn ĐÃ CÓ thật (khớp PUInvoice) vẫn phải bị chặn đúng.
trung2, ket2, _ = chay_nk(pu_invoice_hien_co, "0317743519", "3306", k_doc_gia_lap="nk-khac-gi-cung-duoc")
assert trung2 == 1 and "khớp theo MST NCC + Số HĐ" in ket2[0]["trang_thai"], (trung2, ket2)
print("PASS: hóa đơn ĐÃ CÓ thật (3306) vẫn bị chặn đúng dù 'Số chứng từ' hoàn toàn khác.")

# Đối chứng: khi KHÔNG đối chiếu được theo nội dung (PUInvoice lỗi/không có),
# phải rơi về đúng hành vi CŨ (dùng k_doc) — không được đổi hành vi khi
# CSDL MISA không có bảng PUInvoice.
class FakeCursorLoi(FakeCursor):
    def execute(self, sql, *a):
        raise Exception("bảng không tồn tại")


def chay_nk_loi_pu_invoice(k_doc_gia_lap, unposted_docs):
    block = extract(
        '        # ĐỐI CHIẾU THEO NỘI DUNG HÓA ĐƠN (MST NCC + Số HĐ), KHÔNG CHỈ THEO',
        '            if mst_k not in ncc:')
    ns = {
        "_misa_khncc_chuan_mst": server._misa_khncc_chuan_mst,
        "_chuan_shd": server._chuan_shd,
        "_misa_chon_cot": server._misa_chon_cot,
        "_misa_cot_bang_that": server._misa_cot_bang_that,
        "datetime": datetime,
        "cur": FakeCursorLoi([]),
        "loai": "nk",
        "order": [k_doc_gia_lap],
        "groups": {k_doc_gia_lap: [{"mst": "0317743519", "sohd": "3381"}]},
        "cfg": {"mst": "mst", "sohd": "sohd"},
        "posted_refno": set(),
        "unposted_docs": unposted_docs,
        "ghi_de": False,
        "trung": 0,
        "ket": [],
    }
    exec(compile(block, "<ghi_mua_hang_nk_loi>", "exec"), ns)
    return ns["trung"], ns["ket"], ns.get("doi_chieu_duoc")


trung3, ket3, doi_chieu_duoc3 = chay_nk_loi_pu_invoice(
    "nk20260317743519-99", {"nk20260317743519-99": {"refids": [], "reftype_ten": "x"}})
assert doi_chieu_duoc3 is False, "Không đọc được PUInvoice -> phải rơi về hành vi CŨ (k_doc)"
assert trung3 == 1 and "đã có (do phần mềm tạo trước đó" in ket3[0]["trang_thai"], (trung3, ket3)
print("PASS: khi KHÔNG đối chiếu được theo nội dung (CSDL MISA thiếu bảng PUInvoice), vẫn rơi về "
      "đúng hành vi CŨ theo 'Số chứng từ' như trước — không đổi hành vi cho trường hợp này.")

print("\nTẤT CẢ TEST PASS (nk)")


class FakeCursorDv:
    """_misa_ghi_mua_hang_dv (khác nk) không dò 'hiện rõ trên MISA' — giữ
    FakeCursor ĐƠN GIẢN, 2-tuple gốc (mst,inv), tách riêng khỏi FakeCursor
    (nk) ở trên để không bị ảnh hưởng bởi thay đổi RefID chỉ áp dụng cho nk."""
    def __init__(self, rows):
        self._rows = rows

    def execute(self, sql, *a):
        self._sql = sql
        return self

    def fetchall(self):
        if "sys.columns" in self._sql:
            return []
        return self._rows


def chay_dv(pu_service_detail_rows, mst_dg, sohd_dg, k_doc_gia_lap, unposted_docs=None):
    block = extract(
        '        # ĐỐI CHIẾU THEO NỘI DUNG HÓA ĐƠN (MST NCC + Số HĐ) — xem giải thích',
        '            if mst_k not in ncc:')
    ns = {
        "_misa_khncc_chuan_mst": server._misa_khncc_chuan_mst,
        "_chuan_shd": server._chuan_shd,
        "_misa_chon_cot": server._misa_chon_cot,
        "_misa_cot_bang_that": server._misa_cot_bang_that,
        "datetime": datetime,
        "cur": FakeCursorDv(pu_service_detail_rows),
        "order": [k_doc_gia_lap],
        "groups": {k_doc_gia_lap: [{"mst": mst_dg, "sohd": sohd_dg}]},
        "cfg": {"mst": "mst", "sohd": "sohd"},
        "posted_refno": set(),
        "unposted_docs": unposted_docs if unposted_docs is not None else {},
        "ghi_de": False,
        "trung": 0,
        "ket": [],
    }
    exec(compile(block, "<ghi_mua_hang_dv>", "exec"), ns)
    return ns["trung"], ns["ket"]


trung4, ket4 = chay_dv(
    [("0317743519", "3306")], "0317743519", "3381",
    k_doc_gia_lap="dv-trung-nham",
    unposted_docs={"dv-trung-nham": {"refids": [], "reftype_ten": "x"}})
assert trung4 == 0 and not ket4, (trung4, ket4)
print("PASS (dv): hóa đơn thật sự chưa có trong MISA không còn bị 'Số chứng từ' trùng nhầm chặn lại.")

print("\nTẤT CẢ TEST PASS (nk + dv)")
