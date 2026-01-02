# app/db.py
import sqlite3
from typing import List, Dict, Any
import json
from datetime import datetime

DB_PATH = "db/events.db"

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT
);

CREATE TABLE IF NOT EXISTS artists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    role_tags TEXT, -- JSON array of tags
    contact TEXT
);

CREATE TABLE IF NOT EXISTS formats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    color TEXT DEFAULT '#2b8cbe'
);

CREATE TABLE IF NOT EXISTS promoters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    contact TEXT
);

CREATE TABLE IF NOT EXISTS tour_managers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    contact TEXT
);

CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    date TEXT NOT NULL, -- ISO date YYYY-MM-DD
    format_id INTEGER,
    artist_ids TEXT, -- JSON array of artist ids
    promoter_id INTEGER,
    tour_manager_id INTEGER,
    services_json TEXT,
    notes TEXT,
    status TEXT DEFAULT 'planned',
    last_modified TEXT,
    FOREIGN KEY(format_id) REFERENCES formats(id),
    FOREIGN KEY(promoter_id) REFERENCES promoters(id),
    FOREIGN KEY(tour_manager_id) REFERENCES tour_managers(id)
);
"""

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript(SCHEMA)
    conn.commit()
    conn.close()

# Generic helpers
def row_to_dict(row):
    if row is None:
        return None
    d = dict(row)
    # parse JSON fields
    for k in ("artist_ids","services_json"):
        if k in d and d[k]:
            try:
                d[k] = json.loads(d[k])
            except:
                d[k] = d[k]
    return d

# CRUD: Users
def create_user(email, password_hash, name=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (email,password_hash,name) VALUES (?,?,?)",
                (email, password_hash, name))
    conn.commit()
    conn.close()

def get_user_by_email(email):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cur.fetchone()
    conn.close()
    return row_to_dict(row)

# CRUD: Artists / Formats / Promoters / Services
def insert_artist(name, role_tags=None, contact=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO artists (name, role_tags, contact) VALUES (?,?,?)",
                (name, json.dumps(role_tags or []), contact))
    conn.commit()
    conn.close()

def list_artists():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM artists ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]

def insert_format(name, color="#2b8cbe"):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO formats (name, color) VALUES (?,?)", (name, color))
    conn.commit()
    conn.close()

def list_formats():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM formats ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]

def list_events(date_from=None, date_to=None, artist_ids:List[int]=None, format_ids:List[int]=None):
    conn = get_conn()
    cur = conn.cursor()
    q = "SELECT * FROM events WHERE 1=1"
    params = []
    if date_from:
        q += " AND date >= ?"
        params.append(date_from)
    if date_to:
        q += " AND date <= ?"
        params.append(date_to)
    cur.execute(q, params)
    rows = cur.fetchall()
    events = []
    for r in rows:
        d = row_to_dict(r)
        # filter by artist/format in Python for simplicity
        if artist_ids:
            a_ids = d.get("artist_ids") or []
            if not any(int(x) in artist_ids for x in a_ids):
                continue
        if format_ids:
            if d.get("format_id") is None or int(d.get("format_id")) not in format_ids:
                continue
        events.append(d)
    conn.close()
    return events

def get_event(event_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM events WHERE id = ?", (event_id,))
    row = cur.fetchone()
    conn.close()
    return row_to_dict(row)

def upsert_event(event:Dict[str,Any]):
    conn = get_conn()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    if event.get("id"):
        cur.execute("""
            UPDATE events SET title=?, date=?, format_id=?, artist_ids=?, promoter_id=?, tour_manager_id=?, services_json=?, notes=?, status=?, last_modified=?
            WHERE id=?
        """, (
            event["title"],
            event["date"],
            event.get("format_id"),
            json.dumps(event.get("artist_ids") or []),
            event.get("promoter_id"),
            event.get("tour_manager_id"),
            json.dumps(event.get("services_json") or []),
            event.get("notes"),
            event.get("status","planned"),
            now,
            event["id"]
        ))
    else:
        cur.execute("""
            INSERT INTO events (title,date,format_id,artist_ids,promoter_id,tour_manager_id,services_json,notes,status,last_modified)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            event["title"],
            event["date"],
            event.get("format_id"),
            json.dumps(event.get("artist_ids") or []),
            event.get("promoter_id"),
            event.get("tour_manager_id"),
            json.dumps(event.get("services_json") or []),
            event.get("notes"),
            event.get("status","planned"),
            now
        ))
    conn.commit()
    conn.close()

def delete_event(event_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM events WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()
