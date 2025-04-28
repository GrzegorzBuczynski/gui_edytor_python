# Makefile w ~/Documents/python/gui_edytor_python/

PYTHON_EXEC = python3
VENV_DIR = myenv
VENV_ACTIVATE = $(VENV_DIR)/bin/activate
VENV_PYTHON = $(VENV_DIR)/bin/python3
# Plik znacznikowy potwierdzający instalację
INSTALL_STAMP = $(VENV_DIR)/.installed

.DEFAULT_GOAL := help

.PHONY: all run venv install setup clean help

all: run ## Uruchamia aplikację (domyślna akcja)

# Cel run zależy teraz od znacznika instalacji
run: $(INSTALL_STAMP) ## Uruchamia główny skrypt aplikacji
	@echo "Uruchamianie aplikacji z folderu srcs..."
	# Uruchamiamy skrypt z katalogu srcs używając interpretera z venv
	cd srcs && ../$(VENV_PYTHON) app.py

# Ten cel JEST teraz procesem instalacji.
# Zależy od istnienia venv i pliku requirements.txt.
# Komendy tego celu instalują pakiety i tworzą znacznik.
$(INSTALL_STAMP): $(VENV_ACTIVATE) requirements.txt
	@echo "Instalowanie/Aktualizowanie zależności..."
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PYTHON) -m pip install PyQt5
	# Jeśli masz plik requirements.txt:
	# $(VENV_PYTHON) -m pip install -r requirements.txt
	@echo "Zależności zainstalowane/zaktualizowane."
	# Utwórz/zaktualizuj plik znacznikowy po sukcesie
	touch $(INSTALL_STAMP)

# install i setup mogą teraz po prostu zależeć od znacznika
install: $(INSTALL_STAMP) ## Instaluje/Aktualizuje zależności

setup: $(INSTALL_STAMP) ## Konfiguruje środowisko (tworzy venv i instaluje zależności)
	@echo "Środowisko skonfigurowane."

# Cel venv tylko tworzy strukturę katalogów venv
venv: $(VENV_ACTIVATE)

$(VENV_ACTIVATE):
	# Sprawdź, czy folder venv istnieje, jeśli nie, utwórz go
	test -d $(VENV_DIR) || $(PYTHON_EXEC) -m venv $(VENV_DIR)
	# Dotknięcie pliku jest potrzebne, aby make wiedział, że istnieje,
	# nawet jeśli venv został utworzony wcześniej.
	touch $(VENV_ACTIVATE)

clean: ## Usuwa wirtualne środowisko i pliki __pycache__
	@echo "Czyszczenie..."
	rm -rf $(VENV_DIR)
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