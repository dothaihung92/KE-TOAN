# Regression tests

Mỗi file `test_*.py` tái hiện ĐÚNG 1 lỗi thật đã gặp trên dữ liệu MISA/Thuế
thật của người dùng (không phải test lý thuyết) — trích trực tiếp hàm cần
test từ `server.py` (bằng `exec`, dò theo tên hàm, hoặc `import server`
thẳng), giả lập CSDL/kết nối MISA bằng các lớp `Fake*`, rồi assert kết quả
đúng như ca thật đã xác nhận với người dùng. Không dùng framework test nào —
mỗi file tự chạy độc lập bằng `python3 test_xxx.py`, tự in `PASS`/lỗi.

## Chạy toàn bộ

```
cd tests && ./run_all.sh
```

## Trước khi sửa `server.py`

Luôn chạy `run_all.sh` NGAY SAU khi sửa, trước khi commit — bộ test này là
lưới an toàn duy nhất để tránh sửa lỗi mới lại làm sống lại lỗi cũ đã từng
xác nhận với người dùng thật. Khi thêm 1 fix mới cho 1 lỗi người dùng báo,
luôn thêm kèm 1 test mới:
1. Viết test mô phỏng ĐÚNG dữ liệu/ca thật gây lỗi.
2. Xác nhận test FAIL trên code CŨ (`git stash` rồi chạy lại) — chứng minh
   test thật sự bắt được lỗi, không phải test giả.
3. Sửa code, xác nhận test PASS.
4. Chạy `run_all.sh` để chắc chắn không phá vỡ test nào khác.

## 4 test lỗi từ trước (KHÔNG liên quan các fix trong tests còn lại)

`test_doi_chieu_import.py`, `test_unt_du_phong.py`, `test_unt_unc.py`,
`test_unt_unc_ledger.py` hiện đang FAIL — lỗi trong CHÍNH bài test (thiếu
tên hàm phụ thuộc trong danh sách trích xuất `names`/`ns`, ví dụ
`_doc_nhap_lieu`/`_misa_bank_account_theo_so`), không phải lỗi thật trong
`server.py`. Đã tồn tại từ trước, chưa được sửa. Nếu cần sửa lại: thêm tên
hàm còn thiếu vào danh sách `names`/`for fn in (...)` ở đầu mỗi file rồi
chạy lại — cùng cách đã sửa `test_mua_hang_nk_ghi_so.py`/
`test_mua_hang_dv_ghi_so.py` (xem lịch sử git).
