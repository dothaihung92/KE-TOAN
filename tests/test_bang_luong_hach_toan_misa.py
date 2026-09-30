import os
import sys
import asyncio
import random
import tempfile

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server
import openpyxl
from fastapi import HTTPException

# Yêu cầu: nút import hạch toán chi phí lương vào MISA (mục "Chứng từ nghiệp vụ khác") theo file mẫu người dùng gửi; dữ liệu lấy
# theo bảng lương từng tháng. Mẫu: (1) Hạch toán chi phí lương (Nợ 6422/Có 3341) + Trích BHXH/BHYT/BHTN (Nợ 6421/Có 3383/3384/3386)
# + "DN Trích" BHXH/BHYT/BHTN (Nợ 3341/Có 3383/3384/3386); (2) Hạch toán lương thuế TNCN (Nợ 3341/Có 3335); (3) TT lương (Nợ 3341/
# Có 1111). File mẫu: T1–T5 gộp (2)+(3) thành 1 chứng từ, từ T6 tách riêng (3 chứng từ/tháng) -> mặc định tách, tick "gộp" như T1–T5.

TS = server._luong_chuan_tham_so(None, 2025)
base = {"luong_cb": 5_310_000, "tien_com": 700_000, "muc_xang": 500_000, "pc_chuc_vu": 500_000, "muc_dt": 500_000, "trang_phuc": 400_000}


def bang_luong(thang, n=3, **kw):
    rows = []
    for i in range(n):
        d = dict(base, ma=str(i), ten=f"NV{i}", ghi_chu="CK" if i % 2 == 0 else "", **kw)
        if i == 2:
            d.update(dong_bh=0, ngay_lam=13, thuong_bh=1_000_000)
        rows.append(server._luong_tinh_dong(d, TS, thang))
    return rows


# ===== 1: tổng hợp từng tháng — thực lãnh = chi phí − BH người lao động − thuế (TK 334 đóng về 0 đúng từng đồng) =====
random.seed(5)
for _ in range(60):
    rows = [server._luong_tinh_dong(dict(base, luong_cb=random.randrange(4_000_000, 60_000_000), so_npt=random.randint(0, 3),
                                          ngay_lam=random.randint(5, 26), thuong_bh=random.randrange(0, 3_000_000),
                                          dong_bh=random.choice([0, 1]), ma=str(i), ten=f"N{i}"), TS, "03") for i in range(random.randint(1, 8))]
    g = server._luong_misa_tong(rows)
    assert g["tt_luong"] == g["chi_phi"] - sum(g["bh_nld"].values()) - g["thue"]
    assert abs(g["tt_luong"] - sum(r["tt_luong"] for r in rows)) <= len(rows), "Lệch so với tổng thực lãnh từng người chỉ do làm tròn"
    assert 0 <= g["tt_ck"] <= g["tt_luong"]
print("PASS 1: tổng hạch toán cân đúng: TT lương = chi phí − BH NLĐ − thuế (334 đóng về 0).")

# ===== 2: chứng từ theo mẫu: 2 chứng từ/tháng, đúng tài khoản + diễn giải + số chứng từ + ngày =====
r1 = bang_luong("01")
g1 = server._luong_misa_tong(r1)
ds = server._luong_misa_chung_tu(2025, {"01": r1}, {"gop_thue": True}, 1)             # gộp thuế + TT lương (như T1–T5 của file mẫu)
assert [c["so_ct"] for c in ds] == ["NVK1/1/2025", "NVK2/1/2025"] and all(c["ngay"] == "31/01/2025" for c in ds)
d1, d2 = ds
tach3 = server._luong_misa_chung_tu(2025, {"01": r1}, {}, 1)                             # mặc định: tách (như T6+ của file mẫu)
assert [c["so_ct"] for c in tach3] == ["NVK1/1/2025", "NVK2/1/2025", "NVK3/1/2025"]
assert [d["dien_giai"] for d in tach3[1]["dong"]] == ["Hạch toán lương thuế TNCN T1/2025"] and [d["dien_giai"] for d in tach3[2]["dong"]] == ["TT lương T1/2025"]
assert [d["dien_giai"] for d in tach3[1]["dong"] + tach3[2]["dong"]] == [d["dien_giai"] for d in d2["dong"]]
assert [(d["dien_giai"], d["no"], d["co"]) for d in d1["dong"]] == [
    ("Hạch toán chi phí lương T1/2025", "6422", "3341"), ("Trích BHXH T1/2025", "6421", "3383"), ("Trích BHYT T1/2025", "6421", "3384"),
    ("Trích BHTN T1/2025", "6421", "3386"), ("DN Trích BHXH T1/2025", "3341", "3383"), ("DN Trích BHYT T1/2025", "3341", "3384"),
    ("DN Trích BHTN T1/2025", "3341", "3386")]
assert [(d["dien_giai"], d["no"], d["co"]) for d in d2["dong"]] == [
    ("Hạch toán lương thuế TNCN T1/2025", "3341", "3335"), ("TT lương T1/2025", "3341", "1111")]
tien = lambda ct: {d["dien_giai"]: d["so_tien"] for d in ct["dong"]}
assert tien(d1)["Hạch toán chi phí lương T1/2025"] == g1["chi_phi"] and tien(d1)["Trích BHXH T1/2025"] == g1["bh_dn"]["bhxh"]
assert tien(d1)["DN Trích BHXH T1/2025"] == g1["bh_nld"]["bhxh"] and tien(d2)["Hạch toán lương thuế TNCN T1/2025"] == g1["thue"]
assert tien(d2)["TT lương T1/2025"] == g1["tt_luong"]
# cân TK 334: Có (chi phí) = Nợ (BH NLĐ + thuế + TT lương)
co334 = sum(d["so_tien"] for c in ds for d in c["dong"] if d["co"] == "3341")
no334 = sum(d["so_tien"] for c in ds for d in c["dong"] if d["no"] == "3341")
assert co334 == no334, (co334, no334)
print("PASS 2: chứng từ NVK đúng tài khoản + diễn giải như mẫu (gộp 2 / tách 3 chứng từ); TK 334 cân (Có = Nợ).")

# ===== 3: nhiều tháng: số chứng từ nối tiếp, ngày cuối tháng / ngày tự chọn (không vượt số ngày của tháng), bỏ dòng số tiền 0 =====
ds = server._luong_misa_chung_tu(2025, {"01": r1, "02": bang_luong("02"), "03": bang_luong("03")}, {"gop_thue": True}, 1)
assert [c["so_ct"] for c in ds] == ["NVK1/1/2025", "NVK2/1/2025", "NVK3/2/2025", "NVK4/2/2025", "NVK5/3/2025", "NVK6/3/2025"]
assert [c["ngay"] for c in ds][::2] == ["31/01/2025", "28/02/2025", "31/03/2025"]
dc = server._luong_misa_chung_tu(2025, {"01": r1, "02": bang_luong("02"), "04": bang_luong("04")}, {"ngay": 30}, 7)
assert [c["ngay"] for c in dc][::3] == ["30/01/2025", "28/02/2025", "30/04/2025"], "Ngày 30 tháng 2 -> ngày cuối tháng 28"
assert dc[0]["so_ct"] == "NVK7/1/2025" and [c["so_ct"] for c in dc][3] == "NVK10/2/2025", "Mặc định 3 chứng từ/tháng, số nối tiếp"
khong_bh = [server._luong_tinh_dong(dict(base, ma="9", ten="Thời vụ", dong_bh=0, ngay_lam=5), TS, "05")]
dk = server._luong_misa_chung_tu(2025, {"05": khong_bh}, {}, 1)
assert not any("Trích" in d["dien_giai"] for c in dk for d in c["dong"]), "Không ai đóng BH -> không có dòng trích BH (số 0 bị bỏ)"
assert all(d["so_tien"] > 0 for c in dk for d in c["dong"])
assert server._luong_misa_chung_tu(2025, {"05": []}, {}, 1) == []
print("PASS 3: số chứng từ nối tiếp, ngày cuối tháng/ngày tự chọn, dòng số tiền 0 bị bỏ.")

# ===== 4: tuỳ chọn tài khoản + tách lương chuyển khoản sang TK ngân hàng =====
tk = server._luong_misa_chung_tu(2025, {"01": r1}, {"tk_cp_luong": "642", "tk_cp_bh": "6422", "tach_ck": True}, 1)
assert tk[0]["dong"][0]["no"] == "642" and tk[0]["dong"][1]["no"] == "6422"
tt = [d for c_ in tk[1:] for d in c_["dong"] if d["dien_giai"].startswith("TT lương")]
assert [(d["dien_giai"], d["co"]) for d in tt] == [("TT lương T1/2025", "1111")], "Người tick Chuyển khoản: KHÔNG có dòng Nợ 3341/Có 1121"
assert tt[0]["so_tien"] == g1["tt_luong"] - g1["tt_ck"] and g1["tt_ck"] > 0 and not any(d["co"].startswith("112") for c_ in tk for d in c_["dong"])
# mọi người đều tick Chuyển khoản -> không còn dòng thanh toán lương nào (chỉ còn chi phí + BH + thuế)
cktat = server._luong_misa_chung_tu(2025, {"01": [dict(r, ghi_chu="CK") for r in r1]}, {"tach_ck": True}, 1)
assert not any(d["dien_giai"].startswith("TT lương") for c_ in cktat for d in c_["dong"])
tat = server._luong_misa_chung_tu(2025, {"01": r1}, {"tach_ck": False}, 1)
assert [d["co"] for d in tat[1]["dong"]] == ["3335"] and [d["co"] for d in tat[2]["dong"]] == ["1111"], "Mặc định (như mẫu): toàn bộ TT lương ghi Có 1111"
print("PASS 4: tài khoản tùy chỉnh; người tick Chuyển khoản không hạch toán thanh toán 1121.")

# ===== 5: file Excel đúng mẫu 'Chứng từ nghiệp vụ khác' của MISA =====
_dl = server.DOWNLOAD_DIR
server.DOWNLOAD_DIR = tempfile.mkdtemp()
try:
    duong, ten, so_dong = server._luong_xuat_misa_nvk(2025, tk, {"ma_thong_ke": "BHXH"})
    assert ten == "HachToanLuong_MISA_2025_T1-T1.xlsx" and so_dong == sum(len(c["dong"]) for c in tk)
    ws = openpyxl.load_workbook(duong).active
    assert ws.title == "Chứng từ nghiệp vụ khác"
    assert [c.value for c in ws[1]][:len(server._GLVOUCHER_HEADERS)] == server._GLVOUCHER_HEADERS
    cot = {h: i + 1 for i, h in enumerate(server._GLVOUCHER_HEADERS)}
    v = lambda r, h: ws.cell(r, cot[h]).value
    assert v(2, "Hiển thị trên sổ") == 0 and v(2, "Ngày chứng từ (*)") == "31/01/2025" and v(2, "Ngày hạch toán (*)") == "31/01/2025"
    assert v(2, "Số chứng từ (*)") == "NVK1/1/2025" and v(2, "Diễn giải") == "Hạch toán chi phí lương T1/2025" == v(2, "Diễn giải (Hạch toán)")
    assert v(2, "TK Nợ (*)") == "642" and v(2, "TK Có (*)") == "3341" and v(2, "Số tiền") == g1["chi_phi"] == v(2, "Số tiền quy đổi")
    assert v(2, "Loại tiền") == "VND" and v(2, "Tỷ giá") == 1
    assert v(3, "Mã thống kê") == "BHXH" and v(2, "Mã thống kê") is None, "Mã thống kê chỉ ở dòng BH"
    cuoi = ws.max_row
    assert v(cuoi, "TK Có (*)") == "1111" and all(ws.cell(r, cot["TK ngân hàng"]).value is None for r in range(2, cuoi + 1))
    assert ws.cell(2, cot["Số tiền"]).number_format == "#,##0"
    print("PASS 5: file Excel đúng tiêu đề mẫu MISA; ngày/số CT/diễn giải/TK/số tiền đúng; không có dòng 1121.")

    # ===== 6: API xem trước + xuất file; lỗi khi không có dữ liệu =====
    class _Req:
        def __init__(self, b): self._b = b
        async def json(self): return self._b
    payload = {"nam": 2025, "thang": {"01": [{k: r[k] for k in ("chi_phi_luong", "tt_luong", "thue_tru_luong", "bhxh_dn", "bhyt_dn", "bhtn_dn", "bhxh_nld",
                                                                  "bhyt_nld", "bhtn_nld", "ghi_chu")} for r in r1], "02": []}}
    xem = asyncio.run(server.bang_luong_hach_toan_misa(1, _Req(dict(payload, xuat=False, gop_thue=True))))
    assert len(xem["chung_tu"]) == 2 and xem["so_dong"] == 9 and xem["so_bat_dau"] == 1, xem["so_bat_dau"]
    assert xem["chung_tu"][0]["dong"][0]["so_tien"] == g1["chi_phi"]
    xem3 = asyncio.run(server.bang_luong_hach_toan_misa(1, _Req(dict(payload, xuat=False))))
    assert len(xem3["chung_tu"]) == 3 and xem3["so_dong"] == 9, "Mặc định 3 chứng từ (chi phí + BH / thuế TNCN / TT lương)"
    kq = asyncio.run(server.bang_luong_hach_toan_misa(1, _Req(dict(payload, xuat=True, so_bat_dau=15))))
    assert os.path.exists(kq.path) and os.path.basename(kq.path) == "HachToanLuong_MISA_2025_T1-T1.xlsx"
    assert openpyxl.load_workbook(kq.path).active.cell(2, cot["Số chứng từ (*)"]).value == "NVK15/1/2025", "Số CT bắt đầu do người dùng nhập"
    for sai in ({"nam": 2025, "thang": {}}, {"nam": 2025, "thang": {"01": []}}):
        try:
            asyncio.run(server.bang_luong_hach_toan_misa(1, _Req(sai)))
            raise AssertionError("phải báo lỗi")
        except HTTPException as e:
            assert e.status_code == 404
    print("PASS 6: API xem trước/xuất file hoạt động; số CT bắt đầu tùy chỉnh; không có dữ liệu -> báo lỗi.")

    # ===== 7: số NVK bắt đầu: nối tiếp số cao nhất đang có trong MISA (nếu kết nối được), không thì theo mẫu (2 CT/tháng) =====
    class _Cur:
        def execute(self, sql): return self
        def fetchall(self): return [("NVK9/3/2025",), ("NVK21/6/2025",), ("PC001",), ("NVK3/1/2024",)]
    class _Conn:
        def cursor(self): return _Cur()
        def close(self): pass
    goc = (server._misa_sql_cfg, server._misa_sql_connect)
    server._misa_sql_cfg = lambda cid: {"database": "KT2025"}
    server._misa_sql_connect = lambda cid, database=None, **kw: _Conn()
    try:
        assert server._luong_misa_so_bat_dau(1, {}, 3) == 22, "Tiếp nối số NVK cao nhất trong MISA (21)"
        assert server._luong_misa_so_bat_dau(1, {"so_bat_dau": "40"}, 3) == 40, "Người dùng nhập thì ưu tiên"
        def loi(*a, **k): raise RuntimeError("không kết nối được")
        server._misa_sql_connect = loi
        assert server._luong_misa_so_bat_dau(1, {}, 3) == 7, "Không kết nối MISA -> 3 chứng từ/tháng: T3 = NVK7"
        assert server._luong_misa_so_bat_dau(1, {"gop_thue": True}, 3) == 5, "Gộp: 2 chứng từ/tháng: T3 = NVK5"
        server._misa_sql_cfg = lambda cid: {}
        assert server._luong_misa_so_bat_dau(1, {}, 1) == 1 and server._luong_misa_so_bat_dau(1, {}, 12) == 34
    finally:
        server._misa_sql_cfg, server._misa_sql_connect = goc
    print("PASS 7: số chứng từ bắt đầu: nhập tay > nối tiếp MISA > theo mẫu (T1=NVK1, T3=NVK7...).")
finally:
    server.DOWNLOAD_DIR = _dl

# ===== 8: khớp từng dòng với file mẫu người dùng gửi (Book2.xlsx): T1–T5 gộp 2 chứng từ/tháng, T6–T12 tách 3 chứng từ/tháng =====
def _mau_dong(t, dien_giai, no, co, so):
    return (so, dien_giai, no, co)
mau = []
so_ct = 1
for m in range(1, 13):
    kt = f"T{m}/2025"
    v1 = [(f"Hạch toán chi phí lương {kt}", "6422", "3341")] + [(f"Trích {b} {kt}", "6421", c) for b, c in (("BHXH", "3383"), ("BHYT", "3384"), ("BHTN", "3386"))] \
        + [(f"DN Trích {b} {kt}", "3341", c) for b, c in (("BHXH", "3383"), ("BHYT", "3384"), ("BHTN", "3386"))]
    tn, tt_ = (f"Hạch toán lương thuế TNCN {kt}", "3341", "3335"), (f"TT lương {kt}", "3341", "1111")
    cts = [v1, [tn, tt_]] if m <= 5 else [v1, [tn], [tt_]]
    for ct in cts:
        for d in ct:
            mau.append((f"NVK{so_ct}/{m}/2025",) + d)
        so_ct += 1
lon = {f"{m:02d}": [server._luong_tinh_dong({"luong_cb": 30_000_000, "tien_com": 700_000, "ma": "1", "ten": "A"}, TS, f"{m:02d}")] for m in range(1, 13)}
mine = server._luong_misa_chung_tu(2025, {k: v for k, v in lon.items() if int(k) <= 5}, {"gop_thue": True}, 1) + \
    server._luong_misa_chung_tu(2025, {k: v for k, v in lon.items() if int(k) >= 6}, {}, 11)
assert [(c["so_ct"], d["dien_giai"], d["no"], d["co"]) for c in mine for d in c["dong"]] == mau and len(mau) == 108
print("PASS 8: 108 dòng hạch toán 12 tháng khớp từng dòng với file mẫu (số chứng từ, diễn giải, TK Nợ, TK Có).")

print("\nALL DONE")
