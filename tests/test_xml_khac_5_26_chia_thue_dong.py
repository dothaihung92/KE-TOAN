import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Hóa đơn thuế suất lẻ "KHAC:5.26%" (= 5/95, thuế tính trên giá đã gồm thuế), dòng hàng KHÔNG ghi tiền thuế, chỉ có tổng hợp THTTLTSuat.
# Lỗi thật (C26TAA 377430): phần mềm làm tròn 5.26% về 5% cho từng dòng rồi dòng cuối bù chênh (81.644 thay vì 55.263) -> sheet Đối chiếu báo lệch.
# Đúng: chia theo THUẾ SUẤT THỰC = TThue / ThTien của nhóm, dòng cuối chỉ bù phần làm tròn.
DONG = [(6710000, "Phí A"), (2614600, "Phí B"), (260000, "Phí C"), (440000, "Phí D"), (1050000, "Phí E")]
hh = "".join(f"<HHDVu><TChat>1</TChat><STT>{i}</STT><THHDVu>{t}</THHDVu><ThTien>{v}</ThTien><TSuat>KHAC:5.26%</TSuat></HHDVu>" for i, (v, t) in enumerate(DONG, 1))
xml = ("<HDon><DLHDon><TTChung><KHMSHDon>1</KHMSHDon><KHHDon>C26TAA</KHHDon><SHDon>00000001</SHDon><NLap>2026-09-23</NLap></TTChung>"
       "<NDHDon><NBan><Ten>NB</Ten><MST>0304207743</MST></NBan><NMua><Ten>NM</Ten><MST>0315502878</MST></NMua>"
       f"<DSHHDVu>{hh}</DSHHDVu><TToan><THTTLTSuat><LTSuat><TSuat>KHAC:5.26%</TSuat><ThTien>11074600</ThTien><TThue>582874</TThue></LTSuat></THTTLTSuat>"
       "<TgTCThue>11074600</TgTCThue><TgTThue>582874</TgTThue><TgTTTBSo>11657474</TgTTTBSo></TToan></NDHDon></DLHDon></HDon>").encode("utf-8")
rows = server._parse_xml_invoice(xml)
thue = [r["tien_thue"] for r in rows]
assert thue == [353158, 137611, 13684, 23158, 55263], thue      # = round(thành tiền x 5/95), cộng đúng 582.874
assert sum(thue) == 582874
for r in rows:                                                  # không dòng nào lệch nhãn 5,26% quá mức làm tròn (sheet Đối chiếu không báo)
    assert abs(r["tien_thue"] - float(r["thtien"]) * 0.0526) <= max(10, float(r["thtien"]) * 0.005)
print("PASS 1: thuế suất lẻ KHAC:5.26% chia theo thuế suất thực, tổng khớp hóa đơn, không dồn chênh vào dòng cuối.")

# không hồi quy: thuế suất chuẩn 8% vẫn tính 8%/dòng, dòng cuối bù làm tròn
xml8 = xml.replace(b"KHAC:5.26%", b"8%").replace(b"<TThue>582874</TThue>", b"<TThue>885968</TThue>")
t8 = [r["tien_thue"] for r in server._parse_xml_invoice(xml8)]
assert t8[0] == round(6710000 * 0.08) and sum(t8) == 885968, t8
print("PASS 2: thuế suất chuẩn 8% không đổi cách tính.")
print("ALL DONE")
