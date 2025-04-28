import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QAction, QTabWidget, QWidget,
    QVBoxLayout, QLabel, QFileDialog, QMessageBox,
    QMenuBar, QSplitter # Dodajemy QSplitter
)
from PyQt5.QtCore import Qt, QMimeData # Potrzebne dla orientacji splittera
from PyQt5.QtGui import QDrag # Potencjalnie dla przyszłego D&D

# --- Custom Tab Widget ---
# Na razie prosty, ale gotowy na rozbudowę o D&D
class DraggableTabWidget(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMovable(True) # Pozwala na przesuwanie zakładek w obrębie jednego widgetu
        self.setAcceptDrops(True) # Potrzebne dla przyszłego D&D między panelami

    # --- Miejsce na przyszłą implementację Drag and Drop ---
    # def mouseMoveEvent(self, event):
    #     # Implementacja rozpoczęcia przeciągania
    #     pass

    # def dragEnterEvent(self, event):
    #     # Implementacja akceptowania upuszczenia
    #     pass

    # def dropEvent(self, event):
    #     # Implementacja logiki upuszczenia
    #     pass
    # --- Koniec miejsca na D&D ---


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Okno z Podziałem Paneli (Styl VS Code - Uproszczony)')
        self.setGeometry(100, 100, 1000, 700)
        self.setAcceptDrops(True) # Głównwe okno też może akceptować drop

        # Przechowuje dane o wszystkich zakładkach (widget treści, tytuł, oryginalny indeks)
        self.all_tabs_data = {}
        # Przechowuje akcje menu dla łatwego dostępu i aktualizacji stanu
        self.tab_toggle_actions = {}
        # Słownik mapujący widget treści na QTabWidget, w którym się znajduje
        self.content_widget_to_tab_widget = {}

        # Inicjalizacja - zaczynamy od jednego panelu z zakładkami
        initial_tab_widget = DraggableTabWidget()
        self.setCentralWidget(initial_tab_widget) # Ustawiamy pierwszy panel

        # Dodanie 5 zakładek i zapisanie ich danych
        num_tabs = 5
        for i in range(num_tabs):
            # Tworzymy *widget treści*, który będzie przenoszony
            content_widget = QWidget()
            layout = QVBoxLayout()
            # Używamy oryginalnego indeksu w etykiecie dla jasności
            label = QLabel(f'To jest zawartość zakładki (Oryg. Indeks {i})')
            layout.addWidget(label)
            content_widget.setLayout(layout)
            tab_title = f'Zakładka {i+1}'

            # Zapisz widget TREŚCI, tytuł i oryginalny indeks
            self.all_tabs_data[i] = (content_widget, tab_title, i)

            # Dodaj zakładkę do początkowego widgetu zakładek
            initial_tab_widget.addTab(content_widget, tab_title)
            # Zarejestruj, gdzie znajduje się widget treści
            self.content_widget_to_tab_widget[content_widget] = initial_tab_widget

        # Tworzenie Menu
        self.create_menu()

    def create_menu(self):
        menu_bar = self.menuBar()

        # --- Menu "Plik" ---
        file_menu = menu_bar.addMenu('Plik')
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

        # --- Menu "Narzędzia" (Włącz/Wyłącz/Podziel Zakładki) ---
        tools_menu = menu_bar.addMenu('Narzędzia')

        # Iterujemy przez zapisane dane zakładek
        # Sortujemy wg oryginalnego indeksu dla spójnej kolejności w menu
        sorted_indices = sorted(self.all_tabs_data.keys())
        for original_index in sorted_indices:
            content_widget, title, _ = self.all_tabs_data[original_index]

            # Tworzymy akcję dla każdej zakładki
            toggle_action = QAction(f'Pokaż/Podziel: {title}', self)
            toggle_action.setCheckable(True)
            # Sprawdzamy, czy zakładka jest aktualnie widoczna gdziekolwiek
            is_visible = self.find_tab_widget_for_content(content_widget) is not None
            toggle_action.setChecked(is_visible)

            toggle_action.toggled.connect(
                lambda checked, index=original_index: self.toggle_or_split_tab(checked, index)
            )

            tools_menu.addAction(toggle_action)
            self.tab_toggle_actions[original_index] = toggle_action

    def find_tab_widget_for_content(self, content_widget_to_find):
        """Znajduje QTabWidget zawierający dany widget treści."""
        return self.content_widget_to_tab_widget.get(content_widget_to_find)

    def find_content_widget_index_in_tabwidget(self, tab_widget, content_widget_to_find):
        """Znajduje indeks zakładki z danym widgetem treści w konkretnym QTabWidget."""
        if not tab_widget:
            return -1
        for i in range(tab_widget.count()):
            if tab_widget.widget(i) == content_widget_to_find:
                return i
        return -1

    def find_focused_tab_widget(self):
        """Znajduje DraggableTabWidget, który ma focus, lub pierwszy napotkany."""
        focused_widget = QApplication.focusWidget()
        current_widget = focused_widget

        # Szukaj w górę drzewa widgetów
        while current_widget is not None:
            if isinstance(current_widget, DraggableTabWidget):
                return current_widget
            current_widget = current_widget.parent()

        # Jeśli nie znaleziono focusa, znajdź pierwszy DraggableTabWidget w strukturze
        # (Proste przeszukiwanie - może wymagać ulepszenia dla bardzo złożonych layoutów)
        widgets_to_check = [self.centralWidget()]
        while widgets_to_check:
            widget = widgets_to_check.pop(0)
            if isinstance(widget, DraggableTabWidget):
                return widget
            if isinstance(widget, QSplitter):
                for i in range(widget.count()):
                    widgets_to_check.append(widget.widget(i))
        return None # Nie powinno się zdarzyć, jeśli zawsze jest przynajmniej jeden

    def toggle_or_split_tab(self, checked, original_index):
        """Pokazuje zakładkę (potencjalnie w nowym podziale pionowym) lub ją ukrywa."""
        content_widget, title, _ = self.all_tabs_data[original_index]
        existing_tab_widget = self.find_tab_widget_for_content(content_widget)

        if checked:
            # --- POKAŻ LUB PODZIEL ---
            if existing_tab_widget is not None:
                 # Już jest widoczna, tylko upewnij się, że jest aktywna
                existing_tab_widget.setCurrentWidget(content_widget)
                existing_tab_widget.setFocus() # Ustaw focus na panelu
            else:
                # --- Trzeba dodać zakładkę - tworzymy podział pionowy ---
                target_widget = self.find_focused_tab_widget()
                if not target_widget:
                     print("Błąd: Nie znaleziono widgetu docelowego do podziału.")
                     # Przywróć stan przycisku menu, bo operacja się nie powiodła
                     self.tab_toggle_actions[original_index].setChecked(False)
                     return

                # Znajdź rodzica widgetu docelowego (Splitter lub MainWindow)
                parent_widget = target_widget.parent()
                target_index_in_parent = -1

                # Stwórz nowy panel zakładek dla nowej zakładki
                new_tab_widget = DraggableTabWidget()
                new_tab_widget.addTab(content_widget, title)
                self.content_widget_to_tab_widget[content_widget] = new_tab_widget

                # Stwórz nowy, pionowy splitter
                new_splitter = QSplitter(Qt.Vertical) # Podział pionowy

                # Zamień stary widget (target_widget) na nowy splitter w jego rodzicu
                if isinstance(parent_widget, QSplitter):
                    # Znajdź indeks starego widgetu w rodzicu-splitterze
                    for i in range(parent_widget.count()):
                        if parent_widget.widget(i) == target_widget:
                            target_index_in_parent = i
                            break
                    if target_index_in_parent != -1:
                        # Wstawiamy splitter w miejsce starego widgetu
                        parent_widget.insertWidget(target_index_in_parent, new_splitter)
                        # Usuwamy stary widget (teraz jest o jeden za daleko)
                        # UWAGA: target_widget zostanie usunięty przez Qt po wyjęciu go ze splittera
                        # Trzeba go jednak jawnie usunąć z layoutu rodzica
                        target_widget.setParent(None)
                    else:
                        print("Błąd: Nie znaleziono indeksu widgetu docelowego w rodzicu-splitterze.")
                        # Cofnij zmiany
                        self.content_widget_to_tab_widget.pop(content_widget, None)
                        self.tab_toggle_actions[original_index].setChecked(False)
                        return

                elif parent_widget == self: # Rodzicem jest MainWindow
                    self.setCentralWidget(new_splitter)
                    target_widget.setParent(None) # Usuń stary widget
                else:
                    print("Błąd: Nieoczekiwany typ rodzica widgetu docelowego.")
                    # Cofnij zmiany
                    self.content_widget_to_tab_widget.pop(content_widget, None)
                    self.tab_toggle_actions[original_index].setChecked(False)
                    return

                # Dodaj stary i nowy panel do nowego splittera
                new_splitter.addWidget(target_widget) # Stary panel na górze
                new_splitter.addWidget(new_tab_widget) # Nowy panel na dole
                # Ustaw równe rozmiary (opcjonalnie)
                total_height = new_splitter.size().height()
                if total_height > 0 :
                    new_splitter.setSizes([total_height // 2, total_height // 2])
                else: # Domyślne rozmiary jeśli wysokość jest 0 na początku
                    new_splitter.setSizes([100, 100])

                new_tab_widget.setFocus() # Ustaw focus na nowym panelu

        else:
            # --- UKRYJ ---
            if existing_tab_widget:
                tab_index = self.find_content_widget_index_in_tabwidget(existing_tab_widget, content_widget)
                if tab_index != -1:
                    existing_tab_widget.removeTab(tab_index)
                    # Usuń rejestrację widgetu
                    self.content_widget_to_tab_widget.pop(content_widget, None)

                    # --- Uproszczone czyszczenie (do rozbudowy) ---
                    # Jeśli panel zakładek stał się pusty, można by go usunąć
                    # i uprościć nadrzędny splitter, ale to złożone.
                    # if existing_tab_widget.count() == 0:
                    #     print(f"Panel {existing_tab_widget} stał się pusty - wymaga czyszczenia layoutu (niezaimplementowane).")
                    #     # Tutaj logika usuwania pustego `existing_tab_widget`
                    #     # i potencjalnego upraszczania `parent_splitter`.
            else:
                 # Próba ukrycia czegoś, co już jest ukryte - nic nie rób
                 pass

    # --- Metody open_file i save_file bez zmian ---
    def open_file(self):
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getOpenFileName(self, 'Otwórz plik', '', 'Wszystkie pliki (*);;Pliki tekstowe (*.txt)', options=options)
        if filename:
            print(f"Wybrano plik do otwarcia: {filename}")
            QMessageBox.information(self, "Plik otwarty", f"Otwarty plik:\n{filename}")

    def save_file(self):
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getSaveFileName(self, 'Zapisz plik', '', 'Wszystkie pliki (*);;Pliki tekstowe (*.txt)', options=options)
        if filename:
            print(f"Wybrano plik do zapisu: {filename}")
            QMessageBox.information(self, "Plik zapisany", f"Zapisano plik:\n{filename}")

    # --- Obsługa Drag and Drop (bardzo podstawowa - tylko akceptacja) ---
    # def dragEnterEvent(self, event):
    #      # Tutaj sprawdzalibyśmy, czy przeciągane dane są odpowiednie (np. nasza zakładka)
    #      # event.acceptProposedAction()
    #      pass

    # def dropEvent(self, event):
    #      # Tutaj logika tworzenia podziału na podstawie miejsca upuszczenia (krawędź/narożnik)
    #      # - Pobranie danych z QMimeData
    #      # - Określenie pozycji kursora (event.pos()) względem geometrii okna/widgetów
    #      # - Stworzenie QSplitter (poziomego/pionowego)
    #      # - Stworzenie nowego DraggableTabWidget
    #      # - Przeniesienie widgetu treści
    #      # - Zarządzanie układem splitterów
    #      pass
    # --- Koniec obsługi D&D ---


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())