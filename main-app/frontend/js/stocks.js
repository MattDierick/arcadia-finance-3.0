/** stocks.js – Arcadia Finance Stocks page */
document.addEventListener("DOMContentLoaded", async () => {

  // ── Auth guard ──────────────────────────────────────────────
  let currentUser = null;
  try { currentUser = await API.me(); } catch { window.location.href = "/"; return; }
  const initials = (currentUser.name[0] + currentUser.surname[0]).toUpperCase();
  document.querySelectorAll(".user-initials").forEach(el => el.textContent = initials);
  document.querySelectorAll(".user-fullname").forEach(el =>
    el.textContent = currentUser.name + " " + currentUser.surname);
  document.getElementById("logout-btn")?.addEventListener("click", async () => {
    await API.logout(); sessionStorage.removeItem("arcadia_user"); window.location.href = "/";
  });

  // ── Formatters ──────────────────────────────────────────────
  const fmtCcy = (n, c) => new Intl.NumberFormat("en-US", {
    style: "currency", currency: c || "USD", minimumFractionDigits: 2 }).format(n);
  const fmtNum   = (n, d) => Number(n).toFixed(d == null ? 2 : d);
  const fmtLarge = n => {
    if (!n) return "-";
    if (n >= 1e12) return "$" + (n/1e12).toFixed(2) + "T";
    if (n >= 1e9)  return "$" + (n/1e9).toFixed(2)  + "B";
    if (n >= 1e6)  return "$" + (n/1e6).toFixed(2)  + "M";
    return "$" + n.toLocaleString();
  };

  // ── State ────────────────────────────────────────────────────
  let activeQuote    = null;
  let priceChartInst = null;
  let activePeriod   = "1mo";

  // ── Quick-pick chips ─────────────────────────────────────────
  const POPULAR = ["FFIV","AAPL","MSFT","GOOGL","AMZN","NVDA","TSLA","META","NFLX","AMD","INTC"];
  const chipsEl = document.getElementById("ticker-chips");
  if (chipsEl) {
    chipsEl.innerHTML = POPULAR.map(t =>
      '<button class="ticker-chip" data-ticker="' + t + '">' + t + '</button>').join("");
    chipsEl.querySelectorAll(".ticker-chip").forEach(btn =>
      btn.addEventListener("click", () => loadQuote(btn.dataset.ticker)));
  }

  // ── Search form ──────────────────────────────────────────────
  const searchInput = document.getElementById("ticker-input");
  const searchError = document.getElementById("search-error");
  document.getElementById("search-form")?.addEventListener("submit", async e => {
    e.preventDefault();
    const q = ((searchInput && searchInput.value) || "").trim().toUpperCase();
    if (q) loadQuote(q);
  });

  // ── Load quote + history ─────────────────────────────────────
  async function loadQuote(ticker) {
    if (searchError) { searchError.textContent = ""; searchError.classList.add("hidden"); }
    document.getElementById("quote-loading")?.classList.remove("hidden");
    try {
      const [quote, histResp] = await Promise.all([
        API.stockQuote(ticker),
        API.stockHistory(ticker, activePeriod, "1d"),
      ]);
      activeQuote = quote;
      renderQuoteCard(quote);
      renderPriceChart(histResp.data || [], quote.currency);
      const bt = document.getElementById("buy-ticker"); if (bt) bt.value = ticker;
      updateBuyTotal();
      document.getElementById("quote-loading")?.classList.add("hidden");
      document.getElementById("quote-section")?.classList.remove("hidden");
      document.querySelectorAll(".ticker-chip").forEach(b =>
        b.classList.toggle("active", b.dataset.ticker === ticker));
      if (searchInput) searchInput.value = ticker;
    } catch (err) {
      document.getElementById("quote-loading")?.classList.add("hidden");
      const msg = (err && err.data && err.data.error) || ('Ticker "' + ticker + '" not found.');
      if (searchError) { searchError.textContent = "\u26a0\ufe0f " + msg; searchError.classList.remove("hidden"); }
      document.getElementById("quote-section")?.classList.add("hidden");
    }
  }

  // ── Period selector ──────────────────────────────────────────
  document.querySelectorAll(".period-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      activePeriod = btn.dataset.period;
      document.querySelectorAll(".period-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      if (activeQuote) {
        API.stockHistory(activeQuote.ticker, activePeriod, "1d")
          .then(h => renderPriceChart(h.data || [], activeQuote.currency))
          .catch(() => {});
      }
    });
  });

  // ── Quote card ───────────────────────────────────────────────
  function renderQuoteCard(q) {
    const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v != null ? v : "-"; };
    set("q-ticker",    q.ticker);
    set("q-name",      q.name);
    set("q-price",     fmtCcy(q.price, q.currency));
    set("q-exchange",  q.exchange || "-");
    set("q-volume",    q.volume ? q.volume.toLocaleString() : "-");
    set("q-market-cap",fmtLarge(q.market_cap));
    set("q-pe",        q.pe_ratio ? fmtNum(q.pe_ratio) : "-");
    set("q-52high",    q.fifty_two_week_high ? fmtCcy(q.fifty_two_week_high, q.currency) : "-");
    set("q-52low",     q.fifty_two_week_low  ? fmtCcy(q.fifty_two_week_low,  q.currency) : "-");
    set("q-sector",    q.sector   || "-");
    set("q-industry",  q.industry || "-");
    const changeEl = document.getElementById("q-change");
    if (changeEl) {
      const sign = q.change >= 0 ? "+" : "";
      changeEl.textContent = sign + fmtCcy(q.change, q.currency) + " (" + sign + fmtNum(q.change_pct) + "%)";
      changeEl.className = q.change >= 0 ? "text-success" : "text-error";
    }
  }

  // ── Price chart ──────────────────────────────────────────────
  function renderPriceChart(records, currency) {
    currency = currency || "USD";
    const canvas = document.getElementById("price-chart");
    if (!canvas) return;
    if (priceChartInst) { priceChartInst.destroy(); priceChartInst = null; }
    if (!records.length) return;
    const closes = records.map(r => r.close);
    const up    = closes[closes.length-1] >= closes[0];
    const color = up ? "rgba(16,185,129,1)"    : "rgba(239,68,68,1)";
    const fill  = up ? "rgba(16,185,129,0.08)" : "rgba(239,68,68,0.08)";
    priceChartInst = new Chart(canvas, {
      type: "line",
      data: { labels: records.map(r => r.date), datasets: [{
        label: "Close", data: closes, borderColor: color, backgroundColor: fill,
        borderWidth: 2, pointRadius: records.length > 60 ? 0 : 3, fill: true, tension: 0.3,
      }]},
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false },
          tooltip: { callbacks: { label: c => fmtCcy(c.parsed.y, currency) }}},
        scales: {
          x: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#94A3B8", maxTicksLimit: 8 }},
          y: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#94A3B8", callback: v => fmtCcy(v, currency) }},
        },
      },
    });
  }


  // ── Buy form ─────────────────────────────────────────────────
  function updateBuyTotal() {
    const qty = parseFloat((document.getElementById("buy-qty") || {}).value || 0);
    const el  = document.getElementById("buy-total");
    if (el) el.textContent = (qty > 0 && activeQuote && activeQuote.price > 0)
      ? fmtCcy(qty * activeQuote.price, activeQuote.currency) : "-";
  }
  document.getElementById("buy-qty")?.addEventListener("input", updateBuyTotal);

  async function populateAccountSelect() {
    const sel = document.getElementById("buy-account"); if (!sel) return;
    try {
      const accounts = await API.accounts();
      sel.innerHTML = accounts.map(a =>
        '<option value="' + a.account_number + '">' +
        a.type.charAt(0).toUpperCase() + a.type.slice(1) +
        ' \u2014 ' + a.account_number + ' (' + fmtCcy(a.balance, a.currency) + ')</option>'
      ).join("");
    } catch { sel.innerHTML = "<option>Could not load accounts</option>"; }
  }

  const buyForm   = document.getElementById("buy-form");
  const buyResult = document.getElementById("buy-result");
  buyForm?.addEventListener("submit", async e => {
    e.preventDefault();
    if (buyResult) { buyResult.textContent = ""; buyResult.className = "mt-md"; }
    const ticker       = ((document.getElementById("buy-ticker") || {}).value || "").trim().toUpperCase();
    const quantity     = parseFloat(((document.getElementById("buy-qty") || {}).value) || 0);
    const from_account = ((document.getElementById("buy-account") || {}).value) || "";
    if (!ticker || !quantity || !from_account) {
      if (buyResult) { buyResult.textContent = "\u26a0\ufe0f Please fill in all fields."; buyResult.className = "mt-md text-error"; }
      return;
    }
    const btn = buyForm.querySelector("button[type=submit]");
    btn.disabled = true; btn.textContent = "Processing\u2026";
    try {
      const res = await API.stockBuy({ ticker, quantity, from_account });
      if (buyResult) {
        buyResult.textContent = "\u2705 Purchased " + res.quantity + " \xd7 " + res.ticker +
          " for " + fmtCcy(res.total, res.currency) + " (Order #" + res.order_id + ")";
        buyResult.className = "mt-md text-success";
      }
      buyForm.reset(); activeQuote = null;
      document.getElementById("quote-section")?.classList.add("hidden");
      await Promise.all([loadPortfolio(), loadOrders(), populateAccountSelect()]);
    } catch (err) {
      if (buyResult) {
        buyResult.textContent = "\u274c " + ((err && err.data && err.data.error) || "Purchase failed.");
        buyResult.className = "mt-md text-error";
      }
    } finally { btn.disabled = false; btn.textContent = "Buy Shares"; }
  });

  // ── Portfolio table ──────────────────────────────────────────
  async function loadPortfolio() {
    const tbody = document.getElementById("portfolio-tbody"); if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:20px"><div class="spinner" style="margin:auto"></div></td></tr>';
    try {
      const holdings = await API.stockPortfolio();
      if (!holdings.length) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:24px">No holdings yet. Buy your first stock above!</td></tr>';
        return;
      }
      tbody.innerHTML = holdings.map(h =>
        '<tr><td><strong>' + h.ticker + '</strong></td>' +
        '<td>' + fmtNum(h.quantity, 6).replace(/\.?0+$/, "") + '</td>' +
        '<td>' + fmtCcy(h.avg_price, h.currency) + '</td>' +
        '<td>' + h.currency + '</td>' +
        '<td style="color:var(--text-muted);font-size:0.8rem">' +
        (h.updated_at ? new Date(h.updated_at).toLocaleDateString("fr-FR") : "-") + '</td></tr>'
      ).join("");
    } catch {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:24px">Could not load portfolio.</td></tr>';
    }
  }

  // ── Orders table ─────────────────────────────────────────────
  async function loadOrders() {
    const tbody = document.getElementById("orders-tbody"); if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:20px"><div class="spinner" style="margin:auto"></div></td></tr>';
    try {
      const orders = await API.stockOrders();
      if (!orders.length) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text-muted);padding:24px">No orders yet.</td></tr>';
        return;
      }
      tbody.innerHTML = orders.map(o =>
        '<tr>' +
        '<td style="font-family:monospace;font-size:0.8rem">#' + o.id + '</td>' +
        '<td><strong>' + o.ticker + '</strong></td>' +
        '<td>' + fmtNum(o.quantity, 6).replace(/\.?0+$/, "") + '</td>' +
        '<td>' + fmtCcy(o.price, o.currency) + '</td>' +
        '<td class="text-error" style="font-weight:700">-' + fmtCcy(o.total, o.currency) + '</td>' +
        '<td style="font-family:monospace;font-size:0.75rem">' + o.from_account + '</td>' +
        '<td style="color:var(--text-muted);font-size:0.8rem">' +
        (o.created_at ? new Date(o.created_at).toLocaleDateString("fr-FR") : "-") + '</td></tr>'
      ).join("");
    } catch {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text-muted);padding:24px">Could not load orders.</td></tr>';
    }
  }

  // ── Initial load ─────────────────────────────────────────────
  await Promise.all([populateAccountSelect(), loadPortfolio(), loadOrders()]);
  loadQuote("FFIV");
});

