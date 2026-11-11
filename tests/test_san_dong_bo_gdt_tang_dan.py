import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Đồng bộ hoá đơn đầu ra (Hỗ trợ xuất hoá đơn sàn TMĐT) TĂNG DẦN: hoá đơn đã lấy về không đổi (hoá đơn điều chỉnh âm là hoá đơn MỚI có ngày lập mới),
# nên lần sau chỉ tra cứu từ ngày đã đồng bộ tới (lùi 2 ngày) — trước đây mỗi lần bấm đều dò lại cả khoảng 29/10 -> hôm nay, rất lâu.
server.DATA_DIR = tempfile.mkdtemp()
K = server._san_gdt_khoang_moi
assert K(1, "29/10/2026", "11/11/2026") == ("29/10/2026", False), "Chưa đồng bộ lần nào -> tra cả khoảng"
server._san_gdt_luc_luu(1, 100.0, "29/10/2026", "10/11/2026")
assert server._san_gdt_doc(1) == {"luc": 100.0, "tu": "29/10/2026", "den": "10/11/2026"}
assert server._san_gdt_luc(1) == 100.0
assert K(1, "29/10/2026", "11/11/2026") == ("08/11/2026", True), "Đã có 29/10–10/11 -> chỉ tra 08/11–11/11"
assert K(1, "01/11/2026", "11/11/2026") == ("08/11/2026", True)
assert K(1, "29/10/2026", "11/11/2026", tu_dau=True) == ("29/10/2026", False), "Đồng bộ lại từ đầu"
assert K(1, "20/10/2026", "11/11/2026") == ("20/10/2026", False), "Khoảng yêu cầu bắt đầu trước khoảng đã có -> tra đủ"
assert K(1, "29/10/2026", "09/11/2026") == ("29/10/2026", False) or K(1, "29/10/2026", "09/11/2026")[0] <= "09/11/2026"
server._san_gdt_luc_luu(1, 200.0, "08/11/2026", "11/11/2026")                  # lần đồng bộ ngắn nối tiếp -> khoảng đã có mở rộng
assert server._san_gdt_doc(1) == {"luc": 200.0, "tu": "29/10/2026", "den": "11/11/2026"}
server._san_gdt_luc_luu(1, 300.0, "01/12/2026", "05/12/2026")                  # không liền nhau -> thay khoảng mới
assert server._san_gdt_doc(1)["tu"] == "01/12/2026"
print("PASS: đồng bộ hoá đơn đầu ra chỉ tra cứu phần MỚI từ ngày đã đồng bộ (lùi 2 ngày), có tuỳ chọn đồng bộ lại từ đầu.")
print("\nALL DONE")

# Lưu kết quả tra cứu khoảng MỚI không được xoá hoá đơn của các ngày đã đồng bộ trước đó
import sqlite3
c = sqlite3.connect(":memory:")
c.execute("CREATE TABLE invoices (company_id INTEGER, loai TEXT, he_thong TEXT, shdon TEXT, tdlap TEXT)")
for sh, ng in (("1", "2026-10-30T09:00:00"), ("2", "2026-11-07T10:00:00"), ("3", "2026-11-09T08:00:00"), ("4", "2026-11-11T08:00:00")):
    c.execute("INSERT INTO invoices VALUES (1,'sold','query',?,?)", (sh, ng))
server._xoa_hd_cu(c, 1, "sold", "query", {"chi_xoa_trong_khoang": True, "tu_ngay": "08/11/2026", "den_ngay": "11/11/2026"})
assert sorted(r[0] for r in c.execute("SELECT shdon FROM invoices")) == ["1", "2"], "chỉ xoá trong khoảng vừa tra cứu"
server._xoa_hd_cu(c, 1, "sold", "query", {"tu_ngay": "08/11/2026", "den_ngay": "11/11/2026"})
assert not list(c.execute("SELECT * FROM invoices")), "không có cờ -> xoá như cũ (màn Tra cứu hoá đơn)"
print("PASS 2: lưu kết quả đồng bộ tăng dần chỉ xoá hoá đơn trong khoảng vừa tra cứu, giữ hoá đơn cũ.")
