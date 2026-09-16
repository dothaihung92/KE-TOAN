import os
import re

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Regression test — lỗi THẬT vừa gặp: thêm 2 file dữ liệu mới
# (templates/cqt_catalogue.txt, templates/cqt_dia_ban.txt) để tự điền Mã
# CQT nơi nộp, đã lên build .275 và người dùng đã tự cập nhật phần mềm,
# nhưng tính năng vẫn không chạy — vì update.py (cơ chế tự cập nhật từ
# GitHub) có danh sách FILES CỐ ĐỊNH, quên thêm 2 file mới vào đó, nên
# 2 file dữ liệu chưa BAO GIỜ được tải về máy người dùng (server.py đọc
# không thấy file -> âm thầm trả về {} an toàn, y như chưa có tính năng).
#
# Test này đảm bảo KHÔNG lặp lại lỗi này: mọi file đang có sẵn trong thư
# mục templates/ của repo (dữ liệu/template tĩnh mà server.py đọc qua
# BASE_DIR lúc chạy) đều PHẢI có mặt trong danh sách FILES của update.py,
# nếu không người dùng tự cập nhật xong vẫn không nhận được file đó.


def _lay_danh_sach_files_update_py():
    src = open(os.path.join(_REPO_ROOT, 'update.py'), encoding='utf-8').read()
    m = re.search(r'FILES\s*=\s*\[(.*?)\]', src, re.DOTALL)
    assert m, "Không tìm thấy danh sách FILES trong update.py"
    return re.findall(r'"([^"]+)"', m.group(1))


# ===== Test 1 (QUAN TRỌNG — đúng lỗi thật vừa gặp): mọi file trong
# templates/ của repo phải có trong FILES của update.py. =====
files_trong_update = set(_lay_danh_sach_files_update_py())
thu_muc_templates = os.path.join(_REPO_ROOT, 'templates')
file_thuc_te = [f"templates/{ten}" for ten in os.listdir(thu_muc_templates)
                if os.path.isfile(os.path.join(thu_muc_templates, ten))]
assert file_thuc_te, "Thư mục templates/ đang rỗng — kiểm tra lại đường dẫn test"
thieu = [f for f in file_thuc_te if f not in files_trong_update]
assert not thieu, (
    f"Các file sau có trong thư mục templates/ nhưng THIẾU trong danh sách FILES của update.py — "
    f"người dùng tự cập nhật xong vẫn sẽ KHÔNG nhận được các file này: {thieu}")
print(f"PASS 1: toàn bộ {len(file_thuc_te)} file trong templates/ đều có mặt trong danh sách FILES "
      f"của update.py — người dùng cập nhật sẽ nhận đủ file.")

# ===== Test 2 (không hồi quy): 2 file dữ liệu Mã CQT cụ thể (đúng lỗi vừa
# gặp) phải có mặt, tránh sót lại nếu ai đó lỡ xoá dòng khỏi FILES. =====
for ten_file in ("templates/cqt_catalogue.txt", "templates/cqt_dia_ban.txt"):
    assert ten_file in files_trong_update, f"'{ten_file}' phải có trong FILES của update.py — got {files_trong_update}"
print("PASS 2: 2 file dữ liệu Mã CQT (cqt_catalogue.txt, cqt_dia_ban.txt) có mặt trong FILES của update.py.")

print("\nALL DONE")
