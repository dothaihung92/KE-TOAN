"""
Hỗ trợ xử lý captcha của cổng hoá đơn điện tử.

Captcha trả về dưới dạng ảnh SVG. Cách an toàn và chính xác nhất là
hiển thị/lưu ảnh để người dùng tự nhập (manual). Ngoài ra có hỗ trợ
tuỳ chọn giải tự động bằng OCR nếu cài thêm thư viện (không bắt buộc).
"""

from __future__ import annotations

import os
import re
import tempfile
import webbrowser


def save_captcha_svg(svg_content: str, path: str | None = None) -> str:
    """Lưu nội dung SVG ra file, trả về đường dẫn file."""
    if path is None:
        fd, path = tempfile.mkstemp(suffix=".svg", prefix="captcha_")
        os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg_content)
    return path


def try_open_in_browser(path: str) -> bool:
    """Cố mở file captcha bằng trình duyệt mặc định (nếu có giao diện)."""
    try:
        return webbrowser.open(f"file://{os.path.abspath(path)}")
    except Exception:
        return False


def svg_to_png(svg_content: str, png_path: str) -> bool:
    """Chuyển SVG -> PNG nếu có cairosvg. Trả về True nếu thành công."""
    try:
        import cairosvg  # type: ignore
    except ImportError:
        return False
    try:
        cairosvg.svg2png(
            bytestring=svg_content.encode("utf-8"), write_to=png_path, scale=3
        )
        return True
    except Exception:
        return False


def solve_with_ocr(svg_content: str) -> str | None:
    """
    Thử giải captcha tự động bằng OCR (tesseract).
    Cần cài: cairosvg, pytesseract, Pillow và tesseract-ocr.
    Trả về chuỗi đoán được hoặc None nếu không khả dụng/không chắc.
    """
    try:
        import io

        import cairosvg  # type: ignore
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore
    except ImportError:
        return None
    try:
        png_bytes = cairosvg.svg2png(
            bytestring=svg_content.encode("utf-8"), scale=4
        )
        img = Image.open(io.BytesIO(png_bytes)).convert("L")
        text = pytesseract.image_to_string(
            img, config="--psm 8 -c tessedit_char_whitelist=0123456789"
        )
        text = re.sub(r"\D", "", text)
        return text or None
    except Exception:
        return None
