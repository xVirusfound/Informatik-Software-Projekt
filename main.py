import sys
import sqlite3
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel,
    QVBoxLayout, QHBoxLayout, QListWidget,
    QStackedWidget, QTextEdit, QListWidgetItem,
    QCalendarWidget,
    QMenu, QInputDialog, QMessageBox,
    QDialog
)
from PyQt5.QtCore import Qt, pyqtSignal, QDate
from PyQt5.QtGui import QFont, QTextCharFormat, QColor
from datenbanksetup import setup_test_database, get_conn
# -------------------------
# SCORE-LOGIK (vorerst Dummy)
# -------------------------

def weakly_score_berechnen() -> int:
    # TODO: später echte Berechnung
    return 67

# Demo-Daten für Tages-Scores (damit du Farben siehst)
_DEMO_DAY_SCORES = {
    QDate.currentDate().addDays(-0): 72,
    QDate.currentDate().addDays(-1): 58,
    QDate.currentDate().addDays(-2): 33,
    QDate.currentDate().addDays(-3): 12,
    QDate.currentDate().addDays(-4): 85,
}

def tages_score_berechnen(date: QDate):
    # TODO: später echte Berechnung
    # None bedeutet: kein Tages-Score -> Kalender bleibt hellgrau
    return _DEMO_DAY_SCORES.get(date, None)

def score_to_color(score: int) -> str:
    # Farben nach deinen Bereichen
    if 1 <= score <= 20:
        return "#ff4d4d"   # rot
    if 21 <= score <= 40:
        return "#ffa500"   # orange
    if 41 <= score <= 60:
        return "#ffd84d"   # gelb
    if 61 <= score <= 80:
        return "#4caf50"   # grün
    if 81 <= score <= 99:
        return "#006400"   # dunkelgrün
    return "#d9d9d9"       # fallback hellgrau


class ScoreCircle(QWidget):
    """Kleiner Kreis mit Zahl drin + Hintergrundfarbe je nach Score."""
    def __init__(self, score: int = 67, size: int = 120, parent=None):
        super().__init__(parent)
        self._size = size

        self.label = QLabel("", self)
        self.label.setAlignment(Qt.AlignCenter)

        font = QFont()
        font.setBold(True)
        font.setPointSize(18)
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
        self.setStyleSheet(
            f"background-color: {color}; border-radius: {radius}px;"
        )
class StatistikDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Statistiken")
        self.resize(500, 300)

        layout = QVBoxLayout(self)
        title = QLabel("Statistik:")
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
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

        # Überschrift
        title = QLabel("Dein Tagesscore:")
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        title.setFont(font)
        layout.addWidget(title)

        score = tages_score_berechnen(date)
        if score is None:
            # falls kein score vorhanden
            score = 67  # Dummy, solange in Arbeit
            hint = QLabel("(Tages-Score: noch in Arbeit – aktuell Dummy-Wert)")
            hint.setStyleSheet("color: gray;")
            layout.addWidget(hint)

        circle = ScoreCircle(score=score, size=110)
        layout.addWidget(circle, alignment=Qt.AlignLeft)

        # Listen: später befüllen
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


# --- Ansichten ---

class GewohnheitenAnsicht(QWidget):
    habit_clicked = pyqtSignal(int)  # ID statt Name
    habit_deleted = pyqtSignal(int)  # damit MainWindow reagieren kann

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        self.list_widget_gewohnheit = QListWidget()
        layout.addWidget(self.list_widget_gewohnheit)

        self.list_widget_gewohnheit.itemClicked.connect(self.on_item_clicked)

        # Rechtsklick-Menü
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
        if not item:
            return

        habit_id = item.data(Qt.UserRole)
        if habit_id is None:
            return

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
        if not row:
            return
        old_name = row[0]

        new_name, ok = QInputDialog.getText(self, "Gewohnheit umbenennen", "Neuer Name:", text=old_name)
        new_name = new_name.strip() if new_name else ""

        if not ok or not new_name or new_name == old_name:
            return

        conn = get_conn()
        c = conn.cursor()
        try:
            c.execute("UPDATE gewohnheit SET name = ? WHERE id = ?", (new_name, habit_id))
            conn.commit()
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Name existiert schon", "Es gibt bereits eine Gewohnheit mit diesem Namen.")
        finally:
            conn.close()

        self.lade_gewohnheiten()

    def delete_habit(self, habit_id: int):
        reply = QMessageBox.question(
            self,
            "Gewohnheit löschen",
            "Willst du diese Gewohnheit wirklich löschen?\nAlle dazugehörigen Maßnahmen werden ebenfalls gelöscht.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        conn = get_conn()
        c = conn.cursor()

        # Erst Maßnahmen löschen, dann Gewohnheit
        c.execute("DELETE FROM maßnahme WHERE gewohnheit_id = ?", (habit_id,))
        c.execute("DELETE FROM gewohnheit WHERE id = ?", (habit_id,))
        conn.commit()
        conn.close()

        self.lade_gewohnheiten()
        self.habit_deleted.emit(habit_id)


class MaßnahmenAnsicht(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        label = QLabel("Alle Maßnahmen (Gesamtübersicht)")
        layout.addWidget(label)

        self.list_widget_maßnahme = QListWidget()
        layout.addWidget(self.list_widget_maßnahme)

        # Rechtsklick-Menü
        self.list_widget_maßnahme.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget_maßnahme.customContextMenuRequested.connect(self.show_context_menu)

        self.lade_maßnahmen()

    def lade_maßnahmen(self):
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT id, name FROM maßnahme ORDER BY id")
        zeilen = c.fetchall()

        self.list_widget_maßnahme.clear()
        for mid, name in zeilen:
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, mid)
            self.list_widget_maßnahme.addItem(item)

        conn.close()

    def show_context_menu(self, pos):
        item = self.list_widget_maßnahme.itemAt(pos)
        if not item:
            return
        measure_id = item.data(Qt.UserRole)
        if measure_id is None:
            return

        menu = QMenu(self)
        act_rename = menu.addAction("Neu benennen")
        act_delete = menu.addAction("Löschen")

        action = menu.exec_(self.list_widget_maßnahme.mapToGlobal(pos))
        if action == act_rename:
            self.rename_measure(measure_id)
        elif action == act_delete:
            self.delete_measure(measure_id)

    def rename_measure(self, measure_id: int):
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT name FROM maßnahme WHERE id = ?", (measure_id,))
        row = c.fetchone()
        conn.close()
        if not row:
            return
        old_name = row[0]

        new_name, ok = QInputDialog.getText(self, "Maßnahme umbenennen", "Neuer Name:", text=old_name)
        new_name = new_name.strip() if new_name else ""

        if not ok or not new_name or new_name == old_name:
            return

        conn = get_conn()
        c = conn.cursor()
        c.execute("UPDATE maßnahme SET name = ? WHERE id = ?", (new_name, measure_id))
        conn.commit()
        conn.close()

        self.lade_maßnahmen()

    def delete_measure(self, measure_id: int):
        reply = QMessageBox.question(
            self,
            "Maßnahme löschen",
            "Willst du diese Maßnahme wirklich löschen?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        conn = get_conn()
        c = conn.cursor()
        c.execute("DELETE FROM maßnahme WHERE id = ?", (measure_id,))
        conn.commit()
        conn.close()

        self.lade_maßnahmen()


class DetailAnsicht(QWidget):
    back_clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.current_habit_id = None
        
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
        left_layout.addWidget(QLabel("Zugehörige Maßnahmen:"))
        self.list_details = QListWidget()
        
        # Rechtsklick-Menü für Maßnahmen in der Detailansicht
        self.list_details.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_details.customContextMenuRequested.connect(self.show_measure_menu)

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
        
    def set_habit(self, habit_id: int):
        self.current_habit_id = habit_id
        self.lade_daten()

    def lade_daten(self):
        if self.current_habit_id is None:
            return

        conn = get_conn()
        c = conn.cursor()

        c.execute("SELECT name, beschreibung FROM gewohnheit WHERE id = ?", (self.current_habit_id,))
        result = c.fetchone()
        if result:
            name, beschreibung = result
            self.lbl_title.setText(name)
            if beschreibung:
                self.txt_beschreibung.setText(beschreibung)
            else:
                self.txt_beschreibung.clear()
        else:
            conn.close()
            return

        c.execute(
            "SELECT id, name, erledigt FROM maßnahme WHERE gewohnheit_id = ? ORDER BY id",
            (self.current_habit_id,)
        )
        zeilen = c.fetchall()

        self.list_details.blockSignals(True)
        self.list_details.clear()

        if not zeilen:
            info = QListWidgetItem("Keine Maßnahmen gefunden.")
            info.setFlags(Qt.NoItemFlags)  # nicht anklickbar / nicht editierbar
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
        measure_id = item.data(Qt.UserRole)
        new_state = 1 if item.checkState() == Qt.Checked else 0
        if measure_id is not None:
            conn = get_conn()
            c = conn.cursor()
            c.execute("UPDATE maßnahme SET erledigt = ? WHERE id = ?", (new_state, measure_id))
            conn.commit()
            conn.close()

            
    def show_measure_menu(self, pos):
        item = self.list_details.itemAt(pos)
        if not item:
            return

        measure_id = item.data(Qt.UserRole)
        if measure_id is None:
            return  # "Keine Maßnahmen gefunden." etc.

        menu = QMenu(self)
        act_rename = menu.addAction("Neu benennen")
        act_delete = menu.addAction("Löschen")

        action = menu.exec_(self.list_details.mapToGlobal(pos))
        if action == act_rename:
            self.rename_measure(measure_id)
        elif action == act_delete:
            self.delete_measure(measure_id)

    def rename_measure(self, measure_id: int):
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT name FROM maßnahme WHERE id = ?", (measure_id,))
        row = c.fetchone()
        conn.close()
        if not row:
            return

        old_name = row[0]
        new_name, ok = QInputDialog.getText(self, "Maßnahme umbenennen", "Neuer Name:", text=old_name)
        new_name = new_name.strip() if new_name else ""

        if not ok or not new_name or new_name == old_name:
            return

        conn = get_conn()
        c = conn.cursor()
        c.execute("UPDATE maßnahme SET name = ? WHERE id = ?", (new_name, measure_id))
        conn.commit()
        conn.close()

        self.lade_daten()

    def delete_measure(self, measure_id: int):
        reply = QMessageBox.question(
            self,
            "Maßnahme löschen",
            "Willst du diese Maßnahme wirklich löschen?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        conn = get_conn()
        c = conn.cursor()
        c.execute("DELETE FROM maßnahme WHERE id = ?", (measure_id,))
        conn.commit()
        conn.close()

        self.lade_daten()


    def speichere_beschreibung(self):
        if self.current_habit_id is None:
            return
        text = self.txt_beschreibung.toPlainText()

        conn = get_conn()
        c = conn.cursor()
        try:
            c.execute(
                "UPDATE gewohnheit SET beschreibung = ? WHERE id = ?",
                (text, self.current_habit_id)
            )
            conn.commit()
            print("Beschreibung gespeichert.")
        except Exception as e:
            print("Fehler:", e)
        finally:
            conn.close()

class WochenAnsicht(QWidget):
    def __init__(self):
        super().__init__()

        root = QVBoxLayout(self)

        # ---------- TOP: Score (links) + Review/Buttons (rechts) ----------
        top = QHBoxLayout()

        # links: Score
        left = QVBoxLayout()
        lbl = QLabel("Dein Wochenscore:")
        f = QFont(); f.setBold(True); f.setPointSize(12)
        lbl.setFont(f)
        left.addWidget(lbl)

        self.week_circle = ScoreCircle(score=weakly_score_berechnen(), size=130)
        left.addWidget(self.week_circle, alignment=Qt.AlignLeft)
        left.addStretch()

        # rechts: Review + Buttons
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

        # ---------- BOTTOM: Kalender volle Breite ----------
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
        """Setzt alle Tage im sichtbaren Monat auf hellgrau,
        und überschreibt Tage mit Score farbig."""
        if year is None or month is None:
            year = self.calendar.yearShown()
            month = self.calendar.monthShown()

        # 1) Default: hellgrau für alle Tage im Monat
        base_fmt = QTextCharFormat()
        base_fmt.setBackground(QColor("#eeeeee"))  # hellgrau

        first = QDate(year, month, 1)
        days = first.daysInMonth()
        for d in range(1, days + 1):
            self.calendar.setDateTextFormat(QDate(year, month, d), base_fmt)

        # 2) Score-Tage farbig
        for d in range(1, days + 1):
            date = QDate(year, month, d)
            score = tages_score_berechnen(date)
            if score is None:
                continue
            fmt = QTextCharFormat()
            fmt.setBackground(QColor(score_to_color(score)))
            self.calendar.setDateTextFormat(date, fmt)


# --- Main Window ---

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.btn_gewohnheiten = QPushButton("Gewohnheiten")
        self.btn_maßnahmen = QPushButton("Alle Maßnahmen")
        self.btn_wochenanzeige = QPushButton("Wochenanzeige")

        
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        self.setWindowTitle("Gewohnheit Tracker")
        self.resize(800, 600) 
        
        self.stack = QStackedWidget()
        
        self.view_gewohnheiten = GewohnheitenAnsicht()
        self.view_maßnahmen = MaßnahmenAnsicht()
        self.view_detail = DetailAnsicht()
        self.view_wochen = WochenAnsicht()
        
        self.stack.addWidget(self.view_gewohnheiten)
        self.stack.addWidget(self.view_maßnahmen)
        self.stack.addWidget(self.view_detail)
        self.stack.addWidget(self.view_wochen)


        sidebar_layout = QVBoxLayout()
        
        sidebar_layout.addWidget(self.btn_gewohnheiten)
        sidebar_layout.addWidget(self.btn_maßnahmen)
        sidebar_layout.addWidget(self.btn_wochenanzeige)
        sidebar_layout.addStretch()

        main_layout = QHBoxLayout(self)
        main_layout.addLayout(sidebar_layout)
        main_layout.addWidget(self.stack)

    def connect_signals(self):
        self.btn_gewohnheiten.clicked.connect(lambda: self.stack.setCurrentWidget(self.view_gewohnheiten))
        self.btn_maßnahmen.clicked.connect(lambda: self.stack.setCurrentWidget(self.view_maßnahmen))
        self.btn_wochenanzeige.clicked.connect(self.show_wochenanzeige)
        
        self.view_gewohnheiten.habit_clicked.connect(self.open_detail_view)
        self.view_detail.back_clicked.connect(self.go_back_to_list)

    def open_detail_view(self, habit_id):
        self.view_detail.set_habit(habit_id)
        self.stack.setCurrentWidget(self.view_detail)



    def go_back_to_list(self):
        self.stack.setCurrentWidget(self.view_gewohnheiten)

        
    def on_habit_deleted(self, habit_id: int):
        # Wenn gerade die gelöschte Gewohnheit offen ist, zurück zur Liste
        if self.stack.currentIndex() == 2 and self.view_detail.current_habit_id == habit_id:
            self.stack.setCurrentIndex(0)

        # Gesamtmaßnahmen-Ansicht aktualisieren (weil Maßnahmen mitgelöscht wurden)
        self.view_maßnahmen.lade_maßnahmen()
        
    def show_wochenanzeige(self):
        self.view_wochen.refresh()  # falls du später neu berechnen willst
        self.stack.setCurrentWidget(self.view_wochen)



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
