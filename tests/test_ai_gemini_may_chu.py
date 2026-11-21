import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server
from fastapi import HTTPException
# Khoá Gemini: lưu mã hoá trên máy, không trả lại trình duyệt, không lộ trong lỗi; lệnh gọi Gemini đi qua máy chủ (giả lập requests.post — KHÔNG gọi mạng thật).
server._AI_GEMINI_FILE = os.path.join(tempfile.mkdtemp(), "ai_gemini.json")
server.DATA_DIR = os.path.dirname(server._AI_GEMINI_FILE)
os.environ.pop("GEMINI_API_KEY", None)
KHOA = "AIzaSyDUMMYDUMMYDUMMYDUMMYDUMMYDUMMYabc"
assert server.ai_khoa_trang_thai()["co_khoa"] is False
for xau in ("", "abc", "AIza sai khoang trang " + "x" * 30):
    if xau:
        try: server.ai_khoa_luu({"key": xau}); assert False, xau
        except HTTPException as e: assert e.status_code == 400
r = server.ai_khoa_luu({"key": KHOA, "model": "gemini-2.5-flash"})
assert r["co_khoa"] and r["xem"] == "…" + KHOA[-4:] and KHOA not in str(r)
tt = server.ai_khoa_trang_thai(); assert tt["co_khoa"] and KHOA not in str(tt) and tt["model"] == "gemini-2.5-flash"
assert KHOA not in open(server._AI_GEMINI_FILE, encoding="utf-8").read() or os.name != "nt" and False, "khoá phải được mã hoá/che khi lưu"
assert server._ai_gemini_khoa() == KHOA
goi = {}
class R:
    status_code = 200
    def json(self): return {"candidates": [{"content": {"parts": [{"text": '[{"id":"a","chon":1}]'}]}}]}
def gia_post(url, json=None, headers=None, timeout=None):
    goi.update(url=url, body=json, headers=headers); return R()
server.requests.post = gia_post
kq = server.ai_gemini({"prompt": "xin chao", "system": "ban la ke toan"})
assert kq["text"] == '[{"id":"a","chon":1}]' and "gemini-2.5-flash:generateContent" in goi["url"]
assert KHOA not in goi["url"] and goi["headers"]["x-goog-api-key"] == KHOA, "khoá chỉ nằm trong header, không nằm trong URL"
assert goi["body"]["generationConfig"]["responseMimeType"] == "application/json" and goi["body"]["systemInstruction"]["parts"][0]["text"] == "ban la ke toan"
class R429:
    status_code = 429
    def json(self): return {"error": {"message": "quota " + KHOA}}
server.requests.post = lambda *a, **k: R429()
try: server.ai_gemini({"prompt": "x"}); assert False
except HTTPException as e: assert e.status_code == 502 and KHOA not in e.detail and "429" in e.detail, e.detail
try: server.ai_gemini({"prompt": " "}); assert False
except HTTPException as e: assert e.status_code == 400
server.ai_khoa_luu({"key": ""}); assert server.ai_khoa_trang_thai()["co_khoa"] is False
try: server.ai_gemini({"prompt": "x"}); assert False
except HTTPException as e: assert e.status_code == 400
print("PASS: khoá Gemini lưu mã hoá trên máy, không lộ ra trình duyệt/URL/lỗi; gọi Gemini qua máy chủ; xoá khoá được")
