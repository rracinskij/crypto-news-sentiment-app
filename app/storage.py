# Version: v0.1.0

"""
LLM-friendly description:
- Purpose: Tiny SQLite layer for the demo app. It stores RSS articles, logs, LLM prompts/responses,
  and structured sentiment predictions.
- Tables (all created on import via ensure_tables):
  - articles(id, title, link UNIQUE, source, published_ts, published_str, description, content, content_encoded)
  - logs(id, ts, source, text)
  - predictions(id, ts, horizon_minutes, model, raw_json, text)
  - prediction_items(id, ts, horizon_minutes, model, asset, stance, text)
  - llm_queries(id, ts, model, prompt, response, tokens_used, duration_ms)
- Notes:
  - `published_ts` is a Unix timestamp for filtering; `published_str` keeps human-readable time from the feed.
  - Use `get_latest_article_time(source)` to implement "collect 24h if none before, else uncollected since last seen".
"""
import os, sqlite3, time
from contextlib import contextmanager
from typing import Iterable, Dict, List, Optional, Tuple

DB_PATH = os.environ.get("APP_DB_PATH", os.path.join(os.path.dirname(__file__), "..", "data", "app.db"))

@contextmanager
def get_conn(db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    try:
        yield conn
    finally:
        conn.commit()
        conn.close()

def ensure_tables(db_path: str = DB_PATH) -> None:
    with get_conn(db_path) as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS articles(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            link TEXT NOT NULL UNIQUE,
            source TEXT NOT NULL,
            published_ts INTEGER NOT NULL,
            published_str TEXT,
            description TEXT,
            content TEXT,
            content_encoded TEXT
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS logs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER NOT NULL,
            source TEXT NOT NULL,
            text TEXT NOT NULL
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS predictions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER NOT NULL,
            horizon_minutes INTEGER NOT NULL,
            model TEXT,
            raw_json TEXT,
            text TEXT
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS prediction_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER NOT NULL,
            horizon_minutes INTEGER NOT NULL,
            model TEXT,
            asset TEXT NOT NULL,
            stance TEXT NOT NULL,
            text TEXT NOT NULL
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS llm_queries(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER NOT NULL,
            model TEXT NOT NULL,
            prompt TEXT NOT NULL,
            response TEXT NOT NULL,
            tokens_used INTEGER,
            duration_ms INTEGER
        )""")

def add_log(source: str, text: str) -> int:
    ensure_tables(DB_PATH)
    with get_conn(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO logs(ts, source, text) VALUES(?,?,?)", (int(time.time()), source, text))
        return c.lastrowid

def get_latest_article_time(source: str) -> Optional[int]:
    ensure_tables(DB_PATH)
    with get_conn(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT MAX(published_ts) FROM articles WHERE source=?", (source,))
        row = c.fetchone()
        return int(row[0]) if row and row[0] is not None else None

def save_articles(articles: Iterable[Dict]) -> int:
    """Insert-or-ignore by link to prevent duplicates."""
    ensure_tables(DB_PATH)
    n = 0
    with get_conn(DB_PATH) as conn:
        c = conn.cursor()
        for a in articles:
            try:
                c.execute(
                    """INSERT OR IGNORE INTO articles
                       (title, link, source, published_ts, published_str, description, content, content_encoded)
                       VALUES(?,?,?,?,?,?,?,?)""",
                    (a.get("title","").strip(),
                     a.get("link","").strip(),
                     a.get("source","").strip(),
                     int(a.get("published_ts", 0)),
                     a.get("published_str"),
                     a.get("description"),
                     a.get("content"),
                     a.get("content_encoded"))
                )
                n += c.rowcount
            except Exception as e:
                add_log("db", f"error inserting article: {e}")
    return n

def list_recent_articles(hours: int = 24, limit: int = 200) -> List[Tuple]:
    min_ts = int(time.time()) - hours * 3600
    with get_conn(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            SELECT title, link, source, published_str, substr(coalesce(description, content, content_encoded, ''), 1, 300)
            FROM articles
            WHERE published_ts >= ?
            ORDER BY published_ts DESC
            LIMIT ?
        """, (min_ts, int(limit)))
        return c.fetchall()

def add_prediction(horizon_minutes: int, model: str, raw_json: str, text: str) -> int:
    ensure_tables(DB_PATH)
    with get_conn(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO predictions(ts, horizon_minutes, model, raw_json, text) VALUES(?,?,?,?,?)",
                  (int(time.time()), int(horizon_minutes), model, raw_json, text))
        return c.lastrowid

def add_prediction_item(horizon_minutes: int, model: str, asset: str, stance: str, text: str) -> int:
    ensure_tables(DB_PATH)
    with get_conn(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO prediction_items(ts, horizon_minutes, model, asset, stance, text) VALUES(?,?,?,?,?,?)",
                  (int(time.time()), int(horizon_minutes), model, asset, stance, text))
        return c.lastrowid

def add_llm_query(model: str, prompt: str, response: str, tokens_used: int = None, duration_ms: int = None) -> int:
    ensure_tables(DB_PATH)
    with get_conn(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO llm_queries(ts, model, prompt, response, tokens_used, duration_ms) VALUES(?,?,?,?,?,?)",
                  (int(time.time()), model, prompt, response, tokens_used, duration_ms))
        return c.lastrowid

def list_prediction_items(limit: int = 200) -> List[Tuple]:
    with get_conn(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
          SELECT ts, model, horizon_minutes, asset, stance, text
          FROM prediction_items ORDER BY id DESC LIMIT ?
        """, (int(limit),))
        return c.fetchall()

def list_llm_queries(limit: int = 100) -> List[Tuple]:
    with get_conn(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
          SELECT ts, model, prompt, response, tokens_used, duration_ms
          FROM llm_queries ORDER BY id DESC LIMIT ?
        """, (int(limit),))
        return c.fetchall()
