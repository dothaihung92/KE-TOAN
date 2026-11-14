import random
import string
import sys

MST = sys.argv[1] if len(sys.argv) > 1 else "1102183121"

try:
    from curl_cffi import requests as _cffi
    s = _cffi.Session(impersonate="chrome")
    print("[*] Dung curl_cffi (impersonate=chrome)")
except Exception as e:
    import requests
    s = requests.Session()
    print(f"[*] KHONG co curl_cffi ({e}) -> dung requests thuong")

HEADERS = {
    "x-requested-with": "XMLHttpRequest",
    "accept": "application/json, text/javascript, */*; q=0.01",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "origin": "https://masothue.com",
    "referer": "https://masothue.com/",
    "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
}


def in_dam(tieu_de):
    print("\n" + "=" * 70)
    print(tieu_de)
    print("=" * 70)


def in_cookie_session(nhan):
    try:
        ten_cookie = list(s.cookies.keys())
    except Exception as e:
        ten_cookie = f"(khong doc duoc: {e})"
    print(f"    [cookie trong session sau {nhan}] {ten_cookie}")


# ===== Buoc 0: tai trang chu truoc, giong nhu trinh duyet that luon lam,
# de xem co set cookie PHPSESSID/c_code_name... gi khong. =====
in_dam("BUOC 0: GET https://masothue.com/  (tai trang chu truoc, nhu trinh duyet that)")
try:
    r0 = s.get("https://masothue.com/", headers={"user-agent": HEADERS["user-agent"]}, timeout=10)
    print(f"status = {r0.status_code}")
    print(f"response headers:")
    for k, v in r0.headers.items():
        print(f"    {k}: {v}")
    in_cookie_session("buoc 0")
except Exception as e:
    print(f"LOI: {e}")

# ===== Buoc 1: POST /Ajax/Token =====
in_dam("BUOC 1: POST /Ajax/Token")
r_ngau_nhien = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
print(f"data gui: r={r_ngau_nhien}")
try:
    r1 = s.post("https://masothue.com/Ajax/Token", headers=HEADERS,
                 data={"r": r_ngau_nhien}, timeout=10)
    print(f"status = {r1.status_code}")
    print("response headers:")
    for k, v in r1.headers.items():
        print(f"    {k}: {v}")
    print(f"body = {r1.text[:500]!r}")
    in_cookie_session("buoc 1")
    token = (r1.json() or {}).get("token") or ""
except Exception as e:
    print(f"LOI: {e}")
    token = ""

if not token:
    print("\n[!] Khong lay duoc token -> dung lai.")
    sys.exit(1)

# ===== Buoc 2: POST /Ajax/Search =====
in_dam("BUOC 2: POST /Ajax/Search")
print(f"data gui: q={MST}, type=auto, token={token}, force-search=1")
try:
    r2 = s.post("https://masothue.com/Ajax/Search", headers=HEADERS,
                 data={"q": MST, "type": "auto", "token": token, "force-search": "1"}, timeout=10)
    print(f"status = {r2.status_code}")
    print("response headers:")
    for k, v in r2.headers.items():
        print(f"    {k}: {v}")
    print(f"body = {r2.text[:500]!r}")
    in_cookie_session("buoc 2")
    duong_dan = (r2.json() or {}).get("url") or ""
except Exception as e:
    print(f"LOI: {e}")
    duong_dan = ""

in_dam("KET QUA")
if duong_dan and duong_dan != "/":
    print(f"[OK] url tra ve = {duong_dan}")
else:
    print(f"[FAIL] url rong/khong hop le = {duong_dan!r}")
