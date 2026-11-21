"""Gói dữ liệu CÔNG NỢ cho Claude (hoặc chatbot khác) — màn "Kết nối MISA SME > Đối chiếu công nợ 3 tầng".

Xuất 1 file Excel gồm: PROMPT (hướng dẫn đầy đủ để chatbot tự hiểu), bảng kê hoá đơn đầu ra/đầu vào,
tổng hợp công nợ phải thu/phải trả, chi tiết hoá đơn + khoản thanh toán của từng đối tượng, kết quả
đối chiếu 3 tầng của phần mềm, và sheet KET_QUA (mẫu trả lời). Claude trả về file có sheet KET_QUA;
doc_ket_qua() đọc lại — các dòng CHUYEN_CONG_NO được đổi thành 'danh_sach' đúng dạng goi_y_chuyen để
đưa thẳng vào chức năng xuất Excel "Nghiệp vụ khác" (chuyển công nợ) có sẵn.
Hàm thuần: không đụng CSDL/mạng — dữ liệu do server.py chuẩn bị."""
import re
import unicodedata

COT_KET_QUA = ["LOAI_XU_LY", "LOAI_CN", "TU_MA", "TU_TEN", "DEN_MA", "DEN_TEN", "NGAY_TT", "SO_CT_TT",
               "REF_ID_TT", "SO_HD", "SO_TIEN", "GHI_CHU"]
LOAI_XU_LY = ("CHUYEN_CONG_NO", "KHOP_THANH_TOAN", "DE_XUAT_KHAC")

PROMPT = [
    "BẠN LÀ KẾ TOÁN TRƯỞNG VIỆT NAM RẤT CẨN THẬN. HÃY ĐỌC TOÀN BỘ FILE EXCEL NÀY, LÀM THEO HƯỚNG DẪN VÀ TRẢ VỀ FILE KẾT QUẢ, KHÔNG HỎI LẠI.",
    "",
    "1. BỐI CẢNH",
    "File xuất từ phần mềm kế toán, ghép dữ liệu hoá đơn (bảng kê tải từ cơ quan thuế) với sổ công nợ trong MISA (TK 131 phải thu, TK 331 phải trả). Mục tiêu: rà soát công nợ từng khách hàng/nhà cung cấp, phát hiện khoản thanh toán gắn SAI ĐỐI TƯỢNG, hoá đơn treo, thanh toán trùng/thiếu, lệch giữa bảng kê và sổ, rồi đề xuất cách xử lý.",
    "",
    "2. CÁC SHEET",
    "- HD_DAU_RA / HD_DAU_VAO: bảng kê hoá đơn bán ra / mua vào của công ty (SO_HD, KY_HIEU, NGAY, MST, TEN, TIEN_CHUA_THUE, THUE, TONG_TIEN, TRANG_THAI).",
    "- TONG_HOP_PHAI_THU / TONG_HOP_PHAI_TRA: mỗi dòng 1 đối tượng: tổng hoá đơn, tổng đã thanh toán, SO_DU_CUOI_KY (>0 = còn nợ, <0 = thanh toán dư/trả trước), số hoá đơn treo, số khoản thanh toán chưa khớp.",
    "- CT_HOA_DON: hoá đơn ghi nhận trong sổ công nợ MISA của từng đối tượng (TRANG_THAI: KHOP = đã khớp đủ thanh toán, KHOP_MOT_PHAN = mới khớp một phần, TREO = chưa khớp thanh toán nào).",
    "- CT_THANH_TOAN: các khoản thu/chi (ngân hàng, tiền mặt điều chỉnh) đã ghi vào sổ cho đối tượng đó (TRANG_THAI: KHOP / CHUA_KHOP). MO_TA là nội dung chuyển khoản — thường có tên người chuyển/nhận thật.",
    "- GOI_Y_CHUYEN, KET_QUA_PHAN_MEM: kết quả đối chiếu 3 tầng mà phần mềm đã tính (tham khảo, có thể sai — hãy tự kiểm tra lại).",
    "- KET_QUA: mẫu cột của file trả lời.",
    "",
    "3. VIỆC CẦN LÀM (theo thứ tự)",
    "a) Với mỗi đối tượng còn SO_DU_CUOI_KY khác 0 (vượt dung sai ~20.000đ): xem CT_HOA_DON và CT_THANH_TOAN của đối tượng đó, tìm khoản thanh toán CHUA_KHOP.",
    "b) PHÁT HIỆN GẮN SAI ĐỐI TƯỢNG: khoản thanh toán CHUA_KHOP mà MO_TA nêu tên một công ty KHÁC với đối tượng đang gắn, hoặc số tiền trùng CHÍNH XÁC (hoặc tổng tổ hợp) với hoá đơn TREO của đúng một đối tượng khác. Đọc tên công ty trong MO_TA (viết hoa, không dấu, viết tắt Cty/CT/CP/TNHH…) và so cột TEN các đối tượng. Nếu chắc chắn → dòng CHUYEN_CONG_NO (chuyển khoản thanh toán từ đối tượng TU sang đối tượng DEN).",
    "c) Hoá đơn TREO: nếu có khoản thanh toán của CHÍNH đối tượng đó khớp tổng tổ hợp các hoá đơn treo (nhiều hoá đơn cộng lại, một hoá đơn trả nhiều lần) → dòng KHOP_THANH_TOAN ghi rõ các SO_HD. Hoá đơn treo nhỏ, cũ, thanh toán tiền mặt → DE_XUAT_KHAC (điều chỉnh bằng tiền mặt) kèm lý do.",
    "d) Đối chiếu bảng kê: hoá đơn có trong HD_DAU_RA/HD_DAU_VAO nhưng KHÔNG thấy trong CT_HOA_DON (chưa vào sổ), hoặc có trong sổ nhưng không có trong bảng kê, hoặc lệch số tiền → DE_XUAT_KHAC (nêu SO_HD, MST, số tiền hai bên).",
    "e) Thanh toán 2 lần cùng số tiền/cùng hoá đơn, thanh toán dư, trả trước/tạm ứng → DE_XUAT_KHAC.",
    "Chỉ ghi dòng khi bạn CHẮC CHẮN. Chuyển công nợ là thao tác ghi sổ — KHÔNG đoán. Không chắc thì ghi DE_XUAT_KHAC với GHI_CHU nêu rõ nghi vấn để người dùng tự kiểm tra.",
    "",
    "4. FILE KẾT QUẢ (BẮT BUỘC)",
    "Tạo file Excel .xlsx có sheet tên đúng KET_QUA, dòng 1 là tiêu đề: " + " | ".join(COT_KET_QUA) + ".",
    "- LOAI_XU_LY: CHUYEN_CONG_NO | KHOP_THANH_TOAN | DE_XUAT_KHAC.   LOAI_CN: KH (phải thu 131) hoặc NCC (phải trả 331).",
    "- CHUYEN_CONG_NO bắt buộc đủ: TU_MA, DEN_MA (MÃ đối tượng copy y nguyên từ cột MA), NGAY_TT (ngày khoản thanh toán, dạng YYYY-MM-DD hoặc như trong CT_THANH_TOAN), SO_TIEN (số tiền khoản thanh toán chuyển), SO_CT_TT và REF_ID_TT copy từ CT_THANH_TOAN, SO_HD (hoá đơn đối tượng đích đang treo nếu có).",
    "- TU_TEN, DEN_TEN: tên đối tượng. GHI_CHU: lý do ngắn gọn (vì sao chắc chắn).",
    "Có thể thêm sheet RA_SOAT (nhận xét chi tiết từng đối tượng) — phần mềm chỉ đọc KET_QUA.",
    "Nếu không tạo được file Excel, in bảng KET_QUA dạng CSV trong khung code để người dùng dán vào Excel.",
    "",
    "5. SAU KHI XONG",
    "Trả lời ngắn gọn: số đối tượng đã rà, số dòng mỗi loại, các nghi vấn quan trọng nhất. Nhắc người dùng: vào phần mềm, màn Kết nối MISA SME > Đối chiếu công nợ, bấm \"📥 Nhập kết quả Claude (công nợ)\" và chọn file; các dòng CHUYEN_CONG_NO sẽ được xuất thành Excel 'Chứng từ nghiệp vụ khác' để Import vào MISA.",
]


def _s(v):
    return "" if v is None else v


def _chuan(v):
    s = unicodedata.normalize("NFD", str(v or "")).replace("đ", "d").replace("Đ", "D")
    return re.sub(r"[^A-Z0-9]", "", re.sub(r"[̀-ͯ]", "", s).upper())


def _tong_hop(goc):
    rows = [["MA", "TEN", "TONG_HOA_DON", "TONG_DA_THANH_TOAN", "SO_DU_CUOI_KY", "SO_HOA_DON", "SO_HD_TREO", "SO_KHOAN_TT_CHUA_KHOP"]]
    for d in goc or []:
        hd = d.get("hoa_don") or []
        tt = d.get("thanh_toan") or []
        rows.append([_s(d.get("ma")), _s(d.get("ten")), round(sum(h.get("so_tien") or 0 for h in hd)),
                     round(sum(t.get("so_tien") or 0 for t in tt)), round(d.get("so_du_cuoi_ky") or 0), len(hd),
                     sum(1 for h in hd if not h.get("matched") and not h.get("phan_dung")), sum(1 for t in tt if not t.get("matched"))])
    return rows


def _trang_thai_hd(h):
    """KHOP = đã khớp đủ thanh toán; KHOP_MOT_PHAN = mới khớp 1 phần (giá trị hoặc thuế); TREO = chưa khớp gì."""
    if h.get("matched"):
        return "KHOP"
    if h.get("phan_dung"):
        return "KHOP_MOT_PHAN"
    return "TREO"


def tao_goi(du_lieu):
    """du_lieu: {ten_cty, tu_ngay, den_ngay, hd_dau_ra:[{so_hd,ky_hieu,ngay,mst,ten,chua_thue,thue,tong,trang_thai}], hd_dau_vao:[...],
    cong_no:{'kh': res|None, 'ncc': res|None}} — res là kết quả _misa_doi_chieu_3_tang có thêm khoá 'goc'.
    Trả về dict {tên sheet: danh sách dòng} (dòng đầu là tiêu đề)."""
    cn = du_lieu.get("cong_no") or {}
    head_hd = ["SO_HD", "KY_HIEU", "NGAY", "MST", "TEN", "TIEN_CHUA_THUE", "THUE", "TONG_TIEN", "TRANG_THAI"]

    def bang_ke(ds):
        return [head_hd] + [[_s(x.get("so_hd")), _s(x.get("ky_hieu")), _s(x.get("ngay")), _s(x.get("mst")), _s(x.get("ten")),
                             x.get("chua_thue") or 0, x.get("thue") or 0, x.get("tong") or 0, _s(x.get("trang_thai"))] for x in ds or []]

    ct_hd = [["LOAI_CN", "MA", "TEN", "REF_ID", "SO_HD", "NGAY_HD", "SO_TIEN", "TRANG_THAI"]]
    ct_tt = [["LOAI_CN", "MA", "TEN", "REF_ID", "NGAY", "SO_TIEN", "SO_CT", "NGUON", "TRANG_THAI", "MO_TA"]]
    goi_y = [["LOAI_CN", "TU_MA", "TU_TEN", "NGAY_TT", "SO_CT_TT", "REF_ID_TT", "SO_TIEN", "DEN_MA", "DEN_TEN", "SO_HD_DICH", "HD_SO_TIEN", "CHENH_LECH", "MO_TA"]]
    kq_pm = [["LOAI_CN", "NHOM", "CHI_TIET"]]
    for lcn in ("kh", "ncc"):
        res = cn.get(lcn)
        if not res:
            continue
        L = lcn.upper()
        for d in res.get("goc") or []:
            for h in d.get("hoa_don") or []:
                ct_hd.append([L, _s(d.get("ma")), _s(d.get("ten")), _s(h.get("ref_id")), _s(h.get("inv_no")), _s(h.get("inv_date")), round(h.get("so_tien") or 0), _trang_thai_hd(h)])
            for t in d.get("thanh_toan") or []:
                ct_tt.append([L, _s(d.get("ma")), _s(d.get("ten")), _s(t.get("ref_id")), _s(t.get("date")), round(t.get("so_tien") or 0), _s(t.get("so_ct")),
                              _s(t.get("nguon")), "KHOP" if t.get("matched") else "CHUA_KHOP", _s(t.get("mo_ta"))[:300]])
        for g in res.get("goi_y_chuyen") or []:
            goi_y.append([L, _s(g.get("tu_ma")), _s(g.get("tu_ten")), _s(g.get("tt_ngay")), _s(g.get("tt_so_ct")), _s(g.get("tt_ref_id")), g.get("so_tien") or 0,
                          _s(g.get("den_ma")), _s(g.get("den_ten")), _s(g.get("inv_no")), g.get("hd_so_tien") or 0, g.get("chenh_lech") or 0, _s(g.get("mo_ta"))[:300]])
        for nhom in ("tang1", "tang2", "tam_ung", "khong_ro", "tang3", "thu_2_lan", "nghi_sai_doi_tuong"):
            for it in res.get(nhom) or []:
                kq_pm.append([L, nhom, "; ".join("%s=%s" % (k, v) for k, v in it.items() if isinstance(v, (str, int, float)) and v != "")[:900]])
    tong = {}
    for lcn, ten in (("kh", "TONG_HOP_PHAI_THU"), ("ncc", "TONG_HOP_PHAI_TRA")):
        tong[ten] = _tong_hop((cn.get(lcn) or {}).get("goc"))
    kc = "%s → %s" % (du_lieu.get("tu_ngay") or "…", du_lieu.get("den_ngay") or "…")
    huong_dan = [["GÓI DỮ LIỆU CÔNG NỢ" + (" — " + du_lieu["ten_cty"] if du_lieu.get("ten_cty") else "")],
                 ["Khoảng hoá đơn: " + kc + " · " + str(len(du_lieu.get("hd_dau_ra") or [])) + " HĐ đầu ra · " + str(len(du_lieu.get("hd_dau_vao") or [])) + " HĐ đầu vào"],
                 [""], ["Sheet PROMPT (đầu file) có đầy đủ hướng dẫn cho chatbot. Chỉ cần tải file lên Claude/chatbot khác và gửi: \"Hãy làm theo hướng dẫn trong sheet PROMPT\"."],
                 ["Dữ liệu công nợ lấy từ CSDL MISA (chỉ đọc) tại thời điểm xuất; bảng kê hoá đơn lấy từ dữ liệu tra cứu cơ quan thuế đã lưu trong phần mềm."]]
    out = {"PROMPT": [[x] for x in PROMPT], "HUONG_DAN": huong_dan, "HD_DAU_RA": bang_ke(du_lieu.get("hd_dau_ra")), "HD_DAU_VAO": bang_ke(du_lieu.get("hd_dau_vao"))}
    out.update(tong)
    out.update({"CT_HOA_DON": ct_hd, "CT_THANH_TOAN": ct_tt, "GOI_Y_CHUYEN": goi_y, "KET_QUA_PHAN_MEM": kq_pm, "KET_QUA": [list(COT_KET_QUA)]})
    return out


def ghi_xlsx(sheets, duong_dan):
    from openpyxl import Workbook
    from openpyxl.styles import Font
    wb = Workbook()
    wb.remove(wb.active)
    for ten, rows in sheets.items():
        ws = wb.create_sheet(ten[:31])
        for r in rows:
            ws.append(list(r))
        if ten not in ("PROMPT", "HUONG_DAN") and rows:
            for c in ws[1]:
                c.font = Font(bold=True)
        for i in range(1, (max((len(r) for r in rows), default=1)) + 1):
            ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = 160 if ten in ("PROMPT", "HUONG_DAN") else (46 if i in (2, 5, 10) else 18)
    wb.save(duong_dan)
    return duong_dan


def _ngay_iso(v):
    s = str(v or "").strip()
    m = re.match(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})", s)
    if m:
        return "%s-%02d-%02d" % (m.group(3), int(m.group(2)), int(m.group(1)))
    return s[:10]


def doc_ket_qua(duong_dan):
    """Đọc sheet KET_QUA. Trả {'chuyen': [dict dạng goi_y_chuyen + loai_cn], 'khac': [dict], 'loi': [str]}."""
    from openpyxl import load_workbook
    wb = load_workbook(duong_dan, data_only=True, read_only=True)
    ten = next((n for n in wb.sheetnames if _chuan(n) == "KETQUA"), None)
    if not ten:
        raise ValueError("Không thấy sheet KET_QUA trong file")
    rows = list(wb[ten].iter_rows(values_only=True))
    hi = next((i for i, r in enumerate(rows[:15]) if any(_chuan(c) == "LOAIXULY" for c in (r or []))), -1)
    if hi < 0:
        raise ValueError("Sheet KET_QUA thiếu cột LOAI_XU_LY")
    cot = {}
    for k, c in enumerate(rows[hi]):
        for n in COT_KET_QUA:
            if _chuan(c) == _chuan(n) and n not in cot:
                cot[n] = k
    chuyen, khac, loi = [], [], []
    for i in range(hi + 1, len(rows)):
        r = rows[i] or ()
        g = lambda n: ("" if cot.get(n) is None or cot[n] >= len(r) or r[cot[n]] is None else str(r[cot[n]]).strip())
        lx = _chuan(g("LOAI_XU_LY"))
        if not lx:
            continue
        loai_cn = "kh" if _chuan(g("LOAI_CN")) in ("KH", "PHAITHU", "131") else ("ncc" if _chuan(g("LOAI_CN")) in ("NCC", "PHAITRA", "331") else "")
        if lx == "CHUYENCONGNO":
            try:
                so_tien = float(re.sub(r"[^\d.\-]", "", g("SO_TIEN").replace(",", "")) or 0)
            except ValueError:
                so_tien = 0
            thieu = [n for n, v in (("TU_MA", g("TU_MA")), ("DEN_MA", g("DEN_MA")), ("NGAY_TT", g("NGAY_TT")), ("LOAI_CN", loai_cn)) if not v] + (["SO_TIEN"] if so_tien <= 0 else [])
            if thieu or g("TU_MA") == g("DEN_MA"):
                loi.append("dòng %d: CHUYEN_CONG_NO thiếu/sai %s" % (i + 1, ", ".join(thieu) or "TU_MA = DEN_MA"))
                continue
            chuyen.append({"loai_cn": loai_cn, "tu_ma": g("TU_MA"), "tu_ten": g("TU_TEN"), "den_ma": g("DEN_MA"), "den_ten": g("DEN_TEN"),
                           "tt_ngay": _ngay_iso(g("NGAY_TT")), "tt_so_ct": g("SO_CT_TT"), "tt_ref_id": g("REF_ID_TT"), "inv_no": g("SO_HD"),
                           "inv_date": "", "hd_so_tien": 0, "so_tien": round(so_tien), "mo_ta": g("GHI_CHU"), "chenh_lech": 0})
        elif lx in ("KHOPTHANHTOAN", "DEXUATKHAC"):
            khac.append({"loai_xu_ly": "KHOP_THANH_TOAN" if lx == "KHOPTHANHTOAN" else "DE_XUAT_KHAC", "loai_cn": loai_cn, "tu_ma": g("TU_MA"), "tu_ten": g("TU_TEN"),
                         "den_ma": g("DEN_MA"), "so_hd": g("SO_HD"), "so_tien": g("SO_TIEN"), "ghi_chu": g("GHI_CHU")})
        else:
            loi.append("dòng %d: LOAI_XU_LY không hợp lệ (%s)" % (i + 1, g("LOAI_XU_LY")))
    return {"chuyen": chuyen, "khac": khac, "loi": loi}
