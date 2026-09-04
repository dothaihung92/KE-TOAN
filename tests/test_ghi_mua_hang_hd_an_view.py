import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: hóa đơn khớp PUInvoice (MST NCC + Số HĐ) trước đây LUÔN
bị coi "đã có trong MISA, bỏ qua" — nhưng PUInvoice khớp KHÔNG có nghĩa
chứng từ Mua hàng liên kết THẬT SỰ hiện trên màn hình "Mua hàng hóa, dịch
vụ" của MISA (PUVoucher có thể lỗi/ẩn — PostedDate NULL, sai chi nhánh,
DisplayOnBook không phải 0/2).

Đúng ca thật người dùng báo cáo: đối chiếu file Excel MISA thật, 4 hóa đơn
(Số HĐ 33/41/43/46, NCC "TUẤN TRƯỜNG THỊNH") THẬT SỰ KHÔNG có trong danh
sách "Mua hàng hóa, dịch vụ" MISA — nhưng "Xem trước" ("⬆ Nhập kho vào
MISA") vẫn báo cả 4 là "đã có trong MISA (khớp theo MST NCC + Số HĐ, bỏ
qua)" — vì PUInvoice CÓ bản ghi khớp MST+Số HĐ (từ 1 lần ghi trước đó bị
lỗi/không hoàn chỉnh), nhưng PUVoucher liên kết không hiện trên màn hình
MISA thật.

Test các ca:
1. Bản ghi lỗi DO CHÍNH phần mềm tạo (CustomField10=_PM_MARK) + bấm "Ghi
   đè" -> phần mềm TỰ xóa bản lỗi rồi ghi lại (không chỉ báo suông).
2. Bản ghi KHÔNG do phần mềm tạo -> KHÔNG được tự xóa, chỉ báo rõ để người
   dùng tự kiểm tra trong MISA (không còn báo nhầm "đã có, bỏ qua" khiến
   người dùng yên tâm sai).
3. (Đối chứng) hóa đơn hiện rõ đúng -> giữ hành vi cũ.
4. Bản ghi lỗi KHÔNG có CustomField10 (vd phiên bản phần mềm cũ trước khi
   có quy ước đánh dấu, hoặc bị xóa mất) NHƯNG "Số chứng từ" (RefNoManagement)
   trùng NGUYÊN VĂN công thức phần mềm tự sinh cho ĐÚNG hóa đơn đang xét —
   vẫn phải nhận diện được là CỦA PHẦN MỀM (dấu hiệu phụ) và cho phép Ghi
   đè — đúng ca thật người dùng báo cáo: bấm "Ghi đè" xong vẫn không thấy
   chứng từ nào được xử lý, vì tất cả đều bị báo "KHÔNG do phần mềm tạo"
   dù "Số chứng từ" (NK20263603289732-2...) rõ ràng đúng công thức phần
   mềm (không ai tự tay gõ trùng khớp chính xác tiền tố+năm+MST NCC)."""
import sys, textwrap, datetime
sys.path.insert(0, _REPO_ROOT)
import server


def extract(start_marker, end_marker):
    src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()
    i0 = src.index(start_marker)
    i0 = src.rfind("\n", 0, i0) + 1
    i1 = src.index(end_marker, i0)
    return textwrap.dedent(src[i0:i1])


block = extract(
    '        # ĐỐI CHIẾU THEO NỘI DUNG HÓA ĐƠN (MST NCC + Số HĐ), KHÔNG CHỈ THEO',
    '            if mst_k not in ncc:')
# Bọc "for __once in [0]" để "continue" (vốn continue vòng "for doc in
# order" ngoài cùng thật) vẫn hợp lệ khi exec() đoạn cắt rời — cần LOẠI BỎ
# dòng "for doc in order:" gốc (đã có trong block) và thay bằng thân vòng
# lặp giả, KHÔNG lồng thêm 1 lớp for nữa (đoạn cắt đã tự có "for doc in
# order:" ở đầu block rồi).


class FakeCursor:
    def __init__(self, pu_invoice_rows, pu_invoice_detail, pu_voucher):
        self._inv = pu_invoice_rows          # [(refid, mst, invno)]
        self._invdetail = pu_invoice_detail  # {inv_refid: pu_refid}
        self._voucher = pu_voucher           # {pu_refid: (posted_date, branch, dob, mark, refno)}
        self.deleted = []

    def execute(self, sql, *params):
        self._sql = sql
        self._params = params
        return self

    def fetchall(self):
        if "FROM PUInvoice" in self._sql and "SELECT RefID" in self._sql:
            return self._inv
        return []

    def fetchone(self):
        if "PUVoucherRefID FROM PUInvoiceDetail" in self._sql:
            inv_refid = self._params[0]
            pu = self._invdetail.get(inv_refid)
            return (pu,) if pu else None
        if "FROM PUVoucher WHERE RefID" in self._sql:
            pu_refid = self._params[0]
            v = self._voucher.get(pu_refid)
            return v if v else None
        return None


def chay(pu_invoice_rows, pu_invoice_detail, pu_voucher, mst_dg, sohd_dg, ghi_de, preview, branch_id="BR1"):
    cur = FakeCursor(pu_invoice_rows, pu_invoice_detail, pu_voucher)
    orig_exec = cur.execute
    def exec_track(sql, *p):
        if sql.strip().startswith("DELETE"):
            cur.deleted.append((sql.split()[2], p[0] if p else None))
        return orig_exec(sql, *p)
    cur.execute = exec_track
    ns = {
        "_misa_khncc_chuan_mst": server._misa_khncc_chuan_mst,
        "_chuan_shd": server._chuan_shd,
        "_misa_chon_cot": server._misa_chon_cot,
        "_misa_cot_bang_that": server._misa_cot_bang_that,
        "datetime": datetime,
        "_PM_MARK": server._PM_MARK,
        "cur": cur,
        "loai": "nk",
        "branch_id": branch_id,
        "order": [f"nk-{sohd_dg}"],
        "groups": {f"nk-{sohd_dg}": [{"mst": mst_dg, "sohd": sohd_dg}]},
        "cfg": {"mst": "mst", "sohd": "sohd"},
        "posted_refno": set(),
        "unposted_docs": {},
        "ghi_de": ghi_de,
        "preview": preview,
        "trung": 0,
        "ket": [],
    }
    exec(compile(block, "<ghi_mua_hang_hd_an>", "exec"), ns)
    return ns["trung"], ns["ket"], cur.deleted, ns.get("ghi_de_hd_an", False)


MST, SOHD = "3603289732", "41"
INV_REFID, PU_REFID = "inv-1", "pu-1"

# ====== Ca 1: bản ghi lỗi/ẩn DO CHÍNH PHẦN MỀM tạo (CustomField10=_PM_MARK),
# người dùng bấm "Ghi đè" -> phải TỰ XÓA bản lỗi (không chỉ báo suông). ======
trung1, ket1, deleted1, ghi_de_hd_an1 = chay(
    pu_invoice_rows=[(INV_REFID, MST, SOHD)],
    pu_invoice_detail={INV_REFID: PU_REFID},
    # PostedDate NULL -> KHÔNG hiện rõ; RefNoManagement KHÁC k_doc hiện tại
    # (chỉ CustomField10 làm bằng chứng ở ca này).
    pu_voucher={PU_REFID: (None, "BR1", 0, server._PM_MARK, "so-ct-khac")},
    mst_dg=MST, sohd_dg=SOHD, ghi_de=True, preview=False)

assert ghi_de_hd_an1 is True, "Phải nhận diện đúng là bản ghi lỗi/ẩn DO PHẦN MỀM tạo, cho phép Ghi đè"
assert trung1 == 0 and not ket1, (
    f"KHÔNG được ghi vào 'ket'/'trung' như 1 lần bỏ qua — phải để hóa đơn ĐI TIẾP vào luồng ghi mới "
    f"(fall-through, không continue) — được trung={trung1}, ket={ket1}")
assert ("PUVoucher", PU_REFID) in deleted1 and ("PUInvoice", INV_REFID) in deleted1, (
    f"Phải TỰ XÓA cả PUVoucher lẫn PUInvoice của bản ghi lỗi (do chính phần mềm tạo) — được xóa: {deleted1}")
print("PASS (ca 1): bản ghi lỗi/ẩn DO CHÍNH PHẦN MỀM tạo, bấm 'Ghi đè' -> phần mềm TỰ xóa rồi để hóa "
      "đơn đi tiếp vào luồng ghi lại đúng — không còn báo nhầm 'đã có, bỏ qua'.")

# ====== Ca 2: bản ghi KHÔNG do phần mềm tạo -> KHÔNG được tự xóa, chỉ báo
# rõ cho người dùng tự kiểm tra (không còn báo nhầm 'đã có, bỏ qua'). ======
trung2, ket2, deleted2, ghi_de_hd_an2 = chay(
    pu_invoice_rows=[(INV_REFID, MST, SOHD)],
    pu_invoice_detail={INV_REFID: PU_REFID},
    # CustomField10 rỗng VÀ RefNoManagement KHÁC hẳn công thức phần mềm
    # (chứng từ thật, độc lập) -> KHÔNG phải của phần mềm ở cả 2 dấu hiệu.
    pu_voucher={PU_REFID: (None, "BR1", 0, "", "chung-tu-that-cua-khach")},
    mst_dg=MST, sohd_dg=SOHD, ghi_de=True, preview=False)

assert ghi_de_hd_an2 is False
assert not deleted2, f"KHÔNG được tự xóa chứng từ KHÔNG do phần mềm tạo — được xóa: {deleted2}"
assert trung2 == 1 and len(ket2) == 1
tt2 = ket2[0]["trang_thai"]
print("Trạng thái (ca 2):", tt2)
assert "KHÔNG hiện trên màn hình Mua hàng MISA" in tt2, (
    f"Phải báo RÕ hóa đơn không hiện trên MISA thật (không còn báo nhầm 'đã có, bỏ qua' làm người dùng "
    f"yên tâm sai) — được: {tt2}")
assert "KHÔNG do phần mềm tạo" in tt2
print("PASS (ca 2): bản ghi KHÔNG do phần mềm tạo -> KHÔNG tự xóa, chỉ báo rõ cho người dùng tự kiểm "
      "tra — không còn báo nhầm 'đã có, bỏ qua'.")

# ====== Đối chứng: hóa đơn khớp PUInvoice + PUVoucher THẬT SỰ hiện rõ trên
# MISA (PostedDate có, đúng chi nhánh, DisplayOnBook=0) -> vẫn báo "đã có,
# bỏ qua" như cũ (không đổi hành vi cho ca ĐÚNG). ======
trung3, ket3, deleted3, ghi_de_hd_an3 = chay(
    pu_invoice_rows=[(INV_REFID, MST, SOHD)],
    pu_invoice_detail={INV_REFID: PU_REFID},
    pu_voucher={PU_REFID: (__import__("datetime").datetime(2026, 5, 18), "BR1", 0, "", "chung-tu-khac")},
    mst_dg=MST, sohd_dg=SOHD, ghi_de=True, preview=False)
assert trung3 == 1 and len(ket3) == 1
assert ket3[0]["trang_thai"] == "đã có trong MISA (khớp theo MST NCC + Số HĐ, bỏ qua)"
assert not deleted3
print("PASS (đối chứng): hóa đơn THẬT SỰ hiện rõ trên MISA vẫn báo 'đã có, bỏ qua' đúng như cũ, không "
      "đổi hành vi cho ca bình thường.")

# ====== Ca 4: bản ghi lỗi KHÔNG có CustomField10 (rỗng) nhưng "Số chứng
# từ" TRÙNG NGUYÊN VĂN công thức phần mềm cho ĐÚNG hóa đơn đang xét — vẫn
# phải nhận diện được (dấu hiệu phụ) và cho phép Ghi đè. k_doc thật sự
# dùng trong chay() là f"nk-{sohd_dg}".lower() = "nk-41". ======
trung4, ket4, deleted4, ghi_de_hd_an4 = chay(
    pu_invoice_rows=[(INV_REFID, MST, SOHD)],
    pu_invoice_detail={INV_REFID: PU_REFID},
    pu_voucher={PU_REFID: (None, "BR1", 0, "", "NK-41")},   # CustomField10 rỗng, RefNo TRÙNG k_doc
    mst_dg=MST, sohd_dg=SOHD, ghi_de=True, preview=False)

assert ghi_de_hd_an4 is True, (
    "Phải nhận diện là CỦA PHẦN MỀM qua dấu hiệu PHỤ (Số chứng từ trùng công thức) dù CustomField10 "
    "rỗng — đúng ca thật người dùng báo cáo: bấm 'Ghi đè' vẫn không xử lý được gì vì bị coi nhầm "
    "'KHÔNG do phần mềm tạo'")
assert trung4 == 0 and not ket4
assert ("PUVoucher", PU_REFID) in deleted4 and ("PUInvoice", INV_REFID) in deleted4
print("PASS (ca 4): bản ghi lỗi KHÔNG có CustomField10 nhưng Số chứng từ trùng công thức phần mềm vẫn "
      "được nhận diện đúng là của phần mềm, bấm 'Ghi đè' tự xóa + ghi lại được — không còn kẹt mãi ở "
      "trạng thái 'không do phần mềm tạo' như báo cáo thật của người dùng.")

# ====== Ca 5: PUInvoice HOÀN TOÀN KHÔNG liên kết được PUVoucher nào (không
# có dòng PUInvoiceDetail nào trỏ tới) — nặng hơn ca 1-4 (còn không có gì
# để so CustomField10/RefNoManagement) — vẫn phải coi là rác/lỗi, an toàn
# dọn khi bấm "Ghi đè". Đúng ca thật người dùng báo cáo: sau khi đã sửa
# nhận diện RefNoManagement (ca 4), bấm "Ghi đè" VẪN báo "Đã ghi 0 chứng
# từ" — hóa ra 1 số bản ghi lỗi còn thiếu hẳn PUVoucher liên kết. ======
trung5, ket5, deleted5, ghi_de_hd_an5 = chay(
    pu_invoice_rows=[(INV_REFID, MST, SOHD)],
    pu_invoice_detail={},   # KHÔNG có dòng nào link tới PUVoucher
    pu_voucher={},
    mst_dg=MST, sohd_dg=SOHD, ghi_de=True, preview=False)

assert ghi_de_hd_an5 is True, (
    "PUInvoice không liên kết PUVoucher nào -> CHẮC CHẮN là rác/lỗi (hóa đơn thật không bao giờ thiếu "
    "hẳn chứng từ Mua hàng đi kèm), phải cho phép Ghi đè dọn dẹp — đúng lỗi thật người dùng báo cáo: "
    "'Ghi đè' vẫn báo 'Đã ghi 0 chứng từ' dù đã nhận diện đúng RefNoManagement ở lần sửa trước")
assert trung5 == 0 and not ket5
assert ("PUInvoice", INV_REFID) in deleted5
print("PASS (ca 5): PUInvoice không liên kết PUVoucher nào (rác/lỗi nặng hơn) vẫn được nhận diện đúng, "
      "cho phép Ghi đè dọn dẹp rồi ghi lại — không còn kẹt mãi ở 'Đã ghi 0 chứng từ'.")

print("\nTẤT CẢ TEST PASS")
