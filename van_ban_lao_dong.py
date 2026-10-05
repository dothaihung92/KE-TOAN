# -*- coding: utf-8 -*-
"""
Hợp đồng lao động / Quy chế lương thưởng / Hệ thống thang bảng lương.

Module THUẦN (không đụng DB, không import server.py) để dễ kiểm thử:
  - gop_nhan_vien(...)      : ghép Danh Sách Nhân Viên + Bảng Lương -> danh sách người lao động
  - dung_hop_dong(...)      : HTML hợp đồng lao động của 1 người
  - dung_quy_che(...)       : HTML Quy chế lương thưởng
  - dung_thang_bang_luong() : HTML hệ thống thang lương, bảng lương (+ bảng xếp lương)
  - kiem_tra(...)           : đối chiếu dữ liệu (cảnh báo trước khi nộp thanh tra BHXH/thuế)
  - html_sang_docx(...)     : HTML (đã người dùng chỉnh sửa trên màn hình) -> file Word .docx
  - thang_luong_excel(...)  : thang bảng lương dạng Excel (theo file mẫu)
Văn bản dựng ra là HTML đơn giản (p/table/b/i/u + class c,r,j,b,i,u,ti,l1,l2) để người dùng sửa
trực tiếp trên màn hình trước khi in; đúng HTML đó được đổi sang Word.
"""
import datetime
import html as _html
import io
import re
import unicodedata
import zipfile
from html.parser import HTMLParser
from xml.sax.saxutils import escape as _xml_esc


# ============================================================ tiện ích chung
def esc(s):
    return _html.escape(str(s if s is not None else ""), quote=True)


def khong_dau(s):
    s = str(s or "").replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _chuan(s):
    return re.sub(r"\s+", " ", khong_dau(s).strip().lower())


def so_tien(n):
    """5000000 -> '5.000.000' (làm tròn đồng)."""
    try:
        n = int(round(float(n or 0)))
    except Exception:
        n = 0
    return f"{n:,}".replace(",", ".")


_CHU_SO = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]


def _doc_nhom_ba(n, day_du):
    tram, chuc, dv = n // 100, (n // 10) % 10, n % 10
    kq = []
    if tram or day_du:
        kq.append(_CHU_SO[tram] + " trăm")
    if chuc == 0:
        if dv and (tram or day_du):
            kq.append("lẻ")
    elif chuc == 1:
        kq.append("mười")
    else:
        kq.append(_CHU_SO[chuc] + " mươi")
    if dv:
        if dv == 1 and chuc > 1:
            kq.append("mốt")
        elif dv == 5 and chuc > 0:
            kq.append("lăm")
        else:
            kq.append(_CHU_SO[dv])
    return " ".join(kq)


def doc_so_thanh_chu(n):
    """5250000 -> 'Năm triệu hai trăm năm mươi nghìn đồng'."""
    try:
        n = int(round(float(n or 0)))
    except Exception:
        n = 0
    if n <= 0:
        return "Không đồng"
    nhom = []
    while n:
        nhom.append(n % 1000)
        n //= 1000
    don_vi = ["", " nghìn", " triệu", " tỷ", " nghìn tỷ", " triệu tỷ"]
    ph = []
    for i in range(len(nhom) - 1, -1, -1):
        if nhom[i] == 0:
            continue
        ph.append(_doc_nhom_ba(nhom[i], day_du=(i != len(nhom) - 1)) + don_vi[i])
    s = " ".join(ph).strip()
    return s[:1].upper() + s[1:] + " đồng"


def doc_ngay(v):
    """Đọc ngày/tháng kiểu Việt Nam -> (năm, tháng, ngày|None) hoặc None. Hỗ trợ dd/mm/yyyy, mm/yyyy, yyyy-mm-dd, datetime."""
    if isinstance(v, datetime.datetime):
        v = v.date()
    if isinstance(v, datetime.date):
        return (v.year, v.month, v.day)
    t = str(v or "").strip()
    if not t:
        return None
    g = re.match(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})", t)
    if g:
        d, m, y = int(g.group(1)), int(g.group(2)), int(g.group(3))
    else:
        g = re.match(r"^(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})", t)
        if g:
            y, m, d = int(g.group(1)), int(g.group(2)), int(g.group(3))
        else:
            g = re.match(r"^(\d{1,2})[/\-.](\d{4})$", t)
            if g:
                m, y, d = int(g.group(1)), int(g.group(2)), None
            else:
                g = re.match(r"^(\d{4})[/\-.](\d{1,2})$", t)
                if not g:
                    return None
                y, m, d = int(g.group(1)), int(g.group(2)), None
    if not (1 <= m <= 12 and 1900 <= y <= 2200 and (d is None or 1 <= d <= 31)):
        return None
    return (y, m, d)


def ngay_date(v, mac_dinh=None):
    """Đọc ngày đầy đủ -> datetime.date (thiếu ngày thì lấy mồng 1); không đọc được -> mac_dinh."""
    k = doc_ngay(v)
    if not k:
        return mac_dinh
    try:
        return datetime.date(k[0], k[1], k[2] or 1)
    except ValueError:
        return mac_dinh


def dd_mm_yyyy(d):
    return d.strftime("%d/%m/%Y") if d else ""


def ngay_chu(d):
    return f"ngày {d.day:02d} tháng {d.month:02d} năm {d.year}" if d else "ngày ..... tháng ..... năm ........"


def hien_ngay_nv(v):
    """Ngày sinh/ngày cấp trong danh sách -> dd/mm/yyyy (giữ nguyên chữ nếu không đọc được)."""
    k = doc_ngay(v)
    if k and k[2]:
        return f"{k[2]:02d}/{k[1]:02d}/{k[0]}"
    return str(v or "").strip()


def gioi_tinh_tu_cccd(cccd):
    """CCCD 12 số: chữ số thứ 4 mã giới tính + thế kỷ sinh (0/2/4.. Nam, 1/3/5.. Nữ). Khác -> ''."""
    s = re.sub(r"\D", "", str(cccd or ""))
    if len(s) != 12:
        return ""
    return "Nam" if int(s[3]) % 2 == 0 else "Nữ"


def so_la_ma(n):
    return ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV", "XV"][n - 1] if 1 <= n <= 15 else str(n)


# ============================================================ căn cứ pháp lý + lương tối thiểu vùng
LUONG_TOI_THIEU_VUNG = {
    2022: {1: 4680000, 2: 4160000, 3: 3640000, 4: 3250000},     # NĐ 38/2022/NĐ-CP (từ 01/7/2022)
    2024: {1: 4960000, 2: 4410000, 3: 3860000, 4: 3450000},     # NĐ 74/2024/NĐ-CP (từ 01/7/2024)
    2026: {1: 5310000, 2: 4730000, 3: 4140000, 4: 3700000},     # NĐ 293/2025/NĐ-CP (từ 01/01/2026)
}


def luong_toi_thieu_vung(nam, vung=1):
    nam = int(nam or datetime.date.today().year)
    khoa = 2026 if nam >= 2026 else (2024 if nam >= 2024 else 2022)
    vung = int(vung) if int(vung or 1) in (1, 2, 3, 4) else 1
    return LUONG_TOI_THIEU_VUNG[khoa][vung]


def van_ban_luong_toi_thieu(nam):
    nam = int(nam or datetime.date.today().year)
    if nam >= 2026:
        return "Nghị định số 293/2025/NĐ-CP quy định mức lương tối thiểu đối với người lao động làm việc theo hợp đồng lao động"
    if nam >= 2024:
        return "Nghị định số 74/2024/NĐ-CP ngày 30/6/2024 quy định mức lương tối thiểu đối với người lao động làm việc theo hợp đồng lao động"
    return "Nghị định số 38/2022/NĐ-CP ngày 12/6/2022 quy định mức lương tối thiểu đối với người lao động làm việc theo hợp đồng lao động"


def van_ban_bhxh(ngay):
    if ngay and ngay >= datetime.date(2025, 7, 1):
        return "Luật Bảo hiểm xã hội số 41/2024/QH15 ngày 29/6/2024"
    return "Luật Bảo hiểm xã hội số 58/2014/QH13 ngày 20/11/2014"


def van_ban_thue(ngay):
    if ngay and ngay >= datetime.date(2026, 1, 1):
        return ("Luật Thuế thu nhập cá nhân số 04/2007/QH12 và các văn bản sửa đổi, bổ sung; "
                "Nghị quyết số 110/2025/UBTVQH15 ngày 17/10/2025 về điều chỉnh mức giảm trừ gia cảnh")
    return ("Luật Thuế thu nhập cá nhân số 04/2007/QH12 và các văn bản sửa đổi, bổ sung; "
            "Nghị quyết số 954/2020/UBTVQH14 ngày 02/6/2020 về điều chỉnh mức giảm trừ gia cảnh")


# ============================================================ tuỳ chọn mặc định
TRANG_MAC_DINH = {"font": "Times New Roman", "size": 13, "line": 1.15, "le": [20, 20, 30, 15], "ngang": False}

# Nhóm chức danh mặc định của Hệ thống thang lương, bảng lương (mỗi dòng 1 nhóm, ; = gộp nhiều chức danh; "| mức" = mức bậc 1, bỏ = tự dò từ Bảng Lương)
NHOM_MAC_DINH = "Giám đốc\nPhó giám đốc; Kế toán trưởng\nNhân viên kế toán; Nhân viên kinh doanh\nPhân xưởng sản xuất"

PHUC_LOI_MAC_DINH = {
    # key: (nhãn, mặc định tick, mức 1, mức 2). Mặc định KHÔNG tick khoản có số tiền — người dùng tự tick + nhập theo chính sách công ty.
    "cuoi_nam": ("Thưởng cuối năm theo kết quả sản xuất kinh doanh", True, 0, 0),
    "tham_nien": ("Thưởng thâm niên", False, 0, 0),
    "hieu_hy": ("Hỗ trợ hiếu, hỷ (bản thân / thân nhân: vợ, chồng, bố mẹ, anh chị em ruột)", False, 1000000, 500000),
    "om_dau": ("Hỗ trợ thiên tai, tai nạn, ốm đau (bản thân / thân nhân)", False, 500000, 200000),
    "thuong_le": ("Thưởng sinh nhật và các ngày lễ (từ / đến, đồng/lần)", False, 200000, 400000),
    "cong_tac_phi": ("Công tác phí đi về trong ngày (đồng/ngày)", False, 200000, 0),
    "du_lich": ("Hỗ trợ du lịch, nghỉ mát hằng năm", False, 0, 0),
    "hoc_phi": ("Hỗ trợ học phí đào tạo theo yêu cầu công việc", False, 0, 0),
}


def dia_danh_tu_dia_chi(dia_chi):
    """Địa danh trên văn bản: lấy cụm cuối của địa chỉ (bỏ 'Việt Nam', 'Thành phố', 'Tỉnh'); TP.HCM -> 'TP. Hồ Chí Minh'."""
    ps = [p.strip() for p in re.split(r"[,;]", str(dia_chi or "")) if p.strip()]
    while ps and _chuan(ps[-1]) in ("viet nam", "vn"):
        ps.pop()
    if not ps:
        return ""
    t = ps[-1]
    kd = _chuan(t)
    if kd in ("ho chi minh", "tp ho chi minh", "tp. ho chi minh", "thanh pho ho chi minh", "tp.hcm", "tp hcm", "tphcm", "hcm"):
        return "TP. Hồ Chí Minh"
    m = re.match(r"^(thành phố|tp\.?|tỉnh)\s+(.+)$", t, flags=re.I)
    return m.group(2).strip(". ") if m else ""      # cụm cuối không phải tên thành phố/tỉnh (vd 'Khu Phố 3C') -> để trống, chỉ hiện ngày tháng


def mac_dinh_tuy_chon(cty, hom_nay=None):
    hom_nay = hom_nay or datetime.date.today()
    cty = cty or {}
    return {
        "ngay": dd_mm_yyyy(hom_nay),
        "dia_danh": dia_danh_tu_dia_chi(cty.get("dia_chi")),
        "nguoi_ky": (cty.get("nguoi_ky") or "").strip(),
        "chuc_danh_ky": "Giám đốc",
        "ong_ba_ky": "",
        "dien_thoai": "",
        # hợp đồng
        "loai_hd": "xdth", "so_thang": 12, "bat_dau": "", "ngay_ky": "", "so_bat_dau": 1,
        "mau_so": "{so:02d}/HĐLĐ-{nam}", "dia_diem": (cty.get("dia_chi") or "").strip(), "bo_phan": "", "cong_viec": "",
        "thoi_gio": "08 giờ/ngày, 06 ngày/tuần (nghỉ Chủ nhật), tổng cộng không quá 48 giờ/tuần",
        "hinh_thuc_tra": "chuyển khoản", "ngay_tra": 5, "ghi_phu_cap": False, "quoc_tich": "Việt Nam",
        "noi_cap_cccd": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
        # quy chế
        "so_qd": f"01/QĐ-{hom_nay.year}", "kem_phu_luc": False,
        "phuc_loi": {k: {"bat": v[1], "m1": v[2], "m2": v[3]} for k, v in PHUC_LOI_MAC_DINH.items()},
        # thang bảng lương
        "vung": 1, "buoc_pct": 5, "so_bac": 7, "kem_xep_luong": True, "gan_chu_ky": True,
        "tv_tu": "", "tv_den": "", "tv_phan_tram": 100, "tv_cong_viec": "", "hien_he_so": True, "nhom_tuy_chinh": NHOM_MAC_DINH,
        # hợp đồng lao động part-time (làm việc không trọn thời gian)
        "pt_gio_ngay": "", "pt_ngay_tuan": "", "pt_lich": "", "pt_khung_gio": "", "pt_gio_tuan": "", "pt_gio_thang": "", "pt_luong_gio": "", "pt_mau_so": "{so:02d}/HĐPT-{nam}",
    }


def gop_tuy_chon(cty, tuy_chon, hom_nay=None):
    kq = mac_dinh_tuy_chon(cty, hom_nay)
    for k, v in (tuy_chon or {}).items():
        if k == "phuc_loi" and isinstance(v, dict):
            for kk, vv in v.items():
                if kk in kq["phuc_loi"] and isinstance(vv, dict):
                    kq["phuc_loi"][kk].update(vv)
        elif v is not None and (v != "" or k in ("bat_dau", "ngay_ky", "bo_phan", "cong_viec", "ong_ba_ky", "dien_thoai", "nhom_tuy_chinh", "tv_tu", "tv_den", "tv_cong_viec", "pt_gio_ngay", "pt_ngay_tuan", "pt_lich", "pt_khung_gio", "pt_gio_tuan", "pt_gio_thang", "pt_luong_gio")):
            kq[k] = v
    return kq


# ============================================================ ghép dữ liệu nhân viên + bảng lương
_COT_NV = {  # khoá -> các tên cột (không dấu, thường) của Danh Sách Nhân Viên
    "ma": ["ma nv"], "ten": ["ho va ten"], "ngay_sinh": ["ngay sinh"], "dia_chi": ["dia chi hien dang cu tru", "dia chi"],
    "cccd": ["cccd"], "ngay_cap": ["ngay cap"], "vao_lam": ["thang/nam vao lam"], "dong_bh": ["dong bhxh"],
    "nghi_viec": ["thang/nam nghi viec"], "chuc_vu": ["chuc vu"], "luong_cb": ["luong co ban"],
    "thu_viec_tu": ["thu viec tu"], "thu_viec_den": ["thu viec den"], "part_time": ["part-time"], "luong_gio": ["luong theo gio"],
    "tien_com": ["pc tien com"], "xang_xe": ["pc xang xe"], "dien_thoai": ["pc dien thoai"], "trang_phuc": ["pc trang phuc"],
}


def _so(v):
    if isinstance(v, (int, float)):
        return float(v)
    t = str(v or "").strip().replace("đ", "").replace(" ", "")
    if not t:
        return 0.0
    if re.fullmatch(r"-?\d{1,3}(\.\d{3})+(,\d+)?", t):
        t = t.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(,\d{3})+(\.\d+)?", t):
        t = t.replace(",", "")
    else:
        t = t.replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return 0.0


def _tick(v):
    return _chuan(v) in ("x", "1", "true", "co", "yes", "v", "✓", "☑", "y")



# ============================================================ nhiều phiên bản lương của 1 người (Danh Sách Nhân Viên: cột "Tháng/Năm thay đổi lương")
_RE_MA_PHIEN_BAN = re.compile(r"^(.+)-(\d{3})$")


def ma_goc_phien_ban(ma):
    """'2-001' -> '2' (mã dòng thay đổi lương = mã gốc + '-001', '-002'...). Mã không có đuôi giữ nguyên."""
    m = _RE_MA_PHIEN_BAN.match(str(ma or "").strip())
    return m.group(1) if m else str(ma or "").strip()


def nhom_phien_ban(header, rows):
    """Gom các dòng Danh Sách NV theo NGƯỜI: dòng gốc + các dòng phiên bản (mã gốc-001, -002... hoặc có 'Tháng/Năm thay đổi lương').
    -> list [[((năm, tháng) hiệu lực | (0, 0) = từ đầu, chỉ số dòng, dòng), ...], ...] theo thứ tự xuất hiện. None nếu danh sách không có phiên bản nào."""
    cot = {}
    for i, h in enumerate(header or []):
        cot.setdefault(_chuan(h), i)
    i_ma, i_ten, i_doi = cot.get("ma nv"), cot.get("ho va ten"), cot.get("thang/nam thay doi luong")
    i_vao = cot.get("thang/nam vao lam")
    if i_doi is None and not any(_RE_MA_PHIEN_BAN.match(str(r[i_ma]).strip()) for r in (rows or []) if i_ma is not None and i_ma < len(r) and r[i_ma] is not None):
        return None        # không có cột thay đổi lương và không có dòng phiên bản (mã gốc-001): mỗi dòng là 1 người

    def o(r, i):
        return r[i] if i is not None and i < len(r) and r[i] is not None else ""
    nhom, thu_tu = {}, []
    ten_goc = {}          # họ tên -> khoá của dòng gốc (để dòng thay đổi lương gõ mã khác, không có đuôi -001, vẫn gộp đúng người)
    for r in rows or []:
        if not doc_ngay(o(r, i_doi)) and _chuan(o(r, i_ten)) and str(o(r, i_ma)).strip():
            ten_goc.setdefault(_chuan(o(r, i_ten)), ("ma", str(o(r, i_ma)).strip().lower()))
    # mã gốc có thật trong danh sách (dòng không đuôi -001): chỉ khi đó dòng "gốc-001" mới được coi là phiên bản của người đó (NV-001, NV-002 của 2 người khác nhau thì KHÔNG gộp)
    ma_co_goc = {str(o(r, i_ma)).strip().lower() for r in (rows or []) if str(o(r, i_ma)).strip() and not _RE_MA_PHIEN_BAN.match(str(o(r, i_ma)).strip())}
    for idx, r in enumerate(rows or []):
        ma, ten = str(o(r, i_ma)).strip(), _chuan(o(r, i_ten))
        tu = doc_ngay(o(r, i_doi))
        tu = (tu[0], tu[1]) if tu else None
        if tu is None and _RE_MA_PHIEN_BAN.match(ma) and ma_goc_phien_ban(ma).lower() in ma_co_goc:
            # Dòng mã dạng gốc-001 (thêm bằng nút ＋) chưa ghi "Tháng/Năm thay đổi lương" nhưng có "Tháng/Năm vào làm": coi là phiên bản của người đó HIỆU LỰC TỪ tháng vào làm
            # (vd 2-001 vào làm 12/2024: từ 12/2024 dùng dòng này — kể cả chuyển từ part-time sang toàn thời gian, bắt đầu đóng BHXH; trước đó dùng dòng gốc "2").
            vl = doc_ngay(o(r, i_vao))
            tu = (vl[0], vl[1]) if vl else None
        if tu is None:
            khoa = ("ma", ma.lower()) if ma else ("ten", ten) if ten else ("dong", idx)
        elif _RE_MA_PHIEN_BAN.match(ma):
            khoa = ("ma", ma_goc_phien_ban(ma).lower())
        else:
            khoa = ten_goc.get(ten) or (("ten", ten) if ten else ("dong", idx))
        if khoa not in nhom:
            nhom[khoa] = []
            thu_tu.append(khoa)
        nhom[khoa].append((tu or (0, 0), idx, r))
    return [nhom[k] for k in thu_tu]


def chon_phien_ban_hieu_luc(header, rows, nam=None, thang=None):
    """Danh Sách Nhân Viên có thể có NHIỀU DÒNG cho cùng 1 người: dòng gốc + các dòng thay đổi lương (mã gốc-001, -002..., có ô 'Tháng/Năm thay đổi lương').
    Trả về mỗi người đúng 1 dòng ĐANG HIỆU LỰC ở (nam, thang): dòng có tháng thay đổi lớn nhất mà <= tháng đó (dòng gốc không ghi tháng = từ đầu).
    Không truyền tháng: lấy dòng mới nhất (nam thôi: tính đến hết tháng 12 của năm). Người chỉ có dòng thay đổi ở tương lai thì chưa có."""
    nhom = nhom_phien_ban(header, rows)
    if nhom is None:
        return list(rows or [])
    dich = (int(nam), int(thang)) if nam and thang else ((int(nam), 12) if nam else None)
    kq = []
    for g in nhom:
        ung = [x for x in g if dich is None or x[0] <= dich]
        if ung:
            kq.append(max(ung, key=lambda x: (x[0], x[1]))[2])
    return kq


def gop_nhan_vien(nv_header, nv_rows, bang_luong_theo_thang=None, nam=None):
    """Ghép Danh Sách Nhân Viên (header+rows) với dòng NHẬP Bảng Lương của tháng mới nhất có người đó.
    `bang_luong_theo_thang` = {"01": [dòng nhập...], ...} (dòng nhập: ma, ten, chuc_vu, luong_cb, tien_com, muc_xang, muc_dt,
    trang_phuc, di_lai, dong_bh...). Bảng lương là số THỰC TRẢ nên được ưu tiên; chỗ nào khác danh sách thì ghi vào 'lech'.
    Trả về list dict (đã đánh stt 1..n, theo thứ tự danh sách; người chỉ có trong bảng lương xếp cuối)."""
    nv_rows = chon_phien_ban_hieu_luc(nv_header, nv_rows, nam)      # mỗi người 1 dòng: phiên bản lương đang hiệu lực đến hết năm `nam`
    cot = {}
    for i, h in enumerate(nv_header or []):
        cot.setdefault(_chuan(h), i)

    def lay(r, khoa):
        for ten in _COT_NV[khoa]:
            i = cot.get(ten)
            if i is not None and i < len(r) and r[i] is not None:
                return r[i]
        return ""

    # bảng lương: lấy tháng MỚI NHẤT có người đó
    bl_ma, bl_ten = {}, {}
    for t in sorted((bang_luong_theo_thang or {}).keys()):
        for r in bang_luong_theo_thang[t] or []:
            ma, ten = str(r.get("ma") or "").strip(), str(r.get("ten") or "").strip()
            if not ten and not ma:
                continue
            ban_ghi = dict(r, _thang=t)
            if ma:
                bl_ma[_chuan(ma)] = ban_ghi
            if ten:
                bl_ten[_chuan(ten)] = ban_ghi

    kq = []
    co_cot_tick = "dong bhxh" in cot
    for r in nv_rows or []:
        ten = str(lay(r, "ten") or "").strip()
        if not ten:
            continue
        ma = str(lay(r, "ma") or "").strip()
        nv = {"ma": ma, "ten": ten, "ngay_sinh": hien_ngay_nv(lay(r, "ngay_sinh")), "dia_chi": str(lay(r, "dia_chi") or "").strip(),
              "cccd": re.sub(r"\s+", "", str(lay(r, "cccd") or "")), "ngay_cap": hien_ngay_nv(lay(r, "ngay_cap")),
              "vao_lam": str(lay(r, "vao_lam") or "").strip(), "nghi_viec": str(lay(r, "nghi_viec") or "").strip(),
              "thu_viec_tu": hien_ngay_nv(lay(r, "thu_viec_tu")), "thu_viec_den": hien_ngay_nv(lay(r, "thu_viec_den")),
              "dong_bh": _tick(lay(r, "dong_bh")) if co_cot_tick else True,
              "part_time": _tick(lay(r, "part_time")), "luong_gio": _so(lay(r, "luong_gio")),
              "chuc_vu": str(lay(r, "chuc_vu") or "").strip(), "luong_cb": _so(lay(r, "luong_cb")),
              "tien_com": _so(lay(r, "tien_com")), "xang_xe": _so(lay(r, "xang_xe")), "dien_thoai": _so(lay(r, "dien_thoai")),
              "trang_phuc": _so(lay(r, "trang_phuc")), "di_lai": 0.0, "nguon": "Danh sách nhân viên", "lech": []}
        nv["gioi_tinh"] = gioi_tinh_tu_cccd(nv["cccd"])
        bl = bl_ma.get(_chuan(ma)) if ma else None
        bl = bl or bl_ten.get(_chuan(ten))
        if bl:
            nv["nguon"] = f"Bảng lương tháng {int(bl['_thang'])}"
            for k_nv, k_bl in (("luong_cb", "luong_cb"), ("tien_com", "tien_com"), ("xang_xe", "muc_xang"),
                               ("dien_thoai", "muc_dt"), ("trang_phuc", "trang_phuc")):
                gt_bl = _so(bl.get(k_bl))
                if abs(gt_bl - nv[k_nv]) > 0.5 and (gt_bl or nv[k_nv]):
                    if k_nv == "luong_cb" and gt_bl > 0:
                        nv["lech"].append(f"Lương cơ bản: Danh sách NV {so_tien(nv[k_nv])} ≠ Bảng lương T{int(bl['_thang'])} {so_tien(gt_bl)} (đã lấy theo Bảng lương)")
                if k_nv != "luong_cb" or gt_bl > 0:
                    nv[k_nv] = gt_bl
            nv["di_lai"] = _so(bl.get("di_lai"))
            if str(bl.get("chuc_vu") or "").strip() and not nv["chuc_vu"]:
                nv["chuc_vu"] = str(bl.get("chuc_vu")).strip()
            nv["ghi_chu"] = str(bl.get("ghi_chu") or "").strip()
        else:
            nv["ghi_chu"] = ""
        kq.append(nv)
    # người chỉ có trong bảng lương (chưa vào danh sách)
    thay = {}
    for t in sorted((bang_luong_theo_thang or {}).keys()):
        for r in bang_luong_theo_thang[t] or []:
            ten = str(r.get("ten") or "").strip()
            if not ten:
                continue
            if any(_chuan(x["ten"]) == _chuan(ten) or (x["ma"] and x["ma"] == str(r.get("ma") or "").strip()) for x in kq):
                continue
            thay[_chuan(ten)] = dict(r, _thang=t)
    for r in thay.values():
        kq.append({"ma": str(r.get("ma") or "").strip(), "ten": str(r.get("ten")).strip(), "ngay_sinh": "", "dia_chi": "", "cccd": "",
                   "ngay_cap": "", "vao_lam": "", "nghi_viec": "", "thu_viec_tu": "", "thu_viec_den": "", "dong_bh": bool(r.get("dong_bh")), "gioi_tinh": "",
                   "chuc_vu": str(r.get("chuc_vu") or "").strip(), "luong_cb": _so(r.get("luong_cb")), "tien_com": _so(r.get("tien_com")),
                   "xang_xe": _so(r.get("muc_xang")), "dien_thoai": _so(r.get("muc_dt")), "trang_phuc": _so(r.get("trang_phuc")),
                   "di_lai": _so(r.get("di_lai")), "nguon": f"Bảng lương tháng {int(r['_thang'])} (chưa có trong Danh sách NV)",
                   "lech": ["Có trong Bảng lương nhưng chưa có trong Danh Sách Nhân Viên — thiếu ngày sinh, CCCD, địa chỉ"],
                   "ghi_chu": str(r.get("ghi_chu") or "").strip()})
    for i, nv in enumerate(kq, 1):
        nv["stt"] = i
        nv["da_nghi"] = bool(nv["nghi_viec"])
    return kq


def khoa_lich_su(nv):
    """Khoá người dùng để ghép hợp đồng với lịch sử lương: mã gốc (2-001 -> 2, chữ thường), không có mã thì họ tên chuẩn hoá."""
    m = ma_goc_phien_ban((nv or {}).get("ma"))
    return ("ma", m.lower()) if m else ("ten", _chuan((nv or {}).get("ten")))


def lich_su_luong_hop_dong(nv_header, nv_rows, bang_luong_theo_thang, nam):
    """Người có NHIỀU phiên bản TOÀN THỜI GIAN (dòng gốc + mã gốc-001, -002...) trong Danh Sách NV -> dữ liệu cho hợp đồng lao động năm `nam` + PHỤ LỤC:
    {khoa_lich_su: {"vao_lam": vào làm của phiên bản toàn thời gian ĐẦU TIÊN, "ban_dau": nv (phiên bản hiệu lực ngày bắt đầu hợp đồng),
                    "dieu_chinh": [{"tu": date áp dụng, "nv": nv phiên bản mới, "cu": nv phiên bản trước}, ...]}}
    Chỉ ghi nhận điều chỉnh khi LƯƠNG CƠ BẢN thay đổi, áp dụng sau ngày bắt đầu hợp đồng và trong năm `nam`. Lương mỗi phiên bản ưu tiên Bảng Lương
    của tháng phiên bản đó bắt đầu áp dụng (số thực trả), không có thì lấy Danh Sách NV. Dòng part-time không tính (hợp đồng part-time riêng)."""
    nhom = nhom_phien_ban(nv_header, nv_rows)
    if not nhom or not nam:
        return {}
    nam = int(nam)
    cot = {}
    for i, h in enumerate(nv_header or []):
        cot.setdefault(_chuan(h), i)

    def lay(r, khoa):
        for ten in _COT_NV[khoa]:
            i = cot.get(ten)
            if i is not None and i < len(r) and r[i] is not None:
                return r[i]
        return ""
    bl = bang_luong_theo_thang or {}

    def nv_cua(r, thang):
        t = "%02d" % thang
        ds = gop_nhan_vien(nv_header, [r], {t: bl[t]} if bl.get(t) else None, None)
        return ds[0] if ds and ds[0].get("ten") == str(lay(r, "ten") or "").strip() else None
    kq = {}
    for g in nhom:
        ds = sorted((x for x in g if not _tick(lay(x[2], "part_time")) and str(lay(x[2], "ten") or "").strip()), key=lambda x: (x[0], x[1]))
        if len(ds) < 2:
            continue
        vao_lam = str(lay(ds[0][2], "vao_lam") or "").strip()
        bat_dau = ngay_bat_dau_theo_nam(vao_lam, nam) or datetime.date(nam, 1, 1)
        if bat_dau.year > nam:
            continue
        mo = (bat_dau.year, bat_dau.month)
        truoc = [x for x in ds if x[0] <= mo]
        goc = truoc[-1] if truoc else ds[0]
        sau = [x for x in ds if mo < x[0] <= (nam, 12)]
        ban_dau = nv_cua(goc[2], bat_dau.month if bat_dau.year == nam else 1)
        if not ban_dau:
            continue
        dieu_chinh, cu = [], ban_dau
        for x in sau:
            moi = nv_cua(x[2], x[0][1] if x[0][0] == nam else 1)
            if not moi:
                continue
            if moi["luong_cb"] > 0 and abs(moi["luong_cb"] - cu["luong_cb"]) > 0.5:
                d = ngay_date(lay(x[2], "vao_lam"))
                tu = d if d and (d.year, d.month) == x[0] else datetime.date(x[0][0], x[0][1], 1)
                dieu_chinh.append({"tu": tu, "nv": moi, "cu": cu})
            cu = moi
        kq[khoa_lich_su(ban_dau)] = {"vao_lam": vao_lam, "ban_dau": ban_dau, "dieu_chinh": dieu_chinh}
    return kq


def tong_phu_cap(nv):
    return sum(float(nv.get(k) or 0) for k in ("tien_com", "xang_xe", "dien_thoai", "trang_phuc", "di_lai"))


# ============================================================ nhóm chức danh + thang bảng lương
def nhom_chuc_danh(nv_list):
    """Gom người theo chức vụ (không phân biệt hoa/thường/dấu). -> [{'ten','nguoi':[nv...]}] sắp xếp theo mức lương cao -> thấp."""
    nhom, thu_tu = {}, []
    for nv in nv_list:
        ten = (nv.get("chuc_vu") or "").strip() or "Người lao động (chưa ghi chức vụ)"
        k = _chuan(ten)
        if k not in nhom:
            nhom[k] = {"ten": ten, "nguoi": []}
            thu_tu.append(k)
        nhom[k]["nguoi"].append(nv)
    ds = [nhom[k] for k in thu_tu]
    ds.sort(key=lambda g: (-max([n["luong_cb"] for n in g["nguoi"]] or [0]), _chuan(g["ten"])))
    return ds


def _lam_tron(x, don_vi=1):
    don_vi = don_vi or 1
    return int(round(x / don_vi)) * int(don_vi)


def doc_nhom_tuy_chinh(text):
    """Mỗi dòng = 1 nhóm chức danh: 'Phó giám đốc; Kế toán trưởng | 8000000' (phần sau dấu | là mức bậc 1, có thể bỏ). -> [(tên nhóm, [chức danh], bậc 1|0)]"""
    kq = []
    for dong in str(text or "").splitlines():
        dong = dong.strip()
        if not dong:
            continue
        ten, _, goc = dong.partition("|")
        cds = [x.strip() for x in re.split(r"[;]", ten) if x.strip()]
        if cds:
            kq.append(("; ".join(cds), cds, _so(goc)))
    return kq


def chuc_danh_tu_nhom(text):
    """Danh sách chức danh (không trùng, giữ thứ tự) trong các nhóm khai báo — dùng làm danh sách chọn Chức vụ ở Danh Sách Nhân Viên."""
    kq, thay = [], set()
    for _ten, cds, _goc in doc_nhom_tuy_chinh(text):
        for c in cds:
            if _chuan(c) not in thay:
                thay.add(_chuan(c))
                kq.append(c)
    return kq


# Chức danh luôn có thể CHỌN ở Danh Sách Nhân Viên dù nhóm thang lương của năm chưa khai báo (chưa khai thì Thang bảng lương tự lập nhóm riêng theo chức danh của người đó)
CHUC_DANH_BO_SUNG = ["Quản lý", "Bảo vệ"]


def chuc_danh_day_du(text):
    """chuc_danh_tu_nhom + các chức danh bổ sung (Quản lý, Bảo vệ) nếu chưa có trong các nhóm."""
    kq = chuc_danh_tu_nhom(text)
    co = {_chuan(c) for c in kq}
    return kq + [c for c in CHUC_DANH_BO_SUNG if _chuan(c) not in co]


def bo_muc_bac_1(text):
    """Bỏ phần '| mức' của từng dòng nhóm (sang năm mới: giữ nhóm chức danh, mức bậc 1 tự dò lại từ Bảng Lương của năm đó)."""
    return "\n".join(d.partition("|")[0].strip() for d in str(text or "").splitlines() if d.strip())


def do_luong_theo_nam(nv_list, nam, tuy_chon):
    """'Dò lương cơ bản theo năm': với từng nhóm chức danh, tìm lương cơ bản thấp nhất/cao nhất trong Bảng Lương năm đó và đề xuất mức bậc 1.
    -> {'bang': [{ten, so_nguoi, thap_nhat, cao_nhat, bac_1}], 'nhom_tuy_chinh': text đã điền '| mức bậc 1' cho TẤT CẢ nhóm}."""
    tc = tuy_chon or {}
    dang_lam = [n for n in nv_list if not n.get("da_nghi")] or nv_list
    tl = tinh_thang_luong(dang_lam, nam, tc.get("vung", 1), tc.get("buoc_pct", 5), tc.get("so_bac", 7), nhom_tuy_chinh=bo_muc_bac_1(tc.get("nhom_tuy_chinh", "")))
    bang, dong = [], []
    for g in tl["nhom"]:
        luong = [n["luong_cb"] for n in g["nguoi"] if n["luong_cb"] > 0]
        bang.append({"ten": g["ten"], "so_nguoi": len(g["nguoi"]), "thap_nhat": min(luong) if luong else 0, "cao_nhat": max(luong) if luong else 0,
                     "bac_1": g["bac"][0]})
        dong.append(f"{g['ten']} | {int(g['bac'][0])}")
    return {"bang": bang, "nhom_tuy_chinh": "\n".join(dong), "luong_toi_thieu": tl["luong_toi_thieu"]}


def tinh_thang_luong(nv_list, nam, vung=1, buoc_pct=5.0, so_bac=7, lam_tron=1, nhom_tuy_chinh=""):
    """Thang lương theo từng nhóm chức danh. Bậc 1 = mức lương cơ bản THẤP NHẤT đang trả cho nhóm (không thấp hơn lương tối thiểu vùng; nhóm do
    người dùng khai báo kèm '| mức' thì lấy mức đó); mỗi bậc sau = bậc liền trước × (1 + buoc_pct%). Tự thêm bậc nếu có người lương vượt bậc cuối.
    Mỗi người được xếp vào bậc cao nhất có mức <= lương đang hưởng. `nhom_tuy_chinh`: các nhóm khai báo tay (gộp nhiều chức danh, hoặc chức danh
    chưa có người như Giám đốc); người không thuộc nhóm nào thì tự lập nhóm theo chức vụ của họ."""
    ltt = luong_toi_thieu_vung(nam, vung)
    buoc = 1.0 + float(buoc_pct or 0) / 100.0
    so_bac = max(1, int(so_bac or 7))
    nhom_nguon, con_lai = [], list(nv_list)
    for ten, cds, goc in doc_nhom_tuy_chinh(nhom_tuy_chinh):
        khoa = {_chuan(c) for c in cds}
        nguoi = [n for n in con_lai if _chuan(n.get("chuc_vu")) in khoa]
        con_lai = [n for n in con_lai if _chuan(n.get("chuc_vu")) not in khoa]
        nhom_nguon.append({"ten": ten, "nguoi": nguoi, "goc": goc})
    for g in nhom_chuc_danh(con_lai):
        nhom_nguon.append({"ten": g["ten"], "nguoi": g["nguoi"], "goc": 0})
    nhom_kq = []
    for g in nhom_nguon:
        luong = [n["luong_cb"] for n in g["nguoi"] if n["luong_cb"] > 0]
        goc = max(g["goc"] or (min(luong) if luong else ltt), ltt)
        cao_nhat = max(luong) if luong else 0
        bac, muc = [], float(goc)
        while True:
            bac.append(_lam_tron(muc, lam_tron))
            if len(bac) >= so_bac and bac[-1] * 1.0 + 0.5 >= cao_nhat:
                break
            if len(bac) >= 15:
                break
            muc *= buoc
        xep = []
        for n in g["nguoi"]:
            k = 0
            for i, m in enumerate(bac, 1):
                if n["luong_cb"] + 0.5 >= m:
                    k = i
            xep.append({"nv": n, "bac": k, "muc_bac": bac[k - 1] if k else 0,
                        "chenh": (n["luong_cb"] - bac[k - 1]) if k else 0})
        nhom_kq.append({"ten": g["ten"], "bac": bac, "he_so": [m / ltt for m in bac], "xep": xep, "nguoi": g["nguoi"],
                         "thap_hon_ltt": bool(luong) and min(luong) < ltt,
                         "duoi_bac_1": bool(luong) and min(luong) + 0.5 < bac[0] and min(luong) >= ltt,
                         "vuot_bac_cuoi": bool(luong) and bac[-1] + 0.5 < cao_nhat})
    return {"nhom": nhom_kq, "luong_toi_thieu": ltt, "buoc_pct": float(buoc_pct or 0), "so_bac_toi_da": max([len(g["bac"]) for g in nhom_kq] or [so_bac])}


# ============================================================ kiểm tra / đối chiếu
def kiem_tra(nv_list, nam, tuy_chon, tran_pc=None):
    """Danh sách cảnh báo [{'muc': 'loi'|'canh_bao', 'nd': str}] — những chỗ có thể bị thanh tra BHXH / thuế hỏi."""
    tc = tuy_chon or {}
    nd_ngay = ngay_date(tc.get("ngay"))
    nam = nd_ngay.year if nd_ngay else nam          # lương tối thiểu vùng theo NGÀY BAN HÀNH văn bản
    ltt = luong_toi_thieu_vung(nam, tc.get("vung", 1))
    tran_pc = tran_pc or {}
    kq = []

    def them(muc, nd):
        kq.append({"muc": muc, "nd": nd})
    if not nv_list:
        them("loi", "Chưa có nhân viên: hãy nhập Danh Sách Nhân Viên và/hoặc lưu Bảng Lương.")
        return kq
    for nv in nv_list:
        t = nv["ten"]
        if nv["luong_cb"] <= 0:
            them("loi", f"{t}: chưa có lương cơ bản (hợp đồng/thang lương sẽ để 0 đồng).")
        elif nv["luong_cb"] < ltt and nv["dong_bh"]:
            them("loi", f"{t}: lương cơ bản {so_tien(nv['luong_cb'])} đ thấp hơn lương tối thiểu vùng {int(tc.get('vung', 1))} ({so_tien(ltt)} đ) — trái quy định, cần điều chỉnh.")
        elif nv["luong_cb"] < ltt:
            them("canh_bao", f"{t}: lương cơ bản {so_tien(nv['luong_cb'])} đ thấp hơn lương tối thiểu vùng {so_tien(ltt)} đ (nếu làm toàn thời gian thì trái quy định).")
        if not nv.get("cccd"):
            them("canh_bao", f"{t}: thiếu số CCCD (hợp đồng lao động phải có số căn cước/CMND/hộ chiếu — Điều 21 BLLĐ 2019).")
        if not nv.get("ngay_sinh"):
            them("canh_bao", f"{t}: thiếu ngày sinh.")
        if not nv.get("dia_chi"):
            them("canh_bao", f"{t}: thiếu địa chỉ cư trú.")
        if not nv["dong_bh"] and not nv["da_nghi"]:
            them("canh_bao", f"{t}: không tick 'Đóng BHXH' — hợp đồng lao động từ đủ 01 tháng trở lên thuộc diện bắt buộc tham gia BHXH, BHYT, BHTN (nếu chưa đủ điều kiện thì bỏ qua cảnh báo này).")
        if not nv["gioi_tinh"]:
            them("canh_bao", f"{t}: không suy ra được giới tính từ CCCD — hợp đồng ghi 'Ông/Bà', hãy sửa tay khi xem trước.")
        for ld in nv.get("lech", []):
            them("canh_bao", f"{t}: {ld}")
        for k, ten_pc in (("tien_com", "tiền cơm"), ("trang_phuc", "trang phục"), ("dien_thoai", "điện thoại")):
            tr = tran_pc.get(k)
            if tr and nv.get(k, 0) > tr + 0.5:
                them("canh_bao", f"{t}: phụ cấp {ten_pc} {so_tien(nv[k])} đ vượt trần {so_tien(tr)} đ/tháng đang dùng để tính phụ cấp không chịu thuế — kiểm tra phần vượt có phải tính thuế TNCN.")
    # cùng chức danh nhưng phụ cấp khác nhau (Quy chế ghi theo chức danh)
    for g in nhom_chuc_danh(nv_list):
        for k, ten_pc in (("tien_com", "tiền cơm"), ("xang_xe", "xăng xe"), ("dien_thoai", "điện thoại"), ("trang_phuc", "trang phục"), ("di_lai", "đi lại")):
            tap = sorted({int(n[k]) for n in g["nguoi"]})
            if len(tap) > 1:
                them("canh_bao", f"Chức danh '{g['ten']}': phụ cấp {ten_pc} không đồng nhất ({', '.join(so_tien(x) for x in tap)} đ) — Quy chế sẽ ghi theo khoảng; nên thống nhất theo chức danh.")
    tl = tinh_thang_luong(nv_list, nam, tc.get("vung", 1), tc.get("buoc_pct", 5), tc.get("so_bac", 7), nhom_tuy_chinh=tc.get("nhom_tuy_chinh", ""))
    for g in tl["nhom"]:
        if g["duoi_bac_1"]:
            them("canh_bao", f"Nhóm '{g['ten']}': có người lương thấp hơn mức bậc 1 bạn khai báo ({so_tien(g['bac'][0])} đ) — người đó không xếp được vào bậc nào.")
        if g["thap_hon_ltt"]:
            them("loi", f"Chức danh '{g['ten']}': có người lương thấp hơn lương tối thiểu vùng — thang lương đã nâng bậc 1 lên bằng mức tối thiểu ({so_tien(tl['luong_toi_thieu'])} đ); cần điều chỉnh lương thực trả.")
        if g["vuot_bac_cuoi"]:
            them("canh_bao", f"Chức danh '{g['ten']}': có người lương cao hơn bậc cuối ({so_tien(g['bac'][-1])} đ) kể cả khi đã mở thêm bậc — nên tách chức danh hoặc tăng % mỗi bậc.")
        if len(g["bac"]) > int(tc.get("so_bac", 7) or 7):
            them("canh_bao", f"Chức danh '{g['ten']}': có người lương vượt bậc {so_la_ma(int(tc.get('so_bac', 7) or 7))} nên thang lương tự thêm bậc.")
    return kq


# ============================================================ dựng HTML văn bản
def _p(noi_dung, cls=""):
    return f'<p class="{cls}">{noi_dung}</p>' if cls else f"<p>{noi_dung}</p>"


def _tieu_ngu(cty, so_van_ban, dia_danh, ngay, co_ngay=True, co_dia_chi=False):
    """Khối đầu văn bản: tên công ty + số | Quốc hiệu, tiêu ngữ + địa danh, ngày (co_ngay=False: bỏ dòng ngày — vd thang lương ghi ngày ở chỗ ký)."""
    ten = esc((cty.get("ten") or "").upper())
    trai = [_p(f"<b>{ten}</b>", "c")]
    if cty.get("mst"):
        trai.append(_p(f"Mã số thuế: {esc(cty['mst'])}", "c"))
    if co_dia_chi and cty.get("dia_chi"):
        trai.append(_p(f"Địa chỉ: {esc(cty['dia_chi'])}", "c"))
    if so_van_ban:
        trai.append(_p(f"Số: {esc(so_van_ban)}", "c"))
    phai = [_p("<b>CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</b>", "c"), _p("<b>Độc lập - Tự do - Hạnh phúc</b>", "c"),
            _p("-------oOo-------", "c")]
    if co_ngay:
        phai.append(_p(f"<i>{esc(dia_danh + ', ' if dia_danh else '')}{esc(ngay_chu(ngay))}</i>", "c"))
    return ('<table class="nb"><colgroup><col style="width:44%"><col style="width:56%"></colgroup><tr><td>'
            + "".join(trai) + "</td><td>" + "".join(phai) + "</td></tr></table>")


def khoa_chu_ky(ma, ten):
    """Khoá tìm chữ ký trong Kho chữ ký: theo mã gốc (2-001 -> 2) nếu có mã, không thì theo họ tên. Giám đốc/người đại diện: 'giam_doc'."""
    m = ma_goc_phien_ban(ma)
    return ("ma:" + m.lower()) if m else ("ten:" + _chuan(ten))


def khoa_nguoi(nv):
    """Khoá chữ ký DÙNG CHUNG nhiều công ty: theo số CCCD của người đó (nếu có), không thì theo họ tên (không dấu)."""
    d = re.sub(r"\D", "", str((nv or {}).get("cccd") or ""))
    return ("cccd:" + d) if len(d) >= 9 else ("ten:" + _chuan((nv or {}).get("ten")))


def tim_chu_ky(chu_ky, nv):
    """Ảnh chữ ký của nhân viên trong dict chu_ky: khoá dùng chung (CCCD/họ tên) trước, khoá cũ theo công ty (mã/họ tên) sau."""
    chu_ky = chu_ky or {}
    return chu_ky.get(khoa_nguoi(nv)) or chu_ky.get(khoa_chu_ky(nv.get("ma"), nv.get("ten"))) or ""


def _co_anh_vua_khung(anh, rong_toi_da, cao_toi_da):
    """(rộng, cao) px để ảnh chữ ký NẰM GỌN trong khung rong_toi_da x cao_toi_da, giữ nguyên tỷ lệ (chữ ký dài không bị kéo tràn sang cột bên cạnh).
    Không đọc được kích thước ảnh -> (0, cao_toi_da)."""
    kq = _doc_anh_data_uri(anh)
    w0, h0 = _kich_thuoc_anh(kq[1]) if kq else (0, 0)
    if not (w0 and h0):
        return 0, cao_toi_da
    tl = min(rong_toi_da / w0, cao_toi_da / h0)
    return max(1, round(w0 * tl)), max(1, round(h0 * tl))


def _khoang_ky(anh="", sau=False, cao=150, rong=300):
    """Khoảng trống để ký (3 dòng); có ảnh chữ ký (đã được người đó đồng ý lưu trong Kho chữ ký) thì chèn ảnh vào đúng chỗ ký.
    sau=True (chữ ký + con dấu giám đốc): ảnh LỚN, đặt PHÍA SAU chữ (behind text) — đè lên chức danh/họ tên như dấu thật.
    Ảnh luôn thu vừa khung rong x cao (giữ tỷ lệ) và ghi rõ width + height để bản Word cũng đúng cỡ."""
    if anh and sau:
        w, h = _co_anh_vua_khung(anh, rong, cao)
        return f'<p class="c ky-sau" style="height:80px"><img class="sau" src="{esc(anh)}" style="{f"width:{w}px;" if w else ""}height:{h}px;top:{(80 - h) // 2}px"></p>'
    if anh:
        w, h = _co_anh_vua_khung(anh, rong, 80)
        return f'<p class="c"><img src="{esc(anh)}" style="{f"width:{w}px;" if w else ""}height:{h}px"></p>' + _p("&nbsp;", "c")
    return _p("&nbsp;", "c") * 3


def _bang_ky(trai_tieu_de, trai_phu, trai_ten, phai_tieu_de, phai_phu, phai_ten, trai_anh="", phai_anh=""):
    return ('<table class="nb"><colgroup><col style="width:50%"><col style="width:50%"></colgroup><tr><td>'
            + _p(f"<b>{esc(trai_tieu_de)}</b>", "c") + _p(f"<i>{esc(trai_phu)}</i>", "c") + _khoang_ky(trai_anh, sau=True, cao=100, rong=210) + _p(f"<b>{esc(trai_ten)}</b>", "c")
            + "</td><td>" + _p(f"<b>{esc(phai_tieu_de)}</b>", "c") + _p(f"<i>{esc(phai_phu)}</i>", "c") + _khoang_ky(phai_anh, sau=True)
            + _p(f"<b>{esc(phai_ten)}</b>", "c") + "</td></tr></table>")


def _thoi_han_hd(tc, nv, ngay_bat_dau):
    """(mô tả loại HĐ, ngày kết thúc|None, số tháng|0, thời gian báo trước chấm dứt)."""
    if tc.get("loai_hd") == "kxdth":
        return "Hợp đồng lao động không xác định thời hạn", None, 0, "45 ngày"
    thang = max(1, min(36, int(_so(tc.get("so_thang")) or 12)))
    cuoi = ngay_bat_dau
    if ngay_bat_dau:
        import calendar
        y, m = ngay_bat_dau.year + (ngay_bat_dau.month - 1 + thang) // 12, (ngay_bat_dau.month - 1 + thang) % 12 + 1
        cuoi_thang = calendar.monthrange(y, m)[1]
        if ngay_bat_dau.day > cuoi_thang:          # vd bắt đầu 31/08 + 6 tháng: tháng 2 không có ngày 31 -> hết tháng
            cuoi = datetime.date(y, m, cuoi_thang)
        else:                                      # bắt đầu 01/06 + 12 tháng -> hết ngày 31/05 năm sau
            cuoi = datetime.date(y, m, ngay_bat_dau.day) - datetime.timedelta(days=1)
    bao_truoc = "30 ngày" if thang >= 12 else "03 ngày làm việc"
    return "Hợp đồng lao động xác định thời hạn", cuoi, thang, bao_truoc


def ngay_bat_dau_theo_nam(vao_lam, nam):
    """Ngày bắt đầu hợp đồng mặc định: theo ngày vào làm; nếu vào làm TRƯỚC năm đang lập hợp đồng (hoặc không ghi) thì 01/01 của năm đó."""
    vl = ngay_date(vao_lam)
    if nam and (vl is None or vl.year < int(nam)):
        return datetime.date(int(nam), 1, 1)
    return vl


def dung_hop_dong(nv, cty, tuy_chon, so_thu_tu, hom_nay=None, nam=None, chu_ky=None):
    """HTML 1 hợp đồng lao động (1 <section>) cho người lao động `nv` (dict của gop_nhan_vien)."""
    tc = gop_tuy_chon(cty, tuy_chon, hom_nay)
    hom_nay = hom_nay or datetime.date.today()
    bat_dau = ngay_date(tc.get("bat_dau")) or ngay_bat_dau_theo_nam(nv.get("vao_lam"), nam)
    # Người vào Bảng Lương giữa năm (tháng đầu tiên có trong Bảng Lương muộn hơn tháng đầu của cả bảng): hợp đồng không bắt đầu sớm hơn thời điểm làm việc thực tế
    if nv.get("bl_thang_dau") and nam and not ngay_date(tc.get("bat_dau")):
        d0 = datetime.date(int(nam), int(nv["bl_thang_dau"]), 1)
        if bat_dau is None or bat_dau < d0:
            bat_dau = d0
    ngay_ky = ngay_date(tc.get("ngay_ky")) or bat_dau or ngay_date(tc.get("ngay"), hom_nay)
    bat_dau = bat_dau or ngay_ky
    loai_ten, cuoi, thang, bao_truoc = _thoi_han_hd(tc, nv, bat_dau)
    nam_so = ngay_ky.year if ngay_ky else hom_nay.year
    try:
        so_hd = str(tc.get("mau_so") or "{so:02d}/HĐLĐ-{nam}").format(so=int(tc.get("so_bat_dau") or 1) + so_thu_tu, nam=nam_so)
    except Exception:
        so_hd = f"{int(tc.get('so_bat_dau') or 1) + so_thu_tu:02d}/HĐLĐ-{nam_so}"
    gan = bool(tc.get("gan_chu_ky", True)) and bool(chu_ky)
    anh_nld = tim_chu_ky(chu_ky, nv) if gan else ""
    anh_gd = (chu_ky.get("giam_doc") or "") if gan else ""
    ong_ba_ky = tc.get("ong_ba_ky") or "Ông/Bà"
    ong_ba = {"Nam": "Ông", "Nữ": "Bà"}.get(nv.get("gioi_tinh"), "Ông/Bà")
    h = ['<section class="vb-trang">', _tieu_ngu(cty, so_hd, tc.get("dia_danh"), ngay_ky),
         _p("&nbsp;"), _p("<b>HỢP ĐỒNG LAO ĐỘNG</b>", "c b"), _p(f"<b>({esc(loai_ten.replace('Hợp đồng lao động ', '').capitalize())})</b>", "c"),
         _p("Căn cứ Bộ luật Lao động số 45/2019/QH14 ngày 20/11/2019 và Nghị định số 145/2020/NĐ-CP ngày 14/12/2020 của Chính phủ "
            "quy định chi tiết và hướng dẫn thi hành một số điều của Bộ luật Lao động về điều kiện lao động và quan hệ lao động;", "j ti"),
         _p("Hôm nay, " + esc(ngay_chu(ngay_ky)) + f", tại {esc(tc.get('dia_diem') or cty.get('dia_chi') or '..........')}, chúng tôi gồm:", "j ti"),
         _p("<b>Người sử dụng lao động</b> (sau đây gọi là Công ty):"),
         _p(f"{esc(ong_ba_ky)}: <b>{esc((tc.get('nguoi_ky') or '').upper())}</b>&nbsp;&nbsp;&nbsp;Quốc tịch: Việt Nam", "l1"),
         _p(f"Chức vụ: {esc(tc.get('chuc_danh_ky') or 'Giám đốc')}", "l1"),
         _p(f"Đại diện cho: <b>{esc((cty.get('ten') or '').upper())}</b>" + (f" — Mã số thuế: {esc(cty['mst'])}" if cty.get("mst") else ""), "l1"),
         _p(f"Địa chỉ: {esc(cty.get('dia_chi') or '')}", "l1")]
    if tc.get("dien_thoai"):
        h.append(_p(f"Điện thoại: {esc(tc['dien_thoai'])}", "l1"))
    h += [_p("<b>Người lao động</b> (sau đây gọi là Người lao động):"),
          _p(f"{esc(ong_ba)}: <b>{esc(nv['ten'].upper())}</b>&nbsp;&nbsp;&nbsp;Quốc tịch: {esc(tc.get('quoc_tich') or 'Việt Nam')}", "l1"),
          _p(f"Sinh ngày: {esc(nv.get('ngay_sinh') or '..../..../........')}" + (f"&nbsp;&nbsp;&nbsp;Giới tính: {esc(nv['gioi_tinh'])}" if nv.get("gioi_tinh") else ""), "l1"),
          _p(f"Nơi cư trú: {esc(nv.get('dia_chi') or '..............................')}", "l1")]
    cccd = nv.get("cccd")
    noi_cap = tc.get("noi_cap_cccd") if (cccd and len(re.sub(r"\D", "", cccd)) == 12) else "........................"
    h.append(_p(f"Số CCCD/CMND: {esc(cccd or '............')}, cấp ngày: {esc(nv.get('ngay_cap') or '..../..../........')}, nơi cấp: {esc(noi_cap)}", "l1"))
    h.append(_p("Hai bên thỏa thuận ký kết hợp đồng lao động và cam kết thực hiện đúng những điều khoản sau đây:", "j ti"))

    # Điều 1
    cv = (tc.get("cong_viec") or "").strip() or f"Thực hiện các nhiệm vụ của chức danh {nv.get('chuc_vu') or '.........'} theo phân công, hướng dẫn của Người sử dụng lao động"
    h.append(_p("<b>Điều 1. Thời hạn hợp đồng, địa điểm, chức danh và công việc phải làm</b>"))
    if cuoi:
        h.append(_p(f"1. Loại hợp đồng lao động: {esc(loai_ten)}, thời hạn {thang} tháng, từ {esc(ngay_chu(bat_dau))} đến hết {esc(ngay_chu(cuoi))}.", "j"))
    else:
        h.append(_p(f"1. Loại hợp đồng lao động: {esc(loai_ten)}, có hiệu lực kể từ {esc(ngay_chu(bat_dau))}.", "j"))
    h.append(_p(f"2. Địa điểm làm việc: {esc(tc.get('dia_diem') or cty.get('dia_chi') or '')}.", "j"))
    if (tc.get("bo_phan") or "").strip():
        h.append(_p(f"3. Bộ phận làm việc: {esc(tc['bo_phan'])}.", "j"))
    h.append(_p(f"{4 if (tc.get('bo_phan') or '').strip() else 3}. Chức danh chuyên môn / chức vụ: {esc(nv.get('chuc_vu') or '..........')}.", "j"))
    h.append(_p(f"{5 if (tc.get('bo_phan') or '').strip() else 4}. Công việc phải làm: {esc(cv)}.", "j"))

    # Điều 2
    h += [_p("<b>Điều 2. Thời giờ làm việc, thời giờ nghỉ ngơi và điều kiện làm việc</b>"),
          _p(f"1. Thời giờ làm việc: {esc(tc.get('thoi_gio') or '')}.", "j"),
          _p("2. Thời giờ nghỉ ngơi: Người lao động được nghỉ giữa ca, nghỉ chuyển ca, nghỉ hằng tuần, nghỉ lễ, Tết, nghỉ hằng năm hưởng nguyên lương "
             "và nghỉ việc riêng theo quy định tại Điều 109 đến Điều 115 Bộ luật Lao động năm 2019 và nội quy lao động của Công ty.", "j"),
          _p("3. Công ty bảo đảm điều kiện an toàn, vệ sinh lao động; cấp phát dụng cụ, phương tiện bảo hộ lao động (nếu có) theo chính sách của Công ty và yêu cầu công việc.", "j")]

    # Điều 3 - quyền lợi
    luong = nv.get("luong_cb") or 0
    pc = [("Phụ cấp tiền cơm (ăn trưa/ăn ca)", nv.get("tien_com")), ("Phụ cấp xăng xe, đi lại", (nv.get("xang_xe") or 0) + (nv.get("di_lai") or 0)),
          ("Phụ cấp điện thoại", nv.get("dien_thoai")), ("Phụ cấp trang phục", nv.get("trang_phuc"))]
    pc = [(t, v) for t, v in pc if v and v > 0]
    h.append(_p("<b>Điều 3. Quyền lợi và nghĩa vụ của Người lao động</b>"))
    h.append(_p("<b>1. Quyền lợi:</b>"))
    n = 0

    def muc(txt):
        nonlocal n
        n += 1
        h.append(_p(f"{chr(96 + n)}) {txt}", "j l1"))
    muc(f"Mức lương theo công việc hoặc chức danh: <b>{so_tien(luong)} đồng/tháng</b> (bằng chữ: {esc(doc_so_thanh_chu(luong))}). "
        "Mức lương này không thấp hơn mức lương tối thiểu vùng theo quy định của pháp luật và phù hợp với thang lương, bảng lương của Công ty;")
    if pc:
        chi_tiet = ("; ".join(f"{esc(t)}: {so_tien(v)} đồng/tháng" for t, v in pc) + ". ") if tc.get("ghi_phu_cap") else ""
        muc("Phụ cấp lương và các khoản bổ sung khác: " + chi_tiet
            + "Các khoản phụ cấp được tính theo số ngày công thực tế đi làm trong tháng;")
    else:
        muc("Phụ cấp lương và các khoản bổ sung khác: không có, trừ trường hợp được Công ty quyết định bằng văn bản;")
    muc(f"Hình thức trả lương: {esc(tc.get('hinh_thuc_tra') or 'chuyển khoản')}; kỳ trả lương: hằng tháng, vào ngày {int(_so(tc.get('ngay_tra')) or 5):02d} của tháng sau;")
    muc("Tiền lương làm thêm giờ, làm việc vào ban đêm: được trả theo quy định tại Điều 98 Bộ luật Lao động năm 2019 và Quy chế lương, thưởng của Công ty;")
    muc("Tiền thưởng, chế độ nâng bậc, nâng lương: theo Quy chế lương, thưởng và thang lương, bảng lương của Công ty;")
    if nv.get("dong_bh"):
        muc(f"Bảo hiểm xã hội, bảo hiểm y tế, bảo hiểm thất nghiệp: Công ty và Người lao động cùng tham gia và đóng theo quy định của pháp luật; "
            f"mức tiền lương làm căn cứ đóng bảo hiểm là {so_tien(luong)} đồng/tháng, thay đổi khi hai bên thỏa thuận lại tiền lương hoặc khi pháp luật có quy định mới;")
    else:
        muc("Bảo hiểm xã hội, bảo hiểm y tế, bảo hiểm thất nghiệp: thực hiện theo quy định của pháp luật hiện hành;")
    muc("Chế độ nghỉ ngơi (nghỉ hằng tuần, nghỉ phép năm, nghỉ lễ, Tết...): theo quy định của Bộ luật Lao động và nội quy lao động của Công ty;")
    muc("Được trang bị bảo hộ lao động (nếu có), được đào tạo, bồi dưỡng nâng cao trình độ theo kế hoạch của Công ty và các quyền lợi khác theo quy định của pháp luật.")
    h += [_p("<b>2. Nghĩa vụ:</b>"),
          _p("a) Hoàn thành những công việc đã cam kết trong hợp đồng lao động;", "j l1"),
          _p("b) Chấp hành lệnh điều hành sản xuất, kinh doanh, nội quy lao động, quy chế của Công ty, quy định về an toàn, vệ sinh lao động và bảo vệ bí mật kinh doanh;", "j l1"),
          _p("c) Bồi thường thiệt hại, hoàn trả chi phí đào tạo (nếu có) theo quy định tại Điều 62, Điều 129 và Điều 130 Bộ luật Lao động năm 2019 và nội quy lao động của Công ty;", "j l1"),
          _p(f"d) Khi đơn phương chấm dứt hợp đồng lao động phải tuân thủ Điều 35 Bộ luật Lao động năm 2019, trong đó phải báo trước cho Công ty ít nhất {esc(bao_truoc)}.", "j l1")]

    # Điều 4
    h += [_p("<b>Điều 4. Quyền hạn và nghĩa vụ của Người sử dụng lao động</b>"),
          _p("1. Quyền hạn: Điều hành Người lao động hoàn thành công việc theo hợp đồng (bố trí, điều chuyển, tạm ngừng việc); khen thưởng, xử lý vi phạm kỷ luật lao động "
             "theo quy định của pháp luật và nội quy lao động; tạm hoãn, chấm dứt hợp đồng lao động theo quy định của pháp luật.", "j"),
          _p("2. Nghĩa vụ: Bảo đảm việc làm và thực hiện đầy đủ những điều đã cam kết trong hợp đồng lao động; thanh toán đầy đủ, đúng thời hạn các chế độ và quyền lợi "
             "cho Người lao động; đóng bảo hiểm xã hội, bảo hiểm y tế, bảo hiểm thất nghiệp và khấu trừ, nộp thuế thu nhập cá nhân theo quy định của pháp luật.", "j")]

    # Điều 5
    h += [_p("<b>Điều 5. Điều khoản thi hành</b>"),
          _p("1. Những vấn đề về lao động không ghi trong hợp đồng lao động này thì áp dụng theo thỏa ước lao động tập thể (nếu có) hoặc quy định của pháp luật lao động.", "j"),
          _p("2. Khi một bên có yêu cầu thay đổi nội dung hợp đồng phải báo cho bên kia biết trước ít nhất 03 ngày làm việc; việc sửa đổi, bổ sung được lập bằng phụ lục hợp đồng lao động.", "j"),
          _p(f"3. Hợp đồng lao động được làm thành 02 bản có giá trị pháp lý như nhau, mỗi bên giữ 01 bản và có hiệu lực kể từ {esc(ngay_chu(bat_dau))}.", "j"),
          _p("&nbsp;"),
          _bang_ky("NGƯỜI LAO ĐỘNG", "(Ký, ghi rõ họ tên)", nv["ten"], "NGƯỜI SỬ DỤNG LAO ĐỘNG", f"({tc.get('chuc_danh_ky') or 'Giám đốc'} — Ký, ghi rõ họ tên, đóng dấu)", tc.get("nguoi_ky") or "",
                   anh_nld, anh_gd),
          "</section>"]
    # Người có mã phiên bản (gốc-001...) đổi lương trong năm: mỗi lần đổi lương 1 PHỤ LỤC HỢP ĐỒNG ghi nhận mức lương mới + ngày áp dụng (Điều 22, 33 BLLĐ 2019)
    pl = [x for x in (nv.get("phu_luc") or []) if x["tu"] > bat_dau and (cuoi is None or x["tu"] <= cuoi)]
    h.append(dung_phu_luc_nhieu(nv, cty, tuy_chon, so_hd, ngay_ky, pl, chu_ky, hom_nay))
    return "".join(h)


def dung_phu_luc_nhieu(nv, cty, tuy_chon, so_hd, ngay_ky_hd, ds_pl, chu_ky=None, hom_nay=None):
    """Các PHỤ LỤC điều chỉnh lương của 1 người cho Hợp đồng lao động số `so_hd` (ký ngày `ngay_ky_hd`). Số phụ lục: <thứ tự trong năm>/<năm>/PL-<số HĐ>."""
    tc = gop_tuy_chon(cty, tuy_chon, hom_nay)
    gan = bool(tc.get("gan_chu_ky", True)) and bool(chu_ky)
    anh_nld = tim_chu_ky(chu_ky, nv) if gan else ""
    anh_gd = (chu_ky.get("giam_doc") or "") if gan else ""
    dem, kq = {}, []
    for x in ds_pl or []:
        dem[x["tu"].year] = dem.get(x["tu"].year, 0) + 1
        kq.append(dung_phu_luc_hop_dong(x, nv, cty, tc, so_hd, ngay_ky_hd, f"{dem[x['tu'].year]:02d}/{x['tu'].year}/PL-{so_hd}", anh_nld, anh_gd))
    return "".join(kq)


def dung_phu_luc_hop_dong(dc, nv, cty, tc, so_hd, ngay_ky_hd, so_pl, anh_nld="", anh_gd=""):
    """HTML 1 PHỤ LỤC HỢP ĐỒNG LAO ĐỘNG (1 <section>) về việc điều chỉnh mức lương: dc = {"tu": ngày áp dụng, "nv": phiên bản mới, "cu": phiên bản trước}.
    Ngày lập phụ lục = ngày áp dụng mức lương mới."""
    tu, moi, cu = dc["tu"], dc["nv"], dc["cu"]
    ong_ba_ky = tc.get("ong_ba_ky") or "Ông/Bà"
    ong_ba = {"Nam": "Ông", "Nữ": "Bà"}.get(nv.get("gioi_tinh"), "Ông/Bà")
    ngay_hd = dd_mm_yyyy(ngay_ky_hd) if ngay_ky_hd else "..../..../........"
    h = ['<section class="vb-trang">', _tieu_ngu(cty, so_pl, tc.get("dia_danh"), tu),
         _p("&nbsp;"), _p("<b>PHỤ LỤC HỢP ĐỒNG LAO ĐỘNG</b>", "c b"), _p("<b>(V/v điều chỉnh mức lương)</b>", "c"),
         _p("Căn cứ Bộ luật Lao động số 45/2019/QH14 ngày 20/11/2019 và Nghị định số 145/2020/NĐ-CP ngày 14/12/2020 của Chính phủ "
            "quy định chi tiết và hướng dẫn thi hành một số điều của Bộ luật Lao động về điều kiện lao động và quan hệ lao động;", "j ti"),
         _p(f"Căn cứ Hợp đồng lao động số {esc(so_hd)} ký ngày {esc(ngay_hd)} giữa Công ty và Người lao động;", "j ti"),
         _p("Căn cứ thỏa thuận của hai bên,", "j ti"),
         _p("Hôm nay, " + esc(ngay_chu(tu)) + f", tại {esc(tc.get('dia_diem') or cty.get('dia_chi') or '..........')}, chúng tôi gồm:", "j ti"),
         _p("<b>Người sử dụng lao động</b> (sau đây gọi là Công ty):"),
         _p(f"{esc(ong_ba_ky)}: <b>{esc((tc.get('nguoi_ky') or '').upper())}</b>&nbsp;&nbsp;&nbsp;Chức vụ: {esc(tc.get('chuc_danh_ky') or 'Giám đốc')}", "l1"),
         _p(f"Đại diện cho: <b>{esc((cty.get('ten') or '').upper())}</b>" + (f" — Mã số thuế: {esc(cty['mst'])}" if cty.get("mst") else ""), "l1"),
         _p(f"Địa chỉ: {esc(cty.get('dia_chi') or '')}", "l1"),
         _p("<b>Người lao động</b> (sau đây gọi là Người lao động):"),
         _p(f"{esc(ong_ba)}: <b>{esc(nv['ten'].upper())}</b>&nbsp;&nbsp;&nbsp;Sinh ngày: {esc(nv.get('ngay_sinh') or '..../..../........')}", "l1"),
         _p(f"Số CCCD/CMND: {esc(nv.get('cccd') or '............')}, cấp ngày: {esc(nv.get('ngay_cap') or '..../..../........')}", "l1"),
         _p(f"Hai bên thỏa thuận ký Phụ lục hợp đồng lao động này để sửa đổi, bổ sung Hợp đồng lao động số {esc(so_hd)} với các nội dung sau:", "j ti"),
         _p("<b>Điều 1. Nội dung điều chỉnh</b>"),
         _p(f"1. Điều chỉnh mức lương theo công việc hoặc chức danh quy định tại điểm a khoản 1 Điều 3 Hợp đồng lao động số {esc(so_hd)}:", "j"),
         _p(f"- Mức lương trước khi điều chỉnh: {so_tien(cu.get('luong_cb') or 0)} đồng/tháng;", "j l1"),
         _p(f"- Mức lương sau khi điều chỉnh: <b>{so_tien(moi.get('luong_cb') or 0)} đồng/tháng</b> (bằng chữ: {esc(doc_so_thanh_chu(moi.get('luong_cb') or 0))}).", "j l1")]
    n = 2
    if (moi.get("chuc_vu") or "").strip() and _chuan(moi.get("chuc_vu")) != _chuan(cu.get("chuc_vu")):
        h.append(_p(f"{n}. Chức danh chuyên môn / chức vụ: {esc(moi['chuc_vu'])}" + (f" (trước đây: {esc(cu['chuc_vu'])})" if (cu.get("chuc_vu") or "").strip() else "") + ".", "j"))
        n += 1
    h.append(_p(f"{n}. Thời gian áp dụng: kể từ <b>{esc(ngay_chu(tu))}</b>.", "j"))
    n += 1
    if moi.get("dong_bh"):
        h.append(_p(f"{n}. Mức tiền lương làm căn cứ đóng bảo hiểm xã hội, bảo hiểm y tế, bảo hiểm thất nghiệp kể từ ngày áp dụng là "
                    f"{so_tien(moi.get('luong_cb') or 0)} đồng/tháng.", "j"))
    h += [_p("<b>Điều 2. Điều khoản thi hành</b>"),
          _p(f"1. Các điều khoản khác của Hợp đồng lao động số {esc(so_hd)} không được sửa đổi trong Phụ lục này vẫn giữ nguyên hiệu lực thi hành.", "j"),
          _p(f"2. Phụ lục này là bộ phận không tách rời của Hợp đồng lao động số {esc(so_hd)}, có hiệu lực kể từ {esc(ngay_chu(tu))}; "
             "được lập thành 02 bản có giá trị pháp lý như nhau, mỗi bên giữ 01 bản.", "j"),
          _p("&nbsp;"),
          _bang_ky("NGƯỜI LAO ĐỘNG", "(Ký, ghi rõ họ tên)", nv["ten"], "NGƯỜI SỬ DỤNG LAO ĐỘNG", f"({tc.get('chuc_danh_ky') or 'Giám đốc'} — Ký, ghi rõ họ tên, đóng dấu)", tc.get("nguoi_ky") or "",
                   anh_nld, anh_gd),
          "</section>"]
    return "".join(h)


def dung_hop_dong_nhieu(ds_nv, cty, tuy_chon, hom_nay=None, nam=None, chu_ky=None):
    return "".join(dung_hop_dong(nv, cty, tuy_chon, i, hom_nay, nam, chu_ky) for i, nv in enumerate(ds_nv))



# ============================================================ HỢP ĐỒNG THỬ VIỆC (riêng) — Điều 24 đến Điều 27 Bộ luật Lao động 2019
_CONG_VIEC_KHAC = ("bao ve", "tap vu", "lao cong", "phuc vu", "giup viec", "dong goi", "boc xep", "ve sinh")      # thường là "công việc khác" (tối đa 06 ngày làm việc)


def khoang_thu_viec(nv, tc):
    """(từ, đến) ngày thử việc: ưu tiên ô 'Thử việc từ/đến' của người đó trong Danh Sách NV, không có thì lấy ô trên form. (None, None) nếu thiếu."""
    tu = ngay_date(nv.get("thu_viec_tu")) or ngay_date(tc.get("tv_tu"))
    den_k = doc_ngay(nv.get("thu_viec_den")) or doc_ngay(tc.get("tv_den"))
    den = None
    if den_k:
        import calendar
        d = den_k[2] or calendar.monthrange(den_k[0], den_k[1])[1]
        den = datetime.date(den_k[0], den_k[1], d)
    return tu, den


def kiem_tra_thu_viec(ds_nv, tuy_chon):
    """Cảnh báo khi lập hợp đồng thử việc: thời gian tối đa theo Điều 25, lương thử việc >= 85% (Điều 26), thiếu ngày."""
    tc = tuy_chon or {}
    kq = []
    try:
        pt = float(tc.get("tv_phan_tram") or 85)
    except Exception:
        pt = 85.0
    if pt < 85:
        kq.append({"muc": "loi", "nd": f"Lương thử việc {pt:g}% thấp hơn 85% mức lương chính thức — trái Điều 26 Bộ luật Lao động 2019."})
    for nv in ds_nv:
        tu, den = khoang_thu_viec(nv, tc)
        t = nv["ten"]
        if not tu or not den:
            kq.append({"muc": "loi", "nd": f"{t}: chưa có ngày bắt đầu/kết thúc thử việc (nhập cột 'Thử việc từ/đến' ở Danh Sách Nhân Viên hoặc ô trên màn hình)."})
            continue
        if den < tu:
            kq.append({"muc": "loi", "nd": f"{t}: ngày kết thúc thử việc trước ngày bắt đầu."})
            continue
        so_ngay = (den - tu).days + 1
        cv = _chuan(nv.get("chuc_vu"))
        if so_ngay > 180:
            kq.append({"muc": "loi", "nd": f"{t}: thử việc {so_ngay} ngày vượt tối đa 180 ngày (Điều 25 BLLĐ 2019, kể cả người quản lý doanh nghiệp)."})
        elif so_ngay > 6 and any(k in cv for k in _CONG_VIEC_KHAC):
            kq.append({"muc": "canh_bao", "nd": f"{t} ({nv.get('chuc_vu')}): công việc không đòi hỏi trình độ chuyên môn thường thuộc nhóm 'công việc khác' — thử việc tối đa 06 ngày làm việc, hiện ghi {so_ngay} ngày."})
        elif so_ngay > 60:
            kq.append({"muc": "canh_bao", "nd": f"{t}: thử việc {so_ngay} ngày — chỉ hợp lệ với công việc của người quản lý doanh nghiệp (tối đa 180 ngày); công việc cần trình độ cao đẳng trở lên tối đa 60 ngày."})
        elif so_ngay > 30:
            kq.append({"muc": "canh_bao", "nd": f"{t}: thử việc {so_ngay} ngày — chỉ hợp lệ với công việc cần trình độ cao đẳng trở lên (tối đa 60 ngày); trung cấp/công nhân kỹ thuật/nhân viên nghiệp vụ tối đa 30 ngày."})
    return kq


def dung_hop_dong_thu_viec(nv, cty, tuy_chon, so_thu_tu, hom_nay=None, nam=None, chu_ky=None):
    """HTML 1 HỢP ĐỒNG THỬ VIỆC (riêng) — không thuộc diện BHXH bắt buộc trong thời gian thử việc; lương thử việc >= 85% lương chính thức."""
    tc = gop_tuy_chon(cty, tuy_chon, hom_nay)
    hom_nay = hom_nay or datetime.date.today()
    tu, den = khoang_thu_viec(nv, tc)
    # chưa ghi ngày thử việc: lấy ngày ký trên form, không có thì ngày vào làm (vào làm trước năm lập -> 01/01 năm lập) — KHÔNG lấy ngày hôm nay
    # (đang lập năm 2025 mà hôm nay là 2026 thì hợp đồng thử việc không được nhảy sang năm 2026)
    tu = tu or ngay_date(tc.get("ngay_ky")) or ngay_bat_dau_theo_nam(nv.get("vao_lam"), nam) or (datetime.date(int(nam), 1, 1) if nam else hom_nay)
    so_ngay = ((den - tu).days + 1) if den else 0
    ngay_ky = ngay_date(tc.get("ngay_ky")) or tu
    try:
        pt = float(tc.get("tv_phan_tram") or 85)
    except Exception:
        pt = 85.0
    luong_cb = float(nv.get("luong_cb") or 0)
    luong_tv = round(luong_cb * pt / 100.0)
    so_hd = f"{int(tc.get('so_bat_dau') or 1) + so_thu_tu:02d}/HĐTV-{ngay_ky.year}"
    gan = bool(tc.get("gan_chu_ky", True)) and bool(chu_ky)
    anh_nld = tim_chu_ky(chu_ky, nv) if gan else ""
    anh_gd = (chu_ky.get("giam_doc") or "") if gan else ""
    ong_ba_ky = tc.get("ong_ba_ky") or "Ông/Bà"
    ong_ba = {"Nam": "Ông", "Nữ": "Bà"}.get(nv.get("gioi_tinh"), "Ông/Bà")
    cv = (tc.get("tv_cong_viec") or "").strip() or f"Thực hiện các nhiệm vụ của chức danh {nv.get('chuc_vu') or '.........'} theo phân công, hướng dẫn của Người sử dụng lao động"
    cccd = nv.get("cccd") or ""
    noi_cap = tc.get("noi_cap_cccd") if len(re.sub(r"\D", "", cccd)) == 12 else "........................"
    h = ['<section class="vb-trang">', _tieu_ngu(cty, so_hd, tc.get("dia_danh"), ngay_ky), _p("&nbsp;"), _p("<b>HỢP ĐỒNG THỬ VIỆC</b>", "c b"),
         _p("Căn cứ Bộ luật Lao động số 45/2019/QH14 ngày 20/11/2019 (Điều 24 đến Điều 27) và Nghị định số 145/2020/NĐ-CP ngày 14/12/2020 của Chính phủ;", "j ti"),
         _p("Hôm nay, " + esc(ngay_chu(ngay_ky)) + f", tại {esc(tc.get('dia_diem') or cty.get('dia_chi') or '..........')}, chúng tôi gồm:", "j ti"),
         _p("<b>Người sử dụng lao động</b> (sau đây gọi là Công ty):"),
         _p(f"{esc(ong_ba_ky)}: <b>{esc((tc.get('nguoi_ky') or '').upper())}</b>&nbsp;&nbsp;&nbsp;Quốc tịch: Việt Nam", "l1"),
         _p(f"Chức vụ: {esc(tc.get('chuc_danh_ky') or 'Giám đốc')}", "l1"),
         _p(f"Đại diện cho: <b>{esc((cty.get('ten') or '').upper())}</b>" + (f" — Mã số thuế: {esc(cty['mst'])}" if cty.get("mst") else ""), "l1"),
         _p(f"Địa chỉ: {esc(cty.get('dia_chi') or '')}", "l1"),
         _p("<b>Người lao động thử việc</b> (sau đây gọi là Người thử việc):"),
         _p(f"{esc(ong_ba)}: <b>{esc(nv['ten'].upper())}</b>&nbsp;&nbsp;&nbsp;Quốc tịch: {esc(tc.get('quoc_tich') or 'Việt Nam')}", "l1"),
         _p(f"Sinh ngày: {esc(nv.get('ngay_sinh') or '..../..../........')}" + (f"&nbsp;&nbsp;&nbsp;Giới tính: {esc(nv['gioi_tinh'])}" if nv.get("gioi_tinh") else ""), "l1"),
         _p(f"Nơi cư trú: {esc(nv.get('dia_chi') or '..............................')}", "l1"),
         _p(f"Số CCCD/CMND: {esc(nv.get('cccd') or '............')}, cấp ngày: {esc(nv.get('ngay_cap') or '..../..../........')}, nơi cấp: {esc(noi_cap)}", "l1"),
         _p("Hai bên thỏa thuận ký kết hợp đồng thử việc và cam kết thực hiện đúng những điều khoản sau đây:", "j ti"),
         _p("<b>Điều 1. Công việc, địa điểm và thời gian thử việc</b>"),
         _p(f"1. Chức danh, công việc thử việc: {esc(nv.get('chuc_vu') or '..........')} — {esc(cv)}.", "j"),
         _p(f"2. Địa điểm làm việc: {esc(tc.get('dia_diem') or cty.get('dia_chi') or '')}.", "j"),
         _p(f"3. Thời gian thử việc: từ {esc(ngay_chu(tu))} đến hết {esc(ngay_chu(den)) if den else 'ngày ..... tháng ..... năm ........'}.", "j"),
         _p("4. Người thử việc chỉ thử việc một lần đối với một công việc theo Điều 25 Bộ luật Lao động năm 2019.", "j"),
         _p("<b>Điều 2. Tiền lương và chế độ trong thời gian thử việc</b>"),
         _p(f"1. Tiền lương thử việc: <b>{so_tien(luong_tv)} đồng/tháng</b> (bằng chữ: {esc(doc_so_thanh_chu(luong_tv))}), "
            + ("theo mức lương cơ bản trong bảng lương" if pt == 100 else f"bằng {pt:g}% mức lương cơ bản trong bảng lương ({so_tien(luong_cb)} đồng/tháng)")
            + ", không thấp hơn 85% mức lương của công việc đó (Điều 26 Bộ luật Lao động năm 2019). Tiền lương được tính theo số ngày công thực tế đi làm.", "j"),
         _p(f"2. Hình thức trả lương: {esc(tc.get('hinh_thuc_tra') or 'chuyển khoản')}; trả vào ngày {int(_so(tc.get('ngay_tra')) or 5):02d} của tháng sau hoặc ngay khi kết thúc thử việc.", "j"),
         _p("3. Phụ cấp lương và các khoản bổ sung khác: Các khoản phụ cấp được tính theo số ngày công thực tế đi làm trong tháng;", "j"),
         _p("4. Thời giờ làm việc, thời giờ nghỉ ngơi, an toàn lao động: theo quy định của pháp luật và nội quy lao động của Công ty.", "j"),
         _p("5. Hợp đồng thử việc này là hợp đồng riêng; trong thời gian thử việc Người thử việc không thuộc đối tượng tham gia bảo hiểm xã hội bắt buộc. Thuế thu nhập cá nhân được khấu trừ theo quy định của pháp luật về thuế đối với người thử việc.", "j"),
         _p("<b>Điều 3. Quyền và nghĩa vụ của Người thử việc</b>"),
         _p("1. Được hưởng tiền lương thử việc, được cung cấp thông tin, điều kiện làm việc, bảo hộ lao động (nếu có) theo yêu cầu công việc.", "j"),
         _p("2. Thực hiện công việc được giao, chấp hành nội quy lao động, quy chế của Công ty; bảo mật thông tin kinh doanh.", "j"),
         _p("3. Trong thời gian thử việc, mỗi bên có quyền hủy bỏ thỏa thuận thử việc mà không cần báo trước và không phải bồi thường nếu việc làm thử không đạt yêu cầu (Điều 27 Bộ luật Lao động năm 2019).", "j"),
         _p("<b>Điều 4. Quyền và nghĩa vụ của Người sử dụng lao động</b>"),
         _p("1. Hướng dẫn, kiểm tra, đánh giá kết quả công việc thử việc; trả lương đầy đủ, đúng hạn cho Người thử việc.", "j"),
         _p("2. Kết thúc thời gian thử việc, thông báo kết quả cho Người thử việc.", "j"),
         _p("<b>Điều 5. Kết thúc thử việc</b>"),
         _p("1. Khi kết thúc thời gian thử việc, nếu việc làm thử đạt yêu cầu thì Công ty giao kết hợp đồng lao động với Người thử việc; từ thời điểm hợp đồng lao động có hiệu lực, hai bên thực hiện đóng bảo hiểm xã hội, bảo hiểm y tế, bảo hiểm thất nghiệp theo quy định.", "j"),
         _p("2. Nếu việc làm thử không đạt yêu cầu thì hợp đồng thử việc chấm dứt, hai bên không có nghĩa vụ bồi thường.", "j"),
         _p("<b>Điều 6. Điều khoản thi hành</b>"),
         _p(f"Hợp đồng thử việc được làm thành 02 bản có giá trị pháp lý như nhau, mỗi bên giữ 01 bản và có hiệu lực kể từ {esc(ngay_chu(tu))}.", "j"),
         _p("&nbsp;"),
         _bang_ky("NGƯỜI THỬ VIỆC", "(Ký, ghi rõ họ tên)", nv["ten"], "NGƯỜI SỬ DỤNG LAO ĐỘNG", f"({tc.get('chuc_danh_ky') or 'Giám đốc'} — Ký, ghi rõ họ tên, đóng dấu)", tc.get("nguoi_ky") or "", anh_nld, anh_gd),
         "</section>"]
    return "".join(h)


def dung_hop_dong_thu_viec_nhieu(ds_nv, cty, tuy_chon, hom_nay=None, nam=None, chu_ky=None):
    return "".join(dung_hop_dong_thu_viec(nv, cty, tuy_chon, i, hom_nay, nam, chu_ky) for i, nv in enumerate(ds_nv))


def _khoang(giatri):
    """[1000000, 1000000] -> '1.000.000'; [1000000, 2000000] -> '1.000.000 – 2.000.000'; toàn 0 -> '-'."""
    gt = [int(round(x)) for x in giatri]
    if not gt or max(gt) == 0:
        return "-"
    return so_tien(min(gt)) if min(gt) == max(gt) else f"{so_tien(min(gt))} – {so_tien(max(gt))}"


def dung_quy_che(nv_list, cty, tuy_chon, ts=None, nam=None, hom_nay=None, chu_ky=None):
    """HTML Quyết định ban hành Quy chế lương, thưởng, phụ cấp — số liệu lấy từ Bảng Lương + Danh Sách Nhân Viên."""
    tc = gop_tuy_chon(cty, tuy_chon, hom_nay)
    hom_nay = hom_nay or datetime.date.today()
    ngay = ngay_date(tc.get("ngay"), hom_nay)
    nam_du_lieu = nam or ngay.year       # năm của Bảng Lương dùng làm số liệu
    nam = ngay.year                      # văn bản pháp luật + lương tối thiểu vùng áp dụng theo NGÀY BAN HÀNH quy chế
    ts = ts or {}
    bh_dn, bh_nld = ts.get("bh_dn") or {"bhxh": 17.5, "bhyt": 3.0, "bhtn": 1.0}, ts.get("bh_nld") or {"bhxh": 8.0, "bhyt": 1.5, "bhtn": 1.0}
    cong_chuan = int(_so(ts.get("ngay_cong_chuan")) or 26)
    vung = int(tc.get("vung", 1))
    ltt = luong_toi_thieu_vung(nam, vung)
    dang_lam = [n for n in nv_list if not n.get("da_nghi")] or nv_list
    nhom = nhom_chuc_danh(dang_lam)
    ten_cty = (cty.get("ten") or "").upper()
    buoc = f"{float(tc.get('buoc_pct', 5)):g}".replace(".", ",")

    def pct(d):
        return f"{float(d):g}".replace(".", ",")
    h = ['<section class="vb-trang">', _tieu_ngu(cty, tc.get("so_qd"), tc.get("dia_danh"), ngay),
         _p("&nbsp;"), _p("<b>QUYẾT ĐỊNH</b>", "c b"),
         _p("<b>Về việc ban hành Quy chế lương, thưởng, phụ cấp và các chế độ đối với người lao động</b>", "c"),
         _p(f"<b>{esc(tc.get('chuc_danh_ky') or 'GIÁM ĐỐC').upper()} {esc(ten_cty)}</b>", "c"),
         _p("Căn cứ Bộ luật Lao động số 45/2019/QH14 ngày 20/11/2019;", "j ti"),
         _p("Căn cứ Nghị định số 145/2020/NĐ-CP ngày 14/12/2020 của Chính phủ quy định chi tiết và hướng dẫn thi hành một số điều của Bộ luật Lao động về điều kiện lao động và quan hệ lao động;", "j ti"),
         _p(f"Căn cứ {esc(van_ban_luong_toi_thieu(nam))};", "j ti"),
         _p(f"Căn cứ {esc(van_ban_bhxh(ngay))} và các văn bản hướng dẫn thi hành;", "j ti"),
         _p(f"Căn cứ {esc(van_ban_thue(ngay))};", "j ti"),
         _p("Căn cứ Luật Doanh nghiệp số 59/2020/QH14 ngày 17/6/2020, Điều lệ tổ chức và hoạt động của Công ty;", "j ti"),
         _p("Căn cứ thang lương, bảng lương và tình hình thực tế sử dụng lao động, trả lương của Công ty;", "j ti"),
         _p("<b>QUYẾT ĐỊNH:</b>", "c"),
         _p(f"<b>Điều 1.</b> Ban hành kèm theo Quyết định này Quy chế lương, thưởng, phụ cấp và các chế độ đối với người lao động của {esc(cty.get('ten') or 'Công ty')} "
            "(sau đây gọi là Công ty), gồm các nội dung dưới đây.", "j ti"),
         _p("<b>Điều 2.</b> Quyết định này có hiệu lực kể từ ngày ký. Các Phòng/Bộ phận, kế toán và toàn thể người lao động chịu trách nhiệm thi hành Quyết định này.", "j ti"),
         '<p class="pb">&nbsp;</p>',
         _p("<b>QUY CHẾ LƯƠNG, THƯỞNG, PHỤ CẤP</b>", "c b"),
         _p("<b>Chương I. QUY ĐỊNH CHUNG</b>"),
         _p("<b>Điều 1. Đối tượng và phạm vi áp dụng</b>"),
         _p(f"Quy chế này áp dụng đối với toàn bộ người lao động làm việc theo hợp đồng lao động tại Công ty (hiện có {len(dang_lam)} người lao động trong danh sách lương).", "j ti"),
         _p("<b>Điều 2. Mục đích</b>"),
         _p("1. Quy định việc trả lương, thưởng, phụ cấp cho từng cá nhân, từng bộ phận nhằm khuyến khích người lao động hoàn thành tốt công việc theo chức danh và đóng góp vào kế hoạch sản xuất, kinh doanh của Công ty.", "j ti"),
         _p("2. Bảo đảm đời sống, quyền lợi của người lao động; thực hiện đúng quy định của pháp luật lao động, bảo hiểm xã hội và thuế về tiền lương, tiền thưởng.", "j ti"),
         _p("<b>Điều 3. Nguyên tắc trả lương, thưởng</b>"),
         _p("1. Tiền lương được trả theo công việc hoặc chức danh, trên cơ sở thỏa thuận trong hợp đồng lao động và thang lương, bảng lương của Công ty; làm công việc gì, giữ chức danh gì thì hưởng lương theo công việc, chức danh đó. Khi thay đổi công việc, chức danh thì hưởng lương theo công việc, chức danh mới.", "j ti"),
         _p("2. Công ty bảo đảm trả lương bình đẳng, không phân biệt đối xử về giới tính đối với người lao động làm công việc có giá trị như nhau; trả lương trực tiếp, đầy đủ và đúng thời hạn.", "j ti"),
         _p("3. Tiền thưởng, phụ cấp, hỗ trợ được chi theo kết quả sản xuất, kinh doanh của Công ty và mức độ hoàn thành công việc của người lao động theo quy định tại Quy chế này.", "j ti"),
         _p("<b>Chương II. TIỀN LƯƠNG, PHỤ CẤP</b>"),
         _p("<b>Điều 4. Các loại tiền lương</b>"),
         _p(f"1. Lương theo công việc hoặc chức danh (lương cơ bản): là mức lương ghi trong hợp đồng lao động, được xếp theo thang lương, bảng lương của Công ty; mức thấp nhất không thấp hơn mức lương tối thiểu vùng quy định tại {esc(van_ban_luong_toi_thieu(nam))} "
            f"(hiện áp dụng mức {so_tien(ltt)} đồng/tháng đối với vùng {vung}). Mức lương cơ bản là căn cứ đóng bảo hiểm xã hội, bảo hiểm y tế, bảo hiểm thất nghiệp.", "j ti"),
         _p("2. Lương thử việc (nếu có): bằng ít nhất 85% mức lương của công việc đó (Điều 26 Bộ luật Lao động năm 2019).", "j ti"),
         _p("3. Tiền lương làm thêm giờ, làm việc vào ban đêm: trả theo Điều 7 của Quy chế này.", "j ti"),
         _p("<b>Điều 5. Phụ cấp, trợ cấp, hỗ trợ</b>"),
         _p("1. Ngoài lương cơ bản, tùy theo tính chất công việc, điều kiện làm việc và khả năng của Công ty, người lao động có thể được hưởng các khoản phụ cấp lương, trợ cấp, hỗ trợ khác "
            "như phụ cấp trách nhiệm, tiền ăn, đi lại, điện thoại, trang phục... Đối tượng, mức hưởng cụ thể được ghi trong hợp đồng lao động hoặc quyết định của Người sử dụng lao động.", "j ti"),
         _p("2. Các khoản phụ cấp, hỗ trợ được tính theo số ngày công thực tế đi làm trong tháng (mức phụ cấp ÷ số ngày công chuẩn của tháng × số ngày công thực tế), "
            "không dùng làm căn cứ đóng bảo hiểm xã hội trừ trường hợp pháp luật có quy định khác.", "j ti"),
         _p("3. Việc tính hoặc không tính các khoản phụ cấp, hỗ trợ vào thu nhập chịu thuế thu nhập cá nhân thực hiện theo quy định của pháp luật về thuế.", "j ti"),
          _p("<b>Điều 6. Cách tính lương</b>"),
          _p(f"1. Số ngày công chuẩn của tháng là số ngày làm việc tiêu chuẩn trong tháng theo lịch (tổng số ngày trong tháng trừ ngày nghỉ hằng tuần và ngày nghỉ lễ, Tết hưởng nguyên lương); "
             f"nếu không xác định theo lịch thì tính {cong_chuan} ngày/tháng.", "j ti"),
          _p("2. Căn cứ bảng chấm công hằng tháng, tiền lương thực nhận được tính như sau:", "j ti"),
          _p("<b>Tiền lương theo ngày công = (Lương cơ bản + các khoản phụ cấp) ÷ Số ngày công chuẩn × Số ngày công thực tế</b>", "c"),
          _p("<b>Thu nhập thực nhận = Tiền lương theo ngày công + Tiền lương làm thêm giờ + Tiền thưởng (nếu có) − Bảo hiểm xã hội, y tế, thất nghiệp phần người lao động − Thuế thu nhập cá nhân (nếu có)</b>", "c")]
    vd = next((n for n in dang_lam if n["luong_cb"] > 0 and tong_phu_cap(n) > 0), None) or next((n for n in dang_lam if n["luong_cb"] > 0), None)
    if vd:
        lam = max(1, cong_chuan - 1)
        pc_vd = tong_phu_cap(vd)
        tien = (vd["luong_cb"] + pc_vd) / cong_chuan * lam
        h.append(_p(f"Ví dụ: Chức danh {esc(vd.get('chuc_vu') or '..........')} có lương cơ bản {so_tien(vd['luong_cb'])} đồng, phụ cấp {so_tien(pc_vd)} đồng/tháng; "
                    f"tháng có {cong_chuan} ngày công chuẩn, đi làm thực tế {lam} ngày thì tiền lương theo ngày công = "
                    f"({so_tien(vd['luong_cb'])} + {so_tien(pc_vd)}) ÷ {cong_chuan} × {lam} = {so_tien(tien)} đồng.", "j i"))
    h += [_p(f"3. Bảo hiểm bắt buộc: người sử dụng lao động đóng {pct(bh_dn['bhxh'])}% bảo hiểm xã hội (gồm cả bảo hiểm tai nạn lao động, bệnh nghề nghiệp), {pct(bh_dn['bhyt'])}% bảo hiểm y tế, "
             f"{pct(bh_dn['bhtn'])}% bảo hiểm thất nghiệp; người lao động đóng {pct(bh_nld['bhxh'])}% bảo hiểm xã hội, {pct(bh_nld['bhyt'])}% bảo hiểm y tế, {pct(bh_nld['bhtn'])}% bảo hiểm thất nghiệp "
             "trên mức lương cơ bản ghi trong hợp đồng lao động, theo quy định của pháp luật bảo hiểm tại từng thời điểm.", "j ti"),
          _p("4. Thuế thu nhập cá nhân: Công ty khấu trừ thuế thu nhập cá nhân từ tiền lương, tiền công của người lao động và kê khai, nộp theo quy định của pháp luật về thuế; "
             "người lao động có người phụ thuộc đăng ký giảm trừ gia cảnh theo quy định.", "j ti"),
          _p("<b>Điều 7. Tiền lương làm thêm giờ</b>"),
          _p("1. Tiền lương giờ = Tiền lương của công việc đang làm (không gồm tiền lương làm thêm giờ, tiền thưởng và các khoản không phải là tiền lương) ÷ (Số ngày công chuẩn × 08 giờ).", "j ti"),
          _p("2. Tiền lương làm thêm giờ = Tiền lương giờ × mức tối thiểu 150% (ngày thường); 200% (ngày nghỉ hằng tuần); 300% (ngày nghỉ lễ, Tết, chưa kể tiền lương ngày lễ, Tết) × Số giờ làm thêm. "
             "Làm thêm vào ban đêm được trả thêm theo Điều 98 Bộ luật Lao động năm 2019.", "j ti"),
          _p("3. Số giờ làm thêm không quá 50% số giờ làm việc bình thường trong 01 ngày, không quá 40 giờ trong 01 tháng và không quá 200 giờ trong 01 năm (Điều 107 Bộ luật Lao động năm 2019); "
             "chỉ thực hiện khi được người lao động đồng ý.", "j ti"),
          _p("<b>Điều 8. Thời hạn và hình thức trả lương</b>"),
          _p(f"1. Tiền lương được trả hằng tháng một lần vào ngày {int(_so(tc.get('ngay_tra')) or 5):02d} của tháng sau, bằng hình thức {esc(tc.get('hinh_thuc_tra') or 'chuyển khoản')}.", "j ti"),
          _p("2. Trường hợp trả lương chậm do nguyên nhân bất khả kháng thì không được chậm quá 30 ngày; nếu chậm từ 15 ngày trở lên, Công ty phải đền bù cho người lao động khoản tiền ít nhất bằng số tiền lãi của số tiền trả chậm theo quy định của pháp luật.", "j ti"),
          _p("3. Mỗi lần trả lương, Công ty cung cấp cho người lao động bảng kê trả lương ghi rõ tiền lương, tiền lương làm thêm giờ, các khoản khấu trừ (nếu có) (Điều 95 Bộ luật Lao động năm 2019).", "j ti"),
          _p("<b>Điều 9. Chế độ nâng bậc, nâng lương</b>"),
          _p(f"1. Việc nâng bậc lương thực hiện theo hệ thống thang lương, bảng lương của Công ty, trong đó mức lương mỗi bậc cao hơn bậc liền kề trước {buoc}%.", "j ti"),
          _p("2. Người lao động được xét nâng bậc lương khi đủ 12 tháng giữ bậc lương hiện hưởng, hoàn thành tốt nhiệm vụ được giao và không bị xử lý kỷ luật lao động từ hình thức khiển trách bằng văn bản trở lên.", "j ti"),
          _p("3. Bộ phận nhân sự tổng hợp danh sách đủ điều kiện, trình Người sử dụng lao động quyết định bằng văn bản; mức lương sau nâng không thấp hơn mức lương tối thiểu vùng.", "j ti"),
          _p("<b>Điều 10. Chế độ nghỉ lễ, nghỉ việc riêng hưởng nguyên lương</b>"),
          _p("1. Nghỉ lễ, Tết hưởng nguyên lương (Điều 112 Bộ luật Lao động năm 2019): Tết Dương lịch 01 ngày; Tết Âm lịch 05 ngày; Ngày Chiến thắng (30/4) 01 ngày; Quốc tế lao động (01/5) 01 ngày; "
             "Quốc khánh 02 ngày (02/9 và 01 ngày liền kề); Ngày Giỗ Tổ Hùng Vương (10/3 âm lịch) 01 ngày. Người lao động là người nước ngoài được nghỉ thêm 01 ngày Tết cổ truyền dân tộc và 01 ngày Quốc khánh của nước họ.", "j ti"),
          _p("2. Nghỉ việc riêng hưởng nguyên lương (Điều 115 Bộ luật Lao động năm 2019): kết hôn nghỉ 03 ngày; con đẻ, con nuôi kết hôn nghỉ 01 ngày; cha đẻ, mẹ đẻ, cha nuôi, mẹ nuôi của mình hoặc của vợ (chồng), vợ hoặc chồng, "
             "con đẻ, con nuôi chết nghỉ 03 ngày; ông bà nội, ngoại chết, cha hoặc mẹ, anh, chị, em ruột chết, cha hoặc mẹ kết hôn, anh, chị, em ruột kết hôn nghỉ 01 ngày; người lao động phải thông báo cho Công ty.", "j ti"),
          _p("3. Nghỉ hằng năm: người lao động có đủ 12 tháng làm việc được nghỉ 12 ngày làm việc hưởng nguyên lương (Điều 113 Bộ luật Lao động năm 2019).", "j ti"),
          _p("<b>Điều 11. Chế độ thưởng và các khoản hỗ trợ</b>")]
    pl = tc["phuc_loi"]

    def bat(k):
        return bool((pl.get(k) or {}).get("bat"))

    def mv(k, i):
        return so_tien(_so((pl.get(k) or {}).get("m%d" % i)))
    stt = 0

    def khoan(txt):
        nonlocal stt
        stt += 1
        h.append(_p(f"{stt}. {txt}", "j ti"))
    khoan("Thưởng được thực hiện theo Điều 104 Bộ luật Lao động năm 2019: căn cứ kết quả sản xuất, kinh doanh, mức độ hoàn thành công việc của người lao động và Quy chế thưởng của Công ty. "
          "Mức thưởng cụ thể do Người sử dụng lao động quyết định bằng văn bản tại thời điểm chi thưởng.")
    if bat("cuoi_nam"):
        khoan("Thưởng cuối năm: căn cứ kết quả hoạt động kinh doanh, nếu có lãi Công ty trích từ lợi nhuận để thưởng; mức thưởng từng người tùy thuộc đóng góp, chất lượng công tác và việc chấp hành nội quy, quy định của Công ty.")
    if bat("tham_nien"):
        khoan("Thưởng thâm niên: người lao động có thời gian làm việc từ 02 năm trở lên được xét thưởng thâm niên; mức thưởng do Người sử dụng lao động quyết định hằng năm theo kết quả kinh doanh.")
    if bat("thuong_le"):
        khoan(f"Thưởng sinh nhật và các ngày lễ: mức từ {mv('thuong_le', 1)} đồng đến {mv('thuong_le', 2)} đồng/lần tùy kết quả kinh doanh và sự đóng góp của người lao động.")
    if bat("hieu_hy"):
        khoan(f"Hỗ trợ hiếu, hỷ: bản thân người lao động {mv('hieu_hy', 1)} đồng/người/lần; vợ, chồng, bố mẹ, anh chị em ruột {mv('hieu_hy', 2)} đồng/người/lần.")
    if bat("om_dau"):
        khoan(f"Hỗ trợ thiên tai, tai nạn, ốm đau: bản thân người lao động {mv('om_dau', 1)} đồng/người/lần; vợ, chồng, bố mẹ, anh chị em ruột {mv('om_dau', 2)} đồng/người/lần.")
    if bat("cong_tac_phi"):
        khoan(f"Công tác phí: đi công tác trong ngày được hỗ trợ {mv('cong_tac_phi', 1)} đồng/ngày; chi phí vé máy bay, tàu xe, lưu trú được thanh toán theo hóa đơn, chứng từ hợp lệ.")
    if bat("du_lich"):
        khoan("Hỗ trợ du lịch, nghỉ mát: hằng năm căn cứ kết quả kinh doanh, Người sử dụng lao động quyết định thời gian, địa điểm và mức chi.")
    if bat("hoc_phi"):
        khoan("Hỗ trợ học phí đào tạo: khi công việc, chức danh đòi hỏi người lao động phải được đào tạo thì Công ty chi trả học phí theo hóa đơn, chứng từ thực tế của khóa học.")
    h += [_p("<b>Điều 12. Tổ chức thực hiện</b>"),
          _p("1. Quy chế này được xây dựng sau khi tham khảo ý kiến tổ chức đại diện người lao động tại cơ sở (nếu có) và được công bố công khai tại nơi làm việc.", "j ti"),
          _p("2. Quy chế này có hiệu lực kể từ ngày ký ban hành; Giám đốc giao bộ phận nhân sự và kế toán trưởng (kế toán) triển khai thực hiện. Trong quá trình thực hiện nếu có vướng mắc hoặc pháp luật thay đổi, Công ty sẽ sửa đổi, bổ sung cho phù hợp.", "j ti"),
          _p("&nbsp;"),
          '<table class="nb"><colgroup><col style="width:50%"><col style="width:50%"></colgroup><tr><td>'
          + _p("<b><i>Nơi nhận:</i></b>") + _p("- Như Điều 2;") + _p("- Toàn thể người lao động;") + _p("- Lưu: VT.")
          + "</td><td>" + _p(f"<b>{esc((tc.get('chuc_danh_ky') or 'Giám đốc').upper())}</b>", "c") + _p("<i>(Ký, ghi rõ họ tên và đóng dấu)</i>", "c")
          + _khoang_ky((chu_ky or {}).get("giam_doc") if tc.get("gan_chu_ky", True) else "", sau=True) + _p(f"<b>{esc(tc.get('nguoi_ky') or '')}</b>", "c") + "</td></tr></table>", "</section>"]
    if tc.get("kem_phu_luc"):
        h.append('<section class="vb-trang">' + _p("<b>PHỤ LỤC</b>", "c b")
                 + _p(f"<b>Bảng lương cơ bản và phụ cấp từng người lao động (theo Danh sách nhân viên và Bảng lương năm {nam_du_lieu})</b>", "c") + bang_nhan_vien_html(dang_lam) + "</section>")
    return "".join(h)


def bang_nhan_vien_html(ds):
    cot = [("tien_com", "Tiền cơm"), ("xang_xe", "Xăng xe"), ("dien_thoai", "Điện thoại"), ("trang_phuc", "Trang phục"), ("di_lai", "Đi lại")]
    cot = [(k, t) for k, t in cot if any(n.get(k, 0) > 0 for n in ds)]
    r = ["<table><tr><th>STT</th><th>Họ và tên</th><th>Chức danh</th><th>Lương cơ bản</th>" + "".join(f"<th>{t}</th>" for _, t in cot) + "<th>Đóng BHXH</th></tr>"]
    for i, n in enumerate(ds, 1):
        r.append(f'<tr><td class="c">{i}</td><td>{esc(n["ten"])}</td><td>{esc(n.get("chuc_vu"))}</td><td class="r">{so_tien(n["luong_cb"])}</td>'
                 + "".join(f'<td class="r">{so_tien(n.get(k, 0)) if n.get(k, 0) else "-"}</td>' for k, _ in cot) + f'<td class="c">{"Có" if n.get("dong_bh") else "Không"}</td></tr>')
    r.append("</table>")
    return "".join(r)


def _ky_ben_phai(tc, ngay, anh=""):
    """Khối ký bên phải (như file mẫu): địa danh, ngày / chức danh / (Ký, ghi rõ họ tên và đóng dấu) / họ tên."""
    return ('<table class="nb"><colgroup><col style="width:55%"><col style="width:45%"></colgroup><tr><td></td><td>'
            + _p(f"<i>{esc(tc.get('dia_danh') + ', ' if tc.get('dia_danh') else '')}{esc(ngay_chu(ngay))}</i>", "c")
            + _p(f"<b>{esc((tc.get('chuc_danh_ky') or 'Giám đốc').upper())} CÔNG TY</b>", "c") + _p("<i>(Ký, ghi rõ họ tên và đóng dấu)</i>", "c")
            + _khoang_ky(anh, sau=True) + _p(f"<b>{esc((tc.get('nguoi_ky') or '').upper())}</b>", "c") + "</td></tr></table>")


def _he_so_hien(x):
    return f"{x:.2f}".replace(".", ",")


def dung_thang_bang_luong(nv_list, cty, tuy_chon, nam=None, hom_nay=None, chu_ky=None):
    """HTML Hệ thống thang lương, bảng lương theo bố cục file mẫu (nhóm chức danh × bậc lương; mỗi nhóm có dòng Hệ số + Mức lương) +
    phụ lục bảng xếp lương hiện tại của từng người (kèm mức lương đóng BHXH) để đối chiếu khi thanh tra."""
    tc = gop_tuy_chon(cty, tuy_chon, hom_nay)
    hom_nay = hom_nay or datetime.date.today()
    ngay = ngay_date(tc.get("ngay"), hom_nay)
    nam_du_lieu = nam or ngay.year
    nam = ngay.year                       # lương tối thiểu vùng + văn bản áp dụng theo NGÀY BAN HÀNH
    dang_lam = [n for n in nv_list if not n.get("da_nghi")] or nv_list
    tl = tinh_thang_luong(dang_lam, nam, tc.get("vung", 1), tc.get("buoc_pct", 5), tc.get("so_bac", 7), nhom_tuy_chinh=tc.get("nhom_tuy_chinh", ""))
    nb = tl["so_bac_toi_da"]
    co_hs = bool(tc.get("hien_he_so", True))
    ltt = tl["luong_toi_thieu"]
    anh_gd = ((chu_ky or {}).get("giam_doc") or "") if tc.get("gan_chu_ky", True) else ""
    pct = format(float(tl["buoc_pct"]), "g").replace(".", ",")
    h = ['<section class="vb-trang ngang">', _tieu_ngu(cty, "", tc.get("dia_danh"), ngay, co_ngay=False, co_dia_chi=True), _p("&nbsp;"),
         _p(f"<b>HỆ THỐNG THANG LƯƠNG, BẢNG LƯƠNG NĂM {nam_du_lieu}</b>", "c b"),
         _p(f"Áp dụng mức lương tối thiểu vùng {int(tc.get('vung', 1))}: {so_tien(ltt)} đồng/tháng ({esc(van_ban_luong_toi_thieu(nam).split(' quy định')[0])})", "c"),
         _p("Đơn vị tính: Việt Nam đồng", "r i")]
    rong = f"{72.0 / nb:.3f}%"
    t = [f'<table class="tl-thang" data-ltt="{int(round(ltt))}"><colgroup><col style="width:28%">' + "".join(f'<col style="width:{rong}">' for _ in range(nb)) + "</colgroup>"
         + f'<tr><th>NHÓM CHỨC DANH, VỊ TRÍ CÔNG VIỆC</th><th colspan="{nb}">BẬC LƯƠNG</th></tr><tr><th>&nbsp;</th>'
         + "".join(f"<th>{so_la_ma(i)}</th>" for i in range(1, nb + 1)) + "</tr>"]
    for i, g in enumerate(tl["nhom"], 1):
        t.append(f'<tr><td colspan="{nb + 1}"><b>{i}. {esc(g["ten"])}</b></td></tr>')
        if co_hs:
            t.append('<tr data-k="hs"><td>Hệ số lương</td>' + "".join(f'<td class="r">{_he_so_hien(g["he_so"][j]) if j < len(g["bac"]) else ""}</td>' for j in range(nb)) + "</tr>")
        t.append('<tr data-k="ml"><td>Mức lương</td>' + "".join(f'<td class="r">{so_tien(g["bac"][j]) if j < len(g["bac"]) else ""}</td>' for j in range(nb)) + "</tr>")
    t.append("</table>")
    h.append("".join(t))
    h += [_p("&nbsp;"),
          _p("<b>Nguyên tắc xây dựng và áp dụng thang lương, bảng lương:</b>"),
          _p(f"1. Mức lương bậc 1 của mỗi nhóm chức danh không thấp hơn mức lương tối thiểu vùng ({so_tien(ltt)} đồng/tháng)"
             + (f"; hệ số lương = mức lương của bậc ÷ mức lương tối thiểu vùng." if co_hs else "."), "j"),
          _p(f"2. Mức lương mỗi bậc cao hơn bậc liền kề trước {pct}%.", "j"),
          _p("3. Mức lương ghi trong hợp đồng lao động và mức lương làm căn cứ đóng bảo hiểm xã hội, bảo hiểm y tế, bảo hiểm thất nghiệp của người lao động được xếp theo thang lương, bảng lương này "
             "(chi tiết tại Phụ lục).", "j"),
          _p("4. Người lao động được xét nâng bậc lương khi đủ 12 tháng giữ bậc hiện hưởng, hoàn thành tốt nhiệm vụ và không bị xử lý kỷ luật lao động từ hình thức khiển trách bằng văn bản trở lên.", "j"),
          _p("5. Thang lương, bảng lương được xây dựng theo Điều 93 Bộ luật Lao động năm 2019 sau khi tham khảo ý kiến của tổ chức đại diện người lao động tại cơ sở (nếu có) "
             "và được công bố công khai tại nơi làm việc trước khi thực hiện.", "j"),
          _p("&nbsp;"), _ky_ben_phai(tc, ngay, anh_gd)]
    if tc.get("kem_xep_luong"):
        h.append('<p class="pb">&nbsp;</p>')
        h.append(_p("<b>PHỤ LỤC</b>", "c b"))
        h.append(_p("<b>BẢNG XẾP LƯƠNG HIỆN TẠI CỦA NGƯỜI LAO ĐỘNG</b>", "c"))
        h.append(_p(f"(Theo Danh sách nhân viên và Bảng lương năm {nam_du_lieu})", "c i"))
        x = ["<table><tr><th>STT</th><th>Họ và tên</th><th>Nhóm chức danh</th><th>Mức lương theo hợp đồng</th><th>Bậc lương</th><th>Hệ số</th><th>Mức lương của bậc</th>"
             "<th>Chênh lệch</th><th>Mức lương đóng BHXH</th></tr>"]
        stt = 0
        for g in tl["nhom"]:
            for xp in g["xep"]:
                stt += 1
                n = xp["nv"]
                k = xp["bac"]
                x.append(f'<tr><td class="c">{stt}</td><td>{esc(n["ten"])}</td><td>{esc(g["ten"])}</td><td class="r">{so_tien(n["luong_cb"])}</td>'
                         f'<td class="c">{so_la_ma(k) if k else "-"}</td><td class="r">{_he_so_hien(g["he_so"][k - 1]) if k else "-"}</td>'
                         f'<td class="r">{so_tien(xp["muc_bac"]) if k else "-"}</td><td class="r">{so_tien(xp["chenh"]) if k else "-"}</td>'
                         f'<td class="r">{so_tien(n["luong_cb"]) if n.get("dong_bh") else "Không tham gia"}</td></tr>')
        x.append("</table>")
        h.append("".join(x))
        h.append(_p("Ghi chú: mức lương làm căn cứ đóng bảo hiểm xã hội bằng mức lương theo hợp đồng lao động (lương cơ bản), chưa gồm các khoản phụ cấp, hỗ trợ không thuộc diện đóng bảo hiểm.", "j i"))
        h.append(_p("&nbsp;"))
        h.append(_ky_ben_phai(tc, ngay, anh_gd))
    h.append("</section>")
    return "".join(h)


VB_CSS = """
.vb-doc{font-family:var(--vb-f,"Times New Roman"),Times,serif;font-size:var(--vb-s,13pt);line-height:var(--vb-l,1.15);color:#000}
.vb-doc .vb-trang{background:#fff;box-sizing:border-box;width:210mm;min-height:297mm;padding:var(--vb-mt,20mm) var(--vb-mr,15mm) var(--vb-mb,20mm) var(--vb-ml,30mm);margin:0 auto 14px;box-shadow:0 0 6px rgba(0,0,0,.3)}
.vb-doc .vb-trang.ngang{width:297mm;min-height:210mm}
.vb-doc .vb-trang{position:relative;z-index:0}
.vb-doc p{margin:0 0 3pt}
.vb-doc p.ky-sau{position:relative;margin:0}.vb-doc img.sau{position:absolute;left:50%;top:-35px;transform:translateX(-50%);z-index:-1;pointer-events:none}
.vb-doc .c{text-align:center}.vb-doc .r{text-align:right}.vb-doc .j{text-align:justify}
.vb-doc .b{font-weight:700}.vb-doc .i{font-style:italic}.vb-doc .u{text-decoration:underline}
.vb-doc .ti{text-indent:10mm}.vb-doc .l1{margin-left:10mm}.vb-doc .l2{margin-left:20mm}
.vb-doc table{border-collapse:collapse;width:100%;margin:3pt 0}
.vb-doc td,.vb-doc th{border:1px solid #000;padding:2pt 4pt;vertical-align:top}
.vb-doc table.nb td{border:none}
.vb-doc table,.vb-doc td,.vb-doc th{font-size:inherit;color:#000}
.vb-doc th{background:#e8e8e8;color:#000;text-align:center;font-weight:700;position:static;text-transform:none;letter-spacing:0;font-size:inherit}
.vb-doc .pb{page-break-before:always;height:0;margin:14pt 0 0;overflow:hidden;font-size:1pt}
.vb-doc td p,.vb-doc th p{margin:0}
@media print{.vb-doc .vb-trang{box-shadow:none;margin:0;width:auto;min-height:0;padding:0;page-break-after:always}.vb-doc .vb-trang:last-child{page-break-after:auto}}
"""


# ============================================================ HTML -> DOCX
_RE_KHOANG = re.compile(r"[ \t\r\n\f]+")


def _style_dict(s):
    d = {}
    for m in re.finditer(r"([\w-]+)\s*:\s*([^;]+)", s or ""):
        d[m.group(1).strip().lower()] = m.group(2).strip().lower()
    return d


def _twips(v):
    """'40px'/'12pt'/'1cm'/'10mm' -> twips; không đọc được -> 0."""
    m = re.match(r"^(-?[\d.]+)\s*(px|pt|cm|mm|in)?$", str(v or "").strip())
    if not m:
        return 0
    x, u = float(m.group(1)), m.group(2) or "px"
    return int(x * {"px": 15, "pt": 20, "cm": 567, "mm": 56.7, "in": 1440}[u])


class _HtmlSangKhoi(HTMLParser):
    """Đọc HTML đơn giản của văn bản -> danh sách khối: ('p', para) | ('tbl', table) | ('ngat_trang',)."""

    BLOCK = ("p", "div", "h1", "h2", "h3", "h4", "li", "blockquote")

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.khoi = []
        self.p = None               # đoạn đang mở
        self.pstack = []            # ngăn xếp thẻ block đang mở: (tag, para_hay_None)
        self.fmt = []               # ngăn xếp định dạng inline: (tag, {'b','i','u'})
        self.tbl = None
        self.row = None
        self.cell = None
        self.depth_tbl = 0
        self.sec = 0
        self.sec_moi = False

    # ---- định dạng inline hiện tại
    def _dd(self):
        b = i = u = False
        for _t, f in self.fmt:
            b, i, u = b or f.get("b", False), i or f.get("i", False), u or f.get("u", False)
        return b, i, u

    def _thuoc_tinh_doan(self, attrs):
        a = dict(attrs)
        cls = set((a.get("class") or "").split())
        st = _style_dict(a.get("style"))
        al = None
        for k, v in (("c", "center"), ("r", "right"), ("j", "both"), ("l", "left")):
            if k in cls:
                al = v
        ta = st.get("text-align")
        if ta in ("center", "right", "left", "justify"):
            al = "both" if ta == "justify" else ta
        ml = _twips(st.get("margin-left"))
        ti = _twips(st.get("text-indent"))
        if "l1" in cls:
            ml = ml or 567
        if "l2" in cls:
            ml = ml or 1134
        if "ti" in cls:
            ti = ti or 567
        hgt = _twips(st.get("height")) if "ky-sau" in cls else 0
        return {"al": al, "ml": ml, "ti": ti, "hgt": hgt, "b": "b" in cls or st.get("font-weight") in ("bold", "700", "800", "900"),
                "i": "i" in cls or st.get("font-style") == "italic", "u": "u" in cls or "underline" in st.get("text-decoration", ""),
                "pb": "pb" in cls}

    def _mo_doan(self, props):
        self._dong_doan()
        if self.cell is not None and props.get("al") is None and self.cell.get("al"):
            props = dict(props, al=self.cell["al"])
        if self.cell is not None and self.cell.get("b") and not props.get("b"):
            props = dict(props, b=True)
        self.p = {"props": props, "runs": []}

    def _dong_doan(self):
        p, self.p = self.p, None
        if p is None:
            return
        runs = p["runs"]
        # bỏ khoảng trắng đầu/cuối
        if runs and runs[0][0] == "t":
            runs[0] = ("t", runs[0][1].lstrip(" "), *runs[0][2:])
        if runs and runs[-1][0] == "t":
            runs[-1] = ("t", runs[-1][1].rstrip(" "), *runs[-1][2:])
        runs = [r for r in runs if not (r[0] == "t" and r[1] == "")]
        chi_br = bool(runs) and all(r == ("br",) for r in runs)
        if chi_br:
            p["runs"] = []
        elif not runs:
            if not p["props"].get("pb"):
                return          # đoạn rỗng (vd <div> bao quanh) — bỏ
        else:
            p["runs"] = runs
        if p["props"].get("pb"):
            self.sec_moi = True
            return
        if self.cell is not None:
            self.cell["paras"].append(p)
        else:
            self._them(("p", p))

    def _them(self, k):
        if self.sec_moi:
            self.sec_moi = False
            if self.khoi:
                self.khoi.append(("ngat_trang",))
        self.khoi.append(k)

    # ---- sự kiện
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "section":
            self._dong_doan()
            self.sec += 1
            if self.sec > 1:
                self.sec_moi = True
            return
        if tag == "table":
            if self.depth_tbl == 0:
                self._dong_doan()
                cls = set((a.get("class") or "").split())
                self.tbl = {"rows": [], "cols": [], "vien": "nb" not in cls}
            self.depth_tbl += 1
            return
        if self.depth_tbl > 1:       # bảng lồng: bỏ qua thẻ, chỉ lấy chữ
            return
        if self.tbl is not None:
            if tag == "col":
                w = _style_dict(a.get("style")).get("width", "") or (a.get("width") or "")
                m = re.match(r"([\d.]+)\s*%", w)
                self.tbl["cols"].append(float(m.group(1)) if m else None)
                return
            if tag == "tr":
                self._dong_doan()
                self.row = []
                return
            if tag in ("td", "th"):
                self._dong_doan()
                cls = set((a.get("class") or "").split())
                st = _style_dict(a.get("style"))
                al = "center" if "c" in cls or tag == "th" else ("right" if "r" in cls else ("both" if "j" in cls else None))
                ta = st.get("text-align")
                if ta in ("center", "right", "left"):
                    al = ta
                w = None
                m = re.match(r"([\d.]+)\s*%", st.get("width", "") or (a.get("width") or ""))
                if m:
                    w = float(m.group(1))
                self.cell = {"paras": [], "span": int(a.get("colspan") or 1) if str(a.get("colspan") or "1").isdigit() else 1,
                             "rowspan": int(a.get("rowspan") or 1) if str(a.get("rowspan") or "1").isdigit() else 1,
                             "th": tag == "th", "al": al, "b": tag == "th" or "b" in cls, "w": w}
                self.row.append(self.cell)
                return
        if tag in self.BLOCK:
            self._mo_doan(self._thuoc_tinh_doan(attrs))
            self.pstack.append(tag)
            return
        if tag == "br":
            if self.p is None:
                self._mo_doan({})
            self.p["runs"].append(("br",))
            return
        if tag == "img":                         # ảnh chữ ký (data URI): giữ nguyên tỷ lệ, cao theo style height (px)
            kq = _doc_anh_data_uri(a.get("src"))
            if kq:
                st = _style_dict(a.get("style"))
                w0, h0 = _kich_thuoc_anh(kq[1])
                cao = _twips(st.get("height")) / 15 if st.get("height") else 0
                rong = _twips(st.get("width")) / 15 if st.get("width") else 0
                if w0 and h0:
                    if cao and not rong:
                        rong = cao * w0 / h0
                    elif rong and not cao:
                        cao = rong * h0 / w0
                    elif not cao and not rong:
                        rong, cao = min(w0, 200), min(w0, 200) * h0 / w0
                if self.p is None:
                    self._mo_doan({})
                sau = "sau" in set((a.get("class") or "").split())
                self.p["runs"].append(("img", kq[0], kq[1], max(8, rong or 100), max(8, cao or 40), sau))
            return
        if tag in ("b", "strong"):
            self.fmt.append((tag, {"b": True}))
        elif tag in ("i", "em"):
            self.fmt.append((tag, {"i": True}))
        elif tag == "u":
            self.fmt.append((tag, {"u": True}))
        elif tag in ("span", "font"):
            st = _style_dict(a.get("style"))
            self.fmt.append((tag, {"b": st.get("font-weight") in ("bold", "700", "800", "900"), "i": st.get("font-style") == "italic",
                                   "u": "underline" in st.get("text-decoration", "")}))

    def handle_endtag(self, tag):
        if tag == "section":
            self._dong_doan()
            return
        if tag == "table":
            self.depth_tbl = max(0, self.depth_tbl - 1)
            if self.depth_tbl == 0 and self.tbl is not None:
                self._dong_doan()
                self._them(("tbl", self.tbl))
                self.tbl = self.row = self.cell = None
            return
        if self.depth_tbl > 1:
            return
        if self.tbl is not None:
            if tag in ("td", "th"):
                self._dong_doan()
                self.cell = None
                return
            if tag == "tr":
                self._dong_doan()
                if self.row is not None:
                    self.tbl["rows"].append(self.row)
                self.row = None
                return
        if tag in self.BLOCK:
            self._dong_doan()
            if self.pstack and self.pstack[-1] == tag:
                self.pstack.pop()
            return
        if tag in ("b", "strong", "i", "em", "u", "span", "font"):
            for k in range(len(self.fmt) - 1, -1, -1):
                if self.fmt[k][0] == tag:
                    del self.fmt[k]
                    break

    def handle_data(self, data):
        if self.tbl is not None and self.cell is None and self.depth_tbl == 1:
            return
        t = _RE_KHOANG.sub(" ", data)
        if not t.strip(" ") and self.p is None:
            return
        if self.p is None:
            self._mo_doan({})
        b, i, u = self._dd()
        pr = self.p["props"]
        self.p["runs"].append(("t", t, b or pr.get("b", False), i or pr.get("i", False), u or pr.get("u", False)))


def _kich_thuoc_anh(b):
    """(rộng, cao) pixel của ảnh PNG/JPEG; không đọc được -> (0, 0)."""
    try:
        from PIL import Image
        with Image.open(io.BytesIO(b)) as im:
            return im.size
    except Exception:
        pass
    if b[:8] == b"\x89PNG\r\n\x1a\n" and len(b) >= 24:
        import struct
        return struct.unpack(">II", b[16:24])
    return (0, 0)


def _doc_anh_data_uri(src):
    m = re.match(r"^data:image/(png|jpe?g);base64,(.+)$", str(src or "").strip(), flags=re.S | re.I)
    if not m:
        return None
    import base64
    try:
        return ("png" if m.group(1).lower() == "png" else "jpeg"), base64.b64decode(m.group(2))
    except Exception:
        return None


def _x(s):
    return _xml_esc(re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(s)))


def _xml_hinh(r, hinh, hgt_px=0):
    hinh.append((r[1], r[2]))
    n = len(hinh)
    cx, cy = int(r[3] * 9525), int(r[4] * 9525)
    if len(r) > 5 and r[5]:         # Ảnh PHÍA SAU CHỮ (Wrap text: Behind text): neo vào đoạn trống, canh giữa ô, đè lên chức danh/họ tên như con dấu
        lech = int(((hgt_px or r[4]) - r[4]) / 2 * 9525)
        return ('<w:r><w:drawing><wp:anchor distT="0" distB="0" distL="0" distR="0" simplePos="0" relativeHeight="251658240" behindDoc="1" locked="0" layoutInCell="1" allowOverlap="1">'
                '<wp:simplePos x="0" y="0"/><wp:positionH relativeFrom="column"><wp:align>center</wp:align></wp:positionH>'
                f'<wp:positionV relativeFrom="paragraph"><wp:posOffset>{lech}</wp:posOffset></wp:positionV>'
                f'<wp:extent cx="{cx}" cy="{cy}"/><wp:effectExtent l="0" t="0" r="0" b="0"/><wp:wrapNone/><wp:docPr id="{n}" name="Chu ky {n}"/>'
                '<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
                '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic>'
                f'<pic:nvPicPr><pic:cNvPr id="{n}" name="chuky{n}"/><pic:cNvPicPr/></pic:nvPicPr>'
                f'<pic:blipFill><a:blip r:embed="rIdImg{n}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
                f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
                '</pic:pic></a:graphicData></a:graphic></wp:anchor></w:drawing></w:r>')
    return ('<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
            f'<wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{n}" name="Chu ky {n}"/>'
            '<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
            '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic>'
            f'<pic:nvPicPr><pic:cNvPr id="{n}" name="chuky{n}"/><pic:cNvPicPr/></pic:nvPicPr>'
            f'<pic:blipFill><a:blip r:embed="rIdImg{n}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
            '</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>')


def _xml_doan(p, ngat_truoc=False, an_dau=False, font_cfg=None, sau=None, hinh=None):
    pr = p["props"]
    ppr = []
    if ngat_truoc:
        ppr.append("<w:pageBreakBefore/>")
    if pr.get("hgt"):          # đoạn trống cao cố định chứa ảnh chữ ký/dấu phía sau chữ
        ppr.append(f'<w:spacing w:before="0" w:after="0" w:line="{int(pr["hgt"])}" w:lineRule="exact"/>')
    elif sau is not None:
        ppr.append(f'<w:spacing w:before="0" w:after="{sau}"/>')
    if pr.get("ml") or pr.get("ti"):
        ppr.append(f'<w:ind w:left="{int(pr.get("ml") or 0)}" w:firstLine="{int(pr.get("ti") or 0)}"/>')
    if pr.get("al"):
        ppr.append(f'<w:jc w:val="{pr["al"]}"/>')
    kq = ["<w:p>"]
    if ppr:
        kq.append("<w:pPr>" + "".join(ppr) + "</w:pPr>")
    for r in p["runs"]:
        if r[0] == "br":
            kq.append("<w:r><w:br/></w:r>")
        elif r[0] == "img":
            kq.append(_xml_hinh(r, hinh if hinh is not None else [], (pr.get("hgt") or 0) / 15))
        else:
            rpr = ("<w:b/>" if r[2] else "") + ("<w:i/>" if r[3] else "") + ('<w:u w:val="single"/>' if r[4] else "")
            kq.append("<w:r>" + (f"<w:rPr>{rpr}</w:rPr>" if rpr else "") + f'<w:t xml:space="preserve">{_x(r[1].replace(chr(160), " "))}</w:t></w:r>')
    kq.append("</w:p>")
    return "".join(kq)


def _xml_bang(tbl, rong_chu, hinh=None):
    rows = [r for r in tbl["rows"] if r]
    if not rows:
        return ""
    so_cot = max(sum(c["span"] for c in r) for r in rows)
    tong = [c for c in tbl["cols"]]
    if len(tong) < so_cot or any(w is None for w in tong[:so_cot]):
        w_dau = []
        for c in rows[0]:
            w_dau += ([c["w"] / c["span"]] * c["span"]) if c.get("w") else [None] * c["span"]
        if len(w_dau) == so_cot and all(w is not None for w in w_dau):
            tong = w_dau
        else:
            tong = [100.0 / so_cot] * so_cot
    tong = tong[:so_cot]
    s = sum(tong) or 100.0
    gc = [max(200, int(rong_chu * w / s)) for w in tong]
    vien = ('<w:tblBorders>' + "".join(f'<w:{k} w:val="single" w:sz="4" w:space="0" w:color="000000"/>' for k in ("top", "left", "bottom", "right", "insideH", "insideV")) + "</w:tblBorders>"
            if tbl["vien"] else "")
    x = [f'<w:tbl><w:tblPr><w:tblW w:w="{sum(gc)}" w:type="dxa"/>{vien}<w:tblLayout w:type="fixed"/>'
         '<w:tblCellMar><w:left w:w="80" w:type="dxa"/><w:right w:w="80" w:type="dxa"/></w:tblCellMar></w:tblPr>',
         "<w:tblGrid>" + "".join(f'<w:gridCol w:w="{g}"/>' for g in gc) + "</w:tblGrid>"]
    for r in rows:
        la_dau = all(c["th"] for c in r)
        x.append("<w:tr><w:trPr><w:cantSplit/>" + ("<w:tblHeader/>" if la_dau else "") + "</w:trPr>")
        ci = 0
        for c in r:
            w = sum(gc[ci:ci + c["span"]]) or gc[min(ci, len(gc) - 1)]
            ci += c["span"]
            tcpr = f'<w:tcW w:w="{w}" w:type="dxa"/>' + (f'<w:gridSpan w:val="{c["span"]}"/>' if c["span"] > 1 else "")
            if c["th"]:
                tcpr += '<w:shd w:val="clear" w:color="auto" w:fill="E8E8E8"/>'
            paras = c["paras"] or [{"props": {}, "runs": []}]
            x.append(f"<w:tc><w:tcPr>{tcpr}</w:tcPr>" + "".join(_xml_doan(p, sau=0, hinh=hinh) for p in paras) + "</w:tc>")
        x.append("</w:tr>")
    x.append("</w:tbl>")
    return "".join(x)


def html_sang_docx(html, trang=None):
    """HTML văn bản (do phần mềm dựng, người dùng có thể đã sửa tay) -> nội dung file .docx (bytes).
    `trang`: {font, size (pt), line (giãn dòng), le: [trên, dưới, trái, phải] (mm), ngang: bool}."""
    t = dict(TRANG_MAC_DINH)
    t.update({k: v for k, v in (trang or {}).items() if v not in (None, "")})
    try:
        le = [float(x) for x in t["le"]][:4]
        le = le if len(le) == 4 else TRANG_MAC_DINH["le"]
    except Exception:
        le = TRANG_MAC_DINH["le"]
    try:
        size = float(t["size"])
    except Exception:
        size = 13.0
    try:
        gian = float(t["line"])
    except Exception:
        gian = 1.15
    font = _x(str(t["font"] or "Times New Roman"))
    ngang = bool(t.get("ngang"))
    w_trang, h_trang = (16838, 11906) if ngang else (11906, 16838)
    tw = lambda mm: int(round(mm * 56.7))
    rong_chu = w_trang - tw(le[2]) - tw(le[3])

    ps = _HtmlSangKhoi()
    ps.feed(html or "")
    ps._dong_doan()
    thanh = []
    hinh = []
    ngat = False
    for k in ps.khoi:
        if k[0] == "ngat_trang":
            ngat = True
            continue
        if ngat:                    # đoạn nhỏ 1pt mở trang mới (đảm bảo cả bảng cũng sang trang)
            thanh.append('<w:p><w:pPr><w:pageBreakBefore/><w:spacing w:before="0" w:after="0" w:line="20" w:lineRule="exact"/></w:pPr></w:p>')
            ngat = False
        thanh.append(_xml_doan(k[1], hinh=hinh) if k[0] == "p" else _xml_bang(k[1], rong_chu, hinh))
    if not thanh:
        thanh.append("<w:p/>")
    ns = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
          'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
          'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
          'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"')
    doc = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {ns}><w:body>' + "".join(thanh)
           + f'<w:sectPr><w:pgSz w:w="{w_trang}" w:h="{h_trang}"' + (' w:orient="landscape"' if ngang else "") + "/>"
           + f'<w:pgMar w:top="{tw(le[0])}" w:right="{tw(le[3])}" w:bottom="{tw(le[1])}" w:left="{tw(le[2])}" w:header="709" w:footer="709" w:gutter="0"/>'
           + "</w:sectPr></w:body></w:document>")
    styles = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles {ns}><w:docDefaults><w:rPrDefault><w:rPr>'
              f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:cs="{font}" w:eastAsia="{font}"/><w:sz w:val="{int(round(size * 2))}"/><w:szCs w:val="{int(round(size * 2))}"/>'
              '<w:lang w:val="vi-VN" w:eastAsia="vi-VN" w:bidi="ar-SA"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr>'
              f'<w:spacing w:before="0" w:after="60" w:line="{int(round(gian * 240))}" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>'
              '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style></w:styles>')
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
          '<Default Extension="png" ContentType="image/png"/><Default Extension="jpeg" ContentType="image/jpeg"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    drels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
             '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
             + "".join(f'<Relationship Id="rIdImg{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/chuky{i}.{ext}"/>'
                       for i, (ext, _b) in enumerate(hinh, 1))
             + '</Relationships>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc)
        z.writestr("word/styles.xml", styles)
        z.writestr("word/_rels/document.xml.rels", drels)
        for i, (ext, b) in enumerate(hinh, 1):
            z.writestr(f"word/media/chuky{i}.{ext}", b)
    return buf.getvalue()


# ============================================================ Excel thang bảng lương (theo file mẫu)
def thang_luong_excel(path, nv_list, cty, tuy_chon, nam=None, hom_nay=None):
    """Thang bảng lương dạng Excel, bố cục như file mẫu (nhóm chức danh, Hệ số lương, Mức lương theo bậc) + sheet Xếp lương."""
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter as L
    tc = gop_tuy_chon(cty, tuy_chon, hom_nay)
    hom_nay = hom_nay or datetime.date.today()
    ngay = ngay_date(tc.get("ngay"), hom_nay)
    nam_du_lieu = nam or ngay.year
    nam = ngay.year
    dang_lam = [n for n in nv_list if not n.get("da_nghi")] or nv_list
    tl = tinh_thang_luong(dang_lam, nam, tc.get("vung", 1), tc.get("buoc_pct", 5), tc.get("so_bac", 7), nhom_tuy_chinh=tc.get("nhom_tuy_chinh", ""))
    nb = tl["so_bac_toi_da"]
    co_hs = bool(tc.get("hien_he_so", True))
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Thang bảng lương"
    giua = Alignment(horizontal="center", vertical="center", wrap_text=True)
    s_ = Side(style="thin")
    vien = Border(left=s_, right=s_, top=s_, bottom=s_)
    nc = nb + 1
    cot_p = max(3, nc - 3)
    ws.cell(1, 1, (cty.get("ten") or "").upper()).font = Font(bold=True)
    ws.cell(1, cot_p, "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM").font = Font(bold=True)
    ws.cell(2, 1, ("Mã số thuế: " + cty["mst"]) if cty.get("mst") else "")
    ws.cell(2, cot_p, "Độc lập - Tự do - Hạnh phúc").font = Font(bold=True)
    ws.cell(3, 1, "Địa chỉ: " + (cty.get("dia_chi") or ""))
    ws.merge_cells(start_row=5, start_column=1, end_row=5, end_column=nc)
    ws.cell(5, 1, f"HỆ THỐNG THANG LƯƠNG, BẢNG LƯƠNG NĂM {nam_du_lieu}").font = Font(bold=True, size=14)
    ws.cell(5, 1).alignment = giua
    ws.merge_cells(start_row=6, start_column=1, end_row=6, end_column=nc)
    ws.cell(6, 1, f"Áp dụng mức lương tối thiểu vùng {int(tc.get('vung', 1))}: {so_tien(tl['luong_toi_thieu'])} đồng/tháng").alignment = giua
    ws.cell(7, nc, "Đơn vị tính: Việt Nam đồng").alignment = Alignment(horizontal="right")
    ws.merge_cells(start_row=8, start_column=1, end_row=9, end_column=1)
    ws.cell(8, 1, "NHÓM CHỨC DANH,\nVỊ TRÍ CÔNG VIỆC")
    ws.merge_cells(start_row=8, start_column=2, end_row=8, end_column=nc)
    ws.cell(8, 2, "BẬC LƯƠNG")
    for j in range(1, nb + 1):
        ws.cell(9, 1 + j, so_la_ma(j))
    for rr in (8, 9):
        for j in range(1, nc + 1):
            c = ws.cell(rr, j)
            c.font, c.alignment, c.border = Font(bold=True), giua, vien
            c.fill = PatternFill("solid", fgColor="D9E1F2")
    r = 10
    for i, g in enumerate(tl["nhom"], 1):
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=nc)
        ws.cell(r, 1, f"{i}. {g['ten']}").font = Font(bold=True)
        for j in range(1, nc + 1):
            ws.cell(r, j).border = vien
        r += 1
        if co_hs:
            ws.cell(r, 1, "Hệ số lương")
            for j, m in enumerate(g["bac"]):
                ws.cell(r, 2 + j, round(g["he_so"][j], 2)).number_format = "0.00"
            for j in range(1, nc + 1):
                ws.cell(r, j).border = vien
            r += 1
        ws.cell(r, 1, "Mức lương")
        for j, m in enumerate(g["bac"]):
            ws.cell(r, 2 + j, m).number_format = "#,##0"
        for j in range(1, nc + 1):
            ws.cell(r, j).border = vien
        r += 1
    ws.column_dimensions["A"].width = 38
    for j in range(2, nc + 1):
        ws.column_dimensions[L(j)].width = 15
    r += 1
    ws.cell(r, cot_p, f"{(tc.get('dia_danh') + ', ') if tc.get('dia_danh') else ''}{ngay_chu(ngay)}").font = Font(italic=True)
    ws.cell(r + 1, cot_p, (tc.get("chuc_danh_ky") or "Giám đốc").upper() + " CÔNG TY").font = Font(bold=True)
    ws.cell(r + 2, cot_p, "(Ký, ghi rõ họ tên và đóng dấu)").font = Font(italic=True)
    ws.cell(r + 6, cot_p, (tc.get("nguoi_ky") or "").upper()).font = Font(bold=True)
    if tc.get("kem_xep_luong"):
        w2 = wb.create_sheet("Xếp lương")
        hdr = ["STT", "Họ và tên", "Nhóm chức danh", "Mức lương theo hợp đồng", "Bậc lương", "Hệ số", "Mức lương của bậc", "Chênh lệch", "Mức lương đóng BHXH"]
        w2.append(hdr)
        for j in range(1, len(hdr) + 1):
            c = w2.cell(1, j)
            c.font, c.alignment, c.border = Font(bold=True), giua, vien
            c.fill = PatternFill("solid", fgColor="D9E1F2")
        stt = 0
        for g in tl["nhom"]:
            for xp in g["xep"]:
                stt += 1
                n, k = xp["nv"], xp["bac"]
                w2.append([stt, n["ten"], g["ten"], n["luong_cb"], so_la_ma(k) if k else "-", round(g["he_so"][k - 1], 2) if k else "-",
                           xp["muc_bac"] if k else 0, xp["chenh"] if k else 0, n["luong_cb"] if n.get("dong_bh") else "Không tham gia"])
        for row in w2.iter_rows(min_row=2):
            for c in row:
                c.border = vien
                if c.column in (4, 7, 8, 9):
                    c.number_format = "#,##0"
        for j, w in enumerate([6, 28, 28, 22, 12, 10, 20, 16, 22], 1):
            w2.column_dimensions[L(j)].width = w
    wb.save(path)
    return path



# ============================================================ HỢP ĐỒNG LAO ĐỘNG PART-TIME (làm việc không trọn thời gian) — Điều 32 Bộ luật Lao động 2019
def nguong_part_time(nam, tuy_chon=None):
    """Ngưỡng tiền lương tháng của người làm việc KHÔNG TRỌN THỜI GIAN: dưới ngưỡng này thì không thuộc đối tượng đóng BHXH bắt buộc (mức lương thấp nhất làm căn cứ đóng).
    Mặc định theo mức tham chiếu 2.340.000 (2025) / 2.530.000 (từ 2026) — CẦN ĐỐI CHIẾU văn bản hiện hành; sửa được bằng tuỳ chọn `pt_nguong`."""
    v = _so((tuy_chon or {}).get("pt_nguong"))
    if v > 0:
        return v
    return 2530000.0 if int(nam or datetime.date.today().year) >= 2026 else 2340000.0


def luong_toi_thieu_gio(nam, vung=1):
    """Mức lương tối thiểu giờ ≈ mức tối thiểu tháng ÷ 26 ngày ÷ 8 giờ (làm tròn xuống 100đ): vùng I 2026 = 25.500; vùng I 2024 = 23.800."""
    return int(luong_toi_thieu_vung(nam, vung) / 208.0 // 100 * 100)


def _so_gio(v):
    """'2' / '2,5' / '' -> float|None (giờ làm việc)."""
    t = str(v if v is not None else "").strip().replace(",", ".")
    try:
        x = float(t)
    except ValueError:
        return None
    return x if x > 0 else None


def _gio_dien_ra(tc, nv):
    """(giờ/ngày, ngày/tuần, giờ/tuần, giờ/tháng dự kiến, đơn giá giờ, lương tháng dự kiến) — None nếu thiếu dữ liệu."""
    gio_ngay = _so_gio(tc.get("pt_gio_ngay"))
    ngay_tuan = _so_gio(tc.get("pt_ngay_tuan"))
    gio_tuan = _so_gio(tc.get("pt_gio_tuan")) or ((gio_ngay * ngay_tuan) if gio_ngay and ngay_tuan else None)
    gio_thang = _so_gio(tc.get("pt_gio_thang")) or ((round(gio_tuan * 52 / 12, 1)) if gio_tuan else None)
    don_gia = _so(tc.get("pt_luong_gio")) or _so((nv or {}).get("luong_gio")) or None
    luong = (gio_thang * don_gia) if gio_thang and don_gia else None
    return gio_ngay, ngay_tuan, gio_tuan, gio_thang, don_gia, luong


def _gio_hien(x):
    return (f"{x:g}").replace(".", ",")


def kiem_tra_part_time(ds_nv, tuy_chon, nam=None):
    """Cảnh báo khi lập hợp đồng part-time: phải ngắn hơn 8 giờ/ngày, 48 giờ/tuần; lương tháng dự kiến dưới ngưỡng thì mới được ghi "không thuộc đối tượng BHXH"; đơn giá giờ không thấp hơn mức tối thiểu giờ."""
    tc = gop_tuy_chon({}, tuy_chon or {})
    nam = nam or datetime.date.today().year
    ng = nguong_part_time(nam, tc)
    kq = []

    def nam_hd(nv):          # năm của ngày hợp đồng/ký (= ngày bắt đầu làm việc đầu tiên) quyết định ngưỡng + lương tối thiểu giờ
        d = ngay_date(tc.get("ngay_ky")) or ngay_date(tc.get("bat_dau")) or ngay_date(nv.get("vao_lam"))
        return d.year if d else nam
    if not ds_nv:
        kq.append({"muc": "loi", "nd": "Chưa có người lao động part-time: tick cột 'Part-time' (và nhập 'Lương theo giờ') ở Danh Sách Nhân Viên."})
    for nv in ds_nv:
        t = nv["ten"]
        nam_nv = nam_hd(nv)
        ng = nguong_part_time(nam_nv, tc)
        gio_ngay, ngay_tuan, gio_tuan, gio_thang, don_gia, luong = _gio_dien_ra(tc, nv)
        if (gio_ngay and gio_ngay >= 8) or (gio_tuan and gio_tuan >= 48):
            kq.append({"muc": "loi", "nd": f"{t}: thời giờ làm việc không ngắn hơn 08 giờ/ngày hoặc 48 giờ/tuần — không phải làm việc không trọn thời gian (Điều 32 BLLĐ 2019)."})
        if not don_gia:
            kq.append({"muc": "loi", "nd": f"{t}: chưa có lương theo giờ (cột 'Lương theo giờ' ở Danh Sách Nhân Viên hoặc ô trên màn hình)."})
        elif don_gia + 0.5 < luong_toi_thieu_gio(nam_nv, tc.get("vung", 1)):
            kq.append({"muc": "loi", "nd": f"{t}: lương theo giờ {so_tien(don_gia)} đ thấp hơn mức lương tối thiểu giờ vùng {int(tc.get('vung', 1))} (≈ {so_tien(luong_toi_thieu_gio(nam_nv, tc.get('vung', 1)))} đ/giờ)."})
        if luong is not None and luong >= ng - 1e-9:
            kq.append({"muc": "loi", "nd": f"{t}: tiền lương tháng dự kiến {so_tien(luong)} đ từ {so_tien(ng)} đ trở lên — thuộc đối tượng tham gia BHXH bắt buộc; hợp đồng đã ghi theo hướng PHẢI đóng BHXH, không ghi câu 'không thuộc đối tượng'."})
    kq.append({"muc": "canh_bao", "nd": f"Ngưỡng {so_tien(ng)} đ/tháng lấy theo mức tham chiếu mặc định — hãy đối chiếu văn bản BHXH hiện hành (sửa được trong tham số); chỉ áp dụng khi giờ làm thực tế trong từng tháng đúng như hợp đồng: tháng nào lương thực nhận đạt ngưỡng thì tháng đó phải đóng BHXH."})
    return kq


def dung_hop_dong_part_time(nv, cty, tuy_chon, so_thu_tu, hom_nay=None, nam=None, chu_ky=None):
    """HTML 1 hợp đồng lao động LÀM VIỆC KHÔNG TRỌN THỜI GIAN (part-time): thời giờ làm việc ngắn hơn bình thường, lương theo giờ dưới ngưỡng, điều khoản BHXH."""
    tc = gop_tuy_chon(cty, tuy_chon, hom_nay)
    hom_nay = hom_nay or datetime.date.today()
    # Ngày hợp đồng + ngày ký = NGÀY BẮT ĐẦU LÀM VIỆC ĐẦU TIÊN TRONG NĂM LẬP: tháng đầu tiên của năm lập có giờ làm trong Bảng Lương (ngay_bat_dau_lam), không có thì Tháng/Năm vào làm ở Danh Sách NV (chỉ ghi tháng/năm thì lấy ngày 01)
    # (trong NĂM LẬP: người làm từ năm trước mà năm lập chưa có giờ làm -> 01/01 năm lập, không lấy ngày của năm trước)
    bat_dau = (ngay_date(tc.get("bat_dau")) or ngay_date(nv.get("ngay_bat_dau_lam")) or ngay_bat_dau_theo_nam(nv.get("vao_lam"), nam)
               or ngay_date(nv.get("vao_lam")))
    ngay_ky = ngay_date(tc.get("ngay_ky")) or bat_dau or ngay_date(tc.get("ngay"), hom_nay)
    bat_dau = bat_dau or ngay_ky
    loai_ten, cuoi, thang, bao_truoc = _thoi_han_hd(tc, nv, bat_dau)
    nam_so = ngay_ky.year if ngay_ky else hom_nay.year
    try:
        so_hd = str(tc.get("pt_mau_so") or "{so:02d}/HĐPT-{nam}").format(so=int(tc.get("so_bat_dau") or 1) + so_thu_tu, nam=nam_so)
    except Exception:
        so_hd = f"{int(tc.get('so_bat_dau') or 1) + so_thu_tu:02d}/HĐPT-{nam_so}"
    gan = bool(tc.get("gan_chu_ky", True)) and bool(chu_ky)
    anh_nld = tim_chu_ky(chu_ky, nv) if gan else ""
    anh_gd = (chu_ky.get("giam_doc") or "") if gan else ""
    ong_ba_ky = tc.get("ong_ba_ky") or "Ông/Bà"
    ong_ba = {"Nam": "Ông", "Nữ": "Bà"}.get(nv.get("gioi_tinh"), "Ông/Bà")
    gio_ngay, ngay_tuan, gio_tuan, gio_thang, don_gia, luong_dk = _gio_dien_ra(tc, nv)
    ng = nguong_part_time(ngay_ky.year if ngay_ky else nam, tc)
    khong_bh = luong_dk is None or luong_dk < ng - 1e-9          # chỉ ghi "không thuộc đối tượng BHXH" khi lương tháng dự kiến DƯỚI ngưỡng (thiếu dữ liệu: vẫn ghi theo mẫu, màn hình cảnh báo)
    h = ['<section class="vb-trang">', _tieu_ngu(cty, so_hd, tc.get("dia_danh"), ngay_ky),
         _p("&nbsp;"), _p("<b>HỢP ĐỒNG LAO ĐỘNG</b>", "c b"), _p("<b>(LÀM VIỆC KHÔNG TRỌN THỜI GIAN)</b>", "c b"),
         _p("Căn cứ Bộ luật Lao động số 45/2019/QH14 ngày 20/11/2019 (trong đó có Điều 32 về người lao động làm việc không trọn thời gian), Nghị định số 145/2020/NĐ-CP ngày 14/12/2020 "
            "của Chính phủ và Luật Bảo hiểm xã hội số 41/2024/QH15;", "j ti"),
         _p("Hôm nay, " + esc(ngay_chu(ngay_ky)) + f", tại {esc(tc.get('dia_diem') or cty.get('dia_chi') or '..........')}, chúng tôi gồm:", "j ti"),
         _p("<b>Người sử dụng lao động</b> (sau đây gọi là Công ty):"),
         _p(f"{esc(ong_ba_ky)}: <b>{esc((tc.get('nguoi_ky') or '').upper())}</b>&nbsp;&nbsp;&nbsp;Quốc tịch: Việt Nam", "l1"),
         _p(f"Chức vụ: {esc(tc.get('chuc_danh_ky') or 'Giám đốc')}", "l1"),
         _p(f"Đại diện cho: <b>{esc((cty.get('ten') or '').upper())}</b>" + (f" — Mã số thuế: {esc(cty['mst'])}" if cty.get("mst") else ""), "l1"),
         _p(f"Địa chỉ: {esc(cty.get('dia_chi') or '')}", "l1")]
    if tc.get("dien_thoai"):
        h.append(_p(f"Điện thoại: {esc(tc['dien_thoai'])}", "l1"))
    h += [_p("<b>Người lao động</b> (sau đây gọi là Người lao động):"),
          _p(f"{esc(ong_ba)}: <b>{esc(nv['ten'].upper())}</b>&nbsp;&nbsp;&nbsp;Quốc tịch: {esc(tc.get('quoc_tich') or 'Việt Nam')}", "l1"),
          _p(f"Sinh ngày: {esc(nv.get('ngay_sinh') or '..../..../........')}" + (f"&nbsp;&nbsp;&nbsp;Giới tính: {esc(nv['gioi_tinh'])}" if nv.get("gioi_tinh") else ""), "l1"),
          _p(f"Nơi cư trú: {esc(nv.get('dia_chi') or '..............................')}", "l1")]
    cccd = nv.get("cccd")
    noi_cap = tc.get("noi_cap_cccd") if (cccd and len(re.sub(r"\D", "", cccd)) == 12) else "........................"
    h.append(_p(f"Số CCCD/CMND: {esc(cccd or '............')}, cấp ngày: {esc(nv.get('ngay_cap') or '..../..../........')}, nơi cấp: {esc(noi_cap)}", "l1"))
    h.append(_p("Hai bên thỏa thuận ký kết hợp đồng lao động làm việc không trọn thời gian và cam kết thực hiện đúng những điều khoản sau đây:", "j ti"))

    # Điều 1
    cv = (tc.get("cong_viec") or "").strip() or f"Thực hiện các nhiệm vụ của chức danh {nv.get('chuc_vu') or '.........'} theo phân công, hướng dẫn của Người sử dụng lao động"
    co_bp = bool((tc.get("bo_phan") or "").strip())
    h.append(_p("<b>Điều 1. Chức danh và công việc phải làm</b>"))
    n1 = 0
    if co_bp:
        n1 += 1
        h.append(_p(f"{n1}. Bộ phận làm việc: {esc(tc['bo_phan'])}.", "j"))
    h.append(_p(f"{n1 + 1}. Chức danh chuyên môn / chức vụ: {esc(nv.get('chuc_vu') or '..........')}.", "j"))
    h.append(_p(f"{n1 + 2}. Công việc phải làm: {esc(cv)}.", "j"))

    # Điều 2 — thời giờ làm việc: theo LỊCH SẮP XẾP của Công ty (chỉ làm việc khi Công ty có lịch)
    h.append(_p("<b>Điều 2. Thời giờ làm việc, thời giờ nghỉ ngơi</b>"))
    chi_tiet = []
    if gio_ngay:
        chi_tiet.append(f"khoảng {_gio_hien(gio_ngay)} giờ/ngày")
    if gio_tuan:
        chi_tiet.append(f"tổng cộng khoảng {_gio_hien(gio_tuan)} giờ/tuần")
    if (tc.get("pt_lich") or "").strip():
        chi_tiet.append(esc(tc["pt_lich"]))
    if (tc.get("pt_khung_gio") or "").strip():
        chi_tiet.append(f"khung giờ: {esc(tc['pt_khung_gio'])}")
    h.append(_p("1. Thời giờ làm việc: <b>theo lịch sắp xếp của Công ty</b>. Người lao động chỉ làm việc khi Công ty có lịch sắp xếp và thông báo trước (số giờ làm việc trong ngày, trong tuần "
                "theo lịch đã thông báo)" + (f"; dự kiến {', '.join(chi_tiet)}" if chi_tiet else "")
                + ". Đây là thời giờ làm việc <b>ngắn hơn</b> thời giờ làm việc bình thường (08 giờ/ngày, 48 giờ/tuần) theo quy định của pháp luật và nội quy lao động của Công ty.", "j"))
    h.append(_p("2. Việc thay đổi lịch làm việc do Công ty thông báo (bằng văn bản, tin nhắn hoặc thư điện tử) không làm thay đổi tính chất làm việc không trọn thời gian; "
                "số giờ làm việc thực tế hằng tháng được Công ty ghi nhận trên bảng chấm công và có xác nhận của Người lao động.", "j"))
    h.append(_p("3. Thời giờ nghỉ ngơi, an toàn, vệ sinh lao động: thực hiện theo quy định của Bộ luật Lao động năm 2019, tương ứng với thời gian làm việc thực tế và nội quy lao động của Công ty.", "j"))

    # Điều 3 — tiền lương
    h.append(_p("<b>Điều 3. Tiền lương và các khoản bổ sung</b>"))
    n3 = 0

    def d3(txt):
        nonlocal n3
        n3 += 1
        h.append(_p(f"{n3}. {txt}", "j"))
    if don_gia:
        d3(f"Hình thức trả lương: <b>theo giờ</b>. Mức lương: <b>{so_tien(don_gia)} đồng/giờ</b> (bằng chữ: {esc(doc_so_thanh_chu(don_gia))}). "
           "Mức lương theo giờ không thấp hơn mức lương tối thiểu giờ theo quy định của pháp luật.")
    else:
        d3("Hình thức trả lương: <b>theo giờ</b>. Mức lương: ................ đồng/giờ (bằng chữ: ............................).")
    if luong_dk:
        d3(f"Số giờ làm việc dự kiến khoảng {_gio_hien(gio_thang)} giờ/tháng; <b>tổng tiền lương dự kiến hằng tháng khoảng {so_tien(luong_dk)} đồng/tháng</b>"
           + (f", <b>dưới {so_tien(ng)} đồng/tháng</b>." if khong_bh else f" (từ {so_tien(ng)} đồng/tháng trở lên)."))
    d3("Tiền lương thực nhận hằng tháng = số giờ làm việc thực tế trong tháng × mức lương theo giờ. Tháng không làm việc hoặc không có giờ làm việc thì không phát sinh tiền lương.")
    d3("Phụ cấp lương và các khoản bổ sung khác: <b>không có</b>, trừ trường hợp được Công ty quyết định bằng văn bản.")
    d3(f"Hình thức trả lương: {esc(tc.get('hinh_thuc_tra') or 'chuyển khoản')}; kỳ trả lương: hằng tháng, vào ngày {int(_so(tc.get('ngay_tra')) or 5):02d} của tháng sau.")
    d3("Làm thêm giờ, làm việc ban đêm (nếu có và được hai bên đồng ý): được trả lương theo quy định tại Điều 98 Bộ luật Lao động năm 2019.")

    # Điều 4 — BHXH
    h.append(_p("<b>Điều 4. Bảo hiểm xã hội, bảo hiểm y tế, bảo hiểm thất nghiệp và thuế thu nhập cá nhân</b>"))
    if khong_bh:
        h.append(_p("1. Do thời giờ làm việc và mức tiền lương tháng không đạt mức tối thiểu làm căn cứ đóng bảo hiểm xã hội bắt buộc theo quy định của Luật Bảo hiểm xã hội, "
                    "Người lao động không thuộc đối tượng tham gia bảo hiểm xã hội, bảo hiểm y tế, bảo hiểm thất nghiệp bắt buộc.", "j"))
        h.append(_p(f"2. Tháng nào tiền lương thực nhận của Người lao động đạt từ {so_tien(ng)} đồng/tháng trở lên (hoặc khi pháp luật có quy định khác) thì hai bên thực hiện tham gia bảo hiểm xã hội, "
                    "bảo hiểm y tế, bảo hiểm thất nghiệp bắt buộc theo quy định của pháp luật kể từ tháng đó.", "j"))
    else:
        h.append(_p("1. Tiền lương tháng của Người lao động đạt mức thuộc đối tượng tham gia bảo hiểm xã hội bắt buộc: Công ty và Người lao động cùng tham gia và đóng bảo hiểm xã hội, "
                    "bảo hiểm y tế, bảo hiểm thất nghiệp theo quy định của pháp luật.", "j"))
    h.append(_p(f"{2 if not khong_bh else 3}. Thuế thu nhập cá nhân: Công ty khấu trừ và nộp theo quy định của pháp luật về thuế thu nhập cá nhân.", "j"))

    # Điều 5 — quyền, nghĩa vụ
    h += [_p("<b>Điều 5. Quyền và nghĩa vụ của hai bên</b>"),
          _p("1. Người lao động: hoàn thành công việc đã cam kết; chấp hành nội quy lao động, quy định về an toàn, vệ sinh lao động và bảo vệ bí mật kinh doanh; được trả lương đầy đủ, đúng hạn; "
             "được bảo đảm các điều kiện làm việc và quyền lợi khác theo quy định của pháp luật. Người lao động có thể giao kết hợp đồng lao động với nhiều người sử dụng lao động nhưng phải bảo đảm thực hiện đầy đủ nội dung đã giao kết.", "j"),
          _p(f"2. Khi đơn phương chấm dứt hợp đồng lao động, hai bên tuân thủ Điều 35 và Điều 36 Bộ luật Lao động năm 2019; Người lao động báo trước cho Công ty ít nhất {esc(bao_truoc)}.", "j"),
          _p("3. Công ty: bảo đảm việc làm, ghi nhận đúng số giờ làm việc thực tế, thanh toán đầy đủ, đúng thời hạn tiền lương; khấu trừ, nộp thuế thu nhập cá nhân và thực hiện bảo hiểm (nếu thuộc diện) theo quy định của pháp luật.", "j")]

    # Điều 6
    h += [_p("<b>Điều 6. Điều khoản thi hành</b>"),
          _p("1. Những vấn đề không ghi trong hợp đồng này thì áp dụng theo thỏa ước lao động tập thể (nếu có) hoặc quy định của pháp luật lao động.", "j"),
          _p("2. Việc sửa đổi, bổ sung hợp đồng được lập bằng phụ lục hợp đồng lao động, báo trước cho bên kia ít nhất 03 ngày làm việc.", "j"),
          _p(f"3. Hợp đồng lao động được làm thành 02 bản có giá trị pháp lý như nhau, mỗi bên giữ 01 bản và có hiệu lực kể từ {esc(ngay_chu(bat_dau))}.", "j"),
          _p("&nbsp;"),
          _bang_ky("NGƯỜI LAO ĐỘNG", "(Ký, ghi rõ họ tên)", nv["ten"], "NGƯỜI SỬ DỤNG LAO ĐỘNG", f"({tc.get('chuc_danh_ky') or 'Giám đốc'} — Ký, ghi rõ họ tên, đóng dấu)", tc.get("nguoi_ky") or "",
                   anh_nld, anh_gd),
          "</section>"]
    return "".join(h)


def dung_hop_dong_part_time_nhieu(ds_nv, cty, tuy_chon, hom_nay=None, nam=None, chu_ky=None):
    return "".join(dung_hop_dong_part_time(nv, cty, tuy_chon, i, hom_nay, nam, chu_ky) for i, nv in enumerate(ds_nv))
