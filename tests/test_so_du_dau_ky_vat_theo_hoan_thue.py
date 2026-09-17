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

print("\nALL DONE")
