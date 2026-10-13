import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Regression: HĐ C26TBV 150677 / 153910 (vé máy bay + "Các khoản thu hộ nhà chức trách" trong DSLPhi) bị sheet Đối chiếu báo LỆCH đúng bằng tiền phí:
# "Chi tiết MUA VÀO" có dòng hàng 8% (1.560.370) + dòng "Tổng tiền phí" KCT (234.362) = 1.794.732, còn "BK Mua vào" ghi dòng hàng chính 1.794.732
# (lấy tổng từ Chi tiết, ĐÃ gồm phí) RỒI cộng thêm dòng phí 234.362 -> 2.029.094 (phí bị tính 2 lần).


def hd(thtien, sl, phi, thue):
    return (f"<HDon><DLHDon><TTChung><KHMSHDon>1</KHMSHDon><KHHDon>C26TBV</KHHDon><SHDon>150677</SHDon><NLap>2026-07-07</NLap></TTChung><NDHDon>"
            f"<NBan><Ten>A</Ten><MST>0312479363</MST></NBan><NMua><Ten>B</Ten><MST>0316485079</MST></NMua>"
            f"<DSHHDVu><HHDVu><TChat>1</TChat><STT>1</STT><MHHDVu>VMB</MHHDVu><THHDVu>Vé máy bay</THHDVu><SLuong>{sl}</SLuong><DGia>780185</DGia><ThTien>{thtien}</ThTien><TSuat>8%</TSuat></HHDVu></DSHHDVu>"
            f"<TToan><THTTLTSuat><LTSuat><TSuat>8%</TSuat><ThTien>{thtien}</ThTien><TThue>{thue}</TThue></LTSuat></THTTLTSuat><TgTCThue>{thtien}</TgTCThue><TgTThue>{thue}</TgTThue>"
            f"<DSLPhi><LPhi><TLPhi>Các khoản thu hộ nhà chức trách</TLPhi><TPhi>{phi}</TPhi></LPhi></DSLPhi></TToan></NDHDon></DLHDon></HDon>").encode("utf-8")


for (tt, sl, phi, thue) in ((1560370, 2, 234362, 124830), (780185, 1, 117181, 62415)):
    rows = server._parse_xml_invoice(hd(tt, sl, phi, thue))
    hang = [r for r in rows if not r.get("_la_phi")]
    assert len(hang) == 1 and server._tong_phi_cac_dong(rows) == phi, rows
    # tổng "Chi tiết" (hàng + phí) trừ phí = dòng hàng chính của BK
    ct_ds = sum(server._to_num(r["thtien"]) for r in rows)
    assert ct_ds == tt + phi
    assert ct_ds - server._tong_phi_cac_dong(rows) == tt
assert server._tong_phi_cac_dong([]) == 0 and server._tong_phi_cac_dong([{"thtien": 5}]) == 0
print("PASS 1: tổng phí của hóa đơn có DSLPhi tách đúng; dòng hàng chính = tổng Chi tiết - phí.")

src = open(os.path.join(_REPO_ROOT, "server.py"), encoding="utf-8").read()
a = src.index('ws = wb.create_sheet("BK Mua vào")')
b = src.index('ws = wb.create_sheet("BK Bán ra")')
than = src[a:b]
assert "if ct_tong is not None and isinstance(ds, (int, float)):" in than and "ds = ds - _tong_phi_cac_dong(_items)" in than
assert than.index("ds = ds - _tong_phi_cac_dong(_items)") < than.index("ws.append([stt, r[\"khhdon\"]")
print("PASS 2: BK Mua vào trừ phí khỏi dòng hàng chính trước khi ghi (phí chỉ còn 1 lần ở dòng riêng).")
print("\nALL DONE")
