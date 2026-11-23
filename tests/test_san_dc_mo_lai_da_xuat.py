# Đơn đã xuất file điều chỉnh nhưng chưa phát hành (import MISA lỗi) phải có cách MỞ LẠI để xuất lại; đơn đã có hoá đơn điều chỉnh trên trang Thuế thì không.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import san_tmdt as m
def don(ma, tra, da, can=None, **kw):
    d = {"san": "shopee", "dong": [{"ten": "Hàng A", "sl": 2, "thanh": 200000, "ts": 5}], "tra": [tra], "da_dc": [da], "so_hd": "000" + ma, "ky_hieu": "C26MYY", "ngay_hd": "07/11/2026", "can_dc": can}
    d.update(kw); return d
so = {"don": {
    "A": don("1", 2, 0, {"ngay": "17/11/2026 10:00", "toan_bo": True, "ly_do": "x", "sl": 2}),          # đang cần điều chỉnh (khung đỏ)
    "B": don("2", 2, 2),                                                                                    # đã xuất file, chưa thấy trên trang Thuế -> mở lại được
    "C": don("3", 1, 1, dc_so_hd="C26TAA-77"),                                                              # trang Thuế ĐÃ có hoá đơn điều chỉnh -> không mở
    "D": don("4", 0, 0)}, "lo": []}                                                                         # không trả hàng
ds = m.ds_da_xuat_dc_chua_phat_hanh(so)
assert [x["ma_don"] for x in ds] == ["B"], ds
assert [x["ma_don"] for x in m.ds_can_dieu_chinh(so)] == ["A"]
# xuất lần 1 đánh dấu thời điểm xuất
so["don"]["A"]["da_dc"] = [0]
rows, td, xong, thieu, ghi = m.sang_dieu_chinh(so, ["A"], "shopee", "23/11/2026")
assert xong == ["A"] and ghi
m.danh_dau_da_dieu_chinh(so, ghi)
assert so["don"]["A"]["can_dc"] is None and so["don"]["A"]["dc_xuat_luc"] and [x["ma_don"] for x in m.ds_da_xuat_dc_chua_phat_hanh(so)] == ["A", "B"] or {x["ma_don"] for x in m.ds_da_xuat_dc_chua_phat_hanh(so)} == {"A", "B"}
assert m.ds_can_dieu_chinh(so) == []                      # xuất xong thì khung đỏ hết (không xuất trùng)
# mở lại: chỉ đơn hợp lệ (C đã có HĐ điều chỉnh, D không trả hàng bị từ chối)
mo = m.mo_lai_dieu_chinh(so, ["A", "C", "D", "KHONGCO"])
assert mo == ["A"], mo
assert so["don"]["A"]["da_dc"] == [0] and so["don"]["A"]["can_dc"]["toan_bo"] is True and so["don"]["C"]["da_dc"] == [1]
assert [x["ma_don"] for x in m.ds_can_dieu_chinh(so)] == ["A"]    # lần xuất sau lập lại hoá đơn
rows2, *_ = m.sang_dieu_chinh(so, ["A"], "shopee", "23/11/2026")
assert rows2 and rows2[0][13] == "0001" or rows2[0][13] == "0001".zfill(4) or rows2
assert so["lo"][-1]["loai"] == "mo_dc"
# căn cứ trả/huỷ hiện rõ nguồn (file sàn ghi gì) để người dùng đối chiếu; có thể BỎ QUA đơn không thực sự trả/huỷ
so2 = {"don": {"S1": {"san": "shopee", "dong": [{"ten": "Kính A", "sku": "a", "sl": 2, "thanh": 200000, "ts": 5}], "tra": [0], "da_dc": [0], "so_hd": "0001", "ky_hieu": "C26MYY", "ngay_hd": "07/11/2026", "can_dc": None},
                  "H1": {"san": "shopee", "dong": [{"ten": "Kính B", "sku": "b", "sl": 1, "thanh": 100000, "ts": 5}], "tra": [0], "da_dc": [0], "so_hd": "0002", "ky_hieu": "C26MYY", "ngay_hd": "07/11/2026", "can_dc": None}}, "lo": []}
dong = [{"ma_don": "S1", "ten_hang": "Kính A", "sku": "a", "so_luong": 2, "sl_tra": 2, "tra_hang": "Đã Chấp Thuận Yêu Cầu", "trang_thai": "Hoàn thành"},
        {"ma_don": "H1", "ten_hang": "Kính B", "sku": "b", "so_luong": 1, "sl_tra": 0, "tra_hang": "", "trang_thai": "Đã hủy"}]
moi = m.cap_nhat_tra_hang(so2, dong)
assert set(moi) == {"S1", "H1"}, moi
dc = {x["ma_don"]: x for x in m.ds_can_dieu_chinh(so2)}
assert "CHẤP THUẬN trả hàng/hoàn tiền" in dc["S1"]["nguon"] and "Đã Chấp Thuận Yêu Cầu" in dc["S1"]["nguon"] and "SL hoàn trả 2/2" in dc["S1"]["nguon"], dc["S1"]["nguon"]
assert dc["H1"]["nguon"].startswith("Đơn bị HUỶ") and "Đã hủy" in dc["H1"]["nguon"], dc["H1"]["nguon"]
assert m.bo_qua_dieu_chinh(so2, ["S1", "KHONGCO"]) == ["S1"]
assert [x["ma_don"] for x in m.ds_can_dieu_chinh(so2)] == ["H1"] and "S1" not in {x["ma_don"] for x in m.ds_da_xuat_dc_chua_phat_hanh(so2)}
m.cap_nhat_tra_hang(so2, dong)                                   # cập nhật file lần sau: đơn đã bỏ qua KHÔNG bị báo lại
assert [x["ma_don"] for x in m.ds_can_dieu_chinh(so2)] == ["H1"]
# nối dây
sv = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py"), encoding="utf8").read()
ix = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "index.html"), encoding="utf8").read()
assert '"/api/san-tmdt/{cid}/dc-mo-lai"' in sv and '"da_xuat_dc"' in sv and "xhdMoLaiDc" in ix and "da_xuat_dc" in ix and 'dc-bo-qua' in sv and 'xhdBoQuaDc' in ix
print("PASS: đơn đã xuất file điều chỉnh nhưng chưa phát hành được mở lại để xuất lại; đơn đã có hoá đơn điều chỉnh trên trang Thuế không mở")
