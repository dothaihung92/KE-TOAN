import os
import calendar
import datetime
import tempfile

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test cho _doc_so_du_cuoi_ky_ky_truoc() (trước đây tên
# _doc_ct41_ky_truoc) — người dùng báo ĐÚNG ca thật: công ty MST
# 0317256924 (CÔNG TY TNHH XUẤT NHẬP KHẨU SUNSTEEL INTERNATIONAL), tờ
# khai GTGT tháng 07/2026 có chỉ tiêu [41]=3.819.789.966 (tổng còn được
# khấu trừ) NHƯNG [42] (đề nghị hoàn thuế) CŨNG = 3.819.789.966 — tức
# hoàn thuế TOÀN BỘ số đó, nên [43] (còn lại CHUYỂN KỲ SAU) = 0. Phần
# mềm TRƯỚC ĐÂY đọc [41] của kỳ trước làm 'Số dư đầu kỳ' [22] của kỳ
# sau (tháng 08/2026) -> điền SAI 3.819.789.966 thay vì ĐÚNG là 0 (toàn
# bộ số đó đã tách ra xin hoàn, không còn được khấu trừ tiếp).
#
# Dữ liệu XML dưới đây trích ĐÚNG NGUYÊN VĂN các thẻ liên quan từ 2 file
# thật người dùng gửi (01_GTGT_TT80-M072026-L00.xml và
# 01_GTGT_TT80-M082026-L00.xml).


def extract_fn(name):
    try:
        idx = src.index('async def ' + name + '(')
    except ValueError:
        idx = src.index('def ' + name + '(')
    i = src.index(':', idx)
    lines = src[i + 1:].split('\n')
    body = []
    started = False
    for ln in lines:
        if ln.strip() == '' and not started:
            body.append(ln)
            continue
        if ln and not ln[0].isspace() and started:
            break
        if ln.strip():
            started = True
        body.append(ln)
    return src[idx:i + 1] + '\n'.join(body)


# ===== XML tháng 07/2026 THẬT (rút gọn, giữ NGUYÊN VĂN các thẻ liên
# quan) — [41]=3.819.789.966, [42]=3.819.789.966 (hoàn TOÀN BỘ) ->
# [43]=0. =====
_XML_THANG_7_HOAN_THUE_TOAN_BO = """<?xml version="1.0" encoding="UTF-8"?>
<HSoThueDTu xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://kekhaithue.gdt.gov.vn/TKhaiThue">
  <HSoKhaiThue id="ID_1">
    <TTinChung>
      <TTinTKhaiThue>
        <TKhaiThue>
          <KyKKhaiThue>
            <kieuKy>M</kieuKy>
            <kyKKhai>07/2026</kyKKhai>
          </KyKKhaiThue>
        </TKhaiThue>
        <NNT>
          <mst>0317256924</mst>
        </NNT>
      </TTinTKhaiThue>
    </TTinChung>
    <CTieuTKhaiChinh>
      <ct41>3819789966</ct41>
      <ct42>3819789966</ct42>
      <ct43>0</ct43>
    </CTieuTKhaiChinh>
  </HSoKhaiThue>
</HSoThueDTu>
"""

# ===== XML tháng THÁNG KHÁC — KHÔNG hoàn thuế ([42]=0) -> [43] phải
# BẰNG [41] (kết quả KHÔNG đổi so với hành vi cũ khi không có hoàn thuế
# — bảo đảm sửa lỗi không làm hỏng ca bình thường). =====
_XML_THANG_KHONG_HOAN_THUE = """<?xml version="1.0" encoding="UTF-8"?>
<HSoThueDTu xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://kekhaithue.gdt.gov.vn/TKhaiThue">
  <HSoKhaiThue id="ID_1">
    <TTinChung>
      <TTinTKhaiThue>
        <TKhaiThue>
          <KyKKhaiThue>
            <kieuKy>M</kieuKy>
            <kyKKhai>07/2026</kyKKhai>
          </KyKKhaiThue>
        </TKhaiThue>
        <NNT>
          <mst>0317256924</mst>
        </NNT>
      </TTinTKhaiThue>
    </TTinChung>
    <CTieuTKhaiChinh>
      <ct41>500000000</ct41>
      <ct42>0</ct42>
      <ct43>500000000</ct43>
    </CTieuTKhaiChinh>
  </HSoKhaiThue>
</HSoThueDTu>
"""

ns = {'os': os, 'calendar': calendar, 'datetime': datetime}
exec(extract_fn('_khong_dau'), ns)
exec(extract_fn('_quy_cua_ky'), ns)
exec(extract_fn('_thang_cua_ky'), ns)
exec(extract_fn('_co_thu_muc_theo_thang'), ns)
exec(extract_fn('_thu_muc_ket_xuat_ky'), ns)
exec(extract_fn('_to_num'), ns)
ns['_DVC_LOAI_TU_KHOA_FILE'] = {"GTGT": ["gtgt"], "TNCN": ["tncn"]}
exec(extract_fn('_ky_tu_ten_file_nop'), ns) if 'def _ky_tu_ten_file_nop(' in src else None
exec(extract_fn('_tim_file_nop_to_khai'), ns)
exec(extract_fn('_ky_ve_thang'), ns)
exec(extract_fn('_ky_lien_truoc'), ns)
exec(extract_fn('_doc_so_du_cuoi_ky_ky_truoc'), ns)
_doc_so_du_cuoi_ky_ky_truoc = ns['_doc_so_du_cuoi_ky_ky_truoc']


def _cong_ty_gia(mst, export_dir):
    return {"mst": mst, "export_dir": export_dir}


# ===== Test 1 (QUAN TRỌNG — đúng ca thật người dùng báo): kỳ trước có
# hoàn thuế TOÀN BỘ ([42]==[41]) -> phải lấy [43]=0 làm số dư đầu kỳ
# sau, KHÔNG được lấy nhầm [41]=3.819.789.966. =====
_tmp1 = tempfile.mkdtemp()
_thang7_dir = os.path.join(_tmp1, "2026", "THANG 7")
os.makedirs(_thang7_dir, exist_ok=True)  # công ty đã tự tổ chức thư mục theo THÁNG (như thật)
with open(os.path.join(_thang7_dir, "0317256924000-01_GTGT_TT80-M072026-L00.xml"), "w", encoding="utf-8") as f:
    f.write(_XML_THANG_7_HOAN_THUE_TOAN_BO)
comp1 = _cong_ty_gia("0317256924", _tmp1)
gia_tri1, ky_truoc1, fp1 = _doc_so_du_cuoi_ky_ky_truoc(comp1, "08/2026")
assert ky_truoc1 == "07/2026", f"got {ky_truoc1!r}"
assert fp1, "phải tìm thấy file tờ khai tháng 07/2026 đã lưu"
assert gia_tri1 == 0, (
    f"Tháng 07/2026 hoàn thuế TOÀN BỘ ([41]=[42]=3.819.789.966 -> [43]=0) -> số dư đầu kỳ tháng "
    f"08/2026 PHẢI là 0, không được lấy nhầm [41]=3.819.789.966 (số đã tách ra xin hoàn, không còn "
    f"được khấu trừ tiếp) — got {gia_tri1}")
print("PASS 1: kỳ trước hoàn thuế TOÀN BỘ -> lấy ĐÚNG [43]=0 làm số dư đầu kỳ sau, đúng ca thật người "
      "dùng báo (công ty SUNSTEEL INTERNATIONAL, MST 0317256924).")

# ===== Test 2 (không hồi quy — an toàn): kỳ trước KHÔNG hoàn thuế
# ([42]=0) -> [43]==[41], kết quả giống hệt hành vi cũ (không phá vỡ ca
# bình thường, chiếm đa số). =====
_tmp2 = tempfile.mkdtemp()
_thang7_dir2 = os.path.join(_tmp2, "2026", "THANG 7")
os.makedirs(_thang7_dir2, exist_ok=True)
with open(os.path.join(_thang7_dir2, "0317256924000-01_GTGT_TT80-M072026-L00.xml"), "w", encoding="utf-8") as f:
    f.write(_XML_THANG_KHONG_HOAN_THUE)
comp2 = _cong_ty_gia("0317256924", _tmp2)
gia_tri2, ky_truoc2, fp2 = _doc_so_du_cuoi_ky_ky_truoc(comp2, "08/2026")
assert gia_tri2 == 500000000, (
    f"Kỳ trước KHÔNG hoàn thuế ([42]=0 nên [43]=[41]) -> số dư đầu kỳ sau phải giữ nguyên như hành vi cũ "
    f"(500.000.000) — got {gia_tri2}")
print("PASS 2: kỳ trước KHÔNG hoàn thuế -> [43]=[41], kết quả không đổi so với trước (không phá vỡ ca "
      "bình thường).")

# ===== _tinh_ct22_dau_ky_gtgt(): ĐÚNG luồng "Kết xuất XML cho HTKK" thật
# — người dùng báo: đã sửa _doc_so_du_cuoi_ky_ky_truoc() (đọc [43] thay vì
# [41]) NHƯNG bấm "Kết xuất XML" VẪN lấy sai 3.819.789.966, vì số sai đó
# đã LỠ được lưu sẵn vào bảng vat_balance TỪ TRƯỚC lúc sửa lỗi — "Kết xuất
# XML" trước đây ưu tiên đọc cache CŨ này, chỉ đọc lại file khi cache
# TRỐNG. Người dùng yêu cầu rõ: "không cần nhấn vào tạm tính thuế VAT phần
# mềm cũng phải lấy đúng, 2 nút không liên quan nhau" -> phải ưu tiên đọc
# LẠI file (nguồn chính xác nhất) và TỰ SỬA cache cũ nếu sai, không được
# phụ thuộc/bị kẹt bởi cache của màn "Tạm tính thuế VAT". =====
import sqlite3

exec(extract_fn('_tinh_ct22_dau_ky_gtgt'), ns)
_tinh_ct22_dau_ky_gtgt = ns['_tinh_ct22_dau_ky_gtgt']

_tmp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
_tmp_db.close()


def _fresh_db():
    conn = sqlite3.connect(_tmp_db.name, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS vat_balance (
        company_id INTEGER, ky TEXT, du_dau_ky REAL, updated_at TEXT,
        PRIMARY KEY (company_id, ky)
    )""")
    return conn


ns['db'] = _fresh_db

# ===== Test 3 (QUAN TRỌNG — ĐÚNG ca thật người dùng báo lần 2): bảng
# vat_balance đã LỠ lưu sẵn số SAI (3.819.789.966, từ TRƯỚC lúc sửa lỗi
# [41]/[43]) cho kỳ 08/2026 — "Kết xuất XML" (_tinh_ct22_dau_ky_gtgt) PHẢI
# đọc LẠI file kỳ trước (đúng [43]=0) và TỰ SỬA cache, KHÔNG được dùng lại
# số sai cũ trong vat_balance. =====
conn_seed = _fresh_db()
conn_seed.execute(
    "INSERT INTO vat_balance (company_id, ky, du_dau_ky, updated_at) VALUES (?,?,?,?)",
    (1, "08/2026", 3819789966, datetime.datetime.now().isoformat()))
conn_seed.commit(); conn_seed.close()
comp3 = _cong_ty_gia("0317256924", _tmp1)  # _tmp1: thư mục có sẵn file tháng 7 hoàn thuế TOÀN BỘ -> [43]=0
ct22_3 = _tinh_ct22_dau_ky_gtgt(1, comp3, "08/2026", "08/2026")
assert ct22_3 == 0, (
    f"vat_balance đã lỡ lưu sẵn số SAI (3.819.789.966) từ TRƯỚC lúc sửa lỗi -> 'Kết xuất XML' PHẢI đọc "
    f"LẠI file kỳ trước (đúng [43]=0) và TỰ SỬA cache, không được dùng lại số sai cũ — got {ct22_3}")
# Xác nhận cache ĐÃ được tự sửa lại đúng (0), không còn số sai cũ.
conn_chk = _fresh_db()
row_chk = conn_chk.execute("SELECT du_dau_ky FROM vat_balance WHERE company_id=? AND ky=?", (1, "08/2026")).fetchone()
conn_chk.close()
assert row_chk["du_dau_ky"] == 0, f"cache vat_balance phải được TỰ SỬA về 0, got {row_chk['du_dau_ky']}"
print("PASS 3: 'Kết xuất XML' (_tinh_ct22_dau_ky_gtgt) đọc LẠI file kỳ trước và TỰ SỬA cache dù "
      "vat_balance đã lỡ lưu sẵn số SAI từ trước khi sửa lỗi — đúng ca thật người dùng báo lần 2, và đúng "
      "yêu cầu '2 nút không liên quan nhau, không cần nhấn Tạm tính thuế VAT vẫn phải lấy đúng'.")

# ===== Test 4 (không hồi quy — an toàn): KHÔNG có file kỳ trước (công ty
# mới/chưa cấu hình thư mục kết xuất) -> LÙI VỀ số đã tự lưu tay trong
# vat_balance (vẫn tôn trọng số người dùng tự xác nhận khi không có file
# nào đáng tin cậy hơn). =====
conn_seed4 = _fresh_db()
conn_seed4.execute(
    "INSERT INTO vat_balance (company_id, ky, du_dau_ky, updated_at) VALUES (?,?,?,?)",
    (2, "08/2026", 123456789, datetime.datetime.now().isoformat()))
conn_seed4.commit(); conn_seed4.close()
comp4 = _cong_ty_gia("0399999999", tempfile.mkdtemp())  # thư mục trống, không có file kỳ trước nào
ct22_4 = _tinh_ct22_dau_ky_gtgt(2, comp4, "08/2026", "08/2026")
assert ct22_4 == 123456789, (
    f"Không có file kỳ trước -> phải LÙI VỀ số đã tự lưu tay trong vat_balance, không tự ý đổi thành 0 "
    f"— got {ct22_4}")
print("PASS 4: không có file kỳ trước (công ty mới/chưa cấu hình thư mục) -> lùi về đúng số đã tự lưu "
      "tay trong vat_balance, không đoán bừa/không xóa mất dữ liệu người dùng tự nhập.")

os.unlink(_tmp_db.name)
print("\nALL DONE")
