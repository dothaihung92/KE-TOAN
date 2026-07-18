# -*- coding: utf-8 -*-
"""
CÔNG CỤ ADMIN — cấp phép + quản lý/theo dõi user. CHỈ CHẠY TRÊN MÁY ADMIN,
KHÔNG BAO GIỜ commit lên git / đưa vào danh sách tự cập nhật (update.py) —
file admin_private_key.pem sinh ra ở bước --tao-khoa PHẢI giữ riêng, lộ ra
là bất kỳ ai cũng tự cấp được mã kích hoạt giả cho chính họ.

Cách dùng:
  1) Lần đầu (chỉ 1 lần):  python cap_phep_admin.py --tao-khoa
     -> dán PUBLIC KEY HEX in ra vào PUBLIC_KEY_HEX trong license_core.py
        rồi commit license_core.py (không commit admin_private_key.pem).
  2) Cấp phép cho 1 user:  python cap_phep_admin.py
     -> nhập Mã máy (HWID) + SĐT user gửi qua Zalo, số ngày cấp, phần mềm
        tự tạo mã kích hoạt để gửi lại cho user qua Zalo.
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
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    if not os.path.exists(PRIVATE_KEY_PATH):
        print(f"[LỖI] Chưa có khoá riêng ({PRIVATE_KEY_PATH}). Chạy trước: "
              f"python cap_phep_admin.py --tao-khoa")
        sys.exit(1)
    with open(PRIVATE_KEY_PATH, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def _lich_su_hwid(conn, hwid):
    return conn.execute(
        "SELECT * FROM cap_phep WHERE hwid=? ORDER BY id DESC", (hwid,)).fetchall()


def cap_phep_moi():
    priv = _doc_khoa_rieng()
    conn = _log_db()
    print("=== CẤP PHÉP SỬ DỤNG ===")
    hwid = input("Mã máy (HWID) user gửi qua Zalo: ").strip().lower()
    if not hwid or len(hwid) != 16:
        print("[LỖI] Mã máy phải đúng 16 ký tự (copy y nguyên từ màn hình 'Kích hoạt' của user).")
        return
    su = _lich_su_hwid(conn, hwid)
    if su:
        print(f"\n⚠ Máy này ĐÃ được cấp {len(su)} lần trước:")
        for r in su:
            loai = "DÙNG THỬ" if r["la_dung_thu"] else "CHÍNH THỨC"
            print(f"   - {r['ngay_cap']}: {r['so_ngay']} ngày ({loai}), hết hạn {r['ngay_het_han']}, "
                  f"SĐT {r['so_dien_thoai'] or '(không rõ)'}")
        if any(r["la_dung_thu"] for r in su):
            print("   -> Máy này ĐÃ dùng thử rồi — cân nhắc không cấp thêm bản dùng thử miễn phí nữa.")
        print()

    sdt = input("Số điện thoại đăng ký: ").strip()
    try:
        so_ngay = int(input("Số ngày cấp (vd 7 cho dùng thử, 365 cho 1 năm): ").strip())
    except ValueError:
        print("[LỖI] Số ngày phải là số nguyên.")
        return
    la_dung_thu = input("Đây là bản DÙNG THỬ? (y/N): ").strip().lower() == "y"
    ghi_chu = input("Ghi chú (tuỳ chọn): ").strip()

    han = datetime.date.today() + datetime.timedelta(days=so_ngay)
    payload = f"{hwid}|{han.strftime('%Y%m%d')}".encode("utf-8")
    chu_ky = priv.sign(payload)
    ma_kich_hoat = base64.b32encode(payload + chu_ky).decode("ascii").rstrip("=")
    ma_dep = lc.dinh_dang_ma(ma_kich_hoat)

    conn.execute(
        "INSERT INTO cap_phep (hwid, so_dien_thoai, ghi_chu, so_ngay, ngay_cap, "
        "ngay_het_han, la_dung_thu) VALUES (?,?,?,?,?,?,?)",
        (hwid, sdt, ghi_chu, so_ngay, datetime.date.today().isoformat(),
         han.isoformat(), 1 if la_dung_thu else 0))
    conn.commit()
    conn.close()

    print()
    print(f"[OK] Mã kích hoạt (hết hạn {han.strftime('%d/%m/%Y')}) — gửi lại cho user qua Zalo:")
    print()
    print(f"   {ma_dep}")
    print()


def danh_sach():
    conn = _log_db()
    rows = conn.execute("SELECT * FROM cap_phep ORDER BY ngay_het_han ASC").fetchall()
    conn.close()
    if not rows:
        print("Chưa cấp phép cho ai.")
        return
    homnay = datetime.date.today()
    print(f"{'HWID':<18}{'SĐT':<14}{'Ngày cấp':<12}{'Hết hạn':<12}{'Trạng thái':<20}{'Ghi chú'}")
    print("-" * 100)
    for r in rows:
        han = datetime.date.fromisoformat(r["ngay_het_han"])
        conngay = (han - homnay).days
        if conngay < 0:
            tt = f"HẾT HẠN {abs(conngay)} ngày trước"
        elif conngay <= 7:
            tt = f"Sắp hết hạn ({conngay} ngày)"
        else:
            tt = f"Còn hạn ({conngay} ngày)"
        loai = " [thử]" if r["la_dung_thu"] else ""
        print(f"{r['hwid']:<18}{(r['so_dien_thoai'] or ''):<14}{r['ngay_cap']:<12}"
              f"{r['ngay_het_han']:<12}{tt:<20}{(r['ghi_chu'] or '')}{loai}")


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
