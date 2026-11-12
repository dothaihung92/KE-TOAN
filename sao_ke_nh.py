"""Đọc file SAO KÊ ngân hàng (Excel .xlsx/.xls, .xls dạng HTML, .csv) tải từ internet banking doanh nghiệp
(Vietcombank, ACB, VietinBank, Techcombank — và ngân hàng khác nếu file có dòng tiêu đề thông thường) ra danh sách giao dịch chuẩn
+ văn bản TAB (Ngày | Nội dung giao dịch | Tiền ra | Tiền vào) đúng định dạng ô "Dán dữ liệu" của công cụ Đối Chiếu Ngân Hàng.

File mỗi ngân hàng có vài dòng tiêu đề (tên ngân hàng, số tài khoản, số dư đầu kỳ...) trước bảng giao dịch, tiêu đề có thể 1 hoặc 2 dòng
(vd "Số tiền" trên, "Ghi nợ | Ghi có" dưới), song ngữ Việt/Anh — nên đọc theo TỪ KHÓA của dòng tiêu đề, không theo vị trí cột cố định."""
import csv
import datetime as _dt
import html as _html
import io
import re
import unicodedata

NGAN_HANG = {
    "vcb": {"ten": "Vietcombank", "url": "https://vcbdigibiz.vietcombank.com.vn/",
            "mien": ["vietcombank.com.vn"], "nhan": r"VIETCOMBANK|NGOAI THUONG|\bVCB\b"},
    "acb": {"ten": "ACB", "url": "https://onebiz.acb.com.vn/",
            "mien": ["acb.com.vn"], "nhan": r"\bACB\b|A CHAU"},
    "vtb": {"ten": "VietinBank", "url": "https://efast.vietinbank.vn/",
            "mien": ["vietinbank.vn"], "nhan": r"VIETINBANK|CONG THUONG|EFAST"},
    "tcb": {"ten": "Techcombank", "url": "https://business.techcombank.com.vn/",
            "mien": ["techcombank.com.vn", "techcombank.com"], "nhan": r"TECHCOMBANK|KY THUONG|\bTCB\b"},
}


def chuan(s):
    """Bỏ dấu, viết hoa, gọn khoảng trắng: 'Ngày giao dịch' -> 'NGAY GIAO DICH'."""
    s = unicodedata.normalize("NFD", str(s if s is not None else "")).replace("đ", "d").replace("Đ", "D")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s).strip().upper()


# ---------------- đọc file thành bảng (list các dòng, mỗi dòng list ô) ----------------
def _bang_html(b):
    t = b.decode("utf-8", "ignore")
    if "�" in t[:2000] or not re.search(r"<t[dh]", t, re.I):
        t = b.decode("cp1258", "ignore")
    rows = []
    for tr in re.findall(r"<tr\b.*?</tr>", t, re.I | re.S):
        o = []
        for m in re.finditer(r"<t([dh])\b([^>]*)>(.*?)</t[dh]>", tr, re.I | re.S):
            txt = re.sub(r"<br\s*/?>", " ", m.group(3), flags=re.I)
            txt = _html.unescape(re.sub(r"<[^>]+>", "", txt)).strip()
            o.append(txt)
            cs = re.search(r'colspan\s*=\s*"?(\d+)', m.group(2), re.I)
            o.extend([""] * (int(cs.group(1)) - 1 if cs else 0))
        rows.append(o)
    return rows


def doc_bang(noi_dung, ten_file=""):
    """Trả list các bảng (mỗi sheet 1 bảng)."""
    b = bytes(noi_dung or b"")
    dau = b[:600].lstrip().lower()
    if dau.startswith((b"<", b"\xef\xbb\xbf<")) or b"<table" in dau or b"<html" in dau:
        return [_bang_html(b)]
    if b[:4] == b"PK\x03\x04":
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(b), read_only=True, data_only=True)
        return [[list(r) for r in ws.iter_rows(values_only=True)] for ws in wb.worksheets]
    if b[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        import xlrd
        bk = xlrd.open_workbook(file_contents=b)
        kq = []
        for sh in bk.sheets():
            rows = []
            for i in range(sh.nrows):
                r = []
                for c in sh.row(i):
                    v = c.value
                    if c.ctype == xlrd.XL_CELL_DATE:
                        try:
                            v = xlrd.xldate.xldate_as_datetime(v, bk.datemode)
                        except Exception:
                            pass
                    r.append(v)
                rows.append(r)
            kq.append(rows)
        return kq
    t = None
    for enc in ("utf-8-sig", "utf-16", "cp1258"):
        try:
            t = b.decode(enc)
            break
        except Exception:
            continue
    t = t or b.decode("latin-1")
    dong1 = t.split("\n", 1)[0]
    sep = max(("\t", ",", ";"), key=dong1.count)
    return [[r for r in csv.reader(io.StringIO(t), delimiter=sep)]]


# ---------------- giá trị ô ----------------
def _ngay(v):
    if isinstance(v, _dt.datetime):
        return v.date()
    if isinstance(v, _dt.date):
        return v
    if isinstance(v, (int, float)) and 30000 < v < 80000:          # số serial Excel
        return (_dt.datetime(1899, 12, 30) + _dt.timedelta(days=float(v))).date()
    s = str(v or "").strip()
    m = re.match(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})", s)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        m = re.match(r"^(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})", s)
        if not m:
            return None
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        return _dt.date(y, mo, d)
    except ValueError:
        return None


def _so(v):
    """'1,234,567' / '1.234.567' / '1,234,567.50' / '(1.000)' / '-500' / số -> float (None nếu không phải số)."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(" ", "").replace(" ", "")
    s = re.sub(r"(VND|VNĐ|USD|đ)$", "", s, flags=re.I)
    if not s or s in ("-", "--"):
        return None
    am = s.startswith("(") and s.endswith(")") or s.startswith("-")
    s = s.strip("()+-")
    if not re.fullmatch(r"[\d.,]+", s):
        return None
    if "," in s and "." in s:
        s = s.replace(",", "") if s.rfind(".") > s.rfind(",") else s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", "") if re.fullmatch(r"\d{1,3}(,\d{3})+", s) else s.replace(",", ".")
    elif "." in s and re.fullmatch(r"\d{1,3}(\.\d{3})+", s):
        s = s.replace(".", "")
    try:
        n = float(s)
    except ValueError:
        return None
    return -n if am else n


# ---------------- nhận dòng tiêu đề ----------------
def _vai_tro(t):
    """Vai trò 1 ô tiêu đề (đã chuẩn hoá)."""
    if not t or len(t) > 80:
        return None
    if re.search(r"SO DU|BALANCE", t):
        return "du"
    if re.search(r"THAM CHIEU|SO CT\b|SO CHUNG TU|SO BUT TOAN|REFERENCE|\bREF\b|MA GIAO DICH|TRANSACTION (NO|NUMBER|ID)|SO GD\b|SEQ", t):
        return "ct"
    if re.search(r"^(NO ?/ ?CO|D ?/ ?C|DR ?/ ?CR|DEBIT ?/ ?CREDIT)$|LOAI GIAO DICH|LOAI GD", t):
        return "loai"
    if re.search(r"NOI DUNG|DIEN GIAI|MO TA|DESCRIPTION|DETAIL|REMARK|NARRATIVE|CHI TIET", t):
        return "nd"
    if re.search(r"GHI NO|\bDEBIT|TIEN RA|RUT TIEN|RUT RA|PHAT SINH NO|SO TIEN NO|WITHDRAW|\bNO \(-\)|^NO$|^CHI$|^RA$|TIEN CHI", t):
        return "ra"
    if re.search(r"GHI CO|\bCREDIT|TIEN VAO|GUI TIEN|GUI VAO|PHAT SINH CO|SO TIEN CO|DEPOSIT|\bCO \(\+\)|^CO$|^THU$|^VAO$|TIEN THU", t):
        return "vao"
    if re.search(r"NGAY|DATE", t):
        return "ngay"
    if re.search(r"^SO TIEN|AMOUNT", t):
        return "tien"
    if re.search(r"NO ?/ ?CO|D ?/ ?C\b|DEBIT ?/ ?CREDIT|LOAI GIAO DICH|LOAI GD|TYPE", t):
        return "loai"
    return None


def _ghep_tieu_de(r1, r2):
    """Tiêu đề 2 dòng: ô trên (kéo sang phải nếu ô gộp) + ô dưới."""
    n = max(len(r1), len(r2 or []))
    kq, tren = [], ""
    for i in range(n):
        a = chuan(r1[i]) if i < len(r1) else ""
        b = chuan(r2[i]) if r2 is not None and i < len(r2) else ""
        if a:
            tren = a
        kq.append((a or (tren if b else "")) + (" " + b if b else ""))
    return kq


def _ban_do(cot):
    bd = {}
    for i, t in enumerate(cot):
        v = _vai_tro(t)
        if v == "ngay":       # có nhiều cột ngày: ưu tiên ngày giao dịch, bỏ ngày hiệu lực/giá trị
            if "ngay" in bd and not re.search(r"GIAO DICH|TRANSACTION|HACH TOAN|POSTING|^NGAY$|^DATE$", t):
                continue
            if "ngay" in bd and re.search(r"GIAO DICH|TRANSACTION", cot[bd["ngay"]]):
                continue
        if v and (v not in bd or v == "ngay"):
            bd[v] = i
    return bd


def _hop_le(bd):
    return "ngay" in bd and ("nd" in bd or "ct" in bd) and (("ra" in bd and "vao" in bd) or "tien" in bd)


def _tim_tieu_de(rows):
    for i in range(min(len(rows), 80)):
        r = rows[i]
        if not any(str(x or "").strip() for x in r):
            continue
        for r2 in ((rows[i + 1] if i + 1 < len(rows) else None), None):
            if r2 is not None and any(_ngay(x) for x in r2):      # dòng dưới là dữ liệu -> tiêu đề 1 dòng
                continue
            cot = _ghep_tieu_de(r, r2)
            bd = _ban_do(cot)
            if _hop_le(bd):
                return i + (2 if r2 is not None else 1), bd, cot
    return None, None, None


def _nhan_ngan_hang(ten_file, rows):
    t = chuan(ten_file) + " " + " ".join(chuan(x) for r in rows[:15] for x in r if x)
    for k, v in NGAN_HANG.items():
        if re.search(v["nhan"], t):
            return k
    return ""


def _so_tk(rows, den):
    for r in rows[:den]:
        for j, x in enumerate(r):
            t = chuan(x)
            if re.search(r"SO TAI KHOAN|ACCOUNT (NO|NUMBER)|^TAI KHOAN|SO TK", t):
                m = re.search(r"(\d[\d .\-]{5,24}\d)", str(x))
                if not m:
                    for y in r[j + 1:j + 4]:
                        m = re.search(r"(\d[\d .\-]{5,24}\d)", str(y or ""))
                        if m:
                            break
                if m:
                    return re.sub(r"\D", "", m.group(1))
    return ""


_KET_THUC = re.compile(r"^(TONG CONG|TONG PHAT SINH|CONG PHAT SINH|TOTAL|SO DU CUOI|CLOSING BALANCE|TONG SO)")


def doc_sao_ke(noi_dung, ten_file=""):
    """Trả {"ngan_hang","so_tk","giao_dich":[{ngay,noi_dung,tien_ra,tien_vao,so_ct,so_du}],"tsv","tu","den","canh_bao"}."""
    canh_bao = []
    for rows in doc_bang(noi_dung, ten_file):
        rows = [list(r) for r in rows]
        bat_dau, bd, cot = _tim_tieu_de(rows)
        if bat_dau is None:
            continue
        gd = []
        for r in rows[bat_dau:]:
            o = lambda k: r[bd[k]] if k in bd and bd[k] < len(r) else None
            dau = " ".join(chuan(x) for x in r[:4] if x not in (None, ""))
            if _KET_THUC.search(dau):
                break
            ngay = _ngay(o("ngay"))
            nd = re.sub(r"\s+", " ", str(o("nd") or "")).strip()
            if ngay is None:
                if gd and nd and _so(o("ra")) is None and _so(o("vao")) is None and _so(o("tien")) is None:
                    gd[-1]["noi_dung"] = (gd[-1]["noi_dung"] + " " + nd).strip()      # nội dung xuống dòng sang dòng sau
                continue
            if "ra" in bd and "vao" in bd:
                ra, vao = abs(_so(o("ra")) or 0), abs(_so(o("vao")) or 0)
            else:
                n = _so(o("tien")) or 0
                lo = chuan(o("loai"))
                if lo:
                    la_ra = bool(re.match(r"^(D|DR|N|NO|DEBIT|GHI NO|RUT|CHI)\b", lo))
                else:
                    la_ra = n < 0
                ra, vao = (abs(n), 0.0) if la_ra else (0.0, abs(n))
            if not ra and not vao:
                continue
            gd.append({"ngay": ngay.strftime("%d/%m/%Y"), "noi_dung": nd, "tien_ra": ra, "tien_vao": vao,
                       "so_ct": str(o("ct") or "").strip(), "so_du": _so(o("du"))})
        if not gd:
            canh_bao.append("Có dòng tiêu đề nhưng không có giao dịch nào.")
            continue
        nh = _nhan_ngan_hang(ten_file, rows)
        ngay_ds = sorted(_dt.datetime.strptime(x["ngay"], "%d/%m/%Y") for x in gd)
        return {"ngan_hang": nh, "ten_ngan_hang": NGAN_HANG.get(nh, {}).get("ten", ""), "so_tk": _so_tk(rows, bat_dau),
                "giao_dich": gd, "tsv": tsv(gd), "tu": ngay_ds[0].strftime("%d/%m/%Y"), "den": ngay_ds[-1].strftime("%d/%m/%Y"),
                "cot": [c for c in cot if c], "canh_bao": canh_bao}
    raise ValueError("Không nhận ra bảng giao dịch trong file sao kê (cần có cột Ngày, Nội dung/Diễn giải và Ghi nợ/Ghi có hoặc Số tiền). "
                     "Hãy gửi file mẫu để bổ sung định dạng ngân hàng này.")


def _tien(v):
    if not v:
        return ""
    return str(int(round(v))) if abs(v - round(v)) < 0.005 else f"{v:.2f}"


def tsv(gd):
    dong = ["Ngày\tNội dung giao dịch\tTiền ra\tTiền vào"]
    for x in gd:
        nd = x["noi_dung"].replace("\t", " ")      # KHÔNG nối số tham chiếu vào nội dung: dễ bị nhận nhầm là số hoá đơn khi đối chiếu
        dong.append("\t".join([x["ngay"], nd, _tien(x["tien_ra"]), _tien(x["tien_vao"])]))
    return "\n".join(dong)
