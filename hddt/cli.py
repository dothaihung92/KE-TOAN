"""
Giao diện dòng lệnh để tải hoá đơn điện tử từ cổng Tổng cục Thuế.

Ví dụ:
    python -m hddt.cli --tu-ngay 01/01/2024 --den-ngay 31/03/2024 \
        --loai purchase sold --xuat hoadon.xlsx

Có thể truyền tài khoản qua tham số, biến môi trường, hoặc nhập trực tiếp:
    HDDT_USERNAME, HDDT_PASSWORD
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from typing import List, Optional

from .captcha import save_captcha_svg, solve_with_ocr, svg_to_png, try_open_in_browser
from .client import INVOICE_ENDPOINTS, HoaDonDienTuClient, HddtError
from . import exporter

TYPE_SHEET_NAMES = {
    "purchase": "Mua vao",
    "sold": "Ban ra",
    "sco-purchase": "Mua vao (MTT)",
    "sco-sold": "Ban ra (MTT)",
}


def _login(client: HoaDonDienTuClient, username: str, password: str,
           auto_ocr: bool) -> None:
    """Thực hiện đăng nhập, xử lý captcha (tự động hoặc thủ công)."""
    last_err: Optional[str] = None
    for attempt in range(1, 6):
        captcha = client.get_captcha()
        svg = captcha["content"]
        captcha_value: Optional[str] = None

        if auto_ocr:
            captcha_value = solve_with_ocr(svg)
            if captcha_value:
                print(f"[OCR] Đoán captcha: {captcha_value}")

        if not captcha_value:
            svg_path = save_captcha_svg(svg)
            png_path = svg_path.replace(".svg", ".png")
            if svg_to_png(svg, png_path):
                print(f"Đã lưu captcha (PNG): {png_path}")
                try_open_in_browser(png_path)
            else:
                print(f"Đã lưu captcha (SVG): {svg_path}")
                try_open_in_browser(svg_path)
            print("Mở file trên để xem captcha.")
            captcha_value = input("Nhập captcha: ").strip()

        try:
            client.authenticate(username, password, captcha["key"], captcha_value)
            print("✓ Đăng nhập thành công.")
            return
        except HddtError as exc:
            last_err = str(exc)
            print(f"✗ Lần {attempt}: {last_err}")
            # Nếu OCR sai thì lần sau chuyển sang nhập tay
            auto_ocr = False
    raise HddtError(f"Đăng nhập thất bại sau nhiều lần. Lỗi cuối: {last_err}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="hddt",
        description="Tải dữ liệu hoá đơn điện tử từ hoadondientu.gdt.gov.vn",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--username", "--mst", dest="username",
                   default=os.environ.get("HDDT_USERNAME"),
                   help="Tài khoản đăng nhập (MST). Mặc định lấy từ HDDT_USERNAME.")
    p.add_argument("--password", dest="password",
                   default=os.environ.get("HDDT_PASSWORD"),
                   help="Mật khẩu. Mặc định lấy từ HDDT_PASSWORD (nên dùng biến môi trường).")
    p.add_argument("--tu-ngay", "--from", dest="from_date", required=True,
                   help="Từ ngày (dd/mm/yyyy hoặc yyyy-mm-dd).")
    p.add_argument("--den-ngay", "--to", dest="to_date", required=True,
                   help="Đến ngày (dd/mm/yyyy hoặc yyyy-mm-dd).")
    p.add_argument("--loai", "--type", dest="types", nargs="+",
                   choices=list(INVOICE_ENDPOINTS), default=["purchase", "sold"],
                   help="Loại hoá đơn cần tải.")
    p.add_argument("--ttxly", type=int, default=None,
                   help="Lọc theo trạng thái xử lý (vd 5). Bỏ trống = tất cả.")
    p.add_argument("--size", type=int, default=50, help="Số hoá đơn mỗi trang.")
    p.add_argument("--xuat", "--output", dest="output", default="hoadon.xlsx",
                   help="File xuất (.xlsx, .csv hoặc .json).")
    p.add_argument("--auto-ocr", action="store_true",
                   help="Thử giải captcha tự động bằng OCR (cần cài thêm thư viện).")
    p.add_argument("--token", default=None,
                   help="Dùng token có sẵn thay vì đăng nhập lại.")
    return p


def run(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    # Khởi tạo client / xác thực
    if args.token:
        client = HoaDonDienTuClient(token=args.token)
        print("Dùng token được cung cấp.")
    else:
        username = args.username or input("Tài khoản (MST): ").strip()
        password = args.password or getpass.getpass("Mật khẩu: ")
        client = HoaDonDienTuClient()
        try:
            _login(client, username, password, args.auto_ocr)
        except HddtError as exc:
            print(f"Lỗi: {exc}", file=sys.stderr)
            return 1

    # Tra cứu từng loại hoá đơn
    sheets = {}
    total = 0
    for inv_type in args.types:
        print(f"Đang tải hoá đơn loại '{inv_type}' ...")
        try:
            rows = client.query_invoices(
                inv_type, args.from_date, args.to_date,
                ttxly=args.ttxly, size=args.size,
            )
        except HddtError as exc:
            print(f"  ✗ Lỗi khi tải '{inv_type}': {exc}", file=sys.stderr)
            rows = []
        print(f"  ✓ {len(rows)} hoá đơn.")
        total += len(rows)
        sheets[TYPE_SHEET_NAMES.get(inv_type, inv_type)] = rows

    # Xuất file
    out = args.output
    ext = os.path.splitext(out)[1].lower()
    try:
        if ext == ".xlsx":
            exporter.to_excel(sheets, out)
        elif ext == ".csv":
            # CSV chỉ 1 bảng -> gộp tất cả, thêm cột phân loại
            merged = []
            for name, rows in sheets.items():
                for r in rows:
                    r = dict(r)
                    r["_loai"] = name
                    merged.append(r)
            exporter.to_csv(merged, out)
        elif ext == ".json":
            exporter.to_json(sheets, out)
        else:
            print(f"Định dạng không hỗ trợ: {ext}. Dùng .xlsx/.csv/.json",
                  file=sys.stderr)
            return 1
    except Exception as exc:  # noqa: BLE001
        print(f"Lỗi khi xuất file: {exc}", file=sys.stderr)
        return 1

    print(f"\n✓ Hoàn tất: {total} hoá đơn -> {out}")
    return 0


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
