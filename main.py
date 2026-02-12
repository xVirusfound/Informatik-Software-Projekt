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

        
        self.stack.addWidget(self.view_gewohnheiten)
        self.stack.addWidget(self.view_maßnahmen)
        self.stack.addWidget(self.view_detail)



        sidebar_layout = QVBoxLayout()
        
        sidebar_layout.addWidget(self.btn_gewohnheiten)
        sidebar_layout.addWidget(self.btn_maßnahmen)
        sidebar_layout.addStretch()

        main_layout = QHBoxLayout(self)
        main_layout.addLayout(sidebar_layout)
        main_layout.addWidget(self.stack)

    def connect_signals(self):
        self.btn_gewohnheiten.clicked.connect(lambda: self.stack.setCurrentWidget(self.view_gewohnheiten))
        self.btn_maßnahmen.clicked.connect(lambda: self.stack.setCurrentWidget(self.view_maßnahmen))

        
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
