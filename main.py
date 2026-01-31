import sys
import sqlite3
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QLabel, 
                             QVBoxLayout, QHBoxLayout, QListWidget, 
                             QStackedWidget, QTextEdit, QListWidgetItem,
                             QCalendarWidget)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from datenbanksetup import setup_test_database

# --- Ansichten ---

class GewohnheitenAnsicht(QWidget):
    habit_clicked = pyqtSignal(str) 

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.list_widget_gewohnheit = QListWidget()
        layout.addWidget(self.list_widget_gewohnheit)
        
        self.list_widget_gewohnheit.itemClicked.connect(self.on_item_clicked)
        self.lade_gewohnheiten()

    def lade_gewohnheiten(self):
        conn = sqlite3.connect("datenbank.db")
        c = conn.cursor()
        c.execute("SELECT name FROM gewohnheit")
        zeilen = c.fetchall()
        self.list_widget_gewohnheit.clear()
        for (name,) in zeilen:
            self.list_widget_gewohnheit.addItem(name)
        conn.close()

    def on_item_clicked(self, item):
        self.habit_clicked.emit(item.text())

class MaßnahmenAnsicht(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        label = QLabel("Alle Maßnahmen (Gesamtübersicht)")
        layout.addWidget(label)
        self.list_widget_maßnahme = QListWidget()
        layout.addWidget(self.list_widget_maßnahme)
        self.lade_maßnahmen()

    def lade_maßnahmen(self):
        conn = sqlite3.connect("datenbank.db")
        c = conn.cursor()
        c.execute("SELECT name FROM maßnahme")
        zeilen = c.fetchall()
        self.list_widget_maßnahme.clear()
        for (name,) in zeilen:
            self.list_widget_maßnahme.addItem(name)
        conn.close()

class DetailAnsicht(QWidget):
    back_clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.current_habit_name = None
        
        layout = QVBoxLayout(self)

        # --- 1. Header ---
        header_layout = QHBoxLayout()
        self.btn_back = QPushButton("←")
        self.btn_back.setFixedSize(40, 40)
        self.btn_back.clicked.connect(self.back_clicked.emit)
        header_layout.addWidget(self.btn_back)

        self.lbl_title = QLabel("Habit Name")
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        self.lbl_title.setFont(font)
        header_layout.addWidget(self.lbl_title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # --- 2. Beschreibung ---
        layout.addWidget(QLabel("Beschreibung:"))
        self.txt_beschreibung = QTextEdit()
        self.txt_beschreibung.setMaximumHeight(80)
        self.txt_beschreibung.setPlaceholderText("Beschreibung eingeben...")
        layout.addWidget(self.txt_beschreibung)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_save_desc = QPushButton("Beschreibung speichern")
        self.btn_save_desc.setFixedWidth(150)
        self.btn_save_desc.clicked.connect(self.speichere_beschreibung)
        btn_layout.addWidget(self.btn_save_desc)
        layout.addLayout(btn_layout)

        # --- 3. Hauptbereich (Maßnahmen links + Kalender rechts) ---
        content_layout = QHBoxLayout()

        # LINKS: Maßnahmen Liste
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Maßnahmen (Abhaken):"))
        self.list_details = QListWidget()
        self.list_details.itemChanged.connect(self.on_measure_changed)
        left_layout.addWidget(self.list_details)
        content_layout.addLayout(left_layout, stretch=1) 

        # RECHTS: Kalender
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Kalender:"))
        
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setMaximumSize(350, 250) 
        
        right_layout.addWidget(self.calendar, alignment=Qt.AlignTop)
        
        content_layout.addLayout(right_layout, stretch=1)

        layout.addLayout(content_layout)

    def set_habit(self, habit_name):
        self.current_habit_name = habit_name
        self.lbl_title.setText(habit_name)
        self.lade_daten(habit_name)

    def lade_daten(self, habit_name):
        conn = sqlite3.connect("datenbank.db")
        c = conn.cursor()
        
        c.execute("SELECT beschreibung FROM gewohnheit WHERE name = ?", (habit_name,))
        result = c.fetchone()
        if result and result[0]:
            self.txt_beschreibung.setText(result[0])
        else:
            self.txt_beschreibung.clear()

        query = """
        SELECT m.id, m.name, m.erledigt 
        FROM maßnahme m
        JOIN gewohnheit g ON m.gewohnheit_id = g.id
        WHERE g.name = ?
        """
        c.execute(query, (habit_name,))
        zeilen = c.fetchall()
        
        self.list_details.blockSignals(True)
        self.list_details.clear()
        
        if not zeilen:
            self.list_details.addItem("Keine Maßnahmen gefunden.")
        else:
            for (mid, name, erledigt) in zeilen:
                item = QListWidgetItem(name)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked if erledigt == 1 else Qt.Unchecked)
                item.setData(Qt.UserRole, mid)
                self.list_details.addItem(item)
        
        self.list_details.blockSignals(False)
        conn.close()

    def on_measure_changed(self, item):
        measure_id = item.data(Qt.UserRole)
        new_state = 1 if item.checkState() == Qt.Checked else 0
        if measure_id is not None:
            conn = sqlite3.connect("datenbank.db")
            c = conn.cursor()
            c.execute("UPDATE maßnahme SET erledigt = ? WHERE id = ?", (new_state, measure_id))
            conn.commit()
            conn.close()

    def speichere_beschreibung(self):
        if not self.current_habit_name:
            return
        text = self.txt_beschreibung.toPlainText()
        conn = sqlite3.connect("datenbank.db")
        c = conn.cursor()
        try:
            c.execute("UPDATE gewohnheit SET beschreibung = ? WHERE name = ?", 
                      (text, self.current_habit_name))
            conn.commit()
            print("Beschreibung gespeichert.")
        except Exception as e:
            print("Fehler:", e)
        finally:
            conn.close()

# --- Main Window ---

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        setup_test_database() 
        
        self.btn_gewohnheiten = QPushButton("Gewohnheiten")
        self.btn_maßnahmen = QPushButton("Alle Maßnahmen")
        
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        self.setWindowTitle("Gewohnheit Tracker")
        self.resize(800, 600) 
        
        self.stack = QStackedWidget()
        self.view_gewohnheiten = GewohnheitenAnsicht()
        self.stack.addWidget(self.view_gewohnheiten)
        self.view_maßnahmen = MaßnahmenAnsicht()
        self.stack.addWidget(self.view_maßnahmen)
        self.view_detail = DetailAnsicht()
        self.stack.addWidget(self.view_detail)

        sidebar_layout = QVBoxLayout()
        sidebar_layout.addWidget(self.btn_gewohnheiten)
        sidebar_layout.addWidget(self.btn_maßnahmen)
        sidebar_layout.addStretch()

        main_layout = QHBoxLayout(self)
        main_layout.addLayout(sidebar_layout)
        main_layout.addWidget(self.stack)

    def connect_signals(self):
        self.btn_gewohnheiten.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.btn_maßnahmen.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        self.view_gewohnheiten.habit_clicked.connect(self.open_detail_view)
        self.view_detail.back_clicked.connect(self.go_back_to_list)

    def open_detail_view(self, habit_name):
        self.view_detail.set_habit(habit_name)
        self.stack.setCurrentIndex(2)

    def go_back_to_list(self):
        self.stack.setCurrentIndex(0)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())