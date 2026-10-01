import os, sys, types
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
import server

# Regression — người dùng báo "đối chiếu bảng kê đầu ra bị lệch" (file DoiChieu_GiaTriVAT + BangKe_HoaDon T09/2026):
# HĐ bán ra C26MHH-10216 và 10400 có dòng "Chiết khấu thương mại" (không SL/đơn giá, thành tiền/thuế ghi DƯƠNG).
# Nguồn Thuế (tgtcthue) = hàng - chiết khấu: 1.080.000 - 89.259 = 990.741 (thuế 86.400 - 7.140 = 79.260).
# Bản cũ chỉ phần MUA VÀO biết TRỪ dòng này; BK Bán ra / Chi tiết BÁN RA CỘNG DƯƠNG -> 1.169.259 / 93.540, MISA ghi
# theo đó -> đối chiếu báo LỆCH (và tờ khai 01/GTGT khai thừa doanh thu/thuế đầu ra).

def hh(stt, ten, sl, dg, tt, ts, thue, tchat="1", ck=None):
    d = {"stt": stt, "tchat": tchat, "thhdvu": ten, "sluong": sl, "dgia": dg, "thtien": tt, "ltsuat": ts, "tthue": thue}
    if ck is not None:
        d["stckhau"] = ck
    return d

d10216 = {"khhdon": "C26MHH", "shdon": "10216", "tgtcthue": 990741, "tgtthue": 79260, "tgtttbso": 1070001,
          "hdhhdvu": [hh(1, "Bột ngọt AJI-NO-MOTO 2kgR15", 1, 1080000, 1080000, "8%", 86400),
                      hh(2, "Chiết khấu thương mại", None, None, 89259, "8%", 7140, tchat="3")]}
inf = server._summary_from_detail_json(d10216)
assert inf["theo_ts"]["8"]["ds"] == 990741 and inf["theo_ts"]["8"]["thue"] == 79260, inf["theo_ts"]
print("PASS 1: JSON HĐ 10216 -> doanh số 990.741 / thuế 79.260 (khớp nguồn Thuế), không cộng dương dòng chiết khấu.")

d10400 = {"khhdon": "C26MHH", "shdon": "10400", "tgtcthue": 32457222, "tgtthue": 2596578,
          "hdhhdvu": [hh(1, "Nước tinh khiết Satori 500ml.", 200, 91000, 18200000, "8%", 1456000),
                      hh(2, "Nước tinh khiết Satori 1.500ml.", 200, 91000, 18200000, "8%", 1456000),
                      hh(3, "Nước tinh khiết Satori 350ml.", 200, 82000, 16400000, "8%", 1312000),
                      hh(4, "Chiết khấu thương mại", None, None, 20342778, "8%", 1627422)]}   # TChat không có -> nhận theo tên
inf = server._summary_from_detail_json(d10400)
assert inf["theo_ts"]["8"]["ds"] == 32457222 and inf["theo_ts"]["8"]["thue"] == 2596578, inf["theo_ts"]
print("PASS 2: HĐ 10400 (dòng CK không có TChat, nhận theo tên + không SL/đơn giá) -> 32.457.222 / 2.596.578.")

# XML tương đương
xml = """<HDon><DLHDon><TTChung><KHMSHDon>1</KHMSHDon><KHHDon>C26MHH</KHHDon><SHDon>10216</SHDon></TTChung>
<NDHDon><NBan><Ten>A</Ten><MST>0318712827</MST></NBan><NMua><Ten>DG GROUP</Ten><MST>0316873240</MST></NMua>
<DSHHDVu>
<HHDVu><TChat>1</TChat><STT>1</STT><THHDVu>Bột ngọt</THHDVu><SLuong>1</SLuong><DGia>1080000</DGia><ThTien>1080000</ThTien><TSuat>8%</TSuat>
<TTKhac><TTin><TTruong>TongTien_Thue</TTruong><DLieu>86400</DLieu></TTin></TTKhac></HHDVu>
<HHDVu><TChat>3</TChat><STT>2</STT><THHDVu>Chiết khấu thương mại</THHDVu><ThTien>89259</ThTien><TSuat>8%</TSuat>
<TTKhac><TTin><TTruong>TongTien_Thue</TTruong><DLieu>7140</DLieu></TTin></TTKhac></HHDVu>
</DSHHDVu><TToan><TgTCThue>990741</TgTCThue><TgTThue>79260</TgTThue></TToan></NDHDon></DLHDon></HDon>"""
inf = server._parse_invoice_summary(xml.encode("utf-8"))
assert inf and inf["theo_ts"]["8"]["ds"] == 990741 and inf["theo_ts"]["8"]["thue"] == 79260, inf and inf["theo_ts"]
print("PASS 3: XML HĐ 10216 -> 990.741 / 79.260.")

# An toàn: TgTCThue khớp với cách CỘNG (nhà cung cấp ghi dòng 'chiết khấu' chỉ để tham khảo) -> KHÔNG trừ
d_ref = dict(d10216, tgtcthue=1169259, tgtthue=93540)
inf = server._summary_from_detail_json(d_ref)
assert inf["theo_ts"]["8"]["ds"] == 1169259 and inf["theo_ts"]["8"]["thue"] == 93540, inf["theo_ts"]
# Dòng TChat=3 CÓ STCKhau>0 là HÀNG giảm giá (không phải CK riêng) -> không bị trừ
d_hang = {"tgtcthue": 900000, "hdhhdvu": [hh(1, "Hàng A", 10, 100000, 1000000, "8%", 80000, tchat="3", ck=100000)]}
assert server._summary_from_detail_json(d_hang)["theo_ts"]["8"]["ds"] == 1000000
# Hàng thật tên chứa 'chiết khấu' nhưng có SL/đơn giá -> không bị coi là CK
d_ten = {"tgtcthue": 500000, "hdhhdvu": [hh(1, "Bột giặt Chiết Khấu Xanh", 10, 50000, 500000, "8%", 40000)]}
assert server._summary_from_detail_json(d_ten)["theo_ts"]["8"]["ds"] == 500000
# Hóa đơn bình thường không đổi
d_bt = {"tgtcthue": 300000, "hdhhdvu": [hh(1, "A", 1, 100000, 100000, "8%", 8000), hh(2, "B", 2, 100000, 200000, "10%", 20000)]}
t = server._summary_from_detail_json(d_bt)["theo_ts"]
assert t["8"]["ds"] == 100000 and t["10"]["ds"] == 200000 and t["10"]["thue"] == 20000
print("PASS 4: an toàn — TgTCThue khớp cách cộng thì không trừ; TChat=3 có STCKhau / hàng có SL-đơn giá / HĐ thường không đổi.")

# Chi tiết BÁN RA: phan_bo_chiet_khau(chi_ck_rieng=True) trừ CK vào dòng hàng, KHÔNG đụng STCKhau/NQ204/âm sẵn
src = open(os.path.join(_ROOT, "server.py"), encoding="utf-8").read()
def nested(name):
    idx = src.index("def " + name + "(")
    ls = src.rfind("\n", 0, idx) + 1
    ind = idx - ls
    i = src.index(":", idx)
    body = []
    started = False
    for ln in src[i + 1:].split("\n"):
        if ln.strip() == "":
            body.append(ln); continue
        if len(ln) - len(ln.lstrip(" ")) <= ind and started:
            break
        started = True
        body.append(ln)
    return src[idx:i + 1] + "\n".join(body)
ns = {}
for nm in ("_to_num", "_parse_thue_suat", "_dong_ck_tm_rieng", "_nen_tru_ck_tm_rieng"):
    exec(nested(nm), ns)
exec(nested("phan_bo_chiet_khau"), ns)
pb = ns["phan_bo_chiet_khau"]
def it(tchat, ten, sl, dg, tt, ts="8%", tthue=None, ck=0):
    return {"tchat": tchat, "ten_hang": ten, "sluong": sl, "dgia": dg, "thtien": tt, "tsuat": ts, "tien_thue": tthue, "stckhau": ck}
out = pb([it("1", "Bột ngọt", 1, 1080000, 1080000, tthue=86400), it("3", "Chiết khấu thương mại", 0, 0, 89259, tthue=7140)], 990741, chi_ck_rieng=True)
assert len(out) == 1 and out[0]["thtien"] == 990741 and abs(out[0]["tien_thue"] - 79260) <= 1, out
# HĐ bán ra có dòng ghi chú TChat=4 thành tiền 0 vẫn giữ như trước
out = pb([it("1", "A", 1, 100, 100), it("4", "Ghi chú", 0, 0, 0)], 100, chi_ck_rieng=True)
assert len(out) == 2
# STCKhau trên dòng hàng bán ra KHÔNG bị trừ lần nữa (BK Bán ra không trừ loại này)
out = pb([it("1", "A", 10, 100000, 1000000, ck=100000)], 1000000, chi_ck_rieng=True)
assert out[0]["thtien"] == 1000000
# Có CK riêng nhưng TgTCThue khớp cách cộng -> không trừ
out = pb([it("1", "Bột ngọt", 1, 1080000, 1080000), it("3", "Chiết khấu thương mại", 0, 0, 89259)], 1169259, chi_ck_rieng=True)
assert len(out) == 2
print("PASS 5: Chi tiết BÁN RA trừ CK riêng vào dòng hàng (HĐ 10216 -> 990.741), giữ nguyên STCKhau/ghi chú, an toàn khi TgTCThue khớp cách cộng.")
print("\nALL DONE")
