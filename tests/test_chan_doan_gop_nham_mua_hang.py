import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: mở rộng chẩn đoán "🔍 Vì sao đã có?" — khi 1 hóa đơn
Mua hàng KHÔNG có ứng viên "đã có" nào trong MISA (đúng ca thật: Đối chiếu
tổng giá trị & VAT xác nhận chắc chắn hóa đơn 1145469/NCC 0110269067 chưa
có trong MISA) NHƯNG "⬆ Dịch vụ vào MISA" vẫn không ghi được — chẩn đoán
phải kiểm tra thêm bước GOM NHÓM CHỨNG TỪ (theo "Số CT" tự sinh) để biết
hóa đơn có thật sự tách riêng đúng thành 1 nhóm hay bị gộp nhầm/mất tích."""
import sys
sys.path.insert(0, _REPO_ROOT)
import server


class FakeCursor:
    """Không có ứng viên PUServiceDetail nào — mô phỏng đúng ca thật (hóa
    đơn chưa có trong MISA), để bài test tập trung vào bước gom nhóm mới."""
    def execute(self, sql, *params):
        self.last_sql = sql
        self.last_params = params[0] if len(params) == 1 else params
        return self

    def fetchall(self):
        if "sys.columns" in self.last_sql:
            if self.last_params == "PUServiceDetail":
                return [("TaxAccountObjectTaxCode", "nvarchar"), ("InvNo", "nvarchar"),
                        ("InvDate", "datetime")]
            return []
        return []


class FakeConn:
    def cursor(self):
        return FakeCursor()

    def close(self):
        pass


HEADER = ["Ký hiệu", "Số HĐ", "Ngày", "Người bán", "MST bán", "STT", "Mã vt",
          "Tên hàng hóa/dịch vụ", "ĐVT", "Số lượng", "Đơn giá", "Thành tiền",
          "Thuế suất", "Tiền thuế GTGT", "Nợ", "Có"]

orig_connect = server._misa_sql_connect
orig_get = server.nhap_lieu_get
orig_doc_cty = server._doc_du_lieu_cty

try:
    # ===== Ca 1: hóa đơn ĐÚNG dữ liệu (2 dòng, cùng mst/sohd/ngay/kyhieu) —
    # phải tự đứng riêng thành 1 nhóm, KHÔNG bị gộp với NCC nào khác, không
    # cảnh báo gì. =====
    rows1 = [
        ["C26MHA", "1145469", "04/01/2026", "CÔNG TY CỔ PHẦN DI CHUYỂN XANH VÀ THÔNG MINH GSM",
         "0110269067", "1", "TRANSPORTATION_FEE", "Cước phí vận chuyển", "Chuyến", 1, 214981, 214981,
         "8%", 17198, "6427", "331"],
        ["C26MHA", "1145469", "04/01/2026", "CÔNG TY CỔ PHẦN DI CHUYỂN XANH VÀ THÔNG MINH GSM",
         "0110269067", "2", "PLATFORM_FEE", "Phí nền tảng", "Chuyến", 1, 14820, 14820,
         "0%", 0, "6427", "331"],
        # 1 hóa đơn KHÁC hẳn (NCC khác) để bảo đảm KHÔNG bị gộp chung.
        ["C26TTT", "1", "07/01/2026", "CÔNG TY TNHH TUẤN TRƯỜNG THỊNH", "3603289732", "1",
         "MHDV", "Chậu Polystone ASH30 - MTWT", "Cái", 1, 100000, 100000, "8%", 8000, "6427", "331"],
    ]
    server._misa_sql_connect = lambda cid, database=None: FakeConn()
    server.nhap_lieu_get = lambda cid, loai: {"header": HEADER, "rows": rows1}
    # File JSON (_doc_du_lieu_cty) cố tình để KHÁC hẳn/cũ (rỗng) — chẩn đoán
    # PHẢI bỏ qua nguồn này hoàn toàn và chỉ tin bảng SQL (nhap_lieu_get),
    # đúng như _misa_ghi_mua_hang_dv thật sự dùng khi ghi.
    server._doc_du_lieu_cty = lambda cid: {}

    r1 = server._misa_chan_doan_vi_sao_da_co_mua_hang(1, "TESTDB", "dv", "0110269067", "1145469")
    print("Ca 1:", r1)
    assert r1["so_dong_flat_thuoc_hoa_don"] == 2, (
        f"Phải tìm đúng 2 dòng (2 mặt hàng/dịch vụ) thuộc hóa đơn 1145469 — được {r1}")
    assert len(r1["so_ct_cua_hoa_don"]) == 1, f"2 dòng phải cùng gom về ĐÚNG 1 Số CT — được {r1['so_ct_cua_hoa_don']}"
    assert "canh_bao_gop_nham" not in r1, (
        f"Hóa đơn tách riêng đúng, KHÔNG được cảnh báo gộp nhầm — được {r1.get('canh_bao_gop_nham')}")
    print("PASS ca 1: hóa đơn đúng dữ liệu tự đứng riêng 1 nhóm, không cảnh báo gộp nhầm.")

    # ===== Ca 2: hóa đơn HOÀN TOÀN KHÔNG có trong Bảng kê Đầu vào hiện tại
    # (đã bị xoá/sửa MST hoặc đang xem sai công ty) — phải báo rõ, không
    # được im lặng coi như "đã kiểm tra xong, không có gì bất thường". =====
    rows2 = [
        ["C26TTT", "1", "07/01/2026", "CÔNG TY TNHH TUẤN TRƯỜNG THỊNH", "3603289732", "1",
         "MHDV", "Chậu Polystone ASH30 - MTWT", "Cái", 1, 100000, 100000, "8%", 8000, "6427", "331"],
    ]
    server.nhap_lieu_get = lambda cid, loai: {"header": HEADER, "rows": rows2}
    r2 = server._misa_chan_doan_vi_sao_da_co_mua_hang(1, "TESTDB", "dv", "0110269067", "1145469")
    print("Ca 2:", r2)
    assert r2["so_dong_flat_thuoc_hoa_don"] == 0
    assert r2["so_ct_cua_hoa_don"] == []
    assert "canh_bao_gop_nham" in r2 and "KHÔNG tìm thấy dòng nào" in r2["canh_bao_gop_nham"], (
        f"Phải báo rõ KHÔNG tìm thấy hóa đơn này trong Bảng kê Đầu vào hiện tại — được {r2}")
    print("PASS ca 2: báo đúng khi hóa đơn không có trong Bảng kê Đầu vào hiện tại (kỳ/công ty sai).")

    # ===== Ca 3 (bug thật của người dùng, 3/9/2026): file JSON cũ/lệch
    # (_doc_du_lieu_cty) vẫn có dữ liệu (KHÔNG rỗng) nhưng KHÔNG chứa hóa
    # đơn 1145469 — trong khi bảng SQL (nhap_lieu_get), đúng là bảng đang
    # hiển thị trên màn hình (1015 dòng, người dùng chụp ảnh xác nhận), CÓ
    # đủ 2 dòng của hóa đơn này. Chẩn đoán PHẢI đọc bảng SQL, không được để
    # file JSON cũ "che" mất kết quả đúng chỉ vì file đó không hoàn toàn
    # rỗng. =====
    rows_json_cu = [
        ["C26TTT", "9999", "01/01/2020", "NCC CŨ NÀO ĐÓ", "9999999999", "1",
         "X", "Hàng cũ", "Cái", 1, 1000, 1000, "0%", 0, "6427", "331"],
    ]
    server._doc_du_lieu_cty = lambda cid: {"nhap_lieu_in": {"header": HEADER, "rows": rows_json_cu}}
    server.nhap_lieu_get = lambda cid, loai: {"header": HEADER, "rows": rows1}
    r3 = server._misa_chan_doan_vi_sao_da_co_mua_hang(1, "TESTDB", "dv", "0110269067", "1145469")
    print("Ca 3:", r3)
    assert r3["so_dong_flat_thuoc_hoa_don"] == 2, (
        f"Phải đọc bảng SQL (nhap_lieu_get) đang hiển thị trên màn hình, KHÔNG được lấy nhầm file JSON "
        f"cũ chỉ vì file đó không rỗng — được {r3}")
    assert "canh_bao_gop_nham" not in r3, f"Không được báo nhầm 'không tìm thấy' — được {r3.get('canh_bao_gop_nham')}"
    print("PASS ca 3: không bị file JSON cũ/lệch (còn dữ liệu nhưng khác) làm che mất hóa đơn thật trên bảng SQL.")

    # ===== Ca 4 (nghi vấn nguyên nhân thật, 3/9/2026): hóa đơn Số HĐ 1145469
    # CÓ trong Bảng kê Đầu vào (đúng như ảnh chụp người dùng gửi), nhưng MST
    # ghi trên dòng đó là MST 13 số có hậu tố chi nhánh ("0110269067-001" —
    # _dinh_dang_mst tự thêm dấu '-' cho MST 13 số), trong khi MST đang tra
    # chỉ là MST công ty mẹ 10 số ("0110269067") — 2 giá trị KHÔNG khớp dù
    # cùng gốc. Chẩn đoán phải PHÁT HIỆN RA lệch định dạng này (chỉ dò theo
    # Số HĐ, bỏ qua MST) thay vì chỉ im lặng báo "không có gì". =====
    rows4 = [
        ["C26MHA", "1145469", "04/01/2026", "CÔNG TY CỔ PHẦN DI CHUYỂN XANH VÀ THÔNG MINH GSM",
         "0110269067001", "1", "TRANSPORTATION_FEE", "Cước phí vận chuyển", "Chuyến", 1, 214981, 214981,
         "8%", 17198, "6427", "331"],
    ]
    server.nhap_lieu_get = lambda cid, loai: {"header": HEADER, "rows": rows4}
    server._doc_du_lieu_cty = lambda cid: {}
    r4 = server._misa_chan_doan_vi_sao_da_co_mua_hang(1, "TESTDB", "dv", "0110269067", "1145469")
    print("Ca 4:", r4)
    assert r4["so_dong_flat_thuoc_hoa_don"] == 0, f"MST 13 số khác MST 10 số -> không được tính là khớp — {r4}"
    assert len(r4["dong_khop_theo_so_hd_rieng"]) == 1, (
        f"Phải tìm thấy đúng 1 dòng khớp riêng Số HĐ (bỏ qua MST) để lộ ra MST thật đang lưu — {r4}")
    assert r4["dong_khop_theo_so_hd_rieng"][0]["mst_da_dinh_dang"] == "0110269067-001"
    assert "LỆCH ĐỊNH DẠNG" in r4["canh_bao_gop_nham"], (
        f"Phải cảnh báo rõ đây là lệch định dạng MST (hậu tố chi nhánh), không phải hóa đơn thiếu — {r4}")
    print("PASS ca 4: phát hiện đúng lệch định dạng MST (hậu tố chi nhánh '-001') khi chỉ khớp theo Số HĐ.")

    # ===== Ca 5 (ĐÚNG kết quả thật người dùng báo lại, 3/9/2026): MST và Số
    # HĐ khớp CHÍNH XÁC ("0110269067"=="0110269067"), nhưng cột 'Nợ' (TK Nợ)
    # của dòng này đang TRỐNG (chưa hạch toán) -> _gen_mua_hang_dv (lọc CHỈ
    # lấy Nợ bắt đầu bằng '6') loại dòng này ra khỏi danh sách ứng viên ghi,
    # nên hóa đơn "biến mất" dù MST/Số HĐ đều đúng. Chẩn đoán PHẢI chỉ đúng
    # nguyên nhân là TK Nợ trống, KHÔNG được báo nhầm là lệch MST. =====
    rows5 = [
        ["C26MHA", "1145469", "04/01/2026", "CÔNG TY CỔ PHẦN DI CHUYỂN XANH VÀ THÔNG MINH GSM",
         "0110269067", "1", "TRANSPORTATION_FEE", "Cước phí vận chuyển", "Chuyến", 1, 214981, 214981,
         "8%", 17198, "", "331"],
        ["C26MHA", "1145469", "04/01/2026", "CÔNG TY CỔ PHẦN DI CHUYỂN XANH VÀ THÔNG MINH GSM",
         "0110269067", "2", "PLATFORM_FEE", "Phí nền tảng", "Chuyến", 1, 14820, 14820,
         "0%", 0, "", "331"],
    ]
    server.nhap_lieu_get = lambda cid, loai: {"header": HEADER, "rows": rows5}
    server._doc_du_lieu_cty = lambda cid: {}
    r5 = server._misa_chan_doan_vi_sao_da_co_mua_hang(1, "TESTDB", "dv", "0110269067", "1145469")
    print("Ca 5:", r5)
    assert r5["so_dong_flat_thuoc_hoa_don"] == 0, f"TK Nợ trống -> _gen_mua_hang_dv phải loại dòng này — {r5}"
    assert len(r5["dong_khop_theo_so_hd_rieng"]) == 2
    assert all(d["mst_khop"] for d in r5["dong_khop_theo_so_hd_rieng"]), "MST phải được nhận diện là ĐÃ khớp"
    assert not any(d["no_tk_hop_le_6xx"] for d in r5["dong_khop_theo_so_hd_rieng"])
    assert "TK Nợ" in r5["canh_bao_gop_nham"] and "TRỐNG" in r5["canh_bao_gop_nham"], (
        f"Phải chỉ đúng nguyên nhân là TK Nợ trống, không phải lệch MST — {r5['canh_bao_gop_nham']}")
    assert "MST KHÔNG khớp" not in r5["canh_bao_gop_nham"], (
        f"MST ĐÃ khớp đúng rồi, không được báo nhầm lệch MST — {r5['canh_bao_gop_nham']}")
    print("PASS ca 5: chỉ đúng nguyên nhân TK Nợ trống (không báo nhầm lệch MST) khi MST/Số HĐ đã khớp đúng.")

    print("\nTẤT CẢ TEST PASS")
finally:
    server._misa_sql_connect = orig_connect
    server.nhap_lieu_get = orig_get
    server._doc_du_lieu_cty = orig_doc_cty
