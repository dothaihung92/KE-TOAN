#!/usr/bin/env python3
"""
Khởi chạy phần mềm phân tích chứng khoán Việt Nam.

    pip install -r stock_analyzer/requirements.txt
    python run_stock_analyzer.py            # mở http://127.0.0.1:5050
    PORT=8090 python run_stock_analyzer.py   # đổi cổng

Biến môi trường tuỳ chọn:
    STOCK_FLASK_SECRET          - khoá ký session của Flask
    STOCK_PRICE_REFRESH_MINUTES - chu kỳ làm mới giá (mặc định 15 phút)
    STOCK_NEWS_REFRESH_MINUTES  - chu kỳ làm mới tin tức (mặc định 10 phút)
    STOCK_NEWS_RSS_URL          - đổi nguồn RSS tin tức thị trường
    PORT                        - cổng chạy web (mặc định 5050)
    NO_BROWSER=1                - không tự mở trình duyệt
"""

import os
import threading
import webbrowser


def _open_browser(url: str) -> None:
    try:
        webbrowser.open(url)
    except Exception:
        pass


def main() -> None:
    from stock_analyzer.app import create_app

    app = create_app()

    port = int(os.environ.get("PORT", 5050))
    url = f"http://127.0.0.1:{port}"

    print("=" * 60)
    print("  PHẦN MỀM PHÂN TÍCH CHỨNG KHOÁN VIỆT NAM")
    print("=" * 60)
    print(f"  Máy chủ đang chạy tại: {url}")
    print("  Đang tải dữ liệu giá + tin tức lần đầu ở nền, có thể mất")
    print("  khoảng một phút để hiện đầy đủ khuyến nghị.")
    print("  Nhấn Ctrl+C để dừng phần mềm.")
    print("=" * 60)

    if os.environ.get("NO_BROWSER") != "1":
        threading.Timer(1.2, _open_browser, args=(url,)).start()

    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
