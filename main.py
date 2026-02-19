import sys
import sqlite3
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel,
    QVBoxLayout, QHBoxLayout, QListWidget,
    QStackedWidget, QTextEdit, QListWidgetItem,
    QCalendarWidget, QMenu, QInputDialog, QMessageBox,
    QDialog, QLineEdit, QComboBox, QButtonGroup, QCheckBox,
    QSplitter, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal, QDate, QSize, QTimer
from PyQt5.QtGui import QFont, QTextCharFormat, QColor, QIcon

# Falls deine Datei anders heißt, passe diesen Import an:
from datenbanksetup import setup_test_database, get_conn

# -------------------------
# HILFSFUNKTION: DB ERWEITERN
# -------------------------
def ensure_database_columns():
    """Prüft, ob die neuen Spalten und Tabellen existieren, und fügt sie notfalls hinzu."""
    conn = get_conn()
    c = conn.cursor()
    
    # 1. Tabelle maßnahme prüfen und erweitern
    c.execute("PRAGMA table_info(maßnahme)")
    columns = [info[1] for info in c.fetchall()]
    
    if "beschreibung" not in columns:
        print("Füge Spalte 'beschreibung' zur Tabelle 'maßnahme' hinzu...")
        c.execute("ALTER TABLE maßnahme ADD COLUMN beschreibung TEXT")
        
    if "effektivitaet" not in columns:
        print("Füge Spalte 'effektivitaet' zur Tabelle 'maßnahme' hinzu...")
        c.execute("ALTER TABLE maßnahme ADD COLUMN effektivitaet INTEGER DEFAULT 3")

    # 2. Neue Tabelle für Todos erstellen, falls nicht vorhanden
    c.execute("""
        CREATE TABLE IF NOT EXISTS todo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titel TEXT NOT NULL,
            beschreibung TEXT,
            massnahme_id INTEGER,
            FOREIGN KEY(massnahme_id) REFERENCES maßnahme(id)
        )
    """)
        
    conn.commit()
    conn.close()

# -------------------------
# SCORE-LOGIK (vorerst Dummy)
# -------------------------

def weakly_score_berechnen() -> int:
    return 67

_DEMO_DAY_SCORES = {
    QDate.currentDate().addDays(-0): 72,
    QDate.currentDate().addDays(-1): 58,
    QDate.currentDate().addDays(-2): 33,
    QDate.currentDate().addDays(-3): 12,
    QDate.currentDate().addDays(-4): 85,
}

def tages_score_berechnen(date: QDate):
    return _DEMO_DAY_SCORES.get(date, None)

def score_to_color(score: int) -> str:
    if 1 <= score <= 20: return "#ff4d4d"   # rot
    if 21 <= score <= 40: return "#ffa500"  # orange
    if 41 <= score <= 60: return "#ffd84d"  # gelb
    if 61 <= score <= 80: return "#4caf50"  # grün
    if 81 <= score <= 99: return "#006400"  # dunkelgrün
    return "#d9d9d9"                        # fallback hellgrau


class ScoreCircle(QWidget):
    def __init__(self, score: int = 67, size: int = 120, parent=None):
        super().__init__(parent)
        self._size = size
        self.label = QLabel("", self)
        self.label.setAlignment(Qt.AlignCenter)
        font = QFont(); font.setBold(True); font.setPointSize(18)
        self.label.setFont(font)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        self.setFixedSize(size, size)
        self.set_score(score)

    def set_score(self, score: int):
        self.label.setText(str(score))
        color = score_to_color(score)
        radius = self._size // 2
        self.setStyleSheet(f"background-color: {color}; border-radius: {radius}px;")

# -------------------------
# DIALOGE (Allgemein & Maßnahmen)
# -------------------------

class StatistikDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Statistiken")
        self.resize(500, 300)
        layout = QVBoxLayout(self)
        title = QLabel("Statistik:")
        font = QFont(); font.setBold(True); font.setPointSize(12)
        title.setFont(font)
        layout.addWidget(title)
        layout.addWidget(QLabel("noch in Arbeit …"))

class ImproveDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Was man noch besser machen kann")
        self.resize(500, 300)
        layout = QVBoxLayout(self)
        label = QLabel("noch in Arbeit...")
        font = QFont(); font.setBold(True); font.setPointSize(12)
        label.setFont(font)
        layout.addWidget(label)

class TagesDialog(QDialog):
    def __init__(self, date: QDate, parent=None):
        super().__init__(parent)
        self.setWindowTitle(date.toString("dd.MM.yyyy"))
        self.resize(550, 450)
        layout = QVBoxLayout(self)
        title = QLabel("Dein Tagesscore:")
        font = QFont(); font.setBold(True); font.setPointSize(12)
        title.setFont(font)
        layout.addWidget(title)

        score = tages_score_berechnen(date)
        if score is None:
            score = 67
            hint = QLabel("(Tages-Score: noch in Arbeit – aktuell Dummy-Wert)")
            hint.setStyleSheet("color: gray;")
            layout.addWidget(hint)

        circle = ScoreCircle(score=score, size=110)
        layout.addWidget(circle, alignment=Qt.AlignLeft)
        layout.addSpacing(10)
        
        lbl_done = QLabel("Wurde erledigt:")
        lbl_done.setFont(font)
        layout.addWidget(lbl_done)
        list_done = QListWidget()
        list_done.addItem("— noch in Arbeit —")
        layout.addWidget(list_done)

        lbl_not = QLabel("Wurde nicht erledigt:")
        lbl_not.setFont(font)
        layout.addWidget(lbl_not)
        list_not = QListWidget()
        list_not.addItem("— noch in Arbeit —")
        layout.addWidget(list_not)

class MassnahmeHinzufuegenDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Neue Maßnahme hinzufügen")
        self.resize(400, 350)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name der Maßnahme:"))
        self.input_name = QLineEdit()
        layout.addWidget(self.input_name)

        layout.addWidget(QLabel("Beschreibung:"))
        self.input_desc = QTextEdit()
        self.input_desc.setMaximumHeight(80)
        layout.addWidget(self.input_desc)

        layout.addWidget(QLabel("Gewohnheit zuordnen:"))
        self.combo_habit = QComboBox()
        self.lade_gewohnheiten()
        layout.addWidget(self.combo_habit)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_save = QPushButton("Hinzufügen")
        self.btn_save.clicked.connect(self.speichern)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

    def lade_gewohnheiten(self):
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT id, name FROM gewohnheit ORDER BY name")
        for hid, name in c.fetchall():
            self.combo_habit.addItem(name, hid)
        conn.close()

    def speichern(self):
        name = self.input_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Fehler", "Bitte einen Namen eingeben.")
            return

        desc = self.input_desc.toPlainText()
        habit_id = self.combo_habit.currentData()

        if habit_id is None:
            QMessageBox.warning(self, "Fehler", "Bitte erst eine Gewohnheit anlegen.")
            return

        conn = get_conn()
        c = conn.cursor()
        # Default Effektivität auf 3 (Gelb) setzen, erledigt auf 0
        c.execute("INSERT INTO maßnahme (name, gewohnheit_id, erledigt, beschreibung, effektivitaet) VALUES (?, ?, 0, ?, 3)", 
                  (name, habit_id, desc))
        conn.commit()
        conn.close()
        self.accept()

# -------------------------
# DIALOGE (Todo)
# -------------------------

class TodoHinzufuegenDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Neues To-Do hinzufügen")
        self.resize(400, 400)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Titel:"))
        self.input_titel = QLineEdit()
        layout.addWidget(self.input_titel)

        layout.addWidget(QLabel("Beschreibung:"))
        self.input_desc = QTextEdit()
        layout.addWidget(self.input_desc)

        layout.addWidget(QLabel("Einer Maßnahme zuordnen (optional):"))
        self.combo_massnahme = QComboBox()
        self.combo_massnahme.addItem("--- Keine ---", None)
        self.lade_massnahmen()
        layout.addWidget(self.combo_massnahme)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_save = QPushButton("Speichern")
        self.btn_save.clicked.connect(self.speichern)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

    def lade_massnahmen(self):
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT id, name FROM maßnahme ORDER BY name")
        for mid, name in c.fetchall():
            self.combo_massnahme.addItem(name, mid)
        conn.close()

    def speichern(self):
        titel = self.input_titel.text().strip()
        if not titel:
            QMessageBox.warning(self, "Fehler", "Bitte einen Titel eingeben.")
            return
        desc = self.input_desc.toPlainText()
        mid = self.combo_massnahme.currentData()

        conn = get_conn()
        c = conn.cursor()
        c.execute("INSERT INTO todo (titel, beschreibung, massnahme_id) VALUES (?, ?, ?)", (titel, desc, mid))
        conn.commit()
        conn.close()
        self.accept()

class TodoDetailDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("To-Do Details & Bearbeiten")
        self.resize(400, 400)
        self.todo_id = None
        
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Titel:"))
        self.input_titel = QLineEdit()
        layout.addWidget(self.input_titel)

        layout.addWidget(QLabel("Beschreibung:"))
        self.input_desc = QTextEdit()
        layout.addWidget(self.input_desc)

        layout.addWidget(QLabel("Zugeordnete Maßnahme:"))
        self.combo_massnahme = QComboBox()
        self.combo_massnahme.addItem("--- Keine ---", None)
        self.lade_massnahmen_options()
        layout.addWidget(self.combo_massnahme)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_save = QPushButton("Änderungen speichern")
        self.btn_save.clicked.connect(self.speichern)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

    def lade_massnahmen_options(self):
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT id, name FROM maßnahme ORDER BY name")
        for mid, name in c.fetchall():
            self.combo_massnahme.addItem(name, mid)
        conn.close()

    def set_todo_id(self, tid):
        self.todo_id = tid
        self.lade_daten()

    def lade_daten(self):
        if self.todo_id is None: return
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT titel, beschreibung, massnahme_id FROM todo WHERE id = ?", (self.todo_id,))
        row = c.fetchone()
        conn.close()
        if row:
            titel, desc, mid = row
            self.input_titel.setText(titel)
            self.input_desc.setText(desc if desc else "")
            idx = self.combo_massnahme.findData(mid)
            if idx >= 0:
                self.combo_massnahme.setCurrentIndex(idx)
            else:
                self.combo_massnahme.setCurrentIndex(0) # Keine

    def speichern(self):
        if self.todo_id is None: return
        titel = self.input_titel.text().strip()
        if not titel:
             QMessageBox.warning(self, "Fehler", "Titel darf nicht leer sein.")
             return
        desc = self.input_desc.toPlainText()
        mid = self.combo_massnahme.currentData()
        
        conn = get_conn()
        c = conn.cursor()
        c.execute("UPDATE todo SET titel=?, beschreibung=?, massnahme_id=? WHERE id=?", (titel, desc, mid, self.todo_id))
        conn.commit()
        conn.close()
        self.accept()

# -------------------------
# ANSICHTEN
# -------------------------

class GewohnheitenAnsicht(QWidget):
    habit_clicked = pyqtSignal(int)
    habit_deleted = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.list_widget_gewohnheit = QListWidget()
        layout.addWidget(self.list_widget_gewohnheit)
        self.list_widget_gewohnheit.itemClicked.connect(self.on_item_clicked)
        self.list_widget_gewohnheit.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget_gewohnheit.customContextMenuRequested.connect(self.show_context_menu)
        self.lade_gewohnheiten()

    def lade_gewohnheiten(self):
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT id, name FROM gewohnheit ORDER BY id")
        zeilen = c.fetchall()
        self.list_widget_gewohnheit.clear()
        for hid, name in zeilen:
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, hid)
            self.list_widget_gewohnheit.addItem(item)
        conn.close()

    def on_item_clicked(self, item):
        habit_id = item.data(Qt.UserRole)
        if habit_id is not None:
            self.habit_clicked.emit(habit_id)

    def show_context_menu(self, pos):
        item = self.list_widget_gewohnheit.itemAt(pos)
        if not item: return
        habit_id = item.data(Qt.UserRole)
        menu = QMenu(self)
        act_rename = menu.addAction("Neu benennen")
        act_delete = menu.addAction("Löschen")
        action = menu.exec_(self.list_widget_gewohnheit.mapToGlobal(pos))
        if action == act_rename:
            self.rename_habit(habit_id)
        elif action == act_delete:
            self.delete_habit(habit_id)

    def rename_habit(self, habit_id: int):
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT name FROM gewohnheit WHERE id = ?", (habit_id,))
        row = c.fetchone()
        conn.close()
        if not row: return
        old_name = row[0]
        new_name, ok = QInputDialog.getText(self, "Gewohnheit umbenennen", "Neuer Name:", text=old_name)
        new_name = new_name.strip() if new_name else ""
        if ok and new_name and new_name != old_name:
            conn = get_conn()
            c = conn.cursor()
            try:
                c.execute("UPDATE gewohnheit SET name = ? WHERE id = ?", (new_name, habit_id))
                conn.commit()
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "Fehler", "Name existiert schon.")
            finally:
                conn.close()
            self.lade_gewohnheiten()

    def delete_habit(self, habit_id: int):
        reply = QMessageBox.question(self, "Löschen", "Gewohnheit und Maßnahmen wirklich löschen?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            conn = get_conn()
            c = conn.cursor()
            # Zuerst Todos löschen, die an Maßnahmen dieser Gewohnheit hängen
            c.execute("DELETE FROM todo WHERE massnahme_id IN (SELECT id FROM maßnahme WHERE gewohnheit_id = ?)", (habit_id,))
            c.execute("DELETE FROM maßnahme WHERE gewohnheit_id = ?", (habit_id,))
            c.execute("DELETE FROM gewohnheit WHERE id = ?", (habit_id,))
            conn.commit()
            conn.close()
            self.lade_gewohnheiten()
            self.habit_deleted.emit(habit_id)


class MassnahmenAnsicht(QWidget):
    measure_clicked = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        # Hauptlayout ist horizontal geteilt
        main_layout = QHBoxLayout(self)

        # --- LINKER BEREICH: Maßnahmen Liste ---
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 10, 0)

        # Header Links
        header_left = QHBoxLayout()
        label_m = QLabel("Alle Maßnahmen")
        font = QFont(); font.setBold(True); font.setPointSize(12)
        label_m.setFont(font)
        header_left.addWidget(label_m)
        header_left.addStretch()
        self.btn_add_m = QPushButton("Maßnahme hinzufügen")
        self.btn_add_m.clicked.connect(self.open_add_measure_dialog)
        header_left.addWidget(self.btn_add_m)
        left_layout.addLayout(header_left)

        # Liste Links
        self.list_widget_massnahme = QListWidget()
        self.list_widget_massnahme.itemChanged.connect(self.on_measure_item_changed)
        self.list_widget_massnahme.itemClicked.connect(self.on_measure_item_clicked)
        self.list_widget_massnahme.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget_massnahme.customContextMenuRequested.connect(self.show_measure_context_menu)
        left_layout.addWidget(self.list_widget_massnahme)

        # --- RECHTER BEREICH: To-Do Liste ---
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(10, 0, 0, 0)

        # Header Rechts
        header_right = QHBoxLayout()
        label_t = QLabel("To-Do Liste")
        label_t.setFont(font)
        header_right.addWidget(label_t)
        header_right.addStretch()
        self.btn_add_t = QPushButton("+ Todo hinzufügen")
        self.btn_add_t.clicked.connect(self.open_add_todo_dialog)
        header_right.addWidget(self.btn_add_t)
        right_layout.addLayout(header_right)

        # Liste Rechts
        self.list_widget_todo = QListWidget()
        self.list_widget_todo.itemChanged.connect(self.on_todo_item_changed)
        self.list_widget_todo.itemClicked.connect(self.open_todo_detail)
        right_layout.addWidget(self.list_widget_todo)

        # Splitter für variable Breite
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_container)
        splitter.addWidget(right_container)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter)

        self.lade_massnahmen()
        self.lade_todos()

    # --- Methoden für Maßnahmen (Links) ---
    def open_add_measure_dialog(self):
        dlg = MassnahmeHinzufuegenDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            self.lade_massnahmen()

    def on_measure_item_clicked(self, item):
        mid = item.data(Qt.UserRole)
        if mid is not None:
            self.measure_clicked.emit(mid)

    def on_measure_item_changed(self, item):
        mid = item.data(Qt.UserRole)
        new_state = 1 if item.checkState() == Qt.Checked else 0
        if mid is not None:
            conn = get_conn()
            c = conn.cursor()
            c.execute("UPDATE maßnahme SET erledigt = ? WHERE id = ?", (new_state, mid))
            conn.commit()
            conn.close()

    def lade_massnahmen(self):
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT id, name, erledigt FROM maßnahme ORDER BY id")
        zeilen = c.fetchall()
        self.list_widget_massnahme.blockSignals(True)
        self.list_widget_massnahme.clear()
        for mid, name, erledigt in zeilen:
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if erledigt == 1 else Qt.Unchecked)
            item.setData(Qt.UserRole, mid)
            self.list_widget_massnahme.addItem(item)
        self.list_widget_massnahme.blockSignals(False)
        conn.close()

    def show_measure_context_menu(self, pos):
        item = self.list_widget_massnahme.itemAt(pos)
        if not item: return
        mid = item.data(Qt.UserRole)
        menu = QMenu(self)
        act_rename = menu.addAction("Neu benennen")
        act_delete = menu.addAction("Löschen")
        action = menu.exec_(self.list_widget_massnahme.mapToGlobal(pos))
        if action == act_rename:
            self.rename_measure(mid)
        elif action == act_delete:
            self.delete_measure(mid)

    def rename_measure(self, measure_id: int):
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT name FROM maßnahme WHERE id = ?", (measure_id,))
        row = c.fetchone()
        conn.close()
        if not row: return
        old_name = row[0]
        new_name, ok = QInputDialog.getText(self, "Maßnahme umbenennen", "Neuer Name:", text=old_name)
        new_name = new_name.strip() if new_name else ""
        if ok and new_name and new_name != old_name:
            conn = get_conn()
            c = conn.cursor()
            c.execute("UPDATE maßnahme SET name = ? WHERE id = ?", (new_name, measure_id))
            conn.commit()
            conn.close()
            self.lade_massnahmen()

    def delete_measure(self, measure_id: int):
        reply = QMessageBox.question(self, "Löschen", "Maßnahme löschen? Zugehörige Todos werden auch gelöscht.", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            conn = get_conn()
            c = conn.cursor()
            c.execute("DELETE FROM todo WHERE massnahme_id = ?", (measure_id,))
            c.execute("DELETE FROM maßnahme WHERE id = ?", (measure_id,))
            conn.commit()
            conn.close()
            self.lade_massnahmen()
            self.lade_todos() # Todos neu laden, da manche gelöscht sein könnten

    # --- Methoden für To-Dos (Rechts) ---
    def open_add_todo_dialog(self):
        dlg = TodoHinzufuegenDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            self.lade_todos()

    def lade_todos(self):
        """Lädt Todos und gruppiert sie nach der zugeordneten Maßnahme."""
        conn = get_conn()
        c = conn.cursor()
        c.execute("""
            SELECT t.id, t.titel, t.massnahme_id, m.name 
            FROM todo t 
            LEFT JOIN maßnahme m ON t.massnahme_id = m.id 
            ORDER BY m.name, t.id DESC
        """)
        zeilen = c.fetchall()
        
        self.list_widget_todo.blockSignals(True)
        self.list_widget_todo.clear()
        
        # In Gruppen aufteilen
        gruppen = {}
        for tid, titel, mid, m_name in zeilen:
            group_name = m_name if m_name else "Ohne Maßnahme"
            if group_name not in gruppen:
                gruppen[group_name] = []
            gruppen[group_name].append((tid, titel))
            
        for g_name, todos in gruppen.items():
            # Überschrift hinzufügen
            header = QListWidgetItem(f"--- {g_name} ---")
            header.setFlags(Qt.ItemIsEnabled) # Verhindert anklicken und abhaken
            font = QFont(); font.setBold(True); font.setItalic(True)
            header.setFont(font)
            header.setBackground(QColor("#e0e0e0"))
            self.list_widget_todo.addItem(header)
            
            # Todos zur Gruppe hinzufügen
            for tid, titel in todos:
                item = QListWidgetItem(f"  {titel}") # Leicht eingerückt
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                item.setCheckState(Qt.Unchecked) # Immer unchecked laden
                item.setData(Qt.UserRole, tid)
                self.list_widget_todo.addItem(item)
                
        self.list_widget_todo.blockSignals(False)
        conn.close()

    def on_todo_item_changed(self, item):
        if item is None: return
        tid = item.data(Qt.UserRole)
        if tid is None: return # Handelt sich um eine Überschrift
        
        # Wenn abgehakt wird -> Löschen
        if item.checkState() == Qt.Checked:
            conn = get_conn()
            c = conn.cursor()
            c.execute("DELETE FROM todo WHERE id = ?", (tid,))
            conn.commit()
            conn.close()
            # Verzögertes Neuladen verhindert Absturz durch Klick-Event-Konflikte
            QTimer.singleShot(0, self.lade_todos)

    def open_todo_detail(self, item):
        if item is None: return
        
        # Verhindern, dass sich die Detailansicht öffnet, wenn nur der Haken gesetzt wurde
        if item.checkState() == Qt.Checked: 
            return
            
        tid = item.data(Qt.UserRole)
        if tid is not None:
            dlg = TodoDetailDialog(self)
            dlg.set_todo_id(tid)
            if dlg.exec_() == QDialog.Accepted:
                self.lade_todos()


class MassnahmeDetailAnsicht(QWidget):
    back_clicked = pyqtSignal()
    measure_deleted = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.current_measure_id = None
        
        layout = QVBoxLayout(self)

        # Header
        header_layout = QHBoxLayout()
        self.btn_back = QPushButton("←")
        self.btn_back.setFixedSize(40, 40)
        self.btn_back.clicked.connect(self.back_clicked.emit)
        header_layout.addWidget(self.btn_back)

        self.lbl_title = QLabel("Maßnahmen Name")
        font = QFont(); font.setBold(True); font.setPointSize(12)
        self.lbl_title.setFont(font)
        header_layout.addWidget(self.lbl_title)
        header_layout.addStretch()
        
        self.btn_delete = QPushButton("Löschen")
        self.btn_delete.setStyleSheet("background-color: #ff4d4d; color: white; font-weight: bold;")
        self.btn_delete.clicked.connect(self.loesche_massnahme)
        header_layout.addWidget(self.btn_delete)
        layout.addLayout(header_layout)

        # Zugeordnete Gewohnheit ändern (Dropdown) & Status
        info_layout = QHBoxLayout()
        
        # Links: Dropdown
        habit_layout = QHBoxLayout()
        habit_layout.addWidget(QLabel("Zugeordnete Gewohnheit:"))
        self.combo_habit = QComboBox()
        self.combo_habit.setMinimumWidth(200)
        self.combo_habit.currentIndexChanged.connect(self.speichere_gewohnheit)
        habit_layout.addWidget(self.combo_habit)
        info_layout.addLayout(habit_layout)
        
        info_layout.addStretch()
        
        # Rechts: Status Checkbox
        self.chk_status = QCheckBox("umgesetzt:")
        font_chk = QFont(); font_chk.setBold(True)
        self.chk_status.setFont(font_chk)
        self.chk_status.setLayoutDirection(Qt.RightToLeft) # Checkbox rechts vom Text
        self.chk_status.stateChanged.connect(self.speichere_status)
        info_layout.addWidget(self.chk_status)
        
        layout.addLayout(info_layout)
        layout.addSpacing(10)

        # Beschreibung
        layout.addWidget(QLabel("Beschreibung:"))
        self.txt_beschreibung = QTextEdit()
        self.txt_beschreibung.setMaximumHeight(100)
        layout.addWidget(self.txt_beschreibung)

        self.btn_save_desc = QPushButton("Beschreibung speichern")
        self.btn_save_desc.clicked.connect(self.speichere_beschreibung)
        layout.addWidget(self.btn_save_desc, alignment=Qt.AlignRight)
        layout.addSpacing(20)

        # Effektivität Ranking (kleinere Buttons)
        layout.addWidget(QLabel("Wie effektiv ist diese Maßnahme?"))
        ranking_layout = QHBoxLayout()
        ranking_layout.setSpacing(4) 
        self.btn_group_eff = QButtonGroup(self)
        
        colors = ["#ff4d4d", "#ffa500", "#ffd84d", "#4caf50", "#006400"]
        labels = ["Schlecht", "Eher schlecht", "Mittel", "Eher gut", "Gut"]
        
        for i, (color, text) in enumerate(zip(colors, labels)):
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setMinimumHeight(25) 
            btn.setStyleSheet(f"""
                QPushButton {{ background-color: {color}; border: 1px solid gray; border-radius: 4px; padding: 2px; font-size: 11px; }}
                QPushButton:checked {{ border: 3px solid black; font-weight: bold; font-size: 11px; }}
            """)
            self.btn_group_eff.addButton(btn, i + 1)
            ranking_layout.addWidget(btn)
        
        self.btn_group_eff.buttonClicked.connect(self.speichere_effektivitaet)
        layout.addLayout(ranking_layout)
        layout.addStretch()

    def set_measure(self, measure_id: int):
        self.current_measure_id = measure_id
        self.lade_daten()

    def lade_daten(self):
        if self.current_measure_id is None: return
        
        # Gewohnheiten ins Dropdown laden (ohne dabei das Change-Signal auszulösen)
        self.combo_habit.blockSignals(True)
        self.combo_habit.clear()
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT id, name FROM gewohnheit ORDER BY name")
        for hid, name in c.fetchall():
            self.combo_habit.addItem(name, hid)
            
        # Maßnahmendaten laden
        c.execute("""
            SELECT name, gewohnheit_id, beschreibung, effektivitaet, erledigt 
            FROM maßnahme 
            WHERE id = ?
        """, (self.current_measure_id,))
        
        result = c.fetchone()
        conn.close()

        if result:
            name, gewohnheit_id, beschreibung, effektivitaet, erledigt = result
            self.lbl_title.setText(name)
            
            # ComboBox auf aktuell zugeordnete Gewohnheit setzen
            idx = self.combo_habit.findData(gewohnheit_id)
            if idx >= 0:
                self.combo_habit.setCurrentIndex(idx)
                
            self.txt_beschreibung.setText(beschreibung if beschreibung else "")
            
            # Checkbox Status setzen
            self.chk_status.blockSignals(True)
            self.chk_status.setChecked(bool(erledigt))
            self.chk_status.blockSignals(False)
            
            # Button Status setzen
            if effektivitaet and 1 <= effektivitaet <= 5:
                self.btn_group_eff.button(effektivitaet).setChecked(True)
            else:
                if self.btn_group_eff.checkedButton():
                    self.btn_group_eff.setExclusive(False)
                    self.btn_group_eff.checkedButton().setChecked(False)
                    self.btn_group_eff.setExclusive(True)
                    
        self.combo_habit.blockSignals(False)

    def speichere_gewohnheit(self):
        if self.current_measure_id is None: return
        habit_id = self.combo_habit.currentData()
        if habit_id is None: return
        
        conn = get_conn()
        c = conn.cursor()
        c.execute("UPDATE maßnahme SET gewohnheit_id = ? WHERE id = ?", (habit_id, self.current_measure_id))
        conn.commit()
        conn.close()

    def speichere_status(self, state):
        if self.current_measure_id is None: return
        erledigt = 1 if state == Qt.Checked else 0
        conn = get_conn()
        c = conn.cursor()
        c.execute("UPDATE maßnahme SET erledigt = ? WHERE id = ?", (erledigt, self.current_measure_id))
        conn.commit()
        conn.close()

    def speichere_beschreibung(self):
        if self.current_measure_id is None: return
        text = self.txt_beschreibung.toPlainText()
        conn = get_conn()
        c = conn.cursor()
        c.execute("UPDATE maßnahme SET beschreibung = ? WHERE id = ?", (text, self.current_measure_id))
        conn.commit()
        conn.close()
        QMessageBox.information(self, "Info", "Beschreibung gespeichert.")

    def speichere_effektivitaet(self, button):
        if self.current_measure_id is None: return
        wert = self.btn_group_eff.id(button)
        conn = get_conn()
        c = conn.cursor()
        c.execute("UPDATE maßnahme SET effektivitaet = ? WHERE id = ?", (wert, self.current_measure_id))
        conn.commit()
        conn.close()

    def loesche_massnahme(self):
        reply = QMessageBox.question(self, "Löschen", "Willst du diese Maßnahme wirklich löschen? Zugehörige Todos werden auch gelöscht.", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            conn = get_conn()
            c = conn.cursor()
            c.execute("DELETE FROM todo WHERE massnahme_id = ?", (self.current_measure_id,))
            c.execute("DELETE FROM maßnahme WHERE id = ?", (self.current_measure_id,))
            conn.commit()
            conn.close()
            self.measure_deleted.emit()
            self.back_clicked.emit()


class DetailAnsicht(QWidget):
    back_clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.current_habit_id = None
        layout = QVBoxLayout(self)

        header_layout = QHBoxLayout()
        self.btn_back = QPushButton("←")
        self.btn_back.setFixedSize(40, 40)
        self.btn_back.clicked.connect(self.back_clicked.emit)
        header_layout.addWidget(self.btn_back)

        self.lbl_title = QLabel("Habit Name")
        font = QFont(); font.setBold(True); font.setPointSize(12)
        self.lbl_title.setFont(font)
        header_layout.addWidget(self.lbl_title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        layout.addWidget(QLabel("Beschreibung:"))
        self.txt_beschreibung = QTextEdit()
        self.txt_beschreibung.setMaximumHeight(80)
        layout.addWidget(self.txt_beschreibung)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_save_desc = QPushButton("Beschreibung speichern")
        self.btn_save_desc.setFixedWidth(150)
        self.btn_save_desc.clicked.connect(self.speichere_beschreibung)
        btn_layout.addWidget(self.btn_save_desc)
        layout.addLayout(btn_layout)

        content_layout = QHBoxLayout()
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Maßnahmen (haken):"))
        self.list_details = QListWidget()
        self.list_details.itemChanged.connect(self.on_measure_changed)
        left_layout.addWidget(self.list_details)
        content_layout.addLayout(left_layout, stretch=1) 

        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Kalender:"))
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setMaximumSize(350, 250) 
        right_layout.addWidget(self.calendar, alignment=Qt.AlignTop)
        content_layout.addLayout(right_layout, stretch=1)
        layout.addLayout(content_layout)

    def set_habit(self, habit_id: int):
        self.current_habit_id = habit_id
        self.lade_daten()

    def lade_daten(self):
        if self.current_habit_id is None: return
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT name, beschreibung FROM gewohnheit WHERE id = ?", (self.current_habit_id,))
        result = c.fetchone()
        if result:
            name, beschreibung = result
            self.lbl_title.setText(name)
            self.txt_beschreibung.setText(beschreibung if beschreibung else "")
        else:
            conn.close(); return

        c.execute("SELECT id, name, erledigt FROM maßnahme WHERE gewohnheit_id = ? ORDER BY id", (self.current_habit_id,))
        zeilen = c.fetchall()
        self.list_details.blockSignals(True)
        self.list_details.clear()
        if not zeilen:
            info = QListWidgetItem("Keine Maßnahmen gefunden.")
            info.setFlags(Qt.NoItemFlags)
            self.list_details.addItem(info)
        else:
            for mid, name, erledigt in zeilen:
                item = QListWidgetItem(name)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked if erledigt == 1 else Qt.Unchecked)
                item.setData(Qt.UserRole, mid)
                self.list_details.addItem(item)
        self.list_details.blockSignals(False)
        conn.close()

    def on_measure_changed(self, item):
        mid = item.data(Qt.UserRole)
        new_state = 1 if item.checkState() == Qt.Checked else 0
        if mid is not None:
            conn = get_conn()
            c = conn.cursor()
            c.execute("UPDATE maßnahme SET erledigt = ? WHERE id = ?", (new_state, mid))
            conn.commit()
            conn.close()

    def speichere_beschreibung(self):
        if self.current_habit_id is None: return
        text = self.txt_beschreibung.toPlainText()
        conn = get_conn()
        c = conn.cursor()
        c.execute("UPDATE gewohnheit SET beschreibung = ? WHERE id = ?", (text, self.current_habit_id))
        conn.commit()
        conn.close()

class WochenAnsicht(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        top = QHBoxLayout()
        left = QVBoxLayout()
        lbl = QLabel("Dein Wochenscore:")
        f = QFont(); f.setBold(True); f.setPointSize(12)
        lbl.setFont(f)
        left.addWidget(lbl)
        self.week_circle = ScoreCircle(score=weakly_score_berechnen(), size=130)
        left.addWidget(self.week_circle, alignment=Qt.AlignLeft)
        left.addStretch()

        right = QVBoxLayout()
        review = QLabel("Review:")
        review.setFont(f)
        right.addWidget(review)
        self.btn_stats = QPushButton("Statistiken")
        self.btn_stats.clicked.connect(self.open_stats)
        right.addWidget(self.btn_stats)
        self.btn_improve = QPushButton("Was man noch besser machen kann")
        self.btn_improve.clicked.connect(self.open_improve)
        right.addWidget(self.btn_improve)
        right.addStretch()

        top.addLayout(left, 1)
        top.addLayout(right, 2)
        root.addLayout(top)
        root.addSpacing(10)

        root.addWidget(QLabel("Kalender:"))
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        root.addWidget(self.calendar, 1)
        self.calendar.clicked.connect(self.open_day_dialog)
        self.calendar.currentPageChanged.connect(self.apply_calendar_formats)
        self.apply_calendar_formats()

    def open_stats(self):
        dlg = StatistikDialog(self)
        dlg.exec_()
    def open_improve(self):
        dlg = ImproveDialog(self)
        dlg.exec_()
    def open_day_dialog(self, date: QDate):
        dlg = TagesDialog(date, self)
        dlg.exec_()
    def refresh(self):
        self.week_circle.set_score(weakly_score_berechnen())
        self.apply_calendar_formats()
    def apply_calendar_formats(self, year=None, month=None):
        if year is None: year = self.calendar.yearShown()
        if month is None: month = self.calendar.monthShown()
        base_fmt = QTextCharFormat()
        base_fmt.setBackground(QColor("#eeeeee"))
        first = QDate(year, month, 1)
        days = first.daysInMonth()
        for d in range(1, days + 1):
            self.calendar.setDateTextFormat(QDate(year, month, d), base_fmt)
        for d in range(1, days + 1):
            date = QDate(year, month, d)
            score = tages_score_berechnen(date)
            if score is None: continue
            fmt = QTextCharFormat()
            fmt.setBackground(QColor(score_to_color(score)))
            self.calendar.setDateTextFormat(date, fmt)

# -------------------------
# MAIN WINDOW
# -------------------------

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        setup_test_database()
        ensure_database_columns()  # WICHTIG: Prüft und updated DB-Schema

        self.btn_gewohnheiten = QPushButton("Gewohnheiten")
        self.btn_massnahmen = QPushButton("Alle Maßnahmen") 
        self.btn_wochenanzeige = QPushButton("Wochenanzeige")

        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        self.setWindowTitle("Gewohnheit Tracker")
        self.resize(1000, 700) # Etwas breiter für die zweigeteilte Ansicht
        
        self.stack = QStackedWidget()
        
        self.view_gewohnheiten = GewohnheitenAnsicht()
        self.view_massnahmen = MassnahmenAnsicht() 
        self.view_detail = DetailAnsicht()
        self.view_measure_detail = MassnahmeDetailAnsicht()
        self.view_wochen = WochenAnsicht()
        
        self.stack.addWidget(self.view_gewohnheiten)     # Index 0
        self.stack.addWidget(self.view_massnahmen)       # Index 1
        self.stack.addWidget(self.view_detail)           # Index 2
        self.stack.addWidget(self.view_wochen)           # Index 3
        self.stack.addWidget(self.view_measure_detail)   # Index 4

        sidebar_layout = QVBoxLayout()
        sidebar_layout.addWidget(self.btn_gewohnheiten)
        sidebar_layout.addWidget(self.btn_massnahmen)
        sidebar_layout.addWidget(self.btn_wochenanzeige)
        sidebar_layout.addStretch()

        main_layout = QHBoxLayout(self)
        main_layout.addLayout(sidebar_layout)
        main_layout.addWidget(self.stack)

    def connect_signals(self):
        # Sidebar Navigation
        self.btn_gewohnheiten.clicked.connect(lambda: self.stack.setCurrentWidget(self.view_gewohnheiten))
        self.btn_massnahmen.clicked.connect(lambda: {
            self.view_massnahmen.lade_massnahmen(), 
            self.view_massnahmen.lade_todos(),
            self.stack.setCurrentWidget(self.view_massnahmen)
        })
        self.btn_wochenanzeige.clicked.connect(self.show_wochenanzeige)
        
        # Gewohnheiten Logik
        self.view_gewohnheiten.habit_clicked.connect(self.open_detail_view)
        self.view_gewohnheiten.habit_deleted.connect(self.on_habit_deleted)
        self.view_detail.back_clicked.connect(lambda: {
            self.view_massnahmen.lade_massnahmen(), # Lade Maßnahmen neu, falls sich Haken geändert haben
            self.stack.setCurrentWidget(self.view_gewohnheiten)
        })

        # Maßnahmen Logik
        self.view_massnahmen.measure_clicked.connect(self.open_measure_detail)
        self.view_measure_detail.back_clicked.connect(lambda: {
            self.view_massnahmen.lade_massnahmen(), # Lade Liste neu, falls sich in Detailansicht etwas geändert hat
            self.stack.setCurrentWidget(self.view_massnahmen)
        })
        self.view_measure_detail.measure_deleted.connect(lambda: {
            self.view_massnahmen.lade_massnahmen(),
            self.view_massnahmen.lade_todos()
        })

    def open_detail_view(self, habit_id):
        self.view_detail.set_habit(habit_id)
        self.stack.setCurrentWidget(self.view_detail)

    def open_measure_detail(self, measure_id):
        self.view_measure_detail.set_measure(measure_id)
        self.stack.setCurrentWidget(self.view_measure_detail)
        
    def on_habit_deleted(self, habit_id: int):
        if self.stack.currentWidget() == self.view_detail and self.view_detail.current_habit_id == habit_id:
            self.stack.setCurrentWidget(self.view_gewohnheiten)
        self.view_massnahmen.lade_massnahmen()
        self.view_massnahmen.lade_todos()
        
    def show_wochenanzeige(self):
        self.view_wochen.refresh()
        self.stack.setCurrentWidget(self.view_wochen)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())