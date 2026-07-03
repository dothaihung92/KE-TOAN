# Phần mềm phân tích chứng khoán Việt Nam

Ứng dụng web độc lập (không đụng tới code kế toán/hoá đơn điện tử trong
repo này), gợi ý **mua/bán/giữ** cho các mã cổ phiếu Việt Nam dựa trên:

- **Phân tích kỹ thuật**: SMA/EMA, RSI, MACD, Bollinger Bands, khối lượng
  giao dịch → chấm điểm theo quy tắc rõ ràng, dễ giải thích.
- **Tin tức**: tin theo từng mã (qua vnstock) + tin thị trường chung (RSS
  CafeF) → chấm điểm cảm xúc tích cực/tiêu cực bằng từ điển từ khoá tiếng
  Việt.
- Điểm kỹ thuật (70%) + điểm tin tức (30%) → khuyến nghị: **MUA MẠNH /
  MUA / GIỮ / BÁN / BÁN MẠNH**, kèm danh sách lý do.

Dữ liệu giá & tin tức lấy qua thư viện mã nguồn mở
[vnstock](https://github.com/thinh-vu/vnstock) (miễn phí, không cần tài
khoản công ty chứng khoán).

## ⚠️ Về việc "liên kết" với tài khoản VCBS

**VCBS không cung cấp API công khai** cho nhà đầu tư cá nhân để bên thứ ba
tự động đọc số dư/lệnh giao dịch. Vì vậy phần mềm này **không** lưu và
**không** yêu cầu tài khoản/mật khẩu VCBS của bạn (tự động hoá đăng nhập
để lấy dữ liệu sẽ vi phạm điều khoản dịch vụ của VCBS và có rủi ro bảo
mật nếu để lộ thông tin đăng nhập).

Thay vào đó, dùng cách **an toàn**:

1. Đăng nhập [VCBS Trade](https://www.vcbs.com.vn/) như bình thường.
2. Vào mục **Danh mục / Sao kê tài khoản**, xuất ra file Excel hoặc CSV.
3. Vào trang **Danh mục của tôi** trong ứng dụng này, tải file đó lên.

Ứng dụng sẽ tự nhận diện cột **Mã CK / Số lượng / Giá vốn** (chấp nhận
tiêu đề có dấu hoặc không dấu), tính lãi/lỗ theo giá thị trường mới nhất,
và hiển thị khuyến nghị mua/bán riêng cho từng mã bạn đang nắm giữ. Không
có thông tin nhạy cảm nào được gửi ra ngoài.

## Cài đặt & chạy

```bash
pip install -r stock_analyzer/requirements.txt
python run_stock_analyzer.py
# Mở trình duyệt: http://127.0.0.1:5050
```

Lần đầu chạy, ứng dụng tự tạo danh sách theo dõi mặc định (các mã vốn hoá
lớn, thanh khoản cao) và lấy dữ liệu ở nền - có thể mất khoảng một phút để
hiện đầy đủ khuyến nghị. Giá và tin tức tự động làm mới định kỳ (mặc định
15 phút/lần với giá, 10 phút/lần với tin tức); trang tự động cập nhật lại
mà không cần tải lại (F5). Có thể bấm **"Làm mới ngay"** để cập nhật thủ
công bất cứ lúc nào.

## Cấu trúc

```
stock_analyzer/
  analysis/
    indicators.py   # SMA/EMA/RSI/MACD/Bollinger (pandas thuần)
    signals.py       # Chấm điểm kỹ thuật -1..1 kèm lý do
    sentiment.py      # Chấm điểm cảm xúc tin tức (từ điển từ khoá)
    recommend.py       # Kết hợp kỹ thuật + tin tức -> khuyến nghị cuối
  data_sources/
    market.py        # Lấy giá lịch sử qua vnstock
    news.py            # Lấy tin theo mã (vnstock) + tin thị trường (RSS)
  portfolio/
    importer.py       # Đọc file sao kê VCBS (Excel/CSV), nhận diện cột linh hoạt
  db.py                # SQLite: watchlist, cache khuyến nghị, tin tức, danh mục
  scheduler.py           # Tác vụ nền làm mới dữ liệu định kỳ (APScheduler)
  app.py                  # Flask app + routes
  templates/, static/      # Giao diện web
run_stock_analyzer.py       # Khởi chạy
```

## Giới hạn cần biết

- Đây là **công cụ hỗ trợ tham khảo** dựa trên chỉ báo kỹ thuật và tin tức
  tự động, **không phải khuyến nghị đầu tư chuyên nghiệp**. Tự chịu trách
  nhiệm với quyết định đầu tư của bạn.
- vnstock lấy dữ liệu công khai từ các công ty chứng khoán (VCI mặc định);
  nếu nguồn dữ liệu thay đổi cấu trúc hoặc chặn truy cập, một số mã có thể
  tạm thời không lấy được dữ liệu - ứng dụng sẽ hiển thị lỗi rõ ràng thay
  vì hiển thị số liệu sai.
- Cần có kết nối Internet để lấy giá/tin tức; nếu chạy trong môi trường bị
  chặn mạng ra ngoài (proxy công ty, sandbox...), phần lấy dữ liệu sẽ báo
  lỗi cho tới khi chạy ở môi trường có Internet bình thường.
