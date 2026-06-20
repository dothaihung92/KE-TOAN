"""
Ứng dụng web tra cứu hoá đơn điện tử cho dịch vụ kế toán.

Tính năng:
    - Quản lý danh sách công ty (khách hàng): thêm/sửa/xoá, mật khẩu mã hoá.
    - Đăng nhập cổng HĐĐT ngay trên web (hiển thị captcha trực tiếp).
    - Tra cứu hoá đơn mua vào/bán ra theo khoảng thời gian.
    - Tải kết quả ra Excel / CSV.

Chạy:  python -m webapp.app   (hoặc python run_web.py)
"""

from __future__ import annotations

import io
import os
import secrets

from flask import (
    Flask, abort, flash, redirect, render_template, request,
    send_file, session, url_for,
)

from hddt.client import INVOICE_ENDPOINTS, HoaDonDienTuClient, HddtError
from hddt import exporter
from . import db

TYPE_LABELS = {
    "purchase": "Mua vào",
    "sold": "Bán ra",
    "sco-purchase": "Mua vào (máy tính tiền)",
    "sco-sold": "Bán ra (máy tính tiền)",
}


def create_app() -> Flask:
    app = Flask(__name__)
    # Khoá ký session: ưu tiên biến môi trường, nếu không thì sinh ngẫu nhiên
    app.secret_key = os.environ.get("HDDT_FLASK_SECRET") or secrets.token_hex(32)
    db.init_db()

    # ------------------------------------------------------------------ #
    # Danh sách & quản lý công ty
    # ------------------------------------------------------------------ #
    @app.route("/")
    def index():
        companies = db.list_companies()
        active = session.get("active", {})
        return render_template("index.html", companies=companies,
                               active_id=active.get("company_id"))

    @app.route("/company/add", methods=["GET", "POST"])
    def company_add():
        if request.method == "POST":
            ten = request.form.get("ten", "").strip()
            mst = request.form.get("mst", "").strip()
            password = request.form.get("password", "")
            ghi_chu = request.form.get("ghi_chu", "").strip()
            if not (ten and mst and password):
                flash("Vui lòng nhập đủ Tên công ty, MST và mật khẩu.", "error")
            else:
                db.add_company(ten, mst, password, ghi_chu)
                flash(f"Đã thêm công ty: {ten}", "ok")
                return redirect(url_for("index"))
        return render_template("company_form.html", company=None, action="add")

    @app.route("/company/<int:cid>/edit", methods=["GET", "POST"])
    def company_edit(cid: int):
        company = db.get_company(cid)
        if not company:
            abort(404)
        if request.method == "POST":
            ten = request.form.get("ten", "").strip()
            mst = request.form.get("mst", "").strip()
            password = request.form.get("password", "")  # rỗng = giữ nguyên
            ghi_chu = request.form.get("ghi_chu", "").strip()
            db.update_company(cid, ten, mst, password or None, ghi_chu)
            flash("Đã cập nhật thông tin công ty.", "ok")
            return redirect(url_for("index"))
        return render_template("company_form.html", company=company, action="edit")

    @app.route("/company/<int:cid>/delete", methods=["POST"])
    def company_delete(cid: int):
        db.delete_company(cid)
        flash("Đã xoá công ty.", "ok")
        return redirect(url_for("index"))

    # ------------------------------------------------------------------ #
    # Đăng nhập cổng HĐĐT (hiển thị captcha)
    # ------------------------------------------------------------------ #
    @app.route("/company/<int:cid>/login", methods=["GET", "POST"])
    def company_login(cid: int):
        company = db.get_company(cid)
        if not company:
            abort(404)
        client = HoaDonDienTuClient(timeout=30)

        if request.method == "POST":
            captcha_key = request.form.get("captcha_key", "")
            captcha_value = request.form.get("captcha_value", "").strip()
            try:
                password = db.get_company_password(cid)
                token = client.authenticate(
                    company["mst"], password, captcha_key, captcha_value
                )
                session["active"] = {"company_id": cid, "token": token,
                                     "ten": company["ten"], "mst": company["mst"]}
                flash(f"Đăng nhập thành công: {company['ten']}", "ok")
                return redirect(url_for("query", cid=cid))
            except HddtError as exc:
                flash(f"Đăng nhập thất bại: {exc}", "error")
                # rơi xuống dưới để lấy captcha mới

        # GET hoặc đăng nhập lỗi: lấy captcha mới
        try:
            captcha = client.get_captcha()
        except HddtError as exc:
            flash(f"Không lấy được captcha: {exc}", "error")
            return redirect(url_for("index"))
        return render_template("login.html", company=company,
                               captcha_svg=captcha["content"],
                               captcha_key=captcha["key"])

    # ------------------------------------------------------------------ #
    # Tra cứu hoá đơn
    # ------------------------------------------------------------------ #
    def _require_token(cid: int) -> str:
        active = session.get("active", {})
        if active.get("company_id") != cid or not active.get("token"):
            return ""
        return active["token"]

    @app.route("/company/<int:cid>", methods=["GET", "POST"])
    def query(cid: int):
        company = db.get_company(cid)
        if not company:
            abort(404)
        token = _require_token(cid)
        if not token:
            flash("Cần đăng nhập công ty này trước khi tra cứu.", "error")
            return redirect(url_for("company_login", cid=cid))

        results = None
        params = {
            "from_date": request.form.get("from_date", ""),
            "to_date": request.form.get("to_date", ""),
            "types": request.form.getlist("types") or ["purchase", "sold"],
        }
        if request.method == "POST":
            client = HoaDonDienTuClient(token=token, timeout=60)
            results = {}
            try:
                for t in params["types"]:
                    rows = client.query_invoices(
                        t, params["from_date"], params["to_date"], size=50
                    )
                    results[t] = rows
            except HddtError as exc:
                flash(f"Lỗi tra cứu: {exc}", "error")
                if "hết hạn" in str(exc) or "không hợp lệ" in str(exc):
                    session.pop("active", None)
                    return redirect(url_for("company_login", cid=cid))
                results = None

        return render_template("query.html", company=company, params=params,
                               results=results, type_labels=TYPE_LABELS,
                               all_types=list(INVOICE_ENDPOINTS),
                               label=exporter.COLUMN_LABELS)

    @app.route("/company/<int:cid>/export")
    def export(cid: int):
        company = db.get_company(cid)
        if not company:
            abort(404)
        token = _require_token(cid)
        if not token:
            flash("Phiên đăng nhập đã hết. Vui lòng đăng nhập lại.", "error")
            return redirect(url_for("company_login", cid=cid))

        from_date = request.args.get("from_date", "")
        to_date = request.args.get("to_date", "")
        types = request.args.getlist("types") or ["purchase", "sold"]
        fmt = request.args.get("format", "xlsx")

        client = HoaDonDienTuClient(token=token, timeout=120)
        sheets = {}
        try:
            for t in types:
                sheets[TYPE_LABELS.get(t, t)] = client.query_invoices(
                    t, from_date, to_date, size=50
                )
        except HddtError as exc:
            flash(f"Lỗi khi xuất: {exc}", "error")
            return redirect(url_for("query", cid=cid))

        buf = io.BytesIO()
        fname_base = f"hoadon_{company['mst']}_{from_date}_{to_date}".replace("/", "-")
        if fmt == "csv":
            merged = []
            for name, rows in sheets.items():
                for r in rows:
                    r = dict(r)
                    r["_loai"] = name
                    merged.append(r)
            tmp = io.StringIO()
            import csv as _csv
            from hddt.exporter import _ordered_fields, _stringify, COLUMN_LABELS
            if merged:
                fields = _ordered_fields(merged)
                w = _csv.DictWriter(tmp, fieldnames=fields, extrasaction="ignore")
                w.writerow({k: COLUMN_LABELS.get(k, k) for k in fields})
                for r in merged:
                    w.writerow({k: _stringify(r.get(k, "")) for k in fields})
            buf.write(tmp.getvalue().encode("utf-8-sig"))
            mimetype = "text/csv"
            fname = fname_base + ".csv"
        else:
            # Ghi Excel ra file tạm rồi nạp vào buffer
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tf:
                tmp_path = tf.name
            exporter.to_excel(sheets, tmp_path)
            with open(tmp_path, "rb") as f:
                buf.write(f.read())
            os.unlink(tmp_path)
            mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            fname = fname_base + ".xlsx"

        buf.seek(0)
        return send_file(buf, mimetype=mimetype, as_attachment=True,
                         download_name=fname)

    @app.route("/logout")
    def logout():
        session.pop("active", None)
        flash("Đã đăng xuất.", "ok")
        return redirect(url_for("index"))

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="127.0.0.1", port=port, debug=True)
