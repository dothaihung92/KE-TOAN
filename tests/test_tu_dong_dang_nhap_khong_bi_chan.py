import os
import re

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test cho _tu_dong_dang_nhap() (server.py) — người dùng báo lỗi
# thật qua ảnh chụp màn hình: bấm "🤖 Tự đăng nhập" -> "Đăng nhập lỗi: Đăng
# nhập thất bại (403): {"status":403,"message":"Hệ thống phát hiện hành vi
# không hợp lệ. Yêu cầu đã bị chặn."}" — hệ thống Thuế (WAF) chặn do phát
# hiện HÀNH VI BOT: trước đây vòng lặp thử lại (tối đa 5-6 lần, cả ở
# doAutoLogin() phía frontend LẪN _tu_dong_dang_nhap() phía backend) bắn
# liên tiếp gần như TỨC THỜI (lấy captcha mới -> đăng nhập ngay, KHÔNG nghỉ
# giữa các lần thử), tần suất đăng nhập/giây bất thường so với người thật
# gõ tay -> bị hệ thống Thuế coi là bot và chặn hẳn.
#
# Sửa: (1) nghỉ ngẫu nhiên ~1.2-2.4s TRƯỚC mỗi lần thử lại (không nghỉ ở lần
# đầu); (2) khi đã BỊ CHẶN HẲN (lỗi chứa "hành vi không hợp lệ"/"đã bị
# chặn") thì DỪNG NGAY, không thử tiếp trong lúc đang bị chặn (vô ích, chỉ
# tổ kéo dài thời gian bị chặn).


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


class _FakeRow(dict):
    def __getitem__(self, k):
        return dict.get(self, k)


class _FakeConn:
    def __init__(self, row):
        self._row = row

    def execute(self, sql, params=None):
        return self

    def fetchone(self):
        return self._row

    def close(self):
        pass


class _FakeTime:
    def __init__(self):
        self.sleeps = []

    def sleep(self, s):
        self.sleeps.append(s)


class _FakeRandom:
    def random(self):
        return 0.0   # deterministic — thời gian nghỉ luôn đúng CẬN DƯỚI (1.2s)


class _FakeClient:
    def __init__(self, ket_qua_login):
        # ket_qua_login: list các hành động cho lần login thứ i (1-based):
        #   None -> thành công; Exception(...) -> ném lỗi đó
        self.ket_qua_login = ket_qua_login
        self.so_lan_goi_captcha = 0
        self.so_lan_goi_login = 0
        self._token_dead = True

    def get_captcha(self):
        self.so_lan_goi_captcha += 1
        return {"key": "k", "content": "<svg></svg>"}

    def login(self, username, password, cvalue, ckey):
        self.so_lan_goi_login += 1
        hanh_dong = self.ket_qua_login[self.so_lan_goi_login - 1]
        if hanh_dong is not None:
            raise hanh_dong
        return "fake-token"


ns = {}
_fake_time = _FakeTime()
_fake_random = _FakeRandom()
ns['time'] = _fake_time
ns['random'] = _fake_random
ns['_solve_captcha'] = lambda content, drv=None: "AB12"
_comp_row = _FakeRow({"password": "matkhau", "username": "", "mst": "0300000000"})
ns['db'] = lambda: _FakeConn(_comp_row)

_client_hien_tai = {"c": None}
ns['get_client'] = lambda cid: _client_hien_tai["c"]

exec(extract_fn('_tu_dong_dang_nhap'), ns)
_tu_dong_dang_nhap = ns['_tu_dong_dang_nhap']

# ===== Test 1 (QUAN TRỌNG — đúng ca thật người dùng gặp): hệ thống Thuế
# CHẶN HẲN ngay từ lần thử ĐẦU TIÊN (lỗi "Hệ thống phát hiện hành vi không
# hợp lệ. Yêu cầu đã bị chặn.") -> PHẢI dừng NGAY, KHÔNG thử tiếp các lần
# còn lại (thử tiếp trong lúc đang bị chặn chỉ vô ích, kéo dài thời gian bị
# chặn thêm). =====
loi_waf = Exception(
    'Đăng nhập thất bại (403): {"status":403,"message":"Hệ thống phát hiện hành vi không hợp lệ. '
    'Yêu cầu đã bị chặn."}')
_client_hien_tai["c"] = _FakeClient([loi_waf, None, None, None, None])
_fake_time.sleeps.clear()
ok, msg, so_lan_thu, tried = _tu_dong_dang_nhap(1, so_lan=5)
assert ok is False, f"Đã bị chặn WAF -> phải trả về thất bại — got ok={ok}"
assert _client_hien_tai["c"].so_lan_goi_login == 1, (
    f"Đã bị chặn ở lần 1 -> KHÔNG được thử đăng nhập thêm lần nào nữa (vô ích, chỉ tổ kéo dài thời "
    f"gian bị chặn) — got {_client_hien_tai['c'].so_lan_goi_login} lượt gọi login")
assert "TẠM CHẶN" in msg or "hành vi không hợp lệ" in msg, (
    f"Thông báo lỗi phải nêu rõ đã bị TẠM CHẶN (khác hẳn 'sai mã/lỗi thường') để người dùng biết cần "
    f"đợi thay vì thử lại ngay — got {msg}")
print("PASS 1: hệ thống Thuế chặn hẳn (lỗi 'hành vi không hợp lệ') -> dừng NGAY sau đúng 1 lần thử, "
      "không thử tiếp vô ích, thông báo rõ đã bị tạm chặn.")

# ===== Test 2: nghỉ ngẫu nhiên TRƯỚC mỗi lần thử lại (không nghỉ ở lần đầu)
# — sai captcha liên tục cả 3 lần (lỗi THƯỜNG, không phải bị chặn) -> phải
# thử ĐỦ cả 3 lần (không dừng sớm), và phải nghỉ ĐÚNG 2 lần (trước lần 2 và
# lần 3), mỗi lần nghỉ tối thiểu 1.2 giây. =====
loi_sai_ma = Exception("Sai mã 'AB12': đăng nhập thất bại")
_client_hien_tai["c"] = _FakeClient([loi_sai_ma, loi_sai_ma, loi_sai_ma])
_fake_time.sleeps.clear()
ok2, msg2, so_lan_thu2, tried2 = _tu_dong_dang_nhap(2, so_lan=3)
assert ok2 is False
assert _client_hien_tai["c"].so_lan_goi_login == 3, (
    f"Lỗi sai captcha THƯỜNG (không phải bị chặn WAF) -> phải thử ĐỦ cả 3 lần như cấu hình — got "
    f"{_client_hien_tai['c'].so_lan_goi_login}")
assert len(_fake_time.sleeps) == 2, (
    f"Phải nghỉ ĐÚNG 2 lần (trước lần thử thứ 2 và thứ 3, KHÔNG nghỉ trước lần đầu tiên) — got "
    f"{_fake_time.sleeps}")
assert all(s >= 1.2 for s in _fake_time.sleeps), (
    f"Mỗi lần nghỉ phải tối thiểu 1.2 giây (né hệ thống Thuế coi là hành vi bot do tần suất đăng nhập "
    f"bất thường) — got {_fake_time.sleeps}")
print("PASS 2: lỗi sai captcha thường (không phải bị chặn) -> vẫn thử đủ số lần cấu hình, có nghỉ "
      "đúng 2 lần (trước lần 2 và 3) mỗi lần tối thiểu 1.2s để né bị coi là hành vi bot.")

# ===== Test 3 (không hồi quy): thành công ở lần thử thứ 2 -> trả về đúng
# kết quả thành công như hành vi cũ, vẫn có nghỉ đúng 1 lần trước lần 2. =====
_client_hien_tai["c"] = _FakeClient([loi_sai_ma, None])
_fake_time.sleeps.clear()
ok3, msg3, so_lan_thu3, tried3 = _tu_dong_dang_nhap(3, so_lan=5)
assert ok3 is True, f"Thành công ở lần 2 -> phải trả về ok=True — got {ok3}, msg={msg3}"
assert so_lan_thu3 == 2
assert len(_fake_time.sleeps) == 1, f"Phải nghỉ đúng 1 lần (trước lần thử thứ 2) — got {_fake_time.sleeps}"
assert _client_hien_tai["c"]._token_dead is False, "Đăng nhập thành công phải 'hồi sinh' client (_token_dead=False)"
print("PASS 3: đăng nhập thành công ở lần thử thứ 2 -> vẫn hoạt động đúng như trước (không hồi quy), "
      "có nghỉ đúng 1 lần trước lần thử thứ 2.")

print("\nALL DONE")
