# Makefile w ~/Documents/python/gui_edytor_python/

# Zmienna przechowująca ścieżkę do interpretera python w venv
# Użyjemy python3 -m venv, więc interpreterem będzie python3
PYTHON_EXEC = python3
# Ścieżka do aktywatora venv (dla zależności)
VENV_ACTIVATE = myenv/bin/activate
# Pełna ścieżka do interpretera w venv
VENV_PYTHON = myenv/bin/python3

.DEFAULT_GOAL := help

.PHONY: all run venv install setup clean help

all: run ## Uruchamia aplikację (domyślna akcja)

run: $(VENV_ACTIVATE) ## Uruchamia główny skrypt aplikacji
	@echo "Uruchamianie aplikacji z folderu srcs..."
	# Uruchamiamy skrypt z katalogu srcs używając interpretera z venv
	cd srcs && ../$(VENV_PYTHON) app.py

# Tworzy venv używając systemowego python3
venv: $(VENV_ACTIVATE)

$(VENV_ACTIVATE): requirements.txt # Można dodać plik requirements.txt
	# Sprawdź, czy folder venv istnieje, jeśli nie, utwórz go
	test -d myenv || $(PYTHON_EXEC) -m venv myenv
	# Upewnij się, że plik activate istnieje po utworzeniu venv
	# Dotknięcie pliku aktualizuje jego znacznik czasu dla 'make'
	touch $(VENV_ACTIVATE)
	@echo "Utworzono/Zaktualizowano venv. Zainstaluj zależności 'make install'."

install: $(VENV_ACTIVATE) ## Instaluje zależności z requirements.txt (lub tylko PyQt5)
	@echo "Instalowanie zależności..."
	# Użyj interpretera z venv do uruchomienia modułu pip
	$(VENV_PYTHON) -m pip install --upgrade pip # Najpierw zaktualizuj pip
	$(VENV_PYTHON) -m pip install PyQt5
	# Jeśli masz plik requirements.txt:
	# $(VENV_PYTHON) -m pip install -r requirements.txt
	@echo "Zależności zainstalowane."

setup: install ## Konfiguruje środowisko (tworzy venv i instaluje zależności)
	@echo "Środowisko skonfigurowane."

clean: ## Usuwa wirtualne środowisko i pliki __pycache__
	@echo "Czyszczenie..."
	rm -rf myenv
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -exec rm -rf {} +
	@echo "Wyczyszczono."

help: ## Wyświetla tę pomoc
	@echo "Dostępne komendy make:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

# Opcjonalnie: Stwórz pusty requirements.txt, jeśli nie masz
requirements.txt:
	touch requirements.txt
	
push:
	git add .
	git commit -m "Update"
	git push