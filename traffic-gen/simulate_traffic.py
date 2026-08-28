#!/usr/bin/env python3
"""
simulate_traffic.py – Arcadia Finance traffic generator
========================================================
Simulates realistic user sessions across all API endpoints to populate
WAF / Perf Mgmt / analytics statistics.

Usage:
    python3 simulate_traffic.py [--url http://localhost] [--loops 10] [--delay 1.5]

Requirements: Python 3.7+, stdlib only (no pip install needed).

Each "session" picks a random user, authenticates, then executes a realistic
sequence of API calls that mirrors what the browser SPA does:
  1.  POST /api/login
  2.  GET  /api/me
  3.  GET  /api/accounts
  4.  GET  /api/transfers?account=<checking>
  5.  GET  /api/users          (list all users)
  6.  GET  /api/users/<id>     (view another user – BOLA surface)
  7.  GET  /api/config
  8.  GET  /api/stocks/search?q=<ticker>
  9.  GET  /api/stocks/quote?ticker=<ticker>
  10. GET  /api/stocks/history?ticker=<ticker>&period=1mo
  11. GET  /api/stocks/portfolio
  12. GET  /api/stocks/orders
  13. POST /api/stocks/buy     (small qty, best-effort)
  14. POST /api/transfer       (small amount, best-effort)
  15. POST /api/logout
"""

import argparse
import json
import random
import time
import threading
import urllib.error
import urllib.request
from datetime import datetime

# ── Colours ───────────────────────────────────────────────────────────────────
RESET  = "\033[0m";  GREEN = "\033[32m";  YELLOW = "\033[33m"
RED    = "\033[31m"; CYAN  = "\033[36m";  BOLD   = "\033[1m";  DIM = "\033[2m"

def _ts():
    return datetime.now().strftime("%H:%M:%S")

def log_warn(msg):    print(f"  {YELLOW}⚠{RESET}  {msg}")
def log_err(msg):     print(f"  {RED}✖{RESET}  {msg}")
def log_section(msg): print(f"\n{BOLD}{CYAN}[{_ts()}] {msg}{RESET}")

# ── Seed data matching db/init.sql ────────────────────────────────────────────
USERS = [
    {"username": "alice",  "password": "alice123"},
    {"username": "thomas", "password": "thomas123"},
    {"username": "sophie", "password": "sophie123"},
    {"username": "lucas",  "password": "lucas123"},
]

# Account numbers per user (matching init.sql seed)
ACCOUNTS = {
    "alice":  ["FR7601234001001", "FR7601234001002", "FR7601234001003"],
    "thomas": ["FR7601234002001", "FR7601234002002"],
    "sophie": ["FR7601234003001", "FR7601234003002", "FR7601234003003"],
    "lucas":  ["FR7601234004001", "FR7601234004002"],
}

TICKERS = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "FFIV", "TSLA", "META", "JPM", "V"]

TRANSFER_NOTES = [
    "Rent payment", "Grocery reimbursement", "Coffee ☕",
    "Team lunch", "Birthday gift 🎂", "Utility bill",
    "Subscription", "Trip expenses", "Invoice #2026",
]

# ── HTTP helpers (stdlib only) ────────────────────────────────────────────────

def _http(method, url, body=None, headers=None):
    """Returns (status_code, dict). Never raises on HTTP errors."""
    headers = headers or {}
    headers["x-traffic-gen"] = "allowed"
    data = json.dumps(body).encode() if body is not None else None
    if data:
        headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode()
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:    body_json = json.loads(raw)
        except Exception: body_json = {"raw": raw}
        return e.code, body_json
    except Exception as exc:
        return 0, {"error": str(exc)}

def _get(base, path, token):
    return _http("GET", base + path, headers={"Authorization": f"Bearer {token}"})

def _post(base, path, body, token=None):
    hdrs = {"Authorization": f"Bearer {token}"} if token else {}
    return _http("POST", base + path, body=body, headers=hdrs)

# ── Step logger ───────────────────────────────────────────────────────────────

def step(label, status, data, expected=200):
    ok = (status == expected)
    m  = f"{GREEN}✔{RESET}" if ok else f"{RED}✖{RESET}"
    detail = f"  → {DIM}{data}{RESET}" if not ok else ""
    print(f"    {m}  [{status}] {label}{detail}")
    return ok

# ── Session simulation ────────────────────────────────────────────────────────

def simulate_session(base_url, user, session_id, delay):
    """Run one complete user session. Returns count of successful API calls."""
    username = user["username"]
    accounts = list(ACCOUNTS[username])
    ticker   = random.choice(TICKERS)
    successes = 0

    log_section(f"Session #{session_id:03d} — {BOLD}{username}{RESET}")

    # 1. Login
    status, data = _post(base_url, "/api/login",
                         {"username": username, "password": user["password"]})
    ok = step("POST /api/login", status, data)
    if not ok:
        log_err(f"Login failed for {username} – skipping session")
        return 0
    token = data.get("access_token", "")
    successes += 1
    time.sleep(delay * random.uniform(0.5, 1.5))

    # 2. /me
    status, data = _get(base_url, "/api/me", token)
    if step("GET  /api/me", status, data): successes += 1
    time.sleep(delay * random.uniform(0.3, 1.0))

    # 3. Accounts (refresh list from live response)
    status, data = _get(base_url, "/api/accounts", token)
    if step("GET  /api/accounts", status, data):
        successes += 1
        if isinstance(data, list) and data:
            accounts = [a["account_number"] for a in data]
    time.sleep(delay * random.uniform(0.3, 1.0))

    # 4. Transfer history for primary account
    checking = accounts[0]
    status, data = _get(base_url, f"/api/transfers?account={checking}", token)
    if step(f"GET  /api/transfers?account={checking}", status, data): successes += 1
    time.sleep(delay * random.uniform(0.3, 1.0))

    # 5. List all users
    status, data = _get(base_url, "/api/users", token)
    if step("GET  /api/users", status, data): successes += 1
    time.sleep(delay * random.uniform(0.2, 0.8))

    # 6. Fetch another user's profile (BOLA surface)
    user_idx  = USERS.index(user) + 1          # 1-based id
    other_id  = random.choice([i for i in range(1, 5) if i != user_idx])
    status, data = _get(base_url, f"/api/users/{other_id}", token)
    if step(f"GET  /api/users/{other_id} (BOLA surface)", status, data): successes += 1
    time.sleep(delay * random.uniform(0.2, 0.8))

    # 7. App config
    status, data = _get(base_url, "/api/config", token)
    if step("GET  /api/config", status, data): successes += 1
    time.sleep(delay * random.uniform(0.2, 0.6))

    # 8. Stock search
    status, data = _get(base_url, f"/api/stocks/search?q={ticker}", token)
    if step(f"GET  /api/stocks/search?q={ticker}", status, data): successes += 1
    time.sleep(delay * random.uniform(0.5, 1.5))

    # 9. Stock quote
    status, data = _get(base_url, f"/api/stocks/quote?ticker={ticker}", token)
    if step(f"GET  /api/stocks/quote?ticker={ticker}", status, data): successes += 1
    time.sleep(delay * random.uniform(0.5, 1.5))

    # 10. Stock history
    period   = random.choice(["1mo", "3mo", "6mo", "1y"])
    interval = random.choice(["1d", "1wk"])
    status, data = _get(base_url,
        f"/api/stocks/history?ticker={ticker}&period={period}&interval={interval}", token)
    if step(f"GET  /api/stocks/history?ticker={ticker}&period={period}", status, data):
        successes += 1
    time.sleep(delay * random.uniform(0.5, 1.5))

    # 11. Portfolio
    status, data = _get(base_url, "/api/stocks/portfolio", token)
    if step("GET  /api/stocks/portfolio", status, data): successes += 1
    time.sleep(delay * random.uniform(0.3, 0.8))

    # 12. Orders
    status, data = _get(base_url, "/api/stocks/orders", token)
    if step("GET  /api/stocks/orders", status, data): successes += 1
    time.sleep(delay * random.uniform(0.3, 0.8))

    # 13. Buy stock – tiny fractional quantity to stay within balance
    inv_account = next((a for a in accounts if a.endswith("003")), accounts[0])
    buy_qty = round(random.uniform(0.01, 0.1), 2)
    status, data = _post(base_url, "/api/stocks/buy",
                         {"ticker": ticker, "quantity": buy_qty,
                          "from_account": inv_account}, token=token)
    if status == 200:
        if step(f"POST /api/stocks/buy ({buy_qty}× {ticker})", status, data): successes += 1
    else:
        log_warn(f"POST /api/stocks/buy [{status}] – {data.get('error', data)}")
    time.sleep(delay * random.uniform(0.5, 1.5))

    # 14. Transfer between own accounts
    if len(accounts) >= 2:
        from_acc, to_acc = accounts[0], accounts[1]
        amount = round(random.uniform(1.0, 50.0), 2)
        note   = random.choice(TRANSFER_NOTES)
        status, data = _post(base_url, "/api/transfer",
                             {"from_account": from_acc, "to_account": to_acc,
                              "amount": amount, "note": note}, token=token)
        if status == 200:
            if step(f"POST /api/transfer (€{amount} {from_acc}→{to_acc})", status, data):
                successes += 1
        else:
            log_warn(f"POST /api/transfer [{status}] – {data.get('error', data)}")
        time.sleep(delay * random.uniform(0.5, 1.5))

    # 15. Logout
    status, data = _post(base_url, "/api/logout", {}, token=token)
    if step("POST /api/logout", status, data): successes += 1

    print(f"    {DIM}── {successes} calls succeeded{RESET}")
    return successes

# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Arcadia Finance traffic generator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--url",     default="http://localhost",
                        help="Base URL of the main-app (no trailing slash)")
    parser.add_argument("--loops",   type=int, default=10,
                        help="Total number of sessions to simulate")
    parser.add_argument("--delay",   type=float, default=1.5,
                        help="Base inter-request delay in seconds (randomised ±50%%)")
    parser.add_argument("--threads", type=int, default=1,
                        help="Parallel sessions (>1 for burst / load traffic)")
    parser.add_argument("--user",    default=None,
                        choices=[u["username"] for u in USERS],
                        help="Pin all sessions to a specific user (default: random)")
    args = parser.parse_args()

    base = args.url.rstrip("/")

    print(f"\n{BOLD}{'═'*60}{RESET}")
    print(f"{BOLD}  Arcadia Finance — Traffic Generator{RESET}")
    print(f"{'═'*60}")
    print(f"  Target  : {CYAN}{base}{RESET}")
    print(f"  Sessions: {args.loops}  |  Threads: {args.threads}  |  Delay: {args.delay}s")
    print(f"{'═'*60}\n")

    total_calls = 0
    lock = threading.Lock()

    def run_session(i):
        nonlocal total_calls
        user = (next(u for u in USERS if u["username"] == args.user)
                if args.user else random.choice(USERS))
        calls = simulate_session(base, user, i + 1, args.delay)
        with lock:
            total_calls += calls

    if args.threads == 1:
        for i in range(args.loops):
            run_session(i)
    else:
        active = []
        for i in range(args.loops):
            # Wait until a thread slot is free
            while len([t for t in active if t.is_alive()]) >= args.threads:
                time.sleep(0.1)
            t = threading.Thread(target=run_session, args=(i,), daemon=True)
            t.start()
            active.append(t)
            time.sleep(args.delay * 0.3)   # stagger starts
        for t in active:
            t.join()

    print(f"\n{BOLD}{'═'*60}{RESET}")
    print(f"{BOLD}  Done — {total_calls} API calls succeeded across {args.loops} sessions.{RESET}")
    print(f"{'═'*60}\n")


if __name__ == "__main__":
    main()
