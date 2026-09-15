import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Regression test cho GDTClient (server.py) — người dùng gửi ảnh chụp lỗi
# thật "Đăng nhập lỗi: Đăng nhập thất bại (403): Hệ thống phát hiện hành vi
# không hợp lệ. Yêu cầu đã bị chặn." VẪN gặp lại sau khi đã sửa việc nghỉ
# giữa các lần thử lại — thêm 1 lớp phòng thủ nữa: trình duyệt thật gọi API
# đăng nhập của hoadondientu.gdt.gov.vn LUÔN kèm sẵn header Origin/Referer/
# Accept-Language (vì đây là XHR gọi ra TỪ chính trang đó) — thiếu các
# header này là dấu hiệu dễ nhận ra của request KHÔNG xuất phát từ trình
# duyệt thật, WAF F5 BIG-IP ASM (đã xác nhận đứng trước hoadondientu.gdt.gov.vn,
# xem comment GDTClient.__init__) thường dùng làm 1 tiêu chí chấm điểm "hành
# vi không hợp lệ".

c = server.GDTClient()
headers = dict(c.session.headers)

assert headers.get("Origin") == "https://hoadondientu.gdt.gov.vn", (
    f"Phải có header Origin đúng domain (trình duyệt thật LUÔN gửi kèm cho XHR cùng-origin) — got "
    f"{headers.get('Origin')}")
assert headers.get("Referer") == "https://hoadondientu.gdt.gov.vn/", (
    f"Phải có header Referer đúng domain — got {headers.get('Referer')}")
assert "vi" in (headers.get("Accept-Language") or ""), (
    f"Phải có header Accept-Language hợp lý (trang tiếng Việt) — got {headers.get('Accept-Language')}")
print("PASS 1: GDTClient (đường KHÔNG impersonate, dùng requests.Session thường) có đủ header "
      "Origin/Referer/Accept-Language giống trình duyệt thật.")

assert headers.get("User-Agent"), "Đường KHÔNG impersonate vẫn phải có User-Agent như cũ"
print("PASS 2: đường KHÔNG impersonate vẫn giữ nguyên User-Agent cố định như trước (không hồi quy).")

print("\nALL DONE")
