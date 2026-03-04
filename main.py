import sys
import os
import sqlite3
from typing import List, Tuple
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
from PyQt5.QtWidgets import QScrollArea, QAbstractItemView, QSizePolicy
from PyQt5.QtCore import QMimeData
from PyQt5.QtGui import QDrag

# Falls deine Datei anders heißt, passe diesen Import an:
from datenbanksetup import setup_test_database, get_conn

# -------------------------
# HILFSFUNKTION: DB ERWEITERN
# -------------------------
def ensure_database_columns():
    """Prüft, ob neue Spalten/Tabellen existieren und fügt sie notfalls hinzu."""
    conn = get_conn()
    c = conn.cursor()

    # -------------------------
    # Tabelle "maßnahme" erweitern
    # -------------------------
    c.execute('PRAGMA table_info("maßnahme")')
    columns = [info[1] for info in c.fetchall()]

    if "beschreibung" not in columns:
        c.execute('ALTER TABLE "maßnahme" ADD COLUMN beschreibung TEXT')

    if "effektivitaet" not in columns:
        c.execute('ALTER TABLE "maßnahme" ADD COLUMN effektivitaet INTEGER DEFAULT 3')

    # NEU: status für Maßnahmen (aktiv/geplant/ausser_kraft)
    if "status" not in columns:
        c.execute('ALTER TABLE "maßnahme" ADD COLUMN status TEXT DEFAULT "aktiv"')
    # vorhandene NULLs sauber setzen
    c.execute('UPDATE "maßnahme" SET status="aktiv" WHERE status IS NULL')

    # -------------------------
    # Todo Tabelle (wie bei dir)
    # -------------------------
    c.execute("""
        CREATE TABLE IF NOT EXISTS todo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titel TEXT NOT NULL,
            beschreibung TEXT,
            massnahme_id INTEGER,
            FOREIGN KEY(massnahme_id) REFERENCES maßnahme(id)
        )
    """)

    # -------------------------
    # NEU: Weekly Review Tabelle (Reflexion pro KW)
    # -------------------------
    c.execute("""
        CREATE TABLE IF NOT EXISTS weekly_review (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gewohnheit_id INTEGER NOT NULL,
            iso_year INTEGER NOT NULL,
            iso_week INTEGER NOT NULL,
            reflection TEXT DEFAULT "",
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            UNIQUE(gewohnheit_id, iso_year, iso_week),
            FOREIGN KEY(gewohnheit_id) REFERENCES gewohnheit(id) ON DELETE CASCADE
        )
    """)

    # -------------------------
    # Migration: falls du früher "umgesetzt" genutzt hast -> "implementiert"
    # (Damit Kanban exakt deine Spaltennamen nutzt.)
    # -------------------------
    try:
        c.execute('UPDATE "gewohnheit" SET status="implementiert" WHERE status="umgesetzt"')
    except sqlite3.OperationalError:
        # falls die Tabelle/Spalte in deinem setup anders heißt
        pass

    conn.commit()
    conn.close()

# -------------------------
# Globale Funktionen
# -------------------------
DB_PATH = os.path.join(os.path.dirname(__file__), "datenbank.db")
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
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
# DIALOGE (Allgemein & maßnahmen)
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

class GewohnheitHinzufuegenDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Neue Gewohnheit hinzufügen")
        self.resize(400, 300)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name der Gewohnheit:"))
        self.input_name = QLineEdit()
        layout.addWidget(self.input_name)

        layout.addWidget(QLabel("Beschreibung:"))
        self.input_desc = QTextEdit()
        self.input_desc.setMaximumHeight(80)
        layout.addWidget(self.input_desc)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_save = QPushButton("Hinzufügen")
        self.btn_save.clicked.connect(self.speichern)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

    def speichern(self):
        name = self.input_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Fehler", "Bitte einen Namen eingeben.")
            return

        desc = self.input_desc.toPlainText()

        conn = get_conn()
        c = conn.cursor()
        try:
            # Score auf 0 und Status auf 'wip' (Work in Progress) als Standardwerte
            c.execute(
                "INSERT INTO gewohnheit (name, beschreibung, score, status) VALUES (?, ?, 70, ?)",
                (name, desc, HABIT_STATUS_GEPLANT)
                )
            conn.commit()
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Fehler", "Fehler beim Speichern der Gewohnheit (Name evtl. schon vorhanden).")
        finally:
            conn.close()
        self.accept()

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
        # Default Effektivität auf 3 (Gelb) setzen
        c.execute(
            'INSERT INTO "maßnahme" (name, gewohnheit_id, beschreibung, effektivitaet, status) VALUES (?, ?, ?, 3, ?)',
            (name, habit_id, desc, MEASURE_STATUS_AKTIV)
            )
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
        self.lade_maßnahmen()
        layout.addWidget(self.combo_massnahme)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_save = QPushButton("Speichern")
        self.btn_save.clicked.connect(self.speichern)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

    def lade_maßnahmen(self):
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
        self.lade_maßnahmen_options()
        layout.addWidget(self.combo_massnahme)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_save = QPushButton("Änderungen speichern")
        self.btn_save.clicked.connect(self.speichern)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

    def lade_maßnahmen_options(self):
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
def set_habit_day(gewohnheit_id: int, datum_iso: str, status: int):
    """Setzt oder aktualisiert den Eintrag für (habit, date). datum_iso = 'YYYY-MM-DD'"""
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO gewohnheit_historie (gewohnheit_id, datum, status, created_at, updated_at)
        VALUES (?, ?, ?, datetime('now'), datetime('now'))
        ON CONFLICT(gewohnheit_id, datum) DO UPDATE
          SET status = excluded.status,
              updated_at = datetime('now')
    """, (gewohnheit_id, datum_iso, int(status)))
    conn.commit()
    conn.close()

def get_habit_day(gewohnheit_id: int, datum_iso: str) -> int | None:
    """Gibt 0/1 zurück oder None wenn kein Eintrag existiert."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT status FROM gewohnheit_historie WHERE gewohnheit_id = ? AND datum = ?", (gewohnheit_id, datum_iso))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def get_habit_history(gewohnheit_id: int, start_iso: str, end_iso: str) -> list[Tuple[str,int]]:
    """Gibt Liste (datum_iso, status) ORDER BY datum zurück."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT datum, status FROM gewohnheit_historie
        WHERE gewohnheit_id = ? AND datum BETWEEN ? AND ?
        ORDER BY datum
    """, (gewohnheit_id, start_iso, end_iso))
    rows = c.fetchall()
    conn.close()
    return rows

HABIT_STATUS_GEPLANT = "geplant"
HABIT_STATUS_WIP = "wip"
HABIT_STATUS_IMPL = "implementiert"

MEASURE_STATUS_AKTIV = "aktiv"
MEASURE_STATUS_GEPLANT = "geplant"
MEASURE_STATUS_AUSSER_KRAFT = "ausser_kraft"

def set_habit_status(habit_id: int, status: str) -> bool:
    """
    Setzt den Status einer Gewohnheit.
    Falls gewohnheit.status ein FOREIGN KEY ist, wird der Statuswert
    vorher in die Referenz-Tabelle eingetragen (INSERT OR IGNORE).
    Gibt True/False zurück statt zu crashen.
    """
    conn = get_conn()
    try:
        c = conn.cursor()

        # Prüfen, ob "status" ein Foreign Key ist
        fk = c.execute('PRAGMA foreign_key_list("gewohnheit")').fetchall()
        status_fk = next((r for r in fk if r[3] == "status"), None)

        if status_fk:
            ref_table = status_fk[2]  # Referenz-Tabelle
            ref_col = status_fk[4]    # Referenz-Spalte (meist "status" oder "name")

            # Falls Referenzspalte leer/unbrauchbar ist, fallback auf "name"/"status"
            cols = [r[1] for r in c.execute(f'PRAGMA table_info("{ref_table}")').fetchall()]
            if ref_col not in cols:
                if "status" in cols:
                    ref_col = "status"
                elif "name" in cols:
                    ref_col = "name"

            # Statuswert sicherstellen (wichtig für "implementiert")
            if ref_col in cols:
                c.execute(
                    f'INSERT OR IGNORE INTO "{ref_table}"("{ref_col}") VALUES (?)',
                    (status,)
                )

        # Jetzt Status in gewohnheit setzen
        c.execute('UPDATE "gewohnheit" SET status=? WHERE id=?', (status, habit_id))
        conn.commit()
        return True

    except sqlite3.IntegrityError:
        conn.rollback()
        return False
    finally:
        conn.close()

def set_measure_status(measure_id: int, status: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute('UPDATE "maßnahme" SET status=? WHERE id=?', (status, measure_id))
    conn.commit()
    conn.close()

def iso_week_year(qdate: QDate) -> tuple[int, int]:
    # PyQt liefert typischerweise (week, year)
    week, year = qdate.weekNumber()
    return int(week), int(year)

def monday_of_week(qdate: QDate) -> QDate:
    # Monday = 1 ... Sunday = 7
    return qdate.addDays(1 - qdate.dayOfWeek())

def week_dates(qdate: QDate) -> list[QDate]:
    mon = monday_of_week(qdate)
    return [mon.addDays(i) for i in range(7)]

def upsert_weekly_reflection(habit_id: int, iso_year: int, iso_week: int, text: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO weekly_review (gewohnheit_id, iso_year, iso_week, reflection, created_at, updated_at)
        VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
        ON CONFLICT(gewohnheit_id, iso_year, iso_week) DO UPDATE
            SET reflection=excluded.reflection,
                updated_at=datetime('now')
    """, (habit_id, iso_year, iso_week, text))
    conn.commit()
    conn.close()

def get_weekly_reflection(habit_id: int, iso_year: int, iso_week: int) -> str:
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT reflection FROM weekly_review
        WHERE gewohnheit_id=? AND iso_year=? AND iso_week=?
    """, (habit_id, iso_year, iso_week))
    row = c.fetchone()
    conn.close()
    return row[0] if row and row[0] else ""

def get_old_weekly_reflections(habit_id: int, iso_year: int, iso_week: int, limit: int = 3) -> list[tuple[int,int,str]]:
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT iso_year, iso_week, reflection
        FROM weekly_review
        WHERE gewohnheit_id=?
          AND (iso_year < ? OR (iso_year = ? AND iso_week < ?))
        ORDER BY iso_year DESC, iso_week DESC
        LIMIT ?
    """, (habit_id, iso_year, iso_year, iso_week, limit))
    rows = c.fetchall()
    conn.close()
    return [(int(y), int(w), r or "") for (y, w, r) in rows]
# -------------------------
# Ansichten
# -------------------------

class GewohnheitenAnsicht(QWidget):
    habit_clicked = pyqtSignal(int)
    habit_deleted = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        
        # Header Links (Titel + Button)
        header_left = QHBoxLayout()
        label_g = QLabel("Alle Gewohnheiten")
        font = QFont(); font.setBold(True); font.setPointSize(12)
        label_g.setFont(font)
        header_left.addWidget(label_g)
        header_left.addStretch()
        self.btn_add_g = QPushButton("Gewohnheit hinzufügen")
        self.btn_add_g.clicked.connect(self.open_add_habit_dialog)
        header_left.addWidget(self.btn_add_g)
        layout.addLayout(header_left)
        
        self.list_widget_gewohnheit = QListWidget()
        layout.addWidget(self.list_widget_gewohnheit)
        self.list_widget_gewohnheit.itemClicked.connect(self.on_item_clicked)
        self.list_widget_gewohnheit.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget_gewohnheit.customContextMenuRequested.connect(self.show_context_menu)
        self.lade_gewohnheiten()

    def open_add_habit_dialog(self):
        dlg = GewohnheitHinzufuegenDialog(self)
        if dlg.exec_() == QDialog.Accepted:
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
        if not item:
            return
        habit_id = item.data(Qt.UserRole)
        
        menu = QMenu(self)
        
        act_rename = menu.addAction("Neu benennen")
        status_menu = menu.addMenu("Status setzen")
        act_geplant = status_menu.addAction("geplant")
        act_wip = status_menu.addAction("wip")
        act_impl = status_menu.addAction("implementiert")
        
        menu.addSeparator()
        act_delete = menu.addAction("Löschen")
        
        action = menu.exec_(self.list_widget_gewohnheit.mapToGlobal(pos))
        if action == act_rename:
            self.rename_habit(habit_id)
        elif action == act_delete:
            self.delete_habit(habit_id)
        elif action == act_geplant:
            set_habit_status(habit_id, HABIT_STATUS_GEPLANT)
            self.lade_gewohnheiten()
        elif action == act_wip:
            set_habit_status(habit_id, HABIT_STATUS_WIP)
            self.lade_gewohnheiten()
        elif action == act_impl:
            set_habit_status(habit_id, HABIT_STATUS_IMPL)
            self.lade_gewohnheiten()

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
        reply = QMessageBox.question(
            self,
            "Löschen",
            "Gewohnheit und Maßnahmen wirklich löschen?",
            QMessageBox.Yes | QMessageBox.No
            )
        if reply != QMessageBox.Yes:
            return
    
        conn = get_conn()
        try:
            c = conn.cursor()
    
            # 1) abhängige Daten löschen (wichtig wegen FK!)
            c.execute("DELETE FROM gewohnheit_historie WHERE gewohnheit_id = ?", (habit_id,))
            c.execute("DELETE FROM weekly_review WHERE gewohnheit_id = ?", (habit_id,))  # falls kein CASCADE greift
    
            # 2) Todos löschen, die an Maßnahmen dieser Gewohnheit hängen
            c.execute("""
                DELETE FROM todo
                WHERE massnahme_id IN (SELECT id FROM "maßnahme" WHERE gewohnheit_id = ?)
            """, (habit_id,))
    
            # 3) Maßnahmen löschen
            c.execute('DELETE FROM "maßnahme" WHERE gewohnheit_id = ?', (habit_id,))
    
            # 4) Gewohnheit löschen
            c.execute('DELETE FROM "gewohnheit" WHERE id = ?', (habit_id,))
    
            conn.commit()
    
        except sqlite3.IntegrityError as e:
            conn.rollback()
            QMessageBox.critical(self, "DB-Fehler", f"Löschen fehlgeschlagen:\n\n{e}")
            return
        finally:
            conn.close()
    
        self.lade_gewohnheiten()
        self.habit_deleted.emit(habit_id)


class maßnahmenAnsicht(QWidget):
    measure_clicked = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        # Hauptlayout ist horizontal geteilt
        main_layout = QHBoxLayout(self)

        # --- LINKER BEREICH: maßnahmen Liste ---
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 10, 0)

        # Header Links
        header_left = QHBoxLayout()
        label_m = QLabel("Alle maßnahmen")
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

        self.lade_maßnahmen()
        self.lade_todos()

    # --- Methoden für maßnahmen (Links) ---
    def open_add_measure_dialog(self):
        dlg = MassnahmeHinzufuegenDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            self.lade_maßnahmen()

    def on_measure_item_clicked(self, item):
        mid = item.data(Qt.UserRole)
        if mid is not None:
            self.measure_clicked.emit(mid)

    def lade_maßnahmen(self):
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT id, name FROM maßnahme ORDER BY id")
        zeilen = c.fetchall()
        self.list_widget_massnahme.blockSignals(True)
        self.list_widget_massnahme.clear()
        for mid, name in zeilen:
            item = QListWidgetItem(name)
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
            self.lade_maßnahmen()

    def delete_measure(self, measure_id: int):
        reply = QMessageBox.question(self, "Löschen", "Maßnahme löschen? Zugehörige Todos werden auch gelöscht.", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            conn = get_conn()
            c = conn.cursor()
            c.execute("DELETE FROM todo WHERE massnahme_id = ?", (measure_id,))
            c.execute("DELETE FROM maßnahme WHERE id = ?", (measure_id,))
            conn.commit()
            conn.close()
            self.lade_maßnahmen()
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

        self.lbl_title = QLabel("maßnahmen Name")
        font = QFont(); font.setBold(True); font.setPointSize(12)
        self.lbl_title.setFont(font)
        header_layout.addWidget(self.lbl_title)
        header_layout.addStretch()
        
        self.btn_delete = QPushButton("Löschen")
        self.btn_delete.setStyleSheet("background-color: #ff4d4d; color: white; font-weight: bold;")
        self.btn_delete.clicked.connect(self.loesche_massnahme)
        header_layout.addWidget(self.btn_delete)
        layout.addLayout(header_layout)

        # Zugeordnete Gewohnheit ändern (Dropdown)
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
            
        # maßnahmendaten laden
        c.execute("""
            SELECT name, gewohnheit_id, beschreibung, effektivitaet 
            FROM maßnahme 
            WHERE id = ?
        """, (self.current_measure_id,))
        
        result = c.fetchone()
        conn.close()

        if result:
            name, gewohnheit_id, beschreibung, effektivitaet = result
            self.lbl_title.setText(name)
            
            # ComboBox auf aktuell zugeordnete Gewohnheit setzen
            idx = self.combo_habit.findData(gewohnheit_id)
            if idx >= 0:
                self.combo_habit.setCurrentIndex(idx)
                
            self.txt_beschreibung.setText(beschreibung if beschreibung else "")
            
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
        self.current_habit_id = 1
        self.score = 0
        self.status = "wip"
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

        left_layout.addWidget(QLabel("Zugehörige maßnahmen:"))
        self.list_details = QListWidget()
        left_layout.addWidget(self.list_details)
        content_layout.addLayout(left_layout, stretch=1) 

        right_layout = QVBoxLayout()

        self.scorelabel = QLabel(f"Score: {self.score}%")
        right_layout.addWidget(self.scorelabel)

        self.statuslabel = QLabel(f"Status: {self.status}")
        right_layout.addWidget(self.statuslabel)

        right_layout.addWidget(QLabel("Kalender:"))
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setMaximumSize(350, 250)
        self.calendar.clicked.connect(self.on_calendar_clicked)
        right_layout.addWidget(self.calendar, alignment=Qt.AlignTop)
        content_layout.addLayout(right_layout, stretch=1)
        layout.addLayout(content_layout)

    def update_score(self):
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT score FROM gewohnheit WHERE id = ?", (self.current_habit_id,))
        row = c.fetchone()
        conn.close()
    
        if not row:
            self.score = 0
            self.scorelabel.setText("Score: —")
            return
    
        self.score = row[0]
        self.scorelabel.setText(f"Score: {self.score}%")

    def update_status(self):
        conn = get_conn()
        c = conn.cursor()
        row = c.execute('SELECT status FROM "gewohnheit" WHERE id=?', (self.current_habit_id,)).fetchone()
        conn.close()
        self.status = row[0] if row else "wip"
        self.statuslabel.setText(f"Status: {self.status}")

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

        c.execute("SELECT id, name FROM maßnahme WHERE gewohnheit_id = ? ORDER BY id", (self.current_habit_id,))
        zeilen = c.fetchall()
        self.list_details.blockSignals(True)
        self.list_details.clear()
        if not zeilen:
            info = QListWidgetItem("Keine maßnahmen gefunden.")
            info.setFlags(Qt.NoItemFlags)
            self.list_details.addItem(info)
        else:
            for mid, name in zeilen:
                item = QListWidgetItem(name)
                item.setData(Qt.UserRole, mid)
                self.list_details.addItem(item)
        self.list_details.blockSignals(False)
        conn.close()

    def speichere_beschreibung(self):
        if self.current_habit_id is None: return
        text = self.txt_beschreibung.toPlainText()
        conn = get_conn()
        c = conn.cursor()
        c.execute("UPDATE gewohnheit SET beschreibung = ? WHERE id = ?", (text, self.current_habit_id))
        conn.commit()
        conn.close()


# -------------------------
# MAIN WINDOW
    def calculate_score(self,habit_id):
        MainWindow.calculate_score(self,habit_id)

    def on_calendar_clicked(self, qdate: QDate):
        if self.current_habit_id is None:
            return
        datum_iso = qdate.toString("yyyy-MM-dd")
        current = get_habit_day(self.current_habit_id, datum_iso)  # None / 0 / 1

        # Einfacher Dialog: Yes = gemacht, No = nicht gemacht, Cancel = nichts
        msg = QMessageBox(self)
        msg.setWindowTitle(qdate.toString("dd.MM.yyyy"))
        msg.setText("Markiere diesen Tag für die Gewohnheit:")
        btn_yes = msg.addButton("Gemacht", QMessageBox.YesRole)
        btn_no = msg.addButton("Nicht gemacht", QMessageBox.NoRole)
        btn_delete = msg.addButton("Eintrag löschen", QMessageBox.DestructiveRole)
        msg.addButton("Abbrechen", QMessageBox.RejectRole)
        msg.exec_()

        clicked = msg.clickedButton()
        if clicked == btn_yes:
            set_habit_day(self.current_habit_id, datum_iso, 1)
        elif clicked == btn_no:
            set_habit_day(self.current_habit_id, datum_iso, 0)
        elif clicked == btn_delete:
            # delete entry
            conn = get_conn()
            c = conn.cursor()
            c.execute("DELETE FROM gewohnheit_historie WHERE gewohnheit_id = ? AND datum = ?", (self.current_habit_id, datum_iso))
            conn.commit()
            conn.close()
        else:
            return

        # Nach dem Setzen: Kalender neu formatieren
        self.apply_history_to_calendar_for_current_month()
        self.calculate_score(self.current_habit_id)
        self.update_score()
        self.update_status()

    # Methode zum Laden/Färben:
    def apply_history_to_calendar_for_current_month(self):
        year = self.calendar.yearShown()
        month = self.calendar.monthShown()
        first = QDate(year, month, 1)
        days = first.daysInMonth()
        start_iso = QDate(year, month, 1).toString("yyyy-MM-dd")
        end_iso = QDate(year, month, days).toString("yyyy-MM-dd")

        rows = get_habit_history(self.current_habit_id, start_iso, end_iso)
        # setze zuerst Default-Format (z.B. hellgrau)
        base_fmt = QTextCharFormat()
        base_fmt.setBackground(QColor("#eeeeee"))
        for d in range(1, days + 1):
            self.calendar.setDateTextFormat(QDate(year, month, d), base_fmt)

        for datum_iso, status in rows:
            y, m, d = map(int, datum_iso.split("-"))
            date = QDate(y, m, d)
            fmt = QTextCharFormat()
            if status == 1:
                fmt.setBackground(QColor("#4caf50"))   # grün = gemacht
            else:
                fmt.setBackground(QColor("#ff4d4d"))   # rot = nicht gemacht
            self.calendar.setDateTextFormat(date, fmt)


class KanbanListWidget(QListWidget):
    habits_moved = pyqtSignal(object, str)  # ([habit_ids], new_status)

    def __init__(self, target_status: str, parent=None):
        super().__init__(parent)
        self.target_status = target_status

        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.MoveAction)

    def startDrag(self, supportedActions):
        items = self.selectedItems()
        if not items:
            return
        ids = [str(it.data(Qt.UserRole)) for it in items if it.data(Qt.UserRole) is not None]
        if not ids:
            return

        mime = QMimeData()
        mime.setData("application/x-habit-ids", ",".join(ids).encode("utf-8"))

        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec_(Qt.MoveAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-habit-ids"):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-habit-ids"):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if not event.mimeData().hasFormat("application/x-habit-ids"):
            return super().dropEvent(event)
        
        source = event.source()
        raw = bytes(event.mimeData().data("application/x-habit-ids")).decode("utf-8")
        ids = [int(x) for x in raw.split(",") if x.strip().isdigit()]
        
        # nur zwischen Listen verschieben
        if not (isinstance(source, QListWidget) and source is not self):
            event.acceptProposedAction()
            return
        
        moved = []
        for hid in ids:
            # 1) Erst DB updaten
            ok = set_habit_status(hid, self.target_status)
            if not ok:
                continue
            # 2) Dann UI-Item rüberziehen
            for i in range(source.count()):
                it = source.item(i)
                if it and it.data(Qt.UserRole) == hid:
                    taken = source.takeItem(i)
                    self.addItem(taken)
                    moved.append(hid)
                    break
        # 3) Wichtig: moved muss echte IDs enthalten -> damit Weekly-Review reload triggert
        self.habits_moved.emit(moved, self.target_status)
        event.acceptProposedAction()


class KanbanBoardWidget(QWidget):
    habit_status_changed = pyqtSignal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)

        self.col_geplant = KanbanListWidget(HABIT_STATUS_GEPLANT)
        self.col_wip = KanbanListWidget(HABIT_STATUS_WIP)
        self.col_impl = KanbanListWidget(HABIT_STATUS_IMPL)

        for col, title in [
            (self.col_geplant, "geplant"),
            (self.col_wip, "wip"),
            (self.col_impl, "implementiert"),
        ]:
            box = QVBoxLayout()
            lbl = QLabel(title)
            f = QFont(); f.setBold(True)
            lbl.setFont(f)
            box.addWidget(lbl)
            box.addWidget(col)

            w = QWidget()
            w.setLayout(box)
            w.setMinimumWidth(220)
            layout.addWidget(w)

            col.habits_moved.connect(self._on_moved)

        layout.addStretch()

    def _on_moved(self, moved_ids, new_status):
        for hid in moved_ids:
            self.habit_status_changed.emit(int(hid), new_status)

    def reload(self):
        # Listen leeren
        for col in (self.col_geplant, self.col_wip, self.col_impl):
            col.clear()

        conn = get_conn()
        c = conn.cursor()
        c.execute('SELECT id, name, status FROM "gewohnheit" ORDER BY id')
        rows = c.fetchall()
        conn.close()

        for hid, name, status in rows:
            status = status or HABIT_STATUS_WIP
            it = QListWidgetItem(name)
            it.setData(Qt.UserRole, hid)

            if status == HABIT_STATUS_GEPLANT:
                self.col_geplant.addItem(it)
            elif status == HABIT_STATUS_IMPL:
                self.col_impl.addItem(it)
            else:
                self.col_wip.addItem(it)


class HabitReviewCard(QFrame):
    def __init__(self, habit_id: int, parent=None):
        super().__init__(parent)
        self.habit_id = habit_id
        self.setFrameShape(QFrame.Box)
        self.setStyleSheet("QFrame { border: 1px solid #b0b0b0; }")

        self.week, self.year = iso_week_year(QDate.currentDate())
        self._week_days = week_dates(QDate.currentDate())

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._save_reflection)

        outer = QVBoxLayout(self)
        outer.setSpacing(8)

        # Kopfzeile mit Tagen (wie Screenshot)
        days_row = QHBoxLayout()
        days_row.setSpacing(2)
        self.day_labels = []
        for dname in ["MON","TUE","WED","THU","FRI","SAT","SUN"]:
            lbl = QLabel(dname)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setFixedHeight(18)
            lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            lbl.setStyleSheet("background:#e6e6e6; border:1px solid #c8c8c8; font-size:10px;")
            days_row.addWidget(lbl)
        outer.addLayout(days_row)

        self.lbl_title = QLabel("")
        outer.addWidget(self.lbl_title)

        # Letzte Einträge (Farbleiste für die Woche)
        self.entries_row = QHBoxLayout()
        self.entries_row.setSpacing(2)
        self.entry_boxes = []
        for _ in range(7):
            box = QLabel("")
            box.setFixedHeight(14)
            box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            box.setStyleSheet("background:#d9d9d9; border:1px solid #c8c8c8;")
            self.entries_row.addWidget(box)
            self.entry_boxes.append(box)
        outer.addLayout(self.entries_row)

        self.lbl_ref = QLabel(f"Reflektion von KW {self.week}:")
        outer.addWidget(self.lbl_ref)

        self.txt_reflection = QTextEdit()
        self.txt_reflection.setPlaceholderText("Reflektion hier eingeben…")
        self.txt_reflection.setMaximumHeight(90)
        self.txt_reflection.textChanged.connect(self._on_reflection_changed)
        outer.addWidget(self.txt_reflection)

        outer.addWidget(QLabel("alte reviews:"))
        self.txt_old = QTextEdit()
        self.txt_old.setReadOnly(True)
        self.txt_old.setMaximumHeight(90)
        outer.addWidget(self.txt_old)

        outer.addWidget(QLabel("Maßnahmen:"))
        self.list_measures = QListWidget()
        self.list_measures.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_measures.customContextMenuRequested.connect(self._measures_context_menu)
        outer.addWidget(self.list_measures)

        btns = QHBoxLayout()
        self.btn_plan = QPushButton("Maßnahme planen")
        self.btn_disable = QPushButton("Außer Kraft setzen")
        self.btn_plan.clicked.connect(lambda: self._apply_measure_status(MEASURE_STATUS_GEPLANT))
        self.btn_disable.clicked.connect(lambda: self._apply_measure_status(MEASURE_STATUS_AUSSER_KRAFT))
        btns.addWidget(self.btn_plan)
        btns.addWidget(self.btn_disable)
        outer.addLayout(btns)

        self.reload()

    def reload(self):
        # Titel / Score / Status
        conn = get_conn()
        c = conn.cursor()
        c.execute('SELECT name, score, status FROM "gewohnheit" WHERE id=?', (self.habit_id,))
        row = c.fetchone()
        conn.close()
        if not row:
            self.lbl_title.setText("—")
            return

        name, score, status = row
        status = status or HABIT_STATUS_WIP
        self.lbl_title.setText(f"{name}  score: {int(score)}%  status: {status}")

        # Letzte Einträge (Woche) einfärben
        for i, qd in enumerate(self._week_days):
            iso = qd.toString("yyyy-MM-dd")
            st = get_habit_day(self.habit_id, iso)  # None/0/1
            if st == 1:
                color = "#4caf50"
            elif st == 0:
                color = "#ff4d4d"
            else:
                color = "#d9d9d9"
            self.entry_boxes[i].setStyleSheet(f"background:{color}; border:1px solid #c8c8c8;")
            self.entry_boxes[i].setToolTip(qd.toString("dd.MM.yyyy"))

        # Weekly reflection laden
        self.txt_reflection.blockSignals(True)
        self.txt_reflection.setPlainText(get_weekly_reflection(self.habit_id, self.year, self.week))
        self.txt_reflection.blockSignals(False)

        # Alte Reviews
        olds = get_old_weekly_reflections(self.habit_id, self.year, self.week, limit=3)
        old_text = ""
        for y, w, txt in olds:
            short = (txt.strip().replace("\n", " ")[:120] + "…") if len(txt.strip()) > 120 else txt.strip()
            old_text += f"KW {w} ({y}): {short}\n"
        self.txt_old.setPlainText(old_text.strip())

        # Maßnahmen laden
        self.list_measures.clear()
        conn = get_conn()
        c = conn.cursor()
        c.execute('SELECT id, name, status FROM "maßnahme" WHERE gewohnheit_id=? ORDER BY id', (self.habit_id,))
        rows = c.fetchall()
        conn.close()
        for mid, mname, mstatus in rows:
            mstatus = mstatus or MEASURE_STATUS_AKTIV
            it = QListWidgetItem(f"{mname}   [{mstatus}]")
            it.setData(Qt.UserRole, int(mid))
            self.list_measures.addItem(it)

    def _on_reflection_changed(self):
        # debounce autosave
        self._save_timer.start(600)

    def _save_reflection(self):
        text = self.txt_reflection.toPlainText()
        upsert_weekly_reflection(self.habit_id, self.year, self.week, text)

    def _selected_measure_id(self) -> int | None:
        it = self.list_measures.currentItem()
        if not it:
            return None
        return it.data(Qt.UserRole)

    def _apply_measure_status(self, status: str):
        mid = self._selected_measure_id()
        if mid is None:
            return
        set_measure_status(mid, status)
        self.reload()

    def _measures_context_menu(self, pos):
        it = self.list_measures.itemAt(pos)
        if not it:
            return
        mid = it.data(Qt.UserRole)
        menu = QMenu(self)
        act_a = menu.addAction("Aktivieren")
        act_p = menu.addAction("Planen")
        act_x = menu.addAction("Außer Kraft setzen")
        chosen = menu.exec_(self.list_measures.mapToGlobal(pos))
        if chosen == act_a:
            set_measure_status(mid, MEASURE_STATUS_AKTIV)
        elif chosen == act_p:
            set_measure_status(mid, MEASURE_STATUS_GEPLANT)
        elif chosen == act_x:
            set_measure_status(mid, MEASURE_STATUS_AUSSER_KRAFT)
        self.reload()


class WeeklyReviewAnsicht(QWidget):
    back_clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)

        # Header wie Screenshot
        header = QHBoxLayout()
        self.btn_back = QPushButton("←")
        self.btn_back.setFixedSize(40, 40)
        self.btn_back.clicked.connect(self.back_clicked.emit)
        header.addWidget(self.btn_back)

        title = QLabel("Weekly-Review")
        f = QFont(); f.setBold(True); f.setPointSize(12)
        title.setFont(f)
        header.addWidget(title)
        header.addStretch()

        self.btn_add_measure = QPushButton("Maßnahmen hinzufügen")
        self.btn_add_todo = QPushButton("To-Do hinzufügen")
        header.addWidget(self.btn_add_measure)
        header.addWidget(self.btn_add_todo)
        root.addLayout(header)

        # Scrollbarer Bereich mit Karten (3 Spalten Layout)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.cards_widget = QWidget()
        self.grid = QHBoxLayout(self.cards_widget)
        self.grid.setSpacing(12)
        self.scroll.setWidget(self.cards_widget)
        root.addWidget(self.scroll)

        # Kanban Board darunter (zusätzlich, weil du es explizit wolltest)
        root.addSpacing(10)
        root.addWidget(QLabel("Kanban-Board (Drag & Drop):"))
        self.kanban = KanbanBoardWidget()
        root.addWidget(self.kanban)

        self.btn_add_measure.clicked.connect(self._open_add_measure)
        self.btn_add_todo.clicked.connect(self._open_add_todo)
        self.kanban.habit_status_changed.connect(lambda *_: self.reload())

        self.reload()

    def _open_add_measure(self):
        dlg = MassnahmeHinzufuegenDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            self.reload()

    def _open_add_todo(self):
        dlg = TodoHinzufuegenDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            self.reload()

    def reload(self):
        # Karten leeren
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        # nur WIP Gewohnheiten anzeigen
        conn = get_conn()
        c = conn.cursor()
        c.execute('SELECT id FROM "gewohnheit" WHERE status=? ORDER BY id', (HABIT_STATUS_WIP,))
        ids = [r[0] for r in c.fetchall()]
        conn.close()

        for hid in ids:
            card = HabitReviewCard(hid)
            card.setMinimumWidth(280)
            self.grid.addWidget(card)

        self.grid.addStretch()

        # Kanban reload (alle Status)
        self.kanban.reload()
# -------------------------
# Main Window
# -------------------------

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        setup_test_database()
        ensure_database_columns() # 

        self.btn_gewohnheiten = QPushButton("Gewohnheiten")
        self.btn_maßnahmen = QPushButton("Alle maßnahmen")
        self.btn_weekly = QPushButton("Weekly-Review")
        
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        self.setWindowTitle("Gewohnheit Tracker")
        self.resize(1000, 700) # Etwas breiter für die zweigeteilte Ansicht
        
        self.stack = QStackedWidget()
        
        self.view_gewohnheiten = GewohnheitenAnsicht()
        self.view_maßnahmen = maßnahmenAnsicht() 
        self.view_detail = DetailAnsicht()
        self.view_measure_detail = MassnahmeDetailAnsicht()
        self.view_weekly = WeeklyReviewAnsicht()
        
        self.stack.addWidget(self.view_gewohnheiten)     # Index 0
        self.stack.addWidget(self.view_maßnahmen)       # Index 1
        self.stack.addWidget(self.view_detail)           # Index 2
        self.stack.addWidget(self.view_measure_detail)   # Index 3
        self.stack.addWidget(self.view_weekly)           # Index 4

        sidebar_layout = QVBoxLayout()
        sidebar_layout.addWidget(self.btn_gewohnheiten)
        sidebar_layout.addWidget(self.btn_maßnahmen)
        sidebar_layout.addWidget(self.btn_weekly)
        sidebar_layout.addStretch()

        main_layout = QHBoxLayout(self)
        main_layout.addLayout(sidebar_layout)
        main_layout.addWidget(self.stack)

    def connect_signals(self):
        # Sidebar Navigation
        self.btn_gewohnheiten.clicked.connect(lambda: self.stack.setCurrentWidget(self.view_gewohnheiten))
        
        # Hilfsfunktion, um die Maßnahmen-Ansicht sauber zu laden und anzuzeigen
        def open_massnahmen_view():
            self.view_maßnahmen.lade_maßnahmen()
            self.view_maßnahmen.lade_todos()
            self.stack.setCurrentWidget(self.view_maßnahmen)
            
        self.btn_maßnahmen.clicked.connect(open_massnahmen_view)
        
        # Gewohnheiten Logik
        self.view_gewohnheiten.habit_clicked.connect(self.open_detail_view)
        self.view_gewohnheiten.habit_deleted.connect(self.on_habit_deleted)
        self.view_detail.back_clicked.connect(lambda: {
            self.view_maßnahmen.lade_maßnahmen(), 
            self.stack.setCurrentWidget(self.view_gewohnheiten)
        })

        # maßnahmen Logik
        self.view_maßnahmen.measure_clicked.connect(self.open_measure_detail)
        self.view_measure_detail.back_clicked.connect(lambda: {
            self.view_maßnahmen.lade_maßnahmen(), 
            self.stack.setCurrentWidget(self.view_maßnahmen)
        })
        self.view_measure_detail.measure_deleted.connect(lambda: {
            self.view_maßnahmen.lade_maßnahmen(),
            self.view_maßnahmen.lade_todos()
        })
        def open_weekly_view():
            self.view_weekly.reload()
            self.stack.setCurrentWidget(self.view_weekly)
        self.btn_weekly.clicked.connect(open_weekly_view)
        self.view_weekly.back_clicked.connect(lambda: self.stack.setCurrentWidget(self.view_gewohnheiten))

    def calculate_score(self, habit_id):
        conn = get_conn()
        c = conn.cursor()
        rows = c.execute("""
                         SELECT status
                         FROM gewohnheit_historie
                         WHERE gewohnheit_id = ?;
        """, (habit_id,)).fetchall()
        werte = [row[0] for row in rows if row[0] in (0, 1)]
        
        score = int((sum(werte) / len(werte)) * 100) if len(werte) > 0 else 70
        
        c.execute("""
                  UPDATE gewohnheit
                  SET score = ?
                  WHERE id = ?
        """, (score, habit_id))
        conn.commit()
        conn.close()
        
    def open_detail_view(self, habit_id):
        self.view_detail.set_habit(habit_id)
        self.stack.setCurrentWidget(self.view_detail)
        self.view_detail.update_score()
        self.view_detail.update_status()
        self.view_detail.apply_history_to_calendar_for_current_month()
        
    def open_measure_detail(self, measure_id):
        self.view_measure_detail.set_measure(measure_id)
        self.stack.setCurrentWidget(self.view_measure_detail)
        
    def on_habit_deleted(self, habit_id: int):
        # Wenn gerade die gelöschte Gewohnheit offen ist, zurück zur Liste
        if self.stack.currentWidget() == self.view_detail and self.view_detail.current_habit_id == habit_id:
            self.stack.setCurrentWidget(self.view_gewohnheiten)
    
        # Listen/Ansichten aktualisieren
        self.view_gewohnheiten.lade_gewohnheiten()
        self.view_maßnahmen.lade_maßnahmen()
        self.view_maßnahmen.lade_todos()
    
        # Weekly/Kanban aktualisieren
        if hasattr(self, "view_weekly"):
            self.view_weekly.reload()
            
if __name__ == "__main__":
    setup_test_database()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())