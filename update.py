# -*- coding: utf-8 -*-
"""
Tu dong cap nhat phan mem tu GitHub (repo Public).
- Hoi GitHub commit moi nhat cua nhanh -> so voi .version tren may.
- Neu KHAC: tai cac file thay doi ve de (bo qua thu muc du lieu).
- Neu GIONG: khong tai gi.
- Khong bao gio lam treo phan mem: moi loi mang deu bo qua va chay tiep.

Tra ve exit code 10 neu start.bat bi thay doi (de start.bat tu khoi dong lai).
"""
import os, sys, json, ssl, urllib.request

OWNER  = "dothaihung92"
REPO   = "ke-toan"
BRANCH = "claude/invoice-retrieval-software-jidehw"

BASE     = os.path.dirname(os.path.abspath(__file__))
VER_FILE = os.path.join(BASE, ".version")
API = "https://api.github.com"
RAW = "https://raw.githubusercontent.com"

# Khong dung toi (du lieu nguoi dung / file cuc bo)
SKIP_PREFIX = ("data/", ".git/", "__pycache__/", ".github/")
SKIP_EXT    = (".db", ".pyc", ".sqlite")
SKIP_NAMES  = {".installed", ".version"}


def _get(url, raw=False, timeout=25):
    req = urllib.request.Request(url, headers={
        "User-Agent": "hddt-updater",
        "Accept": "application/vnd.github+json",
    })
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        data = r.read()
    return data if raw else json.loads(data.decode("utf-8"))


def latest_sha():
    j = _get(f"{API}/repos/{OWNER}/{REPO}/commits/{BRANCH}")
    return j["sha"]


def local_sha():
    try:
        with open(VER_FILE, encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def should_skip(path):
    p = path.replace("\\", "/")
    if any(p.startswith(s) for s in SKIP_PREFIX):
        return True
    if os.path.basename(p) in SKIP_NAMES:
        return True
    if p.lower().endswith(SKIP_EXT):
        return True
    return False


def main():
    try:
        sha = latest_sha()
    except Exception as e:
        print(f"[update] Khong kiem tra duoc cap nhat (chay tiep): {e}")
        return 0

    if sha and sha == local_sha():
        print("[update] Phan mem da la ban moi nhat.")
        return 0

    print("[update] Co ban moi - dang tai ve...")
    try:
        tree = _get(f"{API}/repos/{OWNER}/{REPO}/git/trees/{sha}?recursive=1")
        items = [t for t in tree.get("tree", []) if t.get("type") == "blob"]
    except Exception as e:
        print(f"[update] Khong lay duoc danh sach file (chay tiep): {e}")
        return 0

    n = 0
    startbat_changed = False
    for it in items:
        path = it["path"]
        if should_skip(path):
            continue
        url = f"{RAW}/{OWNER}/{REPO}/{BRANCH}/{path}"
        try:
            content = _get(url, raw=True)
        except Exception as e:
            print(f"[update]  (bo qua {path}: {e})")
            continue
        dest = os.path.join(BASE, path.replace("/", os.sep))
        # chi ghi khi noi dung khac (tranh ghi de vo ich)
        try:
            if os.path.exists(dest):
                with open(dest, "rb") as f:
                    if f.read() == content:
                        continue
        except Exception:
            pass
        try:
            d = os.path.dirname(dest)
            if d and not os.path.isdir(d):
                os.makedirs(d, exist_ok=True)
            with open(dest, "wb") as f:
                f.write(content)
            n += 1
            print(f"[update]  + {path}")
            if path.replace("\\", "/").lower() == "start.bat":
                startbat_changed = True
        except Exception as e:
            print(f"[update]  (khong ghi duoc {path}: {e})")

    try:
        with open(VER_FILE, "w", encoding="utf-8") as f:
            f.write(sha)
    except Exception:
        pass

    print(f"[update] Xong: da cap nhat {n} file.")
    return 10 if startbat_changed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"[update] Loi khong mong doi (chay tiep): {e}")
        sys.exit(0)
