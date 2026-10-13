import os
import sqlite3
import sys
import threading
import time

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import server

# Tra cứu hàng loạt: THÊM công ty vào đợt đang chạy (cùng khoảng ngày/tuỳ chọn); công ty đã có trong đợt thì bỏ qua;
# đợt đã xong -> mở đợt MỚI chỉ gồm công ty thêm.


def _db():
    c = sqlite3.connect(":memory:", check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("CREATE TABLE companies (id INTEGER PRIMARY KEY, ten TEXT, mst TEXT)")
    for i in range(1, 7):
        c.execute("INSERT INTO companies VALUES (?,?,?)", (i, f"Cty {i}", f"03000000{i}"))
    c.commit()
    return c


kho = _db()


class _Conn:
    def execute(self, *a):
        return kho.execute(*a)

    def commit(self):
        pass

    def close(self):
        pass


chay = []
nha = threading.Event()


def _gia_fetch(cid, b):
    chay.append((cid, b.get("tu_ngay")))
    if cid == 1:
        nha.wait(5)              # giữ đợt đang chạy
    time.sleep(0.05)


class _Cl:
    token = "x"


goc = (server._run_fetch_job, server.get_client, server._batch_luu_db, server._xoa_loi_tra_cuu, server.db, server._luu_loi_tra_cuu)
server._run_fetch_job = _gia_fetch
server.get_client = lambda cid: _Cl()
server._batch_luu_db = lambda *a, **k: None
server._xoa_loi_tra_cuu = lambda *a, **k: None
server._luu_loi_tra_cuu = lambda *a, **k: None
server.db = lambda: _Conn()
try:
    body = {"cids": [1, 2], "tu_ngay": "01/07/2026", "den_ngay": "30/09/2026", "so_luong": 2}
    kq = server._khoi_dong_batch([1, 2], {1: "Cty 1", 2: "Cty 2", 3: "Cty 3", 4: "Cty 4"}, dict(body, batch=True))
    bid = kq["batch_id"]
    time.sleep(0.4)
    assert server.BATCH_JOBS[bid]["running"] and bid in server.BATCH_HANG_DOI
    # thêm cty 3, 4 + cty 2 (đã có) khi đang chạy
    r = server.fetch_batch_them(bid, {"cids": [2, 3, 4]})
    assert r["da_them"] == 2 and r["bo_qua"] == 1 and not r["doi_moi"] and r["batch_id"] == bid, r
    b = server.BATCH_JOBS[bid]
    assert b["total"] == 4 and b["order"] == [1, 2, 3, 4] and set(b["items"]) == {1, 2, 3, 4}
    # tất cả cty đã có trong đợt -> không thêm
    assert server.fetch_batch_them(bid, {"cids": [1, 3]})["da_them"] == 0
    nha.set()
    for _ in range(100):
        if not b["running"]:
            break
        time.sleep(0.1)
    assert not b["running"] and b["done"] == 4, (b["running"], b["done"])
    assert sorted(c for c, _ in chay) == [1, 2, 3, 4] and all(t == "01/07/2026" for _, t in chay), chay
    print("PASS 1: thêm cty 3,4 vào đợt đang chạy; cty 2 đã có nên bỏ qua; cả 4 cty chạy đúng khoảng ngày.")
    # đợt đã kết thúc -> mở đợt mới chỉ gồm cty thêm
    chay.clear()
    r2 = server.fetch_batch_them(bid, {"cids": [5, 6]}) if False else None
    server.BATCH_BODY[bid] = dict(body, batch=True)
    conn_them = server.fetch_batch_them(bid, {"cids": [3, 5]})
    assert conn_them["doi_moi"] and conn_them["batch_id"] != bid and conn_them["da_them"] == 1 and conn_them["bo_qua"] == 1, conn_them
    for _ in range(100):
        if not server.BATCH_JOBS[conn_them["batch_id"]]["running"]:
            break
        time.sleep(0.1)
    assert [c for c, _ in chay] == [5], chay
    print("PASS 2: đợt đã xong -> mở đợt mới chỉ cho cty thêm (cty đã có trong đợt cũ bỏ qua).")
finally:
    (server._run_fetch_job, server.get_client, server._batch_luu_db, server._xoa_loi_tra_cuu, server.db, server._luu_loi_tra_cuu) = goc

h = open(os.path.join(_REPO_ROOT, "static", "index.html"), encoding="utf-8").read()
assert 'id="batchThemBtn"' in h and "function batchThemCongTy" in h and "/api/fetch-batch-them/" in h
print("PASS 3: giao diện có nút thêm công ty vào đợt đang chạy.")
assert "const nhom=(tieuDe,dongs,ghiChu)=>" in h and 'list-style:disc' in h and "dsVat.map(i=>`<b>${i.ten}</b>" in h
print("PASS 4: tổng kết hàng loạt hiện từng nhóm 1 tiêu đề + mỗi công ty 1 dòng có chấm.")

print("\nALL DONE")
