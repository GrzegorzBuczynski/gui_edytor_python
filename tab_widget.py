# tab_widget.py
from PyQt5.QtWidgets import QTabWidget, QApplication, QWidget
from PyQt5.QtCore import Qt, QMimeData, QPoint, QRect
from PyQt5.QtGui import QDrag, QPixmap, QPainter, QCursor

# Unikalny typ MIME dla naszych zakładek
TAB_MIME_TYPE = "application/x-myapp-tab"

class DropIndicator(QWidget):
    """ Prosty widget pokazujący, gdzie nastąpi upuszczenie. """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setGeometry(0, 0, 0, 0)
        self.setAttribute(Qt.WA_TransparentForMouseEvents) # Ignoruj zdarzenia myszy
        self.setStyleSheet("background-color: rgba(0, 120, 215, 0.5); border: 1px solid rgb(0, 120, 215);")
        self.hide()

class DraggableTabWidget(QTabWidget):
    # Sygnał emitowany, gdy zakładka jest przeciągana poza widget
    tabDraggedOut = pyqtSignal(int, QPoint) # index, globalPos
    # Sygnał emitowany, gdy zakładka jest upuszczana na ten widget (z innego)
    tabDroppedIn = pyqtSignal(QWidget, str, QPoint) # content_widget, title, globalPos

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMovable(True)
        self.setAcceptDrops(True)
        self._drag_start_position = QPoint()
        self._dragged_tab_index = -1
        self._dragged_content_widget = None
        self._dragged_tab_title = ""
        self.drop_indicator = DropIndicator(self.window()) # Wskaźnik na głównym oknie

        # Poprawka: Potrzebujemy dostępu do paska zakładek (TabBar)
        # Niestety, bezpośredni dostęp do TabBar i jego sygnałów może być kruchy.
        # Użyjemy event filter lub obejścia przez eventy myszy.

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            tab_index = self.tabBar().tabAt(event.pos())
            if tab_index >= 0:
                self._drag_start_position = event.pos()
                self._dragged_tab_index = tab_index
                # Nie rozpoczynamy przeciągania od razu, dopiero w mouseMoveEvent
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            super().mouseMoveEvent(event)
            return
        if self._dragged_tab_index == -1:
            super().mouseMoveEvent(event)
            return

        # Sprawdź dystans, aby odróżnić kliknięcie od przeciągania
        if (event.pos() - self._drag_start_position).manhattanLength() < QApplication.startDragDistance():
             super().mouseMoveEvent(event)
             return

        # --- Rozpocznij przeciąganie ---
        if self.count() <= 0 or self._dragged_tab_index >= self.count():
            self._reset_drag_state()
            super().mouseMoveEvent(event)
            return

        self._dragged_content_widget = self.widget(self._dragged_tab_index)
        self._dragged_tab_title = self.tabText(self._dragged_tab_index)

        if not self._dragged_content_widget:
            self._reset_drag_state()
            super().mouseMoveEvent(event)
            return

        mime_data = QMimeData()
        # Przechowujemy wskaźnik (jako int) na widget treści - ryzykowne, ale proste
        # Lepsze byłoby ID lub inny unikalny identyfikator.
        # Na potrzeby przykładu użyjemy id(), ale UWAGA: nie gwarantuje unikalności po usunięciu/stworzeniu widgetu!
        # Alternatywnie, MainWindow mógłby zarządzać unikalnymi ID.
        mime_data.setData(TAB_MIME_TYPE, str(id(self._dragged_content_widget)).encode('utf-8'))
        mime_data.setText(self._dragged_tab_title) # Dodajemy też tytuł

        drag = QDrag(self)
        drag.setMimeData(mime_data)

        # Screenshot zakładki jako podgląd
        pixmap = QPixmap(self.tabBar().tabRect(self._dragged_tab_index).size())
        self.tabBar().render(pixmap, QPoint(), self.tabBar().tabRect(self._dragged_tab_index))
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos() - self.tabBar().tabRect(self._dragged_tab_index).topLeft())

        # Ukryj oryginalną zakładkę (tymczasowo)
        # Uwaga: samo ukrycie może nie wystarczyć, lepiej usunąć i przechować
        original_index = self._dragged_tab_index # Zapisz przed usunięciem
        self.removeTab(self._dragged_tab_index)
        self._dragged_tab_index = -1 # Resetuj stan przeciągania w tym widgecie

        # Wyemituj sygnał, że przeciąganie się zaczęło (MainWindow musi wiedzieć)
        self.tabDraggedOut.emit(original_index, QCursor.pos()) # Przekaż globalną pozycję

        # Rozpocznij operację przeciągania
        drop_action = drag.exec_(Qt.MoveAction | Qt.CopyAction) # Zezwól na przenoszenie

        # --- Po zakończeniu przeciągania ---
        if drop_action == Qt.IgnoreAction:
            # Upuszczono w miejscu niedozwolonym LUB anulowano - przywróć zakładkę
            # MainWindow powinien to obsłużyć, bo zakładka mogła być już gdzieś dodana
            # print(f"Drag ignored, tab {self._dragged_tab_title} should be restored if not handled elsewhere.")
            # Jeśli MainWindow nie obsłużył, można spróbować przywrócić tutaj:
            # self.insertTab(original_index, self._dragged_content_widget, self._dragged_tab_title)
            pass # MainWindow powinien obsłużyć przywrócenie

        self._reset_drag_state()
        self.hide_drop_indicator()


    def _reset_drag_state(self):
        self._drag_start_position = QPoint()
        self._dragged_tab_index = -1
        self._dragged_content_widget = None
        self._dragged_tab_title = ""

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(TAB_MIME_TYPE):
            event.acceptProposedAction()
            # Nie pokazuj wskaźnika jeszcze tutaj, zrób to w dragMoveEvent
        else:
            event.ignore()
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(TAB_MIME_TYPE):
            event.acceptProposedAction()
            self.show_drop_indicator(event.pos()) # Pokaż wskaźnik w odpowiednim miejscu
        else:
            event.ignore()
        super().dragMoveEvent(event)

    def dragLeaveEvent(self, event):
        self.hide_drop_indicator()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        self.hide_drop_indicator()
        if event.mimeData().hasFormat(TAB_MIME_TYPE):
            # Identyfikator widgetu z danych MIME (bardzo uproszczone!)
            # W rzeczywistej aplikacji potrzebny byłby solidniejszy mechanizm identyfikacji.
            try:
                widget_id = int(event.mimeData().data(TAB_MIME_TYPE).data().decode('utf-8'))
            except (ValueError, TypeError):
                 print("Error: Invalid data in MIME for tab widget ID.")
                 event.ignore()
                 return

            # MainWindow powinien znaleźć widget po ID i przekazać go
            # Tutaj emitujemy sygnał, że coś zostało upuszczone
            # MainWindow złapie ten sygnał i zdecyduje, co zrobić
            # self.tabDroppedIn.emit(widget_id, event.mimeData().text(), event.pos(), self.mapToGlobal(event.pos()))

            # UPROSZCZONA WERSJA (bezpośrednie dodanie - niezalecane w złożonej architekturze):
            # Znajdź widget (wymaga dostępu do globalnego stanu lub przekazania)
            # W tej wersji zakładamy, że MainWindow przechwyci drag i sam doda widget

            # Zamiast tego, powiadamiamy MainWindow o potencjalnym dropie
            # MainWindow musi przechwycić DANE z eventu i zdecydować
            # Tutaj tylko akceptujemy drop, MainWindow dokona reszty
            print(f"Drop occurred on {self} at pos {event.pos()}")
            # MainWindow powinien teraz obsłużyć logikę dodania/podziału
            # Potrzebujemy sposobu, aby MainWindow wiedział, który widget upuszczono
            # Można przekazać pozycję globalną i widget docelowy
            self.parent().handle_drop_event(self, event) # Przekazujemy event do rodzica (zakładając, że to MainWindow lub manager)

            event.acceptProposedAction()
        else:
            event.ignore()
        # Nie wołamy super().dropEvent(event), bo sami obsługujemy

    def show_drop_indicator(self, pos):
        """ Pokazuje wskaźnik upuszczenia w odpowiednim miejscu. """
        # TODO: Bardziej zaawansowana logika dzielenia (krawędzie vs środek)
        rect = self.rect()
        margin = int(rect.height() * 0.25) # 25% margines na krawędzie
        width_margin = int(rect.width() * 0.25)

        drop_zone = QRect()
        self.drop_indicator.split_orientation = None # Reset

        # Prosta logika: środek vs krawędzie
        if QRect(rect.topLeft() + QPoint(width_margin, margin), rect.bottomRight() - QPoint(width_margin, margin)).contains(pos):
            # Środek - wstaw jako nową zakładkę
            drop_zone = self.tabBar().geometry() # Celuj w pasek zakładek
            self.drop_indicator.split_orientation = Qt.TargetIsCentralWidget # Własna stała
        elif pos.y() < margin: # Górna krawędź
            drop_zone = QRect(rect.topLeft(), QPoint(rect.right(), rect.top() + rect.height() // 2))
            self.drop_indicator.split_orientation = Qt.Vertical
            self.drop_indicator.split_half = 0 # Górna połowa
        elif pos.y() > rect.height() - margin: # Dolna krawędź
            drop_zone = QRect(QPoint(rect.left(), rect.top() + rect.height() // 2), rect.bottomRight())
            self.drop_indicator.split_orientation = Qt.Vertical
            self.drop_indicator.split_half = 1 # Dolna połowa
        elif pos.x() < width_margin: # Lewa krawędź
             drop_zone = QRect(rect.topLeft(), QPoint(rect.left() + rect.width() // 2, rect.bottom()))
             self.drop_indicator.split_orientation = Qt.Horizontal
             self.drop_indicator.split_half = 0 # Lewa połowa
        elif pos.x() > rect.width() - width_margin: # Prawa krawędź
             drop_zone = QRect(QPoint(rect.left() + rect.width() // 2, rect.top()), rect.bottomRight())
             self.drop_indicator.split_orientation = Qt.Horizontal
             self.drop_indicator.split_half = 1 # Prawa połowa
        else:
             # Domyślnie środek, jeśli gdzieś pomiędzy
             drop_zone = self.tabBar().geometry()
             self.drop_indicator.split_orientation = Qt.TargetIsCentralWidget

        # Mapuj lokalny prostokąt na globalne koordynaty okna
        global_top_left = self.mapTo(self.window(), drop_zone.topLeft())
        global_bottom_right = self.mapTo(self.window(), drop_zone.bottomRight())
        self.drop_indicator.setGeometry(QRect(global_top_left, global_bottom_right))
        self.drop_indicator.raise_()
        self.drop_indicator.show()

    def hide_drop_indicator(self):
        self.drop_indicator.hide()

# --- Potrzebujemy sygnałów PyQt5 ---
from PyQt5.QtCore import pyqtSignal