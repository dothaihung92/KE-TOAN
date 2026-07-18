# -*- coding: utf-8 -*-
"""
CÔNG CỤ ADMIN — cấp phép + quản lý/theo dõi user. Các hàm trong file này
được server.py gọi lại để hiện màn "Quản lý user" NGAY TRONG PHẦN MỀM khi
chạy trên đúng máy admin (phát hiện qua sự tồn tại của admin_private_key.pem
— máy user bình thường không có file này nên màn admin sẽ không hiện).

CHỈ CHẠY ĐƯỢC TRÊN MÁY ADMIN — admin_private_key.pem KHÔNG BAO GIỜ commit
lên git (đã có trong .gitignore); lộ ra là bất kỳ ai cũng tự cấp được mã
kích hoạt giả cho chính họ.

Cách dùng (dòng lệnh — vẫn dùng được song song với màn "Quản lý user" trong
app, cùng đọc/ghi 1 dữ liệu):
  1) Lần đầu (chỉ 1 lần):  python cap_phep_admin.py --tao-khoa
     -> dán PUBLIC KEY HEX in ra vào PUBLIC_KEY_HEX trong license_core.py
        rồi commit license_core.py (không commit admin_private_key.pem).
  2) Cấp phép cho 1 user:  python cap_phep_admin.py
  3) Xem danh sách user đã cấp (theo dõi/quản lý):
     python cap_phep_admin.py --danh-sach
"""
import argparse
import base64
import datetime
import os
import sqlite3
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PRIVATE_KEY_PATH = os.path.join(BASE_DIR, "admin_private_key.pem")
LOG_DB_PATH = os.path.join(BASE_DIR, "admin_license_log.db")

sys.path.insert(0, BASE_DIR)
import license_core as lc  # noqa: E402


def la_may_admin() -> bool:
    """Máy hiện tại có phải máy admin không (có sẵn khoá riêng)."""
    return os.path.exists(PRIVATE_KEY_PATH)


def _log_db():
    conn = sqlite3.connect(LOG_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cap_phep (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hwid TEXT NOT NULL,
            so_dien_thoai TEXT,
            ghi_chu TEXT,
            so_ngay INTEGER,
            ngay_cap TEXT,
            ngay_het_han TEXT,
            la_dung_thu INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    return conn


def tao_khoa():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    if os.path.exists(PRIVATE_KEY_PATH):
        xac_nhan = input(
            f"⚠ File {PRIVATE_KEY_PATH} đã tồn tại. Tạo khoá mới sẽ làm MỌI mã kích "
            f"hoạt cũ đã cấp không còn dùng được nữa. Gõ 'CO' để xác nhận tạo lại: ")
        if xac_nhan.strip().upper() != "CO":
            print("Đã huỷ, giữ nguyên khoá cũ.")
            return
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    priv_bytes = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption())
    with open(PRIVATE_KEY_PATH, "wb") as f:
        f.write(priv_bytes)
    pub_bytes = pub.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw)
    print(f"[OK] Đã lưu khoá riêng (giữ kín, KHÔNG commit git): {PRIVATE_KEY_PATH}")
    print()
    print("Dán dòng dưới đây vào PUBLIC_KEY_HEX trong license_core.py rồi commit "
          "license_core.py (an toàn, đây là khoá CÔNG KHAI):")
    print()
    print(f'PUBLIC_KEY_HEX = "{pub_bytes.hex()}"')


def _doc_khoa_rieng():
    from cryptography.hazmat.primitives import serialization
    if not os.path.exists(PRIVATE_KEY_PATH):
        raise RuntimeError(
            f"Chưa có khoá riêng ({PRIVATE_KEY_PATH}). Chạy trước: "
            f"python cap_phep_admin.py --tao-khoa")
    with open(PRIVATE_KEY_PATH, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def lich_su_hwid(hwid):
    conn = _log_db()
    rows = conn.execute(
        "SELECT * FROM cap_phep WHERE hwid=? ORDER BY id DESC", (hwid,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def cap_phep(hwid, so_dien_thoai, so_ngay=None, vinh_vien=False, la_dung_thu=False, ghi_chu=""):
    """Ký + ghi log 1 lượt cấp phép. hwid PHẢI đúng 16 hex (chữ thường, khớp
    lay_hwid()). vinh_vien=True bỏ qua so_ngay, cấp không thời hạn.
    Trả (ma_kich_hoat_dep, ngay_het_han_iso)."""
    hwid = (hwid or "").strip().lower()
    if not hwid or len(hwid) != 16:
        raise ValueError("Mã máy (HWID) phải đúng 16 ký tự")
    priv = _doc_khoa_rieng()
    if vinh_vien:
        han_str = lc.NGAY_VINH_VIEN
        han_iso = datetime.date(9999, 12, 31).isoformat()
    else:
        so_ngay = int(so_ngay)
        han = datetime.date.today() + datetime.timedelta(days=so_ngay)
        han_str = han.strftime("%Y%m%d")
        han_iso = han.isoformat()
    payload = f"{hwid}|{han_str}".encode("utf-8")
    chu_ky = priv.sign(payload)
    ma_dep = lc.dinh_dang_ma(base64.b32encode(payload + chu_ky).decode("ascii").rstrip("="))

    conn = _log_db()
    conn.execute(
        "INSERT INTO cap_phep (hwid, so_dien_thoai, ghi_chu, so_ngay, ngay_cap, "
        "ngay_het_han, la_dung_thu) VALUES (?,?,?,?,?,?,?)",
        (hwid, so_dien_thoai, ghi_chu, (None if vinh_vien else so_ngay),
         datetime.date.today().isoformat(), han_iso, 1 if la_dung_thu else 0))
    conn.commit()
    conn.close()
    return ma_dep, han_iso


def danh_sach_du_lieu():
    """Danh sách tất cả lượt cấp phép (mới nhất mỗi HWID lên trước theo hạn
    dùng), kèm số ngày còn lại — dùng cho cả CLI --danh-sach và màn 'Quản
    lý user' trong app."""
    conn = _log_db()
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM cap_phep ORDER BY ngay_het_han ASC").fetchall()]
    conn.close()
    homnay = datetime.date.today()
    ra = []
    for r in rows:
        vv = lc.la_vinh_vien(r["ngay_het_han"])
        con_ngay = None if vv else (datetime.date.fromisoformat(r["ngay_het_han"]) - homnay).days
        r["vinh_vien"] = vv
        r["con_ngay"] = con_ngay
        ra.append(r)
    return ra


def cap_phep_moi():
    print("=== CẤP PHÉP SỬ DỤNG ===")
    hwid = input("Mã máy (HWID) user gửi qua Zalo: ").strip().lower()
    su = lich_su_hwid(hwid) if hwid and len(hwid) == 16 else []
    if su:
        print(f"\n⚠ Máy này ĐÃ được cấp {len(su)} lần trước:")
        for r in su:
            loai = "DÙNG THỬ" if r["la_dung_thu"] else "CHÍNH THỨC"
            print(f"   - {r['ngay_cap']}: {r['so_ngay'] or 'vĩnh viễn'} ngày ({loai}), "
                  f"hết hạn {r['ngay_het_han']}, SĐT {r['so_dien_thoai'] or '(không rõ)'}")
        if any(r["la_dung_thu"] for r in su):
            print("   -> Máy này ĐÃ dùng thử rồi — cân nhắc không cấp thêm bản dùng thử miễn phí nữa.")
        print()

    sdt = input("Số điện thoại đăng ký: ").strip()
    vinh_vien = input("Cấp VĨNH VIỄN, không cần gia hạn? (y/N): ").strip().lower() == "y"
    so_ngay = None
    if not vinh_vien:
        try:
            so_ngay = int(input("Số ngày cấp (vd 7 cho dùng thử, 365 cho 1 năm): ").strip())
        except ValueError:
            print("[LỖI] Số ngày phải là số nguyên.")
            return
    la_dung_thu = input("Đây là bản DÙNG THỬ? (y/N): ").strip().lower() == "y"
    ghi_chu = input("Ghi chú (tuỳ chọn): ").strip()

    try:
        ma_dep, han_iso = cap_phep(hwid, sdt, so_ngay, vinh_vien, la_dung_thu, ghi_chu)
    except (ValueError, RuntimeError) as e:
        print(f"[LỖI] {e}")
        return

    print()
    han_hien = "VĨNH VIỄN" if vinh_vien else datetime.date.fromisoformat(han_iso).strftime("%d/%m/%Y")
    print(f"[OK] Mã kích hoạt (hết hạn {han_hien}) — gửi lại cho user qua Zalo:")
    print()
    print(f"   {ma_dep}")
    print()


def danh_sach():
    rows = danh_sach_du_lieu()
    if not rows:
        print("Chưa cấp phép cho ai.")
        return
    print(f"{'HWID':<18}{'SĐT':<14}{'Ngày cấp':<12}{'Hết hạn':<18}{'Trạng thái':<20}{'Ghi chú'}")
    print("-" * 100)
    for r in rows:
        if r["vinh_vien"]:
            han_hien, tt = "VĨNH VIỄN", "Vĩnh viễn"
        else:
            han_hien = r["ngay_het_han"]
            cn = r["con_ngay"]
            tt = (f"HẾT HẠN {abs(cn)} ngày trước" if cn < 0 else
                  f"Sắp hết hạn ({cn} ngày)" if cn <= 7 else f"Còn hạn ({cn} ngày)")
        loai = " [thử]" if r["la_dung_thu"] else ""
        print(f"{r['hwid']:<18}{(r['so_dien_thoai'] or ''):<14}{r['ngay_cap']:<12}"
              f"{han_hien:<18}{tt:<20}{(r['ghi_chu'] or '')}{loai}")


def main():
    ap = argparse.ArgumentParser(description="Công cụ admin cấp phép + quản lý user")
    ap.add_argument("--tao-khoa", action="store_true", help="Tạo cặp khoá ký (chỉ chạy 1 lần)")
    ap.add_argument("--danh-sach", action="store_true", help="Xem danh sách user đã cấp phép")
    args = ap.parse_args()
    if args.tao_khoa:
        tao_khoa()
    elif args.danh_sach:
        danh_sach()
    else:
        cap_phep_moi()


if __name__ == "__main__":
    main()
