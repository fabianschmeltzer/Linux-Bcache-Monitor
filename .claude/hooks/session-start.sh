#!/bin/bash
# SessionStart-Hook für Claude Code im Web: installiert die Entwicklungs-
# abhängigkeiten (pytest, flake8), damit Tests und Linter in der Sitzung laufen.
# Lokal (nicht im Web) wird der Hook übersprungen.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(pwd)}"

python3 -m pip install --quiet --disable-pip-version-check -r requirements-dev.txt
