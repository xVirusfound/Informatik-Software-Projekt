import os
import sqlite3

# DB immer im Projektordner (bei dieser Datei), nicht abhängig vom Startordner
DB_PATH = os.path.join(os.path.dirname(__file__), "datenbank.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def setup_test_database():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS gewohnheit (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE,
            beschreibung TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS maßnahme (
            id INTEGER PRIMARY KEY,
            name TEXT,
            gewohnheit_id INTEGER,
            erledigt INTEGER DEFAULT 0
        )
    """)

    # Defaults nur einfügen, wenn Tabelle leer ist
    c.execute("SELECT COUNT(*) FROM gewohnheit")
    count = c.fetchone()[0]

    if count == 0:
        habits = [
            ('Sport machen', 'Jeden zweiten Tag trainieren.'),
            ('Gesund essen', 'Mehr Gemüse, weniger Zucker.'),
            ('Früh aufstehen', 'Ziel: 06:00 Uhr aufstehen.'),
            ('Nicht Doom Scrollen', 'Kein TikTok vor dem Schlafen.')
        ]
        c.executemany(
            "INSERT INTO gewohnheit (name, beschreibung) VALUES (?, ?)",
            habits
        )

    conn.commit()
    conn.close()

