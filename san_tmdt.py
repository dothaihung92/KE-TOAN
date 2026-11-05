# -*- coding: utf-8 -*-
"""HỖ TRỢ XUẤT HOÁ ĐƠN cho đơn hàng sàn TMĐT (Shopee / TikTok Shop / Lazada).

Đọc file báo cáo đơn hàng mà NGƯỜI DÙNG xuất từ trang người bán (Excel .xlsx/.xls hoặc .csv), chuẩn hoá từng dòng sản phẩm,
lọc đơn đã hoàn thành, rồi dựng các dòng theo form MISA SME "Chứng từ bán hàng" (lập kèm hoá đơn) để import vào MISA và xuất hoá đơn.

Phần mềm KHÔNG đăng nhập thay, KHÔNG nhập OTP/captcha thay người dùng; chỉ đọc file đơn hàng của chính shop.
Tên cột của mỗi sàn thay đổi theo thời gian -> dò cột theo nhiều tên đồng nghĩa (tiếng Việt + tiếng Anh, không dấu)."""
import csv
import datetime
import io
import re
import unicodedata

SAN = {
    "shopee": {"ten": "Shopee", "url": "https://banhang.shopee.vn/portal/sale/order", "tien_to": "SP"},
    "tiktok": {"ten": "TikTok Shop", "url": "https://seller-vn.tiktok.com/order", "tien_to": "TT"},
    "lazada": {"ten": "Lazada", "url": "https://sellercenter.lazada.vn/apps/order/list", "tien_to": "LZ"},
}


def khong_dau(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").replace("đ", "d").replace("Đ", "D")
    return re.sub(r"\s+", " ", s).strip().lower()


# Tên cột đồng nghĩa (đã bỏ dấu, chữ thường). Khớp ĐÚNG trước, rồi khớp "bắt đầu bằng".
COT = {
    "ma_don": ["ma don hang", "order id", "order number", "ordernumber", "ma don", "order no", "order sn", "order_id"],
    "ma_dong": ["order item id", "ma san pham trong don"],
    "trang_thai": ["trang thai don hang", "order status", "status", "trang thai"],
    "ngay_dat": ["ngay dat hang", "created time", "created at", "createtime", "order creation date", "thoi gian dat hang", "order created time", "createtime"],
    "ngay_xong": ["thoi gian hoan thanh don hang", "thoi gian don hang duoc hoan thanh", "completed time", "delivered time", "order complete time",
                  "thoi gian giao hang", "delivered date", "updated at"],
    "ten_hang": ["ten san pham", "product name", "item name", "itemname", "ten hang"],
    "phan_loai": ["ten phan loai hang", "variation", "variation name", "phan loai hang"],
    "sku": ["sku phan loai hang", "seller sku", "sellersku", "ma sku", "sku", "sku reference no.", "ma phan loai"],
    "sku_sp": ["sku san pham"],
    "so_luong": ["so luong", "quantity", "qty"],
    "don_gia": ["gia uu dai", "sku unit original price", "unit price", "unitprice", "gia goc", "item price", "original price"],
    "thanh_tien": ["tong gia ban (san pham)", "sku subtotal after discount", "paid price", "paidprice", "tong gia ban", "subtotal after discount",
                   "item subtotal", "thanh tien"],
    "tien_truoc_giam": ["sku subtotal before discount"],                                   # TikTok: tiền hoá đơn = trước giảm - người bán giảm (theo mẫu)
    "tra_hang": ["trang thai tra hang/hoan tien", "cancelation/return type", "cancellation/return type"],
    "sl_tra": ["so luong san pham duoc hoan tra", "returned quantity", "sku quantity of return"],
    "giam_gia_shop": ["sku seller discount", "seller discount", "seller discount total"],
    "khach": ["ten nguoi nhan", "recipient", "customer name", "buyer username", "nguoi mua", "ten nguoi mua", "shipping name", "buyer name"],
    "sdt": ["so dien thoai", "phone #", "phone", "shipping phone", "sdt"],
    "dia_chi": ["dia chi nhan hang", "detail address", "shipping address", "dia chi", "address"],
    "tinh": ["tinh/thanh pho", "province", "shipping city"],
}

_HUY = ("da huy", "huy", "cancel", "failed", "that bai", "chua thanh toan", "unpaid")
_TRA_DUYET = ("da chap thuan", "chap thuan", "hoan tien thanh cong", "approved", "refunded", "returned", "return/refund", "da tra hang")


def _so(v):
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"[^\d,.\-]", "", str(v))
    if not s or s in "-.,":
        return 0.0
    if "," in s and "." in s:                         # 1.234.567,5 hoặc 1,234,567.5
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif s.count(".") > 1 or (s.count(".") == 1 and len(s.split(".")[1]) == 3):
        s = s.replace(".", "")                        # 1.234.567 (dấu chấm ngăn nghìn)
    elif s.count(",") >= 1 and all(len(x) == 3 for x in s.split(",")[1:]):
        s = s.replace(",", "")
    else:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def _ngay(v):
    """-> 'dd/mm/yyyy' hoặc ''."""
    if isinstance(v, datetime.datetime):
        return v.strftime("%d/%m/%Y")
    if isinstance(v, datetime.date):
        return v.strftime("%d/%m/%Y")
    if isinstance(v, (int, float)) and 20000 < v < 80000:     # số ngày Excel
        return (datetime.date(1899, 12, 30) + datetime.timedelta(days=int(v))).strftime("%d/%m/%Y")
    s = str(v or "").strip()
    m = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", s)
    if m:
        return f"{int(m.group(3)):02d}/{int(m.group(2)):02d}/{m.group(1)}"
    m = re.search(r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})", s)
    if m:
        return f"{int(m.group(1)):02d}/{int(m.group(2)):02d}/{m.group(3)}"
    m = re.search(r"(\d{1,2})\s+([A-Za-z]{3})[a-z]*\s+(\d{4})", s)          # Lazada: '05 Nov 2026 10:00'
    th = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
    if m and m.group(2).lower() in th:
        return f"{int(m.group(1)):02d}/{th[m.group(2).lower()]:02d}/{m.group(3)}"
    return ""


def _doc_bang(noi_dung, ten_file):
    """bytes -> danh sách các bảng (mỗi bảng = list các hàng). File của người dùng: chỉ đọc dữ liệu (openpyxl read_only, không chạy macro)."""
    ten = (ten_file or "").lower()
    if ten.endswith(".csv") or ten.endswith(".txt"):
        for ma in ("utf-8-sig", "utf-16", "cp1258", "latin-1"):
            try:
                t = noi_dung.decode(ma)
                break
            except UnicodeDecodeError:
                continue
        dau = t[:4000]
        sep = "\t" if dau.count("\t") > dau.count(",") else (";" if dau.count(";") > dau.count(",") else ",")
        return [list(csv.reader(io.StringIO(t), delimiter=sep))]
    if ten.endswith(".xls") and not noi_dung[:2] == b"PK":
        import xlrd                                     # .xls cũ
        wb = xlrd.open_workbook(file_contents=noi_dung)
        out = []
        for sh in wb.sheets():
            rows = []
            for r in range(sh.nrows):
                hang = []
                for c in range(sh.ncols):
                    cell = sh.cell(r, c)
                    if cell.ctype == xlrd.XL_CELL_DATE:
                        hang.append(xlrd.xldate.xldate_as_datetime(cell.value, wb.datemode))
                    else:
                        hang.append(cell.value)
                rows.append(hang)
            out.append(rows)
        return out
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(noi_dung), read_only=True, data_only=True)
    out = []
    for ws in wb.worksheets:
        try:
            ws.reset_dimensions()          # file Shopee ghi sai kích thước bảng (chỉ báo 1 ô) -> đọc hết dữ liệu thật
        except Exception:
            pass
        out.append([list(r) for r in ws.iter_rows(values_only=True)])
    wb.close()
    return out


def _tim_cot(hang):
    """Dò vị trí các cột trong 1 hàng tiêu đề -> {khoá: chỉ số}."""
    ten = [khong_dau(x) for x in hang]
    kq = {}
    for khoa, dong_nghia in COT.items():
        vt = next((i for d in dong_nghia for i, t in enumerate(ten) if t == d and i not in kq.values()), None)
        if vt is None:
            vt = next((i for d in dong_nghia for i, t in enumerate(ten) if t.startswith(d) and i not in kq.values()), None)
        if vt is not None:
            kq[khoa] = vt
    return kq


def doc_file_don_hang(noi_dung, ten_file, san=""):
    """-> (danh sách dòng chuẩn hoá, ghi chú). Mỗi dòng: ma_don, trang_thai, ngay (ngày hoàn thành nếu có, không thì ngày đặt), ten_hang, sku,
    so_luong, thanh_tien (tiền khách trả cho dòng, đã trừ giảm giá của shop — giá trên sàn thường ĐÃ gồm VAT), khach, sdt, dia_chi."""
    bang = _doc_bang(noi_dung, ten_file)
    tot = None
    for rows in bang:
        for i, hang in enumerate(rows[:15]):
            c = _tim_cot(hang)
            if "ma_don" in c and ("ten_hang" in c or "sku" in c) and ("thanh_tien" in c or "don_gia" in c):
                if tot is None or len(c) > len(tot[2]):
                    tot = (rows, i, c)
    if tot is None:
        raise ValueError("Không nhận ra file đơn hàng: cần có các cột Mã đơn hàng, Tên sản phẩm/SKU và Giá/Thành tiền "
                         "(hãy xuất đúng báo cáo ĐƠN HÀNG trên trang người bán).")
    rows, i0, c = tot
    g = lambda r, k: (r[c[k]] if k in c and c[k] < len(r) else None)
    kq = []
    ma_truoc = ""
    for r in rows[i0 + 1:]:
        if not r or all(x in (None, "") for x in r):
            continue
        ma = str(g(r, "ma_don") or "").strip()
        if ma.endswith(".0") and ma[:-2].isdigit():
            ma = ma[:-2]
        if not ma:
            ma = ma_truoc                                  # dòng sản phẩm thứ 2.. của cùng 1 đơn (ô mã đơn để trống)
        if not ma:
            continue
        ma_truoc = ma
        sl = _so(g(r, "so_luong")) or 1.0
        if "tien_truoc_giam" in c:                                  # TikTok: trước giảm giá - người bán giảm giá (sàn giảm giá không trừ)
            tt = _so(g(r, "tien_truoc_giam")) - _so(g(r, "giam_gia_shop"))
        else:
            tt = _so(g(r, "thanh_tien"))
            if not tt and "thanh_tien" not in c:
                tt = _so(g(r, "don_gia")) * sl
        ten = str(g(r, "ten_hang") or "").strip()
        pl = str(g(r, "phan_loai") or "").strip()
        kq.append({
            "ma_don": ma, "trang_thai": str(g(r, "trang_thai") or "").strip(),
            "ngay": _ngay(g(r, "ngay_xong")) or _ngay(g(r, "ngay_dat")), "ngay_dat": _ngay(g(r, "ngay_dat")),
            "ten_hang": ten, "phan_loai": pl, "sku": str(g(r, "sku") or "").strip() or str(g(r, "sku_sp") or "").strip(), "so_luong": sl, "thanh_tien": round(tt),
            "tra_hang": str(g(r, "tra_hang") or "").strip(), "sl_tra": _so(g(r, "sl_tra")),
            "khach": str(g(r, "khach") or "").strip(), "sdt": str(g(r, "sdt") or "").strip(),
            "dia_chi": ", ".join(x for x in (str(g(r, "dia_chi") or "").strip(), str(g(r, "tinh") or "").strip()) if x),
        })
    ghi = f"Nhận {len(kq)} dòng sản phẩm từ bảng có {len(c)} cột nhận diện được"
    return kq, ghi


def la_hop_le(x):
    """Đơn được xuất hoá đơn: KHÔNG phải đơn huỷ/thất bại và KHÔNG bị trả hàng/hoàn tiền đã chấp thuận (theo file mẫu: đơn đã giao,
    đang vận chuyển, người mua đã nhận hàng... đều xuất). Trả về (True/False, lý do)."""
    t = khong_dau(x.get("trang_thai"))
    if any(k in t for k in _HUY) and "nhan duoc hang" not in t:
        return False, "huỷ"
    if t.startswith(("tra hang", "return", "refund", "returned")):
        return False, "trả hàng"
    th = khong_dau(x.get("tra_hang"))
    if th and (any(k in th for k in _TRA_DUYET) or th in ("cancel", "huy")):
        return False, "trả hàng/hoàn tiền đã chấp thuận"
    return True, ""


def la_hoan_thanh(trang_thai):
    return la_hop_le({"trang_thai": trang_thai})[0]


def loc_don(dong, chi_hoan_thanh=True, tu_ngay="", den_ngay=""):
    def k(d):
        m = re.match(r"(\d{2})/(\d{2})/(\d{4})", d or "")
        return (m.group(3), m.group(2), m.group(1)) if m else None
    a, b = k(_ngay(tu_ngay) or tu_ngay), k(_ngay(den_ngay) or den_ngay)
    kq = []
    for x in dong:
        if chi_hoan_thanh and not la_hop_le(x)[0]:
            continue
        n = k(x.get("ngay_dat") or x["ngay"])                     # lọc theo NGÀY ĐẶT HÀNG (như hộp "Khoảng thời gian" khi Xuất trên sàn)
        if n and ((a and n < a) or (b and n > b)):
            continue
        kq.append(x)
    return kq


def tong_hop(dong):
    don = {}
    for x in dong:
        don.setdefault(x["ma_don"], 0)
        don[x["ma_don"]] += x["thanh_tien"]
    return {"so_don": len(don), "so_dong": len(dong), "tong_tien": round(sum(don.values()))}


def sang_ban_hang(dong, headers, san="shopee", thue_suat=8.0, gom_vat=True, tk_no="131", tk_co="5111", tk_thue="33311",
                  ma_hang_chung="", ma_kh="KL", ten_kh="Khách lẻ không lấy hoá đơn"):
    """Dòng đơn hàng -> dòng form MISA 'Chứng từ bán hàng' (theo thứ tự cột `headers`). Mỗi đơn = 1 chứng từ, lập kèm hoá đơn (chưa lập).
    Giá trên sàn thường ĐÃ gồm VAT (gom_vat=True): đơn giá chưa thuế = tiền / (1 + thuế suất), tiền thuế = tiền - tiền chưa thuế."""
    vt = {h: i for i, h in enumerate(headers)}
    tien_to = SAN.get(san, {}).get("tien_to", "TM")
    r_ = float(thue_suat or 0) / 100.0
    out = []
    for x in dong:
        tien = float(x["thanh_tien"] or 0)
        sl = float(x["so_luong"] or 1) or 1.0
        chua_thue = round(tien / (1 + r_)) if gom_vat else round(tien)
        thue = round(tien - chua_thue) if gom_vat else round(chua_thue * r_)
        row = [""] * len(headers)

        def dat(cot, v):
            if cot in vt:
                row[vt[cot]] = v
        dat("Hiển thị trên sổ", 0); dat("Hình thức bán hàng", 0); dat("Phương thức thanh toán", 0)
        dat("Kiêm phiếu xuất kho", 0); dat("Lập kèm hóa đơn", 1); dat("Đã lập hóa đơn", 0)
        dat("Ngày hạch toán (*)", x["ngay"]); dat("Ngày chứng từ (*)", x["ngay"])
        dat("Số chứng từ (*)", f"{tien_to}{x['ma_don']}"[:20])
        dat("Mã khách hàng", ma_kh); dat("Tên khách hàng", x.get("khach") or ten_kh); dat("Địa chỉ", x.get("dia_chi") or "")
        dat("Diễn giải", f"Bán hàng {SAN.get(san, {}).get('ten', san)} đơn {x['ma_don']}")
        dat("Mã hàng (*)", (x.get("sku") or ma_hang_chung or "").strip()[:25])
        dat("Tên hàng", x["ten_hang"])
        dat("TK Tiền/Chi phí/Nợ (*)", tk_no); dat("TK Doanh thu/Có (*)", tk_co)
        dat("Số lượng", sl)
        dat("Đơn giá", round(chua_thue / sl, 2)); dat("Thành tiền", chua_thue)
        if gom_vat:
            dat("Đơn giá sau thuế", round(tien / sl, 2))
        dat("% thuế GTGT", int(thue_suat) if float(thue_suat) == int(thue_suat) else float(thue_suat));dat("Tiền thuế GTGT", thue); dat("TK thuế GTGT", tk_thue)
        out.append(row)
    return out


# ---------------- File import hoá đơn điện tử MISA (sheet "Hóa đơn GTGT (3)" theo file mẫu của người dùng) ----------------
HD_SHEET = "Hóa đơn GTGT (3)"
HD_HEADERS = ["Số thứ tự hóa đơn (*)", "Ngày hóa đơn", "Tên đơn vị mua hàng", "Mã số thuế", "Địa chỉ", "Người mua hàng", "Email", "Số điện thoại",
              "Căn cước công dân", "Hình thức thanh toán (*)", "Tên hàng hóa/dịch vụ (*)", "ĐVT", "Số lượng", "Đơn giá", "Thành tiền",
              "Thuế suất GTGT (%)", "Tiền thuế GTGT", "Tổng cộng"]


def ten_hang_hd(x, san):
    """Tên hàng trên hoá đơn theo file mẫu: Shopee = tên sản phẩm; TikTok = tên - mã đơn - Tiktok; Lazada = tên - mã đơn - LAZADA."""
    if san == "tiktok":
        return f"{x['ten_hang']}-{x['ma_don']}-Tiktok"
    if san == "lazada":
        return f"{x['ten_hang']}-{x['ma_don']}-LAZADA"
    return x["ten_hang"]


def sang_hoa_don_gtgt(dong, san="shopee", thue_suat=5, ngay_hd="", dvt="Cái", nguoi_mua="Bán cho người tiêu dùng", httt="Tiền mặt/Chuyển khoản"):
    """-> các hàng (A..S) của sheet 'Hóa đơn GTGT (3)': mỗi ĐƠN HÀNG = 1 hoá đơn (cột A số thứ tự tăng theo đơn), mỗi sản phẩm 1 dòng.
    Thành tiền (chưa thuế) = ROUND(tiền trên sàn / (1 + thuế suất)); Đơn giá = ROUND(Thành tiền / SL); Tiền thuế = ROUND(Thành tiền × thuế suất); cột S = mã đơn (tham chiếu)."""
    kct = str(thue_suat).strip().upper() in ("KCT", "KKKNT")
    ts = 0.0 if kct else float(str(thue_suat).replace("%", "").replace(",", ".") or 0)
    ngay = ngay_hd or datetime.date.today().strftime("%d/%m/%Y")
    out, stt, truoc = [], 0, None
    for x in dong:
        if x["ma_don"] != truoc:
            stt += 1
            truoc = x["ma_don"]
        sl = float(x["so_luong"] or 0) or 1.0
        thanh = round(float(x["thanh_tien"] or 0) / (1 + ts / 100.0))
        thue = 0 if kct else round(thanh * ts / 100.0)
        out.append([stt, ngay, "", "", "", nguoi_mua, "", "", "", httt, ten_hang_hd(x, san), dvt, int(sl) if sl == int(sl) else sl,
                    round(thanh / sl), thanh, ("KCT" if kct else (int(ts) if ts == int(ts) else ts)), thue, thanh + thue, x["ma_don"]])
    return out


def ghi_file_hoa_don(rows, duong_dan):
    """Ghi file Excel import hoá đơn: dòng 1 ô A1 = 0 (như file mẫu), dòng 2 tiêu đề, dữ liệu từ dòng 3."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = HD_SHEET
    ws.cell(1, 1).value = "0"
    for c, h in enumerate(HD_HEADERS, 1):
        ws.cell(2, c).value = h
        ws.cell(2, c).font = Font(bold=True)
        ws.cell(2, c).fill = PatternFill("solid", fgColor="DDEBF7")
    for ri, r in enumerate(rows, 3):
        for ci, v in enumerate(r, 1):
            cell = ws.cell(ri, ci)
            cell.value = v
            if ci in (14, 15, 17, 18):
                cell.number_format = "#,##0"
            if ci == 19:
                cell.number_format = "@"
    for c, w in zip(range(1, 20), (10, 12, 20, 14, 20, 24, 14, 14, 14, 22, 60, 8, 9, 12, 14, 10, 12, 14, 22)):
        ws.column_dimensions[get_column_letter(c)].width = w
    ws.freeze_panes = "A3"
    wb.save(duong_dan)
