# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projekt

Linux-Bcache-Monitor ist ein **einzelnes ausführbares Python-Skript** (`bcache-monitor`, keine `.py`-Endung, ~4000 Zeilen) für die Überwachung von Linux-bcache-Setups. Es gibt keine Paketstruktur, kein `setup.py` und keine Laufzeit-Drittabhängigkeiten: nur die Standardbibliothek (curses, sysfs-Zugriffe, subprocess für `docker`, `nvme`, `smartctl`). Zielplattform ist Linux mit Python ≥ 3.8; CI testet 3.8, 3.11 und 3.13.

Die Oberfläche ist zweisprachig (Deutsch/Englisch, umschaltbar in den Einstellungen). Kommunikation mit dem Projektinhaber erfolgt auf Deutsch.

## Befehle

```bash
make install        # pytest + flake8 installieren (requirements-dev.txt)
make check          # compile + lint + test, entspricht dem CI
make test           # python3 -m pytest
make lint           # flake8 mit den CI-Einstellungen (.flake8)
make compile        # python3 -m py_compile bcache-monitor
make version        # Versionsstände in VERSION, Skript und README vergleichen

# Einzelnen Test ausführen
python3 -m pytest tests/test_smoke.py::test_format_cache_mode_shows_only_active_bracketed_mode

# Skript ohne curses-Dashboard ausführen
./bcache-monitor --version
./bcache-monitor --diagnose          # Text-Report, Exit-Code 0/1/2
./bcache-monitor --diagnose-json     # schema-versioniertes JSON
./bcache-monitor --prometheus        # ein Metrik-Snapshot (Alias: --metrics)
```

CI (`.github/workflows/tests.yml`, `python-package.yml`): `py_compile`, flake8 (nur `E9,F63,F7,F82` sind harte Fehler, der Rest ist `--exit-zero` mit `max-line-length=127`) und `pytest`.

## Tests

`tests/test_smoke.py` lädt das Skript per `SourceFileLoader` als Modul `bcache_monitor` (es hat keine `.py`-Endung, ein normaler Import funktioniert nicht). Alles, was oberhalb von `if __name__ == "__main__"` steht, wird beim Laden ausgeführt; Modul-Konstanten wie `SYSFS_ROOT` werden in Tests per `monkeypatch.setattr(bcache_monitor, ...)` überschrieben.

Wichtige Testmuster:
- `_fake_bcache_sysfs(tmp_path, monkeypatch)` baut einen kompletten sysfs-Baum nach (Backing-Partition, Cache-Partition, Cache-Set unter `fs/bcache/<uuid>`, Symlinks in `class/block`). Neue Topologie-Tests sollten diese Fixture erweitern statt eine eigene zu bauen. Ein echtes Cache-Set enthält neben `cache0` auch Attributdateien wie `cache_available_percent`; Cache-Mitglieder werden deshalb über `cache_member_paths()` ermittelt, nie über ein bloßes `cache*`-Glob.
- `FakeScreen` ersetzt das curses-Fenster und sammelt alle `addstr`-Aufrufe; Render-Tests prüfen damit, dass jede Ausgabe innerhalb der Terminalgrenzen bleibt.
- `test_version_metadata_is_in_sync` erzwingt, dass `VERSION`, `__version__` im Skript und `**Version:** x.y.z` in `README.md` identisch sind und der Test selbst die erwartete Version kennt.

## Versionierung und Self-Update

Eine Versionsänderung erfordert **vier** gleichzeitige Änderungen: `VERSION`, `__version__` im Skript, `**Version:**` in `README.md` und die Literale in `test_version_metadata_is_in_sync` / `test_print_version_and_exit_for_cli_flag`. `make version` zeigt die ersten drei.

Das Skript aktualisiert sich beim Start selbst (`self_update_if_needed`): es lädt `VERSION` und das Skript von den GitHub-Raw-URLs des `main`-Branches (`VERSION_URL`, `SCRIPT_URL`), validiert Größe, Syntax und Versionsstring (`validate_update_script`) und startet sich neu. Ein Push nach `main` mit erhöhter Version wird also sofort an alle Installationen ausgeliefert. Fehlversuche werden über `BCACHE_MONITOR_UPDATE_FAIL_COUNT` gezählt und nach `MAX_UPDATE_FAILURES` gestoppt.

## Architektur des Skripts

Das Skript ist von oben nach unten in Schichten aufgebaut:

1. **Konfiguration und Konstanten** (Dateianfang): fast alle Schwellwerte, Intervalle und Pfade sind Modul-Konstanten, viele per `BCACHE_MONITOR_*`-Umgebungsvariable überschreibbar. `SYSFS_ROOT`, `PROC_ROOT`, `DEV_ROOT` erlauben es, sysfs/proc/dev in Tests umzuleiten; alle Pfadzugriffe sollen über `sysfs_path()`, `proc_path()`, `dev_path()` gehen.
2. **Lokalisierung**: `TRANSLATIONS` ist ein Dict `{ "de": {...}, "en": {...} }`; Texte werden über `tr(config_or_state, key)` aufgelöst. Neue UI-Texte brauchen immer beide Sprachen. Zusätzlich gibt es `localize_*`-Funktionen für Status-, Quellen- und Fehlermeldungen.
3. **Datenerfassung**: `read_metric()` liefert `MetricValue` (Wert, Quelle, Status `ok|unavailable|error`, Grund); `read()` ist die Kurzform, die nur den Wert oder `None` gibt. Die Topologie (`discover_bcache_topology` → `BcacheTopology`) löst Backing-Gerät, Cache-Set, Cache-Blockgeräte und die physischen Geräte für SMART-Daten (`leaf_block_devices`, folgt `slaves/` und Partitionen) auf. `read_bcache_details()` bündelt alle sysfs-Werte, `read_ssd_health()` fragt `nvme`/`smartctl` ab (JSON bevorzugt, Text-Parser als Fallback), Docker-Werte kommen aus `docker stats`.
4. **Bewertung**: `health_report()`, `recommendations()`, `detect_anomalies()`, `maintenance_guard()`, `automatic_diagnosis()` arbeiten rein auf den gesammelten Dicts. Grundregel: Empfehlungen werden unterdrückt, wenn ihre Quelldaten fehlen, und das Tool schreibt nie bcache-Tuning-Werte.
5. **Ausgabekanäle**: `collect_monitor_snapshot(config)` ist der gemeinsame Einstieg für die Nicht-TUI-Modi. Darauf setzen `diagnostic_payload()` (`schema_version`, keine Seriennummern, keine SMART-Rohausgabe), `format_diagnostic_text()` und `prometheus_metrics()` auf. Fehlende optionale Werte werden in Prometheus weggelassen, nie als `0`/`-1` exportiert.
6. **TUI** (curses): `AppState` hält den Laufzeitzustand (Ringpuffer `deque` für Hit/Miss/Effizienz-Historie, Docker-Cache, Ratenfenster). `draw_main()` ist die Hauptschleife, `render_dashboard()` zeichnet abhängig von `dashboard_layout(height, width)` eines der Profile `minimal`, `stacked`, `split`, `wide`. Alle Zeichenaufrufe gehen über `safe_addstr()`; `draw_settings()` und `draw_info()` sind die weiteren Ansichten. Die Historie wird minütlich als CSV nach `HISTORY_CSV_PATH` geschrieben.
7. **CLI-Einstieg**: `main()` prüft nacheinander `--version`, `--diagnose[-json]`, `--prometheus`, führt dann das Self-Update aus und startet `curses.wrapper(init)`.

## Konventionen

- Datenfunktionen liefern bei fehlenden Daten `None` und einen Grund, statt Ausnahmen zu werfen oder Platzhalterwerte zu erfinden; die Anzeige übersetzt `None` in `N/A`.
- Externe Kommandos laufen mit Timeout über `_run_command()`; fehlende Werkzeuge erzeugen einen Hinweis (`DEPENDENCY_INSTALL_HINTS`), aber keinen Abbruch.
- README-Änderungen: Die README ist englisch, enthält aber die Versionsangabe, die vom Test geprüft wird.
