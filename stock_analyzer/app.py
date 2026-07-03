"""
Ứng dụng web Flask: phân tích chứng khoán Việt Nam, gợi ý mua/bán, tin tức
liên tục, và theo dõi danh mục (nhập thủ công từ sao kê VCBS).
"""

from __future__ import annotations

import logging
import os
import threading

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for

from . import db
from .data_sources import market
from .portfolio.importer import PortfolioImportError, parse_portfolio_file
from .scheduler import refresh_all_watchlist, refresh_market_news, refresh_symbol, start_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = Flask(__name__)
app.secret_key = os.environ.get("STOCK_FLASK_SECRET", "doi-chuoi-bi-mat-nay-khi-trien-khai-that")


with app.app_context():
    db.init_db()


def _run_in_background(fn, *args) -> None:
    threading.Thread(target=fn, args=args, daemon=True).start()


@app.route("/")
def dashboard():
    cache = {c["symbol"]: c for c in db.list_recommendation_cache()}
    symbols = db.list_watchlist_symbols()
    rows = []
    for symbol in symbols:
        entry = cache.get(symbol)
        rows.append({
            "symbol": symbol,
            "quote": entry["quote"] if entry else None,
            "recommendation": entry["recommendation"] if entry else None,
            "updated_at": entry["updated_at"] if entry else None,
            "error": entry["error"] if entry else None,
        })

    # Sắp xếp: điểm khuyến nghị cao (nên mua) lên trước
    rows.sort(
        key=lambda r: (r["recommendation"] or {}).get("combined_score", -999),
        reverse=True,
    )

    market_news = db.list_market_news(limit=8)
    return render_template("dashboard.html", rows=rows, market_news=market_news)


@app.route("/stock/<symbol>")
def stock_detail(symbol: str):
    symbol = symbol.strip().upper()
    entry = db.get_recommendation_cache(symbol)
    from .data_sources.news import get_company_news

    company_news = get_company_news(symbol, limit=15)
    return render_template("stock_detail.html", symbol=symbol, entry=entry, news=company_news)


@app.route("/stock/<symbol>/refresh", methods=["POST"])
def stock_refresh(symbol: str):
    symbol = symbol.strip().upper()
    refresh_symbol(symbol)
    flash(f"Đã làm mới dữ liệu {symbol}", "success")
    return redirect(url_for("stock_detail", symbol=symbol))


@app.route("/watchlist/add", methods=["POST"])
def watchlist_add():
    symbol = (request.form.get("symbol") or "").strip().upper()
    if symbol:
        db.add_watchlist_symbol(symbol)
        _run_in_background(refresh_symbol, symbol)
        flash(f"Đã thêm {symbol} vào danh sách theo dõi, đang lấy dữ liệu...", "success")
    return redirect(url_for("dashboard"))


@app.route("/watchlist/remove/<symbol>", methods=["POST"])
def watchlist_remove(symbol: str):
    db.remove_watchlist_symbol(symbol)
    flash(f"Đã bỏ theo dõi {symbol}", "success")
    return redirect(url_for("dashboard"))


@app.route("/refresh", methods=["POST"])
def refresh_now():
    _run_in_background(refresh_all_watchlist)
    _run_in_background(refresh_market_news)
    flash("Đang làm mới dữ liệu giá và tin tức, có thể mất khoảng một phút...", "success")
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/news")
def news_page():
    market_news = db.list_market_news(limit=50)
    return render_template("news.html", market_news=market_news)


@app.route("/search")
def search():
    keyword = request.args.get("q", "").strip()
    results = market.search_symbols(keyword) if keyword else None
    rows = results.to_dict("records") if results is not None else []
    return render_template("search.html", keyword=keyword, rows=rows)


# ------------------------------------------------------------------- portfolio

@app.route("/portfolio")
def portfolio_page():
    holdings = db.list_holdings()
    cache = {c["symbol"]: c for c in db.list_recommendation_cache()}

    enriched = []
    total_cost = 0.0
    total_value = 0.0
    for h in holdings:
        entry = cache.get(h["symbol"])
        quote = entry["quote"] if entry else None
        current_price = quote["close"] if quote else None
        cost_value = h["quantity"] * h["avg_cost"]
        market_value = h["quantity"] * current_price if current_price is not None else None
        pnl = (market_value - cost_value) if market_value is not None else None
        pnl_pct = (pnl / cost_value * 100) if pnl is not None and cost_value else None

        total_cost += cost_value
        if market_value is not None:
            total_value += market_value

        enriched.append({
            **h,
            "current_price": current_price,
            "cost_value": cost_value,
            "market_value": market_value,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "recommendation": entry["recommendation"] if entry else None,
        })

    summary = {
        "total_cost": total_cost,
        "total_value": total_value if total_value else None,
        "total_pnl": (total_value - total_cost) if total_value else None,
    }
    return render_template("portfolio.html", holdings=enriched, summary=summary)


@app.route("/portfolio/upload", methods=["POST"])
def portfolio_upload():
    file = request.files.get("file")
    if not file or not file.filename:
        flash("Vui lòng chọn file sao kê để tải lên", "error")
        return redirect(url_for("portfolio_page"))

    try:
        content = file.read()
        holdings = parse_portfolio_file(content, file.filename)
    except PortfolioImportError as exc:
        flash(str(exc), "error")
        return redirect(url_for("portfolio_page"))

    db.replace_holdings(
        [{"symbol": h.symbol, "quantity": h.quantity, "avg_cost": h.avg_cost} for h in holdings],
        source_file=file.filename,
    )
    # Đảm bảo có dữ liệu khuyến nghị cho các mã vừa nhập, kể cả khi chưa nằm
    # trong watchlist theo dõi mặc định.
    for h in holdings:
        db.add_watchlist_symbol(h.symbol)
        _run_in_background(refresh_symbol, h.symbol)

    flash(f"Đã nhập {len(holdings)} mã từ file {file.filename}", "success")
    return redirect(url_for("portfolio_page"))


@app.route("/portfolio/clear", methods=["POST"])
def portfolio_clear():
    db.clear_holdings()
    flash("Đã xoá danh mục", "success")
    return redirect(url_for("portfolio_page"))


# ------------------------------------------------------------------------ API

@app.route("/api/watchlist")
def api_watchlist():
    return jsonify(db.list_recommendation_cache())


@app.route("/api/news")
def api_news():
    return jsonify(db.list_market_news(limit=30))


def create_app() -> Flask:
    start_scheduler()
    return app
