import os, sys, json, sqlite3
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

# Bước ĐỐI SOÁT BẢNG KÊ THÔ: sau khi lưu dữ liệu tra cứu, lấy LẠI chỉ danh sách từ hệ thống Thuế (phiên kết nối mới),
# đối chiếu với dữ liệu đã lưu; THIẾU -> bổ sung (và đưa vào danh sách để bước tải file tải luôn), LỆCH
# (trạng thái/số tiền) -> cập nhật theo Thuế; lặp tới khi khớp.
conn = sqlite3.connect(":memory:"); conn.row_factory = sqlite3.Row
conn.execute("""CREATE TABLE invoices (id INTEGER PRIMARY KEY, company_id, loai, he_thong, nbmst, nbten, nmmst, khmshdon,
    khhdon, shdon, tdlap, tgtcthue, tgtthue, tgtttbso, tthai, raw, detail_json,
    UNIQUE(company_id, nbmst, khmshdon, khhdon, shdon, loai, he_thong))""")


def hd(so, tien=1000, thue=80, tthai=1):
    return {"khmshdon": "1", "khhdon": "C26MCF", "shdon": so, "nbmst": "0318808536", "nbten": "A", "nmmst": "",
            "tdlap": "2026-09-10T00:00:00", "tgtcthue": tien, "tgtthue": thue, "tgtttbso": tien + thue, "tthai": tthai}


def luu(x):
    cth, th, tt = server._gia_tri_luu_hoa_don(x)
    conn.execute("INSERT INTO invoices (company_id, loai, he_thong, nbmst, nbten, nmmst, khmshdon, khhdon, shdon, tdlap, "
                 "tgtcthue, tgtthue, tgtttbso, tthai, raw) VALUES (7,'sold','sco-query',?,?,?,?,?,?,?,?,?,?,?,?)",
                 (x["nbmst"], x["nbten"], x["nmmst"], x["khmshdon"], x["khhdon"], str(x["shdon"]), x["tdlap"], cth, th, tt,
                  str(x["tthai"]), json.dumps(x)))


class FakeBan:
    class session:
        @staticmethod
        def close(): pass

    def __init__(self, tho): self.tho = tho
    def query_invoices(self, *a, **k): return list(self.tho), len(self.tho), [], []


class FakeClient:
    def __init__(self, vong): self.vong = vong; self.n = 0
    def _ban_sao_phien_moi(self):
        kq = self.vong[min(self.n, len(self.vong) - 1)]; self.n += 1
        return FakeBan(kq)


THO = [hd(n) for n in range(1, 11)]
for x in THO[:6]:
    luu(x)
conn.execute("UPDATE invoices SET tthai='1'"); conn.commit()
luu_thua = hd(2, tien=1000)                                  # đã lưu đúng; bên dưới đổi để tạo LỆCH
conn.execute("UPDATE invoices SET tgtcthue=555 WHERE shdon='3'")   # lệch tiền
conn.execute("UPDATE invoices SET tthai='2' WHERE shdon='4'")      # lệch trạng thái
conn.commit()
invs = [dict(x) for x in THO[:6]]

# 1) vòng 1: thiếu 7..10, lệch 3 & 4 -> bổ sung + sửa; vòng 2: khớp
fc = FakeClient([THO, THO])
tb = []
kq = server._doi_soat_bang_ke_tho(fc, conn, 7, "sold", "sco-query", "01/09/2026", "30/09/2026", invs, progress=tb.append)
assert kq["khop"] and kq["vong"] == 2, kq
assert sorted(kq["thieu"]) == [f"C26MCF {n}" for n in (10, 7, 8, 9)] or len(kq["thieu"]) == 4
assert len(kq["lech"]) == 2, kq
assert conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0] == 10
assert conn.execute("SELECT tgtcthue FROM invoices WHERE shdon='3'").fetchone()[0] == 1000
assert conn.execute("SELECT tthai FROM invoices WHERE shdon='4'").fetchone()[0] == "1"
assert sorted(int(x["shdon"]) for x in invs) == list(range(1, 11)), "HĐ bổ sung phải vào danh sách để tải file"
print("PASS 1: bảng kê thô có mà dữ liệu thiếu -> bổ sung (và vào danh sách tải file); lệch trạng thái/tiền -> sửa; vòng sau khớp.")

# 2) khớp ngay -> 1 vòng, không đổi gì
invs2 = [dict(x) for x in THO]
kq = server._doi_soat_bang_ke_tho(FakeClient([THO]), conn, 7, "sold", "sco-query", "01/09/2026", "30/09/2026", invs2)
assert kq["khop"] and kq["vong"] == 1 and not kq["thieu"] and not kq["lech"]
print("PASS 2: khớp hoàn toàn -> 1 vòng, không thay đổi dữ liệu.")

# 3) ngày lập trong DB đã được sửa theo XML (khác bảng kê thô) KHÔNG bị coi là lệch
conn.execute("UPDATE invoices SET tdlap='2026-10-01T00:00:00' WHERE shdon='5'"); conn.commit()
kq = server._doi_soat_bang_ke_tho(FakeClient([THO]), conn, 7, "sold", "sco-query", "01/09/2026", "30/09/2026", [dict(x) for x in THO])
assert kq["khop"] and not kq["lech"]
print("PASS 3: ngày lập đã sửa theo XML không bị coi là lệch (không so ngày).")

# 4) hóa đơn ngân hàng bị loại theo cấu hình; lỗi mạng khi lấy bảng kê -> không làm hỏng dữ liệu
kq = server._doi_soat_bang_ke_tho(FakeClient([THO + [hd(99)]]), conn, 7, "sold", "sco-query", "01/09/2026", "30/09/2026",
                                  [dict(x) for x in THO], la_ngan_hang=lambda x: x["shdon"] == 99)
assert kq["khop"] and not kq["thieu"] and conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0] == 10


class Hong:
    def _ban_sao_phien_moi(self):
        class B:
            class session:
                @staticmethod
                def close(): pass
            def query_invoices(s, *a, **k): raise RuntimeError("mat ket noi")
        return B()
kq = server._doi_soat_bang_ke_tho(Hong(), conn, 7, "sold", "sco-query", "01/09/2026", "30/09/2026", [])
assert not kq["khop"] and "mat ket noi" in kq["loi"] and conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0] == 10
print("PASS 4: lọc HĐ ngân hàng theo cấu hình; lỗi lấy bảng kê thô không làm hỏng dữ liệu.")

# 5) nối vào luồng tra cứu: chạy SAU khi lưu dữ liệu, TRƯỚC bước tải file
src = open(os.path.join(os.path.dirname(server.__file__), "server.py"), encoding="utf-8").read()
i_ds = src.index("_ds = _doi_soat_bang_ke_tho(")
assert src.index("conn.commit()\n                    if _km_tong:") < i_ds < src.index("fmts = dl_map.get(loai, [])")
print("PASS 5: đối soát chạy sau khi lưu và trước khi tải file (hóa đơn bổ sung được tải luôn).")
print("ALL DONE")
