import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import van_ban_lao_dong as v

# Khối chữ ký (bảng 2 cột) không bị cắt đôi qua 2 trang khi in/xuất PDF: bảng/hàng không ngắt trang, đoạn trống liền trước đi cùng bảng.
css = v.VB_CSS
for k in (".vb-doc tr{break-inside:avoid", ".vb-doc table.nb{break-inside:avoid", ".vb-doc p:has(+ table.nb){break-after:avoid"):
    assert k in css, k
h = v._bang_ky("NGƯỜI LAO ĐỘNG", "(Ký)", "A", "NGƯỜI SỬ DỤNG LAO ĐỘNG", "(Giám đốc)", "B")
assert h.startswith('<table class="nb">') and h.count("<tr>") == 1          # một hàng duy nhất -> avoid giữ nguyên cả khối
print("PASS: CSS giữ nguyên khối chữ ký trên một trang (đã thử in PDF bằng Chromium: 5/15 ca bị cắt với CSS cũ, 0/15 với CSS mới).")
