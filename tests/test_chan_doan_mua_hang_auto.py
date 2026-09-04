import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: endpoint /api/misa-sql/chan-doan-da-co-mua-hang/{cid} với
loai='auto' (mới thêm) — dùng khi từ danh sách "thiếu" của Đối chiếu tổng giá
trị & VAT chỉ có MST+Số HĐ, KHÔNG biết hóa đơn thuộc loại Nhập kho/Không qua
kho/Dịch vụ nào -> tự động chạy chẩn đoán cho cả 3 loại, tránh người dùng
phải tự đoán/thử từng loại một."""
import sys
sys.path.insert(0, _REPO_ROOT)
import server

orig_cfg = server._misa_sql_cfg
orig_chan_doan = server._misa_chan_doan_vi_sao_da_co_mua_hang

goi = []

def fake_chan_doan(cid, database, loai, mst, sohd):
    goi.append(loai)
    return {"loai_test": loai, "ket_luan": f"ket luan cho {loai}"}

try:
    server._misa_sql_cfg = lambda cid: {"database": "TESTDB"}
    server._misa_chan_doan_vi_sao_da_co_mua_hang = fake_chan_doan

    r = server.misa_sql_chan_doan_da_co_mua_hang(1, "auto", "0110269067", "1145469")
    print("Ket qua auto:", r)
    assert set(goi) == {"nk", "kqk", "dv"}, f"Phải gọi chẩn đoán đủ cả 3 loại — đã gọi {goi}"
    assert set(r.keys()) == {"nk", "kqk", "dv"}, f"Kết quả auto phải có đủ 3 khóa — {r.keys()}"
    assert r["nk"]["loai_test"] == "nk"
    assert r["dv"]["ket_luan"] == "ket luan cho dv"
    print("PASS: loai='auto' tự chạy chẩn đoán đủ cả 3 loại nk/kqk/dv.")

    # loai cụ thể (nk/kqk/dv) vẫn hoạt động như cũ (không đổi hành vi cũ).
    goi.clear()
    r2 = server.misa_sql_chan_doan_da_co_mua_hang(1, "dv", "0110269067", "1145469")
    assert goi == ["dv"], f"loai cụ thể chỉ được gọi đúng 1 lần cho loại đó — {goi}"
    assert r2["loai_test"] == "dv"
    print("PASS: loai cụ thể (vd 'dv') vẫn giữ nguyên hành vi cũ, không bị đổi thành dict.")

    print("\nTẤT CẢ TEST PASS")
finally:
    server._misa_sql_cfg = orig_cfg
    server._misa_chan_doan_vi_sao_da_co_mua_hang = orig_chan_doan
