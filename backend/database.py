import sqlite3

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
        last_checked TEXT
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
        message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


# ---------------- CRUD ----------------

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
    conn.commit()
    conn.close()


def update_status(site_id, status, response_time, ssl_days, domain_days, hosting=None):
    conn = get_connection()
    conn.execute("""
        UPDATE websites
        SET status=?, response_time_ms=?, ssl_days=?, domain_days=?, hosting=?, last_checked=datetime('now')
        WHERE id=?
    """, (status, response_time, ssl_days, domain_days, hosting, site_id))
    conn.commit()
    conn.close()