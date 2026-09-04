#!/usr/bin/env bash
# Chạy toàn bộ regression test trong thư mục này. Mỗi file test_*.py là 1
# kịch bản độc lập (không dùng pytest — tự exec, tự assert, tự in PASS/FAIL)
# tái hiện ĐÚNG 1 lỗi thật đã gặp trên dữ liệu MISA/Thuế thật của người dùng,
# xác nhận nó KHÔNG còn xảy ra nữa. Chạy lại bộ này sau MỌI thay đổi ở
# server.py để tránh sửa lỗi mới lại làm sống lại lỗi cũ.
#
# Dùng: cd tests && ./run_all.sh
set -uo pipefail
cd "$(dirname "$0")"

fail=0
total=0
for f in test_*.py; do
    total=$((total + 1))
    if ! output=$(python3 "$f" 2>&1); then
        fail=$((fail + 1))
        echo "=== FAIL: $f ==="
        echo "$output" | tail -15
        echo
    fi
done

echo "----------------------------------------"
echo "$((total - fail))/$total PASS"
if [ "$fail" -gt 0 ]; then
    echo "$fail file(s) FAILED — xem chi tiết ở trên."
    exit 1
fi
echo "TẤT CẢ PASS"
