"""Báo cáo THỐNG KÊ (Phiếu 01/DN-ĐP của Cục Thống kê TP.HCM — gtsphcm.cosis.vn): tính số liệu từng tháng từ hoá đơn BÁN RA đã tra cứu.
Phiếu nhập theo tháng báo cáo T: phần "thực hiện tháng trước" là tháng T-1. Chỉ lấy được từ hoá đơn: doanh thu thuần (chưa thuế) và sản phẩm tiêu thụ (tên, ĐVT, số lượng, giá trị);
tồn kho, số lao động, dự tính… không có trong hoá đơn nên do người dùng nhập."""
import json
import re

DON_VI = 1_000_000          # phiếu tính theo TRIỆU ĐỒNG


def thang_truoc(thang, nam):
    return (12, nam - 1) if int(thang) == 1 else (int(thang) - 1, int(nam))


def _so(v):
    try:
        return float(str(v).replace(",", "")) if str(v).strip() != "" else 0.0
    except Exception:
        return 0.0


def _dong_hang(detail):
    try:
        d = json.loads(detail) if isinstance(detail, str) else (detail or {})
    except Exception:
        return []
    return d.get("hdhhdvu") or []


def tinh(hoa_don):
    """hoa_don: list dict {tgtcthue, tthai, raw?, detail_json?, shdon}. -> {doanh_thu_trieu, so_hd, sp:[{ten,dvt,sl,gia_tri_trieu}], thieu_chi_tiet}"""
    tong, sp, thieu, n = 0.0, {}, 0, 0
    for h in hoa_don:
        n += 1
        tong += _so(h.get("tgtcthue"))
        dong = _dong_hang(h.get("detail_json")) or _dong_hang(h.get("raw"))
        if not dong:
            thieu += 1
            continue
        for it in dong:
            ten = re.sub(r"\s+", " ", str(it.get("ten") or "").strip())
            if not ten or str(it.get("tchat") or "") in ("4",):        # bỏ dòng ghi chú/chiết khấu không phải hàng
                continue
            dvt = str(it.get("dvtinh") or "").strip()
            k = (ten.lower(), dvt.lower())
            x = sp.setdefault(k, {"ten": ten, "dvt": dvt, "sl": 0.0, "gia_tri": 0.0})
            x["sl"] += _so(it.get("sl"))
            x["gia_tri"] += _so(it.get("thtien"))
    ds = sorted(sp.values(), key=lambda x: -x["gia_tri"])
    return {"doanh_thu_trieu": round(tong / DON_VI, 3), "so_hd": n, "thieu_chi_tiet": thieu,
            "sp": [{"ten": x["ten"], "dvt": x["dvt"], "sl": round(x["sl"], 3), "gia_tri_trieu": round(x["gia_tri"] / DON_VI, 3)} for x in ds]}
