import os, sys, re, subprocess, shutil
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Ca thật: công ty nộp GTGT theo mẫu 03/GTGT (trực tiếp trên GTGT, mã 846) hoặc 04/GTGT (trực tiếp trên doanh thu, mã 847) —
# cổng báo "Đã chấp nhận" nhưng "Tra cứu tờ khai hàng loạt" không ghi nhận vì chỉ nhận mẫu 01/GTGT.
L = server._la_to_khai_loai
for ten in ("01/GTGT - Tờ khai thuế GTGT khấu trừ (TT80/2021)", "02/GTGT - Tờ khai thuế GTGT dành cho dự án đầu tư",
            "03/GTGT - Tờ khai thuế GTGT (TT80/2021)", "04/GTGT - Tờ khai thuế GTGT (TT80/2021)",
            "TỜ KHAI THUẾ GIÁ TRỊ GIA TĂNG (Mẫu số 03/GTGT)", "TỜ KHAI THUẾ GIÁ TRỊ GIA TĂNG (Mẫu số 04/GTGT)",
            "TỜ KHAI THUẾ GIÁ TRỊ GIA TĂNG (TT80/2021)(01/GTGT)", "Tờ khai thuế giá trị gia tăng"):
    assert L(ten, "GTGT"), ten
    assert not L(ten, "TNCN"), ten
for ten in ("05/KK-TNCN - Tờ khai khấu trừ thuế TNCN (TT80/2021)", "05/QTT-TNCN - Quyết toán TNCN", "03/TNDN - Quyết toán TNDN", "Báo cáo tài chính"):
    assert not L(ten, "GTGT"), ten
assert L("05/KK-TNCN - Tờ khai khấu trừ thuế TNCN (TT80/2021)", "TNCN")
# phân tích hồ sơ đã nộp: 03/GTGT & 04/GTGT "Đã chấp nhận" đúng quý 3/2026 -> xác nhận
for ten in ("03/GTGT - Tờ khai thuế GTGT (TT80/2021)", "04/GTGT - Tờ khai thuế GTGT (TT80/2021)"):
    hs = [{"to_khai": ten, "ky": "Quý 3/2026", "trang_thai": "Đã chấp nhận", "lan_bs": "0"}]
    xn, tt, ct = server._dvc_phan_tich_da_nop(hs, "GTGT", "01/07/2026", "30/09/2026", "01/10/2026", "31/10/2026")
    assert xn is True and "Đã chấp nhận" in tt, (ten, xn, tt, ct)
assert server._ten_file_than_thien("03/GTGT - Tờ khai thuế GTGT", "Quý 3/2026", "0319624595", "0") == "03GTGT_QUY3.2026-0319624595"
assert server._ten_file_than_thien("04/GTGT - Tờ khai thuế GTGT", "Quý 3/2026", "3702267465", "0") == "04GTGT_QUY3.2026-3702267465"
print("PASS 1: mọi mẫu GTGT (01/02/03/04) được ghi nhận là tờ khai GTGT; TNCN/TNDN/BCTC không bị nhầm.")

# Kỳ quý mặc định = quý VỪA KẾT THÚC (tháng 10-12 -> Quý 3; tháng 1-3 -> Quý 4 năm trước ...)
html = open(os.path.join(_REPO_ROOT, "static", "index.html"), encoding="utf-8").read()
m = re.search(r"function kyQuyMacDinh\(now\)\{.*?\n\}", html, re.S)
assert m and "kyQuyMacDinh(now)" in html.split("async function moDVCBatch(){", 1)[1][:600]
node = shutil.which("node")
if node:
    js = m.group(0) + """
const kq={};
for(let th=1;th<=12;th++){const k=kyQuyMacDinh(new Date(2026,th-1,15));kq[th]=k.quy+'/'+k.nam}
console.log(JSON.stringify(kq));"""
    import json
    out = json.loads(subprocess.run([node, "-e", js], capture_output=True, text=True, check=True).stdout)
    mong = {1: "4/2025", 2: "4/2025", 3: "4/2025", 4: "1/2026", 5: "1/2026", 6: "1/2026",
            7: "2/2026", 8: "2/2026", 9: "2/2026", 10: "3/2026", 11: "3/2026", 12: "3/2026"}
    assert out == {str(k): v for k, v in mong.items()}, out
    print("PASS 2: kỳ quý mặc định: T10-12 -> Quý 3, T1-3 -> Quý 4 năm trước, T4-6 -> Quý 1, T7-9 -> Quý 2.")
else:
    print("SKIP 2: không có node")
