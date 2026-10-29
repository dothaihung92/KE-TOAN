import os, sys, inspect
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Tra cứu HÀNG LOẠT dùng đúng lõi tra cứu 1 công ty (_run_fetch_job -> query_invoices -> _fetch_paginated) nên được luôn bản sửa
# "mã captcha hết lượt -> xin mã ngay"; màn hàng loạt hiện thêm dòng TIẾN ĐỘ chung của từng loại cho mỗi công ty đang chạy.
assert "_run_fetch_job(cid, body)" in inspect.getsource(server._run_batch)
src = inspect.getsource(server._run_fetch_job)
assert ': [TIẾN ĐỘ chung] ' in src and 'job.setdefault("tien_do", {})[loai_td] = noi_dung_td' in src

server.BATCH_JOBS[99] = {"running": True, "total": 2, "done": 0, "current_list": [7], "order": [7],
                         "items": {7: {"cid": 7, "ten": "CTY A", "status": "running"}}}
server.FETCH_JOBS[7] = {"messages": [], "last": {"text": "bán ra (máy tính tiền): [ĐOẠN 11/07/2026→20/07/2026] đang tải..."},
                        "tien_do": {"mua vào (máy tính tiền)": "xong 3/10 đoạn 10 ngày — đã lấy 12 hóa đơn",
                                    "bán ra (máy tính tiền)": "✓ xong 10/10 đoạn 10 ngày — đã lấy 40 hóa đơn"}}
st = server.fetch_batch_status(99)
td = st["current_list"][0]["tien_do"]
assert {"loai": "mua vào (máy tính tiền)", "text": "xong 3/10 đoạn 10 ngày — đã lấy 12 hóa đơn"} in td and len(td) == 2, td
html = open(os.path.join(_REPO_ROOT, "static", "index.html"), encoding="utf-8").read()
assert "(c.tien_do||[]).map(t=>" in html
print("PASS: tra cứu hàng loạt dùng chung cách tra cứu mới + hiện dòng tiến độ chung từng loại cho mỗi công ty đang chạy.")
