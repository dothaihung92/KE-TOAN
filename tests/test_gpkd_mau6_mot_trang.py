import os, shutil, subprocess, sys, tempfile
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import gpkd_soan as g
# Mẫu số 6 (Danh sách thành viên) gọn trong MỘT trang ngang khi ít thành viên (bảng + khối ký + chú thích); nhiều thành viên thì tự xuống trang.
def tao(n):
    ht = [{"ho_ten": f"LÊ THẠCH {i}", "von": "650000000", "cccd": "07508600448" + str(i), "ngay_sinh": "02/11/1986", "gioi_tinh": "Nam", "quoc_tich": "Việt Nam", "dan_toc": "Kinh",
           "dia_chi": "763/5/4/14 Trường Chinh, Phường Tây Thạnh, Thành phố Hồ Chí Minh, Việt Nam", "noi_cap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội", "ngay_cap": "10/07/2022",
           "thoi_han": "30/04/2026"} for i in range(n)]
    return g.soan_phu_luc_i6({"dn": {"ten": "CÔNG TY TNHH GIẢ", "ma_so": "0300000001", "ngay_lap": "17/11/2026", "dia_danh": "TP. Hồ Chí Minh"}, "hien_tai": {"dd_ho_ten": "LÊ THẠCH"}, "thanh_vien": {"ht": ht, "moi": []}}, {})
d = tao(2)
sec = d.sections[0]
assert sec.page_width > sec.page_height and sec.top_margin < g.Cm(1) and len(d.tables[0].rows) == 3 + 2
w = [c.width for c in d.tables[0].rows[3].cells]
assert w[7] > w[0] * 4 and w[4] > w[0] * 3, w                  # cột Địa chỉ + Giấy tờ đủ rộng
print("PASS 1: Mẫu 6 lề hẹp, cột Địa chỉ/Giấy tờ rộng.")
exe = shutil.which("soffice") or shutil.which("libreoffice")
if exe:
    def trang(n):
        tmp = tempfile.mkdtemp(); f = os.path.join(tmp, "m6.docx"); tao(n).save(f)
        subprocess.run([exe, "--headless", "--convert-to", "pdf", "--outdir", tmp, f], capture_output=True, timeout=120)
        out = subprocess.run(["pdfinfo", os.path.join(tmp, "m6.pdf")], capture_output=True, text=True).stdout
        return int([x for x in out.splitlines() if x.startswith("Pages")][0].split()[1])
    assert trang(2) == 1 and trang(3) == 1, "ít thành viên phải vừa 1 trang"
    assert trang(8) >= 2
    print("PASS 2: 2-3 thành viên vừa 1 trang; 8 thành viên tự xuống trang.")
print("\nALL DONE")
