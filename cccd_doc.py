"""Đọc ảnh CCCD (mặt trước / mặt sau) bằng OCR chạy trên máy, ghép 2 mặt của cùng 1 người
và khớp với danh sách nhân viên.

- Mặt trước: lấy SỐ CCCD (12 số) -> khớp nhân viên theo số.
- Mặt sau: lấy HỌ TÊN từ dải MRZ (dòng chữ có dấu <<) + số CCCD nằm trong dòng MRZ đầu -> khớp theo họ tên.
OCR không giữ dấu tiếng Việt nên chỉ dùng để SO KHỚP (không dấu), tuyệt đối không ghi đè họ tên có sẵn.
Phần mềm chỉ gợi ý; người dùng xem lại bảng ghép rồi mới áp dụng."""
import difflib
import io
import re
import threading
import unicodedata

_OCR = None
_OCR_LOI = ""
_OCR_KHOA = threading.Lock()


def khong_dau(s):
    s = str(s or "").replace("đ", "d").replace("Đ", "D")
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower().strip()


def chuan_ten(s):
    """Họ tên so khớp: không dấu, chữ HOA, bỏ ký tự lạ, gộp khoảng trắng."""
    t = re.sub(r"[^a-z ]", " ", khong_dau(s).replace("<", " "))
    return " ".join(t.split()).upper()


def chuan_so(s):
    """Số CCCD: chỉ chữ số; số bị Excel mất số 0 đầu (11 số) được bù lại thành 12 số."""
    d = re.sub(r"\D", "", str(s or ""))
    if 9 < len(d) < 12:
        d = d.zfill(12)
    return d


def _nap_ocr():
    global _OCR, _OCR_LOI
    with _OCR_KHOA:
        if _OCR is None and not _OCR_LOI:
            try:
                from rapidocr_onnxruntime import RapidOCR
                _OCR = RapidOCR()
            except Exception as e:
                _OCR_LOI = ("Chưa có bộ đọc chữ trong ảnh (rapidocr-onnxruntime) trên máy này: %s. "
                            "Hãy đóng hẳn phần mềm rồi mở lại để tự cài, hoặc chạy: pip install rapidocr-onnxruntime" % e)
        return _OCR, _OCR_LOI


_RE_NGAY = re.compile(r"(\d{2})\s*[/.\-]\s*(\d{2})\s*[/.\-]\s*(\d{4})")


def _ngay_hop_le(d, m, y):
    try:
        import datetime
        datetime.date(int(y), int(m), int(d))
        return "%s/%s/%s" % (d, m, y)
    except Exception:
        return ""


def _tim_ngay(text):
    for m in _RE_NGAY.finditer(text or ""):
        k = _ngay_hop_le(*m.groups())
        if k:
            return k
    return ""


def _kiem_tra_mrz(so9, chk):
    tr = (7, 3, 1)
    try:
        return sum(int(c) * tr[i % 3] for i, c in enumerate(so9)) % 10 == int(chk)
    except Exception:
        return False


def phan_tich_dong(lines):
    """Từ các dòng chữ OCR của 1 ảnh -> {mat: truoc|sau|ca2|'', so, ten, ngay_sinh, ngay_cap, mrz_ok}."""
    ds = [str(x or "").strip() for x in lines if str(x or "").strip()]
    nho = [khong_dau(x) for x in ds]
    kq = {"mat": "", "so": "", "ten": "", "ngay_sinh": "", "ngay_cap": "", "mrz_ok": False}

    # --- dải MRZ (mặt sau) ---
    mrz1 = mrz2 = mrz3 = ""
    mrz_ten = ""
    for x in ds:
        g = re.sub(r"\s+", "", x).upper()
        if g.startswith("IDVN") and not mrz1:
            mrz1 = g
        elif re.search(r"\d{6}\d[MF]\d{6}", g) and not mrz2:
            mrz2 = g
        elif g.count("<") >= 2 and re.search(r"[A-Z]{2,}", g) and not re.search(r"\d", g) and not mrz3:
            mrz3 = g
    so_mrz = ""
    if mrz1:
        m = re.match(r"IDVN[M]?(\d{9})(\d)(\d{12})", mrz1)
        if m:
            so_mrz = m.group(3)
            kq["mrz_ok"] = _kiem_tra_mrz(m.group(1), m.group(2)) and so_mrz.endswith(m.group(1))
        else:
            m = re.search(r"(\d{12})", mrz1)
            so_mrz = m.group(1) if m else ""
    if mrz3:
        mrz_ten = chuan_ten(mrz3.replace("<", " "))

    # --- mặt trước ---
    so_truoc = ""
    for x in ds:
        g = re.sub(r"[\s.:]", "", x)
        if re.fullmatch(r"\d{12}", g):
            so_truoc = g
            break
    if not so_truoc:
        for x, kd in zip(ds, nho):
            if x.upper().replace(" ", "").startswith("IDVN"):
                continue
            m = re.search(r"(?<!\d)(\d[\d ]{10,13}\d)(?!\d)", x)
            if m and len(re.sub(r"\D", "", m.group(1))) == 12 and ("no" in kd or "so" in kd):
                so_truoc = re.sub(r"\D", "", m.group(1))
                break
    ten_truoc = ""
    for i, kd in enumerate(nho):
        if "full name" in kd or "ho va ten" in kd:
            sau_nhan = re.split(r"full\s*name\s*:?", ds[i], flags=re.I)[-1].strip(" :/")
            cand = [sau_nhan] + ds[i + 1:i + 3]
            for c in cand:
                t = chuan_ten(c)
                if len(t.split()) >= 2 and not re.search(r"\d", c) and "date of birth" not in khong_dau(c):
                    ten_truoc = t
                    break
            break
    sinh = ""
    for i, kd in enumerate(nho):
        if "birth" in kd or "ngay sinh" in kd:
            sinh = _tim_ngay(ds[i]) or (_tim_ngay(ds[i + 1]) if i + 1 < len(ds) else "")
            break
    if not sinh and mrz2:
        m = re.search(r"(\d{2})(\d{2})(\d{2})\d[MF]", mrz2)
        if m:
            import datetime
            yy, mm, dd = m.groups()
            nam = int(yy) + (2000 if int(yy) <= datetime.date.today().year % 100 else 1900)
            sinh = _ngay_hop_le(dd, mm, str(nam))
    cap = ""
    for i, kd in enumerate(nho):
        if ("date" in kd and "month" in kd) or "ngay, thang" in kd or "ngay.thang" in kd or "thang, nam" in kd:
            cap = _tim_ngay(ds[i]) or (_tim_ngay(ds[i + 1]) if i + 1 < len(ds) else "")
            break

    co_truoc = any(k in kd for kd in nho for k in ("can cuoc", "citizen identity", "full name", "place of origin", "nationality", "cong hoa xa hoi")) or bool(so_truoc)
    co_sau = bool(mrz1 or mrz3) or any(k in kd for kd in nho for k in ("personal identification", "ngon tro", "index finger", "canh sat", "director general"))
    if co_truoc and co_sau:
        kq["mat"] = "ca2"
    elif co_sau:
        kq["mat"] = "sau"
    elif co_truoc:
        kq["mat"] = "truoc"
    kq["so"] = so_truoc or so_mrz
    kq["ten"] = ten_truoc or mrz_ten
    kq["ngay_sinh"] = sinh
    if kq["mat"] in ("sau", "ca2"):
        kq["ngay_cap"] = cap
    return kq


def _ocr_mot_anh(arr):
    ocr, loi = _nap_ocr()
    if ocr is None:
        raise RuntimeError(loi)
    with _OCR_KHOA:
        res, _ = ocr(arr)
    res = res or []
    res = sorted(res, key=lambda r: (min(p[1] for p in r[0]), min(p[0] for p in r[0])))
    return [r[1] for r in res]


def doc_anh(data):
    """Đọc 1 ảnh (bytes) -> kết quả phan_tich_dong + 'canh_bao'. Tự xoay ảnh nếu lần đầu không nhận ra mặt nào."""
    from PIL import Image, ImageOps
    import numpy as np
    if not data or len(data) > 25 * 1024 * 1024:
        return {"mat": "", "so": "", "ten": "", "ngay_sinh": "", "ngay_cap": "", "mrz_ok": False, "canh_bao": "Ảnh rỗng hoặc quá lớn (>25MB)"}
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception:
        return {"mat": "", "so": "", "ten": "", "ngay_sinh": "", "ngay_cap": "", "mrz_ok": False, "canh_bao": "Không mở được file ảnh (chỉ nhận JPG/PNG/WEBP)"}
    img = ImageOps.exif_transpose(img).convert("RGB")
    canh = max(img.size)
    if canh > 2200:
        k = 2200.0 / canh
        img = img.resize((int(img.width * k), int(img.height * k)))
    kq = None
    for goc in (0, 90, 180, 270):
        im = img.rotate(goc, expand=True) if goc else img
        kq = phan_tich_dong(_ocr_mot_anh(np.array(im)[:, :, ::-1]))
        if kq["mat"] and (kq["so"] or kq["ten"]):
            break
    kq["canh_bao"] = "" if (kq["mat"] and (kq["so"] or kq["ten"])) else "Không nhận ra đây là mặt trước/mặt sau CCCD (ảnh mờ, bị che hoặc không phải CCCD gắn chip)"
    return kq


def chuan_anh_jpeg(data, canh_toi_da=1600):
    """Chuẩn hoá ảnh lưu: tự xoay theo EXIF, thu nhỏ, JPEG. Trả bytes; ném ValueError nếu không phải ảnh."""
    from PIL import Image, ImageOps
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception:
        raise ValueError("Không phải file ảnh hợp lệ")
    img = ImageOps.exif_transpose(img).convert("RGB")
    c = max(img.size)
    if c > canh_toi_da:
        k = canh_toi_da / c
        img = img.resize((int(img.width * k), int(img.height * k)))
    out = io.BytesIO()
    img.save(out, "JPEG", quality=85)
    return out.getvalue()


def _cot(header, *khoa):
    for i, h in enumerate(header or []):
        k = khong_dau(h)
        if any(k == x for x in khoa):
            return i
    return -1


def ghep(docs, header, rows):
    """docs: [{id, mat, so, ten, ngay_sinh, ngay_cap}] (kết quả đọc từng ảnh); header/rows: danh sách nhân viên đang hiển thị.
    Trả {nhom: [...]} — mỗi nhóm = 1 người (mặt trước + mặt sau), kèm dòng nhân viên khớp (row) hoặc ứng viên."""
    i_ten = _cot(header, "ho va ten")
    i_cccd = _cot(header, "cccd")
    i_ma = _cot(header, "ma nv")
    i_sinh = _cot(header, "ngay sinh")
    i_cap = _cot(header, "ngay cap")
    nv = []
    for ri, r in enumerate(rows or []):
        ten = r[i_ten] if 0 <= i_ten < len(r) else ""
        nv.append({"ri": ri, "ten": str(ten or ""), "chuan": chuan_ten(ten),
                   "so": chuan_so(r[i_cccd]) if 0 <= i_cccd < len(r) else ""})

    # 1) gom ảnh thành người: theo SỐ trước; ảnh chỉ có tên thì ghép vào nhóm số cùng tên (nếu duy nhất)
    nhom = []
    theo_so = {}
    for d in docs:
        so = chuan_so(d.get("so"))
        if len(so) == 12:
            g = theo_so.get(so)
            if g is None:
                g = {"so": so, "ten": "", "truoc": [], "sau": [], "ngay_sinh": "", "ngay_cap": "", "canh_bao": []}
                theo_so[so] = g
                nhom.append(g)
            _them_anh(g, d)
    for d in docs:
        so = chuan_so(d.get("so"))
        if len(so) == 12:
            continue
        ten = chuan_ten(d.get("ten"))
        if not ten:
            continue
        cho = [g for g in nhom if chuan_ten(g["ten"]) == ten and (not g["sau"] if d.get("mat") == "sau" else not g["truoc"])]
        if len(cho) == 1:
            _them_anh(cho[0], d)
            continue
        g = {"so": "", "ten": "", "truoc": [], "sau": [], "ngay_sinh": "", "ngay_cap": "", "canh_bao": []}
        if len(cho) > 1:
            g["canh_bao"].append("Có nhiều người trùng họ tên này — hãy chọn đúng nhân viên")
        nhom.append(g)
        _them_anh(g, d)

    # 2) khớp từng người với nhân viên
    da_dung = {}
    for g in nhom:
        g["row"] = -1
        g["cach"] = ""
        g["ung_vien"] = []
        ten_g = chuan_ten(g["ten"])
        theo_so_nv = [n for n in nv if g["so"] and n["so"] == g["so"]]
        if len(theo_so_nv) == 1:
            g["row"], g["cach"] = theo_so_nv[0]["ri"], "so"
            if ten_g and theo_so_nv[0]["chuan"] and ten_g != theo_so_nv[0]["chuan"] and \
                    difflib.SequenceMatcher(None, ten_g, theo_so_nv[0]["chuan"]).ratio() < 0.8:
                g["canh_bao"].append("Số CCCD khớp nhưng họ tên trên thẻ (%s) khác họ tên trong danh sách" % g["ten"])
        elif len(theo_so_nv) > 1:
            g["ung_vien"] = [n["ri"] for n in theo_so_nv]
            g["canh_bao"].append("Có nhiều nhân viên trùng số CCCD này")
        elif ten_g:
            dung = [n for n in nv if n["chuan"] == ten_g]
            if len(dung) == 1:
                n = dung[0]
                if g["so"] and n["so"] and n["so"] != g["so"]:
                    g["ung_vien"] = [n["ri"]]
                    g["canh_bao"].append("Trùng họ tên nhưng số CCCD trong danh sách (%s) khác số trên thẻ — có thể là người khác" % n["so"])
                else:
                    g["row"], g["cach"] = n["ri"], "ten"
            elif len(dung) > 1:
                g["ung_vien"] = [n["ri"] for n in dung]
                g["canh_bao"].append("Có %d nhân viên trùng họ tên — hãy chọn đúng người" % len(dung))
            else:
                gan = sorted(((difflib.SequenceMatcher(None, ten_g, n["chuan"]).ratio(), n) for n in nv if n["chuan"]), key=lambda t: -t[0])
                if gan and gan[0][0] >= 0.88 and (len(gan) == 1 or gan[0][0] - gan[1][0] >= 0.05) and not (g["so"] and gan[0][1]["so"] and gan[0][1]["so"] != g["so"]):
                    g["row"], g["cach"] = gan[0][1]["ri"], "gan_dung"
                    g["canh_bao"].append("Họ tên khớp gần đúng (OCR có thể đọc sai 1-2 chữ) — hãy kiểm tra")
        if g["row"] >= 0:
            if g["row"] in da_dung:
                g["canh_bao"].append("Nhân viên này đã được ghép với 1 người khác ở trên — kiểm tra lại")
            da_dung[g["row"]] = True
        if not g["truoc"]:
            g["canh_bao"].append("Chưa có ảnh mặt trước")
        if not g["sau"]:
            g["canh_bao"].append("Chưa có ảnh mặt sau")
        if len(g["truoc"]) > 1 or len(g["sau"]) > 1:
            g["canh_bao"].append("Có ảnh trùng cùng 1 mặt — chỉ lưu ảnh đầu tiên")
        # điền ô còn trống (không bao giờ ghi đè ô đã có)
        g["dien"] = {}
        if g["row"] >= 0:
            r = rows[g["row"]]
            for ten_cot, i, gt in (("CCCD", i_cccd, g["so"]), ("Ngày sinh", i_sinh, g["ngay_sinh"]), ("Ngày cấp", i_cap, g["ngay_cap"])):
                if i >= 0 and gt and not str(r[i] if i < len(r) else "").strip():
                    g["dien"][ten_cot] = gt
            if i_ma >= 0 and i_ma < len(r):
                g["ma_nv"] = str(r[i_ma] or "")
    return {"nhom": nhom}


def _them_anh(g, d):
    mat = d.get("mat")
    if d.get("so") and not g["so"]:
        g["so"] = chuan_so(d.get("so"))
    if not g["ten"] and d.get("ten"):
        g["ten"] = d["ten"]
    if d.get("ngay_sinh") and not g["ngay_sinh"]:
        g["ngay_sinh"] = d["ngay_sinh"]
    if d.get("ngay_cap") and not g["ngay_cap"]:
        g["ngay_cap"] = d["ngay_cap"]
    if mat in ("truoc", "ca2"):
        g["truoc"].append(d.get("id"))
    if mat in ("sau", "ca2"):
        g["sau"].append(d.get("id"))
