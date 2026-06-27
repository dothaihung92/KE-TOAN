#!/bin/bash
echo "============================================================"
echo "   PHẦN MỀM QUẢN LÝ HÓA ĐƠN ĐIỆN TỬ - ĐA CÔNG TY"
echo "============================================================"
cd "$(dirname "$0")"

if ! command -v python3 &> /dev/null; then
    echo "[LỖI] Chưa cài Python3. Cài tại https://www.python.org/downloads/"
    read -p "Nhấn Enter để thoát..."; exit 1
fi

if [ ! -f ".installed" ]; then
    echo "[*] Lần đầu chạy - đang cài thư viện..."
    python3 -m pip install -r requirements.txt --break-system-packages 2>/dev/null || python3 -m pip install -r requirements.txt
    touch .installed
fi

echo "[*] Khởi động... Trình duyệt sẽ mở tại http://127.0.0.1:8686"
echo "[*] Để tắt: nhấn Ctrl+C"
python3 server.py
