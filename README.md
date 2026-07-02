# Phần mềm lấy dữ liệu hoá đơn điện tử (HĐĐT)

Công cụ tải dữ liệu hoá đơn điện tử của **chính doanh nghiệp** từ cổng tra cứu
chính thức của Tổng cục Thuế: <https://hoadondientu.gdt.gov.vn>.

Sử dụng đúng API mà trang web của Tổng cục Thuế dùng (đăng nhập bằng tài khoản
HĐĐT + captcha), sau đó tải hoá đơn **mua vào / bán ra** (kể cả hoá đơn máy tính
tiền) và xuất ra **Excel / CSV / JSON**.

> ⚠️ Chỉ dùng để truy xuất dữ liệu hoá đơn mà bạn có quyền truy cập hợp pháp
> (tài khoản của doanh nghiệp bạn hoặc khách hàng đã uỷ quyền). Hãy tuân thủ
> điều khoản sử dụng của Tổng cục Thuế.

## Tính năng

- Đăng nhập bằng tài khoản HĐĐT, hỗ trợ nhập captcha thủ công (an toàn nhất)
  hoặc thử giải tự động bằng OCR.
- Tải hoá đơn theo khoảng thời gian, tự động phân trang để lấy **toàn bộ**.
- 4 loại hoá đơn: `purchase` (mua vào), `sold` (bán ra),
  `sco-purchase` / `sco-sold` (hoá đơn máy tính tiền).
- Xuất Excel nhiều sheet, hoặc CSV / JSON.
- Dùng được như thư viện Python hoặc công cụ dòng lệnh.

## Cài đặt

```bash
pip install -r requirements.txt
```

(Tuỳ chọn để dùng `--auto-ocr`: bỏ comment các dòng `cairosvg`, `pytesseract`,
`Pillow` trong `requirements.txt` và cài thêm `tesseract-ocr` của hệ điều hành.)

## Dùng nhanh (dòng lệnh)

```bash
# Đặt tài khoản qua biến môi trường để không lộ trên dòng lệnh
export HDDT_USERNAME="0312345678"        # MST / tài khoản
export HDDT_PASSWORD="mat_khau_cua_ban"

python -m hddt.cli \
  --tu-ngay 01/01/2024 --den-ngay 31/03/2024 \
  --loai purchase sold \
  --xuat hoadon_Q1.xlsx
```

Chương trình sẽ lấy captcha, lưu thành file ảnh và mở ra; bạn nhìn rồi gõ captcha
để đăng nhập. Sau đó nó tải hoá đơn và xuất ra file.

### Các tham số chính

| Tham số | Ý nghĩa |
|---|---|
| `--tu-ngay`, `--den-ngay` | Khoảng thời gian (dd/mm/yyyy hoặc yyyy-mm-dd) |
| `--loai` | `purchase`, `sold`, `sco-purchase`, `sco-sold` |
| `--ttxly` | Lọc theo trạng thái xử lý (vd `5`); bỏ trống = tất cả |
| `--xuat` | File xuất `.xlsx`, `.csv` hoặc `.json` |
| `--auto-ocr` | Thử giải captcha tự động (cần cài thêm thư viện) |
| `--token` | Dùng token có sẵn thay vì đăng nhập |

## Dùng như thư viện

```python
from hddt import HoaDonDienTuClient

client = HoaDonDienTuClient()

# 1. Lấy captcha
captcha = client.get_captcha()
# captcha["content"] là ảnh SVG -> hiển thị cho người dùng giải
cvalue = input("Nhập captcha: ")

# 2. Đăng nhập
client.authenticate("0312345678", "mat_khau", captcha["key"], cvalue)

# 3. Tra cứu (tự phân trang)
hoa_don = client.query_invoices(
    "purchase", "01/01/2024", "31/03/2024"
)
print(len(hoa_don), "hoá đơn")

# 4. Chi tiết một hoá đơn
chi_tiet = client.get_invoice_detail(
    nbmst="0312345678", khhdon="C24TAA", khmshdon=1, shdon=123
)
```

## Giao diện web (cho dịch vụ kế toán)

Nếu bạn quản lý nhiều công ty, dùng giao diện web để **lưu tài khoản từng công ty**
và tra cứu nhanh:

```bash
# Nên đặt chuỗi bí mật cố định để mã hoá mật khẩu công ty
export HDDT_SECRET="mot_chuoi_bi_mat_dai_va_ngau_nhien"
python run_web.py
# Mở trình duyệt: http://127.0.0.1:5000
```

Chức năng web:

- **Quản lý công ty**: thêm / sửa / xoá danh sách công ty (tên, MST, mật khẩu).
  Mật khẩu được **mã hoá** (Fernet) trước khi lưu vào SQLite — không lưu văn bản thường.
- **Đăng nhập trên web**: bấm *Tra cứu* ở một công ty → hiển thị **captcha trực tiếp**
  trên trình duyệt, MST/mật khẩu tự điền, bạn chỉ cần gõ captcha.
- **Tra cứu** hoá đơn mua vào / bán ra (kể cả máy tính tiền) theo khoảng thời gian,
  xem bảng kết quả ngay.
- **Tải xuống** Excel hoặc CSV.

> 🔐 Thư mục `instance/` chứa CSDL công ty và khoá mã hoá — đã được `.gitignore`,
> **không commit** lên git. Hãy sao lưu và bảo vệ thư mục này.

## Fanpage AI — đăng bài & quản lý quảng cáo sản phẩm

Module `fbai/` cho phép dùng AI soạn nội dung, lên lịch đăng bài và tạo chiến
dịch quảng cáo sản phẩm cho Fanpage Facebook, **thông qua Graph API /
Marketing API chính thức của Meta** — không giả lập trình duyệt, không
auto-like/comment/kết bạn hàng loạt (những hành vi đó vi phạm điều khoản
Meta và dễ bị khoá page/tài khoản quảng cáo).

### Chuẩn bị

1. Tạo Facebook App tại <https://developers.facebook.com/apps>.
2. Lấy **Page Access Token** (quyền `pages_manage_posts`,
   `pages_read_engagement`, và `ads_management` nếu muốn chạy quảng cáo) qua
   [Graph API Explorer](https://developers.facebook.com/tools/explorer/).
3. (Tuỳ chọn, để chạy quảng cáo) Lấy **Ad Account ID** trong Ads Manager.
4. (Tuỳ chọn, để AI viết nội dung tự nhiên hơn) Đặt biến môi trường
   `ANTHROPIC_API_KEY` hoặc `OPENAI_API_KEY`. Nếu không có, hệ thống dùng
   mẫu nội dung có sẵn.

### Dùng trên web

Trong giao diện web (`python run_web.py`), vào mục **Fanpage AI**:

- **Kết nối Fanpage**: nhập Page ID + Access Token (mã hoá khi lưu, giống
  mật khẩu công ty).
- **Sản phẩm**: khai báo tên/mô tả/giá/link sản phẩm.
- **AI soạn bài**: bấm "AI soạn bài" ở một sản phẩm để AI viết nội dung,
  xem lại/sửa rồi chọn đăng ngay hoặc lên lịch.
- **Quảng cáo**: tạo chiến dịch cho một sản phẩm với ngân sách/ngày — chiến
  dịch luôn được tạo ở trạng thái **PAUSED**, bạn tự vào Ads Manager duyệt
  đối tượng mục tiêu rồi bật chạy (hệ thống không tự chi tiền quảng cáo).

### Tự động đăng bài đến hạn

Bài đã lên lịch cần một tiến trình đăng đúng giờ. Chạy định kỳ bằng cron:

```bash
# ví dụ: mỗi 5 phút
*/5 * * * * cd /path/to/KE-TOAN && python -m fbai.scheduler
```

Hoặc bấm nút "Đăng ngay các bài đến hạn" trên giao diện web.

> ⚠️ Bạn tự chịu trách nhiệm tuân thủ Điều khoản dịch vụ của Meta và các quy
> định quảng cáo hiện hành. Đây là công cụ hỗ trợ, không đảm bảo hiệu quả
> marketing hay việc Meta phê duyệt quảng cáo.

## Cấu trúc dự án

```
hddt/                 # Thư viện lõi tra cứu hoá đơn điện tử
  client.py           # Giao tiếp API: captcha, đăng nhập, tra cứu hoá đơn
  captcha.py          # Lưu / hiển thị / (tuỳ chọn) OCR captcha
  exporter.py         # Xuất JSON / CSV / Excel
  cli.py              # Giao diện dòng lệnh
fbai/                 # Fanpage AI: đăng bài & quảng cáo sản phẩm
  client.py           # Giao tiếp Graph API (Fanpage) + Marketing API (quảng cáo)
  content.py          # Sinh nội dung bài đăng bằng AI (hoặc mẫu có sẵn)
  db.py               # Quản lý Fanpage/sản phẩm/lịch đăng/chiến dịch (SQLite)
  scheduler.py         # Đăng các bài đã lên lịch (chạy qua cron)
webapp/               # Giao diện web
  app.py              # Các route Flask (hoá đơn điện tử)
  fb_app.py            # Các route Flask (Fanpage AI)
  db.py               # Quản lý công ty + mã hoá mật khẩu (SQLite)
  templates/          # Giao diện HTML
run_web.py            # Khởi chạy web
```

## Ghi chú kỹ thuật

- API gốc: `https://hoadondientu.gdt.gov.vn` (có thể đổi qua biến môi trường `HDDT_API_URL`)
- Token (JWT) có thời hạn; khi hết hạn cần đăng nhập lại.
- Các mã trường chính: `nbmst` (MST bán), `nmmst` (MST mua), `shdon` (số HĐ),
  `tdlap` (ngày lập), `tgtttbso` (tổng tiền thanh toán)...

## Miễn trừ trách nhiệm

Đây là công cụ độc lập, không liên kết với Tổng cục Thuế. Người dùng tự chịu
trách nhiệm về việc sử dụng đúng quy định và chỉ truy cập dữ liệu hợp pháp.
