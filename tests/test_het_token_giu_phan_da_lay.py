import os, sys, datetime
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Hết token giữa chừng: GIỮ các đoạn 10 ngày đã xong, chỉ dò tiếp các đoạn còn lại sau khi đăng nhập lại (không làm lại từ đầu).
c = server.GDTClient.__new__(server.GDTClient)
c._toan_ky_rong = lambda *a, **k: False
het = {"da": False}
goi = []
def fake(tu, den, loai, page_size, he_thong, progress=None, ttxly_can_do=None, cancel_check=None):
    goi.append(tu)
    if tu == "21/01/2026" and not het["da"]:
        raise Exception("TOKEN_EXPIRED")
    return ([{"khmshdon": "1", "khhdon": "K", "shdon": tu, "nbmst": "1"}], 1, [], [])
c._query_one_range_on_dinh = fake
try:
    c.query_invoices("01/01/2026", "28/02/2026", loai="sold", he_thong="sco-query"); assert False
except Exception as e:
    assert "TOKEN_EXPIRED" in str(e)
    res, tot, loi, doan = e.partial
assert [x["shdon"] for x in res] == ["01/01/2026", "11/01/2026"] and tot == 2, (res, tot)
assert [d["tu"] for d in doan] == ["21/01/2026", "31/01/2026", "10/02/2026", "20/02/2026"] or sorted(d["tu"] for d in doan) == sorted(["21/01/2026", "31/01/2026", "10/02/2026", "20/02/2026"]), doan
assert not any(t in goi for t in ()) and len(goi) == 3, goi        # dừng ngay sau đoạn lỗi, không chạy tiếp các đoạn sau
# đăng nhập lại xong: dò ĐÚNG các đoạn còn lại
het["da"] = True; goi.clear()
res2, tot2, loi2, doan2 = c.query_invoices("01/01/2026", "28/02/2026", loai="sold", he_thong="sco-query", chi_cac_doan=doan)
assert sorted(goi) == sorted(d["tu"] for d in doan) and len(res2) == 4 and not doan2, (goi, res2)
print("PASS: hết token giữa chừng -> giữ 2 đoạn đã lấy, trả đúng 4 đoạn còn lại để dò tiếp (không làm lại từ đầu).")
