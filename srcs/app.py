# main.py
import sys
from PyQt5.QtWidgets import QApplication
# Używamy względnego importu
from main_window import MainWindow

if __name__ == "__main__":
    # Poprawka dla niektórych środowisk Wayland/X11
    # QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    # QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # Ustawienie zmiennej środowiskowej może pomóc z niektórymi błędami renderowania
    # import os
    # os.environ['QT_QPA_PLATFORM'] = 'xcb' # lub 'wayland', w zależności od systemu

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    try:
        sys.exit(app.exec_())
    except SystemError as e:
         print(f"Caught SystemError during app exit: {e}")
         # Ten błąd podczas zamykania może czasem wystąpić w złożonych aplikacjach Qt,
         # często związany z czyszczeniem zasobów. Powyższe poprawki powinny go minimalizować.