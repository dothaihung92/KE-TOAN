# -*- coding: utf-8 -*-
"""Hồ sơ CHUYỂN ĐỔI LOẠI HÌNH doanh nghiệp (bản NHÁP): công ty TNHH 2 thành viên trở lên <-> TNHH 1 thành viên <-> công ty cổ phần.

Hồ sơ gồm: (1) Giấy đề nghị đăng ký doanh nghiệp theo biểu mẫu mới Thông tư 121/2026/TT-BTC (Mẫu số 2 = TNHH 1 thành viên, Mẫu số 3 = TNHH 2 thành viên trở lên,
Mẫu số 4 = công ty cổ phần) với tình trạng thành lập "chuyển đổi loại hình doanh nghiệp"; (2) Điều lệ công ty sau chuyển đổi; (3) Hợp đồng chuyển nhượng phần vốn góp
(khi có chuyển nhượng); (4) Mẫu số 10 — Danh sách chủ sở hữu hưởng lợi; (5) Quyết định/Nghị quyết chuyển đổi loại hình; kèm Phụ lục danh sách thành viên (Mẫu 6) hoặc
danh sách cổ đông sáng lập (Mẫu 7) tùy loại hình sau chuyển đổi.
Phần mềm chỉ điền thông tin người dùng đã nhập/đã gom; ô thiếu giữ dấu chấm; KHÔNG ký thay. Luật sư/kế toán rà soát trước khi nộp.
"""
import re
import copy

from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

import gpkd_soan as g
import gpkd_dieu_le as dl

TEN_LOAI = {"1tv": "công ty trách nhiệm hữu hạn một thành viên", "2tv": "công ty trách nhiệm hữu hạn hai thành viên trở lên", "cp": "công ty cổ phần"}
MAU_TT121 = {"1tv": 2, "2tv": 3, "cp": 4}
_CHAM = "……"


def loai_tu_ten(lh):
    t = (lh or "").lower()
    if "cổ phần" in t:
        return "cp"
    if "một thành viên" in t or "1 thành viên" in t or "1tv" in t:
        return "1tv"
    if "hai thành viên" in t or "2 thành viên" in t or "2tv" in t or "trách nhiệm hữu hạn" in t:
        return "2tv"
    return ""


def _v(x, mac_dinh=_CHAM):
    t = str(x or "").strip()
    return t if t else mac_dinh


def _so(n):
    return f"{int(n):,}".replace(",", ".")


def _tien(n):
    return (f"{int(n):,}".replace(",", ".") + " đồng") if n else _CHAM


def _ty_le_chuoi(von, tong):
    if not von or not tong:
        return ""
    return f"{von * 100 / tong:.3f}".rstrip("0").rstrip(".").replace(".", ",") + "%"


def _ten_theo_loai(ten, den):
    """Đổi tiền tố tên công ty theo loại hình mới (TNHH <-> cổ phần); giữ nguyên nếu không nhận ra."""
    t = (ten or "").strip().upper()
    if den == "cp":
        return re.sub(r"^CÔNG TY\s+(TNHH|TRÁCH NHIỆM HỮU HẠN)\b", "CÔNG TY CỔ PHẦN", t)
    return re.sub(r"^CÔNG TY\s+CỔ PHẦN\b", "CÔNG TY TNHH", t)


def _ngay_chu_ky(dn):
    mm = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", g._ngay_dd_mm_yyyy(dn.get("ngay_lap") or ""))
    return f"Ngày {int(mm.group(1))} tháng {int(mm.group(2))} năm {mm.group(3)}" if mm else "Ngày …… tháng …… năm ……"


def _chuan(x):
    return " ".join(str(x or "").upper().split())


def _tim_nguoi(du, ten):
    """Thông tin chi tiết của người tên `ten` trong các danh sách thành viên/cổ đông đã nhập (hiện tại + mới)."""
    if not _chuan(ten):
        return {}
    tv = du.get("thanh_vien") or {}
    for x in list(tv.get("moi") or []) + list(tv.get("ht") or []):
        if _chuan(x.get("ho_ten")) == _chuan(ten):
            return dict(x)
    return {}


def thong_tin_sau(du):
    """Gom thông tin công ty SAU chuyển đổi: giá trị mới nếu người dùng tick thay đổi (tên/địa chỉ/vốn/ngành/người đại diện) và đã nhập, không thì giữ như hiện tại."""
    dn = dict(du.get("dn") or {})
    ht = dict(du.get("hien_tai") or {})
    loai = set(du.get("loai") or [])
    cd = dict(du.get("chuyen_doi") or {})
    den = cd.get("den") if cd.get("den") in TEN_LOAI else "1tv"
    tu = cd.get("tu") if cd.get("tu") in TEN_LOAI else loai_tu_ten(dn.get("loai_hinh"))
    ten_cu = (dn.get("ten") or "").strip().upper()
    t = du.get("ten") or {}
    if "ten" in loai and (t.get("viet") or "").strip():
        ten = t["viet"].strip().upper()
    else:
        ten = _ten_theo_loai(ten_cu, den)
    ten_vt = (t.get("viet_tat") or "").strip() if "ten" in loai else ""
    ten_nn = (t.get("nuoc_ngoai") or "").strip() if "ten" in loai else ""
    # địa chỉ
    a_ht = dict(du.get("ht_dia_chi") or {})
    if not any((a_ht.get(k) or "").strip() for k in ("so_nha", "xa", "tinh")):
        a_ht = g._tach_dia_chi(ht.get("dia_chi"))
    a_moi = du.get("dia_chi") or {}
    a = dict(a_moi) if ("dia_chi" in loai and any((a_moi.get(k) or "").strip() for k in ("so_nha", "xa", "tinh"))) else a_ht
    dia_chi = g._dia_chi_day_du(a.get("so_nha"), a.get("xa"), a.get("tinh")) + (", Việt Nam" if any(a.get(k) for k in ("so_nha", "xa", "tinh")) else "")
    # ngành nghề
    nganh = [dict(x) for x in (du.get("ht_nganh") or []) if (x.get("ma") or x.get("ten")) and not x.get("mau")]    # ngành bị tô màu (mã đã đổi/không còn) thì loại ra
    ng = du.get("nganh") or {}
    if "nganh" in loai:
        bo = {str(x.get("ma") or "").strip() for x in (ng.get("bo") or []) if (x.get("ma") or "").strip()}
        nganh = [x for x in nganh if str(x.get("ma") or "").strip() not in bo]
        for x in ng.get("sua") or []:
            for y in nganh:
                if str(y.get("ma") or "").strip() == str(x.get("ma") or "").strip():
                    y.update({k: x[k] for k in ("ten", "chi_tiet") if x.get(k)})
        nganh += [dict(x) for x in (ng.get("them") or []) if (x.get("ma") or x.get("ten"))]
    gop, thu_tu = {}, []                                   # gộp trùng mã: dòng sau (nhập ở mục Thay đổi ngành) ghi đè dòng trước
    for x in nganh:
        k = str(x.get("ma") or "").strip() or str(x.get("ten") or "")
        if k not in gop:
            thu_tu.append(k)
            gop[k] = x
        else:
            gop[k].update({a: b for a, b in x.items() if b})
    nganh = [gop[k] for k in thu_tu]
    try:                                                   # tên ngành trống (cổng/nút cũ không lấy được) -> tra theo mã ở danh mục ngành cấp 4
        import json, os
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "gpkd", "nganh_cap4_QD27_2018.json"), encoding="utf-8") as f:
            dm = {str(m): t for m, t in json.load(f)}
        for x in nganh:
            if not (x.get("ten") or "").strip() and dm.get(str(x.get("ma") or "").strip()):
                x["ten"] = dm[str(x["ma"]).strip()]
    except Exception:
        pass
    chinh = str(cd.get("nganh_chinh") or "").strip()
    for x in nganh:
        if chinh and str(x.get("ma") or "").strip() == chinh:
            x["chinh"] = True
    # thành viên/chủ sở hữu/cổ đông sau chuyển đổi
    sau, tong = g.tinh_thanh_vien_sau(du.get("thanh_vien"))
    sau = [g._chuan_dia_chi(x) for x in sau]
    von_moi = g.so_nguyen((du.get("von") or {}).get("moi")) if "von" in loai else None
    von = von_moi or tong or g.so_nguyen(du.get("ht_von"))
    if len(sau) == 1 and not sau[0].get("von") and von:
        sau[0]["von"], sau[0]["ty_le"] = von, "100%"
    # người đại diện theo pháp luật
    dd = dict((du.get("dai_dien") or [{}])[0]) if "dai_dien" in loai and ((du.get("dai_dien") or [{}])[0].get("ho_ten") or "").strip() else \
        {"ho_ten": (ht.get("dd_ho_ten") or "").strip(), "chuc_danh": (ht.get("dd_chuc_danh") or "").strip()}
    kh = _tim_nguoi(du, dd.get("ho_ten"))
    for k, v in kh.items():
        if k in ("ngay_sinh", "gioi_tinh", "cccd", "ngay_cap", "noi_cap", "dan_toc", "quoc_tich", "dia_chi", "so_nha", "xa", "tinh", "quoc_gia", "dien_thoai", "email") and v and not str(dd.get(k) or "").strip():
            dd[k] = v
    dd = g._chuan_dia_chi(dd)
    # chủ tịch
    ct = ""
    if du.get("chu_tich_moi"):
        x = g._tra_khoa_nguoi(du.get("thanh_vien"), du.get("chu_tich_moi"))
        ct = ((x or {}).get("ho_ten") or "").strip()
    if not ct and den == "1tv" and sau:
        ct = (sau[0].get("ho_ten") or "").strip()
    gd = dd.get("ho_ten") if re.search(r"giám đốc", (dd.get("chuc_danh") or "").lower()) else ""
    tt = {"loai_moi": den, "loai_cu": tu, "ten": ten, "ten_cu": ten_cu, "ten_viet_tat": ten_vt, "ten_nuoc_ngoai": ten_nn, "dia_chi": dia_chi, "a": a,
          "nganh": nganh, "von": von, "sau": sau, "nguoi_dd": dd, "chu_tich": ct, "giam_doc": gd, "ngay_ky": _ngay_chu_ky(dn),
          "chu_so_huu": sau if den == "1tv" else [], "thanh_vien": sau if den == "2tv" else [], "co_dong": sau if den == "cp" else [],
          "menh_gia": g.so_nguyen(cd.get("menh_gia")) or 10000, "thoi_han": (cd.get("thoi_han") or "").strip(), "so_qd": (dn.get("so_vb") or "").strip(),
          "ngay_dieu_le": (ht.get("ngay_dieu_le") or "").strip()}
    tt["can_cu_chuyen_doi"] = f"Quyết định số {_v(tt['so_qd'])} ngày {g._ngay_dd_mm_yyyy(dn.get('ngay_lap')) or _CHAM} về việc chuyển đổi loại hình doanh nghiệp"
    return tt


# ====================================================================================================== GIẤY ĐỀ NGHỊ (MẪU 2 / 3 / 4)
def _o_vuong(p, nhan_re, neo=0):
    """Đánh dấu ☒ vào ô vuông □ đứng ngay sau nhãn (trong cùng đoạn). True nếu đã đánh."""
    t = g._van(p)
    m = re.search(nhan_re, t[neo:])
    if not m:
        return False
    k = t.find("□", neo + m.end())
    if k < 0:
        return False
    g._thay_khoang(p, k, k + 1, "☒")
    return True


def _tick_bang(bang, nhan_re):
    """Bảng 'nhãn | ô vuông': đánh ☒ vào ô □ cùng hàng với nhãn."""
    for r in bang.rows:
        cells = r.cells
        if any(re.search(nhan_re, c.text) for c in cells):
            for c in cells:
                for p in c.paragraphs:
                    for run in p.runs:
                        if "□" in run.text:
                            run.text = run.text.replace("□", "☒", 1)
                            return True
    return False


def _dien_nguoi(m, n, lo, hi, nhan_ten):
    g_ = lambda k: (n.get(k) or "").strip()
    m.dien(nhan_ten, g_("ho_ten").upper(), lo, hi)
    p = m.tim(r"Ngày, tháng, năm sinh", lo, hi)
    if p is not None and g_("ngay_sinh"):
        g.dien_cham(p, r"Ngày, tháng, năm sinh", g._ngay_dd_mm_yyyy(g_("ngay_sinh")), g._NGAY3)
    m.dien(r"Giới tính", g_("gioi_tinh"), lo, hi)
    m.dien(r"Số định danh cá nhân", g_("cccd"), lo, hi)
    if g_("chuc_danh"):
        m.dien(r"Chức danh", g_("chuc_danh"), lo, hi)
    m.dien(r"Số nhà/phòng, ngách/hẻm, ngõ/kiệt, đường/phố/đại lộ, tổ/xóm/ấp/thôn", g_("so_nha"), lo, hi)
    m.dien(r"Xã/Phường/Đặc khu", g_("xa"), lo, hi)
    m.dien(r"Tỉnh/Thành phố trực thuộc trung ương", g_("tinh"), lo, hi)
    m.dien(r"Quốc gia", g_("quoc_gia") or ("Việt Nam" if (g_("so_nha") or g_("xa") or g_("tinh")) else ""), lo, hi)
    m.dien(r"Điện thoại \(nếu có\)", g_("dien_thoai"), lo, hi)
    m.dien(r"Thư điện tử \(nếu có\)", g_("email"), lo, hi)


def _xoa_den_truoc(m, bat_dau_re, ket_thuc_re, tu=0):
    """Xoá các phần tử từ đoạn khớp bat_dau_re tới TRƯỚC đoạn khớp ket_thuc_re (tìm từ vị trí tu). True nếu xoá."""
    a = m.chi_so(bat_dau_re, tu)
    if a is None:
        return False
    b = m.chi_so(ket_thuc_re, a + 1)
    if b is None or b <= a:
        return False
    m.xoa_phan(a, b)
    return True


def soan_giay_de_nghi(du, tt, chu_ky=None):
    den = tt["loai_moi"]
    d = g.cat_mau(MAU_TT121[den])
    m = g._Mau(d)
    dn = du.get("dn") or {}
    loai = set(du.get("loai") or [])
    nguoi = tt["nguoi_dd"]
    sau = tt["sau"]
    # --- người ký + người đăng ký ("Tôi là"): người đại diện theo pháp luật sau chuyển đổi (chủ sở hữu nếu 1TV và chưa có người đại diện)
    ky = dict(nguoi)
    if not (ky.get("ho_ten") or "").strip() and den == "1tv" and sau:
        ky = dict(sau[0])
    i_toi = m.chi_so(r"^Tôi là")
    i_dang_ky = m.chi_so(r"^Đăng ký công ty")
    g._dien_dau(m, dn, i_toi if i_toi is not None else 6)
    hi_ky = i_dang_ky if i_dang_ky is not None else len(m.ch)
    _dien_nguoi(m, ky, i_toi or 0, hi_ky, r"Tôi là\d?")
    # --- 1. Tình trạng thành lập: chuyển đổi loại hình
    i_tt = m.chi_so(r"^1\.\s*Tình trạng thành lập")
    if i_tt is not None:
        for c in m.ch[i_tt + 1:i_tt + 4]:
            if c.tag == qn("w:tbl"):
                _tick_bang(g.Table(c, d._body), r"chuyển đổi loại hình doanh nghiệp")
                break
    p = m.tim(r"^- Lý do chuyển đổi loại hình doanh nghiệp")
    if p is not None:
        t = g._van(p)
        k = t.index(":") + 1 if ":" in t else len(t)
        g._thay_khoang(p, k, len(t), f" (Quyết định {_v(tt['so_qd'], '……')} của {tt['ten_cu'] or _CHAM})")
    i_dn = m.chi_so(r"^- Thông tin về các doanh nghiệp bị chia")
    i_hkd = m.chi_so(r"^- Thông tin về hộ kinh doanh được chuyển đổi")
    if i_dn is not None:
        hi = i_hkd if i_hkd is not None else i_dn + 5
        m.dien(r"^Tên doanh nghiệp \(ghi bằng chữ in hoa\)", tt["ten_cu"], i_dn, hi)
        m.dien(r"^Mã số doanh nghiệp/Mã số thuế", dn.get("ma_so"), i_dn, hi)
    # bỏ phần hộ kinh doanh + cơ sở bảo trợ xã hội (không áp dụng khi chuyển đổi loại hình doanh nghiệp)
    _xoa_den_truoc(m, r"^- Thông tin về hộ kinh doanh được chuyển đổi", r"^- Doanh nghiệp thực hiện dự án đầu tư được đăng ký đầu tư theo thủ tục đầu tư đặc biệt")
    # --- 2. Tên công ty; 3. Địa chỉ
    i2, i3, i4 = m.chi_so(r"^2\.\s*Tên công ty"), m.chi_so(r"^3\.\s*Địa chỉ trụ sở chính"), m.chi_so(r"^4\.\s*Ngành, nghề")
    if i2 is not None and i3 is not None:
        m.dien(r"Tên công ty viết bằng tiếng Việt", tt["ten"], i2, i3)
        m.dien(r"Tên công ty viết bằng tiếng nước ngoài", tt["ten_nuoc_ngoai"], i2, i3)
        m.dien(r"Tên công ty viết tắt", tt["ten_viet_tat"], i2, i3)
    if i3 is not None and i4 is not None:
        a = tt["a"]
        m.dien(r"Số nhà/phòng, ngách/hẻm, ngõ/kiệt, đường/phố/đại lộ, tổ/xóm/ấp/thôn", a.get("so_nha"), i3, i4)
        m.dien(r"Xã/Phường/Đặc khu", a.get("xa"), i3, i4)
        m.dien(r"Tỉnh/Thành phố trực thuộc trung ương", a.get("tinh"), i3, i4)
        m.dien(r"Điện thoại", a.get("dien_thoai"), i3, i4)
        m.dien(r"Số fax \(nếu có\)", a.get("fax"), i3, i4)
        m.dien(r"Thư điện tử \(nếu có\)", a.get("email"), i3, i4)
        m.dien(r"Website \(nếu có\)", a.get("website"), i3, i4)
        for c in m.ch[i3:i4]:
            if c.tag == qn("w:p") and re.search(r"Doanh nghiệp có Giấy chứng nhận quyền sử dụng đất", g._chu(c)):
                _o_vuong(g.Paragraph(c, d._body), r"Không")
    # --- 4. Ngành nghề (bảng ngay sau tiêu đề)
    if i4 is not None and tt["nganh"] and i4 + 1 < len(m.ch) and m.ch[i4 + 1].tag == qn("w:tbl"):
        g._dien_bang_nganh(m.bang(i4 + 1), tt["nganh"], ["ten", "ma", "chinh"])
    # --- phần riêng từng mẫu
    i_von = m.chi_so(r"^\d+\.\s*Vốn điều lệ")
    i_nguon = m.chi_so(r"^\d+\.\s*Nguồn vốn điều lệ")
    von = tt["von"]
    if den == "1tv":
        i5 = m.chi_so(r"^5\.\s*Chủ sở hữu")
        i5b = m.chi_so(r"^b\)\s*Đối với chủ sở hữu là tổ chức")
        i_mh = m.chi_so(r"^- Mô hình tổ chức công ty")
        cs = sau[0] if sau else {}
        if i5 is not None and i5b is not None:
            _dien_nguoi(m, cs, i5, i5b, r"Họ, chữ đệm và tên chủ sở hữu")
        if i5b is not None and i_mh is not None and i5b < i_mh:
            m.xoa_phan(i5b, i_mh)                                   # chủ sở hữu là cá nhân: bỏ phần chủ sở hữu là tổ chức
        i_mh = m.chi_so(r"^- Mô hình tổ chức công ty")
        if i_mh is not None and i_mh + 1 < len(m.ch) and m.ch[i_mh + 1].tag == qn("w:tbl"):
            _tick_bang(m.bang(i_mh + 1), r"Chủ tịch công ty, Giám đốc")            # chủ sở hữu là CÁ NHÂN: Chủ tịch công ty + Giám đốc/Tổng giám đốc (Luật Doanh nghiệp)
    i_von = m.chi_so(r"^\d+\.\s*Vốn điều lệ")
    i_nguon = m.chi_so(r"^\d+\.\s*Nguồn vốn điều lệ")
    if i_von is not None and i_nguon is not None and von:
        m.dien(r"Vốn điều lệ \(bằng số; VNĐ\)", f"{von:,}".replace(",", ".") + " VNĐ", i_von, i_nguon)
        chu = g.doc_so_vn(von)
        m.dien(r"Vốn điều lệ \(bằng chữ; VNĐ\)", chu[:1].upper() + chu[1:] + " đồng", i_von, i_nguon)
        for c in m.ch[i_von:i_nguon]:
            if c.tag == qn("w:p") and re.search(r"Có hiển thị thông tin về giá trị tương đương", g._chu(c)):
                nxt = c.getnext()
                if nxt is not None and nxt.tag == qn("w:p") and re.search(r"Có\s*□\s*Không", g._chu(nxt)):
                    _o_vuong(g.Paragraph(nxt, d._body), r"Không")
                else:
                    _o_vuong(g.Paragraph(c, d._body), r"Không")
                break
    # nguồn vốn (vốn tư nhân) + tài sản góp vốn (đồng Việt Nam)
    if von:
        so = f"{von:,}".replace(",", ".")
        for tb in d.tables:
            tx = "".join(c.text for c in tb.rows[0].cells)
            if "Loại nguồn vốn" in tx:
                for r in tb.rows:
                    if r.cells[0].text.strip() == "Vốn tư nhân" or r.cells[0].text.strip().startswith("Tổng cộng"):
                        g._dat_o(r.cells[1], so)
                        g._dat_o(r.cells[2], "100")
            elif "Tài sản góp vốn" in tx and len(tb.rows) > 3:
                for r in tb.rows:
                    t0 = r.cells[1].text.strip() if len(r.cells) > 1 else ""
                    if t0.startswith("Đồng Việt Nam") or r.cells[0].text.strip().startswith("Tổng số"):
                        g._dat_o(r.cells[-2], so)
                        g._dat_o(r.cells[-1], "100")
    # cổ phần (Mẫu 4)
    if den == "cp":
        menh = tt["menh_gia"]
        p = m.tim(r"^Mệnh giá cổ phần \(VNĐ\)")
        if p is not None:
            g.dien_cham(p, r"Mệnh giá cổ phần \(VNĐ\)", f"{menh:,}".replace(",", "."))
        if von:
            sl = von // menh
            for tb in d.tables:
                tx = "".join(c.text for c in tb.rows[0].cells)
                if "Loại cổ phần" in tx and "Giá trị" in tx:
                    for r in tb.rows:
                        if "Cổ phần phổ thông" in r.cells[1].text:
                            g._dat_o(r.cells[2], f"{sl:,}".replace(",", "."))
                            g._dat_o(r.cells[3], f"{von:,}".replace(",", "."))
                            g._dat_o(r.cells[4], "100")
                elif "Loại cổ phần được quyền chào bán" in tx:
                    for r in tb.rows:
                        if "Cổ phần phổ thông" in r.cells[1].text:
                            g._dat_o(r.cells[2], f"{sl:,}".replace(",", "."))
    # --- Người đại diện theo pháp luật
    i_dd = m.chi_so(r"^\d+\.\s*Người đại diện theo pháp luật")
    i_thue = m.chi_so(r"^\d+\.\s*Thông tin đăng ký thuế")
    if i_dd is not None and i_thue is not None:
        _dien_nguoi(m, nguoi, i_dd, i_thue, r"Họ, chữ đệm và tên")
    # --- thông tin đăng ký thuế (chỉ ô có dữ liệu)
    i_bh = m.chi_so(r"^\d+\.\s*Thông tin về việc đóng bảo hiểm xã hội")
    if i_thue is not None:
        hi_thue = i_bh if i_bh is not None else len(m.ch)
        du_t = dict(du)
        du_t["loai"] = [x for x in (du.get("loai") or []) if x not in ("dia_chi",)]
        if (du.get("thue") or {}).get("cung_dia_chi") in (True, "1", 1, "true"):
            du_t["thue"] = dict(du.get("thue") or {}, **{k: v for k, v in (("tt_so_nha", tt["a"].get("so_nha")), ("tt_xa", tt["a"].get("xa")), ("tt_tinh", tt["a"].get("tinh"))) if v})
        if nguoi.get("ho_ten") and not ((du.get("thue") or {}).get("gd_ho_ten") or "").strip():
            du_t["thue"] = dict(du_t.get("thue") or {}, **{"gd_" + k: v for k, v in (("ho_ten", nguoi.get("ho_ten") if tt["giam_doc"] else ""), ("ngay_sinh", nguoi.get("ngay_sinh")),
                                                                                       ("gioi_tinh", nguoi.get("gioi_tinh")), ("cccd", nguoi.get("cccd")), ("dien_thoai", nguoi.get("dien_thoai"))) if v})
        g._dien_thong_tin_thue(m, du_t, (i_thue, hi_thue))
    # --- bảo hiểm xã hội: "Không kê khai trong trường hợp thành lập doanh nghiệp trên cơ sở chuyển đổi loại hình doanh nghiệp" (chú thích Mẫu 2/3/4 TT 121/2026) -> bỏ mục
    if i_bh is not None:
        i_cshhl = m.chi_so(r"^\d+\.\s*Thông tin về chủ sở hữu hưởng lợi", i_bh)
        if i_cshhl is not None:
            m.xoa_phan(i_bh, i_cshhl)
    # --- chữ ký
    ten_ky = (ky.get("ho_ten") or "").strip()
    for tb in d.tables:
        c = next((c for r in tb.rows for c in r.cells if "NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT/" in c.text), None)
        if c is not None:
            tieu_de = c.text.split("(Ký")[0].strip().replace("\n", " ")
            tieu_de = tieu_de.replace("/CHỦ TỊCH", "/\nCHỦ TỊCH", 1)
            anh = None
            ck = chu_ky or {}
            so = re.sub(r"\D", "", ky.get("cccd") or "")
            if len(so) >= 9:
                anh = ck.get("cccd:" + so)
            if not anh and _chuan(ten_ky) and _chuan(ten_ky) == _chuan((du.get("hien_tai") or {}).get("dd_ho_ten")):
                anh = ck.get("giam_doc")
            if ten_ky:
                g._khoi_ky(c, tieu_de, ten_ky, anh)
            g._giu_mot_trang(tb)
            break
    # --- bỏ phụ lục cam kết nhà đầu tư nước ngoài (không áp dụng) + dòng "Xin gửi kèm cam kết…"
    i_pl = m.chi_so(r"^Phụ lục\s*$")
    if i_pl is None:
        i_pl = m.chi_so(r"^Phụ lục")
    if i_pl is not None:
        m.xoa_phan(i_pl, len(m.ch))
    i_xin = m.chi_so(r"^Xin gửi kèm cam kết của nhà đầu tư nước ngoài")
    if i_xin is not None:
        m.xoa_phan(i_xin, i_xin + 1)
    g._bo_ngoac_kinh_gui(m)
    g._lam_sach_mau(m)
    return d


# ====================================================================================================== QUYẾT ĐỊNH / NGHỊ QUYẾT CHUYỂN ĐỔI
def _xung(n):
    return "Bà" if (n.get("gioi_tinh") or "").strip().lower() in ("nữ", "nu", "female") else "Ông"


def _khoi_ca_nhan(d, n, nhan_ten):
    g_ = lambda k: (n.get(k) or "").strip()
    g._doan(d, f"{nhan_ten} (ghi bằng chữ in hoa): {_v(g_('ho_ten').upper())}\t\tGiới tính: {_v(g_('gioi_tinh'))}", sau=0)
    g._doan(d, f"Sinh ngày: {_v(g._ngay_dd_mm_yyyy(g_('ngay_sinh')))}\t\tDân tộc: {_v(g_('dan_toc'), 'Kinh')}\t\tQuốc tịch: {_v(g_('quoc_tich'), 'Việt Nam')}", sau=4)
    g._doan(d, "Loại giấy tờ pháp lý cá nhân:", sau=2)
    g._bang_loai_giay_to(d, g_("cccd"))
    g._doan(d, f"Số giấy tờ pháp lý cá nhân: {_v(g_('cccd'))}", sau=0)
    g._doan(d, f"Ngày cấp: {_v(g._ngay_dd_mm_yyyy(g_('ngay_cap')))}", sau=0)
    g._doan(d, f"Nơi cấp: {_v(g_('noi_cap'))}", sau=0)
    g._doan(d, "Ngày hết hạn (nếu có):", sau=0)
    dc = g._dia_chi_nguoi(n)
    g._doan(d, f"Địa chỉ thường trú: {_v(dc)}", sau=0)
    g._doan(d, f"Địa chỉ liên lạc: {_v(dc)}", sau=6)


def _bang_nganh_docx(d, nganh):
    tb = d.add_table(rows=1, cols=4)
    tb.style = "Table Grid"
    for i, t in enumerate(["STT", "Tên ngành", "Mã ngành", "Ngành, nghề kinh doanh chính (đánh dấu X để chọn một trong các ngành đã kê khai)"]):
        c = tb.rows[0].cells[i]
        c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        c.paragraphs[0].add_run(t)
    for i, n in enumerate(nganh or [], 1):
        r = tb.add_row()
        r.cells[0].paragraphs[0].add_run(str(i))
        r.cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        r.cells[1].paragraphs[0].add_run((n.get("ten") or "").strip())
        ct = (n.get("chi_tiet") or "").strip()
        if ct:
            r.cells[1].add_paragraph().add_run(ct if re.match(r"(?i)chi tiết\s*:", ct) else "Chi tiết: " + ct).italic = True
        r.cells[2].paragraphs[0].add_run(str(n.get("ma") or ""))
        r.cells[2].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        r.cells[3].paragraphs[0].add_run("X" if n.get("chinh") else "")
        r.cells[3].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    g._doan(d, "", sau=2)


def soan_quyet_dinh(du, tt, chu_ky=None):
    """Quyết định (HĐTV/chủ sở hữu) hoặc Nghị quyết (ĐHĐCĐ) về việc chuyển đổi loại hình doanh nghiệp — theo mẫu hồ sơ người dùng cung cấp."""
    dn = dict(du.get("dn") or {})
    tu, den = tt["loai_cu"], tt["loai_moi"]
    lh_cu = TEN_LOAI.get(tu) or (dn.get("loai_hinh") or "loại hình hiện tại")
    lh_moi = TEN_LOAI[den]
    chu_the_hoa, loai_vb, chu_the = g._chu_the_quyet_dinh(dn.get("loai_hinh") or TEN_LOAI.get(tu, ""))
    ky = g._nguoi_ky_2tv(du, chu_ky) if tu == "2tv" else None
    ten_cu = tt["ten_cu"] or _CHAM
    d = g._van_ban_moi()
    g._bang_quoc_hieu(d, dict(dn, ten=tt["ten_cu"]), tt["so_qd"])
    g._doan(d, loai_vb, dam=True, can="giua", sau=0)
    g._doan(d, "Về việc chuyển đổi loại hình doanh nghiệp", dam=True, can="giua", sau=10)
    g._doan(d, chu_the_hoa, dam=True, can="giua", sau=8)
    g._doan(d, "- Căn cứ Luật Doanh nghiệp số 59/2020/QH14 được Quốc hội thông qua ngày 17 tháng 06 năm 2020 (đã được sửa đổi, bổ sung);", can="deu", sau=4)
    g._doan(d, f"- Căn cứ Điều lệ {ten_cu} đã được {'thành viên' if tu == '2tv' else ('Chủ sở hữu' if tu == '1tv' else 'Đại hội đồng cổ đông')} thông qua ngày {_v(g._ngay_dd_mm_yyyy(tt['ngay_dieu_le']))};", can="deu", sau=8)
    g._doan(d, f"{loai_vb}:", dam=True, can="giua", sau=6)
    g._doan(d, "ĐIỀU 1:", dam=True, gach=True, sau=2)
    g._doan(d, f"Chuyển đổi loại hình {ten_cu} từ loại hình {lh_cu} sang {lh_moi}, cụ thể như sau:", can="deu", sau=4)
    pairs = g._cac_cap_chuyen_nhuong(du.get("thanh_vien"))
    tv = du.get("thanh_vien") or {}
    tong_truoc = sum(g._gia_tri_von(x) for x in tv.get("ht") or [])
    for ban, mua in pairs:
        von_ban = g._gia_tri_von(ban)
        ty = _ty_le_chuoi(von_ban, tong_truoc)
        g._doan(d, f"- {_xung(ban)} {_v((ban.get('ho_ten') or '').upper())} chuyển nhượng số vốn {_tien(von_ban)} chiếm {ty or _CHAM} vốn điều lệ cho {_xung(mua)} {_v((mua.get('ho_ten') or '').upper())}", can="deu", sau=4)
    if den == "cp":
        g._doan(d, f"Chuyển đổi toàn bộ phần vốn góp thành cổ phần, mệnh giá mỗi cổ phần {_so(tt['menh_gia'])} đồng.", can="deu", sau=4)
    if tt["sau"]:
        g._doan(d, "Cơ cấu vốn góp sau khi đổi:" if den != "cp" else "Cơ cấu cổ đông sau khi chuyển đổi:", can="deu", sau=2)
        for x in tt["sau"]:
            if den == "cp":
                cp = (x.get("von") or 0) // tt["menh_gia"] if x.get("von") else 0
                g._doan(d, f"- {_xung(x)} {_v((x.get('ho_ten') or '').upper())} sở hữu {_so(cp) if cp else _CHAM} cổ phần ({_tien(x.get('von'))}), chiếm tỷ lệ {_v(x.get('ty_le'))} vốn điều lệ", can="deu", thut=True, sau=2)
            else:
                g._doan(d, f"- {_xung(x)} {_v((x.get('ho_ten') or '').upper())} sở hữu {_tien(x.get('von'))} vốn góp, chiếm tỷ lệ {_v(x.get('ty_le'))} vốn điều lệ", can="deu", thut=True, sau=2)
    g._doan(d, f"1. Tên công ty chuyển đổi viết bằng tiếng Việt: {_v(tt['ten'])}", dam=True, can="deu", sau=2)
    g._doan(d, f"- Tên công ty viết bằng tiếng nước ngoài: {tt['ten_nuoc_ngoai']}", can="deu", sau=0)
    g._doan(d, f"- Tên công ty viết tắt: {tt['ten_viet_tat']}", can="deu", sau=4)
    g._doan(d, f"2. Địa chỉ trụ sở chính: {_v(tt['dia_chi'])}", dam=True, can="deu", sau=4)
    g._doan(d, "3. Ngành nghề kinh doanh:", dam=True, sau=2)
    _bang_nganh_docx(d, tt["nganh"])
    g._doan(d, f"4. Vốn điều lệ: {_v(_so(tt['von']) + ' VNĐ' if tt['von'] else '')}", dam=True, sau=4)
    if den == "1tv":
        g._doan(d, "5. Chủ sở hữu:", dam=True, sau=2)
        _khoi_ca_nhan(d, tt["sau"][0] if tt["sau"] else {}, "Họ tên chủ sở hữu")
    else:
        g._doan(d, "5. Danh sách thành viên:" if den == "2tv" else "5. Danh sách cổ đông:", dam=True, sau=2)
        for i, x in enumerate(tt["sau"], 1):
            g._doan(d, f"{i}. {_v((x.get('ho_ten') or '').upper())}", dam=True, sau=2)
            _khoi_ca_nhan(d, x, "Họ tên")
    g._doan(d, "6. Người đại diện theo pháp luật:", dam=True, sau=2)
    _khoi_ca_nhan(d, tt["nguoi_dd"], "Họ tên người đại diện theo pháp luật")
    ten_dd = _v((tt["nguoi_dd"].get("ho_ten") or "").upper())
    g._doan(d, f"Điều 2: Giao cho Ông/Bà {ten_dd} (người đại diện theo pháp luật) tiến hành các thủ tục cần thiết theo quy định của pháp luật.", can="deu", sau=4)
    g._doan(d, f"Điều 3: Người đại diện theo pháp luật của công ty, các {'thành viên' if tu == '2tv' else 'cổ đông' if tu == 'cp' else 'bộ phận liên quan'} công ty có trách nhiệm thi hành {loai_vb.capitalize()} này.", can="deu", sau=4)
    g._doan(d, f"Điều 4: {loai_vb.capitalize()} này có hiệu lực kể từ ngày ký.", can="deu", sau=8)
    tb = d.add_table(rows=1, cols=2)
    a, b = tb.rows[0].cells
    pa = a.paragraphs[0]
    pa.add_run("Nơi nhận:").bold = True
    for dong in ("- Như Điều 1;", "- Phòng ĐKKD;", "- Lưu VP."):
        a.add_paragraph().add_run(dong).italic = True
    if tu == "2tv":
        tm, chuc = "TM. HỘI ĐỒNG THÀNH VIÊN", "CHỦ TỊCH HỘI ĐỒNG THÀNH VIÊN"
        ten_ky, anh = (ky[1], ky[2]) if ky else ((du.get("hien_tai") or {}).get("chu_so_huu") or "", None)
    elif tu == "1tv":
        tm, chuc = "", "CHỦ SỞ HỮU"
        ten_ky = (du.get("hien_tai") or {}).get("chu_so_huu") or ""
        anh = (chu_ky or {}).get("chu_so_huu")
    else:
        tm, chuc = "TM. ĐẠI HỘI ĐỒNG CỔ ĐÔNG", "CHỦ TỌA CUỘC HỌP"
        ten_ky, anh = (du.get("hien_tai") or {}).get("chu_so_huu") or "", None
    g._khoi_ky(b, (tm + "\n" if tm else "") + chuc, ten_ky, anh)
    return d


# ====================================================================================================== DANH SÁCH CỔ ĐÔNG SÁNG LẬP (MẪU 7 TT 68/2025)
def soan_danh_sach_co_dong(du, tt, chu_ky=None):
    from docx.enum.section import WD_ORIENT
    from docx.oxml import OxmlElement
    dn = du.get("dn") or {}
    d = g._van_ban_moi()
    sec = d.sections[0]
    sec.orientation = WD_ORIENT.LANDSCAPE
    sec.page_width, sec.page_height = Cm(29.7), Cm(21)
    sec.left_margin = sec.right_margin = Cm(1.5)
    sec.top_margin = sec.bottom_margin = Cm(1.5)
    d.styles["Normal"].font.size = Pt(11)
    g._doan(d, "Mẫu số 7", dam=True, can="giua", sau=0)
    g._doan(d, "(Ban hành kèm theo Thông tư số 68/2025/TT-BTC ngày 01 tháng 07 năm 2025 của Bộ trưởng Bộ Tài chính)", nghieng=True, can="giua", sau=6)
    g._doan(d, "DANH SÁCH CỔ ĐÔNG SÁNG LẬP CÔNG TY CỔ PHẦN", dam=True, can="giua", sau=2)
    g._doan(d, f"{tt['ten']}" + (f" — MST {dn['ma_so']}" if (dn.get("ma_so") or "").strip() else ""), can="giua", sau=6)
    cot = ["STT", "Tên cổ đông sáng lập", "Ngày, tháng, năm sinh", "Giới tính", "Loại giấy tờ, số, ngày cấp, cơ quan cấp giấy tờ pháp lý của cá nhân", "Quốc tịch", "Dân tộc",
           "Địa chỉ liên lạc", "Loại cổ phần", "Số cổ phần", "Giá trị cổ phần (VNĐ)", "Tỷ lệ (%)", "Chữ ký của cổ đông", "Ghi chú"]
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
    rong = [0.9, 2.5, 2.0, 1.2, 3.3, 1.5, 1.3, 3.2, 1.9, 1.7, 2.4, 1.3, 2.3, 1.2]
    for r in tb.rows:
        for i, c in enumerate(r.cells):
            c.width = Cm(rong[i])
    for stt, x in enumerate(tt["sau"], 1):
        r = tb.add_row()
        cp = (x.get("von") or 0) // tt["menh_gia"] if x.get("von") else 0
        gt = [str(stt), (x.get("ho_ten") or "").upper(), g._ngay_dd_mm_yyyy(x.get("ngay_sinh")), x.get("gioi_tinh") or "", g._giay_to(x), x.get("quoc_tich") or "Việt Nam",
              x.get("dan_toc") or "", g._dia_chi_nguoi(x), "Cổ phần phổ thông", f"{cp:,}".replace(",", ".") if cp else "",
              f"{x['von']:,}".replace(",", ".") if x.get("von") else "", x.get("ty_le") or "", "", ""]
        for i, v in enumerate(gt):
            r.cells[i].width = Cm(rong[i])
            p = r.cells[i].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run(v)
        so = re.sub(r"\D", "", x.get("cccd") or "")
        if len(so) >= 9:
            g._gan_chu_ky(r.cells[12].paragraphs[0], (chu_ky or {}).get("cccd:" + so), 2.2, 1.4)
        r._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
    p = g._doan(d, (dn.get("dia_danh") or "……") + ", " + tt["ngay_ky"][:1].lower() + tt["ngay_ky"][1:], nghieng=True, can="giua", sau=0)
    p.paragraph_format.space_before = Pt(8)
    g._doan(d, "NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT/CHỦ TỊCH HỘI ĐỒNG QUẢN TRỊ CỦA CÔNG TY", dam=True, can="giua", sau=0)
    g._doan(d, "(Ký và ghi họ tên)", nghieng=True, can="giua", sau=0)
    ten_ky = (tt["nguoi_dd"].get("ho_ten") or "").strip()
    if ten_ky:
        g._dong_trong_ky(d)
        g._doan(d, ten_ky.upper(), dam=True, can="giua", sau=0)
    return d


# ====================================================================================================== DANH MỤC + ĐÓNG GÓI
def _danh_muc(du, tt, ds_file, thieu):
    d = g.docx.Document()
    dn = du.get("dn") or {}
    d.add_heading("DANH MỤC HỒ SƠ CHUYỂN ĐỔI LOẠI HÌNH DOANH NGHIỆP (BẢN NHÁP)", level=1)
    d.add_paragraph(f"Doanh nghiệp: {tt['ten_cu']} — MST/Mã số doanh nghiệp: {dn.get('ma_so') or '……'}")
    d.add_paragraph(f"Chuyển đổi từ: {TEN_LOAI.get(tt['loai_cu']) or (dn.get('loai_hinh') or '……')}  →  sang: {TEN_LOAI[tt['loai_moi']]}"
                    + (f" (tên mới: {tt['ten']})" if tt["ten"] != tt["ten_cu"] else ""))
    d.add_heading("I. Hồ sơ đã soạn (người có thẩm quyền ký — phần mềm KHÔNG ký thay)", level=2)
    for ten in ds_file:
        d.add_paragraph(ten, style="List Bullet")
    d.add_heading("II. Giấy tờ thường kèm theo — gợi ý để kiểm tra", level=2)
    kem = ["Văn bản ủy quyền (nếu người nộp hồ sơ không phải người đại diện theo pháp luật) kèm giấy tờ pháp lý của người được ủy quyền.",
           "Bản sao giấy tờ pháp lý của các thành viên/chủ sở hữu/cổ đông (chỉ cần khi cơ quan đăng ký không khai thác được qua số định danh cá nhân).",
           "Chứng từ hoàn tất việc chuyển nhượng vốn/cổ phần (nếu có) và biên bản họp/biên bản kiểm phiếu của Hội đồng thành viên/Đại hội đồng cổ đông (nếu Điều lệ yêu cầu).",
           "Cam kết, văn bản thỏa thuận về việc kế thừa quyền, nghĩa vụ của công ty chuyển đổi (nếu có)."]
    if tt["loai_moi"] == "cp":
        kem.append("Giấy chứng nhận đăng ký đầu tư/văn bản liên quan nếu có cổ đông là nhà đầu tư nước ngoài (kê khai Mẫu số 8).")
    for t in kem:
        d.add_paragraph(t, style="List Bullet")
    d.add_heading("III. Thông tin còn thiếu (ô giữ nguyên dấu chấm trong biểu mẫu)", level=2)
    if thieu:
        for t in thieu:
            d.add_paragraph(t, style="List Bullet")
    else:
        d.add_paragraph("Không thiếu thông tin bắt buộc đã được yêu cầu nhập.")
    d.add_heading("Lưu ý", level=2)
    d.add_paragraph("Đây là BẢN NHÁP do phần mềm lập từ biểu mẫu chính thức (Phụ lục I Thông tư 121/2026/TT-BTC và Thông tư 68/2025/TT-BTC); Điều lệ và Quyết định/Nghị quyết soạn theo mẫu "
                    "người dùng cung cấp và Luật Doanh nghiệp số 59/2020/QH14 (đã được sửa đổi, bổ sung). Nội dung và danh mục giấy tờ cần được luật sư/kế toán kiểm tra theo quy định hiện hành "
                    "(Nghị định 168/2025/NĐ-CP, Nghị định 296/2026/NĐ-CP) và theo Điều lệ hiện hành của công ty trước khi ký và nộp. Phần mềm không tự điền thông tin chưa được cung cấp và không ký thay.")
    return d


def tao_ho_so_chuyen_doi(du, chu_ky=None, xuat_pdf=False):
    """Trả (bytes zip, tên file zip, cảnh báo[])."""
    import datetime
    du = dict(du)
    du["dn"] = dn = dict(du.get("dn") or {})
    if not (dn.get("ngay_lap") or "").strip():
        dn["ngay_lap"] = datetime.date.today().strftime("%d/%m/%Y")
    ht = dict(du.get("hien_tai") or {})
    du["hien_tai"] = ht
    tt = thong_tin_sau(du)
    tu, den = tt["loai_cu"], tt["loai_moi"]
    ma = re.sub(r"\D", "", dn.get("ma_so") or "") or "DN"
    canh_bao, thieu, tep, ds_file = [], [], [], []
    if not tu:
        canh_bao.append("Chưa biết loại hình HIỆN TẠI của công ty (ô 'Loại hình' ở mục 1) — Quyết định/Điều lệ ghi dấu chấm ở phần này.")
    if tu == den:
        canh_bao.append("Loại hình hiện tại trùng loại hình chuyển đổi sang — hãy kiểm tra lại ô 'Loại hình' ở mục 1 và loại hình chuyển đổi sang.")
    for k, ten in (("ten_cu", "Tên doanh nghiệp"),):
        if not tt.get(k):
            thieu.append(ten)
    if not (dn.get("ma_so") or "").strip():
        thieu.append("Mã số doanh nghiệp/MST")
    if not (dn.get("co_quan") or "").strip():
        thieu.append("Cơ quan đăng ký kinh doanh nhận hồ sơ (ô 'Kính gửi')")
    if not tt["sau"]:
        thieu.append("Chủ sở hữu/thành viên/cổ đông SAU chuyển đổi (nhập ở bảng thành viên)")
    elif den == "1tv" and len(tt["sau"]) != 1:
        canh_bao.append(f"Chuyển sang công ty TNHH một thành viên nhưng danh sách SAU chuyển đổi có {len(tt['sau'])} người — công ty TNHH một thành viên chỉ có 1 chủ sở hữu.")
    elif den in ("2tv", "cp") and len(tt["sau"]) < 2 and den == "2tv":
        canh_bao.append("Chuyển sang công ty TNHH hai thành viên trở lên nhưng danh sách SAU chuyển đổi chỉ có 1 người — cần từ 2 thành viên.")
    elif den == "cp" and len(tt["sau"]) < 3:
        canh_bao.append("Công ty cổ phần cần tối thiểu 03 cổ đông (trừ trường hợp cổ đông là Nhà nước...) — hãy kiểm tra danh sách cổ đông SAU chuyển đổi.")
    for x in tt["sau"]:
        for k, ten in (("ngay_sinh", "ngày sinh"), ("cccd", "số giấy tờ pháp lý"), ("von", "phần vốn góp")):
            if not x.get(k):
                thieu.append(f"{x.get('ho_ten') or '?'}: thiếu {ten}")
    if not tt["von"]:
        thieu.append("Vốn điều lệ")
    if not tt["nganh"]:
        thieu.append("Ngành, nghề kinh doanh (chưa lấy được từ hồ sơ đã gom — nhập ở mục 'Thay đổi ngành, nghề')")
    elif not any(x.get("chinh") for x in tt["nganh"]):
        thieu.append("Ngành, nghề kinh doanh CHÍNH (nhập mã ngành chính ở mục Chuyển đổi)")
    if not (tt["nguoi_dd"].get("ho_ten") or "").strip():
        thieu.append("Người đại diện theo pháp luật (tick 'Thay đổi người đại diện' để nhập, hoặc lấy từ hồ sơ đã gom)")
    if tt["ten"] != tt["ten_cu"]:
        canh_bao.append(f"Tên công ty đổi theo loại hình mới: {tt['ten_cu']} → {tt['ten']} (đổi tiền tố 'CÔNG TY TNHH'/'CÔNG TY CỔ PHẦN') — kiểm tra lại, hoặc nhập tên mới ở mục 'Thay đổi tên doanh nghiệp'.")
    if not (ht.get("ngay_dieu_le") or "").strip() and not (ht.get("ngay_cap_gcn") or "").strip():
        canh_bao.append("Chưa có ngày thông qua Điều lệ hiện hành (mục 1b) — Quyết định ghi dấu chấm ở câu 'Căn cứ Điều lệ … đã được thông qua ngày …'.")

    def them(ten_file, doc, nhan):
        g._bo_dong_trong_thua(doc)
        tep.append((ten_file, g._luu_bytes(doc)))
        ds_file.append(nhan)

    mau = MAU_TT121[den]
    them(f"1_Mau{mau}_Giay_de_nghi_dang_ky_doanh_nghiep_chuyen_doi_{ma}.docx", soan_giay_de_nghi(du, tt, chu_ky),
         f"Mẫu số {mau} — Giấy đề nghị đăng ký doanh nghiệp {TEN_LOAI[den]} (tình trạng: chuyển đổi loại hình) — Thông tư 121/2026/TT-BTC")
    them(f"2_Dieu_le_{ {'1tv': 'TNHH_1TV', '2tv': 'TNHH_2TV', 'cp': 'Co_phan'}[den] }_{ma}.docx", dl.soan_dieu_le(tt, chu_ky), f"Điều lệ {TEN_LOAI[den]} (phần mềm soạn theo mẫu — luật sư rà soát)")
    cap = g._cac_cap_chuyen_nhuong(du.get("thanh_vien"))
    for stt, (ban, mua) in enumerate(cap, 1):
        them(f"3_Hop_dong_chuyen_nhuong_phan_von_gop_{stt}_{ma}.docx", g.soan_hop_dong_chuyen_nhuong(du, ban, mua, chu_ky),
             f"Hợp đồng chuyển nhượng phần vốn góp: {ban.get('ho_ten') or '?'} → {mua.get('ho_ten') or '?'} (phần mềm soạn theo mẫu)")
    if not cap and tu == "2tv" and den == "1tv":
        canh_bao.append("Chưa có hợp đồng chuyển nhượng vốn: ở bảng thành viên, gạch (bỏ) thành viên rời công ty và chọn 'chuyển cho' người nhận để phần mềm soạn hợp đồng chuyển nhượng.")
    # Mẫu 10: danh sách chủ sở hữu hưởng lợi — người dùng đã nhập thì dùng; chưa nhập: tự lập từ danh sách SAU chuyển đổi (người sở hữu từ 25% vốn trở lên)
    du10 = dict(du)
    du10["loai"] = []
    cs = du.get("cshhl_ds") or {}
    if not (danh := g.danh_sach_cshhl_sau(cs)):
        ds = []
        for x in tt["sau"]:
            if (x.get("von") or 0) and tt["von"] and (x["von"] * 100 / tt["von"]) >= 25:
                y = dict(x)
                y["truc_tiep"] = f"{x['von'] * 100 / tt['von']:.3f}".rstrip("0").rstrip(".").replace(".", ",")
                y["gian_tiep"] = ""
                ds.append(y)
        du10["cshhl_ds"] = {"ht": [], "moi": ds}
        if ds:
            canh_bao.append("Mẫu số 10 tự lập từ danh sách SAU chuyển đổi (người sở hữu từ 25% vốn trở lên) — hãy đối chiếu với định nghĩa chủ sở hữu hưởng lợi tại Điều 3 Nghị định 296/2026/NĐ-CP "
                            "hoặc nhập danh sách chủ sở hữu hưởng lợi ở mục 'Thay đổi thông tin về chủ sở hữu hưởng lợi'.")
    du10["hien_tai"] = dict(ht, dd_ho_ten=tt["nguoi_dd"].get("ho_ten") or ht.get("dd_ho_ten") or "")
    ck10 = {k: v for k, v in (chu_ky or {}).items() if k != "giam_doc"}
    if _chuan(du10["hien_tai"]["dd_ho_ten"]) == _chuan(ht.get("dd_ho_ten")) and (chu_ky or {}).get("giam_doc"):
        ck10["giam_doc"] = chu_ky["giam_doc"]
    them(f"4_Mau10_Danh_sach_chu_so_huu_huong_loi_{ma}.docx", g.soan_mau10(du10, ck10), "Mẫu số 10 — Danh sách chủ sở hữu hưởng lợi — Thông tư 121/2026/TT-BTC")
    loai_vb = g._chu_the_quyet_dinh(dn.get("loai_hinh") or TEN_LOAI.get(tu, ""))[1]
    them(f"5_{'Nghi_quyet' if loai_vb == 'NGHỊ QUYẾT' else 'Quyet_dinh'}_chuyen_doi_loai_hinh_{ma}.docx", soan_quyet_dinh(du, tt, chu_ky),
         f"{loai_vb.capitalize()} về việc chuyển đổi loại hình doanh nghiệp (phần mềm soạn theo mẫu)")
    if den == "2tv":
        them(f"6_Mau6_Danh_sach_thanh_vien_{ma}.docx", g.soan_phu_luc_i6(dict(du, hien_tai=dict(ht, dd_ho_ten=tt["nguoi_dd"].get("ho_ten") or ht.get("dd_ho_ten") or "")), ck10),
             "Mẫu số 6 (Phụ lục I-6) — Danh sách thành viên công ty TNHH hai thành viên trở lên (phần mềm soạn theo mẫu)")
    if den == "cp":
        them(f"6_Mau7_Danh_sach_co_dong_sang_lap_{ma}.docx", soan_danh_sach_co_dong(du, tt, chu_ky), "Mẫu số 7 — Danh sách cổ đông sáng lập (phần mềm soạn theo mẫu)")
        canh_bao.append("Công ty cổ phần: nếu có cổ đông là nhà đầu tư nước ngoài, bổ sung Mẫu số 8 (Danh sách cổ đông là nhà đầu tư nước ngoài) — phần mềm chưa soạn mẫu này.")
    tep.append(("00_Danh_muc_ho_so_chuyen_doi.docx", g._luu_bytes(_danh_muc(du, tt, ds_file, thieu))))
    if thieu:
        canh_bao.append("Còn thiếu thông tin: " + "; ".join(thieu))
    if chu_ky and any(chu_ky.values()):
        canh_bao.append("Đã gắn chữ ký từ Kho chữ ký (chỉ chữ ký đã được người đó xác nhận đồng ý). Người ký vẫn cần kiểm tra nội dung trước khi nộp.")
    zip_b = g.dong_goi_zip(tep, xuat_pdf, canh_bao)
    return zip_b, f"Ho_so_chuyen_doi_loai_hinh_{ma}.zip", canh_bao
