# -*- coding: utf-8 -*-
"""SQLite data layer: schema + per-call connections (WAL, thread-safe)."""
import sqlite3
import os
import threading

_DB_DEFAULT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "demo.db")
DB_PATH = os.environ.get("DEMO_DB_PATH", _DB_DEFAULT)
_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL, type TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active',
  deadline TEXT, created_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS contents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL,
  type TEXT NOT NULL,                    -- invitation | article
  title TEXT DEFAULT '',
  body_json TEXT DEFAULT '{}',           -- structured output
  params_json TEXT DEFAULT '{}',         -- generation inputs
  status TEXT NOT NULL DEFAULT 'draft',  -- draft/generating/pending_supervisor/pending_revision/pending_boss/confirmed/distributed
  version INTEGER NOT NULL DEFAULT 1,
  used_preference_ids_json TEXT DEFAULT '[]',
  generation_meta_json TEXT DEFAULT '{}',
  created_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS channel_versions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  content_id INTEGER NOT NULL,
  channel TEXT NOT NULL,                 -- wechat_mp/website/channels/xhs/linkedin
  copy_json TEXT DEFAULT '{}',
  spec_json TEXT DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'ready',
  created_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS reviews (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  content_id INTEGER NOT NULL,
  reviewer_role TEXT NOT NULL,           -- supervisor | boss
  action TEXT NOT NULL,                  -- approve | reject
  feedback_text TEXT DEFAULT '',
  round INTEGER NOT NULL DEFAULT 1,
  created_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS preference_rules (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT NOT NULL,                    -- P01...
  category TEXT NOT NULL,                -- 色彩/风格/排版/内容/标杆
  rule_text TEXT NOT NULL,
  confidence REAL NOT NULL DEFAULT 0.9,
  status TEXT NOT NULL DEFAULT 'active', -- pending/active/disabled
  source_note TEXT DEFAULT '',
  source_review_id INTEGER,
  evidence TEXT DEFAULT '',
  created_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  payload_json TEXT DEFAULT '{}',
  created_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL, platform TEXT NOT NULL,
  persona TEXT DEFAULT '', persona_key TEXT DEFAULT 'engineer',
  followers INTEGER DEFAULT 0, owner TEXT DEFAULT '', auth_status TEXT DEFAULT 'authorized',
  config_json TEXT DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS content_packages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  content_id INTEGER NOT NULL, account_id INTEGER NOT NULL,
  copy_text TEXT DEFAULT '', image_url TEXT DEFAULT '',
  tags_json TEXT DEFAULT '[]', suggest_time TEXT DEFAULT '',
  status TEXT NOT NULL DEFAULT 'draft',
  created_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS publish_receipts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  package_id INTEGER NOT NULL, link TEXT DEFAULT '', note TEXT DEFAULT '',
  reach INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_contents_status ON contents(status);
CREATE INDEX IF NOT EXISTS idx_reviews_content ON reviews(content_id);
CREATE INDEX IF NOT EXISTS idx_pref_status ON preference_rules(status);
"""


def connect():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    with _lock:
        conn = connect()
        try:
            conn.executescript(SCHEMA)
            try:
                conn.execute("ALTER TABLE accounts ADD COLUMN config_json TEXT DEFAULT '{}'")
            except Exception:
                pass  # column already exists
            conn.commit()
        finally:
            conn.close()


def query(sql, args=()):
    conn = connect()
    try:
        return [dict(r) for r in conn.execute(sql, args).fetchall()]
    finally:
        conn.close()


def query_one(sql, args=()):
    rows = query(sql, args)
    return rows[0] if rows else None


def execute(sql, args=()):
    with _lock:
        conn = connect()
        try:
            cur = conn.execute(sql, args)
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()


def drop_all():
    with _lock:
        conn = connect()
        try:
            for t in ("events", "preference_rules", "reviews", "channel_versions", "contents", "projects", "content_packages", "publish_receipts", "accounts"):
                conn.execute(f"DROP TABLE IF EXISTS {t}")
            conn.commit()
        finally:
            conn.close()
