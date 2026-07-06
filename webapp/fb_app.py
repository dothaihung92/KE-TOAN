"""
Blueprint quản lý Fanpage Facebook: đăng bài tự động bằng AI + quảng cáo sản phẩm.

Chỉ dùng Graph API / Marketing API chính thức của Meta. Người dùng tự tạo
Facebook App + lấy Page Access Token (và Ad Account ID nếu muốn chạy quảng
cáo) rồi nhập vào đây — fbai không tự động hoá bất kỳ hành vi nào ngoài
API được Meta cấp phép (không auto-like/comment/kết bạn hàng loạt).
"""

from __future__ import annotations

from datetime import datetime

from flask import (
    Blueprint, abort, flash, redirect, render_template, request, url_for,
)

from fbai import db as fbdb
from fbai.client import FacebookApiError, FacebookClient
from fbai.content import generate_post_content

bp = Blueprint("fb", __name__, url_prefix="/fb")


# ------------------------------------------------------------------ #
# Fanpage
# ------------------------------------------------------------------ #
@bp.route("/")
def pages():
    fbdb.init_db()
    return render_template("fb_pages.html", pages=fbdb.list_pages())


@bp.route("/page/add", methods=["GET", "POST"])
def page_add():
    fbdb.init_db()
    if request.method == "POST":
        ten = request.form.get("ten", "").strip()
        page_id = request.form.get("page_id", "").strip()
        access_token = request.form.get("access_token", "").strip()
        ad_account_id = request.form.get("ad_account_id", "").strip()
        if not (ten and page_id and access_token):
            flash("Vui lòng nhập đủ Tên, Page ID và Access Token.", "error")
        else:
            fbdb.add_page(ten, page_id, access_token, ad_account_id)
            flash(f"Đã kết nối Fanpage: {ten}", "ok")
            return redirect(url_for("fb.pages"))
    return render_template("fb_page_form.html", page=None, action="add")


@bp.route("/page/<int:ref_id>/edit", methods=["GET", "POST"])
def page_edit(ref_id: int):
    page = fbdb.get_page(ref_id)
    if not page:
        abort(404)
    if request.method == "POST":
        ten = request.form.get("ten", "").strip()
        page_id = request.form.get("page_id", "").strip()
        access_token = request.form.get("access_token", "")  # rỗng = giữ nguyên
        ad_account_id = request.form.get("ad_account_id", "").strip()
        fbdb.update_page(ref_id, ten, page_id, access_token or None, ad_account_id)
        flash("Đã cập nhật Fanpage.", "ok")
        return redirect(url_for("fb.pages"))
    return render_template("fb_page_form.html", page=page, action="edit")


@bp.route("/page/<int:ref_id>/delete", methods=["POST"])
def page_delete(ref_id: int):
    fbdb.delete_page(ref_id)
    flash("Đã xoá Fanpage.", "ok")
    return redirect(url_for("fb.pages"))


@bp.route("/page/<int:ref_id>")
def page_dashboard(ref_id: int):
    page = fbdb.get_page(ref_id)
    if not page:
        abort(404)
    page_info = None
    try:
        client = FacebookClient(fbdb.get_page_token(ref_id))
        page_info = client.get_page_info(page["page_id"])
    except FacebookApiError as exc:
        flash(f"Không lấy được thông tin Fanpage: {exc}", "error")

    return render_template(
        "fb_dashboard.html",
        page=page,
        page_info=page_info,
        products=fbdb.list_products(ref_id),
        posts=fbdb.list_scheduled_posts(ref_id),
        campaigns=fbdb.list_campaigns(ref_id),
    )


# ------------------------------------------------------------------ #
# Sản phẩm
# ------------------------------------------------------------------ #
@bp.route("/page/<int:ref_id>/product/add", methods=["POST"])
def product_add(ref_id: int):
    if not fbdb.get_page(ref_id):
        abort(404)
    ten = request.form.get("ten", "").strip()
    mo_ta = request.form.get("mo_ta", "").strip()
    gia = request.form.get("gia", "").strip()
    link = request.form.get("link", "").strip()
    if not ten:
        flash("Vui lòng nhập tên sản phẩm.", "error")
    else:
        fbdb.add_product(ref_id, ten, mo_ta, gia, link)
        flash(f"Đã thêm sản phẩm: {ten}", "ok")
    return redirect(url_for("fb.page_dashboard", ref_id=ref_id))


@bp.route("/page/<int:ref_id>/product/<int:product_id>/delete", methods=["POST"])
def product_delete(ref_id: int, product_id: int):
    fbdb.delete_product(product_id)
    flash("Đã xoá sản phẩm.", "ok")
    return redirect(url_for("fb.page_dashboard", ref_id=ref_id))


# ------------------------------------------------------------------ #
# Đăng bài bằng AI (tạo nội dung + lên lịch)
# ------------------------------------------------------------------ #
@bp.route("/page/<int:ref_id>/post/generate", methods=["POST"])
def post_generate(ref_id: int):
    if not fbdb.get_page(ref_id):
        abort(404)
    product_id = request.form.get("product_id", type=int)
    product = fbdb.get_product(product_id) if product_id else None
    if product:
        content = generate_post_content(
            product["ten"], product["mo_ta"], product["gia"] or "Liên hệ",
        )
        link = product["link"]
    else:
        content = generate_post_content(
            request.form.get("ten", "Sản phẩm"),
            request.form.get("mo_ta", ""),
            request.form.get("gia", "Liên hệ"),
        )
        link = ""
    return render_template(
        "fb_post_preview.html", page_id=ref_id, content=content, link=link,
        product_id=product_id,
    )


@bp.route("/page/<int:ref_id>/post/schedule", methods=["POST"])
def post_schedule(ref_id: int):
    page = fbdb.get_page(ref_id)
    if not page:
        abort(404)
    noi_dung = request.form.get("noi_dung", "").strip()
    link = request.form.get("link", "").strip()
    image_url = request.form.get("image_url", "").strip()
    scheduled_at = request.form.get("scheduled_at", "").strip()  # yyyy-mm-ddThh:mm
    publish_now = request.form.get("publish_now") == "1"

    if not noi_dung:
        flash("Nội dung bài đăng không được trống.", "error")
        return redirect(url_for("fb.page_dashboard", ref_id=ref_id))

    if publish_now:
        try:
            client = FacebookClient(fbdb.get_page_token(ref_id))
            result = client.publish_post(page["page_id"], noi_dung,
                                         link=link or None, image_url=image_url or None)
            flash(f"Đã đăng bài lên Fanpage (id: {result.get('id', '?')}).", "ok")
        except FacebookApiError as exc:
            flash(f"Đăng bài thất bại: {exc}", "error")
        return redirect(url_for("fb.page_dashboard", ref_id=ref_id))

    if not scheduled_at:
        flash("Vui lòng chọn thời gian lên lịch hoặc chọn đăng ngay.", "error")
        return redirect(url_for("fb.page_dashboard", ref_id=ref_id))

    fbdb.add_scheduled_post(ref_id, noi_dung, scheduled_at, link, image_url)
    flash("Đã lên lịch bài đăng. Chạy `python -m fbai.scheduler` (hoặc cron) để tự đăng đúng giờ.", "ok")
    return redirect(url_for("fb.page_dashboard", ref_id=ref_id))


@bp.route("/page/<int:ref_id>/post/<int:post_id>/delete", methods=["POST"])
def post_delete(ref_id: int, post_id: int):
    fbdb.delete_scheduled_post(post_id)
    flash("Đã xoá bài đã lên lịch.", "ok")
    return redirect(url_for("fb.page_dashboard", ref_id=ref_id))


@bp.route("/page/<int:ref_id>/post/run_due", methods=["POST"])
def post_run_due(ref_id: int):
    from fbai.scheduler import run_due_posts
    n = run_due_posts(datetime.now())
    flash(f"Đã đăng {n} bài đến hạn.", "ok")
    return redirect(url_for("fb.page_dashboard", ref_id=ref_id))


# ------------------------------------------------------------------ #
# Quảng cáo sản phẩm
# ------------------------------------------------------------------ #
@bp.route("/page/<int:ref_id>/campaign/create", methods=["POST"])
def campaign_create(ref_id: int):
    page = fbdb.get_page(ref_id)
    if not page:
        abort(404)
    if not page["ad_account_id"]:
        flash("Fanpage này chưa cấu hình Ad Account ID.", "error")
        return redirect(url_for("fb.page_dashboard", ref_id=ref_id))

    ten = request.form.get("ten", "").strip()
    product_id = request.form.get("product_id", type=int)
    daily_budget_vnd = request.form.get("daily_budget", type=int) or 0
    product = fbdb.get_product(product_id) if product_id else None

    if not (ten and product and daily_budget_vnd > 0):
        flash("Vui lòng nhập tên chiến dịch, chọn sản phẩm và ngân sách/ngày hợp lệ.", "error")
        return redirect(url_for("fb.page_dashboard", ref_id=ref_id))

    # Facebook yêu cầu ngân sách theo đơn vị nhỏ nhất của tiền tệ tài khoản quảng cáo
    daily_budget_cents = daily_budget_vnd

    try:
        client = FacebookClient(fbdb.get_page_token(ref_id))
        campaign = client.create_campaign(
            page["ad_account_id"], ten,
            daily_budget_cents=daily_budget_cents, status="PAUSED",
        )
        fbdb.add_campaign(ref_id, ten, campaign["id"], daily_budget_cents, status="PAUSED")
        flash(
            f"Đã tạo chiến dịch '{ten}' ở trạng thái TẠM DỪNG (PAUSED) trên Facebook Ads Manager. "
            "Vào Ads Manager kiểm tra đối tượng/ngân sách rồi tự bật chạy — hệ thống không tự chi tiền.",
            "ok",
        )
    except FacebookApiError as exc:
        flash(f"Tạo chiến dịch thất bại: {exc}", "error")

    return redirect(url_for("fb.page_dashboard", ref_id=ref_id))
