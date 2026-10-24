import os, sys
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Ca thật: HĐ C26TUN 6357 (UNIVERSE GLOBAL LOGISTICS) — file hóa đơn: tổng chưa thuế 5.610.241, TỔNG THUẾ 448.820 (8%).
# Thuế từng dòng (TTKhac TongTien_Thue người bán ghi) dòng "Phí xếp hàng vào kho" = 271.347 (đúng 127.347) -> Chi tiết/BK Mua vào ra 592.820.
# Danh sách tra cứu trả tổng thuế 0 nên bản .287 (so với tổng danh sách) không sửa được. Nay lấy tổng thuế TỪ FILE XML.
DONG = [("Phí đại lý", 529200, 42336), ("Phí dịch vụ giao nhận TK 108500567010", 1800000, 144000), ("Phí cân bằng cont", 298469, 23878),
        ("Phí chứng từ", 793800, 63504), ("Phí dịch vụ xếp dỡ tại cảng", 596938, 47755), ("Phí xếp hàng vào kho", 1591834, 271347)]
hh = "".join(f"<HHDVu><TChat>1</TChat><STT>{i}</STT><THHDVu>{t}</THHDVu><SLuong>1</SLuong><DGia>{tt}</DGia><ThTien>{tt}</ThTien><TSuat>8%</TSuat>"
             f"<TTKhac><TTin><TTruong>TongTien_Thue</TTruong><KDLieu>numeric</KDLieu><DLieu>{th}</DLieu></TTin></TTKhac></HHDVu>"
             for i, (t, tt, th) in enumerate(DONG, 1))
xml = (f"<HDon><DLHDon><TTChung><KHMSHDon>1</KHMSHDon><KHHDon>C26TUN</KHHDon><SHDon>6357</SHDon><NLap>2026-08-10</NLap></TTChung><NDHDon>"
       f"<NBan><Ten>UNIVERSE</Ten><MST>0318581564</MST></NBan><NMua><Ten>MAY LAM MAT KINH</Ten><MST>0313335734</MST></NMua><DSHHDVu>{hh}</DSHHDVu>"
       f"<TToan><THTTLTSuat><LTSuat><TSuat>8%</TSuat><ThTien>5610241</ThTien><TThue>448820</TThue></LTSuat></THTTLTSuat>"
       f"<TgTCThue>5610241</TgTCThue><TgTThue>448820</TgTThue><TgTTTBSo>6059061</TgTTTBSo></TToan></NDHDon></DLHDon></HDon>").encode("utf-8")
items = server._parse_xml_invoice(xml)
assert sum(server._to_num(x["tien_thue"]) for x in items) == 592820, "dữ liệu dòng người bán ghi đúng như ca thật"
assert server._tong_thue_hd_tu_file(items, 0) == 448820 and server._tong_thue_hd_tu_file(items, None) == 448820
dl = [{"ds": server._to_num(x["thtien"]), "ts_hien": x["tsuat"], "tien_thue": round(server._to_num(x["tien_thue"])), "phan_bo": False, "it": x} for x in items]
assert server._khop_thue_dong_voi_tong_hd(dl, server._tong_thue_hd_tu_file(items, 0))
assert sum(d["tien_thue"] for d in dl) == 448820 and dl[5]["tien_thue"] == 127347, [d["tien_thue"] for d in dl]
print("PASS 1: HĐ 6357 — tổng thuế lấy từ XML 448.820 (danh sách tra cứu = 0) -> dòng xếp hàng 127.347, Chi tiết/BK Mua vào = 448.820.")

assert server._tong_thue_hd_tu_file([{"tgtthue": 0}], 357467) == 357467, "file ghi 0 mà danh sách có số -> dùng danh sách"
assert server._tong_thue_hd_tu_file([{"tgtthue": ""}], 1000) == 1000 and server._tong_thue_hd_tu_file([], 5) == 5
assert server._tong_thue_hd_tu_file([{"tgtthue": 0}], 0) == 0
print("PASS 2: không có tổng trong file -> dùng tổng danh sách tra cứu.")

src = open(os.path.join(_REPO_ROOT, "server.py"), encoding="utf-8").read()
assert '_khop_thue_dong_voi_tong_hd(dong_list, _tong_thue_hd_tu_file(items, r["tgtthue"]))' in src
print("PASS 3: xuất Bảng kê (Chi tiết MUA VÀO -> BK Mua vào) dùng tổng thuế theo file hóa đơn.")
print("ALL DONE")
