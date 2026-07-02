"""
fbai - Quản lý Fanpage Facebook + quảng cáo sản phẩm bằng AI.

Dùng đúng API chính thức của Meta (Graph API cho Fanpage, Marketing API cho
quảng cáo) — không giả lập trình duyệt, không auto-like/auto-comment/kết bạn
hàng loạt. Người dùng tự cung cấp Page Access Token / Ad Account do chính họ
sở hữu và chịu trách nhiệm tuân thủ Điều khoản dịch vụ của Meta.
"""

from .client import FacebookClient, FacebookApiError
from .content import generate_post_content

__all__ = ["FacebookClient", "FacebookApiError", "generate_post_content"]
__version__ = "1.0.0"
