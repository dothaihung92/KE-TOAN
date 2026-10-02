import os, sys, shutil, subprocess, tempfile, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server, openpyxl

# Excel bảng lương CẢ NĂM gộp: 1 người = 1 dòng, cộng dồn các tháng; tổng KHỚP bảng lương từng tháng (sheet "Đối chiếu tháng" = "✓ Khớp").
TS = server._luong_chuan_tham_so(None, 2026)
rng = random.Random(4)
dong = lambda ma, ten, **k: server._luong_chuan_dong_nhap(dict({"ma": ma, "ten": ten, "chuc_vu": "KD", "luong_cb": 5_310_000, "tien_com": 730_000, "muc_xang": 1_000_000, "muc_dt": 500_000,
                                                              "trang_phuc": 416_000, "dong_bh": 1}, **k))
thang_nhap = {}
for t in ("01", "02", "03", "07", "08"):
    rows = [dong("1", "An", ngay_lam=rng.choice([20, 22, 26]), thuong_bh=rng.randint(0, 5) * 1_000_000, tang_ca=rng.randint(0, 9) * 100_000),
            dong("2", "Bình", ngay_lam=rng.choice([14, 18, 26]), thuong_bh=rng.randint(0, 9) * 3_000_000)]
    if t in ("07", "08"):
        rows.append(dong("3", "Cường", ngay_lam=26, thuong_bh=12_345_678))
    thang_nhap[t] = rows
thang_tinh = {t: server._luong_tinh_thang(r, TS, t, 2026) for t, r in thang_nhap.items()}
path, fname, tt = server._luong_xuat_excel_nam_gop(2026, TS, thang_tinh, "CÔNG TY TNHH THỬ", "0300000001")

assert fname == "BangLuong_GopCaNam_2026.xlsx" and tt["so_nguoi"] == 3 and tt["so_dong_thang"] == 12

def tinh_lai(p):
    """Tính lại mọi công thức bằng thư viện formulas; trả hàm lấy giá trị (sheet, ô)."""
    try:
        import formulas
    except ImportError:
        return None
    sol = formulas.ExcelModel().loads(p).finish().calculate()
    base = os.path.basename(p).upper()

    def lay(sheet, o):
        for k in sol:
            if k.upper() == "'[%s]%s'!%s" % (base, sheet.upper(), o):
                v = sol[k].value[0][0]
                return v
        raise KeyError((sheet, o))
    return lay
lay = tinh_lai(path)
if lay is not None:
    wb = openpyxl.load_workbook(path)           # cấu trúc/cột
    ws = wb["CẢ NĂM"]
    L = openpyxl.utils.get_column_letter
    hdr = {str(ws.cell(5, j).value): j for j in range(1, ws.max_column + 1)}
    hang = {ws.cell(r, 3).value: r for r in range(6, ws.max_row + 1) if ws.cell(r, 3).value}
    assert set(hang) == {"An", "Bình", "Cường", "TỔNG CỘNG"}
    val = lambda ten, tieu_de: float(lay("CẢ NĂM", "%s%d" % (L(hdr[tieu_de]), hang[ten])))
    for ma, ten in (("1", "An"), ("2", "Bình"), ("3", "Cường")):
        ky = [k for t in thang_tinh for k in thang_tinh[t] if k["ma"] == ma]
        assert ws.cell(hang[ten], 5).value == len(ky)
        for tieu_de, kk in (("Chi phí lương (tổng)", "chi_phi_luong"), ("TT lương (thực lãnh)", "tt_luong"), ("Tiền lương", "luong"), ("PC Xăng xe", "xang_xe"),
                            ("Thuế TNCN (trừ lương)", "thue_tru_luong"), ("Trừ BHXH", "bhxh_nld"), ("Thưởng bán hàng", "thuong_bh"), ("Tăng ca (tiền)", "tang_ca")):
            ky_v = sum(server._luong_lam_tron(k[kk]) if kk in ("chi_phi_luong", "tt_luong") else k[kk] for k in ky)
            assert abs(val(ten, tieu_de) - ky_v) < 0.01, (ten, tieu_de, val(ten, tieu_de), ky_v)
    all_k = [k for t in thang_tinh for k in thang_tinh[t]]
    assert val("TỔNG CỘNG", "Chi phí lương (tổng)") == sum(server._luong_lam_tron(k["chi_phi_luong"]) for k in all_k)
    assert val("TỔNG CỘNG", "TT lương (thực lãnh)") == sum(server._luong_lam_tron(k["tt_luong"]) for k in all_k)
    dc = wb["Đối chiếu tháng"]
    assert dc.max_row == 1 + 5 + 3, "5 tháng + cộng + bảng cả năm + kết quả"
    for j in range(3, 8):
        kq = lay("Đối chiếu tháng", "%s%d" % (L(j), dc.max_row))
        assert str(kq).startswith("✓ Khớp"), kq
    print("PASS 1: gộp cả năm: mỗi người 1 dòng, cộng dồn đúng các tháng; tổng khớp bảng lương từng tháng; đối chiếu ✓ Khớp (tính lại công thức).")
else:
    print("SKIP: thiếu thư viện formulas")
# API
import asyncio
tmp = tempfile.mkdtemp(); server.DOWNLOAD_DIR = tmp
import sqlite3
f = os.path.join(tmp, "t.db")
def _db():
    c = sqlite3.connect(f); c.row_factory = sqlite3.Row; return c
server.db = _db
c0 = _db(); c0.execute("CREATE TABLE companies (id INTEGER PRIMARY KEY, ten TEXT, mst TEXT)"); c0.execute("INSERT INTO companies VALUES (1,'CT THỬ','0300000001')"); c0.commit(); c0.close()
server._luong_doc_nam = lambda cid, nam: (TS, thang_nhap, "", [2026])
resp = server.bang_luong_xuat_excel_nam_gop(1, 2026)
assert os.path.basename(resp.path) == "BangLuong_GopCaNam_2026.xlsx" and resp.headers["x-so-nguoi"] == "3"
server._luong_doc_nam = lambda cid, nam: (TS, {}, "", [])
try:
    server.bang_luong_xuat_excel_nam_gop(1, 2026); raise SystemExit("phải lỗi")
except server.HTTPException as e:
    assert e.status_code == 404
print("PASS 2: API xuất Excel cả năm gộp; năm chưa có dữ liệu báo lỗi.")
html = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "index.html"), encoding="utf-8").read()
assert 'onclick="blXuatExcelNamGop()"' in html and "xuat-excel-nam-gop?nam=${blNam}" in html and "Xuất Excel cả năm (gộp)" in html
print("PASS 3: có nút 'Xuất Excel cả năm (gộp)' trong hộp In bảng lương & chấm công.")
print("\nALL DONE")
