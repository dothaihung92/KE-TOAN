#!/usr/bin/env python3
"""
Khởi chạy giao diện web tra cứu hoá đơn điện tử.

    python run_web.py            # mở http://127.0.0.1:5000
    PORT=8080 python run_web.py  # đổi cổng

Biến môi trường tuỳ chọn:
    HDDT_SECRET        - chuỗi bí mật để mã hoá mật khẩu công ty (nên đặt cố định)
    HDDT_FLASK_SECRET  - khoá ký session của Flask
    PORT               - cổng chạy web (mặc định 5000)
"""

import os

from webapp.app import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Mở trình duyệt tại: http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)
