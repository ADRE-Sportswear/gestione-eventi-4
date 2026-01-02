# app/seed_data.py
from db import insert_artist, insert_format, init_db, list_artists
from db import get_conn
import sqlite3

def seed():
    init_db()
    # check if artists exist
    from db import list_artists
    if list_artists():
        return
    insert_artist("The Swingers", ["band"], "swingers@agency.it")
    insert_artist("Luna Mascotte", ["mascotte"], "luna@agency.it")
    insert_artist("Vocalist A", ["vocalist"], "vocal@agency.it")
    insert_format("Cabaret", "#ff7f0e")
    insert_format("Concert", "#2ca02c")
    insert_format("Kids Show", "#1f77b4")
