"""
Database access for the Module 4 Admin Dashboard.

One connection is opened lazily per request (stored on flask.g) and closed when
the request ends, so a stale global connection can never be reused. Every
helper closes its cursor, and every query takes parameters separately from the
SQL text.
"""
import mysql.connector
from mysql.connector import errorcode
from flask import current_app, g

# Tables/columns Module 4 relies on. The first four belong to the main
# Waste2Value application (Modules 1-3); the last three are owned by Module 4.
EXPECTED_SCHEMA = {
    "users": ["id", "name", "email", "password_hash", "role", "created_at"],
    "listings": ["id", "seller_id", "title", "category", "description", "price",
                 "item_condition", "image_path", "status", "created_at"],
    "offers": ["id", "listing_id", "buyer_id", "offer_price", "status", "created_at"],
    "pickups": ["id", "offer_id", "address", "pickup_date", "status", "created_at"],
    "admins": ["id", "username", "password_hash", "created_at"],
    "recyclers": ["id", "recycler_name", "company", "location", "status"],
    "complaints": ["id", "user_id", "subject", "description", "status", "created_at"],
}

MISSING_SCHEMA_ERRNOS = (errorcode.ER_NO_SUCH_TABLE, errorcode.ER_BAD_FIELD_ERROR)


def get_db():
    if "db" not in g:
        cfg = current_app.config
        g.db = mysql.connector.connect(
            host=cfg["DB_HOST"],
            port=cfg["DB_PORT"],
            user=cfg["DB_USER"],
            password=cfg["DB_PASSWORD"],
            database=cfg["DB_NAME"],
            connection_timeout=10,
        )
    return g.db


def close_db(exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        try:
            conn.close()
        except mysql.connector.Error:
            pass


def init_app(app):
    app.teardown_appcontext(close_db)


def query_all(sql, params=()):
    cur = get_db().cursor(dictionary=True, buffered=True)
    try:
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        cur.close()


def query_one(sql, params=()):
    cur = get_db().cursor(dictionary=True, buffered=True)
    try:
        cur.execute(sql, params)
        return cur.fetchone()
    finally:
        cur.close()


def execute(sql, params=()):
    """Run a single write statement in its own transaction; returns affected row count."""
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute(sql, params)
        conn.commit()
        return cur.rowcount
    except mysql.connector.Error:
        conn.rollback()
        raise
    finally:
        cur.close()


def is_missing_schema_error(err):
    return getattr(err, "errno", None) in MISSING_SCHEMA_ERRNOS


def is_duplicate_error(err):
    return getattr(err, "errno", None) == errorcode.ER_DUP_ENTRY


def is_fk_error(err):
    return getattr(err, "errno", None) in (errorcode.ER_ROW_IS_REFERENCED_2,
                                           errorcode.ER_ROW_IS_REFERENCED)


def like_pattern(term):
    """Build a LIKE pattern that matches `term` literally anywhere in a column."""
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def check_schema():
    """Compare the connected database against EXPECTED_SCHEMA (read-only)."""
    rows = query_all(
        "SELECT TABLE_NAME AS table_name, COLUMN_NAME AS column_name "
        "FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE()"
    )
    present = {}
    for row in rows:
        present.setdefault(row["table_name"].lower(), set()).add(row["column_name"].lower())

    report = {}
    for table, columns in EXPECTED_SCHEMA.items():
        existing = present.get(table)
        report[table] = {
            "exists": existing is not None,
            "missing_columns": [] if existing is None else [c for c in columns if c not in existing],
        }
    return report
