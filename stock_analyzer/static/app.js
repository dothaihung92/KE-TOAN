// Tự động làm mới tin tức & bảng theo dõi mỗi 60 giây, không cần tải lại trang.

const POLL_INTERVAL_MS = 60_000;

function fmt1(n) {
  return typeof n === "number" ? n.toFixed(1) : "-";
}

function labelClass(label) {
  return "badge-" + (label || "").toLowerCase().replace(/ \/ /g, "-").replace(/ /g, "-");
}

function renderNewsList(el, items) {
  if (!el) return;
  if (!items || items.length === 0) {
    el.innerHTML = '<li class="muted">Chưa có tin tức. Bấm "Làm mới ngay" ở trên để tải.</li>';
    return;
  }
  el.innerHTML = items
    .map(
      (item) => `<li>
        <a href="${item.link || "#"}" target="_blank" rel="noopener">${escapeHtml(item.title)}</a>
        <span class="muted small">${escapeHtml(item.published || "")}</span>
      </li>`
    )
    .join("");
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str || "";
  return div.innerHTML;
}

function renderWatchlistRows(cacheBySymbol) {
  const tbody = document.querySelector("#watchlist-table tbody");
  if (!tbody) return;
  tbody.querySelectorAll("tr[data-symbol]").forEach((tr) => {
    const symbol = tr.getAttribute("data-symbol");
    const entry = cacheBySymbol[symbol];
    if (!entry) return;

    const quote = entry.quote;
    const rec = entry.recommendation;

    const priceCell = tr.querySelector(".cell-price");
    const changeCell = tr.querySelector(".cell-change");
    const rsiCell = tr.querySelector(".cell-rsi");
    const techCell = tr.querySelector(".cell-tech");
    const newsCell = tr.querySelector(".cell-news");
    const labelCell = tr.querySelector(".cell-label");
    const updatedCell = tr.querySelector(".cell-updated");

    if (quote && priceCell) priceCell.textContent = fmt1(quote.close);
    if (quote && changeCell) {
      changeCell.textContent = fmt1(quote.change_pct) + "%";
      changeCell.className = "cell-change " + (quote.change_pct >= 0 ? "pos" : "neg");
    }
    if (rec) {
      const rsi = rec.technical_details && rec.technical_details.rsi14;
      if (rsiCell) rsiCell.textContent = typeof rsi === "number" ? Math.round(rsi) : "-";
      if (techCell) techCell.textContent = rec.technical_score;
      if (newsCell) newsCell.textContent = rec.news_score;
      if (labelCell) {
        labelCell.innerHTML = `<span class="badge ${labelClass(rec.label)}">${escapeHtml(rec.label)}</span>`;
      }
    }
    if (updatedCell) updatedCell.textContent = entry.updated_at || "-";
  });
}

async function pollNews() {
  try {
    const resp = await fetch("/api/news");
    if (!resp.ok) return;
    const items = await resp.json();
    renderNewsList(document.getElementById("market-news-preview"), items.slice(0, 8));
    renderNewsList(document.getElementById("market-news-full"), items);
  } catch (e) {
    // Bỏ qua lỗi mạng tạm thời, thử lại ở lần polling sau
  }
}

async function pollWatchlist() {
  try {
    const resp = await fetch("/api/watchlist");
    if (!resp.ok) return;
    const list = await resp.json();
    const bySymbol = {};
    list.forEach((entry) => (bySymbol[entry.symbol] = entry));
    renderWatchlistRows(bySymbol);
  } catch (e) {
    // Bỏ qua lỗi mạng tạm thời
  }
}

function startPolling() {
  setInterval(() => {
    pollNews();
    pollWatchlist();
  }, POLL_INTERVAL_MS);
}

document.addEventListener("DOMContentLoaded", startPolling);
