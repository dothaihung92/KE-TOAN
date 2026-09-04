import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: chẩn đoán "🔍 Vì sao đã có?" — cho biết CHÍNH XÁC vì sao
1 hóa đơn Mua hàng cụ thể (MST NCC + Số HĐ) bị "Import tự động toàn bộ"/
"⬆ ... vào MISA" báo "đã có, bỏ qua" dù thực tế KHÔNG có trong MISA (đối
chiếu qua file export thật) — người dùng báo cáo đúng ca này: hóa đơn Số
HĐ 1145469 (NCC 0110269067) vẫn báo "đã có" dù tìm trong file
Mua_hang_hoa__dich_vu.xlsx thật KHÔNG thấy Số HĐ này ở đâu cả."""
import sys
sys.path.insert(0, _REPO_ROOT)
import server
import datetime


class FakeCursor:
    def __init__(self, cols_psd, psd_rows):
        self._cols_psd = cols_psd
        self._psd_rows = psd_rows

    def execute(self, sql, *params):
        self.last_sql = sql
        self.last_params = params[0] if len(params) == 1 else params
        return self

    def fetchall(self):
        if "sys.columns" in self.last_sql:
            table = self.last_params
            if table == "PUServiceDetail":
                return [(c, "nvarchar") for c in self._cols_psd]
            return []
        if "FROM PUServiceDetail" in self.last_sql:
            return self._psd_rows
        return []


class FakeConn:
    def __init__(self, cur):
        self._cur = cur

    def cursor(self):
        return self._cur

    def close(self):
        pass


orig_connect = server._misa_sql_connect

try:
    # ===== Ca 1: KHÔNG dò được cột ngày (schema lạ, thiếu InvDate/RefDate)
    # -> phải báo rõ đây là nguyên nhân, không được im lặng. =====
    cur1 = FakeCursor(["TaxAccountObjectTaxCode", "InvNo", "Amount"],  # KHÔNG có InvDate/RefDate
                      [("0110269067", "1145469")])
    server._misa_sql_connect = lambda cid, database=None: FakeConn(cur1)
    r1 = server._misa_chan_doan_vi_sao_da_co_mua_hang(1, "TESTDB", "dv", "0110269067", "1145469")
    print("Ca 1:", r1)
    assert r1["cot_ngay_dung"] is None, f"Không có cột ngày trong bảng -> cot_ngay_dung phải None — {r1}"
    assert "KHÔNG dò được cột ngày" in r1["ket_luan"], f"Kết luận phải nêu rõ thiếu cột ngày — {r1['ket_luan']}"
    print("PASS ca 1: báo đúng khi không dò được cột ngày.")

    # ===== Ca 2: CÓ cột ngày, KHÔNG có ứng viên nào khớp (MST,Số HĐ) —
    # đúng hiện trạng người dùng báo: hóa đơn THẬT SỰ chưa có trong MISA. =====
    cur2 = FakeCursor(["TaxAccountObjectTaxCode", "InvNo", "InvDate"],
                      [("0316491058", "178", datetime.datetime(2026, 6, 30))])  # NCC/Số HĐ KHÁC hẳn
    server._misa_sql_connect = lambda cid, database=None: FakeConn(cur2)
    r2 = server._misa_chan_doan_vi_sao_da_co_mua_hang(1, "TESTDB", "dv", "0110269067", "1145469")
    print("Ca 2:", r2)
    assert r2["cot_ngay_dung"] == "InvDate"
    assert r2["so_ung_vien_khop_mst_sohd"] == 0
    assert "THẬT SỰ chưa có trong MISA" in r2["ket_luan"], f"Phải kết luận hóa đơn thật sự chưa có — {r2['ket_luan']}"
    print("PASS ca 2: báo đúng khi hóa đơn thật sự chưa có (0 ứng viên khớp).")

    # ===== Ca 3: CÓ ứng viên khớp (MST,Số HĐ) — liệt kê đủ để người dùng/
    # Claude tự xem ngày có hợp lý hay là bug (ngày cách xa mà vẫn khớp). =====
    cur3 = FakeCursor(["TaxAccountObjectTaxCode", "InvNo", "InvDate"],
                      [("0110269067", "1145469", datetime.datetime(2021, 1, 1))])
    server._misa_sql_connect = lambda cid, database=None: FakeConn(cur3)
    r3 = server._misa_chan_doan_vi_sao_da_co_mua_hang(1, "TESTDB", "dv", "0110269067", "1145469")
    print("Ca 3:", r3)
    assert r3["so_ung_vien_khop_mst_sohd"] == 1
    assert r3["ung_vien"][0]["Ngay"] == "2021-01-01T00:00:00"
    assert "Tìm thấy 1 ứng viên" in r3["ket_luan"]
    print("PASS ca 3: liệt kê đúng ứng viên khớp kèm ngày để tự xem có hợp lý không.")

    print("\nTẤT CẢ TEST PASS")
finally:
    server._misa_sql_connect = orig_connect
