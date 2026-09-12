import sqlite3
import json

DB_NAME = "monitor.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS websites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        url TEXT UNIQUE,
        status TEXT DEFAULT 'PENDING',
        response_time_ms INTEGER,
        ssl_days INTEGER,
        domain_days INTEGER,
        hosting TEXT,
        last_checked TEXT,
        last_ssl_check TEXT,
        last_domain_check TEXT,
        last_hosting_check TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        site_id INTEGER,
        status TEXT,
        response_time INTEGER,
        ssl_days INTEGER,
        domain_days INTEGER,
        attempts TEXT,
        message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    try:
        conn.execute("ALTER TABLE logs ADD COLUMN attempts TEXT")
    except Exception:
        pass

    conn.commit()
    conn.close()

def is_valid_hosting(val):
    if not val:
        return False
    val = val.lower()
    bad = ["unknown", "n/a", "redacted", "privacy", "proxy"]
    return not any(b in val for b in bad)

def get_all_sites():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM websites").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_site(name, url):
    conn = get_connection()
    try:
        conn.execute("INSERT INTO websites (name, url) VALUES (?, ?)", (name, url))
        conn.commit()
    except:
        pass
    conn.close()


def delete_site(site_id):
    conn = get_connection()
    conn.execute("DELETE FROM websites WHERE id = ?", (site_id,))
    conn.execute("DELETE FROM logs WHERE site_id = ?", (site_id,))
    conn.commit()
    conn.close()


def update_status(
    site_id,
    status,
    response_time,
    ssl_days,
    domain_days,
    hosting,
    ssl_updated=False,
    domain_updated=False,
    hosting_updated=False,
    attempts=None
):
    conn = get_connection()

    existing = conn.execute(
        "SELECT ssl_days, domain_days, hosting FROM websites WHERE id=?",
        (site_id,)
    ).fetchone()

    if not existing:
        conn.close()
        return

    # -------- Preserve values --------
    ssl_final = ssl_days if (ssl_updated or existing["ssl_days"] is None) and ssl_days is not None else existing["ssl_days"]
    domain_final = domain_days if (domain_updated or existing["domain_days"] is None) and domain_days is not None else existing["domain_days"]

    hosting_final = existing["hosting"]
    if (hosting_updated or not existing["hosting"]) and is_valid_hosting(hosting):
        hosting_final = hosting

    # -------- Update DB --------
    conn.execute("""
        UPDATE websites
        SET status=?,
            response_time_ms=?,
            ssl_days=?,
            domain_days=?,
            hosting=?,
            last_checked=datetime('now'),
            last_ssl_check=CASE WHEN ? THEN datetime('now') ELSE last_ssl_check END,
            last_domain_check=CASE WHEN ? THEN datetime('now') ELSE last_domain_check END,
            last_hosting_check=CASE WHEN ? THEN datetime('now') ELSE last_hosting_check END
        WHERE id=?
    """, (
        status,
        response_time,
        ssl_final,
        domain_final,
        hosting_final,
        ssl_updated,
        domain_updated,
        hosting_updated,
        site_id
    ))

    # -------- Insert Log Record --------
    attempts_str = json.dumps(attempts) if attempts else None
    msg = f"Check completed: {status} ({response_time} ms)" if response_time else f"Check completed: {status}"

    conn.execute("""
        INSERT INTO logs (site_id, status, response_time, ssl_days, domain_days, attempts, message, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """, (
        site_id,
        status,
        response_time,
        ssl_final,
        domain_final,
        attempts_str,
        msg
    ))

    conn.commit()
    conn.close()