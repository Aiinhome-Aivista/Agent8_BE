# api/database/db.py
# Simple MySQL connection using pymysql — no pool, no ORM

import os
from contextlib import contextmanager
import pymysql
from pymysql.cursors import DictCursor
from dotenv import load_dotenv

load_dotenv()


def _config():
    return {
        "host": os.getenv("DB_HOST"),
        "port": int(os.getenv("DB_PORT", 3306)),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_NAME"),
        "charset": "utf8mb4",
        "cursorclass": DictCursor,
        "autocommit": False,
    }


def get_connection():
    """Return a new MySQL connection."""
    return pymysql.connect(**_config())


# --- Test connection on module load ---
try:
    _test_conn = get_connection()
    _test_conn.close()
    print("[OK] Database connected successfully!")
except Exception as e:
    print(f"[ERROR] Database connection failed: {e}")


# --- Context manager ---
@contextmanager
def db_cursor(commit=False):
    """Yield (conn, cursor); commits on exit when commit=True, rolls back on error."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        yield conn, cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# --- Simple helpers ---
def fetch_all(sql, params=None):
    with db_cursor() as (_, cur):
        cur.execute(sql, params or ())
        return cur.fetchall()


def fetch_one(sql, params=None):
    with db_cursor() as (_, cur):
        cur.execute(sql, params or ())
        return cur.fetchone()


def execute(sql, params=None):
    with db_cursor(commit=True) as (_, cur):
        cur.execute(sql, params or ())
        return cur.lastrowid


def execute_many(sql, seq_params):
    with db_cursor(commit=True) as (_, cur):
        cur.executemany(sql, seq_params)
        return cur.rowcount


# --- Backward-compatible wrapper (used by existing controllers) ---
def execute_query(query, params=None, fetch="all"):
    """
    Drop-in replacement so existing controllers keep working.
    fetch='all'  -> list of dicts
    fetch='one'  -> single dict or None
    fetch='none' -> lastrowid (INSERT/UPDATE/DELETE)
    """
    if fetch == "all":
        return fetch_all(query, params)
    elif fetch == "one":
        return fetch_one(query, params)
    else:
        return execute(query, params)
