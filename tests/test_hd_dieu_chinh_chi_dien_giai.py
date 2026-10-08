import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Hóa đơn điều chỉnh thuế (vd C26TVN 279, mua vào): dòng hàng DUY NHẤT là diễn giải TChat=4 "Điều chỉnh thuế GTGT ... từ 10% thành 8%" (không thành tiền,
# không thuế suất); số tiền CHỈ nằm ở khối tổng hợp THTTLTSuat: 8%, Thành tiền 0, Thuế -48.112. Trước đây: Chi tiết MUA VÀO không có dòng nào, BK Mua vào
# lấy nhầm Tổng thanh toán (-48.112) làm Doanh số chưa thuế -> sheet Đối chiếu báo lệch -48.112 cả hàng hóa lẫn VAT.
XML = ("<HDon><DLHDon><TTChung><KHMSHDon>1</KHMSHDon><KHHDon>C26TVN</KHHDon><SHDon>0000279</SHDon><NLap>2026-08-01</NLap><DVTTe>VND</DVTTe><TGia>1.00</TGia>"
       "<TTHDLQuan><TCHDon>2</TCHDon><SHDCLQuan>0000267</SHDCLQuan></TTHDLQuan></TTChung><NDHDon><NBan><Ten>DAVINCI</Ten><MST>0319194423</MST></NBan>"
       "<NMua><Ten>NGỌC PHÁT</Ten><MST>0318332127</MST></NMua><DSHHDVu><HHDVu><TChat>4</TChat><STT/><THHDVu>Điều chỉnh thuế GTGT hóa đơn số 0000267 từ 10% thành 8%</THHDVu>"
       "<SLuong/><DGia/><ThTien/><TSuat/></HHDVu></DSHHDVu><TToan><THTTLTSuat><LTSuat><TSuat>8%</TSuat><ThTien>0.000000</ThTien><TThue>-48112.000000</TThue></LTSuat></THTTLTSuat>"
       "<TgTCThue>0.000000</TgTCThue><TgTThue>-48112.000000</TgTThue><TgTTTBSo>-48112.000000</TgTTTBSo></TToan></NDHDon></DLHDon></HDon>").encode()
rows = server._parse_xml_invoice(XML)
assert len(rows) == 1 and rows[0]["thtien"] == 0 and rows[0]["tsuat"] == "8%" and rows[0]["tien_thue"] == -48112 and "từ 10% thành 8%" in rows[0]["ten_hang"], rows
assert server._parse_invoice_summary(XML)["theo_ts"] == {"8": {"ds": 0, "thue": -48112, "ds_nt": 0}}
det = {"khhdon": "C26TVN", "shdon": 279, "tgtcthue": 0, "tgtthue": -48112, "tgtttbso": -48112,
       "hdhhdvu": [{"tchat": 4, "ten": "Điều chỉnh thuế GTGT từ 10% thành 8%", "thtien": None, "tsuat": None}], "thttltsuat": [{"tsuat": "8%", "thtien": 0, "tthue": -48112}]}
jr = server._parse_detail_json(det)
assert len(jr) == 1 and jr[0]["thtien"] == 0 and jr[0]["tien_thue"] == -48112 and jr[0]["tsuat"] == "8%"
assert server._summary_from_detail_json(det)["theo_ts"] == {"8": {"ds": 0, "thue": -48112, "ds_nt": 0}}
# hóa đơn thường có dòng diễn giải + dòng hàng thật: KHÔNG thêm dòng tổng hợp
XML2 = XML.replace(b"<DSHHDVu>", b"<DSHHDVu><HHDVu><TChat>1</TChat><THHDVu>Gach</THHDVu><ThTien>1000</ThTien><TSuat>8%</TSuat></HHDVu>")
r2 = server._parse_xml_invoice(XML2)
assert [r["ten_hang"] for r in r2] == ["Gach", "Điều chỉnh thuế GTGT hóa đơn số 0000267 từ 10% thành 8%"] and not any(r.get("_tu_tong_hop") for r in r2)
# BK Mua vào (dự phòng không có Chi tiết): có thuế mà Tổng chưa thuế = 0 thì KHÔNG lấy Tổng thanh toán làm doanh số
src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py"), encoding="utf-8").read()
assert "if not ds and not thue:          # (có tiền thuế mà Tổng chưa thuế = 0" in src
print("PASS")
