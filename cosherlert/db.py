import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime
from cosherlert import config

DDL = """
CREATE TABLE IF NOT EXISTS users (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    phone      TEXT NOT NULL UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    active     INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER REFERENCES users(id),
    zone       TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, zone)
);

CREATE TABLE IF NOT EXISTS alert_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    oref_id       TEXT NOT NULL,
    cat           TEXT NOT NULL,
    zones         TEXT NOT NULL,
    dispatched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    recipients    INTEGER DEFAULT 0
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_alert_log_oref_id ON alert_log(oref_id);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(DDL)


def upsert_user(phone: str) -> int:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (phone) VALUES (?)", (phone,)
        )
        conn.execute("UPDATE users SET active=1 WHERE phone=?", (phone,))
        row = conn.execute("SELECT id FROM users WHERE phone=?", (phone,)).fetchone()
        return row["id"]


def add_subscription(phone: str, zone: str):
    user_id = upsert_user(phone)
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO subscriptions (user_id, zone) VALUES (?,?)",
            (user_id, zone),
        )


def remove_all_subscriptions(phone: str):
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM users WHERE phone=?", (phone,)).fetchone()
        if row:
            conn.execute("DELETE FROM subscriptions WHERE user_id=?", (row["id"],))
            conn.execute("UPDATE users SET active=0 WHERE id=?", (row["id"],))


def get_subscribers_for_zones(zones: list[str]) -> list[str]:
    if not zones:
        return []
    placeholders = ",".join("?" * len(zones))
    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT DISTINCT u.phone
            FROM users u
            JOIN subscriptions s ON s.user_id = u.id
            WHERE u.active=1 AND s.zone IN ({placeholders})
            """,
            zones,
        ).fetchall()
    return [r["phone"] for r in rows]


def get_subscriptions_for_phone(phone: str) -> list[str]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT s.zone FROM subscriptions s
            JOIN users u ON u.id = s.user_id
            WHERE u.phone=? AND u.active=1
            """,
            (phone,),
        ).fetchall()
    return [r["zone"] for r in rows]


def already_dispatched(oref_id: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM alert_log WHERE oref_id=?", (oref_id,)
        ).fetchone()
    return row is not None


def log_dispatch(oref_id: str, cat: str, zones: list[str], recipients: int):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO alert_log (oref_id, cat, zones, recipients) VALUES (?,?,?,?)",
            (oref_id, cat, json.dumps(zones, ensure_ascii=False), recipients),
        )
