import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Ca thật: HĐ C26TKV số 109275 (CÔNG TY CỔ PHẦN KHO VẬN TÂN CẢNG) — dòng hàng TSuat 8%, ThTien 121.500 nhưng TTKhac VATAmount = 0; tổng hợp THTTLTSuat
# ghi TThue 9.720. Bảng kê (đọc chi tiết qua API) ghi tiền thuế 0. Đường đọc file XML đã bù đúng; nay đường đọc chi tiết qua API cũng bù theo tổng hợp.
XML = ("<HDon><DLHDon><TTChung><KHMSHDon>1</KHMSHDon><KHHDon>C26TKV</KHHDon><SHDon>109275</SHDon><NLap>2026-08-20</NLap></TTChung><NDHDon>"
       "<NBan><Ten>KHO VAN</Ten><MST>0309532497</MST></NBan><NMua><Ten>SEN HAI</Ten><MST>0318517985</MST></NMua><DSHHDVu><HHDVu><TChat>1</TChat><STT>1</STT>"
       "<THHDVu>Lưu kho</THHDVu><SLuong>9</SLuong><DGia>13500</DGia><TSuat>8%</TSuat><ThTien>121500</ThTien><TTKhac><TTin><TTruong>VATAmount</TTruong>"
       "<DLieu>0</DLieu></TTin></TTKhac></HHDVu></DSHHDVu><TToan><THTTLTSuat><LTSuat><TSuat>8%</TSuat><TThue>9720</TThue><ThTien>121500</ThTien></LTSuat>"
       "</THTTLTSuat><TgTCThue>121500</TgTCThue><TgTThue>9720</TgTThue><TgTTTBSo>131220</TgTTTBSo></TToan></NDHDon></DLHDon></HDon>").encode()
r = server._parse_xml_invoice(XML)
assert [(x["tsuat"], x["tien_thue"]) for x in r] == [("8%", 9720)], r
print("PASS 1: đọc file XML: tiền thuế dòng = 9.720 (bù theo tổng hợp thuế suất).")

DET = {"khmshdon": 1, "khhdon": "C26TKV", "shdon": 109275, "tdlap": "2026-08-20T00:00:00", "nbten": "KHO VAN", "nbmst": "0309532497",
       "nmten": "SEN HAI", "nmmst": "0318517985", "tgtcthue": 121500, "tgtthue": 9720, "tgtttbso": 131220,
       "hdhhdvu": [{"tchat": 1, "stt": 1, "ten": "Lưu kho", "sluong": 9, "dgia": 13500, "thtien": 121500, "ltsuat": "8%", "tsuat": 0.08,
                    "tthue": None, "ttkhac": [{"ttruong": "VATAmount", "dlieu": "0"}]}],
       "thttltsuat": [{"tsuat": "8%", "thtien": 121500, "tthue": 9720}]}
r2 = server._parse_detail_json(DET)
hh = [x for x in r2 if str(x.get("tchat")) in ("", "1")]
assert [(x["tsuat"], x["tien_thue"]) for x in hh] == [("8%", 9720)], r2
print("PASS 2: đọc chi tiết qua API: tiền thuế dòng = 9.720 (trước đây = 0).")

DET0 = dict(DET, tgtthue=0, thttltsuat=[{"tsuat": "8%", "thtien": 121500, "tthue": 0}])
assert all(not server._to_num(x["tien_thue"]) for x in server._parse_detail_json(DET0) if str(x.get("tchat")) in ("", "1"))
print("PASS 3: hóa đơn thật sự không có thuế (tổng hợp TThue = 0) -> giữ nguyên 0.")
print("ALL DONE")
