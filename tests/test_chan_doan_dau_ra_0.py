import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: chẩn đoán "Vì sao Thuế đầu ra = 0?" cho 1 quý trên màn
xem trước Tờ khai GTGT — người dùng báo cáo: đã "nhập đầy đủ" Bán hàng vào
MISA (ảnh chụp/export cho thấy nhiều hóa đơn Bán hàng thật) nhưng tờ khai
vẫn hiện "Thuế đầu ra: 0" cho quý xét tới.

Nguyên nhân thường gặp: MISA chỉ tính hóa đơn ĐÃ 'Ghi sổ' (IsPostedFinance=1)
vào tờ khai thật — "Lập/Lưu hóa đơn" và "Ghi sổ" là 2 bước RIÊNG. Hàm chẩn
đoán _misa_chan_doan_vi_sao_thue_dau_ra_0 phải phân biệt được 2 ca:
(a) hoàn toàn KHÔNG có hóa đơn Bán hàng nào rơi vào quý đó, và
(b) CÓ hóa đơn nhưng TOÀN BỘ CHƯA ghi sổ — và trả kết luận + danh sách mẫu
hóa đơn chưa ghi sổ tương ứng."""
import sys, datetime
sys.path.insert(0, _REPO_ROOT)
import server

# Dữ liệu SAVoucher/SAVoucherDetail giả lập: mỗi phần tử là 1 dòng chi tiết
# (RefID, RefNoFinance, RefDate, AccountObjectName, InvNo, IsPostedFinance, Amount, VATAmount)
DU_LIEU = [
    # Quý 1/2026 (01/01-31/03): 2 hóa đơn, CẢ 2 CHƯA ghi sổ -> ca (b)
    ("R1", "BH001/T1/2026", datetime.datetime(2026, 1, 15), "Khách A", "101", 0, 10_000_000, 1_000_000),
    ("R2", "BH002/T2/2026", datetime.datetime(2026, 2, 10), "Khách B", "102", None, 20_000_000, 2_000_000),
    # Quý 2/2026 (01/04-30/06): KHÔNG có hóa đơn nào -> ca (a)
    # Quý 3/2026 (01/07-30/09): 1 hóa đơn ĐÃ ghi sổ -> ca bình thường
    ("R3", "BH010/T8/2026", datetime.datetime(2026, 8, 5), "Khách C", "110", 1, 5_000_000, 500_000),
]


class FakeCursor:
    def execute(self, sql, params=()):
        self.last_sql = sql
        self.last_params = params
        return self

    def _loc_ngay(self):
        tu_ngay, den_ngay = self.last_params[0], self.last_params[1]
        return [r for r in DU_LIEU if tu_ngay <= r[2] <= den_ngay]

    def fetchone(self):
        sql = self.last_sql
        if "COUNT(DISTINCT RefID) FROM SAVoucher" in sql:
            return (len(set(r[0] for r in DU_LIEU)),)
        rows = self._loc_ngay()
        if "IsPostedFinance=1" in sql:
            rows = [r for r in rows if r[5] == 1]
        elif "IsPostedFinance=0 OR" in sql:
            rows = [r for r in rows if r[5] in (0, None)]
        n = len(set(r[0] for r in rows))
        tong_tien = sum(r[6] for r in rows)
        tong_thue = sum(r[7] for r in rows)
        return (n, tong_tien, tong_thue)

    def fetchall(self):
        rows = self._loc_ngay()
        rows = [r for r in rows if r[5] in (0, None)]
        seen, out = set(), []
        for r in sorted(rows, key=lambda x: x[2]):
            if r[0] in seen:
                continue
            seen.add(r[0])
            out.append((r[0], r[1], r[2], r[3], r[4], r[5]))
        return out


class FakeConn:
    def cursor(self):
        return FakeCursor()

    def close(self):
        pass


orig_connect = server._misa_sql_connect
server._misa_sql_connect = lambda cid, database=None: FakeConn()

try:
    # ===== Ca (b): Quý 1/2026 -> CÓ hóa đơn nhưng CHƯA ghi sổ. =====
    r1 = server._misa_chan_doan_vi_sao_thue_dau_ra_0(1, "TESTDB", 1, 2026)
    print("Quý 1/2026:", r1)
    assert r1["da_ghi_so"]["so_chung_tu"] == 0, f"Quý 1 không có hóa đơn nào đã ghi sổ — được {r1['da_ghi_so']}"
    assert r1["chua_ghi_so"]["so_chung_tu"] == 2, f"Quý 1 phải phát hiện đúng 2 hóa đơn CHƯA ghi sổ — được {r1['chua_ghi_so']}"
    assert r1["chua_ghi_so"]["tong_thue_gtgt"] == 3_000_000
    assert "CHƯA" in r1["ket_luan"] and "GHI SỔ" in r1["ket_luan"], (
        f"Kết luận phải nêu rõ nguyên nhân là CHƯA ghi sổ — được {r1['ket_luan']!r}")
    assert len(r1["mau_hoa_don_chua_ghi_so"]) == 2, "Phải liệt kê đủ 2 hóa đơn mẫu chưa ghi sổ"
    ma_ct = {m["RefNoFinance"] for m in r1["mau_hoa_don_chua_ghi_so"]}
    assert ma_ct == {"BH001/T1/2026", "BH002/T2/2026"}, f"Phải đúng tên 2 chứng từ — được {ma_ct}"
    print("PASS ca (b): phát hiện đúng 'có hóa đơn nhưng chưa ghi sổ', liệt kê đúng mẫu.")

    # ===== Ca (a): Quý 2/2026 -> KHÔNG có hóa đơn nào. =====
    r2 = server._misa_chan_doan_vi_sao_thue_dau_ra_0(1, "TESTDB", 2, 2026)
    print("Quý 2/2026:", r2)
    assert r2["da_ghi_so"]["so_chung_tu"] == 0 and r2["chua_ghi_so"]["so_chung_tu"] == 0
    assert "KHÔNG có hóa đơn" in r2["ket_luan"], f"Kết luận phải nêu KHÔNG có hóa đơn nào — được {r2['ket_luan']!r}"
    assert r2["mau_hoa_don_chua_ghi_so"] == []
    print("PASS ca (a): phát hiện đúng 'hoàn toàn không có hóa đơn' cho quý trống.")

    # ===== Ca bình thường: Quý 3/2026 -> ĐÃ có hóa đơn ghi sổ (không phải
    # nguyên nhân gây Thuế đầu ra=0, dùng để đối chứng không báo nhầm). =====
    r3 = server._misa_chan_doan_vi_sao_thue_dau_ra_0(1, "TESTDB", 3, 2026)
    print("Quý 3/2026:", r3)
    assert r3["da_ghi_so"]["so_chung_tu"] == 1 and r3["da_ghi_so"]["tong_thue_gtgt"] == 500_000
    assert "Đã có hóa đơn ghi sổ" in r3["ket_luan"]
    print("PASS ca bình thường: quý đã có hóa đơn ghi sổ không bị báo nhầm là thiếu.")

    print("\nTẤT CẢ TEST PASS")
finally:
    server._misa_sql_connect = orig_connect
