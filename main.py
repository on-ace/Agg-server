import sys
from PyQt5.QtWidgets import QApplication
from gui.main_window import AggServerWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = AggServerWindow()
    window.show()
    sys.exit(app.exec_())