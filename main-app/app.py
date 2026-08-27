"""
app.py – Arcadia Finance main-app
Serves the frontend and all API routes except money transfers (proxied to transfer-service).
⚠️  Deliberately vulnerable (SQLi on login, verbose errors) for F5 security demo.
"""

import os
import datetime
import functools
import requests as http_requests
import jwt
from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
import db

TRANSFER_SERVICE_URL = os.environ.get("TRANSFER_SERVICE_URL", "http://transfer-service:8081")
STOCK_SERVICE_URL    = os.environ.get("STOCK_SERVICE_URL",    "http://stock-service:8082")
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")
JWT_SECRET = os.environ.get("JWT_SECRET", "arcadia-jwt-secret-2026")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 8

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
app.secret_key = os.environ.get("SECRET_KEY", "arcadia-super-secret-2026")
CORS(app, supports_credentials=True, origins="*")


# ──────────────────────────────────────────────────────────────
# JWT HELPERS
# ──────────────────────────────────────────────────────────────

def _create_jwt(user):
    """Issue a signed JWT for the given user dict."""
    payload = {
        "sub": user["id"],
        "username": user["username"],
        "iat": datetime.datetime.utcnow(),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _decode_jwt(token):
    """Decode and validate a JWT. Returns the payload or raises jwt.PyJWTError."""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def _get_token_from_request():
    """Extract the Bearer token from the Authorization header, if present."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


def require_auth(f):
    """
    Decorator that enforces authentication via JWT (Authorization: Bearer <token>)
    OR via an active Flask session (browser-based login).
    Sets g.current_user_id for use inside the route.
    """
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        from flask import g

        # 1. Try JWT Bearer token first (Postman / API clients)
        token = _get_token_from_request()
        if token:
            try:
                payload = _decode_jwt(token)
                g.current_user_id = payload["sub"]
                g.jwt_token = token   # forward to transfer-service if needed
                return f(*args, **kwargs)
            except jwt.ExpiredSignatureError:
                return jsonify({"error": "Token has expired"}), 401
            except jwt.PyJWTError:
                return jsonify({"error": "Invalid token"}), 401

        # 2. Fall back to Flask session (browser cookies)
        user_id = session.get("user_id")
        if user_id:
            g.current_user_id = user_id
            g.jwt_token = None
            return f(*args, **kwargs)

        return jsonify({"error": "Not authenticated"}), 401

    return wrapper

# ──────────────────────────────────────────────────────────────
# STATIC FRONTEND
# ──────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/<path:path>")
def static_files(path):
    full = os.path.join(FRONTEND_DIR, path)
    if os.path.isfile(full):
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, "index.html")

# ──────────────────────────────────────────────────────────────
# AUTH
# ──────────────────────────────────────────────────────────────

@app.route("/api/token", methods=["POST"])
def token():
    """
    Exchange username + password for a JWT.
    Used by API clients (Postman, curl, etc.).
    ⚠️  INTENTIONALLY VULNERABLE TO SQL INJECTION (F5 demo surface).
    """
    data = request.get_json(force=True)
    username = data.get("username", "")
    password = data.get("password", "")
    # ⚠️  Raw SQL concatenation – intentional SQLi
    sql = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
    try:
        rows = db.query_raw(sql)
    except Exception as e:
        return jsonify({"error": str(e), "sql": sql}), 500
    if not rows:
        return jsonify({"error": "Invalid credentials"}), 401
    user = rows[0]
    access_token = _create_jwt(user)
    return jsonify({
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": JWT_EXPIRY_HOURS * 3600,
        "user": {
            "id": user["id"], "name": user["name"], "surname": user["surname"],
            "email": user["email"], "phone": user["phone"], "username": user["username"],
        },
    })


@app.route("/api/login", methods=["POST"])
def login():
    """
    Browser login – sets a Flask session cookie AND returns a JWT.
    ⚠️  INTENTIONALLY VULNERABLE TO SQL INJECTION (F5 demo surface).
    """
    data = request.get_json(force=True)
    username = data.get("username", "")
    password = data.get("password", "")
    # ⚠️  Raw SQL concatenation – intentional SQLi
    sql = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
    try:
        rows = db.query_raw(sql)
    except Exception as e:
        return jsonify({"error": str(e), "sql": sql}), 500
    if not rows:
        return jsonify({"error": "Invalid credentials"}), 401
    user = rows[0]
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    access_token = _create_jwt(user)
    return jsonify({
        "id": user["id"], "name": user["name"], "surname": user["surname"],
        "email": user["email"], "phone": user["phone"], "username": user["username"],
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": JWT_EXPIRY_HOURS * 3600,
    })


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"})


@app.route("/api/me")
@require_auth
def me():
    from flask import g
    rows = db.query("SELECT id, name, surname, email, phone, username FROM users WHERE id = %s", (g.current_user_id,))
    if not rows:
        return jsonify({"error": "User not found"}), 404
    return jsonify(rows[0])

# ──────────────────────────────────────────────────────────────
# ACCOUNTS
# ──────────────────────────────────────────────────────────────

@app.route("/api/accounts")
@require_auth
def accounts():
    from flask import g
    # Allow an explicit user_id query param (kept for backward compat), otherwise use the authenticated user
    user_id = request.args.get("user_id") or g.current_user_id
    rows = db.query(
        "SELECT id, account_number, type, balance, currency, created_at FROM accounts WHERE user_id = %s ORDER BY type",
        (user_id,)
    )
    for r in rows:
        r["balance"] = float(r["balance"])
        if r["created_at"]:
            r["created_at"] = r["created_at"].isoformat()
    return jsonify(rows)


@app.route("/api/users")
@require_auth
def users():
    rows = db.query("SELECT id, name, surname, email, phone, username FROM users")
    return jsonify(rows)


@app.route("/api/users/<int:user_id>")
@require_auth
def get_user(user_id):
    """
    Return the profile of a specific user by ID.
    ⚠️  INTENTIONALLY VULNERABLE TO BOLA (Broken Object Level Authorization):
        Any authenticated user can fetch ANY other user's data simply by
        changing the {user_id} path parameter.  There is NO check that the
        requested ID belongs to the caller – this is the classic BOLA pattern.
    """
    # ⚠️  No ownership check: g.current_user_id is never compared to user_id
    rows = db.query(
        "SELECT id, name, surname, email, phone, username, password FROM users WHERE id = %s",
        (user_id,),
    )
    if not rows:
        return jsonify({"error": "User not found"}), 404
    return jsonify(rows[0])


# ──────────────────────────────────────────────────────────────
# TRANSFERS – proxy to transfer-service
# ──────────────────────────────────────────────────────────────

@app.route("/api/transfer", methods=["POST"])
@require_auth
def transfer():
    from flask import g
    # Build auth header to forward to transfer-service
    # If the client used a JWT, forward it; otherwise mint a new service token
    fwd_token = g.jwt_token or _create_jwt(
        db.query("SELECT id, username FROM users WHERE id = %s", (g.current_user_id,))[0]
    )
    headers = {"Authorization": f"Bearer {fwd_token}"}
    try:
        resp = http_requests.post(
            f"{TRANSFER_SERVICE_URL}/api/transfer",
            json=request.get_json(force=True),
            headers=headers,
            timeout=10,
        )
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({"error": f"Transfer service unavailable: {str(e)}"}), 503


@app.route("/api/transfers")
@require_auth
def transfers():
    from flask import g
    fwd_token = g.jwt_token or _create_jwt(
        db.query("SELECT id, username FROM users WHERE id = %s", (g.current_user_id,))[0]
    )
    headers = {"Authorization": f"Bearer {fwd_token}"}
    account = request.args.get("account", "")
    try:
        resp = http_requests.get(
            f"{TRANSFER_SERVICE_URL}/api/transfers",
            params={"account": account},
            headers=headers,
            timeout=10,
        )
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({"error": f"Transfer service unavailable: {str(e)}"}), 503

# ──────────────────────────────────────────────────────────────
# APP CONFIG (LLM settings)
# ──────────────────────────────────────────────────────────────

@app.route("/api/config", methods=["GET"])
@require_auth
def get_config():
    rows = db.query("SELECT config_key, config_value FROM app_config")
    cfg = {r["config_key"]: r["config_value"] for r in rows}
    # llm_token is stored in the user's browser only — never returned from the server.
    cfg.pop("llm_token", None)
    return jsonify(cfg)


@app.route("/api/config", methods=["POST"])
@require_auth
def set_config():
    data = request.get_json(force=True)
    # llm_token is intentionally excluded: it must never be persisted on the server.
    allowed_keys = {"llm_url", "llm_model", "chatbot_system_prompt"}
    for key, value in data.items():
        if key in allowed_keys:
            db.execute(
                "INSERT INTO app_config (config_key, config_value) VALUES (%s, %s) "
                "ON DUPLICATE KEY UPDATE config_value = VALUES(config_value)",
                (key, value),
            )
    return jsonify({"message": "Configuration saved"})

# ──────────────────────────────────────────────────────────────
# CHATBOT – proxies to configured LLM
# ──────────────────────────────────────────────────────────────

@app.route("/api/chat", methods=["POST"])
@require_auth
def chat():
    rows = db.query("SELECT config_key, config_value FROM app_config")
    cfg = {r["config_key"]: r["config_value"] for r in rows}

    llm_url    = (cfg.get("llm_url") or "").strip()
    llm_model  = (cfg.get("llm_model") or "gpt-4o").strip()
    sys_prompt = cfg.get("chatbot_system_prompt") or "You are Aria, a helpful Arcadia Finance virtual assistant."

    # The LLM token is stored exclusively in the user's browser (localStorage).
    # The browser sends it per-request via the X-LLM-Token header.
    # It is used only in-memory here to build the outbound request — never written to DB or disk.
    llm_token = (request.headers.get("X-LLM-Token") or "").strip()

    if not llm_url:
        return jsonify({
            "reply": "I'm not configured yet. Please go to **Settings > LLM Config** and enter your LLM URL and API token.",
            "configured": False,
        })

    data = request.get_json(force=True)
    messages = data.get("messages", [])
    full_messages = [{"role": "system", "content": sys_prompt}] + messages

    headers = {"Content-Type": "application/json"}
    if llm_token:
        # Azure OpenAI uses "api-key" header; all other providers use "Authorization: Bearer"
        if "openai.azure.com" in llm_url:
            headers["api-key"] = llm_token
        else:
            headers["Authorization"] = f"Bearer {llm_token}"

    # Resolve the final endpoint URL:
    #   - If the stored URL already contains "chat/completions" (e.g. full Azure OpenAI URL
    #     with deployment path + api-version query param), use it exactly as-is.
    #   - If it ends with "/v1", append "/chat/completions".
    #   - Otherwise treat it as a base URL and append "/v1/chat/completions".
    url_stripped = llm_url.rstrip("/")
    if "chat/completions" in url_stripped:
        endpoint = llm_url  # already a full endpoint — preserve query string intact
    elif url_stripped.endswith("/v1"):
        endpoint = url_stripped + "/chat/completions"
    else:
        endpoint = url_stripped + "/v1/chat/completions"

    # Azure OpenAI ignores the "model" field (the deployment is encoded in the URL),
    # but sending it is harmless. For non-Azure endpoints the model field is required.
    payload = {"model": llm_model, "messages": full_messages, "stream": False}

    try:
        resp = http_requests.post(endpoint, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        reply = result["choices"][0]["message"]["content"]
        return jsonify({"reply": reply, "configured": True})
    except http_requests.exceptions.Timeout:
        return jsonify({"error": "LLM request timed out", "configured": True}), 504
    except Exception as e:
        return jsonify({"error": str(e), "configured": True}), 502


# ──────────────────────────────────────────────────────────────
# STOCKS – proxy to stock-service + portfolio/buy in main-app
# ──────────────────────────────────────────────────────────────

def _stock_headers():
    """Build auth headers to forward (or mint) a JWT for stock-service."""
    from flask import g
    fwd_token = g.jwt_token or _create_jwt(
        db.query("SELECT id, username FROM users WHERE id = %s", (g.current_user_id,))[0]
    )
    return {"Authorization": f"Bearer {fwd_token}"}


@app.route("/api/stocks/quote")
@require_auth
def stock_quote():
    """Proxy GET /api/stocks/quote?ticker=X to stock-service."""
    try:
        resp = http_requests.get(
            f"{STOCK_SERVICE_URL}/api/stocks/quote",
            params={"ticker": request.args.get("ticker", "")},
            headers=_stock_headers(),
            timeout=30,
        )
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({"error": f"Stock service unavailable: {str(e)}"}), 503


@app.route("/api/stocks/history")
@require_auth
def stock_history():
    """Proxy GET /api/stocks/history?ticker=X&period=1mo&interval=1d to stock-service."""
    try:
        resp = http_requests.get(
            f"{STOCK_SERVICE_URL}/api/stocks/history",
            params={
                "ticker":   request.args.get("ticker", ""),
                "period":   request.args.get("period",   "1mo"),
                "interval": request.args.get("interval", "1d"),
            },
            headers=_stock_headers(),
            timeout=30,
        )
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({"error": f"Stock service unavailable: {str(e)}"}), 503


@app.route("/api/stocks/search")
@require_auth
def stock_search():
    """Proxy GET /api/stocks/search?q=X to stock-service."""
    try:
        resp = http_requests.get(
            f"{STOCK_SERVICE_URL}/api/stocks/search",
            params={"q": request.args.get("q", "")},
            headers=_stock_headers(),
            timeout=30,
        )
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({"error": f"Stock service unavailable: {str(e)}"}), 503


@app.route("/api/stocks/portfolio")
@require_auth
def stock_portfolio():
    """Return the authenticated user's stock holdings."""
    from flask import g
    rows = db.query(
        "SELECT ticker, quantity, avg_price, currency, updated_at "
        "FROM stock_holdings WHERE user_id = %s ORDER BY ticker",
        (g.current_user_id,),
    )
    result = []
    for r in rows:
        result.append({
            "ticker":    r["ticker"],
            "quantity":  float(r["quantity"]),
            "avg_price": float(r["avg_price"]),
            "currency":  r["currency"],
            "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
        })
    return jsonify(result)


@app.route("/api/stocks/orders")
@require_auth
def stock_orders():
    """Return the authenticated user's stock order history."""
    from flask import g
    rows = db.query(
        "SELECT id, ticker, quantity, price, total, currency, from_account, status, created_at "
        "FROM stock_orders WHERE user_id = %s ORDER BY created_at DESC",
        (g.current_user_id,),
    )
    result = []
    for r in rows:
        result.append({
            "id":           r["id"],
            "ticker":       r["ticker"],
            "quantity":     float(r["quantity"]),
            "price":        float(r["price"]),
            "total":        float(r["total"]),
            "currency":     r["currency"],
            "from_account": r["from_account"],
            "status":       r["status"],
            "created_at":   r["created_at"].isoformat() if r["created_at"] else None,
        })
    return jsonify(result)


@app.route("/api/stocks/buy", methods=["POST"])
@require_auth
def stock_buy():
    """
    Purchase shares of a stock, debiting a bank account.
    Body: { ticker, quantity, from_account }
    """
    from flask import g

    data         = request.get_json(force=True)
    ticker       = (data.get("ticker") or "").strip().upper()
    from_account = (data.get("from_account") or "").strip()
    try:
        quantity = float(data.get("quantity", 0))
        if quantity <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return jsonify({"error": "quantity must be a positive number"}), 400

    if not ticker:
        return jsonify({"error": "ticker is required"}), 400
    if not from_account:
        return jsonify({"error": "from_account is required"}), 400

    # Step 1: fetch live price from stock-service
    try:
        quote_resp = http_requests.get(
            f"{STOCK_SERVICE_URL}/api/stocks/quote",
            params={"ticker": ticker},
            headers=_stock_headers(),
            timeout=30,
        )
        if not quote_resp.ok:
            return jsonify({"error": quote_resp.json().get("error", "Ticker not found")}), 404
        quote = quote_resp.json()
    except Exception as e:
        return jsonify({"error": f"Cannot reach stock service: {str(e)}"}), 503

    price    = float(quote["price"])
    currency = quote.get("currency", "USD")
    total    = round(quantity * price, 4)

    # Step 2: debit the bank account via transfer-service
    # "STOCK-MARKET-VIRTUAL" acts as the destination so existing
    # balance-check + transfer logic handles the debit.
    fwd_token = g.jwt_token or _create_jwt(
        db.query("SELECT id, username FROM users WHERE id = %s", (g.current_user_id,))[0]
    )
    try:
        debit_resp = http_requests.post(
            f"{TRANSFER_SERVICE_URL}/api/transfer",
            json={
                "from_account": from_account,
                "to_account":   "STOCK-MARKET-VIRTUAL",
                "amount":       total,
                "note":         f"Buy {quantity} × {ticker} @ {price} {currency}",
            },
            headers={"Authorization": f"Bearer {fwd_token}"},
            timeout=15,
        )
        if not debit_resp.ok:
            err = debit_resp.json().get("error", "Debit failed")
            return jsonify({"error": err}), debit_resp.status_code
    except Exception as e:
        return jsonify({"error": f"Transfer service unavailable: {str(e)}"}), 503

    # Step 3: upsert stock_holdings (weighted avg price)
    existing = db.query(
        "SELECT quantity, avg_price FROM stock_holdings WHERE user_id = %s AND ticker = %s",
        (g.current_user_id, ticker),
    )
    if existing:
        old_qty = float(existing[0]["quantity"])
        old_avg = float(existing[0]["avg_price"])
        new_qty = old_qty + quantity
        new_avg = round(((old_qty * old_avg) + (quantity * price)) / new_qty, 4)
        db.execute(
            "UPDATE stock_holdings SET quantity=%s, avg_price=%s, currency=%s "
            "WHERE user_id=%s AND ticker=%s",
            (new_qty, new_avg, currency, g.current_user_id, ticker),
        )
    else:
        db.execute(
            "INSERT INTO stock_holdings (user_id, ticker, quantity, avg_price, currency) "
            "VALUES (%s, %s, %s, %s, %s)",
            (g.current_user_id, ticker, quantity, price, currency),
        )

    # Step 4: record the order
    order_id = db.execute(
        "INSERT INTO stock_orders "
        "(user_id, ticker, quantity, price, total, currency, from_account, status) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, 'completed')",
        (g.current_user_id, ticker, quantity, price, total, currency, from_account),
    )

    return jsonify({
        "message":      f"Successfully purchased {quantity} share(s) of {ticker}",
        "order_id":     order_id,
        "ticker":       ticker,
        "quantity":     quantity,
        "price":        price,
        "total":        total,
        "currency":     currency,
        "from_account": from_account,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)

