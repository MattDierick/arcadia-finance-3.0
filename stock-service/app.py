"""
app.py – Arcadia Finance stock-service
Provides stock quote / history data by wrapping the yahoo-finance-mcp stdio server.
Protected by JWT auth (same secret as main-app and transfer-service).
"""

import functools
import os

import jwt
from flask import Flask, g, jsonify, request
from flask_cors import CORS

import mcp_client

JWT_SECRET    = os.environ.get("JWT_SECRET", "arcadia-jwt-secret-2026")
JWT_ALGORITHM = "HS256"

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "stock-secret-2026")
CORS(app, origins="*")


# ──────────────────────────────────────────────────────────────
# AUTH
# ──────────────────────────────────────────────────────────────

def require_auth(f):
    """Validate JWT Bearer token (identical logic to transfer-service)."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401
        token = auth[7:]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            g.current_user_id = payload["sub"]
            g.username = payload.get("username", "")
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except jwt.PyJWTError:
            return jsonify({"error": "Invalid token"}), 401
        return f(*args, **kwargs)
    return wrapper


# ──────────────────────────────────────────────────────────────
# STOCK ROUTES
# ──────────────────────────────────────────────────────────────

@app.route("/api/stocks/quote")
@require_auth
def quote():
    """
    GET /api/stocks/quote?ticker=AAPL
    Returns a normalised quote dict for a single ticker.
    """
    ticker = (request.args.get("ticker") or "").strip().upper()
    if not ticker:
        return jsonify({"error": "ticker parameter is required"}), 400
    try:
        data = mcp_client.get_stock_info(ticker)
        return jsonify(data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to fetch quote: {str(e)}"}), 502


@app.route("/api/stocks/history")
@require_auth
def history():
    """
    GET /api/stocks/history?ticker=AAPL&period=1mo&interval=1d
    Returns a list of OHLCV records suitable for Chart.js.
    period  : 1d 5d 1mo 3mo 6mo 1y 2y 5y ytd max  (default 1mo)
    interval: 1m 5m 15m 1h 1d 1wk 1mo              (default 1d)
    """
    ticker   = (request.args.get("ticker") or "").strip().upper()
    period   = request.args.get("period",   "1mo")
    interval = request.args.get("interval", "1d")

    if not ticker:
        return jsonify({"error": "ticker parameter is required"}), 400

    # Validate period / interval to avoid passing arbitrary strings to yfinance
    valid_periods   = {"1d","5d","1mo","3mo","6mo","1y","2y","5y","10y","ytd","max"}
    valid_intervals = {"1m","2m","5m","15m","30m","60m","90m","1h","1d","5d","1wk","1mo","3mo"}
    if period not in valid_periods:
        return jsonify({"error": f"Invalid period '{period}'"}), 400
    if interval not in valid_intervals:
        return jsonify({"error": f"Invalid interval '{interval}'"}), 400

    try:
        records = mcp_client.get_historical_prices(ticker, period=period, interval=interval)
        return jsonify({"ticker": ticker, "period": period, "interval": interval, "data": records})
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to fetch history: {str(e)}"}), 502


@app.route("/api/stocks/search")
@require_auth
def search():
    """
    GET /api/stocks/search?q=AAPL
    Validates the query string as a ticker via get_stock_info.
    Returns a short summary on success, 404 if not found.
    """
    q = (request.args.get("q") or "").strip().upper()
    if not q:
        return jsonify({"error": "q parameter is required"}), 400
    if len(q) > 10:
        return jsonify({"error": "Ticker too long"}), 400
    try:
        data = mcp_client.get_stock_info(q)
        return jsonify({
            "ticker":   data["ticker"],
            "name":     data["name"],
            "price":    data["price"],
            "currency": data["currency"],
            "exchange": data["exchange"],
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"Search failed: {str(e)}"}), 502


# ──────────────────────────────────────────────────────────────
# HEALTH
# ──────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "stock-service"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8082, debug=True)
