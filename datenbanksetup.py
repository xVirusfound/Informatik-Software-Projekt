import sqlite3

def setup_test_database():
    conn = sqlite3.connect("datenbank.db")
    c = conn.cursor()
    
    # UNIQUE sorgt dafür, dass Namen nicht doppelt gespeichert werden
    c.execute("CREATE TABLE IF NOT EXISTS gewohnheit (id INTEGER PRIMARY KEY, name TEXT UNIQUE, beschreibung TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS maßnahme (id INTEGER PRIMARY KEY, name TEXT, gewohnheit_id INTEGER, erledigt INTEGER DEFAULT 0)")
    
    habits = [
        ('Sport machen', 'Jeden zweiten Tag trainieren.'),
        ('Gesund essen', 'Mehr Gemüse, weniger Zucker.'),
        ('Früh aufstehen', 'Ziel: 06:00 Uhr aufstehen.'),
        ('Nicht Doom Scrollen', 'Kein TikTok vor dem Schlafen.')
    ]

    for name, desc in habits:
        try:
            c.execute("INSERT INTO gewohnheit (name, beschreibung) VALUES (?, ?)", (name, desc))
        except sqlite3.IntegrityError:
            pass # Falls Name schon existiert, wird er übersprungen
    
    conn.commit()
    conn.close()