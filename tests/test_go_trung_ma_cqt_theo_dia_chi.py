import os
import tempfile
import datetime

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test cho việc gỡ trùng Mã CQT nơi nộp bằng Xã/Phường trong địa
# chỉ công ty (_lay_ma_cqt_theo_xa / _go_trung_ma_cqt_theo_dia_chi) — người
# dùng báo: với công ty MST 1102183121 (địa chỉ "...Xã Đức Lập, Tây Ninh"),
# Tên CQT "Thuế cơ sở 4 tỉnh Tây Ninh" bị trùng ở 2 mã (80113/80115) nên
# phần mềm để trống — rồi gửi ảnh chụp màn hình HTKK CHÍNH CHỦ cho thấy:
# chọn Tỉnh Tây Ninh + Xã Đức Lập thì HTKK tự nhảy ra ĐÚNG mã 80115 (không
# phải 80113) — tức là HTKK tự suy Mã CQT từ Tỉnh/Thành + Xã/Phường, không
# chỉ dựa vào tên CQT suông. Người dùng gửi tiếp 2 file gốc HTKK
# (Catalogue_CQT_Dia_Ban.xml + Catalogue_CQThu_Dia_Ban.xml, nối qua khoá
# chung "MaXa") để dựng bảng Mã CQT <-> Xã/Phường, rồi so khớp tên xã có
# trong địa chỉ (API XInvoice trả về) với xã của từng mã ứng viên.
#
# Xác nhận qua xử lý THẬT 2 file người dùng gửi: mã 80115 có xã "Xã Đức
# Lập" trực thuộc, còn 80113 có các xã khác (Mỹ Quý, Đông Thành, Đức Huệ)
# — KHÔNG có "Xã Đức Lập" — nên so khớp địa chỉ sẽ chọn đúng 80115.


def extract_fn(name):
    try:
        idx = src.index('async def ' + name + '(')
    except ValueError:
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
        self.next_status = 200
        self.next_data = None

    def get(self, url, headers=None, timeout=None):
        return _FakeResp(self.next_status, self.next_data)


class _FakeSettings:
    def __init__(self):
        self.store = {"xinvoice_client_id": "demo", "xinvoice_api_key": "demo"}

    def get(self, key, default=""):
        return self.store.get(key, default)


class _FakeHTTPException(Exception):
    def __init__(self, status_code, detail):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


# ===== Thư mục templates/ giả lập — tập con nhỏ nhưng đúng NGUYÊN VĂN dữ
# liệu THẬT (Mã/xã) người dùng gửi, để test không phụ thuộc file thật cả
# ngàn dòng trong repo. =====
_tmp_dir = tempfile.mkdtemp()
os.makedirs(os.path.join(_tmp_dir, "templates"))
with open(os.path.join(_tmp_dir, "templates", "cqt_catalogue.txt"), "w", encoding="utf-8") as f:
    f.write(
        "80100###Thuế Tỉnh Tây Ninh\n"
        "80113###Thuế cơ sở 4 tỉnh Tây Ninh\n"
        "80115###Thuế cơ sở 4 tỉnh Tây Ninh\n"
    )
with open(os.path.join(_tmp_dir, "templates", "cqt_dia_ban.txt"), "w", encoding="utf-8") as f:
    f.write(
        "80113###Xã Mỹ Quý\n"
        "80113###Xã Đông Thành\n"
        "80113###Xã Đức Huệ\n"
        "80115###Xã Đức Lập\n"
    )

_tmp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
_tmp_db.close()


def _fresh_db():
    import sqlite3
    conn = sqlite3.connect(_tmp_db.name, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS cqt_ma_ten (
        ten_cqt TEXT PRIMARY KEY, ma_cqt TEXT, cap_nhat_at TEXT
    )""")
    return conn


ns = {
    'datetime': datetime, 'os': os, 'BASE_DIR': _tmp_dir,
    '_DANH_MUC_CQT': None, '_MA_CQT_THEO_XA': None,
}
ns['db'] = _fresh_db
ns['HTTPException'] = _FakeHTTPException
_fake_requests = _FakeRequests()
_fake_settings = _FakeSettings()
ns['requests'] = _fake_requests
ns['_get_setting'] = _fake_settings.get
exec(extract_fn('_khong_dau'), ns)
exec(extract_fn('_chuan_mst'), ns)
exec(extract_fn('_lay_danh_sach_xinvoice_keys'), ns)
exec(extract_fn('_tra_cuu_thong_tin_nnt'), ns)
exec(extract_fn('_lay_danh_muc_cqt'), ns)
exec(extract_fn('_lay_ma_cqt_theo_xa'), ns)
exec(extract_fn('_go_trung_ma_cqt_theo_dia_chi'), ns)
exec(extract_fn('tra_cuu_doanh_nghiep'), ns)
_lay_ma_cqt_theo_xa = ns['_lay_ma_cqt_theo_xa']
_go_trung_ma_cqt_theo_dia_chi = ns['_go_trung_ma_cqt_theo_dia_chi']
tra_cuu_doanh_nghiep = ns['tra_cuu_doanh_nghiep']

_conn0 = _fresh_db()
_conn0.execute("DELETE FROM cqt_ma_ten")
_conn0.commit()
_conn0.close()

# ===== Test 1: _lay_ma_cqt_theo_xa() đọc đúng danh sách xã cho từng mã. =====
bang_xa = _lay_ma_cqt_theo_xa()
assert bang_xa.get("80115") == ["Xã Đức Lập"], f"got {bang_xa.get('80115')}"
assert sorted(bang_xa.get("80113", [])) == ["Xã Mỹ Quý", "Xã Đông Thành", "Xã Đức Huệ"], \
    f"got {sorted(bang_xa.get('80113', []))}"
print("PASS 1: _lay_ma_cqt_theo_xa() đọc đúng danh sách xã/phường trực thuộc từng Mã CQT.")

# ===== Test 2 (QUAN TRỌNG — đúng ví dụ thật người dùng gửi ảnh chụp HTKK):
# địa chỉ có chứa TÊN XÃ của 1 mã ứng viên (Xã Đức Lập -> 80115), mã còn
# lại (80113) không khớp xã nào -> phải chọn ĐÚNG 80115. =====
ma = _go_trung_ma_cqt_theo_dia_chi(
    ["80113", "80115"], "Thửa Đất Số 1155, Tờ Bản Đồ Số 4, Ấp Đức Hạnh 1, Xã Đức Lập, Tây Ninh")
assert ma == "80115", f"got {ma}"
print("PASS 2: địa chỉ có tên xã của đúng 1 mã ứng viên -> gỡ trùng chọn ĐÚNG mã đó (80115, khớp ảnh "
      "chụp HTKK thật người dùng gửi).")

# ===== Test 3 (không hồi quy — an toàn): địa chỉ KHÔNG khớp tên xã nào
# trong các mã ứng viên -> để rỗng, không đoán bừa. =====
ma3 = _go_trung_ma_cqt_theo_dia_chi(["80113", "80115"], "Địa chỉ hoàn toàn không liên quan")
assert ma3 == "", f"got {ma3}"
print("PASS 3: địa chỉ không khớp xã nào -> để rỗng an toàn, không đoán bừa.")

# ===== Test 4 (không hồi quy — an toàn): không có địa chỉ -> để rỗng, không
# lỗi/crash. =====
ma4 = _go_trung_ma_cqt_theo_dia_chi(["80113", "80115"], "")
assert ma4 == "", f"got {ma4}"
print("PASS 4: không có địa chỉ -> để rỗng an toàn, không lỗi.")

# ===== Test 5 (QUAN TRỌNG — end-to-end đúng ca thật người dùng báo): công
# ty MỚI (MST 1102183121), Tên CQT bị trùng 2 mã, nhưng địa chỉ XInvoice
# trả về có tên xã "Xã Đức Lập" -> tra_cuu_doanh_nghiep() phải tự điền
# ĐÚNG Mã CQT 80115, đúng như HTKK chính chủ tự suy ra. =====
_fake_requests.next_data = {
    "name": "CÔNG TY TNHH THIÊN Ý VN",
    "address": "Thửa Đất Số 1155, Tờ Bản Đồ Số 4, Ấp Đức Hạnh 1, Xã Đức Lập, Tây Ninh",
    "taxDepartment": "Thuế cơ sở 4 tỉnh Tây Ninh", "status": "NNT đang hoạt động",
}
ket_qua5 = tra_cuu_doanh_nghiep("1102183121")
assert ket_qua5["ma_cqt"] == "80115", (
    f"Địa chỉ có tên xã 'Xã Đức Lập' (chỉ khớp mã 80115 trong 2 mã bị trùng tên) -> phải tự điền ĐÚNG "
    f"80115, đúng như HTKK chính chủ tự suy ra từ Tỉnh/Thành + Xã/Phường — got {ket_qua5}")
print("PASS 5: end-to-end tra_cuu_doanh_nghiep() tự điền ĐÚNG Mã CQT (80115) nhờ gỡ trùng theo địa chỉ "
      "— đúng ca thật người dùng báo, khớp ảnh chụp màn hình HTKK.")

# ===== Test 6 (không hồi quy — an toàn): Tên CQT bị trùng, địa chỉ KHÔNG
# chứa tên xã nào của các mã ứng viên -> vẫn để rỗng an toàn (không đoán
# bừa), như hành vi trước khi có tính năng gỡ trùng theo địa chỉ. =====
_fake_requests.next_data = {
    "name": "CÔNG TY KHÁC KHÔNG RÕ XÃ", "address": "Địa chỉ chung chung không có tên xã",
    "taxDepartment": "Thuế cơ sở 4 tỉnh Tây Ninh", "status": "NNT đang hoạt động",
}
ket_qua6 = tra_cuu_doanh_nghiep("0399999999")
assert ket_qua6["ma_cqt"] == "", f"got {ket_qua6}"
print("PASS 6: địa chỉ không xác định được xã -> vẫn để rỗng an toàn, không đoán bừa giữa 2 mã.")

os.unlink(_tmp_db.name)
print("\nALL DONE")
