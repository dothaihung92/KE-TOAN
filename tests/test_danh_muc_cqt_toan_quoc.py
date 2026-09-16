import os
import json
import sqlite3
import tempfile
import datetime

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test cho tính năng tự động điền Mã CQT nơi nộp cho CẢ CÔNG TY
# HOÀN TOÀN MỚI (không cần đợi "học" từ công ty khác, không cần đã từng có
# file tờ khai cũ) — người dùng yêu cầu: "tôi muốn khi điền mst vào phần
# mềm sẽ tự dò ra các thông tin cty vì có những cty mới nên trong thư mục
# sẽ chưa có file". Nguồn dữ liệu: file danh mục CHÍNH CHỦ của phần mềm
# HTKK (D:\HTKK\InterfaceIni\Catalogue_CQT_Dia_Ban.xml) — người dùng tự
# trích xuất và gửi lại NGUYÊN VĂN các cặp Mã<->Tên cơ quan thuế (xác nhận
# qua thực tế: "70129" khớp đúng "Thuế cơ sở 14 Thành phố Hồ Chí Minh",
# đúng công ty MST 0313829148 đã xác nhận ở file tờ khai thật trước đó).
#
# QUAN TRỌNG: nhiều TÊN bị trùng ở NHIỀU Mã khác nhau (vd "Thuế cơ sở 7
# Thành phố Hồ Chí Minh" ứng với cả 70113 lẫn 70141 — dữ liệu THẬT rút ra
# từ Catalogue_CQT_Dia_Ban.xml) -> _lay_danh_muc_cqt() phải trả về DANH
# SÁCH các mã cho mỗi tên, và tra_cuu_doanh_nghiep() chỉ được tự điền khi
# danh sách có ĐÚNG 1 phần tử — không được đoán bừa giữa nhiều mã.


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


# ===== Thư mục data/ giả lập, chứa 1 tập con NHỎ nhưng đúng NGUYÊN VĂN dữ
# liệu THẬT người dùng gửi (để test không phụ thuộc/không cần đọc lại toàn
# bộ file thật hàng trăm dòng trong repo). =====
_tmp_dir = tempfile.mkdtemp()
os.makedirs(os.path.join(_tmp_dir, "templates"))
with open(os.path.join(_tmp_dir, "templates", "cqt_catalogue.txt"), "w", encoding="utf-8") as f:
    f.write(
        "70100###Thuế Thành phố Hồ Chí Minh\n"
        "70113###Thuế cơ sở 7 Thành phố Hồ Chí Minh\n"
        "70129###Thuế cơ sở 14 Thành phố Hồ Chí Minh\n"
        "70141###Thuế cơ sở 7 Thành phố Hồ Chí Minh\n"
    )

_tmp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
_tmp_db.close()


def _fresh_db():
    conn = sqlite3.connect(_tmp_db.name, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS cqt_ma_ten (
        ten_cqt TEXT PRIMARY KEY, ma_cqt TEXT, cap_nhat_at TEXT
    )""")
    return conn


ns = {'datetime': datetime, 'os': os, 'BASE_DIR': _tmp_dir, '_DANH_MUC_CQT': None}
ns['db'] = _fresh_db
ns['HTTPException'] = _FakeHTTPException
_fake_requests = _FakeRequests()
_fake_settings = _FakeSettings()
ns['requests'] = _fake_requests
ns['_get_setting'] = _fake_settings.get
# tra_cuu_doanh_nghiep() giờ còn gỡ trùng Mã CQT theo Xã/Phường trong địa
# chỉ (_go_trung_ma_cqt_theo_dia_chi, xem test_go_trung_ma_cqt_theo_dia_chi.py)
# — thư mục templates/ giả lập ở đây KHÔNG có cqt_dia_ban.txt nên hàm đó
# luôn trả {} an toàn, giữ đúng kỳ vọng "để rỗng khi không gỡ được" của
# các test trong file này (chỉ kiểm tra riêng phần danh mục toàn quốc).
ns['_MA_CQT_THEO_XA'] = None
exec(extract_fn('_khong_dau'), ns)
exec(extract_fn('_chuan_mst'), ns)
exec(extract_fn('_lay_danh_sach_xinvoice_keys'), ns)
exec(extract_fn('_tra_cuu_thong_tin_nnt'), ns)
exec(extract_fn('_lay_danh_muc_cqt'), ns)
exec(extract_fn('_lay_ma_cqt_theo_xa'), ns)
exec(extract_fn('_go_trung_ma_cqt_theo_dia_chi'), ns)
exec(extract_fn('tra_cuu_doanh_nghiep'), ns)
_lay_danh_muc_cqt = ns['_lay_danh_muc_cqt']
tra_cuu_doanh_nghiep = ns['tra_cuu_doanh_nghiep']

_conn0 = _fresh_db()
_conn0.execute("DELETE FROM cqt_ma_ten")
_conn0.commit()
_conn0.close()

# ===== Test 1 (QUAN TRỌNG — đúng dữ liệu THẬT xác nhận qua file tờ khai
# 0313829148 trước đó): tên KHÔNG bị trùng -> trả về danh sách ĐÚNG 1 mã. =====
danh_muc = _lay_danh_muc_cqt()
assert danh_muc.get("Thuế cơ sở 14 Thành phố Hồ Chí Minh") == ["70129"], (
    f"got {danh_muc.get('Thuế cơ sở 14 Thành phố Hồ Chí Minh')}")
print("PASS 1: _lay_danh_muc_cqt() trả đúng 1 mã duy nhất (70129) cho tên không bị trùng.")

# ===== Test 2 (không hồi quy — QUAN TRỌNG): tên BỊ TRÙNG ở nhiều mã (dữ
# liệu thật: "Thuế cơ sở 7 Thành phố Hồ Chí Minh" ứng với cả 70113 và
# 70141) -> phải trả về ĐỦ CẢ 2 mã, không được chỉ giữ 1 mã ngẫu nhiên. =====
cac_ma_trung = danh_muc.get("Thuế cơ sở 7 Thành phố Hồ Chí Minh")
assert sorted(cac_ma_trung) == ["70113", "70141"], f"got {cac_ma_trung}"
print("PASS 2: tên bị trùng nhiều mã -> _lay_danh_muc_cqt() trả về ĐỦ danh sách, không bỏ sót.")

# ===== Test 3 (QUAN TRỌNG — đúng kịch bản người dùng yêu cầu: CÔNG TY HOÀN
# TOÀN MỚI, CHƯA từng có công ty nào cùng cơ quan thuế được nhập trước đó
# (bảng cqt_ma_ten rỗng) -> vẫn PHẢI tự điền được Mã CQT, không cần đợi
# "học" dần, MIỄN LÀ tên không bị trùng. =====
_fake_requests.next_data = {
    "name": "CÔNG TY HOÀN TOÀN MỚI CHƯA TỪNG NỘP", "address": "địa chỉ mới",
    "taxDepartment": "Thuế cơ sở 14 Thành phố Hồ Chí Minh", "status": "NNT đang hoạt động",
}
ket_qua3 = tra_cuu_doanh_nghiep("0399999999")
assert ket_qua3["ma_cqt"] == "70129", (
    f"Công ty MỚI (chưa 'học' được từ công ty khác) vẫn phải tự điền đúng Mã CQT nhờ danh mục toàn "
    f"quốc, vì tên cơ quan thuế này không bị trùng mã — got {ket_qua3}")
print("PASS 3: công ty HOÀN TOÀN MỚI (bảng học cqt_ma_ten rỗng) vẫn tự điền đúng Mã CQT nhờ danh mục "
      "toàn quốc — đúng yêu cầu người dùng.")

# ===== Test 4 (không hồi quy — an toàn, không đoán bừa): tên ứng với
# NHIỀU mã (70113/70141) và CHƯA từng được "học" -> ma_cqt phải để RỖNG,
# không tự ý chọn đại 1 trong 2 mã (có thể sai, gây lỗi khi nộp tờ khai). =====
_fake_requests.next_data = {
    "name": "CÔNG TY Ở CƠ QUAN THUẾ CÓ TÊN BỊ TRÙNG MÃ", "address": "địa chỉ khác",
    "taxDepartment": "Thuế cơ sở 7 Thành phố Hồ Chí Minh", "status": "NNT đang hoạt động",
}
ket_qua4 = tra_cuu_doanh_nghiep("0388888888")
assert ket_qua4["ma_cqt"] == "", (
    f"Tên bị trùng nhiều mã, CHƯA từng 'học' -> phải để rỗng an toàn, không đoán bừa — got {ket_qua4}")
print("PASS 4: tên cơ quan thuế bị trùng nhiều mã (chưa từng 'học') -> để rỗng an toàn, không đoán bừa.")

# ===== Test 5 (không hồi quy): bảng cqt_ma_ten đã "học" (người dùng tự xác
# nhận trước đó) PHẢI được ưu tiên hơn danh mục toàn quốc, kể cả khi danh
# mục có nhiều mã cho tên đó (vd người dùng đã xác nhận đúng 70141 cho tên
# bị trùng ở Test 4). =====
conn5 = _fresh_db()
conn5.execute(
    "INSERT INTO cqt_ma_ten(ten_cqt, ma_cqt, cap_nhat_at) VALUES(?,?,?)",
    ("Thuế cơ sở 7 Thành phố Hồ Chí Minh", "70141", datetime.datetime.now().isoformat()))
conn5.commit()
conn5.close()
ket_qua5 = tra_cuu_doanh_nghiep("0377777777")
assert ket_qua5["ma_cqt"] == "70141", (
    f"Bảng đã 'học' (người dùng tự xác nhận) phải được ƯU TIÊN hơn danh mục toàn quốc — got {ket_qua5}")
print("PASS 5: bảng cqt_ma_ten đã 'học' (người dùng tự xác nhận) được ưu tiên hơn danh mục toàn quốc.")

os.unlink(_tmp_db.name)
print("\nALL DONE")
