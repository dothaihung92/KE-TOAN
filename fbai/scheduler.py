"""
Đăng các bài đã lên lịch mà đã tới giờ.

Không tự chạy nền — gọi run_due_posts() định kỳ bằng cron / Task Scheduler,
ví dụ mỗi 5 phút:

    * * * * *  cd /path/to/KE-TOAN && python -m fbai.scheduler

Cách này tránh phải chạy thêm một tiến trình thường trực trong ứng dụng web.
"""

from __future__ import annotations

from datetime import datetime

from . import db
from .client import FacebookApiError, FacebookClient


def run_due_posts(now: datetime | None = None) -> int:
    """Đăng mọi bài đã lên lịch đến hạn. Trả về số bài đã đăng thành công."""
    now = now or datetime.now()
    now_iso = now.isoformat(timespec="seconds")
    due = db.list_due_posts(now_iso)
    published = 0
    for post in due:
        token = db.get_page_token(post["page_ref_id"])
        if not token:
            db.mark_post_failed(post["id"], "Không tìm thấy access token của Fanpage")
            continue
        page = db.get_page(post["page_ref_id"])
        try:
            client = FacebookClient(token)
            result = client.publish_post(
                page["page_id"], post["noi_dung"],
                link=post["link"] or None,
                image_url=post["image_url"] or None,
            )
            fb_id = result.get("id") or result.get("post_id", "")
            db.mark_post_published(post["id"], fb_id)
            published += 1
        except FacebookApiError as exc:
            db.mark_post_failed(post["id"], str(exc))
    return published


if __name__ == "__main__":
    db.init_db()
    n = run_due_posts()
    print(f"Đã đăng {n} bài.")
