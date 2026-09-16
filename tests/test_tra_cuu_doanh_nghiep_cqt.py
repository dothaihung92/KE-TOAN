import os
import re
import json
import sqlite3
import tempfile
import datetime

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test cho tính năng "tự động điền thông tin công ty khi Thêm
# công ty" (_tra_cuu_thong_tin_nnt / _ghi_nho_ma_cqt / tra_cuu_doanh_nghiep
# trong server.py) — người dùng yêu cầu: "hãy thêm chức năng chỉ cần điền
# mã thì phần mềm tự động điền các thông tin dưới Mã CQT nơi nộp (HTKK) và
# Tên CQT nơi nộp".
#
# Nguồn dữ liệu: API XInvoice (api.xinvoice.vn/gdt-api/tax-payer/{mst}) đã
# cấu hình sẵn cho tính năng tra tình trạng MST — người dùng tự gọi API
# THẬT (curl.exe) và gửi lại ĐÚNG NGUYÊN VĂN JSON trả về để xác nhận cấu
# trúc, KHÔNG đoán:
#   {"orgType":"Doanh nghiệp / Đơn vị sự nghiệp công lập","taxID":"1102183121",
#    "name":"CÔNG TY TNHH THIÊN Ý VN","address":"Thửa Đất Số 1155, ...",
#    "taxDepartment":"Thuế cơ sở 4 tỉnh Tây Ninh","status":"NNT đang hoạt động",
#    "updatedAt":"2026-08-28T20:49:46.000Z"}
#
# QUAN TRỌNG: trường "taxDepartment" CHỈ có TÊN cơ quan thuế, KHÔNG có MÃ số
# (vd "70113") — API không trả mã này. Vì "Mã CQT nơi nộp" sai có thể khiến
# HTKK từ chối file Kết xuất XML (cảnh báo ngay trong form), phần mềm KHÔNG
# đoán mã — chỉ tự "học" dần: mỗi khi người dùng tự nhập/xác nhận ĐÚNG cả 2
# trường Mã+Tên CQT cho 1 công ty (add_company/update_company), bảng
# cqt_ma_ten ghi nhớ lại, để công ty SAU cùng chung 1 cơ quan thuế được tự
# động gợi ý đúng Mã CQT.


def extract_fn(name):
    idx = src.index('def ' + name + '(')
    i = src.index(':', idx)
    lines = src[i + 1:].split('\n')
    body = []
    started = False
    for ln in lines:
        if ln.strip() == '' and not started:
            body.append(ln)
            continue
        if ln and not ln[0].isspace() and started:
            break
        if ln.strip():
            started = True
        body.append(ln)
    return src[idx:i + 1] + '\n'.join(body)


class _FakeResp:
    def __init__(self, status_code, data=None):
        self.status_code = status_code
        self._data = data

    def json(self):
        return self._data


class _FakeRequests:
    def __init__(self):
        self.calls = []
        self.next_status = 200
        self.next_data = None

    def get(self, url, headers=None, timeout=None):
        self.calls.append({"url": url, "headers": dict(headers or {})})
        return _FakeResp(self.next_status, self.next_data)


class _FakeSettings:
    def __init__(self):
        self.store = {}

    def get(self, key, default=""):
        return self.store.get(key, default)

    def set(self, key, value):
        self.store[key] = value


class _FakeHTTPException(Exception):
    def __init__(self, status_code, detail):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


ns = {'datetime': datetime, 'json': json}
exec(extract_fn('_khong_dau'), ns)
exec(extract_fn('_chuan_mst'), ns)
_fake_requests = _FakeRequests()
_fake_settings = _FakeSettings()
ns['requests'] = _fake_requests
ns['_get_setting'] = _fake_settings.get
ns['_set_setting'] = _fake_settings.set
ns['HTTPException'] = _FakeHTTPException
exec(extract_fn('_lay_danh_sach_xinvoice_keys'), ns)

_tmp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
_tmp_db.close()


def _fresh_db():
    conn = sqlite3.connect(_tmp_db.name, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS cqt_ma_ten (
        ten_cqt TEXT PRIMARY KEY, ma_cqt TEXT, cap_nhat_at TEXT
    )""")
    return conn


ns['db'] = _fresh_db
# tra_cuu_doanh_nghiep() giờ còn dò thêm danh mục CQT toàn quốc
# (_lay_danh_muc_cqt, xem test_danh_muc_cqt_toan_quoc.py) — trỏ BASE_DIR
# vào thư mục KHÔNG có data/cqt_catalogue.txt để hàm đó trả về {} an toàn,
# giữ đúng các kỳ vọng "chưa học được thì để rỗng" của các test PHÍA TRÊN
# (chỉ kiểm tra việc "học" qua cqt_ma_ten, không phải danh mục toàn quốc).
ns['os'] = os
ns['BASE_DIR'] = tempfile.mkdtemp()
ns['_DANH_MUC_CQT'] = None
exec(extract_fn('_tra_cuu_thong_tin_nnt'), ns)
exec(extract_fn('_ghi_nho_ma_cqt'), ns)
exec(extract_fn('_lay_danh_muc_cqt'), ns)
# tra_cuu_doanh_nghiep() giờ còn tra "Người đại diện" trên masothue.com
# (_lay_ten_nguoi_dai_dien_masothue, xem test_nguoi_dai_dien_masothue.py)
# — dùng bản giả luôn trả "" (không gọi mạng), vì các test trong file này
# chỉ kiểm tra riêng phần Tên/Địa chỉ/Mã CQT qua XInvoice, không liên quan
# masothue.com.
ns['_lay_ten_nguoi_dai_dien_masothue'] = lambda mst: ""
exec(extract_fn('tra_cuu_doanh_nghiep'), ns)
_tra_cuu_thong_tin_nnt = ns['_tra_cuu_thong_tin_nnt']
_ghi_nho_ma_cqt = ns['_ghi_nho_ma_cqt']
tra_cuu_doanh_nghiep = ns['tra_cuu_doanh_nghiep']

_conn0 = _fresh_db()
_conn0.execute("DELETE FROM cqt_ma_ten")
_conn0.commit()
_conn0.close()

# ===== Test 1 (QUAN TRỌNG — đúng dữ liệu THẬT người dùng gửi từ curl.exe):
# _tra_cuu_thong_tin_nnt() phải trích đúng "name"->ten, "address"->dia_chi,
# "taxDepartment"->ten_cqt, "status"->trang_thai — ĐÚNG NGUYÊN VĂN cấu trúc
# JSON thật, không suy đoán tên trường khác. =====
_fake_settings.set("xinvoice_client_id", "demo-client")
_fake_settings.set("xinvoice_api_key", "demo-key")
_fake_requests.next_status = 200
_fake_requests.next_data = {
    "orgType": "Doanh nghiệp / Đơn vị sự nghiệp công lập", "taxID": "1102183121",
    "name": "CÔNG TY TNHH THIÊN Ý VN",
    "address": "Thửa Đất Số 1155, Tờ Bản Đồ Số 4, Ấp Đức Hạnh 1, Xã Đức Lập, Tây Ninh",
    "taxDepartment": "Thuế cơ sở 4 tỉnh Tây Ninh",
    "status": "NNT đang hoạt động", "updatedAt": "2026-08-28T20:49:46.000Z",
}
info = _tra_cuu_thong_tin_nnt("1102183121")
assert info is not None
assert info["ten"] == "CÔNG TY TNHH THIÊN Ý VN", f"got {info}"
assert info["dia_chi"].startswith("Thửa Đất Số 1155"), f"got {info}"
assert info["ten_cqt"] == "Thuế cơ sở 4 tỉnh Tây Ninh", f"got {info}"
assert info["trang_thai"] == "NNT đang hoạt động", f"got {info}"
print("PASS 1: _tra_cuu_thong_tin_nnt() trích đúng ten/dia_chi/ten_cqt/trang_thai từ ĐÚNG cấu trúc "
      "JSON thật (name/address/taxDepartment/status) người dùng đã tự xác nhận qua curl.exe.")

# ===== Test 2 (không hồi quy): CHƯA cấu hình key XInvoice nào -> trả về
# None (không lỗi/crash), để endpoint báo 404 cho giao diện bỏ qua. =====
_fake_settings.set("xinvoice_client_id", "")
_fake_settings.set("xinvoice_api_key", "")
_fake_settings.set("xinvoice_api_keys", "")
info2 = _tra_cuu_thong_tin_nnt("1102183121")
assert info2 is None, f"Chưa cấu hình key -> phải trả None — got {info2}"
print("PASS 2: chưa cấu hình key XInvoice nào -> trả None an toàn, không lỗi.")

_fake_settings.set("xinvoice_client_id", "demo-client")
_fake_settings.set("xinvoice_api_key", "demo-key")

# ===== Test 3 (không hồi quy): MST không hợp lệ (rỗng/quá ngắn) -> trả về
# None ngay, không gọi mạng. =====
_fake_requests.calls.clear()
info3 = _tra_cuu_thong_tin_nnt("123")
assert info3 is None
assert len(_fake_requests.calls) == 0, f"MST không hợp lệ không được gọi mạng — got {_fake_requests.calls}"
print("PASS 3: MST không hợp lệ -> trả None, không gọi mạng.")

# ===== Test 4 (QUAN TRỌNG — đúng tinh thần yêu cầu người dùng "tự học Mã
# CQT"): _ghi_nho_ma_cqt() lưu đúng cặp Tên CQT <-> Mã CQT khi CẢ 2 đều có;
# BỎ QUA khi thiếu 1 trong 2 (không lưu cặp không đầy đủ). =====
conn4 = _fresh_db()
conn4.execute("DELETE FROM cqt_ma_ten")
conn4.commit()
conn4.close()
_ghi_nho_ma_cqt("Thuế cơ sở 4 tỉnh Tây Ninh", "70113")
_ghi_nho_ma_cqt("Thuế cơ sở khác chưa có mã", "")   # thiếu mã -> bỏ qua
_ghi_nho_ma_cqt("", "12345")   # thiếu tên -> bỏ qua
conn4b = _fresh_db()
rows = conn4b.execute("SELECT * FROM cqt_ma_ten").fetchall()
conn4b.close()
assert len(rows) == 1 and rows[0]["ten_cqt"] == "Thuế cơ sở 4 tỉnh Tây Ninh" and rows[0]["ma_cqt"] == "70113", (
    f"Chỉ được lưu ĐÚNG 1 cặp đầy đủ cả Tên+Mã, bỏ qua các cặp thiếu — got {[dict(r) for r in rows]}")
print("PASS 4: _ghi_nho_ma_cqt() chỉ lưu khi CÓ ĐỦ cả Tên CQT lẫn Mã CQT, bỏ qua cặp thiếu.")

# ===== Test 5 (QUAN TRỌNG — kịch bản THẬT: công ty sau cùng cơ quan thuế
# được tự động gợi ý đúng Mã CQT): sau khi đã "học" được 1 cặp Tên<->Mã CQT
# (Test 4), tra_cuu_doanh_nghiep() cho 1 MST KHÁC nhưng CÙNG "taxDepartment"
# -> phải tự động điền đúng "ma_cqt" từ bảng đã học, dù API không trả mã. =====
_fake_requests.next_data = {
    "name": "CÔNG TY TNHH KHÁC CÙNG CQT", "address": "địa chỉ khác",
    "taxDepartment": "Thuế cơ sở 4 tỉnh Tây Ninh", "status": "NNT đang hoạt động",
}
ket_qua5 = tra_cuu_doanh_nghiep("0399999999")
assert ket_qua5["ten"] == "CÔNG TY TNHH KHÁC CÙNG CQT"
assert ket_qua5["ten_cqt"] == "Thuế cơ sở 4 tỉnh Tây Ninh"
assert ket_qua5["ma_cqt"] == "70113", (
    f"Công ty khác CÙNG cơ quan thuế đã 'học' trước đó (Test 4) -> phải tự động gợi ý ĐÚNG Mã CQT dù "
    f"API không trả mã — got {ket_qua5}")
print("PASS 5: tra_cuu_doanh_nghiep() tự động gợi ý ĐÚNG Mã CQT (từ bảng đã 'học' trước đó) cho công "
      "ty khác cùng cơ quan thuế quản lý, dù API XInvoice không trả mã.")

# ===== Test 6 (không hồi quy): cơ quan thuế CHƯA từng được 'học' Mã CQT ->
# ma_cqt trả về rỗng (không suy đoán bừa), vẫn có đủ ten/dia_chi/ten_cqt. =====
_fake_requests.next_data = {
    "name": "CÔNG TY CHƯA AI NHẬP MÃ CQT", "address": "địa chỉ",
    "taxDepartment": "Thuế cơ sở hoàn toàn mới chưa từng gặp",
    "status": "NNT đang hoạt động",
}
ket_qua6 = tra_cuu_doanh_nghiep("0388888888")
assert ket_qua6["ten_cqt"] == "Thuế cơ sở hoàn toàn mới chưa từng gặp"
assert ket_qua6["ma_cqt"] == "", f"Cơ quan thuế chưa từng được 'học' Mã -> phải để rỗng, không suy đoán — got {ket_qua6}"
print("PASS 6: cơ quan thuế chưa từng được 'học' Mã CQT -> để rỗng an toàn (không suy đoán bừa), vẫn "
      "điền đủ Tên công ty/Địa chỉ/Tên CQT.")

# ===== Test 7 (không hồi quy): MST không tra được (API lỗi/không cấu hình)
# -> tra_cuu_doanh_nghiep() báo lỗi rõ ràng (404) thay vì trả dữ liệu rỗng
# lặng lẽ, để giao diện biết mà bỏ qua thay vì tưởng đã tự điền xong. =====
_fake_settings.set("xinvoice_client_id", "")
_fake_settings.set("xinvoice_api_key", "")
_fake_settings.set("xinvoice_api_keys", "")
loi7 = None
try:
    tra_cuu_doanh_nghiep("0377777777")
except _FakeHTTPException as e:
    loi7 = e
assert loi7 is not None and loi7.status_code == 404, f"Không tra được -> phải báo lỗi 404 rõ ràng — got {loi7}"
print("PASS 7: không tra được thông tin (chưa cấu hình API) -> báo lỗi 404 rõ ràng, không âm thầm trả "
      "dữ liệu rỗng.")

os.unlink(_tmp_db.name)
print("\nALL DONE")
