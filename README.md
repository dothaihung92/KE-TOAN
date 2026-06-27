# Phần mềm Quản lý Hóa đơn điện tử — Đa công ty

Kết nối trang **hoadondientu.gdt.gov.vn** của Tổng cục Thuế để tra cứu và tải hóa
đơn (XML, Excel tổng hợp, HTML) cho **nhiều công ty**, mỗi công ty một tài khoản
thuế riêng. Phù hợp cho **dịch vụ kế toán** quản lý nhiều khách hàng.

Backend: **FastAPI + SQLite**. Giao diện: 1 trang web (`static/index.html`).

> ⚠️ Chỉ dùng để truy xuất dữ liệu hoá đơn mà bạn có quyền truy cập hợp pháp
> (tài khoản của doanh nghiệp bạn hoặc khách hàng đã uỷ quyền). Đăng nhập bằng
> chính tài khoản thật của bạn → hợp pháp, đúng quyền.

---

## 🚀 Cách chạy

### Bước 1: Cài Python (chỉ làm 1 lần)
- Tải tại: <https://www.python.org/downloads/>
- **Quan trọng:** khi cài, tick vào ô **"Add Python to PATH"**

### Bước 2: Chạy phần mềm
- **Windows:** bấm đúp vào file **`start.bat`**
- **Mac/Linux:** chạy `./start.sh` trong Terminal

Lần đầu sẽ tự cài thư viện (hơi chậm ~1-2 phút). Các lần sau mở nhanh.
Trình duyệt tự mở tại `http://127.0.0.1:8686`. Để tắt: đóng cửa sổ đen / Ctrl+C.

Hoặc chạy thủ công:

```bash
pip install -r requirements.txt
python server.py
```

---

## 📋 Cách sử dụng

1. **Thêm công ty** (nút "+ Thêm công ty"): nhập tên, MST, tài khoản + mật khẩu
   trang Thuế của công ty đó.
2. **Chọn công ty** → **1. Đăng nhập**: bấm "Lấy mã", nhập captcha, Đăng nhập.
3. **2. Tra cứu**: chọn khoảng ngày, chọn mua vào / bán ra → "Tra cứu hóa đơn".
4. **3. Tải dữ liệu**: xem bảng, rồi tải **XML (.zip)** hoặc **Xuất Excel tổng hợp**.

### Tra cứu nhiều công ty cùng lúc (batch)

Sau khi đã đăng nhập cho từng công ty, dùng khu **"Tra cứu hàng loạt"** để chọn
nhiều công ty và lấy hóa đơn cho tất cả trong một lần — chạy lần lượt từng công
ty (an toàn, tránh bị Tổng cục Thuế chặn tạm 429).

Dữ liệu được lưu lại trong `data/hddt.db` nên lần sau mở vẫn còn.

---

## 🔒 Bảo mật & dữ liệu
- Toàn bộ thông tin (kể cả mật khẩu) lưu **cục bộ** trên máy bạn trong `data/hddt.db`.
- Phần mềm chỉ kết nối tới trang Tổng cục Thuế, không gửi dữ liệu đi đâu khác.
- Thư mục `data/` và `downloads/` đã được `.gitignore` — **không commit** lên git.

---

## ⚠️ Lưu ý kỹ thuật

Tổng cục Thuế **không công bố API chính thức**. Phần mềm dùng các endpoint nội bộ
mà trình duyệt gọi khi thao tác trên web. Các đường dẫn nằm gọn trong class
`GDTClient` ở đầu `server.py`:

- `/api/captcha` — lấy captcha
- `/api/security-taxpayer/authenticate` — đăng nhập
- `/api/query/invoices/{purchase,sold}` (và `/api/sco-query/...` cho hóa đơn
  máy tính tiền) — tra cứu
- `/api/query/invoices/export-xml` — tải XML
- `/api/query/invoices/detail` — chi tiết hóa đơn

**Nếu Tổng cục Thuế đổi cấu trúc** (lỗi 404, login fail dù mật khẩu đúng, captcha
không hiện): mở Chrome → F12 → tab **Network** → đăng nhập + tra cứu → xem các
request (lọc `Fetch/XHR`) để lấy URL/payload/header thật, rồi sửa trong `GDTClient`.

---

## 🛠️ Cấu trúc

```
server.py                       # Backend FastAPI + GDTClient gọi API Thuế
static/index.html               # Toàn bộ giao diện
templates/htkk_01gtgt_template.xml  # Mẫu tờ khai HTKK 01/GTGT
start.bat / start.sh            # Chạy nhanh trên Windows / Mac-Linux
requirements.txt                # Thư viện cần cài
data/hddt.db                    # CSDL (tự tạo — KHÔNG commit)
downloads/                      # File tải về (tự tạo — KHÔNG commit)
```

## Miễn trừ trách nhiệm

Đây là công cụ độc lập, không liên kết với Tổng cục Thuế. Người dùng tự chịu
trách nhiệm về việc sử dụng đúng quy định và chỉ truy cập dữ liệu hợp pháp.
