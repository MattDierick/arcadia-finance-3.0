"""
db.py – MySQL connection helper for main-app
⚠️  Uses plain string-formatted SQL queries intentionally (SQL-injection surface for F5 demo).
"""
import os
import pymysql
import pymysql.cursors

DB_HOST = os.environ.get("DB_HOST", "db")
DB_PORT = int(os.environ.get("DB_PORT", 3306))
DB_USER = os.environ.get("DB_USER", "arcadia")
DB_PASS = os.environ.get("DB_PASS", "arcadia_pass")
DB_NAME = os.environ.get("DB_NAME", "arcadia")


def get_connection():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def query(sql, params=None):
    """Execute a parameterised SELECT and return all rows."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()
    finally:
        conn.close()


def execute(sql, params=None):
    """Execute a parameterised INSERT / UPDATE / DELETE."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.lastrowid
    finally:
        conn.close()


def query_raw(sql):
    """
    ⚠️  INTENTIONALLY VULNERABLE: executes a raw, un-parameterised SQL string.
    Used in login and search to allow SQL injection demos.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()
    finally:
        conn.close()
