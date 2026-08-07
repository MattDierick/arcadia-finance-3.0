#!/usr/bin/env python3
"""Generate the Arcadia Finance Postman collection from the OpenAPI spec."""
import json

OUTPUT = "/Users/m.dierick/Github/demo-app-f5-2026-claude/postman_collection.json"


def bearer():
    return {"type": "bearer", "bearer": [{"key": "token", "value": "{{token}}", "type": "string"}]}


def make_url(path, query=None):
    parts = path.strip("/").split("/")
    raw = "{{base_url}}/" + "/".join(parts)
    obj = {"raw": raw, "host": ["{{base_url}}"], "path": parts}
    if query:
        raw += "?" + "&".join(f"{k}={v}" for k, v in query.items())
        obj["raw"] = raw
        obj["query"] = [{"key": k, "value": v} for k, v in query.items()]
    return obj


def save_token_event():
    return {
        "listen": "test",
        "script": {
            "exec": [
                "var json = pm.response.json();",
                "if (json.access_token) {",
                "    pm.collectionVariables.set('token', json.access_token);",
                "    console.log('Token saved to {{token}}');",
                "}"
            ],
            "type": "text/javascript"
        }
    }


def build_request(method, path, desc, body=None, query=None, auth=True, events=None):
    r = {
        "method": method,
        "header": [],
        "url": make_url(path, query),
        "description": desc
    }
    if auth:
        r["auth"] = bearer()
    if body:
        r["header"].append({"key": "Content-Type", "value": "application/json"})
        r["body"] = {
            "mode": "raw",
            "raw": json.dumps(body, indent=2),
            "options": {"raw": {"language": "json"}}
        }
    node = {"request": r}
    if events:
        node["event"] = events
    return node


def make_item(name, node, responses=None):
    obj = {"name": name}
    obj.update(node)
    if responses:
        obj["response"] = responses
    return obj


def make_resp(name, code, status, body_obj, orig_request):
    return {
        "name": name,
        "status": status,
        "code": code,
        "originalRequest": orig_request,
        "header": [{"key": "Content-Type", "value": "application/json"}],
        "_postman_previewlanguage": "json",
        "body": json.dumps(body_obj, indent=2)
    }


# ---------------------------------------------------------------------------
# Authentication folder
# ---------------------------------------------------------------------------

def build_authentication():
    token_node = build_request(
        "POST", "/api/token",
        "Issues a JWT Bearer token (HS256, 8-hour expiry). "
        "The test script automatically saves the token to the {{token}} collection variable.",
        body={"username": "alice", "password": "alice123"},
        auth=False, events=[save_token_event()]
    )
    login_node = build_request(
        "POST", "/api/login",
        "Authenticates the user, sets a Flask session cookie and returns a JWT.\n"
        "NOTE: Intentionally vulnerable to SQL injection (F5 demo surface).\n"
        "The test script automatically saves the token to the {{token}} collection variable.",
        body={"username": "thomas", "password": "thomas123"},
        auth=False, events=[save_token_event()]
    )
    logout_node = build_request(
        "POST", "/api/logout",
        "Clears the server-side Flask session cookie. "
        "The client must also remove the JWT from localStorage.",
        auth=False
    )

    return {
        "name": "Authentication",
        "description": "Obtain and invalidate JWT tokens",
        "item": [
            make_item("Get Token  POST /api/token", token_node, [
                make_resp("200 – Token issued (alice)", 200, "OK", {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer", "expires_in": 28800,
                    "user": {"id": 1, "name": "Alice", "surname": "Moreau",
                             "email": "alice.moreau@arcadiafinance.com",
                             "phone": "+33 6 12 34 56 78", "username": "alice"}
                }, token_node["request"]),
                make_resp("401 – Invalid credentials", 401, "Unauthorized",
                          {"error": "Invalid username or password"}, token_node["request"])
            ]),
            make_item("Login  POST /api/login", login_node, [
                make_resp("200 – Login successful (thomas)", 200, "OK", {
                    "id": 2, "name": "Thomas", "surname": "Lefebvre",
                    "email": "thomas.lefebvre@arcadiafinance.com",
                    "phone": "+33 6 23 45 67 89", "username": "thomas",
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer", "expires_in": 28800
                }, login_node["request"]),
                make_resp("401 – Invalid credentials", 401, "Unauthorized",
                          {"error": "Invalid username or password"}, login_node["request"]),
                make_resp("500 – SQL error (SQLi surface)", 500, "Internal Server Error",
                          {"error": "Database error: syntax error in SQL query..."}, login_node["request"])
            ]),
            make_item("Logout  POST /api/logout", logout_node, [
                make_resp("200 – Session cleared", 200, "OK",
                          {"message": "Logged out"}, logout_node["request"])
            ])
        ]
    }


# ---------------------------------------------------------------------------
# Users folder
# ---------------------------------------------------------------------------

def build_users():
    me_node = build_request("GET", "/api/me", "Returns the profile of the currently authenticated user.")
    users_node = build_request("GET", "/api/users", "Returns the full user directory.")
    user_id_node = build_request(
        "GET", "/api/users/2",
        "INTENTIONALLY VULNERABLE TO BOLA (OWASP API1:2023).\n"
        "Any valid token holder can enumerate all user profiles including plain-text passwords:\n"
        "  GET /api/users/1 -> Alice + password\n"
        "  GET /api/users/2 -> Thomas + password\n"
        "  GET /api/users/3 -> Sophie + password\n"
        "  GET /api/users/4 -> Lucas + password"
    )
    return {
        "name": "Users",
        "description": "Current user profile and user list",
        "item": [
            make_item("Get My Profile  GET /api/me", me_node, [
                make_resp("200 - User profile", 200, "OK", {
                    "id": 1, "name": "Alice", "surname": "Moreau",
                    "email": "alice.moreau@arcadiafinance.com",
                    "phone": "+33 6 12 34 56 78", "username": "alice"
                }, me_node["request"]),
                make_resp("401 - Not authenticated", 401, "Unauthorized",
                          {"error": "Missing or invalid token"}, me_node["request"])
            ]),
            make_item("List All Users  GET /api/users", users_node, [
                make_resp("200 - Array of all users", 200, "OK", [
                    {"id": 1, "name": "Alice", "username": "alice"},
                    {"id": 2, "name": "Thomas", "username": "thomas"}
                ], users_node["request"])
            ]),
            make_item("Get User by ID BOLA  GET /api/users/2", user_id_node, [
                make_resp("200 - Thomas profile (plain-text password exposed)", 200, "OK", {
                    "id": 2, "name": "Thomas", "surname": "Lefebvre",
                    "email": "thomas.lefebvre@arcadiafinance.com",
                    "phone": "+33 6 23 45 67 89",
                    "username": "thomas", "password": "thomas123"
                }, user_id_node["request"]),
                make_resp("404 - User not found", 404, "Not Found",
                          {"error": "User not found"}, user_id_node["request"])
            ])
        ]
    }



# ---------------------------------------------------------------------------
# Accounts folder
# ---------------------------------------------------------------------------

def build_accounts():
    acc_node = build_request(
        "GET", "/api/accounts",
        "List bank accounts for the authenticated user.\n"
        "Optional user_id query param overrides the user (BOLA surface - no ownership check)."
    )
    acc_bola_node = build_request(
        "GET", "/api/accounts",
        "BOLA demo: pass a different user_id to see another user accounts without authorization check.",
        query={"user_id": "2"}
    )
    return {
        "name": "Accounts",
        "description": "Bank accounts belonging to the authenticated user",
        "item": [
            make_item("List My Accounts  GET /api/accounts", acc_node, [
                make_resp("200 - Array of accounts", 200, "OK", [
                    {"id": 1, "account_number": "FR7601234001001", "type": "checking",
                     "balance": 12450.75, "currency": "EUR", "created_at": "2026-01-15T09:00:00"},
                    {"id": 2, "account_number": "FR7601234001002", "type": "savings",
                     "balance": 35000.00, "currency": "EUR", "created_at": "2026-01-15T09:00:00"}
                ], acc_node["request"])
            ]),
            make_item("List Accounts BOLA  GET /api/accounts?user_id=2", acc_bola_node, [
                make_resp("200 - Another user accounts (BOLA)", 200, "OK", [
                    {"id": 3, "account_number": "FR7601234002001", "type": "checking",
                     "balance": 8200.00, "currency": "EUR", "created_at": "2026-01-20T10:00:00"}
                ], acc_bola_node["request"])
            ])
        ]
    }


# ---------------------------------------------------------------------------
# Transfers folder
# ---------------------------------------------------------------------------

def build_transfers():
    history_node = build_request(
        "GET", "/api/transfers",
        "Returns all transfers (sent and received) for the authenticated user, ordered by date descending."
    )
    create_node = build_request(
        "POST", "/api/transfer",
        "Executes a money transfer. The transfer-service validates balances atomically.",
        body={"from_account": "FR7601234001001", "to_account": "FR7601234002001",
              "amount": 250.00, "note": "Invoice #42"}
    )
    return {
        "name": "Transfers",
        "description": "Money transfers between accounts",
        "item": [
            make_item("Get Transfer History  GET /api/transfers", history_node, [
                make_resp("200 - List of transfers", 200, "OK", [
                    {"id": 7, "from_account": "FR7601234001001",
                     "to_account": "FR7601234002001", "amount": 500.00,
                     "note": "Dinner split", "status": "completed",
                     "created_at": "2026-07-01T10:30:00"}
                ], history_node["request"])
            ]),
            make_item("Create Transfer  POST /api/transfer", create_node, [
                make_resp("200 - Transfer completed", 200, "OK", {
                    "message": "Transfer completed successfully", "transfer_id": 14,
                    "from_account": "FR7601234001001", "to_account": "FR7601234002001",
                    "amount": 250.00, "note": "Invoice #42"
                }, create_node["request"]),
                make_resp("422 - Insufficient funds", 422, "Unprocessable Entity",
                          {"error": "Insufficient funds"}, create_node["request"]),
                make_resp("400 - Missing required field", 400, "Bad Request",
                          {"error": "amount is required"}, create_node["request"])
            ])
        ]
    }



# ---------------------------------------------------------------------------
# Stocks folder
# ---------------------------------------------------------------------------

def _stocks_nodes():
    quote = build_request(
        "GET", "/api/stocks/quote",
        "Returns a real-time normalised quote for the requested ticker (yfinance MCP).",
        query={"ticker": "AAPL"}
    )
    hist = build_request(
        "GET", "/api/stocks/history",
        "Returns OHLCV price history. Valid periods: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max",
        query={"ticker": "AAPL", "period": "1mo"}
    )
    search = build_request(
        "GET", "/api/stocks/search",
        "Resolves an exact ticker symbol. Must be exact (e.g. AAPL not Apple). Max 10 chars.",
        query={"q": "NVDA"}
    )
    portfolio = build_request(
        "GET", "/api/stocks/portfolio",
        "Returns all stock holdings for the current user, ordered by ticker."
    )
    orders = build_request(
        "GET", "/api/stocks/orders",
        "Returns all stock orders for the current user, ordered by created_at descending."
    )
    buy = build_request(
        "POST", "/api/stocks/buy",
        "Purchases shares: fetches live price, debits account, upserts holdings, inserts order.\n"
        "Fractional shares supported (minimum 0.001).",
        body={"ticker": "AAPL", "quantity": 5, "from_account": "FR7601234001001"}
    )
    buy_frac = build_request(
        "POST", "/api/stocks/buy",
        "Fractional share purchase example (0.5 shares of NVDA).",
        body={"ticker": "NVDA", "quantity": 0.5, "from_account": "FR7601234001002"}
    )
    return quote, hist, search, portfolio, orders, buy, buy_frac



def build_stocks():
    q, h, s, p, o, b, bf = _stocks_nodes()
    return {
        "name": "Stocks",
        "description": "Live stock quotes, price history and share purchases via Yahoo Finance MCP (stock-service port 8082). All routes proxied through main-app, require JWT.",
        "item": [
            make_item("Get Stock Quote  GET /api/stocks/quote", q, [
                make_resp("200 - Live quote (AAPL)", 200, "OK", {
                    "ticker": "AAPL", "name": "Apple Inc.", "price": 213.49,
                    "currency": "USD", "exchange": "NMS", "change": 1.23,
                    "change_pct": 0.58, "market_cap": 3280000000000, "pe_ratio": 33.4,
                    "volume": 52341200, "day_high": 215.10, "day_low": 211.85,
                    "fifty_two_week_high": 237.23, "fifty_two_week_low": 164.08,
                    "sector": "Technology", "industry": "Consumer Electronics"
                }, q["request"]),
                make_resp("404 - Ticker not found", 404, "Not Found",
                          {"error": "Ticker INVALID not found"}, q["request"]),
                make_resp("503 - stock-service unavailable", 503, "Service Unavailable",
                          {"error": "stock-service unavailable"}, q["request"])
            ]),
            make_item("Get Stock History  GET /api/stocks/history", h, [
                make_resp("200 - Price history (AAPL 1mo)", 200, "OK", [
                    {"date": "2026-06-08", "open": 210.52, "high": 212.30,
                     "low": 209.85, "close": 211.60, "volume": 45230100}
                ], h["request"])
            ]),
            make_item("Search Stock Ticker  GET /api/stocks/search", s, [
                make_resp("200 - Ticker resolved (NVDA)", 200, "OK", {
                    "ticker": "NVDA", "name": "NVIDIA Corporation",
                    "price": 131.38, "currency": "USD", "exchange": "NMS"
                }, s["request"]),
                make_resp("404 - Ticker not found", 404, "Not Found",
                          {"error": "Ticker not found"}, s["request"])
            ]),
            make_item("Get Stock Portfolio  GET /api/stocks/portfolio", p, [
                make_resp("200 - Holdings list", 200, "OK", [
                    {"ticker": "AAPL", "quantity": 10.0, "avg_price": 207.32,
                     "currency": "USD", "updated_at": "2026-07-08T14:23:00"},
                    {"ticker": "NVDA", "quantity": 3.0, "avg_price": 128.50,
                     "currency": "USD", "updated_at": "2026-07-08T15:01:00"}
                ], p["request"])
            ]),
            make_item("Get Stock Orders  GET /api/stocks/orders", o, [
                make_resp("200 - Order history", 200, "OK", [
                    {"id": 3, "ticker": "AAPL", "quantity": 5.0, "price": 213.49,
                     "total": 1067.45, "currency": "USD",
                     "from_account": "FR7601234001001", "status": "completed",
                     "created_at": "2026-07-08T14:23:00"}
                ], o["request"])
            ]),
            make_item("Buy Stock  POST /api/stocks/buy", b, [
                make_resp("200 - Purchase completed (5 x AAPL)", 200, "OK", {
                    "message": "Successfully purchased 5 share(s) of AAPL",
                    "order_id": 3, "ticker": "AAPL", "quantity": 5.0,
                    "price": 213.49, "total": 1067.45, "currency": "USD",
                    "from_account": "FR7601234001001"
                }, b["request"]),
                make_resp("422 - Insufficient funds", 422, "Unprocessable Entity",
                          {"error": "Insufficient funds"}, b["request"]),
                make_resp("404 - Ticker not found", 404, "Not Found",
                          {"error": "Ticker not found"}, b["request"])
            ]),
            make_item("Buy Stock Fractional  POST /api/stocks/buy", bf, [
                make_resp("200 - Purchase completed (0.5 x NVDA)", 200, "OK", {
                    "message": "Successfully purchased 0.5 share(s) of NVDA",
                    "order_id": 4, "ticker": "NVDA", "quantity": 0.5,
                    "price": 131.38, "total": 65.69, "currency": "USD",
                    "from_account": "FR7601234001002"
                }, bf["request"])
            ])
        ]
    }



# ---------------------------------------------------------------------------
# Configuration folder
# ---------------------------------------------------------------------------

def build_config():
    get_node = build_request(
        "GET", "/api/config",
        "Returns the current LLM / chatbot configuration (URL, masked token, model, system prompt)."
    )
    update_node = build_request(
        "POST", "/api/config",
        "Updates the LLM configuration used by the Aria chatbot. All fields are optional.",
        body={
            "llm_url":           "https://api.openai.com",
            "llm_token":         "sk-proj-your-token-here",
            "llm_model":         "gpt-4o",
            "llm_system_prompt": "You are Aria, the Arcadia Finance AI assistant."
        }
    )
    return {
        "name": "Configuration",
        "description": "LLM / chatbot configuration",
        "item": [
            make_item("Get LLM Config  GET /api/config", get_node, [
                make_resp("200 - LLM config", 200, "OK", {
                    "llm_url": "https://api.openai.com",
                    "llm_token_masked": "sk-pro...k3Qz",
                    "llm_model": "gpt-4o",
                    "llm_system_prompt": "You are Aria, the Arcadia Finance AI assistant."
                }, get_node["request"]),
                make_resp("401 - Not authenticated", 401, "Unauthorized",
                          {"error": "Missing or invalid token"}, get_node["request"])
            ]),
            make_item("Update LLM Config  POST /api/config", update_node, [
                make_resp("200 - Config updated", 200, "OK",
                          {"message": "Configuration updated"}, update_node["request"]),
                make_resp("401 - Not authenticated", 401, "Unauthorized",
                          {"error": "Missing or invalid token"}, update_node["request"])
            ])
        ]
    }


# ---------------------------------------------------------------------------
# Chatbot folder
# ---------------------------------------------------------------------------

def build_chatbot():
    chat_node = build_request(
        "POST", "/api/chat",
        "Sends a conversation to the configured LLM and returns Aria reply.\n"
        "The system prompt is prepended automatically from stored configuration.\n"
        "Supported backends: Azure OpenAI, OpenAI, Ollama, LM Studio, vLLM.",
        body={"messages": [{"role": "user", "content": "What is my current balance?"}]}
    )
    return {
        "name": "Chatbot",
        "description": "Aria AI assistant (proxies to configured LLM)",
        "item": [
            make_item("Chat with Aria  POST /api/chat", chat_node, [
                make_resp("200 - Aria replies", 200, "OK", {
                    "reply": "Hello! I am Aria, your Arcadia Finance assistant. "
                             "Let me check your balance for you..."
                }, chat_node["request"]),
                make_resp("502 - LLM backend error", 502, "Bad Gateway",
                          {"error": "LLM backend returned an error"}, chat_node["request"]),
                make_resp("504 - LLM request timed out", 504, "Gateway Timeout",
                          {"error": "LLM request timed out (60s limit)"}, chat_node["request"])
            ])
        ]
    }


# ---------------------------------------------------------------------------
# Assemble and write the collection
# ---------------------------------------------------------------------------

def main():
    collection = {
        "info": {
            "name": "Arcadia Finance API",
            "description": (
                "REST API for the Arcadia Finance demo banking application.\n\n"
                "WARNING: Intentionally vulnerable (SQL injection, plain-text passwords, "
                "verbose errors) for F5 WAF/security demonstration purposes. "
                "NEVER deploy in production.\n\n"
                "## Authentication\n\n"
                "All private endpoints require a valid JWT Bearer token (HS256, 8-hour expiry).\n\n"
                "Workflow:\n"
                "1. POST /api/token with username + password -> receive access_token\n"
                "2. Every request: Authorization: Bearer <access_token>\n\n"
                "The collection variable {{base_url}} defaults to http://localhost:8080. "
                "After running 'Get Token' or 'Login', the {{token}} variable is set automatically."
            ),
            "version": "1.0.0",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
        },
        "variable": [
            {"key": "base_url", "value": "http://localhost:8080", "type": "string"},
            {"key": "token",    "value": "",                       "type": "string"}
        ],
        "auth": bearer(),
        "item": [
            build_authentication(),
            build_users(),
            build_accounts(),
            build_transfers(),
            build_stocks(),
            build_config(),
            build_chatbot()
        ]
    }
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(collection, f, indent=2, ensure_ascii=False)
    print(f"Postman collection written to {OUTPUT}")


if __name__ == "__main__":
    main()

