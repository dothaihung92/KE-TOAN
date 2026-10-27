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
from docx.shared import Pt, Cm, Emu

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


def _bo_dong_trong_thua(d):
    """Văn bản không có dòng trống thừa: bỏ đoạn trống ở CUỐI văn bản và gộp các đoạn trống liên tiếp (>= 2) thành 1. Chỉ đụng tới đoạn trống THẬT
    (không chữ, không ảnh, không ngắt trang/ngắt mục, không phải khoảng chừa chữ ký có chiều cao cố định). Không bỏ đoạn cuối nếu ngay trước nó là bảng
    (Word cần 1 đoạn sau bảng)."""
    try:
        body = d.element.body
        def trong(e):
            if e.tag != qn("w:p"):
                return False
            if "".join(e.itertext()).strip():
                return False
            for x in e.iter():
                if x.tag in (qn("w:drawing"), qn("w:pict"), qn("w:br"), qn("w:sectPr"), qn("w:object"), qn("w:fldChar")):
                    return False
            sp = e.find(".//" + qn("w:spacing"))
            return not (sp is not None and sp.get(qn("w:lineRule")) == "exact")
        con = [e for e in body if e.tag != qn("w:sectPr")]
        i = len(con) - 1
        while i > 0 and trong(con[i]) and con[i - 1].tag == qn("w:p"):          # đoạn trống ở cuối (sau 1 đoạn, không phải sau bảng)
            body.remove(con[i]); i -= 1
        con = [e for e in body if e.tag != qn("w:sectPr")]
        for a, b in zip(con, con[1:]):
            if trong(a) and trong(b):
                body.remove(b)
    except Exception:
        pass


def _luu_bytes(d):
    bio = io.BytesIO()
    d.save(bio)
    return bio.getvalue()


def _luu_sach(d):
    """Lưu văn bản ĐẦU RA đã làm sạch dòng trống thừa."""
    _bo_dong_trong_thua(d)
    return _luu_bytes(d)


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
    t = re.sub(r"[^\d.,]", "", str(v or ""))
    m = re.match(r"^([\d.]*\d),(\d+)$", t)
    if m and ("." in m.group(1) or len(m.group(2)) != 3):      # '4.500.000.000,000': cổng ghi kèm phần thập phân -> bỏ phần sau dấu phẩy
        t = m.group(1)
    t = re.sub(r"\D", "", t)
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
            ct = str(n.get("chi_tiet") or "").strip()
            if khoa == "ten" and ct:                         # dòng "Chi tiết: …" nằm ở hàng dưới tên ngành, in nghiêng (như bảng trên cổng)
                ct = ct if re.match(r"(?i)chi tiết\s*:", ct) else "Chi tiết: " + ct
                p2 = r.cells[j].add_paragraph()
                rr = p2.add_run(ct)
                rr.italic = True
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
_GIU_12 = {"ten": "TEN", "dia_chi": "DIA_CHI", "von": "VON", "nganh": "NGANH", "thue": "THUE", "cshhl": "CSHHL", "bo_sung": "B", "cap_nhat": "B"}
# Thay đổi cần Quyết định/Nghị quyết của chủ sở hữu/HĐTV/ĐHĐCĐ (tự soạn). Chỉ bổ sung/cập nhật thông tin (mục B Mẫu 12) thì KHÔNG cần.
CAN_QUYET_DINH = {"ten", "dia_chi", "von", "nganh", "dai_dien", "chu_so_huu"}


def _loai_can_quyet_dinh(du):
    """Các nội dung thay đổi CẦN Quyết định/Nghị quyết. Công ty TNHH từ 2 thành viên: chuyển nhượng vốn/thay đổi thành viên góp vốn mà KHÔNG đổi người đại diện
    (giám đốc) và KHÔNG bầu Chủ tịch HĐTV mới thì KHÔNG cần Quyết định của Hội đồng thành viên (hồ sơ chỉ gồm Mẫu 12, Phụ lục I-6, Hợp đồng chuyển nhượng)."""
    can = set(du.get("loai") or []) & CAN_QUYET_DINH
    if "chu_so_huu" in can and "dai_dien" not in can and not str(du.get("chu_tich_moi") or "").strip() and _doi_thanh_vien_nhieu_tv(du):
        can -= {"chu_so_huu"}
    return can


def _kieu_cshhl(du):
    """Mục CSHHL của Mẫu 12: 'a' = THAY ĐỔI thông tin chủ sở hữu hưởng lợi đã kê khai; 'b' = BỔ SUNG/CẬP NHẬT (doanh nghiệp thành lập trước 01/7/2025 bổ sung theo khoản 1
    Điều 3 Luật 76/2025/QH15). Người dùng chọn (du["cshhl_kieu"] = a/b); để trống thì tự: ngày cấp GCN trước 01/7/2025 -> 'b', còn lại 'a'."""
    v = str(du.get("cshhl_kieu") or "").strip().lower()
    if v in ("a", "b"):
        return v
    mm = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", _ngay_dd_mm_yyyy((du.get("hien_tai") or {}).get("ngay_cap_gcn") or ""))
    if mm and (int(mm.group(3)), int(mm.group(2)), int(mm.group(1))) < (2025, 7, 1):
        return "b"
    return "a"


def _lam_sach_mau(m, bo_dong=(), giu_b_cshhl=False):
    """Làm gọn Mẫu 12/13 như bộ hồ sơ thực tế: bỏ tiêu đề 'Mẫu số…', các dòng chú thích/ghi chú trong ngoặc, khối chú thích cuối trang và chỉ số trên."""
    d = m.doc
    thua = [r"^M[ẫa]u\s*số\s*\d+\s*$", r"^\(Dùng trong trường hợp", r"^\(Doanh nghiệp chọn và kê khai", r"^Trường hợp thay đổi thành viên hợp danh",
            ] + ([] if giu_b_cshhl else [r"^b\)\s*Đối với doanh nghiệp được thành lập trước ngày 01/7/2025"]) + list(bo_dong)
    body = d.element.body
    phan_tu = list(body)
    i = 0
    while i < len(phan_tu):
        c = phan_tu[i]
        if c.tag == qn("w:p"):
            t = _chu(c)
            if any(re.search(p, t) for p in thua):
                body.remove(c)
            elif re.fullmatch(r"_{5,}", t):                 # dòng gạch ngang + các chú thích (1, 2, 3, - …) bên dưới
                body.remove(c)
                j = i + 1
                while j < len(phan_tu) and phan_tu[j].tag == qn("w:p") and re.match(r"^(\d+\s|-\s)", _chu(phan_tu[j]) or "x"):
                    body.remove(phan_tu[j])
                    j += 1
                i = j - 1
        i += 1
    for r in list(d.element.body.iter(qn("w:r"))):          # chỉ số chú thích (1, 2, 3 in nhỏ lên trên)
        va = r.find(qn("w:rPr") + "/" + qn("w:vertAlign"))
        if va is not None and va.get(qn("w:val")) == "superscript" and re.fullmatch(r"\d+", "".join(t.text or "" for t in r.iter(qn("w:t")))):
            r.getparent().remove(r)


def _bo_ngoac_kinh_gui(m):
    for p in m.doan(0, 12):
        t = _van(p)
        k = "(Cơ quan đăng ký kinh doanh cấp tỉnh) "
        if t.startswith("Kính gửi:") and k in t:
            _thay_khoang(p, t.index(k), t.index(k) + len(k), "- ")
            return


def _anh_ky_nguoi(du, chu_ky, ten, *anh_uu_tien):
    """Ảnh chữ ký (Kho chữ ký, đã được người đó đồng ý) của người tên `ten`: thử các ảnh ưu tiên trước; không có thì nếu người đó CHÍNH LÀ người đại diện theo pháp luật
    hiện tại (cùng họ tên) dùng chữ ký 'giam_doc', hoặc chính là chủ sở hữu hiện tại thì dùng 'chu_so_huu' (ca thật SOL AGENCY: chủ sở hữu kiêm giám đốc, Kho chữ ký
    chỉ lưu ở mục Giám đốc nên Mẫu 12 ký bằng tư cách Chủ sở hữu không gắn được chữ ký)."""
    for a in anh_uu_tien:
        if a:
            return a
    ck = chu_ky or {}
    ht = du.get("hien_tai") or {}
    chuan = lambda x: " ".join(str(x or "").upper().split())
    if chuan(ten) and chuan(ten) == chuan(ht.get("dd_ho_ten")) and ck.get("giam_doc"):
        return ck["giam_doc"]
    if chuan(ten) and chuan(ten) == chuan(ht.get("chu_so_huu")) and ck.get("chu_so_huu"):
        return ck["chu_so_huu"]
    return None


def _nguoi_ky_2tv(du, chu_ky):
    """Người ký hồ sơ + bên ủy quyền: công ty TNHH 1 thành viên -> CHỦ SỞ HỮU CÔNG TY (chủ công ty); TNHH từ 2 thành viên -> CHỦ TỊCH HĐTV (mới nếu có bầu mới).
    (Giấy ủy quyền: hồ sơ KHÔNG đổi người đại diện thì Bên A là GIÁM ĐỐC hiện tại — xem soan_giay_uy_quyen.)
    (tiêu đề, họ tên, ảnh chữ ký) hoặc None nếu chưa biết người đó / loại hình khác."""
    dn, ht = du.get("dn") or {}, du.get("hien_tai") or {}
    lh = (dn.get("loai_hinh") or "").lower()
    if "trách nhiệm hữu hạn" not in lh:
        return None
    if "một thành viên" in lh:
        if (ht.get("chu_so_huu") or "").strip():
            return "CHỦ SỞ HỮU CÔNG TY", ht["chu_so_huu"].strip(), _anh_ky_nguoi(du, chu_ky, ht["chu_so_huu"], (chu_ky or {}).get("chu_so_huu"))
        return None
    ct = _tra_khoa_nguoi(du.get("thanh_vien"), du.get("chu_tich_moi")) if du.get("chu_tich_moi") else None
    if ct and (ct.get("ho_ten") or "").strip():
        so = re.sub(r"\D", "", ct.get("cccd") or "")
        return "CHỦ TỊCH HỘI ĐỒNG THÀNH VIÊN", ct["ho_ten"].strip(), _anh_ky_nguoi(du, chu_ky, ct["ho_ten"], (chu_ky or {}).get("cccd:" + so) if len(so) >= 9 else None)
    if (ht.get("chu_so_huu") or "").strip():
        return "CHỦ TỊCH HỘI ĐỒNG THÀNH VIÊN", ht["chu_so_huu"].strip(), _anh_ky_nguoi(du, chu_ky, ht["chu_so_huu"], (chu_ky or {}).get("chu_so_huu"))
    return None


def _cccd_chu_tich(du):
    """Số định danh của Chủ tịch (HĐTV mới nếu có, không thì chủ sở hữu 1TV) — dùng cho dòng 'Chỉ kê khai khi ủy quyền' ở Mẫu 13."""
    ct = _tra_khoa_nguoi(du.get("thanh_vien"), du.get("chu_tich_moi")) if du.get("chu_tich_moi") else None
    if ct and (ct.get("cccd") or "").strip():
        return ct["cccd"].strip()
    ht = du.get("hien_tai") or {}
    if (ht.get("chu_so_huu_cccd") or "").strip():
        return ht["chu_so_huu_cccd"].strip()
    for x in (du.get("thanh_vien") or {}).get("ht") or []:
        if (x.get("ho_ten") or "").strip().upper() == (ht.get("chu_so_huu") or "").strip().upper() and (x.get("cccd") or "").strip():
            return x["cccd"].strip()
    return ""


TIEU_DE_KY = "NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT/\nCHỦ TỊCH CÔNG TY/CHỦ TỊCH HỘI ĐỒNG THÀNH VIÊN CỦA CÔNG TY"


def _khoi_ky(c, tieu_de, ten, anh):
    """Thay nội dung ô ký: tiêu đề + (Ký, ghi họ tên) + chỗ ký + họ tên (không ký thay; gắn ảnh chỉ khi đã được người đó đồng ý)."""
    for p in list(c.paragraphs)[1:]:
        p._p.getparent().remove(p._p)
    p0 = c.paragraphs[0]
    for r in list(p0.runs):
        r._r.getparent().remove(r._r)
    p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
    dong_td = tieu_de.split("\n")
    p0.add_run(dong_td[0]).bold = True
    for them_dong in dong_td[1:]:
        pp = c.add_paragraph()
        pp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pp.add_run(them_dong).bold = True
    p1 = c.add_paragraph()
    p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p1.add_run("(Ký, ghi họ tên)").italic = True
    _dong_trong_ky(c)
    pk = c.add_paragraph()
    pk.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pk.add_run(ten.strip().upper()).bold = True
    _gan_chu_ky(pk, anh)


def _dien_thong_tin_thue(m, du, pham_vi):
    """Mẫu 12 — 'Thông báo thay đổi thông tin đăng ký thuế': Giám đốc, Kế toán trưởng, địa chỉ nhận thông báo thuế, ngày bắt đầu hoạt động,
    hình thức hạch toán, năm tài chính, số lao động, phương pháp tính thuế GTGT. Chỉ điền ô có dữ liệu; ô khác giữ nguyên dấu chấm."""
    t = dict(du.get("thue") or {})
    if t.get("cung_dia_chi") in (True, "1", 1, "true"):             # địa chỉ nhận thông báo thuế = địa chỉ trụ sở công ty (mới nếu có đổi địa chỉ)
        a = du.get("dia_chi") if "dia_chi" in set(du.get("loai") or []) else _tach_dia_chi((du.get("hien_tai") or {}).get("dia_chi"))
        for k, ka in (("tt_so_nha", "so_nha"), ("tt_xa", "xa"), ("tt_tinh", "tinh")):
            if not (t.get(k) or "").strip() and (a or {}).get(ka):
                t[k] = a[ka]
    lo, hi = pham_vi
    ps = m.doan(lo, hi)
    van = [_van(p) for p in ps]

    def vt(mau, tu=0):
        for i in range(tu, len(ps)):
            if re.search(mau, van[i]):
                return i
        return None
    i_gd, i_kt, i_dc = vt(r"^Thông tin về Giám đốc"), vt(r"^Thông tin về Kế toán trưởng"), vt(r"^Địa chỉ nhận thông báo thuế")
    i_ngay, i_hach, i_nam = vt(r"^Ngày bắt đầu hoạt động"), vt(r"^Hình thức hạch toán"), vt(r"^Năm tài chính")
    i_ld, i_pp = vt(r"^Tổng số lao động"), vt(r"^Phương pháp tính thuế GTGT")

    def dien_neu_trong(p, nhan, v, mau=_CHAM):
        """Chỉ điền khi ô còn trống (dấu chấm); ô đã có chữ (vd đã điền Giám đốc từ mục đổi người đại diện) thì không điền lần 2."""
        tx = _van(p)
        mm = re.search(nhan, tx)
        if not mm:
            return
        con = re.sub(r"\([^)]*\)", "", tx[mm.end():])
        if not re.fullmatch(r"[…\.\s/:：]*", con):
            return
        dien_cham(p, nhan, v, mau)

    def dien_muc(a, b, tien_to, giatri):
        if a is None:
            return
        b = b if b is not None else len(ps)
        for nhan, k, mau in ((tien_to, "ho_ten", _CHAM), (r"Ngày, tháng, năm sinh", "ngay_sinh", _NGAY3), (r"Giới tính", "gioi_tinh", _CHAM),
                             (r"Số định danh cá nhân", "cccd", _CHAM), (r"Điện thoại", "dien_thoai", _CHAM)):
            v = (giatri.get(k) or "").strip()
            if not v:
                continue
            if k == "ngay_sinh":
                v = _ngay_dd_mm_yyyy(v)
            if k == "ho_ten":
                v = v.upper()
            for i in range(a, b):
                if re.search(nhan, van[i]):
                    dien_neu_trong(ps[i], nhan, v, mau)
                    break
    gd = {k[3:]: v for k, v in t.items() if k.startswith("gd_")}
    kt = {k[3:]: v for k, v in t.items() if k.startswith("kt_")}
    dien_muc(i_gd, i_kt, r"Họ, chữ đệm và tên Giám đốc/Tổng giám đốc", gd)
    dien_muc(i_kt, i_dc, r"Họ, chữ đệm và tên Kế toán trưởng/Phụ trách kế toán", kt)
    if i_dc is not None:
        for nhan, k in ((r"Số nhà/phòng, ngách/hẻm, ngõ/kiệt, đường/phố/đại lộ, tổ/xóm/ấp/thôn", "tt_so_nha"), (r"Xã/Phường/Đặc khu", "tt_xa"), (r"Tỉnh/Thành phố trực thuộc trung ương", "tt_tinh"),
                        (r"Điện thoại \(nếu có\)", "tt_dien_thoai"), (r"Số fax \(nếu có\)", "tt_fax"), (r"Thư điện tử \(nếu có\)", "tt_email")):
            v = (t.get(k) or "").strip()
            for i in range(i_dc, i_ngay if i_ngay is not None else len(ps)):
                if v and re.search(nhan, van[i]):
                    dien_cham(ps[i], nhan, v)
                    break
    if i_ngay is not None and (t.get("ngay_bat_dau") or "").strip():
        dien_cham(ps[i_ngay], r"Ngày bắt đầu hoạt động\d?", _ngay_dd_mm_yyyy(t["ngay_bat_dau"]), _NGAY3)

    def tick(i0, ten):
        if i0 is None:
            return
        for i in range(i0, min(len(ps), i0 + 40)):
            if van[i].strip() == ten:
                for j in range(i + 1, min(len(ps), i + 4)):
                    if "□" in van[j]:
                        for r in ps[j].runs:
                            if "□" in r.text:
                                r.text = r.text.replace("□", "☒", 1)
                                return
        return
    hach = (t.get("hach_toan") or "").strip().lower()
    if i_hach is not None and hach:
        tick(i_hach, "Hạch toán phụ thuộc" if "phụ" in hach else "Hạch toán độc lập")
    if i_nam is not None and (t.get("nam_tu") or "").strip() and (t.get("nam_den") or "").strip():
        for i in range(i_nam, min(len(ps), i_nam + 4)):
            if van[i].startswith("Áp dụng từ ngày"):
                _thay_khoang(ps[i], 0, len(van[i]), f"Áp dụng từ ngày {t['nam_tu'].strip()} đến ngày {t['nam_den'].strip()}")
                break
    if i_ld is not None and str(t.get("lao_dong") or "").strip():
        dien_cham(ps[i_ld], r"Tổng số lao động", str(t["lao_dong"]).strip())
    pp = (t.get("pp_gtgt") or "").strip()
    if i_pp is not None and pp:
        ten_pp = {"khấu trừ": "Khấu trừ", "trực tiếp trên gtgt": "Trực tiếp trên GTGT", "trực tiếp trên doanh số": "Trực tiếp trên doanh số", "không phải nộp thuế gtgt": "Không phải nộp thuế GTGT"}.get(pp.lower())
        if ten_pp:
            tick(i_pp, ten_pp)


def _dong_cap_nhat(du):
    """Các dòng mục B Mẫu 12 khi chỉ CẬP NHẬT thông tin (không đổi nội dung đăng ký): [(văn bản, đậm_cả_dòng, thụt_đầu_dòng, [(đoạn, đậm)...])].
    Theo bộ hồ sơ thực tế: "1. Cập nhật địa chỉ trụ sở chính công ty:" (3 dòng số nhà/xã/tỉnh — địa chỉ ghi lại theo đơn vị hành chính mới sau sáp nhập) rồi
    "2. Cập nhật thông tin đại diện pháp luật và thành viên:" kèm từng người "n/ Họ và tên …, Giới tính, Sinh ngày, Dân tộc, Quốc tịch, Số giấy tờ…, Ngày cấp,
    Nơi cấp, Địa chỉ thường trú". Chỉ ghi ô có dữ liệu (không bịa)."""
    cn = du.get("cap_nhat") or {}
    dc = cn.get("dia_chi") or {}
    dong, so = [], 0
    if any((dc.get(k) or "").strip() for k in ("so_nha", "xa", "tinh")):
        so += 1
        dong.append((f"{so}. Cập nhật địa chỉ trụ sở chính công ty:", True, True, None))
        for nhan, k in (("Số nhà/phòng, ngách/hẻm, ngõ/kiệt, đường/phố/đại lộ, tổ/xóm/ấp/thôn: ", "so_nha"), ("Xã/Phường/Đặc khu: ", "xa"),
                        ("Tỉnh/Thành phố trực thuộc trung ương: ", "tinh")):
            if (dc.get(k) or "").strip():
                dong.append((nhan + dc[k].strip(), False, False, None))
    ng = [x for x in (cn.get("nguoi") or []) if (x.get("ho_ten") or "").strip()]
    if ng:
        so += 1
        dong.append((f"{so}. Cập nhật thông tin đại diện pháp luật và thành viên:", True, True, None))
        for i, x in enumerate(ng, 1):
            dong.append((f"{i}/ Họ và tên: {x['ho_ten'].strip().upper()}", False, False, [(f"{i}/ Họ và tên: ", False), (x["ho_ten"].strip().upper(), True)]))
            for nhan, v in (("Giới tính", x.get("gioi_tinh")), ("Sinh ngày", _ngay_dd_mm_yyyy(x.get("ngay_sinh"))), ("Dân tộc", x.get("dan_toc") or "Kinh"),
                            ("Quốc tịch", x.get("quoc_tich") or "Việt Nam"), ("Số giấy tờ pháp lý của cá nhân", x.get("cccd")),
                            ("Ngày cấp", _ngay_dd_mm_yyyy(x.get("ngay_cap"))), ("Nơi cấp", x.get("noi_cap")),
                            ("Địa chỉ thường trú", x.get("dia_chi") or _dia_chi_nguoi(x))):
                if str(v or "").strip():
                    dong.append((f"{nhan}: {str(v).strip()}", False, False, None))
    return dong


def _chen_cap_nhat_muc_b(mau_el, dong):
    """Chèn các dòng _dong_cap_nhat vào TRƯỚC đoạn chấm `mau_el` của mục B (nhân bản định dạng đoạn chấm: cỡ chữ/căn lề/giãn dòng)."""
    import copy
    for van, dam, thut, runs in dong:
        el = copy.deepcopy(mau_el)
        r0 = el.find(qn("w:r"))
        rpr = copy.deepcopy(r0.find(qn("w:rPr"))) if r0 is not None and r0.find(qn("w:rPr")) is not None else None
        for r in el.findall(qn("w:r")):
            el.remove(r)
        mau_el.addprevious(el)
        p = Paragraph(el, None)
        if thut:
            p.paragraph_format.first_line_indent = Emu(285750)
        for t, d in (runs or [(van, dam)]):
            r = p.add_run(t)
            if rpr is not None:
                r._r.insert(0, copy.deepcopy(rpr))
            r.bold = bool(d)


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
    if "dai_dien" in loai and "THUE" in cac and (du.get("dai_dien") or [{}])[0].get("ho_ten"):
        n = du["dai_dien"][0]
        lo, hi = cac["THUE"]
        m.dien(r"Họ, chữ đệm và tên Giám đốc/Tổng giám đốc", (n.get("ho_ten") or "").upper(), lo, hi)
        p = m.tim(r"Ngày, tháng, năm sinh", lo, hi)
        if p is not None and n.get("ngay_sinh"):
            dien_cham(p, r"Ngày, tháng, năm sinh", _ngay_dd_mm_yyyy(n["ngay_sinh"]), _NGAY3)
        m.dien(r"Giới tính", n.get("gioi_tinh"), lo, hi)
        m.dien(r"Số định danh cá nhân", n.get("cccd"), lo, hi)
        m.dien(r"Điện thoại", n.get("dien_thoai"), lo, hi)
    if "thue" in loai and "THUE" in cac:
        _dien_thong_tin_thue(m, du, cac["THUE"])
    if ("bo_sung" in loai or "cap_nhat" in loai) and "B" in cac:
        lo, hi = cac["B"]
        trong = [c for c in m.ch[lo:hi] if c.tag == qn("w:p") and re.fullmatch(r"[…\.\s]+", _chu(c) or "")]
        if "cap_nhat" in loai and trong:
            _chen_cap_nhat_muc_b(trong[0], _dong_cap_nhat(du))
            if "bo_sung" not in loai:                         # chỉ CẬP NHẬT: bỏ các dòng chấm của mục B
                for c in trong:
                    c.getparent().remove(c)
                trong = []
        if "bo_sung" in loai:
            dong = [x.strip() for x in re.split(r"[\n;]+", str((du.get("bo_sung") or {}).get("noi_dung") or "")) if x.strip()]
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
    chi_chuyen = _chi_chuyen_nhuong_von(du)
    if chi_chuyen:
        giu.add("VON")                            # chỉ chuyển nhượng vốn giữa các thành viên: mục "THAY ĐỔI VỐN ĐIỀU LỆ, PHẦN VỐN GÓP, TỶ LỆ PHẦN VỐN GÓP" (mục 2), không phải mục thành viên
    elif _doi_thanh_vien_nhieu_tv(du):
        giu.add("THANH_VIEN")                     # đổi thành viên công ty TNHH 2TV trở lên: "kê khai Danh sách thành viên theo Mẫu số 6 (Phụ lục I-6). Gửi kèm."
    if "dai_dien" in loai:
        giu.add("THUE")                           # đổi người đại diện: thông báo thay đổi thông tin đăng ký thuế (Giám đốc/Tổng giám đốc)
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
    if chi_chuyen and "von" not in loai and "VON" in cac:
        # vốn điều lệ KHÔNG đổi: bỏ mục "1. Đăng ký thay đổi vốn điều lệ…" (và phần cổ phần), bỏ cam kết thanh toán nợ (chỉ khi giảm vốn); giữ mục 2 (phần vốn góp, tỷ lệ)
        m1, m2, cam = (m.chi_so(r"^1\.\s*Đăng ký thay đổi vốn điều lệ"), m.chi_so(r"^2\.\s*Đăng ký thay đổi phần vốn góp"),
                       m.chi_so(r"^Doanh nghiệp cam kết bảo đảm thanh toán"))
        if cam is not None:
            m.xoa_phan(cam, cam + 1)
        if m1 is not None and m2 is not None and m1 < m2:
            m.xoa_phan(m1, m2)
    # chữ ký: ghi sẵn họ tên người đại diện theo pháp luật (người đại diện mới nếu có thay đổi) — phần mềm KHÔNG ký thay
    ten_ky = ((du.get("dai_dien") or [{}])[0].get("ho_ten") if "dai_dien" in loai else "") or (du.get("hien_tai") or {}).get("dd_ho_ten") or ""
    ky2 = _nguoi_ky_2tv(du, chu_ky)
    if ten_ky.strip() or ky2:
        for tb in d.tables:
            if any("NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT/" in c.text for r in tb.rows for c in r.cells):
                c = [c for c in tb.rows[-1].cells if "NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT/" in c.text][0]
                if ky2:                               # người ký là Chủ tịch công ty/Chủ tịch HĐTV; tiêu đề chuẩn của giấy đề nghị
                    _khoi_ky(c, TIEU_DE_KY, ky2[1], ky2[2])
                else:
                    # chữ ký trong Kho chữ ký chỉ là của người đại diện HIỆN TẠI (đã được người đó đồng ý) — không gắn khi ký là người đại diện mới
                    _dong_trong_ky(c)
                    pk = c.add_paragraph()
                    pk.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    pk.add_run(ten_ky.strip().upper()).bold = True
                    _gan_chu_ky(pk, (chu_ky or {}).get("giam_doc") if "dai_dien" not in loai else None)
                _giu_mot_trang(tb)
                break
    _bo_ngoac_kinh_gui(m)
    giu_b = False
    if "cshhl" in loai and _kieu_cshhl(du) == "b":
        # CẬP NHẬT/BỔ SUNG thông tin CSHHL (DN thành lập trước 01/7/2025): giữ mục b), bỏ mục a)
        for c in list(d.element.body):
            if c.tag == qn("w:p") and re.match(r"^a\)\s*Trường hợp doanh nghiệp có sự thay đổi thông tin về chủ sở hữu hưởng lợi", _chu(c) or ""):
                d.element.body.remove(c)
        giu_b = True
    _lam_sach_mau(m, giu_b_cshhl=giu_b)
    for p in m.doan(0, len(m.ch)):                      # công ty TNHH: tiêu đề mục thành viên chỉ giữ phần TNHH (bỏ "thành viên hợp danh công ty hợp danh")
        t = _van(p)
        if t.startswith("ĐĂNG KÝ THAY ĐỔI THÀNH VIÊN CÔNG TY TNHH") and "HỢP DANH" in t:
            _thay_khoang(p, 0, len(t), "ĐĂNG KÝ THAY ĐỔI THÀNH VIÊN CÔNG TY TNHH")
            break
    return d


def soan_mau13(du, chu_ky=None):
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
    ky = _nguoi_ky_2tv(du, chu_ky)
    if ky:
        if du.get("tao_uy_quyen"):                                       # "Số định danh cá nhân của Chủ tịch…" chỉ kê khai khi ủy quyền nộp hồ sơ
            so_ct = _cccd_chu_tich(du)
            if so_ct:
                m.dien(r"Số định danh cá nhân của Chủ tịch hội đồng thành viên", so_ct, 0, bd if bd is not None else len(m.ch))
        for tb in d.tables:
            c = next((c for r in tb.rows for c in r.cells if "CHỦ TỊCH CÔNG TY/CHỦ TỊCH HỘI ĐỒNG" in c.text.replace("\n", " ")), None)
            if c is not None:
                _khoi_ky(c, TIEU_DE_KY, ky[1], ky[2])
                _giu_mot_trang(tb)
                break
    _bo_ngoac_kinh_gui(m)
    _lam_sach_mau(m)
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



# ============================================================ ĐỊA CHỈ 1 Ô, DANH SÁCH THÀNH VIÊN (Phụ lục I-6), MẪU 10
def _tach_dia_chi(s):
    """'481 Hòa Hảo, Phường Diên Hồng, TP Hồ Chí Minh, Việt Nam' -> số nhà/đường, xã/phường, tỉnh/thành, quốc gia (người dùng chỉ nhập 1 ô)."""
    parts = [p.strip() for p in str(s or "").replace("\n", ",").split(",") if p.strip()]
    kq = {"so_nha": "", "xa": "", "tinh": "", "quoc_gia": ""}
    if parts and parts[-1].lower() in ("việt nam", "viet nam", "vietnam", "vn"):
        kq["quoc_gia"] = "Việt Nam"
        parts.pop()
    if len(parts) >= 3:
        kq["tinh"], kq["xa"], kq["so_nha"] = parts[-1], parts[-2], ", ".join(parts[:-2])
    elif len(parts) == 2:
        kq["so_nha"], kq["tinh"] = parts
    elif parts:
        kq["so_nha"] = parts[0]
    return kq


def _chuan_dia_chi(n):
    """Người dùng nhập 'dia_chi' (1 ô) mà chưa có số nhà/xã/tỉnh -> tự tách ra để điền Mẫu 13/15."""
    n = dict(n or {})
    if (n.get("dia_chi") or "").strip() and not any((n.get(k) or "").strip() for k in ("so_nha", "xa", "tinh")):
        for k, v in _tach_dia_chi(n["dia_chi"]).items():
            if v and not (n.get(k) or "").strip():
                n[k] = v
    return n


def _gia_tri_von(x):
    return so_nguyen(x.get("von")) or 0


def _chuyen_mot_phan(x, cac, k=None):
    """Các lần chuyển MỘT PHẦN vốn hợp lệ của thành viên x (đang còn): người nhận còn trong công ty, số tiền > 0; tổng không vượt phần vốn đang có."""
    kq, con = [], x.get("_von") if "_von" in x else _gia_tri_von(x)
    for c in x.get("cn") or []:
        t = so_nguyen(c.get("tien")) or 0
        den = c.get("den")
        if t > 0 and den in cac and den != k and not cac[den].get("bo") and t <= con:
            con -= t
            kq.append({"den": den, "_tien": t, "gia": c.get("gia")})
    return kq


def tinh_thanh_vien_sau(tv):
    """tv = {"ht": [thành viên hiện tại], "moi": [thành viên mới]}. Hiện tại có "bo": True là bị gạch (rời công ty); "chuyen_cho": "h2"/"m0"
    là chuyển phần vốn đó cho thành viên có số thứ tự tương ứng (h = hiện tại, m = mới). Trả danh sách SAU thay đổi kèm von (số) và ty_le (%)."""
    ht = [dict(x) for x in (tv or {}).get("ht") or []]
    moi = [dict(x) for x in (tv or {}).get("moi") or [] if (x.get("ho_ten") or "").strip()]
    cac = {f"h{i}": x for i, x in enumerate(ht)}
    cac.update({f"m{i}": x for i, x in enumerate(moi)})
    for x in cac.values():
        x["_von"] = _gia_tri_von(x)
    nhan = {x["chuyen_cho"] for x in cac.values() if x.get("bo") and x.get("chuyen_cho") in cac and not cac[x["chuyen_cho"]].get("bo")}
    for k, x in cac.items():                                  # chuyển MỘT PHẦN vốn (người chuyển vẫn còn là thành viên): x["cn"] = [{"den": "h0"/"m0", "tien": "2.000.000.000"}]
        if not x.get("bo"):
            nhan |= {c["den"] for c in _chuyen_mot_phan(x, cac, k)}
    for k in nhan:
        if k.startswith("m"):
            cac[k]["_von"] = 0                      # thành viên MỚI nhận chuyển nhượng: phần vốn = phần nhận (không cộng thêm số đã nhập, tránh tính 2 lần)
    for k, x in list(cac.items()):
        if x.get("bo") and x.get("chuyen_cho") in cac and not cac[x["chuyen_cho"]].get("bo"):
            cac[x["chuyen_cho"]]["_von"] += so_nguyen(x.get("gia")) or _gia_tri_von(x)      # giá chuyển nhượng đã nhập thì phần vốn chuyển theo giá đó
    for k, x in cac.items():
        if not x.get("bo"):
            for c in _chuyen_mot_phan(x, cac, k):
                x["_von"] -= c["_tien"]
                cac[c["den"]]["_von"] += c["_tien"]
    sau = [x for x in cac.values() if not x.get("bo")]
    tong = sum(x["_von"] for x in sau)
    for x in sau:
        x["von"] = x.pop("_von")
        x["ty_le"] = (f"{x['von'] * 100 / tong:.2f}".rstrip("0").rstrip(".").replace(".", ",") + "%") if tong else (x.get("ty_le") or "")
    return sau, tong


def _dia_chi_nguoi(n):
    return ((n.get("dia_chi") or "").strip() or _dia_chi_day_du(n.get("so_nha"), n.get("xa"), n.get("tinh"))) + \
        ((", " + n["quoc_gia"]) if (n.get("quoc_gia") or "").strip() and "việt nam" not in ((n.get("dia_chi") or "").lower()) else "")


def _giay_to(n):
    t = (n.get("cccd") or "").strip()
    if not t:
        return ""
    return f"Số giấy tờ pháp lý của cá nhân: {t}" + (f", Nơi cấp: {n['noi_cap'].strip()}" if (n.get("noi_cap") or "").strip() else "")


def _chi_chuyen_nhuong_von(du):
    """Chỉ CHUYỂN NHƯỢNG phần vốn giữa các thành viên hiện tại (không ai rời/không thành viên mới): Mẫu 12 dùng mục "ĐĂNG KÝ THAY ĐỔI VỐN ĐIỀU LỆ,
    PHẦN VỐN GÓP, TỶ LỆ PHẦN VỐN GÓP" (2. thay đổi phần vốn góp, tỷ lệ phần vốn góp) chứ không phải "ĐĂNG KÝ THAY ĐỔI THÀNH VIÊN"."""
    if not _doi_thanh_vien_nhieu_tv(du):
        return False
    tv = du.get("thanh_vien") or {}
    return not [x for x in tv.get("ht") or [] if x.get("bo")] and not [x for x in tv.get("moi") or [] if (x.get("ho_ten") or "").strip()] \
        and bool(_cac_cap_chuyen_nhuong(tv))


def _doi_thanh_vien_nhieu_tv(du):
    """Thay đổi thành viên của công ty TNHH từ 2 thành viên trở lên (không phải công ty 1 thành viên)."""
    if "chu_so_huu" not in set(du.get("loai") or []):
        return False
    lh = ((du.get("dn") or {}).get("loai_hinh") or "").lower()
    sau, _t = tinh_thanh_vien_sau(du.get("thanh_vien"))
    return "một thành viên" not in lh and len(sau) >= 2


def _tra_khoa_nguoi(tv, khoa):
    """'h1' / 'm0' -> người thứ 2 trong danh sách hiện tại / người mới thứ 1."""
    try:
        ds = (tv or {}).get("ht" if str(khoa)[:1] == "h" else "moi") or []
        return ds[int(str(khoa)[1:])]
    except (ValueError, IndexError, TypeError):
        return None


def _xung(n):
    return "bà" if (n.get("gioi_tinh") or "").strip().lower() in ("nữ", "nu", "female") else "ông"


def _cac_cap_chuyen_nhuong(tv):
    """[(bên bán, bên mua)] cho mỗi thành viên bị gạch có chuyển phần vốn cho người khác (toàn bộ), và mỗi lần chuyển MỘT PHẦN vốn
    (bên bán là bản sao của thành viên với "von" = số tiền chuyển, để hợp đồng ghi đúng phần chuyển và tỷ lệ chuyển)."""
    kq = []
    cac = {f"h{i}": x for i, x in enumerate((tv or {}).get("ht") or [])}
    cac.update({f"m{i}": x for i, x in enumerate((tv or {}).get("moi") or [])})
    for k, x in cac.items():
        if k[0] == "h" and not x.get("bo"):
            for c in _chuyen_mot_phan(x, cac, k):
                mua = cac[c["den"]]
                if (mua.get("ho_ten") or "").strip():
                    kq.append((dict(x, von=c["_tien"], gia=c.get("gia") or "", von_truoc=_gia_tri_von(x)), mua))
    for x in (tv or {}).get("ht") or []:
        if x.get("bo") and x.get("chuyen_cho"):
            mua = _tra_khoa_nguoi(tv, x["chuyen_cho"])
            if mua and not mua.get("bo") and (mua.get("ho_ten") or "").strip():
                kq.append((x, mua))
    return kq


def soan_hop_dong_chuyen_nhuong(du, ban, mua, chu_ky=None):
    """Hợp đồng chuyển nhượng phần vốn góp (công ty TNHH hai thành viên trở lên) — theo mẫu hồ sơ người dùng cung cấp. Không ký thay."""
    dn, ht = du.get("dn") or {}, du.get("hien_tai") or {}
    ten = (dn.get("ten") or "").strip().upper() or "……"
    tv = du.get("thanh_vien") or {}
    tong_truoc = sum(_gia_tri_von(x) for x in tv.get("ht") or [])
    von_ban = _gia_tri_von(ban)
    ty = (f"{von_ban * 100 / tong_truoc:.2f}".rstrip("0").rstrip(".").replace(".", ",") + "%") if tong_truoc and von_ban else "……"
    tien = (f"{von_ban:,}".replace(",", ".") + " đồng") if von_ban else "……"
    # Điều 1: PHẦN VỐN GÓP HIỆN CÓ của bên bán trước khi chuyển (vd 2.250.000.000 đồng, 45%); Điều 2: phần CHUYỂN NHƯỢNG (vd 1.750.000.000 đồng, 35%).
    von_goc = so_nguyen(ban.get("von_truoc")) or von_ban
    ty_goc = (f"{von_goc * 100 / tong_truoc:.2f}".rstrip("0").rstrip(".").replace(".", ",") + "%") if tong_truoc and von_goc else "……"
    tien_goc = (f"{von_goc:,}".replace(",", ".") + " đồng") if von_goc else "……"
    gia = so_nguyen(ban.get("gia")) if (str(ban.get("gia") or "").strip()) else von_ban
    gia_s = (f"{gia:,}".replace(",", ".") + " đồng") if gia else "……"
    import datetime
    mm = re.match(r"(\d{2})/(\d{2})/(\d{4})", _ngay_dd_mm_yyyy(dn.get("ngay_lap") or "")) or re.match(r"(\d{2})/(\d{2})/(\d{4})", datetime.date.today().strftime("%d/%m/%Y"))
    ngay = f"ngày {int(mm.group(1))} tháng {int(mm.group(2))} năm {mm.group(3)}"
    dia_chi_cty = (ht.get("dia_chi") or "").strip() or "……"
    d = _van_ban_moi()
    _doan(d, "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", dam=True, can="giua", sau=0)
    _doan(d, "Độc lập - Tự do - Hạnh phúc", dam=True, can="giua", sau=0)
    _doan(d, "----0o0----", can="giua", sau=8)
    _doan(d, "HỢP ĐỒNG CHUYỂN NHƯỢNG PHẦN VỐN GÓP", dam=True, can="giua", sau=8)
    _doan(d, f"Hôm nay, {ngay[0].upper() + ngay[1:]} tại trụ sở {ten}, địa chỉ {dia_chi_cty}. Chúng tôi gồm có:", can="deu")

    def ben(tieu_de, n, ho_khau):
        _doan(d, tieu_de, dam=True, sau=2)
        _doan(d, f"Họ và tên: {(n.get('ho_ten') or '').upper() or '……'}\t\tGiới tính: {n.get('gioi_tinh') or '……'}", sau=0)
        _doan(d, f"Sinh ngày: {_ngay_dd_mm_yyyy(n.get('ngay_sinh')) or '……'}\tDân tộc: {n.get('dan_toc') or 'Kinh'}\tQuốc tịch: {n.get('quoc_tich') or 'Việt Nam'}", sau=0)
        _doan(d, f"Số chứng thực: {n.get('cccd') or '……'}\tNgày cấp: {_ngay_dd_mm_yyyy(n.get('ngay_cap')) or '……'}\tNơi cấp: {n.get('noi_cap') or '……'}", sau=0)
        _doan(d, f"{ho_khau}: {_dia_chi_nguoi(n) or '……'}", sau=6)
    ben("Bên chuyển nhượng (Bên bán):", ban, "Chỗ ở hiện tại")
    ben("Bên nhận chuyển nhượng (Bên mua):", mua, "Nơi đăng ký hộ khẩu thường trú")
    _doan(d, "Hai bên đồng ý thực hiện việc chuyển nhượng phần vốn góp với các thỏa thuận sau:", can="deu")
    so_gcn, ngay_gcn = (dn.get("ma_so") or "……"), (ht.get("ngay_cap_gcn") or "……")
    dieu = [("Điều 1:", f"Trong thời gian qua Ông/bà: {(ban.get('ho_ten') or '').upper() or '……'} (Bên bán) có góp vốn vào {ten} với tỷ lệ giá trị phần góp vốn là {tien_goc} chiếm {ty_goc} vốn điều lệ công ty theo Giấy chứng nhận đăng ký doanh nghiệp số {so_gcn} cấp ngày {ngay_gcn}."),
            ("Điều 2:", f"Hai bên cùng thỏa thuận giá chuyển nhượng phần góp {tien} chiếm {ty} vốn điều lệ nói trên là {gia_s}.\nThời điểm hoàn thành việc chuyển nhượng: {ngay[0].upper() + ngay[1:]}."),
            ("Điều 3:", f"1/ Hai bên có nghĩa vụ thực hiện các vấn đề liên quan đến việc chuyển nhượng phần vốn góp để {ten} hoàn tất thủ tục đăng ký kinh doanh theo quy định của pháp luật.\n2/ Bên mua có trách nhiệm kế thừa toàn bộ các quyền và nghĩa vụ của bên bán với tư cách là một thành viên góp vốn của {ten} kể từ ngày hoàn tất việc chuyển nhượng vốn góp."),
            ("Điều 4:", f"Sau khi hoàn tất việc chuyển nhượng vốn, mọi sự tranh chấp phát sinh nếu có, hai bên cùng nhau thương lượng giải quyết theo nguyên tắc tôn trọng quyền lợi của nhau. Trong trường hợp không giải quyết được thì một trong hai bên có quyền khởi kiện để yêu cầu tòa án có thẩm quyền giải quyết theo quy định của pháp luật hiện hành. {ten}, cơ quan đăng ký kinh doanh không có trách nhiệm giải quyết các tranh chấp phát sinh nếu có."),
            ("Điều 5:", "Hai bên cùng cam kết những thông tin về nhân thân, phần vốn chuyển nhượng đã ghi trên hợp đồng là đúng sự thật. Phần vốn góp chuyển nhượng không có tranh chấp, không bị kê biên để đảm bảo thi hành án. Việc giao kết hợp đồng là hoàn toàn tự nguyện, không bị lừa dối hoặc ép buộc. Bên mua đã xem xét kỹ, biết rõ về phần vốn góp nhận chuyển nhượng nêu trên và giấy tờ pháp lý liên quan. Hai bên có trách nhiệm thực hiện đúng và đầy đủ các nội dung đã thỏa thuận trong hợp đồng."),
            ("Điều 6:", "Hai bên đã đọc, đã hiểu và đồng ý tất cả các điều khoản ghi trong Hợp đồng trước khi ký tên vào hợp đồng."),
            ("Điều 7:", f"Hợp đồng này có hiệu lực kể từ thời điểm các bên ký tên và được lập thành bốn bản có giá trị như nhau, Ông/bà: {(ban.get('ho_ten') or '').upper() or '……'} (Bên bán) giữ 01 bản, Ông/bà: {(mua.get('ho_ten') or '').upper() or '……'} (Bên mua) giữ 01 bản, 01 bản lưu lại công ty, 01 bản nộp Phòng Đăng ký kinh doanh.")]
    for tieu, nd in dieu:
        p = _doan(d, tieu, dam=True, sau=2)
        p.paragraph_format.keep_with_next = True
        for dong in nd.split("\n"):
            _doan(d, dong, can="deu", sau=4)
    tb = d.add_table(rows=1, cols=2)
    for c, (nhan, n, k) in zip(tb.rows[0].cells, (("Bên bán", ban, "ben_ban"), ("Bên mua", mua, "ben_mua"))):
        c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        c.paragraphs[0].add_run(nhan).bold = True
        p2 = c.add_paragraph()
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p2.add_run("(ký, ghi rõ họ tên)").italic = True
        _dong_trong_ky(c)
        pk = c.add_paragraph()
        pk.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pk.add_run((n.get("ho_ten") or "").upper()).bold = True
        so = re.sub(r"\D", "", n.get("cccd") or "")
        _gan_chu_ky(pk, (chu_ky or {}).get("cccd:" + so) if len(so) >= 9 else None)
    _can_bang_hai_ben(tb)
    _giu_mot_trang(tb, 2)
    return d


def soan_phu_luc_i6(du, chu_ky=None):
    """Phụ lục I-6 (TT 68/2025/TT-BTC): Danh sách thành viên công ty TNHH hai thành viên trở lên — theo danh sách SAU khi chuyển/chuyển nhượng vốn."""
    from docx.enum.section import WD_ORIENT
    from docx.oxml import OxmlElement
    dn = du.get("dn") or {}
    sau, tong = tinh_thanh_vien_sau(du.get("thanh_vien"))
    d = _van_ban_moi()
    sec = d.sections[0]
    sec.orientation = WD_ORIENT.LANDSCAPE
    sec.page_width, sec.page_height = Cm(29.7), Cm(21)
    sec.left_margin = sec.right_margin = Cm(1.5)
    sec.top_margin = sec.bottom_margin = Cm(1.5)              # trang ngang: lề trên/dưới 1,5 cm để khối ký giám đốc còn chỗ ở trang 1
    d.styles["Normal"].font.size = Pt(11)
    _doan(d, "Phụ lục I-6", dam=True, can="giua", sau=0)
    _doan(d, "(Ban hành kèm theo Thông tư số 68/2025/TT-BTC ngày 01 tháng 07 năm 2025 của Bộ trưởng Bộ Tài Chính)", nghieng=True, can="giua", sau=8)
    _doan(d, "DANH SÁCH THÀNH VIÊN CÔNG TY TRÁCH NHIỆM HỮU HẠN HAI THÀNH VIÊN TRỞ LÊN", dam=True, can="giua", sau=2)
    if (dn.get("ten") or "").strip():
        _doan(d, (dn["ten"]).strip().upper() + (f" — MST {dn['ma_so']}" if (dn.get("ma_so") or "").strip() else ""), can="giua", sau=8)
    cot = ["STT", "Tên thành viên", "Ngày, tháng, năm sinh đối với thành viên là cá nhân", "Giới tính", "Loại giấy tờ, số, ngày cấp, cơ quan cấp Giấy tờ pháp lý của cá nhân",
           "Quốc tịch", "Dân tộc", "Địa chỉ liên lạc", "Phần vốn góp (bằng số; VNĐ và giá trị tương đương theo đơn vị tiền nước ngoài, nếu có)", "Tỷ lệ (%)",
           "Loại tài sản, số lượng, giá trị tài sản góp vốn", "Thời hạn góp vốn", "Chữ ký của thành viên", "Ghi chú (nếu có)"]
    tb = d.add_table(rows=2, cols=len(cot))
    tb.style = "Table Grid"
    tb.alignment = 1
    for i, t in enumerate(cot):
        c = tb.rows[0].cells[i]
        c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        c.paragraphs[0].add_run(t).bold = True
        n = tb.rows[1].cells[i]
        n.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        n.paragraphs[0].add_run(str(i + 1)).bold = True
    rong = [0.9, 2.3, 2.1, 1.3, 3.2, 1.5, 1.4, 3.3, 2.8, 1.3, 2.0, 1.9, 2.4, 1.3]
    for r in tb.rows:
        for i, c in enumerate(r.cells):
            c.width = Cm(rong[i])
    for stt, n in enumerate(sau, 1):
        r = tb.add_row()
        gia_tri = [str(stt), (n.get("ho_ten") or "").upper(), _ngay_dd_mm_yyyy(n.get("ngay_sinh")), n.get("gioi_tinh") or "", _giay_to(n), n.get("quoc_tich") or "Việt Nam",
                   n.get("dan_toc") or "", _dia_chi_nguoi(n), (f"{n['von']:,}".replace(",", ".") + " VNĐ") if n.get("von") else "", n.get("ty_le") or "",
                   n.get("loai_tai_san") or "Đồng Việt Nam", _ngay_dd_mm_yyyy(n.get("thoi_han")), "", n.get("ghi_chu") or ""]
        for i, v in enumerate(gia_tri):
            r.cells[i].width = Cm(rong[i])
            p = r.cells[i].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run(v)
        key = "cccd:" + re.sub(r"\D", "", n.get("cccd") or "")
        anh = (chu_ky or {}).get(key)
        if anh and len(key) > 9:                      # chữ ký thành viên lấy từ Kho chữ ký (đã được người đó đồng ý)
            _gan_chu_ky(r.cells[12].paragraphs[0], anh, 2.2, 1.4)
        trpr = r._tr.get_or_add_trPr()
        trpr.append(OxmlElement("w:cantSplit"))
    khoi = [_doan(d, _ngay_chu(dn), nghieng=True, can="giua", sau=0)]       # không chèn dòng trống: cách bảng bằng khoảng trước 8pt
    khoi[0].paragraph_format.space_before = Pt(8)
    khoi.append(_doan(d, "NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT/CHỦ TỊCH HỘI ĐỒNG THÀNH VIÊN CỦA CÔNG TY", dam=True, can="giua", sau=0))
    khoi.append(_doan(d, "(Ký và ghi họ tên)", nghieng=True, can="giua", sau=0))
    ten_ky = (du.get("hien_tai") or {}).get("dd_ho_ten") or (du.get("hien_tai") or {}).get("chu_so_huu") or ""
    if ten_ky.strip():
        _dong_trong_ky(d)
        pk = _doan(d, ten_ky.strip().upper(), dam=True, can="giua", sau=0)
        _gan_chu_ky(pk, (chu_ky or {}).get("giam_doc"), 8.0, 3.6)   # trang ngang thấp: dấu tối đa 3,6 cm (cỡ dấu thật) để khối ký vừa trang
        khoi += d.paragraphs[-1 - _SO_DONG_KY:-1]                   # các dòng chừa chỗ ký ngay trên họ tên
    for pp in khoi:                                                 # cả khối ký (ngày, chức danh, chỗ ký, họ tên) luôn đi CÙNG một trang
        pp.paragraph_format.keep_with_next = True
        pp.paragraph_format.keep_together = True
    return d


def danh_sach_cshhl_sau(cs):
    ht = [x for x in (cs or {}).get("ht") or [] if not x.get("bo")]
    moi = [x for x in (cs or {}).get("moi") or [] if (x.get("ho_ten") or "").strip()]
    return ht + moi


def soan_mau10(du, chu_ky=None):
    """Mẫu số 10 (TT 121/2026) — Danh sách chủ sở hữu hưởng lợi: điền người đang tham gia (trừ người bị gạch) + người thêm mới."""
    d = cat_mau(10)
    m = _Mau(d)
    ds = danh_sach_cshhl_sau(du.get("cshhl_ds"))
    bang = [c for c in d.element.body if c.tag == qn("w:tbl")]
    if ds and bang:
        from docx.table import _Row, Table
        tb = Table(bang[0], d._body)
        mau_hang = tb.rows[-1]._tr
        for i, n in enumerate(ds, 1):
            hang = copy.deepcopy(mau_hang)
            mau_hang.addprevious(hang)
            r = _Row(hang, tb)
            tt = lambda v: "" if v in (None, "") else str(v)
            tong = ""
            try:
                a, b = float(str(n.get("truc_tiep") or 0).replace(",", ".")), float(str(n.get("gian_tiep") or 0).replace(",", "."))
                tong = (f"{a + b:g}") if (n.get("truc_tiep") or n.get("gian_tiep")) else ""
            except ValueError:
                tong = ""
            gia_tri = [str(i), (n.get("ho_ten") or "").upper(), _ngay_dd_mm_yyyy(n.get("ngay_sinh")), n.get("gioi_tinh") or "", _giay_to(n), n.get("quoc_tich") or "Việt Nam",
                       n.get("dan_toc") or "", _dia_chi_nguoi(n), tt(n.get("truc_tiep")), tt(n.get("gian_tiep")), tong]
            for j, v in enumerate(gia_tri):
                _dat_o(r.cells[j], v)
        mau_hang.getparent().remove(mau_hang)
    # họ tên người đại diện ký (không ký thay; gắn chữ ký chỉ khi có trong Kho chữ ký)
    ten_ky = ((du.get("dai_dien") or [{}])[0].get("ho_ten") if "dai_dien" in set(du.get("loai") or []) else "") or (du.get("hien_tai") or {}).get("dd_ho_ten") or ""
    for tb in d.tables:
        c = next((c for r in tb.rows for c in r.cells if "NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT/" in c.text), None)
        if c is not None:
            for p in c.paragraphs:
                if _van(p).strip().startswith("……, ngày"):
                    _thay_khoang(p, 0, len(_van(p).split("\n")[0]), _ngay_chu(du.get("dn") or {}))
                    break
            if ten_ky.strip():
                _dong_trong_ky(c)
                pk = c.add_paragraph()
                pk.alignment = WD_ALIGN_PARAGRAPH.CENTER
                pk.add_run(ten_ky.strip().upper()).bold = True
                _gan_chu_ky(pk, (chu_ky or {}).get("giam_doc") if "dai_dien" not in set(du.get("loai") or []) else None)
                _giu_mot_trang(tb)
            break
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


_SO_DONG_KY = 3          # số dòng trống chừa cho chữ ký phía trên họ tên
_CAO_DONG_KY_PT = 24      # mỗi dòng trống cao CỐ ĐỊNH 24pt (không phụ thuộc kiểu chữ của mẫu) -> khoảng ký cao 3 x 24pt = 2,54 cm


def _dong_trong_ky(o):
    """Thêm các dòng trống (cao cố định) chừa chỗ ký phía trên họ tên trong ô/khối `o`."""
    from docx.enum.text import WD_LINE_SPACING
    for _ in range(_SO_DONG_KY):
        pp = o.add_paragraph()
        pf = pp.paragraph_format
        pf.space_before = pf.space_after = Pt(0)
        pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
        pf.line_spacing = Pt(_CAO_DONG_KY_PT)


def _rong_cot_emu(p):
    """Bề rộng (EMU) ô bảng chứa đoạn p (theo w:tcW) — để canh chữ ký quanh giữa ô; None nếu không đọc được."""
    try:
        tc = p._p.xpath("ancestor::w:tc")[0]
        w = tc.xpath("./w:tcPr/w:tcW/@w:w")
        loai = tc.xpath("./w:tcPr/w:tcW/@w:type")
        if w and (not loai or loai[0] == "dxa"):
            return int(w[0]) * 635                       # 1 dxa = 1/20 pt = 635 EMU
    except Exception:
        pass
    return None


def _cat_vien_anh(raw):
    """Cắt bỏ viền TRẮNG/TRONG SUỐT thừa quanh dấu/chữ ký (ảnh người dùng chụp/quét có lề to nhỏ khác nhau) để mọi mẫu được co
    theo đúng phần nét mực -> kích thước in ra đồng đều. Trả (bytes PNG, rộng, cao); ảnh trống/lỗi thì giữ nguyên ảnh gốc."""
    from PIL import Image, ImageChops
    im = Image.open(io.BytesIO(raw))
    try:
        rgba = im.convert("RGBA")
        nen = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        phang = Image.alpha_composite(nen, rgba).convert("L")             # nền trong suốt -> trắng
        muc = phang.point(lambda v: 255 if v < 235 else 0)                 # điểm có mực (tối hơn gần-trắng)
        bb = muc.getbbox()
        if not bb:
            return raw, im.size[0], im.size[1]
        dem = max(2, int(0.03 * max(bb[2] - bb[0], bb[3] - bb[1])))
        bb = (max(0, bb[0] - dem), max(0, bb[1] - dem), min(rgba.size[0], bb[2] + dem), min(rgba.size[1], bb[3] + dem))
        if bb == (0, 0) + rgba.size:
            return raw, im.size[0], im.size[1]
        cat = rgba.crop(bb)
        bio = io.BytesIO()
        cat.save(bio, "PNG")
        return bio.getvalue(), cat.size[0], cat.size[1]
    except Exception:
        return raw, im.size[0], im.size[1]


def _gan_chu_ky(p, anh_uri, rong_cm=8.0, cao_cm=4.0):
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
        raw, w, h = _cat_vien_anh(raw)                                  # bỏ lề trắng thừa -> mọi mẫu dấu/chữ ký co theo đúng phần nét
        import random
        # TỰ CÂN CHỈNH VỪA FORM (kích thước dấu/chữ ký KHÔNG cố định): ảnh co theo tỷ lệ để vừa bề rộng ô (<= 90%) và chiều cao tối đa cao_cm,
        # rồi khoảng trống phía trên họ tên được co/giãn theo đúng chiều cao ảnh (cao ảnh + 2,5 mm, tối thiểu 1,5 cm) — ảnh nhỏ thì không chừa
        # dòng trống thừa, ảnh lớn thì chừa vừa đủ, không bao giờ đè lên dòng "(Ký, ghi họ tên)" hay họ tên.
        rc = _rong_cot_emu(p)
        if rc:
            rong_cm = min(rong_cm, rc / 360000 * 0.9)
        ti = min(rong_cm / w, cao_cm / h) * random.uniform(0.96, 1.0)           # lệch nhẹ kích thước/vị trí/góc xoay mỗi lần như ký tay
        cao_anh_cm = h * ti
        e = p._p.getprevious()
        trong = []
        while e is not None and e.tag == qn("w:p") and not "".join(e.itertext()).strip() and e.find(".//" + qn("w:spacing")) is not None \
                and e.find(".//" + qn("w:spacing")).get(qn("w:lineRule")) == "exact":
            trong.append(e)
            e = e.getprevious()
        if trong:
            tong_pt = max(cao_anh_cm * 0.8, 1.2) * 28.3465            # ảnh ở phía sau chữ nên chỉ chừa ~80% chiều cao ảnh: họ tên được kéo lên sát, ảnh phủ nhẹ xuống họ tên như ký/đóng dấu thật
            for e in trong:
                e.find(".//" + qn("w:spacing")).set(qn("w:line"), str(int(tong_pt / len(trong) * 20)))
            khoang_emu = int(tong_pt * 12700)
        else:
            khoang_emu = int(_SO_DONG_KY * _CAO_DONG_KY_PT * 12700)
        cx, cy = int(w * ti * 360000), int(h * ti * 360000)
        run = p.add_run()
        run.add_picture(io.BytesIO(raw), width=Emu(cx), height=Emu(cy))
        inline = run._r.xpath(".//wp:inline")[0]
        ns = {"wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"}
        if not trong and p._p.xpath("ancestor::w:tc"):
            # Ô ký trong BẢNG không có khoảng chừa phía trên (vd. cột "Chữ ký của thành viên" Phụ lục I-6): vẫn để "phía sau chữ" nhưng neo
            # TỪ ĐỈNH ô xuống (không lùi lên — lùi lên là lệch sang hàng trên) và đặt chiều cao tối thiểu của hàng >= chiều cao ảnh
            # (ảnh nổi không tự nới hàng) -> ảnh luôn nằm trọn trong đúng hàng của người ký.
            from docx.oxml import OxmlElement
            tr = p._p.xpath("ancestor::w:tr")[0]
            trpr = tr.get_or_add_trPr()
            can = cy + int(0.2 * 360000)
            cu = trpr.find(qn("w:trHeight"))
            if cu is None:
                cu = OxmlElement("w:trHeight")
                trpr.append(cu)
            cu.set(qn("w:val"), str(max(int(cu.get(qn("w:val")) or 0), can // 635 + 1)))
            cu.set(qn("w:hRule"), "atLeast")
            lech = int(0.1 * 360000 * random.uniform(0.6, 1.0))
        else:
            khoang = khoang_emu                                   # chiều cao khoảng trống phía trên họ tên (EMU) — đã khớp với chiều cao ảnh ở trên
            lech = -int(khoang * 0.98) + int(random.uniform(-1, 1) * 0.06 * 360000)       # đỉnh ảnh bắt đầu từ đầu khoảng trống, phần thừa phủ xuống họ tên (behind text)
        rong_cot = _rong_cot_emu(p)
        if rong_cot and rong_cot > cx:
            vi_tri_h = f'<wp:positionH relativeFrom="column"><wp:posOffset>{int((rong_cot - cx) / 2 + random.uniform(-1, 1) * min(0.45 * 360000, (rong_cot - cx) / 2))}</wp:posOffset></wp:positionH>'
        else:
            vi_tri_h = '<wp:positionH relativeFrom="column"><wp:align>center</wp:align></wp:positionH>'
        anchor = parse_xml(
            f'<wp:anchor {nsdecls("wp")} distT="0" distB="0" distL="0" distR="0" simplePos="0" relativeHeight="251658240" behindDoc="1" '
            f'locked="0" layoutInCell="1" allowOverlap="1"><wp:simplePos x="0" y="0"/>'
            f'{vi_tri_h}'
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
        try:                                                        # xoay nhẹ quanh tâm (−6° … +6°)
            xf = dr.xpath(".//a:xfrm")[0]
            xf.set("rot", str(int(random.uniform(-6, 6) * 60000)))
        except Exception:
            pass
        return True
    except Exception:
        return False


def _can_bang_hai_ben(tb):
    """Bảng ký 2 cột (Bên A | Bên B...): chiều cao khoảng chừa ký của 2 ô PHẢI BẰNG NHAU (lấy bên lớn hơn) để hai họ tên nằm ngang hàng.
    Ảnh của bên nhỏ hơn được dịch theo để vẫn nằm trong khoảng chừa."""
    cot = []
    for c in tb.rows[0].cells:
        sp = [e for e in c._tc.findall(qn("w:p")) if not "".join(e.itertext()).strip() and e.find(".//" + qn("w:spacing")) is not None
              and e.find(".//" + qn("w:spacing")).get(qn("w:lineRule")) == "exact"]
        cot.append((c, sp, sum(int(e.find(".//" + qn("w:spacing")).get(qn("w:line"))) for e in sp)))
    if len(cot) < 2 or not all(x[1] for x in cot):
        return
    cao = max(x[2] for x in cot)
    for c, sp, tong in cot:
        if tong >= cao:
            continue
        for e in sp:
            e.find(".//" + qn("w:spacing")).set(qn("w:line"), str(int(cao / len(sp))))
        d_emu = int((cao - tong) * 635)                                    # twips -> EMU
        for pv in c._tc.xpath(".//wp:positionV/wp:posOffset"):
            pv.text = str(int(pv.text) - d_emu // 2)


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
    if "hai thành viên" in lh or "trách nhiệm hữu hạn" in lh or "hợp danh" in lh:
        return "HỘI ĐỒNG THÀNH VIÊN", "QUYẾT ĐỊNH", "Hội đồng thành viên"       # công ty từ 2 thành viên: Quyết định của Hội đồng thành viên
    return "CHỦ SỞ HỮU", "QUYẾT ĐỊNH", "Chủ sở hữu"


def _bang_loai_giay_to(d, so_giay_to):
    """Bảng 2x2 tick loại giấy tờ chứng thực cá nhân (CCCD 12 số -> Căn cước công dân; 9 số -> Chứng minh nhân dân)."""
    so = re.sub(r"\D", "", so_giay_to or "")
    tb = d.add_table(rows=2, cols=2)
    tb.style = "Table Grid"
    for i, (nhan, k) in enumerate((("Chứng minh nhân dân", 9), ("Căn cước công dân", 12), ("Hộ chiếu", 0), ("Loại khác (ghi rõ):", 0))):
        tb.rows[i // 2].cells[i % 2].paragraphs[0].add_run(("☒ " if k and len(so) == k else "☐ ") + nhan)
    return tb


def _dieu_doi_dai_dien_1tv(d, du):
    """Quyết định của CHỦ SỞ HỮU (TNHH 1TV) khi chỉ đổi người đại diện theo pháp luật — theo mẫu hồ sơ thực tế. Trả số Điều kế tiếp."""
    ht = du.get("hien_tai") or {}
    moi = (du.get("dai_dien") or [{}])[0]
    cu = (ht.get("dd_ho_ten") or "").strip()
    ten_moi = (moi.get("ho_ten") or "").strip().upper() or "……"
    _doan(d, "Điều 1: ", dam=True, gach=True, sau=4)
    _doan(d, f"Thay đổi Ông/Bà {cu.upper() or '……'} chức danh {ht.get('dd_chuc_danh') or '……'} chuyển sang đại diện pháp luật mới là Ông/Bà {ten_moi} - chức danh {moi.get('chuc_danh') or '……'}.", can="deu", sau=2)
    _doan(d, "Đại diện theo pháp luật", dam=True, sau=2)
    dia_chi = _dia_chi_nguoi(moi) or "……"
    for dong in (f"- Họ tên: {ten_moi}", f"Sinh ngày: {_ngay_dd_mm_yyyy(moi.get('ngay_sinh')) or '……'}", f"Dân tộc: {moi.get('dan_toc') or 'Kinh'}",
                 f"Quốc tịch: {moi.get('quoc_tich') or 'Việt Nam'}", "Loại giấy tờ chứng thực cá nhân:"):
        _doan(d, dong, sau=0)
    _bang_loai_giay_to(d, moi.get("cccd"))
    for dong in (f"Số giấy tờ chứng thực cá nhân: {moi.get('cccd') or '……'}", f"Ngày cấp: {_ngay_dd_mm_yyyy(moi.get('ngay_cap')) or '……'}", f"Nơi cấp: {moi.get('noi_cap') or '……'}",
                 "Ngày hết hạn (nếu có): ", f"Nơi đăng ký hộ khẩu thường trú: {dia_chi}", f"Chỗ ở hiện tại: {dia_chi}", f"Chức vụ: {moi.get('chuc_danh') or '……'}"):
        _doan(d, dong, sau=0)
    _doan(d, "", sau=4)
    return 2


def _dieu_bau_chu_tich(d, du, ct):
    """Các Điều của Quyết định bầu Chủ tịch HĐTV (đổi chủ/thành viên 2TV) theo mẫu hồ sơ thực tế. Trả số Điều kế tiếp."""
    dn, ht = du.get("dn") or {}, du.get("hien_tai") or {}
    tv = du.get("thanh_vien") or {}
    loai = set(du.get("loai") or [])
    ngay = _ngay_dd_mm_yyyy(dn.get("ngay_lap") or "") or "……"
    ten_ct = (ct.get("ho_ten") or "").strip().upper()
    _doan(d, "Điều 1: ", dam=True, gach=True, sau=4).add_run("Bầu Chủ tịch Hội đồng thành viên").bold = True
    _doan(d, f"Bầu {_xung(ct)} {ten_ct} giữ chức vụ Chủ tịch Hội đồng thành viên Công ty kể từ ngày {ngay}, thông tin cá nhân như sau:", can="deu", sau=2)
    _doan(d, "Chủ tịch Hội đồng thành viên", dam=True, sau=2)
    for dong in (f"- Họ tên: {ten_ct}", f"Sinh ngày: {_ngay_dd_mm_yyyy(ct.get('ngay_sinh')) or '……'}", f"Dân tộc: {ct.get('dan_toc') or 'Kinh'}",
                 f"Quốc tịch: {ct.get('quoc_tich') or 'Việt Nam'}", "Loại giấy tờ chứng thực cá nhân:"):
        _doan(d, dong, sau=0)
    _bang_loai_giay_to(d, ct.get("cccd"))
    for dong in (f"Số giấy tờ chứng thực cá nhân: {ct.get('cccd') or '……'}", f"Ngày cấp: {_ngay_dd_mm_yyyy(ct.get('ngay_cap')) or '……'}", f"Nơi cấp: {ct.get('noi_cap') or '……'}",
                 "Ngày hết hạn (nếu có): ", f"Chỗ ở hiện tại: {_dia_chi_nguoi(ct) or '……'}", "Chức vụ: Chủ tịch Hội đồng thành viên"):
        _doan(d, dong, sau=0)
    _doan(d, "", sau=4)
    n = 2
    cu = (ht.get("chu_so_huu") or "").strip()
    if cu and cu.upper() != ten_ct:
        bo = [x for x in tv.get("ht") or [] if x.get("bo")]
        roi = any((x.get("ho_ten") or "").strip().upper() == cu.upper() for x in bo)
        cu_obj = next((x for x in tv.get("ht") or [] if (x.get("ho_ten") or "").strip().upper() == cu.upper()), {})
        _doan(d, f"Điều {n}: ", dam=True, gach=True, sau=4).add_run(
            f"{_xung(cu_obj).capitalize()} {cu.upper()} thôi giữ chức vụ Chủ tịch Hội đồng thành viên Công ty kể từ ngày {ngay}" + (" do đã chuyển nhượng toàn bộ phần vốn góp tại Công ty." if roi else "."))
        n += 1
    if "dai_dien" in loai:
        moi = (du.get("dai_dien") or [{}])[0]
        cu_dd = (ht.get("dd_ho_ten") or "").strip()
        y = "Thay đổi người đại diện theo pháp luật của Công ty: "
        if cu_dd and cu_dd.upper() != (moi.get("ho_ten") or "").strip().upper():
            cu_obj = next((x for x in tv.get("ht") or [] if (x.get("ho_ten") or "").strip().upper() == cu_dd.upper()), {})
            y += f"{_xung(cu_obj)} {cu_dd.upper()}" + (f" (chức danh {ht['dd_chuc_danh']})" if (ht.get("dd_chuc_danh") or "").strip() else "") + " thôi làm người đại diện theo pháp luật; "
        y += f"{_xung(moi)} {(moi.get('ho_ten') or '').upper() or '……'}, chức danh {moi.get('chuc_danh') or '……'}, là người đại diện theo pháp luật mới của Công ty kể từ ngày {ngay}."
        _doan(d, f"Điều {n}: ", dam=True, gach=True, sau=4).add_run(y)
        n += 1
    return n


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
    la_hdtv = chu == "HỘI ĐỒNG THÀNH VIÊN"
    ct_moi = _tra_khoa_nguoi(du.get("thanh_vien"), du.get("chu_tich_moi")) if (la_hdtv and du.get("chu_tich_moi")) else None
    bau_ct = bool(ct_moi and (ct_moi.get("ho_ten") or "").strip() and bool(loai & {"chu_so_huu", "dai_dien"}) and not (loai & (CAN_QUYET_DINH - {"chu_so_huu", "dai_dien"})))      # chỉ đổi chủ/thành viên + người đại diện: Quyết định bầu Chủ tịch HĐTV (theo mẫu hồ sơ thực tế)
    dd_1tv = (not la_hdtv) and chu == "CHỦ SỞ HỮU" and "một thành viên" in (dn.get("loai_hinh") or "").lower() and "dai_dien" in loai \
        and not (loai & (CAN_QUYET_DINH - {"dai_dien"})) and ((du.get("dai_dien") or [{}])[0].get("ho_ten") or "").strip()
    if bau_ct:
        d.paragraphs[-3].runs[0].text = loai_vb
        d.paragraphs[-2].runs[0].text = "Về việc bầu Chủ tịch Hội đồng thành viên"
    if la_hdtv:
        _doan(d, "- Căn cứ Luật Doanh nghiệp năm 2020 được sửa đổi, bổ sung năm 2025" + (" (Điều 55, Điều 56);" if bau_ct else ";"), can="deu", thut=True)
        _doan(d, "- Căn cứ Nghị định số 168/2025/NĐ-CP ngày 30 tháng 6 năm 2025 của Chính phủ về đăng ký doanh nghiệp;", can="deu", thut=True)
    if not bau_ct:
        _doan(d, f"- Căn cứ Điều lệ {ten} đã được thông qua ngày {ht.get('ngay_dieu_le') or '……'}" + (";" if la_hdtv else "."), can="deu", thut=True)
    _doan(d, loai_vb, dam=True, can="giua", sau=10)
    loai_goc = loai
    if bau_ct:
        so_dieu = _dieu_bau_chu_tich(d, du, ct_moi)
        loai = set()                                    # các mục thay đổi đã nằm trong các Điều ở trên
    elif dd_1tv:
        so_dieu = _dieu_doi_dai_dien_1tv(d, du)
        loai = set()
    else:
        so_dieu = 2
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
            if ds and any((x.get("chi_tiet") or "").strip() for x in ds):
                muc.append((f"{nhan} ngành, nghề kinh doanh:", [(f"{x.get('ma') or '……'} — {x.get('ten') or ''}", (x.get("chi_tiet") or "").strip()) for x in ds]))
            elif ds:
                muc.append(f"{nhan} ngành, nghề kinh doanh: " + "; ".join(f"{x.get('ten') or ''} (mã ngành {x.get('ma') or '……'})" for x in ds) + ".")
    if "dai_dien" in loai:
        n = (du.get("dai_dien") or [{}])[0]
        muc.append(f"Thay đổi người đại diện theo pháp luật của công ty từ Ông/Bà {(ht.get('dd_ho_ten') or '……')} sang Ông/Bà "
                   f"{(n.get('ho_ten') or '').upper() or '……'}, chức danh {n.get('chuc_danh') or '……'}, số định danh cá nhân {n.get('cccd') or '……'}.")
    if "chu_so_huu" in loai:
        n = du.get("chu_so_huu_moi") or {}
        tv = du.get("thanh_vien") or {}
        if tv.get("ht") or tv.get("moi"):
            bo = [x for x in tv.get("ht") or [] if x.get("bo")]
            moi = [x for x in tv.get("moi") or [] if (x.get("ho_ten") or "").strip()]
            sau, tong = tinh_thanh_vien_sau(tv)
            y = "Thay đổi thành viên/chủ sở hữu công ty"
            chi_chuyen = not bo and not moi and bool(_cac_cap_chuyen_nhuong(tv))
            if chi_chuyen:                                  # chỉ chuyển nhượng vốn giữa các thành viên hiện tại: KHÔNG phải thay đổi thành viên/chủ sở hữu
                tong_truoc = sum(_gia_tri_von(x) for x in tv.get("ht") or [])
                y = "Chuyển nhượng phần vốn góp giữa các thành viên công ty: " + "; ".join(
                    f"Ông/Bà {(b_['ho_ten'] or '').upper()} chuyển nhượng cho Ông/Bà {(m_['ho_ten'] or '').upper()} phần vốn góp trị giá {b_['von']:,}".replace(",", ".")
                    + (f" đồng, tương ứng tỷ lệ {b_['von'] * 100 / tong_truoc:.2f}".rstrip("0").rstrip(".").replace(".", ",") + "% vốn điều lệ" if tong_truoc else " đồng")
                    for b_, m_ in _cac_cap_chuyen_nhuong(tv))
            if bo:
                y += ": " + "; ".join(f"Ông/Bà {(x.get('ho_ten') or '').upper()} chuyển nhượng/chuyển giao phần vốn góp" for x in bo)
            if moi:
                y += ("; " if bo else ": ") + "tiếp nhận thành viên/chủ sở hữu mới " + ", ".join(f"Ông/Bà {(x.get('ho_ten') or '').upper()} (số định danh cá nhân {x.get('cccd') or '……'})" for x in moi)
            muc.append(y + ".")
            ct = _tra_khoa_nguoi(tv, du.get("chu_tich_moi")) if la_hdtv else None
            if ct and (ct.get("ho_ten") or "").strip():
                ngay_hl = _ngay_dd_mm_yyyy(dn.get("ngay_lap") or "") or "……"
                dong = [f"Họ tên: {(ct.get('ho_ten') or '').upper()}", f"Sinh ngày: {_ngay_dd_mm_yyyy(ct.get('ngay_sinh')) or '……'}",
                        f"Dân tộc: {ct.get('dan_toc') or 'Kinh'}", f"Quốc tịch: {ct.get('quoc_tich') or 'Việt Nam'}",
                        f"Số giấy tờ chứng thực cá nhân: {ct.get('cccd') or '……'}", f"Ngày cấp: {_ngay_dd_mm_yyyy(ct.get('ngay_cap')) or '……'}",
                        f"Nơi cấp: {ct.get('noi_cap') or '……'}", f"Chỗ ở hiện tại: {_dia_chi_nguoi(ct) or '……'}", "Chức vụ: Chủ tịch Hội đồng thành viên"]
                muc.append((f"Bầu {_xung(ct)} {(ct.get('ho_ten') or '').upper()} giữ chức vụ Chủ tịch Hội đồng thành viên Công ty kể từ ngày {ngay_hl}, thông tin cá nhân như sau:", [(x, "") for x in dong]))
                cu = (ht.get("chu_so_huu") or "").strip()
                if cu and cu.upper() != (ct.get("ho_ten") or "").strip().upper():
                    roi = any((x.get("ho_ten") or "").strip().upper() == cu.upper() for x in bo)
                    muc.append(f"Ông/Bà {cu.upper()} thôi giữ chức vụ Chủ tịch Hội đồng thành viên Công ty kể từ ngày {ngay_hl}" + (" do đã chuyển nhượng toàn bộ phần vốn góp tại Công ty." if roi else "."))
            if sau and tong:
                muc.append(("Phần vốn góp sau khi chuyển nhượng: " if chi_chuyen else "Phần vốn góp sau khi thay đổi: ") + "; ".join(f"Ông/Bà {(x.get('ho_ten') or '').upper()} góp {x['von']:,}".replace(",", ".") + f" đồng, tỷ lệ {x['ty_le']}" for x in sau) + ".")
        else:
            muc.append(f"Thay đổi chủ sở hữu công ty: chủ sở hữu mới là Ông/Bà {(n.get('ho_ten') or '').upper() or '……'}, số định danh cá nhân {n.get('cccd') or '……'}.")
    for i, t in enumerate(muc, 1):
        if isinstance(t, tuple):                      # ngành có "Chi tiết": mỗi ngành 1 dòng, dòng "Chi tiết: …" nghiêng ở hàng dưới
            p = _doan(d, f"{i}. {t[0]}", can="deu", sau=2)
            p.paragraph_format.left_indent = Cm(0.8)
            for dong, ct in t[1]:
                q = _doan(d, "- " + dong, can="deu", sau=0 if ct else 2)
                q.paragraph_format.left_indent = Cm(1.6)
                if ct:
                    q2 = _doan(d, ct if re.match(r"(?i)chi tiết\s*:", ct) else "Chi tiết: " + ct, nghieng=True, can="deu", sau=2)
                    q2.paragraph_format.left_indent = Cm(2.0)
            continue
        p = _doan(d, f"{i}. {t}", can="deu")
        p.paragraph_format.left_indent = Cm(0.8)
    loai = loai_goc
    dd = (ht.get("dd_ho_ten") or "").strip()
    if "dai_dien" in loai and (du.get("dai_dien") or [{}])[0].get("ho_ten"):
        dd = (du["dai_dien"][0].get("ho_ten") or "").strip()
    if dd_1tv:
        chu_hs = (ht.get("chu_so_huu") or ht.get("dd_ho_ten") or "").strip()      # người thực hiện thủ tục: chủ sở hữu (theo mẫu hồ sơ thực tế)
        _doan(d, f"Điều {so_dieu}: ", dam=True, gach=True, sau=10).add_run(f"Giao cho Ông/Bà {chu_hs.upper() or '……'} (người đại diện theo pháp luật) tiến hành các thủ tục cần thiết theo quy định của pháp luật.")
    elif bau_ct:
        dd = (ct_moi.get("ho_ten") or "").strip()
        _doan(d, f"Điều {so_dieu}: ", dam=True, gach=True, sau=10).add_run(f"Giao cho {_xung(ct_moi)} {dd.upper()} (Chủ tịch Hội đồng thành viên, người đại diện theo pháp luật) tiến hành các thủ tục đăng ký thay đổi cần thiết theo quy định của pháp luật.")
    else:
        _doan(d, f"Điều {so_dieu}: ", dam=True, gach=True, sau=10).add_run(f"Giao cho Ông/Bà {dd.upper() or '……'} (người đại diện theo pháp luật) tiến hành các thủ tục cần thiết theo quy định của pháp luật.")
    if la_hdtv:
        _doan(d, f"Điều {so_dieu + 1}: ", dam=True, gach=True, sau=10).add_run(
            "Các thành viên Hội đồng thành viên, người đại diện theo pháp luật của Công ty và các cá nhân, bộ phận có liên quan chịu trách nhiệm thi hành Quyết định này.")
    else:
        _doan(d, f"Điều {so_dieu + 1}: ", dam=True, gach=True, sau=10).add_run(f"Người đại diện theo pháp luật của công ty, {ten_co.lower()} công ty có trách nhiệm thi hành {loai_vb.capitalize()} này.")
    _doan(d, f"Điều {so_dieu + 2}: ", dam=True, gach=True, sau=10).add_run(f"{loai_vb.capitalize()} này có hiệu lực kể từ ngày ký.")
    tb = d.add_table(rows=1, cols=2)
    a, b = tb.rows[0].cells
    a.paragraphs[0].add_run("Nơi nhận:").bold = True
    a.paragraphs[0].runs[0].italic = True
    for t in (f"- Như Điều {so_dieu + 1} (để thực hiện);", "- Phòng ĐKKD (để đăng ký);", "- Lưu."):
        a.add_paragraph(t)
    pb = b.paragraphs[0]
    pb.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if la_hdtv:
        pb.add_run("TM. Hội đồng thành viên").bold = True
        pb = b.add_paragraph()
        pb.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pb.add_run("CHỦ TỊCH HỘI ĐỒNG THÀNH VIÊN").bold = True
    else:
        pb.add_run(chu).bold = True
    pb2 = b.add_paragraph()
    pb2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pb2.add_run("(Ký, ghi rõ họ và tên)").italic = True
    ct_ky = _tra_khoa_nguoi(du.get("thanh_vien"), du.get("chu_tich_moi")) if (la_hdtv and du.get("chu_tich_moi")) else None
    nguoi_ky, anh_ky = (ht.get("chu_so_huu") or "").strip(), (chu_ky or {}).get("chu_so_huu")
    if ct_ky and (ct_ky.get("ho_ten") or "").strip():                  # Chủ tịch HĐTV mới ký Quyết định (chữ ký lấy theo CCCD trong Kho chữ ký nếu người đó đã đồng ý)
        so = re.sub(r"\D", "", ct_ky.get("cccd") or "")
        nguoi_ky, anh_ky = ct_ky["ho_ten"].strip(), (chu_ky or {}).get("cccd:" + so) if len(so) >= 9 else None
    if not nguoi_ky and la_hdtv:
        # Chưa chọn Chủ tịch HĐTV (và không có chủ sở hữu): lấy người đại diện theo pháp luật (mới nếu đổi người đại diện, không thì hiện tại) —
        # Chủ tịch HĐTV thường kiêm người đại diện (Điều "Giao cho …" cũng ghi người này); người dùng kiểm tra/chọn lại Chủ tịch ở mục Thành viên nếu khác.
        dd_moi = ((du.get("dai_dien") or [{}])[0].get("ho_ten") or "").strip() if "dai_dien" in loai else ""
        nguoi_ky = dd_moi or (ht.get("dd_ho_ten") or "").strip()
        anh_ky = (chu_ky or {}).get("giam_doc") if (nguoi_ky and not dd_moi) else None      # ảnh chữ ký trong Kho chỉ của người đại diện HIỆN TẠI (đã đồng ý)
    if nguoi_ky:
        _dong_trong_ky(b)
        pk = b.add_paragraph()
        pk.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pk.add_run(nguoi_ky.upper()).bold = True
        _gan_chu_ky(pk, anh_ky)
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
    ben_a = _nguoi_ky_2tv(du, chu_ky)           # TNHH 1TV: Chủ tịch công ty; TNHH 2TV: Chủ tịch HĐTV (đúng bộ hồ sơ thực tế)
    lh = (dn.get("loai_hinh") or "").lower()
    if ("trách nhiệm hữu hạn" in lh and "dai_dien" not in set(du.get("loai") or [])
            and (ht.get("dd_ho_ten") or "").strip()):
        # TNHH (1 thành viên hay từ 2 thành viên) mà người đại diện (giám đốc) KHÔNG đổi — vd hồ sơ chỉ cập nhật thông tin thành viên/người đại diện, chuyển
        # nhượng vốn: Bên A vẫn là người đại diện hiện tại với đúng CHỨC DANH hiện tại (Giám đốc), không phải Chủ tịch. Chỉ khi ĐỔI người đại diện mới là
        # Chủ tịch HĐTV (công ty từ 2 thành viên) hoặc Chủ sở hữu công ty (1 thành viên).
        ben_a = ((ht.get("dd_chuc_danh") or "GIÁM ĐỐC").strip().upper(), ht["dd_ho_ten"].strip(), (chu_ky or {}).get("giam_doc"))
    if ben_a:
        _doan(d, f"Ông (Bà): {ben_a[1].upper()}")
        _doan(d, f"Chức danh: {ben_a[0]} của {ten}", sau=6)
    else:
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
    _dong_trong_ky(a)
    pa3 = a.add_paragraph()
    pa3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pa3.add_run((uq.get("ho_ten") or "").upper())
    _gan_chu_ky(pa3, (chu_ky or {}).get("ben_b"), 5.4, 2.5)      # bên nhận ủy quyền: nhỏ hơn một chút
    pb = b.paragraphs[0]
    pb.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pb.add_run("Bên ủy quyền")
    _dong_trong_ky(b)
    pb3 = b.add_paragraph()
    pb3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pb3.add_run((ben_a[1] if ben_a else (ht.get("dd_ho_ten") or "")).upper())
    _gan_chu_ky(pb3, ben_a[2] if ben_a else (chu_ky or {}).get("giam_doc"))
    _can_bang_hai_ben(tb)
    _giu_mot_trang(tb, 3)
    return d


def _dia_chi_day_du(so_nha, xa, tinh):
    return ", ".join(x.strip() for x in (so_nha, xa, tinh) if x and str(x).strip())




# ============================================================ GÓI HỒ SƠ
LOAI_THAY_DOI = {
    "cshhl": "Thông báo thay đổi thông tin về chủ sở hữu hưởng lợi",
    "ten": "Thay đổi tên doanh nghiệp", "dia_chi": "Thay đổi địa chỉ trụ sở chính", "von": "Thay đổi vốn điều lệ",
    "nganh": "Thay đổi ngành, nghề kinh doanh", "bo_sung": "Bổ sung, cập nhật thông tin đăng ký doanh nghiệp", "dai_dien": "Thay đổi người đại diện theo pháp luật (giám đốc)",
    "chu_so_huu": "Thay đổi chủ sở hữu công ty TNHH một thành viên (chủ sở hữu mới là cá nhân)",
    "thue": "Thông báo thay đổi thông tin đăng ký thuế",
    "cap_nhat": "Cập nhật thông tin (địa chỉ theo đơn vị hành chính mới, thông tin người đại diện pháp luật và thành viên) — mục B Mẫu 12",
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
        sau_tv, _t = tinh_thanh_vien_sau(du.get("thanh_vien"))
        if "một thành viên" in (dn.get("loai_hinh") or "").lower() or len(sau_tv) < 2:
            n = du.get("chu_so_huu_moi") or {}
            for k, ten in (("ho_ten", "họ tên"), ("ngay_sinh", "ngày sinh"), ("gioi_tinh", "giới tính"), ("cccd", "số định danh cá nhân")):
                if not (n.get(k) or "").strip():
                    th.append(f"Chủ sở hữu mới — {ten}")
        else:
            for x in sau_tv:
                for k, ten in (("ngay_sinh", "ngày sinh"), ("cccd", "số giấy tờ pháp lý"), ("von", "phần vốn góp")):
                    if not x.get(k):
                        th.append(f"Danh sách thành viên (Phụ lục I-6) — {x.get('ho_ten') or '?'}: thiếu {ten}")
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
    if _loai_can_quyet_dinh(du):
        kem.append("Quyết định/Nghị quyết của chủ sở hữu hoặc cấp có thẩm quyền của công ty về nội dung thay đổi (theo Điều lệ công ty) — phần mềm đã soạn bản nháp, cần ký.")
    kem.append("Văn bản ủy quyền (nếu người nộp hồ sơ không phải người đại diện theo pháp luật) kèm giấy tờ pháp lý của người được ủy quyền.")
    if "dai_dien" in loai:
        kem += ["Giấy tờ pháp lý (căn cước/hộ chiếu) của người đại diện theo pháp luật mới — chỉ cần khi không khai thác được qua số định danh cá nhân.",
                "Thông báo/biên bản chấm dứt chức danh của người đại diện cũ (nếu có).",
                "Nếu thông tin chủ sở hữu hưởng lợi cũng thay đổi: tick mục \"Thay đổi thông tin về chủ sở hữu hưởng lợi\" để phần mềm soạn thêm Mẫu số 10 (TT 121/2026) — chỉ đổi người đại diện thì không cần Mẫu số 10."]
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
            # Hàm này chạy trong LUỒNG của máy chủ web (không phải luồng chính) -> phải khởi tạo COM cho luồng này, nếu không Word báo
            # "(-2147221008, 'CoInitialize has not been called.')". Khởi tạo bằng đúng thư viện đang dùng và giải phóng sau khi xong.
            if trinh[1] == "win32com.client":
                import pythoncom
                import win32com.client as wc
                pythoncom.CoInitialize()
                huy_com = pythoncom.CoUninitialize
                tao = lambda: wc.DispatchEx("Word.Application")
            else:
                import comtypes
                import comtypes.client as cc
                comtypes.CoInitialize()
                huy_com = comtypes.CoUninitialize
                tao = lambda: cc.CreateObject("Word.Application")
            try:
                w = tao()
                try:
                    w.Visible = False
                    d = w.Documents.Open(src, ReadOnly=True)
                    d.SaveAs(out, FileFormat=17)          # 17 = wdFormatPDF
                    d.Close(False)
                finally:
                    try:
                        w.Quit()
                    except Exception:
                        pass
            finally:
                huy_com()
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
    toi = (duoi(y, 0.014, 0.15) + duoi(1 - y, 0.012, 0.11) + duoi(1 - x, 0.016, 0.17) + duoi(x, 0.006, 0.05) + duoi(1 - x, 0.06, 0.07))
    a *= (1 - np.clip(toi, 0, 0.32))[..., None]
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


def tao_ho_so(du, chu_ky=None, xuat_pdf=False):
    """du: dữ liệu (xem soan_mau12/13/15).
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
    du["dai_dien"] = [_chuan_dia_chi(x) for x in (du.get("dai_dien") or [])]
    tv = du.get("thanh_vien") or {}
    moi_tv = [x for x in tv.get("moi") or [] if (x.get("ho_ten") or "").strip()]
    if moi_tv and not (du.get("chu_so_huu_moi") or {}).get("ho_ten"):
        du["chu_so_huu_moi"] = moi_tv[0]                   # chủ sở hữu mới (Mẫu 15) = người đầu tiên trong danh sách thành viên mới
    du["chu_so_huu_moi"] = _chuan_dia_chi(du.get("chu_so_huu_moi"))
    if not (dn.get("ngay_lap") or "").strip():
        dn["ngay_lap"] = datetime.date.today().strftime("%d/%m/%Y")        # mặc định: ngày hiện tại
    ma = re.sub(r"\D", "", dn.get("ma_so") or "") or "DN"
    nguon = danh_sach_mau()
    ten_nguon = lambda n: nguon[n][1]
    tep, ds_file = [], []

    def them(ten_file, d, nhan, n):
        _bo_dong_trong_thua(d)                      # chỉ làm sạch văn bản ĐẦU RA (không đụng quy trình cắt mẫu từ Thông tư)
        tep.append((ten_file, _luu_bytes(d)))
        ds_file.append((nhan, ten_nguon(n)))
    if (loai & {"ten", "dia_chi", "von", "nganh", "bo_sung", "cap_nhat", "cshhl", "thue"}) or _doi_thanh_vien_nhieu_tv(du):
        them(f"Mau12_Giay_de_nghi_thay_doi_noi_dung_DKDN_{ma}.docx", soan_mau12(du, chu_ky), "Mẫu số 12 — Giấy đề nghị đăng ký thay đổi nội dung ĐKDN", 12)
    if "cshhl" in loai:                          # Mẫu 10 CHỈ khi người dùng tick thay đổi chủ sở hữu hưởng lợi (đổi người đại diện không kèm Mẫu 10)
        them(f"Mau10_Danh_sach_chu_so_huu_huong_loi_{ma}.docx", soan_mau10(du, chu_ky), "Mẫu số 10 — Danh sách chủ sở hữu hưởng lợi (phần mềm điền theo danh sách đã chọn)", 10)
    if "dai_dien" in loai:
        them(f"Mau13_Giay_de_nghi_thay_doi_nguoi_dai_dien_theo_phap_luat_{ma}.docx", soan_mau13(du, chu_ky), "Mẫu số 13 — Giấy đề nghị đăng ký thay đổi người đại diện theo pháp luật", 13)
    if "chu_so_huu" in loai:
        sau_tv, _tong = tinh_thanh_vien_sau(du.get("thanh_vien"))
        la_1tv = "một thành viên" in (dn.get("loai_hinh") or "").lower()
        if la_1tv or len(sau_tv) < 2:
            them(f"Mau15_Giay_de_nghi_thay_doi_chu_so_huu_{ma}.docx", soan_mau15(du), "Mẫu số 15 — Giấy đề nghị đăng ký thay đổi chủ sở hữu công ty TNHH một thành viên", 15)
        else:
            tep.append((f"PhuLuc_I-6_Danh_sach_thanh_vien_{ma}.docx", _luu_sach(soan_phu_luc_i6(du, chu_ky))))
            for stt, (ban, mua) in enumerate(_cac_cap_chuyen_nhuong(du.get("thanh_vien")), 1):
                tep.append((f"Hop_dong_chuyen_nhuong_phan_von_gop_{stt}_{ma}.docx", _luu_sach(soan_hop_dong_chuyen_nhuong(du, ban, mua, chu_ky))))
                ds_file.append((f"Hợp đồng chuyển nhượng phần vốn góp: {ban.get('ho_ten') or '?'} → {mua.get('ho_ten') or '?'} (phần mềm soạn theo mẫu)", "mẫu do người dùng cung cấp"))
            ds_file.append(("Phụ lục I-6 — Danh sách thành viên công ty TNHH hai thành viên trở lên (phần mềm soạn theo mẫu)", "Thông tư 68/2025/TT-BTC (Phụ lục I-6)"))
    canh_bao = []
    can_qd = _loai_can_quyet_dinh(du)
    if (can_qd or du.get("tao_uy_quyen")) and not (ht.get("ngay_cap_gcn") or "").strip():
        canh_bao.append("Chưa có ngày cấp Giấy chứng nhận ĐKDN (mục 1b) — Quyết định (ngày thông qua Điều lệ) và Giấy ủy quyền để trống ngày.")
    if can_qd:                                   # tự soạn khi có thay đổi cần quyết định; chỉ bổ sung/cập nhật, hoặc chỉ chuyển nhượng vốn/đổi thành viên (không đổi GĐ/Chủ tịch) thì không
        _, loai_vb, ten_co = _chu_the_quyet_dinh(dn.get("loai_hinh"))
        tep.append((f"Quyet_dinh_{'cua_hoi_dong_thanh_vien' if ten_co == 'Hội đồng thành viên' and loai_vb == 'QUYẾT ĐỊNH' else ('cua_chu_so_huu' if loai_vb == 'QUYẾT ĐỊNH' else 'Nghi_quyet')}_{ma}.docx", _luu_sach(soan_quyet_dinh(du, chu_ky))))
        ds_file.append((f"{loai_vb.capitalize()} của {ten_co} về việc thay đổi nội dung đăng ký doanh nghiệp (phần mềm soạn theo mẫu)", "mẫu do người dùng cung cấp"))
        if "một thành viên" not in (dn.get("loai_hinh") or "").lower():
            canh_bao.append(f"{loai_vb.capitalize()} soạn theo thẩm quyền của {ten_co} (ký bởi Chủ tịch Hội đồng thành viên thay mặt) — hãy đối chiếu Điều lệ công ty (thể thức, tỷ lệ biểu quyết, biên bản họp nếu cần).")
    if du.get("tao_uy_quyen"):
        tep.append((f"Giay_uy_quyen_nop_ho_so_{ma}.docx", _luu_sach(soan_giay_uy_quyen(du, chu_ky))))
        ds_file.append(("Giấy ủy quyền nộp hồ sơ và nhận kết quả đăng ký doanh nghiệp (phần mềm soạn theo mẫu)", "mẫu do người dùng cung cấp"))
        uq = du.get("uy_quyen") or {}
        for k, nhan in (("ho_ten", "họ tên"), ("ngay_sinh", "ngày sinh"), ("so_giay_to", "số chứng thực/CCCD"), ("ngay_cap", "ngày cấp"), ("noi_cap", "nơi cấp"), ("cho_o", "chỗ ở hiện tại")):
            if not (uq.get(k) or "").strip():
                canh_bao.append(f"Giấy ủy quyền — bên nhận ủy quyền thiếu {nhan}")
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
                if ten.lower().endswith(".docx") and not ten.startswith("00_"):
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
