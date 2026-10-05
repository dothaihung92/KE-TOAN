import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Hóa đơn ĐIỀU CHỈNH GIẢM (TCHDon=2) ghi thuế suất "KHAC:8.00%" (vd C26TYY 1374: -127.400 đ, thuế -10.192 đ): phải vào nhóm 8% (BK Bán ra -> [32]/[33] +
# Phụ lục NQ142), KHÔNG được vào nhóm "Khác" rồi bị gộp vào KHÔNG CHỊU THUẾ [26] của tờ khai HTKK.
XML = ("<HDon><DLHDon><TTChung><KHMSHDon>1</KHMSHDon><KHHDon>C26TYY</KHHDon><SHDon>00001374</SHDon><NLap>2026-08-19</NLap><DVTTe>VND</DVTTe><TGia>1.00</TGia>"
       "<TTHDLQuan><TCHDon>2</TCHDon><SHDCLQuan>00001343</SHDCLQuan></TTHDLQuan></TTChung><NDHDon>"
       "<NBan><Ten>CÔNG TY TNHH BIOGREEN</Ten><MST>0315253276</MST><DChi>x</DChi></NBan><NMua><Ten>CÔNG TY TNHH HOD LTT</Ten><MST>0313639845</MST></NMua>"
       "<DSHHDVu><HHDVu><TChat>1</TChat><STT>1</STT><THHDVu>DĨA GIẤY TRẮNG</THHDVu><DVTinh>Cái</DVTinh><SLuong>-150</SLuong><DGia>849.3333</DGia>"
       "<ThTien>-127400.000000</ThTien><TSuat>KHAC:8.00%</TSuat><TTKhac><TTin><TTruong>VATAmount</TTruong><KDLieu>numeric</KDLieu><DLieu>-10192.0</DLieu></TTin></TTKhac></HHDVu></DSHHDVu>"
       "<TToan><THTTLTSuat><LTSuat><TSuat>KHAC:8.00%</TSuat><ThTien>-127400.000000</ThTien><TThue>-10192.000000</TThue></LTSuat></THTTLTSuat>"
       "<TgTCThue>-127400.000000</TgTCThue><TgTThue>-10192.000000</TgTThue><TgTTTBSo>-137592.000000</TgTTTBSo></TToan></NDHDon></DLHDon></HDon>").encode("utf-8")
info = server._parse_invoice_summary(XML)
assert info["theo_ts"] == {"8": {"ds": -127400, "thue": -10192, "ds_nt": -127400}}, info["theo_ts"]
# bản JSON của cổng thuế
det = {"khmshdon": "1", "khhdon": "C26TYY", "shdon": 1374, "dvtte": "VND", "tgia": 1,
       "hdhhdvu": [{"stt": 1, "ten": "DĨA GIẤY", "thtien": -127400, "tsuat": "KHAC:8.00%", "tthue": -10192}]}
js = server._summary_from_detail_json(det)
assert js["theo_ts"] == {"8": {"ds": -127400, "thue": -10192, "ds_nt": -127400}}, js["theo_ts"]
# dòng hàng của các trang khác (nhóm theo thuế suất)
assert server._nhom_hoa_don_theo_thue_suat([{"tsuat": "KHAC:8.00%", "thtien": -127400, "tien_thue": -10192}]) == {"8": {"ds": -127400, "thue": -10192}}
for v, kq in [("KHAC:8.00%", "8"), ("KHAC:8%", "8"), ("KHAC:5.26%", "5"), ("KHAC:10.00%", "10"), ("KHAC:0%", "0"), ("KHAC:3%", "KHAC"), ("KHAC:abc", "KHAC"),
              ("KHAC", "KCT"), ("KCT", "KCT"), ("KKKNT", "KCT"), ("KHTKKNT", "KCT"), ("8%", "8"), ("8", "8"), ("10.00%", "10"), ("5.0", "5"), ("", "KCT")]:
    assert server._chuan_hoa_thue_suat(v) == kq, (v, server._chuan_hoa_thue_suat(v), kq)
print("PASS")
src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py"), encoding="utf-8").read()
assert "nhóm '6. Khác / chưa lấy được file XML' trong kỳ" in src and 'khac_ban = dict(_tu_file_bk.get("KHAC") or {})' in src, "cảnh báo khi nhóm Khác bị gộp vào [26]"
print("PASS (cảnh báo nhóm Khác)")

# ---- JSON chi tiết của cổng thuế: dòng ghi ltsuat "KHAC" (không kèm số), tiền thuế dòng trống/0 -> trước đây xếp vào KCT với thuế 0 (BK Bán ra nhóm 1) ----
def dong(**k):
    d = {"stt": 1, "ten": "DĨA GIẤY TRẮNG", "dvtinh": "Cái", "sluong": -150, "dgia": 849.3333, "thtien": -127400, "tchat": 1}
    d.update(k); return d
def hd(*lines, **k):
    d = {"khmshdon": "1", "khhdon": "C26TYY", "shdon": 1374, "dvtte": "VND", "tgia": 1, "hdhhdvu": list(lines)}
    d.update(k); return d
OK = {"8": {"ds": -127400, "thue": -10192, "ds_nt": -127400}}
casos = {
    "A ltsuat KHAC + tsuat 8":           hd(dong(ltsuat="KHAC", tsuat=8)),
    "B ltsuat KHAC + tsuat 0.08":        hd(dong(ltsuat="KHAC", tsuat=0.08)),
    "C ltsuat KHAC:8.00%":               hd(dong(ltsuat="KHAC:8.00%")),
    "D KHAC + tthue -10192 (suy ra %)":  hd(dong(ltsuat="KHAC", tthue=-10192)),
    "E KHAC + VATAmount trong ttkhac":   hd(dong(ltsuat="KHAC", ttkhac=[{"ttruong": "VATAmount", "kdlieu": "numeric", "dlieu": "-10192.0"}]), tgtthue=-10192, tgtcthue=-127400),
    "F KHAC + chỉ có tổng hóa đơn":      hd(dong(ltsuat="KHAC"), tgtthue=-10192, tgtcthue=-127400),
    "G KHAC + khối thttltsuat":          hd(dong(ltsuat="KHAC"), thttltsuat=[{"tsuat": "KHAC:8.00%", "thtien": -127400, "tthue": -10192}]),
    "H KHAC + tsuat 0 mặc định + tổng":  hd(dong(ltsuat="KHAC", tsuat=0), tgtthue=-10192, tgtcthue=-127400),
}
for ten, det in casos.items():
    sm = server._summary_from_detail_json(det)
    assert sm["theo_ts"] == OK and not sm.get("ts_chua_ro"), (ten, sm["theo_ts"])
    rows = server._parse_detail_json(det)
    assert rows[0]["tsuat"] == "8%" and float(rows[0]["tien_thue"]) == -10192, (ten, rows[0]["tsuat"], rows[0]["tien_thue"])
# không có bất kỳ dữ liệu nào để biết mấy %: xếp nhóm Khác + đánh dấu để dùng file XML gốc / cảnh báo
sm = server._summary_from_detail_json(hd(dong(ltsuat="KHAC")))
assert list(sm["theo_ts"]) == ["KHAC"] and sm["ts_chua_ro"] is True, "không giải được: nhóm Khác (có cảnh báo), không âm thầm vào KCT"
# dòng bình thường không bị đổi: 10% có tthue = 0 vẫn giữ 0 (không tự tính lại), KCT vẫn KCT, 8% thường
sm = server._summary_from_detail_json(hd(dong(ltsuat="10%", tthue=0, thtien=1000, sluong=1)))
assert sm["theo_ts"]["10"]["thue"] == 0
sm = server._summary_from_detail_json(hd(dong(ltsuat="KCT", thtien=1000, sluong=1)))
assert list(sm["theo_ts"]) == ["KCT"] and not sm.get("ts_chua_ro")
sm = server._summary_from_detail_json(hd(dong(ltsuat="8%", tthue=80, thtien=1000, sluong=1)))
assert sm["theo_ts"] == {"8": {"ds": 1000, "thue": 80, "ds_nt": 1000}}
print("PASS (JSON cổng thuế KHAC)")
