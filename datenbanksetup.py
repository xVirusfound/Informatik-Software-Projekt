import sqlite3

conn = sqlite3.connect("datenbank.db")
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS gewohnheit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    beschreibung TEXT
)
""")

habit_data = [
    ("Früh aufstehen", "Jeden Morgen"),
    ("Lesen", "Täglich 10 Minuten"),
    ("Sport", "3× pro Woche")
]

c.executemany("INSERT INTO gewohnheit (name, beschreibung) VALUES (?, ?)", habit_data)

conn.commit()
conn.close()
