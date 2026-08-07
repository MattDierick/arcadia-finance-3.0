/**
 * api.js – Fetch helpers for Arcadia Finance
 * All calls go to /api/* on the same origin.
 *
 * Authentication strategy:
 *  - JWT token stored in localStorage under "arcadia_jwt".
 *  - Attached automatically as "Authorization: Bearer <token>" on every request.
 *  - Session cookie is also sent (credentials: "include") so browser-based auth
 *    works as a fallback during page navigation.
 */

const BASE = "";

/** Read the stored JWT token, if any. */
function _getJwt() {
  return localStorage.getItem("arcadia_jwt") || null;
}

/** Persist a JWT token after login. */
function _setJwt(token) {
  if (token) localStorage.setItem("arcadia_jwt", token);
}

/** Remove the JWT token on logout. */
function _clearJwt() {
  localStorage.removeItem("arcadia_jwt");
}

async function apiFetch(path, options = {}) {
  const token = _getJwt();
  const authHeader = token ? { "Authorization": `Bearer ${token}` } : {};
  const defaults = {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...authHeader,
      ...(options.headers || {}),
    },
  };
  const res = await fetch(BASE + path, {
    ...defaults,
    ...options,
    headers: { ...defaults.headers, ...(options.headers || {}) },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw { status: res.status, data };
  return data;
}

const API = {
  // ── Public ──────────────────────────────────────────────────────────────────
  /** Browser login: sets session cookie AND stores the JWT in localStorage. */
  login: (username, password) =>
    apiFetch("/api/login", { method: "POST", body: JSON.stringify({ username, password }) })
      .then(data => { _setJwt(data.access_token); return data; }),

  /**
   * API-only token endpoint (Postman / curl).
   * Returns { access_token, token_type, expires_in, user }.
   */
  token: (username, password) =>
    apiFetch("/api/token", { method: "POST", body: JSON.stringify({ username, password }) })
      .then(data => { _setJwt(data.access_token); return data; }),

  /** Sign out: clears the server session and removes the local JWT. */
  logout: () =>
    apiFetch("/api/logout", { method: "POST" })
      .finally(() => _clearJwt()),

  // ── Protected (require valid JWT or active session) ──────────────────────────
  me:         ()           => apiFetch("/api/me"),
  accounts:   (userId)     => apiFetch(`/api/accounts${userId ? "?user_id=" + userId : ""}`),
  transfer:   (body)       => apiFetch("/api/transfer",  { method: "POST", body: JSON.stringify(body) }),
  transfers:  (account)    => apiFetch(`/api/transfers?account=${encodeURIComponent(account)}`),
  getConfig:  ()           => apiFetch("/api/config"),
  saveConfig: (body)       => apiFetch("/api/config",    { method: "POST", body: JSON.stringify(body) }),
  chat:       (messages)   => apiFetch("/api/chat",      { method: "POST", body: JSON.stringify({ messages }) }),

  // ── Stocks ────────────────────────────────────────────────────────────────
  /** Get a live quote for a ticker symbol, e.g. "AAPL" */
  stockQuote:     (ticker)          => apiFetch(`/api/stocks/quote?ticker=${encodeURIComponent(ticker)}`),
  /** Get OHLCV history. period: 1d|5d|1mo|3mo|6mo|1y|2y|5y|ytd|max. interval: 1d|1wk|1mo */
  stockHistory:   (ticker, period = "1mo", interval = "1d") =>
    apiFetch(`/api/stocks/history?ticker=${encodeURIComponent(ticker)}&period=${period}&interval=${interval}`),
  /** Validate / search a ticker symbol */
  stockSearch:    (q)               => apiFetch(`/api/stocks/search?q=${encodeURIComponent(q)}`),
  /** Get current user's stock holdings */
  stockPortfolio: ()                => apiFetch("/api/stocks/portfolio"),
  /** Get current user's stock order history */
  stockOrders:    ()                => apiFetch("/api/stocks/orders"),
  /** Buy shares: { ticker, quantity, from_account } */
  stockBuy:       (body)            => apiFetch("/api/stocks/buy", { method: "POST", body: JSON.stringify(body) }),
};

window.API = API;
// Expose JWT helpers for debugging / Postman-like usage from the console
window._arcadiaJwt = { get: _getJwt, set: _setJwt, clear: _clearJwt };
