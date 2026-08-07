"""
app.py – Arcadia Finance transfer-service
Handles money transfers and transfer history.
⚠️  Deliberately vulnerable (SQLi in history lookup) for F5 security demo.
"""

import os
import functools
import jwt
from flask import Flask, request, jsonify, g
from flask_cors import CORS
import pymysql
import db as dbmod

JWT_SECRET = os.environ.get("JWT_SECRET", "arcadia-jwt-secret-2026")
JWT_ALGORITHM = "HS256"

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "transfer-secret-2026")
CORS(app, origins="*")


# ──────────────────────────────────────────────────────────────
# JWT AUTH DECORATOR
# ──────────────────────────────────────────────────────────────

def require_auth(f):
    """Validates the JWT Bearer token on every protected endpoint."""
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


def _serialize(rows):
    """Convert Decimal / datetime objects for JSON."""
    result = []
    for r in rows:
        row = {}
        for k, v in r.items():
            if hasattr(v, "isoformat"):
                row[k] = v.isoformat()
            elif hasattr(v, "__float__"):
                row[k] = float(v)
            else:
                row[k] = v
        result.append(row)
    return result


# ──────────────────────────────────────────────────────────────
# POST /api/transfer
# ──────────────────────────────────────────────────────────────

@app.route("/api/transfer", methods=["POST"])
@require_auth
def transfer():
    data = request.get_json(force=True)
    from_account = data.get("from_account", "").strip()
    to_account   = data.get("to_account", "").strip()
    amount_raw   = data.get("amount", 0)
    note         = data.get("note", "")

    if not from_account or not to_account:
        return jsonify({"error": "from_account and to_account are required"}), 400

    try:
        amount = float(amount_raw)
        if amount <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return jsonify({"error": "Amount must be a positive number"}), 400

    conn = dbmod.get_connection()
    try:
        with conn.cursor() as cur:
            # Fetch source account
            cur.execute("SELECT id, balance FROM accounts WHERE account_number = %s FOR UPDATE", (from_account,))
            src = cur.fetchone()
            if not src:
                return jsonify({"error": f"Source account {from_account} not found"}), 404
            if float(src["balance"]) < amount:
                return jsonify({"error": "Insufficient funds"}), 422

            # Fetch destination account
            cur.execute("SELECT id, balance FROM accounts WHERE account_number = %s FOR UPDATE", (to_account,))
            dst = cur.fetchone()
            if not dst:
                return jsonify({"error": f"Destination account {to_account} not found"}), 404

            # Debit / credit
            cur.execute("UPDATE accounts SET balance = balance - %s WHERE account_number = %s", (amount, from_account))
            cur.execute("UPDATE accounts SET balance = balance + %s WHERE account_number = %s", (amount, to_account))

            # Record transfer
            cur.execute(
                "INSERT INTO transfers (from_account, to_account, amount, note, status) VALUES (%s, %s, %s, %s, 'completed')",
                (from_account, to_account, amount, note),
            )
            transfer_id = cur.lastrowid
        conn.commit()

        return jsonify({
            "message": "Transfer completed successfully",
            "transfer_id": transfer_id,
            "from_account": from_account,
            "to_account": to_account,
            "amount": amount,
            "note": note,
        })
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────
# GET /api/transfers?account=<account_number>
# ⚠️  INTENTIONALLY VULNERABLE TO SQL INJECTION
# ──────────────────────────────────────────────────────────────

@app.route("/api/transfers")
@require_auth
def transfers():
    account = request.args.get("account", "")
    # ⚠️  Raw SQL – intentional SQLi surface
    sql = (
        f"SELECT * FROM transfers "
        f"WHERE from_account = '{account}' OR to_account = '{account}' "
        f"ORDER BY created_at DESC LIMIT 50"
    )
    try:
        rows = dbmod.query_raw(sql)
        return jsonify(_serialize(rows))
    except Exception as e:
        return jsonify({"error": str(e), "sql": sql}), 500


# ──────────────────────────────────────────────────────────────
# HEALTH
# ──────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "transfer-service"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081, debug=True)
