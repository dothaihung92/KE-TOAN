# -*- coding: utf-8 -*-
"""Soạn hồ sơ thay đổi đăng ký doanh nghiệp (GPKD) từ BIỂU MẪU CHÍNH THỨC.

Nguồn biểu mẫu: Phụ lục I Thông tư 68/2025/TT-BTC (đủ 80 mẫu) và Phụ lục I Thông tư 121/2026/TT-BTC (cập nhật các mẫu
1-5, 10, 12, 27, 30) — mẫu có trong TT 121/2026 thì LẤY BẢN MỚI. Mỗi mẫu được cắt ra từ file Thông tư (giữ nguyên định dạng) rồi
điền các ô "……" theo dữ liệu người dùng; ô nào không có dữ liệu thì GIỮ NGUYÊN dấu chấm (không tự bịa dữ liệu).
Giấy tờ này chỉ là bản NHÁP để người đại diện kiểm tra, ký — kế toán/luật sư rà soát nội dung trước khi nộp.
"""
import io
import unicodedata
import os
import re
import copy
import zipfile

import docx
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, Cm

BASE = os.path.dirname(os.path.abspath(__file__))
THU_MUC_MAU = os.path.join(BASE, "templates", "gpkd")
NGUON = [("TT121", "TT121_2026_PL1.docx", "Thông tư 121/2026/TT-BTC"),
         ("TT68", "TT68_2025_PL1.docx", "Thông tư 68/2025/TT-BTC")]       # thứ tự ưu tiên: bản mới trước
_RE_MAU = re.compile(r"^M[ẫa]u\s*(?:số\s*)?(\d{1,3})\s*$", re.I)
_CACHE_NGUON = {}
_CACHE_MAU = {}


def _chu(e):
    # NFC: một số tiêu đề trong file Thông tư dùng ký tự tổ hợp (vd "VỀ" = E + dấu mũ + dấu huyền) nên regex không khớp nếu không chuẩn hoá
    return unicodedata.normalize("NFC", "".join(t.text or "" for t in e.iter(qn("w:t")))).strip()


def _mo_nguon(ma):
    if ma not in _CACHE_NGUON:
        tep = next(t for m, t, _ in NGUON if m == ma)
        d = docx.Document(os.path.join(THU_MUC_MAU, tep))
        thanh = [c for c in d.element.body if c.tag != qn("w:sectPr")]
        moc = {}
        for i, c in enumerate(thanh):
            if c.tag == qn("w:p"):
                m = _RE_MAU.match(_chu(c))
                if m:
                    moc.setdefault(int(m.group(1)), i)
        _CACHE_NGUON[ma] = (d, thanh, moc)
    return _CACHE_NGUON[ma]


def danh_sach_mau():
    """{số mẫu: (mã nguồn, tên nguồn)} — mẫu có ở TT 121/2026 thì lấy bản đó."""
    kq = {}
    for ma, _t, ten in reversed(NGUON):
        for n in _mo_nguon(ma)[2]:
            kq[n] = (ma, ten)
    return dict(sorted(kq.items()))


def cat_mau(so_mau):
    """Cắt riêng 1 mẫu ra 1 Document (bản sao độc lập)."""
    so_mau = int(so_mau)
    nguon = danh_sach_mau().get(so_mau)
    if not nguon:
        raise KeyError(f"Không có Mẫu số {so_mau} trong Thông tư 121/2026 hoặc 68/2025")
    d, thanh, moc = _mo_nguon(nguon[0])
    bat_dau = moc[so_mau]
    sau = sorted(i for n, i in moc.items() if i > bat_dau)
    ket_thuc = sau[0] if sau else len(thanh)
    giu = {id(c) for c in thanh[bat_dau:ket_thuc]}
    ban = docx.Document(io.BytesIO(_luu_bytes(d)))
    t2 = [c for c in ban.element.body if c.tag != qn("w:sectPr")]
    for i, c in enumerate(t2):
        if not (bat_dau <= i < ket_thuc):
            ban.element.body.remove(c)
    return ban


def _luu_bytes(d):
    bio = io.BytesIO()
    d.save(bio)
    return bio.getvalue()


# ============================================================ ĐỌC SỐ TIỀN THÀNH CHỮ
_CHU_SO = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]


def _doc_3(n, day_du):
    """Đọc 0..999. day_du=True: nhóm này đứng sau nhóm khác -> đọc đủ 'không trăm', 'linh'."""
    tram, chuc, dv = n // 100, (n // 10) % 10, n % 10
    kq = []
    if tram or day_du:
        kq.append(_CHU_SO[tram] + " trăm")
    if chuc > 1:
        kq.append(_CHU_SO[chuc] + " mươi")
    elif chuc == 1:
        kq.append("mười")
    elif (tram or day_du) and dv:
        kq.append("linh")
    if dv:
        if chuc > 1 and dv == 1:
            kq.append("mốt")
        elif chuc > 1 and dv == 4:
            kq.append("tư")
        elif chuc >= 1 and dv == 5:
            kq.append("lăm")
        elif chuc == 0 and (tram or day_du) and dv == 5:
            kq.append("năm")
        else:
            kq.append(_CHU_SO[dv])
    return " ".join(kq)


def _doc_duoi_ty(n, co_truoc=False):
    """Đọc 0 < n < 1e9 (triệu/nghìn/đơn vị); co_truoc: phía trước đã có số (đọc đủ 'không trăm', 'linh')."""
    don_vi = ["", " nghìn", " triệu"]
    nhom = []
    while n:
        nhom.append(n % 1000)
        n //= 1000
    kq = []
    for i in range(len(nhom) - 1, -1, -1):
        if nhom[i] == 0:
            continue
        kq.append(_doc_3(nhom[i], day_du=bool(kq) or co_truoc) + don_vi[i])
    return " ".join(kq)


def doc_so_vn(n):
    """1000000000 -> 'một tỷ'; 5300000 -> 'năm triệu ba trăm nghìn'; 1500000000000 -> 'một nghìn năm trăm tỷ'; 0 -> 'không'."""
    n = int(n)
    if n == 0:
        return "không"
    if n < 0:
        return "âm " + doc_so_vn(-n)
    ty, du = divmod(n, 10 ** 9)
    if not ty:
        return _doc_duoi_ty(du)
    kq = doc_so_vn(ty) + " tỷ"
    return kq + (" " + _doc_duoi_ty(du, co_truoc=True) if du else "")


def so_nguyen(v):
    """'1.000.000.000', '1,000,000 đồng', 5300000 -> int (không đọc được -> None)."""
    if isinstance(v, (int, float)):
        return int(v)
    t = re.sub(r"[^\d]", "", str(v or ""))
    return int(t) if t else None


def tien_bang_so_chu(v):
    """'1.000.000.000 đồng (Một tỷ đồng)' — thiếu số -> chuỗi gốc người dùng nhập."""
    n = so_nguyen(v)
    if n is None:
        return str(v or "").strip()
    bang_chu = doc_so_vn(n)
    return f"{n:,}".replace(",", ".") + f" đồng (bằng chữ: {bang_chu[:1].upper() + bang_chu[1:]} đồng)"


# ============================================================ ĐIỀN Ô "……" TRONG BIỂU MẪU
from docx.text.paragraph import Paragraph
from docx.table import Table

_CHAM = r"(?:…|\.{2,})[…\.]*"
_NGAY3 = r"[…\.]+\s*/\s*[…\.]+\s*/\s*[…\.]+"


def _van(p):
    return "".join(r.text for r in p.runs)


def _thay_khoang(p, a, b, moi):
    """Thay [a,b) của văn bản đoạn bằng `moi`, giữ định dạng của run đầu tiên bị chạm (a==b: chèn)."""
    runs = p.runs
    pos = 0
    da = False
    if a == b:
        for r in runs:
            t = r.text
            ra, rb = pos, pos + len(t)
            pos = rb
            if ra < a <= rb:
                r.text = t[:a - ra] + moi + t[a - ra:]
                return
        (runs[-1] if runs else p.add_run("")).text += moi
        return
    for r in runs:
        t = r.text
        ra, rb = pos, pos + len(t)
        pos = rb
        if rb <= a or ra >= b:
            continue
        s, e = max(a, ra) - ra, min(b, rb) - ra
        if not da:
            r.text = t[:s] + moi + t[e:]
            da = True
        else:
            r.text = t[:s] + t[e:]
    if not da:
        p.add_run(moi)


def dien_cham(p, nhan_re, gia_tri, mau=_CHAM):
    """Sau nhãn (regex) thay dãy dấu chấm bằng giá trị; không có dấu chấm thì nối vào cuối đoạn. True nếu có điền."""
    gia_tri = str(gia_tri or "").strip()
    if not gia_tri:
        return False
    text = _van(p)
    m = re.search(nhan_re, text)
    if not m:
        return False
    k = re.match(r"(?:\s*\([^)]{0,90}\))*\s*[:：]?\s*", text[m.end():])      # bỏ qua chú thích "(ghi bằng chữ in hoa)", "(nếu có)" sau nhãn
    a = m.end() + k.end()
    cm = re.match(mau, text[a:])
    if cm:
        _thay_khoang(p, a, a + cm.end(), gia_tri)
    else:
        e = len(text.rstrip())
        _thay_khoang(p, e, e, ("" if text.rstrip().endswith(":") else "") + " " + gia_tri)
    return True


def _ngay_dd_mm_yyyy(v):
    t = str(v or "").strip()
    m = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$", t)
    if m:
        return f"{int(m.group(3)):02d}/{int(m.group(2)):02d}/{m.group(1)}"
    m = re.match(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})$", t)
    return f"{int(m.group(1)):02d}/{int(m.group(2)):02d}/{m.group(3)}" if m else t


def _cac_doan(phan_tu, goc):
    return [Paragraph(pe, goc) for pe in phan_tu.iter(qn("w:p"))]


class _Mau:
    """Một biểu mẫu đã cắt: thao tác theo các phần tử cấp cao nhất (đoạn/bảng) của thân văn bản."""

    def __init__(self, doc):
        self.doc = doc
        self.ch = [c for c in doc.element.body if c.tag != qn("w:sectPr")]

    def chi_so(self, mau_re, tu=0):
        for i in range(tu, len(self.ch)):
            c = self.ch[i]
            if c.tag == qn("w:p") and re.search(mau_re, _chu(c)):
                return i
        return None

    def doan(self, lo=0, hi=None):
        kq = []
        for c in self.ch[lo:hi]:
            kq += _cac_doan(c, self.doc._body)
        return kq

    def tim(self, nhan_re, lo=0, hi=None):
        for p in self.doan(lo, hi):
            if re.search(nhan_re, _van(p)):
                return p
        return None

    def dien(self, nhan_re, gia_tri, lo=0, hi=None, mau=_CHAM):
        p = self.tim(nhan_re, lo, hi)
        return bool(p is not None and dien_cham(p, nhan_re, gia_tri, mau))

    def xoa_phan(self, lo, hi):
        for c in self.ch[lo:hi]:
            if c.getparent() is not None:
                c.getparent().remove(c)

    def bang(self, i):
        return Table(self.ch[i], self.doc._body)


def _dat_o(cell, text):
    p = cell.paragraphs[0]
    if p.runs:
        p.runs[0].text = str(text)
        for r in p.runs[1:]:
            r.text = ""
    else:
        p.add_run(str(text))


def _dien_bang_nganh(tb, ds, cot):
    """tb: bảng có hàng tiêu đề + 1 hàng trống; ds: danh sách dict; cot: [khoá cho từng cột sau STT]."""
    mau_hang = tb.rows[1]._tr
    for i, n in enumerate(ds, 1):
        hang = copy.deepcopy(mau_hang)
        mau_hang.addprevious(hang)
        from docx.table import _Row
        r = _Row(hang, tb)
        _dat_o(r.cells[0], i)
        for j, khoa in enumerate(cot, 1):
            v = n.get(khoa, "")
            _dat_o(r.cells[j], "X" if khoa == "chinh" and v else ("" if khoa == "chinh" else v))
    mau_hang.getparent().remove(mau_hang)


def _dien_dau(m, dn, hi):
    """Phần đầu chung: tên/MST/cơ quan nhận + tên DN ở tiêu đề + ngày lập."""
    ten = (dn.get("ten") or "").strip().upper()
    if ten:
        for p in m.doan(0, 3):
            if _van(p).strip().split("\n")[0].strip() == "TÊN DOANH NGHIỆP":      # đoạn có thể kèm dòng "-------" sau dấu xuống dòng
                _thay_khoang(p, 0, len("TÊN DOANH NGHIỆP"), ten)
                break
    so = (dn.get("so_vb") or "").strip()
    if so:
        for p in m.doan(0, 4):
            if re.match(r"^Số:\s*" + _CHAM + r"\s*$", _van(p).strip()):
                _thay_khoang(p, 0, len(_van(p)), f"Số: {so}")
                break
    m.dien(r"Tên doanh nghiệp", ten, 0, hi)
    m.dien(r"Mã số doanh nghiệp/Mã số thuế", dn.get("ma_so"), 0, hi)
    m.dien(r"Kính gửi: \(Cơ quan đăng ký kinh doanh cấp tỉnh\)", dn.get("co_quan"), 0, hi)
    if dn.get("ngay_lap"):
        ngay = _ngay_dd_mm_yyyy(dn["ngay_lap"])
        mm = re.match(r"(\d{2})/(\d{2})/(\d{4})", ngay)
        if mm:
            for p in m.doan(0, 3):
                if re.search(r"ngày…", _van(p)) or re.search(r"…\s*,\s*ngày", _van(p)):
                    _thay_khoang(p, 0, len(_van(p)), f"{dn.get('dia_danh') or '……'}, ngày {int(mm.group(1))} tháng {int(mm.group(2))} năm {mm.group(3)}")
                    break


_MARKER_12 = [("A", r"^A\.\s*ĐĂNG KÝ THAY ĐỔI NỘI DUNG"), ("TEN", r"^ĐĂNG KÝ THAY ĐỔI TÊN DOANH NGHIỆP"),
              ("DIA_CHI", r"^ĐĂNG KÝ THAY ĐỔI ĐỊA CHỈ TRỤ SỞ"), ("THANH_VIEN", r"^ĐĂNG KÝ THAY ĐỔI THÀNH VIÊN"),
              ("VON", r"^ĐĂNG KÝ THAY ĐỔI VỐN ĐIỀU LỆ"), ("NGANH", r"^THÔNG BÁO THAY ĐỔI NGÀNH"),
              ("VON_DNTN", r"^ĐĂNG KÝ THAY ĐỔI VỐN ĐẦU TƯ"), ("UY_QUYEN", r"^THÔNG BÁO THAY ĐỔI NGƯỜI ĐẠI DIỆN THEO ỦY QUYỀN"),
              ("CO_DONG", r"^THÔNG BÁO THAY ĐỔI CỔ ĐÔNG"), ("THUE", r"^THÔNG BÁO THAY ĐỔI THÔNG TIN ĐĂNG KÝ THUẾ"),
              ("CSHHL", r"^THÔNG BÁO THAY ĐỔI THÔNG TIN VỀ CHỦ SỞ HỮU HƯỞNG LỢI"), ("B", r"^B\.\s*BỔ SUNG"),
              ("C", r"^C\.\s*ĐỀ NGHỊ HIỆU ĐÍNH"), ("KET", r"^Trường hợp hồ sơ đăng ký doanh nghiệp hợp lệ")]
_GIU_12 = {"ten": "TEN", "dia_chi": "DIA_CHI", "von": "VON", "nganh": "NGANH", "thue": "THUE", "cshhl": "CSHHL", "bo_sung": "B"}
# Thay đổi cần Quyết định/Nghị quyết của chủ sở hữu/HĐTV/ĐHĐCĐ (tự soạn). Chỉ bổ sung/cập nhật thông tin (mục B Mẫu 12) thì KHÔNG cần.
CAN_QUYET_DINH = {"ten", "dia_chi", "von", "nganh", "dai_dien", "chu_so_huu"}


def soan_mau12(du, chu_ky=None):
    """Mẫu số 12 (TT 121/2026) — Giấy đề nghị đăng ký thay đổi nội dung ĐKDN: chỉ giữ các mục được chọn, điền dữ liệu."""
    d = cat_mau(12)
    m = _Mau(d)
    loai = set(du.get("loai") or [])
    dn = du.get("dn") or {}
    mk = {}
    for ten, mau in _MARKER_12:
        i = m.chi_so(mau)
        if i is not None:
            mk[ten] = i
    thu_tu = sorted(mk.items(), key=lambda kv: kv[1])
    dau_a = mk["A"]
    cac = {t: (i, (thu_tu[k + 1][1] if k + 1 < len(thu_tu) else len(m.ch))) for k, (t, i) in enumerate(thu_tu)}
    # ---- điền (trước khi xoá, chỉ số còn nguyên)
    _dien_dau(m, dn, dau_a)
    if "ten" in loai and "TEN" in cac:
        t = du.get("ten") or {}
        lo, hi = cac["TEN"]
        for nhan, k in ((r"Tên doanh nghiệp viết bằng tiếng Việt sau khi thay đổi", "viet"),
                        (r"Tên doanh nghiệp viết bằng tiếng nước ngoài sau khi thay đổi", "nuoc_ngoai"),
                        (r"Tên doanh nghiệp viết tắt sau khi thay đổi", "viet_tat")):
            v = (t.get(k) or "").strip()
            p = m.tim(nhan, lo, hi)
            if v and p is not None and dien_cham(p, nhan, v.upper() if k == "viet" else v):
                nxt = p._p.getnext()                       # dòng chấm nối tiếp (chỉ có dấu chấm) -> bỏ
                if nxt is not None and nxt.tag == qn("w:p") and re.fullmatch(r"[…\.\s]*", _chu(nxt)):
                    nxt.getparent().remove(nxt)
    if "dia_chi" in loai and "DIA_CHI" in cac:
        a = du.get("dia_chi") or {}
        lo, hi = cac["DIA_CHI"]
        m.dien(r"Số nhà/phòng, ngách/hẻm, ngõ/kiệt, đường/phố/đại lộ, tổ/xóm/ấp/thôn", a.get("so_nha"), lo, hi)
        m.dien(r"Xã/Phường/Đặc khu", a.get("xa"), lo, hi)
        m.dien(r"Tỉnh/Thành phố trực thuộc trung ương", a.get("tinh"), lo, hi)
        m.dien(r"Điện thoại", a.get("dien_thoai"), lo, hi)
        m.dien(r"Số fax \(nếu có\)", a.get("fax"), lo, hi)
        m.dien(r"Thư điện tử \(nếu có\)", a.get("email"), lo, hi)
        m.dien(r"Website \(nếu có\)", a.get("website"), lo, hi)
        if a.get("doi_thue"):
            p = m.tim(r"Đồng thời thay đổi địa chỉ nhận thông báo thuế", lo, hi)
            if p is not None:
                for r in p.runs:
                    if "□" in r.text:
                        r.text = r.text.replace("□", "☒", 1)
                        break
    if "dia_chi" in loai and (du.get("dia_chi") or {}).get("doi_thue") and "THUE" in cac:
        a = du.get("dia_chi") or {}
        lo, hi = cac["THUE"]                       # đổi địa chỉ nhận thông báo thuế -> điền chỉ tiêu 3 của "Thông báo thay đổi thông tin đăng ký thuế"
        m.dien(r"Số nhà/phòng, ngách/hẻm, ngõ/kiệt, đường/phố/đại lộ, tổ/xóm/ấp/thôn", a.get("so_nha"), lo, hi)
        m.dien(r"Xã/Phường/Đặc khu", a.get("xa"), lo, hi)
        m.dien(r"Tỉnh/Thành phố trực thuộc trung ương", a.get("tinh"), lo, hi)
        m.dien(r"Điện thoại \(nếu có\)", a.get("dien_thoai"), lo, hi)
        m.dien(r"Số fax \(nếu có\)", a.get("fax"), lo, hi)
        m.dien(r"Thư điện tử \(nếu có\)", a.get("email"), lo, hi)
    if True:                                       # "Đề nghị cấp Giấy xác nhận thay đổi nội dung ĐKDN": luôn tick
        p = m.tim(r"Đề nghị Quý Cơ quan cấp Giấy xác nhận thay đổi nội dung đăng ký doanh nghiệp")
        if p is not None:
            for r in p.runs:
                if "□" in r.text:
                    r.text = r.text.replace("□", "☒", 1)
                    break
    if "bo_sung" in loai and "B" in cac:
        lo, hi = cac["B"]
        dong = [x.strip() for x in re.split(r"[\n;]+", str((du.get("bo_sung") or {}).get("noi_dung") or "")) if x.strip()]
        trong = [c for c in m.ch[lo:hi] if c.tag == qn("w:p") and re.fullmatch(r"[…\.\s]+", _chu(c) or "")]
        for c, t in zip(trong, dong):
            ps = Paragraph(c, m.doc._body)
            _thay_khoang(ps, 0, len(_van(ps)), t) if ps.runs else ps.add_run(t)
    if "von" in loai and "VON" in cac:
        v = du.get("von") or {}
        lo, hi = cac["VON"]
        m.dien(r"Vốn điều lệ đã đăng ký", tien_bang_so_chu(v.get("cu")) if v.get("cu") else "", lo, hi)
        m.dien(r"Vốn điều lệ sau khi thay đổi", tien_bang_so_chu(v.get("moi")) if v.get("moi") else "", lo, hi)
        m.dien(r"Thời điểm thay đổi vốn", v.get("thoi_diem"), lo, hi)
        m.dien(r"Hình thức tăng, giảm vốn", v.get("hinh_thuc"), lo, hi)
    # ---- bảng ngành nghề: điền, và bỏ tiểu mục không có dữ liệu
    nganh = du.get("nganh") or {}
    if "nganh" in loai and "NGANH" in cac:
        lo, hi = cac["NGANH"]
        cac_tm = [("them", r"^1\.\s*Bổ sung ngành", ["ten", "ma", "chinh"]), ("bo", r"^2\.\s*Bỏ ngành", ["ten", "ma", "ghi_chu"]),
                  ("sua", r"^3\.\s*Sửa đổi chi tiết ngành", ["ten", "ma", "chinh"])]
        vi_tri = []
        for k, mau, cot in cac_tm:
            i = m.chi_so(mau, lo)
            if i is not None and i < hi:
                vi_tri.append((k, i, cot))
        ket_thuc_tm = m.chi_so(r"^Doanh nghiệp cam kết đáp ứng điều kiện tiếp cận thị trường", lo)
        xoa = []
        for n, (k, i, cot) in enumerate(vi_tri):
            j = vi_tri[n + 1][1] if n + 1 < len(vi_tri) else ket_thuc_tm
            ds = [x for x in (nganh.get(k) or []) if (x.get("ten") or x.get("ma"))]
            if ds and i + 1 < len(m.ch) and m.ch[i + 1].tag == qn("w:tbl"):
                _dien_bang_nganh(m.bang(i + 1), ds, cot)
            elif not ds:
                xoa.append((i, j))
        for i, j in sorted(xoa, reverse=True):
            m.xoa_phan(i, j)
    # ---- bỏ các phần KHÔNG dùng
    giu = {_GIU_12[k] for k in loai if k in _GIU_12}
    if "dia_chi" in loai and (du.get("dia_chi") or {}).get("doi_thue"):
        giu.add("THUE")
    con_lai = {"A", "KET"} | giu
    ck = m.chi_so(r"^[□☒]?\s*Đề nghị Quý Cơ quan cấp Giấy xác nhận thay đổi nội dung")
    if ck is not None and "C" in cac and cac["C"][0] < ck < cac["C"][1]:
        cac["KET"] = (ck, cac["KET"][1])
        cac["C"] = (cac["C"][0], ck)               # phần C (hiệu đính) bỏ, nhưng GIỮ dòng "Đề nghị cấp Giấy xác nhận..." như mẫu hồ sơ thực tế
    for ten, (lo, hi) in sorted(cac.items(), key=lambda kv: -kv[1][0]):
        if ten not in con_lai:
            m.xoa_phan(lo, hi)
    # tách/sáp nhập (ở phần A): bỏ từ "Doanh nghiệp đăng ký thay đổi trên cơ sở" đến trước dòng "- Doanh nghiệp có Giấy chứng nhận quyền sử dụng đất"
    s = m.chi_so(r"^Doanh nghiệp đăng ký thay đổi trên cơ sở")
    e = m.chi_so(r"^- Doanh nghiệp có Giấy chứng nhận quyền sử dụng đất")
    if s is not None and e is not None and s < e:
        m.xoa_phan(s, e)
    # vốn điều lệ: bỏ phần không áp dụng theo loại hình
    lh = (dn.get("loai_hinh") or "").lower()
    if "von" in loai and "VON" in cac:
        cp, vg, cam = (m.chi_so(r"^Thông tin về cổ phần"), m.chi_so(r"^2\.\s*Đăng ký thay đổi phần vốn góp"),
                       m.chi_so(r"^Doanh nghiệp cam kết bảo đảm thanh toán"))
        if cp is not None and vg is not None and cam is not None and ("cổ phần" not in lh):
            m.xoa_phan(cp, vg)                        # không phải công ty cổ phần -> bỏ phần cổ phần
        if vg is not None and cam is not None and ("một thành viên" in lh or "cổ phần" in lh):
            m.xoa_phan(vg, cam)                       # CT TNHH 1TV / cổ phần: không có "phần vốn góp của thành viên"
    # chữ ký: ghi sẵn họ tên người đại diện theo pháp luật (người đại diện mới nếu có thay đổi) — phần mềm KHÔNG ký thay
    ten_ky = ((du.get("dai_dien") or [{}])[0].get("ho_ten") if "dai_dien" in loai else "") or (du.get("hien_tai") or {}).get("dd_ho_ten") or ""
    if ten_ky.strip():
        for tb in d.tables:
            if any("NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT/" in c.text for r in tb.rows for c in r.cells):
                c = [c for c in tb.rows[-1].cells if "NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT/" in c.text][0]
                # chữ ký trong Kho chữ ký chỉ là của người đại diện HIỆN TẠI (đã được người đó đồng ý) — không gắn khi ký là người đại diện mới
                for _ in range(3):
                    c.add_paragraph()
                pk = c.add_paragraph()
                pk.alignment = WD_ALIGN_PARAGRAPH.CENTER
                pk.add_run(ten_ky.strip().upper()).bold = True
                _gan_chu_ky(pk, (chu_ky or {}).get("giam_doc") if "dai_dien" not in loai else None)
                _giu_mot_trang(tb)
                break
    return d


def soan_mau13(du):
    """Mẫu số 13 (TT 68/2025) — Giấy đề nghị đăng ký thay đổi người đại diện theo pháp luật."""
    d = cat_mau(13)
    m = _Mau(d)
    dn = du.get("dn") or {}
    ds = du.get("dai_dien") or []
    bd = m.chi_so(r"^Người đại diện theo pháp luật sau khi thay đổi")
    _dien_dau(m, dn, bd if bd is not None else len(m.ch))
    if ds and bd is not None:
        n = ds[0]
        m.dien(r"Họ, chữ đệm và tên", (n.get("ho_ten") or "").upper(), bd)
        p = m.tim(r"Ngày, tháng, năm sinh", bd)
        if p is not None and n.get("ngay_sinh"):
            dien_cham(p, r"Ngày, tháng, năm sinh", _ngay_dd_mm_yyyy(n["ngay_sinh"]), _NGAY3)
        m.dien(r"Giới tính", n.get("gioi_tinh"), bd)
        m.dien(r"Số định danh cá nhân", n.get("cccd"), bd)
        m.dien(r"Chức danh", n.get("chuc_danh"), bd)
        m.dien(r"Số nhà/phòng, ngách/hẻm, ngõ/kiệt, đường/phố/đại lộ, tổ/xóm/ấp/thôn", n.get("so_nha"), bd)
        m.dien(r"Xã/Phường/Đặc khu", n.get("xa"), bd)
        m.dien(r"Tỉnh/Thành phố trực thuộc trung ương", n.get("tinh"), bd)
        m.dien(r"Quốc gia", n.get("quoc_gia") or "Việt Nam", bd)
        m.dien(r"Điện thoại \(nếu có\)", n.get("dien_thoai"), bd)
        m.dien(r"Thư điện tử \(nếu có\)", n.get("email"), bd)
    return d


def soan_mau15(du):
    """Mẫu số 15 (TT 68/2025) — Giấy đề nghị đăng ký thay đổi chủ sở hữu công ty TNHH một thành viên (chủ sở hữu MỚI là cá nhân)."""
    d = cat_mau(15)
    m = _Mau(d)
    dn = du.get("dn") or {}
    n = du.get("chu_so_huu_moi") or {}
    bd = m.chi_so(r"^1\.\s*Đối với chủ sở hữu là cá nhân")
    ket = m.chi_so(r"^2\.\s*Đối với chủ sở hữu là tổ chức")
    _dien_dau(m, dn, bd if bd is not None else len(m.ch))
    if bd is not None and ket is not None:
        hi = ket
        m.dien(r"Họ, chữ đệm và tên chủ sở hữu", (n.get("ho_ten") or "").upper(), bd, hi)
        p = m.tim(r"Ngày, tháng, năm sinh", bd, hi)
        if p is not None and n.get("ngay_sinh"):
            dien_cham(p, r"Ngày, tháng, năm sinh", _ngay_dd_mm_yyyy(n["ngay_sinh"]), _NGAY3)
        m.dien(r"Giới tính", n.get("gioi_tinh"), bd, hi)
        m.dien(r"Số định danh cá nhân", n.get("cccd"), bd, hi)
        m.dien(r"Số nhà/phòng, ngách/hẻm, ngõ/kiệt, đường/phố/đại lộ, tổ/xóm/ấp/thôn", n.get("so_nha"), bd, hi)
        m.dien(r"Xã/Phường/Đặc khu", n.get("xa"), bd, hi)
        m.dien(r"Tỉnh/Thành phố trực thuộc trung ương", n.get("tinh"), bd, hi)
        m.dien(r"Quốc gia", n.get("quoc_gia") or "Việt Nam", bd, hi)
        m.dien(r"Điện thoại \(nếu có\)", n.get("dien_thoai"), bd, hi)
        m.dien(r"Thư điện tử \(nếu có\)", n.get("email"), bd, hi)
        # chủ sở hữu mới là cá nhân: bỏ phần "2. Đối với chủ sở hữu là tổ chức" (đến trước dòng đề nghị công bố)
        cb = m.chi_so(r"^Trường hợp hồ sơ đăng ký doanh nghiệp hợp lệ", ket)
        if cb is not None:
            m.xoa_phan(ket, cb)
    return d



# ============================================================ VĂN BẢN DO PHẦN MỀM SOẠN (Quyết định của chủ sở hữu, Giấy ủy quyền)
# Nội dung theo bộ hồ sơ mẫu người dùng cung cấp; thông tin công ty lấy từ dữ liệu công ty đang làm. Không có chữ ký/con dấu.


def _ngay_chu(dn):
    """'TP.HCM, ngày 6 tháng 8 năm 2026' (ngày lập; nếu trống thì lấy ngày hiện tại)."""
    import datetime
    mm = re.match(r"(\d{2})/(\d{2})/(\d{4})", _ngay_dd_mm_yyyy(dn.get("ngay_lap") or ""))
    if mm:
        d_, m_, y_ = int(mm.group(1)), int(mm.group(2)), mm.group(3)
    else:
        t = datetime.date.today()
        d_, m_, y_ = t.day, t.month, str(t.year)
    return f"{(dn.get('dia_danh') or '').strip() or '……'}, ngày {d_} tháng {m_} năm {y_}"


def _gan_chu_ky(p, anh_uri, rong_cm=4.4, cao_cm=2.2):
    """Gắn ảnh chữ ký dạng NỔI "phía sau chữ" (behind text), canh giữa theo cột/ô và đè lên khoảng trống phía trên họ tên (đoạn `p`).
    Ảnh được co/giãn vừa khung rong_cm x cao_cm, giữ tỷ lệ. Chỉ gọi với chữ ký ĐÃ được người đó xác nhận đồng ý. True nếu đã gắn."""
    if not anh_uri or "," not in str(anh_uri):
        return False
    try:
        import base64
        from PIL import Image
        from docx.oxml import parse_xml
        from docx.oxml.ns import nsdecls
        from docx.shared import Emu
        raw = base64.b64decode(str(anh_uri).split(",", 1)[1])
        w, h = Image.open(io.BytesIO(raw)).size
        ti = min(rong_cm / w, cao_cm / h)
        cx, cy = int(w * ti * 360000), int(h * ti * 360000)
        run = p.add_run()
        run.add_picture(io.BytesIO(raw), width=Emu(cx), height=Emu(cy))
        inline = run._r.xpath(".//wp:inline")[0]
        ns = {"wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"}
        lech = -(cy - int(0.8 * 360000))
        anchor = parse_xml(
            f'<wp:anchor {nsdecls("wp")} distT="0" distB="0" distL="0" distR="0" simplePos="0" relativeHeight="251658240" behindDoc="1" '
            f'locked="0" layoutInCell="1" allowOverlap="1"><wp:simplePos x="0" y="0"/>'
            f'<wp:positionH relativeFrom="column"><wp:align>center</wp:align></wp:positionH>'
            f'<wp:positionV relativeFrom="paragraph"><wp:posOffset>{lech}</wp:posOffset></wp:positionV></wp:anchor>')
        anchor.append(inline.find("wp:extent", ns))
        anchor.append(parse_xml(f'<wp:effectExtent {nsdecls("wp")} l="0" t="0" r="0" b="0"/>'))
        anchor.append(parse_xml(f'<wp:wrapNone {nsdecls("wp")}/>'))
        for ten in ("docPr", "cNvGraphicFramePr"):
            anchor.append(inline.find("wp:" + ten, ns))
        anchor.append(inline.find("{http://schemas.openxmlformats.org/drawingml/2006/main}graphic"))
        dr = inline.getparent()
        dr.remove(inline)
        dr.append(anchor)
        return True
    except Exception:
        return False


def _giu_mot_trang(tb, so_doan_truoc=3):
    """Khối chữ ký không bị tách trang: hàng bảng không được cắt đôi, các đoạn trong khối + vài đoạn ngay trước đó "giữ cùng trang tiếp theo"."""
    from docx.oxml import OxmlElement
    from docx.text.paragraph import Paragraph as _P
    for r in tb.rows:
        r._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        for c in r.cells:
            for pp in c.paragraphs:
                pp.paragraph_format.keep_with_next = True
    e = tb._tbl.getprevious()
    n = 0
    while e is not None and n < so_doan_truoc:
        if e.tag == qn("w:p"):
            _P(e, tb._parent).paragraph_format.keep_with_next = True
            n += 1
        e = e.getprevious()


def _van_ban_moi():
    d = docx.Document()
    st = d.styles["Normal"]
    st.font.name = "Times New Roman"
    st.font.size = Pt(13)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    for sec in d.sections:
        sec.top_margin = sec.bottom_margin = Cm(2)
        sec.left_margin, sec.right_margin = Cm(3), Cm(2)
    return d


def _doan(d, text="", dam=False, nghieng=False, can="", gach=False, thut=False, sau=6):
    p = d.add_paragraph()
    if text:
        r = p.add_run(text)
        r.bold, r.italic, r.underline = dam, nghieng, gach
    if can == "giua":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif can == "phai":
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    elif can == "deu":
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if thut:
        p.paragraph_format.first_line_indent = Cm(1)
    p.paragraph_format.space_after = Pt(sau)
    return p


def _bang_quoc_hieu(d, dn, so_vb=""):
    ten = (dn.get("ten") or "").strip().upper() or "TÊN DOANH NGHIỆP"
    tb = d.add_table(rows=1, cols=2)
    tb.autofit = True
    a, b = tb.rows[0].cells
    pa = a.paragraphs[0]
    pa.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pa.add_run(ten).bold = True
    pa2 = a.add_paragraph()
    pa2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pa2.add_run(f"Số: {so_vb or '……'}")
    pb = b.paragraphs[0]
    pb.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pb.add_run("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM").bold = True
    pb2 = b.add_paragraph()
    pb2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = pb2.add_run("Độc lập - Tự do - Hạnh phúc")
    r.bold = True
    r.underline = True
    pb3 = b.add_paragraph()
    pb3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pb3.add_run(_ngay_chu(dn)).italic = True
    d.add_paragraph()


def _tien_dong(v):
    n = so_nguyen(v)
    return None if n is None else f"{n:,}".replace(",", ".") + " đồng (" + doc_so_vn(n) + " đồng)"


def _chu_the_quyet_dinh(loai_hinh):
    lh = (loai_hinh or "").lower()
    if "một thành viên" in lh:
        return "CHỦ SỞ HỮU", "QUYẾT ĐỊNH", "Chủ sở hữu"
    if "cổ phần" in lh:
        return "ĐẠI HỘI ĐỒNG CỔ ĐÔNG", "NGHỊ QUYẾT", "Đại hội đồng cổ đông"
    if "hai thành viên" in lh or "trách nhiệm hữu hạn" in lh:
        return "HỘI ĐỒNG THÀNH VIÊN", "NGHỊ QUYẾT", "Hội đồng thành viên"
    return "CHỦ SỞ HỮU", "QUYẾT ĐỊNH", "Chủ sở hữu"


def soan_quyet_dinh(du, chu_ky=None):
    """Quyết định (chủ sở hữu công ty TNHH một thành viên) / Nghị quyết (HĐTV, ĐHĐCĐ) về việc thay đổi nội dung đăng ký doanh nghiệp."""
    dn, ht = du.get("dn") or {}, du.get("hien_tai") or {}
    loai = set(du.get("loai") or [])
    chu, loai_vb, ten_co = _chu_the_quyet_dinh(dn.get("loai_hinh"))
    ten = (dn.get("ten") or "").strip().upper() or "……"
    d = _van_ban_moi()
    _bang_quoc_hieu(d, dn, dn.get("so_vb"))
    _doan(d, loai_vb, dam=True, can="giua", sau=0)
    _doan(d, "Về việc thay đổi nội dung đăng ký doanh nghiệp", dam=True, can="giua", sau=0)
    _doan(d, chu, dam=True, can="giua")
    _doan(d, f"- Căn cứ Điều lệ {ten} đã được thông qua ngày {ht.get('ngay_dieu_le') or '……'}.", can="deu", thut=True)
    _doan(d, loai_vb, dam=True, can="giua", sau=10)
    _doan(d, "Điều 1: ", dam=True, gach=True, sau=4)
    muc = []
    if "ten" in loai:
        t = du.get("ten") or {}
        muc.append(f"Thay đổi tên công ty từ {ten} thành {(t.get('viet') or '').upper() or '……'}"
                   + (f"; tên viết bằng tiếng nước ngoài: {t['nuoc_ngoai']}" if t.get("nuoc_ngoai") else "")
                   + (f"; tên viết tắt: {t['viet_tat']}" if t.get("viet_tat") else "") + ".")
    if "dia_chi" in loai:
        a = du.get("dia_chi") or {}
        moi = _dia_chi_day_du(a.get("so_nha"), a.get("xa"), a.get("tinh")) or "……"
        muc.append(f"Thay đổi địa chỉ trụ sở chính công ty từ {ht.get('dia_chi') or '……'} đến địa chỉ {moi}.")
    if "von" in loai:
        v = du.get("von") or {}
        muc.append(f"Thay đổi vốn điều lệ công ty từ {_tien_dong(v.get('cu')) or '……'} thành {_tien_dong(v.get('moi')) or '……'}"
                   + (f" ({v['hinh_thuc']})" if v.get("hinh_thuc") else "") + (f", thời điểm thay đổi: {v['thoi_diem']}" if v.get("thoi_diem") else "") + ".")
    if "nganh" in loai:
        ng = du.get("nganh") or {}
        for k, nhan in (("them", "Bổ sung"), ("bo", "Bỏ"), ("sua", "Sửa đổi chi tiết")):
            ds = [x for x in (ng.get(k) or []) if (x.get("ten") or x.get("ma"))]
            if ds:
                muc.append(f"{nhan} ngành, nghề kinh doanh: " + "; ".join(f"{x.get('ten') or ''} (mã ngành {x.get('ma') or '……'})" for x in ds) + ".")
    if "dai_dien" in loai:
        n = (du.get("dai_dien") or [{}])[0]
        muc.append(f"Thay đổi người đại diện theo pháp luật của công ty từ Ông/Bà {(ht.get('dd_ho_ten') or '……')} sang Ông/Bà "
                   f"{(n.get('ho_ten') or '').upper() or '……'}, chức danh {n.get('chuc_danh') or '……'}, số định danh cá nhân {n.get('cccd') or '……'}.")
    if "chu_so_huu" in loai:
        n = du.get("chu_so_huu_moi") or {}
        muc.append(f"Thay đổi chủ sở hữu công ty: chủ sở hữu mới là Ông/Bà {(n.get('ho_ten') or '').upper() or '……'}, số định danh cá nhân {n.get('cccd') or '……'}.")
    for i, t in enumerate(muc, 1):
        p = _doan(d, f"{i}. {t}", can="deu")
        p.paragraph_format.left_indent = Cm(0.8)
    dd = (ht.get("dd_ho_ten") or "").strip()
    if "dai_dien" in loai and (du.get("dai_dien") or [{}])[0].get("ho_ten"):
        dd = (du["dai_dien"][0].get("ho_ten") or "").strip()
    _doan(d, f"Điều 2: ", dam=True, gach=True, sau=10).add_run(f"Giao cho Ông/Bà {dd.upper() or '……'} (người đại diện theo pháp luật) tiến hành các thủ tục cần thiết theo quy định của pháp luật.")
    _doan(d, "Điều 3: ", dam=True, gach=True, sau=10).add_run(f"Người đại diện theo pháp luật của công ty, {ten_co.lower()} công ty có trách nhiệm thi hành {loai_vb.capitalize()} này.")
    _doan(d, "Điều 4: ", dam=True, gach=True, sau=10).add_run(f"{loai_vb.capitalize()} này có hiệu lực kể từ ngày ký.")
    tb = d.add_table(rows=1, cols=2)
    a, b = tb.rows[0].cells
    a.paragraphs[0].add_run("Nơi nhận:").bold = True
    a.paragraphs[0].runs[0].italic = True
    for t in (f"- Như Điều 3 (để thực hiện);", "- Cơ quan đăng ký kinh doanh (để đăng ký);", "- Lưu."):
        a.add_paragraph(t)
    pb = b.paragraphs[0]
    pb.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pb.add_run(chu).bold = True
    pb2 = b.add_paragraph()
    pb2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pb2.add_run("(Ký, ghi rõ họ tên)").italic = True
    if (ht.get("chu_so_huu") or "").strip():
        for _ in range(3):
            b.add_paragraph()
        pk = b.add_paragraph()
        pk.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pk.add_run(ht["chu_so_huu"].strip().upper()).bold = True
        _gan_chu_ky(pk, (chu_ky or {}).get("chu_so_huu"))
    _giu_mot_trang(tb, 2)
    return d


def soan_giay_uy_quyen(du, chu_ky=None):
    """Giấy ủy quyền nộp hồ sơ và nhận kết quả đăng ký doanh nghiệp (theo mẫu người dùng cung cấp)."""
    dn, ht, uq = du.get("dn") or {}, du.get("hien_tai") or {}, du.get("uy_quyen") or {}
    ten = (dn.get("ten") or "").strip().upper() or "……"
    co_quan = (dn.get("co_quan") or "").strip() or "cơ quan đăng ký kinh doanh"
    d = _van_ban_moi()
    _doan(d, "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", dam=True, can="giua", sau=2)
    _doan(d, "Độc lập - Tự do - Hạnh phúc", dam=True, can="giua", sau=2)
    _doan(d, "----0o0----", dam=True, can="giua", sau=8)
    _doan(d, "GIẤY ỦY QUYỀN", dam=True, can="giua", sau=10)
    _doan(d, "BÊN ỦY QUYỀN (BÊN A):", dam=True)
    _doan(d, f"Ông (Bà): {(ht.get('dd_ho_ten') or '').upper() or '……'}")
    _doan(d, f"Chức danh: {ht.get('dd_chuc_danh') or '……'}")
    p = _doan(d, "Là người đại diện theo pháp luật của ", sau=6)
    p.add_run(ten).bold = True
    _doan(d, f"Địa chỉ trụ sở chính: {ht.get('dia_chi') or '……'}")
    _doan(d, f"Giấy chứng nhận đăng ký doanh nghiệp số: {dn.get('ma_so') or '……'} do {ht.get('noi_cap_gcn') or '……'} cấp ngày {ht.get('ngay_cap_gcn') or '……'}")
    _doan(d, "BÊN NHẬN ỦY QUYỀN (BÊN B):", dam=True)
    _doan(d, f"Ông (Bà): {(uq.get('ho_ten') or '').upper() or '……'}")
    _doan(d, f"Sinh ngày: {_ngay_dd_mm_yyyy(uq.get('ngay_sinh')) or '……'} – Dân tộc: {uq.get('dan_toc') or '……'} – Quốc tịch: {uq.get('quoc_tich') or '……'}")
    _doan(d, f"Số chứng thực: {uq.get('so_giay_to') or '……'}, ngày cấp: {_ngay_dd_mm_yyyy(uq.get('ngay_cap')) or '……'}, nơi cấp: {uq.get('noi_cap') or '……'}")
    _doan(d, f"Chỗ ở hiện tại: {uq.get('cho_o') or '……'}")
    _doan(d, "ĐIỀU 1: NỘI DUNG VÀ PHẠM VI ỦY QUYỀN", dam=True)
    _doan(d, "Bên A ủy quyền cho bên B thực hiện các công việc sau đây:")
    _doan(d, f"-   Nộp hồ sơ và nhận kết quả đăng ký doanh nghiệp tại {co_quan}.", can="deu")
    _doan(d, "-   Bên B có thể ủy quyền lại, thuê hoặc nhờ đơn vị khác, đơn vị Bưu điện thực hiện việc nộp và nhận kết quả đăng ký doanh nghiệp.", can="deu")
    _doan(d, "ĐIỀU 2: THỜI HẠN ỦY QUYỀN", dam=True)
    _doan(d, f"Ủy quyền này có hiệu lực kể từ ngày ký cho đến khi ông/bà: {(uq.get('ho_ten') or '').upper() or '……'} hoàn thành công việc của công ty tại "
             f"{uq.get('cong_viec_tai') or co_quan}.", can="deu")
    _doan(d, "ĐIỀU 3: NGHĨA VỤ CỦA CÁC BÊN", dam=True)
    _doan(d, "Bên A và bên B chịu trách nhiệm trước pháp luật về những lời cam đoan sau đây:")
    _doan(d, "1. Bên B thực hiện công việc theo ủy quyền và báo cho Bên A về kết quả thực hiện công việc.", can="deu")
    _doan(d, "2. Việc giao kết hoàn toàn tự nguyện, không bị lừa dối hoặc ép buộc.", can="deu")
    _doan(d, "3. Thực hiện đúng và đầy đủ tất cả các thỏa thuận đã ghi trong Giấy ủy quyền này.", can="deu")
    _doan(d, "ĐIỀU 4: ĐIỀU KHOẢN CUỐI CÙNG", dam=True)
    _doan(d, "1. Hai bên công nhận đã hiểu rõ quyền, nghĩa vụ và lợi ích hợp pháp của mình, ý nghĩa và hậu quả pháp lý của việc giao kết Giấy ủy quyền này.", can="deu")
    _doan(d, "2. Hai bên đã tự đọc Giấy ủy quyền, đã hiểu và đồng ý tất cả các điều khoản ghi trong Giấy và ký vào Giấy ủy quyền này.", can="deu")
    _doan(d, "3. Giấy này có hiệu lực kể từ ngày hai bên ký./.", can="deu")
    _doan(d, _ngay_chu(dn).replace(", ngày", ", Ngày", 1), nghieng=False, can="phai", sau=10)
    tb = d.add_table(rows=1, cols=2)
    a, b = tb.rows[0].cells
    pa = a.paragraphs[0]
    pa.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pa.add_run("Bên được ủy quyền")
    for _ in range(4):
        a.add_paragraph()
    pa3 = a.add_paragraph()
    pa3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pa3.add_run((uq.get("ho_ten") or "").upper())
    _gan_chu_ky(pa3, (chu_ky or {}).get("ben_b"))
    pb = b.paragraphs[0]
    pb.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pb.add_run("Bên ủy quyền")
    for _ in range(4):
        b.add_paragraph()
    pb3 = b.add_paragraph()
    pb3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pb3.add_run((ht.get("dd_ho_ten") or "").upper())
    _gan_chu_ky(pb3, (chu_ky or {}).get("giam_doc"))
    _giu_mot_trang(tb, 3)
    return d


# ============================================================ MẪU RIÊNG CỦA NGƯỜI DÙNG: thay {{biến}}
CAC_BIEN = {
    "dn_ten": "Tên doanh nghiệp", "dn_ten_hoa": "Tên doanh nghiệp (IN HOA)", "dn_ma_so": "Mã số doanh nghiệp/MST",
    "dn_loai_hinh": "Loại hình doanh nghiệp", "dn_co_quan": "Cơ quan đăng ký kinh doanh nhận hồ sơ", "dn_dia_chi": "Địa chỉ trụ sở hiện tại",
    "ngay_lap": "Ngày lập (dd/mm/yyyy)", "ngay": "Ngày", "thang": "Tháng", "nam": "Năm", "dia_danh": "Địa danh",
    "ten_moi_viet": "Tên mới (tiếng Việt, IN HOA)", "ten_moi_nuoc_ngoai": "Tên mới (nước ngoài)", "ten_moi_viet_tat": "Tên mới (viết tắt)",
    "dia_chi_moi": "Địa chỉ trụ sở mới (đầy đủ)", "dia_chi_moi_so_nha": "Địa chỉ mới - số nhà/đường", "dia_chi_moi_xa": "Địa chỉ mới - xã/phường",
    "dia_chi_moi_tinh": "Địa chỉ mới - tỉnh/thành phố",
    "von_cu": "Vốn điều lệ cũ (số)", "von_cu_chu": "Vốn điều lệ cũ (bằng chữ)", "von_moi": "Vốn điều lệ mới (số)", "von_moi_chu": "Vốn điều lệ mới (bằng chữ)",
    "dd_ho_ten": "Người đại diện mới - họ tên", "dd_ho_ten_hoa": "Người đại diện mới - họ tên IN HOA", "dd_ngay_sinh": "Người đại diện mới - ngày sinh",
    "dd_gioi_tinh": "Người đại diện mới - giới tính", "dd_cccd": "Người đại diện mới - số định danh", "dd_chuc_danh": "Người đại diện mới - chức danh",
    "dd_dia_chi": "Người đại diện mới - địa chỉ liên lạc", "dd_dien_thoai": "Người đại diện mới - điện thoại", "dd_email": "Người đại diện mới - email",
    "cs_ho_ten": "Chủ sở hữu mới - họ tên", "cs_ho_ten_hoa": "Chủ sở hữu mới - họ tên IN HOA", "cs_ngay_sinh": "Chủ sở hữu mới - ngày sinh",
    "cs_gioi_tinh": "Chủ sở hữu mới - giới tính", "cs_cccd": "Chủ sở hữu mới - số định danh", "cs_dia_chi": "Chủ sở hữu mới - địa chỉ liên lạc",
}


def _dia_chi_day_du(so_nha, xa, tinh):
    return ", ".join(x.strip() for x in (so_nha, xa, tinh) if x and str(x).strip())


def bien_thay_the(du):
    dn, t, a, v = du.get("dn") or {}, du.get("ten") or {}, du.get("dia_chi") or {}, du.get("von") or {}
    dd = (du.get("dai_dien") or [{}])[0] if du.get("dai_dien") else {}
    cs = du.get("chu_so_huu_moi") or {}
    ngay = _ngay_dd_mm_yyyy(dn.get("ngay_lap") or "")
    mm = re.match(r"(\d{2})/(\d{2})/(\d{4})", ngay)
    b = {
        "dn_ten": dn.get("ten") or "", "dn_ten_hoa": (dn.get("ten") or "").upper(), "dn_ma_so": dn.get("ma_so") or "",
        "dn_loai_hinh": dn.get("loai_hinh") or "", "dn_co_quan": dn.get("co_quan") or "", "dn_dia_chi": dn.get("dia_chi") or "",
        "ngay_lap": ngay, "ngay": str(int(mm.group(1))) if mm else "", "thang": str(int(mm.group(2))) if mm else "", "nam": mm.group(3) if mm else "",
        "dia_danh": dn.get("dia_danh") or "",
        "ten_moi_viet": (t.get("viet") or "").upper(), "ten_moi_nuoc_ngoai": t.get("nuoc_ngoai") or "", "ten_moi_viet_tat": t.get("viet_tat") or "",
        "dia_chi_moi": _dia_chi_day_du(a.get("so_nha"), a.get("xa"), a.get("tinh")), "dia_chi_moi_so_nha": a.get("so_nha") or "",
        "dia_chi_moi_xa": a.get("xa") or "", "dia_chi_moi_tinh": a.get("tinh") or "",
        "von_cu": (f"{so_nguyen(v.get('cu')):,}".replace(",", ".") if so_nguyen(v.get("cu")) is not None else ""),
        "von_cu_chu": (doc_so_vn(so_nguyen(v.get("cu"))) + " đồng") if so_nguyen(v.get("cu")) is not None else "",
        "von_moi": (f"{so_nguyen(v.get('moi')):,}".replace(",", ".") if so_nguyen(v.get("moi")) is not None else ""),
        "von_moi_chu": (doc_so_vn(so_nguyen(v.get("moi"))) + " đồng") if so_nguyen(v.get("moi")) is not None else "",
        "dd_ho_ten": dd.get("ho_ten") or "", "dd_ho_ten_hoa": (dd.get("ho_ten") or "").upper(), "dd_ngay_sinh": _ngay_dd_mm_yyyy(dd.get("ngay_sinh")),
        "dd_gioi_tinh": dd.get("gioi_tinh") or "", "dd_cccd": dd.get("cccd") or "", "dd_chuc_danh": dd.get("chuc_danh") or "",
        "dd_dia_chi": _dia_chi_day_du(dd.get("so_nha"), dd.get("xa"), dd.get("tinh")), "dd_dien_thoai": dd.get("dien_thoai") or "", "dd_email": dd.get("email") or "",
        "cs_ho_ten": cs.get("ho_ten") or "", "cs_ho_ten_hoa": (cs.get("ho_ten") or "").upper(), "cs_ngay_sinh": _ngay_dd_mm_yyyy(cs.get("ngay_sinh")),
        "cs_gioi_tinh": cs.get("gioi_tinh") or "", "cs_cccd": cs.get("cccd") or "",
        "cs_dia_chi": _dia_chi_day_du(cs.get("so_nha"), cs.get("xa"), cs.get("tinh")),
    }
    return b


def dien_mau_rieng(noi_dung, bien):
    """Mẫu .docx do người dùng cung cấp: thay mọi {{tên_biến}} (biến không có dữ liệu giữ nguyên để người dùng thấy còn thiếu).
    Trả (bytes docx đã điền, danh sách biến đã gặp, danh sách biến chưa có dữ liệu)."""
    d = docx.Document(io.BytesIO(noi_dung))
    gap, thieu = set(), set()

    def xu_ly(p):
        t = _van(p)
        if "{{" not in t:
            return

        def sua(m):
            k = m.group(1).strip()
            gap.add(k)
            v = bien.get(k)
            if v in (None, ""):
                thieu.add(k)
                return m.group(0)
            return str(v)
        moi = re.sub(r"\{\{\s*([A-Za-z0-9_]+)\s*\}\}", sua, t)
        if moi != t:
            rs = p.runs
            if rs:
                rs[0].text = moi
                for r in rs[1:]:
                    r.text = ""
    for p in d.paragraphs:
        xu_ly(p)
    for tb in d.tables:
        for hang in tb.rows:
            for o in hang.cells:
                for p in o.paragraphs:
                    xu_ly(p)
    for sec in d.sections:
        for p in sec.header.paragraphs + sec.footer.paragraphs:
            xu_ly(p)
    return _luu_bytes(d), sorted(gap), sorted(thieu)


# ============================================================ GÓI HỒ SƠ
LOAI_THAY_DOI = {
    "cshhl": "Thông báo thay đổi thông tin về chủ sở hữu hưởng lợi",
    "ten": "Thay đổi tên doanh nghiệp", "dia_chi": "Thay đổi địa chỉ trụ sở chính", "von": "Thay đổi vốn điều lệ",
    "nganh": "Thay đổi ngành, nghề kinh doanh", "bo_sung": "Bổ sung, cập nhật thông tin đăng ký doanh nghiệp", "dai_dien": "Thay đổi người đại diện theo pháp luật (giám đốc)",
    "chu_so_huu": "Thay đổi chủ sở hữu công ty TNHH một thành viên (chủ sở hữu mới là cá nhân)",
}


def _kiem_thieu(du):
    """Các thông tin còn THIẾU cho từng loại thay đổi (để người dùng bổ sung; ô thiếu giữ dấu chấm trong biểu mẫu)."""
    loai = set(du.get("loai") or [])
    dn = du.get("dn") or {}
    th = []
    if not (dn.get("ten") or "").strip():
        th.append("Tên doanh nghiệp")
    if not (dn.get("ma_so") or "").strip():
        th.append("Mã số doanh nghiệp/MST")
    if not (dn.get("co_quan") or "").strip():
        th.append("Cơ quan đăng ký kinh doanh nhận hồ sơ (ô 'Kính gửi')")
    if "ten" in loai and not ((du.get("ten") or {}).get("viet") or "").strip():
        th.append("Tên doanh nghiệp mới (tiếng Việt)")
    if "dia_chi" in loai:
        a = du.get("dia_chi") or {}
        for k, ten in (("so_nha", "số nhà/đường"), ("xa", "xã/phường"), ("tinh", "tỉnh/thành phố")):
            if not (a.get(k) or "").strip():
                th.append(f"Địa chỉ trụ sở mới — {ten}")
    if "von" in loai:
        v = du.get("von") or {}
        if so_nguyen(v.get("cu")) is None:
            th.append("Vốn điều lệ đã đăng ký (số tiền)")
        if so_nguyen(v.get("moi")) is None:
            th.append("Vốn điều lệ sau khi thay đổi (số tiền)")
    if "nganh" in loai:
        ng = du.get("nganh") or {}
        if not any((ng.get(k) or []) for k in ("them", "bo", "sua")):
            th.append("Ngành, nghề kinh doanh bổ sung/bỏ/sửa đổi (chưa nhập ngành nào)")
    if "dai_dien" in loai:
        ds = du.get("dai_dien") or []
        n = ds[0] if ds else {}
        for k, ten in (("ho_ten", "họ tên"), ("ngay_sinh", "ngày sinh"), ("gioi_tinh", "giới tính"), ("cccd", "số định danh cá nhân"), ("chuc_danh", "chức danh")):
            if not (n.get(k) or "").strip():
                th.append(f"Người đại diện theo pháp luật mới — {ten}")
    if "chu_so_huu" in loai:
        n = du.get("chu_so_huu_moi") or {}
        for k, ten in (("ho_ten", "họ tên"), ("ngay_sinh", "ngày sinh"), ("gioi_tinh", "giới tính"), ("cccd", "số định danh cá nhân")):
            if not (n.get(k) or "").strip():
                th.append(f"Chủ sở hữu mới — {ten}")
    return th


def _danh_muc(du, ds_file, thieu, ghi_chu_nguon):
    """Danh mục hồ sơ (docx): các biểu mẫu đã soạn + giấy tờ thường kèm theo (GỢI Ý — cần kế toán/luật sư xác nhận)."""
    loai = set(du.get("loai") or [])
    d = docx.Document()
    d.add_heading("DANH MỤC HỒ SƠ ĐĂNG KÝ THAY ĐỔI NỘI DUNG ĐĂNG KÝ DOANH NGHIỆP (BẢN NHÁP)", level=1)
    dn = du.get("dn") or {}
    d.add_paragraph(f"Doanh nghiệp: {(dn.get('ten') or '').upper()} — MST/Mã số doanh nghiệp: {dn.get('ma_so') or '……'}")
    d.add_paragraph("Nội dung đề nghị thay đổi: " + "; ".join(LOAI_THAY_DOI[k] for k in LOAI_THAY_DOI if k in loai))
    d.add_heading("I. Biểu mẫu đã soạn (ký bởi người có thẩm quyền — phần mềm KHÔNG ký thay)", level=2)
    for ten, nguon in ds_file:
        d.add_paragraph(f"{ten} ({nguon})", style="List Bullet")
    d.add_heading("II. Giấy tờ thường kèm theo — gợi ý để kiểm tra", level=2)
    kem = []
    if loai & CAN_QUYET_DINH:
        kem.append("Quyết định/Nghị quyết của chủ sở hữu hoặc cấp có thẩm quyền của công ty về nội dung thay đổi (theo Điều lệ công ty) — phần mềm đã soạn bản nháp, cần ký.")
    kem.append("Văn bản ủy quyền (nếu người nộp hồ sơ không phải người đại diện theo pháp luật) kèm giấy tờ pháp lý của người được ủy quyền.")
    if "dai_dien" in loai:
        kem += ["Giấy tờ pháp lý (căn cước/hộ chiếu) của người đại diện theo pháp luật mới — chỉ cần khi không khai thác được qua số định danh cá nhân.",
                "Thông báo/biên bản chấm dứt chức danh của người đại diện cũ (nếu có).",
                "Danh sách chủ sở hữu hưởng lợi (Mẫu số 10 TT 121/2026) khi có thay đổi thông tin người quản lý doanh nghiệp — xem file kèm."]
    if "dia_chi" in loai:
        kem += ["Giấy tờ chứng minh quyền sử dụng hợp pháp địa chỉ trụ sở mới (nếu cơ quan đăng ký yêu cầu) — doanh nghiệp cam kết trong Giấy đề nghị.",
                "Thông báo thay đổi địa chỉ với cơ quan thuế/BHXH/các cơ quan quản lý liên quan (sau khi có Giấy xác nhận)."]
    if "von" in loai:
        kem += ["Quyết định của chủ sở hữu/Nghị quyết về tăng/giảm vốn điều lệ; chứng từ góp vốn (nếu tăng vốn); cam kết bảo đảm thanh toán nợ (nếu giảm vốn)."]
    if "nganh" in loai:
        kem += ["Giấy tờ chứng minh điều kiện kinh doanh đối với ngành, nghề có điều kiện (nếu có)."]
    if "chu_so_huu" in loai:
        kem += ["Hợp đồng chuyển nhượng/tặng cho/văn bản thừa kế vốn góp và chứng từ liên quan; giấy tờ pháp lý của chủ sở hữu mới."]
    for t in kem:
        d.add_paragraph(t, style="List Bullet")
    d.add_heading("III. Thông tin còn thiếu (ô giữ nguyên dấu chấm trong biểu mẫu)", level=2)
    if thieu:
        for t in thieu:
            d.add_paragraph(t, style="List Bullet")
    else:
        d.add_paragraph("Không thiếu thông tin bắt buộc đã được yêu cầu nhập.")
    d.add_heading("Lưu ý", level=2)
    d.add_paragraph("Đây là BẢN NHÁP do phần mềm lập từ biểu mẫu chính thức; nội dung và danh mục giấy tờ cần được kế toán/luật sư kiểm tra theo quy định hiện hành "
                    "(Nghị định 168/2025/NĐ-CP, Thông tư 68/2025/TT-BTC, Thông tư 121/2026/TT-BTC) trước khi nộp. Các ô chưa có dữ liệu được giữ nguyên dấu chấm — "
                    "phần mềm không tự điền thông tin chưa được cung cấp và không ký thay.")
    d.add_paragraph("Nguồn biểu mẫu: " + ghi_chu_nguon)
    return d


# ============================================================ XUẤT PDF (có viền như bản scan)
def _timn_trinh_chuyen_pdf():
    """('lo', đường dẫn soffice) | ('word', None) | None."""
    import shutil
    import sys as _sys
    for n in ("soffice", "libreoffice"):
        p = shutil.which(n)
        if p:
            return ("lo", p)
    for p in (r"C:\Program Files\LibreOffice\program\soffice.exe", r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"):
        if os.path.isfile(p):
            return ("lo", p)
    if _sys.platform == "win32":
        for mod in ("win32com.client", "comtypes.client"):
            try:
                __import__(mod)
                return ("word", mod)
            except Exception:
                continue
    return None


def docx_sang_pdf(noi_dung, trinh=None):
    """docx (bytes) -> pdf (bytes) bằng LibreOffice hoặc Microsoft Word có sẵn trên máy; ném RuntimeError nếu không chuyển được."""
    import tempfile
    import subprocess
    trinh = trinh or _timn_trinh_chuyen_pdf()
    if not trinh:
        raise RuntimeError("Máy chưa có Microsoft Word hoặc LibreOffice để đổi sang PDF")
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "vb.docx")
        with open(src, "wb") as f:
            f.write(noi_dung)
        out = os.path.join(td, "vb.pdf")
        if trinh[0] == "lo":
            r = subprocess.run([trinh[1], "--headless", "--norestore", f"-env:UserInstallation=file:///{td.replace(os.sep, '/')}/prof",
                                "--convert-to", "pdf", "--outdir", td, src], capture_output=True, text=True, timeout=180)
            if not os.path.isfile(out):
                raise RuntimeError("LibreOffice không chuyển được: " + (r.stderr or r.stdout or "")[-200:])
        else:
            if trinh[1] == "win32com.client":
                import win32com.client as wc
                w = wc.DispatchEx("Word.Application")
            else:
                import comtypes.client as cc
                w = cc.CreateObject("Word.Application")
            try:
                w.Visible = False
                d = w.Documents.Open(src, ReadOnly=True)
                d.SaveAs(out, FileFormat=17)          # 17 = wdFormatPDF
                d.Close(False)
            finally:
                w.Quit()
            if not os.path.isfile(out):
                raise RuntimeError("Word không xuất được PDF")
        with open(out, "rb") as f:
            return f.read()


def _bong_vien_scan(img):
    """Làm tối nhẹ MÉP trang như ảnh chụp/scan giấy (mép trên/phải đậm nhất, mép trái nhạt; giữa trang giữ nguyên trắng)."""
    import numpy as np
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    h, w = a.shape[:2]
    y = (np.arange(h, dtype=np.float32) / h)[:, None]
    x = (np.arange(w, dtype=np.float32) / w)[None, :]

    def duoi(d, rong, manh):
        return manh * np.exp(-d / rong)
    toi = (duoi(y, 0.012, 0.10) + duoi(1 - y, 0.010, 0.07) + duoi(1 - x, 0.012, 0.08) + duoi(x, 0.005, 0.03) + duoi(1 - x, 0.045, 0.03))
    a *= (1 - np.clip(toi, 0, 0.2))[..., None]
    from PIL import Image
    return Image.fromarray(np.clip(a, 0, 255).astype("uint8"))


def pdf_vien_scan(pdf_bytes, dpi=150):
    """PDF -> PDF dạng ảnh từng trang, mép trang tối nhẹ như file scan. Cần pymupdf (+ Pillow, numpy)."""
    try:
        import pymupdf
    except ImportError:
        import fitz as pymupdf
    from PIL import Image
    nguon = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    kq = pymupdf.open()
    for tr in nguon:
        r = tr.rect
        px = tr.get_pixmap(dpi=dpi, alpha=False)
        img = _bong_vien_scan(Image.frombytes("RGB", (px.width, px.height), px.samples))
        bio = io.BytesIO()
        img.save(bio, "JPEG", quality=92, subsampling=0)
        moi = kq.new_page(width=r.width, height=r.height)
        moi.insert_image(r, stream=bio.getvalue())
    return kq.tobytes(deflate=True)


def tao_ho_so(du, mau_rieng=None, chu_ky=None, xuat_pdf=False):
    """du: dữ liệu (xem soan_mau12/13/15); mau_rieng: [(tên, bytes docx)] mẫu riêng của người dùng.
    Trả (bytes zip, tên file zip, cảnh báo[])."""
    import datetime
    loai = set(du.get("loai") or [])
    if not loai and not du.get("tao_uy_quyen"):
        raise ValueError("Chưa chọn nội dung thay đổi nào")
    du = dict(du)
    du["dn"] = dn = dict(du.get("dn") or {})
    ht = dict(du.get("hien_tai") or {})
    ht["noi_cap_gcn"] = (ht.get("noi_cap_gcn") or "").strip() or "Phòng Đăng ký kinh doanh"
    ht["ngay_dieu_le"] = (ht.get("ngay_dieu_le") or "").strip() or (ht.get("ngay_cap_gcn") or "").strip()     # Điều lệ thông qua cùng ngày cấp GCN (mặc định)
    du["hien_tai"] = ht
    if not (dn.get("ngay_lap") or "").strip():
        dn["ngay_lap"] = datetime.date.today().strftime("%d/%m/%Y")        # mặc định: ngày hiện tại
    ma = re.sub(r"\D", "", dn.get("ma_so") or "") or "DN"
    nguon = danh_sach_mau()
    ten_nguon = lambda n: nguon[n][1]
    tep, ds_file = [], []

    def them(ten_file, d, nhan, n):
        tep.append((ten_file, _luu_bytes(d)))
        ds_file.append((nhan, ten_nguon(n)))
    if loai & {"ten", "dia_chi", "von", "nganh", "bo_sung", "cshhl"}:
        them(f"Mau12_Giay_de_nghi_thay_doi_noi_dung_DKDN_{ma}.docx", soan_mau12(du, chu_ky), "Mẫu số 12 — Giấy đề nghị đăng ký thay đổi nội dung ĐKDN", 12)
    if "cshhl" in loai and "dai_dien" not in loai:
        them(f"Mau10_Danh_sach_chu_so_huu_huong_loi_{ma}.docx", cat_mau(10), "Mẫu số 10 — Danh sách chủ sở hữu hưởng lợi (mẫu trống kèm theo, điền theo quy định)", 10)
    if "dai_dien" in loai:
        them(f"Mau13_Giay_de_nghi_thay_doi_nguoi_dai_dien_theo_phap_luat_{ma}.docx", soan_mau13(du), "Mẫu số 13 — Giấy đề nghị đăng ký thay đổi người đại diện theo pháp luật", 13)
        them(f"Mau10_Danh_sach_chu_so_huu_huong_loi_{ma}.docx", cat_mau(10), "Mẫu số 10 — Danh sách chủ sở hữu hưởng lợi (mẫu trống kèm theo, điền theo quy định)", 10)
    if "chu_so_huu" in loai:
        them(f"Mau15_Giay_de_nghi_thay_doi_chu_so_huu_{ma}.docx", soan_mau15(du), "Mẫu số 15 — Giấy đề nghị đăng ký thay đổi chủ sở hữu công ty TNHH một thành viên", 15)
    canh_bao = []
    if (loai & CAN_QUYET_DINH or du.get("tao_uy_quyen")) and not (ht.get("ngay_cap_gcn") or "").strip():
        canh_bao.append("Chưa có ngày cấp Giấy chứng nhận ĐKDN (mục 1b) — Quyết định (ngày thông qua Điều lệ) và Giấy ủy quyền để trống ngày.")
    if loai & CAN_QUYET_DINH:                    # tự soạn khi có thay đổi cần quyết định; chỉ bổ sung/cập nhật thì không
        _, loai_vb, ten_co = _chu_the_quyet_dinh(dn.get("loai_hinh"))
        tep.append((f"Quyet_dinh_{'cua_chu_so_huu' if loai_vb == 'QUYẾT ĐỊNH' else 'Nghi_quyet'}_{ma}.docx", _luu_bytes(soan_quyet_dinh(du, chu_ky))))
        ds_file.append((f"{loai_vb.capitalize()} của {ten_co} về việc thay đổi nội dung đăng ký doanh nghiệp (phần mềm soạn theo mẫu)", "mẫu do người dùng cung cấp"))
        if "một thành viên" not in (dn.get("loai_hinh") or "").lower():
            canh_bao.append(f"{loai_vb.capitalize()} soạn theo thẩm quyền của {ten_co} — hãy đối chiếu Điều lệ công ty (thể thức, tỷ lệ biểu quyết, biên bản họp nếu cần).")
    if du.get("tao_uy_quyen"):
        tep.append((f"Giay_uy_quyen_nop_ho_so_{ma}.docx", _luu_bytes(soan_giay_uy_quyen(du, chu_ky))))
        ds_file.append(("Giấy ủy quyền nộp hồ sơ và nhận kết quả đăng ký doanh nghiệp (phần mềm soạn theo mẫu)", "mẫu do người dùng cung cấp"))
        uq = du.get("uy_quyen") or {}
        for k, nhan in (("ho_ten", "họ tên"), ("ngay_sinh", "ngày sinh"), ("so_giay_to", "số chứng thực/CCCD"), ("ngay_cap", "ngày cấp"), ("noi_cap", "nơi cấp"), ("cho_o", "chỗ ở hiện tại")):
            if not (uq.get(k) or "").strip():
                canh_bao.append(f"Giấy ủy quyền — bên nhận ủy quyền thiếu {nhan}")
    bien = bien_thay_the(du)
    for ten, nd in (mau_rieng or []):
        try:
            b, _gap, thieu_bien = dien_mau_rieng(nd, bien)
            tep.append((f"MauRieng_{re.sub(r'[^0-9A-Za-zÀ-ỹ_.-]+', '_', ten)}", b))
            ds_file.append((f"Mẫu riêng: {ten}", "do người dùng cung cấp"))
            if thieu_bien:
                canh_bao.append(f"Mẫu riêng '{ten}': chưa có dữ liệu cho biến " + ", ".join("{{%s}}" % x for x in thieu_bien))
        except Exception as e:
            canh_bao.append(f"Mẫu riêng '{ten}': không đọc được ({type(e).__name__}: {str(e)[:100]})")
    thieu = _kiem_thieu(du)
    if thieu:
        canh_bao.append("Còn thiếu thông tin: " + "; ".join(thieu))
    if loai & {"ten", "dia_chi", "von", "nganh"} and (du.get("dn") or {}).get("loai_hinh") is None:
        canh_bao.append("Chưa biết loại hình doanh nghiệp: Mẫu 12 giữ nguyên các mục về cổ phần/phần vốn góp — hãy xoá mục không áp dụng.")
    if "dai_dien" in loai and len(du.get("dai_dien") or []) > 1:
        canh_bao.append("Mẫu 13 chỉ điền người đại diện đầu tiên; nếu công ty có nhiều người đại diện theo pháp luật, bổ sung các người còn lại trực tiếp vào biểu mẫu (Chú thích 2 của Mẫu 13).")
    ghi = "; ".join(sorted({f"{n[1]}" for n in nguon.values() if n[0] in ("TT121", "TT68")}))
    dm = _danh_muc(du, ds_file, thieu, "Phụ lục I Thông tư 121/2026/TT-BTC (mẫu cập nhật) và Phụ lục I Thông tư 68/2025/TT-BTC")
    tep.append(("00_Danh_muc_ho_so.docx", _luu_bytes(dm)))
    if chu_ky and any(chu_ky.values()):
        canh_bao.append("Đã gắn chữ ký từ Kho chữ ký (chỉ chữ ký đã được người đó xác nhận đồng ý). Người đại diện/chủ sở hữu vẫn cần kiểm tra nội dung trước khi nộp.")
    if xuat_pdf:
        try:
            trinh = _timn_trinh_chuyen_pdf()
            if not trinh:
                raise RuntimeError("Máy chưa có Microsoft Word hoặc LibreOffice để đổi sang PDF")
            pdfs, loi = [], []
            for ten, nd in tep:
                if ten.lower().endswith(".docx") and not ten.startswith(("00_", "MauRieng_")):
                    try:
                        pdfs.append(("PDF/" + ten[:-5] + "_scan.pdf", pdf_vien_scan(docx_sang_pdf(nd, trinh))))
                    except ImportError:
                        raise RuntimeError("Thiếu thư viện pymupdf (pip install pymupdf)")
                    except Exception as e:
                        loi.append(f"{ten}: {str(e)[:100]}")
            tep += pdfs
            if loi:
                canh_bao.append("Không xuất được PDF cho: " + "; ".join(loi))
        except Exception as e:
            canh_bao.append("Chưa xuất PDF được: " + str(e)[:160])
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as z:
        for ten, nd in tep:
            z.writestr(ten, nd)
    return bio.getvalue(), f"Ho_so_thay_doi_DKDN_{ma}.zip", canh_bao
