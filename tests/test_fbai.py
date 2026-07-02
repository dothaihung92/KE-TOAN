"""Kiểm thử cơ bản không cần mạng cho fbai (client / content / db)."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fbai.client import FacebookApiError, FacebookClient  # noqa: E402
from fbai.content import generate_post_content  # noqa: E402


def test_client_requires_token():
    try:
        FacebookClient("")
    except FacebookApiError:
        pass
    else:
        raise AssertionError("Phải báo lỗi khi thiếu access token")


def test_client_base_url():
    c = FacebookClient("token123")
    assert c.base_url.startswith("https://graph.facebook.com/v")


def test_generate_post_content_fallback_no_keys():
    # Đảm bảo không có API key -> dùng template, không gọi mạng
    os.environ.pop("ANTHROPIC_API_KEY", None)
    os.environ.pop("OPENAI_API_KEY", None)
    text = generate_post_content("Áo thun nam", "Vải cotton thoáng mát", "199.000đ")
    assert "Áo thun nam" in text
    assert "199.000đ" in text


def test_fbai_db_crud():
    with tempfile.TemporaryDirectory() as d:
        os.environ["HDDT_SECRET"] = "test-secret-key-for-fbai"
        import webapp.db as wdb
        wdb.INSTANCE_DIR = d
        wdb.DB_PATH = os.path.join(d, "ketoan.db")
        wdb.KEY_PATH = os.path.join(d, "secret.key")

        from fbai import db as fbdb
        fbdb.init_db()

        ref_id = fbdb.add_page("Shop Test", "1234567890", "EAABtoken", "999888")
        page = fbdb.get_page(ref_id)
        assert page["ten"] == "Shop Test"
        assert fbdb.get_page_token(ref_id) == "EAABtoken"

        product_id = fbdb.add_product(ref_id, "Áo thun", "Cotton", "199.000đ", "https://vd.com")
        assert len(fbdb.list_products(ref_id)) == 1

        post_id = fbdb.add_scheduled_post(ref_id, "Nội dung test", "2026-01-01T10:00:00")
        due = fbdb.list_due_posts("2030-01-01T00:00:00")
        assert any(p["id"] == post_id for p in due)

        fbdb.mark_post_published(post_id, "fbpost_1")
        posts = fbdb.list_scheduled_posts(ref_id)
        assert posts[0]["status"] == "published"

        fbdb.delete_page(ref_id)
        assert fbdb.get_page(ref_id) is None


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("Tất cả test đã chạy.")
