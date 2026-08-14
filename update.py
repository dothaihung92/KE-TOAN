# -*- coding: utf-8 -*-
"""
Tu dong cap nhat phan mem tu GitHub (repo Public).
- Tai TUNG FILE trong danh sach FILES ben duoi qua raw.githubusercontent.com,
  so byte voi file dang co tren may -> KHAC thi ghi de, GIONG thi bo qua.
- Danh sach FILES la co dinh (khong doi ten file goc). Neu sau nay them file
  moi vao du an, phai them duong dan file do vao FILES ben duoi.
- CHI dung raw.githubusercontent.com (khong dung api.github.com) vi
  raw.githubusercontent.com la CDN phuc vu file tinh, KHONG bi gioi han
  "60 request/gio" ma api.github.com ap dung cho may khong dang nhap - tranh
  loi "403 rate limit exceeded" hay gap khi khoi dong nhieu lan lien tuc.
- Khong bao gio lam treo phan mem: moi loi mang deu bo qua va chay tiep.

Tra ve exit code 10 neu start.bat bi thay doi (de start.bat tu khoi dong lai).
"""
import os, sys, ssl, urllib.request

OWNER  = "dothaihung92"
REPO   = "ke-toan"
BRANCH = "claude/invoice-retrieval-software-jidehw"

BASE = os.path.dirname(os.path.abspath(__file__))
RAW  = "https://raw.githubusercontent.com"

# Cac file cua phan mem lay tu repo (KHONG gom du lieu nguoi dung: data/,
# *.db, .env...). Sua/them file moi vao day khi du an co file moi.
FILES = [
    "server.py",
    "update.py",
    "requirements.txt",
    "start.bat",
    "start.sh",
    ".gitattributes",
    "static/index.html",
    "static/doi_chieu_ngan_hang.html",
    "templates/htkk_01gtgt_template.xml",
    "templates/htkk_05tncn_template.xml",
    "license_core.py",
    "cap_phep_admin.py",
]

# raw.githubusercontent.com khong bi gioi han nhu api.github.com nen KHONG can
# cooldown de "tranh goi mang qua day" - truoc day co cooldown 180s khien
# nguoi dung tat/mo lai phan mem de kiem tra ban cap nhat (vd sau khi bao loi)
# trong vong 3 phut se bi BO QUA kiem tra, ngo la da chay ban moi nhung thuc
# te van dang chay ban CU -> gay nham lan kho chuan doan. Nay LUON kiem tra
# moi lan khoi dong cho chac chan.


def _tai_raw(path, timeout=20):
    url = f"{RAW}/{OWNER}/{REPO}/{BRANCH}/{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "hddt-updater"})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return r.read()


def main():
    n = 0
    loi = 0
    startbat_changed = False
    for path in FILES:
        try:
            content = _tai_raw(path)
        except Exception as e:
            print(f"[update]  (bo qua {path}: {e})")
            loi += 1
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
            if path.lower() == "start.bat":
                startbat_changed = True
        except Exception as e:
            print(f"[update]  (khong ghi duoc {path}: {e})")

    if n == 0 and loi == 0:
        print("[update] Phan mem da la ban moi nhat.")
    elif n == 0 and loi > 0:
        print(f"[update] Khong ket noi duoc GitHub ({loi} file) - chay tiep voi ban dang co san.")
    else:
        print(f"[update] Xong: da cap nhat {n} file.")
    return 10 if startbat_changed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"[update] Loi khong mong doi (chay tiep): {e}")
        sys.exit(0)
