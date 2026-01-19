# main.py
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, QListWidget, QStackedWidget
from PyQt5.QtCore import Qt
from PyQt5 import QtSql
from PyQt5.QtSql import QSqlDatabase, QSqlQuery
import sqlite3

class GewohnheitenAnsicht(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.list_widget_gewohnheit = QListWidget()
        layout.addWidget(self.list_widget_gewohnheit)
        self.lade_gewohnheiten()

    def lade_gewohnheiten(self):
        # Verbindung zur DB
        conn = sqlite3.connect("datenbank.db")
        c = conn.cursor()
        c.execute("SELECT name FROM gewohnheit")
        zeilen = c.fetchall()
        # Liste mit Items füllen
        self.list_widget_gewohnheit.clear()
        for (name,) in zeilen:
            self.list_widget_gewohnheit.addItem(name)

        conn.close()

class MaßnahmenAnsicht(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.list_widget_maßnahme = QListWidget()
        layout.addWidget(self.list_widget_maßnahme)
        self.lade_maßnahmen()

    def lade_maßnahmen(self):
        # Verbindung zur DB
        conn = sqlite3.connect("datenbank.db")
        c = conn.cursor()
        c.execute("SELECT name FROM maßnahme")
        zeilen = c.fetchall()
        # Liste mit Items füllen
        self.list_widget_maßnahme.clear()
        for (name,) in zeilen:
            self.list_widget_maßnahme.addItem(name)
        conn.close()

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.btn_gewohnheiten = QPushButton("Gewohnheiten")
        self.btn_maßnahmen = QPushButton("Maßnahmen")
        self.init_ui()

        self.btn_gewohnheiten.clicked.connect(
            lambda: self.stack.setCurrentIndex(0))
        self.btn_maßnahmen.clicked.connect(
            lambda: self.stack.setCurrentIndex(1))
    def init_ui(self):
        self.setWindowTitle("Test App: Button + Counter")
        self.resize(300, 80)
        self.stack = QStackedWidget()
        self.stack.addWidget(GewohnheitenAnsicht())
        self.stack.addWidget(MaßnahmenAnsicht())

        sidebar_layout = QVBoxLayout()
        sidebar_layout.addWidget(self.btn_gewohnheiten)
        sidebar_layout.addWidget(self.btn_maßnahmen)
        sidebar_layout.addStretch()

        main_layout = QHBoxLayout(self)
        main_layout.addLayout(sidebar_layout)
        main_layout.addWidget(self.stack)
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
