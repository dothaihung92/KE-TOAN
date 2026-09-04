import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: chứng từ Mua hàng (Nhập kho nk/kqk và Dịch vụ dv) ghi
thẳng vào MISA phải có GIỜ CỐ ĐỊNH 10:00:00 (không còn NỬA ĐÊM 00:00:00 hay
giờ THẬT lúc script chạy) — đúng nguyên nhân người dùng tự chẩn đoán và xác
nhận qua MISA thật: hộp thoại "Điều chỉnh thời gian nhập/xuất kho" của MISA
khi Ghi sổ KHÔNG bảo toàn giờ phần mềm đã ghi mà lấy giờ thật lúc bấm Ghi sổ
trong MISA — nếu Nhập kho được ghi sổ SAU (giờ) so với Xuất kho (thường ghi
sổ vào cuối ngày), MISA tính tồn lúc ghi sổ Xuất kho KHÔNG thấy phần Nhập
kho đó, từ chối ghi sổ dù tồn thực tế đủ. Đặt giờ SỚM cố định (10:00) cho
Nhập kho giúp tránh đúng tình huống này."""
import sys, textwrap, datetime
sys.path.insert(0, _REPO_ROOT)
import server


def extract(start_marker, end_marker):
    src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()
    i0 = src.index(start_marker)
    i0 = src.rfind("\n", 0, i0) + 1
    i1 = src.index(end_marker, i0)
    return textwrap.dedent(src[i0:i1])


# ---- 1. Unit test hàm helper ----
dt_nua_dem = datetime.datetime(2026, 8, 31, 0, 0, 0)
dt_gio_that = datetime.datetime(2026, 8, 31, 23, 59, 9)
assert server._misa_gio_nhap_co_dinh(dt_nua_dem) == datetime.datetime(2026, 8, 31, 10, 0, 0)
assert server._misa_gio_nhap_co_dinh(dt_gio_that) == datetime.datetime(2026, 8, 31, 10, 0, 0)
assert server._misa_gio_nhap_co_dinh(None) is None
print("PASS: _misa_gio_nhap_co_dinh luôn trả về đúng 10:00:00, giữ nguyên ngày/tháng/năm.")

# ---- 2. Xác nhận đoạn code THẬT trong _misa_ghi_mua_hang (nk/kqk) có gọi
# hàm này khi tính ngay_dt (không chỉ test hàm helper đứng riêng — phải chắc
# chắn đã NỐI DÂY đúng vào chỗ ghi chứng từ thật). ----
block_nk = extract(
    '            ngay_dt = None\n            ngay_str = str(first[cfg["ngayct"]] or "").strip()\n'
    '            for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):\n'
    '                try:\n                    ngay_dt = datetime.datetime.strptime(ngay_str, fmt)\n'
    '                    break\n                except Exception:\n                    pass\n'
    '            # KHÔNG đọc được ngày',
    '            co_tk = str(first[cfg["co"]] or "").strip()')
assert "_misa_gio_nhap_co_dinh" in block_nk, (
    "Đoạn tính ngay_dt trong _misa_ghi_mua_hang (nk/kqk) PHẢI gọi _misa_gio_nhap_co_dinh")
ns = {"datetime": datetime, "_misa_gio_nhap_co_dinh": server._misa_gio_nhap_co_dinh,
      "first": {"ngayct": "31/07/2026"}, "cfg": {"ngayct": "ngayct", "co": "co"},
      "now": datetime.datetime(2026, 8, 31, 23, 59, 9)}
exec(compile(block_nk, "<ghi_mua_hang_nk_ngay>", "exec"), ns)
assert ns["ngay_dt"] == datetime.datetime(2026, 7, 31, 10, 0, 0), (
    f"ngay_dt (nk/kqk) phải là 31/07/2026 10:00:00 — được {ns['ngay_dt']}")
print("PASS (nk/kqk): _misa_ghi_mua_hang ghi RefDate với giờ cố định 10:00:00 thay vì nửa đêm.")

# ---- 3. Cùng kiểm tra cho _misa_ghi_mua_hang_dv ----
block_dv = extract(
    '            ngay_dt = None\n            ngay_str = str(first[cfg["ngayct"]] or "").strip()\n'
    '            for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):\n'
    '                try:\n                    ngay_dt = datetime.datetime.strptime(ngay_str, fmt)\n'
    '                    break\n                except Exception:\n                    pass\n'
    '            ngay_loi = ngay_dt is None\n            ngay_dt = _misa_gio_nhap_co_dinh(ngay_dt or now)\n'
    '            co_tk = str(first[cfg["co"]] or "").strip()',
    '            # ƯU TIÊN dò RefType theo ĐÚNG phương thức thanh toán')
assert "_misa_gio_nhap_co_dinh" in block_dv
ns2 = {"datetime": datetime, "_misa_gio_nhap_co_dinh": server._misa_gio_nhap_co_dinh,
       "first": {"ngayct": "05/08/2026", "co": ""}, "cfg": {"ngayct": "ngayct", "co": "co"},
       "now": datetime.datetime(2026, 8, 31, 8, 15, 0)}
exec(compile(block_dv, "<ghi_mua_hang_dv_ngay>", "exec"), ns2)
assert ns2["ngay_dt"] == datetime.datetime(2026, 8, 5, 10, 0, 0), (
    f"ngay_dt (dv) phải là 05/08/2026 10:00:00 — được {ns2['ngay_dt']}")
print("PASS (dv): _misa_ghi_mua_hang_dv cũng ghi giờ cố định 10:00:00.")

print("\nTẤT CẢ TEST PASS")
