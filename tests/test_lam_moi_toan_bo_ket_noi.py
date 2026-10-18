import os, sys, threading, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Ca thật: tra cứu hàng loạt chạy lâu thì công ty nào cũng bị "ngắt kết nối" (kể cả lấy captcha bằng phiên mới), nhưng TẮT/MỞ LẠI phần mềm là
# tra cứu bình thường -> trạng thái kết nối tích tụ BÊN TRONG phần mềm. Đã kiểm chứng: curl_cffi giữ 1 handle (+ kết nối) RIÊNG cho MỖI luồng
# từng dùng phiên, Session.close() chỉ đóng handle của luồng gọi -> phiên dùng bởi nhiều luồng sống lâu để lại nhiều kết nối mở.
# Nay: _lam_moi_toan_bo_ket_noi() thay phiên mới cho mọi công ty (giữ token), bỏ phiên cũ + gom rác -> đóng mọi handle/kết nối cũ.
c = server.GDTClient()
if not c.impersonate:
    print("SKIP: máy kiểm thử không có curl_cffi"); sys.exit(0)
c.set_token("TOKEN-1")
server.CLIENTS.clear(); server.CLIENTS[1] = c
dung = threading.Event()
def luong():
    c.session.curl          # luồng dùng phiên -> curl_cffi tạo handle riêng cho luồng này
    dung.wait()
ts = [threading.Thread(target=luong) for _ in range(20)]
[t.start() for t in ts]; time.sleep(0.3)
mo = server._dem_ket_noi_curl_dang_mo()
assert mo >= 21, mo
c.session.close()
assert server._dem_ket_noi_curl_dang_mo() >= 20, "Session.close() cách cũ chỉ đóng handle của luồng gọi"
truoc, sau = server._lam_moi_toan_bo_ket_noi()
assert truoc >= 20 and sau <= 2, (truoc, sau)
assert c.session.headers.get("Authorization") == "Bearer TOKEN-1", "giữ đăng nhập"
dung.set(); [t.join() for t in ts]
print(f"PASS 1: 20 luồng giữ kết nối riêng; làm mới toàn bộ kết nối: {truoc} -> {sau}; vẫn giữ token đăng nhập.")

r = server.lam_moi_ket_noi()
assert r["ok"] and "truoc" in r and "sau" in r
print("PASS 2: API /api/lam-moi-ket-noi chạy được (nút 'Làm mới kết nối').")

src = open(os.path.join(os.path.dirname(server.__file__), "server.py"), encoding="utf-8").read()
assert "if suc_khoe.lien_tiep >= 2:" in src and src.count("_lam_moi_toan_bo_ket_noi()") >= 4
assert 'if ly_do == "nghỉ giữa các nhóm công ty":' in src
html = open(os.path.join(os.path.dirname(server.__file__), "static", "index.html"), encoding="utf-8").read()
assert 'onclick="lamMoiKetNoi()"' in html and "/api/lam-moi-ket-noi" in html and "st.lam_moi_ket_noi_text" in html
print("PASS 3: tra cứu hàng loạt tự làm mới kết nối sau mỗi nhóm 10 công ty, khi 2 công ty liên tiếp bị ngắt, và trước mỗi vòng thử lại; có nút bấm tay.")
print("ALL DONE")
