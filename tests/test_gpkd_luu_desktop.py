import os, sys, tempfile, zipfile, io
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Soạn hồ sơ GPKD xong: file zip được lưu ra DESKTOP (không tải vào Downloads của trình duyệt); không ghi đè bản cũ; Desktop không dùng được thì để trình duyệt tải như cũ.
DU = {"loai": ["ten"], "dn": {"ten": "CÔNG TY TNHH GIẢ", "ma_so": "0300000001", "loai_hinh": "Công ty TNHH một thành viên", "co_quan": "Phòng ĐKKD", "ngay_lap": "01/01/2026"},
      "ten": {"viet": "CÔNG TY TNHH MỚI"}, "hien_tai": {}}
d = tempfile.mkdtemp()
server._get_desktop_dir = lambda: d
r = server.gpkd_soan_tao({"du_lieu": DU})
assert r.headers.get("X-Saved-Desktop") == "1"
f1 = [x for x in os.listdir(d) if x.endswith(".zip")]
assert len(f1) == 1 and zipfile.ZipFile(os.path.join(d, f1[0])).namelist() == zipfile.ZipFile(io.BytesIO(r.body)).namelist()
r = server.gpkd_soan_tao({"du_lieu": DU})
f2 = sorted(x for x in os.listdir(d) if x.endswith(".zip"))
assert len(f2) == 2 and any("(2)" in x for x in f2), f2                       # bản mới không ghi đè bản cũ
server._get_desktop_dir = lambda: os.path.join(d, "khong_co")
r = server.gpkd_soan_tao({"du_lieu": DU})
assert not r.headers.get("X-Saved-Desktop") and r.body                         # không có Desktop -> trình duyệt tải như cũ
print("PASS: hồ sơ GPKD lưu ra Desktop, không ghi đè, có phương án dự phòng.")
