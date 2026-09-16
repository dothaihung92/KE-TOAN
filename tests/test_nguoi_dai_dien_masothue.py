import os
import re as _re_module

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(_REPO_ROOT, 'server.py'), encoding='utf-8').read()

# Regression test cho tính năng tra "Người đại diện" trên masothue.com để
# gợi ý điền "Tên người ký tờ khai" (_lay_ten_nguoi_dai_dien_masothue) —
# người dùng yêu cầu vì API XInvoice không có trường này. Người dùng tự
# bắt (DevTools) đúng luồng 3 bước THẬT trang masothue.com dùng khi tìm
# kiếm theo MST:
#
# LƯU Ý: sau khi build .277 KHÔNG hoạt động ở môi trường thật (dù test cũ
# pass), đổi sang tạo session qua curl_cffi.impersonate("chrome") — giống
# hệt GDTClient dùng cho trang Thuế bị WAF chặn theo TLS/JA3 — vì
# masothue.com chạy sau Cloudflare (endpoint cdn-cgi/rum thấy trong log
# DevTools người dùng gửi), nghi vấn requests thuần bị Cloudflare âm thầm
# chặn/trả khác do vân tay TLS không giống trình duyệt thật. Việc tạo
# session được tách riêng thành _tao_session_masothue() để test giả lập
# được (không phụ thuộc curl_cffi có cài trong máy chạy test hay không).
#   1) POST /Ajax/Token   -> {"success":1,"token":"24quXCbivJ"}  (token
#      phiên đơn giản, lấy tự do — KHÔNG phải thử thách chống bot phức
#      tạp cần giải mã, khác hẳn WAF F5 Bot Defense của trang Thuế trước
#      đó nên không vi phạm nguyên tắc đã từ chối trước đây trong phiên).
#   2) POST /Ajax/Search  (q=<mst>, type=auto, token=<token trên>,
#      force-search=1) -> {"success":1,"url":"/1102183121-cong-ty-tnhh-
#      thien-y-vn",...}
#   3) GET https://masothue.com<url> -> trang chi tiết, đọc tên trong
#      khối <tr itemprop='alumni' itemscope itemtype='.../Person'>...
#      <span itemprop='name'><a ...>TÊN</a></span>...</tr> — ĐÚNG NGUYÊN
#      VĂN cấu trúc HTML thật người dùng gửi cho MST 1102183121 (kết quả
#      thật: "HÀ MINH VŨ").
#
# QUAN TRỌNG: trang này còn liệt kê "Người đại diện" của các công ty KHÁC
# gần đó ở cuối trang (dạng <em><a>...TÊN...</a></em>, KHÔNG có
# itemprop='alumni') — hàm phải CHỈ lấy đúng khối công ty đang tra, không
# lấy nhầm các khối phụ đó.


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


# ===== HTML THẬT (rút gọn, giữ NGUYÊN VĂN 2 khối quan trọng) người dùng
# đã gửi cho MST 1102183121: khối "alumni" của ĐÚNG công ty đang tra, và
# 1 khối "Người đại diện" của công ty KHÁC (phải bị bỏ qua). =====
_HTML_THAT = """
<html><body>
<table>
<tr><td>Mã số thuế</td><td>1102183121</td></tr>
<tr itemprop='alumni' itemscope itemtype='http://schema.org/Person'>
        <td><i class='fa fa-user'></i> Người đại diện</td>
        <td><span itemprop='name'><a href='https://masothue.com/Search/?q=H%C3%80+MINH+V%C5%A8&type=legalName' title="tra cứu mã số thuế công ty có giám đốc HÀ MINH VŨ">HÀ MINH VŨ</a></span> </td>
    </tr>
</table>
<hr />
<div>
    <i class='fa fa-hashtag'></i> Mã số thuế: <a href='/1102184710-cong-ty-tnhh-tmdv-tu-van-thuy-duong' title='Tra cứu mã số thuế 1102184710'>1102184710</a><br />
    <i class='fa fa-user'></i> Người đại diện: <em><a href='https://masothue.com/Search/?q=H%E1%BB%92+V%C4%82N+S%C6%A0N&type=legalName' title='Tra cứu mã số thuế công ty có giám đốc HỒ VĂN SƠN'>HỒ VĂN SƠN</a></em>
</div>
</body></html>
"""


class _FakeResp:
    def __init__(self, status_code, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data
        self.text = text

    def json(self):
        return self._json


class _FakeSession:
    def __init__(self, plan):
        self.headers = {}
        self.calls = []
        self._plan = list(plan)

    def post(self, url, headers=None, data=None, timeout=None):
        self.calls.append({"method": "POST", "url": url, "headers": headers, "data": data})
        return self._plan.pop(0)

    def get(self, url, headers=None, timeout=None):
        self.calls.append({"method": "GET", "url": url, "headers": headers})
        return self._plan.pop(0)


class _FakeTaoSessionMasothue:
    """Giả lập _tao_session_masothue() — trả session giả đã xếp sẵn kịch
    bản thay vì gọi curl_cffi/requests thật, để test không phụ thuộc việc
    máy chạy test có cài curl_cffi hay không và không gọi mạng."""
    def __init__(self):
        self._next = None

    def dat_session_ke_tiep(self, sess, dung_tls_chrome=True):
        self._next = (sess, dung_tls_chrome)

    def __call__(self):
        return self._next


ns = {
    '_MASOTHUE_UA': ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
}
_fake_tao_session = _FakeTaoSessionMasothue()
ns['_tao_session_masothue'] = _fake_tao_session
exec(extract_fn('_khong_dau'), ns)
exec(extract_fn('_chuan_mst'), ns)
exec(extract_fn('_lay_ten_nguoi_dai_dien_masothue'), ns)
_lay_ten_nguoi_dai_dien_masothue = ns['_lay_ten_nguoi_dai_dien_masothue']

# ===== Test 1 (QUAN TRỌNG — đúng luồng thật + HTML thật người dùng gửi):
# 3 bước Token -> Search -> GET trang chi tiết, trích ĐÚNG "HÀ MINH VŨ" từ
# khối alumni, KHÔNG lấy nhầm "HỒ VĂN SƠN" của công ty khác trên cùng
# trang. =====
sess1 = _FakeSession([
    _FakeResp(200, json_data={"success": 1, "token": "24quXCbivJ"}),
    _FakeResp(200, json_data={"success": 1, "url": "/1102183121-cong-ty-tnhh-thien-y-vn", "numRows": 1}),
    _FakeResp(200, text=_HTML_THAT),
])
_fake_tao_session.dat_session_ke_tiep(sess1)
ket_qua1 = _lay_ten_nguoi_dai_dien_masothue("1102183121")
assert ket_qua1 == "HÀ MINH VŨ", f"got {ket_qua1!r}"
assert sess1.calls[0]["url"] == "https://masothue.com/Ajax/Token"
assert sess1.calls[1]["url"] == "https://masothue.com/Ajax/Search"
assert sess1.calls[1]["data"]["token"] == "24quXCbivJ", f"got {sess1.calls[1]['data']}"
assert sess1.calls[2]["url"] == "https://masothue.com/1102183121-cong-ty-tnhh-thien-y-vn"
# ===== Đúng ĐÚNG hình dạng tham số "r" của /Ajax/Token khớp request thật
# (Copy as cURL từ DevTools: "r=bc36lo" — 6 ký tự chữ thường+số) — trước
# đó dùng uuid hex 8 ký tự (khác hẳn hình dạng thật), nghi là nguyên nhân
# /Ajax/Search trả kết quả RỖNG dù không báo lỗi gì. =====
r_gui = sess1.calls[0]["data"]["r"]
assert _re_module.fullmatch(r"[a-z0-9]{6}", r_gui), (
    f"Tham số 'r' gửi /Ajax/Token phải có hình dạng 6 ký tự chữ thường+số, đúng như request thật "
    f"(vd 'bc36lo') — got {r_gui!r}")
# ===== Các header Content-Type/Client-Hints/Fetch-Metadata mà request
# thật (Copy as cURL) có nhưng code cũ chưa gửi — thêm vào cho giống 1
# request bình thường từ trình duyệt thật. =====
for h in ("content-type", "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform",
          "sec-fetch-dest", "sec-fetch-mode", "sec-fetch-site"):
    assert h in sess1.calls[0]["headers"], f"Thiếu header '{h}' (có trong request thật) — got {sess1.calls[0]['headers']}"
print("PASS 1: đúng luồng 3 bước Token->Search->GET (đúng dữ liệu thật MST 1102183121), trích ĐÚNG "
      "'HÀ MINH VŨ' từ khối alumni của công ty đang tra, không lấy nhầm 'HỒ VĂN SƠN' của công ty khác "
      "liệt kê thêm trên cùng trang.")

# ===== Test 2 (không hồi quy): MST không hợp lệ -> trả '', KHÔNG gọi
# mạng. =====
sess2 = _FakeSession([])
_fake_tao_session.dat_session_ke_tiep(sess2)
ket_qua2 = _lay_ten_nguoi_dai_dien_masothue("123")
assert ket_qua2 == "", f"got {ket_qua2!r}"
assert sess2.calls == [], f"MST không hợp lệ không được gọi mạng — got {sess2.calls}"
print("PASS 2: MST không hợp lệ -> trả '' an toàn, không gọi mạng.")

# ===== Test 3 (không hồi quy — an toàn): /Ajax/Token lỗi/không trả token
# -> trả '' an toàn, không lỗi/crash, không gọi tiếp Search/GET. =====
sess3 = _FakeSession([_FakeResp(200, json_data={"success": 0})])
_fake_tao_session.dat_session_ke_tiep(sess3)
ket_qua3 = _lay_ten_nguoi_dai_dien_masothue("1102183121")
assert ket_qua3 == "", f"got {ket_qua3!r}"
assert len(sess3.calls) == 1, f"Không có token -> không được gọi tiếp Search/GET — got {sess3.calls}"
print("PASS 3: /Ajax/Token không trả token -> dừng lại an toàn, trả '', không gọi tiếp.")

# ===== Test 4 (không hồi quy — an toàn): /Ajax/Search trả URL không chứa
# đúng MST đang tra (kết quả không khớp) -> trả '' an toàn, không lấy
# nhầm thông tin công ty khác. =====
sess4 = _FakeSession([
    _FakeResp(200, json_data={"success": 1, "token": "abc"}),
    _FakeResp(200, json_data={"success": 1, "url": "/9999999999-cong-ty-khac", "numRows": 1}),
])
_fake_tao_session.dat_session_ke_tiep(sess4)
ket_qua4 = _lay_ten_nguoi_dai_dien_masothue("1102183121")
assert ket_qua4 == "", f"got {ket_qua4!r}"
assert len(sess4.calls) == 2, f"URL không khớp MST -> không được tải tiếp trang chi tiết — got {sess4.calls}"
print("PASS 4: /Ajax/Search trả URL không khớp đúng MST đang tra -> trả '' an toàn, không lấy nhầm "
      "công ty khác.")

# ===== Test 5 (không hồi quy — an toàn): trang chi tiết không có khối
# 'alumni' (vd công ty không công khai người đại diện) -> trả '' an toàn.
# =====
sess5 = _FakeSession([
    _FakeResp(200, json_data={"success": 1, "token": "abc"}),
    _FakeResp(200, json_data={"success": 1, "url": "/1102183121-cong-ty-khong-co-nguoi-dai-dien"}),
    _FakeResp(200, text="<html><body>Không có thông tin người đại diện</body></html>"),
])
_fake_tao_session.dat_session_ke_tiep(sess5)
ket_qua5 = _lay_ten_nguoi_dai_dien_masothue("1102183121")
assert ket_qua5 == "", f"got {ket_qua5!r}"
print("PASS 5: trang chi tiết không có khối 'alumni' -> trả '' an toàn, không lỗi.")

print("\nALL DONE")
