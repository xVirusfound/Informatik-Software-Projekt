# main.py
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QListWidget
from PyQt5.QtCore import Qt
from PyQt5 import QtSql
from PyQt5.QtSql import QSqlDatabase, QSqlQuery
import sqlite3

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Test App: Button + Counter")
        self.resize(300, 80)

        layout = QVBoxLayout()
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        self.setLayout(layout)

        self.lade_gewohnheiten #soll das eher in die init funktion?

    def lade_gewohnheiten(self):
        # Verbindung zur DB
        conn = sqlite3.connect("datenbank.db")
        c = conn.cursor()

        c.execute("SELECT name FROM gewohnheit")
        zeilen = c.fetchall()

        # Liste mit Items füllen
        self.list_widget.clear()
        for (name,) in zeilen:
            self.list_widget.addItem(name)

        conn.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
