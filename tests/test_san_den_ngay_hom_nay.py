import os, sys, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server
# "Đến ngày" luôn tự = hôm nay: ô còn là hôm qua (mở app qua đêm) không được làm lần xuất đầu bỏ sót đơn của hôm nay.
hn = datetime.date.today()
hq = (hn - datetime.timedelta(days=1)).isoformat()
assert server._san_den_ngay_moi(hq) == hn.isoformat()
assert server._san_den_ngay_moi((hn - datetime.timedelta(days=1)).strftime("%d/%m/%Y")) == hn.isoformat()
assert server._san_den_ngay_moi("") == hn.isoformat()
assert server._san_den_ngay_moi(hn.isoformat()) == hn.isoformat()
tuong_lai = (hn + datetime.timedelta(days=2)).isoformat()
assert server._san_den_ngay_moi(tuong_lai) == tuong_lai
# đơn của hôm nay nằm trong khoảng lọc khi dùng ngày đến đã làm mới
import san_tmdt as m
dong = [{"ma_don": "A", "ngay": hn.strftime("%d/%m/%Y"), "trang_thai": "Hoàn thành"}, {"ma_don": "B", "ngay": (hn - datetime.timedelta(days=3)).strftime("%d/%m/%Y"), "trang_thai": "Hoàn thành"}]
tu = (hn - datetime.timedelta(days=10)).isoformat()
cu = m.loc_don(dong, False, tu, hq)
moi = m.loc_don(dong, False, tu, server._san_den_ngay_moi(hq))
assert {x["ma_don"] for x in cu} == {"B"} and {x["ma_don"] for x in moi} == {"A", "B"}, (cu, moi)
print("PASS: 'đến ngày' tự = hôm nay (ô còn là hôm qua vẫn lấy đơn hôm nay ngay ở lần xuất đầu)")
