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

c.execute("""
CREATE TABLE IF NOT EXISTS maßnahme (
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

maßnahmen_data = [
    ("QR-Code Wecker", "QR-Code im Bad -> muss dahin laufen"),
    ("Buch auf den Tisch legen", "immer wenn ich schlafen gehe, damit ich es am Morgen in die Schule nehme"),
    ("Cooles Schweißband kaufen", "Schweißband kaufen und immer beim Sport tragen")]

c.executemany("INSERT INTO gewohnheit (name, beschreibung) VALUES (?, ?)", habit_data)
c.executemany("INSERT INTO maßnahme (name, beschreibung) VALUES (?, ?)", maßnahmen_data)

conn.commit()
conn.close()
