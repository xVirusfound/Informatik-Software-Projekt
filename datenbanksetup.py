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

    #erzeugt gewohnheitentabelle
    c.execute("""
        CREATE TABLE IF NOT EXISTS gewohnheit (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE,
            beschreibung TEXT
        )
    """)
    #erzeugt maßnahmentabelle
    c.execute("""
        CREATE TABLE IF NOT EXISTS maßnahme (
            id INTEGER PRIMARY KEY,
            name TEXT,
            gewohnheit_id INTEGER,
            erledigt INTEGER DEFAULT 0
        )
    """)

    # erzeugt tabele für historische einträge
    c.execute("""
        CREATE TABLE IF NOT EXISTS gewohnheit_historie (
            id INTEGER PRIMARY KEY,
            gewohnheit_id INTEGER NOT NULL,
            datum TEXT NOT NULL,
            status INTEGER NOT NULL CHECK (status IN (0,1)),
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT,
            UNIQUE(gewohnheit_id, datum),
            FOREIGN KEY (gewohnheit_id) REFERENCES gewohnheit(id) ON DELETE CASCADE
        )
    """)

    c.execute("CREATE INDEX IF NOT EXISTS idx_gew_hist_gew_datum ON gewohnheit_historie(gewohnheit_id, datum)")

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

