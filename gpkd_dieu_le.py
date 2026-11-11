# -*- coding: utf-8 -*-
"""Soạn ĐIỀU LỆ công ty (bản NHÁP) cho hồ sơ chuyển đổi loại hình doanh nghiệp: công ty TNHH một thành viên / TNHH hai thành viên trở lên / công ty cổ phần.

Cấu trúc theo Điều lệ mẫu 1 thành viên người dùng cung cấp (6 chương, 24 điều) và Luật Doanh nghiệp số 59/2020/QH14 (đã được sửa đổi, bổ sung).
Phần mềm chỉ điền thông tin do người dùng nhập; ô thiếu giữ dấu chấm "……" (không bịa thông tin). Luật sư/kế toán cần rà soát trước khi ký.
"""
import re

from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

import gpkd_soan as g

_CHAM = "……"


def _v(x, mac_dinh=_CHAM):
    t = str(x or "").strip()
    return t if t else mac_dinh


def _tien(n):
    return (f"{int(n):,}".replace(",", ".") + " đồng") if n else _CHAM


def _nguoi_dong(n):
    """Các dòng thông tin cá nhân (họ tên, giới tính, ngày sinh, dân tộc, quốc tịch, giấy tờ, địa chỉ)."""
    n = n or {}
    gt = (n.get("gioi_tinh") or "").strip()
    return [f"Họ và tên: {_v((n.get('ho_ten') or '').upper())}" + (f" - Giới tính: {gt}" if gt else ""),
            f"Sinh ngày: {_v(g._ngay_dd_mm_yyyy(n.get('ngay_sinh')))} - Dân tộc: {_v(n.get('dan_toc'), 'Kinh')} - Quốc tịch: {_v(n.get('quoc_tich'), 'Việt Nam')}",
            f"Số giấy tờ pháp lý của cá nhân (CCCD/hộ chiếu): {_v(n.get('cccd'))} - Ngày cấp: {_v(g._ngay_dd_mm_yyyy(n.get('ngay_cap')))}",
            f"Nơi cấp: {_v(n.get('noi_cap'))}",
            f"Địa chỉ liên lạc: {_v(g._dia_chi_nguoi(n))}"]


class _VanBan:
    def __init__(self):
        self.d = g._van_ban_moi()
        self.so_dieu = 0
        self.so_chuong = 0

    def doan(self, text="", **kw):
        return g._doan(self.d, text, **kw)

    def chuong(self, ten):
        self.so_chuong += 1
        self.doan("-" * 50, can="giua", sau=2)
        self.doan(f"CHƯƠNG {self.so_chuong}", dam=True, can="giua", sau=2).paragraph_format.keep_with_next = True
        self.doan(ten.upper(), dam=True, can="giua", sau=8).paragraph_format.keep_with_next = True

    def dieu(self, tieu_de, *doan):
        self.so_dieu += 1
        self.doan(f"Điều {self.so_dieu}: {tieu_de}", dam=True, sau=4).paragraph_format.keep_with_next = True
        for x in doan:
            if isinstance(x, (list, tuple)):
                for y in x:
                    self.doan(y, can="deu", sau=4)
            else:
                self.doan(x, can="deu", sau=4)

    def bang(self, tieu_de_cot, hang, rong=None):
        tb = self.d.add_table(rows=1, cols=len(tieu_de_cot))
        tb.style = "Table Grid"
        for i, t in enumerate(tieu_de_cot):
            c = tb.rows[0].cells[i]
            c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            c.paragraphs[0].add_run(t).bold = True
        for r in hang:
            row = tb.add_row()
            for i, t in enumerate(r):
                row.cells[i].paragraphs[0].add_run(str(t))
                if i == 0 or (rong and i in rong):
                    row.cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        self.doan("", sau=2)
        return tb


def _bang_nganh(vb, nganh):
    hang = []
    for i, n in enumerate(nganh or [], 1):
        ten = (n.get("ten") or "").strip()
        ct = (n.get("chi_tiet") or "").strip()
        if ct:
            ct = ct if re.match(r"(?i)chi tiết\s*:", ct) else "Chi tiết: " + ct
            ten += "\n" + ct
        hang.append([i, ten, n.get("ma") or "", "X" if n.get("chinh") else ""])
    if not hang:
        hang = [["1", _CHAM, _CHAM, ""]]
    vb.bang(["Số tt", "Tên ngành nghề kinh doanh", "Mã ngành", "Ngành chính"], hang)


def _thoi_han(tt):
    n = str(tt.get("thoi_han") or "").strip()
    if n and re.fullmatch(r"\d+", n):
        return (f"1. Thời hạn hoạt động của công ty là: {n} năm kể từ ngày thành lập và được phép hoạt động theo quy định của pháp luật.\n"
                "2. Công ty có thể chấm dứt hoạt động trước thời hạn hoặc kéo dài thêm thời gian hoạt động theo quyết định của " + tt["co_quan_quyet_dinh"] + " hoặc theo quy định của pháp luật.").split("\n")
    return ["1. Công ty hoạt động không thời hạn kể từ ngày được cơ quan đăng ký kinh doanh cấp Giấy chứng nhận đăng ký doanh nghiệp.",
            "2. Công ty có thể chấm dứt hoạt động hoặc bị giải thể theo quyết định của " + tt["co_quan_quyet_dinh"] + " hoặc theo quy định của pháp luật."]


def _dau_dieu_le(vb, tt, loai_ten, dong_gioi_thieu):
    vb.doan("ĐIỀU LỆ", dam=True, can="giua", sau=0)
    vb.doan(_v(tt.get("ten")), dam=True, can="giua", sau=10)
    for x in dong_gioi_thieu:
        vb.doan(x, can="deu", sau=2)
    vb.doan("", sau=2)
    vb.doan(f"Nay quyết định hoạt động dưới loại hình {loai_ten} (dưới đây gọi tắt là Công ty) theo Luật Doanh nghiệp số 59/2020/QH14 được Quốc hội nước Cộng hòa xã hội chủ nghĩa "
            "Việt Nam thông qua ngày 17/6/2020 (đã được sửa đổi, bổ sung) và các điều khoản sau đây của Bản điều lệ này.", can="deu", thut=True, sau=8)


def _dieu_chung(vb, tt, tu_cach, trach_nhiem):
    vb.chuong("Điều khoản chung")
    vb.dieu("Tư cách pháp nhân, phạm vi trách nhiệm",
            "1. Công ty là một pháp nhân độc lập và có tư cách pháp nhân theo Luật pháp Việt Nam. Tất cả hoạt động của Công ty được điều chỉnh bởi Luật pháp Việt Nam và theo các quy định tại "
            "Giấy chứng nhận đăng ký doanh nghiệp, Điều lệ này và bất kỳ giấy phép hoặc cấp phép của Cơ quan Nhà nước cần thiết cho hoạt động kinh doanh của Công ty.",
            trach_nhiem)
    vb.dieu("Tên doanh nghiệp",
            f"Tên công ty viết bằng tiếng Việt (ghi bằng chữ in hoa): {_v(tt.get('ten'))}",
            f"Tên công ty viết bằng tiếng nước ngoài (nếu có): {_v(tt.get('ten_nuoc_ngoai'), '')}",
            f"Tên công ty viết tắt (nếu có): {_v(tt.get('ten_viet_tat'), '')}")
    vb.dieu("Trụ sở chính và địa chỉ chi nhánh, văn phòng đại diện",
            f"- Trụ sở chính của Công ty đặt tại số: {_v(tt.get('dia_chi'))}",
            "- Công ty có thể thành lập chi nhánh, văn phòng đại diện, địa điểm kinh doanh theo quyết định của " + tt["co_quan_quyet_dinh"] + " và đăng ký với cơ quan có thẩm quyền theo quy định của pháp luật.")
    vb.dieu("Ngành, nghề kinh doanh")
    _bang_nganh(vb, tt.get("nganh"))
    vb.dieu("Thời hạn hoạt động", _thoi_han(tt))
    dd = tt.get("nguoi_dd") or {}
    vb.dieu("Người đại diện theo pháp luật",
            f"1. Số lượng người đại diện theo pháp luật: Công ty có 01 người là người đại diện theo pháp luật, Chức danh: {_v(dd.get('chuc_danh'))}",
            _nguoi_dong(dd),
            ["2. Quyền và nghĩa vụ của người đại diện theo pháp luật:",
             "a) Thực hiện quyền và nghĩa vụ được giao một cách trung thực, cẩn trọng, tốt nhất nhằm bảo đảm lợi ích hợp pháp của doanh nghiệp;",
             "b) Trung thành với lợi ích của doanh nghiệp; không lạm dụng địa vị, chức vụ và sử dụng thông tin, bí quyết, cơ hội kinh doanh, tài sản khác của doanh nghiệp để tư lợi hoặc phục vụ lợi ích của tổ chức, cá nhân khác;",
             "c) Thông báo kịp thời, đầy đủ, chính xác cho doanh nghiệp về việc người đại diện đó, người có liên quan của họ làm chủ hoặc có cổ phần, phần vốn góp chi phối tại các doanh nghiệp khác."])


def _dieu_tai_chinh_giai_the(vb, tt, chu_the, chu_the_hoa):
    vb.chuong("Năm tài chính, phân phối lợi nhuận")
    vb.dieu("Năm tài chính",
            "1. Năm tài chính của Công ty bắt đầu từ ngày 1/1 dương lịch và chấm dứt vào ngày 31/12 hàng năm.",
            "2. Trường hợp công ty chuyển đổi loại hình doanh nghiệp, năm tài chính được tiếp tục theo quy định của pháp luật về kế toán, thuế.")
    vb.dieu("Phân phối lợi nhuận, lập quỹ, nguyên tắc xử lý lỗ trong kinh doanh",
            "1. Sau khi đã hoàn thành nghĩa vụ nộp thuế và các nghĩa vụ tài chính khác theo quy định của pháp luật, đã thanh toán đủ (hoặc đã dành phần thanh toán đủ) các khoản nợ và nghĩa vụ tài sản "
            "khác đã đến hạn phải trả, Công ty lập các loại quỹ theo quy định của pháp luật và " + tt["phan_loi_nhuan"],
            "2. Các vấn đề khác liên quan đến phân phối lợi nhuận được thực hiện theo quy định của pháp luật.",
            ["3. Trường hợp quyết toán năm tài chính bị lỗ, " + chu_the + " quyết định theo các hướng sau:", "a) Trích quỹ dự trữ để bù;",
             "b) Chuyển sang năm sau để trừ vào lợi nhuận của năm tài chính sau trước khi phân phối lợi nhuận."])
    vb.chuong("Tổ chức lại, giải thể")
    vb.dieu("Tổ chức lại, chuyển đổi",
            f"1. Công ty được chuyển đổi loại hình doanh nghiệp theo {tt.get('can_cu_chuyen_doi')} và hoạt động theo Điều lệ này kể từ ngày được cơ quan đăng ký kinh doanh cấp Giấy chứng nhận đăng ký doanh nghiệp.",
            "2. Công ty kế thừa toàn bộ quyền, nghĩa vụ, tài sản, hợp đồng, lao động của công ty trước chuyển đổi; mọi chi phí liên quan đến việc chuyển đổi được ghi vào chi phí của Công ty.",
            "3. Việc tổ chức lại doanh nghiệp (chia, tách, hợp nhất, sáp nhập hoặc chuyển đổi loại hình doanh nghiệp) Công ty thực hiện theo quy định của Luật Doanh nghiệp.")
    vb.dieu("Giải thể, trình tự giải thể và thủ tục thanh lý tài sản công ty",
            ["1. Công ty bị giải thể trong các trường hợp sau đây:",
             "a) Kết thúc thời hạn hoạt động đã ghi trong Điều lệ công ty mà không có quyết định gia hạn;",
             f"b) Theo nghị quyết, quyết định của {chu_the};",
             "c) Công ty không còn đủ số lượng thành viên tối thiểu theo quy định của Luật Doanh nghiệp trong thời hạn 06 tháng liên tục mà không làm thủ tục chuyển đổi loại hình doanh nghiệp;" if tt.get("loai") == "2tv" else
             "c) Bị thu hồi Giấy chứng nhận đăng ký doanh nghiệp, trừ trường hợp Luật Quản lý thuế có quy định khác;",
             "d) Bị thu hồi Giấy chứng nhận đăng ký doanh nghiệp, trừ trường hợp Luật Quản lý thuế có quy định khác." if tt.get("loai") == "2tv" else
             "d) Các trường hợp khác theo quy định của pháp luật."],
            ["2. Việc giải thể doanh nghiệp được thực hiện theo quy định sau đây:",
             f"Thông qua nghị quyết, quyết định giải thể doanh nghiệp. Nghị quyết, quyết định giải thể doanh nghiệp phải bao gồm các nội dung chủ yếu sau đây: a) Tên, địa chỉ trụ sở chính của doanh nghiệp; "
             "b) Lý do giải thể; c) Thời hạn, thủ tục thanh lý hợp đồng và thanh toán các khoản nợ của doanh nghiệp; d) Phương án xử lý các nghĩa vụ phát sinh từ hợp đồng lao động; "
             f"đ) Họ, tên, chữ ký của {tt['nguoi_ky_giai_the']}.",
             "Trong thời hạn 07 ngày làm việc kể từ ngày thông qua, quyết định giải thể phải được gửi đến Cơ quan đăng ký kinh doanh, cơ quan thuế, người lao động trong doanh nghiệp. "
             "Quyết định giải thể phải được đăng trên Cổng thông tin quốc gia về đăng ký doanh nghiệp và được niêm yết công khai tại trụ sở chính, chi nhánh, văn phòng đại diện của doanh nghiệp.",
             "Các khoản nợ của doanh nghiệp được thanh toán theo thứ tự: a) Các khoản nợ lương, trợ cấp thôi việc, bảo hiểm xã hội, bảo hiểm y tế, bảo hiểm thất nghiệp theo quy định của pháp luật và quyền lợi khác "
             "của người lao động theo thỏa ước lao động tập thể và hợp đồng lao động đã ký kết; b) Nợ thuế; c) Các khoản nợ khác. Sau khi đã thanh toán chi phí giải thể doanh nghiệp và các khoản nợ, phần còn lại thuộc về "
             f"{tt['nguoi_nhan_con_lai']}.",
             "Người đại diện theo pháp luật của doanh nghiệp gửi hồ sơ giải thể doanh nghiệp cho Cơ quan đăng ký kinh doanh trong thời hạn 05 ngày làm việc kể từ ngày thanh toán hết các khoản nợ của doanh nghiệp."])


def _dieu_thi_hanh(vb, tt):
    vb.chuong("Điều khoản thi hành")
    vb.dieu("Hiệu lực của Điều lệ", "Điều lệ này có hiệu lực kể từ ngày được cơ quan đăng ký kinh doanh cấp Giấy chứng nhận đăng ký doanh nghiệp.")
    vb.dieu("Thể thức sửa đổi, bổ sung Điều lệ",
            "1. Những vấn đề liên quan đến hoạt động của Công ty không được nêu trong Bản Điều lệ này sẽ do Luật Doanh nghiệp và các văn bản pháp luật liên quan khác điều chỉnh.",
            f"2. Khi muốn bổ sung, sửa đổi nội dung Điều lệ này, {tt['co_quan_quyet_dinh']} sẽ xem xét, quyết định theo thẩm quyền và tình hình thực tế.")
    vb.dieu("Điều khoản cuối cùng",
            "1. Trong trường hợp Điều lệ này có điều khoản trái pháp luật hoặc dẫn đến việc thi hành trái pháp luật, thì điều khoản đó không được thi hành và sẽ được xem xét sửa đổi theo quy định.")


def _anh_chu_tich(tt, chu_ky):
    """Chữ ký Chủ tịch HĐTV/HĐQT: lấy trong KHO CHỮ KÝ theo số giấy tờ của người đó; Chủ tịch là Giám đốc/người đại diện thì dùng chữ ký 'giám đốc' nếu kho chưa có."""
    ck = chu_ky or {}
    so = tt.get("chu_tich_cccd") or ""
    anh = ck.get("cccd:" + so) if len(so) >= 9 else None
    if not anh and tt.get("chu_tich") and (tt.get("chu_tich_la_giam_doc") or not so):
        anh = ck.get("giam_doc")
    return anh


def _ky(vb, tt, chuc_danh_ky, ten_ky, anh=None):
    n_chuong, n_dieu = vb.so_chuong, vb.so_dieu
    vb.doan(f"Bản điều lệ này đã được {tt['co_quan_quyet_dinh']} xem xét từng chương, từng điều và ký tên. Bản điều lệ này gồm {n_chuong} chương {n_dieu} điều, được lập thành 03 bản có giá trị như nhau: "
            "01 bản đăng ký tại cơ quan đăng ký kinh doanh, 01 bản lưu trữ tại trụ sở công ty, mỗi bên liên quan giữ 01 bản.", can="deu", sau=4)
    vb.doan("Mọi sự sao chép, trích lục phải được ký xác nhận của người đại diện theo pháp luật của công ty.", can="deu", sau=8)
    vb.doan(tt.get("ngay_ky") or "Ngày …… tháng …… năm ……", nghieng=True, can="giua", sau=2)
    vb.doan(chuc_danh_ky, dam=True, can="giua", sau=0)
    vb.doan("(Ký và ghi họ tên)", nghieng=True, can="giua", sau=0)
    g._dong_trong_ky(vb.d)
    pk = vb.doan(_v((ten_ky or "").upper(), ""), dam=True, can="giua", sau=0)
    g._gan_chu_ky(pk, anh, 8.0, 3.6)


# ---------------------------------------------------------------------------------------------------------------- 1 THÀNH VIÊN
def _dieu_le_1tv(tt, chu_ky):
    cs = (tt.get("chu_so_huu") or [{}])[0]
    tt = dict(tt, co_quan_quyet_dinh="Chủ sở hữu", phan_loi_nhuan="theo quyết định của Chủ sở hữu.", nguoi_ky_giai_the="Chủ sở hữu công ty",
              nguoi_nhan_con_lai="Chủ sở hữu công ty", loai="1tv")
    vb = _VanBan()
    _dau_dieu_le(vb, tt, "Công ty trách nhiệm hữu hạn một thành viên",
                 [f"Tôi là: {_v((cs.get('ho_ten') or '').upper())} - Sinh ngày: {_v(g._ngay_dd_mm_yyyy(cs.get('ngay_sinh')))}",
                  f"Dân tộc: {_v(cs.get('dan_toc'), 'Kinh')} - Quốc tịch: {_v(cs.get('quoc_tich'), 'Việt Nam')}",
                  f"Số giấy tờ pháp lý: {_v(cs.get('cccd'))}", f"Ngày cấp: {_v(g._ngay_dd_mm_yyyy(cs.get('ngay_cap')))} - Cơ quan cấp: {_v(cs.get('noi_cap'))}",
                  f"Địa chỉ liên lạc: {_v(g._dia_chi_nguoi(cs))}"])
    _dieu_chung(vb, tt, "", "2. Chủ sở hữu chịu trách nhiệm về các khoản nợ và các nghĩa vụ tài sản khác của doanh nghiệp trong phạm vi số vốn điều lệ của doanh nghiệp.")
    vb.chuong("Vốn và chủ sở hữu công ty")
    vb.dieu("Vốn điều lệ",
            f"1. Vốn của công ty được ấn định là: {_tien(tt.get('von'))}",
            f"2. Bao gồm tiền Việt Nam: {_tien(tt.get('von'))}",
            "Vốn điều lệ của Công ty là phần vốn góp của Chủ sở hữu đã được ghi nhận tại hồ sơ đăng ký doanh nghiệp, được kế thừa nguyên vẹn khi chuyển đổi loại hình doanh nghiệp.",
            "3. Chủ sở hữu Công ty cam đoan và chịu trách nhiệm trước pháp luật về mức giá của tất cả các phần vốn góp bằng tài sản trên.")
    vb.dieu("Thay đổi vốn điều lệ",
            "1. Công ty trách nhiệm hữu hạn một thành viên tăng vốn điều lệ thông qua việc chủ sở hữu công ty góp thêm vốn hoặc huy động thêm vốn góp của người khác. Chủ sở hữu công ty quyết định hình thức tăng và mức tăng vốn điều lệ.",
            "2. Trường hợp tăng vốn điều lệ bằng việc huy động thêm phần vốn góp của người khác, công ty phải tổ chức quản lý theo loại hình công ty trách nhiệm hữu hạn hai thành viên trở lên hoặc công ty cổ phần. "
            "Việc tổ chức quản lý công ty được thực hiện như sau:",
            "a) Trường hợp tổ chức quản lý theo loại hình công ty trách nhiệm hữu hạn hai thành viên trở lên thì công ty phải thông báo thay đổi nội dung đăng ký doanh nghiệp trong thời hạn 10 ngày kể từ ngày hoàn thành việc thay đổi vốn điều lệ;",
            "b) Trường hợp chuyển đổi thành công ty cổ phần thì công ty thực hiện theo quy định tại Điều 202 của Luật Doanh nghiệp.",
            "3. Công ty trách nhiệm hữu hạn một thành viên giảm vốn điều lệ trong các trường hợp sau đây:",
            "a) Hoàn trả một phần vốn góp cho chủ sở hữu công ty nếu công ty đã hoạt động kinh doanh liên tục từ 02 năm trở lên kể từ ngày đăng ký thành lập doanh nghiệp và bảo đảm thanh toán đủ các khoản nợ và nghĩa vụ tài sản khác sau khi đã hoàn trả phần vốn góp cho chủ sở hữu công ty;",
            "b) Vốn điều lệ không được chủ sở hữu công ty thanh toán đầy đủ và đúng hạn theo quy định của Luật Doanh nghiệp.")
    vb.dieu("Quyền của chủ sở hữu công ty",
            ["a) Quyết định nội dung Điều lệ công ty, sửa đổi, bổ sung Điều lệ công ty;", "b) Quyết định thành lập công ty con, góp vốn vào công ty khác;",
             "c) Quyết định tăng vốn điều lệ, chuyển nhượng một phần hoặc toàn bộ vốn điều lệ của công ty cho tổ chức, cá nhân khác;",
             "d) Quyết định việc sử dụng lợi nhuận sau khi đã hoàn thành nghĩa vụ thuế và các nghĩa vụ tài chính khác của công ty;",
             "đ) Quyết định tổ chức lại, giải thể và yêu cầu phá sản công ty;", "e) Thu hồi toàn bộ giá trị tài sản của công ty sau khi công ty hoàn thành giải thể hoặc phá sản;",
             "g) Quyền khác theo quy định của Luật Doanh nghiệp và Điều lệ công ty."])
    vb.dieu("Nghĩa vụ của chủ sở hữu",
            ["1. Góp đầy đủ và đúng hạn vốn điều lệ công ty.", "2. Tuân thủ Điều lệ công ty.",
             "3. Phải xác định và tách biệt tài sản của chủ sở hữu công ty và tài sản của công ty. Chủ sở hữu công ty là cá nhân phải tách biệt các chi tiêu của cá nhân và gia đình mình với các chi tiêu của Chủ tịch công ty và Giám đốc hoặc Tổng giám đốc.",
             "4. Tuân thủ quy định của pháp luật về hợp đồng và quy định khác của pháp luật có liên quan trong việc mua, bán, vay, cho vay, thuê, cho thuê, hợp đồng, giao dịch khác giữa công ty và chủ sở hữu công ty.",
             "5. Chủ sở hữu công ty chỉ được quyền rút vốn bằng cách chuyển nhượng một phần hoặc toàn bộ vốn điều lệ cho tổ chức hoặc cá nhân khác; trường hợp rút một phần hoặc toàn bộ vốn điều lệ đã góp ra khỏi công ty dưới hình thức khác thì chủ sở hữu và cá nhân, tổ chức có liên quan phải liên đới chịu trách nhiệm về các khoản nợ và nghĩa vụ tài sản khác của công ty.",
             "6. Chủ sở hữu công ty không được rút lợi nhuận khi công ty không thanh toán đủ các khoản nợ và nghĩa vụ tài sản khác đến hạn."])
    vb.dieu("Thực hiện quyền của chủ sở hữu công ty trong một số trường hợp đặc biệt",
            ["1. Trường hợp chủ sở hữu công ty chuyển nhượng, tặng cho một phần vốn điều lệ cho một hoặc nhiều tổ chức hoặc cá nhân khác hoặc kết nạp thêm thành viên mới, công ty phải tổ chức quản lý theo loại hình công ty trách nhiệm hữu hạn hai thành viên trở lên hoặc công ty cổ phần và đồng thời thực hiện đăng ký thay đổi nội dung đăng ký doanh nghiệp với Cơ quan đăng ký kinh doanh trong thời hạn 10 ngày, kể từ ngày hoàn thành việc chuyển nhượng, tặng cho hoặc kết nạp thành viên mới.",
             "2. Trường hợp chủ sở hữu công ty là cá nhân bị tạm giam, đang chấp hành hình phạt tù, đang chấp hành biện pháp xử lý hành chính tại cơ sở cai nghiện bắt buộc, cơ sở giáo dục bắt buộc thì ủy quyền cho người khác thực hiện một số hoặc tất cả quyền và nghĩa vụ của chủ sở hữu công ty.",
             "3. Trường hợp chủ sở hữu công ty là cá nhân chết thì người thừa kế theo di chúc hoặc theo pháp luật là chủ sở hữu hoặc thành viên công ty. Công ty phải tổ chức quản lý theo loại hình doanh nghiệp tương ứng và đăng ký thay đổi nội dung đăng ký doanh nghiệp trong thời hạn 10 ngày, kể từ ngày kết thúc việc giải quyết thừa kế. Trường hợp chủ sở hữu công ty là cá nhân chết mà không có người thừa kế, người thừa kế từ chối nhận thừa kế hoặc bị truất quyền thừa kế thì phần vốn góp của chủ sở hữu được giải quyết theo quy định của pháp luật về dân sự.",
             "4. Trường hợp chủ sở hữu công ty là cá nhân mất tích thì phần vốn góp của chủ sở hữu được giải quyết theo quy định của pháp luật về dân sự.",
             "5. Trường hợp chủ sở hữu công ty là cá nhân bị hạn chế hoặc bị mất năng lực hành vi dân sự, có khó khăn trong nhận thức, làm chủ hành vi thì quyền và nghĩa vụ của chủ sở hữu công ty được thực hiện thông qua người đại diện.",
             "6. Trường hợp chủ sở hữu công ty là tổ chức bị giải thể hoặc phá sản thì người nhận chuyển nhượng phần vốn góp của chủ sở hữu sẽ trở thành chủ sở hữu hoặc thành viên công ty. Công ty phải tổ chức hoạt động theo loại hình doanh nghiệp tương ứng và đăng ký thay đổi nội dung đăng ký doanh nghiệp trong thời hạn 10 ngày, kể từ ngày hoàn thành việc chuyển nhượng."])
    vb.chuong("Cơ cấu tổ chức quản lý công ty")
    ten_cs, ten_gd = _v((cs.get("ho_ten") or "").upper()), _v((tt.get("giam_doc") or "").upper())
    vb.dieu("Cơ cấu tổ chức quản lý", f"- Chủ tịch Công ty: {ten_cs}", f"- Giám đốc (hoặc Tổng giám đốc): {ten_gd}")
    vb.dieu("Chủ tịch công ty",
            ["1. Chủ tịch công ty nhân danh chủ sở hữu thực hiện các quyền và nghĩa vụ của chủ sở hữu công ty; nhân danh công ty thực hiện các quyền và nghĩa vụ của công ty, trừ quyền và nghĩa vụ của Giám đốc hoặc Tổng giám đốc; chịu trách nhiệm trước pháp luật và chủ sở hữu công ty về việc thực hiện các quyền và nghĩa vụ được giao theo quy định của Luật Doanh nghiệp, Điều lệ công ty và quy định khác của pháp luật có liên quan.",
             "2. Quyền, nghĩa vụ và chế độ làm việc của Chủ tịch công ty được thực hiện theo quy định tại Điều lệ công ty, Luật Doanh nghiệp và quy định khác của pháp luật có liên quan.",
             "3. Quyết định của Chủ tịch công ty về thực hiện quyền và nghĩa vụ của chủ sở hữu công ty có hiệu lực kể từ ngày được chủ sở hữu công ty phê duyệt."])
    vb.dieu("Giám đốc, Tổng giám đốc",
            ["1. Chủ tịch công ty bổ nhiệm hoặc thuê Giám đốc hoặc Tổng giám đốc với nhiệm kỳ không quá 05 năm để điều hành hoạt động kinh doanh hằng ngày của công ty. Giám đốc hoặc Tổng giám đốc chịu trách nhiệm trước pháp luật và Chủ tịch công ty về việc thực hiện quyền và nghĩa vụ của mình. Chủ tịch công ty có thể kiêm Giám đốc hoặc Tổng giám đốc.",
             "2. Giám đốc hoặc Tổng giám đốc có các quyền và nghĩa vụ sau đây:", "a) Tổ chức thực hiện nghị quyết, quyết định của Chủ tịch công ty;",
             "b) Quyết định các vấn đề liên quan đến hoạt động kinh doanh hằng ngày của công ty;", "c) Tổ chức thực hiện kế hoạch kinh doanh và phương án đầu tư của công ty;",
             "d) Ban hành quy chế quản lý nội bộ của công ty;", "đ) Bổ nhiệm, miễn nhiệm, bãi nhiệm người quản lý trong công ty, trừ các chức danh thuộc thẩm quyền của Chủ tịch công ty;",
             "e) Ký hợp đồng nhân danh công ty, trừ trường hợp thuộc thẩm quyền của Chủ tịch công ty;", "g) Kiến nghị phương án cơ cấu tổ chức công ty;",
             "h) Trình báo cáo tài chính hằng năm lên Chủ tịch công ty;", "i) Kiến nghị phương án sử dụng lợi nhuận hoặc xử lý lỗ trong kinh doanh;", "k) Tuyển dụng lao động;",
             "l) Quyền và nghĩa vụ khác được quy định tại hợp đồng lao động mà Giám đốc hoặc Tổng giám đốc ký với Chủ tịch công ty.",
             "3. Giám đốc hoặc Tổng giám đốc phải có các tiêu chuẩn và điều kiện sau đây:", "a) Có năng lực hành vi dân sự đầy đủ và không thuộc đối tượng quy định tại khoản 2 Điều 17 của Luật Doanh nghiệp;",
             "b) Có trình độ chuyên môn, kinh nghiệm thực tế trong quản trị kinh doanh của công ty."])
    vb.dieu("Trách nhiệm của Chủ tịch công ty, Giám đốc, Tổng giám đốc",
            ["1. Tuân thủ pháp luật, Điều lệ công ty, quyết định của chủ sở hữu công ty trong việc thực hiện các quyền và nghĩa vụ được giao.",
             "2. Thực hiện các quyền và nghĩa vụ được giao một cách trung thực, cẩn trọng, tốt nhất nhằm bảo đảm lợi ích hợp pháp của công ty và chủ sở hữu công ty.",
             "3. Trung thành với lợi ích của công ty và chủ sở hữu công ty; không lạm dụng địa vị, chức vụ và sử dụng thông tin, bí quyết, cơ hội kinh doanh, tài sản khác của công ty để tư lợi hoặc phục vụ lợi ích của tổ chức, cá nhân khác.",
             "4. Thông báo kịp thời, đầy đủ và chính xác cho chủ sở hữu công ty về doanh nghiệp mà mình làm chủ hoặc có cổ phần, phần vốn góp chi phối và doanh nghiệp mà người có liên quan của mình làm chủ, cùng sở hữu hoặc sở hữu riêng cổ phần, phần vốn góp chi phối. Thông báo phải được lưu giữ tại trụ sở chính của công ty.",
             "5. Người đại diện theo pháp luật của doanh nghiệp chịu trách nhiệm cá nhân đối với thiệt hại cho doanh nghiệp do vi phạm trách nhiệm quy định tại Điều này."])
    vb.dieu("Thù lao, tiền lương, thưởng và lợi ích khác của người quản lý công ty",
            ["1. Người quản lý công ty được hưởng thù lao, tiền lương, thưởng và lợi ích khác theo kết quả và hiệu quả kinh doanh của công ty.",
             "2. Chủ sở hữu công ty quyết định mức thù lao, tiền lương, thưởng và lợi ích khác của Chủ tịch công ty. Thù lao, tiền lương, thưởng và lợi ích khác của người quản lý công ty được tính vào chi phí kinh doanh theo quy định của pháp luật về thuế thu nhập doanh nghiệp, pháp luật có liên quan và được thể hiện thành mục riêng trong báo cáo tài chính hằng năm của công ty.",
             "3. Thù lao, tiền lương, thưởng và lợi ích khác của người quản lý công ty có thể do chủ sở hữu công ty chi trả trực tiếp theo quy định của pháp luật hiện hành."])
    vb.dieu("Nguyên tắc giải quyết tranh chấp nội bộ",
            ["1. Các tranh chấp nội bộ giữa Công ty liên quan đến thành lập, hoạt động, giải thể Công ty trước hết phải được giải quyết thông qua thương lượng, hòa giải.",
             "2. Trường hợp giải quyết tranh chấp nội bộ theo phương thức thương lượng, hòa giải không đạt được kết quả thì bất kỳ bên nào cũng có quyền đưa tranh chấp ra Tòa án có thẩm quyền để giải quyết."])
    _dieu_tai_chinh_giai_the(vb, tt, "Chủ sở hữu", "Chủ sở hữu")
    _dieu_thi_hanh(vb, tt)
    _ky(vb, tt, "Chủ sở hữu", cs.get("ho_ten"), (chu_ky or {}).get("cccd:" + re.sub(r"\D", "", cs.get("cccd") or "")) if len(re.sub(r"\D", "", cs.get("cccd") or "")) >= 9 else None)
    return vb.d


# ---------------------------------------------------------------------------------------------------------------- 2 THÀNH VIÊN TRỞ LÊN
def _dieu_le_2tv(tt, chu_ky):
    tvs = tt.get("thanh_vien") or []
    tt = dict(tt, co_quan_quyet_dinh="Hội đồng thành viên", phan_loi_nhuan="chia cho các thành viên tương ứng với phần vốn góp của họ trong vốn điều lệ công ty.",
              nguoi_ky_giai_the="Chủ tịch Hội đồng thành viên", nguoi_nhan_con_lai="các thành viên công ty tương ứng với tỷ lệ phần vốn góp", loai="2tv")
    vb = _VanBan()
    _dau_dieu_le(vb, tt, "Công ty trách nhiệm hữu hạn hai thành viên trở lên", ["Danh sách các thành viên sáng lập/góp vốn của Công ty được nêu tại Điều 8 của Điều lệ này."])
    _dieu_chung(vb, tt, "", "2. Thành viên công ty chịu trách nhiệm về các khoản nợ và các nghĩa vụ tài sản khác của doanh nghiệp trong phạm vi số vốn đã cam kết góp vào doanh nghiệp.")
    vb.chuong("Vốn và thành viên công ty")
    vb.dieu("Vốn điều lệ",
            f"1. Vốn điều lệ của Công ty được ấn định là: {_tien(tt.get('von'))}",
            f"2. Bao gồm tiền Việt Nam: {_tien(tt.get('von'))}",
            "3. Vốn điều lệ là tổng giá trị phần vốn góp của các thành viên cam kết góp, được ghi nhận tại hồ sơ đăng ký doanh nghiệp và được kế thừa khi chuyển đổi loại hình doanh nghiệp.")
    vb.dieu("Danh sách thành viên, phần vốn góp và tỷ lệ phần vốn góp")
    hang = []
    for i, n in enumerate(tvs, 1):
        hang.append([i, f"{(n.get('ho_ten') or '').upper()}\nSinh ngày: {g._ngay_dd_mm_yyyy(n.get('ngay_sinh')) or _CHAM}\nSố giấy tờ: {n.get('cccd') or _CHAM}\nĐịa chỉ: {g._dia_chi_nguoi(n) or _CHAM}",
                     _tien(n.get("von")), (n.get("ty_le") or "") or _CHAM])
    if not hang:
        hang = [["1", _CHAM, _CHAM, _CHAM]]
    vb.bang(["Số tt", "Thành viên (họ tên, ngày sinh, giấy tờ pháp lý, địa chỉ)", "Phần vốn góp", "Tỷ lệ (%)"], hang)
    vb.dieu("Góp vốn và cấp giấy chứng nhận phần vốn góp",
            ["1. Thành viên phải góp vốn cho công ty đủ và đúng loại tài sản đã cam kết khi đăng ký thành lập doanh nghiệp trong thời hạn 90 ngày kể từ ngày được cấp Giấy chứng nhận đăng ký doanh nghiệp, "
             "không kể thời gian vận chuyển, nhập khẩu tài sản góp vốn, thực hiện thủ tục hành chính để chuyển quyền sở hữu tài sản. Trường hợp phần vốn góp đã được góp đủ trước khi chuyển đổi loại hình doanh nghiệp thì được ghi nhận nguyên vẹn.",
             "2. Công ty có trách nhiệm lập sổ đăng ký thành viên và cấp giấy chứng nhận phần vốn góp cho thành viên theo quy định của Luật Doanh nghiệp."])
    vb.dieu("Chuyển nhượng phần vốn góp",
            ["1. Thành viên có quyền chuyển nhượng một phần hoặc toàn bộ phần vốn góp của mình cho người khác theo quy định của Luật Doanh nghiệp: phải chào bán phần vốn góp đó cho các thành viên còn lại theo tỷ lệ tương ứng với phần vốn góp của họ trong công ty với cùng điều kiện chào bán; "
             "chỉ được chuyển nhượng cho người không phải là thành viên nếu các thành viên còn lại của công ty không mua hoặc không mua hết trong thời hạn 30 ngày kể từ ngày chào bán.",
             "2. Thành viên chuyển nhượng vẫn có các quyền và nghĩa vụ đối với công ty tương ứng với phần vốn góp cho đến khi thông tin của người nhận chuyển nhượng được ghi đầy đủ vào sổ đăng ký thành viên."])
    vb.dieu("Mua lại phần vốn góp",
            "Thành viên đã biểu quyết không tán thành đối với nghị quyết, quyết định của Hội đồng thành viên về sửa đổi, bổ sung các nội dung trong Điều lệ công ty liên quan đến quyền và nghĩa vụ của thành viên, hội đồng thành viên; tổ chức lại công ty; "
            "hoặc trường hợp khác theo Điều lệ có quyền yêu cầu công ty mua lại phần vốn góp của mình theo quy định của Luật Doanh nghiệp.")
    vb.dieu("Quyền của thành viên",
            ["1. Tham dự họp Hội đồng thành viên, thảo luận, kiến nghị, biểu quyết các vấn đề thuộc thẩm quyền của Hội đồng thành viên.",
             "2. Có số phiếu biểu quyết tương ứng với phần vốn góp, trừ trường hợp Luật Doanh nghiệp có quy định khác.",
             "3. Xem xét, tra cứu, sao chép hoặc trích lục sổ đăng ký thành viên, biên bản họp, nghị quyết, quyết định của Hội đồng thành viên, hợp đồng, giao dịch, sổ sách kế toán, báo cáo tài chính hằng năm và tài liệu khác của công ty.",
             "4. Được chia lợi nhuận tương ứng với phần vốn góp sau khi công ty đã hoàn thành nghĩa vụ thuế và các nghĩa vụ tài chính khác theo quy định của pháp luật.",
             "5. Được chia giá trị tài sản còn lại của công ty tương ứng với phần vốn góp khi công ty giải thể hoặc phá sản.",
             "6. Được ưu tiên góp thêm vốn vào công ty khi công ty tăng vốn điều lệ; được quyền chuyển nhượng, tặng cho, để thừa kế phần vốn góp theo quy định của Luật Doanh nghiệp và Điều lệ này.",
             "7. Các quyền khác theo quy định của Luật Doanh nghiệp và Điều lệ này."])
    vb.dieu("Nghĩa vụ của thành viên",
            ["1. Góp vốn đầy đủ, đúng hạn theo đúng cam kết; chịu trách nhiệm về các khoản nợ và nghĩa vụ tài sản khác của công ty trong phạm vi số vốn đã cam kết góp.",
             "2. Không được rút vốn đã góp ra khỏi công ty dưới mọi hình thức, trừ trường hợp được công ty hoặc thành viên khác mua lại phần vốn góp hoặc chuyển nhượng theo quy định.",
             "3. Tuân thủ Điều lệ công ty; chấp hành nghị quyết, quyết định của Hội đồng thành viên.",
             "4. Chịu trách nhiệm cá nhân khi nhân danh công ty để thực hiện hành vi vi phạm pháp luật, tiến hành kinh doanh hoặc giao dịch khác không nhằm phục vụ lợi ích của công ty và gây thiệt hại cho người khác.",
             "5. Các nghĩa vụ khác theo quy định của Luật Doanh nghiệp."])
    vb.chuong("Cơ cấu tổ chức quản lý công ty")
    ct = _v((tt.get("chu_tich") or "").upper())
    vb.dieu("Cơ cấu tổ chức quản lý", "Cơ cấu tổ chức quản lý của Công ty gồm: Hội đồng thành viên, Chủ tịch Hội đồng thành viên, Giám đốc hoặc Tổng giám đốc.",
            f"- Chủ tịch Hội đồng thành viên: {ct}", f"- Giám đốc (hoặc Tổng giám đốc): {_v((tt.get('giam_doc') or '').upper())}")
    vb.dieu("Hội đồng thành viên",
            ["1. Hội đồng thành viên gồm tất cả các thành viên công ty, là cơ quan quyết định cao nhất của công ty.",
             "2. Hội đồng thành viên có quyền và nghĩa vụ: a) Quyết định chiến lược phát triển và kế hoạch kinh doanh hằng năm của công ty; b) Quyết định tăng hoặc giảm vốn điều lệ, quyết định thời điểm và phương thức huy động thêm vốn; "
             "c) Quyết định phương thức đầu tư và dự án đầu tư có giá trị trên 50% tổng giá trị tài sản được ghi trong báo cáo tài chính gần nhất của công ty hoặc một tỷ lệ khác nhỏ hơn quy định tại Điều lệ công ty; "
             "d) Quyết định giải pháp phát triển thị trường, tiếp thị và công nghệ; đ) Bầu, miễn nhiệm, bãi nhiệm Chủ tịch Hội đồng thành viên; bổ nhiệm, miễn nhiệm, bãi nhiệm, ký và chấm dứt hợp đồng đối với Giám đốc hoặc Tổng giám đốc; "
             "e) Quyết định mức lương, thù lao, thưởng và lợi ích khác đối với Chủ tịch Hội đồng thành viên, Giám đốc hoặc Tổng giám đốc; g) Thông qua báo cáo tài chính hằng năm, phương án sử dụng và phân chia lợi nhuận hoặc phương án xử lý lỗ của công ty; "
             "h) Quyết định cơ cấu tổ chức quản lý công ty; thành lập công ty con, chi nhánh, văn phòng đại diện; i) Sửa đổi, bổ sung Điều lệ công ty; k) Quyết định tổ chức lại, giải thể hoặc yêu cầu phá sản công ty; "
             "l) Quyền và nghĩa vụ khác theo quy định của Luật Doanh nghiệp và Điều lệ này."])
    vb.dieu("Chủ tịch Hội đồng thành viên",
            ["1. Chủ tịch Hội đồng thành viên do Hội đồng thành viên bầu. Chủ tịch Hội đồng thành viên có thể kiêm Giám đốc hoặc Tổng giám đốc công ty.",
             "2. Chủ tịch Hội đồng thành viên có các quyền và nghĩa vụ: chuẩn bị chương trình, kế hoạch hoạt động của Hội đồng thành viên; chuẩn bị chương trình, nội dung, tài liệu họp; triệu tập và chủ tọa cuộc họp Hội đồng thành viên; "
             "giám sát việc tổ chức thực hiện các nghị quyết, quyết định của Hội đồng thành viên; thay mặt Hội đồng thành viên ký các nghị quyết, quyết định của Hội đồng thành viên; các quyền và nghĩa vụ khác theo quy định của Luật Doanh nghiệp.",
             "3. Nhiệm kỳ của Chủ tịch Hội đồng thành viên không quá 05 năm."])
    vb.dieu("Triệu tập, điều kiện và thể thức họp Hội đồng thành viên",
            ["1. Hội đồng thành viên họp ít nhất mỗi năm một lần hoặc khi cần thiết theo yêu cầu của Chủ tịch Hội đồng thành viên, Giám đốc hoặc thành viên (nhóm thành viên) sở hữu trên 10% vốn điều lệ. Thông báo mời họp được gửi cho các thành viên ít nhất 03 ngày làm việc trước ngày họp, kèm chương trình, nội dung và tài liệu họp.",
             "2. Cuộc họp Hội đồng thành viên được tiến hành khi có số thành viên dự họp sở hữu ít nhất 65% vốn điều lệ. Trường hợp cuộc họp lần thứ nhất không đủ điều kiện thì được triệu tập lần thứ hai trong thời hạn 15 ngày kể từ ngày dự định họp lần thứ nhất, "
             "cuộc họp lần thứ hai được tiến hành khi có số thành viên dự họp sở hữu ít nhất 50% vốn điều lệ. Trường hợp cuộc họp lần thứ hai không đủ điều kiện thì được triệu tập lần thứ ba, và được tiến hành không phụ thuộc số thành viên dự họp và số vốn điều lệ được đại diện bởi số thành viên dự họp.",
             "3. Nghị quyết, quyết định của Hội đồng thành viên được thông qua tại cuộc họp khi được số thành viên đại diện ít nhất 65% tổng số vốn góp của các thành viên dự họp chấp thuận; riêng quyết định về sửa đổi, bổ sung Điều lệ, tổ chức lại công ty, "
             "bán tài sản có giá trị từ 50% tổng giá trị tài sản trở lên được ghi trong báo cáo tài chính gần nhất của công ty (hoặc tỷ lệ khác nhỏ hơn theo Điều lệ) phải được số thành viên đại diện ít nhất 75% tổng số vốn góp của các thành viên dự họp chấp thuận.",
             "4. Hội đồng thành viên có thể thông qua nghị quyết, quyết định bằng hình thức lấy ý kiến bằng văn bản theo quy định của Luật Doanh nghiệp. Nghị quyết, quyết định của Hội đồng thành viên có hiệu lực kể từ ngày được thông qua hoặc từ ngày ghi trong nghị quyết, quyết định đó, "
             "và phải được ghi vào biên bản, lưu giữ tại trụ sở chính của công ty."])
    vb.dieu("Giám đốc, Tổng giám đốc",
            ["1. Hội đồng thành viên bổ nhiệm hoặc thuê Giám đốc hoặc Tổng giám đốc với nhiệm kỳ không quá 05 năm để điều hành hoạt động kinh doanh hằng ngày của công ty. Giám đốc hoặc Tổng giám đốc chịu trách nhiệm trước pháp luật và Hội đồng thành viên về việc thực hiện quyền và nghĩa vụ của mình.",
             "2. Giám đốc hoặc Tổng giám đốc có các quyền và nghĩa vụ: tổ chức thực hiện nghị quyết, quyết định của Hội đồng thành viên; quyết định các vấn đề liên quan đến hoạt động kinh doanh hằng ngày; tổ chức thực hiện kế hoạch kinh doanh và phương án đầu tư; "
             "ban hành quy chế quản lý nội bộ; bổ nhiệm, miễn nhiệm, bãi nhiệm các chức danh quản lý trong công ty trừ các chức danh thuộc thẩm quyền của Hội đồng thành viên; ký hợp đồng nhân danh công ty; kiến nghị phương án cơ cấu tổ chức công ty; "
             "trình báo cáo tài chính hằng năm lên Hội đồng thành viên; kiến nghị phương án sử dụng lợi nhuận hoặc xử lý lỗ; tuyển dụng lao động; các quyền và nghĩa vụ khác theo hợp đồng lao động và Điều lệ này.",
             "3. Giám đốc hoặc Tổng giám đốc phải có năng lực hành vi dân sự đầy đủ, không thuộc đối tượng quy định tại khoản 2 Điều 17 của Luật Doanh nghiệp, có trình độ chuyên môn, kinh nghiệm thực tế trong quản trị kinh doanh của công ty."])
    vb.dieu("Trách nhiệm của người quản lý công ty",
            ["1. Tuân thủ pháp luật, Điều lệ công ty, nghị quyết, quyết định của Hội đồng thành viên trong việc thực hiện các quyền và nghĩa vụ được giao.",
             "2. Thực hiện các quyền và nghĩa vụ một cách trung thực, cẩn trọng, tốt nhất nhằm bảo đảm lợi ích hợp pháp của công ty và các thành viên; trung thành với lợi ích của công ty; không lạm dụng địa vị, chức vụ và sử dụng thông tin, bí quyết, cơ hội kinh doanh, tài sản khác của công ty để tư lợi.",
             "3. Thông báo kịp thời, đầy đủ, chính xác cho công ty về doanh nghiệp mà mình và người có liên quan làm chủ hoặc có phần vốn góp chi phối; thông báo được lưu giữ tại trụ sở chính của công ty."])
    vb.dieu("Nguyên tắc giải quyết tranh chấp nội bộ",
            ["1. Các tranh chấp nội bộ giữa công ty và thành viên, giữa các thành viên liên quan đến thành lập, hoạt động, giải thể công ty trước hết phải được giải quyết thông qua thương lượng, hòa giải.",
             "2. Nếu không đạt được kết quả thương lượng, hòa giải thì bất kỳ bên nào cũng có quyền đưa tranh chấp ra Tòa án có thẩm quyền để giải quyết."])
    _dieu_tai_chinh_giai_the(vb, tt, "Hội đồng thành viên", "Hội đồng thành viên")
    _dieu_thi_hanh(vb, tt)
    _ky(vb, tt, "CHỦ TỊCH HỘI ĐỒNG THÀNH VIÊN", tt.get("chu_tich"), _anh_chu_tich(tt, chu_ky))
    # chữ ký từng thành viên
    vb.doan("Các thành viên ký tên:", dam=True, sau=2)
    tb = vb.d.add_table(rows=1, cols=2)
    tb.style = "Table Grid"
    tb.rows[0].cells[0].paragraphs[0].add_run("Họ và tên thành viên").bold = True
    tb.rows[0].cells[1].paragraphs[0].add_run("Chữ ký").bold = True
    for n in tvs:
        r = tb.add_row()
        r.cells[0].paragraphs[0].add_run((n.get("ho_ten") or "").upper())
        so = re.sub(r"\D", "", n.get("cccd") or "")
        g._gan_chu_ky(r.cells[1].paragraphs[0], (chu_ky or {}).get("cccd:" + so) if len(so) >= 9 else None, 3.0, 1.6)
        r.height = Cm(1.8)
    return vb.d


# ---------------------------------------------------------------------------------------------------------------- CÔNG TY CỔ PHẦN
def _dieu_le_cp(tt, chu_ky):
    cds = tt.get("co_dong") or []
    tt = dict(tt, co_quan_quyet_dinh="Đại hội đồng cổ đông", phan_loi_nhuan="chia cho các cổ đông theo tỷ lệ cổ phần sở hữu theo nghị quyết của Đại hội đồng cổ đông.",
              nguoi_ky_giai_the="Chủ tịch Hội đồng quản trị", nguoi_nhan_con_lai="các cổ đông theo tỷ lệ cổ phần sở hữu", loai="cp")
    vb = _VanBan()
    _dau_dieu_le(vb, tt, "Công ty cổ phần", ["Danh sách cổ đông sáng lập và cổ phần của các cổ đông được nêu tại Điều 8 của Điều lệ này."])
    _dieu_chung(vb, tt, "", "2. Cổ đông chịu trách nhiệm về các khoản nợ và nghĩa vụ tài sản khác của công ty trong phạm vi số vốn đã góp vào công ty.")
    menh = tt.get("menh_gia") or 10000
    vb.chuong("Vốn điều lệ, cổ phần, cổ đông")
    tong_cp = (tt.get("von") or 0) // menh if tt.get("von") else 0
    vb.dieu("Vốn điều lệ, cổ phần",
            f"1. Vốn điều lệ của Công ty được ấn định là: {_tien(tt.get('von'))}",
            f"2. Vốn điều lệ được chia thành {f'{tong_cp:,}'.replace(',', '.') if tong_cp else _CHAM} cổ phần phổ thông, mệnh giá mỗi cổ phần là {f'{menh:,}'.replace(',', '.')} đồng.",
            "3. Vốn điều lệ là tổng giá trị mệnh giá cổ phần đã bán và được ghi nhận tại hồ sơ đăng ký doanh nghiệp, được kế thừa khi chuyển đổi loại hình doanh nghiệp.")
    vb.dieu("Danh sách cổ đông và cổ phần")
    hang = []
    for i, n in enumerate(cds, 1):
        cp = (n.get("von") or 0) // menh if n.get("von") else 0
        hang.append([i, f"{(n.get('ho_ten') or '').upper()}\nSố giấy tờ: {n.get('cccd') or _CHAM}\nĐịa chỉ: {g._dia_chi_nguoi(n) or _CHAM}",
                     f"{cp:,}".replace(",", ".") if cp else _CHAM, _tien(n.get("von")), (n.get("ty_le") or "") or _CHAM])
    if not hang:
        hang = [["1", _CHAM, _CHAM, _CHAM, _CHAM]]
    vb.bang(["Số tt", "Cổ đông (họ tên, giấy tờ pháp lý, địa chỉ)", "Số cổ phần phổ thông", "Giá trị cổ phần", "Tỷ lệ (%)"], hang)
    vb.dieu("Chuyển nhượng cổ phần",
            ["1. Cổ phần phổ thông được tự do chuyển nhượng, trừ trường hợp hạn chế theo quy định của Luật Doanh nghiệp và Điều lệ này. Cổ phần của cổ đông sáng lập chỉ được chuyển nhượng cho cổ đông sáng lập khác hoặc cho người không phải cổ đông sáng lập khi được Đại hội đồng cổ đông chấp thuận trong 03 năm đầu kể từ ngày công ty được cấp Giấy chứng nhận đăng ký doanh nghiệp, theo quy định của Luật Doanh nghiệp.",
             "2. Việc chuyển nhượng được thực hiện bằng hợp đồng hoặc giao dịch trên thị trường chứng khoán (nếu có) và được ghi vào sổ đăng ký cổ đông của công ty."])
    vb.dieu("Quyền của cổ đông",
            ["1. Tham dự và phát biểu trong các cuộc họp Đại hội đồng cổ đông và thực hiện quyền biểu quyết trực tiếp hoặc thông qua đại diện được ủy quyền; mỗi cổ phần phổ thông có một phiếu biểu quyết.",
             "2. Nhận cổ tức theo nghị quyết của Đại hội đồng cổ đông; ưu tiên mua cổ phần mới chào bán tương ứng với tỷ lệ cổ phần phổ thông mà họ sở hữu; tự do chuyển nhượng cổ phần.",
             "3. Xem xét, tra cứu và trích lục thông tin trong danh sách cổ đông có quyền biểu quyết; yêu cầu sửa đổi thông tin không chính xác; xem xét, tra cứu, sao chép Điều lệ, biên bản họp và nghị quyết của Đại hội đồng cổ đông.",
             "4. Khi công ty giải thể hoặc phá sản, được nhận một phần tài sản còn lại tương ứng với số cổ phần góp vốn vào công ty.",
             "5. Cổ đông hoặc nhóm cổ đông sở hữu từ 5% tổng số cổ phần phổ thông trở lên (hoặc tỷ lệ nhỏ hơn theo Điều lệ) có các quyền theo quy định của Luật Doanh nghiệp (đề cử người vào Hội đồng quản trị, yêu cầu triệu tập họp, kiểm tra sổ sách...).",
             "6. Các quyền khác theo quy định của Luật Doanh nghiệp và Điều lệ này."])
    vb.dieu("Nghĩa vụ của cổ đông",
            ["1. Thanh toán đủ và đúng hạn số cổ phần đã đăng ký mua; chịu trách nhiệm về các khoản nợ và nghĩa vụ tài sản khác của công ty trong phạm vi số vốn đã góp.",
             "2. Không được rút vốn đã góp bằng cổ phần phổ thông ra khỏi công ty dưới mọi hình thức, trừ trường hợp được công ty hoặc người khác mua lại cổ phần.",
             "3. Tuân thủ Điều lệ công ty và quy chế quản lý nội bộ; chấp hành nghị quyết, quyết định của Đại hội đồng cổ đông, Hội đồng quản trị.",
             "4. Các nghĩa vụ khác theo quy định của Luật Doanh nghiệp."])
    vb.chuong("Cơ cấu tổ chức quản lý công ty")
    vb.dieu("Cơ cấu tổ chức quản lý",
            "Cơ cấu tổ chức quản lý của Công ty gồm: Đại hội đồng cổ đông, Hội đồng quản trị, Giám đốc hoặc Tổng giám đốc và Ban kiểm soát (hoặc Ủy ban kiểm toán trong Hội đồng quản trị) nếu thuộc trường hợp bắt buộc theo quy định của Luật Doanh nghiệp.",
            f"- Chủ tịch Hội đồng quản trị: {_v((tt.get('chu_tich') or '').upper())}", f"- Giám đốc (hoặc Tổng giám đốc): {_v((tt.get('giam_doc') or '').upper())}")
    vb.dieu("Đại hội đồng cổ đông",
            ["1. Đại hội đồng cổ đông gồm tất cả cổ đông có quyền biểu quyết, là cơ quan có thẩm quyền cao nhất của công ty. Đại hội đồng cổ đông họp thường niên mỗi năm một lần trong thời hạn 04 tháng kể từ ngày kết thúc năm tài chính, và họp bất thường khi cần thiết.",
             "2. Đại hội đồng cổ đông có quyền và nhiệm vụ: thông qua định hướng phát triển; quyết định loại cổ phần và tổng số cổ phần của từng loại được quyền chào bán; bầu, miễn nhiệm, bãi nhiệm thành viên Hội đồng quản trị, Kiểm soát viên; "
             "quyết định đầu tư hoặc bán tài sản có giá trị từ 35% tổng giá trị tài sản trở lên (hoặc tỷ lệ khác theo Điều lệ); sửa đổi, bổ sung Điều lệ; thông qua báo cáo tài chính hằng năm; quyết định mua lại cổ phần; xem xét xử lý vi phạm của thành viên Hội đồng quản trị, Kiểm soát viên; "
             "quyết định tổ chức lại, giải thể công ty; các quyền khác theo quy định của Luật Doanh nghiệp.",
             "3. Cuộc họp Đại hội đồng cổ đông được tiến hành khi có số cổ đông dự họp đại diện từ 50% tổng số phiếu biểu quyết trở lên; nếu không đủ điều kiện thì triệu tập lần thứ hai (từ 33%) và lần thứ ba (không phụ thuộc tỷ lệ) theo quy định của Luật Doanh nghiệp.",
             "4. Nghị quyết được thông qua khi được số cổ đông đại diện trên 50% tổng số phiếu biểu quyết của tất cả cổ đông dự họp tán thành; riêng quyết định về loại cổ phần và số lượng cổ phần chào bán, sửa đổi Điều lệ, tổ chức lại, giải thể, đầu tư hoặc bán tài sản từ 35% tổng giá trị tài sản (hoặc tỷ lệ khác theo Điều lệ) phải được ít nhất 65% tổng số phiếu biểu quyết của cổ đông dự họp tán thành."])
    vb.dieu("Hội đồng quản trị",
            ["1. Hội đồng quản trị là cơ quan quản lý công ty, có toàn quyền nhân danh công ty để quyết định, thực hiện quyền và nghĩa vụ của công ty không thuộc thẩm quyền của Đại hội đồng cổ đông. Hội đồng quản trị có từ 03 đến 11 thành viên; nhiệm kỳ không quá 05 năm.",
             "2. Hội đồng quản trị có quyền và nghĩa vụ: quyết định chiến lược, kế hoạch phát triển trung hạn và kế hoạch kinh doanh hằng năm; kiến nghị loại cổ phần và tổng số cổ phần được quyền chào bán; quyết định bán cổ phần mới trong phạm vi số cổ phần được quyền chào bán; "
             "quyết định phương án đầu tư; giải pháp phát triển thị trường; bổ nhiệm, miễn nhiệm, bãi nhiệm Giám đốc hoặc Tổng giám đốc; quyết định cơ cấu tổ chức, quy chế quản lý nội bộ; trình báo cáo tài chính hằng năm; kiến nghị mức cổ tức; các quyền khác theo Luật Doanh nghiệp.",
             "3. Chủ tịch Hội đồng quản trị do Hội đồng quản trị bầu; có thể kiêm Giám đốc hoặc Tổng giám đốc nếu Điều lệ không quy định khác và theo quy định của Luật Doanh nghiệp.",
             "4. Cuộc họp Hội đồng quản trị được tiến hành khi có từ 3/4 tổng số thành viên trở lên dự họp; nghị quyết được thông qua khi được đa số thành viên dự họp tán thành, mỗi thành viên có một phiếu biểu quyết."])
    vb.dieu("Giám đốc, Tổng giám đốc",
            ["1. Hội đồng quản trị bổ nhiệm một người trong số họ hoặc thuê người khác làm Giám đốc hoặc Tổng giám đốc; nhiệm kỳ không quá 05 năm.",
             "2. Giám đốc hoặc Tổng giám đốc điều hành công việc kinh doanh hằng ngày của công ty; chịu sự giám sát của Hội đồng quản trị; chịu trách nhiệm trước Hội đồng quản trị và trước pháp luật về việc thực hiện quyền và nhiệm vụ được giao; có quyền và nghĩa vụ theo quy định của Luật Doanh nghiệp và Điều lệ này.",
             "3. Giám đốc hoặc Tổng giám đốc phải có trình độ chuyên môn, kinh nghiệm trong quản trị kinh doanh và không thuộc đối tượng bị cấm quản lý doanh nghiệp theo quy định của Luật Doanh nghiệp."])
    vb.dieu("Ban kiểm soát",
            "Công ty cổ phần có trên 11 cổ đông là cá nhân hoặc có cổ đông là tổ chức sở hữu trên 50% tổng số cổ phần của công ty phải có Ban kiểm soát; các trường hợp khác do công ty tự quyết định theo mô hình tổ chức quản lý được lựa chọn theo quy định của Luật Doanh nghiệp. "
            "Quyền, nghĩa vụ, tiêu chuẩn, nhiệm kỳ của Kiểm soát viên được thực hiện theo quy định của Luật Doanh nghiệp.")
    vb.dieu("Trách nhiệm của người quản lý công ty",
            ["1. Tuân thủ pháp luật, Điều lệ công ty, nghị quyết của Đại hội đồng cổ đông trong việc thực hiện các quyền và nghĩa vụ được giao.",
             "2. Thực hiện các quyền và nghĩa vụ một cách trung thực, cẩn trọng, tốt nhất nhằm bảo đảm lợi ích hợp pháp của công ty và cổ đông; không lạm dụng địa vị, chức vụ, thông tin, bí quyết, cơ hội kinh doanh, tài sản của công ty để tư lợi.",
             "3. Thông báo kịp thời, đầy đủ, chính xác cho công ty về các doanh nghiệp mà mình và người có liên quan làm chủ hoặc có phần vốn góp, cổ phần chi phối."])
    vb.dieu("Nguyên tắc giải quyết tranh chấp nội bộ",
            ["1. Các tranh chấp nội bộ liên quan đến thành lập, hoạt động, giải thể công ty trước hết phải được giải quyết thông qua thương lượng, hòa giải.",
             "2. Nếu không đạt được kết quả thương lượng, hòa giải thì bất kỳ bên nào cũng có quyền đưa tranh chấp ra Tòa án có thẩm quyền để giải quyết."])
    _dieu_tai_chinh_giai_the(vb, tt, "Đại hội đồng cổ đông", "Đại hội đồng cổ đông")
    _dieu_thi_hanh(vb, tt)
    _ky(vb, tt, "CHỦ TỊCH HỘI ĐỒNG QUẢN TRỊ", tt.get("chu_tich") or (tt.get("nguoi_dd") or {}).get("ho_ten"), _anh_chu_tich(tt, chu_ky))
    return vb.d


def soan_dieu_le(tt, chu_ky=None):
    """tt: thông tin sau chuyển đổi (xem gpkd_chuyen_doi.thong_tin_sau). tt['loai'] = 1tv | 2tv | cp. Trả Document."""
    tt = dict(tt)
    tt["can_cu_chuyen_doi"] = tt.get("can_cu_chuyen_doi") or "quyết định chuyển đổi loại hình doanh nghiệp"
    loai = tt.get("loai_moi")
    return {"1tv": _dieu_le_1tv, "2tv": _dieu_le_2tv, "cp": _dieu_le_cp}[loai](tt, chu_ky)
