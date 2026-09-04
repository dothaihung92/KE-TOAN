import os
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Regression test: "Xuất file Xuất Kho" (xk_export) KHÔNG còn cảnh báo
"vượt tồn ĐẦU KỲ" nữa (banner/toast/header X-So-Canh-Bao-Dau-Ky) — CHỈ chặn
xuất khi thật sự ÂM tồn kho (vượt tồn Cuối kỳ), theo đúng yêu cầu người
dùng: "chỉ thông báo khi mã hàng nào bị âm tồn kho thôi".

Trước đây: mã hàng gán VƯỢT tồn Đầu kỳ (nhưng vẫn trong tồn Cuối kỳ, vì có
Nhập kho bù trong kỳ) làm xuất hiện cảnh báo riêng (banner + toast "N mã
hàng vượt tồn ĐẦU KỲ") dù không phải lỗi thật/không chặn — với công ty
nhập/xuất liên tục, số mã kiểu này có thể lên tới hàng trăm (211 mã, theo
ảnh chụp người dùng gửi), gây nhiễu quá mức."""
import sys, sqlite3, os, tempfile
sys.path.insert(0, _REPO_ROOT)
import server

_db_path = tempfile.mktemp(suffix=".sqlite3")
_data_dir = tempfile.mkdtemp()
_download_dir = tempfile.mkdtemp()


def db_factory():
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    return conn


orig_db, orig_data_dir, orig_dl_dir = server.db, server.DATA_DIR, server.DOWNLOAD_DIR
server.db = db_factory
server.DATA_DIR = _data_dir
server.DOWNLOAD_DIR = _download_dir

goi_luu_loi = []
orig_luu_loi = server._luu_loi_tra_cuu
server._luu_loi_tra_cuu = lambda cid, text: goi_luu_loi.append((cid, text))

try:
    conn = db_factory()
    conn.execute("""CREATE TABLE companies (id INTEGER PRIMARY KEY, mst TEXT,
        save_dir TEXT, data_dir TEXT)""")
    conn.execute("INSERT INTO companies VALUES (1,'0317743519','','')")
    conn.commit()
    conn.close()

    # MA1: tồn Đầu kỳ chỉ 5, nhưng Nhập thêm trong kỳ nên tồn Cuối kỳ lên 50
    # -> gán bán 20 (VƯỢT đầu kỳ 5, nhưng KHÔNG vượt cuối kỳ 50) -> trước
    # đây bị cảnh báo riêng "vượt tồn ĐẦU KỲ", giờ KHÔNG còn cảnh báo này
    # nữa, xuất bình thường không có gì bất thường.
    data1 = server._doc_du_lieu_cty(1)
    data1["xk_ton"] = [{"ma": "MA1", "ten": "San pham A", "dvt": "Cai",
                        "ton": 50, "dau_ky": 5, "gia": 100000}]
    data1["xk_giathanh"] = [{
        "khhdon": "", "sohd": "H1", "ngay": "10/05/2026", "ten_sp": "San pham A",
        "dvt": "Cai", "sl": 20, "dgia": 100000, "tt": 2000000,
        "ma": "MA1", "ten_xk": "San pham A", "dvt_xk": "Cai", "gia_xk": 100000,
        "sl_kho": 20, "goi_y": [], "mo_ho": False, "thieu_ton": False,
    }]
    server._ghi_du_lieu_cty(1, data1)

    resp = server.xk_export(1)
    print("Header X-So-Canh-Bao-Dau-Ky:", resp.headers.get("x-so-canh-bao-dau-ky"))
    print("Số lần gọi _luu_loi_tra_cuu (log cảnh báo):", len(goi_luu_loi))
    assert resp.headers.get("x-so-canh-bao-dau-ky") is None, (
        f"KHÔNG được còn header X-So-Canh-Bao-Dau-Ky nữa (mã vượt đầu kỳ không còn cảnh báo riêng) — "
        f"được {resp.headers.get('x-so-canh-bao-dau-ky')}")
    assert not goi_luu_loi, (
        f"KHÔNG được ghi cảnh báo 'vượt tồn ĐẦU KỲ' vào banner công ty nữa — được {goi_luu_loi}")
    print("PASS: mã hàng vượt tồn ĐẦU KỲ (nhưng KHÔNG âm tồn Cuối kỳ) xuất file bình thường, không còn "
          "cảnh báo riêng.")

    # ===== Đối chứng: mã hàng THẬT SỰ âm tồn (vượt cả tồn Cuối kỳ) vẫn PHẢI
    # bị CHẶN xuất như trước — đúng yêu cầu "chỉ thông báo khi âm tồn kho". =====
    data1 = server._doc_du_lieu_cty(1)
    data1["xk_ton"] = [{"ma": "MA1", "ten": "San pham A", "dvt": "Cai",
                        "ton": 10, "dau_ky": 5, "gia": 100000}]
    data1["xk_giathanh"] = [{
        "khhdon": "", "sohd": "H2", "ngay": "10/05/2026", "ten_sp": "San pham A",
        "dvt": "Cai", "sl": 20, "dgia": 100000, "tt": 2000000,
        "ma": "MA1", "ten_xk": "San pham A", "dvt_xk": "Cai", "gia_xk": 100000,
        "sl_kho": 20, "goi_y": [], "mo_ho": False, "thieu_ton": False,
    }]
    server._ghi_du_lieu_cty(1, data1)

    bi_chan = False
    try:
        server.xk_export(1)
    except server.HTTPException as e:
        bi_chan = True
        print("Bị chặn đúng như mong đợi (âm tồn kho thật):", e.detail[:120])
        assert e.status_code == 400 and "VƯỢT tồn kho" in e.detail
    assert bi_chan, "Mã hàng THẬT SỰ âm tồn kho (vượt cả Cuối kỳ) vẫn phải bị CHẶN xuất — không được bỏ qua"
    print("PASS: mã hàng thật sự âm tồn kho (vượt cả tồn Cuối kỳ) vẫn bị CHẶN xuất đúng như trước.")

    print("\nTẤT CẢ TEST PASS")
finally:
    server.db = orig_db
    server.DATA_DIR = orig_data_dir
    server.DOWNLOAD_DIR = orig_dl_dir
    server._luu_loi_tra_cuu = orig_luu_loi
    try:
        os.remove(_db_path)
    except OSError:
        pass
    import shutil
    shutil.rmtree(_data_dir, ignore_errors=True)
    shutil.rmtree(_download_dir, ignore_errors=True)
