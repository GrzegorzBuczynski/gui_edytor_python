import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QAction, QTabWidget, QWidget,
    QVBoxLayout, QLabel, QToolBar, QPushButton, QFileDialog, QMessageBox,
    QMenuBar
)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Moje Okno z Menu i Zakładkami (Włącz/Wyłącz)')
        self.setGeometry(100, 100, 800, 600)

        # Przechowuje dane o wszystkich zakładkach (widget, tytuł)
        # Klucz: oryginalny indeks (0, 1, 2...), Wartość: (QWidget, str_title)
        self.all_tabs_data = {}
        # Przechowuje akcje menu dla łatwego dostępu
        self.tab_toggle_actions = {}

        # Tworzenie głównego widgetu (TabWidget)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Dodanie 5 zakładek i zapisanie ich danych
        num_tabs = 5
        for i in range(num_tabs):
            tab_widget = QWidget()
            layout = QVBoxLayout()
            label = QLabel(f'To jest zawartość zakładki {i+1}')
            layout.addWidget(label)
            tab_widget.setLayout(layout)
            tab_title = f'Zakładka {i+1}'

            # Zapisz widget i tytuł w słowniku z oryginalnym indeksem jako kluczem
            self.all_tabs_data[i] = (tab_widget, tab_title)

            # Dodaj zakładkę do widżetu zakładek na starcie
            self.tabs.addTab(tab_widget, tab_title)

        # Tworzenie Menu
        self.create_menu()

    def create_menu(self):
        menu_bar = self.menuBar()

        # --- Menu "Plik" ---
        file_menu = menu_bar.addMenu('Plik')
        # ... (reszta kodu menu Plik bez zmian) ...
        open_action = QAction('Otwórz', self)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        save_action = QAction('Zapisz', self)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        exit_action = QAction('Zamknij', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # --- Menu "Narzędzia" (Włącz/Wyłącz Zakładki) ---
        tools_menu = menu_bar.addMenu('Narzędzia')

        # Iterujemy przez zapisane dane zakładek używając oryginalnych indeksów
        for original_index, (widget, title) in self.all_tabs_data.items():
            # Tworzymy akcję dla każdej zakładki
            # Tekst akcji pokazuje, którą zakładkę kontroluje
            toggle_action = QAction(f'Pokaż/Ukryj: {title}', self)
            toggle_action.setCheckable(True)  # Ustawiamy akcję jako przełącznik
            toggle_action.setChecked(True)   # Domyślnie wszystkie są widoczne (zaznaczone)

            # Łączymy sygnał toggled akcji z naszą nową metodą
            # Przekazujemy oryginalny indeks, aby wiedzieć, którą zakładką zarządzamy
            toggle_action.toggled.connect(
                lambda checked, index=original_index: self.toggle_tab_visibility(checked, index)
            )

            # Dodajemy akcję do menu "Narzędzia"
            tools_menu.addAction(toggle_action)
            # Zapisujemy akcję, aby móc ewentualnie zaktualizować jej stan
            self.tab_toggle_actions[original_index] = toggle_action


    def toggle_tab_visibility(self, checked, original_index):
        """Pokazuje lub ukrywa zakładkę na podstawie stanu akcji menu."""
        widget, title = self.all_tabs_data[original_index]

        if checked:
            # --- Pokaż zakładkę (dodaj ją z powrotem) ---
            # Sprawdź, czy widget już przypadkiem nie jest widoczny
            current_index = self.find_widget_index(widget)
            if current_index == -1: # Widgetu nie ma w zakładkach
                # Oblicz poprawny indeks wstawienia, aby zachować oryginalną kolejność
                insert_at_index = 0
                for i in range(original_index):
                    # Sprawdź, czy zakładka o niższym oryginalnym indeksie jest aktualnie widoczna
                    if i in self.all_tabs_data:
                         prev_widget, _ = self.all_tabs_data[i]
                         if self.find_widget_index(prev_widget) != -1:
                              insert_at_index += 1

                self.tabs.insertTab(insert_at_index, widget, title)
        else:
            # --- Ukryj zakładkę (usuń ją) ---
            # Znajdź aktualny indeks widgetu w QTabWidget
            current_index = self.find_widget_index(widget)
            if current_index != -1: # Jeśli widget jest znaleziony (widoczny)
                self.tabs.removeTab(current_index)

    def find_widget_index(self, widget_to_find):
        """Zwraca aktualny indeks podanego widgetu w self.tabs lub -1, jeśli nie znaleziono."""
        for i in range(self.tabs.count()):
            if self.tabs.widget(i) == widget_to_find:
                return i
        return -1 # Nie znaleziono

    # Metody open_file i save_file pozostają bez zmian
    def open_file(self):
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getOpenFileName(self,
                                                'Otwórz plik',
                                                '',
                                                'Wszystkie pliki (*);;Pliki tekstowe (*.txt)',
                                                options=options)
        if filename:
            print(f"Wybrano plik do otwarcia: {filename}")
            QMessageBox.information(self, "Plik otwarty", f"Otwarty plik:\n{filename}")

    def save_file(self):
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getSaveFileName(self,
                                                'Zapisz plik',
                                                '',
                                                'Wszystkie pliki (*);;Pliki tekstowe (*.txt)',
                                                options=options)
        if filename:
            print(f"Wybrano plik do zapisu: {filename}")
            QMessageBox.information(self, "Plik zapisany", f"Zapisano plik:\n{filename}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())