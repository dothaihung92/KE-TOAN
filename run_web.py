#!/usr/bin/env python3
"""
Khởi chạy giao diện web tra cứu hoá đơn điện tử.

    python run_web.py            # mở http://127.0.0.1:5000
    PORT=8080 python run_web.py  # đổi cổng

Biến môi trường tuỳ chọn:
    HDDT_SECRET        - chuỗi bí mật để mã hoá mật khẩu công ty (nên đặt cố định)
    HDDT_FLASK_SECRET  - khoá ký session của Flask
    PORT               - cổng chạy web (mặc định 5000)
    NO_BROWSER=1       - không tự mở trình duyệt
"""

import os
import threading
import webbrowser


def _open_browser(url: str) -> None:
    """Mở trình duyệt sau khi máy chủ kịp khởi động."""
    try:
        webbrowser.open(url)
    except Exception:
        pass


def main() -> None:
    from webapp.app import app

    port = int(os.environ.get("PORT", 5000))
    url = f"http://127.0.0.1:{port}"

    print("=" * 56)
    print("  PHẦN MỀM TRA CỨU HOÁ ĐƠN ĐIỆN TỬ")
    print("=" * 56)
    print(f"  Máy chủ đang chạy tại: {url}")
    print("  Nếu trình duyệt không tự mở, hãy copy địa chỉ trên")
    print("  vào trình duyệt (Chrome/Edge/Firefox).")
    print("  Nhấn Ctrl+C để dừng phần mềm.")
    print("=" * 56)

    # Tự mở trình duyệt sau ~1.2 giây (trừ khi tắt bằng NO_BROWSER=1)
    if os.environ.get("NO_BROWSER") != "1":
        threading.Timer(1.2, _open_browser, args=(url,)).start()

    # use_reloader=False để không khởi động 2 lần (tránh mở 2 tab)
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
