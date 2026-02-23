import os
import sqlite3

# Bestimmt den Pfad zur Datenbank im gleichen Ordner wie dieses Skript
DB_PATH = os.path.join(os.path.dirname(__file__), "datenbank.db")

def get_conn():
    """Baut die Verbindung zur SQLite-Datenbank auf und aktiviert Fremdschlüssel."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def setup_test_database():
    """Erstellt alle benötigten Tabellen, falls sie noch nicht existieren."""
    conn = get_conn()
    c = conn.cursor()

    # 1. Tabelle für Gewohnheiten
    c.execute("""
        CREATE TABLE IF NOT EXISTS gewohnheit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            beschreibung TEXT,
            score INTEGER DEFAULT 0,
            status TEXT DEFAULT 'wip'
        )
    """)

    # 2. Tabelle für Maßnahmen
    # HIER ist die neue Spalte 'effektivitaet' (1-5) und 'beschreibung' enthalten
    c.execute("""
        CREATE TABLE IF NOT EXISTS maßnahme (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            gewohnheit_id INTEGER,
            beschreibung TEXT,
            effektivitaet INTEGER DEFAULT 3,
            FOREIGN KEY(gewohnheit_id) REFERENCES gewohnheit(id)
        )
    """)

    # 3. Tabelle für Todos (die an Maßnahmen hängen)
    c.execute("""
        CREATE TABLE IF NOT EXISTS todo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titel TEXT NOT NULL,
            beschreibung TEXT,
            massnahme_id INTEGER,
            FOREIGN KEY(massnahme_id) REFERENCES maßnahme(id)
        )
    """)

    # 4. Tabelle für die Kalender-Historie der Gewohnheiten
    c.execute("""
        CREATE TABLE IF NOT EXISTS gewohnheit_historie (
            gewohnheit_id INTEGER,
            datum TEXT,
            status INTEGER,
            created_at TEXT,
            updated_at TEXT,
            PRIMARY KEY (gewohnheit_id, datum),
            FOREIGN KEY(gewohnheit_id) REFERENCES gewohnheit(id)
        )
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    setup_test_database()
    print("Datenbank-Setup erfolgreich: Alle Tabellen (inkl. Effektivität) sind bereit.")