"""Giải thể doanh nghiệp — BƯỚC 1: Quyết định giải thể (chủ sở hữu / Hội đồng thành viên / Đại hội đồng cổ đông) + thông tin nhập vào khối
"Thông tin quyết định giải thể" của cổng đăng ký doanh nghiệp (Số quyết định, Ngày quyết định, Lý do giải thể) + danh mục hồ sơ kèm theo.
Quyết định soạn theo bản Quyết định giải thể thực tế người dùng cung cấp (9 Điều). Phần mềm KHÔNG ký thay, KHÔNG nộp hồ sơ."""
import re

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm

import gpkd_soan as g

MAC_DINH = {"ly_do": "Không hoạt động nữa", "hop_dong": "Không có hợp đồng ký kết", "no": "Không có các khoản nợ phát sinh",
            "lao_dong": "0", "tai_san": "Không có tài sản"}


def thong_tin(du):
    """Gom thông tin giải thể từ dữ liệu người dùng + hồ sơ hiện tại (ô trống thì dùng mặc định)."""
    dn, ht, gt = du.get("dn") or {}, du.get("hien_tai") or {}, du.get("giai_the") or {}
    v = lambda k: (gt.get(k) or "").strip()
    lao = re.sub(r"\D", "", v("lao_dong")) or MAC_DINH["lao_dong"]
    so = v("so_qd") or ((dn.get("so_vb") or "").strip() and (dn.get("so_vb").strip() + "/QĐ")) or ""
    ngay = g._ngay_dd_mm_yyyy(v("ngay_qd") or dn.get("ngay_lap") or "")
    dia_chi = v("dia_chi") or ", ".join(x for x in ((ht.get("dia_chi") or "").strip(),) if x)
    return {"so": so, "ngay": ngay, "ly_do": v("ly_do") or MAC_DINH["ly_do"], "hop_dong": v("hop_dong") or MAC_DINH["hop_dong"],
            "no": v("no") or MAC_DINH["no"], "lao_dong": lao, "tai_san": v("tai_san") or MAC_DINH["tai_san"],
            "dia_chi": dia_chi, "nguoi": (v("nguoi") or (ht.get("chu_so_huu") or "").strip() or (ht.get("dd_ho_ten") or "").strip())}


def _ngay_ghi(s):
    return s or "……"


def soan_quyet_dinh_giai_the(du, chu_ky=None):
    dn, ht = du.get("dn") or {}, du.get("hien_tai") or {}
    tt = thong_tin(du)
    chu, loai_vb, ten_co = g._chu_the_quyet_dinh(dn.get("loai_hinh"))
    la_1tv, la_cp = chu == "CHỦ SỞ HỮU", chu == "ĐẠI HỘI ĐỒNG CỔ ĐÔNG"
    ten = (dn.get("ten") or "").strip().upper() or "……"
    d = g._van_ban_moi()
    g._bang_quoc_hieu(d, dict(dn, ngay_lap=tt["ngay"]), tt["so"])
    g._doan(d, loai_vb, dam=True, can="giua", sau=0)
    g._doan(d, "Về việc giải thể doanh nghiệp", dam=True, can="giua", sau=0)
    g._doan(d, "", sau=2)
    g._doan(d, chu, dam=True, can="giua")
    g._doan(d, "- Căn cứ tình hình hoạt động của doanh nghiệp;", thut=True)
    if not la_1tv:
        g._doan(d, f"- Căn cứ Điều lệ công ty {ten} và Luật Doanh nghiệp;", thut=True)
    g._doan(d, loai_vb, dam=True, can="giua")
    ngay_cap = g._ngay_dd_mm_yyyy(ht.get("ngay_cap_gcn") or "")
    noi_cap = (ht.get("noi_cap_gcn") or "").strip() or "Phòng Đăng ký kinh doanh"
    ma = (dn.get("ma_so") or "").strip() or "……"
    for tieu, nd in (
        ("Điều 1: ", f"Giải thể doanh nghiệp: {ten}"),
    ):
        p = g._doan(d, tieu, thut=True, sau=2)
        p.runs[0].bold = True
        p.add_run(nd)
    g._doan(d, f"- Mã số doanh nghiệp {ma} ngày cấp {_ngay_ghi(ngay_cap)} nơi cấp {noi_cap}", thut=True, sau=2)
    g._doan(d, f"- Địa chỉ trụ sở: {tt['dia_chi'] or '……'}", thut=True)

    def dieu(so, tieu, *dong, thut_dong=True):
        p = g._doan(d, f"Điều {so}: ", thut=True, sau=2)
        p.runs[0].bold = True
        p.add_run(tieu)
        for x in dong:
            g._doan(d, x, thut=thut_dong, sau=2, can="deu")
        d.paragraphs[-1].paragraph_format.space_after = g.Pt(6)
    dieu(2, f"Lý do giải thể: {tt['ly_do']}")
    dieu(3, "Thời hạn, thủ tục thanh lý các hợp đồng đã ký kết:", tt["hop_dong"],
         "- Kể từ thời điểm quyết định giải thể, doanh nghiệp không ký kết hợp đồng mới không phải là hợp đồng nhằm thực hiện giải thể doanh nghiệp.",
         "- Không được chấm dứt thực hiện các hợp đồng đã có hiệu lực.")
    dieu(4, "Thời hạn, thủ tục thanh toán các khoản nợ:", tt["no"],
         "- Kể từ thời điểm quyết định giải thể, doanh nghiệp không huy động vốn dưới mọi hình thức.")
    dieu(5, "Xử lý các nghĩa vụ phát sinh từ hợp đồng lao động:", f"Doanh nghiệp sử dụng {tt['lao_dong']} lao động.")
    dieu(6, "Thanh lý tài sản sau khi thanh toán hết các khoản nợ và chi phí giải thể doanh nghiệp", tt["tai_san"])
    nguoi = (tt["nguoi"] or "").upper() or "……"
    if la_1tv:
        ai = f"Ông/bà {nguoi} chủ sở hữu"
    elif la_cp:
        ai = f"Người đại diện theo pháp luật {nguoi} và các cổ đông"
    else:
        ai = f"Ông/bà {nguoi} (Chủ tịch Hội đồng thành viên) và các thành viên công ty"
    dieu(7, f"{ai} phải liên đới chịu trách nhiệm thanh toán quyền lợi của người lao động chưa được giải quyết, số thuế chưa nộp, số nợ chưa thanh toán "
            "và chịu trách nhiệm cá nhân trước pháp luật về những hệ quả phát sinh của doanh nghiệp trong thời hạn 05 năm kể từ ngày nộp hồ sơ giải thể "
            "doanh nghiệp đến Cơ quan đăng ký kinh doanh.")
    dieu(8, f"{loai_vb.capitalize()} này phải được đăng trên Cổng thông tin quốc gia về đăng ký doanh nghiệp và được niêm yết công khai tại trụ sở chính của "
            "doanh nghiệp và trụ sở các đơn vị phụ thuộc của doanh nghiệp, được gửi đến các chủ nợ kèm phương án giải quyết nợ, được gửi đến người lao động, "
            "được gửi đến người có quyền và nghĩa vụ, lợi ích có liên quan, gửi đến cơ quan Nhà Nước.")
    dieu(9, f"{loai_vb.capitalize()} này có hiệu lực từ ngày ký.")
    tb = d.add_table(rows=1, cols=2)
    a, b = tb.rows[0].cells
    a.paragraphs[0].add_run("Nơi nhận:").bold = True
    a.paragraphs[0].runs[0].italic = True
    for t in ("- Như điều 8;", "- Lưu."):
        a.add_paragraph(t)
    pb = b.paragraphs[0]
    pb.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if la_1tv:
        pb.add_run("CHỦ SỞ HỮU").bold = True
    elif la_cp:
        pb.add_run("TM. ĐẠI HỘI ĐỒNG CỔ ĐÔNG").bold = True
        pb = b.add_paragraph()
        pb.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pb.add_run("CHỦ TỌA").bold = True
    else:
        pb.add_run("TM. HỘI ĐỒNG THÀNH VIÊN").bold = True
        pb = b.add_paragraph()
        pb.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pb.add_run("CHỦ TỊCH HỘI ĐỒNG THÀNH VIÊN").bold = True
    pb2 = b.add_paragraph()
    pb2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pb2.add_run("(Ký, ghi rõ họ và tên)").italic = True
    if tt["nguoi"]:
        g._dong_trong_ky(b)
        pk = b.add_paragraph()
        pk.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pk.add_run(tt["nguoi"].upper()).bold = True
        so = re.sub(r"\D", "", ht.get("chu_so_huu_cccd") or "")
        ck = chu_ky or {}
        anh = (ck.get("cccd:" + so) if len(so) >= 9 else None) or ck.get("chu_so_huu")
        g._gan_chu_ky(pk, anh)
    g._giu_mot_trang(tb, 2)
    return d


def soan_danh_muc_giai_the(du, ds_file, canh_bao):
    dn = du.get("dn") or {}
    tt = thong_tin(du)
    d = docx.Document()
    d.add_heading("HỒ SƠ GIẢI THỂ DOANH NGHIỆP — BƯỚC 1: THÔNG BÁO QUYẾT ĐỊNH GIẢI THỂ (BẢN NHÁP)", level=1)
    d.add_paragraph(f"Doanh nghiệp: {(dn.get('ten') or '').upper()} — MST/Mã số doanh nghiệp: {dn.get('ma_so') or '……'}")
    d.add_heading("I. Thông tin nhập vào cổng đăng ký doanh nghiệp — khối “Thông tin quyết định giải thể”", level=2)
    for nhan, gt in (("Số quyết định", tt["so"]), ("Ngày quyết định", tt["ngay"]), ("Lý do giải thể", tt["ly_do"])):
        d.add_paragraph(f"{nhan}: {gt or '……'}", style="List Bullet")
    d.add_paragraph("Các khối còn lại trên cổng: Thông tin Ủy quyền, Người nộp hồ sơ; văn bản đính kèm: “Thông báo; nghị quyết, quyết định; Biên bản họp "
                    "của Hội đồng thành viên, của Đại hội đồng cổ đông, của chủ sở hữu công ty” và “Khác”.")
    d.add_heading("II. Biểu mẫu đã soạn (ký bởi người có thẩm quyền — phần mềm KHÔNG ký thay)", level=2)
    for ten, nguon in ds_file:
        d.add_paragraph(f"{ten} ({nguon})", style="List Bullet")
    d.add_heading("III. Giấy tờ thường kèm theo — gợi ý để kiểm tra", level=2)
    la_1tv = "một thành viên" in (dn.get("loai_hinh") or "").lower()
    for t in (["Quyết định giải thể của chủ sở hữu (đã ký, đóng dấu nếu có) — file đã soạn."] if la_1tv else
              ["Nghị quyết/Quyết định giải thể của Hội đồng thành viên (hoặc Đại hội đồng cổ đông) — file đã soạn.",
               "Biên bản họp Hội đồng thành viên (hoặc Đại hội đồng cổ đông) về việc giải thể (kèm danh sách thành viên/cổ đông dự họp)."]) + \
             ["Bản sao giấy tờ pháp lý của người nộp hồ sơ (nếu nộp qua mạng bằng chữ ký số/tài khoản đăng ký kinh doanh thì theo hướng dẫn trên cổng).",
              "Giấy ủy quyền (nếu người đại diện ủy quyền cho người khác nộp hồ sơ).",
              "Sau khi cổng đăng thông báo: niêm yết quyết định tại trụ sở chính/đơn vị phụ thuộc, gửi chủ nợ, người lao động, cơ quan thuế (theo Điều 8 Quyết định)."]:
        d.add_paragraph(t, style="List Bullet")
    d.add_heading("IV. Lưu ý", level=2)
    for t in (canh_bao or ["Không có cảnh báo."]):
        d.add_paragraph(t, style="List Bullet")
    d.add_paragraph("Đây là BẢN NHÁP do phần mềm lập; kế toán/người đại diện kiểm tra theo Điều lệ, Luật Doanh nghiệp, Nghị định hướng dẫn về đăng ký doanh nghiệp "
                    "và tình hình thực tế (nghĩa vụ thuế, hoá đơn, bảo hiểm) trước khi ký và nộp. Phần mềm không tự ký, không tự nộp.")
    return d


def tao_ho_so_giai_the(du, chu_ky=None, xuat_pdf=False):
    import datetime
    du = dict(du)
    du["dn"] = dn = dict(du.get("dn") or {})
    du["hien_tai"] = ht = dict(du.get("hien_tai") or {})
    if not (dn.get("ngay_lap") or "").strip():
        dn["ngay_lap"] = datetime.date.today().strftime("%d/%m/%Y")
    ma = re.sub(r"\D", "", dn.get("ma_so") or "") or "DN"
    _chu, loai_vb, ten_co = g._chu_the_quyet_dinh(dn.get("loai_hinh"))
    tt = thong_tin(du)
    canh_bao = []
    if not (dn.get("ten") or "").strip():
        canh_bao.append("Chưa có tên doanh nghiệp.")
    if not tt["so"]:
        canh_bao.append("Chưa có Số quyết định — nhập ở mục Giải thể (để trống thì văn bản ghi dấu chấm).")
    if not tt["ngay"]:
        canh_bao.append("Chưa có Ngày quyết định giải thể.")
    if not (ht.get("ngay_cap_gcn") or "").strip():
        canh_bao.append("Chưa có ngày cấp Giấy chứng nhận ĐKDN (mục 1b) — Điều 1 để trống ngày cấp.")
    if not tt["dia_chi"]:
        canh_bao.append("Chưa có địa chỉ trụ sở (mục 1b hoặc ô địa chỉ ở mục Giải thể) — Điều 1 để dấu chấm.")
    if not tt["nguoi"]:
        canh_bao.append("Chưa có tên Chủ sở hữu/Chủ tịch HĐTV (mục 1b) — Điều 7 và phần ký để dấu chấm.")
    if "một thành viên" not in (dn.get("loai_hinh") or "").lower():
        canh_bao.append(f"{loai_vb.capitalize()} soạn theo thẩm quyền của {ten_co}: công ty từ 2 thành viên/cổ phần cần có Biên bản họp thông qua việc giải thể — hãy đối chiếu Điều lệ.")
    tep, ds_file = [], []
    d = soan_quyet_dinh_giai_the(du, chu_ky)
    g._bo_dong_trong_thua(d)
    ten_qd = f"1_{'Nghi_quyet' if loai_vb == 'NGHỊ QUYẾT' else 'Quyet_dinh'}_giai_the_doanh_nghiep_{ma}.docx"
    tep.append((ten_qd, g._luu_bytes(d)))
    ds_file.append((f"{loai_vb.capitalize()} của {ten_co} về việc giải thể doanh nghiệp (phần mềm soạn theo mẫu)", "mẫu do người dùng cung cấp"))
    if du.get("tao_uy_quyen"):
        tep.append((f"2_Giay_uy_quyen_nop_ho_so_{ma}.docx", g._luu_sach(g.soan_giay_uy_quyen(du, chu_ky))))
        ds_file.append(("Giấy ủy quyền nộp hồ sơ và nhận kết quả (phần mềm soạn theo mẫu)", "mẫu do người dùng cung cấp"))
    dm = soan_danh_muc_giai_the(du, ds_file, canh_bao)
    tep.append(("00_Danh_muc_ho_so_giai_the.docx", g._luu_bytes(dm)))
    if chu_ky and any(chu_ky.values()):
        canh_bao.append("Đã gắn chữ ký từ Kho chữ ký (chỉ chữ ký đã được người đó xác nhận đồng ý). Người ký vẫn cần kiểm tra nội dung trước khi nộp.")
    return g.dong_goi_zip(tep, xuat_pdf, canh_bao), f"Ho_so_giai_the_{ma}.zip", canh_bao
