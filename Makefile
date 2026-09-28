# Entwicklungsbefehle für Linux-Bcache-Monitor.
# Das Skript selbst hat keine Drittabhängigkeiten; nur die Tests brauchen pytest.

PYTHON ?= python3

.PHONY: help install compile lint lint-strict test check version clean

help:
	@echo "make install   - Entwicklungsabhängigkeiten installieren (pytest, flake8)"
	@echo "make compile   - Skript syntaktisch prüfen (py_compile)"
	@echo "make lint      - flake8 wie im CI (harte Fehler + Statistik)"
	@echo "make test      - pytest ausführen"
	@echo "make check     - compile + lint + test (entspricht dem CI)"
	@echo "make version   - Versionsstände von VERSION, Skript und README anzeigen"
	@echo "make clean     - Caches entfernen"

install:
	$(PYTHON) -m pip install -r requirements-dev.txt

compile:
	$(PYTHON) -m py_compile bcache-monitor

lint-strict:
	$(PYTHON) -m flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

lint: lint-strict
	$(PYTHON) -m flake8 . --count --exit-zero --statistics

test:
	$(PYTHON) -m pytest

check: compile lint test

version:
	@echo "VERSION:        $$(cat VERSION)"
	@echo "bcache-monitor: $$(grep -m1 '^__version__' bcache-monitor | cut -d'"' -f2)"
	@echo "README.md:      $$(grep -m1 -o '\*\*Version:\*\* [0-9.]*' README.md | cut -d' ' -f2)"

clean:
	rm -rf .pytest_cache __pycache__ tests/__pycache__
	find . -name '*.pyc' -delete
