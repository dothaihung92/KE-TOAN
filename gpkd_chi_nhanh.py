# -*- coding: utf-8 -*-
"""Hồ sơ thay đổi nội dung đăng ký hoạt động CHI NHÁNH / VĂN PHÒNG ĐẠI DIỆN / ĐỊA ĐIỂM KINH DOANH (bản NHÁP) — Mẫu số 19 (Thông tư 68/2025/TT-BTC).
Chỉ điền thông tin người dùng đã nhập/đã gom; ô thiếu giữ dấu chấm; KHÔNG ký thay (chữ ký chỉ gắn từ Kho chữ ký khi người đó đã đồng ý)."""
import re
import docx
from docx.oxml.ns import qn

import gpkd_soan as g
import gpkd_chuyen_doi as cd

TEN_DON_VI = {"chi_nhanh": "chi nhánh", "vpdd": "văn phòng đại diện", "ddkd": "địa điểm kinh doanh"}
LOAI_THAY_DOI_CN = {"ten": "Thay đổi tên", "dia_chi": "Thay đổi địa chỉ", "nganh": "Thay đổi ngành, nghề kinh doanh / nội dung hoạt động",
                    "dai_dien": "Thay đổi người đứng đầu", "thue": "Thay đổi thông tin đăng ký thuế", "bo_sung": "Bổ sung, cập nhật thông tin đăng ký hoạt động (mục B)"}
_MARKER = [("A", r"^A\.\s*ĐĂNG KÝ THAY ĐỔI NỘI DUNG"), ("TEN", r"^ĐĂNG KÝ THAY ĐỔI TÊN"), ("DIA_CHI", r"^ĐĂNG KÝ THAY ĐỔI ĐỊA CHỈ"),
           ("NGANH", r"^ĐĂNG KÝ THAY ĐỔI NGÀNH, NGHỀ"), ("NGUOI", r"^ĐĂNG KÝ THAY ĐỔI NGƯỜI ĐỨNG ĐẦU"), ("CHU_QUAN", r"^ĐĂNG KÝ THAY ĐỔI CHI NHÁNH CHỦ QUẢN"),
           ("THUE", r"^ĐĂNG KÝ THAY ĐỔI THÔNG TIN ĐĂNG KÝ THUẾ"), ("B", r"^B\.\s*BỔ SUNG"), ("C", r"^C\.\s*ĐỀ NGHỊ HIỆU ĐÍNH"),
           ("KET", r"^Doanh nghiệp cam kết hoàn toàn chịu trách nhiệm")]
_GIU = {"ten": "TEN", "dia_chi": "DIA_CHI", "nganh": "NGANH", "dai_dien": "NGUOI", "thue": "THUE", "bo_sung": "B"}
_CHUNG = re.compile(r"chi\s+nhánh/\s*văn\s+phòng\s+đại\s+diện/\s*địa\s+điểm\s+kinh\s+doanh", re.I)
_CHUNG2 = re.compile(r"chi\s+nhánh/\s*văn\s+phòng\s+đại\s+diện", re.I)


def _don_gian_ten_don_vi(d, loai):
    """Đổi cụm 'chi nhánh/văn phòng đại diện/địa điểm kinh doanh' trong biểu mẫu thành đúng loại đơn vị đang làm hồ sơ."""
    ten = TEN_DON_VI[loai]
    for p in _moi_doan(d):
        for _ in range(6):
            t = g._van(p)
            m = _CHUNG.search(t) or _CHUNG2.search(t)
            if not m:
                break
            viet = ten.upper() if m.group(0).isupper() else ten
            g._thay_khoang(p, m.start(), m.end(), viet)


def _moi_doan(d):
    from docx.text.paragraph import Paragraph
    kq = [Paragraph(p, d._body) for p in d.element.body.iter(qn("w:p"))]
    return kq


def soan_mau19(du, chu_ky=None):
    d = g.cat_mau(19)
    m = g._Mau(d)
    loai = set(du.get("loai") or [])
    dn = du.get("dn") or {}
    cn = du.get("cn") or {}
    kieu = cn.get("kieu") if cn.get("kieu") in TEN_DON_VI else "chi_nhanh"
    mk = {}
    for ten, mau in _MARKER:
        i = m.chi_so(mau)
        if i is not None:
            mk[ten] = i
    thu_tu = sorted(mk.items(), key=lambda kv: kv[1])
    cac = {t: (i, (thu_tu[k + 1][1] if k + 1 < len(thu_tu) else len(m.ch))) for k, (t, i) in enumerate(thu_tu)}
    dau_a = mk.get("A", len(m.ch))
    # ---- phần đầu: doanh nghiệp + đơn vị trực thuộc
    g._dien_dau(m, dn, dau_a)
    m.dien(r"Tên chi nhánh/văn phòng đại diện/địa điểm kinh doanh \(ghi bằng chữ in hoa\)", (cn.get("ten") or "").upper(), 0, dau_a)
    p = m.tim(r"Mã số chi nhánh/văn phòng đại diện/địa điểm kinh doanh hoặc mã số thuế", 0, dau_a)
    if p is not None and (cn.get("ma_so") or "").strip():
        t = g._van(p)
        k = t.index(":") + 1 if ":" in t else len(t)
        g._thay_khoang(p, k, len(t), " " + cn["ma_so"].strip())           # dòng có 2 nhóm dấu chấm -> thay cả cụm bằng mã số
    # ---- các mục thay đổi
    if "ten" in loai and "TEN" in cac:
        t = du.get("ten") or {}
        lo, hi = cac["TEN"]
        for nhan, k in ((r"viết bằng tiếng Việt sau khi thay đổi", "viet"), (r"viết bằng tiếng nước ngoài sau khi thay đổi", "nuoc_ngoai"), (r"viết tắt sau khi thay đổi", "viet_tat")):
            v = (t.get(k) or "").strip()
            if v:
                m.dien(nhan, v.upper() if k == "viet" else v, lo, hi)
    if "dia_chi" in loai and "DIA_CHI" in cac:
        a = du.get("dia_chi") or {}
        lo, hi = cac["DIA_CHI"]
        m.dien(r"Số nhà/phòng, ngách/hẻm, ngõ/kiệt, đường/phố/đại lộ, tổ/xóm/ấp/thôn", a.get("so_nha"), lo, hi)
        m.dien(r"Xã/Phường/Đặc khu", a.get("xa"), lo, hi)
        m.dien(r"Tỉnh/Thành phố trực thuộc trung ương", a.get("tinh"), lo, hi)
        m.dien(r"Điện thoại \(nếu có\)", a.get("dien_thoai"), lo, hi)
        m.dien(r"Số fax \(nếu có\)", a.get("fax"), lo, hi)
        m.dien(r"Thư điện tử \(nếu có\)", a.get("email"), lo, hi)
        m.dien(r"Website \(nếu có\)", a.get("website"), lo, hi)
    if "nganh" in loai and "NGANH" in cac:
        lo, hi = cac["NGANH"]
        i_ng = m.chi_so(r"^Ngành, nghề kinh doanh sau khi thay đổi", lo)
        i_nd = m.chi_so(r"^Nội dung hoạt động sau khi thay đổi", lo)
        ds = [x for x in ((du.get("nganh") or {}).get("ds") or []) if (x.get("ten") or x.get("ma"))]
        if kieu == "vpdd":
            if i_ng is not None and i_nd is not None and i_ng < i_nd:
                m.xoa_phan(i_ng, i_nd)                            # văn phòng đại diện: bỏ bảng ngành, chỉ ghi nội dung hoạt động
            nd = str((du.get("nganh") or {}).get("noi_dung") or "").strip()
            if nd:
                for c in m.ch[(i_nd or 0):hi]:
                    if c.getparent() is not None and c.tag == qn("w:p") and re.fullmatch(r"[…\.\s]+", g._chu(c) or ""):
                        from docx.text.paragraph import Paragraph
                        ps = Paragraph(c, d._body)
                        g._thay_khoang(ps, 0, len(g._van(ps)), nd) if ps.runs else ps.add_run(nd)
                        break
        else:
            if i_nd is not None:
                j = next((k for k in range(i_nd + 1, hi) if m.ch[k].tag == qn("w:p") and re.fullmatch(r"[…\.\s]+", g._chu(m.ch[k]) or "")), i_nd)
                m.xoa_phan(i_nd, j + 1)                           # chi nhánh/địa điểm: bỏ phần "Nội dung hoạt động" (chỉ dùng cho văn phòng đại diện)
            if i_ng is not None and ds:
                for k in range(i_ng + 1, min(len(m.ch), i_ng + 4)):
                    if m.ch[k].tag == qn("w:tbl"):
                        g._dien_bang_nganh(m.bang(k), ds, ["ten", "ma", "chinh"])
                        break
    if "dai_dien" in loai and "NGUOI" in cac:
        lo, hi = cac["NGUOI"]
        n = g._chuan_dia_chi((du.get("dai_dien") or [{}])[0])
        cd._dien_nguoi(m, n, lo, hi, r"Họ, chữ đệm và tên")
        if (n.get("ho_ten") or "").strip():
            p = m.tim(r"^Dân tộc", lo, hi)
            if p is not None:
                g.dien_cham(p, r"Dân tộc", (n.get("dan_toc") or "Kinh").strip())
                g.dien_cham(p, r"Quốc tịch", (n.get("quoc_tich") or "Việt Nam").strip())
    if "thue" in loai and "THUE" in cac:
        g._dien_thong_tin_thue(m, du, cac["THUE"])
    if "bo_sung" in loai and "B" in cac:
        lo, hi = cac["B"]
        trong = [c for c in m.ch[lo:hi] if c.tag == qn("w:p") and re.fullmatch(r"[…\.\s]+", g._chu(c) or "")]
        dong = [x.strip() for x in re.split(r"[\n;]+", str((du.get("bo_sung") or {}).get("noi_dung") or "")) if x.strip()]
        from docx.text.paragraph import Paragraph
        dong_cn = g._dong_cap_nhat(du, chi_dai_dien=True) if trong else []      # mục B: "Cập nhật địa chỉ trụ sở chính (theo đơn vị hành chính mới)" + "Cập nhật thông tin đại diện pháp luật"
        if dong_cn:
            g._chen_cap_nhat_muc_b(trong[0], dong_cn)
            if not dong:                                                       # chỉ có phần cập nhật: bỏ các dòng chấm của mục B
                for c in trong:
                    c.getparent().remove(c)
                trong = []
        for c, t in zip(trong, dong):
            ps = Paragraph(c, d._body)
            g._thay_khoang(ps, 0, len(g._van(ps)), t) if ps.runs else ps.add_run(t)
    # ---- bỏ phần không dùng
    giu = {_GIU[k] for k in loai if k in _GIU}
    con_lai = {"A", "KET"} | giu
    for ten, (lo, hi) in sorted(cac.items(), key=lambda kv: -kv[1][0]):
        if ten not in con_lai:
            m.xoa_phan(lo, hi)
    cd._xoa_den_truoc(m, r"^Chi nhánh chủ quản \(chỉ kê khai", r"^A\.\s*ĐĂNG KÝ THAY ĐỔI NỘI DUNG")      # chi nhánh chủ quản chỉ dùng cho địa điểm kinh doanh trực thuộc chi nhánh (chưa hỗ trợ)
    # ---- chữ ký: người đại diện theo pháp luật của doanh nghiệp (không ký thay; ảnh chỉ khi trong Kho chữ ký)
    ten_ky = ((du.get("hien_tai") or {}).get("dd_ho_ten") or "").strip()
    if ten_ky:
        for tb in d.tables:
            c = next((c for r in tb.rows for c in r.cells if "NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT CỦA DOANH NGHIỆP" in c.text), None)
            if c is not None:
                tieu_de = "NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT CỦA DOANH NGHIỆP"           # người ký là người đại diện theo pháp luật của doanh nghiệp
                g._khoi_ky(c, tieu_de, ten_ky, (chu_ky or {}).get("giam_doc"))
                g._giu_mot_trang(tb)
                break
    g._lam_sach_mau(m)
    _don_gian_ten_don_vi(d, kieu)
    _bo_trang_trang_cuoi(d)
    return d


def _bo_trang_trang_cuoi(d):
    """Các đoạn trống sau khối ký đẩy Mẫu 19 sang một TRANG TRẮNG cuối (chỉ có số trang): bỏ các đoạn trống cuối, giữ 1 đoạn nhỏ 1pt (Word cần 1 đoạn sau bảng)."""
    body = d.element.body
    while True:
        cac = [e for e in body if e.tag != qn("w:sectPr")]
        if len(cac) > 1 and cac[-1].tag == qn("w:p") and not g._chu(cac[-1]).strip() and not cac[-1].xpath(".//w:br | .//w:drawing | .//w:pict"):
            body.remove(cac[-1])
        else:
            break
    cac = [e for e in body if e.tag != qn("w:sectPr")]
    if cac and cac[-1].tag == qn("w:tbl"):
        from docx.text.paragraph import Paragraph
        sect = body.find(qn("w:sectPr"))
        el = d.add_paragraph()._p                                          # đoạn trống cuối bảng, thu nhỏ để không tràn sang trang mới
        pf = Paragraph(el, d._body)
        pf.paragraph_format.space_before = pf.paragraph_format.space_after = 0
        pf.paragraph_format.line_spacing = 0.01
        r = pf.add_run("")
        r.font.size = docx.shared.Pt(1)


def tao_ho_so_chi_nhanh(du, chu_ky=None, xuat_pdf=False):
    """Trả (bytes zip, tên file zip, cảnh báo[])."""
    import datetime
    du = dict(du)
    du["dn"] = dn = dict(du.get("dn") or {})
    loai = set(du.get("loai") or [])
    if not loai and not du.get("tao_uy_quyen"):
        raise ValueError("Chưa chọn nội dung thay đổi nào")
    if not (dn.get("ngay_lap") or "").strip():
        dn["ngay_lap"] = datetime.date.today().strftime("%d/%m/%Y")
    cn = dict(du.get("cn") or {})
    du["cn"] = cn
    ma = re.sub(r"\D", "", cn.get("ma_so") or dn.get("ma_so") or "") or "CN"
    canh_bao, thieu, tep, ds_file = [], [], [], []
    if not (dn.get("ten") or "").strip():
        thieu.append("Tên doanh nghiệp")
    if not (dn.get("ma_so") or "").strip():
        thieu.append("Mã số doanh nghiệp/MST")
    if not (cn.get("ten") or "").strip():
        thieu.append("Tên chi nhánh/văn phòng đại diện/địa điểm kinh doanh")
    if not (cn.get("ma_so") or "").strip():
        thieu.append("Mã số chi nhánh/văn phòng đại diện (mã số thuế)")
    if not (dn.get("co_quan") or "").strip():
        thieu.append("Cơ quan đăng ký kinh doanh nhận hồ sơ (ô 'Kính gửi')")
    if "ten" in loai and not ((du.get("ten") or {}).get("viet") or "").strip():
        thieu.append("Tên mới")
    if "dia_chi" in loai and not any(((du.get("dia_chi") or {}).get(k) or "").strip() for k in ("so_nha", "xa", "tinh")):
        thieu.append("Địa chỉ mới")
    if "dai_dien" in loai and not (((du.get("dai_dien") or [{}])[0]).get("ho_ten") or "").strip():
        thieu.append("Người đứng đầu mới")
    if not ((du.get("hien_tai") or {}).get("dd_ho_ten") or "").strip():
        thieu.append("Người đại diện theo pháp luật của doanh nghiệp (người ký)")
    mau = soan_mau19(du, chu_ky)
    g._bo_dong_trong_thua(mau)
    tep.append((f"Mau19_Thay_doi_noi_dung_dang_ky_hoat_dong_chi_nhanh_{ma}.docx", g._luu_bytes(mau)))
    ds_file.append("Mẫu số 19 — Giấy đề nghị đăng ký thay đổi nội dung đăng ký hoạt động chi nhánh/văn phòng đại diện/địa điểm kinh doanh — Thông tư 68/2025/TT-BTC")
    if du.get("tao_uy_quyen"):
        tep.append((f"Giay_uy_quyen_nop_ho_so_{ma}.docx", g._luu_sach(g.soan_giay_uy_quyen(du, chu_ky))))
        ds_file.append("Giấy ủy quyền nộp hồ sơ và nhận kết quả (phần mềm soạn theo mẫu)")
    d = docx.Document()
    d.add_heading("DANH MỤC HỒ SƠ THAY ĐỔI ĐĂNG KÝ HOẠT ĐỘNG CHI NHÁNH/VĂN PHÒNG ĐẠI DIỆN/ĐỊA ĐIỂM KINH DOANH (BẢN NHÁP)", level=1)
    d.add_paragraph(f"Doanh nghiệp: {(dn.get('ten') or '').upper()} — MST: {dn.get('ma_so') or '……'}")
    d.add_paragraph(f"{TEN_DON_VI.get(cn.get('kieu'), 'Chi nhánh').capitalize()}: {(cn.get('ten') or '').upper()} — Mã số: {cn.get('ma_so') or '……'}")
    d.add_paragraph("Nội dung đề nghị thay đổi: " + "; ".join(LOAI_THAY_DOI_CN[k] for k in LOAI_THAY_DOI_CN if k in loai))
    d.add_heading("I. Biểu mẫu đã soạn (phần mềm KHÔNG ký thay)", level=2)
    for t in ds_file:
        d.add_paragraph(t, style="List Bullet")
    d.add_heading("II. Giấy tờ thường kèm theo — gợi ý để kiểm tra (cần kế toán/luật sư xác nhận)", level=2)
    kem = ["Quyết định/Nghị quyết của chủ sở hữu/Hội đồng thành viên/cấp có thẩm quyền của công ty về việc thay đổi nội dung hoạt động của chi nhánh/văn phòng đại diện/địa điểm kinh doanh (theo Điều lệ công ty).",
           "Văn bản ủy quyền (nếu người nộp hồ sơ không phải người đại diện theo pháp luật) kèm giấy tờ pháp lý của người được ủy quyền."]
    if "dai_dien" in loai:
        kem.append("Giấy tờ pháp lý của người đứng đầu mới (chỉ cần khi không khai thác được qua số định danh cá nhân).")
    if "dia_chi" in loai:
        kem.append("Giấy tờ chứng minh quyền sử dụng hợp pháp địa chỉ mới (nếu cơ quan đăng ký yêu cầu).")
    for t in kem:
        d.add_paragraph(t, style="List Bullet")
    if thieu:
        d.add_heading("III. Thông tin còn THIẾU (ô tương ứng giữ dấu chấm)", level=2)
        for t in thieu:
            d.add_paragraph(t, style="List Bullet")
    tep.append(("00_Danh_muc_ho_so_chi_nhanh.docx", g._luu_bytes(d)))
    if thieu:
        canh_bao.append("Còn thiếu thông tin: " + "; ".join(thieu))
    if "dai_dien" in loai and cn.get("kieu") == "ddkd":
        canh_bao.append("Địa điểm kinh doanh trực thuộc chi nhánh (mục 'Chi nhánh chủ quản') chưa được phần mềm điền — bổ sung trực tiếp vào biểu mẫu nếu cần.")
    if chu_ky and any(chu_ky.values()):
        canh_bao.append("Đã gắn chữ ký từ Kho chữ ký (chỉ chữ ký đã được người đó xác nhận đồng ý). Người ký vẫn cần kiểm tra nội dung trước khi nộp.")
    return g.dong_goi_zip(tep, xuat_pdf, canh_bao), f"Ho_so_chi_nhanh_{ma}.zip", canh_bao
