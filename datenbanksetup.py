import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QHBoxLayout
from PyQt5.QtCore import Qt
from PyQt5 import QtSql
from PyQt5.QtSql import QSqlDatabase, QSqlQuery
import sqlite3

# Verbindung öffnen (legt Datei an, falls nicht existiert)
conn = sqlite3.connect("datenbank.db")
c = conn.cursor()

# Tabelle Gewohnheit erstellen
c.execute("""
CREATE TABLE IF NOT EXISTS gewohnheit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    beschreibung TEXT
)
""")

conn.commit()

print("Datenbank & Tabelle erstellt!")

# Beispiel-Daten einfügen
habit_data = [
    ("Früh aufstehen", "Jeden Morgen vor 7 Uhr"),
    ("10 Minuten lesen", "Täglich vorm Schlafengehen"),
    ("Spazieren gehen", "Mind. 30 Minuten täglich")
]

c.executemany("INSERT INTO gewohnheit (name, beschreibung) VALUES (?, ?)", habit_data)

conn.commit()
conn.close()
