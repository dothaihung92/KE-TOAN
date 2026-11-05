# -*- coding: utf-8 -*-
"""HỖ TRỢ XUẤT HOÁ ĐƠN cho đơn hàng sàn TMĐT (Shopee / TikTok Shop / Lazada).

Đọc file báo cáo đơn hàng mà NGƯỜI DÙNG xuất từ trang người bán (Excel .xlsx/.xls hoặc .csv), chuẩn hoá từng dòng sản phẩm,
lọc đơn đã hoàn thành, rồi dựng các dòng theo form MISA SME "Chứng từ bán hàng" (lập kèm hoá đơn) để import vào MISA và xuất hoá đơn.

Phần mềm KHÔNG đăng nhập thay, KHÔNG nhập OTP/captcha thay người dùng; chỉ đọc file đơn hàng của chính shop.
Tên cột của mỗi sàn thay đổi theo thời gian -> dò cột theo nhiều tên đồng nghĩa (tiếng Việt + tiếng Anh, không dấu)."""
import csv
import datetime
import time
import io
import re
import unicodedata

SAN = {
    "shopee": {"ten": "Shopee", "url": "https://banhang.shopee.vn/portal/sale/order", "tien_to": "SP"},
    "tiktok": {"ten": "TikTok Shop", "ten_hd": "TikTok", "url": "https://seller-vn.tiktok.com/order?selected_sort=6&tab=all", "tien_to": "TT"},
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
    "trang_thai_phu": ["order substatus", "trang thai phu"],                                 # TikTok: Đã vận chuyển -> Đã giao / Đang trung chuyển / Đã hoàn tất
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
    "giam_cong_tt": ["payment platform discount"],
    "phi_vc": ["shipping fee after discount"],                                              # TikTok: phí vận chuyển KHÁCH trả (cả đơn) -> thêm dòng "Phí vận chuyển"                                          # TikTok: giảm giá của nền tảng thanh toán (cả đơn, lặp lại ở mỗi dòng)
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
    if all(max((len(r) for r in b), default=0) <= 1 for b in out) and any(len(b) > 1 for b in out):
        # TikTok: chế độ đọc nhanh chỉ thấy 1 cột (file không ghi kích thước/khoảng cột) -> đọc lại đầy đủ
        wb = openpyxl.load_workbook(io.BytesIO(noi_dung), data_only=True)
        out = [[list(r) for r in ws.iter_rows(values_only=True)] for ws in wb.worksheets]
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
        if not ma or " " in ma:                            # dòng mô tả cột (TikTok: "Platform unique order ID.")
            continue
        ma_truoc = ma
        sl = _so(g(r, "so_luong")) or 1.0
        if "tien_truoc_giam" in c and "thanh_tien" in c:           # TikTok: số KHÁCH THANH TOÁN = sau mọi giảm giá (người bán + TikTok); giảm của nền tảng thanh toán trừ sau theo đơn
            tt = _so(g(r, "thanh_tien"))
        elif "tien_truoc_giam" in c:
            tt = _so(g(r, "tien_truoc_giam")) - _so(g(r, "giam_gia_shop"))
        else:
            tt = _so(g(r, "thanh_tien"))
            if not tt and "thanh_tien" not in c:
                tt = _so(g(r, "don_gia")) * sl
        ten = str(g(r, "ten_hang") or "").strip()
        pl = str(g(r, "phan_loai") or "").strip()
        kq.append({
            "ma_don": ma, "trang_thai": str(g(r, "trang_thai_phu") or "").strip() or str(g(r, "trang_thai") or "").strip(),
            "ngay": _ngay(g(r, "ngay_xong")) or _ngay(g(r, "ngay_dat")), "ngay_dat": _ngay(g(r, "ngay_dat")),
            "ten_hang": ten, "phan_loai": pl, "sku": str(g(r, "sku") or "").strip() or str(g(r, "sku_sp") or "").strip(), "so_luong": sl, "thanh_tien": round(tt),
            "tra_hang": str(g(r, "tra_hang") or "").strip(), "sl_tra": _so(g(r, "sl_tra")),
            "khach": str(g(r, "khach") or "").strip(), "sdt": str(g(r, "sdt") or "").strip(),
            "dia_chi": ", ".join(x for x in (str(g(r, "dia_chi") or "").strip(), str(g(r, "tinh") or "").strip()) if x),
        })
    if "giam_cong_tt" in c:                                       # TikTok: "Payment platform discount" là của CẢ ĐƠN -> phân bổ theo tiền từng dòng (dòng cuối nhận phần lẻ)
        giam = {}
        for r in rows[i0 + 1:]:
            ma = str(g(r, "ma_don") or "").strip()
            if ma and " " not in ma:
                giam[ma] = _so(g(r, "giam_cong_tt"))
        theo_don = {}
        for x in kq:
            theo_don.setdefault(x["ma_don"], []).append(x)
        for ma, ds in theo_don.items():
            gm = round(giam.get(ma) or 0)
            tong = sum(x["thanh_tien"] for x in ds)
            if gm <= 0 or tong <= 0:
                continue
            con = gm
            for k, x in enumerate(ds):
                phan = con if k == len(ds) - 1 else round(gm * x["thanh_tien"] / tong)
                x["thanh_tien"] -= phan
                con -= phan
    if "phi_vc" in c:                                             # TikTok: "Tổng cộng" khách trả gồm cả phí vận chuyển sau giảm giá -> 1 dòng "Phí vận chuyển" cho mỗi đơn có phí
        phi = {}
        for r in rows[i0 + 1:]:
            ma = str(g(r, "ma_don") or "").strip()
            if ma and " " not in ma:
                phi[ma] = round(_so(g(r, "phi_vc")))
        them, da = [], set()
        for x in kq:
            them.append(x)
            ma = x["ma_don"]
            if ma in da or not phi.get(ma, 0) > 0:
                continue
            cuoi = max(i for i, y in enumerate(kq) if y["ma_don"] == ma)
            if kq[cuoi] is x:
                da.add(ma)
                them.append(dict(x, ten_hang="Phí vận chuyển", phan_loai="", sku="", so_luong=1.0, thanh_tien=phi[ma], sl_tra=0.0, phi_vc=True))
        kq = them
    ghi = f"Nhận {len(kq)} dòng sản phẩm từ bảng có {len(c)} cột nhận diện được"
    return kq, ghi


def la_hop_le(x):
    """Đơn được xuất hoá đơn: KHÔNG phải đơn huỷ/thất bại và KHÔNG bị trả hàng/hoàn tiền đã chấp thuận (theo file mẫu: đơn đã giao,
    đang vận chuyển, người mua đã nhận hàng... đều xuất). Trả về (True/False, lý do)."""
    t = khong_dau(x.get("trang_thai"))
    if any(re.search(r"(^|[^a-z])" + k + r"($|[^a-z])", t) for k in _HUY) and "nhan duoc hang" not in t:      # theo TỪ: "chuyen" không phải "huy"
        return False, "huỷ"
    if t.startswith(("tra hang", "return", "refund", "returned")):
        return False, "trả hàng"
    th = khong_dau(x.get("tra_hang"))
    if th and (any(k in th for k in _TRA_DUYET) or th in ("cancel", "huy")):
        return False, "trả hàng/hoàn tiền đã chấp thuận"
    return True, ""


_DA_GIAO = ("hoan thanh", "hoan tat", "da giao", "nhan duoc hang", "completed", "delivered", "giao thanh cong", "giao hang thanh cong", "da nhan")
_CHUA_GIAO = ("dang giao", "trung chuyen", "cho giao", "dang van chuyen", "giao cho", "cho lay", "cho xac nhan", "to ship", "shipped", "in transit", "awaiting", "pending", "ready_to_ship",
              "ready to ship", "dang xu ly", "processing")


def la_da_giao(x):
    """Chỉ xuất hoá đơn đơn ĐÃ GIAO THÀNH CÔNG (hoàn thành / đã giao / người mua đã nhận hàng). Chờ lấy/chờ giao/đang giao: chưa xuất, chờ lần cập nhật sau."""
    t = khong_dau(x.get("trang_thai"))
    if "nhan duoc hang" in t:
        return True
    if any(k in t for k in _CHUA_GIAO):
        return False
    return any(k in t for k in _DA_GIAO)


def la_hoan_thanh(trang_thai):
    return la_hop_le({"trang_thai": trang_thai})[0]


def loc_don(dong, chi_hoan_thanh=True, tu_ngay="", den_ngay=""):
    def k(d):
        m = re.match(r"(\d{2})/(\d{2})/(\d{4})", d or "")
        return (m.group(3), m.group(2), m.group(1)) if m else None
    a, b = k(_ngay(tu_ngay) or tu_ngay), k(_ngay(den_ngay) or den_ngay)
    kq = []
    for x in dong:
        if chi_hoan_thanh:
            if not la_da_giao(x) and la_hop_le(x)[0]:
                continue                                              # chưa giao thành công (chờ giao/đang giao): chưa xuất, chờ cập nhật sau
            ok, ly_do = la_hop_le(x)
            if not ok:
                sl_, tra_ = float(x.get("so_luong") or 0), float(x.get("sl_tra") or 0)
                if ly_do.startswith("trả hàng/hoàn tiền") and 0 < tra_ < sl_ and not khong_dau(x.get("trang_thai")).startswith(("tra hang", "return", "refund")):
                    x = dict(x, so_luong=sl_ - tra_, thanh_tien=round(float(x["thanh_tien"] or 0) * (sl_ - tra_) / sl_))      # trả MỘT PHẦN: vẫn xuất hoá đơn phần còn lại
                else:
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


def sang_hoa_don_gtgt(dong, san="shopee", thue_suat=5, ngay_hd="", dvt="Cái", nguoi_mua=None, httt="Tiền mặt/Chuyển khoản"):
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
        nm = nguoi_mua or f"Bán cho người tiêu dùng - {SAN.get(san, {}).get('ten_hd') or SAN.get(san, {}).get('ten', san)} - {x['ma_don']}"      # phân biệt được sàn nào + mã bill nào
        out.append([stt, ngay, "", "", "", nm, "", "", "", httt, ten_hang_hd(x, san), dvt, int(sl) if sl == int(sl) else sl,
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
    ws.auto_filter.ref = f"A2:S{max(len(rows) + 2, 3)}"                      # bộ lọc trên TẤT CẢ các cột
    wb.save(duong_dan)


# ======================= SỔ ĐƠN ĐÃ XUẤT HOÁ ĐƠN + HOÁ ĐƠN ĐIỀU CHỈNH GIẢM (trả hàng / huỷ đơn) =======================
# `so` = {"tu_goc": "YYYY-MM-DD", "lo": [{"id", "luc", "loai", "so_don"}], "don": {ma_don: {...}}} — lưu bằng server (file JSON theo công ty + sàn).
def so_moi():
    return {"tu_goc": "", "ky_hieu_mac_dinh": "", "lo": [], "don": {}}


def khoang_ngay(tu_goc, hom_nay=None, toi_da=30):
    """(từ, đến) = (max(ngày bắt đầu đã lưu, hôm nay - 30 ngày), hôm nay) — cửa sổ trượt 30 ngày để còn bắt được đơn khách trả/huỷ sau khi đã xuất hoá đơn."""
    hn = hom_nay or datetime.date.today()
    try:
        g = datetime.date.fromisoformat(tu_goc) if tu_goc else hn
    except ValueError:
        g = hn
    return max(g, hn - datetime.timedelta(days=toi_da)), hn


def luc_xuat(d):
    """Thời điểm (giây) đơn được xuất file: trường ts, không có thì đọc từ mã lô 'hdYYYYmmddHHMMSS...'."""
    if d.get("ts_xuat"):
        return float(d["ts_xuat"])
    m = re.match(r"hd(\d{14})", str(d.get("lo") or ""))
    if m:
        try:
            return datetime.datetime.strptime(m.group(1), "%Y%m%d%H%M%S").timestamp()
        except ValueError:
            pass
    return 0.0


def loai_don_da_xuat(so, dong, da_co=None, gdt_luc=None):
    """Bỏ các dòng thuộc đơn ĐÃ có hoá đơn (sổ có số hoá đơn / có trong dữ liệu hoá đơn đầu ra) VÀ đơn đã xuất file SAU lần đồng bộ hoá đơn đầu ra gần nhất
    (chưa kiểm tra được trên trang Thuế -> chưa xuất lại để khỏi trùng). Đơn đã xuất file nhưng đồng bộ SAU đó vẫn không thấy hoá đơn thì lập lại. -> (dòng mới, số đơn trùng)."""
    moi, trung = [], set()
    g = float(gdt_luc or 0)
    for x in dong:
        d = so["don"].get(x["ma_don"])
        if (d or {}).get("so_hd") or (da_co and x["ma_don"] in da_co) or (d and luc_xuat(d) > g):
            trung.add(x["ma_don"])
        else:
            moi.append(x)
    return moi, len(trung)


def bill_tu_hoa_don(chuoi_json, san):
    """Tìm mã bill 'Bán cho người tiêu dùng - <Sàn> - <mã>' trong JSON hoá đơn (raw/chi tiết) lấy từ trang Thuế -> mã đơn hoặc ''."""
    for mb in _RE_BILL.finditer(chuoi_json or ""):
        sn = "tiktok" if mb.group(1).lower().startswith("tiktok") else mb.group(1).lower()
        if sn == san:
            return mb.group(2)
    return ""


def so_chua_hd(so, dong):
    """Số đơn trong `dong` (đã lọc) từng xuất file trước đó nhưng đồng bộ hoá đơn đầu ra sau đó vẫn chưa thấy hoá đơn (sẽ được xuất lại)."""
    return len({x["ma_don"] for x in dong if x["ma_don"] in so["don"] and not so["don"][x["ma_don"]].get("so_hd")})


def ghi_so_xuat(so, dong, san, thue_suat, ngay_hd, lo_id):
    """Ghi các đơn vừa xuất vào sổ (mỗi dòng: tên, sku, số lượng, tiền gồm VAT, thành tiền chưa thuế, tiền thuế)."""
    kct = str(thue_suat).strip().upper() in ("KCT", "KKKNT")
    ts = 0.0 if kct else float(str(thue_suat).replace("%", "").replace(",", ".") or 0)
    so["lo"].append({"id": lo_id, "luc": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"), "loai": "hd", "so_don": len({x["ma_don"] for x in dong})})
    for ma in {x["ma_don"] for x in dong}:
        if ma in so["don"] and not so["don"][ma].get("so_hd"):
            del so["don"][ma]                                         # xuất lại đơn MISA chưa có hoá đơn: thay mục cũ trong sổ
    for x in dong:
        d = so["don"].setdefault(x["ma_don"], {"lo": lo_id, "san": san, "ngay_hd": ngay_hd, "ngay_dat": x.get("ngay_dat") or x.get("ngay"), "ts": ts, "kct": kct,
                                               "dong": [], "tra": [], "da_dc": [], "so_hd": "", "ky_hieu": "", "ngay_so_hd": "", "can_dc": None,
                                               "ts_xuat": time.time()})
        thanh = round(float(x["thanh_tien"] or 0) / (1 + ts / 100.0))
        d["dong"].append({"ten": x["ten_hang"], "sku": x.get("sku") or "", "sl": float(x["so_luong"] or 1) or 1.0, "tien": round(float(x["thanh_tien"] or 0)),
                          "thanh": thanh, "thue": 0 if kct else round(thanh * ts / 100.0)})
        d["tra"].append(0)
        d["da_dc"].append(0)


def go_lo_cuoi(so):
    """Gỡ LÔ xuất hoá đơn gần nhất khỏi sổ (khi import vào MISA không thành công, muốn xuất lại). -> số đơn đã gỡ."""
    lo = [l for l in so["lo"] if l["loai"] == "hd"]
    if not lo:
        return 0
    cuoi = lo[-1]["id"]
    ma = [m for m, d in so["don"].items() if d["lo"] == cuoi]
    for m in ma:
        del so["don"][m]
    so["lo"] = [l for l in so["lo"] if l["id"] != cuoi]
    return len(ma)


def _qty_tra(x, sl_dong):
    """Số lượng đã trả/huỷ của 1 dòng file theo trạng thái hiện tại."""
    ok, ly = la_hop_le(x)
    if ok:
        return 0.0
    tra = float(x.get("sl_tra") or 0)
    if ly.startswith("trả hàng/hoàn tiền") and 0 < tra < sl_dong and not khong_dau(x.get("trang_thai")).startswith(("tra hang", "return", "refund")):
        return tra                                              # trả một phần
    return sl_dong                                              # huỷ đơn / trả cả đơn / trả hết số lượng


def cap_nhat_tra_hang(so, dong_goc):
    """Đối chiếu file đơn hàng MỚI với sổ: đơn đã xuất hoá đơn mà nay bị huỷ/trả hàng (toàn bộ hoặc một phần) -> đánh dấu 'cần điều chỉnh giảm'.
    -> danh sách mã đơn vừa phát hiện (mới hoặc phát sinh thêm)."""
    nhom = {}
    for x in dong_goc:
        if x["ma_don"] in so["don"]:
            nhom.setdefault(x["ma_don"], []).append(x)
    moi = []
    for ma, ds in nhom.items():
        d = so["don"][ma]
        dung = set()
        thay = False
        for j, L in enumerate(d["dong"]):
            r = next((i for i, x in enumerate(ds) if i not in dung and x["ten_hang"] == L["ten"] and (x.get("sku") or "") == L["sku"]), None)
            if r is None:
                continue
            dung.add(r)
            q = min(L["sl"], _qty_tra(ds[r], L["sl"]))
            if q > d["tra"][j]:
                d["tra"][j] = q
            if d["tra"][j] > d["da_dc"][j]:
                thay = True
        if thay:
            truoc = d["can_dc"]
            tong_tra = sum(d["tra"][j] - d["da_dc"][j] for j in range(len(d["dong"])) if d["tra"][j] > d["da_dc"][j])
            toan_bo = all(d["tra"][j] >= d["dong"][j]["sl"] for j in range(len(d["dong"])))
            d["can_dc"] = {"ngay": (truoc or {}).get("ngay") or datetime.datetime.now().strftime("%d/%m/%Y %H:%M"), "toan_bo": toan_bo,
                           "ly_do": ("huỷ/trả hàng toàn bộ đơn" if toan_bo else "trả hàng một phần"), "sl": tong_tra}
            if not truoc or truoc.get("sl") != tong_tra:
                moi.append(ma)
    return moi


def ds_can_dieu_chinh(so):
    kq = []
    for ma, d in so["don"].items():
        if d.get("can_dc"):
            kq.append({"ma_don": ma, "ngay_hd": d["ngay_hd"], "so_hd": d.get("so_hd") or "", "ky_hieu": d.get("ky_hieu") or so.get("ky_hieu_mac_dinh") or "", "ngay_phat_hien": d["can_dc"]["ngay"],
                       "ly_do": d["can_dc"]["ly_do"], "dong": [{"ten": d["dong"][j]["ten"], "sl_tra": d["tra"][j] - d["da_dc"][j]} for j in range(len(d["dong"])) if d["tra"][j] > d["da_dc"][j]]})
    return kq


HD_DC_BASE = ["Số thứ tự hóa đơn (*)", "Ngày hóa đơn", "Tên đơn vị mua hàng", "Mã số thuế", "Địa chỉ", "Người mua hàng", "Email", "Số điện thoại", "Căn cước công dân",
              "Hình thức thanh toán (*)", "HĐ bị điều chỉnh thuộc hệ thống khác", "Ký hiệu HĐ bị điều chỉnh (*)", "Số hóa đơn bị điều chỉnh (*)", "Ngày hóa đơn bị điều chỉnh",
              "Mã của CQT trên HĐ bị điều chỉnh", "Lý do điều chỉnh", "Tên hàng hóa/dịch vụ (*)", "ĐVT", "Số lượng", "Đơn giá", "Thành tiền"]


def sang_dieu_chinh(so, ds_ma, san="shopee", ngay_hd="", dvt="Cái", co_vat=True, httt="Tiền mặt/Chuyển khoản", chi_co_so_hd=True):
    """Dựng các hàng file import HOÁ ĐƠN ĐIỀU CHỈNH GIẢM (số lượng âm) theo mẫu MISA. Mỗi đơn = 1 hoá đơn điều chỉnh, mỗi dòng hàng bị trả 1 dòng.
    Đơn chưa có số hoá đơn gốc (chưa cập nhật từ MISA) -> bỏ qua nếu chi_co_so_hd. -> (hàng, tiêu đề, các mã đã dựng, các mã thiếu số hoá đơn gốc, ghi nhận để đánh dấu đã điều chỉnh)."""
    tieu_de = HD_DC_BASE + (["Thuế suất GTGT (%)", "Tiền thuế GTGT"] if co_vat else []) + ["Tổng tiền hàng", "Tổng tiền thanh toán"]
    ngay = ngay_hd or datetime.date.today().strftime("%d/%m/%Y")
    ten_san = SAN.get(san, {}).get("ten", san)
    ten_hd = SAN.get(san, {}).get("ten_hd") or ten_san
    rows, xong, thieu, ghi = [], [], [], []
    stt = 0
    for ma in ds_ma:
        d = so["don"].get(ma)
        if not d or not d.get("can_dc"):
            continue
        ky_hd = d.get("ky_hieu") or so.get("ky_hieu_mac_dinh") or ""
        if chi_co_so_hd and not (d.get("so_hd") and ky_hd):
            thieu.append(ma)
            continue
        stt += 1
        ly = f"Điều chỉnh giảm do khách trả hàng/huỷ đơn {ten_san} mã {ma}"
        dong_dc = []
        for j, L in enumerate(d["dong"]):
            q = d["tra"][j] - d["da_dc"][j]
            if q <= 0:
                continue
            dg = round(L["thanh"] / L["sl"])
            thanh = -L["thanh"] if q >= L["sl"] - d["da_dc"][j] and d["da_dc"][j] == 0 else -round(dg * q)
            thue = 0 if d.get("kct") else -round(abs(thanh) * float(d.get("ts") or 0) / 100.0)
            dong_dc.append((j, L, q, dg, thanh, thue))
        tong, tong_thue = sum(x[4] for x in dong_dc), sum(x[5] for x in dong_dc)
        for k, (j, L, q, dg, thanh, thue) in enumerate(dong_dc):
            h = [stt, ngay, "", "", "", f"Bán cho người tiêu dùng - {ten_hd} - {ma}", "", "", "", httt, "", ky_hd, d["so_hd"], d.get("ngay_so_hd") or d.get("ngay_hd") or "", "", ly,
                 L["ten"], dvt, -(int(q) if q == int(q) else q), dg, thanh]
            if co_vat:
                h += [("KCT" if d.get("kct") else (int(d["ts"]) if float(d["ts"]) == int(d["ts"]) else d["ts"])), thue]
            h += [tong if k == 0 else "", (tong + tong_thue) if k == 0 else ""]
            rows.append(h)
            ghi.append((ma, j, q))
        xong.append(ma)
    return rows, tieu_de, xong, thieu, ghi


def danh_dau_da_dieu_chinh(so, ghi):
    for ma, j, q in ghi:
        d = so["don"][ma]
        d["da_dc"][j] += q
    for ma in {g[0] for g in ghi}:
        d = so["don"][ma]
        if all(d["tra"][j] <= d["da_dc"][j] for j in range(len(d["dong"]))):
            d["can_dc"] = None
    so["lo"].append({"id": datetime.datetime.now().strftime("dc%Y%m%d%H%M%S%f"), "luc": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"), "loai": "dc", "so_don": len({g[0] for g in ghi})})


def danh_dau_dc_tu_gdt(so, dc):
    """Bill đã có hoá đơn điều chỉnh âm trên trang Thuế (dc: {mã đơn: {chua_thue,...}}) và số tiền điều chỉnh >= 99% số tiền cần điều chỉnh -> coi là ĐÃ điều chỉnh (không xuất điều chỉnh nữa).
    -> số đơn được đánh dấu."""
    n = 0
    for ma, v in dc.items():
        d = so["don"].get(ma)
        if not d or not d.get("can_dc"):
            continue
        can = sum(d["dong"][j]["thanh"] * (d["tra"][j] - d["da_dc"][j]) / (d["dong"][j]["sl"] or 1) for j in range(len(d["dong"])) if d["tra"][j] > d["da_dc"][j])
        if v["chua_thue"] >= can * 0.99 - 1:
            for j in range(len(d["dong"])):
                d["da_dc"][j] = max(d["da_dc"][j], d["tra"][j])
            d["can_dc"] = None
            d["dc_so_hd"] = ", ".join(v.get("ds") or [])
            n += 1
    return n


def ghi_file_dieu_chinh(rows, tieu_de, duong_dan):
    """File import hoá đơn điều chỉnh: giữ cấu trúc mẫu MISA (hướng dẫn ở dòng 1-7, tiêu đề dòng 9, dữ liệu từ dòng 10); bật bộ lọc cho mọi cột."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Hóa đơn bán hàng"
    for i, t in enumerate(["File mẫu danh sách hóa đơn để nhập vào phần mềm ", "Hướng dẫn:", "- Điền dữ liệu hóa đơn cần lập trên phần mềm vào các cột tương ứng trên file này",
                           "- Các cột có dấu (*) là những cột bắt buộc",
                           "- Tại cột Tổng tiền hàng, Tổng tiền thanh toán cần nhập tổng tiền hàng, tổng tiền thanh toán của hóa đơn (chỉ cần nhập dữ liệu tại dòng đầu tiên của hóa đơn tương ứng)",
                           "- Nếu muốn nhập thêm thông tin khác, người dùng có thể tự thêm cột trên file này",
                           "- Hoá đơn điều chỉnh GIẢM: Số lượng và Thành tiền ÂM; tạo bởi phần mềm kế toán từ sổ đơn đã xuất"], 1):
        ws.cell(i, 1).value = t
    for c, h in enumerate(tieu_de, 1):
        ws.cell(9, c).value = h
        ws.cell(9, c).font = Font(bold=True)
        ws.cell(9, c).fill = PatternFill("solid", fgColor="DDEBF7")
    cot_so = {tieu_de.index(h) + 1 for h in ("Số lượng", "Đơn giá", "Thành tiền", "Tiền thuế GTGT", "Tổng tiền hàng", "Tổng tiền thanh toán") if h in tieu_de}
    for ri, r in enumerate(rows, 10):
        for ci, v in enumerate(r, 1):
            cell = ws.cell(ri, ci)
            cell.value = v
            if ci in cot_so:
                cell.number_format = "#,##0"
            if ci in (12, 13, 14):
                cell.number_format = "@"
    for c in range(1, len(tieu_de) + 1):
        ws.column_dimensions[get_column_letter(c)].width = 18 if c != 17 else 60
    ws.freeze_panes = "A10"
    ws.auto_filter.ref = f"A9:{get_column_letter(len(tieu_de))}{max(len(rows) + 9, 10)}"
    wb.save(duong_dan)


_RE_BILL = re.compile(r"(shopee|tiktok(?:\s*shop)?|lazada)\s*[-–—]\s*([A-Za-z0-9]{6,40})", re.I)


def doc_ds_hoa_don_misa(noi_dung, ten_file):
    """Đọc file 'Danh sách hoá đơn' xuất từ MISA meInvoice (Excel) -> [{san, ma_don, ky_hieu, so_hd, ngay_hd, trang_thai}].
    Mã đơn lấy từ cột người mua dạng 'Bán cho người tiêu dùng - Shopee - <mã bill>' (quét mọi ô của dòng)."""
    kq = []
    for rows in _doc_bang(noi_dung, ten_file):
        cot = None
        for i, h in enumerate(rows[:40]):
            t = [khong_dau(x) for x in h]
            so = next((j for j, x in enumerate(t) if x in ("so hoa don", "so hd", "so hoa don (*)") or (x.startswith("so hoa don") and "dieu chinh" not in x and "thay the" not in x)), None)
            ky = next((j for j, x in enumerate(t) if "ky hieu" in x and "dieu chinh" not in x and "thay the" not in x), None)
            if so is not None:                                       # cột Ký hiệu có thể không có trong danh sách (dùng ký hiệu mặc định đã lưu)
                ngay = next((j for j, x in enumerate(t) if x.startswith("ngay hoa don") or x in ("ngay hd", "ngay lap", "ngay phat hanh") or x.startswith("ngay hd")), None)
                tt = next((j for j, x in enumerate(t) if "trang thai" in x and "cqt" not in x), None)
                cot = (i, so, ky, ngay, tt)
                break
        if not cot:
            continue
        hi, c_so, c_ky, c_ngay, c_tt = cot
        for r in rows[hi + 1:]:
            if not r or c_so >= len(r) or r[c_so] in (None, ""):
                continue
            chuoi = " | ".join(str(x) for x in r if x not in (None, ""))
            mb = _RE_BILL.search(chuoi)
            if not mb:
                continue
            sh = r[c_so]
            sh = str(int(sh)) if isinstance(sh, float) and sh == int(sh) else str(sh).strip()
            if sh.isdigit() and len(sh) < 8:
                sh = sh.zfill(8)
            san = "tiktok" if mb.group(1).lower().startswith("tiktok") else mb.group(1).lower()
            kq.append({"san": san, "ma_don": mb.group(2), "ky_hieu": str(r[c_ky]).strip() if c_ky is not None and c_ky < len(r) and r[c_ky] else "", "so_hd": sh,
                       "ngay_hd": _ngay(r[c_ngay]) if c_ngay is not None and c_ngay < len(r) else "", "trang_thai": str(r[c_tt]).strip() if c_tt is not None and c_tt < len(r) and r[c_tt] else ""})
    return kq


def cap_nhat_so_hoa_don(so, ds, san):
    """Gán số hoá đơn/ký hiệu/ngày (từ MISA) cho các đơn trong sổ theo mã bill. Bỏ qua hoá đơn đã bị huỷ/thay thế. -> (số đơn cập nhật, số hoá đơn không khớp đơn nào trong sổ)."""
    ok, khong = 0, 0
    for x in ds:
        if x["san"] != san:
            continue
        t = khong_dau(x["trang_thai"])
        if any(k in t for k in ("huy", "thay the", "xoa bo")):
            continue
        d = so["don"].get(x["ma_don"])
        if not d:
            khong += 1
            continue
        ky = x["ky_hieu"] or d.get("ky_hieu") or so.get("ky_hieu_mac_dinh") or ""
        if d.get("so_hd") != x["so_hd"] or d.get("ky_hieu") != ky:
            ok += 1
        d["so_hd"], d["ky_hieu"], d["ngay_so_hd"] = x["so_hd"], ky, x["ngay_hd"] or d.get("ngay_so_hd") or ""
    return ok, khong
