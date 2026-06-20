"""
hddt - Thư viện lấy dữ liệu hoá đơn điện tử từ cổng Tổng cục Thuế
(https://hoadondientu.gdt.gov.vn).

Sử dụng API chính thức của cổng tra cứu HĐĐT để đăng nhập và tải về
dữ liệu hoá đơn mua vào / bán ra của chính doanh nghiệp.
"""

from .client import HoaDonDienTuClient, HddtError

__all__ = ["HoaDonDienTuClient", "HddtError"]
__version__ = "1.0.0"
