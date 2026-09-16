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
        self.token = None

    def get_captcha(self):
        self.so_lan_goi_captcha += 1
        return {"key": "k", "content": "<svg></svg>"}

    def login(self, username, password, cvalue, ckey):
        self.so_lan_goi_login += 1
        hanh_dong = self.ket_qua_login[self.so_lan_goi_login - 1]
        if hanh_dong is not None:
            raise hanh_dong
        return "fake-token"

    def set_token(self, token):
        self.token = token


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

_goi_browser_login = []
_ket_qua_browser_login = {"v": (False, None, {"tried": []})}


def _fake_gdt_browser_login(drv, username, password, so_lan=6, progress=None):
    _goi_browser_login.append({"drv": drv, "username": username, "password": password, "so_lan": so_lan})
    return _ket_qua_browser_login["v"]


ns['_gdt_browser_login'] = _fake_gdt_browser_login

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
# CỘNG THÊM nghỉ "đọc + gõ captcha" SAU khi giải xong captcha, TRƯỚC khi gửi
# đăng nhập (mỗi lần giải captcha thành công đều có, kể cả lần đầu) — sai
# captcha liên tục cả 3 lần (lỗi THƯỜNG, không phải bị chặn) -> phải thử ĐỦ
# cả 3 lần (không dừng sớm); tổng số lần nghỉ = 2 (khoảng cách giữa các lần
# thử, KHÔNG có trước lần đầu) + 3 (nghỉ đọc+gõ, có ở CẢ 3 lần vì lần nào
# cũng giải được captcha) = 5, mỗi lần nghỉ tối thiểu 0.8 giây (mức thấp
# nhất trong 2 loại nghỉ). =====
loi_sai_ma = Exception("Sai mã 'AB12': đăng nhập thất bại")
_client_hien_tai["c"] = _FakeClient([loi_sai_ma, loi_sai_ma, loi_sai_ma])
_fake_time.sleeps.clear()
ok2, msg2, so_lan_thu2, tried2 = _tu_dong_dang_nhap(2, so_lan=3)
assert ok2 is False
assert _client_hien_tai["c"].so_lan_goi_login == 3, (
    f"Lỗi sai captcha THƯỜNG (không phải bị chặn WAF) -> phải thử ĐỦ cả 3 lần như cấu hình — got "
    f"{_client_hien_tai['c'].so_lan_goi_login}")
assert len(_fake_time.sleeps) == 5, (
    f"Phải nghỉ ĐÚNG 5 lần (2 lần giữa các lượt thử [trước lần 2, trước lần 3] CỘNG 3 lần đọc+gõ "
    f"captcha [1 lần/lượt thử, cả 3 lượt đều giải được captcha]) — got {_fake_time.sleeps}")
assert all(s >= 0.8 for s in _fake_time.sleeps), (
    f"Mỗi lần nghỉ phải tối thiểu 0.8 giây (né hệ thống Thuế coi là hành vi bot do tần suất đăng nhập "
    f"bất thường VÀ tốc độ phản xạ 'siêu nhân') — got {_fake_time.sleeps}")
assert sum(1 for s in _fake_time.sleeps if s >= 1.2) == 2, (
    f"Trong đó phải có ĐÚNG 2 lần nghỉ >= 1.2s (khoảng cách GIỮA các lượt thử) — got {_fake_time.sleeps}")
print("PASS 2: lỗi sai captcha thường (không phải bị chặn) -> vẫn thử đủ số lần cấu hình, có nghỉ cả "
      "giữa các lượt thử (>=1.2s) LẪN sau khi giải captcha trước khi gửi đăng nhập (>=0.8s, mô phỏng "
      "thời gian đọc+gõ) để né bị coi là hành vi bot.")

# ===== Test 3 (không hồi quy): thành công ở lần thử thứ 2 -> trả về đúng
# kết quả thành công như hành vi cũ; tổng nghỉ = 1 (giữa lượt 1 và 2) + 2
# (đọc+gõ, cả 2 lượt đều giải được captcha) = 3. =====
_client_hien_tai["c"] = _FakeClient([loi_sai_ma, None])
_fake_time.sleeps.clear()
ok3, msg3, so_lan_thu3, tried3 = _tu_dong_dang_nhap(3, so_lan=5)
assert ok3 is True, f"Thành công ở lần 2 -> phải trả về ok=True — got {ok3}, msg={msg3}"
assert so_lan_thu3 == 2
assert len(_fake_time.sleeps) == 3, (
    f"Phải nghỉ đúng 3 lần (1 lần giữa lượt 1-2, cộng 2 lần đọc+gõ captcha ở cả 2 lượt) — got "
    f"{_fake_time.sleeps}")
assert _client_hien_tai["c"]._token_dead is False, "Đăng nhập thành công phải 'hồi sinh' client (_token_dead=False)"
print("PASS 3: đăng nhập thành công ở lần thử thứ 2 -> vẫn hoạt động đúng như trước (không hồi quy), "
      "có nghỉ đủ cả 2 loại (giữa lượt + đọc/gõ captcha).")

# ===== Test 4-6 (MỚI — đúng yêu cầu người dùng khẳng định lại: "không phải
# do đăng nhập nhanh mà do hệ thống thuế phát hiện đăng nhập qua phần mềm
# ... hãy xem có cách nào vào như người đăng nhập bình thường không"): khi
# HTTP thuần (GDTClient, dù đã giả lập kỹ) vẫn bị chặn hẳn, PHẢI tự động dự
# phòng bằng TRÌNH DUYỆT THẬT (_gdt_browser_login, chỉ khi có sẵn drv). =====

# Test 4 (QUAN TRỌNG): bị chặn hẳn qua HTTP (lỗi "hành vi không hợp lệ") +
# CÓ drv (trình duyệt ẩn thật) -> PHẢI tự động gọi _gdt_browser_login() dự
# phòng, và nếu nó THÀNH CÔNG thì trả về ok=True, gán đúng token vào client
# qua set_token() (không phải qua login() HTTP thường).
_client_hien_tai["c"] = _FakeClient([loi_waf])
_goi_browser_login.clear()
_ket_qua_browser_login["v"] = (True, "token-tu-trinh-duyet-that", {"so_lan": 2, "tried": ["AB", "CD"]})
_fake_time.sleeps.clear()
ok4, msg4, so_lan_thu4, tried4 = _tu_dong_dang_nhap(4, so_lan=5, drv="fake-driver")
assert ok4 is True, f"Trình duyệt thật đăng nhập được -> phải trả về ok=True — got {ok4}, msg={msg4}"
assert "trình duyệt thật" in msg4, f"Thông báo phải nêu rõ đã đăng nhập qua trình duyệt thật — got {msg4}"
assert len(_goi_browser_login) == 1, (
    f"Phải gọi ĐÚNG 1 lần _gdt_browser_login() dự phòng khi HTTP bị chặn hẳn và có sẵn drv — got "
    f"{len(_goi_browser_login)}")
assert _goi_browser_login[0]["drv"] == "fake-driver", "Phải truyền đúng drv đã có sẵn cho _gdt_browser_login()"
assert _goi_browser_login[0]["username"] == "0300000000", "Phải truyền đúng username (mst) cho _gdt_browser_login()"
assert _client_hien_tai["c"].token == "token-tu-trinh-duyet-that", (
    f"Token lấy được từ trình duyệt thật phải được gán vào client qua set_token() — got "
    f"{_client_hien_tai['c'].token}")
assert _client_hien_tai["c"]._token_dead is False
print("PASS 4: HTTP thuần bị chặn hẳn + có sẵn trình duyệt ẩn thật -> tự động dự phòng đăng nhập qua "
      "trình duyệt thật, thành công thì gán đúng token vào client — đúng yêu cầu người dùng 'xem có "
      "cách nào vào như người đăng nhập bình thường không'.")

# Test 5 (không hồi quy — QUAN TRỌNG): HTTP thuần THÀNH CÔNG ngay từ đầu ->
# TUYỆT ĐỐI KHÔNG được gọi _gdt_browser_login() dự phòng (lãng phí, mở
# trình duyệt thật tốn thời gian hơn hẳn — chỉ dùng khi HTTP thường thất
# bại), dù có sẵn drv đi nữa.
_client_hien_tai["c"] = _FakeClient([None])
_goi_browser_login.clear()
ok5, msg5, so_lan_thu5, tried5 = _tu_dong_dang_nhap(5, so_lan=5, drv="fake-driver")
assert ok5 is True
assert len(_goi_browser_login) == 0, (
    f"HTTP thuần đã thành công ngay từ lần đầu -> KHÔNG được gọi thêm _gdt_browser_login() dự phòng "
    f"(lãng phí, mở trình duyệt thật chậm hơn hẳn) — got {len(_goi_browser_login)} lượt gọi")
print("PASS 5: HTTP thuần đăng nhập thành công ngay -> không lãng phí gọi thêm trình duyệt thật dự "
      "phòng (chỉ dùng khi HTTP thường thất bại).")

# Test 6 (không hồi quy): HTTP thuần bị chặn hẳn + có drv, NHƯNG trình duyệt
# thật dự phòng CŨNG thất bại -> trả về ok=False, thông báo kèm cả lý do
# thất bại của trình duyệt thật (không chỉ lý do HTTP), không crash.
_client_hien_tai["c"] = _FakeClient([loi_waf])
_goi_browser_login.clear()
_ket_qua_browser_login["v"] = (False, None, {"so_lan": 6, "tried": ["AB", "CD", "EF"]})
ok6, msg6, so_lan_thu6, tried6 = _tu_dong_dang_nhap(6, so_lan=5, drv="fake-driver")
assert ok6 is False
assert len(_goi_browser_login) == 1
assert "Trình duyệt thật" in msg6 or "trình duyệt thật" in msg6, (
    f"Thông báo thất bại cuối cùng phải nêu rõ trình duyệt thật dự phòng CŨNG đã thất bại — got {msg6}")
print("PASS 6: HTTP thuần bị chặn hẳn VÀ trình duyệt thật dự phòng cũng thất bại -> trả về thất bại "
      "an toàn, thông báo nêu rõ cả 2 cách đã thử, không crash.")

print("\nALL DONE")
