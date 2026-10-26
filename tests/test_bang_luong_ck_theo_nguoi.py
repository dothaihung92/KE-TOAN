import os, sys, random
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import io, datetime
import openpyxl
import server

# Ca thật (Cơ khí - Vận tải Thiên Phúc): import sổ chi tiết TK 334 (chuyển khoản lương, diễn giải "... TT LUONG THANG m.yyyy CHO <TÊN>") nhưng bảng lương
# chỉ khớp TỔNG từng tháng, mỗi người lệch (Trang +773.431/Tuấn -773.431 tháng 1...) và các khoản chi ngày 20/04 ghi "LUONG THANG 3.2026" bị xếp sang tháng 4.
DONG = [("20/01/2026", "TT LUONG THANG 1.2026 CHO HUA MINH TUAN", 13859950), ("20/01/2026", "TT LUONG THANG 1.2026 CHO LE THI HUYEN TRANG", 14694019),
        ("20/03/2026", "CHI TAM UNG LUONG THANG 3.2026 CHO HUA MINH TUAN", 10000000), ("20/03/2026", "TT LUONG THANG 3.2026 CHO LE THI HUYEN TRANG", 14188250),
        ("20/04/2026", "CHI LUONG THANG 3.2026 CHO HUA MINH TUAN", 9638625), ("20/04/2026", "TT LUONG THANG 4.2026 CHO LE THI HUYEN TRANG", 14576712),
        ("20/07/2026", "CHI TAM UNG LUONG THANG 7.2026 CHO LUU VAN KHOA", 12714379)]
wb = openpyxl.Workbook(); ws = wb.active
ws.append(["SỔ CHI TIẾT CÁC TÀI KHOẢN"]); ws.append(["Tài khoản: 3341; Năm 2026"])
ws.append(["Ngày hạch toán", "Ngày chứng từ", "Số chứng từ", "Số hóa đơn", "Diễn giải", "Tài khoản", "TK đối ứng", "Phát sinh Nợ", "Phát sinh Có", "Dư Nợ", "Dư Có"])
for i, (ng, dg, tien) in enumerate(DONG):
    d = datetime.datetime.strptime(ng, "%d/%m/%Y")
    ws.append([d, d, "UNC%d" % i, None, "CTY THIEN PHUC " + dg, "3341", "1121-TPB", tien, 0, 0, 0])
bio = io.BytesIO(); wb.save(bio)
ck = server._luong_doc_so_ck(bio.getvalue(), 2026)
assert ck["theo_thang"] == {"01": 28553969, "03": 33826875, "04": 14576712, "07": 12714379}, ck["theo_thang"]
assert ck["theo_nguoi"]["03"] == {"HUA MINH TUAN": 19638625, "LE THI HUYEN TRANG": 14188250}, ck["theo_nguoi"]
assert ck["theo_nguoi"]["04"] == {"LE THI HUYEN TRANG": 14576712} and ck["theo_nguoi"]["07"] == {"LUU VAN KHOA": 12714379}
assert any("khác tháng với kỳ lương" in c for c in ck["canh_bao"])
print("PASS 1: đọc sổ TK 334 — kỳ lương trong diễn giải ưu tiên hơn ngày chi (lương T3 chi 20/04 vào T3), tên người nhận lấy từ 'CHO <TÊN>', cộng theo người/tháng.")

H = server.NV_HEADERS
def nv(stt, ma, ten, vao, chuc):
    d = dict.fromkeys(H, ""); d.update({"STT": stt, "Mã NV": ma, "Họ và tên": ten, "Tháng/Năm vào làm": vao, "Đóng BHXH": "x", "Chức vụ": chuc,
                                        "Lương Cơ bản": 5310000, "PC Tiền cơm": 730000, "PC Xăng xe": 2000000, "PC Điện thoại": 1000000, "PC Trang phục": 400000})
    return [d[h] for h in H]
rows = [nv(1, "1-001", "Lê Thị Huyền Trang", "01/2025", "Kế Toán"), nv(2, "2", "Lưu Văn Khoa", "02/2025", "Tài Xế"), nv(3, "3-001", "Hứa Minh Tuấn", "01/2025", "Tài xế")]
pool = lambda t: server._luong_dong_tu_nhan_vien(H, rows, 0, 2026, int(t))
th, tom = server._luong_ke_hoach(pool, 2026, 1, 7, 0, None, 50.0, 0, random.Random(3), False, None, ck["theo_thang"], 12000000, False, ck_theo_nguoi=ck["theo_nguoi"])
tt = lambda t, ten: sum(r["tt_luong"] for r in th[t] if server._luong_ten_chuan(r["ten"]) == ten and r["ghi_chu"] == "CK")
assert tt("01", "HUA MINH TUAN") == 13859950 and tt("01", "LE THI HUYEN TRANG") == 14694019
assert tt("03", "HUA MINH TUAN") == 19638625 and tt("03", "LE THI HUYEN TRANG") == 14188250
assert tt("04", "LE THI HUYEN TRANG") == 14576712 and tt("07", "LUU VAN KHOA") == 12714379
for t, so in ck["theo_thang"].items():
    assert sum(r["tt_luong"] for r in th[t] if r["ghi_chu"] == "CK") == so, t
print("PASS 2: TT lương chuyển khoản TỪNG NGƯỜI = đúng số người đó đã nhận (Tuấn T3 19.638.625 = tạm ứng + chi bổ sung), tổng tháng khớp từng đồng.")

# không có tên khớp -> cách cũ (khớp tổng, chia nhiều người)
th2, _ = server._luong_ke_hoach(pool, 2026, 1, 1, 0, None, 50.0, 0, random.Random(3), False, None, {"01": 28553969}, 12000000, False, ck_theo_nguoi={"01": {"NGUOI LA": 28553969}})
assert sum(r["tt_luong"] for r in th2["01"] if r["ghi_chu"] == "CK") == 28553969
print("PASS 3: tên không khớp ai trong Danh Sách Nhân Viên -> vẫn khớp tổng tháng như cũ.")
print("ALL DONE")
