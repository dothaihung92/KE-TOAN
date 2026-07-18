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
import os, sys, ssl, time, urllib.request

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
    "templates/htkk_01gtgt_template.xml",
    "license_core.py",
    "cap_phep_admin.py",
]

# raw.githubusercontent.com khong bi gioi han nhu api.github.com, nhung van
# dat cooldown de tranh goi mang qua day khi khoi dong lai lien tuc (vd dang
# thu nghiem) - chi kiem tra cap nhat toi da 1 lan / khoang thoi gian duoi day.
CHECK_COOLDOWN_SEC = 180
LAST_CHECK_FILE = os.path.join(BASE, ".last_update_check")


def _da_kiem_tra_gan_day():
    try:
        with open(LAST_CHECK_FILE, encoding="utf-8") as f:
            t = float(f.read().strip())
        return (time.time() - t) < CHECK_COOLDOWN_SEC
    except Exception:
        return False


def _danh_dau_da_kiem_tra():
    try:
        with open(LAST_CHECK_FILE, "w", encoding="utf-8") as f:
            f.write(str(time.time()))
    except Exception:
        pass


def _tai_raw(path, timeout=20):
    url = f"{RAW}/{OWNER}/{REPO}/{BRANCH}/{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "hddt-updater"})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return r.read()


def _thieu_file_can_thiet():
    """True nếu có file trong FILES chưa từng tồn tại trên máy này — dùng để
    BỎ QUA cooldown, ép kiểm tra ngay. Tránh lặp lại lỗi 'file mới thêm vào
    FILES nhưng máy user kẹt ở cooldown nên mãi không tải về được, dẫn tới
    server.py crash vì import module chưa từng có trên đĩa'."""
    for path in FILES:
        if not os.path.exists(os.path.join(BASE, path.replace("/", os.sep))):
            return True
    return False


def main():
    if not _thieu_file_can_thiet() and _da_kiem_tra_gan_day():
        print("[update] Vua kiem tra gan day - bo qua lan nay, chay thang voi ban dang co san.")
        return 0
    _danh_dau_da_kiem_tra()

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
