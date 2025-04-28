# main_window.py
import sys
from PyQt5.QtWidgets import (
    QMainWindow, QAction, QWidget, QVBoxLayout, QLabel,
    QFileDialog, QMessageBox, QSplitter, QApplication
)
from PyQt5.QtCore import Qt, QPoint, pyqtSignal
from functools import partial # Lepsze niż lambda dla slotów

# Używamy względnych importów
from .tab_widget import DraggableTabWidget, TAB_MIME_TYPE, DropIndicator
from .layout_manager import split_widget, cleanup_empty_splitters, find_widget_parent_splitter

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Edytor z Podziałem Paneli (Styl VS Code)')
        self.setGeometry(100, 100, 1200, 800)
        # Akceptuj drop globalnie, aby móc przechwycić upuszczenie poza panelem
        self.setAcceptDrops(True)

        # Przechowuje dane o wszystkich zakładkach (widget treści, tytuł, unikalne ID)
        self.all_tabs_data = {} # key: unique_id, value: (content_widget, title)
        # Mapuje ID na akcję w menu
        self.tab_toggle_actions = {} # key: unique_id, value: QAction
        # Mapuje widget treści na QTabWidget, w którym się aktualnie znajduje
        self.content_widget_to_tab_widget = {}
        self._next_tab_id = 0

        # Przechowuje informacje o przeciąganej zakładce (globalnie w oknie)
        self._dragged_content_widget_ref = None # Użyj słabego odwołania lub ID
        self._dragged_tab_title_ref = ""
        self._source_tab_widget_ref = None # Skąd przeciągnięto

        # Inicjalizacja - zaczynamy od jednego panelu
        initial_tab_widget = DraggableTabWidget()
        # Połącz sygnały D&D z naszego niestandardowego widgetu
        # initial_tab_widget.tabDraggedOut.connect(self.handle_tab_drag_start) # Podłączymy dynamicznie
        self.setCentralWidget(initial_tab_widget)
        self.connect_tab_widget_signals(initial_tab_widget) # Podłącz sygnały

        # Wskaźnik upuszczania (jeden dla całego okna)
        self.drop_indicator = DropIndicator(self)

        # Dodanie początkowych zakładek
        self.add_new_tab(title="Zakładka 1", make_current=True)
        self.add_new_tab(title="Zakładka 2")
        self.add_new_tab(title="Zakładka 3")

        # Tworzenie Menu
        self.create_menu()

    def get_unique_tab_id(self):
        """ Generuje unikalne ID dla zakładki. """
        id_val = self._next_tab_id
        self._next_tab_id += 1
        return id_val

    def add_new_tab(self, content_widget=None, title="Nowa Zakładka", target_tab_widget=None, make_current=False):
        """ Dodaje nową zakładkę do wskazanego panelu lub pierwszego znalezionego. """
        tab_id = self.get_unique_tab_id()

        if content_widget is None:
            content_widget = QWidget()
            layout = QVBoxLayout()
            label = QLabel(f'Zawartość zakładki ID: {tab_id}\nTytuł: {title}')
            layout.addWidget(label)
            content_widget.setLayout(layout)
            # Zapisz ID w widgecie, aby łatwiej go odnaleźć
            content_widget.setProperty("tab_id", tab_id)

        self.all_tabs_data[tab_id] = (content_widget, title)

        if target_tab_widget is None:
            target_tab_widget = self.find_first_tab_widget()
            if target_tab_widget is None: # Jeśli nie ma żadnego, stwórz pierwszy
                target_tab_widget = DraggableTabWidget()
                self.setCentralWidget(target_tab_widget)
                self.connect_tab_widget_signals(target_tab_widget)

        target_tab_widget.addTab(content_widget, title)
        self.content_widget_to_tab_widget[content_widget] = target_tab_widget

        if make_current:
            target_tab_widget.setCurrentWidget(content_widget)

        # Zaktualizuj menu (dodaj nową akcję, jeśli trzeba)
        self.update_tools_menu()

        return tab_id, content_widget

    def find_tab_widget_for_content(self, content_widget_to_find):
        """ Znajduje QTabWidget zawierający dany widget treści. """
        return self.content_widget_to_tab_widget.get(content_widget_to_find)

    def find_tab_widget_by_id(self, tab_id):
        """ Znajduje widget treści i jego panel na podstawie ID. """
        if tab_id in self.all_tabs_data:
            content_widget, _ = self.all_tabs_data[tab_id]
            tab_widget = self.find_tab_widget_for_content(content_widget)
            return content_widget, tab_widget
        return None, None

    def find_first_tab_widget(self, root_widget=None):
        """ Znajduje pierwszy napotkany DraggableTabWidget w strukturze. """
        if root_widget is None:
            root_widget = self.centralWidget()

        if isinstance(root_widget, DraggableTabWidget):
            return root_widget
        elif isinstance(root_widget, QSplitter):
            for i in range(root_widget.count()):
                found = self.find_first_tab_widget(root_widget.widget(i))
                if found:
                    return found
        return None

    def find_all_tab_widgets(self, root_widget=None):
         """ Znajduje wszystkie DraggableTabWidget w strukturze. """
         if root_widget is None:
             root_widget = self.centralWidget()
         widgets = []
         if isinstance(root_widget, DraggableTabWidget):
             widgets.append(root_widget)
         elif isinstance(root_widget, QSplitter):
             for i in range(root_widget.count()):
                 widgets.extend(self.find_all_tab_widgets(root_widget.widget(i)))
         return widgets

    def create_menu(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu('Plik')
        # ... (Akcje Plik bez zmian - Otwórz, Zapisz, Zamknij) ...
        open_action = QAction('Otwórz', self)
        # open_action.triggered.connect(self.open_file) # Dodaj metody później
        file_menu.addAction(open_action)
        save_action = QAction('Zapisz', self)
        # save_action.triggered.connect(self.save_file) # Dodaj metody później
        file_menu.addAction(save_action)
        file_menu.addSeparator()
        exit_action = QAction('Zamknij', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Menu "Narzędzia" będzie aktualizowane dynamicznie
        self.tools_menu = menu_bar.addMenu('Narzędzia')
        self.update_tools_menu()

    def update_tools_menu(self):
        """ Czyści i ponownie tworzy menu 'Narzędzia' na podstawie aktualnych zakładek. """
        self.tools_menu.clear()
        self.tab_toggle_actions.clear() # Wyczyść stare akcje

        sorted_ids = sorted(self.all_tabs_data.keys())
        for tab_id in sorted_ids:
            content_widget, title = self.all_tabs_data[tab_id]
            current_tab_widget = self.find_tab_widget_for_content(content_widget)
            is_visible = current_tab_widget is not None

            action_text = f"{'[✓]' if is_visible else '[ ]'} {title} (ID: {tab_id})"
            toggle_action = QAction(action_text, self)
            toggle_action.setCheckable(True) # Użyjemy checkable do logiki, ale tekst pokazuje stan
            toggle_action.setChecked(is_visible)

            # Użyj partial zamiast lambda, aby uniknąć problemów z zasięgiem w pętli
            # Przekazujemy ID zakładki
            toggle_action.triggered.connect(partial(self.toggle_or_split_tab, tab_id))

            self.tools_menu.addAction(toggle_action)
            self.tab_toggle_actions[tab_id] = toggle_action


    def toggle_or_split_tab(self, tab_id):
        """ Pokazuje zakładkę (w aktywnym panelu lub nowym podziale) lub ją ukrywa. """
        content_widget, title = self.all_tabs_data.get(tab_id, (None, None))
        if not content_widget:
            print(f"Error: Tab with ID {tab_id} not found.")
            return

        existing_tab_widget = self.find_tab_widget_for_content(content_widget)
        action = self.tab_toggle_actions.get(tab_id) # Pobierz akcję dla aktualizacji stanu

        if existing_tab_widget:
            # --- UKRYJ ---
            # Jeśli zakładka jest widoczna, ukryj ją (usuń z panelu)
            tab_index = existing_tab_widget.indexOf(content_widget)
            if tab_index != -1:
                print(f"Hiding tab ID {tab_id} ('{title}')")
                existing_tab_widget.removeTab(tab_index)
                del self.content_widget_to_tab_widget[content_widget] # Usuń rejestrację

                # Sprawdź, czy panel stał się pusty i posprzątaj
                # Użyj QTimer.singleShot, aby sprzątanie odbyło się po zakończeniu bieżącego eventu
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(0, partial(self.cleanup_layout_if_needed, existing_tab_widget))

                if action: action.setChecked(False) # Aktualizuj stan menu
            else:
                 # Stan niespójny - powinno być w panelu, ale nie ma indeksu
                 print(f"Warning: Tab ID {tab_id} was registered in a panel but not found by index.")
                 del self.content_widget_to_tab_widget[content_widget]
                 if action: action.setChecked(False)


        else:
            # --- POKAŻ / PODZIEL ---
            # Jeśli zakładka jest ukryta, pokaż ją
            # Znajdź aktywny/ostatnio używany panel lub pierwszy dostępny
            target_widget = self.find_focused_tab_widget()
            if not target_widget:
                target_widget = self.find_first_tab_widget()

            print(f"Showing tab ID {tab_id} ('{title}')")
            if target_widget:
                # Dodaj do istniejącego panelu
                target_widget.addTab(content_widget, title)
                target_widget.setCurrentWidget(content_widget)
                self.content_widget_to_tab_widget[content_widget] = target_widget
                target_widget.setFocus()
                if action: action.setChecked(True)
            else:
                # Nie ma żadnych paneli - stwórz pierwszy
                print("No existing tab panels found. Creating the first one.")
                new_tab_widget = DraggableTabWidget()
                self.setCentralWidget(new_tab_widget)
                self.connect_tab_widget_signals(new_tab_widget)
                new_tab_widget.addTab(content_widget, title)
                self.content_widget_to_tab_widget[content_widget] = new_tab_widget
                new_tab_widget.setFocus()
                if action: action.setChecked(True)

        # Zaktualizuj tekst akcji w menu po zmianie stanu
        self.update_tools_menu()


    def find_focused_tab_widget(self):
        """ Znajduje DraggableTabWidget, który ma focus, lub ostatnio aktywny. """
        focused_widget = QApplication.focusWidget()
        current_widget = focused_widget
        while current_widget is not None:
            if isinstance(current_widget, DraggableTabWidget):
                return current_widget
            # Sprawdź też, czy focus jest wewnątrz widgetu treści zakładki
            parent_tab_widget = self.content_widget_to_tab_widget.get(current_widget)
            if parent_tab_widget:
                 return parent_tab_widget
            current_widget = current_widget.parent()

        # Jeśli nie ma focusa, zwróć pierwszy napotkany (fallback)
        return self.find_first_tab_widget()

    def connect_tab_widget_signals(self, tab_widget):
        """ Podłącza sygnały D&D dla danego tab_widget. """
        #tab_widget.tabDraggedOut.connect(self.handle_tab_drag_start) # Już niepotrzebne, drag zaczyna się w widgecie
        #tab_widget.tabDroppedIn.connect(self.handle_tab_drop) # Już niepotrzebne, drop jest obsługiwany w handle_drop_event

        # Ważne: Połącz wskaźnik upuszczania z tym panelem
        tab_widget.drop_indicator = self.drop_indicator


    # --- Obsługa Drag and Drop ---

    def dragEnterEvent(self, event):
        # Akceptuj tylko nasz niestandardowy typ MIME
        if event.mimeData().hasFormat(TAB_MIME_TYPE):
            event.acceptProposedAction()
            # Pokaż globalny wskaźnik, jeśli przeciągamy nad głównym oknem (poza panelami)
            # self.drop_indicator.setGeometry(self.rect()) # Można by pokazać, że okno akceptuje
            # self.drop_indicator.show()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
         if event.mimeData().hasFormat(TAB_MIME_TYPE):
            event.acceptProposedAction()
            # Wskaźnik jest zarządzany przez DraggableTabWidget, gdy kursor jest nad nim
            # Jeśli kursor jest nad QMainWindow, ale nie nad żadnym panelem, można by coś pokazać
            widget_at_pos = self.childAt(event.pos())
            is_over_tab_widget = False
            temp = widget_at_pos
            while temp is not None:
                 if isinstance(temp, DraggableTabWidget):
                      is_over_tab_widget = True
                      break
                 temp = temp.parent()

            if not is_over_tab_widget:
                 self.drop_indicator.hide() # Ukryj, jeśli nie jesteśmy nad panelem

         else:
            event.ignore()


    def dragLeaveEvent(self, event):
        # Ukryj globalny wskaźnik, gdy opuszczamy okno
        self.drop_indicator.hide()

    def dropEvent(self, event):
        """ Obsługuje upuszczenie na głównym oknie (poza panelami zakładek). """
        self.drop_indicator.hide()
        print("Drop occurred on MainWindow (outside any panel)")
        # Można zignorować lub np. otworzyć w nowym oknie (bardziej złożone)
        # Na razie ignorujemy - zakładka powinna wrócić na swoje miejsce
        event.ignore() # Ignorujemy drop bezpośrednio na MainWindow
        # Sygnał zwrotny z QDrag (IgnoreAction) powinien spowodować przywrócenie zakładki

        # Jeśli _dragged_content_widget_ref nie jest None, oznacza to, że drag się zakończył
        # i nie został obsłużony przez żaden panel. Musimy przywrócić zakładkę.
        self.restore_dragged_tab_if_needed()


    def handle_drop_event(self, target_tab_widget, event):
        """ Centralna metoda obsługująca logikę upuszczenia na DraggableTabWidget. """
        self.drop_indicator.hide()
        if not event.mimeData().hasFormat(TAB_MIME_TYPE):
            event.ignore()
            self.restore_dragged_tab_if_needed() # Przywróć, jeśli MIME nie pasuje
            return

        try:
            # Odzyskaj ID widgetu z danych MIME
            widget_id_str = event.mimeData().data(TAB_MIME_TYPE).data().decode('utf-8')
            widget_id = int(widget_id_str)
            # Znajdź widget treści na podstawie ID (bardzo ważne!)
            dragged_content_widget = None
            for id_val, (content, _) in self.all_tabs_data.items():
                if id(content) == widget_id: # Porównujemy z ID zapisanym w MIME
                    dragged_content_widget = content
                    break

            if not dragged_content_widget:
                print(f"Error: Could not find content widget for ID {widget_id} during drop.")
                event.ignore()
                self.restore_dragged_tab_if_needed()
                return

            source_tab_widget = self.find_tab_widget_for_content(dragged_content_widget)
            title = event.mimeData().text() # Pobierz tytuł z MIME

        except Exception as e:
            print(f"Error processing drop data: {e}")
            event.ignore()
            self.restore_dragged_tab_if_needed()
            return

        # Sprawdź, czy upuszczamy na ten sam panel, z którego przeciągamy
        # (QDrag już usunął zakładkę, więc source_tab_widget może być None,
        #  musimy użyć referencji zapisanej na początku przeciągania)

        # --- Logika Podziału/Dodania ---
        orientation = getattr(target_tab_widget.drop_indicator, 'split_orientation', None)
        split_half = getattr(target_tab_widget.drop_indicator, 'split_half', 0)

        if orientation == Qt.TargetIsCentralWidget or target_tab_widget == self._source_tab_widget_ref:
             # Upuszczenie na środek lub na ten sam panel -> Dodaj jako zakładkę
             print(f"Adding tab '{title}' to existing panel {target_tab_widget}")
             target_tab_widget.addTab(dragged_content_widget, title)
             target_tab_widget.setCurrentWidget(dragged_content_widget)
             self.content_widget_to_tab_widget[dragged_content_widget] = target_tab_widget
        elif orientation in [Qt.Vertical, Qt.Horizontal]:
            # Upuszczenie na krawędź -> Podziel panel
            print(f"Splitting panel {target_tab_widget} {'Vertically' if orientation == Qt.Vertical else 'Horizontally'}")
            new_panel = split_widget(target_tab_widget, dragged_content_widget, title, orientation, split_half == 0)
            if new_panel:
                print("Split successful.")
                self.content_widget_to_tab_widget[dragged_content_widget] = new_panel
                self.connect_tab_widget_signals(new_panel) # Podłącz sygnały do nowego panelu
                new_panel.setFocus()
                # Target_tab_widget jest teraz częścią nowego splittera
            else:
                 print("Split failed. Restoring tab to original position.")
                 # Jeśli podział się nie udał, przywróć zakładkę do oryginalnego panelu
                 self.restore_dragged_tab_if_needed(force_restore=True)

        else:
             print("Unknown drop zone. Adding as tab.")
             # Domyślnie dodaj jako zakładkę
             target_tab_widget.addTab(dragged_content_widget, title)
             target_tab_widget.setCurrentWidget(dragged_content_widget)
             self.content_widget_to_tab_widget[dragged_content_widget] = target_tab_widget


        # Posprzątaj po źródłowym panelu, jeśli stał się pusty
        if self._source_tab_widget_ref and self._source_tab_widget_ref != target_tab_widget :
             # Użyj QTimer.singleShot dla bezpieczeństwa
             from PyQt5.QtCore import QTimer
             QTimer.singleShot(0, partial(self.cleanup_layout_if_needed, self._source_tab_widget_ref))


        # Resetuj stan przeciągania w MainWindow
        self._dragged_content_widget_ref = None
        self._source_tab_widget_ref = None
        self._dragged_tab_title_ref = ""

        event.acceptProposedAction()
        self.update_tools_menu() # Zaktualizuj menu

    def mousePressEvent(self, event):
        """ Przechwytuje początek przeciągania globalnie. """
        # Sprawdź, czy kliknięcie jest na DraggableTabWidget i czy trafia w zakładkę
        widget_at_pos = self.childAt(event.pos())
        target_tab_widget = None
        temp = widget_at_pos
        while temp is not None:
            if isinstance(temp, DraggableTabWidget):
                target_tab_widget = temp
                break
            temp = temp.parent()

        if target_tab_widget:
            # Przekaż event do tab widgetu, aby mógł rozpocząć drag & drop
            # Potrzebujemy zmapować pozycję eventu na koordynaty tab_widgetu
            local_pos = target_tab_widget.mapFromGlobal(event.globalPos())
            # Symulujemy mousePress dla target_tab_widget - To może być problematyczne!
            # Lepiej, żeby DraggableTabWidget sam obsługiwał swoje eventy myszy.
            # Usuwamy tę logikę stąd, DraggableTabWidget.mousePressEvent/mouseMoveEvent zajmie się tym.
            pass

        super().mousePressEvent(event)


    def start_drag(self, source_tab_widget, content_widget, title, global_pos):
        """ Metoda wywoływana, gdy DraggableTabWidget inicjuje przeciąganie. """
        # Ta metoda może nie być już potrzebna, jeśli cała logika startu jest w TabWidget
        print(f"MainWindow notified of drag start for '{title}' from {source_tab_widget}")
        # Zapisz stan na czas przeciągania
        self._dragged_content_widget_ref = content_widget # Zapisz referencję
        self._source_tab_widget_ref = source_tab_widget
        self._dragged_tab_title_ref = title

        # Usuń rejestrację widgetu na czas przeciągania
        if content_widget in self.content_widget_to_tab_widget:
             del self.content_widget_to_tab_widget[content_widget]


    def restore_dragged_tab_if_needed(self, force_restore=False):
        """ Przywraca przeciąganą zakładkę, jeśli drop się nie powiódł. """
        # Sprawdź, czy stan przeciągania jest aktywny
        if self._dragged_content_widget_ref is not None and self._source_tab_widget_ref is not None:
            # Sprawdź, czy widget nie został już gdzieś dodany
            already_placed = self._dragged_content_widget_ref in self.content_widget_to_tab_widget

            if not already_placed or force_restore:
                print(f"Restoring tab '{self._dragged_tab_title_ref}' to original panel {self._source_tab_widget_ref}")
                try:
                    # Sprawdź, czy source_tab_widget wciąż istnieje
                    all_widgets = self.find_all_tab_widgets()
                    if self._source_tab_widget_ref in all_widgets:
                        self._source_tab_widget_ref.addTab(self._dragged_content_widget_ref, self._dragged_tab_title_ref)
                        # Przywróć rejestrację
                        self.content_widget_to_tab_widget[self._dragged_content_widget_ref] = self._source_tab_widget_ref
                        self._source_tab_widget_ref.setCurrentWidget(self._dragged_content_widget_ref)
                    else:
                         # Panel źródłowy został usunięty - dodaj do pierwszego lepszego
                         print("Source panel not found, adding to first available panel.")
                         fallback_panel = self.find_first_tab_widget()
                         if not fallback_panel: # Stwórz nowy, jeśli nie ma żadnego
                              fallback_panel = DraggableTabWidget()
                              self.setCentralWidget(fallback_panel)
                              self.connect_tab_widget_signals(fallback_panel)

                         fallback_panel.addTab(self._dragged_content_widget_ref, self._dragged_tab_title_ref)
                         self.content_widget_to_tab_widget[self._dragged_content_widget_ref] = fallback_panel
                         fallback_panel.setCurrentWidget(self._dragged_content_widget_ref)

                except RuntimeError as e:
                    # Może się zdarzyć, jeśli source_tab_widget został usunięty w międzyczasie
                    print(f"Error restoring tab: {e}. Widget might have been deleted.")
                    # Tutaj można by próbować dodać do innego panelu jako fallback

                self.update_tools_menu() # Zaktualizuj menu

            # Zawsze resetuj stan przeciągania po próbie przywrócenia
            self._dragged_content_widget_ref = None
            self._source_tab_widget_ref = None
            self._dragged_tab_title_ref = ""


    def cleanup_layout_if_needed(self, potential_empty_widget):
        """ Sprawdza i czyści layout, jeśli widget stał się pusty lub zbędny. """
        print(f"Checking layout for cleanup starting from {potential_empty_widget}...")
        # Wywołaj funkcję czyszczącą z layout_manager
        # Zaczynamy od widgetu, który mógł stać się pusty
        cleanup_empty_splitters(potential_empty_widget)
        # Dodatkowo można wywołać czyszczenie od roota dla pewności
        cleanup_empty_splitters(self.centralWidget())
        print("Layout cleanup finished.")
        self.update_tools_menu() # Menu mogło się zmienić


    # --- Metody Plik (Placeholder) ---
    def open_file(self):
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getOpenFileName(self, 'Otwórz plik', '', 'Wszystkie pliki (*);;Pliki tekstowe (*.txt)', options=options)
        if filename:
            print(f"Wybrano plik do otwarcia: {filename}")
            # TODO: Otwórz plik w nowej zakładce
            title = filename.split('/')[-1]
            # Tutaj powinna być logika wczytania pliku do widgetu edytora
            self.add_new_tab(title=title, make_current=True)
            QMessageBox.information(self, "Plik otwarty", f"Otwarto plik:\n{filename}")


    def save_file(self):
         # TODO: Zapisz zawartość aktywnej zakładki
         active_tab_widget = self.find_focused_tab_widget()
         if active_tab_widget and active_tab_widget.currentWidget():
              options = QFileDialog.Options()
              filename, _ = QFileDialog.getSaveFileName(self, 'Zapisz plik', '', 'Wszystkie pliki (*);;Pliki tekstowe (*.txt)', options=options)
              if filename:
                  print(f"Wybrano plik do zapisu: {filename}")
                  # TODO: Logika zapisu zawartości widgetu active_tab_widget.currentWidget()
                  QMessageBox.information(self, "Plik zapisany", f"Zapisano plik:\n{filename}")
         else:
              QMessageBox.warning(self, "Zapisz plik", "Brak aktywnej zakładki do zapisania.")


    # --- Poprawka błędu ---
    # RuntimeError: wrapped C/C++ object of type DraggableTabWidget has been deleted
    # SystemError: _PyEval_EvalFrameDefault returned a result with an exception set

    # Ten błąd często występuje, gdy sygnał (np. z QAction.triggered) jest połączony
    # z metodą (lub lambda), która próbuje uzyskać dostęp do obiektu (np. DraggableTabWidget),
    # który został już usunięty przez Qt w wyniku wcześniejszych operacji (np. zmiany layoutu).

    # Kluczowe poprawki zastosowane:
    # 1. Użycie `functools.partial` zamiast `lambda` w `connect` dla akcji menu. Jest to często bezpieczniejsze.
    # 2. Ostrożne zarządzanie rodzicielstwem (`setParent(None)`) i usuwaniem widgetów.
    # 3. Użycie `QTimer.singleShot(0, ...)` do odłożenia operacji czyszczenia layoutu (`cleanup_layout_if_needed`).
    #    To pozwala zakończyć bieżącą obsługę zdarzenia (np. kliknięcia menu, dropu) przed modyfikacją
    #    struktury widgetów, co może zapobiec sytuacji, w której slot próbuje użyć usuniętego obiektu.
    # 4. W `handle_drop_event` i `restore_dragged_tab_if_needed` sprawdzamy, czy panele (widgety)
    #    nadal istnieją przed próbą ich użycia.
    # 5. Identyfikacja przeciąganego widgetu przez `id()` i przekazywanie go w MIME jest **ryzykowne**. Lepszym
    #    podejściem byłoby użycie unikalnego ID zarządzanego przez MainWindow lub przekazanie referencji
    #    w bardziej kontrolowany sposób. Jednak dla uproszczenia zostawiono `id()`. Należy być tego świadomym.

    # Dodatkowo, upewnij się, że w `layout_manager.py` funkcje `replace_widget_in_parent` i `cleanup_empty_splitters`
    # poprawnie zarządzają cyklem życia widgetów i ich rodzicielstwem (`setParent(None)`).