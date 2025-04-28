# layout_manager.py
from PyQt5.QtWidgets import QWidget, QSplitter, QMainWindow
from PyQt5.QtCore import Qt
from .tab_widget import DraggableTabWidget # Użyj kropki dla względnego importu

def find_widget_parent_splitter(widget):
    """ Znajduje najbliższy nadrzędny QSplitter dla danego widgetu. """
    parent = widget.parent()
    while parent is not None:
        if isinstance(parent, QSplitter):
            return parent
        parent = parent.parent()
    return None

def find_widget_index_in_splitter(splitter, widget):
    """ Znajduje indeks widgetu w splitterze. """
    if not splitter:
        return -1
    for i in range(splitter.count()):
        if splitter.widget(i) == widget:
            return i
    return -1

def replace_widget_in_parent(old_widget, new_widget):
    """ Zastępuje old_widget przez new_widget w jego rodzicu (Splitter lub MainWindow). """
    parent = old_widget.parent()
    if isinstance(parent, QSplitter):
        index = find_widget_index_in_splitter(parent, old_widget)
        if index != -1:
            # Zapamiętaj rozmiary, aby je przywrócić (w przybliżeniu)
            sizes = parent.sizes()
            parent.insertWidget(index, new_widget)
            old_widget.setParent(None) # Usuń stary widget z layoutu
            # Próba przywrócenia proporcji - może wymagać dostosowania
            if len(sizes) > index:
                 current_total = sum(parent.sizes())
                 original_widget_size = sizes.pop(index)
                 new_total_size = sum(sizes) if sizes else 0
                 ratio = original_widget_size / (new_total_size + original_widget_size) if (new_total_size + original_widget_size) > 0 else 0.5
                 # Nowy splitter zajmuje miejsce starego widgetu, podzielmy jego rozmiar
                 split_size1 = int(original_widget_size * 0.5)
                 split_size2 = original_widget_size - split_size1
                 sizes.insert(index, split_size2) # Rozmiar dla drugiego elementu splittera
                 sizes.insert(index, split_size1) # Rozmiar dla pierwszego elementu splittera

                 # Skaluj rozmiary, aby suma pasowała (jeśli się zmieniła)
                 final_total = sum(sizes)
                 if final_total > 0 and current_total > 0:
                      scale_factor = current_total / final_total
                      sizes = [int(s * scale_factor) for s in sizes]

                 parent.setSizes(sizes)

            return True
    elif isinstance(parent, QMainWindow):
        parent.setCentralWidget(new_widget)
        old_widget.setParent(None)
        return True
    elif isinstance(parent, QWidget) and parent.layout() is not None: # Ogólny przypadek layoutu
         layout = parent.layout()
         index = layout.indexOf(old_widget)
         if index != -1:
             layout.insertWidget(index, new_widget)
             old_widget.setParent(None) # Usuwa też z layoutu
             return True

    print(f"Warning: Could not replace widget. Parent type: {type(parent)}")
    return False


def split_widget(target_widget, new_content_widget, title, orientation, first_half):
    """
    Tworzy nowy splitter i umieszcza w nim target_widget oraz nowy panel
    z new_content_widget. Zastępuje target_widget nowym splitterem.
    Zwraca nowo utworzony DraggableTabWidget lub None w przypadku błędu.
    """
    if not target_widget or not new_content_widget:
        return None

    new_tab_panel = DraggableTabWidget()
    new_tab_panel.addTab(new_content_widget, title)

    splitter = QSplitter(orientation)

    # Ważne: zachowaj oryginalny target_widget!
    # Usuń go tymczasowo z rodzica, aby dodać do splittera
    # (replace_widget_in_parent zrobi to za nas)

    if first_half:
        splitter.addWidget(new_tab_panel)
        splitter.addWidget(target_widget)
        initial_sizes = [100, 100] # Domyślne równe rozmiary
    else:
        splitter.addWidget(target_widget)
        splitter.addWidget(new_tab_panel)
        initial_sizes = [100, 100]

    # Pobierz oryginalny rozmiar przed zastąpieniem
    original_size = target_widget.size()

    if replace_widget_in_parent(target_widget, splitter):
        # Ustaw rozmiary po dodaniu do layoutu
        total_size = original_size.height() if orientation == Qt.Vertical else original_size.width()
        if total_size > 0:
             splitter.setSizes([total_size // 2, total_size - total_size // 2])
        else:
             splitter.setSizes(initial_sizes) # Fallback

        return new_tab_panel # Zwróć nowy panel zakładek
    else:
        # Coś poszło nie tak, spróbuj posprzątać
        new_tab_panel.setParent(None)
        new_tab_panel.deleteLater()
        splitter.setParent(None)
        splitter.deleteLater()
        # Przywrócenie target_widget może być trudne, jeśli został już usunięty z rodzica
        print("Error: Failed to replace widget with splitter.")
        return None


def cleanup_empty_splitters(widget):
    """ Rekurencyjnie usuwa puste splittery i upraszcza layout. """
    if not widget:
        return

    # Przetwarzaj dzieci najpierw (od dołu do góry)
    if isinstance(widget, QSplitter):
        widgets_to_remove = []
        valid_children = []
        for i in range(widget.count()):
            child = widget.widget(i)
            cleanup_empty_splitters(child) # Rekurencja

            # Sprawdź, czy dziecko stało się "puste" (np. TabWidget bez zakładek)
            # lub czy samo jest splitterem, który stał się zbędny
            is_empty_tab_widget = isinstance(child, DraggableTabWidget) and child.count() == 0
            is_redundant_splitter = isinstance(child, QSplitter) and child.count() <= 1

            if is_empty_tab_widget:
                 widgets_to_remove.append(child)
            elif is_redundant_splitter:
                 # Jeśli splitter ma jedno dziecko, zastąp splitter tym dzieckiem
                 if child.count() == 1:
                      single_child = child.widget(0)
                      # Uwaga: Bezpośrednie zastąpienie w pętli jest ryzykowne
                      # Lepiej zaplanować zastąpienie po pętli
                      valid_children.append(single_child)
                      single_child.setParent(None) # Przygotuj do przeniesienia
                 widgets_to_remove.append(child) # Usuń pusty lub zastąpiony splitter
            else:
                 valid_children.append(child) # Zachowaj to dziecko

        # Usuń oznaczone widgety z bieżącego splittera
        # Musimy to zrobić ostrożnie, aby nie zepsuć pętli - najlepiej przez kopię
        current_widgets = [widget.widget(i) for i in range(widget.count())]
        widget_map = {w: i for i, w in enumerate(current_widgets)}

        if widgets_to_remove:
             # Blokowanie sygnałów może pomóc uniknąć problemów podczas modyfikacji
             widget.blockSignals(True)
             original_sizes = widget.sizes()
             new_widgets_in_splitter = []
             new_sizes = []

             for i, child in enumerate(current_widgets):
                 if child in widgets_to_remove:
                     child.setParent(None) # Usuń
                     child.deleteLater()
                 else:
                     # Może to być dziecko zastępujące redundantny splitter
                     found_replacement = False
                     for repl in valid_children:
                          # Trudno jednoznacznie powiązać, chyba że przez oryginalną pozycję
                          # Uproszczenie: Dodajemy wszystkie valid_children
                          # Lepsze byłoby dokładne mapowanie
                          pass # Logika dodawania zastępstw wymaga przemyślenia

                     # Dodajmy na razie tylko te, które nie były do usunięcia
                     new_widgets_in_splitter.append(child)
                     if i < len(original_sizes):
                          new_sizes.append(original_sizes[i])


             # Usuń wszystkie stare widgety (te, które zostały, są już w new_widgets_in_splitter)
             while widget.count() > 0:
                  widget.widget(0).setParent(None)

             # Dodaj nowe/pozostałe widgety
             for w in new_widgets_in_splitter:
                 widget.addWidget(w)

             if new_sizes and len(new_sizes) == widget.count():
                  widget.setSizes(new_sizes)
             elif widget.count() > 0: # Domyślne rozmiary, jeśli coś poszło nie tak
                 default_size = [1] * widget.count()
                 widget.setSizes(default_size)

             widget.blockSignals(False)


    # Po przetworzeniu dzieci, sprawdź sam widget (jeśli to splitter)
    if isinstance(widget, QSplitter) and widget.count() <= 1:
        parent_splitter = find_widget_parent_splitter(widget)
        if parent_splitter:
            index = find_widget_index_in_splitter(parent_splitter, widget)
            if index != -1:
                sizes = parent_splitter.sizes()
                replacement = None
                if widget.count() == 1:
                    replacement = widget.widget(0)
                    replacement.setParent(None) # Przygotuj do przeniesienia

                # Usuń stary splitter
                widget.setParent(None)
                widget.deleteLater()

                # Wstaw zamiennik (jeśli istnieje)
                if replacement:
                    parent_splitter.insertWidget(index, replacement)
                    # Przywróć rozmiary (w przybliżeniu)
                    if len(sizes) > index:
                         # Ta logika wymaga dopracowania, jak rozdzielić rozmiar
                         parent_splitter.setSizes(sizes) # Może nie być poprawne
                else:
                     # Jeśli nie ma zamiennika, po prostu usuń index i rozmiar
                     # Trzeba zaktualizować rozmiary pozostałych
                     if len(sizes) > index:
                         sizes.pop(index)
                         if sizes:
                              parent_splitter.setSizes(sizes)

            # Sprawdź, czy rodzic też stał się zbędny
            cleanup_empty_splitters(parent_splitter)

        elif isinstance(widget.parent(), QMainWindow):
             # Jeśli główny widget to splitter z <= 1 dzieckiem
             main_win = widget.parent()
             replacement = None
             if widget.count() == 1:
                 replacement = widget.widget(0)
                 replacement.setParent(None) # Przygotuj do przeniesienia
                 main_win.setCentralWidget(replacement)
             else:
                 main_win.setCentralWidget(QWidget()) # Puste okno? Lub zamknij?

             widget.setParent(None)
             widget.deleteLater()
             