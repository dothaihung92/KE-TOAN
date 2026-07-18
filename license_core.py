# -*- coding: utf-8 -*-
"""
Lõi giấy phép sử dụng (license) — CHỈ chứa KHOÁ CÔNG KHAI (public key), an
toàn để nằm trong repo công khai vì file này TỰ ĐỘNG CẬP NHẬT tới máy mọi
người dùng (xem update.py). Khoá RIÊNG (private key) dùng để KÝ (cấp) mã
kích hoạt nằm ở 1 file RIÊNG trên máy admin (admin_private_key.pem),
KHÔNG BAO GIỜ được đưa vào đây hay commit lên git — nếu lộ khoá riêng, bất
kỳ ai cũng tự tạo được mã kích hoạt giả.

Định dạng mã kích hoạt: base32(payload_bytes + chữ_ký_64_byte), payload =
"{hwid16}|{yyyymmdd_het_han}" (UTF-8), ký bằng Ed25519. Trình bày cho người
dùng dạng nhóm 5 ký tự cách nhau bằng dấu gạch ngang cho dễ đọc/gõ lại.
"""
import base64
import ctypes
import hashlib
import os
import platform
import re
import datetime

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

# Khoá CÔNG KHAI của Đại lý thuế Hưng Phúc — dùng để KIỂM TRA chữ ký mã kích
# hoạt (không thể dùng để TẠO mã, an toàn khi công khai).
# Sinh bằng: python cap_phep_admin.py --tao-khoa (chạy 1 lần, chỉ trên máy admin)
PUBLIC_KEY_HEX = "99b3ea79ee42f36e12192e0791e41951957326772f805309c016463d041d9462"


def _sha16(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def lay_hwid() -> str:
    """Mã định danh phần cứng máy hiện tại (16 hex) — dùng để khoá giấy phép
    theo máy, tránh 1 người tạo nhiều 'máy ảo'/đổi tên để xin dùng thử nhiều
    lần. Ưu tiên serial ổ đĩa hệ thống (Windows); máy không lấy được thì rớt
    về địa chỉ MAC (vẫn ổn định trên cùng 1 máy)."""
    nguon = ""
    try:
        if platform.system() == "Windows":
            drive = (os.environ.get("SystemDrive", "C:") or "C:") + "\\"
            serial = ctypes.c_uint(0)
            ok = ctypes.windll.kernel32.GetVolumeInformationW(
                ctypes.c_wchar_p(drive), None, 0,
                ctypes.byref(serial), None, None, None, 0)
            if ok and serial.value:
                nguon = f"VOLSER-{serial.value:08X}"
    except Exception:
        nguon = ""
    if not nguon:
        try:
            import uuid
            nguon = f"MAC-{uuid.getnode():012X}"
        except Exception:
            nguon = f"HOST-{platform.node()}"
    return _sha16(nguon)


_B32_RE = re.compile(r"[^A-Z2-7]")


def dinh_dang_ma(ma_tho: str) -> str:
    """Trình bày mã kích hoạt dạng nhóm 5 ký tự cách nhau bằng '-' cho dễ đọc."""
    s = ma_tho.strip().upper()
    return "-".join(s[i:i + 5] for i in range(0, len(s), 5))


def _chuan_hoa_ma(ma: str) -> str:
    """Bỏ dấu gạch ngang/khoảng trắng người dùng gõ/dán vào, chuẩn hoá hoa."""
    return _B32_RE.sub("", (ma or "").strip().upper())


def kiem_tra_ma_kich_hoat(ma_kich_hoat: str, hwid: str = None):
    """Kiểm tra 1 mã kích hoạt có hợp lệ cho MÁY HIỆN TẠI không.
    Trả (ok: bool, ngay_het_han: 'yyyy-mm-dd' hoặc None, loi: str)."""
    if not PUBLIC_KEY_HEX:
        return False, None, "Phần mềm chưa cấu hình khoá công khai — liên hệ admin"
    hwid = hwid or lay_hwid()
    ma_sach = _chuan_hoa_ma(ma_kich_hoat)
    if not ma_sach:
        return False, None, "Mã kích hoạt trống"
    # thêm padding '=' cho đủ bội số 8 ký tự (base32 yêu cầu)
    pad = (-len(ma_sach)) % 8
    try:
        blob = base64.b32decode(ma_sach + ("=" * pad))
    except Exception:
        return False, None, "Mã kích hoạt sai định dạng"
    if len(blob) <= 64:
        return False, None, "Mã kích hoạt sai định dạng (quá ngắn)"
    payload, chu_ky = blob[:-64], blob[-64:]
    try:
        pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(PUBLIC_KEY_HEX))
        pub.verify(chu_ky, payload)
    except InvalidSignature:
        return False, None, "Mã kích hoạt không hợp lệ (chữ ký sai)"
    except Exception as e:
        return False, None, f"Lỗi kiểm tra chữ ký: {e}"
    try:
        payload_str = payload.decode("utf-8")
        hwid_ma, han_str = payload_str.split("|")
    except Exception:
        return False, None, "Mã kích hoạt sai định dạng (payload)"
    if hwid_ma.strip().lower() != hwid.strip().lower():
        return False, None, "Mã kích hoạt này được cấp cho MÁY KHÁC — liên hệ admin để cấp lại"
    try:
        han = datetime.datetime.strptime(han_str, "%Y%m%d").date()
    except Exception:
        return False, None, "Mã kích hoạt sai định dạng (ngày hết hạn)"
    ngay_het_han = han.isoformat()
    if han < datetime.date.today():
        return False, ngay_het_han, f"Giấy phép đã hết hạn ngày {han.strftime('%d/%m/%Y')}"
    return True, ngay_het_han, ""
