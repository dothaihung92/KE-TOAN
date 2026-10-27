import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, "server.py"), encoding="utf-8").read()
# Tra cứu HÀNG LOẠT đi qua đúng _run_fetch_job của tra cứu 1 công ty -> dùng chung cơ chế: máy tính tiền 1 luồng từng đoạn 10 ngày,
# hết token thì giữ phần đã lấy + đăng nhập lại + dò tiếp đúng đoạn còn lại.
rb = src[src.index("def _run_batch("):]
rb = rb[:rb.index("\ndef ", 10)]
assert "_run_fetch_job(cid, body)" in rb and "query_invoices" not in rb, "batch không có đường tra cứu riêng"
rf = src[src.index("def _run_fetch_job("):src.index("def _run_batch(")]
for k in ("e.partial", 'getattr(e, "partial"', "SO_DN_LAI_TOI_DA", "client.query_invoices("):
    assert k in rf or k.replace("e.partial", 'getattr(e, "partial"') in rf, k
assert "het_ev" in src and "_khoa_mtt_cua(self)" in src
print("PASS: tra cứu hàng loạt dùng chung _run_fetch_job -> cùng cơ chế giữ phần đã lấy khi hết token và máy tính tiền từng đoạn 1 luồng.")
