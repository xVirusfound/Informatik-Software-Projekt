# main.py
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QHBoxLayout
from PyQt5.QtCore import Qt

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.count = 0
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Test App: Button + Counter")
        self.resize(300, 80)

        # Button
        self.button = QPushButton("Klick mich")
        self.button.clicked.connect(self.on_button_clicked)

        # Label (Zahl rechts vom Button)
        self.counter_label = QLabel(str(self.count))
        self.counter_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)  # vertikal zentriert
        self.counter_label.setFixedWidth(40)  # feste Breite, damit es nicht hüpft

        # Layout: Button links, Zahl rechts
        layout = QHBoxLayout()
        layout.addWidget(self.button)
        layout.addWidget(self.counter_label)
        layout.addStretch()  # optional: schiebt Inhalt nach links

        self.setLayout(layout)

    def on_button_clicked(self):
        # erhöht die Zahl um 1 und aktualisiert das Label
        self.count += 1
        self.counter_label.setText(str(self.count))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
