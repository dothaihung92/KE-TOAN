import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Regression: HĐ Cao Phong C26MCP (810976, 810987) ghi tiền thuế TỪNG DÒNG = 0 (TTKhac VATAmount=0, chỉ có Amount = giá thanh toán) nhưng TToan có thuế 8%
# (TThue 106.370 / 11.778). Trước đây Chi tiết MUA VÀO và BK Mua vào ghi thuế 0 -> sheet Đối chiếu báo lệch.


def hd(dong, tong_thue, thtien_tong, ts="8%"):
    ds = "".join(
        f"<HHDVu><TChat>1</TChat><STT>{i}</STT><THHDVu>H{i}</THHDVu><SLuong>1</SLuong><DGia>{t}</DGia><TSuat>{ts}</TSuat><ThTien>{t}</ThTien>"
        f"<TTKhac><TTin><TTruong>Amount</TTruong><DLieu>{t}</DLieu></TTin><TTin><TTruong>VATAmount</TTruong><DLieu>0</DLieu></TTin></TTKhac></HHDVu>"
        for i, t in enumerate(dong, 1))
    return (f"<HDon><DLHDon><TTChung><KHMSHDon>1</KHMSHDon><KHHDon>C26MCP</KHHDon><SHDon>1</SHDon><NLap>2026-07-04</NLap></TTChung><NDHDon>"
            f"<NBan><Ten>A</Ten><MST>0302309845</MST></NBan><NMua><Ten>B</Ten><MST>0318807606</MST></NMua><DSHHDVu>{ds}</DSHHDVu>"
            f"<TToan><THTTLTSuat><LTSuat><TSuat>{ts}</TSuat><TThue>{tong_thue}</TThue><ThTien>{thtien_tong}</ThTien></LTSuat></THTTLTSuat>"
            f"<TgTCThue>{thtien_tong}</TgTCThue><TgTThue>{tong_thue}</TgTThue></TToan></NDHDon></DLHDon></HDon>").encode("utf-8")


# 1 dòng (810976)
x1 = hd([1329630], 106370, 1329630)
assert [r["tien_thue"] for r in server._parse_xml_invoice(x1)] == [106370]
assert server._parse_invoice_summary(x1)["theo_ts"]["8"] == {"ds": 1329630, "thue": 11778 * 0 + 106370, "ds_nt": 1329630}
# 4 dòng (810987): chia theo thuế suất, cộng đúng TThue
x2 = hd([87963, 7407, 25926, 25926], 11778, 147222)
th = [r["tien_thue"] for r in server._parse_xml_invoice(x2)]
assert sum(th) == 11778 and all(t > 0 for t in th), th
assert server._parse_invoice_summary(x2)["theo_ts"]["8"]["thue"] == 11778
print("PASS 1: dòng ghi VATAmount=0 nhưng tổng hợp có thuế 8% -> ghi đúng tiền thuế (Chi tiết + BK).")

# làm tròn: dòng cuối nhóm bù chênh lệch để cộng đúng TThue
x3 = hd([333, 333, 333], 80, 999)
assert sum(r["tien_thue"] for r in server._parse_xml_invoice(x3)) == 80
print("PASS 2: chênh lệch làm tròn được bù ở dòng cuối.")

# HĐ thật sự không có thuế (tổng hợp = 0): giữ nguyên 0 (ca Satori C26TSA 6036)
x4 = hd([1000000], 0, 1000000)
assert [_to for _to in (server._to_num(r["tien_thue"]) for r in server._parse_xml_invoice(x4))] == [0]
assert server._parse_invoice_summary(x4)["theo_ts"]["8"]["thue"] == 0
print("PASS 3: hóa đơn không có thuế thật (TgTThue = 0) giữ nguyên.")

# dòng đã ghi thuế thật -> tin dữ liệu dòng
x5 = hd([1000000], 80000, 1000000).replace(b"<DLieu>0</DLieu></TTin></TTKhac>", b"<DLieu>80000</DLieu></TTin></TTKhac>")
assert [server._to_num(r["tien_thue"]) for r in server._parse_xml_invoice(x5)] == [80000]
print("PASS 4: dòng có VATAmount thật thì giữ.")
print("\nALL DONE")
