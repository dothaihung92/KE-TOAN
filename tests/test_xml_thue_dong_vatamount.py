import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# HĐ chiết khấu Satori C26TSA số 6036 (XML thật người dùng gửi, rút gọn): xuất từ phần mềm MISA — tiền thuế dòng nằm ở TTKhac "VATAmount" (không có
# "TongTien_Thue"), dòng ghi TSuat 8% nhưng VATAmount = 0, TgTThue = 0 => hóa đơn KHÔNG có thuế. Bản cũ không đọc VATAmount nên tự tính 8% =
# 1.067.237 vào Bảng kê/MISA, lệch với nguồn Thuế (0).
def xml(vat_line, tgtthue="0.000000"):
    return ("<HDon><DLHDon><TTChung><KHMSHDon>1</KHMSHDon><KHHDon>C26TSA</KHHDon><SHDon>00006036</SHDon><NLap>2026-09-23</NLap></TTChung>"
            "<NDHDon><NBan><Ten>SATORI</Ten><MST>0319340593</MST></NBan><NMua><Ten>HCH</Ten><MST>0318712827</MST></NMua><DSHHDVu><HHDVu><TChat>1</TChat><STT>1</STT>"
            "<THHDVu>Hỗ trợ phát triển thị trường</THHDVu><SLuong>0.000000</SLuong><DGia>0.000000</DGia><ThTien>-13340460.000000</ThTien><TSuat>8%</TSuat>"
            "<TTKhac><TTin><TTruong>Amount</TTruong><DLieu>-13340460.0</DLieu></TTin>" + vat_line + "</TTKhac></HHDVu></DSHHDVu>"
            "<TToan><THTTLTSuat><LTSuat><TSuat>8%</TSuat><ThTien>-13340460.000000</ThTien><TThue>" + tgtthue + "</TThue></LTSuat></THTTLTSuat>"
            "<TgTCThue>-13340460.000000</TgTCThue><TgTThue>" + tgtthue + "</TgTThue><TgTTTBSo>-13340460.000000</TgTTTBSo></TToan></NDHDon></DLHDon></HDon>").encode("utf-8")

b = xml("<TTin><TTruong>VATAmount</TTruong><DLieu>0.0</DLieu></TTin>")
r = server._parse_xml_invoice(b)
assert len(r) == 1 and r[0]["tien_thue"] == "0.0" and server._to_num(r[0]["tien_thue"]) == 0, r[0]["tien_thue"]
s = server._parse_invoice_summary(b)["theo_ts"]["8"]
assert s["ds"] == -13340460 and s["thue"] == 0, s
print("PASS 1: XML kiểu MISA (VATAmount=0, TgTThue=0) -> thuế dòng = 0 (không tự tính 8%), cả Chi tiết lẫn tổng hợp.")

# có VATAmount khác 0 -> dùng đúng số đó; có TongTien_Thue thì ưu tiên TongTien_Thue; không có cả hai -> như cũ (để tính theo thuế suất)
b2 = xml("<TTin><TTruong>VATAmount</TTruong><DLieu>-1067237.0</DLieu></TTin>", "-1067237.000000")
assert server._to_num(server._parse_xml_invoice(b2)[0]["tien_thue"]) == -1067237 and server._parse_invoice_summary(b2)["theo_ts"]["8"]["thue"] == -1067237
b3 = xml("<TTin><TTruong>VATAmount</TTruong><DLieu>5.0</DLieu></TTin><TTin><TTruong>TongTien_Thue</TTruong><DLieu>-1067237.0</DLieu></TTin>", "-1067237.000000")
assert server._to_num(server._parse_xml_invoice(b3)[0]["tien_thue"]) == -1067237 and server._parse_invoice_summary(b3)["theo_ts"]["8"]["thue"] == -1067237
b4 = xml("")
assert server._parse_xml_invoice(b4)[0]["tien_thue"] == "" and server._parse_invoice_summary(b4)["theo_ts"]["8"]["thue"] == round(-13340460 * 0.08)
print("PASS 2: VATAmount khác 0 dùng đúng số; TongTien_Thue được ưu tiên; không có cả hai thì giữ cách cũ.")
print("\nALL DONE")
